from typing import Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.badge_service import BadgeService
from app.api.dependencies import RoleChecker, get_current_user
from app.models.user import UserRole
from app.core.config import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/badges",
    tags=["Badges"],
    responses={404: {"description": "Not found"}},
)


# ============================================================================
# Admin Badge Management Endpoints
# ============================================================================

@router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new badge (admin only)",
    description="""
    Create a new achievement badge.
    
    ### Required Fields:
    - **name**: Unique badge name
    - **description**: Badge description
    - **criteria_type**: Type of achievement (problems_solved, contests_participated, etc.)
    - **criteria_value**: Target value to achieve
    
    ### Optional Fields:
    - **icon**: URL or emoji for the badge
    - **criteria_data**: Additional configuration
    
    ### Criteria Types:
    - `problems_solved`: Total problems solved
    - `contests_participated`: Number of contests joined
    - `streak_days`: Current/max streak days
    - `submissions_made`: Total submissions
    - `perfect_solves`: Solved on first try
    - `contests_won`: Won contests (rank 1)
    - `problems_created`: For creators
    - `forum_posts`: Active forum participant
    - `account_age`: Days since registration
    """
)
def create_badge(
    name: str,
    description: str,
    criteria_type: str,
    criteria_value: int,
    icon: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN]))
):
    logger.info(f"Admin {current_user.username} creating badge: {name}")
    badge_service = BadgeService(db)
    badge = badge_service.create_badge(
        name=name,
        description=description,
        criteria_type=criteria_type,
        criteria_value=criteria_value,
        icon=icon,
        created_by=current_user.id
    )
    return {
        "id": badge.id,
        "name": badge.name,
        "description": badge.description,
        "criteria_type": badge.criteria_type,
        "criteria_value": badge.criteria_value,
        "icon": badge.icon,
        "created_at": badge.created_at,
        "message": "Badge created successfully"
    }


@router.get(
    "",
    response_model=dict,
    summary="List all badges",
    description="""
    List all badges with pagination and filtering.
    
    ### Filters:
    - `active_only`: Show only active badges (default: true)
    - `criteria_type`: Filter by criteria type
    
    ### Pagination:
    - Use `page` and `page_size` query parameters
    """
)
def list_badges(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    active_only: bool = Query(default=True, description="Show only active badges"),
    criteria_type: Optional[str] = Query(default=None, description="Filter by criteria type"),
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Listing badges: page={page}, active_only={active_only}")
    badge_service = BadgeService(db)
    result = badge_service.list_badges(
        page=page,
        page_size=page_size,
        active_only=active_only,
        criteria_type=criteria_type
    )
    
    # Convert to response format
    result["items"] = [
        {
            "id": b.id,
            "name": b.name,
            "description": b.description,
            "criteria_type": b.criteria_type,
            "criteria_value": b.criteria_value,
            "icon": b.icon,
            "is_active": b.is_active,
            "created_at": b.created_at
        }
        for b in result["items"]
    ]
    
    return result


@router.get(
    "/{badge_id}",
    response_model=dict,
    summary="Get badge details",
    description="Get detailed information about a badge."
)
def get_badge(
    badge_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Getting badge: badge_id={badge_id}")
    badge_service = BadgeService(db)
    badge = badge_service.get_badge(badge_id)
    
    return {
        "id": badge.id,
        "name": badge.name,
        "description": badge.description,
        "criteria_type": badge.criteria_type,
        "criteria_value": badge.criteria_value,
        "icon": badge.icon,
        "is_active": badge.is_active,
        "created_at": badge.created_at,
        "created_by": badge.created_by
    }


@router.put(
    "/{badge_id}",
    response_model=dict,
    summary="Update a badge (admin only)",
    description="""
    Update badge information.
    
    ### Authorization:
    - Only admins can update badges
    """
)
def update_badge(
    badge_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    icon: Optional[str] = None,
    criteria_value: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN]))
):
    logger.info(f"Admin {current_user.username} updating badge {badge_id}")
    badge_service = BadgeService(db)
    badge = badge_service.update_badge(
        badge_id=badge_id,
        current_user=current_user,
        name=name,
        description=description,
        icon=icon,
        criteria_value=criteria_value,
        is_active=is_active
    )
    
    return {
        "id": badge.id,
        "name": badge.name,
        "description": badge.description,
        "criteria_type": badge.criteria_type,
        "criteria_value": badge.criteria_value,
        "icon": badge.icon,
        "is_active": badge.is_active,
        "message": "Badge updated successfully"
    }


@router.delete(
    "/{badge_id}",
    response_model=dict,
    summary="Delete a badge (admin only)",
    description="""
    Delete a badge permanently.
    
    ### Authorization:
    - Only admins can delete badges
    """
)
def delete_badge(
    badge_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN]))
):
    logger.info(f"Admin {current_user.username} deleting badge {badge_id}")
    badge_service = BadgeService(db)
    result = badge_service.delete_badge(badge_id, current_user)
    return result


# ============================================================================
# User Badge Endpoints
# ============================================================================

@router.get(
    "/my/badges",
    response_model=dict,
    summary="Get my badges with progress",
    description="""
    Get all badges for the current user with progress information.
    
    ### Filters:
    - `earned_only`: Show only earned badges
    
    ### Pagination:
    - Use `page` and `page_size` query parameters
    """
)
def get_my_badges(
    earned_only: bool = Query(default=False, description="Show only earned badges"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Getting badges for user {current_user.username}, earned_only={earned_only}")
    badge_service = BadgeService(db)
    
    # First check and update badges
    badge_service.check_and_update_badges(current_user.id)
    
    # Then get user badges
    result = badge_service.get_user_badges(
        user_id=current_user.id,
        earned_only=earned_only,
        page=page,
        page_size=page_size
    )
    
    # Convert to response format
    result["items"] = [
        {
            "id": ub.id,
            "badge_id": ub.badge_id,
            "badge_name": ub.badge.name if ub.badge else None,
            "badge_description": ub.badge.description if ub.badge else None,
            "badge_icon": ub.badge.icon if ub.badge else None,
            "criteria_type": ub.badge.criteria_type if ub.badge else None,
            "criteria_value": ub.badge.criteria_value if ub.badge else None,
            "progress": ub.progress,
            "progress_percentage": ub.progress_percentage,
            "is_earned": ub.is_earned,
            "earned_at": ub.earned_at,
            "created_at": ub.created_at
        }
        for ub in result["items"]
    ]
    
    return result


@router.get(
    "/my/stats",
    response_model=dict,
    summary="Get my badge statistics",
    description="Get badge statistics for the current user."
)
def get_my_badge_stats(
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Getting badge stats for user {current_user.username}")
    badge_service = BadgeService(db)
    
    # First check and update badges
    badge_service.check_and_update_badges(current_user.id)
    
    stats = badge_service.get_user_badge_stats(current_user.id)
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "stats": stats
    }


@router.post(
    "/my/check",
    response_model=dict,
    summary="Check and update my badges",
    description="""
    Manually trigger badge progress check and update.
    This will recalculate progress for all badges and award any newly earned ones.
    """
)
def check_my_badges(
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Checking badges for user {current_user.username}")
    badge_service = BadgeService(db)
    newly_earned = badge_service.check_and_update_badges(current_user.id)
    
    return {
        "message": f"Checked {len(newly_earned)} newly earned badges",
        "newly_earned": [
            {
                "badge_id": ub.badge_id,
                "badge_name": ub.badge.name if ub.badge else None,
                "earned_at": ub.earned_at
            }
            for ub in newly_earned
        ]
    }


@router.get(
    "/users/{user_id}/badges",
    response_model=dict,
    summary="Get user's earned badges (public)",
    description="""
    Get publicly visible earned badges for any user.
    Only shows badges that have been earned.
    """
)
def get_user_badges_public(
    user_id: int,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Getting public badges for user {user_id}")
    badge_service = BadgeService(db)
    
    result = badge_service.get_user_badges(
        user_id=user_id,
        earned_only=True,  # Only show earned badges publicly
        page=page,
        page_size=page_size
    )
    
    # Convert to response format
    result["items"] = [
        {
            "badge_id": ub.badge_id,
            "badge_name": ub.badge.name if ub.badge else None,
            "badge_description": ub.badge.description if ub.badge else None,
            "badge_icon": ub.badge.icon if ub.badge else None,
            "criteria_type": ub.badge.criteria_type if ub.badge else None,
            "earned_at": ub.earned_at
        }
        for ub in result["items"]
    ]
    
    return result
