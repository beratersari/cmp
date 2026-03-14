from typing import Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.team_service import TeamService
from app.api.dependencies import RoleChecker, get_current_user
from app.models.user import UserRole
from app.core.config import get_logger
from app.schemas import PaginatedResponse

logger = get_logger(__name__)

router = APIRouter(
    prefix="/teams",
    tags=["Teams"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new team",
    description="""
    Create a new team.
    
    The creator automatically becomes the team leader.
    
    ### Required Fields:
    - **name**: Team name (unique, at least 3 characters)
    
    ### Optional Fields:
    - **description**: Team description
    """
)
def create_team(
    name: str,
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Creating team: name='{name}' by {current_user.username}")
    team_service = TeamService(db)
    team = team_service.create_team(name=name, description=description, leader=current_user)
    return {
        "id": team.id,
        "name": team.name,
        "description": team.description,
        "leader_id": team.leader_id,
        "leader_username": current_user.username,
        "member_count": team.member_count,
        "created_at": team.created_at
    }


@router.get(
    "",
    response_model=dict,
    summary="List teams",
    description="""
    List all teams with pagination and search.
    
    ### Filters:
    - `search`: Search by team name or description
    - `my_teams`: If true, show only teams where current user is a member
    
    ### Pagination:
    - Use `page` and `page_size` query parameters
    """
)
def list_teams(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    search: Optional[str] = Query(default=None, description="Search by name or description"),
    my_teams: bool = Query(default=False, description="Show only my teams"),
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Listing teams: page={page}, search={search}, my_teams={my_teams}")
    team_service = TeamService(db)
    
    user_id = current_user.id if my_teams else None
    result = team_service.list_teams(
        page=page,
        page_size=page_size,
        search=search,
        user_id=user_id
    )
    
    # Convert teams to response format
    result["items"] = [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "leader_id": t.leader_id,
            "leader_username": t.leader.username if t.leader else None,
            "member_count": t.member_count,
            "created_at": t.created_at
        }
        for t in result["items"]
    ]
    
    return result


@router.get(
    "/{team_id}",
    response_model=dict,
    summary="Get team details",
    description="Get detailed information about a team including members."
)
def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Getting team: team_id={team_id}")
    team_service = TeamService(db)
    team = team_service.get_team(team_id)
    
    return {
        "id": team.id,
        "name": team.name,
        "description": team.description,
        "leader_id": team.leader_id,
        "leader_username": team.leader.username if team.leader else None,
        "members": [
            {
                "user_id": m.user_id,
                "username": m.user.username if m.user else None,
                "role": m.role,
                "status": m.status,
                "joined_at": m.joined_at
            }
            for m in team.active_members
        ],
        "member_count": team.member_count,
        "created_at": team.created_at
    }


@router.post(
    "/{team_id}/members",
    response_model=dict,
    summary="Add member to team",
    description="""
    Add a member to the team by username.
    
    ### Authorization:
    - Only team leader can add members
    """
)
def add_team_member(
    team_id: int,
    username: str,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Adding member to team {team_id}: username={username}")
    team_service = TeamService(db)
    member = team_service.add_member(team_id, username, current_user)
    
    return {
        "team_id": team_id,
        "user_id": member.user_id,
        "username": member.user.username if member.user else None,
        "role": member.role,
        "status": member.status,
        "message": "Member added successfully"
    }


@router.delete(
    "/{team_id}/members/{user_id}",
    response_model=dict,
    summary="Remove member from team",
    description="""
    Remove a member from the team.
    
    ### Authorization:
    - Team leader can remove any member
    - Members can remove themselves (leave the team)
    """
)
def remove_team_member(
    team_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Removing member from team {team_id}: user_id={user_id}")
    team_service = TeamService(db)
    result = team_service.remove_member(team_id, user_id, current_user)
    return result


@router.post(
    "/{team_id}/leave",
    response_model=dict,
    summary="Leave team",
    description="""
    Leave the team (for current user).
    
    Team leader cannot leave. Must transfer leadership or delete team first.
    """
)
def leave_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"User leaving team {team_id}: user_id={current_user.id}")
    team_service = TeamService(db)
    result = team_service.leave_team(team_id, current_user)
    return result


@router.post(
    "/{team_id}/transfer-leadership",
    response_model=dict,
    summary="Transfer team leadership",
    description="""
    Transfer team leadership to another member.
    
    ### Authorization:
    - Only current team leader can transfer leadership
    - New leader must be an active member of the team
    """
)
def transfer_leadership(
    team_id: int,
    new_leader_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Transferring leadership: team_id={team_id}, new_leader_id={new_leader_id}")
    team_service = TeamService(db)
    result = team_service.transfer_leadership(team_id, new_leader_id, current_user)
    return result


@router.delete(
    "/{team_id}",
    response_model=dict,
    summary="Delete team",
    description="""
    Delete a team.
    
    ### Authorization:
    - Only team leader can delete the team
    """
)
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(RoleChecker([UserRole.ADMIN, UserRole.CREATOR, UserRole.USER]))
):
    logger.info(f"Deleting team {team_id}")
    team_service = TeamService(db)
    result = team_service.delete_team(team_id, current_user)
    return result
