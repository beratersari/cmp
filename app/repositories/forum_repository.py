"""
Forum repository for database operations.
"""
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from app.models.forum import ForumPost, ForumComment
from app.core.config import get_logger

logger = get_logger(__name__)


class ForumRepository:
    def __init__(self, db: Session):
        self.db = db
        logger.debug("ForumRepository initialized")

    # Post operations
    def create_post(self, title: str, content: str, author_id: int) -> ForumPost:
        """Create a new forum post."""
        logger.debug(f"Creating post: title='{title[:30]}...', author_id={author_id}")
        post = ForumPost(
            title=title,
            content=content,
            author_id=author_id,
            is_published=True,
            is_deleted=False
        )
        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)
        logger.debug(f"Post created: id={post.id}")
        return post

    def get_post_by_id(self, post_id: int) -> Optional[ForumPost]:
        """Get a post by ID with author loaded."""
        return self.db.query(ForumPost).options(
            joinedload(ForumPost.author)
        ).filter(ForumPost.id == post_id).first()

    def list_posts(
        self,
        skip: int = 0,
        limit: int = 20,
        include_unpublished: bool = False,
        include_deleted: bool = False
    ) -> tuple[List[ForumPost], int]:
        """List posts with pagination."""
        query = self.db.query(ForumPost).options(joinedload(ForumPost.author))
        
        if not include_unpublished:
            query = query.filter(ForumPost.is_published == True)
        if not include_deleted:
            query = query.filter(ForumPost.is_deleted == False)
        
        total = query.count()
        posts = query.order_by(desc(ForumPost.created_at)).offset(skip).limit(limit).all()
        return posts, total

    def update_post(self, post: ForumPost, title: Optional[str] = None, content: Optional[str] = None) -> ForumPost:
        """Update a post."""
        if title is not None:
            post.title = title
        if content is not None:
            post.content = content
        self.db.commit()
        self.db.refresh(post)
        return post

    def delete_post(self, post: ForumPost, soft: bool = True) -> None:
        """Delete a post (soft or hard delete)."""
        if soft:
            post.is_deleted = True
            self.db.commit()
            logger.debug(f"Post soft deleted: id={post.id}")
        else:
            self.db.delete(post)
            self.db.commit()
            logger.debug(f"Post hard deleted: id={post.id}")

    def publish_post(self, post: ForumPost, publish: bool = True) -> ForumPost:
        """Publish or unpublish a post."""
        post.is_published = publish
        self.db.commit()
        self.db.refresh(post)
        return post

    # Comment operations
    def create_comment(
        self,
        content: str,
        author_id: int,
        post_id: int,
        parent_id: Optional[int] = None
    ) -> ForumComment:
        """Create a new comment or reply."""
        logger.debug(f"Creating comment: post_id={post_id}, parent_id={parent_id}, author_id={author_id}")
        comment = ForumComment(
            content=content,
            author_id=author_id,
            post_id=post_id,
            parent_id=parent_id,
            is_published=True,
            is_deleted=False
        )
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        logger.debug(f"Comment created: id={comment.id}")
        return comment

    def get_comment_by_id(self, comment_id: int) -> Optional[ForumComment]:
        """Get a comment by ID with author loaded."""
        return self.db.query(ForumComment).options(
            joinedload(ForumComment.author)
        ).filter(ForumComment.id == comment_id).first()

    def get_comments_by_post(
        self,
        post_id: int,
        include_unpublished: bool = False,
        include_deleted: bool = False
    ) -> List[ForumComment]:
        """Get all comments for a post."""
        query = self.db.query(ForumComment).options(
            joinedload(ForumComment.author)
        ).filter(ForumComment.post_id == post_id)
        
        if not include_unpublished:
            query = query.filter(ForumComment.is_published == True)
        if not include_deleted:
            query = query.filter(ForumComment.is_deleted == False)
        
        return query.order_by(ForumComment.created_at).all()

    def get_top_level_comments(
        self,
        post_id: int,
        include_unpublished: bool = False,
        include_deleted: bool = False
    ) -> List[ForumComment]:
        """Get top-level comments (not replies) for a post."""
        query = self.db.query(ForumComment).options(
            joinedload(ForumComment.author)
        ).filter(
            ForumComment.post_id == post_id,
            ForumComment.parent_id == None
        )
        
        if not include_unpublished:
            query = query.filter(ForumComment.is_published == True)
        if not include_deleted:
            query = query.filter(ForumComment.is_deleted == False)
        
        return query.order_by(ForumComment.created_at).all()

    def get_comment_replies(
        self,
        comment_id: int,
        include_unpublished: bool = False,
        include_deleted: bool = False
    ) -> List[ForumComment]:
        """Get replies to a specific comment."""
        query = self.db.query(ForumComment).options(
            joinedload(ForumComment.author)
        ).filter(ForumComment.parent_id == comment_id)
        
        if not include_unpublished:
            query = query.filter(ForumComment.is_published == True)
        if not include_deleted:
            query = query.filter(ForumComment.is_deleted == False)
        
        return query.order_by(ForumComment.created_at).all()

    def update_comment(self, comment: ForumComment, content: str) -> ForumComment:
        """Update a comment."""
        comment.content = content
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def delete_comment(self, comment: ForumComment, soft: bool = True) -> None:
        """Delete a comment (soft or hard delete)."""
        if soft:
            comment.is_deleted = True
            self.db.commit()
            logger.debug(f"Comment soft deleted: id={comment.id}")
        else:
            self.db.delete(comment)
            self.db.commit()
            logger.debug(f"Comment hard deleted: id={comment.id}")

    def publish_comment(self, comment: ForumComment, publish: bool = True) -> ForumComment:
        """Publish or unpublish a comment."""
        comment.is_published = publish
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def get_comment_count(self, post_id: int) -> int:
        """Get total comment count for a post."""
        return self.db.query(ForumComment).filter(
            ForumComment.post_id == post_id,
            ForumComment.is_deleted == False,
            ForumComment.is_published == True
        ).count()
