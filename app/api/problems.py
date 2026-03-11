from typing import List
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    ProblemCreate,
    ProblemOut,
    ProblemUpdate,
    SubmissionCreate,
    SubmissionOut,
    SubmissionUpdate,
    SubmissionStatusUpdate,
    ProblemsByOwnerOut,
    CreatorProblemStatsOut,
    ProblemSubmissionStatsOut,
    TagCreate,
    TagOut,
    EditorialCreate,
    EditorialUpdate,
    EditorialOut,
    TestcaseCreate,
    TestcaseOut,
    PaginatedResponse,
    VoteCreate,
    VoteOut,
    ProblemVoteStatsOut,
    EditorialVoteStatsOut,
    CreatorVoteStatsOut,
    DiscussionCreate,
    DiscussionUpdate,
    DiscussionOut,
    DiscussionCommentCreate,
    DiscussionCommentUpdate,
    DiscussionCommentOut,
    DiscussionDetailOut,
    DiscussionTreeOut,
    BookmarkCreate,
    BookmarkOut,
)
from app.services.problem_service import ProblemService
from app.services.problem_discussion_service import ProblemDiscussionService
from app.services.bookmark_service import BookmarkService
from app.api.dependencies import RoleChecker, oauth2_scheme, get_current_user
from app.models.user import UserRole
from jose import jwt, JWTError
from app.core.security import SECRET_KEY, ALGORITHM
from app.core.config import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/problems",
    tags=["Problems"],
    responses={404: {"description": "Not found"}},
)

def get_optional_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    logger.debug("Getting optional current user from token")
    if not token:
        logger.debug("No token provided")
        return None
    try:
        user = get_current_user(token, db)
        logger.debug(f"Optional user resolved: username={user.username if user else None}")
        return user
    except Exception as e:
        logger.debug(f"Failed to resolve optional user: {str(e)}")
        return None

@router.post(
    "",
    response_model=ProblemOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new problem (admin/creator only)",
    description="""
    Create a new programming problem with full metadata and testcases.

    ### Required Fields:
    - **title**: Unique title of the problem.
    - **description**: Full problem statement.
    - **constraints**: Constraints section.
    - **testcases**: List of testcases with input/output pairs.
    - **is_published**: Defaults to False. If False, only owner/admin can see.
    - **is_public**: Defaults to True. If False, only owner/admin/allowed creators can see/edit.

    ### Authorization:
    This endpoint is restricted to **admin** and **creator** roles.
    """
)
def create_problem(
    problem_create: ProblemCreate, 
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    logger.info(f"Creating problem: title='{problem_create.title}' by {current_user.username}")
    try:
        problem_service = ProblemService(db)
        problem = problem_service.create_problem(problem_create, owner_id=current_user.id, created_by=current_user.username)
        logger.info(f"Problem created successfully: id={problem.id}, title='{problem.title}'")
        return problem
    except Exception as e:
        logger.error(f"Failed to create problem: title='{problem_create.title}', error={str(e)}")
        raise

@router.get(
    "",
    response_model=PaginatedResponse[ProblemOut],
    summary="List all problems (filtered by visibility)",
    description="""
    Retrieve problems available in the system with pagination and search support.

    ### Filtering Logic:
    - **Standard Users/Unauthenticated**: Only see **published AND public** problems.
    - **Creators**: See public published problems, **their own** problems, and problems they are **allowed to access**.
    - **Admins**: See **all** problems.

    ### Pagination:
    - Use `page` and `page_size` query parameters to control pagination.
    - Default: page=1, page_size=20

    ### Search:
    - Use `search` query parameter to search by title or description (case-insensitive).
    """
)
def list_problems(
    db: Session = Depends(get_db),
    tag: str | None = Query(default=None, description="Filter problems by tag"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    search: str | None = Query(default=None, description="Search by title or description"),
    token: str = Depends(oauth2_scheme)
):
    logger.info(f"Listing problems: page={page}, page_size={page_size}, tag={tag}, search={search}")
    # Manual check for current user because OAuth2PasswordBearer raises 401 if missing
    # We want this to be optional for listing
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
            
    problem_service = ProblemService(db)
    result = problem_service.list_problems(current_user, tag=tag, page=page, page_size=page_size, search=search)
    logger.debug(f"Listed {len(result.get('items', []))} problems, total={result.get('total', 0)}")
    return result

@router.get(
    "/grouped-by-owner",
    response_model=list[ProblemsByOwnerOut],
    summary="List problems grouped by owner (admin/creator only)",
    description="""
    Returns problems grouped by the username of the creator who owns them.

    ### Authorization:
    Only admins and creators can access this grouped listing.
    """
)
def list_problems_grouped_by_owner(
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    problem_service = ProblemService(db)
    return problem_service.group_problems_by_owner(current_user)

@router.get(
    "/stats/creators",
    response_model=list[CreatorProblemStatsOut],
    summary="Creator problem counts (admin/creator only)",
    description="""
    Returns usernames with their number of created problems, sorted by highest count first.
    """
)
def creator_problem_stats(
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    problem_service = ProblemService(db)
    return problem_service.creator_problem_stats(current_user)

@router.get(
    "/stats/submissions",
    response_model=list[ProblemSubmissionStatsOut],
    summary="Submission counts per problem (admin/creator only)",
    description="""
    Returns each problem with the total number of submissions.
    """
)
def submission_stats(
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    problem_service = ProblemService(db)
    return problem_service.problem_submission_stats(current_user)

@router.get(
    "/tags",
    response_model=PaginatedResponse[TagOut],
    summary="List all tags",
    description="""
    Retrieve all problem tags in the system with pagination and search support.

    ### Pagination:
    - Use `page` and `page_size` query parameters to control pagination.
    - Default: page=1, page_size=20

    ### Search:
    - Use `search` query parameter to search by tag name (case-insensitive).
    """
)
def list_tags(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    search: str | None = Query(default=None, description="Search by tag name")
):
    problem_service = ProblemService(db)
    return problem_service.list_tags(page=page, page_size=page_size, search=search)

@router.post(
    "/tags",
    response_model=TagOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tag (admin/creator only)",
    description="""
    Create a new tag that can be applied to problems.
    """
)
def create_tag(
    payload: TagCreate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    problem_service = ProblemService(db)
    return problem_service.create_tag(payload.name, current_user)

@router.get(
    "/bookmarks",
    response_model=dict,
    summary="List bookmarked problems",
    description="""
    Get a paginated list of the current user's bookmarked problems.
    """
)
def list_bookmarks(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    bookmark_service = BookmarkService(db)
    result = bookmark_service.list_bookmarks(current_user.id, page=page, page_size=page_size)
    result["items"] = [
        BookmarkOut(
            id=b.id,
            user_id=b.user_id,
            problem_id=b.problem_id,
            problem_title=b.problem.title if b.problem else None,
            created_at=b.created_at.isoformat() if b.created_at else None
        )
        for b in result["items"]
    ]
    return result

@router.get(
    "/{problem_id}",
    response_model=ProblemOut,
    summary="Get a specific problem by ID",
    description="""
    Fetch a specific problem by its unique ID.

    ### Visibility Rules:
    - If unpublished: Only owner/admin.
    - If private: Only owner/admin/allowed creators.
    """
)
def get_problem(
    problem_id: int, 
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    logger.info(f"Getting problem: problem_id={problem_id}")
    current_user = None
    if token:
        try:
            current_user = get_current_user(token, db)
            logger.debug(f"Authenticated user: {current_user.username}")
        except:
            logger.debug("Token validation failed")
            pass
    
    try:
        problem_service = ProblemService(db)
        problem = problem_service.get_problem(problem_id, current_user)
        logger.info(f"Problem retrieved: id={problem.id}, title='{problem.title}'")
        return problem
    except Exception as e:
        logger.warning(f"Failed to get problem: problem_id={problem_id}, error={str(e)}")
        raise

@router.put(
    "/{problem_id}",
    response_model=ProblemOut,
    summary="Update a problem (admin/owner/allowed creator)",
    description="""
    Update any field of a problem, including its testcases and visibility.

    ### Authorization:
    - **Admins**: Can update any problem.
    - **Owners**: Can update their own problems.
    - **Allowed Creators**: Can update private problems if they are in the allowed list.
    """
)
def update_problem(
    problem_id: int, 
    problem_update: ProblemUpdate, 
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    logger.info(f"Updating problem: problem_id={problem_id} by {current_user.username}")
    try:
        problem_service = ProblemService(db)
        problem = problem_service.update_problem(problem_id, problem_update, current_user)
        logger.info(f"Problem updated: id={problem.id}, title='{problem.title}'")
        return problem
    except Exception as e:
        logger.error(f"Failed to update problem: problem_id={problem_id}, error={str(e)}")
        raise

@router.post(
    "/{problem_id}/allowed-users/{username}",
    response_model=ProblemOut,
    summary="Add a creator to the allowed list (admin/owner/allowed creator)",
    description="""
    Grant another creator access to a private problem.
    """
)
def add_allowed_user(
    problem_id: int,
    username: str,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    problem_service = ProblemService(db)
    problem = problem_service.add_user_to_allowed_list(problem_id, username, current_user)
    # The model now has computed properties for tags and allowed_user_ids
    return problem

@router.delete(
    "/{problem_id}/allowed-users/{username}",
    response_model=ProblemOut,
    summary="Remove a creator from the allowed list (admin/owner/allowed creator)",
)
def remove_allowed_user(
    problem_id: int,
    username: str,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    problem_service = ProblemService(db)
    problem = problem_service.remove_user_from_allowed_list(problem_id, username, current_user)
    # The model now has computed properties for tags and allowed_user_ids
    return problem

@router.delete(
    "/{problem_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a problem (admin/owner/allowed creator)",
)
def delete_problem(
    problem_id: int, 
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    logger.info(f"Deleting problem: problem_id={problem_id} by {current_user.username}")
    try:
        problem_service = ProblemService(db)
        problem_service.delete_problem(problem_id, current_user)
        logger.info(f"Problem deleted: problem_id={problem_id}")
    except Exception as e:
        logger.error(f"Failed to delete problem: problem_id={problem_id}, error={str(e)}")
        raise

@router.post(
    "/{problem_id}/submissions",
    response_model=SubmissionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Submit code for a problem (authenticated users)",
)
def create_submission(
    problem_id: int,
    submission_create: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    problem_service = ProblemService(db)
    return problem_service.create_submission(
        problem_id,
        submission_create,
        user_id=current_user.id,
        username=current_user.username,
        current_user=current_user
    )

@router.get(
    "/{problem_id}/submissions",
    response_model=list[SubmissionOut],
    summary="List submissions for a problem (admin/creator only)",
)
def list_submissions(
    problem_id: int, 
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    problem_service = ProblemService(db)
    return problem_service.list_submissions(problem_id, current_user)

@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionOut,
    summary="Get a submission by ID",
)
def get_submission(
    submission_id: int, 
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    problem_service = ProblemService(db)
    return problem_service.get_submission(submission_id, current_user)

@router.put(
    "/submissions/{submission_id}",
    response_model=SubmissionOut,
    summary="Update a submission (admin/creator only)",
)
def update_submission(
    submission_id: int, 
    submission_update: SubmissionUpdate, 
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    problem_service = ProblemService(db)
    return problem_service.update_submission(submission_id, submission_update, current_user)

@router.put(
    "/submissions/{submission_id}/status",
    response_model=SubmissionOut,
    summary="Update submission status (admin/creator only)",
    description="""
    Update the status of a submission.

    ### Allowed Status Values:
    - PENDING
    - ACCEPTED
    - WRONG_ANSWER
    - TIME_LIMIT_EXCEEDED
    - MEMORY_LIMIT_EXCEEDED
    - SYNTAX_ERROR
    """
)
def update_submission_status(
    submission_id: int,
    status_update: SubmissionStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    problem_service = ProblemService(db)
    return problem_service.update_submission_status(submission_id, status_update, current_user)

@router.delete(
    "/submissions/{submission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a submission (admin/creator only)",
)
def delete_submission(
    submission_id: int, 
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    problem_service = ProblemService(db)
    problem_service.delete_submission(submission_id, current_user)

@router.get(
    "/{problem_id}/editorial",
    response_model=EditorialOut,
    summary="Get problem editorial",
    description="""
    Retrieve the editorial for a specific problem.
    """
)
def get_editorial(
    problem_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    current_user = None
    if token:
        try:
            current_user = get_current_user(token, db)
        except:
            pass
    problem_service = ProblemService(db)
    return problem_service.get_editorial(problem_id, current_user)

@router.post(
    "/{problem_id}/editorial",
    response_model=EditorialOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create problem editorial (admin/owner/allowed creator)",
)
def create_editorial(
    problem_id: int,
    editorial_create: EditorialCreate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    problem_service = ProblemService(db)
    return problem_service.create_editorial(problem_id, editorial_create, current_user)

@router.put(
    "/{problem_id}/editorial",
    response_model=EditorialOut,
    summary="Update problem editorial (admin/owner/allowed creator)",
)
def update_editorial(
    problem_id: int,
    editorial_update: EditorialUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    problem_service = ProblemService(db)
    return problem_service.update_editorial(problem_id, editorial_update, current_user)

@router.delete(
    "/{problem_id}/editorial",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete problem editorial (admin/owner/allowed creator)",
)
def delete_editorial(
    problem_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    problem_service = ProblemService(db)
    problem_service.delete_editorial(problem_id, current_user)


# ============================================================================
# Problem Discussion Endpoints (LeetCode-style discussion per problem)
# ============================================================================

@router.post(
    "/{problem_id}/discussions",
    response_model=DiscussionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a discussion for a problem",
    description="""
    Create a new discussion thread for a problem.

    ### Authorization:
    - Any authenticated user can create discussions for published problems.
    """
)
def create_problem_discussion(
    problem_id: int,
    discussion_create: DiscussionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Creating discussion: problem_id={problem_id}, user={current_user.username}")
    discussion_service = ProblemDiscussionService(db)
    discussion = discussion_service.create_discussion(
        problem_id=problem_id,
        title=discussion_create.title,
        content=discussion_create.content,
        author_id=current_user.id
    )
    return DiscussionOut(
        id=discussion.id,
        problem_id=discussion.problem_id,
        title=discussion.title,
        content=discussion.content,
        author_id=discussion.author_id,
        author_username=discussion.author.username if discussion.author else None,
        is_published=discussion.is_published,
        created_at=discussion.created_at.isoformat() if discussion.created_at else None,
        updated_at=discussion.updated_at.isoformat() if discussion.updated_at else None
    )


@router.get(
    "/{problem_id}/discussions",
    response_model=dict,
    summary="List discussions for a problem",
    description="""
    List discussion threads for a specific problem (paginated).

    ### Authorization:
    - Any authenticated user can view discussions.
    """
)
def list_problem_discussions(
    problem_id: int,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Listing discussions: problem_id={problem_id}, page={page}")
    discussion_service = ProblemDiscussionService(db)
    result = discussion_service.list_discussions(
        problem_id=problem_id,
        page=page,
        page_size=page_size,
        current_user=current_user
    )
    result["items"] = [
        DiscussionOut(
            id=d.id,
            problem_id=d.problem_id,
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
    response_model=DiscussionDetailOut,
    summary="Get a discussion with comments",
    description="""
    Get a specific discussion by ID along with its comments in a tree structure.
    """
)
def get_problem_discussion(
    discussion_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    discussion_service = ProblemDiscussionService(db)
    discussion = discussion_service.get_discussion(discussion_id, current_user)
    comments = discussion_service.get_comment_tree(discussion_id, current_user)

    discussion_out = DiscussionOut(
        id=discussion.id,
        problem_id=discussion.problem_id,
        title=discussion.title,
        content=discussion.content,
        author_id=discussion.author_id,
        author_username=discussion.author.username if discussion.author else None,
        is_published=discussion.is_published,
        created_at=discussion.created_at.isoformat() if discussion.created_at else None,
        updated_at=discussion.updated_at.isoformat() if discussion.updated_at else None
    )

    return DiscussionDetailOut(
        **discussion_out.model_dump(),
        comments=comments
    )


@router.put(
    "/discussions/{discussion_id}",
    response_model=DiscussionOut,
    summary="Update a discussion",
    description="""
    Update a discussion thread (author or admin only).
    """
)
def update_problem_discussion(
    discussion_id: int,
    discussion_update: DiscussionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    discussion_service = ProblemDiscussionService(db)
    discussion = discussion_service.update_discussion(
        discussion_id=discussion_id,
        title=discussion_update.title,
        content=discussion_update.content,
        current_user=current_user
    )
    return DiscussionOut(
        id=discussion.id,
        problem_id=discussion.problem_id,
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
def delete_problem_discussion(
    discussion_id: int,
    hard: bool = Query(default=False, description="Permanently delete the discussion (admin only)"),
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    discussion_service = ProblemDiscussionService(db)
    discussion_service.delete_discussion(discussion_id, current_user, hard=hard)


@router.post(
    "/discussions/{discussion_id}/comments",
    response_model=DiscussionCommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a comment in a discussion",
    description="""
    Create a comment in a discussion (or reply to another comment).
    Set `parent_id` to create a nested reply.
    """
)
def create_discussion_comment(
    discussion_id: int,
    comment_create: DiscussionCommentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    discussion_service = ProblemDiscussionService(db)
    comment = discussion_service.create_comment(
        discussion_id=discussion_id,
        content=comment_create.content,
        author_id=current_user.id,
        parent_id=comment_create.parent_id
    )
    return DiscussionCommentOut(
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
    response_model=List[DiscussionTreeOut],
    summary="Get discussion comments (tree)",
    description="""
    Get discussion comments organized in a tree structure.
    """
)
def get_discussion_comments(
    discussion_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    discussion_service = ProblemDiscussionService(db)
    return discussion_service.get_comment_tree(discussion_id, current_user)


@router.get(
    "/discussion-comments/{comment_id}",
    response_model=DiscussionCommentOut,
    summary="Get a discussion comment",
    description="Get a specific discussion comment by ID."
)
def get_discussion_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    discussion_service = ProblemDiscussionService(db)
    comment = discussion_service.get_comment(comment_id, current_user)
    return DiscussionCommentOut(
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
    response_model=DiscussionCommentOut,
    summary="Update a discussion comment",
    description="""
    Update a discussion comment (author or admin only).
    """
)
def update_discussion_comment(
    comment_id: int,
    comment_update: DiscussionCommentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    discussion_service = ProblemDiscussionService(db)
    comment = discussion_service.update_comment(
        comment_id=comment_id,
        content=comment_update.content,
        current_user=current_user
    )
    return DiscussionCommentOut(
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
def delete_discussion_comment(
    comment_id: int,
    hard: bool = Query(default=False, description="Permanently delete the comment (admin only)"),
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    discussion_service = ProblemDiscussionService(db)
    discussion_service.delete_comment(comment_id, current_user, hard=hard)


# ============================================================================
# Bookmark Endpoints
# ============================================================================

@router.post(
    "/{problem_id}/bookmarks",
    response_model=BookmarkOut,
    status_code=status.HTTP_201_CREATED,
    summary="Bookmark a problem",
    description="""
    Bookmark a problem so you can find it later.
    Each user can only bookmark a problem once.
    """
)
def add_bookmark(
    problem_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    bookmark_service = BookmarkService(db)
    bookmark = bookmark_service.add_bookmark(current_user.id, problem_id)
    return BookmarkOut(
        id=bookmark.id,
        user_id=bookmark.user_id,
        problem_id=bookmark.problem_id,
        problem_title=bookmark.problem.title if bookmark.problem else None,
        created_at=bookmark.created_at.isoformat() if bookmark.created_at else None
    )


@router.delete(
    "/{problem_id}/bookmarks",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove bookmark from a problem",
    description="Remove the current user's bookmark from a problem."
)
def remove_bookmark(
    problem_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    bookmark_service = BookmarkService(db)
    bookmark_service.remove_bookmark(current_user.id, problem_id)


@router.get(
    "/{problem_id}/bookmarks/me",
    response_model=dict,
    summary="Check if problem is bookmarked",
    description="Check if the current user has bookmarked this problem."
)
def is_problem_bookmarked(
    problem_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    bookmark_service = BookmarkService(db)
    return {
        "problem_id": problem_id,
        "bookmarked": bookmark_service.is_bookmarked(current_user.id, problem_id)
    }


@router.post(
    "/{problem_id}/testcases",
    response_model=TestcaseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new testcase to a problem (admin/owner/allowed creator)",
    description="""
    Add a new testcase to an existing problem.

    ### Authorization:
    - **Admins**: Can add testcases to any problem.
    - **Owners**: Can add testcases to their own problems.
    - **Allowed Creators**: Can add testcases to private problems if they are in the allowed list.
    """
)
def add_testcase(
    problem_id: int,
    testcase_create: TestcaseCreate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    problem_service = ProblemService(db)
    return problem_service.add_testcase(problem_id, testcase_create, current_user)

@router.delete(
    "/{problem_id}/testcases/{testcase_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a testcase from a problem (admin/owner/allowed creator)",
    description="""
    Delete a specific testcase from a problem.

    ### Authorization:
    - **Admins**: Can delete testcases from any problem.
    - **Owners**: Can delete testcases from their own problems.
    - **Allowed Creators**: Can delete testcases from private problems if they are in the allowed list.
    """
)
def delete_testcase(
    problem_id: int,
    testcase_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    problem_service = ProblemService(db)
    problem_service.delete_testcase(problem_id, testcase_id, current_user)


# Vote endpoints
@router.post(
    "/{problem_id}/vote",
    response_model=VoteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Vote on a problem (authenticated users)",
    description="""
    Cast a like or dislike vote on a problem.
    
    ### Vote Types:
    - **like**: Upvote the problem
    - **dislike**: Downvote the problem
    
    ### Notes:
    - Users can only vote once per problem. Subsequent votes update the existing vote.
    - Cannot vote on unpublished problems.
    """
)
def vote_problem(
    problem_id: int,
    vote_create: VoteCreate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Voting on problem: problem_id={problem_id}, vote_type={vote_create.vote_type}, user={current_user.username}")
    try:
        problem_service = ProblemService(db)
        result = problem_service.vote_problem(problem_id, vote_create, current_user.id)
        logger.info(f"Vote recorded: problem_id={problem_id}, vote_id={result.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to vote on problem: problem_id={problem_id}, error={str(e)}")
        raise


@router.delete(
    "/{problem_id}/vote",
    status_code=status.HTTP_200_OK,
    summary="Remove vote from a problem (authenticated users)",
    description="""
    Remove the current user's vote from a problem.
    """
)
def delete_problem_vote(
    problem_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    problem_service = ProblemService(db)
    return problem_service.delete_problem_vote(problem_id, current_user.id)


@router.get(
    "/{problem_id}/stats",
    response_model=ProblemVoteStatsOut,
    summary="Get vote statistics for a problem",
    description="""
    Retrieve the vote statistics (likes, dislikes, like rate) for a specific problem.
    """
)
def get_problem_vote_stats(
    problem_id: int,
    db: Session = Depends(get_db)
):
    logger.debug(f"Getting vote stats for problem: problem_id={problem_id}")
    problem_service = ProblemService(db)
    result = problem_service.get_problem_vote_stats(problem_id)
    logger.debug(f"Vote stats retrieved: problem_id={problem_id}, likes={result.votes.likes}, dislikes={result.votes.dislikes}")
    return result


@router.post(
    "/{problem_id}/editorial/vote",
    response_model=VoteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Vote on a problem's editorial (authenticated users)",
    description="""
    Cast a like or dislike vote on a problem's editorial.
    
    ### Vote Types:
    - **like**: Upvote the editorial
    - **dislike**: Downvote the editorial
    
    ### Notes:
    - Users can only vote once per editorial. Subsequent votes update the existing vote.
    - Cannot vote on editorials for unpublished problems.
    """
)
def vote_editorial(
    problem_id: int,
    vote_create: VoteCreate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    problem_service = ProblemService(db)
    return problem_service.vote_editorial(problem_id, vote_create, current_user.id)


@router.delete(
    "/{problem_id}/editorial/vote",
    status_code=status.HTTP_200_OK,
    summary="Remove vote from a problem's editorial (authenticated users)",
    description="""
    Remove the current user's vote from a problem's editorial.
    """
)
def delete_editorial_vote(
    problem_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    problem_service = ProblemService(db)
    return problem_service.delete_editorial_vote(problem_id, current_user.id)


@router.get(
    "/{problem_id}/editorial/stats",
    response_model=EditorialVoteStatsOut,
    summary="Get vote statistics for a problem's editorial",
    description="""
    Retrieve the vote statistics (likes, dislikes, like rate) for a problem's editorial.
    """
)
def get_editorial_vote_stats(
    problem_id: int,
    db: Session = Depends(get_db)
):
    problem_service = ProblemService(db)
    return problem_service.get_editorial_vote_stats(problem_id)


@router.get(
    "/stats/votes/by-creator",
    response_model=list[CreatorVoteStatsOut],
    summary="Get vote statistics grouped by creator (admin/creator only)",
    description="""
    Retrieve vote statistics for all problems grouped by their creators.
    
    ### Response:
    - Shows each creator with their total problems, likes, dislikes, and overall like rate
    - Includes per-problem vote statistics
    - Sorted by overall like rate (descending), then by total likes
    
    ### Authorization:
    Only admins and creators can access this endpoint.
    """
)
def get_creator_vote_stats(
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))
):
    logger.info(f"Getting creator vote stats by {current_user.username}")
    problem_service = ProblemService(db)
    result = problem_service.get_creator_vote_stats(current_user)
    logger.info(f"Creator vote stats retrieved: {len(result)} creators")
    return result
