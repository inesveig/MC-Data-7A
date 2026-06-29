import sqlite3
from datetime import datetime

DB_PATH = "diagnostics.db"


_MIGRATIONS = [
    ("analysis_name", "TEXT"),
    ("heatmap_path", "TEXT"),
    ("doctor_diagnosis", "TEXT"),
    ("doctor_notes", "TEXT"),
    ("doctor_recorded_at", "TEXT"),
]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
                CREATE TABLE IF NOT EXISTS diagnostics (
                                                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                           filename TEXT NOT NULL,
                                                           image_path TEXT NOT NULL,
                                                           diagnosis TEXT NOT NULL,
                                                           confidence REAL,
                                                           created_at TEXT NOT NULL
                )
                """)
    conn.commit()

    # Migration automatique : ajoute les colonnes manquantes une par une.
    for col_name, col_type in _MIGRATIONS:
        try:
            cur.execute(f"ALTER TABLE diagnostics ADD COLUMN {col_name} {col_type}")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # la colonne existe déjà, rien à faire

    conn.close()


def save_diagnostic(filename, image_path, diagnosis, confidence, analysis_name="", heatmap_path=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO diagnostics
           (filename, image_path, diagnosis, confidence, created_at, analysis_name, heatmap_path)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (filename, image_path, diagnosis, confidence, datetime.now().isoformat(), analysis_name, heatmap_path),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_all_diagnostics():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM diagnostics ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return rows


def update_doctor_diagnosis(diag_id, doctor_diagnosis, doctor_notes=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """UPDATE diagnostics
           SET doctor_diagnosis = ?, doctor_notes = ?, doctor_recorded_at = ?
           WHERE id = ?""",
        (doctor_diagnosis, doctor_notes, datetime.now().isoformat(), diag_id),
    )
    conn.commit()
    conn.close()


def delete_diagnostic(diag_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM diagnostics WHERE id = ?", (diag_id,))
    conn.commit()
    conn.close()


def get_stats():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS n FROM diagnostics")
    total = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) AS n FROM diagnostics WHERE diagnosis = 'Sain'")
    sain = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) AS n FROM diagnostics WHERE diagnosis = 'Malade'")
    malade = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) AS n FROM diagnostics WHERE diagnosis = 'Incertain'")
    incertain = cur.fetchone()["n"]

    cur.execute(
        "SELECT COUNT(*) AS n FROM diagnostics WHERE doctor_diagnosis IS NOT NULL AND doctor_diagnosis != ''"
    )
    avec_avis = cur.fetchone()["n"]

    conn.close()
    return {
        "total": total,
        "sain": sain,
        "malade": malade,
        "incertain": incertain,
        "avec_avis_medecin": avec_avis,
    }