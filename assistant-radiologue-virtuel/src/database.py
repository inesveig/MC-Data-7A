"""
Journalisation des inférences dans SQLite.
Chaque appel /predict est enregistré pour traçabilité.
"""

import sqlite3
import json
import time
from pathlib import Path

DB_DEFAULT = Path("data/evidence.sqlite")


def init_db(db_path: Path = DB_DEFAULT):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            image_name  TEXT,
            prompt_version TEXT,
            model_name  TEXT,
            predicted_class TEXT,
            confidence  REAL,
            image_quality TEXT,
            latency_ms  REAL,
            json_valid  INTEGER,
            output_json TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_prediction(
    image_name: str,
    prompt_version: str,
    model_name: str,
    result: dict,
    latency_ms: float,
    db_path: Path = DB_DEFAULT,
):
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO predictions
           (timestamp, image_name, prompt_version, model_name,
            predicted_class, confidence, image_quality, latency_ms, json_valid, output_json)
           VALUES (datetime('now'), ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
        (
            image_name,
            prompt_version,
            model_name,
            result.get("predicted_class"),
            result.get("confidence"),
            result.get("image_quality"),
            latency_ms,
            json.dumps(result, ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()
