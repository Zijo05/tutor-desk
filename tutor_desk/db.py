import sqlite3

def get_connection(path="data/tutor_desk.db"):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

def init_db(connection):
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        name TEXT NOT NULL,
        level TEXT NOT NULL CHECK(level in ('primary school' ,'highschool', 'university')),
        school TEXT,
        contact TEXT,
        active BOOLEAN DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS sessions(
        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        student_id INTEGER NOT NULL REFERENCES students(id),
        date TEXT NOT NULL,
        duration_min INTEGER NOT NULL,
        subject TEXT NOT NULL,
        notes TEXT,
        paid BOOLEAN DEFAULT 0
    );

    CREATE INDEX IF NOT EXISTS idx_sessions_student ON sessions(student_id);

    CREATE TABLE IF NOT EXISTS topics(
        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        subject TEXT NOT NULL,
        name TEXT NOT NULL,
        UNIQUE(subject, name)
    );

    CREATE TABLE IF NOT EXISTS session_topics(
        session_id INTEGER NOT NULL REFERENCES sessions(id),
        topic_id INTEGER NOT NULL REFERENCES topics(id),
        PRIMARY KEY (session_id, topic_id)
    );

    CREATE TABLE IF NOT EXISTS questions(
        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        topic_id INTEGER NOT NULL REFERENCES topics(id),
        type TEXT NOT NULL,
        difficulty INTEGER NOT NULL CHECK(difficulty BETWEEN 1 AND 3),
        body_tex TEXT NOT NULL,
        solution_tex TEXT
    );

    CREATE TABLE IF NOT EXISTS tests(
        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
        student_id INTEGER NOT NULL REFERENCES students(id),
        created_at TEXT NOT NULL,
        file_path TEXT
    );

    CREATE TABLE IF NOT EXISTS test_questions(
        test_id INTEGER NOT NULL REFERENCES tests(id),
        question_id INTEGER NOT NULL REFERENCES questions(id),
        position INTEGER NOT NULL,
        PRIMARY KEY(test_id, question_id)
    );
    """)
    connection.commit()



if __name__ == "__main__":
    connection = get_connection()
    init_db(connection)
    init_db(connection)   # twice: must not crash
    print("init twice OK")

    try:
        connection.execute(
            "INSERT INTO students (name, level) VALUES (?, ?)", 
            ("Test", "primary school")
        )
        connection.execute(
            "INSERT INTO sessions (student_id, date, duration_min, subject) VALUES (?, ?, ?, ?)",
            (1, "2026-10-15", 60, "math"),
        )
        connection.commit()
    except Exception as e:
        print(type(e).__name__, e)