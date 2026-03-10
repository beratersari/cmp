from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import LeaderboardEntryOut, CreatorLeaderboardEntryOut, PaginatedResponse
from app.services.leaderboard_service import LeaderboardService

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
    leaderboard_service = LeaderboardService(db)
    return leaderboard_service.submission_leaderboard(page=page, page_size=page_size, search=search)

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
    leaderboard_service = LeaderboardService(db)
    return leaderboard_service.creator_leaderboard(page=page, page_size=page_size, search=search)

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
