"""
Forum service for business logic.
"""
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.forum_repository import ForumRepository
from app.repositories.user_repository import UserRepository
from app.models.forum import ForumPost, ForumComment
from app.models.user import UserRole
from app.core.config import get_logger

logger = get_logger(__name__)


class ForumService:
    def __init__(self, db: Session):
        self.forum_repo = ForumRepository(db)
        self.user_repo = UserRepository(db)
        logger.debug("ForumService initialized")

    # Post operations
    def create_post(self, title: str, content: str, author_id: int) -> ForumPost:
        """Create a new forum post."""
        logger.info(f"Creating post: title='{title[:30]}...', author_id={author_id}")
        if not title or not title.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Post title is required"
            )
        if not content or not content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Post content is required"
            )
        post = self.forum_repo.create_post(title.strip(), content.strip(), author_id)
        logger.info(f"Post created: id={post.id}")
        return post

    def get_post(self, post_id: int, current_user=None) -> ForumPost:
        """Get a post by ID with visibility checks."""
        logger.debug(f"Getting post: id={post_id}")
        post = self.forum_repo.get_post_by_id(post_id)
        if not post:
            logger.warning(f"Post not found: id={post_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # Check visibility
        is_author = current_user and post.author_id == current_user.id
        is_admin = current_user and current_user.role == UserRole.ADMIN
        
        if not post.is_published and not (is_author or is_admin):
            logger.warning(f"Unauthorized access to unpublished post: id={post_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Post is not published"
            )
        
        if post.is_deleted and not is_admin:
            logger.warning(f"Unauthorized access to deleted post: id={post_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        return post

    def list_posts(
        self,
        page: int = 1,
        page_size: int = 20,
        current_user=None
    ) -> dict:
        """List posts with pagination."""
        logger.info(f"Listing posts: page={page}, page_size={page_size}")
        skip = (page - 1) * page_size
        
        # Determine visibility based on user role
        is_admin = current_user and current_user.role == UserRole.ADMIN
        include_unpublished = is_admin
        include_deleted = is_admin
        
        posts, total = self.forum_repo.list_posts(
            skip=skip,
            limit=page_size,
            include_unpublished=include_unpublished,
            include_deleted=include_deleted
        )
        
        pages = (total + page_size - 1) // page_size
        
        return {
            "items": posts,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1
        }

    def update_post(
        self,
        post_id: int,
        title: Optional[str],
        content: Optional[str],
        current_user
    ) -> ForumPost:
        """Update a post."""
        logger.info(f"Updating post: id={post_id}, user={current_user.username}")
        post = self.get_post(post_id, current_user)
        
        # Check permission
        is_author = post.author_id == current_user.id
        is_admin = current_user.role == UserRole.ADMIN
        
        if not (is_author or is_admin):
            logger.warning(f"Unauthorized post update attempt: id={post_id}, user={current_user.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own posts"
            )
        
        updated = self.forum_repo.update_post(post, title, content)
        logger.info(f"Post updated: id={post_id}")
        return updated

    def delete_post(self, post_id: int, current_user, hard: bool = False) -> None:
        """Delete a post."""
        logger.info(f"Deleting post: id={post_id}, user={current_user.username}, hard={hard}")
        post = self.get_post(post_id, current_user)
        
        # Check permission
        is_author = post.author_id == current_user.id
        is_admin = current_user.role == UserRole.ADMIN
        
        if not (is_author or is_admin):
            logger.warning(f"Unauthorized post delete attempt: id={post_id}, user={current_user.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own posts"
            )
        
        # Only admins can hard delete
        if hard and not is_admin:
            logger.warning(f"Non-admin hard delete attempt: id={post_id}, user={current_user.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can permanently delete posts"
            )
        
        self.forum_repo.delete_post(post, soft=not hard)
        logger.info(f"Post deleted: id={post_id}")

    def publish_post(self, post_id: int, publish: bool, current_user) -> ForumPost:
        """Publish or unpublish a post."""
        logger.info(f"Publishing post: id={post_id}, publish={publish}, user={current_user.username}")
        post = self.get_post(post_id, current_user)
        
        is_author = post.author_id == current_user.id
        is_admin = current_user.role == UserRole.ADMIN
        
        if not (is_author or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only publish/unpublish your own posts"
            )
        
        updated = self.forum_repo.publish_post(post, publish)
        logger.info(f"Post publish status changed: id={post_id}, published={publish}")
        return updated

    # Comment operations
    def create_comment(
        self,
        content: str,
        post_id: int,
        author_id: int,
        parent_id: Optional[int] = None
    ) -> ForumComment:
        """Create a new comment or reply."""
        logger.info(f"Creating comment: post_id={post_id}, parent_id={parent_id}, author_id={author_id}")
        
        # Validate content
        if not content or not content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comment content is required"
            )
        
        # Check if post exists and is published
        post = self.forum_repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        if not post.is_published:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot comment on unpublished posts"
            )
        if post.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # If replying to a comment, verify it exists
        if parent_id:
            parent = self.forum_repo.get_comment_by_id(parent_id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent comment not found"
                )
            if parent.post_id != post_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent comment does not belong to this post"
                )
            if not parent.is_published or parent.is_deleted:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot reply to this comment"
                )
        
        comment = self.forum_repo.create_comment(
            content=content.strip(),
            author_id=author_id,
            post_id=post_id,
            parent_id=parent_id
        )
        logger.info(f"Comment created: id={comment.id}")
        return comment

    def get_comment(self, comment_id: int, current_user=None) -> ForumComment:
        """Get a comment by ID with visibility checks."""
        logger.debug(f"Getting comment: id={comment_id}")
        comment = self.forum_repo.get_comment_by_id(comment_id)
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

    def get_post_comments(self, post_id: int, current_user=None) -> List[ForumComment]:
        """Get all comments for a post in a flat structure."""
        logger.debug(f"Getting comments for post: id={post_id}")
        
        # Verify post exists
        post = self.get_post(post_id, current_user)
        
        is_admin = current_user and current_user.role == UserRole.ADMIN
        return self.forum_repo.get_comments_by_post(
            post_id,
            include_unpublished=is_admin,
            include_deleted=is_admin
        )

    def get_comment_tree(self, post_id: int, current_user=None) -> List[dict]:
        """Get comments organized in a tree structure."""
        logger.debug(f"Building comment tree for post: id={post_id}")
        
        # Get all comments for the post
        all_comments = self.get_post_comments(post_id, current_user)
        
        # Build comment map
        comment_map = {c.id: c for c in all_comments}
        
        # Build tree
        tree = []
        for comment in all_comments:
            if comment.parent_id is None:
                # Top-level comment
                tree.append(self._build_comment_node(comment, comment_map))
        
        return tree

    def _format_datetime(self, dt):
        """Format datetime to ISO string."""
        return dt.isoformat() if dt else None

    def _build_comment_node(self, comment: ForumComment, comment_map: dict) -> dict:
        """Recursively build a comment node with its replies."""
        node = {
            "id": comment.id,
            "content": comment.content,
            "author_id": comment.author_id,
            "author_username": comment.author.username if comment.author else None,
            "post_id": comment.post_id,
            "parent_id": comment.parent_id,
            "is_published": comment.is_published,
            "is_deleted": comment.is_deleted,
            "created_at": self._format_datetime(comment.created_at),
            "updated_at": self._format_datetime(comment.updated_at),
            "replies": []
        }
        
        # Get replies (comments that have this comment as parent)
        for c in comment_map.values():
            if c.parent_id == comment.id:
                node["replies"].append(self._build_comment_node(c, comment_map))
        
        return node

    def update_comment(
        self,
        comment_id: int,
        content: str,
        current_user
    ) -> ForumComment:
        """Update a comment."""
        logger.info(f"Updating comment: id={comment_id}, user={current_user.username}")
        comment = self.get_comment(comment_id, current_user)
        
        is_author = comment.author_id == current_user.id
        is_admin = current_user.role == UserRole.ADMIN
        
        if not (is_author or is_admin):
            logger.warning(f"Unauthorized comment update: id={comment_id}, user={current_user.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own comments"
            )
        
        if not content or not content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comment content is required"
            )
        
        updated = self.forum_repo.update_comment(comment, content.strip())
        logger.info(f"Comment updated: id={comment_id}")
        return updated

    def delete_comment(self, comment_id: int, current_user, hard: bool = False) -> None:
        """Delete a comment."""
        logger.info(f"Deleting comment: id={comment_id}, user={current_user.username}, hard={hard}")
        comment = self.get_comment(comment_id, current_user)
        
        is_author = comment.author_id == current_user.id
        is_admin = current_user.role == UserRole.ADMIN
        
        if not (is_author or is_admin):
            logger.warning(f"Unauthorized comment delete: id={comment_id}, user={current_user.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own comments"
            )
        
        if hard and not is_admin:
            logger.warning(f"Non-admin hard delete attempt: id={comment_id}, user={current_user.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can permanently delete comments"
            )
        
        self.forum_repo.delete_comment(comment, soft=not hard)
        logger.info(f"Comment deleted: id={comment_id}")
