"""
Emoji reaction model for the forum.
Users can react to posts and comments with emojis like :happy:, :angry:, :sad:
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class EmojiReaction(Base):
    """Emoji reaction model for posts and comments."""
    __tablename__ = "emoji_reactions"

    id = Column(Integer, primary_key=True, index=True)
    
    # User who reacted
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", foreign_keys=[user_id])
    
    # Target type: 'post' or 'comment'
    target_type = Column(String(20), nullable=False)
    
    # Target ID (post_id or comment_id based on target_type)
    target_id = Column(Integer, nullable=False)
    
    # Emoji in string format like :happy:, :angry:, :sad:
    emoji = Column(String(50), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Unique constraint: one reaction per user per target
    __table_args__ = (
        UniqueConstraint('user_id', 'target_type', 'target_id', name='unique_user_target_reaction'),
        Index('idx_emoji_target', 'target_type', 'target_id'),
        Index('idx_emoji_user', 'user_id'),
    )
    
    def __repr__(self):
        return f"<EmojiReaction(id={self.id}, user_id={self.user_id}, target={self.target_type}:{self.target_id}, emoji='{self.emoji}')>"
