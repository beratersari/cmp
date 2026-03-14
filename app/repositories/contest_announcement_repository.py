from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.contest import ContestAnnouncement
from app.schemas import ContestAnnouncementCreate, ContestAnnouncementUpdate
from app.core.config import get_logger

logger = get_logger(__name__)


class ContestAnnouncementRepository:
    def __init__(self, db: Session):
        self.db = db
        logger.debug("ContestAnnouncementRepository initialized")

    def create_announcement(
        self,
        contest_id: int,
        announcement_create: ContestAnnouncementCreate,
        author_id: int
    ) -> ContestAnnouncement:
        """Create a new announcement for a contest."""
        logger.debug(f"Creating announcement: contest_id={contest_id}, author_id={author_id}")
        announcement = ContestAnnouncement(
            contest_id=contest_id,
            title=announcement_create.title,
            content=announcement_create.content,
            is_published=announcement_create.is_published,
            author_id=author_id
        )
        self.db.add(announcement)
        self.db.commit()
        self.db.refresh(announcement)
        logger.debug(f"Announcement created: id={announcement.id}")
        return announcement

    def get_announcement_by_id(self, announcement_id: int) -> Optional[ContestAnnouncement]:
        """Get an announcement by ID."""
        return self.db.query(ContestAnnouncement).filter(
            ContestAnnouncement.id == announcement_id
        ).first()

    def list_announcements_by_contest(
        self,
        contest_id: int,
        include_unpublished: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[ContestAnnouncement], int]:
        """List announcements for a contest."""
        query = self.db.query(ContestAnnouncement).filter(
            ContestAnnouncement.contest_id == contest_id
        )
        
        if not include_unpublished:
            query = query.filter(ContestAnnouncement.is_published == True)
        
        total = query.count()
        announcements = query.order_by(
            ContestAnnouncement.created_at.desc()
        ).offset(skip).limit(limit).all()
        return announcements, total

    def update_announcement(
        self,
        announcement: ContestAnnouncement,
        announcement_update: ContestAnnouncementUpdate
    ) -> ContestAnnouncement:
        """Update an announcement."""
        if announcement_update.title is not None:
            announcement.title = announcement_update.title
        if announcement_update.content is not None:
            announcement.content = announcement_update.content
        if announcement_update.is_published is not None:
            announcement.is_published = announcement_update.is_published
        
        self.db.commit()
        self.db.refresh(announcement)
        logger.debug(f"Announcement updated: id={announcement.id}")
        return announcement

    def delete_announcement(self, announcement: ContestAnnouncement) -> None:
        """Delete an announcement."""
        self.db.delete(announcement)
        self.db.commit()
        logger.debug(f"Announcement deleted: id={announcement.id}")
