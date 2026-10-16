import typer
from os import environ
import datetime
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


def db_path():
    return environ.get("TUTOR_DESK_DB", "data/tutor_desk.db")


def open_db():
    connection = get_connection(db_path())
    init_db(connection)
    return connection


app = typer.Typer(help="Manage tutoring students, sessions and tests.")

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
        typer.secho(f"Error: {e}", fg="red", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Added {counts['students']} students and {counts['sessions']} sessions")

@app.command("list-students")
def list_students_command(all_: bool = typer.Option(False, "--all")):
    """Lists students"""
    connection = open_db()
    for student in list_students(connection, active_only=not all_):
        typer.echo(f"{student['id']}   {student['name']}   {student['level']}")

@app.command("add-student")
def add_student_command(
    name: str = typer.Argument(..., help="Student's name."),
    level: str = typer.Option(..., "--level", help="primary school, highschool or university."),
    school: str = typer.Option(None, "--school", help="School name."),
    contact: str = typer.Option(None, "--contact", help="Phone or email."),
):
    """Add a new student."""
    connection = open_db()
    student_id = add_student(connection, name, level, school, contact)
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
        typer.secho(f"Error: student {student_id} not found", fg="red", err=True)
        raise typer.Exit(code=1)
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
        typer.secho(f"Error: student {student_id} not found", fg="red", err=True)
        raise typer.Exit(code=1)

    # 3. Topic names -> ids
    names = [t.strip() for t in topics.split(",") if t.strip()]
    topic_ids = [add_topic(connection, subject, name) for name in names]

    # 4. Save
    session_id = log_session(
        connection, student_id, date, minutes, subject, topic_ids, notes
    )
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
    if get_student(connection, student_id) is None:
        typer.secho(f"Error: student {student_id} not found", fg="red", err=True)
        raise typer.Exit(code=1)

    rows = student_history(connection, student_id, since)
    if not rows:
        typer.echo(f"No sessions yet. Add one with: log-session {student_id}")
        return
    for row in rows:
        typer.echo(f"{row['date']} · {format_duration(row['duration_min'])} · {row['topics'] or '-'}")

@app.command("mark-paid")
def mark_paid_command(session_id: int = typer.Argument(..., help="ID of the student.")):
    """Mark session as paid"""
    connection = open_db()
    session = get_session(connection, session_id)
    if session is None:
        typer.secho(f"Error: session {session_id} not found", fg="red", err=True)
        raise typer.Exit(code=1)
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
        typer.secho(f"Error: student {student_id} not found", fg="red", err=True)
        raise typer.Exit(code=1)
    rows = unpaid_sessions(connection, student_id)
    if not rows:
        typer.echo("All sessions are paid")
        return
    for row in rows:
        curr_student = get_student(connection, row['student_id'])
        typer.echo(f"Session {row['id']} · {curr_student['name']} · {row['date']} · {format_duration(row['duration_min'])}")

@app.command("stats")
def stats_command():
    """Show time per student, top topics and sessions per month."""
    connection = open_db()

    typer.echo("Time per student:")
    for row in minutes_per_student(connection):
        typer.echo(f"  {row['name']:<20} {format_duration(row['duration'])}")

    typer.echo("\nTop topics:")
    for row in top_topics(connection):
        typer.echo(f"  {row['name']:<20} {row['session_count']}")

    typer.echo("\nSessions per month:")
    for row in sessions_per_month(connection):
        typer.echo(f"  {row['month']}  {row['session_count']}")


if __name__ == "__main__":
    app()
