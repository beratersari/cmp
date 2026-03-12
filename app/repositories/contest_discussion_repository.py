"""
Repository for contest discussion operations.
"""
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from app.models.contest_discussion import ContestDiscussion, ContestDiscussionComment
from app.core.config import get_logger

logger = get_logger(__name__)


class ContestDiscussionRepository:
    def __init__(self, db: Session):
        self.db = db
        logger.debug("ContestDiscussionRepository initialized")

    # Discussion operations
    def create_discussion(self, contest_id: int, title: str, content: str, author_id: int) -> ContestDiscussion:
        """Create a new contest discussion."""
        discussion = ContestDiscussion(
            contest_id=contest_id,
            title=title,
            content=content,
            author_id=author_id,
            is_published=True,
            is_deleted=False
        )
        self.db.add(discussion)
        self.db.commit()
        self.db.refresh(discussion)
        return discussion

    def get_discussion_by_id(self, discussion_id: int) -> Optional[ContestDiscussion]:
        """Get discussion by ID with author loaded."""
        return self.db.query(ContestDiscussion).options(
            joinedload(ContestDiscussion.author)
        ).filter(ContestDiscussion.id == discussion_id).first()

    def list_discussions_by_contest(
        self,
        contest_id: int,
        skip: int = 0,
        limit: int = 20,
        include_unpublished: bool = False,
        include_deleted: bool = False
    ) -> tuple[List[ContestDiscussion], int]:
        """List discussions for a specific contest."""
        query = self.db.query(ContestDiscussion).options(joinedload(ContestDiscussion.author))
        query = query.filter(ContestDiscussion.contest_id == contest_id)

        if not include_unpublished:
            query = query.filter(ContestDiscussion.is_published == True)
        if not include_deleted:
            query = query.filter(ContestDiscussion.is_deleted == False)

        total = query.count()
        discussions = query.order_by(desc(ContestDiscussion.created_at)).offset(skip).limit(limit).all()
        return discussions, total

    def update_discussion(self, discussion: ContestDiscussion, title: Optional[str] = None, content: Optional[str] = None) -> ContestDiscussion:
        """Update a discussion."""
        if title is not None:
            discussion.title = title
        if content is not None:
            discussion.content = content
        self.db.commit()
        self.db.refresh(discussion)
        return discussion

    def delete_discussion(self, discussion: ContestDiscussion, soft: bool = True) -> None:
        """Delete a discussion (soft or hard)."""
        if soft:
            discussion.is_deleted = True
            self.db.commit()
        else:
            self.db.delete(discussion)
            self.db.commit()

    def publish_discussion(self, discussion: ContestDiscussion, publish: bool = True) -> ContestDiscussion:
        """Publish or unpublish a discussion."""
        discussion.is_published = publish
        self.db.commit()
        self.db.refresh(discussion)
        return discussion

    # Comment operations
    def create_comment(
        self,
        discussion_id: int,
        content: str,
        author_id: int,
        parent_id: Optional[int] = None
    ) -> ContestDiscussionComment:
        """Create a new discussion comment or reply."""
        comment = ContestDiscussionComment(
            discussion_id=discussion_id,
            content=content,
            author_id=author_id,
            parent_id=parent_id,
            is_published=True,
            is_deleted=False
        )
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def get_comment_by_id(self, comment_id: int) -> Optional[ContestDiscussionComment]:
        """Get comment by ID with author loaded."""
        return self.db.query(ContestDiscussionComment).options(
            joinedload(ContestDiscussionComment.author)
        ).filter(ContestDiscussionComment.id == comment_id).first()

    def get_comments_by_discussion(
        self,
        discussion_id: int,
        include_unpublished: bool = False,
        include_deleted: bool = False
    ) -> List[ContestDiscussionComment]:
        """Get all comments for a discussion."""
        query = self.db.query(ContestDiscussionComment).options(
            joinedload(ContestDiscussionComment.author)
        ).filter(ContestDiscussionComment.discussion_id == discussion_id)

        if not include_unpublished:
            query = query.filter(ContestDiscussionComment.is_published == True)
        if not include_deleted:
            query = query.filter(ContestDiscussionComment.is_deleted == False)

        return query.order_by(ContestDiscussionComment.created_at).all()

    def update_comment(self, comment: ContestDiscussionComment, content: str) -> ContestDiscussionComment:
        """Update a comment."""
        comment.content = content
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def delete_comment(self, comment: ContestDiscussionComment, soft: bool = True) -> None:
        """Delete a comment (soft or hard)."""
        if soft:
            comment.is_deleted = True
            self.db.commit()
        else:
            self.db.delete(comment)
            self.db.commit()

    def publish_comment(self, comment: ContestDiscussionComment, publish: bool = True) -> ContestDiscussionComment:
        """Publish or unpublish a comment."""
        comment.is_published = publish
        self.db.commit()
        self.db.refresh(comment)
        return comment
