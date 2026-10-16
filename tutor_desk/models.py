import sqlite3

def add_student(connection, name, level, school=None, contact=None):
    cursor = connection.execute(
        "INSERT INTO students(name, level, school, contact) VALUES(?, ?, ?, ?)", 
        (name, level, school, contact)
        )
    connection.commit()
    return cursor.lastrowid

def list_students(connection, active_only=True):
    query = "SELECT * FROM students "
    if active_only:
        query += "WHERE active = 1 "
    query += "ORDER BY name"
    return connection.execute(query).fetchall()

def get_student(connection, student_id):
    return connection.execute(
    "SELECT * FROM students WHERE id=?", 
    (student_id,)).fetchone()

def set_active(connection, student_id, active):
    cursor = connection.execute(
        "UPDATE students SET active = ? WHERE id = ?",
        (1 if active else 0, student_id)
    )
    connection.commit()
    return cursor.rowcount == 1

def add_topic(connection, subject, name):
    connection.execute(
        "INSERT OR IGNORE INTO topics(subject, name) VALUES(?, ?)",
        (subject, name)
    )
    row = connection.execute(
        "SELECT id FROM topics WHERE subject = ? AND name = ?",
        (subject, name)
    ).fetchone()

    connection.commit()
    return row["id"]

def log_session(connection, student_id, date, duration_min, subject, topic_ids, notes=None):
    try:
        session_id = connection.execute(
            "INSERT INTO sessions (student_id, date, duration_min, subject, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (student_id, date, duration_min, subject, notes),
        ).lastrowid

        for topic_id in topic_ids:
            connection.execute(
                "INSERT INTO session_topics (session_id, topic_id) VALUES (?, ?)",
                (session_id, topic_id),
            )
        connection.commit()
        return session_id
    except Exception:
        connection.rollback()
        raise

def student_history(connection, student_id, since=None):
    query = """
        SELECT sessions.date, sessions.duration_min, GROUP_CONCAT(topics.name, ', ') AS topics
        FROM sessions
        LEFT JOIN session_topics ON session_topics.session_id = sessions.id
        LEFT JOIN topics ON topics.id = session_topics.topic_id
        WHERE sessions.student_id = ?
    """
    parameters = [student_id]
    if since:
        query += " AND sessions.date >= ?"
        parameters.append(since)

    query += " GROUP BY sessions.id ORDER BY sessions.date DESC"
    return connection.execute(query, parameters).fetchall()

def mark_paid(connection, session_id):
    cursor = connection.execute("UPDATE sessions SET paid = 1 WHERE id = ?", (session_id, ))
    connection.commit()
    return cursor.rowcount == 1

def unpaid_sessions(connection, student_id = None):
    query = "SELECT * FROM sessions WHERE paid = 0"
    params = []
    if student_id:
        query += " AND student_id = ?"
        params.append(student_id)
    query += " ORDER BY date"
    return connection.execute(query, params).fetchall()

