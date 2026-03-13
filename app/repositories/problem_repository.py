from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.problem import Problem, Testcase, Submission, Tag, Editorial, Vote
from app.models.user import User
from app.schemas import ProblemCreate, ProblemUpdate, SubmissionCreate, SubmissionUpdate, EditorialCreate, EditorialUpdate, TestcaseCreate
from app.core.config import get_logger

logger = get_logger(__name__)

class ProblemRepository:
    def __init__(self, db: Session):
        self.db = db
        logger.debug("ProblemRepository initialized")

    def create_problem(self, problem_create: ProblemCreate, owner_id: int, created_by: str) -> Problem:
        logger.debug(f"Creating problem in database: title='{problem_create.title}', owner_id={owner_id}")
        problem = Problem(
            title=problem_create.title,
            description=problem_create.description,
            constraints=problem_create.constraints,
            difficulty=problem_create.difficulty,
            is_published=problem_create.is_published,
            is_public=problem_create.is_public,
            owner_id=owner_id,
            created_by=created_by,
            updated_by=created_by
        )
        self.db.add(problem)
        self.db.flush()

        for testcase in problem_create.testcases:
            self.db.add(Testcase(problem_id=problem.id, input=testcase.input, output=testcase.output))

        if problem_create.tags:
            tags = self.get_tags_by_names(problem_create.tags)
            existing_names = {tag.name for tag in tags}
            missing = [name for name in problem_create.tags if name not in existing_names]
            if missing:
                raise ValueError(f"Tags not found: {', '.join(missing)}")
            problem._tags = tags

        self.db.commit()
        self.db.refresh(problem)
        logger.debug(f"Problem created in database: id={problem.id}, title='{problem.title}'")
        return problem

    def get_problem_by_id(self, problem_id: int):
        return self.db.query(Problem).filter(Problem.id == problem_id).first()

    def get_problem_by_title(self, title: str):
        return self.db.query(Problem).filter(Problem.title == title).first()

    def list_problems(self, skip: int = 0, limit: int = 100, search: Optional[str] = None):
        query = self.db.query(Problem)
        if search:
            query = query.filter(
                (Problem.title.ilike(f"%{search}%")) |
                (Problem.description.ilike(f"%{search}%"))
            )
        total = query.count()
        problems = query.offset(skip).limit(limit).all()
        return problems, total

    def list_problems_created_in_date_range(self, start_date: datetime, end_date: datetime, skip: int = 0, limit: int = 100):
        query = (
            self.db.query(Problem)
            .filter(Problem.created_at >= start_date)
            .filter(Problem.created_at <= end_date)
        )
        total = query.count()
        problems = query.offset(skip).limit(limit).all()
        return problems, total

    def list_problems_by_tag(self, tag_name: str, skip: int = 0, limit: int = 100):
        query = (
            self.db.query(Problem)
            .join(Problem._tags)
            .filter(Tag.name == tag_name)
        )
        total = query.count()
        problems = query.offset(skip).limit(limit).all()
        return problems, total

    def get_tag_by_name(self, name: str):
        return self.db.query(Tag).filter(Tag.name == name).first()

    def get_tags_by_names(self, names: list[str]):
        return self.db.query(Tag).filter(Tag.name.in_(names)).all()

    def list_tags(self, search: Optional[str] = None, skip: int = 0, limit: int = 100):
        query = self.db.query(Tag)
        if search:
            query = query.filter(Tag.name.ilike(f"%{search}%"))
        total = query.count()
        tags = query.offset(skip).limit(limit).all()
        return tags, total

    def create_tag(self, name: str, created_by: str):
        tag = Tag(name=name, created_by=created_by, updated_by=created_by)
        self.db.add(tag)
        self.db.commit()
        self.db.refresh(tag)
        return tag

    def add_tags_to_problem(self, problem: Problem, tags: list[Tag], updated_by: str):
        problem._tags = tags
        problem.updated_by = updated_by
        self.db.commit()
        self.db.refresh(problem)
        return problem

    def update_problem(self, problem: Problem, problem_update: ProblemUpdate, updated_by: str):
        if problem_update.title is not None:
            problem.title = problem_update.title
        if problem_update.description is not None:
            problem.description = problem_update.description
        if problem_update.constraints is not None:
            problem.constraints = problem_update.constraints
        if problem_update.difficulty is not None:
            problem.difficulty = problem_update.difficulty
        if problem_update.is_published is not None:
            problem.is_published = problem_update.is_published
        if problem_update.is_public is not None:
            problem.is_public = problem_update.is_public
        if problem_update.testcases is not None:
            problem.testcases.clear()
            for testcase in problem_update.testcases:
                problem.testcases.append(Testcase(input=testcase.input, output=testcase.output))
        if problem_update.tags is not None:
            tags = self.get_tags_by_names(problem_update.tags)
            existing_names = {tag.name for tag in tags}
            missing = [name for name in problem_update.tags if name not in existing_names]
            if missing:
                raise ValueError(f"Tags not found: {', '.join(missing)}")
            problem._tags = tags
        problem.updated_by = updated_by
        self.db.commit()
        self.db.refresh(problem)
        return problem

    def get_testcase_by_id(self, testcase_id: int):
        return self.db.query(Testcase).filter(Testcase.id == testcase_id).first()

    def add_testcase_to_problem(self, problem: Problem, testcase_create: TestcaseCreate, updated_by: str):
        testcase = Testcase(
            problem_id=problem.id,
            input=testcase_create.input,
            output=testcase_create.output
        )
        self.db.add(testcase)
        problem.updated_by = updated_by
        self.db.commit()
        self.db.refresh(testcase)
        return testcase

    def delete_testcase(self, testcase: Testcase, problem: Problem, updated_by: str):
        self.db.delete(testcase)
        problem.updated_by = updated_by
        self.db.commit()

    def add_allowed_user(self, problem: Problem, user: User):
        if user not in problem.allowed_users:
            problem.allowed_users.append(user)
            self.db.commit()
            self.db.refresh(problem)
        return problem

    def remove_allowed_user(self, problem: Problem, user: User):
        if user in problem.allowed_users:
            problem.allowed_users.remove(user)
            self.db.commit()
            self.db.refresh(problem)
        return problem

    def delete_problem(self, problem: Problem):
        self.db.delete(problem)
        self.db.commit()

    def create_submission(self, problem_id: int, submission_create: SubmissionCreate, user_id: int, username: str, contest_id: Optional[int] = None, is_contest_submission: bool = False, is_late_submission: bool = False):
        submission = Submission(
            problem_id=problem_id,
            user_id=user_id,
            username=username,
            programming_language=submission_create.programming_language,
            code=submission_create.code,
            status="PENDING",
            created_by=username,
            updated_by=username,
            contest_id=contest_id,
            is_contest_submission=is_contest_submission,
            is_late_submission=is_late_submission
        )
        self.db.add(submission)
        self.db.commit()
        self.db.refresh(submission)
        return submission

    def list_submissions_for_problem(self, problem_id: int, exclude_contest_submissions: bool = False):
        """List submissions for a problem.
        
        Args:
            problem_id: The problem ID
            exclude_contest_submissions: If True, exclude submissions made during contests
        """
        query = self.db.query(Submission).filter(Submission.problem_id == problem_id)
        if exclude_contest_submissions:
            query = query.filter(Submission.is_contest_submission == False)
        return query.all()

    def list_submissions_for_contest(self, contest_id: int, problem_id: Optional[int] = None):
        """List submissions for a contest.
        
        Args:
            contest_id: The contest ID
            problem_id: Optional problem ID to filter by
        """
        query = self.db.query(Submission).filter(
            Submission.contest_id == contest_id,
            Submission.is_contest_submission == True
        )
        if problem_id:
            query = query.filter(Submission.problem_id == problem_id)
        return query.all()

    def list_submissions_for_problem_in_contest(self, problem_id: int, contest_id: int):
        """List submissions for a specific problem within a specific contest."""
        return self.db.query(Submission).filter(
            Submission.problem_id == problem_id,
            Submission.contest_id == contest_id,
            Submission.is_contest_submission == True
        ).all()

    def list_all_submissions(self):
        return self.db.query(Submission).all()

    def list_submissions_in_date_range(self, start_date: datetime, end_date: datetime):
        return (
            self.db.query(Submission)
            .filter(Submission.submission_time >= start_date)
            .filter(Submission.submission_time <= end_date)
            .all()
        )

    def get_user_submissions_in_date_range(self, user_id: int, start_date: datetime, end_date: datetime):
        """Get all submissions for a user within a date range."""
        return (
            self.db.query(Submission)
            .filter(Submission.user_id == user_id)
            .filter(Submission.submission_time >= start_date)
            .filter(Submission.submission_time <= end_date)
            .order_by(Submission.submission_time.asc())
            .all()
        )

    def get_user_accepted_submissions(self, user_id: int):
        """Get all accepted submissions for a user ordered by date."""
        return (
            self.db.query(Submission)
            .filter(Submission.user_id == user_id)
            .filter(Submission.status == "ACCEPTED")
            .order_by(Submission.submission_time.asc())
            .all()
        )

    def get_submission_by_id(self, submission_id: int):
        return self.db.query(Submission).filter(Submission.id == submission_id).first()

    def update_submission(self, submission: Submission, submission_update: SubmissionUpdate, updated_by: str):
        if submission_update.programming_language is not None:
            submission.programming_language = submission_update.programming_language
        if submission_update.code is not None:
            submission.code = submission_update.code
        submission.updated_by = updated_by
        self.db.commit()
        self.db.refresh(submission)
        return submission

    def update_submission_status(self, submission: Submission, status: str, updated_by: str):
        submission.status = status
        submission.updated_by = updated_by
        self.db.commit()
        self.db.refresh(submission)
        return submission

    def delete_submission(self, submission: Submission):
        self.db.delete(submission)
        self.db.commit()

    def get_editorial_by_problem_id(self, problem_id: int):
        return self.db.query(Editorial).filter(Editorial.problem_id == problem_id).first()

    def create_editorial(self, problem_id: int, editorial_create: EditorialCreate, created_by: str):
        editorial = Editorial(
            problem_id=problem_id,
            description=editorial_create.description,
            code_solution=editorial_create.code_solution,
            created_by=created_by,
            updated_by=created_by
        )
        self.db.add(editorial)
        self.db.commit()
        self.db.refresh(editorial)
        return editorial

    def update_editorial(self, editorial: Editorial, editorial_update: EditorialUpdate, updated_by: str):
        if editorial_update.description is not None:
            editorial.description = editorial_update.description
        if editorial_update.code_solution is not None:
            editorial.code_solution = editorial_update.code_solution
        editorial.updated_by = updated_by
        self.db.commit()
        self.db.refresh(editorial)
        return editorial

    def delete_editorial(self, editorial: Editorial):
        self.db.delete(editorial)
        self.db.commit()

    # Vote-related methods
    def get_vote(self, user_id: int, target_id: int, target_type: str) -> Optional[Vote]:
        return self.db.query(Vote).filter(
            Vote.user_id == user_id,
            Vote.target_id == target_id,
            Vote.target_type == target_type
        ).first()

    def create_or_update_vote(self, user_id: int, target_id: int, target_type: str, vote_type: str) -> Vote:
        logger.debug(f"Creating/updating vote: user_id={user_id}, target_id={target_id}, target_type={target_type}, vote_type={vote_type}")
        vote = self.get_vote(user_id, target_id, target_type)
        if vote:
            logger.debug(f"Updating existing vote: vote_id={vote.id}, old_type={vote.vote_type}, new_type={vote_type}")
            vote.vote_type = vote_type
        else:
            logger.debug(f"Creating new vote for user_id={user_id}")
            vote = Vote(
                user_id=user_id,
                target_id=target_id,
                target_type=target_type,
                vote_type=vote_type
            )
            self.db.add(vote)
        self.db.commit()
        self.db.refresh(vote)
        logger.debug(f"Vote saved: vote_id={vote.id}")
        return vote

    def delete_vote(self, user_id: int, target_id: int, target_type: str) -> bool:
        vote = self.get_vote(user_id, target_id, target_type)
        if vote:
            self.db.delete(vote)
            self.db.commit()
            return True
        return False

    def get_vote_stats(self, target_id: int, target_type: str) -> dict:
        likes = self.db.query(func.count(Vote.id)).filter(
            Vote.target_id == target_id,
            Vote.target_type == target_type,
            Vote.vote_type == "like"
        ).scalar() or 0

        dislikes = self.db.query(func.count(Vote.id)).filter(
            Vote.target_id == target_id,
            Vote.target_type == target_type,
            Vote.vote_type == "dislike"
        ).scalar() or 0

        total = likes + dislikes
        like_rate = likes / total if total > 0 else 0.0

        return {
            "likes": likes,
            "dislikes": dislikes,
            "total": total,
            "like_rate": round(like_rate, 4)
        }

    def get_votes_by_target_ids(self, target_ids: list[int], target_type: str) -> dict[int, dict]:
        """Get vote stats for multiple targets at once."""
        if not target_ids:
            return {}

        votes = self.db.query(Vote).filter(
            Vote.target_id.in_(target_ids),
            Vote.target_type == target_type
        ).all()

        stats = {}
        for target_id in target_ids:
            stats[target_id] = {"likes": 0, "dislikes": 0, "total": 0, "like_rate": 0.0}

        for vote in votes:
            if vote.vote_type == "like":
                stats[vote.target_id]["likes"] += 1
            else:
                stats[vote.target_id]["dislikes"] += 1
            stats[vote.target_id]["total"] += 1

        for target_id in target_ids:
            total = stats[target_id]["total"]
            if total > 0:
                stats[target_id]["like_rate"] = round(stats[target_id]["likes"] / total, 4)

        return stats

    def get_editorial_by_id(self, editorial_id: int) -> Optional[Editorial]:
        return self.db.query(Editorial).filter(Editorial.id == editorial_id).first()
