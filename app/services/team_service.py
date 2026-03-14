from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.team_repository import TeamRepository
from app.repositories.user_repository import UserRepository
from app.models.team import Team, TeamMember, TeamMembershipStatus
from app.models.user import User
from app.core.config import get_logger

logger = get_logger(__name__)


class TeamService:
    def __init__(self, db: Session):
        self.team_repo = TeamRepository(db)
        self.user_repo = UserRepository(db)
        logger.debug("TeamService initialized")

    def create_team(self, name: str, description: Optional[str], leader: User) -> Team:
        """Create a new team."""
        logger.info(f"Creating team: name='{name}', leader={leader.username}")
        
        # Validate team name
        if not name or len(name.strip()) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Team name must be at least 3 characters long"
            )
        
        # Check if name is available
        if not self.team_repo.is_team_name_available(name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team name '{name}' is already taken"
            )
        
        team = self.team_repo.create_team(
            name=name.strip(),
            description=description,
            leader_id=leader.id
        )
        
        logger.info(f"Team created: id={team.id}, name='{team.name}'")
        return team

    def get_team(self, team_id: int) -> Team:
        """Get a team by ID."""
        team = self.team_repo.get_team_by_id(team_id)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )
        return team

    def list_teams(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        user_id: Optional[int] = None
    ):
        """List teams with pagination."""
        skip = (page - 1) * page_size
        teams, total = self.team_repo.list_teams(
            skip=skip,
            limit=page_size,
            search=search,
            user_id=user_id
        )
        
        pages = (total + page_size - 1) // page_size if total > 0 else 0
        has_next = page < pages
        has_prev = page > 1
        
        return {
            "items": teams,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }

    def add_member(self, team_id: int, username: str, current_user: User) -> TeamMember:
        """Add a member to a team."""
        logger.info(f"Adding member to team {team_id}: username={username}")
        
        team = self.get_team(team_id)
        
        # Check if current user is team leader
        if team.leader_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only team leader can add members"
            )
        
        # Get user to add
        user_to_add = self.user_repo.get_user_by_username(username)
        if not user_to_add:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )
        
        # Check if user is already a member
        existing_member = self.team_repo.get_member(team_id, user_to_add.id)
        if existing_member and existing_member.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User '{username}' is already a team member"
            )
        
        # Add or reactivate member
        if existing_member:
            member = self.team_repo.update_member_status(
                existing_member, 
                TeamMembershipStatus.ACTIVE.value
            )
        else:
            member = self.team_repo.add_member(
                team=team,
                user_id=user_to_add.id,
                role="member",
                status=TeamMembershipStatus.ACTIVE.value
            )
        
        logger.info(f"Member added: team_id={team_id}, user_id={user_to_add.id}")
        return member

    def remove_member(self, team_id: int, user_id: int, current_user: User):
        """Remove a member from a team."""
        logger.info(f"Removing member from team {team_id}: user_id={user_id}")
        
        team = self.get_team(team_id)
        
        # Check if current user is team leader or removing themselves
        if team.leader_id != current_user.id and current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only team leader can remove members"
            )
        
        # Cannot remove leader
        if user_id == team.leader_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove team leader. Transfer leadership first or delete the team."
            )
        
        member = self.team_repo.get_member(team_id, user_id)
        if not member or not member.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in team"
            )
        
        self.team_repo.remove_member(member)
        logger.info(f"Member removed: team_id={team_id}, user_id={user_id}")
        
        return {"message": "Member removed successfully"}

    def leave_team(self, team_id: int, current_user: User):
        """Current user leaves a team."""
        logger.info(f"User leaving team {team_id}: user_id={current_user.id}")
        
        team = self.get_team(team_id)
        
        # Leader cannot leave, must transfer or delete
        if team.leader_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Team leader cannot leave. Transfer leadership or delete the team."
            )
        
        member = self.team_repo.get_member(team_id, current_user.id)
        if not member or not member.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You are not a member of this team"
            )
        
        member.status = TeamMembershipStatus.LEFT.value
        self.team_repo.db.commit()
        
        logger.info(f"User left team: team_id={team_id}, user_id={current_user.id}")
        return {"message": "You have left the team"}

    def transfer_leadership(self, team_id: int, new_leader_id: int, current_user: User):
        """Transfer team leadership to another member."""
        logger.info(f"Transferring leadership: team_id={team_id}, new_leader_id={new_leader_id}")
        
        team = self.get_team(team_id)
        
        # Only current leader can transfer
        if team.leader_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only team leader can transfer leadership"
            )
        
        # Check new leader is a member
        new_leader_member = self.team_repo.get_member(team_id, new_leader_id)
        if not new_leader_member or not new_leader_member.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New leader must be an active team member"
            )
        
        # Update roles
        old_leader_member = self.team_repo.get_member(team_id, current_user.id)
        self.team_repo.update_member_role(old_leader_member, "member")
        self.team_repo.update_member_role(new_leader_member, "leader")
        
        # Update team leader
        team.leader_id = new_leader_id
        self.team_repo.db.commit()
        
        logger.info(f"Leadership transferred: team_id={team_id}, new_leader_id={new_leader_id}")
        return {"message": "Leadership transferred successfully"}

    def delete_team(self, team_id: int, current_user: User):
        """Delete a team."""
        logger.info(f"Deleting team {team_id}")
        
        team = self.get_team(team_id)
        
        # Only leader can delete
        if team.leader_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only team leader can delete the team"
            )
        
        self.team_repo.delete_team(team)
        logger.info(f"Team deleted: team_id={team_id}")
        return {"message": "Team deleted successfully"}

    def is_user_in_team(self, team_id: int, user_id: int) -> bool:
        """Check if a user is an active member of a team."""
        team = self.team_repo.get_team_by_id(team_id)
        if not team:
            return False
        return team.has_member(user_id)
