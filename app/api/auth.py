from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import UserCreate, UserOut, Token, LoginRequest, UserRegister, UserListOut, UserActiveUpdate
from app.services.user_service import UserService
from app.api.dependencies import RoleChecker
from app.models.user import UserRole

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
    user_service = UserService(db)
    return user_service.register_user(user_register)

@router.get(
    "/admin/users",
    response_model=list[UserListOut],
    dependencies=[Depends(RoleChecker([UserRole.ADMIN]))],
    summary="List all users (admin-only)",
    description="""
    Retrieve all users in the system.

    ### Authorization:
    This endpoint is restricted to **admins only**.
    """
)
def list_users(db: Session = Depends(get_db)):
    user_service = UserService(db)
    return user_service.list_users()

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
    user_service = UserService(db)
    return user_service.create_user_by_admin(user_create)

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
    user_service = UserService(db)
    return user_service.set_user_active(username, payload.is_active, updated_by="admin")

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
    user_service = UserService(db)
    # Convert OAuth2PasswordRequestForm to LoginRequest for the service layer
    login_request = LoginRequest(username=form_data.username, password=form_data.password)
    return user_service.authenticate_user(login_request)
