"""
Service layer for contest discussions.
"""
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.contest_discussion_repository import ContestDiscussionRepository
from app.repositories.contest_repository import ContestRepository
from app.models.contest_discussion import ContestDiscussion, ContestDiscussionComment
from app.models.user import UserRole
from app.core.config import get_logger

logger = get_logger(__name__)


class ContestDiscussionService:
    def __init__(self, db: Session):
        self.discussion_repo = ContestDiscussionRepository(db)
        self.contest_repo = ContestRepository(db)
        logger.debug("ContestDiscussionService initialized")

    # Discussion operations
    def create_discussion(self, contest_id: int, title: str, content: str, author_id: int) -> ContestDiscussion:
        """Create a new contest discussion."""
        logger.info(f"Creating discussion: contest_id={contest_id}, author_id={author_id}")

        if not title or not title.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Discussion title is required"
            )
        if not content or not content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Discussion content is required"
            )

        # Ensure contest exists
        contest = self.contest_repo.get_contest_by_id(contest_id)
        if not contest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contest not found"
            )
        
        # For private/archived contests, only contest owner can create discussions
        # Admins are checked via API RoleChecker, so we trust the caller
        is_owner = contest.owner_id == author_id
        
        # For non-public contests, only owners can create discussions
        if not contest.is_public and not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create discussion for non-public contest. Only contest owners can do this."
            )

        discussion = self.discussion_repo.create_discussion(
            contest_id=contest_id,
            title=title.strip(),
            content=content.strip(),
            author_id=author_id
        )
        logger.info(f"Discussion created: id={discussion.id}")
        return discussion

    def get_discussion(self, discussion_id: int, current_user=None) -> ContestDiscussion:
        """Get a discussion by ID with visibility checks."""
        discussion = self.discussion_repo.get_discussion_by_id(discussion_id)
        if not discussion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Discussion not found"
            )

        is_author = current_user and discussion.author_id == current_user.id
        is_admin = current_user and current_user.role == UserRole.ADMIN

        if not discussion.is_published and not (is_author or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Discussion is not published"
            )

        if discussion.is_deleted and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Discussion not found"
            )

        return discussion

    def list_discussions(
        self,
        contest_id: int,
        page: int = 1,
        page_size: int = 20,
        current_user=None
    ) -> dict:
        """List discussions for a contest with pagination."""
        logger.info(f"Listing discussions: contest_id={contest_id}, page={page}")
        skip = (page - 1) * page_size

        is_admin = current_user and current_user.role == UserRole.ADMIN
        include_unpublished = is_admin
        include_deleted = is_admin

        discussions, total = self.discussion_repo.list_discussions_by_contest(
            contest_id=contest_id,
            skip=skip,
            limit=page_size,
            include_unpublished=include_unpublished,
            include_deleted=include_deleted
        )

        pages = (total + page_size - 1) // page_size

        return {
            "items": discussions,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1
        }

    def update_discussion(
        self,
        discussion_id: int,
        title: Optional[str],
        content: Optional[str],
        current_user
    ) -> ContestDiscussion:
        """Update a discussion."""
        discussion = self.get_discussion(discussion_id, current_user)

        is_author = discussion.author_id == current_user.id
        is_admin = current_user.role == UserRole.ADMIN
        if not (is_author or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own discussions"
            )

        return self.discussion_repo.update_discussion(discussion, title, content)

    def delete_discussion(self, discussion_id: int, current_user, hard: bool = False) -> None:
        """Delete a discussion."""
        discussion = self.get_discussion(discussion_id, current_user)

        is_author = discussion.author_id == current_user.id
        is_admin = current_user.role == UserRole.ADMIN
        if not (is_author or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own discussions"
            )

        if hard and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can permanently delete discussions"
            )

        self.discussion_repo.delete_discussion(discussion, soft=not hard)

    # Comment operations
    def create_comment(
        self,
        discussion_id: int,
        content: str,
        author_id: int,
        parent_id: Optional[int] = None
    ) -> ContestDiscussionComment:
        """Create a comment or reply in a discussion."""
        logger.info(f"Creating comment: discussion_id={discussion_id}, author_id={author_id}")

        if not content or not content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comment content is required"
            )

        discussion = self.discussion_repo.get_discussion_by_id(discussion_id)
        if not discussion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Discussion not found"
            )
        if not discussion.is_published:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot comment on unpublished discussions"
            )
        if discussion.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Discussion not found"
            )

        if parent_id:
            parent = self.discussion_repo.get_comment_by_id(parent_id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent comment not found"
                )
            if parent.discussion_id != discussion_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent comment does not belong to this discussion"
                )
            if not parent.is_published or parent.is_deleted:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot reply to this comment"
                )

        return self.discussion_repo.create_comment(
            discussion_id=discussion_id,
            content=content.strip(),
            author_id=author_id,
            parent_id=parent_id
        )

    def get_comment(self, comment_id: int, current_user=None) -> ContestDiscussionComment:
        """Get a comment by ID with visibility checks."""
        comment = self.discussion_repo.get_comment_by_id(comment_id)
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )

        is_author = current_user and comment.author_id == current_user.id
        is_admin = current_user and current_user.role == UserRole.ADMIN

        if not comment.is_published and not (is_author or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Comment is not published"
            )

        if comment.is_deleted and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )

        return comment

    def get_discussion_comments(self, discussion_id: int, current_user=None) -> List[ContestDiscussionComment]:
        """Get all comments for a discussion."""
        discussion = self.get_discussion(discussion_id, current_user)
        is_admin = current_user and current_user.role == UserRole.ADMIN
        return self.discussion_repo.get_comments_by_discussion(
            discussion_id,
            include_unpublished=is_admin,
            include_deleted=is_admin
        )

    def get_comment_tree(self, discussion_id: int, current_user=None) -> List[dict]:
        """Get comments organized in a tree structure."""
        all_comments = self.get_discussion_comments(discussion_id, current_user)
        comment_map = {c.id: c for c in all_comments}

        tree = []
        for comment in all_comments:
            if comment.parent_id is None:
                tree.append(self._build_comment_node(comment, comment_map))

        return tree

    def _format_datetime(self, dt):
        return dt.isoformat() if dt else None

    def _build_comment_node(self, comment: ContestDiscussionComment, comment_map: dict) -> dict:
        node = {
            "id": comment.id,
            "content": comment.content,
            "author_id": comment.author_id,
            "author_username": comment.author.username if comment.author else None,
            "discussion_id": comment.discussion_id,
            "parent_id": comment.parent_id,
            "is_published": comment.is_published,
            "is_deleted": comment.is_deleted,
            "created_at": self._format_datetime(comment.created_at),
            "updated_at": self._format_datetime(comment.updated_at),
            "replies": []
        }

        for c in comment_map.values():
            if c.parent_id == comment.id:
                node["replies"].append(self._build_comment_node(c, comment_map))

        return node

    def update_comment(self, comment_id: int, content: str, current_user) -> ContestDiscussionComment:
        comment = self.get_comment(comment_id, current_user)

        is_author = comment.author_id == current_user.id
        is_admin = current_user.role == UserRole.ADMIN
        if not (is_author or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own comments"
            )

        if not content or not content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comment content is required"
            )

        return self.discussion_repo.update_comment(comment, content.strip())

    def delete_comment(self, comment_id: int, current_user, hard: bool = False) -> None:
        comment = self.get_comment(comment_id, current_user)

        is_author = comment.author_id == current_user.id
        is_admin = current_user.role == UserRole.ADMIN
        if not (is_author or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own comments"
            )

        if hard and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can permanently delete comments"
            )

        self.discussion_repo.delete_comment(comment, soft=not hard)
