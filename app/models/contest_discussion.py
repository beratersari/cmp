"""
Contest discussion models for contest-specific discussions.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ContestDiscussion(Base):
    """Discussion thread attached to a specific contest."""
    __tablename__ = "contest_discussions"

    id = Column(Integer, primary_key=True, index=True)
    contest_id = Column(Integer, ForeignKey("contests.id"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)

    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    author = relationship("User", foreign_keys=[author_id])

    is_published = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    comments = relationship(
        "ContestDiscussionComment",
        back_populates="discussion",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    __table_args__ = (
        Index("idx_contest_discussions_contest", "contest_id"),
    )

    def __repr__(self):
        return f"<ContestDiscussion(id={self.id}, contest_id={self.contest_id}, title='{self.title[:30]}...')>"


class ContestDiscussionComment(Base):
    """Comment in a contest discussion thread (supports nested replies)."""
    __tablename__ = "contest_discussion_comments"

    id = Column(Integer, primary_key=True, index=True)
    discussion_id = Column(Integer, ForeignKey("contest_discussions.id"), nullable=False)
    discussion = relationship("ContestDiscussion", back_populates="comments")
    content = Column(Text, nullable=False)

    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    author = relationship("User", foreign_keys=[author_id])

    parent_id = Column(Integer, ForeignKey("contest_discussion_comments.id"), nullable=True)
    parent = relationship("ContestDiscussionComment", remote_side=[id], back_populates="replies")
    replies = relationship(
        "ContestDiscussionComment",
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    is_published = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_contest_discussion_comments_discussion", "discussion_id"),
        Index("idx_contest_discussion_comments_parent", "parent_id"),
        Index("idx_contest_discussion_comments_author", "author_id"),
    )

    def __repr__(self):
        return f"<ContestDiscussionComment(id={self.id}, discussion_id={self.discussion_id}, author_id={self.author_id}, parent_id={self.parent_id})>"
