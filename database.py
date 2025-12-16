from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus
import os
from models import Base
import logging

logger = logging.getLogger("app")
password = os.getenv("PASSWORD")
# URL-encode the password
password = quote_plus(os.environ.get("DB_PASSWORD", "Qir@t_S2eed123"))

# Get database host and port from environment variables, with defaults
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5433") # Default to 5433

# Construct the default DATABASE_URL using environment variables
DEFAULT_DATABASE_URL = f"postgresql://postgres:{password}@{DB_HOST}:{DB_PORT}/app"

DATABASE_URL = os.environ.get(
    "SQLALCHEMY_DATABASE_URL", 
    DEFAULT_DATABASE_URL
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Dependency to get a DB session for each request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """
    Create all tables defined by models that inherit from Base.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created or already exist.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise