from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus
import os
from models import Base
import logging

logger = logging.getLogger("app")

# Check if full database URL is provided (e.g., from Render, Heroku)
DATABASE_URL = os.environ.get("SQLALCHEMY_DATABASE_URL") or os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    # No full URL provided, construct from individual components
    DB_PASSWORD_RAW = os.environ.get("DB_PASSWORD")
    if not DB_PASSWORD_RAW:
        raise ValueError(
            "Either SQLALCHEMY_DATABASE_URL/DATABASE_URL or DB_PASSWORD must be set. "
            "Please configure database connection in your .env file. "
            "See .env.example for template."
        )

    # URL-encode the password to handle special characters
    password = quote_plus(DB_PASSWORD_RAW)

    # Get database configuration from environment variables
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", "5432")  # Standard PostgreSQL port
    DB_NAME = os.environ.get("DB_NAME", "app")
    DB_USER = os.environ.get("DB_USER", "postgres")

    # Construct the DATABASE_URL
    DATABASE_URL = f"postgresql://{DB_USER}:{password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

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