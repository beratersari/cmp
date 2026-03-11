"""
Emoji reaction repository for database operations.
"""
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.emoji_reaction import EmojiReaction
from app.core.config import get_logger

logger = get_logger(__name__)


class EmojiReactionRepository:
    def __init__(self, db: Session):
        self.db = db
        logger.debug("EmojiReactionRepository initialized")

    def create_reaction(self, user_id: int, target_type: str, target_id: int, emoji: str) -> EmojiReaction:
        """Create a new emoji reaction."""
        logger.debug(f"Creating reaction: user_id={user_id}, target={target_type}:{target_id}, emoji={emoji}")
        reaction = EmojiReaction(
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
            emoji=emoji
        )
        self.db.add(reaction)
        self.db.commit()
        self.db.refresh(reaction)
        logger.debug(f"Reaction created: id={reaction.id}")
        return reaction

    def get_reaction_by_user_and_target(self, user_id: int, target_type: str, target_id: int) -> Optional[EmojiReaction]:
        """Get a user's reaction for a specific target."""
        return self.db.query(EmojiReaction).filter(
            EmojiReaction.user_id == user_id,
            EmojiReaction.target_type == target_type,
            EmojiReaction.target_id == target_id
        ).first()

    def get_reactions_by_target(self, target_type: str, target_id: int) -> List[EmojiReaction]:
        """Get all reactions for a specific target."""
        return self.db.query(EmojiReaction).filter(
            EmojiReaction.target_type == target_type,
            EmojiReaction.target_id == target_id
        ).all()

    def get_reaction_counts_by_target(self, target_type: str, target_id: int) -> Dict[str, int]:
        """Get reaction counts grouped by emoji for a target."""
        results = self.db.query(
            EmojiReaction.emoji,
            func.count(EmojiReaction.id).label('count')
        ).filter(
            EmojiReaction.target_type == target_type,
            EmojiReaction.target_id == target_id
        ).group_by(EmojiReaction.emoji).all()
        
        return {emoji: count for emoji, count in results}

    def update_reaction(self, reaction: EmojiReaction, emoji: str) -> EmojiReaction:
        """Update an existing reaction with a new emoji."""
        reaction.emoji = emoji
        self.db.commit()
        self.db.refresh(reaction)
        logger.debug(f"Reaction updated: id={reaction.id}, new_emoji={emoji}")
        return reaction

    def delete_reaction(self, reaction: EmojiReaction) -> None:
        """Delete a reaction."""
        self.db.delete(reaction)
        self.db.commit()
        logger.debug(f"Reaction deleted: id={reaction.id}")

    def delete_reactions_by_target(self, target_type: str, target_id: int) -> int:
        """Delete all reactions for a target (used when post/comment is deleted)."""
        count = self.db.query(EmojiReaction).filter(
            EmojiReaction.target_type == target_type,
            EmojiReaction.target_id == target_id
        ).delete()
        self.db.commit()
        logger.debug(f"Deleted {count} reactions for {target_type}:{target_id}")
        return count

    def has_user_reacted(self, user_id: int, target_type: str, target_id: int) -> bool:
        """Check if a user has already reacted to a target."""
        return self.db.query(EmojiReaction).filter(
            EmojiReaction.user_id == user_id,
            EmojiReaction.target_type == target_type,
            EmojiReaction.target_id == target_id
        ).first() is not None
