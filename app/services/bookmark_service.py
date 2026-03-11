"""
Service layer for bookmark operations.
"""
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.bookmark_repository import BookmarkRepository
from app.repositories.problem_repository import ProblemRepository
from app.core.config import get_logger

logger = get_logger(__name__)


class BookmarkService:
    def __init__(self, db: Session):
        self.bookmark_repo = BookmarkRepository(db)
        self.problem_repo = ProblemRepository(db)
        logger.debug("BookmarkService initialized")

    def add_bookmark(self, user_id: int, problem_id: int):
        """Add a bookmark for a problem."""
        logger.info(f"Adding bookmark: user_id={user_id}, problem_id={problem_id}")

        # Ensure problem exists and is published
        problem = self.problem_repo.get_problem_by_id(problem_id)
        if not problem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problem not found"
            )
        if not problem.is_published:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot bookmark unpublished problems"
            )

        if self.bookmark_repo.is_bookmarked(user_id, problem_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Problem already bookmarked"
            )

        return self.bookmark_repo.create_bookmark(user_id, problem_id)

    def remove_bookmark(self, user_id: int, problem_id: int):
        """Remove a bookmark."""
        logger.info(f"Removing bookmark: user_id={user_id}, problem_id={problem_id}")
        bookmark = self.bookmark_repo.get_bookmark(user_id, problem_id)
        if not bookmark:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bookmark not found"
            )
        self.bookmark_repo.delete_bookmark(bookmark)

    def list_bookmarks(self, user_id: int, page: int = 1, page_size: int = 20):
        """List bookmarks for a user with pagination."""
        logger.info(f"Listing bookmarks: user_id={user_id}, page={page}")
        skip = (page - 1) * page_size
        bookmarks, total = self.bookmark_repo.list_bookmarks_by_user(user_id, skip=skip, limit=page_size)
        pages = (total + page_size - 1) // page_size

        return {
            "items": bookmarks,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1
        }

    def is_bookmarked(self, user_id: int, problem_id: int) -> bool:
        """Check if a problem is bookmarked by the user."""
        return self.bookmark_repo.is_bookmarked(user_id, problem_id)
