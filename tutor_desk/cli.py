import sqlite3
import typer
from rich.table import Table
from rich.console import Console
from os import environ
import datetime
from pathlib import Path
from tutor_desk.models import (
    add_student,
    add_topic,
    list_students,
    log_session,
    mark_paid,
    set_active,
    get_student,
    student_history,
    format_duration,
    unpaid_sessions,
    get_session,
    minutes_per_student, 
    top_topics, 
    sessions_per_month,
)
from tutor_desk.db import (
    init_db,
    get_connection
)
from tutor_desk.seed import seed_demo


# data/tutor_desk.db inside the project folder, no matter where the command is run from
DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "tutor_desk.db"


def db_path():
    return environ.get("TUTOR_DESK_DB", str(DEFAULT_DB))


def fail(message):
    typer.secho(f"Error: {message}", fg="red", err=True)
    raise typer.Exit(code=1)


def open_db():
    try:
        connection = get_connection(db_path())
        init_db(connection)
    except sqlite3.OperationalError as e:
        fail(f"cannot open database at {db_path()} ({e})")
    return connection

app = typer.Typer(help="Manage tutoring students, sessions and tests.")
console = Console()

@app.command("init")
def init_command():
    """Create the database."""
    open_db()
    typer.echo(f"Database ready at {db_path()}")


@app.command("seed-demo")
def seed_demo_command():
    """Fill the database with fictional demo data."""
    connection = open_db()
    try:
        counts = seed_demo(connection)
    except ValueError as e:
        fail(e)
    except sqlite3.IntegrityError as e:
        fail(f"could not save the demo data ({e})")
    typer.echo(f"Added {counts['students']} students and {counts['sessions']} sessions")

@app.command("list-students")
def list_students_command(all_: bool = typer.Option(False, "--all")):
    """Lists students"""
    connection = open_db()

    students = list_students(connection, active_only=not all_)
    if not students:
        typer.echo("No students yet. Add one with: add-student <name> --level <level>")
        return

    table = Table(title="Students")
    table.add_column("ID", justify="right")
    table.add_column("Name")
    table.add_column("Level")
    table.add_column("School")
    table.add_column("Active")

    for student in students:
        table.add_row(
            str(student["id"]),
            student["name"],
            student["level"],
            student["school"] or "-",
            "Yes" if student["active"] else "No",
        )
    console.print(table)

@app.command("add-student")
def add_student_command(
    name: str = typer.Argument(..., help="Student's name."),
    level: str = typer.Option(..., "--level", help="primary school, highschool or university."),
    school: str = typer.Option(None, "--school", help="School name."),
    contact: str = typer.Option(None, "--contact", help="Phone or email."),
):
    """Add a new student."""
    connection = open_db()
    try:
        student_id = add_student(connection, name, level, school, contact)
    except sqlite3.IntegrityError:
        fail(f"invalid level '{level}'. Use primary school, highschool or university")
    typer.echo(f"Added {name} with id {student_id}")

@app.command("deactivate")
def deactivate_command(
    student_id: int = typer.Argument(..., help="Student's ID."),
    yes: bool = typer.Option(False, "--yes", help="Skip the confirmation."),
):
    """Deactivate a student."""
    connection = open_db()
    student = get_student(connection, student_id)
    if student is None:
        fail(f"student {student_id} not found")
    if not student["active"]:
        typer.echo(f"{student['name']} is already inactive")
        return
    if not yes and not typer.confirm(f"Deactivate {student['name']}?"):
        typer.echo("Cancelled")
        return
    set_active(connection, student_id, False)
    typer.echo(f"Deactivated {student['name']}")


@app.command("log-session")
def log_session_command(
    student_id: int = typer.Argument(..., help="ID of the student."),
    minutes: int = typer.Option(60, help="Length of the session in minutes."),
    subject: str = typer.Option("math", help="Subject of the session."),
    topics: str = typer.Option("", help="Comma-separated topics, e.g. derivatives,limits."),
    date: str = typer.Option(None, help="Date as YYYY-MM-DD. Defaults to today."),
    notes: str = typer.Option(None, help="Optional notes."),
):
    """Log a tutoring session."""
    # 1. Date: default to today, validate otherwise
    if date is None:
        date = datetime.date.today().isoformat()
    else:
        try:
            datetime.date.fromisoformat(date)
        except ValueError:
            raise typer.BadParameter("Use YYYY-MM-DD", param_hint="--date")

    connection = open_db()

    # 2. Student must exist
    if get_student(connection, student_id) is None:
        fail(f"student {student_id} not found")

    # 3. Topic names -> ids
    names = [t.strip() for t in topics.split(",") if t.strip()]

    # 4. Save
    try:
        topic_ids = [add_topic(connection, subject, name) for name in names]
        session_id = log_session(
            connection, student_id, date, minutes, subject, topic_ids, notes
        )
    except sqlite3.IntegrityError as e:
        if "session_topics" in str(e):
            fail("each topic can only be listed once per session")
        fail(f"could not save the session ({e})")
    typer.echo(f"Logged session {session_id} on {date} ({minutes} min)")

@app.command("history")
def student_history_command(
    student_id: int = typer.Argument(..., help="ID of the student."),
    since: str = typer.Option(None, help="Only sessions from this date (YYYY-MM-DD)."),
):
    """Show a student's session history."""
    if since is not None:
        try:
            datetime.date.fromisoformat(since)
        except ValueError:
            raise typer.BadParameter("Use YYYY-MM-DD", param_hint="--since")

    connection = open_db()
    student = get_student(connection, student_id)
    if student is None:
        fail(f"student {student_id} not found")

    rows = student_history(connection, student_id, since)
    if not rows:
        typer.echo(f"No sessions yet. Add one with: log-session {student_id}")
        return
    table = Table(title=f"History for {student['name']}")
    table.add_column("Date")
    table.add_column("Duration", justify="right")
    table.add_column("Topics")

    for row in rows:
        table.add_row(
            row["date"],
            format_duration(row["duration_min"]),
            row["topics"] or "-",
        )
    console.print(table)

@app.command("mark-paid")
def mark_paid_command(session_id: int = typer.Argument(..., help="ID of the session.")):
    """Mark session as paid"""
    connection = open_db()
    session = get_session(connection, session_id)
    if session is None:
        fail(f"session {session_id} not found")
    if session['paid']:
        typer.echo(f"Session {session_id} is already paid")
        return
    mark_paid(connection, session_id)
    typer.echo(f"Session {session_id} marked as paid")

@app.command("unpaid-sessions")
def unpaid_sessions_command(student_id: int = typer.Option(None, "--student", help="ID of the student")):
    """List unpaid sessions"""
    connection = open_db()
    if student_id and not get_student(connection, student_id):
        fail(f"student {student_id} not found")

    rows = unpaid_sessions(connection, student_id)
    if not rows:
        typer.echo("All sessions are paid")
        return
    table = Table(title="Unpaid sessions")
    table.add_column("Session", justify="right")
    table.add_column("Student")
    table.add_column("Date")
    table.add_column("Duration", justify="right")

    for row in rows:
        curr_student = get_student(connection, row["student_id"])
        table.add_row(
            str(row["id"]),
            curr_student["name"],
            row["date"],
            format_duration(row["duration_min"]),
        )
    console.print(table)

@app.command("stats")
def stats_command():
    """Show time per student, top topics and sessions per month."""
    connection = open_db()

    students = minutes_per_student(connection)
    if not students:
        typer.echo("No students yet. Add one with: add-student <name> --level <level>")
    else:
        time_table = Table(title="Time per student")
        time_table.add_column("Student")
        time_table.add_column("Time", justify="right")
        for row in students:
            time_table.add_row(row["name"], format_duration(row["duration"]))
        console.print(time_table)

    topics = top_topics(connection)
    if not topics:
        typer.secho("No topics yet. Topics are added when logging a session")
    else:
        topic_table = Table(title="Top topics")
        topic_table.add_column("Topic")
        topic_table.add_column("Sessions", justify="right")
        for row in topics:
            topic_table.add_row(row["name"], str(row["session_count"]))
        console.print(topic_table)

    months = sessions_per_month(connection)
    if not months:
        typer.echo("No sessions yet. Add one with: log-session <student_id>")
        return
    month_table = Table(title="Sessions per month")
    month_table.add_column("Month")
    month_table.add_column("Sessions", justify="right")
    for row in months:
        month_table.add_row(row["month"], str(row["session_count"]))
    console.print(month_table)

if __name__ == "__main__":
    app()
