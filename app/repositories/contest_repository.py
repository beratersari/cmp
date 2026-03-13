from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.contest import Contest, ContestProblem, ContestType, ContestManager
from app.models.problem import Problem
from app.schemas import ContestCreate, ContestUpdate
from app.core.config import get_logger

logger = get_logger(__name__)


class ContestRepository:
    def __init__(self, db: Session):
        self.db = db
        logger.debug("ContestRepository initialized")

    def create_contest(self, contest_create: ContestCreate, owner_id: int, created_by: str) -> Contest:
        logger.debug(f"Creating contest in database: title='{contest_create.title}', owner_id={owner_id}")
        contest = Contest(
            title=contest_create.title,
            description=contest_create.description,
            start_date=contest_create.start_date,
            end_date=contest_create.end_date,
            contest_type=contest_create.contest_type.value,
            owner_id=owner_id,
            created_by=created_by,
            updated_by=created_by
        )
        
        self.db.add(contest)
        self.db.flush()  # Get the contest ID
        
        # Add problems if provided (with ordering)
        if contest_create.problem_ids:
            for order, problem_id in enumerate(contest_create.problem_ids):
                contest_problem = ContestProblem(
                    contest_id=contest.id,
                    problem_id=problem_id,
                    order=order
                )
                self.db.add(contest_problem)
        
        self.db.commit()
        self.db.refresh(contest)
        logger.debug(f"Contest created in database: id={contest.id}, title='{contest.title}'")
        return contest

    def get_contest_by_id(self, contest_id: int) -> Optional[Contest]:
        return self.db.query(Contest).filter(Contest.id == contest_id).first()

    def list_contests(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        contest_type: Optional[ContestType] = None,
        owner_id: Optional[int] = None,
        exclude_archived: bool = True
    ):
        query = self.db.query(Contest)
        
        # By default, exclude archived contests from public listings
        if exclude_archived:
            query = query.filter(Contest.contest_type != ContestType.ARCHIVED.value)
        
        if search:
            query = query.filter(
                (Contest.title.ilike(f"%{search}%")) |
                (Contest.description.ilike(f"%{search}%"))
            )
        
        if contest_type is not None:
            query = query.filter(Contest.contest_type == contest_type.value)
        
        if owner_id is not None:
            query = query.filter(Contest.owner_id == owner_id)
        
        total = query.count()
        contests = query.order_by(Contest.start_date.desc()).offset(skip).limit(limit).all()
        return contests, total

    def list_upcoming_contests(self, current_time: datetime, skip: int = 0, limit: int = 100):
        """List contests that haven't started yet (public and private only)."""
        query = self.db.query(Contest).filter(
            Contest.start_date > current_time,
            Contest.contest_type.in_([ContestType.PUBLIC.value, ContestType.PRIVATE.value])
        )
        total = query.count()
        contests = query.order_by(Contest.start_date.asc()).offset(skip).limit(limit).all()
        return contests, total

    def list_active_contests(self, current_time: datetime, skip: int = 0, limit: int = 100):
        """List contests that are currently running (public and private only)."""
        query = self.db.query(Contest).filter(
            Contest.start_date <= current_time,
            Contest.end_date > current_time,
            Contest.contest_type.in_([ContestType.PUBLIC.value, ContestType.PRIVATE.value])
        )
        total = query.count()
        contests = query.order_by(Contest.end_date.asc()).offset(skip).limit(limit).all()
        return contests, total

    def list_past_contests(self, current_time: datetime, skip: int = 0, limit: int = 100):
        """List contests that have ended (public and private only)."""
        query = self.db.query(Contest).filter(
            Contest.end_date <= current_time,
            Contest.contest_type.in_([ContestType.PUBLIC.value, ContestType.PRIVATE.value])
        )
        total = query.count()
        contests = query.order_by(Contest.end_date.desc()).offset(skip).limit(limit).all()
        return contests, total

    def update_contest(self, contest: Contest, contest_update: ContestUpdate, updated_by: str) -> Contest:
        if contest_update.title is not None:
            contest.title = contest_update.title
        if contest_update.description is not None:
            contest.description = contest_update.description
        if contest_update.start_date is not None:
            contest.start_date = contest_update.start_date
        if contest_update.end_date is not None:
            contest.end_date = contest_update.end_date
        if contest_update.contest_type is not None:
            contest.contest_type = contest_update.contest_type.value
        
        contest.updated_by = updated_by
        self.db.commit()
        self.db.refresh(contest)
        return contest

    def add_problems_to_contest(self, contest: Contest, problem_ids: list[int], updated_by: str) -> Contest:
        """Add problems to a contest with proper ordering."""
        # Get current max order
        max_order = max([cp.order for cp in contest.contest_problems], default=-1)
        
        existing_problem_ids = {cp.problem_id for cp in contest.contest_problems}
        
        for i, problem_id in enumerate(problem_ids):
            if problem_id not in existing_problem_ids:
                contest_problem = ContestProblem(
                    contest_id=contest.id,
                    problem_id=problem_id,
                    order=max_order + 1 + i
                )
                self.db.add(contest_problem)
        
        contest.updated_by = updated_by
        self.db.commit()
        self.db.refresh(contest)
        return contest

    def remove_problems_from_contest(self, contest: Contest, problem_ids: list[int], updated_by: str) -> Contest:
        """Remove problems from a contest."""
        # Delete the ContestProblem entries
        self.db.query(ContestProblem).filter(
            ContestProblem.contest_id == contest.id,
            ContestProblem.problem_id.in_(problem_ids)
        ).delete(synchronize_session=False)
        
        # Re-order remaining problems to maintain sequential order
        remaining = self.db.query(ContestProblem).filter(
            ContestProblem.contest_id == contest.id
        ).order_by(ContestProblem.order).all()
        
        for i, cp in enumerate(remaining):
            cp.order = i
        
        contest.updated_by = updated_by
        self.db.commit()
        self.db.refresh(contest)
        return contest

    def reorder_problems(self, contest: Contest, problem_orders: list[dict], updated_by: str) -> Contest:
        """Reorder problems in a contest.
        
        Args:
            contest: The contest to reorder
            problem_orders: List of dicts with 'problem_id' and 'order' keys
            updated_by: Username of the user making the change
        """
        for item in problem_orders:
            contest_problem = self.db.query(ContestProblem).filter(
                ContestProblem.contest_id == contest.id,
                ContestProblem.problem_id == item['problem_id']
            ).first()
            if contest_problem:
                contest_problem.order = item['order']
        
        contest.updated_by = updated_by
        self.db.commit()
        self.db.refresh(contest)
        return contest

    def delete_contest(self, contest: Contest):
        self.db.delete(contest)
        self.db.commit()

    # Contest Manager methods
    def get_contest_manager(self, contest_id: int, user_id: int) -> Optional[ContestManager]:
        """Get a specific contest manager entry."""
        return self.db.query(ContestManager).filter(
            ContestManager.contest_id == contest_id,
            ContestManager.user_id == user_id
        ).first()

    def add_manager_to_contest(self, contest_id: int, user_id: int, added_by: int) -> ContestManager:
        """Add a user as a manager to a contest."""
        manager = ContestManager(
            contest_id=contest_id,
            user_id=user_id,
            added_by=added_by
        )
        self.db.add(manager)
        self.db.commit()
        self.db.refresh(manager)
        return manager

    def remove_manager_from_contest(self, contest_id: int, user_id: int) -> bool:
        """Remove a manager from a contest."""
        manager = self.get_contest_manager(contest_id, user_id)
        if manager:
            self.db.delete(manager)
            self.db.commit()
            return True
        return False

    def list_contest_managers(self, contest_id: int) -> list[ContestManager]:
        """List all managers for a contest."""
        return self.db.query(ContestManager).filter(
            ContestManager.contest_id == contest_id
        ).all()

    def is_user_manager(self, contest_id: int, user_id: int) -> bool:
        """Check if a user is a manager of a contest."""
        return self.get_contest_manager(contest_id, user_id) is not None
