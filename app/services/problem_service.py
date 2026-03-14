from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.problem_repository import ProblemRepository
from app.repositories.user_repository import UserRepository
from app.schemas import (
    ProblemCreate,
    ProblemUpdate,
    SubmissionCreate,
    SubmissionUpdate,
    SubmissionStatusUpdate,
    ProblemsByOwnerOut,
    CreatorProblemStatsOut,
    ProblemSubmissionStatsOut,
    EditorialCreate,
    EditorialUpdate,
    TestcaseCreate,
    VoteCreate,
    VoteStats,
    ProblemVoteStatsOut,
    EditorialVoteStatsOut,
    CreatorVoteStatsOut,
)
from app.models.user import UserRole
from app.models.problem import SubmissionStatus
from app.core.config import get_logger

logger = get_logger(__name__)

class ProblemService:
    def __init__(self, db: Session):
        self.problem_repo = ProblemRepository(db)
        self.user_repo = UserRepository(db)
        logger.debug("ProblemService initialized")

    def create_problem(self, problem_create: ProblemCreate, owner_id: int, created_by: str):
        logger.debug(f"Creating problem: title='{problem_create.title}', owner_id={owner_id}")
        if self.problem_repo.get_problem_by_title(problem_create.title):
            logger.warning(f"Problem title already exists: '{problem_create.title}'")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Problem title already exists"
            )
        if problem_create.tags:
            problem_create.tags = [tag.strip() for tag in problem_create.tags if tag.strip()]
        try:
            problem = self.problem_repo.create_problem(problem_create, owner_id, created_by=created_by)
            logger.debug(f"Problem created: id={problem.id}, title='{problem.title}'")
            return problem
        except ValueError as exc:
            logger.error(f"Failed to create problem: {str(exc)}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    def list_problems(self, current_user=None, tag: str | None = None, page: int = 1, page_size: int = 20, search: Optional[str] = None):
        skip = (page - 1) * page_size
        
        # Get problems with pagination
        if tag:
            problems, total = self.problem_repo.list_problems_by_tag(tag, skip=skip, limit=page_size)
        else:
            problems, total = self.problem_repo.list_problems(skip=skip, limit=page_size, search=search)
        
        # Filter for normal users or unauthenticated users
        if not current_user or current_user.role == UserRole.USER:
            filtered = [p for p in problems if p.is_published and p.is_public]
        elif current_user.role == UserRole.ADMIN:
            # Admins see everything
            filtered = problems
        elif current_user.role == UserRole.CREATOR:
            # Creators see public published problems, their own problems, and problems they are allowed to see
            filtered = [
                p for p in problems 
                if (p.is_published and p.is_public) or 
                   p.owner_id == current_user.id or 
                   current_user in p.allowed_users
            ]
        else:
            filtered = []
        
        # Calculate pagination info
        pages = (total + page_size - 1) // page_size
        has_next = page < pages
        has_prev = page > 1
        
        return {
            "items": self._serialize_problems(filtered),
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }

    def get_problem(self, problem_id: int, current_user=None):
        problem = self.problem_repo.get_problem_by_id(problem_id)
        if not problem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problem not found"
            )
        
        # Check visibility
        is_owner = current_user and problem.owner_id == current_user.id
        is_admin = current_user and current_user.role == UserRole.ADMIN
        is_allowed = current_user and current_user in problem.allowed_users
        
        # If not published, only owner or admin can see
        if not problem.is_published:
            if not (is_owner or is_admin):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Problem is not published"
                )
        
        # If private, only owner, admin, or allowed creators can see
        if not problem.is_public:
            if not (is_owner or is_admin or is_allowed):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Problem is private"
                )
        
        problem.allowed_user_ids = [u.id for u in problem.allowed_users]
        return problem

    def check_edit_permission(self, problem, current_user):
        if current_user.role == UserRole.ADMIN:
            return True
        if current_user.role == UserRole.CREATOR:
            if problem.owner_id == current_user.id:
                return True
            if not problem.is_public and current_user in problem.allowed_users:
                return True
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this problem"
        )

    def update_problem(self, problem_id: int, problem_update: ProblemUpdate, current_user):
        problem = self.get_problem(problem_id, current_user)
        self.check_edit_permission(problem, current_user)
        
        if problem_update.title and problem_update.title != problem.title:
            if self.problem_repo.get_problem_by_title(problem_update.title):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Problem title already exists"
                )
        if problem_update.tags is not None:
            problem_update.tags = [tag.strip() for tag in problem_update.tags if tag.strip()]
        try:
            return self.problem_repo.update_problem(problem, problem_update, updated_by=current_user.username)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    def add_user_to_allowed_list(self, problem_id: int, username: str, current_user):
        problem = self.get_problem(problem_id, current_user)
        self.check_edit_permission(problem, current_user)
        
        user_to_add = self.user_repo.get_user_by_username(username)
        if not user_to_add:
            raise HTTPException(status_code=404, detail="User not found")
        
        if user_to_add.role != UserRole.CREATOR:
             raise HTTPException(status_code=400, detail="Only creators can be added to the allowed list")
             
        return self.problem_repo.add_allowed_user(problem, user_to_add)

    def remove_user_from_allowed_list(self, problem_id: int, username: str, current_user):
        problem = self.get_problem(problem_id, current_user)
        self.check_edit_permission(problem, current_user)
        
        user_to_remove = self.user_repo.get_user_by_username(username)
        if not user_to_remove:
            raise HTTPException(status_code=404, detail="User not found")
            
        return self.problem_repo.remove_allowed_user(problem, user_to_remove)

    def delete_problem(self, problem_id: int, current_user):
        problem = self.get_problem(problem_id, current_user)
        self.check_edit_permission(problem, current_user)
        self.problem_repo.delete_problem(problem)

    def add_testcase(self, problem_id: int, testcase_create: TestcaseCreate, current_user):
        problem = self.get_problem(problem_id, current_user)
        self.check_edit_permission(problem, current_user)
        return self.problem_repo.add_testcase_to_problem(problem, testcase_create, current_user.username)

    def delete_testcase(self, problem_id: int, testcase_id: int, current_user):
        problem = self.get_problem(problem_id, current_user)
        self.check_edit_permission(problem, current_user)

        testcase = self.problem_repo.get_testcase_by_id(testcase_id)
        if not testcase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Testcase not found"
            )
        if testcase.problem_id != problem_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Testcase does not belong to this problem"
            )
        self.problem_repo.delete_testcase(testcase, problem, current_user.username)

    def create_submission(self, problem_id: int, submission_create: SubmissionCreate, user_id: int, username: str, current_user):
        # This ensures the user can see the problem before submitting
        self.get_problem(problem_id, current_user)
        return self.problem_repo.create_submission(problem_id, submission_create, user_id, username)

    def list_submissions(self, problem_id: int, current_user):
        problem = self.get_problem(problem_id, current_user)
        # Only admin or owner can see all submissions? User query didn't specify, 
        # but usually only admins/creators see all.
        if current_user.role not in [UserRole.ADMIN, UserRole.CREATOR]:
             raise HTTPException(status_code=403, detail="Not authorized to view submissions")
        return self.problem_repo.list_submissions_for_problem(problem_id)

    def get_submission(self, submission_id: int, current_user):
        submission = self.problem_repo.get_submission_by_id(submission_id)
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found"
            )
        # Check if user can see the problem
        self.get_problem(submission.problem_id, current_user)
        return submission

    def update_submission(self, submission_id: int, submission_update: SubmissionUpdate, current_user):
        submission = self.get_submission(submission_id, current_user)
        # Usually only admins/creators can update?
        if current_user.role not in [UserRole.ADMIN, UserRole.CREATOR]:
             raise HTTPException(status_code=403, detail="Not authorized to update submissions")
        return self.problem_repo.update_submission(submission, submission_update, updated_by=current_user.username)

    def delete_submission(self, submission_id: int, current_user):
        submission = self.get_submission(submission_id, current_user)
        if current_user.role not in [UserRole.ADMIN, UserRole.CREATOR]:
             raise HTTPException(status_code=403, detail="Not authorized to delete submissions")
        self.problem_repo.delete_submission(submission)

    def update_submission_status(self, submission_id: int, status_update: SubmissionStatusUpdate, current_user):
        submission = self.get_submission(submission_id, current_user)
        if current_user.role not in [UserRole.ADMIN, UserRole.CREATOR]:
             raise HTTPException(status_code=403, detail="Not authorized to update submission status")
        return self.problem_repo.update_submission_status(
            submission,
            status=status_update.status.value,
            updated_by=current_user.username
        )

    def group_problems_by_owner(self, current_user):
        problems = self.list_problems(current_user)
        grouped = {}
        for problem in problems:
            owner_username = problem.owner.username if problem.owner else "unknown"
            grouped.setdefault(owner_username, []).append(problem)

        grouped_results = []
        for owner, items in grouped.items():
            problem_dicts = [self._problem_to_dict(p) for p in items]
            grouped_results.append(
                ProblemsByOwnerOut(owner_username=owner, problems=problem_dicts)
            )
        return grouped_results

    def _serialize_problems(self, problems):
        # The model now has computed properties for tags and allowed_user_ids
        return problems

    def _problem_to_dict(self, problem):
        return {
            "id": problem.id,
            "title": problem.title,
            "description": problem.description,
            "constraints": problem.constraints,
            "difficulty": problem.difficulty,
            "testcases": [
                {"input": tc.input, "output": tc.output} for tc in problem.testcases
            ],
            "tags": [t.name for t in problem._tags],
            "is_published": problem.is_published,
            "is_public": problem.is_public,
            "owner_id": problem.owner_id,
            "created_by": problem.created_by,
            "updated_by": problem.updated_by,
            "update_time": problem.update_time,
            "created_at": problem.created_at,
            "allowed_user_ids": [u.id for u in problem.allowed_users]
        }

    def creator_problem_stats(self, current_user):
        problems = self.problem_repo.list_problems()
        counts = {}
        for problem in problems:
            owner_username = problem.owner.username if problem.owner else "unknown"
            counts[owner_username] = counts.get(owner_username, 0) + 1
        stats = [CreatorProblemStatsOut(username=owner, problem_count=count) for owner, count in counts.items()]
        stats.sort(key=lambda item: item.problem_count, reverse=True)
        return stats

    def list_tags(self, page: int = 1, page_size: int = 20, search: Optional[str] = None):
        skip = (page - 1) * page_size
        tags, total = self.problem_repo.list_tags(search=search, skip=skip, limit=page_size)
        
        # Calculate pagination info
        pages = (total + page_size - 1) // page_size
        has_next = page < pages
        has_prev = page > 1
        
        return {
            "items": tags,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }

    def create_tag(self, tag_name: str, current_user):
        existing = self.problem_repo.get_tag_by_name(tag_name)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tag already exists")
        return self.problem_repo.create_tag(tag_name, created_by=current_user.username)

    def problem_submission_stats(self, current_user):
        problems, _ = self.problem_repo.list_problems()
        submissions = self.problem_repo.list_all_submissions()
        counts = {}
        for submission in submissions:
            counts[submission.problem_id] = counts.get(submission.problem_id, 0) + 1
        return [
            ProblemSubmissionStatsOut(
                problem_id=problem.id,
                title=problem.title,
                submission_count=counts.get(problem.id, 0)
            )
            for problem in problems
        ]

    def get_editorial(self, problem_id: int, current_user):
        # Check if user can see problem first
        self.get_problem(problem_id, current_user)
        editorial = self.problem_repo.get_editorial_by_problem_id(problem_id)
        if not editorial:
            raise HTTPException(status_code=404, detail="Editorial not found for this problem")
        return editorial

    def create_editorial(self, problem_id: int, editorial_create: EditorialCreate, current_user):
        problem = self.get_problem(problem_id, current_user)
        self.check_edit_permission(problem, current_user)
        
        if self.problem_repo.get_editorial_by_problem_id(problem_id):
            raise HTTPException(status_code=400, detail="Editorial already exists for this problem")
            
        return self.problem_repo.create_editorial(problem_id, editorial_create, created_by=current_user.username)

    def update_editorial(self, problem_id: int, editorial_update: EditorialUpdate, current_user):
        problem = self.get_problem(problem_id, current_user)
        self.check_edit_permission(problem, current_user)
        
        editorial = self.problem_repo.get_editorial_by_problem_id(problem_id)
        if not editorial:
            raise HTTPException(status_code=404, detail="Editorial not found")
            
        return self.problem_repo.update_editorial(editorial, editorial_update, updated_by=current_user.username)

    def delete_editorial(self, problem_id: int, current_user):
        problem = self.get_problem(problem_id, current_user)
        self.check_edit_permission(problem, current_user)
        
        editorial = self.problem_repo.get_editorial_by_problem_id(problem_id)
        if not editorial:
            raise HTTPException(status_code=404, detail="Editorial not found")
            
        self.problem_repo.delete_editorial(editorial)

    # Vote-related service methods
    def vote_problem(self, problem_id: int, vote_create: VoteCreate, user_id: int):
        logger.debug(f"Voting on problem: problem_id={problem_id}, user_id={user_id}, vote_type={vote_create.vote_type}")
        # Verify problem exists and is accessible
        problem = self.get_problem(problem_id, None)
        if not problem.is_published:
            logger.warning(f"Cannot vote on unpublished problem: problem_id={problem_id}")
            raise HTTPException(status_code=403, detail="Cannot vote on unpublished problems")
        
        vote = self.problem_repo.create_or_update_vote(
            user_id=user_id,
            target_id=problem_id,
            target_type="problem",
            vote_type=vote_create.vote_type.value
        )
        logger.debug(f"Vote recorded: vote_id={vote.id}")
        return vote

    def delete_problem_vote(self, problem_id: int, user_id: int):
        # Verify problem exists
        self.get_problem(problem_id, None)
        
        deleted = self.problem_repo.delete_vote(
            user_id=user_id,
            target_id=problem_id,
            target_type="problem"
        )
        if not deleted:
            raise HTTPException(status_code=404, detail="Vote not found")
        return {"message": "Vote removed successfully"}

    def vote_editorial(self, problem_id: int, vote_create: VoteCreate, user_id: int):
        # Verify problem and editorial exist
        problem = self.get_problem(problem_id, None)
        if not problem.is_published:
            raise HTTPException(status_code=403, detail="Cannot vote on unpublished problem editorials")
        
        editorial = self.problem_repo.get_editorial_by_problem_id(problem_id)
        if not editorial:
            raise HTTPException(status_code=404, detail="Editorial not found")
        
        vote = self.problem_repo.create_or_update_vote(
            user_id=user_id,
            target_id=editorial.id,
            target_type="editorial",
            vote_type=vote_create.vote_type.value
        )
        return vote

    def delete_editorial_vote(self, problem_id: int, user_id: int):
        # Verify problem and editorial exist
        self.get_problem(problem_id, None)
        editorial = self.problem_repo.get_editorial_by_problem_id(problem_id)
        if not editorial:
            raise HTTPException(status_code=404, detail="Editorial not found")
        
        deleted = self.problem_repo.delete_vote(
            user_id=user_id,
            target_id=editorial.id,
            target_type="editorial"
        )
        if not deleted:
            raise HTTPException(status_code=404, detail="Vote not found")
        return {"message": "Vote removed successfully"}

    def get_problem_vote_stats(self, problem_id: int) -> ProblemVoteStatsOut:
        problem = self.problem_repo.get_problem_by_id(problem_id)
        if not problem:
            raise HTTPException(status_code=404, detail="Problem not found")
        
        stats = self.problem_repo.get_vote_stats(problem_id, "problem")
        return ProblemVoteStatsOut(
            problem_id=problem_id,
            title=problem.title,
            votes=VoteStats(**stats)
        )

    def get_editorial_vote_stats(self, problem_id: int) -> EditorialVoteStatsOut:
        problem = self.problem_repo.get_problem_by_id(problem_id)
        if not problem:
            raise HTTPException(status_code=404, detail="Problem not found")
        
        editorial = self.problem_repo.get_editorial_by_problem_id(problem_id)
        if not editorial:
            raise HTTPException(status_code=404, detail="Editorial not found")
        
        stats = self.problem_repo.get_vote_stats(editorial.id, "editorial")
        return EditorialVoteStatsOut(
            editorial_id=editorial.id,
            problem_id=problem_id,
            votes=VoteStats(**stats)
        )

    def get_creator_vote_stats(self, current_user) -> list[CreatorVoteStatsOut]:
        """Get vote statistics grouped by creator."""
        logger.debug(f"Getting creator vote stats for user: {current_user.username}")
        # Only admin and creator can see these stats
        if current_user.role not in [UserRole.ADMIN, UserRole.CREATOR]:
            logger.warning(f"Unauthorized access to creator stats: {current_user.username}")
            raise HTTPException(status_code=403, detail="Not authorized to view creator stats")
        
        # Get all problems with their owners
        problems, _ = self.problem_repo.list_problems()
        
        # Group problems by creator
        creator_problems = {}
        for problem in problems:
            owner = problem.owner
            if not owner:
                continue
            
            if owner.username not in creator_problems:
                creator_problems[owner.username] = []
            creator_problems[owner.username].append(problem)
        
        # Get vote stats for all problems
        problem_ids = [p.id for p in problems]
        vote_stats = self.problem_repo.get_votes_by_target_ids(problem_ids, "problem")
        
        # Build creator stats
        results = []
        for username, probs in creator_problems.items():
            problem_stats = []
            total_likes = 0
            total_dislikes = 0
            total_votes = 0
            
            for problem in probs:
                stats = vote_stats.get(problem.id, {"likes": 0, "dislikes": 0, "total": 0, "like_rate": 0.0})
                total_likes += stats["likes"]
                total_dislikes += stats["dislikes"]
                total_votes += stats["total"]
                
                problem_stats.append(ProblemVoteStatsOut(
                    problem_id=problem.id,
                    title=problem.title,
                    votes=VoteStats(**stats)
                ))
            
            overall_like_rate = total_likes / total_votes if total_votes > 0 else 0.0
            
            results.append(CreatorVoteStatsOut(
                username=username,
                total_problems=len(probs),
                total_likes=total_likes,
                total_dislikes=total_dislikes,
                total_votes=total_votes,
                overall_like_rate=round(overall_like_rate, 4),
                problems=problem_stats
            ))
        
        # Sort by overall like rate (descending), then by total likes
        results.sort(key=lambda x: (-x.overall_like_rate, -x.total_likes))
        return results

