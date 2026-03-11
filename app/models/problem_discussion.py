"""
Problem discussion models for problem-specific discussions.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ProblemDiscussion(Base):
    """Discussion thread attached to a specific problem."""
    __tablename__ = "problem_discussions"

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)

    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    author = relationship("User", foreign_keys=[author_id])

    is_published = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    comments = relationship(
        "ProblemDiscussionComment",
        back_populates="discussion",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    __table_args__ = (
        Index("idx_problem_discussions_problem", "problem_id"),
    )

    def __repr__(self):
        return f"<ProblemDiscussion(id={self.id}, problem_id={self.problem_id}, title='{self.title[:30]}...')>"


class ProblemDiscussionComment(Base):
    """Comment in a problem discussion thread (supports nested replies)."""
    __tablename__ = "problem_discussion_comments"

    id = Column(Integer, primary_key=True, index=True)
    discussion_id = Column(Integer, ForeignKey("problem_discussions.id"), nullable=False)
    discussion = relationship("ProblemDiscussion", back_populates="comments")
    content = Column(Text, nullable=False)

    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    author = relationship("User", foreign_keys=[author_id])

    parent_id = Column(Integer, ForeignKey("problem_discussion_comments.id"), nullable=True)
    parent = relationship("ProblemDiscussionComment", remote_side=[id], back_populates="replies")
    replies = relationship(
        "ProblemDiscussionComment",
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    is_published = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_discussion_comments_discussion", "discussion_id"),
        Index("idx_discussion_comments_parent", "parent_id"),
        Index("idx_discussion_comments_author", "author_id"),
    )

    def __repr__(self):
        return f"<ProblemDiscussionComment(id={self.id}, discussion_id={self.discussion_id}, author_id={self.author_id}, parent_id={self.parent_id})>"
