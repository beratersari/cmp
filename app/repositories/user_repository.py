from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from app.models.user import User, Education
from app.schemas import UserCreate, EducationCreate

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_username(self, username: str):
        return self.db.query(User).options(joinedload(User.educations)).filter(User.username == username).first()

    def get_user_by_email(self, email: str):
        return self.db.query(User).options(joinedload(User.educations)).filter(User.email == email).first()

    def get_user_by_id(self, user_id: int):
        return self.db.query(User).options(joinedload(User.educations)).filter(User.id == user_id).first()

    def create_user(self, user_create: UserCreate, hashed_password: str, created_by: str = None, educations: Optional[List[EducationCreate]] = None):
        db_user = User(
            username=user_create.username,
            email=user_create.email,
            hashed_password=hashed_password,
            role=user_create.role,
            created_by=created_by,
            updated_by=created_by
        )
        self.db.add(db_user)
        self.db.flush()  # Flush to get the user ID

        # Add educations if provided
        if educations:
            for edu in educations:
                db_education = Education(
                    user_id=db_user.id,
                    institution=edu.institution,
                    degree=edu.degree,
                    field_of_study=edu.field_of_study,
                    start_year=edu.start_year,
                    end_year=edu.end_year,
                    description=edu.description
                )
                self.db.add(db_education)

        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def add_education(self, user: User, education_create: EducationCreate):
        db_education = Education(
            user_id=user.id,
            institution=education_create.institution,
            degree=education_create.degree,
            field_of_study=education_create.field_of_study,
            start_year=education_create.start_year,
            end_year=education_create.end_year,
            description=education_create.description
        )
        self.db.add(db_education)
        self.db.commit()
        self.db.refresh(db_education)
        return db_education

    def get_education_by_id(self, education_id: int):
        return self.db.query(Education).filter(Education.id == education_id).first()

    def update_education(self, education: Education, education_update):
        if education_update.institution is not None:
            education.institution = education_update.institution
        if education_update.degree is not None:
            education.degree = education_update.degree
        if education_update.field_of_study is not None:
            education.field_of_study = education_update.field_of_study
        if education_update.start_year is not None:
            education.start_year = education_update.start_year
        if education_update.end_year is not None:
            education.end_year = education_update.end_year
        if education_update.description is not None:
            education.description = education_update.description
        self.db.commit()
        self.db.refresh(education)
        return education

    def delete_education(self, education: Education):
        self.db.delete(education)
        self.db.commit()

    def list_users(self, skip: int = 0, limit: int = 100, search: Optional[str] = None):
        query = self.db.query(User)
        if search:
            query = query.filter(
                (User.username.ilike(f"%{search}%")) |
                (User.email.ilike(f"%{search}%"))
            )
        total = query.count()
        users = query.offset(skip).limit(limit).all()
        return users, total

    def follow_user(self, follower: User, followed: User):
        if followed not in follower.following:
            follower.following.append(followed)
            self.db.commit()
            self.db.refresh(follower)
        return follower

    def unfollow_user(self, follower: User, followed: User):
        if followed in follower.following:
            follower.following.remove(followed)
            self.db.commit()
            self.db.refresh(follower)
        return follower

    def set_user_active(self, user: User, is_active: bool, updated_by: str):
        user.is_active = is_active
        user.updated_by = updated_by
        self.db.commit()
        self.db.refresh(user)
        return user
