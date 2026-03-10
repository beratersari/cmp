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
)
from app.services.problem_service import ProblemService
from app.api.dependencies import RoleChecker, oauth2_scheme, get_current_user
from app.models.user import UserRole
from jose import jwt, JWTError
from app.core.security import SECRET_KEY, ALGORITHM

router = APIRouter(
    prefix="/problems",
    tags=["Problems"],
    responses={404: {"description": "Not found"}},
)

def get_optional_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    if not token:
        return None
    try:
        return get_current_user(token, db)
    except:
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
    problem_service = ProblemService(db)
    problem = problem_service.create_problem(problem_create, owner_id=current_user.id, created_by=current_user.username)
    # The model now has computed properties for tags and allowed_user_ids
    return problem

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
    # Manual check for current user because OAuth2PasswordBearer raises 401 if missing
    # We want this to be optional for listing
    current_user = None
    if token:
        try:
            current_user = get_current_user(token, db)
        except:
            pass
            
    problem_service = ProblemService(db)
    result = problem_service.list_problems(current_user, tag=tag, page=page, page_size=page_size, search=search)
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
    current_user = None
    if token:
        try:
            current_user = get_current_user(token, db)
        except:
            pass
            
    problem_service = ProblemService(db)
    problem = problem_service.get_problem(problem_id, current_user)
    # The model now has computed properties for tags and allowed_user_ids
    return problem

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
    problem_service = ProblemService(db)
    problem = problem_service.update_problem(problem_id, problem_update, current_user)
    # The model now has computed properties for tags and allowed_user_ids
    return problem

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
    problem_service = ProblemService(db)
    problem_service.delete_problem(problem_id, current_user)

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
