from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import LeaderboardEntryOut, CreatorLeaderboardEntryOut
from app.services.leaderboard_service import LeaderboardService

router = APIRouter(
    prefix="/leaderboards",
    tags=["Leaderboards"],
    responses={404: {"description": "Not found"}},
)

@router.get(
    "/submissions",
    response_model=list[LeaderboardEntryOut],
    summary="Leaderboard by accepted submissions",
    description="""
    Returns users ranked by the number of unique problems solved with ACCEPTED submissions.
    Multiple accepted submissions for the same problem count only once per user.
    """
)
def submission_leaderboard(db: Session = Depends(get_db)):
    leaderboard_service = LeaderboardService(db)
    return leaderboard_service.submission_leaderboard()

@router.get(
    "/creators",
    response_model=list[CreatorLeaderboardEntryOut],
    summary="Leaderboard by problems created",
    description="""
    Returns creators ranked by the number of problems they have created.
    """
)
def creator_leaderboard(db: Session = Depends(get_db)):
    leaderboard_service = LeaderboardService(db)
    return leaderboard_service.creator_leaderboard()
