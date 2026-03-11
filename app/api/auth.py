from fastapi import APIRouter, Depends, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    UserCreate, UserOut, Token, LoginRequest, UserRegister, UserListOut, 
    UserActiveUpdate, PaginatedResponse, EducationCreate, EducationUpdate, EducationOut
)
from app.services.user_service import UserService
from app.api.dependencies import RoleChecker, get_current_user
from app.models.user import UserRole
from app.core.config import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={404: {"description": "Not found"}},
)

@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user to the platform",
    description="""
    This endpoint allows **anyone** to register a new **standard user** for the platform.

    ### Important Security Note:
    - The role is **not** accepted from public clients.
    - Every user created here will always be assigned the **user** role.
    - Admins and creators can only be created by an authenticated admin via `/auth/admin/create-user`.

    ### Workflow:
    1. Validates the input data using Pydantic v1.
    2. Checks if the username or email is already taken.
    3. Hashes the password using bcrypt.
    4. Persists the user in the SQLite database with role `user`.
    5. Returns the user details without the sensitive password field.
    """
)
def register(user_register: UserRegister, db: Session = Depends(get_db)):
    logger.info(f"User registration attempt: username={user_register.username}, email={user_register.email}")
    try:
        user_service = UserService(db)
        result = user_service.register_user(user_register)
        logger.info(f"User registered successfully: username={result.username}, id={result.id}")
        return result
    except Exception as e:
        logger.warning(f"User registration failed: username={user_register.username}, error={str(e)}")
        raise

@router.get(
    "/admin/users",
    response_model=PaginatedResponse[UserListOut],
    dependencies=[Depends(RoleChecker([UserRole.ADMIN]))],
    summary="List all users (admin-only)",
    description="""
    Retrieve all users in the system with pagination and search support.

    ### Authorization:
    This endpoint is restricted to **admins only**.

    ### Pagination:
    - Use `page` and `page_size` query parameters to control pagination.
    - Default: page=1, page_size=20

    ### Search:
    - Use `search` query parameter to search by username or email (case-insensitive).
    """
)
def list_users(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    search: str | None = Query(default=None, description="Search by username or email")
):
    logger.info(f"Listing users: page={page}, page_size={page_size}, search={search}")
    user_service = UserService(db)
    result = user_service.list_users(page=page, page_size=page_size, search=search)
    logger.debug(f"Listed {len(result.get('items', []))} users, total={result.get('total', 0)}")
    return result

@router.post(
    "/admin/create-user",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([UserRole.ADMIN]))],
    summary="Create a new user with admin or creator role (admin-only)",
    description="""
    This endpoint allows **authenticated admins** to create new users with any role.

    ### Why this exists:
    - Public registration should never allow creating admin or creator accounts.
    - Admins can safely provision privileged accounts via this endpoint.

    ### Workflow:
    1. Requires a valid JWT for an admin user.
    2. Validates the input data with Pydantic v1.
    3. Checks for unique username/email.
    4. Hashes the password and creates the account.
    """
)
def create_user_by_admin(user_create: UserCreate, db: Session = Depends(get_db)):
    logger.info(f"Admin creating user: username={user_create.username}, role={user_create.role}")
    try:
        user_service = UserService(db)
        result = user_service.create_user_by_admin(user_create)
        logger.info(f"User created by admin: username={result.username}, id={result.id}, role={result.role}")
        return result
    except Exception as e:
        logger.error(f"Admin user creation failed: username={user_create.username}, error={str(e)}")
        raise

@router.put(
    "/admin/users/{username}/active",
    response_model=UserOut,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RoleChecker([UserRole.ADMIN]))],
    summary="Activate or ban a user (admin-only)",
    description="""
    Toggle a user's active status. When inactive, the user cannot log in.

    ### Authorization:
    Admin only.
    """
)
def set_user_active(
    username: str,
    payload: UserActiveUpdate,
    db: Session = Depends(get_db)
):
    logger.info(f"Setting user active status: username={username}, is_active={payload.is_active}")
    user_service = UserService(db)
    result = user_service.set_user_active(username, payload.is_active, updated_by="admin")
    logger.info(f"User active status updated: username={username}, is_active={result.is_active}")
    return result

@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate user and obtain a JWT access token",
    description="""
    This endpoint allows registered users to log in by providing their credentials.
    
    ### Swagger UI Usage:
    This endpoint is compatible with the **Authorize** button in Swagger UI. 
    It accepts both `application/x-www-form-urlencoded` (used by Swagger) and `application/json`.

    ### Workflow:
    1. Receives the username and password.
    2. Validates the credentials against the database.
    3. If valid, generates a JSON Web Token (JWT) containing the user's identity and role.
    4. The token is signed with a secret key and has an expiration time (default 30 minutes).
    
    ### Usage:
    The returned `access_token` should be included in the `Authorization` header of subsequent requests as a Bearer token:
    `Authorization: Bearer <your_access_token>`
    """
)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    logger.info(f"Login attempt: username={form_data.username}")
    try:
        user_service = UserService(db)
        # Convert OAuth2PasswordRequestForm to LoginRequest for the service layer
        login_request = LoginRequest(username=form_data.username, password=form_data.password)
        result = user_service.authenticate_user(login_request)
        logger.info(f"Login successful: username={form_data.username}")
        return result
    except Exception as e:
        logger.warning(f"Login failed: username={form_data.username}, error={str(e)}")
        raise


# Education endpoints
@router.post(
    "/users/{user_id}/education",
    response_model=EducationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add education entry for a user",
    description="""
    Add a new education entry for a user.
    
    ### Authorization:
    - Users can add education entries for themselves.
    - Admins can add education entries for any user.
    """
)
def add_education(
    user_id: int,
    education_create: EducationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Adding education for user_id={user_id} by {current_user.username}")
    try:
        user_service = UserService(db)
        result = user_service.add_education(user_id, education_create, current_user)
        logger.info(f"Education added successfully: id={result.id}, user_id={user_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to add education: user_id={user_id}, error={str(e)}")
        raise

@router.put(
    "/users/education/{education_id}",
    response_model=EducationOut,
    summary="Update an education entry",
    description="""
    Update an existing education entry.
    
    ### Authorization:
    - Users can update their own education entries.
    - Admins can update any user's education entries.
    """
)
def update_education(
    education_id: int,
    education_update: EducationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Updating education: education_id={education_id} by {current_user.username}")
    try:
        user_service = UserService(db)
        result = user_service.update_education(education_id, education_update, current_user)
        logger.info(f"Education updated successfully: education_id={education_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to update education: education_id={education_id}, error={str(e)}")
        raise

@router.delete(
    "/users/education/{education_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an education entry",
    description="""
    Delete an education entry.
    
    ### Authorization:
    - Users can delete their own education entries.
    - Admins can delete any user's education entries.
    """
)
def delete_education(
    education_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Deleting education: education_id={education_id} by {current_user.username}")
    try:
        user_service = UserService(db)
        user_service.delete_education(education_id, current_user)
        logger.info(f"Education deleted successfully: education_id={education_id}")
    except Exception as e:
        logger.error(f"Failed to delete education: education_id={education_id}, error={str(e)}")
        raise
