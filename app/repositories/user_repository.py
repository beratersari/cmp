from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas import UserCreate

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_username(self, username: str):
        return self.db.query(User).filter(User.username == username).first()

    def get_user_by_email(self, email: str):
        return self.db.query(User).filter(User.email == email).first()

    def create_user(self, user_create: UserCreate, hashed_password: str, created_by: str = None):
        db_user = User(
            username=user_create.username,
            email=user_create.email,
            hashed_password=hashed_password,
            role=user_create.role,
            created_by=created_by,
            updated_by=created_by
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def list_users(self):
        return self.db.query(User).all()

    def set_user_active(self, user: User, is_active: bool, updated_by: str):
        user.is_active = is_active
        user.updated_by = updated_by
        self.db.commit()
        self.db.refresh(user)
        return user
