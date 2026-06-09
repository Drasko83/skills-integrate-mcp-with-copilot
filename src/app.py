"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import closing
from pathlib import Path
import sqlite3

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

BASE_DIR = Path(__file__).parent
DB_DIR = BASE_DIR / "data"
DB_PATH = DB_DIR / "activities.db"
MIGRATIONS_DIR = BASE_DIR / "migrations"

# Mount the static files directory
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

DEFAULT_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def apply_migrations(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            name TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    for migration_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        migration_name = migration_file.name
        already_applied = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE name = ?",
            (migration_name,)
        ).fetchone()

        if already_applied:
            continue

        conn.executescript(migration_file.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO schema_migrations (name) VALUES (?)",
            (migration_name,)
        )

    conn.commit()


def seed_default_data(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT COUNT(*) AS total FROM activities").fetchone()
    if row and row["total"] > 0:
        return

    for activity_name, details in DEFAULT_ACTIVITIES.items():
        conn.execute(
            """
            INSERT INTO activities (name, description, schedule, max_participants)
            VALUES (?, ?, ?, ?)
            """,
            (
                activity_name,
                details["description"],
                details["schedule"],
                details["max_participants"],
            ),
        )

        for email in details["participants"]:
            conn.execute(
                """
                INSERT INTO enrollments (activity_name, email)
                VALUES (?, ?)
                """,
                (activity_name, email),
            )

    conn.commit()


def initialize_database() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)

    with closing(get_connection()) as conn:
        apply_migrations(conn)
        seed_default_data(conn)


def get_activities_payload() -> dict:
    with closing(get_connection()) as conn:
        activity_rows = conn.execute(
            """
            SELECT name, description, schedule, max_participants
            FROM activities
            ORDER BY name
            """
        ).fetchall()

        enrollment_rows = conn.execute(
            """
            SELECT activity_name, email
            FROM enrollments
            ORDER BY activity_name, email
            """
        ).fetchall()

    activities = {
        row["name"]: {
            "description": row["description"],
            "schedule": row["schedule"],
            "max_participants": row["max_participants"],
            "participants": [],
        }
        for row in activity_rows
    }

    for enrollment in enrollment_rows:
        activity_name = enrollment["activity_name"]
        if activity_name in activities:
            activities[activity_name]["participants"].append(enrollment["email"])

    return activities


@app.on_event("startup")
def startup_event() -> None:
    initialize_database()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return get_activities_payload()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    with closing(get_connection()) as conn:
        activity_exists = conn.execute(
            "SELECT 1 FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()

        if not activity_exists:
            raise HTTPException(status_code=404, detail="Activity not found")

        already_signed_up = conn.execute(
            "SELECT 1 FROM enrollments WHERE activity_name = ? AND email = ?",
            (activity_name, email),
        ).fetchone()

        if already_signed_up:
            raise HTTPException(
                status_code=400,
                detail="Student is already signed up"
            )

        conn.execute(
            "INSERT INTO enrollments (activity_name, email) VALUES (?, ?)",
            (activity_name, email),
        )
        conn.commit()

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    with closing(get_connection()) as conn:
        activity_exists = conn.execute(
            "SELECT 1 FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()

        if not activity_exists:
            raise HTTPException(status_code=404, detail="Activity not found")

        delete_result = conn.execute(
            "DELETE FROM enrollments WHERE activity_name = ? AND email = ?",
            (activity_name, email),
        )

        if delete_result.rowcount == 0:
            raise HTTPException(
                status_code=400,
                detail="Student is not signed up for this activity"
            )

        conn.commit()

    return {"message": f"Unregistered {email} from {activity_name}"}
