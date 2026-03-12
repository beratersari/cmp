from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.contest import ContestRegistration, ContestRegistrationStatus
from app.core.config import get_logger

logger = get_logger(__name__)


class ContestRegistrationRepository:
    def __init__(self, db: Session):
        self.db = db
        logger.debug("ContestRegistrationRepository initialized")

    def create_registration(self, contest_id: int, user_id: int) -> ContestRegistration:
        """Create a new registration for a contest."""
        logger.debug(f"Creating registration: contest_id={contest_id}, user_id={user_id}")
        registration = ContestRegistration(
            contest_id=contest_id,
            user_id=user_id,
            status=ContestRegistrationStatus.PENDING.value
        )
        self.db.add(registration)
        self.db.commit()
        self.db.refresh(registration)
        logger.debug(f"Registration created: id={registration.id}")
        return registration

    def get_registration_by_id(self, registration_id: int) -> Optional[ContestRegistration]:
        """Get a registration by ID."""
        return self.db.query(ContestRegistration).filter(
            ContestRegistration.id == registration_id
        ).first()

    def get_registration_by_contest_and_user(
        self, contest_id: int, user_id: int
    ) -> Optional[ContestRegistration]:
        """Get a registration by contest and user."""
        return self.db.query(ContestRegistration).filter(
            ContestRegistration.contest_id == contest_id,
            ContestRegistration.user_id == user_id
        ).first()

    def list_registrations_by_contest(
        self,
        contest_id: int,
        status: Optional[ContestRegistrationStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[ContestRegistration], int]:
        """List registrations for a contest with optional status filter."""
        query = self.db.query(ContestRegistration).filter(
            ContestRegistration.contest_id == contest_id
        )
        
        if status is not None:
            query = query.filter(ContestRegistration.status == status.value)
        
        total = query.count()
        registrations = query.order_by(
            ContestRegistration.registered_at.desc()
        ).offset(skip).limit(limit).all()
        return registrations, total

    def list_registrations_by_user(
        self,
        user_id: int,
        status: Optional[ContestRegistrationStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[ContestRegistration], int]:
        """List registrations for a user with optional status filter."""
        query = self.db.query(ContestRegistration).filter(
            ContestRegistration.user_id == user_id
        )
        
        if status is not None:
            query = query.filter(ContestRegistration.status == status.value)
        
        total = query.count()
        registrations = query.order_by(
            ContestRegistration.registered_at.desc()
        ).offset(skip).limit(limit).all()
        return registrations, total

    def update_registration_status(
        self,
        registration: ContestRegistration,
        status: ContestRegistrationStatus,
        approved_by: Optional[int] = None
    ) -> ContestRegistration:
        """Update registration status."""
        registration.status = status.value
        
        if status == ContestRegistrationStatus.APPROVED:
            registration.approved_at = datetime.utcnow()
            registration.approved_by = approved_by
        else:
            registration.approved_at = None
            registration.approved_by = None
        
        self.db.commit()
        self.db.refresh(registration)
        logger.debug(f"Registration {registration.id} status updated to {status.value}")
        return registration

    def delete_registration(self, registration: ContestRegistration) -> None:
        """Delete a registration (cancel registration)."""
        self.db.delete(registration)
        self.db.commit()
        logger.debug(f"Registration {registration.id} deleted")

    def is_user_registered(self, contest_id: int, user_id: int) -> bool:
        """Check if a user has an approved registration for a contest."""
        registration = self.db.query(ContestRegistration).filter(
            ContestRegistration.contest_id == contest_id,
            ContestRegistration.user_id == user_id,
            ContestRegistration.status == ContestRegistrationStatus.APPROVED.value
        ).first()
        return registration is not None

    def get_registration_summary(self, contest_id: int) -> dict:
        """Get registration summary for a contest."""
        registrations = self.db.query(ContestRegistration).filter(
            ContestRegistration.contest_id == contest_id
        ).all()
        
        pending = sum(1 for r in registrations if r.status == ContestRegistrationStatus.PENDING.value)
        approved = sum(1 for r in registrations if r.status == ContestRegistrationStatus.APPROVED.value)
        rejected = sum(1 for r in registrations if r.status == ContestRegistrationStatus.REJECTED.value)
        
        return {
            "contest_id": contest_id,
            "total_registrations": len(registrations),
            "pending_count": pending,
            "approved_count": approved,
            "rejected_count": rejected
        }
