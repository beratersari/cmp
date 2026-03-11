"""
Test script to verify the voting functionality works correctly.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.core.security import get_password_hash
from app.models.user import User, UserRole

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="function")
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Create test users
    admin_user = User(
        username="admin",
        email="admin@test.com",
        hashed_password=get_password_hash("adminpass123"),
        role=UserRole.ADMIN,
        is_active=True
    )
    creator_user = User(
        username="creator",
        email="creator@test.com",
        hashed_password=get_password_hash("creatorpass123"),
        role=UserRole.CREATOR,
        is_active=True
    )
    regular_user = User(
        username="user",
        email="user@test.com",
        hashed_password=get_password_hash("userpass123"),
        role=UserRole.USER,
        is_active=True
    )
    db.add(admin_user)
    db.add(creator_user)
    db.add(regular_user)
    db.commit()
    
    yield db
    
    db.close()
    Base.metadata.drop_all(bind=engine)


def get_token(username, password):
    response = client.post(
        "/auth/login",
        data={"username": username, "password": password}
    )
    return response.json()["access_token"]


def test_vote_problem(setup_db):
    # Get tokens
    admin_token = get_token("admin", "adminpass123")
    user_token = get_token("user", "userpass123")
    
    # Create a problem as admin
    problem_data = {
        "title": "Test Problem",
        "description": "A test problem",
        "constraints": "None",
        "difficulty": 5,
        "testcases": [{"input": "1 2", "output": "3"}],
        "is_published": True,
        "is_public": True
    }
    response = client.post(
        "/problems",
        json=problem_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    problem_id = response.json()["id"]
    
    # Vote on the problem as user
    vote_data = {"vote_type": "like"}
    response = client.post(
        f"/problems/{problem_id}/vote",
        json=vote_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 201
    assert response.json()["vote_type"] == "like"
    assert response.json()["target_type"] == "problem"
    
    # Get vote stats
    response = client.get(f"/problems/{problem_id}/stats")
    assert response.status_code == 200
    stats = response.json()
    assert stats["problem_id"] == problem_id
    assert stats["votes"]["likes"] == 1
    assert stats["votes"]["dislikes"] == 0
    assert stats["votes"]["total"] == 1
    assert stats["votes"]["like_rate"] == 1.0
    
    # Change vote to dislike
    vote_data = {"vote_type": "dislike"}
    response = client.post(
        f"/problems/{problem_id}/vote",
        json=vote_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 201
    assert response.json()["vote_type"] == "dislike"
    
    # Verify stats updated
    response = client.get(f"/problems/{problem_id}/stats")
    stats = response.json()
    assert stats["votes"]["likes"] == 0
    assert stats["votes"]["dislikes"] == 1
    assert stats["votes"]["like_rate"] == 0.0
    
    # Delete vote
    response = client.delete(
        f"/problems/{problem_id}/vote",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 200
    
    # Verify stats updated
    response = client.get(f"/problems/{problem_id}/stats")
    stats = response.json()
    assert stats["votes"]["total"] == 0


def test_vote_editorial(setup_db):
    # Get tokens
    admin_token = get_token("admin", "adminpass123")
    user_token = get_token("user", "userpass123")
    
    # Create a problem as admin
    problem_data = {
        "title": "Test Problem 2",
        "description": "A test problem",
        "constraints": "None",
        "difficulty": 5,
        "testcases": [{"input": "1 2", "output": "3"}],
        "is_published": True,
        "is_public": True
    }
    response = client.post(
        "/problems",
        json=problem_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    problem_id = response.json()["id"]
    
    # Create editorial
    editorial_data = {
        "description": "Solution explanation",
        "code_solution": "print(a + b)"
    }
    response = client.post(
        f"/problems/{problem_id}/editorial",
        json=editorial_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    
    # Vote on the editorial as user
    vote_data = {"vote_type": "like"}
    response = client.post(
        f"/problems/{problem_id}/editorial/vote",
        json=vote_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 201
    assert response.json()["vote_type"] == "like"
    assert response.json()["target_type"] == "editorial"
    
    # Get editorial vote stats
    response = client.get(f"/problems/{problem_id}/editorial/stats")
    assert response.status_code == 200
    stats = response.json()
    assert stats["problem_id"] == problem_id
    assert stats["votes"]["likes"] == 1


def test_creator_vote_stats(setup_db):
    # Get tokens
    admin_token = get_token("admin", "adminpass123")
    user_token = get_token("user", "userpass123")
    
    # Create problems as admin
    for i in range(3):
        problem_data = {
            "title": f"Test Problem {i+10}",
            "description": "A test problem",
            "constraints": "None",
            "difficulty": 5,
            "testcases": [{"input": "1 2", "output": "3"}],
            "is_published": True,
            "is_public": True
        }
        response = client.post(
            "/problems",
            json=problem_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        problem_id = response.json()["id"]
        
        # Add votes
        vote_type = "like" if i < 2 else "dislike"
        client.post(
            f"/problems/{problem_id}/vote",
            json={"vote_type": vote_type},
            headers={"Authorization": f"Bearer {user_token}"}
        )
    
    # Get creator stats
    response = client.get(
        "/problems/stats/votes/by-creator",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    stats = response.json()
    assert len(stats) >= 1
    
    # Find admin's stats
    admin_stats = next(s for s in stats if s["username"] == "admin")
    assert admin_stats["total_problems"] == 3
    assert admin_stats["total_likes"] == 2
    assert admin_stats["total_dislikes"] == 1
    assert admin_stats["total_votes"] == 3
    assert abs(admin_stats["overall_like_rate"] - 2/3) < 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
