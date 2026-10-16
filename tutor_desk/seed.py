# tutor_desk/seed.py
import datetime
import random

from tutor_desk.models import (
    add_student,
    add_topic,
    list_students,
    log_session,
    mark_paid,
    set_active,
)

# All fictional. (name, level, school, contact, active)
STUDENTS = [
    ("Amar Hodžić", "highschool", "Gimnazija Ilijaš", "061 111 222", True),
    ("Lejla Begović", "highschool", "Prva gimnazija", None, True),
    ("Dino Kovač", "highschool", "Gimnazija Ilijaš", "062 333 444", True),
    ("Ajla Mujić", "highschool", "Druga gimnazija", None, False),
    ("Tarik Šehić", "university", "PMF Sarajevo", "063 555 666", True),
    ("Emina Delić", "university", "ETF Sarajevo", None, True),
    ("Kenan Žilić", "university", "PMF Sarajevo", None, True),
    ("Selma Čaušević", "university", "Mašinski fakultet", None, False),
]

HIGHSCHOOL_TOPICS = ["equations", "inequalities", "functions", "logarithms", "trigonometry"]
UNIVERSITY_TOPICS = ["functions", "limits", "derivatives", "integrals"]


def seed_demo(connection, session_count=40, today=None):
    """Fill an empty database with fictional demo data. Returns the counts."""
    if list_students(connection, active_only=False):
        raise ValueError("Database already has students. Seed only runs on an empty database.")

    rng = random.Random(42)                 # same "random" data on every run
    today = today or datetime.date.today()

    # Topics: name -> id
    topic_ids = {}
    for name in HIGHSCHOOL_TOPICS + UNIVERSITY_TOPICS:
        topic_ids[name] = add_topic(connection, "math", name)

    # Students
    students = []
    for name, level, school, contact, active in STUDENTS:
        student_id = add_student(connection, name, level, school, contact)
        students.append((student_id, level, active))

    # Sessions over the last ~110 days
    for _ in range(session_count):
        student_id, level, active = rng.choice(students)

        # Inactive students only have older sessions: they stopped coming
        days_ago = rng.randint(70, 110) if not active else rng.randint(0, 110)
        date = (today - datetime.timedelta(days=days_ago)).isoformat()

        pool = HIGHSCHOOL_TOPICS if level == "highschool" else UNIVERSITY_TOPICS
        chosen = rng.sample(pool, rng.randint(1, 2))

        session_id = log_session(
            connection,
            student_id,
            date,
            rng.choice([60, 90]),
            "math",
            [topic_ids[name] for name in chosen],
        )

        # Most older sessions are paid, most recent ones are not
        chance_paid = 0.9 if days_ago > 21 else 0.3
        if rng.random() < chance_paid:
            mark_paid(connection, session_id)

    # Deactivate at the end, after their sessions exist
    for student_id, level, active in students:
        if not active:
            set_active(connection, student_id, False)

    return {"students": len(students), "sessions": session_count}