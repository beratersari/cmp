from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
from app.repositories.problem_repository import ProblemRepository
from app.repositories.user_repository import UserRepository
from app.schemas import (
    LeaderboardEntryOut, CreatorLeaderboardEntryOut, 
    UserSubmissionHistoryOut, SubmissionHistoryEntry, UserStreakOut, StreakInfo
)
from app.models.problem import SubmissionStatus
from app.models.user import User
from app.core.config import get_logger

logger = get_logger(__name__)

class LeaderboardService:
    def __init__(self, db: Session):
        self.problem_repo = ProblemRepository(db)
        self.user_repo = UserRepository(db)
        logger.debug("LeaderboardService initialized")

    def submission_leaderboard(self, page: int = 1, page_size: int = 20, search: Optional[str] = None, days: Optional[int] = None):
        logger.debug(f"Generating submission leaderboard: page={page}, page_size={page_size}, days={days}")
        if days is None:
            submissions = self.problem_repo.list_all_submissions()
        else:
            start, end = self._get_date_range_from_days(days)
            submissions = self.problem_repo.list_submissions_in_date_range(start, end)

        accepted = [s for s in submissions if s.status == SubmissionStatus.ACCEPTED.value]
        solved_by_user: dict[str, set[int]] = {}
        for submission in accepted:
            solved_by_user.setdefault(submission.username, set()).add(submission.problem_id)
        
        leaderboard = [
            LeaderboardEntryOut(username=username, accepted_problem_count=len(problem_ids))
            for username, problem_ids in solved_by_user.items()
        ]
        leaderboard.sort(key=lambda entry: entry.accepted_problem_count, reverse=True)
        
        # Apply search filter
        if search:
            leaderboard = [entry for entry in leaderboard if search.lower() in entry.username.lower()]
        
        # Calculate pagination
        total = len(leaderboard)
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated = leaderboard[start_index:end_index]
        
        pages = (total + page_size - 1) // page_size
        has_next = page < pages
        has_prev = page > 1
        
        return {
            "items": paginated,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }

    def get_user_submission_history(self, user_id: int, start_date: datetime, end_date: datetime):
        """Get submission history for a user within a date range."""
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        submissions = self.problem_repo.get_user_submissions_in_date_range(user_id, start_date, end_date)

        # Group submissions by date
        daily_counts = defaultdict(int)
        for submission in submissions:
            date_str = submission.submission_time.strftime("%Y-%m-%d")
            daily_counts[date_str] += 1

        # Generate all dates in range
        daily_submissions = []
        current = start_date.date()
        end = end_date.date()
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            daily_submissions.append(SubmissionHistoryEntry(
                date=date_str,
                submission_count=daily_counts.get(date_str, 0)
            ))
            current += timedelta(days=1)

        return UserSubmissionHistoryOut(
            user_id=user_id,
            username=user.username,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            daily_submissions=daily_submissions,
            total_submissions=len(submissions)
        )

    def get_user_streaks(self, user_id: int):
        """Calculate current and maximum daily streaks for a user based on accepted submissions."""
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        accepted_submissions = self.problem_repo.get_user_accepted_submissions(user_id)

        if not accepted_submissions:
            return UserStreakOut(
                user_id=user_id,
                username=user.username,
                streak_info=StreakInfo(
                    current_streak=0,
                    max_streak=0,
                    last_accepted_date=None
                )
            )

        # Get unique dates with accepted submissions
        accepted_dates = {submission.submission_time.date() for submission in accepted_submissions}
        sorted_dates = sorted(accepted_dates)

        last_accepted_date = sorted_dates[-1].strftime("%Y-%m-%d") if sorted_dates else None
        today = datetime.now().date()

        # Calculate current daily streak
        current_streak = 0
        if sorted_dates:
            # Check if last submission was today or yesterday
            if (today - sorted_dates[-1]).days <= 1:
                current_streak = 1
                for i in range(len(sorted_dates) - 2, -1, -1):
                    if (sorted_dates[i + 1] - sorted_dates[i]).days == 1:
                        current_streak += 1
                    else:
                        break

        # Calculate max daily streak
        max_streak = 1
        streak = 1
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 1

        return UserStreakOut(
            user_id=user_id,
            username=user.username,
            streak_info=StreakInfo(
                current_streak=current_streak,
                max_streak=max_streak if len(sorted_dates) > 0 else 0,
                last_accepted_date=last_accepted_date
            )
        )

    def creator_leaderboard(self, page: int = 1, page_size: int = 20, search: Optional[str] = None, days: Optional[int] = None):
        if days is None:
            problems, _ = self.problem_repo.list_problems()
        else:
            start, end = self._get_date_range_from_days(days)
            problems, _ = self.problem_repo.list_problems_created_in_date_range(start, end)

        counts: dict[str, int] = {}
        for problem in problems:
            owner_username = problem.owner.username if problem.owner else "unknown"
            counts[owner_username] = counts.get(owner_username, 0) + 1
        
        leaderboard = [
            CreatorLeaderboardEntryOut(username=username, created_problem_count=count)
            for username, count in counts.items()
        ]
        leaderboard.sort(key=lambda entry: entry.created_problem_count, reverse=True)
        
        # Apply search filter
        if search:
            leaderboard = [entry for entry in leaderboard if search.lower() in entry.username.lower()]
        
        # Calculate pagination
        total = len(leaderboard)
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated = leaderboard[start_index:end_index]
        
        pages = (total + page_size - 1) // page_size
        has_next = page < pages
        has_prev = page > 1
        
        return {
            "items": paginated,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }

    def _get_date_range_from_days(self, days: int) -> tuple[datetime, datetime]:
        end = datetime.now()
        start = end - timedelta(days=days - 1)
        return start, end

    def get_following_leaderboard(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        days: Optional[int] = None
    ):
        """
        Generate a leaderboard consisting only of users that the current user follows.
        Includes the current user as well so they can see their own ranking.
        """
        logger.info(f"Generating following leaderboard: user_id={user_id}, page={page}, days={days}")
        
        # Get the current user
        current_user = self.user_repo.get_user_by_id(user_id)
        if not current_user:
            raise ValueError("User not found")
        
        # Get list of users the current user follows
        following_usernames = {user.username for user in current_user.following}
        # Also include the current user themselves
        following_usernames.add(current_user.username)
        
        logger.debug(f"User {current_user.username} follows {len(following_usernames) - 1} users")
        
        # Get submissions based on time range
        if days is None:
            submissions = self.problem_repo.list_all_submissions()
        else:
            start, end = self._get_date_range_from_days(days)
            submissions = self.problem_repo.list_submissions_in_date_range(start, end)
        
        # Filter submissions to only include followed users + current user
        accepted = [
            s for s in submissions 
            if s.status == SubmissionStatus.ACCEPTED.value and s.username in following_usernames
        ]
        
        # Count unique problems solved per user
        solved_by_user: dict[str, set[int]] = {}
        for submission in accepted:
            solved_by_user.setdefault(submission.username, set()).add(submission.problem_id)
        
        # Build leaderboard
        leaderboard = [
            LeaderboardEntryOut(username=username, accepted_problem_count=len(problem_ids))
            for username, problem_ids in solved_by_user.items()
        ]
        
        # Sort by problem count (descending)
        leaderboard.sort(key=lambda entry: entry.accepted_problem_count, reverse=True)
        
        # Calculate pagination
        total = len(leaderboard)
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated = leaderboard[start_index:end_index]
        
        pages = (total + page_size - 1) // page_size
        has_next = page < pages
        has_prev = page > 1
        
        logger.info(f"Following leaderboard generated: {total} entries, {pages} pages")
        
        return {
            "items": paginated,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev,
            "following_count": len(current_user.following)
        }
