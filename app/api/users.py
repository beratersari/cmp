from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import UserSubmissionHistoryOut, UserStreakOut, UserFollowStatsOut, UserFollowersOut
from app.services.leaderboard_service import LeaderboardService
from app.services.user_service import UserService
from app.api.dependencies import RoleChecker
from app.models.user import UserRole
from app.core.config import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    responses={404: {"description": "Not found"}},
)

@router.get(
    "/me/submission-history",
    response_model=UserSubmissionHistoryOut,
    summary="Get my submission history with daily counts",
    description="""
    Returns the current user's submission history aggregated by date within a given date range.

    ### Authorization:
    - Any authenticated user can view their own history.

    ### Date Format:
    - Use YYYY-MM-DD format for start_date and end_date.
    """
)
def get_my_submission_history(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Getting submission history for {current_user.username}: {start_date} to {end_date}")
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        logger.warning(f"Invalid date format: start_date={start_date}, end_date={end_date}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD."
        )

    if start > end:
        logger.warning(f"Invalid date range: start={start_date} > end={end_date}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before or equal to end date"
        )

    leaderboard_service = LeaderboardService(db)
    try:
        result = leaderboard_service.get_user_submission_history(current_user.id, start, end)
        logger.debug(f"Submission history retrieved: {len(result.daily_submissions)} days")
        return result
    except ValueError as exc:
        logger.error(f"Failed to get submission history: {str(exc)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

@router.get(
    "/me/submission-history/last-7-days",
    response_model=UserSubmissionHistoryOut,
    summary="Get my submission history for last 7 days",
    description="Returns daily submission counts for the last 7 days (including today)."
)
def get_my_submission_history_last_7_days(
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    return _get_my_submission_history_window(db, current_user, days=7)

@router.get(
    "/me/submission-history/last-30-days",
    response_model=UserSubmissionHistoryOut,
    summary="Get my submission history for last 30 days",
    description="Returns daily submission counts for the last 30 days (including today)."
)
def get_my_submission_history_last_30_days(
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    return _get_my_submission_history_window(db, current_user, days=30)

@router.get(
    "/me/submission-history/last-year",
    response_model=UserSubmissionHistoryOut,
    summary="Get my submission history for last year",
    description="Returns daily submission counts for the last 365 days (including today)."
)
def get_my_submission_history_last_year(
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    return _get_my_submission_history_window(db, current_user, days=365)

@router.get(
    "/me/streaks",
    response_model=UserStreakOut,
    summary="Get my submission streaks",
    description="""
    Returns the current user's current and maximum streak based on accepted submissions.

    ### Authorization:
    - Any authenticated user can view their own streaks.
    """
)
def get_my_streaks(
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Getting streaks for {current_user.username}")
    leaderboard_service = LeaderboardService(db)
    try:
        result = leaderboard_service.get_user_streaks(current_user.id)
        logger.debug(f"Streaks retrieved: current={result.streak_info.current_streak}, max={result.streak_info.max_streak}")
        return result
    except ValueError as exc:
        logger.error(f"Failed to get streaks: {str(exc)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

@router.get(
    "/me/follows",
    response_model=UserFollowStatsOut,
    summary="Get my follow stats and following list",
    description="""
    Returns follower/following counts and the list of users this user follows.

    ### Authorization:
    - Any authenticated user can view their own follow stats.
    """
)
def get_my_follow_stats(
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    user_service = UserService(db)
    return user_service.get_follow_stats(current_user, current_user)

@router.get(
    "/admin/{user_id}/followers",
    response_model=UserFollowersOut,
    summary="Get a user's followers (admin-only)",
    description="""
    Returns the list of followers for a user.

    ### Authorization:
    - Admins only.
    """
)
def get_followers(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN]))
):
    user_service = UserService(db)
    return user_service.get_followers(user_id, current_user)

@router.post(
    "/me/follow/{target_user_id}",
    response_model=UserFollowStatsOut,
    summary="Follow a user",
    description="""
    Follow another user.

    ### Authorization:
    - Users can only follow as themselves.
    """
)
def follow_user(
    target_user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Follow request: {current_user.username} -> user_id={target_user_id}")
    try:
        user_service = UserService(db)
        result = user_service.follow_user(current_user, target_user_id, current_user)
        logger.info(f"Follow successful: {current_user.username} -> user_id={target_user_id}")
        return result
    except Exception as e:
        logger.error(f"Follow failed: {current_user.username} -> user_id={target_user_id}, error={str(e)}")
        raise

@router.delete(
    "/me/follow/{target_user_id}",
    response_model=UserFollowStatsOut,
    summary="Unfollow a user",
    description="""
    Unfollow another user.

    ### Authorization:
    - Users can only unfollow as themselves.
    """
)
def unfollow_user(
    target_user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Unfollow request: {current_user.username} -> user_id={target_user_id}")
    try:
        user_service = UserService(db)
        result = user_service.unfollow_user(current_user, target_user_id, current_user)
        logger.info(f"Unfollow successful: {current_user.username} -> user_id={target_user_id}")
        return result
    except Exception as e:
        logger.error(f"Unfollow failed: {current_user.username} -> user_id={target_user_id}, error={str(e)}")
        raise


def _get_my_submission_history_window(db: Session, current_user, days: int):
    end = datetime.now()
    start = (end - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
    leaderboard_service = LeaderboardService(db)
    try:
        return leaderboard_service.get_user_submission_history(current_user.id, start, end)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
