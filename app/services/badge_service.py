from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.badge_repository import BadgeRepository
from app.repositories.user_repository import UserRepository
from app.models.badge import Badge, UserBadge, BadgeCriteriaType
from app.models.user import User
from app.core.config import get_logger

logger = get_logger(__name__)


class BadgeService:
    def __init__(self, db: Session):
        self.badge_repo = BadgeRepository(db)
        self.user_repo = UserRepository(db)
        logger.debug("BadgeService initialized")

    # Admin Badge Management
    def create_badge(
        self,
        name: str,
        description: str,
        criteria_type: str,
        criteria_value: int,
        icon: Optional[str] = None,
        criteria_data: Optional[dict] = None,
        created_by: int = None
    ) -> Badge:
        """Create a new badge (admin only)."""
        logger.info(f"Creating badge: name='{name}', criteria={criteria_type}")
        
        # Validate criteria_type
        try:
            BadgeCriteriaType(criteria_type)
        except ValueError:
            valid_types = [t.value for t in BadgeCriteriaType]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid criteria_type. Valid types: {', '.join(valid_types)}"
            )
        
        # Check if name is unique
        existing = self.badge_repo.get_badge_by_name(name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Badge with name '{name}' already exists"
            )
        
        # Validate criteria_value
        if criteria_value <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="criteria_value must be greater than 0"
            )
        
        badge = self.badge_repo.create_badge(
            name=name,
            description=description,
            criteria_type=criteria_type,
            criteria_value=criteria_value,
            icon=icon,
            criteria_data=criteria_data,
            created_by=created_by
        )
        
        logger.info(f"Badge created: id={badge.id}, name='{badge.name}'")
        return badge

    def get_badge(self, badge_id: int) -> Badge:
        """Get a badge by ID."""
        badge = self.badge_repo.get_badge_by_id(badge_id)
        if not badge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Badge not found"
            )
        return badge

    def list_badges(
        self,
        page: int = 1,
        page_size: int = 20,
        active_only: bool = True,
        criteria_type: Optional[str] = None
    ):
        """List badges with pagination."""
        skip = (page - 1) * page_size
        badges, total = self.badge_repo.list_badges(
            skip=skip,
            limit=page_size,
            active_only=active_only,
            criteria_type=criteria_type
        )
        
        pages = (total + page_size - 1) // page_size if total > 0 else 0
        has_next = page < pages
        has_prev = page > 1
        
        return {
            "items": badges,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }

    def update_badge(
        self,
        badge_id: int,
        current_user: User,
        name: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        criteria_value: Optional[int] = None,
        is_active: Optional[bool] = None
    ) -> Badge:
        """Update a badge (admin only)."""
        logger.info(f"Updating badge {badge_id}")
        
        badge = self.get_badge(badge_id)
        
        # Check if name is being changed and is unique
        if name and name != badge.name:
            existing = self.badge_repo.get_badge_by_name(name)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Badge with name '{name}' already exists"
                )
        
        status_str = None
        if is_active is not None:
            status_str = "active" if is_active else "inactive"
        
        updated_badge = self.badge_repo.update_badge(
            badge=badge,
            name=name,
            description=description,
            icon=icon,
            criteria_value=criteria_value,
            is_active=status_str
        )
        
        logger.info(f"Badge updated: id={badge_id}")
        return updated_badge

    def delete_badge(self, badge_id: int, current_user: User):
        """Delete a badge (admin only)."""
        logger.info(f"Deleting badge {badge_id}")
        
        badge = self.get_badge(badge_id)
        self.badge_repo.delete_badge(badge)
        
        logger.info(f"Badge deleted: id={badge_id}")
        return {"message": "Badge deleted successfully"}

    # User Badge Management
    def get_user_badges(
        self,
        user_id: int,
        earned_only: bool = False,
        page: int = 1,
        page_size: int = 20
    ):
        """Get badges for a user with progress."""
        skip = (page - 1) * page_size
        user_badges, total = self.badge_repo.list_user_badges(
            user_id=user_id,
            earned_only=earned_only,
            skip=skip,
            limit=page_size
        )
        
        pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        return {
            "items": user_badges,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1
        }

    def get_user_badge_stats(self, user_id: int) -> dict:
        """Get badge statistics for a user."""
        return self.badge_repo.get_user_stats(user_id)

    def check_and_update_badges(self, user_id: int) -> List[UserBadge]:
        """Check all badges for a user and update progress/awards."""
        logger.debug(f"Checking badges for user {user_id}")
        
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get all active badges
        badges, _ = self.badge_repo.list_badges(active_only=True, limit=1000)
        
        newly_earned = []
        
        for badge in badges:
            user_badge = self.badge_repo.get_or_create_user_badge(user_id, badge.id)
            
            if user_badge.is_earned:
                continue  # Already earned
            
            # Calculate progress based on criteria type
            progress = self._calculate_progress(user, badge)
            
            # Check if earned
            earned = progress >= badge.criteria_value
            
            # Update progress
            updated_badge = self.badge_repo.update_user_badge_progress(
                user_badge,
                progress=min(progress, badge.criteria_value),
                earned=earned
            )
            
            if earned:
                newly_earned.append(updated_badge)
                logger.info(f"User {user_id} earned badge '{badge.name}'")
        
        return newly_earned

    def _calculate_progress(self, user: User, badge: Badge) -> int:
        """Calculate progress for a badge based on criteria."""
        from app.repositories.problem_repository import ProblemRepository
        from app.repositories.contest_repository import ContestRepository
        from app.models.problem import SubmissionStatus
        from datetime import datetime
        
        criteria_type = badge.criteria_type
        
        if criteria_type == BadgeCriteriaType.PROBLEMS_SOLVED.value:
            # Count unique problems solved
            problem_repo = ProblemRepository(self.badge_repo.db)
            accepted = problem_repo.get_user_accepted_submissions(user.id)
            return len(set(s.problem_id for s in accepted))
        
        elif criteria_type == BadgeCriteriaType.SUBMISSIONS_MADE.value:
            # Count total submissions
            from app.models.problem import Submission
            count = self.badge_repo.db.query(Submission).filter(
                Submission.user_id == user.id
            ).count()
            return count
        
        elif criteria_type == BadgeCriteriaType.CONTESTS_PARTICIPATED.value:
            # Count contests participated
            contest_repo = ContestRepository(self.badge_repo.db)
            from app.models.contest import ContestRegistration
            count = self.badge_repo.db.query(ContestRegistration).filter(
                ContestRegistration.user_id == user.id
            ).count()
            return count
        
        elif criteria_type == BadgeCriteriaType.STREAK_DAYS.value:
            # Get current streak
            from app.services.leaderboard_service import LeaderboardService
            leaderboard_service = LeaderboardService(self.badge_repo.db)
            try:
                streaks = leaderboard_service.get_user_streaks(user.id)
                return streaks.streak_info.current_streak
            except:
                return 0
        
        elif criteria_type == BadgeCriteriaType.FORUM_POSTS.value:
            # Count forum posts and comments
            from app.models.forum import ForumPost, ForumComment
            posts_count = self.badge_repo.db.query(ForumPost).filter(
                ForumPost.author_id == user.id
            ).count()
            comments_count = self.badge_repo.db.query(ForumComment).filter(
                ForumComment.author_id == user.id
            ).count()
            return posts_count + comments_count
        
        elif criteria_type == BadgeCriteriaType.ACCOUNT_AGE.value:
            # Days since account creation
            from app.database import SessionLocal
            account_age = (datetime.now() - user.update_time).days
            return account_age
        
        elif criteria_type == BadgeCriteriaType.PERFECT_SOLVES.value:
            # Count perfect solves (first submission accepted)
            from app.models.problem import Submission
            all_submissions = self.badge_repo.db.query(Submission).filter(
                Submission.user_id == user.id
            ).order_by(Submission.submission_time.asc()).all()
            
            perfect_count = 0
            problem_first_sub = {}
            
            for sub in all_submissions:
                if sub.problem_id not in problem_first_sub:
                    problem_first_sub[sub.problem_id] = sub
            
            for problem_id, first_sub in problem_first_sub.items():
                if first_sub.status == SubmissionStatus.ACCEPTED.value:
                    perfect_count += 1
            
            return perfect_count
        
        elif criteria_type == BadgeCriteriaType.PROBLEMS_CREATED.value:
            # For creators - count problems created
            problem_repo = ProblemRepository(self.badge_repo.db)
            problems, _ = problem_repo.list_problems_by_owner(user.id)
            return len(problems)
        
        return 0

    def initialize_user_badges(self, user_id: int):
        """Initialize badge progress for a new user."""
        logger.debug(f"Initializing badges for user {user_id}")
        
        badges, _ = self.badge_repo.list_badges(active_only=True, limit=1000)
        
        for badge in badges:
            # Create user badge entry if not exists
            self.badge_repo.get_or_create_user_badge(user_id, badge.id)
