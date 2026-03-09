import sys
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db, run_sqlite_migrations
from app.main import app

# Setup test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
Base.metadata.create_all(bind=engine)
# Apply migrations for new columns
run_sqlite_migrations(engine)

client = TestClient(app)

def test_register_and_login():
    # 1. Register a new user
    response = client.post(
        "/auth/register",
        json={"username": "testuser", "email": "test@example.com", "password": "password123", "role": "user"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert "id" in data

    # 2. Login with the new user
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    token = data["access_token"]

    # 3. Access a protected route (fails because not admin)
    response = client.get(
        "/admin-only",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403

    # 4. Login as admin (using the bootstrap admin)
    from app.mock_data import seed_mock_data
    db = TestingSessionLocal()
    seed_mock_data(db)
    db.close()

    response = client.post(
        "/auth/login",
        data={"username": "admin", "password": "admin12345"}
    )
    if response.status_code != 200:
        print(f"Admin login failed: {response.status_code} - {response.text}")
    assert response.status_code == 200
    token = response.json()["access_token"]

    # 6. Access admin route
    response = client.get(
        "/admin-only",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Hello Admin! You have access to this protected resource."}

    print("All tests passed!")

if __name__ == "__main__":
    try:
        test_register_and_login()
    finally:
        if os.path.exists("./test.db"):
            os.remove("./test.db")
