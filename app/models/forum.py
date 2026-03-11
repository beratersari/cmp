"""
Forum models for the application.
Supports posts and nested comments (tree structure).
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ForumPost(Base):
    """Forum post model - top level posts in the forum."""
    __tablename__ = "forum_posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    
    # Author relationship
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    author = relationship("User", foreign_keys=[author_id])
    
    # Publishing status - only published posts are visible to regular users
    is_published = Column(Boolean, default=True, nullable=False)
    
    # Soft delete - deleted posts are hidden but kept in database
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    comments = relationship(
        "ForumComment",
        back_populates="post",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    @property
    def comment_count(self):
        """Get total number of non-deleted comments."""
        return self.comments.filter_by(is_deleted=False).count()
    
    def __repr__(self):
        return f"<ForumPost(id={self.id}, title='{self.title[:30]}...', author_id={self.author_id})>"


class ForumComment(Base):
    """Forum comment model - supports nested replies (tree structure)."""
    __tablename__ = "forum_comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    
    # Author relationship
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    author = relationship("User", foreign_keys=[author_id])
    
    # Post relationship (top-level parent)
    post_id = Column(Integer, ForeignKey("forum_posts.id"), nullable=False)
    post = relationship("ForumPost", foreign_keys=[post_id], back_populates="comments")
    
    # Self-referential relationship for nested replies
    # Null parent_id means this is a top-level comment on the post
    parent_id = Column(Integer, ForeignKey("forum_comments.id"), nullable=True)
    
    # Replies to this comment
    replies = relationship(
        "ForumComment",
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    # Parent comment (the comment this is replying to)
    parent = relationship(
        "ForumComment",
        remote_side=[id],
        back_populates="replies"
    )
    
    # Publishing status
    is_published = Column(Boolean, default=True, nullable=False)
    
    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_comment_post_id', 'post_id'),
        Index('idx_comment_parent_id', 'parent_id'),
        Index('idx_comment_author_id', 'author_id'),
    )
    
    @property
    def reply_count(self):
        """Get total number of non-deleted replies."""
        return self.replies.filter_by(is_deleted=False).count()
    
    @property
    def depth(self):
        """Calculate the depth of this comment in the tree."""
        depth = 0
        current = self
        while current.parent_id is not None:
            depth += 1
            current = current.parent
        return depth
    
    def __repr__(self):
        return f"<ForumComment(id={self.id}, post_id={self.post_id}, author_id={self.author_id}, parent_id={self.parent_id})>"
