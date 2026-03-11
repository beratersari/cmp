"""
Forum API endpoints for posts and comments.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.services.forum_service import ForumService
from app.api.dependencies import RoleChecker, get_current_user
from app.models.user import UserRole
from app.core.config import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/forum",
    tags=["Forum"],
    responses={404: {"description": "Not found"}},
)


# Schemas
class PostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Post title")
    content: str = Field(..., min_length=1, description="Post content")


class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Post title")
    content: Optional[str] = Field(None, min_length=1, description="Post content")


class PostOut(BaseModel):
    id: int
    title: str
    content: str
    author_id: int
    author_username: Optional[str]
    is_published: bool
    comment_count: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, description="Comment content")
    parent_id: Optional[int] = Field(None, description="Parent comment ID for replies")


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, description="Comment content")


class CommentOut(BaseModel):
    id: int
    content: str
    author_id: int
    author_username: Optional[str]
    post_id: int
    parent_id: Optional[int]
    is_published: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class CommentTreeOut(BaseModel):
    id: int
    content: str
    author_id: int
    author_username: Optional[str]
    post_id: int
    parent_id: Optional[int]
    is_published: bool
    is_deleted: bool
    created_at: str
    updated_at: str
    replies: List["CommentTreeOut"] = []


class PostDetailOut(PostOut):
    comments: List[CommentTreeOut] = []


# Helper to convert datetime to string
def format_datetime(dt):
    return dt.isoformat() if dt else None


def convert_post_to_out(post) -> PostOut:
    """Convert a ForumPost model to PostOut schema."""
    return PostOut(
        id=post.id,
        title=post.title,
        content=post.content,
        author_id=post.author_id,
        author_username=post.author.username if post.author else None,
        is_published=post.is_published,
        comment_count=post.comment_count,
        created_at=format_datetime(post.created_at),
        updated_at=format_datetime(post.updated_at)
    )


def convert_comment_to_out(comment) -> CommentOut:
    """Convert a ForumComment model to CommentOut schema."""
    return CommentOut(
        id=comment.id,
        content=comment.content,
        author_id=comment.author_id,
        author_username=comment.author.username if comment.author else None,
        post_id=comment.post_id,
        parent_id=comment.parent_id,
        is_published=comment.is_published,
        created_at=format_datetime(comment.created_at),
        updated_at=format_datetime(comment.updated_at)
    )


# Post endpoints
@router.post(
    "/posts",
    response_model=PostOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new forum post",
    description="""
    Create a new forum post.
    
    ### Authorization:
    - Any authenticated user can create posts.
    """
)
def create_post(
    post_create: PostCreate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Creating post: title='{post_create.title[:30]}...', user={current_user.username}")
    forum_service = ForumService(db)
    post = forum_service.create_post(
        title=post_create.title,
        content=post_create.content,
        author_id=current_user.id
    )
    return convert_post_to_out(post)


@router.get(
    "/posts",
    response_model=dict,
    summary="List all forum posts",
    description="""
    List forum posts with pagination.
    
    ### Visibility:
    - Regular users see only published, non-deleted posts.
    - Admins can see all posts including unpublished and deleted.
    
    ### Pagination:
    - Use `page` and `page_size` query parameters.
    - Default: page=1, page_size=20
    """
)
def list_posts(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Listing posts: page={page}, page_size={page_size}, user={current_user.username}")
    forum_service = ForumService(db)
    result = forum_service.list_posts(page=page, page_size=page_size, current_user=current_user)
    result["items"] = [convert_post_to_out(p) for p in result["items"]]
    return result


@router.get(
    "/posts/{post_id}",
    response_model=PostDetailOut,
    summary="Get a specific post with comments",
    description="""
    Get a post by ID with all its comments in a tree structure.
    
    ### Visibility:
    - Regular users can only see published posts.
    - Admins can see unpublished and deleted posts.
    """
)
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Getting post: id={post_id}, user={current_user.username}")
    forum_service = ForumService(db)
    post = forum_service.get_post(post_id, current_user)
    comment_tree = forum_service.get_comment_tree(post_id, current_user)
    
    post_out = convert_post_to_out(post)
    return PostDetailOut(
        **post_out.model_dump(),
        comments=comment_tree
    )


@router.put(
    "/posts/{post_id}",
    response_model=PostOut,
    summary="Update a forum post",
    description="""
    Update a post's title or content.
    
    ### Authorization:
    - Users can only update their own posts.
    - Admins can update any post.
    """
)
def update_post(
    post_id: int,
    post_update: PostUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Updating post: id={post_id}, user={current_user.username}")
    forum_service = ForumService(db)
    post = forum_service.update_post(
        post_id=post_id,
        title=post_update.title,
        content=post_update.content,
        current_user=current_user
    )
    return convert_post_to_out(post)


@router.delete(
    "/posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a forum post",
    description="""
    Delete a post (soft delete by default).
    
    ### Authorization:
    - Users can only delete their own posts.
    - Admins can delete any post.
    
    ### Query Parameters:
    - `hard=true`: Permanently delete the post (admin only).
    """
)
def delete_post(
    post_id: int,
    hard: bool = Query(default=False, description="Permanently delete the post (admin only)"),
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Deleting post: id={post_id}, user={current_user.username}, hard={hard}")
    forum_service = ForumService(db)
    forum_service.delete_post(post_id, current_user, hard=hard)


@router.put(
    "/posts/{post_id}/publish",
    response_model=PostOut,
    summary="Publish or unpublish a post",
    description="""
    Toggle the published status of a post.
    
    ### Authorization:
    - Users can only publish/unpublish their own posts.
    - Admins can publish/unpublish any post.
    """
)
def publish_post(
    post_id: int,
    publish: bool = Query(..., description="True to publish, False to unpublish"),
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Publishing post: id={post_id}, publish={publish}, user={current_user.username}")
    forum_service = ForumService(db)
    post = forum_service.publish_post(post_id, publish, current_user)
    return convert_post_to_out(post)


# Comment endpoints
@router.post(
    "/posts/{post_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a comment on a post",
    description="""
    Create a new comment on a post, or reply to an existing comment.
    
    ### Authorization:
    - Any authenticated user can comment on published posts.
    
    ### Notes:
    - Set `parent_id` to reply to an existing comment.
    - Without `parent_id`, the comment is a top-level comment on the post.
    """
)
def create_comment(
    post_id: int,
    comment_create: CommentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Creating comment: post_id={post_id}, parent_id={comment_create.parent_id}, user={current_user.username}")
    forum_service = ForumService(db)
    comment = forum_service.create_comment(
        content=comment_create.content,
        post_id=post_id,
        author_id=current_user.id,
        parent_id=comment_create.parent_id
    )
    return convert_comment_to_out(comment)


@router.get(
    "/posts/{post_id}/comments",
    response_model=List[CommentTreeOut],
    summary="Get all comments for a post (tree structure)",
    description="""
    Get all comments for a post organized in a tree structure.
    
    ### Response:
    - Comments are returned in a nested tree structure.
    - Each comment has a `replies` array containing its replies.
    """
)
def get_post_comments(
    post_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Getting comments for post: id={post_id}, user={current_user.username}")
    forum_service = ForumService(db)
    return forum_service.get_comment_tree(post_id, current_user)


@router.get(
    "/comments/{comment_id}",
    response_model=CommentOut,
    summary="Get a specific comment",
    description="Get a comment by ID."
)
def get_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Getting comment: id={comment_id}, user={current_user.username}")
    forum_service = ForumService(db)
    comment = forum_service.get_comment(comment_id, current_user)
    return convert_comment_to_out(comment)


@router.put(
    "/comments/{comment_id}",
    response_model=CommentOut,
    summary="Update a comment",
    description="""
    Update a comment's content.
    
    ### Authorization:
    - Users can only update their own comments.
    - Admins can update any comment.
    """
)
def update_comment(
    comment_id: int,
    comment_update: CommentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Updating comment: id={comment_id}, user={current_user.username}")
    forum_service = ForumService(db)
    comment = forum_service.update_comment(
        comment_id=comment_id,
        content=comment_update.content,
        current_user=current_user
    )
    return convert_comment_to_out(comment)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment",
    description="""
    Delete a comment (soft delete by default).
    
    ### Authorization:
    - Users can only delete their own comments.
    - Admins can delete any comment.
    
    ### Query Parameters:
    - `hard=true`: Permanently delete the comment (admin only).
    """
)
def delete_comment(
    comment_id: int,
    hard: bool = Query(default=False, description="Permanently delete the comment (admin only)"),
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Deleting comment: id={comment_id}, user={current_user.username}, hard={hard}")
    forum_service = ForumService(db)
    forum_service.delete_comment(comment_id, current_user, hard=hard)


# ============================================================================
# Emoji Reaction Endpoints
# ============================================================================

class EmojiReactionCreate(BaseModel):
    emoji: str = Field(..., description="Emoji in format like :happy:, :angry:, :sad:")


class EmojiReactionOut(BaseModel):
    id: int
    user_id: int
    target_type: str
    target_id: int
    emoji: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


from app.services.emoji_reaction_service import EmojiReactionService


@router.get(
    "/emojis",
    response_model=List[str],
    summary="Get valid emoji list",
    description="Returns a list of valid emoji strings that can be used for reactions."
)
def get_valid_emojis(
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    """Get list of valid emoji strings."""
    from app.services.emoji_reaction_service import VALID_EMOJIS
    return sorted(list(VALID_EMOJIS))


@router.post(
    "/posts/{post_id}/reactions",
    response_model=EmojiReactionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add or update emoji reaction on a post",
    description="""
    Add a new emoji reaction to a post, or update existing reaction.
    Each user can only have ONE reaction per post.
    
    ### Valid Emojis:
    `:happy:`, `:sad:`, `:angry:`, `:laugh:`, `:love:`, `:thumbsup:`, `:thumbsdown:`,
    `:wow:`, `:cool:`, `:confused:`, `:fire:`, `:rocket:`, `:clap:`, `:thinking:`
    """
)
def add_post_reaction(
    post_id: int,
    reaction: EmojiReactionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Adding reaction to post: post_id={post_id}, user={current_user.username}, emoji={reaction.emoji}")
    emoji_service = EmojiReactionService(db)
    result = emoji_service.add_or_update_reaction(
        user_id=current_user.id,
        target_type="post",
        target_id=post_id,
        emoji=reaction.emoji
    )
    return {
        "id": result.id,
        "user_id": result.user_id,
        "target_type": result.target_type,
        "target_id": result.target_id,
        "emoji": result.emoji,
        "created_at": result.created_at.isoformat() if result.created_at else None,
        "updated_at": result.updated_at.isoformat() if result.updated_at else None
    }


@router.get(
    "/posts/{post_id}/reactions",
    response_model=dict,
    summary="Get emoji reactions for a post",
    description="Get all emoji reactions for a post with counts per emoji."
)
def get_post_reactions(
    post_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Getting reactions for post: post_id={post_id}, user={current_user.username}")
    emoji_service = EmojiReactionService(db)
    return emoji_service.get_reactions_for_target("post", post_id)


@router.get(
    "/posts/{post_id}/reactions/me",
    response_model=Optional[EmojiReactionOut],
    summary="Get current user's reaction on a post",
    description="Get the current user's emoji reaction for a specific post (if any)."
)
def get_my_post_reaction(
    post_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Getting my reaction for post: post_id={post_id}, user={current_user.username}")
    emoji_service = EmojiReactionService(db)
    return emoji_service.get_user_reaction(current_user.id, "post", post_id)


@router.delete(
    "/posts/{post_id}/reactions",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove emoji reaction from a post",
    description="Remove the current user's emoji reaction from a post."
)
def remove_post_reaction(
    post_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Removing reaction from post: post_id={post_id}, user={current_user.username}")
    emoji_service = EmojiReactionService(db)
    emoji_service.remove_reaction(current_user.id, "post", post_id)


@router.post(
    "/comments/{comment_id}/reactions",
    response_model=EmojiReactionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add or update emoji reaction on a comment",
    description="""
    Add a new emoji reaction to a comment, or update existing reaction.
    Each user can only have ONE reaction per comment.
    
    ### Valid Emojis:
    `:happy:`, `:sad:`, `:angry:`, `:laugh:`, `:love:`, `:thumbsup:`, `:thumbsdown:`,
    `:wow:`, `:cool:`, `:confused:`, `:fire:`, `:rocket:`, `:clap:`, `:thinking:`
    """
)
def add_comment_reaction(
    comment_id: int,
    reaction: EmojiReactionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Adding reaction to comment: comment_id={comment_id}, user={current_user.username}, emoji={reaction.emoji}")
    emoji_service = EmojiReactionService(db)
    result = emoji_service.add_or_update_reaction(
        user_id=current_user.id,
        target_type="comment",
        target_id=comment_id,
        emoji=reaction.emoji
    )
    return {
        "id": result.id,
        "user_id": result.user_id,
        "target_type": result.target_type,
        "target_id": result.target_id,
        "emoji": result.emoji,
        "created_at": result.created_at.isoformat() if result.created_at else None,
        "updated_at": result.updated_at.isoformat() if result.updated_at else None
    }


@router.get(
    "/comments/{comment_id}/reactions",
    response_model=dict,
    summary="Get emoji reactions for a comment",
    description="Get all emoji reactions for a comment with counts per emoji."
)
def get_comment_reactions(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Getting reactions for comment: comment_id={comment_id}, user={current_user.username}")
    emoji_service = EmojiReactionService(db)
    return emoji_service.get_reactions_for_target("comment", comment_id)


@router.get(
    "/comments/{comment_id}/reactions/me",
    response_model=Optional[EmojiReactionOut],
    summary="Get current user's reaction on a comment",
    description="Get the current user's emoji reaction for a specific comment (if any)."
)
def get_my_comment_reaction(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Getting my reaction for comment: comment_id={comment_id}, user={current_user.username}")
    emoji_service = EmojiReactionService(db)
    return emoji_service.get_user_reaction(current_user.id, "comment", comment_id)


@router.delete(
    "/comments/{comment_id}/reactions",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove emoji reaction from a comment",
    description="Remove the current user's emoji reaction from a comment."
)
def remove_comment_reaction(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Removing reaction from comment: comment_id={comment_id}, user={current_user.username}")
    emoji_service = EmojiReactionService(db)
    emoji_service.remove_reaction(current_user.id, "comment", comment_id)
