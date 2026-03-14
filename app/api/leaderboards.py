from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import LeaderboardEntryOut, CreatorLeaderboardEntryOut, PaginatedResponse, ContestLeaderboardEntryOut, TeamContestLeaderboardEntryOut
from app.services.leaderboard_service import LeaderboardService
from app.api.dependencies import RoleChecker, get_current_user
from app.models.user import UserRole
from app.core.config import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/leaderboards",
    tags=["Leaderboards"],
    responses={404: {"description": "Not found"}},
)

@router.get(
    "/submissions",
    response_model=PaginatedResponse[LeaderboardEntryOut],
    summary="Leaderboard by accepted submissions",
    description="""
    Returns users ranked by the number of unique problems solved with ACCEPTED submissions.
    Multiple accepted submissions for the same problem count only once per user.

    ### Pagination:
    - Use `page` and `page_size` query parameters to control pagination.
    - Default: page=1, page_size=20

    ### Search:
    - Use `search` query parameter to search by username (case-insensitive).
    """
)
def submission_leaderboard(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    search: str | None = Query(default=None, description="Search by username")
):
    logger.info(f"Getting submission leaderboard: page={page}, page_size={page_size}, search={search}")
    leaderboard_service = LeaderboardService(db)
    result = leaderboard_service.submission_leaderboard(page=page, page_size=page_size, search=search)
    logger.debug(f"Submission leaderboard retrieved: {len(result.get('items', []))} entries")
    return result

@router.get(
    "/submissions/last-7-days",
    response_model=PaginatedResponse[LeaderboardEntryOut],
    summary="Leaderboard by accepted submissions in the last 7 days",
    description="""
    Returns users ranked by unique problems solved with ACCEPTED submissions in the last 7 days.

    ### Pagination:
    - Use `page` and `page_size` query parameters to control pagination.
    - Default: page=1, page_size=20

    ### Search:
    - Use `search` query parameter to search by username (case-insensitive).
    """
)
def submission_leaderboard_last_7_days(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    search: str | None = Query(default=None, description="Search by username")
):
    leaderboard_service = LeaderboardService(db)
    return leaderboard_service.submission_leaderboard(page=page, page_size=page_size, search=search, days=7)

@router.get(
    "/submissions/last-30-days",
    response_model=PaginatedResponse[LeaderboardEntryOut],
    summary="Leaderboard by accepted submissions in the last 30 days",
    description="""
    Returns users ranked by unique problems solved with ACCEPTED submissions in the last 30 days.

    ### Pagination:
    - Use `page` and `page_size` query parameters to control pagination.
    - Default: page=1, page_size=20

    ### Search:
    - Use `search` query parameter to search by username (case-insensitive).
    """
)
def submission_leaderboard_last_30_days(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    search: str | None = Query(default=None, description="Search by username")
):
    leaderboard_service = LeaderboardService(db)
    return leaderboard_service.submission_leaderboard(page=page, page_size=page_size, search=search, days=30)

@router.get(
    "/submissions/last-year",
    response_model=PaginatedResponse[LeaderboardEntryOut],
    summary="Leaderboard by accepted submissions in the last year",
    description="""
    Returns users ranked by unique problems solved with ACCEPTED submissions in the last year.

    ### Pagination:
    - Use `page` and `page_size` query parameters to control pagination.
    - Default: page=1, page_size=20

    ### Search:
    - Use `search` query parameter to search by username (case-insensitive).
    """
)
def submission_leaderboard_last_year(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    search: str | None = Query(default=None, description="Search by username")
):
    leaderboard_service = LeaderboardService(db)
    return leaderboard_service.submission_leaderboard(page=page, page_size=page_size, search=search, days=365)

@router.get(
    "/creators",
    response_model=PaginatedResponse[CreatorLeaderboardEntryOut],
    summary="Leaderboard by problems created",
    description="""
    Returns creators ranked by the number of problems they have created.

    ### Pagination:
    - Use `page` and `page_size` query parameters to control pagination.
    - Default: page=1, page_size=20

    ### Search:
    - Use `search` query parameter to search by username (case-insensitive).
    """
)
def creator_leaderboard(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    search: str | None = Query(default=None, description="Search by username")
):
    logger.info(f"Getting creator leaderboard: page={page}, page_size={page_size}, search={search}")
    leaderboard_service = LeaderboardService(db)
    result = leaderboard_service.creator_leaderboard(page=page, page_size=page_size, search=search)
    logger.debug(f"Creator leaderboard retrieved: {len(result.get('items', []))} entries")
    return result

@router.get(
    "/creators/last-7-days",
    response_model=PaginatedResponse[CreatorLeaderboardEntryOut],
    summary="Leaderboard by problems created in the last 7 days",
    description="""
    Returns creators ranked by the number of problems they created in the last 7 days.

    ### Pagination:
    - Use `page` and `page_size` query parameters to control pagination.
    - Default: page=1, page_size=20

    ### Search:
    - Use `search` query parameter to search by username (case-insensitive).
    """
)
def creator_leaderboard_last_7_days(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    search: str | None = Query(default=None, description="Search by username")
):
    leaderboard_service = LeaderboardService(db)
    return leaderboard_service.creator_leaderboard(page=page, page_size=page_size, search=search, days=7)

@router.get(
    "/creators/last-30-days",
    response_model=PaginatedResponse[CreatorLeaderboardEntryOut],
    summary="Leaderboard by problems created in the last 30 days",
    description="""
    Returns creators ranked by the number of problems they created in the last 30 days.

    ### Pagination:
    - Use `page` and `page_size` query parameters to control pagination.
    - Default: page=1, page_size=20

    ### Search:
    - Use `search` query parameter to search by username (case-insensitive).
    """
)
def creator_leaderboard_last_30_days(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    search: str | None = Query(default=None, description="Search by username")
):
    leaderboard_service = LeaderboardService(db)
    return leaderboard_service.creator_leaderboard(page=page, page_size=page_size, search=search, days=30)

@router.get(
    "/creators/last-year",
    response_model=PaginatedResponse[CreatorLeaderboardEntryOut],
    summary="Leaderboard by problems created in the last year",
    description="""
    Returns creators ranked by the number of problems they created in the last year.

    ### Pagination:
    - Use `page` and `page_size` query parameters to control pagination.
    - Default: page=1, page_size=20

    ### Search:
    - Use `search` query parameter to search by username (case-insensitive).
    """
)
def creator_leaderboard_last_year(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    search: str | None = Query(default=None, description="Search by username")
):
    leaderboard_service = LeaderboardService(db)
    return leaderboard_service.creator_leaderboard(page=page, page_size=page_size, search=search, days=365)


# ============================================================================
# Following Leaderboard Endpoints
# ============================================================================

@router.get(
    "/following",
    response_model=dict,
    summary="Leaderboard of users you follow",
    description="""
    Returns a leaderboard consisting only of users that the current user follows,
    plus the current user themselves.
    
    Ranked by unique problems solved with ACCEPTED submissions.

    ### Pagination:
    - Use `page` and `page_size` query parameters to control pagination.
    - Default: page=1, page_size=20
    """
)
def following_leaderboard(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Getting following leaderboard: user={current_user.username}, page={page}")
    leaderboard_service = LeaderboardService(db)
    result = leaderboard_service.get_following_leaderboard(
        user_id=current_user.id,
        page=page,
        page_size=page_size
    )
    logger.debug(f"Following leaderboard retrieved: {len(result.get('items', []))} entries")
    return result


@router.get(
    "/following/last-7-days",
    response_model=dict,
    summary="Leaderboard of users you follow (last 7 days)",
    description="""
    Returns a leaderboard of users you follow, ranked by unique problems solved
    with ACCEPTED submissions in the last 7 days.

    ### Pagination:
    - Use `page` and `page_size` query parameters to control pagination.
    - Default: page=1, page_size=20
    """
)
def following_leaderboard_last_7_days(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Getting following leaderboard (7 days): user={current_user.username}, page={page}")
    leaderboard_service = LeaderboardService(db)
    result = leaderboard_service.get_following_leaderboard(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        days=7
    )
    return result


@router.get(
    "/following/last-30-days",
    response_model=dict,
    summary="Leaderboard of users you follow (last 30 days)",
    description="""
    Returns a leaderboard of users you follow, ranked by unique problems solved
    with ACCEPTED submissions in the last 30 days.

    ### Pagination:
    - Use `page` and `page_size` query parameters to control pagination.
    - Default: page=1, page_size=20
    """
)
def following_leaderboard_last_30_days(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Getting following leaderboard (30 days): user={current_user.username}, page={page}")
    leaderboard_service = LeaderboardService(db)
    result = leaderboard_service.get_following_leaderboard(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        days=30
    )
    return result


@router.get(
    "/following/last-year",
    response_model=dict,
    summary="Leaderboard of users you follow (last year)",
    description="""
    Returns a leaderboard of users you follow, ranked by unique problems solved
    with ACCEPTED submissions in the last year.

    ### Pagination:
    - Use `page` and `page_size` query parameters to control pagination.
    - Default: page=1, page_size=20
    """
)
def following_leaderboard_last_year(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Getting following leaderboard (1 year): user={current_user.username}, page={page}")
    leaderboard_service = LeaderboardService(db)
    result = leaderboard_service.get_following_leaderboard(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        days=365
    )
    return result


# ============================================================================
# Contest Leaderboard Endpoints
# ============================================================================

@router.get(
    "/contests/{contest_id}",
    response_model=PaginatedResponse[ContestLeaderboardEntryOut],
    summary="Contest leaderboard with ICPC-style scoring",
    description="""
    Returns a leaderboard for a specific contest with ICPC-style scoring.
    
    ### Scoring Rules:
    - **Primary**: Users ranked by number of problems solved (descending)
    - **Tiebreaker**: Total penalty time (ascending)
    - **Penalty Calculation**: For each solved problem:
      - Base time = minutes from contest start to first accepted submission
      - Penalty = 15 minutes per wrong submission BEFORE the accepted one
      - After an accepted submission, further wrong submissions don't add penalty
    - Only submissions within the contest time window are considered
    
    ### Pagination:
    - Use `page` and `page_size` query parameters to control pagination.
    - Default: page=1, page_size=20
    """
)
def contest_leaderboard(
    contest_id: int = Path(..., description="Contest ID", ge=1),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page")
):
    logger.info(f"Getting contest leaderboard: contest_id={contest_id}, page={page}")
    leaderboard_service = LeaderboardService(db)
    result = leaderboard_service.get_contest_leaderboard(
        contest_id=contest_id,
        page=page,
        page_size=page_size
    )
    logger.debug(f"Contest leaderboard retrieved: {len(result.get('items', []))} entries")
    return result


@router.get(
    "/contests/{contest_id}/teams",
    response_model=PaginatedResponse[TeamContestLeaderboardEntryOut],
    summary="Team contest leaderboard with ICPC-style scoring",
    description="""
    Returns a leaderboard for a team contest with ICPC-style scoring.
    
    This endpoint aggregates submissions from all team members. For each problem,
    the first accepted submission by any team member counts for the team.
    
    ### Scoring Rules:
    - **Primary**: Teams ranked by number of problems solved (descending)
    - **Tiebreaker**: Total penalty time (ascending)
    - **Penalty Calculation**: For each solved problem:
      - Base time = minutes from contest start to first accepted submission by any team member
      - Penalty = contest.penalty_minutes per wrong submission BEFORE the first accepted
      - After a team member's accepted submission, further wrong submissions don't add penalty
    - Only submissions within contest time window are considered
    - Only registered teams appear on the leaderboard
    
    ### Error Cases:
    - Returns error if contest is not a team contest
    
    ### Pagination:
    - Use `page` and `page_size` query parameters to control pagination.
    - Default: page=1, page_size=20
    """
)
def team_contest_leaderboard(
    contest_id: int = Path(..., description="Contest ID", ge=1),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page")
):
    logger.info(f"Getting team contest leaderboard: contest_id={contest_id}, page={page}")
    leaderboard_service = LeaderboardService(db)
    result = leaderboard_service.get_team_contest_leaderboard(
        contest_id=contest_id,
        page=page,
        page_size=page_size
    )
    logger.debug(f"Team contest leaderboard retrieved: {len(result.get('items', []))} entries")
    return result
