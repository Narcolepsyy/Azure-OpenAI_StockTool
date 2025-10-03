"""Database models for the application."""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from sqlalchemy.types import JSON as SAJSON
from datetime import datetime, timezone
from app.core.config import DATABASE_URL

# Database setup
_sqlite = DATABASE_URL.startswith("sqlite")
engine = create_engine(
    DATABASE_URL, 
    echo=False, 
    future=True, 
    connect_args={
        "check_same_thread": False,
        "timeout": 20  # 20 seconds timeout for busy database
    } if _sqlite else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()

class User(Base):
    """User model for authentication."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=False, nullable=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    logs = relationship("Log", back_populates="user", cascade="all, delete-orphan")

class Log(Base):
    """Log model for tracking user actions."""
    __tablename__ = "logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    action = Column(String(50), nullable=False)
    conversation_id = Column(String(64), nullable=True)
    prompt = Column(Text, nullable=True)
    response = Column(Text, nullable=True)
    tool_calls = Column(SAJSON, nullable=True)

    user = relationship("User", back_populates="logs")

class RefreshToken(Base):
    """Refresh token model for JWT authentication."""
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)

    user = relationship("User")

class PasswordReset(Base):
    """Password reset token model."""
    __tablename__ = "password_resets"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)

    user = relationship("User")

# Enable SQLite WAL mode for better concurrent access
if _sqlite:
    from sqlalchemy import event
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set SQLite pragmas for optimal performance and concurrency."""
        cursor = dbapi_connection.cursor()
        # Enable WAL mode for better concurrent reads
        cursor.execute("PRAGMA journal_mode=WAL")
        # Set synchronous mode to NORMAL for better performance
        cursor.execute("PRAGMA synchronous=NORMAL")
        # Increase cache size (negative value means KB)
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Create tables
Base.metadata.create_all(bind=engine)

# DB dependency
def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
