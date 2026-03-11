"""
Repository for problem discussion operations.
"""
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from app.models.problem_discussion import ProblemDiscussion, ProblemDiscussionComment
from app.core.config import get_logger

logger = get_logger(__name__)


class ProblemDiscussionRepository:
    def __init__(self, db: Session):
        self.db = db
        logger.debug("ProblemDiscussionRepository initialized")

    # Discussion operations
    def create_discussion(self, problem_id: int, title: str, content: str, author_id: int) -> ProblemDiscussion:
        """Create a new problem discussion."""
        discussion = ProblemDiscussion(
            problem_id=problem_id,
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

    def get_discussion_by_id(self, discussion_id: int) -> Optional[ProblemDiscussion]:
        """Get discussion by ID with author loaded."""
        return self.db.query(ProblemDiscussion).options(
            joinedload(ProblemDiscussion.author)
        ).filter(ProblemDiscussion.id == discussion_id).first()

    def list_discussions_by_problem(
        self,
        problem_id: int,
        skip: int = 0,
        limit: int = 20,
        include_unpublished: bool = False,
        include_deleted: bool = False
    ) -> tuple[List[ProblemDiscussion], int]:
        """List discussions for a specific problem."""
        query = self.db.query(ProblemDiscussion).options(joinedload(ProblemDiscussion.author))
        query = query.filter(ProblemDiscussion.problem_id == problem_id)

        if not include_unpublished:
            query = query.filter(ProblemDiscussion.is_published == True)
        if not include_deleted:
            query = query.filter(ProblemDiscussion.is_deleted == False)

        total = query.count()
        discussions = query.order_by(desc(ProblemDiscussion.created_at)).offset(skip).limit(limit).all()
        return discussions, total

    def update_discussion(self, discussion: ProblemDiscussion, title: Optional[str] = None, content: Optional[str] = None) -> ProblemDiscussion:
        """Update a discussion."""
        if title is not None:
            discussion.title = title
        if content is not None:
            discussion.content = content
        self.db.commit()
        self.db.refresh(discussion)
        return discussion

    def delete_discussion(self, discussion: ProblemDiscussion, soft: bool = True) -> None:
        """Delete a discussion (soft or hard)."""
        if soft:
            discussion.is_deleted = True
            self.db.commit()
        else:
            self.db.delete(discussion)
            self.db.commit()

    def publish_discussion(self, discussion: ProblemDiscussion, publish: bool = True) -> ProblemDiscussion:
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
    ) -> ProblemDiscussionComment:
        """Create a new discussion comment or reply."""
        comment = ProblemDiscussionComment(
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

    def get_comment_by_id(self, comment_id: int) -> Optional[ProblemDiscussionComment]:
        """Get comment by ID with author loaded."""
        return self.db.query(ProblemDiscussionComment).options(
            joinedload(ProblemDiscussionComment.author)
        ).filter(ProblemDiscussionComment.id == comment_id).first()

    def get_comments_by_discussion(
        self,
        discussion_id: int,
        include_unpublished: bool = False,
        include_deleted: bool = False
    ) -> List[ProblemDiscussionComment]:
        """Get all comments for a discussion."""
        query = self.db.query(ProblemDiscussionComment).options(
            joinedload(ProblemDiscussionComment.author)
        ).filter(ProblemDiscussionComment.discussion_id == discussion_id)

        if not include_unpublished:
            query = query.filter(ProblemDiscussionComment.is_published == True)
        if not include_deleted:
            query = query.filter(ProblemDiscussionComment.is_deleted == False)

        return query.order_by(ProblemDiscussionComment.created_at).all()

    def update_comment(self, comment: ProblemDiscussionComment, content: str) -> ProblemDiscussionComment:
        """Update a comment."""
        comment.content = content
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def delete_comment(self, comment: ProblemDiscussionComment, soft: bool = True) -> None:
        """Delete a comment (soft or hard)."""
        if soft:
            comment.is_deleted = True
            self.db.commit()
        else:
            self.db.delete(comment)
            self.db.commit()

    def publish_comment(self, comment: ProblemDiscussionComment, publish: bool = True) -> ProblemDiscussionComment:
        """Publish or unpublish a comment."""
        comment.is_published = publish
        self.db.commit()
        self.db.refresh(comment)
        return comment
