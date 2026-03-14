from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.team import Team, TeamMember, TeamMembershipStatus
from app.core.config import get_logger

logger = get_logger(__name__)


class TeamRepository:
    def __init__(self, db: Session):
        self.db = db
        logger.debug("TeamRepository initialized")

    def create_team(self, name: str, description: Optional[str], leader_id: int) -> Team:
        """Create a new team."""
        logger.debug(f"Creating team: name='{name}', leader_id={leader_id}")
        
        team = Team(
            name=name,
            description=description,
            leader_id=leader_id
        )
        self.db.add(team)
        self.db.flush()  # Get the team ID
        
        # Add leader as a member
        leader_member = TeamMember(
            team_id=team.id,
            user_id=leader_id,
            role="leader",
            status=TeamMembershipStatus.ACTIVE.value
        )
        self.db.add(leader_member)
        
        self.db.commit()
        self.db.refresh(team)
        logger.debug(f"Team created: id={team.id}, name='{team.name}'")
        return team

    def get_team_by_id(self, team_id: int) -> Optional[Team]:
        """Get team by ID."""
        return self.db.query(Team).filter(Team.id == team_id).first()

    def get_team_by_name(self, name: str) -> Optional[Team]:
        """Get team by name."""
        return self.db.query(Team).filter(Team.name == name).first()

    def list_teams(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        user_id: Optional[int] = None
    ):
        """List teams with optional filtering."""
        query = self.db.query(Team)
        
        if search:
            query = query.filter(
                or_(
                    Team.name.ilike(f"%{search}%"),
                    Team.description.ilike(f"%{search}%")
                )
            )
        
        if user_id:
            # Filter teams where user is an active member
            query = query.join(TeamMember).filter(
                and_(
                    TeamMember.user_id == user_id,
                    TeamMember.status == TeamMembershipStatus.ACTIVE.value
                )
            )
        
        total = query.count()
        teams = query.order_by(Team.created_at.desc()).offset(skip).limit(limit).all()
        return teams, total

    def add_member(self, team: Team, user_id: int, role: str = "member", 
                   status: str = TeamMembershipStatus.ACTIVE.value) -> TeamMember:
        """Add a member to a team."""
        logger.debug(f"Adding member to team {team.id}: user_id={user_id}, role={role}")
        
        member = TeamMember(
            team_id=team.id,
            user_id=user_id,
            role=role,
            status=status
        )
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member

    def get_member(self, team_id: int, user_id: int) -> Optional[TeamMember]:
        """Get a specific team member."""
        return self.db.query(TeamMember).filter(
            and_(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id
            )
        ).first()

    def update_member_status(self, member: TeamMember, status: str) -> TeamMember:
        """Update member status."""
        member.status = status
        self.db.commit()
        self.db.refresh(member)
        return member

    def update_member_role(self, member: TeamMember, role: str) -> TeamMember:
        """Update member role."""
        member.role = role
        self.db.commit()
        self.db.refresh(member)
        return member

    def remove_member(self, member: TeamMember):
        """Remove a member from a team (soft delete by setting status)."""
        member.status = TeamMembershipStatus.REMOVED.value
        self.db.commit()

    def delete_team(self, team: Team):
        """Delete a team."""
        self.db.delete(team)
        self.db.commit()

    def is_team_name_available(self, name: str) -> bool:
        """Check if a team name is available."""
        return self.db.query(Team).filter(Team.name == name).first() is None
