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

