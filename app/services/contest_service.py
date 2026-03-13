from typing import Optional
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.contest_repository import ContestRepository
from app.repositories.contest_registration_repository import ContestRegistrationRepository
from app.repositories.contest_announcement_repository import ContestAnnouncementRepository, ContestTicketRepository
from app.repositories.problem_repository import ProblemRepository
from app.schemas import (
    ContestCreate,
    ContestUpdate,
    ContestOut,
    ContestDetailOut,
    ContestProblemOut,
    ContestRegistrationOut,
    ContestRegistrationSummaryOut,
    UserRegistrationOut,
    ContestAnnouncementCreate,
    ContestAnnouncementUpdate,
    ContestAnnouncementOut,
    SubmissionCreate,
    SubmissionOut,
    ContestTicketCreate,
    ContestTicketUpdate,
    ContestTicketOut,
    ContestTicketSummaryOut,
    ContestTicketResponseCreate,
    ContestTicketResponseOut,
)
from app.models.user import UserRole
from app.models.contest import ContestType, ContestRegistrationStatus, ContestTicketStatus
from app.core.config import get_logger

logger = get_logger(__name__)


class ContestService:
    def __init__(self, db: Session):
        self.contest_repo = ContestRepository(db)
        self.registration_repo = ContestRegistrationRepository(db)
        self.announcement_repo = ContestAnnouncementRepository(db)
        self.ticket_repo = ContestTicketRepository(db)
        self.problem_repo = ProblemRepository(db)
        logger.debug("ContestService initialized")

    def create_contest(self, contest_create: ContestCreate, owner_id: int, created_by: str):
        logger.debug(f"Creating contest: title='{contest_create.title}', owner_id={owner_id}")
        
        # Validate problem IDs if provided
        if contest_create.problem_ids:
            self._validate_problem_ids(contest_create.problem_ids)
        
        contest = self.contest_repo.create_contest(contest_create, owner_id, created_by)
        logger.debug(f"Contest created: id={contest.id}, title='{contest.title}'")
        return contest

    def _validate_problem_ids(self, problem_ids: list[int]):
        """Validate that all problem IDs exist."""
        for problem_id in problem_ids:
            problem = self.problem_repo.get_problem_by_id(problem_id)
            if not problem:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Problem with id {problem_id} not found"
                )

    def list_contests(
        self,
        current_user=None,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        contest_type: Optional[ContestType] = None
    ):
        skip = (page - 1) * page_size
        
        # Determine if we should include archived contests
        exclude_archived = True
        if current_user and current_user.role == UserRole.ADMIN:
            exclude_archived = False
        
        contests, total = self.contest_repo.list_contests(
            skip=skip,
            limit=page_size,
            search=search,
            contest_type=contest_type,
            exclude_archived=exclude_archived
        )
        
        # Filter for visibility based on contest_type
        filtered = []
        for c in contests:
            # Archived contests only visible to owner/admin
            if c.is_archived:
                if current_user and (current_user.role == UserRole.ADMIN or c.owner_id == current_user.id):
                    filtered.append(c)
            # Public and private contests visible to everyone
            else:
                filtered.append(c)
        
        # Calculate pagination info
        pages = (len(filtered) + page_size - 1) // page_size
        has_next = page < pages
        has_prev = page > 1
        
        return {
            "items": [self._to_contest_out(c) for c in filtered],
            "total": len(filtered),
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }

    def list_upcoming_contests(self, current_user=None, page: int = 1, page_size: int = 20):
        """List contests that haven't started yet."""
        skip = (page - 1) * page_size
        current_time = datetime.utcnow()
        
        contests, total = self.contest_repo.list_upcoming_contests(
            current_time, skip=skip, limit=page_size
        )
        
        pages = (total + page_size - 1) // page_size
        has_next = page < pages
        has_prev = page > 1
        
        return {
            "items": [self._to_contest_out(c) for c in contests],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }

    def list_active_contests(self, current_user=None, page: int = 1, page_size: int = 20):
        """List contests that are currently running."""
        skip = (page - 1) * page_size
        current_time = datetime.utcnow()
        
        contests, total = self.contest_repo.list_active_contests(
            current_time, skip=skip, limit=page_size
        )
        
        pages = (total + page_size - 1) // page_size
        has_next = page < pages
        has_prev = page > 1
        
        return {
            "items": [self._to_contest_out(c) for c in contests],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }

    def list_past_contests(self, current_user=None, page: int = 1, page_size: int = 20):
        """List contests that have ended."""
        skip = (page - 1) * page_size
        current_time = datetime.utcnow()
        
        contests, total = self.contest_repo.list_past_contests(
            current_time, skip=skip, limit=page_size
        )
        
        pages = (total + page_size - 1) // page_size
        has_next = page < pages
        has_prev = page > 1
        
        return {
            "items": [self._to_contest_out(c) for c in contests],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }

    def get_contest(self, contest_id: int, current_user=None):
        contest = self.contest_repo.get_contest_by_id(contest_id)
        if not contest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contest not found"
            )
        
        # Check visibility based on contest_type
        is_owner = current_user and contest.owner_id == current_user.id
        is_admin = current_user and current_user.role == UserRole.ADMIN
        
        # Archived contests only visible to owner or admin
        if contest.is_archived:
            if not (is_owner or is_admin):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Contest is archived"
                )
        
        return contest

    def get_contest_detail(self, contest_id: int, current_user=None) -> ContestDetailOut:
        contest = self.get_contest(contest_id, current_user)
        
        # Determine if user can see problems
        can_see_problems = self._can_user_see_problems(contest, current_user)
        
        return self._to_contest_detail_out(contest, include_problems=can_see_problems)

    def _can_user_see_problems(self, contest, current_user) -> bool:
        """Check if user can see problems in a contest."""
        # Managers (owner, admin, or manager) can always see problems
        if self.has_manager_access(contest, current_user):
            return True
        
        # Public contests: everyone can see problems
        if contest.is_public:
            return True
        
        # Private contests: only registered users can see problems
        if contest.is_private:
            if current_user:
                return self.registration_repo.is_user_registered(contest.id, current_user.id)
            return False
        
        # Archived contests: already handled above, but default to False
        return False

    def check_edit_permission(self, contest, current_user):
        """Check if the user has permission to edit the contest.
        
        Users with edit permission:
        - Admins
        - Contest owner
        - Contest managers (collaborators)
        """
        if current_user.role == UserRole.ADMIN:
            return True
        if contest.owner_id == current_user.id:
            return True
        # Check if user is a manager
        if self.contest_repo.is_user_manager(contest.id, current_user.id):
            return True
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this contest"
        )

    def has_manager_access(self, contest, current_user) -> bool:
        """Check if user has manager-level access to the contest.
        
        Users with manager access:
        - Admins
        - Contest owner
        - Contest managers (collaborators)
        """
        if not current_user:
            return False
        if current_user.role == UserRole.ADMIN:
            return True
        if contest.owner_id == current_user.id:
            return True
        if self.contest_repo.is_user_manager(contest.id, current_user.id):
            return True
        return False

    def update_contest(self, contest_id: int, contest_update: ContestUpdate, current_user):
        contest = self.get_contest(contest_id, current_user)
        self.check_edit_permission(contest, current_user)
        
        # Validate dates if both are provided
        start_date = contest_update.start_date or contest.start_date
        end_date = contest_update.end_date or contest.end_date
        if end_date <= start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after start date"
            )
        
        return self.contest_repo.update_contest(contest, contest_update, updated_by=current_user.username)

    def add_problems_to_contest(self, contest_id: int, problem_ids: list[int], current_user):
        contest = self.get_contest(contest_id, current_user)
        self.check_edit_permission(contest, current_user)
        
        # Validate problem IDs
        self._validate_problem_ids(problem_ids)
        
        return self.contest_repo.add_problems_to_contest(contest, problem_ids, updated_by=current_user.username)

    def remove_problems_from_contest(self, contest_id: int, problem_ids: list[int], current_user):
        contest = self.get_contest(contest_id, current_user)
        self.check_edit_permission(contest, current_user)
        
        return self.contest_repo.remove_problems_from_contest(contest, problem_ids, updated_by=current_user.username)

    def reorder_problems(self, contest_id: int, problem_orders: list[dict], current_user):
        """Reorder problems in a contest.
        
        Args:
            contest_id: ID of the contest
            problem_orders: List of dicts with 'problem_id' and 'order' keys
            current_user: The user making the request
        """
        contest = self.get_contest(contest_id, current_user)
        self.check_edit_permission(contest, current_user)
        
        # Validate that all problem IDs are in the contest
        contest_problem_ids = {cp.problem_id for cp in contest.contest_problems}
        for item in problem_orders:
            if item['problem_id'] not in contest_problem_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Problem with id {item['problem_id']} is not in this contest"
                )
        
        return self.contest_repo.reorder_problems(contest, problem_orders, updated_by=current_user.username)

    def delete_contest(self, contest_id: int, current_user):
        contest = self.get_contest(contest_id, current_user)
        self.check_edit_permission(contest, current_user)
        self.contest_repo.delete_contest(contest)

    # Contest Manager methods
    def add_contest_manager(self, contest_id: int, user_id: int, current_user):
        """Add a manager to a contest.
        
        Only admins and contest owners can add managers.
        """
        contest = self.get_contest(contest_id, current_user)
        
        # Only owner and admin can add managers
        is_owner = contest.owner_id == current_user.id
        is_admin = current_user.role == UserRole.ADMIN
        
        if not (is_owner or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only contest owner or admin can add managers"
            )
        
        # Check if user is already a manager
        if self.contest_repo.is_user_manager(contest_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a manager of this contest"
            )
        
        # Can't add owner as manager (they already have full access)
        if user_id == contest.owner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot add contest owner as manager"
            )
        
        manager = self.contest_repo.add_manager_to_contest(contest_id, user_id, current_user.id)
        return self._to_manager_out(manager)

    def remove_contest_manager(self, contest_id: int, user_id: int, current_user):
        """Remove a manager from a contest.
        
        Only admins and contest owners can remove managers.
        """
        contest = self.get_contest(contest_id, current_user)
        
        # Only owner and admin can remove managers
        is_owner = contest.owner_id == current_user.id
        is_admin = current_user.role == UserRole.ADMIN
        
        if not (is_owner or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only contest owner or admin can remove managers"
            )
        
        # Check if user is a manager
        if not self.contest_repo.is_user_manager(contest_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not a manager of this contest"
            )
        
        self.contest_repo.remove_manager_from_contest(contest_id, user_id)
        return {"message": "Manager removed successfully"}

    def list_contest_managers(self, contest_id: int, current_user):
        """List all managers for a contest."""
        contest = self.get_contest(contest_id, current_user)
        
        # Anyone who can see the contest can list managers
        managers = self.contest_repo.list_contest_managers(contest_id)
        return [self._to_manager_out(m) for m in managers]

    def _to_manager_out(self, manager):
        """Convert ContestManager to output schema."""
        from app.schemas import ContestManagerOut
        return ContestManagerOut(
            id=manager.id,
            contest_id=manager.contest_id,
            user_id=manager.user_id,
            username=manager.user.username if manager.user else None,
            added_by=manager.added_by,
            adder_username=manager.adder.username if manager.adder else None,
            added_at=manager.added_at
        )

    # Registration methods
    def register_for_contest(self, contest_id: int, current_user) -> ContestRegistrationOut:
        """Register the current user for a contest."""
        contest = self.get_contest(contest_id, current_user)
        
        # Check if already registered
        existing = self.registration_repo.get_registration_by_contest_and_user(
            contest_id, current_user.id
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You are already registered for this contest (status: {existing.status})"
            )
        
        # Create registration
        registration = self.registration_repo.create_registration(contest_id, current_user.id)
        
        return self._to_registration_out(registration)

    def get_my_registration(self, contest_id: int, current_user) -> Optional[ContestRegistrationOut]:
        """Get the current user's registration for a contest."""
        registration = self.registration_repo.get_registration_by_contest_and_user(
            contest_id, current_user.id
        )
        if registration:
            return self._to_registration_out(registration)
        return None

    def cancel_registration(self, contest_id: int, current_user):
        """Cancel the current user's registration for a contest."""
        registration = self.registration_repo.get_registration_by_contest_and_user(
            contest_id, current_user.id
        )
        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registration not found"
            )
        
        self.registration_repo.delete_registration(registration)
        return {"message": "Registration cancelled successfully"}

    def list_contest_registrations(
        self,
        contest_id: int,
        current_user,
        status_filter: Optional[ContestRegistrationStatus] = None,
        page: int = 1,
        page_size: int = 20
    ):
        """List all registrations for a contest (admin/owner only)."""
        contest = self.get_contest(contest_id, current_user)
        self.check_edit_permission(contest, current_user)
        
        skip = (page - 1) * page_size
        registrations, total = self.registration_repo.list_registrations_by_contest(
            contest_id, status=status_filter, skip=skip, limit=page_size
        )
        
        pages = (total + page_size - 1) // page_size
        has_next = page < pages
        has_prev = page > 1
        
        return {
            "items": [self._to_registration_out(r) for r in registrations],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }

    def update_registration_status(
        self,
        contest_id: int,
        registration_id: int,
        new_status: ContestRegistrationStatus,
        current_user
    ) -> ContestRegistrationOut:
        """Update registration status (approve/reject) - admin/owner only."""
        contest = self.get_contest(contest_id, current_user)
        self.check_edit_permission(contest, current_user)
        
        registration = self.registration_repo.get_registration_by_id(registration_id)
        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registration not found"
            )
        
        if registration.contest_id != contest_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration does not belong to this contest"
            )
        
        updated = self.registration_repo.update_registration_status(
            registration, new_status, approved_by=current_user.id
        )
        
        return self._to_registration_out(updated)

    def get_registration_summary(self, contest_id: int, current_user) -> ContestRegistrationSummaryOut:
        """Get registration summary for a contest."""
        contest = self.get_contest(contest_id, current_user)
        
        # Only owner/admin can see summary
        is_owner = current_user and contest.owner_id == current_user.id
        is_admin = current_user and current_user.role == UserRole.ADMIN
        
        if not (is_owner or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only contest owner or admin can view registration summary"
            )
        
        summary = self.registration_repo.get_registration_summary(contest_id)
        return ContestRegistrationSummaryOut(**summary)

    def list_my_registrations(
        self,
        current_user,
        status_filter: Optional[ContestRegistrationStatus] = None,
        page: int = 1,
        page_size: int = 20
    ):
        """List all registrations for the current user."""
        skip = (page - 1) * page_size
        registrations, total = self.registration_repo.list_registrations_by_user(
            current_user.id, status=status_filter, skip=skip, limit=page_size
        )
        
        pages = (total + page_size - 1) // page_size
        has_next = page < pages
        has_prev = page > 1
        
        return {
            "items": [
                UserRegistrationOut(
                    contest_id=r.contest_id,
                    contest_title=r.contest.title if r.contest else "Unknown",
                    status=ContestRegistrationStatus(r.status),
                    registered_at=r.registered_at
                ) for r in registrations
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }

    def _to_contest_out(self, contest) -> ContestOut:
        return ContestOut(
            id=contest.id,
            title=contest.title,
            description=contest.description,
            start_date=contest.start_date,
            end_date=contest.end_date,
            contest_type=ContestType(contest.contest_type),
            owner_id=contest.owner_id,
            created_by=contest.created_by,
            updated_by=contest.updated_by,
            update_time=contest.update_time,
            created_at=contest.created_at,
            problem_ids=[p.id for p in contest.problems]
        )

    def _to_contest_detail_out(self, contest, include_problems: bool = True) -> ContestDetailOut:
        problems = []
        if include_problems:
            problems = [
                ContestProblemOut(id=p.id, title=p.title, difficulty=p.difficulty)
                for p in contest.problems
            ]
        
        return ContestDetailOut(
            id=contest.id,
            title=contest.title,
            description=contest.description,
            start_date=contest.start_date,
            end_date=contest.end_date,
            contest_type=ContestType(contest.contest_type),
            owner_id=contest.owner_id,
            created_by=contest.created_by,
            updated_by=contest.updated_by,
            update_time=contest.update_time,
            created_at=contest.created_at,
            problem_ids=[p.id for p in contest.problems],
            problems=problems
        )

    def _to_registration_out(self, registration) -> ContestRegistrationOut:
        return ContestRegistrationOut(
            id=registration.id,
            contest_id=registration.contest_id,
            user_id=registration.user_id,
            username=registration.user.username if registration.user else None,
            status=ContestRegistrationStatus(registration.status),
            registered_at=registration.registered_at,
            approved_at=registration.approved_at,
            approved_by=registration.approved_by,
            approver_username=registration.approver.username if registration.approver else None
        )

    # Submission methods
    def create_contest_submission(
        self,
        contest_id: int,
        problem_id: int,
        submission_create: SubmissionCreate,
        current_user
    ):
        """Create a submission for a problem within a contest."""
        contest = self.get_contest(contest_id, current_user)
        
        # Check if user can see problems (must be registered for private contests)
        if not self._can_user_see_problems(contest, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to submit to this contest"
            )
        
        # Verify the problem is part of this contest
        if problem_id not in contest.problem_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Problem is not part of this contest"
            )
        
        # Check if contest has ended (late submission)
        current_time = datetime.utcnow()
        is_late_submission = current_time > contest.end_date
        
        # Create submission with contest context
        submission = self.problem_repo.create_submission(
            problem_id=problem_id,
            submission_create=submission_create,
            user_id=current_user.id,
            username=current_user.username,
            contest_id=contest_id,
            is_contest_submission=True,
            is_late_submission=is_late_submission
        )
        
        return submission

    def list_contest_submissions(
        self,
        contest_id: int,
        current_user,
        problem_id: Optional[int] = None
    ):
        """List all submissions for a contest.
        
        Args:
            contest_id: The contest ID
            current_user: The current user
            problem_id: Optional problem ID to filter by
        """
        contest = self.get_contest(contest_id, current_user)
        
        # Check if user has manager access (owner, admin, or manager)
        if self.has_manager_access(contest, current_user):
            return self.problem_repo.list_submissions_for_contest(contest_id, problem_id=problem_id)
        
        # Registered users can see submissions too
        is_registered = False
        if current_user:
            registration = self.registration_repo.get_registration_by_contest_and_user(contest_id, current_user.id)
            is_registered = registration is not None and registration.status == "approved"
        
        if not is_registered:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view contest submissions"
            )
        
        return self.problem_repo.list_submissions_for_contest(contest_id, problem_id=problem_id)

    def list_my_contest_submissions(
        self,
        contest_id: int,
        current_user,
        problem_id: Optional[int] = None
    ):
        """List current user's submissions for a contest."""
        contest = self.get_contest(contest_id, current_user)
        
        # Check if user can see problems
        if not self._can_user_see_problems(contest, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view submissions for this contest"
            )
        
        # Filter by current user
        submissions = self.problem_repo.list_submissions_for_contest(contest_id, problem_id=problem_id)
        return [s for s in submissions if s.user_id == current_user.id]

    # Announcement methods
    def create_announcement(
        self,
        contest_id: int,
        announcement_create: ContestAnnouncementCreate,
        current_user
    ) -> ContestAnnouncementOut:
        """Create an announcement for a contest (admin/owner only)."""
        contest = self.get_contest(contest_id, current_user)
        self.check_edit_permission(contest, current_user)
        
        announcement = self.announcement_repo.create_announcement(
            contest_id=contest_id,
            announcement_create=announcement_create,
            author_id=current_user.id
        )
        
        return self._to_announcement_out(announcement)

    def get_announcement(
        self,
        contest_id: int,
        announcement_id: int,
        current_user=None
    ) -> ContestAnnouncementOut:
        """Get a specific announcement."""
        announcement = self.announcement_repo.get_announcement_by_id(announcement_id)
        if not announcement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Announcement not found"
            )
        
        if announcement.contest_id != contest_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Announcement does not belong to this contest"
            )
        
        # Check if user can see unpublished announcements
        if not announcement.is_published:
            contest = self.get_contest(contest_id, current_user)
            if not self.has_manager_access(contest, current_user):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Announcement not found"
                )
        
        return self._to_announcement_out(announcement)

    def list_announcements(
        self,
        contest_id: int,
        current_user=None,
        page: int = 1,
        page_size: int = 20
    ):
        """List announcements for a contest."""
        # Verify contest exists
        contest = self.contest_repo.get_contest_by_id(contest_id)
        if not contest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contest not found"
            )
        
        # Check if user can see unpublished announcements (managers have access)
        include_unpublished = self.has_manager_access(contest, current_user)
        
        skip = (page - 1) * page_size
        announcements, total = self.announcement_repo.list_announcements_by_contest(
            contest_id,
            include_unpublished=include_unpublished,
            skip=skip,
            limit=page_size
        )
        
        pages = (total + page_size - 1) // page_size
        has_next = page < pages
        has_prev = page > 1
        
        return {
            "items": [self._to_announcement_out(a) for a in announcements],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }

    def update_announcement(
        self,
        contest_id: int,
        announcement_id: int,
        announcement_update: ContestAnnouncementUpdate,
        current_user
    ) -> ContestAnnouncementOut:
        """Update an announcement (admin/owner only)."""
        contest = self.get_contest(contest_id, current_user)
        self.check_edit_permission(contest, current_user)
        
        announcement = self.announcement_repo.get_announcement_by_id(announcement_id)
        if not announcement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Announcement not found"
            )
        
        if announcement.contest_id != contest_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Announcement does not belong to this contest"
            )
        
        updated = self.announcement_repo.update_announcement(announcement, announcement_update)
        return self._to_announcement_out(updated)

    def delete_announcement(
        self,
        contest_id: int,
        announcement_id: int,
        current_user
    ):
        """Delete an announcement (admin/owner only)."""
        contest = self.get_contest(contest_id, current_user)
        self.check_edit_permission(contest, current_user)
        
        announcement = self.announcement_repo.get_announcement_by_id(announcement_id)
        if not announcement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Announcement not found"
            )
        
        if announcement.contest_id != contest_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Announcement does not belong to this contest"
            )
        
        self.announcement_repo.delete_announcement(announcement)
        return {"message": "Announcement deleted successfully"}

    def _to_announcement_out(self, announcement) -> ContestAnnouncementOut:
        return ContestAnnouncementOut(
            id=announcement.id,
            contest_id=announcement.contest_id,
            title=announcement.title,
            content=announcement.content,
            author_id=announcement.author_id,
            author_username=announcement.author.username if announcement.author else None,
            is_published=announcement.is_published,
            created_at=announcement.created_at,
            updated_at=announcement.updated_at
        )

    # Ticket methods
    def create_ticket(
        self,
        contest_id: int,
        ticket_create: ContestTicketCreate,
        current_user
    ) -> ContestTicketOut:
        """Create a ticket for a contest.
        
        Any registered user can create a ticket.
        """
        contest = self.get_contest(contest_id, current_user)
        
        # Check if user can see problems (must be registered for private contests)
        if not self._can_user_see_problems(contest, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to create tickets for this contest"
            )
        
        # Verify the problem is part of this contest if problem_id is provided
        if ticket_create.problem_id:
            if ticket_create.problem_id not in contest.problem_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Problem is not part of this contest"
                )
        
        ticket = self.ticket_repo.create_ticket(
            contest_id=contest_id,
            user_id=current_user.id,
            title=ticket_create.title,
            content=ticket_create.content,
            problem_id=ticket_create.problem_id,
            is_public=ticket_create.is_public
        )
        
        return self._to_ticket_out(ticket)

    def get_ticket(
        self,
        ticket_id: int,
        current_user
    ) -> ContestTicketOut:
        """Get a ticket by ID.
        
        Users can see their own tickets and public tickets.
        Managers can see all tickets.
        """
        ticket = self.ticket_repo.get_ticket_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        contest = self.get_contest(ticket.contest_id, current_user)
        
        # Check visibility
        is_manager = self.has_manager_access(contest, current_user)
        is_owner = ticket.user_id == current_user.id
        
        if not is_manager and not is_owner and not ticket.is_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this ticket"
            )
        
        return self._to_ticket_out(ticket)

    def list_tickets(
        self,
        contest_id: int,
        current_user,
        status_filter: Optional[str] = None,
        problem_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ):
        """List tickets for a contest.
        
        Regular users see their own tickets and public tickets.
        Managers see all tickets.
        """
        contest = self.get_contest(contest_id, current_user)
        is_manager = self.has_manager_access(contest, current_user)
        
        # Validate status filter
        if status_filter and status_filter not in [s.value for s in ContestTicketStatus]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: open, answered, closed"
            )
        
        skip = (page - 1) * page_size
        tickets, total = self.ticket_repo.list_tickets_by_contest(
            contest_id=contest_id,
            user_id=current_user.id if current_user else None,
            is_manager=is_manager,
            status_filter=status_filter,
            problem_id=problem_id,
            skip=skip,
            limit=page_size
        )
        
        pages = (total + page_size - 1) // page_size
        has_next = page < pages
        has_prev = page > 1
        
        return {
            "items": [self._to_ticket_summary_out(t) for t in tickets],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }

    def list_my_tickets(
        self,
        current_user,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ):
        """List all tickets created by the current user."""
        # Validate status filter
        if status_filter and status_filter not in [s.value for s in ContestTicketStatus]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: open, answered, closed"
            )
        
        skip = (page - 1) * page_size
        tickets, total = self.ticket_repo.list_tickets_by_user(
            user_id=current_user.id,
            status_filter=status_filter,
            skip=skip,
            limit=page_size
        )
        
        pages = (total + page_size - 1) // page_size
        has_next = page < pages
        has_prev = page > 1
        
        return {
            "items": [self._to_ticket_summary_out(t) for t in tickets],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }

    def update_ticket(
        self,
        ticket_id: int,
        ticket_update: ContestTicketUpdate,
        current_user
    ) -> ContestTicketOut:
        """Update a ticket.
        
        Only the ticket author can update the ticket.
        Managers can make tickets public.
        """
        ticket = self.ticket_repo.get_ticket_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        contest = self.get_contest(ticket.contest_id, current_user)
        is_manager = self.has_manager_access(contest, current_user)
        is_owner = ticket.user_id == current_user.id
        
        # Only author can update content, managers can only change visibility
        if is_owner:
            updated = self.ticket_repo.update_ticket(
                ticket,
                title=ticket_update.title,
                content=ticket_update.content,
                is_public=ticket_update.is_public
            )
        elif is_manager and ticket_update.is_public is not None:
            updated = self.ticket_repo.update_ticket(
                ticket,
                is_public=ticket_update.is_public
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this ticket"
            )
        
        return self._to_ticket_out(updated)

    def update_ticket_status(
        self,
        ticket_id: int,
        new_status: str,
        current_user
    ) -> ContestTicketOut:
        """Update ticket status.
        
        Managers can change ticket status.
        Ticket authors can close their own tickets.
        """
        ticket = self.ticket_repo.get_ticket_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        contest = self.get_contest(ticket.contest_id, current_user)
        is_manager = self.has_manager_access(contest, current_user)
        is_owner = ticket.user_id == current_user.id
        
        # Validate status
        if new_status not in [s.value for s in ContestTicketStatus]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: open, answered, closed"
            )
        
        # Managers can change any status
        # Authors can only close their tickets
        if is_manager:
            pass
        elif is_owner and new_status == ContestTicketStatus.CLOSED.value:
            pass
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this ticket's status"
            )
        
        updated = self.ticket_repo.update_ticket_status(ticket, new_status)
        return self._to_ticket_out(updated)

    def delete_ticket(
        self,
        ticket_id: int,
        current_user
    ):
        """Delete a ticket.
        
        Only the ticket author or managers can delete a ticket.
        """
        ticket = self.ticket_repo.get_ticket_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        contest = self.get_contest(ticket.contest_id, current_user)
        is_manager = self.has_manager_access(contest, current_user)
        is_owner = ticket.user_id == current_user.id
        
        if not is_manager and not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this ticket"
            )
        
        self.ticket_repo.delete_ticket(ticket)
        return {"message": "Ticket deleted successfully"}

    def create_ticket_response(
        self,
        ticket_id: int,
        response_create: ContestTicketResponseCreate,
        current_user
    ) -> ContestTicketResponseOut:
        """Create a response to a ticket.
        
        Only managers (admin/owner/managers) can respond to tickets.
        """
        ticket = self.ticket_repo.get_ticket_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        contest = self.get_contest(ticket.contest_id, current_user)
        
        # Only managers can respond
        if not self.has_manager_access(contest, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only contest managers can respond to tickets"
            )
        
        response = self.ticket_repo.create_response(
            ticket_id=ticket_id,
            responder_id=current_user.id,
            content=response_create.content
        )
        
        # Auto-update ticket status to answered if it was open
        if ticket.status == ContestTicketStatus.OPEN.value:
            self.ticket_repo.update_ticket_status(ticket, ContestTicketStatus.ANSWERED.value)
        
        return self._to_ticket_response_out(response)

    def update_ticket_response(
        self,
        response_id: int,
        content: str,
        current_user
    ) -> ContestTicketResponseOut:
        """Update a ticket response.
        
        Only the responder can update their response.
        """
        response = self.ticket_repo.get_response_by_id(response_id)
        if not response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Response not found"
            )
        
        # Only the responder can update
        if response.responder_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own responses"
            )
        
        updated = self.ticket_repo.update_response(response, content)
        return self._to_ticket_response_out(updated)

    def delete_ticket_response(
        self,
        response_id: int,
        current_user
    ):
        """Delete a ticket response.
        
        Only the responder or managers can delete a response.
        """
        response = self.ticket_repo.get_response_by_id(response_id)
        if not response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Response not found"
            )
        
        ticket = self.ticket_repo.get_ticket_by_id(response.ticket_id)
        contest = self.get_contest(ticket.contest_id, current_user)
        is_manager = self.has_manager_access(contest, current_user)
        
        if response.responder_id != current_user.id and not is_manager:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this response"
            )
        
        self.ticket_repo.delete_response(response)
        return {"message": "Response deleted successfully"}

    def _to_ticket_out(self, ticket) -> ContestTicketOut:
        responses = [
            self._to_ticket_response_out(r) for r in ticket.responses
        ]
        return ContestTicketOut(
            id=ticket.id,
            contest_id=ticket.contest_id,
            problem_id=ticket.problem_id,
            problem_title=ticket.problem.title if ticket.problem else None,
            user_id=ticket.user_id,
            username=ticket.user.username if ticket.user else None,
            title=ticket.title,
            content=ticket.content,
            status=ticket.status,
            is_public=ticket.is_public,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            responses=responses
        )

    def _to_ticket_summary_out(self, ticket) -> ContestTicketSummaryOut:
        return ContestTicketSummaryOut(
            id=ticket.id,
            contest_id=ticket.contest_id,
            problem_id=ticket.problem_id,
            problem_title=ticket.problem.title if ticket.problem else None,
            user_id=ticket.user_id,
            username=ticket.user.username if ticket.user else None,
            title=ticket.title,
            status=ticket.status,
            is_public=ticket.is_public,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            response_count=len(ticket.responses) if ticket.responses else 0
        )

    def _to_ticket_response_out(self, response) -> ContestTicketResponseOut:
        return ContestTicketResponseOut(
            id=response.id,
            ticket_id=response.ticket_id,
            responder_id=response.responder_id,
            responder_username=response.responder.username if response.responder else None,
            content=response.content,
            created_at=response.created_at,
            updated_at=response.updated_at
        )
