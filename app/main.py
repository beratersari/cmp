from fastapi import FastAPI, Depends
from app.database import engine, Base, SessionLocal, run_sqlite_migrations
from app.api import auth, dependencies, problems, leaderboards, users
from app.models.user import UserRole
from app.services.user_service import UserService
from app.mock_data import seed_mock_data

# Create the database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Codeforces Clone API",
    description="""
    This API provides authentication and authorization for a Codeforces-like platform.
    
    ### Architecture:
    The project follows a **N-Layered Architecture**:
    - **API Layer**: Handles HTTP requests, input validation (Pydantic v1), and returns responses.
    - **Service Layer**: Contains business logic, manages password hashing, and JWT generation.
    - **Repository Layer**: Interacts with the database using SQLAlchemy.
    - **Models Layer**: Defines the database schema and roles (Admin, Creator, User).
    - **Core**: Contains configuration and security-related utilities.
    
    ### Roles:
    1. **Admin**: Full access to the system.
    2. **Creator**: Can create and manage problems/contests.
    3. **User**: Standard user who can participate in contests.
    
    ### Authentication:
    The system uses **JWT (JSON Web Token)** for stateless authentication.
    - Register using `/auth/register`.
    - Login using `/auth/login` to get an access token.
    - Include the token in the `Authorization` header as `Bearer <token>`.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.on_event("startup")
def startup_create_dummy_admin():
    """
    Initializes the system with required defaults and mock data.

    Steps:
    1. Runs lightweight SQLite migrations for new columns.
    2. Seeds mock data (users, problems, submissions).
    """
    run_sqlite_migrations()
    db = SessionLocal()
    try:
        seed_mock_data(db)
    finally:
        db.close()

# Include the routers
app.include_router(auth.router)
app.include_router(problems.router)
app.include_router(leaderboards.router)
app.include_router(users.router)

@app.get("/", tags=["Health Check"], summary="Check if the API is running")
def root():
    """
    Simple health check endpoint to verify that the API service is up and running.
    """
    return {"message": "Welcome to the Codeforces Clone API. Visit /docs for Swagger documentation."}

@app.get(
    "/admin-only",
    tags=["Role Testing"],
    dependencies=[Depends(dependencies.RoleChecker([UserRole.ADMIN]))],
    summary="Example endpoint accessible only to Admins",
    description="""
    This endpoint is used to test the **Role-Based Access Control (RBAC)**.
    It can only be accessed by users who have the 'admin' role.
    """
)
def admin_only():
    return {"message": "Hello Admin! You have access to this protected resource."}

@app.get(
    "/creator-only",
    tags=["Role Testing"],
    dependencies=[Depends(dependencies.RoleChecker([UserRole.ADMIN, UserRole.CREATOR]))],
    summary="Example endpoint accessible to Creators and Admins",
    description="""
    This endpoint is used to test the **Role-Based Access Control (RBAC)**.
    It can be accessed by users with either 'admin' or 'creator' roles.
    """
)
def creator_only():
    return {"message": "Hello Creator/Admin! You have access to this protected resource."}
