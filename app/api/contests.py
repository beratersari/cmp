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
    ContestRegistrationCreate,
    ContestRegistrationOut,
    ContestRegistrationUpdate,
    ContestRegistrationSummaryOut,
    UserRegistrationOut,
    ContestAnnouncementCreate,
    ContestAnnouncementUpdate,
    ContestAnnouncementOut,
    SubmissionOut,
    ContestUserSubmissionsGroupedOut,
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
        author_username=getattr(discussion.author, 'username', None) if discussion.author else None,
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
        author_username=getattr(discussion.author, 'username', None) if discussion.author else None,
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
        author_username=getattr(discussion.author, 'username', None) if discussion.author else None,
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
    Register the current user or team for a contest.

    ### Registration Flow:
    - User registers for a contest with "pending" status.
    - For private contests, the owner/admin must approve the registration.
    - Once approved, the user can see problems in private contests.
    - For team contests, provide `team_id` to register as a team.
    - For individual contests, omit `team_id` or set to null.

    ### Authorization:
    - Any authenticated user can register for public/private contests.
    - Only team leaders can register their team for contests.

    ### Validations:
    - Cannot register team for individual-only contests
    - Cannot register as individual for team-only contests
    - Team size must not exceed contest limit
    """
)
def register_for_contest(
    contest_id: int,
    registration_data: ContestRegistrationCreate = None,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    team_id = registration_data.team_id if registration_data else None
    logger.info(f"User {current_user.username} registering for contest {contest_id}, team_id={team_id}")
    contest_service = ContestService(db)
    return contest_service.register_for_contest(contest_id, current_user, team_id)


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
# Contest Submissions Endpoints
# ============================================================================

@router.get(
    "/{contest_id}/submissions",
    response_model=PaginatedResponse[SubmissionOut],
    summary="Get contest submissions (filtered by user)",
    description="""
    Get all submissions for a contest, optionally filtered by username.

    ### Filters:
    - `username`: Filter submissions by a specific user (optional).
    - If no username is provided, returns all submissions for the contest.

    ### Pagination:
    - Use `page` and `page_size` query parameters to control pagination.
    - Default: page=1, page_size=20

    ### Authorization:
    - Any authenticated user can view submissions.
    - For ongoing contests, users can only see their own submissions.
    - Admins and contest owners can see all submissions.
    """
)
def get_contest_submissions(
    contest_id: int,
    username: str | None = Query(default=None, description="Filter by username"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Getting submissions for contest {contest_id}, username={username}")
    contest_service = ContestService(db)
    return contest_service.get_contest_submissions(
        contest_id=contest_id,
        current_user=current_user,
        username=username,
        page=page,
        page_size=page_size
    )


@router.get(
    "/{contest_id}/submissions/grouped",
    response_model=ContestUserSubmissionsGroupedOut,
    summary="Get user submissions grouped by problem",
    description="""
    Get all submissions for a specific user in a contest, grouped by problem.
    
    This endpoint returns submissions organized by problem, making it easy to see:
    - All submissions made for each problem
    - Whether the problem was solved (accepted)
    - When the first accepted submission was made
    - Number of incorrect submissions before the first accepted
    
    ### Required Parameters:
    - `contest_id`: The ID of the contest
    - `username`: The username to filter submissions by (query parameter)
    
    ### Authorization:
    - Users can only view their own submissions
    - Admins and contest owners can view any user's submissions
    """
)
def get_contest_submissions_grouped(
    contest_id: int,
    username: str = Query(..., description="Username to get submissions for"),
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Getting grouped submissions for contest {contest_id}, username={username}")
    contest_service = ContestService(db)
    return contest_service.get_contest_submissions_grouped_by_problem(
        contest_id=contest_id,
        username=username,
        current_user=current_user
    )
