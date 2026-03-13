import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ContestType(str, enum.Enum):
    """Contest visibility types."""
    PUBLIC = "public"      # Visible to everyone, problems visible to everyone
    PRIVATE = "private"    # Visible to everyone, problems only to registered users
    ARCHIVED = "archived"  # Only visible to owner/admin


class ContestRegistrationStatus(str, enum.Enum):
    """Status of a user's contest registration."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ContestProblem(Base):
    """Association object for contest-problem relationship with ordering."""
    __tablename__ = "contest_problems"

    contest_id = Column(Integer, ForeignKey("contests.id", ondelete="CASCADE"), primary_key=True)
    problem_id = Column(Integer, ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True)
    order = Column(Integer, default=0, nullable=False)

    # Relationships
    contest = relationship("Contest", back_populates="contest_problems")
    problem = relationship("Problem", backref="contest_associations")


class ContestRegistration(Base):
    """User registration for a contest."""
    __tablename__ = "contest_registrations"

    id = Column(Integer, primary_key=True, index=True)
    contest_id = Column(Integer, ForeignKey("contests.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default=ContestRegistrationStatus.PENDING.value, nullable=False)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    contest = relationship("Contest", back_populates="registrations")
    user = relationship("User", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approved_by])

    @property
    def is_approved(self) -> bool:
        return self.status == ContestRegistrationStatus.APPROVED.value


class ContestManager(Base):
    """Contest managers/collaborators who can edit the contest.
    
    This allows team collaboration on contests - managers can:
    - Edit contest details
    - Add/remove problems
    - Manage registrations
    - Create/edit/delete announcements
    """
    __tablename__ = "contest_managers"

    id = Column(Integer, primary_key=True, index=True)
    contest_id = Column(Integer, ForeignKey("contests.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    added_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    contest = relationship("Contest", back_populates="managers")
    user = relationship("User", foreign_keys=[user_id])
    adder = relationship("User", foreign_keys=[added_by])

    __table_args__ = (
        # Ensure a user can only be a manager once per contest
        {'sqlite_autoincrement': True},
    )


class Contest(Base):
    __tablename__ = "contests"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    contest_type = Column(String, default=ContestType.PUBLIC.value, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)
    update_time = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    contest_problems = relationship("ContestProblem", back_populates="contest", cascade="all, delete-orphan", order_by="ContestProblem.order")
    registrations = relationship("ContestRegistration", back_populates="contest", cascade="all, delete-orphan")
    announcements = relationship("ContestAnnouncement", back_populates="contest", cascade="all, delete-orphan", order_by="ContestAnnouncement.created_at.desc()")
    managers = relationship("ContestManager", back_populates="contest", cascade="all, delete-orphan")
    tickets = relationship("ContestTicket", back_populates="contest", cascade="all, delete-orphan", order_by="ContestTicket.created_at.desc()")

    @property
    def problems(self):
        """Returns problems in order."""
        return [cp.problem for cp in self.contest_problems if cp.problem]

    @property
    def problem_ids(self) -> list[int]:
        """Returns problem IDs in order."""
        return [cp.problem_id for cp in self.contest_problems]

    @property
    def is_public(self) -> bool:
        return self.contest_type == ContestType.PUBLIC.value

    @property
    def is_private(self) -> bool:
        return self.contest_type == ContestType.PRIVATE.value

    @property
    def is_archived(self) -> bool:
        return self.contest_type == ContestType.ARCHIVED.value

    @property
    def registered_user_ids(self) -> list[int]:
        """Returns list of approved user IDs."""
        return [r.user_id for r in self.registrations if r.is_approved]

    @property
    def manager_user_ids(self) -> list[int]:
        """Returns list of manager user IDs."""
        return [m.user_id for m in self.managers]


class ContestAnnouncement(Base):
    """Announcement for a contest."""
    __tablename__ = "contest_announcements"

    id = Column(Integer, primary_key=True, index=True)
    contest_id = Column(Integer, ForeignKey("contests.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_published = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    contest = relationship("Contest", back_populates="announcements")
    author = relationship("User")


class ContestTicketStatus(str, enum.Enum):
    """Status of a contest ticket/clarification."""
    OPEN = "open"          # Ticket is open, awaiting response
    ANSWERED = "answered"  # Ticket has been answered by staff
    CLOSED = "closed"      # Ticket is closed


class ContestTicket(Base):
    """Ticket/clarification for a contest problem.
    
    This allows contestants to ask questions about problems during a contest.
    Common in competitive programming platforms like Codeforces.
    """
    __tablename__ = "contest_tickets"

    id = Column(Integer, primary_key=True, index=True)
    contest_id = Column(Integer, ForeignKey("contests.id", ondelete="CASCADE"), nullable=False)
    problem_id = Column(Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String, default=ContestTicketStatus.OPEN.value, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)  # If true, all contestants can see
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    contest = relationship("Contest", back_populates="tickets")
    problem = relationship("Problem")
    user = relationship("User", foreign_keys=[user_id])
    responses = relationship("ContestTicketResponse", back_populates="ticket", cascade="all, delete-orphan", order_by="ContestTicketResponse.created_at")

    @property
    def is_open(self) -> bool:
        return self.status == ContestTicketStatus.OPEN.value

    @property
    def is_answered(self) -> bool:
        return self.status == ContestTicketStatus.ANSWERED.value

    @property
    def is_closed(self) -> bool:
        return self.status == ContestTicketStatus.CLOSED.value


class ContestTicketResponse(Base):
    """Response to a contest ticket from staff (admin/owner/manager)."""
    __tablename__ = "contest_ticket_responses"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("contest_tickets.id", ondelete="CASCADE"), nullable=False)
    responder_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    ticket = relationship("ContestTicket", back_populates="responses")
    responder = relationship("User")
