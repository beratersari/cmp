from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.contest import ContestAnnouncement, ContestTicket, ContestTicketResponse, ContestTicketStatus
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


class ContestTicketRepository:
    """Repository for contest ticket operations."""
    
    def __init__(self, db: Session):
        self.db = db
        logger.debug("ContestTicketRepository initialized")

    def create_ticket(
        self,
        contest_id: int,
        user_id: int,
        title: str,
        content: str,
        problem_id: Optional[int] = None,
        is_public: bool = False
    ) -> ContestTicket:
        """Create a new ticket for a contest."""
        logger.debug(f"Creating ticket: contest_id={contest_id}, user_id={user_id}")
        ticket = ContestTicket(
            contest_id=contest_id,
            user_id=user_id,
            title=title,
            content=content,
            problem_id=problem_id,
            is_public=is_public,
            status=ContestTicketStatus.OPEN.value
        )
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        logger.debug(f"Ticket created: id={ticket.id}")
        return ticket

    def get_ticket_by_id(self, ticket_id: int) -> Optional[ContestTicket]:
        """Get a ticket by ID."""
        return self.db.query(ContestTicket).filter(
            ContestTicket.id == ticket_id
        ).first()

    def list_tickets_by_contest(
        self,
        contest_id: int,
        user_id: Optional[int] = None,
        is_manager: bool = False,
        status_filter: Optional[str] = None,
        problem_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[ContestTicket], int]:
        """List tickets for a contest.
        
        Args:
            contest_id: The contest ID
            user_id: The current user ID (for filtering private tickets)
            is_manager: Whether the user is a manager (can see all tickets)
            status_filter: Filter by status (open, answered, closed)
            problem_id: Filter by problem ID
            skip: Pagination offset
            limit: Pagination limit
        """
        query = self.db.query(ContestTicket).filter(
            ContestTicket.contest_id == contest_id
        )
        
        # Non-managers can only see:
        # - Their own tickets
        # - Public tickets
        if not is_manager and user_id:
            query = query.filter(
                (ContestTicket.user_id == user_id) | (ContestTicket.is_public == True)
            )
        
        if status_filter:
            query = query.filter(ContestTicket.status == status_filter)
        
        if problem_id:
            query = query.filter(ContestTicket.problem_id == problem_id)
        
        total = query.count()
        tickets = query.order_by(
            ContestTicket.created_at.desc()
        ).offset(skip).limit(limit).all()
        return tickets, total

    def list_tickets_by_user(
        self,
        user_id: int,
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[ContestTicket], int]:
        """List all tickets created by a user."""
        query = self.db.query(ContestTicket).filter(
            ContestTicket.user_id == user_id
        )
        
        if status_filter:
            query = query.filter(ContestTicket.status == status_filter)
        
        total = query.count()
        tickets = query.order_by(
            ContestTicket.created_at.desc()
        ).offset(skip).limit(limit).all()
        return tickets, total

    def update_ticket_status(
        self,
        ticket: ContestTicket,
        new_status: str
    ) -> ContestTicket:
        """Update the status of a ticket."""
        ticket.status = new_status
        self.db.commit()
        self.db.refresh(ticket)
        logger.debug(f"Ticket status updated: id={ticket.id}, status={new_status}")
        return ticket

    def update_ticket(
        self,
        ticket: ContestTicket,
        title: Optional[str] = None,
        content: Optional[str] = None,
        is_public: Optional[bool] = None
    ) -> ContestTicket:
        """Update a ticket's content."""
        if title is not None:
            ticket.title = title
        if content is not None:
            ticket.content = content
        if is_public is not None:
            ticket.is_public = is_public
        
        self.db.commit()
        self.db.refresh(ticket)
        logger.debug(f"Ticket updated: id={ticket.id}")
        return ticket

    def delete_ticket(self, ticket: ContestTicket) -> None:
        """Delete a ticket."""
        self.db.delete(ticket)
        self.db.commit()
        logger.debug(f"Ticket deleted: id={ticket.id}")

    def create_response(
        self,
        ticket_id: int,
        responder_id: int,
        content: str
    ) -> ContestTicketResponse:
        """Create a response to a ticket."""
        logger.debug(f"Creating response: ticket_id={ticket_id}, responder_id={responder_id}")
        response = ContestTicketResponse(
            ticket_id=ticket_id,
            responder_id=responder_id,
            content=content
        )
        self.db.add(response)
        self.db.commit()
        self.db.refresh(response)
        logger.debug(f"Response created: id={response.id}")
        return response

    def get_response_by_id(self, response_id: int) -> Optional[ContestTicketResponse]:
        """Get a response by ID."""
        return self.db.query(ContestTicketResponse).filter(
            ContestTicketResponse.id == response_id
        ).first()

    def list_responses_for_ticket(self, ticket_id: int) -> List[ContestTicketResponse]:
        """List all responses for a ticket."""
        return self.db.query(ContestTicketResponse).filter(
            ContestTicketResponse.ticket_id == ticket_id
        ).order_by(ContestTicketResponse.created_at.asc()).all()

    def update_response(
        self,
        response: ContestTicketResponse,
        content: str
    ) -> ContestTicketResponse:
        """Update a response."""
        response.content = content
        self.db.commit()
        self.db.refresh(response)
        logger.debug(f"Response updated: id={response.id}")
        return response

    def delete_response(self, response: ContestTicketResponse) -> None:
        """Delete a response."""
        self.db.delete(response)
        self.db.commit()
        logger.debug(f"Response deleted: id={response.id}")
