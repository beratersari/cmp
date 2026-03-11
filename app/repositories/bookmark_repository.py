"""
Repository for bookmark operations.
"""
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from app.models.bookmark import Bookmark
from app.core.config import get_logger

logger = get_logger(__name__)


class BookmarkRepository:
    def __init__(self, db: Session):
        self.db = db
        logger.debug("BookmarkRepository initialized")

    def create_bookmark(self, user_id: int, problem_id: int) -> Bookmark:
        """Create a new bookmark."""
        bookmark = Bookmark(user_id=user_id, problem_id=problem_id)
        self.db.add(bookmark)
        self.db.commit()
        self.db.refresh(bookmark)
        return bookmark

    def get_bookmark(self, user_id: int, problem_id: int) -> Optional[Bookmark]:
        """Get a bookmark by user and problem."""
        return self.db.query(Bookmark).filter(
            Bookmark.user_id == user_id,
            Bookmark.problem_id == problem_id
        ).first()

    def list_bookmarks_by_user(self, user_id: int, skip: int = 0, limit: int = 20) -> tuple[List[Bookmark], int]:
        """List bookmarks for a user with pagination."""
        query = self.db.query(Bookmark).options(joinedload(Bookmark.problem))
        query = query.filter(Bookmark.user_id == user_id)
        total = query.count()
        bookmarks = query.order_by(Bookmark.created_at.desc()).offset(skip).limit(limit).all()
        return bookmarks, total

    def delete_bookmark(self, bookmark: Bookmark) -> None:
        """Delete a bookmark."""
        self.db.delete(bookmark)
        self.db.commit()

    def is_bookmarked(self, user_id: int, problem_id: int) -> bool:
        """Check if a problem is bookmarked by user."""
        return self.get_bookmark(user_id, problem_id) is not None
