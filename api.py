"""FleetOps FastAPI server.

Provides REST endpoints for the robot fleet data stored in fleetops.db.

Start with:
    uvicorn api:app --reload --port 8000

Swagger UI: http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="FleetOps API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = Path(__file__).parent / "fleetops.db"

# Valid choices (mirrors the db.py schema):
VALID_STATUSES = {"Working", "Ready", "Idle", "Maintenance", "Active"}
VALID_SIGNALS  = {"Excellent", "Good", "Fair", "Poor", "Offline"}


# Database helpers:

def _get_conn() -> sqlite3.Connection:
    """Open a fresh connection with Row factory enabled."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_table() -> None:
    """Make sure the robots table exists (it is created by db.init() in main.py)."""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS robots (
            id               TEXT PRIMARY KEY,
            model            TEXT NOT NULL,
            serial           TEXT NOT NULL,
            status           TEXT NOT NULL,
            zone             TEXT NOT NULL,
            battery          REAL NOT NULL,
            last_maintenance TEXT NOT NULL,
            temperature      REAL NOT NULL DEFAULT 32,
            signal           TEXT NOT NULL DEFAULT 'Excellent'
        )
    """)
    conn.commit()
    conn.close()


_ensure_table()


# Pydantic model:

class RobotIn(BaseModel):
    """Input schema for registering a new robot."""

    id: str = Field(..., min_length=1, description="Unique robot ID, e.g. RX-900")
    model: str = Field(..., min_length=1, description="Robot model name")
    serial: str = Field(..., min_length=1, description="Serial number")
    status: str = Field(..., description="One of: Working / Ready / Idle / Maintenance / Active")
    zone: str = Field(..., min_length=1, description="Warehouse zone")
    battery: float = Field(..., ge=0.0, le=1.0, description="Battery level 0.0 – 1.0")
    last_maintenance: str = Field(..., min_length=1, description="Last maintenance string, e.g. '2d ago'")
    temperature: float = Field(32.0, description="Core temperature in °C")
    signal: str = Field("Excellent", description="One of: Excellent / Good / Fair / Poor / Offline")

    @field_validator("status")
    @classmethod
    def check_status(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
        return v

    @field_validator("signal")
    @classmethod
    def check_signal(cls, v: str) -> str:
        if v not in VALID_SIGNALS:
            raise ValueError(f"signal must be one of {sorted(VALID_SIGNALS)}")
        return v


# GET /robots — list all robots:
from typing import Optional

@app.get("/robots", summary="List all robots")
def get_robots(search: Optional[str] = None) -> list[dict]:
    print(f">>> API: GET /robots called (search='{search}')")
    conn = _get_conn()
    if search:
        like = f"%{search}%"
        rows = conn.execute(
            "SELECT * FROM robots WHERE id LIKE ? OR model LIKE ? ORDER BY id",
            (like, like)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM robots ORDER BY id").fetchall()
    conn.close()
    print(f"--- API: Returning {len(rows)} robots")
    return [dict(row) for row in rows]


# GET /robots/{robot_id} — single robot:

@app.get("/robots/{robot_id}", summary="Get a single robot by ID")
def get_robot(robot_id: str) -> dict:
    print(f">>> API: GET /robots/{robot_id} called")
    conn = _get_conn()
    row = conn.execute("SELECT * FROM robots WHERE id = ?", (robot_id,)).fetchone()
    conn.close()
    if row is None:
        print(f"!!! API: Robot {robot_id} not found")
        raise HTTPException(status_code=404, detail=f"Robot '{robot_id}' not found")
    return dict(row)


# POST /robots — add a new robot:

@app.post("/robots", status_code=201, summary="Register a new robot")
def add_robot(robot: RobotIn) -> dict:
    print(f">>> API: POST /robots called for ID: {robot.id}")
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO robots "
            "(id, model, serial, status, zone, battery, last_maintenance, temperature, signal) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                robot.id,
                robot.model,
                robot.serial,
                robot.status,
                robot.zone,
                robot.battery,
                robot.last_maintenance,
                robot.temperature,
                robot.signal,
            ),
        )
        conn.commit()
        print(f"+++ API: Robot {robot.id} created successfully")
    except sqlite3.IntegrityError:
        conn.close()
        print(f"!!! API: IntegrityError - ID {robot.id} exists")
        raise HTTPException(
            status_code=409,
            detail=f"Robot ID '{robot.id}' already exists",
        )
    finally:
        conn.close()

    return {"message": "Robot registered successfully", "robot": robot.model_dump()}


# PUT /robots/{robot_id} — update a robot:

@app.put("/robots/{robot_id}", summary="Update an existing robot")
def update_robot(robot_id: str, robot: RobotIn) -> dict:
    print(f">>> API: PUT /robots/{robot_id} called")
    conn = _get_conn()
    row = conn.execute("SELECT id FROM robots WHERE id = ?", (robot_id,)).fetchone()
    if row is None:
        conn.close()
        print(f"!!! API: Cannot update, robot {robot_id} not found")
        raise HTTPException(status_code=404, detail=f"Robot '{robot_id}' not found")
    
    try:
        conn.execute(
            """UPDATE robots SET 
               model=?, serial=?, status=?, zone=?, battery=?, 
               last_maintenance=?, temperature=?, signal=?
               WHERE id=?""",
            (
                robot.model,
                robot.serial,
                robot.status,
                robot.zone,
                robot.battery,
                robot.last_maintenance,
                robot.temperature,
                robot.signal,
                robot_id,
            ),
        )
        conn.commit()
        print(f"*** API: Robot {robot_id} updated successfully")
    finally:
        conn.close()

    return {"message": "Robot updated successfully", "robot": robot.model_dump()}


# DELETE /robots/{robot_id} — delete a robot:

@app.delete("/robots/{robot_id}", summary="Delete a robot")
def delete_robot(robot_id: str) -> dict:
    print(f">>> API: DELETE /robots/{robot_id} called")
    conn = _get_conn()
    row = conn.execute("SELECT id FROM robots WHERE id = ?", (robot_id,)).fetchone()
    if row is None:
        conn.close()
        print(f"!!! API: Cannot delete, robot {robot_id} not found")
        raise HTTPException(status_code=404, detail=f"Robot '{robot_id}' not found")
    
    conn.execute("DELETE FROM robots WHERE id = ?", (robot_id,))
    conn.commit()
    conn.close()
    print(f"--- API: Robot {robot_id} deleted")
    return {"message": f"Robot '{robot_id}' deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
