"""SQLite-backed persistence for FleetOps.

One file: schema + seed + CRUD repos. Database lives at `./fleetops.db`.
Call `db.init()` once at app startup. Each repo function opens a fresh
connection so we don't have to thread a connection through views.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "fleetops.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'manager',
    name TEXT NOT NULL DEFAULT 'Fleet Manager'
);

CREATE TABLE IF NOT EXISTS robots (
    id TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    serial TEXT NOT NULL,
    status TEXT NOT NULL,            -- Working / Ready / Idle / Maintenance / Active
    zone TEXT NOT NULL,
    battery REAL NOT NULL,           -- 0..1
    last_maintenance TEXT NOT NULL,
    temperature REAL NOT NULL DEFAULT 32,
    signal TEXT NOT NULL DEFAULT 'Excellent'
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,            -- Queued / In Progress / Completed / Aborted / Paused
    priority TEXT NOT NULL,          -- Low / Medium / High / Urgent
    source TEXT NOT NULL,
    destination TEXT NOT NULL,
    robot_id TEXT,
    progress REAL NOT NULL DEFAULT 0,
    elapsed_secs INTEGER NOT NULL DEFAULT 0,
    description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS zones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    used INTEGER NOT NULL,
    capacity INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'NORMAL'   -- NORMAL / WARNING / CRITICAL
);

CREATE TABLE IF NOT EXISTS bays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,            -- ACTIVE / AVAILABLE / MAINTENANCE
    robot_id TEXT,
    charge REAL,
    eta_minutes INTEGER,
    health REAL
);

CREATE TABLE IF NOT EXISTS queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    robot_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    eta TEXT NOT NULL,
    battery REAL NOT NULL,
    position INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    meta TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mission_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    msg TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS op_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    robot_id TEXT NOT NULL,
    date TEXT NOT NULL,
    kind TEXT NOT NULL,              -- Maintenance / Software / Error
    body TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def cursor():
    conn = _connect()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    finally:
        conn.close()


def init(force_reseed: bool = False) -> None:
    """Create schema + seed if empty (or always if force_reseed)."""
    with cursor() as cur:
        cur.executescript(SCHEMA)
        cur.execute("SELECT COUNT(*) FROM robots")
        already_seeded = cur.fetchone()[0] > 0
    if force_reseed or not already_seeded:
        _seed()


def reset() -> None:
    """Drop everything and reseed — useful for the 'Reset Demo Data' button."""
    if DB_PATH.exists():
        os.remove(DB_PATH)
    init(force_reseed=True)


def _seed() -> None:
    with cursor() as cur:
        cur.execute("DELETE FROM users")
        cur.execute("INSERT INTO users (email, password, role, name) VALUES (?,?,?,?)",
                    ("admin@fleetops.logistics", "fleetops", "manager", "Fleet Manager"))

        cur.execute("DELETE FROM robots")
        cur.executemany(
            "INSERT INTO robots (id, model, serial, status, zone, battery, "
            "last_maintenance, temperature, signal) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            [
                ("RX-701", "Titan-X Cargo Lifter", "TX-7001-AA", "Working",
                 "Loading A-1", 0.84, "2d ago", 32, "Excellent"),
                ("RX-705", "Titan-X Cargo Lifter", "TX-7005-AB", "Ready",
                 "Staging-B",   0.96, "5d ago", 30, "Excellent"),
                ("RX-712", "SwiftBot",             "SB-7012-AC", "Idle",
                 "Charging-03", 0.12, "12h ago", 28, "Good"),
                ("RX-802", "SwiftBot",             "SB-8002-AD", "Working",
                 "Picking-C4", 0.45, "3d ago", 36, "Excellent"),
                ("RX-699", "Titan-X Cargo Lifter", "TX-6999-AE", "Maintenance",
                 "Repair-Tech", 0.0, "Active", 0, "Offline"),
                ("RBT-904", "Titan-X Cargo Lifter", "TX-8829-BK", "Active",
                 "B-Sector 4", 0.84, "1d ago", 42, "Excellent"),
            ],
        )

        cur.execute("DELETE FROM tasks")
        cur.executemany(
            "INSERT INTO tasks (id, name, kind, status, priority, source, "
            "destination, robot_id, progress, elapsed_secs, description) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [
                ("TASK-8422", "Pallet Relocation", "Pallet Transfer", "In Progress",
                 "High",   "Incoming-Zone B", "Storage-Row 14", "RX-701", 0.40, 600,
                 "Move 6 mixed pallets from incoming bay to long-term storage."),
                ("TASK-8425", "Order Picking", "Order Picking", "In Progress",
                 "Normal", "Bulk-Zone C", "Sorting-A", "RX-802", 0.55, 320,
                 "Standard order picking sweep through bulk zone C."),
                ("TSK-4421", "Pallet Transfer", "Pallet Transfer", "In Progress",
                 "High",   "Loading Bay 04", "Storage Rack C-12", "RBT-904", 0.65, 512,
                 "Mission assigned to SwiftBot Alpha for inventory optimization."),
                ("TSK-88219", "Inventory Move", "Pallet Transfer", "In Progress",
                 "High",   "Inventory Zone B-4", "Loading Dock 02", "RBT-904", 0.68, 240,
                 "High-priority transfer to outbound dock."),
            ],
        )

        cur.execute("DELETE FROM zones")
        cur.executemany(
            "INSERT INTO zones (name, category, used, capacity, status) VALUES (?,?,?,?,?)",
            [
                ("Zone A (Cold)", "COLD", 420, 500, "NORMAL"),
                ("Zone B (Bulk)", "BULK", 880, 900, "CRITICAL"),
                ("Zone C (Picking)", "PICKING", 150, 1000, "NORMAL"),
                ("Zone D (Haz)", "HAZ", 45, 100, "NORMAL"),
                ("Zone E (Sorting)", "SORTING", 290, 400, "NORMAL"),
                ("Zone F (Dispatch)", "DISPATCH", 580, 600, "CRITICAL"),
                ("Storage A-1", "STATIC STORAGE", 920, 1000, "CRITICAL"),
                ("Storage A-2", "STATIC STORAGE", 880, 1000, "WARNING"),
                ("Storage B-1", "COLD STORAGE", 300, 1000, "NORMAL"),
                ("Storage B-2", "COLD STORAGE", 955, 1000, "CRITICAL"),
                ("Inbound Alpha", "LOADING", 450, 1000, "NORMAL"),
                ("Outbound Beta", "LOADING", 780, 1000, "WARNING"),
                ("Picking Lane 1", "PICKING", 650, 1000, "NORMAL"),
                ("QC Station 4", "QUALITY CONTROL", 120, 1000, "NORMAL"),
            ],
        )

        cur.execute("DELETE FROM bays")
        cur.executemany(
            "INSERT INTO bays (name, status, robot_id, charge, eta_minutes, health) "
            "VALUES (?,?,?,?,?,?)",
            [
                ("BAY-01", "ACTIVE",      "ROBO-77", 0.82, 12,  0.98),
                ("BAY-02", "ACTIVE",      "ROBO-12", 0.45, 48,  0.95),
                ("BAY-03", "AVAILABLE",   None,      None, None, None),
                ("BAY-04", "ACTIVE",      "ROBO-94", 0.12, 75,  0.88),
                ("BAY-05", "MAINTENANCE", None,      None, None, None),
                ("BAY-06", "ACTIVE",      "ROBO-05", 0.95, 3,   0.99),
            ],
        )

        cur.execute("DELETE FROM queue")
        cur.executemany(
            "INSERT INTO queue (robot_id, reason, eta, battery, position) "
            "VALUES (?,?,?,?,?)",
            [
                ("ROBO-22", "Low Battery Alert", "Est. 5m",  0.08, 1),
                ("ROBO-41", "Shift End",         "Est. 12m", 0.18, 2),
                ("ROBO-15", "Preventative",      "Est. 20m", 0.22, 3),
                ("ROBO-33", "Scheduled",         "Est. 25m", 0.25, 4),
            ],
        )

        cur.execute("DELETE FROM alerts")
        cur.executemany(
            "INSERT INTO alerts (kind, title, body, meta, created_at) "
            "VALUES (?,?,?,?,?)",
            [
                ("critical", "Battery Critical", "Battery below 15% threshold",
                 "RX-712", "2 min ago"),
                ("critical", "Task Failed", "Obstruction in Picking Zone C-4",
                 "RX-802", "14 min ago"),
                ("info", "System Update",
                 "Maintenance window starting at 22:00", "Global", "1 hour ago"),
                ("info", "Sensor Warning", "Lidar calibration variance high",
                 "RX-705", "2 hours ago"),
            ],
        )

        cur.execute("DELETE FROM mission_log")
        cur.executemany(
            "INSERT INTO mission_log (task_id, ts, msg) VALUES (?,?,?)",
            [
                ("TSK-4421", "14:00:12", "Task initialized. Fleet manager approval granted."),
                ("TSK-4421", "14:01:45", "Robot SwiftBot Alpha (ROBOT-X9) assigned to task."),
                ("TSK-4421", "14:03:10", "Navigation path calculated: 124m estimated."),
                ("TSK-4421", "14:05:22", "Robot arrived at Source Zone (L-04). Pallet securing in progress."),
                ("TSK-4421", "14:06:55", "Pallet secured. Integrity check passed. Commencing transport."),
                ("TSK-4421", "14:08:12", "Entering High Traffic Zone (Sector B). Adjusting speed to 0.5m/s."),
            ],
        )

        cur.execute("DELETE FROM op_history")
        cur.executemany(
            "INSERT INTO op_history (robot_id, date, kind, body) VALUES (?,?,?,?)",
            [
                ("RBT-904", "Oct 24, 14:20", "Maintenance", "Drive wheel alignment and sensor calibration."),
                ("RBT-904", "Oct 22, 08:45", "Software",    "Firmware update to v4.2.1 - Pathing Optimization."),
                ("RBT-904", "Oct 20, 11:30", "Error",       "Obstacle detection timeout in Aisle 4."),
                ("RBT-904", "Oct 15, 16:00", "Maintenance", "Scheduled battery health checkup."),
                ("RBT-904", "Oct 12, 09:15", "Error",       "WiFi signal drop during zone transition."),
            ],
        )


# ---------- Repos ----------

def authenticate(email: str, password: str) -> dict | None:
    with cursor() as cur:
        cur.execute("SELECT * FROM users WHERE email = ? AND password = ?",
                    (email.strip().lower(), password))
        row = cur.fetchone()
        return dict(row) if row else None


def list_robots() -> list[dict]:
    with cursor() as cur:
        cur.execute("SELECT * FROM robots ORDER BY id")
        return [dict(r) for r in cur.fetchall()]


def get_robot(robot_id: str) -> dict | None:
    with cursor() as cur:
        cur.execute("SELECT * FROM robots WHERE id = ?", (robot_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def update_robot_status(robot_id: str, status: str, *, zone: str | None = None) -> None:
    with cursor() as cur:
        if zone:
            cur.execute("UPDATE robots SET status=?, zone=? WHERE id=?",
                        (status, zone, robot_id))
        else:
            cur.execute("UPDATE robots SET status=? WHERE id=?", (status, robot_id))


def list_tasks(*, status: str | None = None, limit: int | None = None) -> list[dict]:
    with cursor() as cur:
        sql = "SELECT * FROM tasks"
        args: tuple = ()
        if status:
            sql += " WHERE status = ?"
            args = (status,)
        sql += " ORDER BY id"
        if limit:
            sql += f" LIMIT {int(limit)}"
        cur.execute(sql, args)
        return [dict(r) for r in cur.fetchall()]


def get_task(task_id: str) -> dict | None:
    with cursor() as cur:
        cur.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def insert_task(*, name: str, kind: str, priority: str, source: str,
                destination: str, robot_id: str | None,
                description: str = "") -> str:
    """Auto-assign a TASK-#### id."""
    with cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(CAST(SUBSTR(id, 6) AS INTEGER)), 8500) "
                    "FROM tasks WHERE id LIKE 'TASK-%'")
        next_n = (cur.fetchone()[0] or 8500) + 1
        new_id = f"TASK-{next_n}"
        cur.execute(
            "INSERT INTO tasks (id, name, kind, status, priority, source, "
            "destination, robot_id, progress, elapsed_secs, description) "
            "VALUES (?,?,?,'Queued',?,?,?,?,0,0,?)",
            (new_id, name, kind, priority, source, destination, robot_id, description),
        )
        return new_id


def update_task_status(task_id: str, status: str) -> None:
    with cursor() as cur:
        cur.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))


def update_task_priority(task_id: str, priority: str) -> None:
    with cursor() as cur:
        cur.execute("UPDATE tasks SET priority=? WHERE id=?", (priority, task_id))


def delete_task(task_id: str) -> None:
    with cursor() as cur:
        cur.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        cur.execute("DELETE FROM mission_log WHERE task_id=?", (task_id,))


def list_zones(*, categories: tuple[str, ...] | None = None) -> list[dict]:
    with cursor() as cur:
        if categories:
            placeholders = ",".join("?" * len(categories))
            cur.execute(f"SELECT * FROM zones WHERE category IN ({placeholders}) "
                        "ORDER BY id", categories)
        else:
            cur.execute("SELECT * FROM zones ORDER BY id")
        return [dict(r) for r in cur.fetchall()]


def get_zone(zone_id: int) -> dict | None:
    with cursor() as cur:
        cur.execute("SELECT * FROM zones WHERE id = ?", (zone_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def update_zone(zone_id: int, *, used: int, capacity: int) -> None:
    pct = used / capacity if capacity else 0
    status = "CRITICAL" if pct >= 0.9 else "WARNING" if pct >= 0.78 else "NORMAL"
    with cursor() as cur:
        cur.execute("UPDATE zones SET used=?, capacity=?, status=? WHERE id=?",
                    (used, capacity, status, zone_id))


def list_bays() -> list[dict]:
    with cursor() as cur:
        cur.execute("SELECT * FROM bays ORDER BY name")
        return [dict(r) for r in cur.fetchall()]


def reset_bay(bay_id: int) -> None:
    """Reset cycle: clear charge progress, keep robot assigned."""
    with cursor() as cur:
        cur.execute("UPDATE bays SET charge = 0.05, eta_minutes = "
                    "COALESCE(eta_minutes, 0) + 30 WHERE id=?", (bay_id,))


def update_bay_status(bay_id: int, status: str) -> None:
    with cursor() as cur:
        if status == "AVAILABLE":
            cur.execute("UPDATE bays SET status=?, robot_id=NULL, charge=NULL, "
                        "eta_minutes=NULL, health=NULL WHERE id=?",
                        (status, bay_id))
        else:
            cur.execute("UPDATE bays SET status=? WHERE id=?", (status, bay_id))


def list_queue() -> list[dict]:
    with cursor() as cur:
        cur.execute("SELECT * FROM queue ORDER BY position")
        return [dict(r) for r in cur.fetchall()]


def remove_queue_entry(entry_id: int) -> None:
    with cursor() as cur:
        cur.execute("DELETE FROM queue WHERE id=?", (entry_id,))


def reorder_queue() -> None:
    """Re-rank charging queue by ascending battery (lowest = position 1)."""
    with cursor() as cur:
        cur.execute("SELECT id FROM queue ORDER BY battery ASC, id ASC")
        ids = [row[0] for row in cur.fetchall()]
        for new_pos, qid in enumerate(ids, start=1):
            cur.execute("UPDATE queue SET position=? WHERE id=?", (new_pos, qid))


def recall_idle_robots() -> int:
    """Bulk action: send any Idle robot back to Home Dock as Ready. Returns count."""
    with cursor() as cur:
        cur.execute("UPDATE robots SET status='Ready', zone='Home Dock' "
                    "WHERE status='Idle'")
        return cur.rowcount


def list_alerts(limit: int = 10) -> list[dict]:
    with cursor() as cur:
        cur.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]


def dismiss_alert(alert_id: int) -> None:
    with cursor() as cur:
        cur.execute("DELETE FROM alerts WHERE id=?", (alert_id,))


def insert_alert(kind: str, title: str, body: str, meta: str,
                 created_at: str = "just now") -> None:
    with cursor() as cur:
        cur.execute("INSERT INTO alerts (kind, title, body, meta, created_at) "
                    "VALUES (?,?,?,?,?)", (kind, title, body, meta, created_at))


def list_mission_log(task_id: str) -> list[dict]:
    with cursor() as cur:
        cur.execute("SELECT * FROM mission_log WHERE task_id=? ORDER BY id",
                    (task_id,))
        return [dict(r) for r in cur.fetchall()]


def append_mission_log(task_id: str, ts: str, msg: str) -> None:
    with cursor() as cur:
        cur.execute("INSERT INTO mission_log (task_id, ts, msg) VALUES (?,?,?)",
                    (task_id, ts, msg))


def list_op_history(robot_id: str) -> list[dict]:
    with cursor() as cur:
        cur.execute("SELECT * FROM op_history WHERE robot_id=? ORDER BY id DESC",
                    (robot_id,))
        return [dict(r) for r in cur.fetchall()]


# Aggregates for dashboard KPIs

def kpis() -> dict:
    with cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM robots WHERE status NOT IN ('Maintenance','Offline')")
        active = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM tasks WHERE status='Completed'")
        completed = cur.fetchone()[0]
        cur.execute("SELECT AVG(battery) FROM robots WHERE status != 'Maintenance'")
        avg_batt = (cur.fetchone()[0] or 0) * 100
    return {
        "active": active or 42,             # fallback to mock if empty
        "completed": completed or 1284,
        "avg_battery": round(avg_batt) if avg_batt else 76,
    }


def zone_kpis() -> dict:
    with cursor() as cur:
        cur.execute("SELECT SUM(capacity), SUM(used), COUNT(*) FROM zones")
        total_cap, total_used, _ = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM zones WHERE status='CRITICAL'")
        critical = cur.fetchone()[0]
    rate = (total_used / total_cap * 100) if total_cap else 0
    return {
        "total_capacity": total_cap or 0,
        "active_load":    total_used or 0,
        "occupancy":      round(rate, 1),
        "critical":       critical or 0,
    }


def charging_kpis() -> dict:
    with cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM bays WHERE status='ACTIVE'")
        active = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM bays")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM bays WHERE status='AVAILABLE'")
        idle = cur.fetchone()[0]
    return {"active": active, "total": total, "idle": idle}
