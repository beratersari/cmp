from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./codeforces_clone.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

PROBLEM_TABLE_NAME = "problems"
USER_TABLE_NAME = "users"
SUBMISSION_TABLE_NAME = "submissions"
TAG_TABLE_NAME = "tags"
PROBLEM_TAG_TABLE_NAME = "problem_tags"
EDITORIAL_TABLE_NAME = "editorials"
USER_FOLLOWS_TABLE_NAME = "user_follows"


def add_column_if_missing(connection, table_name: str, column_name: str, column_sql: str):
    columns = connection.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    existing_columns = {column[1] for column in columns}
    if column_name not in existing_columns:
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}"))


def run_sqlite_migrations(engine_override=None):
    """
    Lightweight migration helper for SQLite to add new columns and tables.
    """
    migration_engine = engine_override or engine
    with migration_engine.connect() as connection:
        # Problem table columns
        add_column_if_missing(connection, PROBLEM_TABLE_NAME, "is_published", "BOOLEAN NOT NULL DEFAULT 0")
        add_column_if_missing(connection, PROBLEM_TABLE_NAME, "is_public", "BOOLEAN NOT NULL DEFAULT 1")
        add_column_if_missing(connection, PROBLEM_TABLE_NAME, "owner_id", "INTEGER NOT NULL DEFAULT 1")
        add_column_if_missing(connection, PROBLEM_TABLE_NAME, "created_by", "TEXT")
        add_column_if_missing(connection, PROBLEM_TABLE_NAME, "updated_by", "TEXT")
        add_column_if_missing(connection, PROBLEM_TABLE_NAME, "update_time", "DATETIME")
        add_column_if_missing(connection, PROBLEM_TABLE_NAME, "difficulty", "INTEGER NOT NULL DEFAULT 5")

        # User table columns
        add_column_if_missing(connection, USER_TABLE_NAME, "is_active", "BOOLEAN NOT NULL DEFAULT 1")
        add_column_if_missing(connection, USER_TABLE_NAME, "created_by", "TEXT")
        add_column_if_missing(connection, USER_TABLE_NAME, "updated_by", "TEXT")
        add_column_if_missing(connection, USER_TABLE_NAME, "update_time", "DATETIME")

        # Submission table columns
        add_column_if_missing(connection, SUBMISSION_TABLE_NAME, "status", "TEXT NOT NULL DEFAULT 'PENDING'")
        add_column_if_missing(connection, SUBMISSION_TABLE_NAME, "created_by", "TEXT")
        add_column_if_missing(connection, SUBMISSION_TABLE_NAME, "updated_by", "TEXT")
        add_column_if_missing(connection, SUBMISSION_TABLE_NAME, "update_time", "DATETIME")

        # Create allowed users join table if missing
        connection.execute(text(
            """
            CREATE TABLE IF NOT EXISTS problem_allowed_users (
                problem_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (problem_id, user_id),
                FOREIGN KEY(problem_id) REFERENCES problems(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        ))

        # Create tags table if missing
        connection.execute(text(
            """
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                created_by TEXT,
                updated_by TEXT,
                update_time DATETIME
            )
            """
        ))

        # Create problem tags join table if missing
        connection.execute(text(
            """
            CREATE TABLE IF NOT EXISTS problem_tags (
                problem_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (problem_id, tag_id),
                FOREIGN KEY(problem_id) REFERENCES problems(id),
                FOREIGN KEY(tag_id) REFERENCES tags(id)
            )
            """
        ))

        # Create editorials table if missing
        connection.execute(text(
            """
            CREATE TABLE IF NOT EXISTS editorials (
                id INTEGER PRIMARY KEY,
                problem_id INTEGER NOT NULL UNIQUE,
                description TEXT NOT NULL,
                code_solution TEXT NOT NULL,
                created_by TEXT,
                updated_by TEXT,
                update_time DATETIME,
                FOREIGN KEY(problem_id) REFERENCES problems(id)
            )
            """
        ))

        # Create educations table if missing
        connection.execute(text(
            """
            CREATE TABLE IF NOT EXISTS educations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                institution TEXT NOT NULL,
                degree TEXT NOT NULL,
                field_of_study TEXT,
                start_year INTEGER NOT NULL,
                end_year INTEGER,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        ))

        # Create user follows table if missing
        connection.execute(text(
            """
            CREATE TABLE IF NOT EXISTS user_follows (
                follower_id INTEGER NOT NULL,
                followed_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (follower_id, followed_id),
                FOREIGN KEY(follower_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(followed_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        ))

        connection.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
