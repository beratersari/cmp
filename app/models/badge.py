import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class BadgeCriteriaType(str, enum.Enum):
    """Types of badge criteria."""
    PROBLEMS_SOLVED = "problems_solved"  # Total problems solved
    CONTESTS_PARTICIPATED = "contests_participated"  # Number of contests joined
    STREAK_DAYS = "streak_days"  # Current/max streak
    SUBMISSIONS_MADE = "submissions_made"  # Total submissions
    PERFECT_SOLVES = "perfect_solves"  # Solved on first try
    CONTESTS_WON = "contests_won"  # Won contests (rank 1)
    PROBLEMS_CREATED = "problems_created"  # For creators
    FORUM_POSTS = "forum_posts"  # Active forum participant
    ACCOUNT_AGE = "account_age"  # Days since registration


class Badge(Base):
    """Badge model for achievements."""
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=False)
    icon = Column(String(255), nullable=True)  # URL or emoji/icon name
    criteria_type = Column(String(50), nullable=False)  # BadgeCriteriaType value
    criteria_value = Column(Integer, nullable=False)  # Target value to achieve
    criteria_data = Column(JSON, nullable=True)  # Additional criteria config
    is_active = Column(String, default="active", nullable=False)  # active, inactive
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    user_badges = relationship("UserBadge", back_populates="badge", cascade="all, delete-orphan")

    @property
    def is_active_badge(self) -> bool:
        return self.is_active == "active"

    def __repr__(self):
        return f"<Badge(id={self.id}, name='{self.name}', criteria={self.criteria_type})>"


class UserBadge(Base):
    """User-Badge association with progress tracking."""
    __tablename__ = "user_badges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    badge_id = Column(Integer, ForeignKey("badges.id", ondelete="CASCADE"), nullable=False)
    progress = Column(Integer, default=0, nullable=False)  # Current progress toward criteria
    earned_at = Column(DateTime(timezone=True), nullable=True)  # Null if not yet earned
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="badges")
    badge = relationship("Badge", back_populates="user_badges")

    @property
    def is_earned(self) -> bool:
        return self.earned_at is not None

    @property
    def progress_percentage(self) -> int:
        """Calculate progress percentage."""
        if not self.badge:
            return 0
        if self.badge.criteria_value <= 0:
            return 100 if self.is_earned else 0
        pct = min(100, int((self.progress / self.badge.criteria_value) * 100))
        return pct

    def __repr__(self):
        return f"<UserBadge(user_id={self.user_id}, badge_id={self.badge_id}, earned={self.is_earned})>"
