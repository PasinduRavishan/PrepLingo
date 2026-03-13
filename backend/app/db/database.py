"""
database.py — Database Connection & Session Management

KEY CONCEPTS:

  ENGINE:
    The SQLAlchemy engine is the connection to the database.
    Think of it as the "wire" between Python and SQLite.
    We create ONE engine for the whole app (expensive to create, cheap to reuse).

  SESSION:
    A database session tracks all the changes you make (inserts, updates)
    and commits them together at the end. Like a transaction.
    Each API request gets its OWN session (via get_db dependency below).

  WHY get_db() is a Generator (uses yield):
    FastAPI's dependency injection uses Python generators for setup/teardown.
    - Code BEFORE yield: setup (open session)
    - yield: hand the session to the endpoint
    - Code AFTER yield: teardown (close session, even if there was an error)
    This guarantees the DB session is ALWAYS closed, preventing memory/connection leaks.
"""

from sqlmodel import SQLModel, create_engine, Session
from app.config import get_settings

settings = get_settings()

# echo=True logs every SQL query to the console — great for learning/debugging
# Set to False in production
engine = create_engine(
    settings.database_url,
    echo=settings.app_env == "development",
    connect_args={"check_same_thread": False}  # Required for SQLite with FastAPI
)


def create_tables():
    """
    Creates all database tables based on SQLModel model classes.
    
    SQLModel.metadata contains all table definitions from every model
    that has been imported. This is why models/__init__.py imports all
    models — they must be imported BEFORE this function runs.
    
    Called once at app startup (see main.py lifespan).
    """
    # Import all models so SQLModel knows about them before creating tables
    import app.models  # noqa — triggers all model imports via models/__init__.py
    SQLModel.metadata.create_all(engine)


def get_db():
    """
    FastAPI Dependency — provides a database session per request.
    
    Usage in a route:
        @router.get("/example")
        def my_route(db: Session = Depends(get_db)):
            results = db.exec(select(MyModel)).all()
    
    The `with` block auto-closes the session when the request ends.
    """
    with Session(engine) as session:
        yield session
