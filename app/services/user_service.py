from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.repositories.user_repository import UserRepository
from app.schemas import UserCreate, LoginRequest, Token, UserRegister
from app.core.security import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import timedelta
from app.models.user import UserRole

class UserService:
    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)

    def list_users(self):
        return self.user_repo.list_users()

    def register_user(self, user_register: UserRegister):
        # Business logic: Check if user or email already exists
        if self.user_repo.get_user_by_username(user_register.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        if self.user_repo.get_user_by_email(user_register.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        hashed_password = get_password_hash(user_register.password)
        user_create = UserCreate(
            username=user_register.username,
            email=user_register.email,
            role=UserRole.USER,
            password=user_register.password
        )
        return self.user_repo.create_user(user_create, hashed_password, created_by=user_register.username)

    def create_user_by_admin(self, user_create: UserCreate):
        if self.user_repo.get_user_by_username(user_create.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        if self.user_repo.get_user_by_email(user_create.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        hashed_password = get_password_hash(user_create.password)
        return self.user_repo.create_user(user_create, hashed_password, created_by="admin")

    def authenticate_user(self, login_request: LoginRequest):
        user = self.user_repo.get_user_by_username(login_request.username)
        if not user or not verify_password(login_request.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username, "role": user.role},
            expires_delta=access_token_expires
        )
        return Token(access_token=access_token, token_type="bearer")

    def set_user_active(self, username: str, is_active: bool, updated_by: str):
        user = self.user_repo.get_user_by_username(username)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return self.user_repo.set_user_active(user, is_active, updated_by=updated_by)

    def ensure_dummy_admin(self, username: str, email: str, password: str):
        existing_admin = self.user_repo.get_user_by_username(username)
        if existing_admin:
            return existing_admin
        dummy_admin = UserCreate(
            username=username,
            email=email,
            role=UserRole.ADMIN,
            password=password
        )
        hashed_password = get_password_hash(password)
        return self.user_repo.create_user(dummy_admin, hashed_password, created_by=username)
