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


class ContestMode(str, enum.Enum):
    """Contest participation mode."""
    INDIVIDUAL = "individual"  # Individual participation
    TEAM = "team"              # Team participation


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
    """User or team registration for a contest."""
    __tablename__ = "contest_registrations"

    id = Column(Integer, primary_key=True, index=True)
    contest_id = Column(Integer, ForeignKey("contests.id", ondelete="CASCADE"), nullable=False)
    # For individual contests: user_id is set, team_id is null
    # For team contests: team_id is set, user_id is the team leader who registered
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=True)
    status = Column(String, default=ContestRegistrationStatus.PENDING.value, nullable=False)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    contest = relationship("Contest", back_populates="registrations")
    user = relationship("User", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approved_by])
    team = relationship("Team", back_populates="registrations")

    @property
    def is_approved(self) -> bool:
        return self.status == ContestRegistrationStatus.APPROVED.value

    @property
    def is_team_registration(self) -> bool:
        return self.team_id is not None


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

    # Contest configuration fields
    penalty_minutes = Column(Integer, default=15, nullable=False)  # Penalty per wrong submission
    contest_mode = Column(String, default=ContestMode.INDIVIDUAL.value, nullable=False)  # individual or team
    team_size = Column(Integer, nullable=True)  # Max team size for team contests (null for individual)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    contest_problems = relationship("ContestProblem", back_populates="contest", cascade="all, delete-orphan", order_by="ContestProblem.order")
    registrations = relationship("ContestRegistration", back_populates="contest", cascade="all, delete-orphan")
    announcements = relationship("ContestAnnouncement", back_populates="contest", cascade="all, delete-orphan", order_by="ContestAnnouncement.created_at.desc()")

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
    def is_individual(self) -> bool:
        return self.contest_mode == ContestMode.INDIVIDUAL.value

    @property
    def is_team(self) -> bool:
        return self.contest_mode == ContestMode.TEAM.value


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
