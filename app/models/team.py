import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class TeamMembershipStatus(str, enum.Enum):
    """Status of a team member."""
    PENDING = "pending"    # Invitation sent, awaiting acceptance
    ACTIVE = "active"      # Member is active in the team
    REMOVED = "removed"    # Member was removed from the team
    LEFT = "left"          # Member left the team


class TeamMember(Base):
    """Association model for team members with status tracking."""
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default=TeamMembershipStatus.ACTIVE.value, nullable=False)
    role = Column(String, default="member", nullable=False)  # "leader" or "member"
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("User")

    @property
    def is_leader(self) -> bool:
        return self.role == "leader"

    @property
    def is_active(self) -> bool:
        return self.status == TeamMembershipStatus.ACTIVE.value


class Team(Base):
    """Team model for group participation in contests."""
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    leader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    leader = relationship("User", foreign_keys=[leader_id])
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    registrations = relationship("ContestRegistration", back_populates="team", cascade="all, delete-orphan")

    @property
    def active_members(self):
        """Returns list of active team members."""
        return [m for m in self.members if m.is_active]

    @property
    def member_count(self) -> int:
        """Returns count of active members."""
        return len(self.active_members)

    @property
    def member_ids(self) -> list[int]:
        """Returns list of active member user IDs."""
        return [m.user_id for m in self.active_members]

    @property
    def member_usernames(self) -> list[str]:
        """Returns list of active member usernames."""
        return [m.user.username for m in self.active_members if m.user]

    def has_member(self, user_id: int) -> bool:
        """Check if user is an active member of the team."""
        return any(m.user_id == user_id and m.is_active for m in self.members)

    def get_member(self, user_id: int):
        """Get team member by user ID."""
        for m in self.members:
            if m.user_id == user_id:
                return m
        return None
