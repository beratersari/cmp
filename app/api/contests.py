from typing import List
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    ContestCreate,
    ContestUpdate,
    ContestOut,
    ContestDetailOut,
    ContestAddProblems,
    ContestRemoveProblems,
    ContestReorderProblems,
    PaginatedResponse,
    ContestDiscussionCreate,
    ContestDiscussionUpdate,
    ContestDiscussionOut,
    ContestDiscussionDetailOut,
    ContestDiscussionCommentCreate,
    ContestDiscussionCommentUpdate,
    ContestDiscussionCommentOut,
    ContestDiscussionTreeOut,
    ContestRegistrationOut,
    ContestRegistrationUpdate,
    ContestRegistrationSummaryOut,
    UserRegistrationOut,
    ContestAnnouncementCreate,
    ContestAnnouncementUpdate,
    ContestAnnouncementOut,
    SubmissionCreate,
    SubmissionOut,
    ContestManagerOut,
    ContestTicketCreate,
    ContestTicketUpdate,
    ContestTicketOut,
    ContestTicketSummaryOut,
    ContestTicketStatusUpdate,
    ContestTicketResponseCreate,
    ContestTicketResponseOut,
)
from app.services.contest_service import ContestService
from app.services.contest_discussion_service import ContestDiscussionService
from app.api.dependencies import RoleChecker, oauth2_scheme, get_current_user
from app.models.user import UserRole
from app.models.contest import ContestType, ContestRegistrationStatus
from app.core.config import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/contests",
    tags=["Contests"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "",
    response_model=ContestOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new contest (admin/creator only)",
    description="""
    Create a new programming contest with problems.

    ### Required Fields:
    - **title**: Title of the contest.
    - **start_date**: Start date and time of the contest (ISO format).
    - **end_date**: End date and time of the contest (ISO format, must be after start_date).

    ### Optional Fields:
    - **description**: Description of the contest.
    - **contest_type**: Type of contest - "public", "private", or "archived" (default: "public").
        - **public**: Visible to everyone, problems visible to everyone.
        - **private**: Visible to everyone, problems only to registered users.
        - **archived**: Only visible to owner/admin.
    - **problem_ids**: List of problem IDs to include in the contest.

    ### Authorization:
    This endpoint is restricted to **admin** and **creator** roles.
    """
)
def create_contest(
    contest_create: ContestCreate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    logger.info(f"Creating contest: title='{contest_create.title}' by {current_user.username}")
    try:
        contest_service = ContestService(db)
        contest = contest_service.create_contest(
            contest_create,
            owner_id=current_user.id,
            created_by=current_user.username
        )
        logger.info(f"Contest created successfully: id={contest.id}, title='{contest.title}'")
        return contest
    except Exception as e:
        logger.error(f"Failed to create contest: title='{contest_create.title}', error={str(e)}")
        raise


@router.get(
    "",
    response_model=PaginatedResponse[ContestOut],
    summary="List all contests (filtered by visibility)",
    description="""
    Retrieve contests available in the system with pagination and search support.

    ### Filtering Logic:
    - **Standard Users/Unauthenticated**: See **public** and **private** contests (not archived).
    - **Creators**: See public/private contests and their own contests.
    - **Admins**: See **all** contests including archived.

    ### Pagination:
    - Use `page` and `page_size` query parameters to control pagination.
    - Default: page=1, page_size=20

    ### Search:
    - Use `search` query parameter to search by title or description (case-insensitive).

    ### Filters:
    - `contest_type`: Filter by contest type (public, private, archived).
    """
)
def list_contests(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    search: str | None = Query(default=None, description="Search by title or description"),
    contest_type: ContestType | None = Query(default=None, description="Filter by contest type"),
    token: str = Depends(oauth2_scheme)
):
    logger.info(f"Listing contests: page={page}, page_size={page_size}, search={search}")
    current_user = None
    if token:
        try:
            current_user = get_current_user(token, db)
            logger.debug(f"Authenticated user: {current_user.username}")
        except Exception as e:
            logger.debug(f"Token validation failed: {str(e)}")
            pass
    else:
        logger.debug("No token provided, listing as anonymous")

    contest_service = ContestService(db)
    result = contest_service.list_contests(
        current_user,
        page=page,
        page_size=page_size,
        search=search,
        contest_type=contest_type
    )
    logger.debug(f"Listed {len(result.get('items', []))} contests, total={result.get('total', 0)}")
    return result


@router.get(
    "/upcoming",
    response_model=PaginatedResponse[ContestOut],
    summary="List upcoming contests",
    description="""
    List contests that haven't started yet.

    Only shows published, non-archived contests.
    """
)
def list_upcoming_contests(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    token: str = Depends(oauth2_scheme)
):
    logger.info(f"Listing upcoming contests: page={page}")
    current_user = None
    if token:
        try:
            current_user = get_current_user(token, db)
        except:
            pass

    contest_service = ContestService(db)
    return contest_service.list_upcoming_contests(current_user, page=page, page_size=page_size)


@router.get(
    "/active",
    response_model=PaginatedResponse[ContestOut],
    summary="List active contests",
    description="""
    List contests that are currently running.

    Only shows published, non-archived contests.
    """
)
def list_active_contests(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    token: str = Depends(oauth2_scheme)
):
    logger.info(f"Listing active contests: page={page}")
    current_user = None
    if token:
        try:
            current_user = get_current_user(token, db)
        except:
            pass

    contest_service = ContestService(db)
    return contest_service.list_active_contests(current_user, page=page, page_size=page_size)


@router.get(
    "/past",
    response_model=PaginatedResponse[ContestOut],
    summary="List past contests",
    description="""
    List contests that have ended.

    Only shows published contests.
    """
)
def list_past_contests(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    token: str = Depends(oauth2_scheme)
):
    logger.info(f"Listing past contests: page={page}")
    current_user = None
    if token:
        try:
            current_user = get_current_user(token, db)
        except:
            pass

    contest_service = ContestService(db)
    return contest_service.list_past_contests(current_user, page=page, page_size=page_size)


@router.get(
    "/my/registrations",
    response_model=PaginatedResponse[UserRegistrationOut],
    summary="List my contest registrations",
    description="""
    List all contest registrations for the current user.

    ### Filters:
    - `status`: Filter by registration status (pending, approved, rejected).
    """
)
def list_my_registrations(
    status_filter: ContestRegistrationStatus | None = Query(default=None, alias="status", description="Filter by registration status"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    contest_service = ContestService(db)
    return contest_service.list_my_registrations(
        current_user, status_filter=status_filter, page=page, page_size=page_size
    )


@router.get(
    "/{contest_id}",
    response_model=ContestDetailOut,
    summary="Get a specific contest by ID",
    description="""
    Fetch a specific contest by its unique ID with full problem details.

    ### Visibility Rules:
    - **Public contests**: Everyone can see problems.
    - **Private contests**: Everyone can see general details, but only registered users can see problems.
    - **Archived contests**: Only owner/admin can see.

    ### Problem Visibility:
    - For private contests, problems are only shown to:
        - Contest owner
        - Admins
        - Users with approved registration
    """
)
def get_contest(
    contest_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    logger.info(f"Getting contest: contest_id={contest_id}")
    current_user = None
    if token:
        try:
            current_user = get_current_user(token, db)
            logger.debug(f"Authenticated user: {current_user.username}")
        except:
            logger.debug("Token validation failed")
            pass

    try:
        contest_service = ContestService(db)
        contest = contest_service.get_contest_detail(contest_id, current_user)
        logger.info(f"Contest retrieved: id={contest.id}, title='{contest.title}'")
        return contest
    except Exception as e:
        logger.warning(f"Failed to get contest: contest_id={contest_id}, error={str(e)}")
        raise


@router.put(
    "/{contest_id}",
    response_model=ContestOut,
    summary="Update a contest (admin/owner)",
    description="""
    Update any field of a contest.

    ### Authorization:
    - **Admins**: Can update any contest.
    - **Owners**: Can update their own contests.
    """
)
def update_contest(
    contest_id: int,
    contest_update: ContestUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    logger.info(f"Updating contest: contest_id={contest_id} by {current_user.username}")
    try:
        contest_service = ContestService(db)
        contest = contest_service.update_contest(contest_id, contest_update, current_user)
        logger.info(f"Contest updated: id={contest.id}, title='{contest.title}'")
        return contest
    except Exception as e:
        logger.error(f"Failed to update contest: contest_id={contest_id}, error={str(e)}")
        raise


@router.delete(
    "/{contest_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a contest (admin/owner)",
    description="""
    Delete a contest.

    ### Authorization:
    - **Admins**: Can delete any contest.
    - **Owners**: Can delete their own contests.
    """
)
def delete_contest(
    contest_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    logger.info(f"Deleting contest: contest_id={contest_id} by {current_user.username}")
    try:
        contest_service = ContestService(db)
        contest_service.delete_contest(contest_id, current_user)
        logger.info(f"Contest deleted: contest_id={contest_id}")
    except Exception as e:
        logger.error(f"Failed to delete contest: contest_id={contest_id}, error={str(e)}")
        raise


@router.post(
    "/{contest_id}/problems",
    response_model=ContestOut,
    summary="Add problems to a contest (admin/owner)",
    description="""
    Add problems to an existing contest.

    ### Authorization:
    - **Admins**: Can add problems to any contest.
    - **Owners**: Can add problems to their own contests.
    """
)
def add_problems_to_contest(
    contest_id: int,
    payload: ContestAddProblems,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    logger.info(f"Adding problems to contest: contest_id={contest_id}, problems={payload.problem_ids}")
    try:
        contest_service = ContestService(db)
        contest = contest_service.add_problems_to_contest(contest_id, payload.problem_ids, current_user)
        logger.info(f"Problems added to contest: id={contest.id}")
        return contest
    except Exception as e:
        logger.error(f"Failed to add problems: contest_id={contest_id}, error={str(e)}")
        raise


@router.delete(
    "/{contest_id}/problems",
    response_model=ContestOut,
    summary="Remove problems from a contest (admin/owner)",
    description="""
    Remove problems from an existing contest.

    ### Authorization:
    - **Admins**: Can remove problems from any contest.
    - **Owners**: Can remove problems from their own contests.
    """
)
def remove_problems_from_contest(
    contest_id: int,
    payload: ContestRemoveProblems,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    logger.info(f"Removing problems from contest: contest_id={contest_id}, problems={payload.problem_ids}")
    try:
        contest_service = ContestService(db)
        contest = contest_service.remove_problems_from_contest(contest_id, payload.problem_ids, current_user)
        logger.info(f"Problems removed from contest: id={contest.id}")
        return contest
    except Exception as e:
        logger.error(f"Failed to remove problems: contest_id={contest_id}, error={str(e)}")
        raise


@router.put(
    "/{contest_id}/problems/order",
    response_model=ContestOut,
    summary="Reorder problems in a contest (admin/owner)",
    description="""
    Change the order of problems in a contest.

    ### Request Body:
    Send a list of objects with `problem_id` and `order` fields.
    The `order` field is 0-indexed (first problem has order 0).

    ### Example:
    ```json
    {
        "problems": [
            {"problem_id": 1, "order": 2},
            {"problem_id": 2, "order": 0},
            {"problem_id": 3, "order": 1}
        ]
    }
    ```

    ### Authorization:
    - **Admins**: Can reorder problems in any contest.
    - **Owners**: Can reorder problems in their own contests.
    """
)
def reorder_problems_in_contest(
    contest_id: int,
    payload: ContestReorderProblems,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    logger.info(f"Reordering problems in contest: contest_id={contest_id}")
    try:
        contest_service = ContestService(db)
        # Convert Pydantic models to dicts
        problem_orders = [{"problem_id": p.problem_id, "order": p.order} for p in payload.problems]
        contest = contest_service.reorder_problems(contest_id, problem_orders, current_user)
        logger.info(f"Problems reordered in contest: id={contest.id}")
        return contest
    except Exception as e:
        logger.error(f"Failed to reorder problems: contest_id={contest_id}, error={str(e)}")
        raise


# ============================================================================
# Contest Discussion Endpoints
# ============================================================================

@router.post(
    "/{contest_id}/discussions",
    response_model=ContestDiscussionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a discussion for a contest",
    description="""
    Create a new discussion thread for a contest.

    ### Authorization:
    - Any authenticated user can create discussions for published contests.
    """
)
def create_contest_discussion(
    contest_id: int,
    discussion_create: ContestDiscussionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Creating discussion: contest_id={contest_id}, user={current_user.username}")
    discussion_service = ContestDiscussionService(db)
    discussion = discussion_service.create_discussion(
        contest_id=contest_id,
        title=discussion_create.title,
        content=discussion_create.content,
        author_id=current_user.id
    )
    return ContestDiscussionOut(
        id=discussion.id,
        contest_id=discussion.contest_id,
        title=discussion.title,
        content=discussion.content,
        author_id=discussion.author_id,
        author_username=discussion.author.username if discussion.author else None,
        is_published=discussion.is_published,
        created_at=discussion.created_at.isoformat() if discussion.created_at else None,
        updated_at=discussion.updated_at.isoformat() if discussion.updated_at else None
    )


@router.get(
    "/{contest_id}/discussions",
    response_model=dict,
    summary="List discussions for a contest",
    description="""
    List discussion threads for a specific contest (paginated).

    ### Authorization:
    - Any authenticated user can view discussions for published contests.
    """
)
def list_contest_discussions(
    contest_id: int,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Listing discussions: contest_id={contest_id}, page={page}")
    discussion_service = ContestDiscussionService(db)
    result = discussion_service.list_discussions(
        contest_id=contest_id,
        page=page,
        page_size=page_size,
        current_user=current_user
    )
    result["items"] = [
        ContestDiscussionOut(
            id=d.id,
            contest_id=d.contest_id,
            title=d.title,
            content=d.content,
            author_id=d.author_id,
            author_username=d.author.username if d.author else None,
            is_published=d.is_published,
            created_at=d.created_at.isoformat() if d.created_at else None,
            updated_at=d.updated_at.isoformat() if d.updated_at else None
        )
        for d in result["items"]
    ]
    return result


@router.get(
    "/discussions/{discussion_id}",
    response_model=ContestDiscussionDetailOut,
    summary="Get a discussion with comments",
    description="""
    Get a specific discussion by ID along with its comments in a tree structure.
    """
)
def get_contest_discussion(
    discussion_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    discussion_service = ContestDiscussionService(db)
    discussion = discussion_service.get_discussion(discussion_id, current_user)
    comments = discussion_service.get_comment_tree(discussion_id, current_user)

    discussion_out = ContestDiscussionOut(
        id=discussion.id,
        contest_id=discussion.contest_id,
        title=discussion.title,
        content=discussion.content,
        author_id=discussion.author_id,
        author_username=discussion.author.username if discussion.author else None,
        is_published=discussion.is_published,
        created_at=discussion.created_at.isoformat() if discussion.created_at else None,
        updated_at=discussion.updated_at.isoformat() if discussion.updated_at else None
    )

    return ContestDiscussionDetailOut(
        **discussion_out.model_dump(),
        comments=comments
    )


@router.put(
    "/discussions/{discussion_id}",
    response_model=ContestDiscussionOut,
    summary="Update a discussion",
    description="""
    Update a discussion thread (author or admin only).
    """
)
def update_contest_discussion(
    discussion_id: int,
    discussion_update: ContestDiscussionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    discussion_service = ContestDiscussionService(db)
    discussion = discussion_service.update_discussion(
        discussion_id=discussion_id,
        title=discussion_update.title,
        content=discussion_update.content,
        current_user=current_user
    )
    return ContestDiscussionOut(
        id=discussion.id,
        contest_id=discussion.contest_id,
        title=discussion.title,
        content=discussion.content,
        author_id=discussion.author_id,
        author_username=discussion.author.username if discussion.author else None,
        is_published=discussion.is_published,
        created_at=discussion.created_at.isoformat() if discussion.created_at else None,
        updated_at=discussion.updated_at.isoformat() if discussion.updated_at else None
    )


@router.delete(
    "/discussions/{discussion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a discussion",
    description="""
    Delete a discussion thread (soft delete by default).

    ### Authorization:
    - Users can only delete their own discussions.
    - Admins can delete any discussion.

    ### Query Parameters:
    - `hard=true`: Permanently delete the discussion (admin only).
    """
)
def delete_contest_discussion(
    discussion_id: int,
    hard: bool = Query(default=False, description="Permanently delete the discussion (admin only)"),
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    discussion_service = ContestDiscussionService(db)
    discussion_service.delete_discussion(discussion_id, current_user, hard=hard)


@router.post(
    "/discussions/{discussion_id}/comments",
    response_model=ContestDiscussionCommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a comment in a discussion",
    description="""
    Create a comment in a discussion (or reply to another comment).
    Set `parent_id` to create a nested reply.
    """
)
def create_contest_discussion_comment(
    discussion_id: int,
    comment_create: ContestDiscussionCommentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    discussion_service = ContestDiscussionService(db)
    comment = discussion_service.create_comment(
        discussion_id=discussion_id,
        content=comment_create.content,
        author_id=current_user.id,
        parent_id=comment_create.parent_id
    )
    return ContestDiscussionCommentOut(
        id=comment.id,
        discussion_id=comment.discussion_id,
        content=comment.content,
        author_id=comment.author_id,
        author_username=comment.author.username if comment.author else None,
        parent_id=comment.parent_id,
        is_published=comment.is_published,
        created_at=comment.created_at.isoformat() if comment.created_at else None,
        updated_at=comment.updated_at.isoformat() if comment.updated_at else None
    )


@router.get(
    "/discussions/{discussion_id}/comments",
    response_model=List[ContestDiscussionTreeOut],
    summary="Get discussion comments (tree)",
    description="""
    Get discussion comments organized in a tree structure.
    """
)
def get_contest_discussion_comments(
    discussion_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    discussion_service = ContestDiscussionService(db)
    return discussion_service.get_comment_tree(discussion_id, current_user)


@router.get(
    "/discussion-comments/{comment_id}",
    response_model=ContestDiscussionCommentOut,
    summary="Get a discussion comment",
    description="Get a specific discussion comment by ID."
)
def get_contest_discussion_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    discussion_service = ContestDiscussionService(db)
    comment = discussion_service.get_comment(comment_id, current_user)
    return ContestDiscussionCommentOut(
        id=comment.id,
        discussion_id=comment.discussion_id,
        content=comment.content,
        author_id=comment.author_id,
        author_username=comment.author.username if comment.author else None,
        parent_id=comment.parent_id,
        is_published=comment.is_published,
        created_at=comment.created_at.isoformat() if comment.created_at else None,
        updated_at=comment.updated_at.isoformat() if comment.updated_at else None
    )


@router.put(
    "/discussion-comments/{comment_id}",
    response_model=ContestDiscussionCommentOut,
    summary="Update a discussion comment",
    description="""
    Update a discussion comment (author or admin only).
    """
)
def update_contest_discussion_comment(
    comment_id: int,
    comment_update: ContestDiscussionCommentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    discussion_service = ContestDiscussionService(db)
    comment = discussion_service.update_comment(
        comment_id=comment_id,
        content=comment_update.content,
        current_user=current_user
    )
    return ContestDiscussionCommentOut(
        id=comment.id,
        discussion_id=comment.discussion_id,
        content=comment.content,
        author_id=comment.author_id,
        author_username=comment.author.username if comment.author else None,
        parent_id=comment.parent_id,
        is_published=comment.is_published,
        created_at=comment.created_at.isoformat() if comment.created_at else None,
        updated_at=comment.updated_at.isoformat() if comment.updated_at else None
    )


@router.delete(
    "/discussion-comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a discussion comment",
    description="""
    Delete a discussion comment (soft delete by default).

    ### Authorization:
    - Users can only delete their own comments.
    - Admins can delete any comment.

    ### Query Parameters:
    - `hard=true`: Permanently delete the comment (admin only).
    """
)
def delete_contest_discussion_comment(
    comment_id: int,
    hard: bool = Query(default=False, description="Permanently delete the comment (admin only)"),
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    discussion_service = ContestDiscussionService(db)
    discussion_service.delete_comment(comment_id, current_user, hard=hard)


# ============================================================================
# Contest Registration Endpoints
# ============================================================================

@router.post(
    "/{contest_id}/register",
    response_model=ContestRegistrationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register for a contest",
    description="""
    Register the current user for a contest.

    ### Registration Flow:
    - User registers for a contest with "pending" status.
    - For private contests, the owner/admin must approve the registration.
    - Once approved, the user can see problems in private contests.

    ### Authorization:
    - Any authenticated user can register for public/private contests.
    """
)
def register_for_contest(
    contest_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"User {current_user.username} registering for contest {contest_id}")
    contest_service = ContestService(db)
    return contest_service.register_for_contest(contest_id, current_user)


@router.get(
    "/{contest_id}/registration",
    response_model=ContestRegistrationOut | None,
    summary="Get my registration status",
    description="""
    Get the current user's registration status for a contest.

    Returns null if the user is not registered.
    """
)
def get_my_registration(
    contest_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    contest_service = ContestService(db)
    return contest_service.get_my_registration(contest_id, current_user)


@router.delete(
    "/{contest_id}/registration",
    status_code=status.HTTP_200_OK,
    summary="Cancel my registration",
    description="""
    Cancel the current user's registration for a contest.
    """
)
def cancel_my_registration(
    contest_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"User {current_user.username} cancelling registration for contest {contest_id}")
    contest_service = ContestService(db)
    return contest_service.cancel_registration(contest_id, current_user)


@router.get(
    "/{contest_id}/registrations",
    response_model=PaginatedResponse[ContestRegistrationOut],
    summary="List contest registrations (admin/owner only)",
    description="""
    List all registrations for a contest.

    ### Authorization:
    - **Admins**: Can view registrations for any contest.
    - **Owners**: Can view registrations for their own contests.

    ### Filters:
    - `status`: Filter by registration status (pending, approved, rejected).
    """
)
def list_contest_registrations(
    contest_id: int,
    status_filter: ContestRegistrationStatus | None = Query(default=None, alias="status", description="Filter by registration status"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    logger.info(f"Listing registrations for contest {contest_id}")
    contest_service = ContestService(db)
    return contest_service.list_contest_registrations(
        contest_id, current_user, status_filter=status_filter, page=page, page_size=page_size
    )


@router.put(
    "/{contest_id}/registrations/{registration_id}",
    response_model=ContestRegistrationOut,
    summary="Update registration status (admin/owner only)",
    description="""
    Approve or reject a user's registration.

    ### Authorization:
    - **Admins**: Can update registrations for any contest.
    - **Owners**: Can update registrations for their own contests.

    ### Status Values:
    - `pending`: Registration awaiting approval.
    - `approved`: User can see problems in private contests.
    - `rejected`: User's registration was denied.
    """
)
def update_registration_status(
    contest_id: int,
    registration_id: int,
    registration_update: ContestRegistrationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    logger.info(f"Updating registration {registration_id} to {registration_update.status}")
    contest_service = ContestService(db)
    return contest_service.update_registration_status(
        contest_id, registration_id, registration_update.status, current_user
    )


@router.get(
    "/{contest_id}/registrations/summary",
    response_model=ContestRegistrationSummaryOut,
    summary="Get registration summary",
    description="""
    Get a summary of registrations for a contest.

    ### Authorization:
    - **Admins**: Can view summary for any contest.
    - **Owners**: Can view summary for their own contests.

    ### Returns:
    - Total registrations count
    - Pending count
    - Approved count
    - Rejected count
    """
)
def get_registration_summary(
    contest_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    contest_service = ContestService(db)
    return contest_service.get_registration_summary(contest_id, current_user)


# ============================================================================
# Contest Announcement Endpoints
# ============================================================================

@router.post(
    "/{contest_id}/announcements",
    response_model=ContestAnnouncementOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a contest announcement (admin/owner only)",
    description="""
    Create an announcement for a contest.

    ### Authorization:
    - **Admins**: Can create announcements for any contest.
    - **Owners**: Can create announcements for their own contests.

    ### Fields:
    - **title**: Announcement title (required, 1-200 characters)
    - **content**: Announcement content (required)
    - **is_published**: Whether to publish immediately (default: true)
    """
)
def create_contest_announcement(
    contest_id: int,
    announcement_create: ContestAnnouncementCreate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    logger.info(f"Creating announcement for contest {contest_id} by {current_user.username}")
    contest_service = ContestService(db)
    return contest_service.create_announcement(contest_id, announcement_create, current_user)


@router.get(
    "/{contest_id}/announcements",
    response_model=PaginatedResponse[ContestAnnouncementOut],
    summary="List contest announcements",
    description="""
    List announcements for a contest.

    ### Visibility:
    - Regular users see only published announcements.
    - Admins and owners can see all announcements including drafts.

    ### Pagination:
    - Use `page` and `page_size` query parameters.
    - Announcements are ordered by creation date (newest first).
    """
)
def list_contest_announcements(
    contest_id: int,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    logger.info(f"Listing announcements for contest {contest_id}")
    current_user = None
    if token:
        try:
            current_user = get_current_user(token, db)
        except:
            pass

    contest_service = ContestService(db)
    return contest_service.list_announcements(
        contest_id, current_user=current_user, page=page, page_size=page_size
    )


@router.get(
    "/{contest_id}/announcements/{announcement_id}",
    response_model=ContestAnnouncementOut,
    summary="Get a specific announcement",
    description="""
    Get a specific announcement by ID.

    ### Visibility:
    - Regular users can only see published announcements.
    - Admins and owners can see unpublished announcements.
    """
)
def get_contest_announcement(
    contest_id: int,
    announcement_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    logger.info(f"Getting announcement {announcement_id} for contest {contest_id}")
    current_user = None
    if token:
        try:
            current_user = get_current_user(token, db)
        except:
            pass

    contest_service = ContestService(db)
    return contest_service.get_announcement(contest_id, announcement_id, current_user)


@router.put(
    "/{contest_id}/announcements/{announcement_id}",
    response_model=ContestAnnouncementOut,
    summary="Update an announcement (admin/owner only)",
    description="""
    Update a contest announcement.

    ### Authorization:
    - **Admins**: Can update any announcement.
    - **Owners**: Can update announcements for their own contests.

    ### Fields:
    - **title**: New title (optional)
    - **content**: New content (optional)
    - **is_published**: Publish/unpublish (optional)
    """
)
def update_contest_announcement(
    contest_id: int,
    announcement_id: int,
    announcement_update: ContestAnnouncementUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    logger.info(f"Updating announcement {announcement_id} by {current_user.username}")
    contest_service = ContestService(db)
    return contest_service.update_announcement(
        contest_id, announcement_id, announcement_update, current_user
    )


@router.delete(
    "/{contest_id}/announcements/{announcement_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an announcement (admin/owner only)",
    description="""
    Delete a contest announcement.

    ### Authorization:
    - **Admins**: Can delete any announcement.
    - **Owners**: Can delete announcements for their own contests.
    """
)
def delete_contest_announcement(
    contest_id: int,
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    logger.info(f"Deleting announcement {announcement_id} by {current_user.username}")
    contest_service = ContestService(db)
    return contest_service.delete_announcement(contest_id, announcement_id, current_user)


# ============================================================================
# Contest Submission Endpoints
# ============================================================================

@router.post(
    "/{contest_id}/problems/{problem_id}/submissions",
    response_model=SubmissionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Submit code for a contest problem",
    description="""
    Submit code for a problem within a contest.
    
    ### Authorization:
    - For public contests: Any authenticated user.
    - For private contests: Only registered (approved) users.
    
    ### Notes:
    - Submissions made through this endpoint are marked as contest submissions.
    - They will NOT appear when listing submissions for the problem outside of the contest.
    - They WILL appear when listing submissions for the contest.
    """
)
def create_contest_submission(
    contest_id: int,
    problem_id: int,
    submission_create: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Creating contest submission: contest_id={contest_id}, problem_id={problem_id}, user={current_user.username}")
    contest_service = ContestService(db)
    submission = contest_service.create_contest_submission(
        contest_id=contest_id,
        problem_id=problem_id,
        submission_create=submission_create,
        current_user=current_user
    )
    return SubmissionOut.model_validate(submission)


@router.get(
    "/{contest_id}/submissions",
    response_model=list[SubmissionOut],
    summary="List all submissions for a contest (admin/owner only)",
    description="""
    List all submissions made during a contest.
    
    ### Authorization:
    - **Admins**: Can view submissions for any contest.
    - **Owners**: Can view submissions for their own contests.
    
    ### Notes:
    - This only returns submissions made through the contest submission endpoint.
    - Individual problem submissions are NOT included.
    """
)
def list_contest_submissions(
    contest_id: int,
    problem_id: int | None = Query(default=None, description="Filter by problem ID"),
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    logger.info(f"Listing contest submissions: contest_id={contest_id}")
    contest_service = ContestService(db)
    return [
        SubmissionOut.model_validate(s) 
        for s in contest_service.list_contest_submissions(contest_id, current_user, problem_id=problem_id)
    ]


@router.get(
    "/{contest_id}/my/submissions",
    response_model=list[SubmissionOut],
    summary="List my submissions for a contest",
    description="""
    List the current user's submissions made during a contest.
    
    ### Authorization:
    - For public contests: Any authenticated user.
    - For private contests: Only registered (approved) users.
    
    ### Notes:
    - This only returns the current user's contest submissions.
    """
)
def list_my_contest_submissions(
    contest_id: int,
    problem_id: int | None = Query(default=None, description="Filter by problem ID"),
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Listing my contest submissions: contest_id={contest_id}, user={current_user.username}")
    contest_service = ContestService(db)
    return [
        SubmissionOut.model_validate(s) 
        for s in contest_service.list_my_contest_submissions(contest_id, current_user, problem_id=problem_id)
    ]


@router.get(
    "/{contest_id}/problems/{problem_id}/submissions",
    response_model=list[SubmissionOut],
    summary="List contest submissions for a specific problem (admin/owner only)",
    description="""
    List all submissions for a specific problem within a contest.
    
    ### Authorization:
    - **Admins**: Can view submissions for any contest.
    - **Owners**: Can view submissions for their own contests.
    
    ### Notes:
    - This only returns contest submissions, not individual problem submissions.
    """
)
def list_contest_problem_submissions(
    contest_id: int,
    problem_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    logger.info(f"Listing contest submissions for problem: contest_id={contest_id}, problem_id={problem_id}")
    contest_service = ContestService(db)
    return [
        SubmissionOut.model_validate(s) 
        for s in contest_service.list_contest_submissions(contest_id, current_user, problem_id=problem_id)
    ]


# ============================================================================
# Contest Manager Endpoints (Team Collaboration)
# ============================================================================

@router.post(
    "/{contest_id}/managers/{user_id}",
    response_model=ContestManagerOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a manager to a contest (admin/owner only)",
    description="""
    Add a user as a manager to a contest.
    
    ### Authorization:
    - **Admins**: Can add managers to any contest.
    - **Owners**: Can add managers to their own contests.
    
    ### Manager Permissions:
    Managers can:
    - Edit contest details
    - Add/remove problems
    - Manage registrations
    - Create/edit/delete announcements
    
    ### Notes:
    - Cannot add the contest owner as a manager (they already have full access).
    - Cannot add a user who is already a manager.
    """
)
def add_contest_manager(
    contest_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    logger.info(f"Adding manager: contest_id={contest_id}, user_id={user_id}, by={current_user.username}")
    contest_service = ContestService(db)
    return contest_service.add_contest_manager(contest_id, user_id, current_user)


@router.delete(
    "/{contest_id}/managers/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove a manager from a contest (admin/owner only)",
    description="""
    Remove a manager from a contest.
    
    ### Authorization:
    - **Admins**: Can remove managers from any contest.
    - **Owners**: Can remove managers from their own contests.
    """
)
def remove_contest_manager(
    contest_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    logger.info(f"Removing manager: contest_id={contest_id}, user_id={user_id}, by={current_user.username}")
    contest_service = ContestService(db)
    return contest_service.remove_contest_manager(contest_id, user_id, current_user)


@router.get(
    "/{contest_id}/managers",
    response_model=list[ContestManagerOut],
    summary="List contest managers",
    description="""
    List all managers for a contest.
    
    ### Authorization:
    - Any authenticated user who can view the contest can list managers.
    """
)
def list_contest_managers(
    contest_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Listing managers: contest_id={contest_id}")
    contest_service = ContestService(db)
    return contest_service.list_contest_managers(contest_id, current_user)


# ============================================================================
# Contest Ticket Endpoints (Clarification System)
# ============================================================================

@router.post(
    "/{contest_id}/tickets",
    response_model=ContestTicketOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a ticket/clarification for a contest",
    description="""
    Create a ticket/clarification for a contest problem.
    
    This feature allows contestants to ask questions about problems during a contest,
    similar to Codeforces and other competitive programming platforms.
    
    ### Authorization:
    - For public contests: Any authenticated user.
    - For private contests: Only registered (approved) users.
    
    ### Fields:
    - **title**: Ticket title (required, 1-200 characters)
    - **content**: The question/clarification (required)
    - **problem_id**: Problem ID this ticket is about (optional)
    - **is_public**: Whether this ticket is visible to all contestants (default: false)
    
    ### Ticket Status:
    - **open**: Ticket is awaiting response
    - **answered**: Ticket has been answered by staff
    - **closed**: Ticket is closed
    """
)
def create_contest_ticket(
    contest_id: int,
    ticket_create: ContestTicketCreate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Creating ticket: contest_id={contest_id}, user={current_user.username}")
    contest_service = ContestService(db)
    return contest_service.create_ticket(contest_id, ticket_create, current_user)


@router.get(
    "/{contest_id}/tickets",
    response_model=PaginatedResponse[ContestTicketSummaryOut],
    summary="List tickets for a contest",
    description="""
    List tickets/clarifications for a contest.
    
    ### Visibility:
    - Regular users see their own tickets and public tickets.
    - Managers (admin/owner/managers) see all tickets.
    
    ### Filters:
    - `status`: Filter by status (open, answered, closed)
    - `problem_id`: Filter by problem ID
    
    ### Pagination:
    - Use `page` and `page_size` query parameters.
    """
)
def list_contest_tickets(
    contest_id: int,
    status_filter: str | None = Query(default=None, alias="status", description="Filter by status: open, answered, closed"),
    problem_id: int | None = Query(default=None, description="Filter by problem ID"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Listing tickets: contest_id={contest_id}")
    contest_service = ContestService(db)
    return contest_service.list_tickets(
        contest_id, current_user, 
        status_filter=status_filter, 
        problem_id=problem_id,
        page=page, 
        page_size=page_size
    )


@router.get(
    "/tickets/my",
    response_model=PaginatedResponse[ContestTicketSummaryOut],
    summary="List my tickets across all contests",
    description="""
    List all tickets created by the current user across all contests.
    
    ### Filters:
    - `status`: Filter by status (open, answered, closed)
    """
)
def list_my_tickets(
    status_filter: str | None = Query(default=None, alias="status", description="Filter by status: open, answered, closed"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Listing my tickets: user={current_user.username}")
    contest_service = ContestService(db)
    return contest_service.list_my_tickets(
        current_user,
        status_filter=status_filter,
        page=page,
        page_size=page_size
    )


@router.get(
    "/tickets/{ticket_id}",
    response_model=ContestTicketOut,
    summary="Get a specific ticket",
    description="""
    Get a specific ticket by ID with all responses.
    
    ### Visibility:
    - Users can see their own tickets.
    - Users can see public tickets.
    - Managers can see all tickets.
    """
)
def get_contest_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Getting ticket: ticket_id={ticket_id}")
    contest_service = ContestService(db)
    return contest_service.get_ticket(ticket_id, current_user)


@router.put(
    "/tickets/{ticket_id}",
    response_model=ContestTicketOut,
    summary="Update a ticket",
    description="""
    Update a ticket's content or visibility.
    
    ### Authorization:
    - **Ticket author**: Can update title, content, and visibility.
    - **Managers**: Can only change visibility (is_public).
    """
)
def update_contest_ticket(
    ticket_id: int,
    ticket_update: ContestTicketUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Updating ticket: ticket_id={ticket_id}, user={current_user.username}")
    contest_service = ContestService(db)
    return contest_service.update_ticket(ticket_id, ticket_update, current_user)


@router.put(
    "/tickets/{ticket_id}/status",
    response_model=ContestTicketOut,
    summary="Update ticket status",
    description="""
    Update a ticket's status.
    
    ### Authorization:
    - **Managers**: Can change ticket status to any value.
    - **Ticket author**: Can only close their own tickets.
    
    ### Status Values:
    - `open`: Ticket is awaiting response
    - `answered`: Ticket has been answered by staff
    - `closed`: Ticket is closed
    """
)
def update_contest_ticket_status(
    ticket_id: int,
    status_update: ContestTicketStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Updating ticket status: ticket_id={ticket_id}, status={status_update.status}")
    contest_service = ContestService(db)
    return contest_service.update_ticket_status(ticket_id, status_update.status, current_user)


@router.delete(
    "/tickets/{ticket_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a ticket",
    description="""
    Delete a ticket.
    
    ### Authorization:
    - **Ticket author**: Can delete their own tickets.
    - **Managers**: Can delete any ticket.
    """
)
def delete_contest_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Deleting ticket: ticket_id={ticket_id}, user={current_user.username}")
    contest_service = ContestService(db)
    return contest_service.delete_ticket(ticket_id, current_user)


@router.post(
    "/tickets/{ticket_id}/responses",
    response_model=ContestTicketResponseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a response to a ticket",
    description="""
    Create a response to a ticket (managers only).
    
    ### Authorization:
    - Only contest managers (admin/owner/managers) can respond to tickets.
    
    ### Notes:
    - When a response is created, the ticket status is automatically changed to "answered".
    """
)
def create_ticket_response(
    ticket_id: int,
    response_create: ContestTicketResponseCreate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    logger.info(f"Creating ticket response: ticket_id={ticket_id}, user={current_user.username}")
    contest_service = ContestService(db)
    return contest_service.create_ticket_response(ticket_id, response_create, current_user)


@router.put(
    "/ticket-responses/{response_id}",
    response_model=ContestTicketResponseOut,
    summary="Update a ticket response",
    description="""
    Update a ticket response.
    
    ### Authorization:
    - Only the responder can update their own response.
    """
)
def update_ticket_response(
    response_id: int,
    content: str = Query(..., description="Updated response content"),
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Updating ticket response: response_id={response_id}")
    contest_service = ContestService(db)
    return contest_service.update_ticket_response(response_id, content, current_user)


@router.delete(
    "/ticket-responses/{response_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a ticket response",
    description="""
    Delete a ticket response.
    
    ### Authorization:
    - The responder can delete their own response.
    - Managers can delete any response.
    """
)
def delete_ticket_response(
    response_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Deleting ticket response: response_id={response_id}")
    contest_service = ContestService(db)
    return contest_service.delete_ticket_response(response_id, current_user)
