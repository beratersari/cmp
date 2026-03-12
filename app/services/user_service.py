from sqlalchemy.orm import Session
from typing import Optional
from fastapi import HTTPException, status
from app.repositories.user_repository import UserRepository
from app.schemas import UserCreate, LoginRequest, Token, UserRegister, EducationCreate, EducationUpdate, UserSummaryOut
from app.core.security import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import timedelta
from app.models.user import UserRole
from app.core.config import get_logger

logger = get_logger(__name__)

class UserService:
    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)
        logger.debug("UserService initialized")

    def list_users(self, page: int = 1, page_size: int = 20, search: Optional[str] = None):
        skip = (page - 1) * page_size
        users, total = self.user_repo.list_users(skip=skip, limit=page_size, search=search)

        for user in users:
            user.followers_count = len([u for u in user.followers if u.is_active])
            user.following_count = len([u for u in user.following if u.is_active])

        # Calculate pagination info
        pages = (total + page_size - 1) // page_size
        has_next = page < pages
        has_prev = page > 1
        
        return {
            "items": users,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }

    def register_user(self, user_register: UserRegister):
        logger.debug(f"Registering user: username={user_register.username}")
        # Business logic: Check if user or email already exists
        if self.user_repo.get_user_by_username(user_register.username):
            logger.warning(f"Username already registered: {user_register.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        if self.user_repo.get_user_by_email(user_register.email):
            logger.warning(f"Email already registered: {user_register.email}")
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
        user = self.user_repo.create_user(
            user_create, 
            hashed_password, 
            created_by=user_register.username,
            educations=user_register.educations
        )
        user.followers_count = 0
        user.following_count = 0
        logger.debug(f"User registered: id={user.id}, username={user.username}")
        return user

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
        user = self.user_repo.create_user(
            user_create, 
            hashed_password, 
            created_by="admin",
            educations=user_create.educations
        )
        user.followers_count = 0
        user.following_count = 0
        return user

    def add_education(self, user_id: int, education_create: EducationCreate, current_user):
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        # Check permission: only admin or the user themselves can add education
        if current_user.role != UserRole.ADMIN and current_user.id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to add education for this user")
        
        return self.user_repo.add_education(user, education_create)

    def update_education(self, education_id: int, education_update: EducationUpdate, current_user):
        education = self.user_repo.get_education_by_id(education_id)
        if not education:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Education entry not found")
        
        # Check permission: only admin or the user themselves can update education
        if current_user.role != UserRole.ADMIN and current_user.id != education.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this education entry")
        
        return self.user_repo.update_education(education, education_update)

    def delete_education(self, education_id: int, current_user):
        education = self.user_repo.get_education_by_id(education_id)
        if not education:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Education entry not found")
        
        # Check permission: only admin or the user themselves can delete education
        if current_user.role != UserRole.ADMIN and current_user.id != education.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this education entry")
        
        self.user_repo.delete_education(education)

    def authenticate_user(self, login_request: LoginRequest):
        logger.debug(f"Authenticating user: {login_request.username}")
        user = self.user_repo.get_user_by_username(login_request.username)
        if not user or not verify_password(login_request.password, user.hashed_password):
            logger.warning(f"Authentication failed for user: {login_request.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            logger.warning(f"Authentication failed - inactive account: {login_request.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username, "role": user.role},
            expires_delta=access_token_expires
        )
        logger.debug(f"Authentication successful: {login_request.username}, role={user.role}")
        return Token(access_token=access_token, token_type="bearer")

    def get_follow_stats(self, user, current_user):
        if current_user.role != UserRole.ADMIN and current_user.id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view follow stats")

        active_following = [u for u in user.following if u.is_active]
        active_followers = [u for u in user.followers if u.is_active]
        following = [UserSummaryOut.model_validate(u) for u in active_following]
        return {
            "user_id": user.id,
            "username": user.username,
            "followers_count": len(active_followers),
            "following_count": len(active_following),
            "following": following
        }

    def get_followers(self, user_id: int, current_user):
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view followers")

        active_followers = [u for u in user.followers if u.is_active]
        followers = [UserSummaryOut.model_validate(u) for u in active_followers]
        return {
            "user_id": user.id,
            "username": user.username,
            "followers": followers
        }

    def follow_user(self, follower, target_user_id: int, current_user):
        if current_user.id != follower.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to follow for this user")

        if follower.id == target_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Users cannot follow themselves")

        target = self.user_repo.get_user_by_id(target_user_id)
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")

        if not target.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot follow inactive users")

        self.user_repo.follow_user(follower, target)
        return self.get_follow_stats(follower, current_user)

    def unfollow_user(self, follower, target_user_id: int, current_user):
        if current_user.id != follower.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to unfollow for this user")

        if follower.id == target_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Users cannot unfollow themselves")

        target = self.user_repo.get_user_by_id(target_user_id)
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")

        self.user_repo.unfollow_user(follower, target)
        return self.get_follow_stats(follower, current_user)

    def set_user_active(self, username: str, is_active: bool, updated_by: str):
        user = self.user_repo.get_user_by_username(username)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return self.user_repo.set_user_active(user, is_active, updated_by=updated_by)

    def ensure_dummy_admin(self, username: str, email: str, password: str):
        existing_admin = self.user_repo.get_user_by_username(username)
        if existing_admin:
            # Update the password in case it changed
            hashed_password = get_password_hash(password)
            existing_admin.hashed_password = hashed_password
            existing_admin.email = email  # Also update email in case it changed
            self.user_repo.db.commit()
            self.user_repo.db.refresh(existing_admin)
            return existing_admin
        dummy_admin = UserCreate(
            username=username,
            email=email,
            role=UserRole.ADMIN,
            password=password
        )
        hashed_password = get_password_hash(password)
        return self.user_repo.create_user(dummy_admin, hashed_password, created_by=username)
