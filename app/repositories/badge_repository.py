from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from app.models.badge import Badge, UserBadge, BadgeCriteriaType
from app.core.config import get_logger

logger = get_logger(__name__)


class BadgeRepository:
    def __init__(self, db: Session):
        self.db = db
        logger.debug("BadgeRepository initialized")

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
        """Create a new badge."""
        logger.debug(f"Creating badge: name='{name}', criteria={criteria_type}")
        
        badge = Badge(
            name=name,
            description=description,
            criteria_type=criteria_type,
            criteria_value=criteria_value,
            icon=icon,
            criteria_data=criteria_data or {},
            created_by=created_by,
            is_active="active"
        )
        self.db.add(badge)
        self.db.commit()
        self.db.refresh(badge)
        logger.debug(f"Badge created: id={badge.id}, name='{badge.name}'")
        return badge

    def get_badge_by_id(self, badge_id: int) -> Optional[Badge]:
        """Get badge by ID."""
        return self.db.query(Badge).filter(Badge.id == badge_id).first()

    def get_badge_by_name(self, name: str) -> Optional[Badge]:
        """Get badge by name."""
        return self.db.query(Badge).filter(Badge.name == name).first()

    def list_badges(
        self,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
        criteria_type: Optional[str] = None
    ):
        """List badges with optional filtering."""
        query = self.db.query(Badge)
        
        if active_only:
            query = query.filter(Badge.is_active == "active")
        
        if criteria_type:
            query = query.filter(Badge.criteria_type == criteria_type)
        
        total = query.count()
        badges = query.order_by(Badge.created_at.desc()).offset(skip).limit(limit).all()
        return badges, total

    def update_badge(
        self,
        badge: Badge,
        name: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        criteria_value: Optional[int] = None,
        is_active: Optional[str] = None
    ) -> Badge:
        """Update a badge."""
        if name is not None:
            badge.name = name
        if description is not None:
            badge.description = description
        if icon is not None:
            badge.icon = icon
        if criteria_value is not None:
            badge.criteria_value = criteria_value
        if is_active is not None:
            badge.is_active = is_active
        
        self.db.commit()
        self.db.refresh(badge)
        logger.debug(f"Badge updated: id={badge.id}")
        return badge

    def delete_badge(self, badge: Badge):
        """Delete a badge."""
        self.db.delete(badge)
        self.db.commit()
        logger.debug(f"Badge deleted: id={badge.id}")

    # User Badge Methods
    def get_user_badge(self, user_id: int, badge_id: int) -> Optional[UserBadge]:
        """Get a specific user badge."""
        return self.db.query(UserBadge).filter(
            and_(
                UserBadge.user_id == user_id,
                UserBadge.badge_id == badge_id
            )
        ).first()

    def get_or_create_user_badge(self, user_id: int, badge_id: int) -> UserBadge:
        """Get existing user badge or create new one."""
        user_badge = self.get_user_badge(user_id, badge_id)
        if not user_badge:
            user_badge = UserBadge(
                user_id=user_id,
                badge_id=badge_id,
                progress=0
            )
            self.db.add(user_badge)
            self.db.commit()
            self.db.refresh(user_badge)
        return user_badge

    def update_user_badge_progress(
        self,
        user_badge: UserBadge,
        progress: int,
        earned: bool = False
    ) -> UserBadge:
        """Update user badge progress."""
        from datetime import datetime
        
        user_badge.progress = progress
        if earned and not user_badge.earned_at:
            user_badge.earned_at = datetime.now()
        
        self.db.commit()
        self.db.refresh(user_badge)
        return user_badge

    def list_user_badges(
        self,
        user_id: int,
        earned_only: bool = False,
        skip: int = 0,
        limit: int = 100
    ):
        """List badges for a user."""
        query = self.db.query(UserBadge).filter(UserBadge.user_id == user_id)
        
        if earned_only:
            query = query.filter(UserBadge.earned_at.isnot(None))
        
        total = query.count()
        user_badges = query.order_by(UserBadge.earned_at.desc()).offset(skip).limit(limit).all()
        return user_badges, total

    def get_user_stats(self, user_id: int) -> dict:
        """Get badge statistics for a user."""
        total_badges = self.db.query(Badge).filter(Badge.is_active == "active").count()
        
        earned_badges = self.db.query(UserBadge).filter(
            and_(
                UserBadge.user_id == user_id,
                UserBadge.earned_at.isnot(None)
            )
        ).count()
        
        in_progress = self.db.query(UserBadge).filter(
            and_(
                UserBadge.user_id == user_id,
                UserBadge.earned_at.is_(None),
                UserBadge.progress > 0
            )
        ).count()
        
        return {
            "total_badges": total_badges,
            "earned_badges": earned_badges,
            "in_progress": in_progress,
            "completion_percentage": round((earned_badges / total_badges * 100), 2) if total_badges > 0 else 0
        }
