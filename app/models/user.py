from sqlalchemy import Column, Integer, String, Enum, DateTime, Boolean, ForeignKey, Text, Table
from sqlalchemy.orm import relationship
import enum
from sqlalchemy.sql import func
from app.database import Base

user_follows = Table(
    "user_follows",
    Base.metadata,
    Column("follower_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("followed_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now())
)

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CREATOR = "creator"
    USER = "user"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)
    update_time = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to education entries
    educations = relationship("Education", back_populates="user", cascade="all, delete-orphan")

    # Following relationships
    following = relationship(
        "User",
        secondary=user_follows,
        primaryjoin=id == user_follows.c.follower_id,
        secondaryjoin=id == user_follows.c.followed_id,
        backref="followers"
    )

class Education(Base):
    __tablename__ = "educations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    institution = Column(String, nullable=False)
    degree = Column(String, nullable=False)
    field_of_study = Column(String, nullable=True)
    start_year = Column(Integer, nullable=False)
    end_year = Column(Integer, nullable=True)  # Null means currently studying
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="educations")
