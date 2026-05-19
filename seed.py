# seed.py — run to seed 100 robots for pagination testing
import sqlite3
import random
import string
from pathlib import Path
import db

def seed_data():
    print("Resetting database...")
    db.reset() # This drops tables, recreates schema, and seeds default records
    
    conn = sqlite3.connect(db.DB_PATH)

    models = ["SwiftBot", "Titan-X Cargo Lifter", "Apex Picker", "Drone-HD"]
    statuses = ["Working", "Ready", "Idle", "Maintenance", "Active"]
    zones = ["Zone A (Cold)", "Zone B (Bulk)", "Zone C (Picking)", "Storage A-1", "Storage B-2"]
    signals = ["Excellent", "Good", "Fair", "Poor", "Offline"]

    print("Adding 94 additional robots...")
    # Add 94 more robots to bring total to 100 (6 defaults + 94 generated)
    for i in range(1, 95):
        rnd = ''.join(random.choices(string.ascii_uppercase, k=4))
        rid = f"RBT-{i:03d}"
        model = random.choice(models)
        serial = f"{model[:2].upper()}-{i:03d}-{rnd}"
        status = random.choice(statuses)
        zone = random.choice(zones)
        battery = round(random.uniform(0.1, 1.0), 2)
        last_m = f"{random.randint(1, 15)}d ago"
        temp = round(random.uniform(25.0, 45.0), 1)
        sig = random.choice(signals)
        
        conn.execute(
            "INSERT OR IGNORE INTO robots VALUES (?,?,?,?,?,?,?,?,?)",
            (rid, model, serial, status, zone, battery, last_m, temp, sig)
        )

    conn.commit()
    conn.close()
    print("Database fully reset and seeded with exactly 100 robots total.")

if __name__ == "__main__":
    seed_data()
