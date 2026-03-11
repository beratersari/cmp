"""
Bookmark model for user saved problems.
"""
from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Bookmark(Base):
    """Bookmark model to save problems for a user."""
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)

    user = relationship("User", foreign_keys=[user_id])
    problem = relationship("Problem", foreign_keys=[problem_id])

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "problem_id", name="unique_user_problem_bookmark"),
        Index("idx_bookmarks_user", "user_id"),
        Index("idx_bookmarks_problem", "problem_id"),
    )

    def __repr__(self):
        return f"<Bookmark(id={self.id}, user_id={self.user_id}, problem_id={self.problem_id})>"
