from typing import Optional
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.contest_repository import ContestRepository
from app.repositories.contest_registration_repository import ContestRegistrationRepository
from app.repositories.contest_announcement_repository import ContestAnnouncementRepository
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
)
from app.models.user import UserRole
from app.models.contest import ContestType, ContestRegistrationStatus, ContestRegistration, ContestMode
from app.core.config import get_logger

logger = get_logger(__name__)


class ContestService:
    def __init__(self, db: Session):
        self.contest_repo = ContestRepository(db)
        self.registration_repo = ContestRegistrationRepository(db)
        self.announcement_repo = ContestAnnouncementRepository(db)
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
        # Owner and admin can always see problems
        if current_user:
            if contest.owner_id == current_user.id or current_user.role == UserRole.ADMIN:
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
        if current_user.role == UserRole.ADMIN:
            return True
        if current_user.role == UserRole.CREATOR:
            if contest.owner_id == current_user.id:
                return True
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this contest"
        )

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

    # Registration methods
    def register_for_contest(
        self, 
        contest_id: int, 
        current_user, 
        team_id: Optional[int] = None
    ) -> ContestRegistrationOut:
        """Register the current user or team for a contest."""
        from app.repositories.team_repository import TeamRepository
        from app.models.contest import ContestMode
        
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
        
        # Validate team registration
        if team_id is not None:
            # Check if contest is team contest
            if contest.contest_mode == ContestMode.INDIVIDUAL.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This is an individual contest. Team registration is not allowed."
                )
            
            # Get team
            team_repo = TeamRepository(self.problem_repo.db)
            team = team_repo.get_team_by_id(team_id)
            if not team:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Team not found"
                )
            
            # Check if user is team leader
            if team.leader_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only team leader can register the team for a contest"
                )
            
            # Check team size against contest limit
            if contest.team_size and team.member_count > contest.team_size:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Team size ({team.member_count}) exceeds contest limit ({contest.team_size})"
                )
            
            # Check if team is already registered
            existing_team_reg = self.registration_repo.db.query(
                self.registration_repo.db.query(ContestRegistration).filter(
                    ContestRegistration.contest_id == contest_id,
                    ContestRegistration.team_id == team_id
                ).exists()
            ).scalar()
            
            if existing_team_reg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This team is already registered for this contest"
                )
            
            # Create team registration
            registration = ContestRegistration(
                contest_id=contest_id,
                user_id=current_user.id,
                team_id=team_id,
                status=ContestRegistrationStatus.PENDING.value
            )
            self.problem_repo.db.add(registration)
            self.problem_repo.db.commit()
            self.problem_repo.db.refresh(registration)
            
        else:
            # Individual registration
            # Check if contest is team-only
            if contest.contest_mode == ContestMode.TEAM.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This is a team contest. Please register with a team."
                )
            
            # Create individual registration
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
        from app.models.contest import ContestMode
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
            problem_ids=[p.id for p in contest.problems],
            penalty_minutes=contest.penalty_minutes,
            contest_mode=ContestMode(contest.contest_mode),
            team_size=contest.team_size
        )

    def _to_contest_detail_out(self, contest, include_problems: bool = True) -> ContestDetailOut:
        from app.models.contest import ContestMode
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
            problems=problems,
            penalty_minutes=contest.penalty_minutes,
            contest_mode=ContestMode(contest.contest_mode),
            team_size=contest.team_size
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
            is_owner = current_user and contest.owner_id == current_user.id
            is_admin = current_user and current_user.role == UserRole.ADMIN
            if not (is_owner or is_admin):
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
        
        # Check if user can see unpublished announcements
        include_unpublished = False
        if current_user:
            is_owner = contest.owner_id == current_user.id
            is_admin = current_user.role == UserRole.ADMIN
            include_unpublished = is_owner or is_admin
        
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

    def get_contest_submissions(
        self,
        contest_id: int,
        current_user,
        username: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ):
        """Get submissions for a contest, optionally filtered by username."""
        contest = self.get_contest(contest_id, current_user)
        
        # Check permissions
        is_owner = current_user and contest.owner_id == current_user.id
        is_admin = current_user and current_user.role == UserRole.ADMIN
        
        # If filtering by username, check if user can see those submissions
        if username and not (is_owner or is_admin):
            # Regular users can only see their own submissions
            if username != current_user.username:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only view your own submissions"
                )
        
        # Get problem IDs for this contest
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
        
        # Get submissions from problem repository
        from app.models.problem import Submission
        from app.schemas import SubmissionOut
        
        query = self.problem_repo.db.query(Submission).filter(
            Submission.problem_id.in_(problem_ids)
        )
        
        # Filter by username if provided
        if username:
            query = query.filter(Submission.username == username)
        
        # Order by submission time
        query = query.order_by(Submission.submission_time.desc())
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        skip = (page - 1) * page_size
        submissions = query.offset(skip).limit(page_size).all()
        
        # Convert to output schema
        items = [
            SubmissionOut(
                id=s.id,
                problem_id=s.problem_id,
                user_id=s.user_id,
                username=s.username,
                programming_language=s.programming_language,
                code=s.code,
                status=s.status,
                created_by=s.created_by,
                updated_by=s.updated_by,
                update_time=s.update_time,
                submission_time=s.submission_time
            )
            for s in submissions
        ]
        
        pages = (total + page_size - 1) // page_size if total > 0 else 0
        has_next = page < pages
        has_prev = page > 1
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }

    def get_contest_submissions_grouped_by_problem(
        self,
        contest_id: int,
        username: str,
        current_user
    ):
        """Get submissions for a user in a contest, grouped by problem."""
        from app.models.problem import Submission, SubmissionStatus
        from app.schemas import SubmissionOut, UserProblemSubmissionsOut, ContestUserSubmissionsGroupedOut
        from app.repositories.user_repository import UserRepository
        
        contest = self.get_contest(contest_id, current_user)
        
        # Check permissions
        is_owner = current_user and contest.owner_id == current_user.id
        is_admin = current_user and current_user.role == UserRole.ADMIN
        
        # Only owner, admin, or the user themselves can view their submissions
        if not (is_owner or is_admin or current_user.username == username):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own submissions"
            )
        
        # Get user by username
        user_repo = UserRepository(self.problem_repo.db)
        target_user = user_repo.get_user_by_username(username)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )
        
        # Get problem IDs for this contest
        problem_ids = contest.problem_ids
        if not problem_ids:
            return ContestUserSubmissionsGroupedOut(
                contest_id=contest_id,
                username=username,
                problems=[],
                total_problems_solved=0,
                total_submissions=0
            )
        
        # Get all contest problems for reference
        contest_problems = {cp.problem_id: cp.problem for cp in contest.contest_problems}
        
        # Get all submissions for this user in this contest
        submissions = self.problem_repo.db.query(Submission).filter(
            Submission.problem_id.in_(problem_ids),
            Submission.user_id == target_user.id
        ).order_by(Submission.submission_time.asc()).all()
        
        # Group submissions by problem
        problem_submissions = {}
        for submission in submissions:
            if submission.problem_id not in problem_submissions:
                problem_submissions[submission.problem_id] = []
            problem_submissions[submission.problem_id].append(submission)
        
        # Build problem details
        problems_out = []
        total_solved = 0
        total_submissions = 0
        
        for problem_id in problem_ids:
            problem = contest_problems.get(problem_id)
            if not problem:
                continue
            
            subs = problem_submissions.get(problem_id, [])
            total_submissions += len(subs)
            
            # Convert submissions to output schema
            submission_outs = [
                SubmissionOut(
                    id=s.id,
                    problem_id=s.problem_id,
                    user_id=s.user_id,
                    username=s.username,
                    programming_language=s.programming_language,
                    code=s.code,
                    status=s.status,
                    created_by=s.created_by,
                    updated_by=s.updated_by,
                    update_time=s.update_time,
                    submission_time=s.submission_time
                )
                for s in subs
            ]
            
            # Check if problem was solved (has an accepted submission)
            accepted = any(s.status == SubmissionStatus.ACCEPTED for s in subs)
            if accepted:
                total_solved += 1
            
            # Find first accepted submission time
            first_accepted_at = None
            for s in subs:
                if s.status == SubmissionStatus.ACCEPTED:
                    first_accepted_at = s.submission_time
                    break
            
            # Count incorrect submissions before first accepted
            incorrect_submissions = 0
            for s in subs:
                if s.status == SubmissionStatus.ACCEPTED:
                    break
                if s.status != SubmissionStatus.ACCEPTED:
                    incorrect_submissions += 1
            
            problems_out.append(UserProblemSubmissionsOut(
                problem_id=problem_id,
                problem_title=problem.title,
                submissions=submission_outs,
                accepted=accepted,
                first_accepted_at=first_accepted_at,
                total_submissions=len(subs),
                incorrect_submissions=incorrect_submissions
            ))
        
        return ContestUserSubmissionsGroupedOut(
            contest_id=contest_id,
            username=username,
            problems=problems_out,
            total_problems_solved=total_solved,
            total_submissions=total_submissions
        )

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
