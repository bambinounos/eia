import sys
import os

# Add the project root to the Python path to allow for absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eia.database.session import engine
from eia.database.models import Base
from eia.config import settings

def initialize_database():
    """
    Connects to the database specified in the config and creates all tables.
    """
    if not settings:
        print("Error: Could not load configuration. Aborting database initialization.")
        return

    print(f"Connecting to database: {settings.database.url}")

    try:
        # The 'connect' method will test the connection without needing a full session.
        with engine.connect() as connection:
            print("Database connection successful.")

        print("Creating all tables based on models...")
        # This command creates all tables that inherit from Base
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully!")
        print("\nYour database is now ready.")

    except Exception as e:
        print("\n--- An Error Occurred ---")
        print(f"Failed to initialize the database: {e}")
        print("\nPlease check the following:")
        print("1. Your PostgreSQL server is running.")
        print("2. The database URL in your 'config.yml' is correct (user, password, host, db name).")
        print("3. The specified database exists and the user has permission to connect and create tables.")
        print("   (You may need to create the database manually, e.g., `CREATE DATABASE eia_db;`)")


if __name__ == "__main__":
    # This confirmation step is a simple safeguard.
    confirm = input("This will create new tables in the database. Are you sure? (y/n): ")
    if confirm.lower() == 'y':
        initialize_database()
    else:
        print("Database initialization cancelled.")