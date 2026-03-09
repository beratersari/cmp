from sqlalchemy.orm import Session
from app.repositories.problem_repository import ProblemRepository
from app.schemas import LeaderboardEntryOut, CreatorLeaderboardEntryOut
from app.models.problem import SubmissionStatus

class LeaderboardService:
    def __init__(self, db: Session):
        self.problem_repo = ProblemRepository(db)

    def submission_leaderboard(self):
        submissions = self.problem_repo.list_all_submissions()
        accepted = [s for s in submissions if s.status == SubmissionStatus.ACCEPTED.value]
        solved_by_user: dict[str, set[int]] = {}
        for submission in accepted:
            solved_by_user.setdefault(submission.username, set()).add(submission.problem_id)
        leaderboard = [
            LeaderboardEntryOut(username=username, accepted_problem_count=len(problem_ids))
            for username, problem_ids in solved_by_user.items()
        ]
        leaderboard.sort(key=lambda entry: entry.accepted_problem_count, reverse=True)
        return leaderboard

    def creator_leaderboard(self):
        problems = self.problem_repo.list_problems()
        counts: dict[str, int] = {}
        for problem in problems:
            owner_username = problem.owner.username if problem.owner else "unknown"
            counts[owner_username] = counts.get(owner_username, 0) + 1
        leaderboard = [
            CreatorLeaderboardEntryOut(username=username, created_problem_count=count)
            for username, count in counts.items()
        ]
        leaderboard.sort(key=lambda entry: entry.created_problem_count, reverse=True)
        return leaderboard
