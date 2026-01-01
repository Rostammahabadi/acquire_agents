from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
import os

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://acquire_user:acquire_pass@localhost:5432/acquire_agents"
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
    pool_pre_ping=True,
)

def create_db_and_tables():
    """Create all tables defined in SQLModel models"""
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    with Session(engine) as session:
        yield session

def get_session_sync() -> Session:
    """Get synchronous database session"""
    return Session(engine)
