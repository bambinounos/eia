from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ..config import settings

# Check if settings were loaded correctly
if not settings or not settings.database.url:
    raise ValueError("Database URL is not configured. Please check your config.yml.")

# Create the SQLAlchemy engine
# The pool_pre_ping argument helps with connection stability, especially for long-running applications.
engine = create_engine(
    settings.database.url,
    pool_pre_ping=True
)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Dependency for FastAPI to get a DB session.
    Ensures the database session is always closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Example of how to use the session, for testing purposes
if __name__ == '__main__':
    print("Attempting to connect to the database and create a session...")

    try:
        # The 'get_db' function is a generator, so we need to iterate it
        db_generator = get_db()
        db_session = next(db_generator)

        print("Session created successfully.")

        # Perform a simple query to test the connection
        result = db_session.execute("SELECT 1")
        print(f"Test query result: {result.scalar()}")

        print("Database connection is working.")

    except Exception as e:
        print(f"An error occurred while connecting to the database: {e}")
        print("Please ensure your database is running and the URL in config.yml is correct.")

    finally:
        # Manually close the session when testing this way
        if 'db_session' in locals():
            db_session.close()
            print("Session closed.")