from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
from app.repositories.problem_repository import ProblemRepository
from app.repositories.user_repository import UserRepository
from app.repositories.contest_repository import ContestRepository
from fastapi import HTTPException, status
from app.schemas import (
    LeaderboardEntryOut, CreatorLeaderboardEntryOut, 
    UserSubmissionHistoryOut, SubmissionHistoryEntry, UserStreakOut, StreakInfo,
    ContestLeaderboardEntryOut, TeamContestLeaderboardEntryOut, TeamContestProblemDetail
)
from app.models.problem import SubmissionStatus
from app.models.user import User
from app.core.config import get_logger

# Penalty in minutes for each wrong submission before accepted
CONTEST_PENALTY_MINUTES = 15

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

    def get_contest_leaderboard(
        self,
        contest_id: int,
        page: int = 1,
        page_size: int = 20
    ):
        """
        Generate a leaderboard for a specific contest with ICPC-style scoring.
        
        Scoring rules:
        - Users are ranked by number of problems solved (descending)
        - Ties are broken by total penalty time (ascending)
        - Penalty time = time to solve each problem + 15 min per wrong submission before accepted
        - Only submissions within contest time window are considered
        - After an accepted submission for a problem, further wrong submissions don't add penalty
        """
        logger.debug(f"Generating contest leaderboard: contest_id={contest_id}, page={page}, page_size={page_size}")
        
        # Get contest details
        contest_repo = ContestRepository(self.problem_repo.db)
        contest = contest_repo.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("Contest not found")
        
        # Get problem IDs and titles for this contest
        problem_ids = contest.problem_ids
        if not problem_ids:
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "pages": 0,
                "has_next": False,
                "has_prev": False
            }
        
        # Build problem_id -> problem mapping for titles
        problems = contest.problems
        problem_map = {p.id: p for p in problems}
        
        # Get all submissions during contest time
        submissions = self.problem_repo.list_submissions_for_contest(
            problem_ids=problem_ids,
            start_time=contest.start_date,
            end_time=contest.end_date
        )
        
        # Calculate stats per user per problem
        # user_stats[username][problem_id] = {
        #     'accepted': bool,
        #     'first_accepted_time': datetime or None,
        #     'wrong_before_accepted': int (count of wrong submissions before first accepted)
        # }
        user_stats: dict[str, dict[int, dict]] = defaultdict(lambda: defaultdict(lambda: {
            'accepted': False,
            'first_accepted_time': None,
            'wrong_before_accepted': 0
        }))
        
        for submission in submissions:
            username = submission.username
            problem_id = submission.problem_id
            sub_status = submission.status
            sub_time = submission.submission_time
            
            stats = user_stats[username][problem_id]
            
            # If already accepted this problem, skip (no more penalty after accepted)
            if stats['accepted']:
                continue
            
            if sub_status == SubmissionStatus.ACCEPTED.value:
                stats['accepted'] = True
                stats['first_accepted_time'] = sub_time
            else:
                # Wrong submission before accepted
                stats['wrong_before_accepted'] += 1
        
        # Calculate leaderboard entries with problem details
        from app.schemas import ContestProblemSubmissionDetail
        
        leaderboard_data = []
        contest_start = contest.start_date
        
        for username, problem_stats in user_stats.items():
            problems_solved = 0
            total_penalty = 0
            problem_details = []
            
            for problem_id in problem_ids:
                stats = problem_stats[problem_id]
                problem = problem_map.get(problem_id)
                problem_title = problem.title if problem else f"Problem {problem_id}"
                
                if stats['accepted'] and stats['first_accepted_time']:
                    problems_solved += 1
                    
                    # Time to solve in minutes
                    time_to_solve = int((stats['first_accepted_time'] - contest_start).total_seconds() / 60)
                    
                    # Penalty = time to solve + (wrong submissions before accepted * contest penalty)
                    penalty_minutes_per_wrong = contest.penalty_minutes
                    penalty = time_to_solve + (stats['wrong_before_accepted'] * penalty_minutes_per_wrong)
                    total_penalty += penalty
                    
                    problem_details.append(ContestProblemSubmissionDetail(
                        problem_id=problem_id,
                        problem_title=problem_title,
                        accepted=True,
                        accepted_at_minutes=time_to_solve,
                        incorrect_submissions=stats['wrong_before_accepted'],
                        penalty_minutes=penalty
                    ))
                else:
                    # Problem not solved - still include with accepted=False
                    problem_details.append(ContestProblemSubmissionDetail(
                        problem_id=problem_id,
                        problem_title=problem_title,
                        accepted=False,
                        accepted_at_minutes=None,
                        incorrect_submissions=stats['wrong_before_accepted'],
                        penalty_minutes=0
                    ))
            
            if problems_solved > 0:
                leaderboard_data.append({
                    'username': username,
                    'problems_solved': problems_solved,
                    'penalty_time': total_penalty,
                    'problem_details': problem_details
                })
        
        # Sort by problems solved (desc), then by penalty time (asc)
        leaderboard_data.sort(key=lambda x: (-x['problems_solved'], x['penalty_time']))
        
        # Assign ranks (handle ties)
        ranked_entries = []
        rank = 0
        prev_problems = -1
        prev_penalty = -1
        
        for i, entry in enumerate(leaderboard_data):
            if entry['problems_solved'] != prev_problems or entry['penalty_time'] != prev_penalty:
                rank = i + 1
                prev_problems = entry['problems_solved']
                prev_penalty = entry['penalty_time']
            
            ranked_entries.append(ContestLeaderboardEntryOut(
                username=entry['username'],
                problems_solved=entry['problems_solved'],
                penalty_time=entry['penalty_time'],
                rank=rank,
                problem_details=entry['problem_details']
            ))
        
        # Apply pagination
        total = len(ranked_entries)
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated = ranked_entries[start_index:end_index]
        
        pages = (total + page_size - 1) // page_size if total > 0 else 0
        has_next = page < pages
        has_prev = page > 1
        
        logger.debug(f"Contest leaderboard generated: {total} entries, {pages} pages")
        
        return {
            "items": paginated,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }

    def get_team_contest_leaderboard(
        self,
        contest_id: int,
        page: int = 1,
        page_size: int = 20
    ):
        """
        Generate a leaderboard for a team contest with ICPC-style scoring.
        
        Teams are ranked by aggregating submissions from all team members.
        For each problem, the first accepted submission by any team member counts.
        
        Scoring rules:
        - Teams are ranked by number of problems solved (descending)
        - Ties are broken by total penalty time (ascending)
        - Penalty time = time to solve each problem + penalty per wrong submission before first accepted
        - Only submissions within contest time window are considered
        - After a team member's accepted submission for a problem, further wrong submissions don't add penalty
        """
        logger.debug(f"Generating team contest leaderboard: contest_id={contest_id}, page={page}, page_size={page_size}")
        
        # Get contest details
        contest_repo = ContestRepository(self.problem_repo.db)
        contest = contest_repo.get_contest_by_id(contest_id)
        if not contest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contest not found"
            )
        
        # Check if this is a team contest
        from app.models.contest import ContestMode
        if contest.contest_mode != ContestMode.TEAM.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This is not a team contest. Use the regular contest leaderboard endpoint."
            )
        
        # Get problem IDs and titles for this contest
        problem_ids = contest.problem_ids
        if not problem_ids:
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "pages": 0,
                "has_next": False,
                "has_prev": False
            }
        
        # Build problem_id -> problem mapping for titles
        problems = contest.problems
        problem_map = {p.id: p for p in problems}
        
        # Get all submissions during contest time
        submissions = self.problem_repo.list_submissions_for_contest(
            problem_ids=problem_ids,
            start_time=contest.start_date,
            end_time=contest.end_date
        )
        
        # Get all team registrations for this contest
        from app.models.contest import ContestRegistration
        from app.models.team import Team, TeamMember
        
        team_registrations = self.problem_repo.db.query(ContestRegistration).filter(
            ContestRegistration.contest_id == contest_id,
            ContestRegistration.team_id.isnot(None)
        ).all()
        
        # Build team_id -> team mapping and team member lists
        teams_map = {}
        team_members_map = {}  # team_id -> set of user_ids
        
        for reg in team_registrations:
            if reg.team:
                teams_map[reg.team_id] = reg.team
                # Get active team member IDs
                member_ids = {m.user_id for m in reg.team.active_members}
                team_members_map[reg.team_id] = member_ids
        
        # Calculate stats per team per problem
        # team_stats[team_id][problem_id] = {
        #     'accepted': bool,
        #     'first_accepted_time': datetime or None,
        #     'wrong_before_accepted': int,
        #     'solved_by': username or None
        # }
        team_stats: dict[int, dict[int, dict]] = defaultdict(lambda: defaultdict(lambda: {
            'accepted': False,
            'first_accepted_time': None,
            'wrong_before_accepted': 0,
            'solved_by': None
        }))
        
        # Group submissions by team
        for submission in submissions:
            user_id = submission.user_id
            problem_id = submission.problem_id
            sub_status = submission.status
            sub_time = submission.submission_time
            username = submission.username
            
            # Find which team this user belongs to (if any)
            for team_id, member_ids in team_members_map.items():
                if user_id in member_ids:
                    stats = team_stats[team_id][problem_id]
                    
                    # If already accepted this problem by any team member, skip
                    if stats['accepted']:
                        continue
                    
                    if sub_status == SubmissionStatus.ACCEPTED.value:
                        stats['accepted'] = True
                        stats['first_accepted_time'] = sub_time
                        stats['solved_by'] = username
                    else:
                        # Wrong submission before accepted
                        stats['wrong_before_accepted'] += 1
                    break  # User can only be in one team per contest
        
        # Calculate leaderboard entries with problem details
        leaderboard_data = []
        contest_start = contest.start_date
        
        for team_id, problem_stats in team_stats.items():
            team = teams_map.get(team_id)
            if not team:
                continue
            
            problems_solved = 0
            total_penalty = 0
            problem_details = []
            
            for problem_id in problem_ids:
                stats = problem_stats[problem_id]
                problem = problem_map.get(problem_id)
                problem_title = problem.title if problem else f"Problem {problem_id}"
                
                if stats['accepted'] and stats['first_accepted_time']:
                    problems_solved += 1
                    
                    # Time to solve in minutes
                    time_to_solve = int((stats['first_accepted_time'] - contest_start).total_seconds() / 60)
                    
                    # Penalty = time to solve + (wrong submissions before accepted * contest penalty)
                    penalty_minutes_per_wrong = contest.penalty_minutes
                    penalty = time_to_solve + (stats['wrong_before_accepted'] * penalty_minutes_per_wrong)
                    total_penalty += penalty
                    
                    problem_details.append(TeamContestProblemDetail(
                        problem_id=problem_id,
                        problem_title=problem_title,
                        accepted=True,
                        accepted_at_minutes=time_to_solve,
                        incorrect_submissions=stats['wrong_before_accepted'],
                        penalty_minutes=penalty,
                        solved_by=stats['solved_by']
                    ))
                else:
                    # Problem not solved - still include with accepted=False
                    problem_details.append(TeamContestProblemDetail(
                        problem_id=problem_id,
                        problem_title=problem_title,
                        accepted=False,
                        accepted_at_minutes=None,
                        incorrect_submissions=stats['wrong_before_accepted'],
                        penalty_minutes=0,
                        solved_by=None
                    ))
            
            if problems_solved > 0:
                leaderboard_data.append({
                    'team_id': team_id,
                    'team_name': team.name,
                    'member_count': team.member_count,
                    'member_usernames': team.member_usernames,
                    'problems_solved': problems_solved,
                    'penalty_time': total_penalty,
                    'problem_details': problem_details
                })
        
        # Sort by problems solved (desc), then by penalty time (asc)
        leaderboard_data.sort(key=lambda x: (-x['problems_solved'], x['penalty_time']))
        
        # Assign ranks (handle ties)
        ranked_entries = []
        rank = 0
        prev_problems = -1
        prev_penalty = -1
        
        for i, entry in enumerate(leaderboard_data):
            if entry['problems_solved'] != prev_problems or entry['penalty_time'] != prev_penalty:
                rank = i + 1
                prev_problems = entry['problems_solved']
                prev_penalty = entry['penalty_time']
            
            ranked_entries.append(TeamContestLeaderboardEntryOut(
                team_id=entry['team_id'],
                team_name=entry['team_name'],
                member_count=entry['member_count'],
                problems_solved=entry['problems_solved'],
                penalty_time=entry['penalty_time'],
                rank=rank,
                problem_details=entry['problem_details'],
                member_usernames=entry['member_usernames']
            ))
        
        # Apply pagination
        total = len(ranked_entries)
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated = ranked_entries[start_index:end_index]
        
        pages = (total + page_size - 1) // page_size if total > 0 else 0
        has_next = page < pages
        has_prev = page > 1
        
        logger.debug(f"Team contest leaderboard generated: {total} entries, {pages} pages")
        
        return {
            "items": paginated,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }
