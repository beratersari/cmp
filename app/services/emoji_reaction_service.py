"""
Emoji reaction service for business logic.
"""
from typing import Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.emoji_reaction_repository import EmojiReactionRepository
from app.repositories.forum_repository import ForumRepository
from app.models.emoji_reaction import EmojiReaction
from app.core.config import get_logger

logger = get_logger(__name__)

# Valid emoji formats (string format like :happy:, :angry:, :sad:)
VALID_EMOJIS = {
    ":happy:", ":sad:", ":angry:", ":laugh:", ":love:", ":thumbsup:", ":thumbsdown:",
    ":wow:", ":cool:", ":confused:", ":fire:", ":rocket:", ":clap:", ":thinking:"
}


class EmojiReactionService:
    def __init__(self, db: Session):
        self.emoji_repo = EmojiReactionRepository(db)
        self.forum_repo = ForumRepository(db)
        logger.debug("EmojiReactionService initialized")

    def _validate_emoji(self, emoji: str) -> str:
        """Validate and normalize emoji format."""
        if not emoji:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Emoji is required"
            )
        
        emoji = emoji.strip().lower()
        
        # Ensure emoji is in :name: format
        if not (emoji.startswith(":") and emoji.endswith(":")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Emoji must be in format like :happy:, :angry:, :sad:"
            )
        
        if emoji not in VALID_EMOJIS:
            valid_list = ", ".join(sorted(VALID_EMOJIS))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid emoji. Valid options: {valid_list}"
            )
        
        return emoji

    def _validate_target(self, target_type: str, target_id: int) -> None:
        """Validate that the target exists and is visible."""
        if target_type not in ["post", "comment"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target type must be 'post' or 'comment'"
            )
        
        if target_type == "post":
            target = self.forum_repo.get_post_by_id(target_id)
            if not target:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Post not found"
                )
            if not target.is_published or target.is_deleted:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot react to this post"
                )
        else:  # comment
            target = self.forum_repo.get_comment_by_id(target_id)
            if not target:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Comment not found"
                )
            if not target.is_published or target.is_deleted:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot react to this comment"
                )

    def add_or_update_reaction(
        self,
        user_id: int,
        target_type: str,
        target_id: int,
        emoji: str
    ) -> EmojiReaction:
        """
        Add a new reaction or update existing one.
        Each user can only have one reaction per target.
        """
        logger.info(f"Adding/updating reaction: user={user_id}, target={target_type}:{target_id}, emoji={emoji}")
        
        # Validate emoji format
        emoji = self._validate_emoji(emoji)
        
        # Validate target exists
        self._validate_target(target_type, target_id)
        
        # Check if user already has a reaction for this target
        existing = self.emoji_repo.get_reaction_by_user_and_target(user_id, target_type, target_id)
        
        if existing:
            # Update existing reaction
            updated = self.emoji_repo.update_reaction(existing, emoji)
            logger.info(f"Reaction updated: id={updated.id}")
            return updated
        else:
            # Create new reaction
            reaction = self.emoji_repo.create_reaction(user_id, target_type, target_id, emoji)
            logger.info(f"Reaction created: id={reaction.id}")
            return reaction

    def remove_reaction(self, user_id: int, target_type: str, target_id: int) -> None:
        """Remove a user's reaction from a target."""
        logger.info(f"Removing reaction: user={user_id}, target={target_type}:{target_id}")
        
        if target_type not in ["post", "comment"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target type must be 'post' or 'comment'"
            )
        
        existing = self.emoji_repo.get_reaction_by_user_and_target(user_id, target_type, target_id)
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reaction not found"
            )
        
        self.emoji_repo.delete_reaction(existing)
        logger.info(f"Reaction removed: user={user_id}, target={target_type}:{target_id}")

    def get_reactions_for_target(self, target_type: str, target_id: int) -> Dict:
        """Get all reactions for a target with counts."""
        logger.debug(f"Getting reactions for target={target_type}:{target_id}")
        
        if target_type not in ["post", "comment"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target type must be 'post' or 'comment'"
            )
        
        reactions = self.emoji_repo.get_reactions_by_target(target_type, target_id)
        counts = self.emoji_repo.get_reaction_counts_by_target(target_type, target_id)
        
        return {
            "target_type": target_type,
            "target_id": target_id,
            "total_reactions": len(reactions),
            "counts": counts,
            "reactions": [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "emoji": r.emoji,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                }
                for r in reactions
            ]
        }

    def get_user_reaction(self, user_id: int, target_type: str, target_id: int) -> Optional[Dict]:
        """Get a specific user's reaction for a target."""
        logger.debug(f"Getting user reaction: user={user_id}, target={target_type}:{target_id}")
        
        if target_type not in ["post", "comment"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target type must be 'post' or 'comment'"
            )
        
        reaction = self.emoji_repo.get_reaction_by_user_and_target(user_id, target_type, target_id)
        
        if not reaction:
            return None
        
        return {
            "id": reaction.id,
            "user_id": reaction.user_id,
            "target_type": reaction.target_type,
            "target_id": reaction.target_id,
            "emoji": reaction.emoji,
            "created_at": reaction.created_at.isoformat() if reaction.created_at else None,
            "updated_at": reaction.updated_at.isoformat() if reaction.updated_at else None
        }

    def get_valid_emojis(self) -> List[str]:
        """Get list of valid emoji strings."""
        return sorted(list(VALID_EMOJIS))
