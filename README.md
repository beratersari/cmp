# Codeforces Clone API

This project provides a FastAPI-based backend for a Codeforces-like platform. It follows a strict **N-Layered Architecture** and includes authentication, role-based authorization, problem management, and submission tracking.

## Architecture Overview

- **API Layer** (`app/api`): HTTP routes and Swagger documentation.
- **Service Layer** (`app/services`): Business logic for users, problems, and submissions.
- **Repository Layer** (`app/repositories`): Database interaction using SQLAlchemy.
- **Models Layer** (`app/models`): ORM models for users, problems, testcases, and submissions.
- **Core Layer** (`app/core`): Security utilities and configuration.

## Requirements

- Python 3.11+ (Pydantic v1 has compatibility issues with Python 3.12+).
- SQLite database file stored in the project root (`codeforces_clone.db`).

Install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run the application:

```bash
uvicorn app.main:app --reload
```

### SQLite Migrations

This project includes a lightweight startup migration helper that automatically adds new columns and join tables when the schema evolves (e.g., `is_published`, `is_public`, `owner_id`, and the `problem_allowed_users` join table).

The migration runs automatically on application startup.

### Mock Data on Startup

On startup, the application creates:
- The dummy admin user (if missing).
- A sample published public problem (if no problems exist).

## Authentication and Roles

### Dummy Admin User
On startup, the system automatically creates a dummy admin:
- **Username**: `admin`
- **Email**: `admin@example.com`
- **Password**: `admin12345`

Use this account to log in and create additional admin/creator users via the admin-only endpoint.

### Public Registration
- `POST /auth/register` creates **user** accounts only.

### Admin User Creation
- `POST /auth/admin/create-user` allows admins to create **admin** or **creator** accounts.
- `PUT /auth/admin/users/{username}/active` lets admins ban or reactivate users.

## Problem Entity

A `Problem` contains:
- **Title**
- **Description**
- **Constraints**
- **Testcases** (array of `{input, output}` pairs)
- **Tags** (list of tag names)
- **Editorial** (detailed explanation and reference code solution)
- **Submissions** (each submission tracks `user_id`, `username`, `programming_language`, `code`, `status`, and `submission_time`)

## API Overview

### Auth Endpoints
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/admin/create-user`
- `PUT /auth/admin/users/{username}/active`

### Problem CRUD
- `POST /problems` (admin/creator)
- `GET /problems` (supports `?tag=` filter)
- `GET /problems/{problem_id}`
- `PUT /problems/{problem_id}` (admin/creator)
- `DELETE /problems/{problem_id}` (admin/creator)

### Editorials
- `GET /problems/{problem_id}/editorial`
- `POST /problems/{problem_id}/editorial` (admin/creator/owner)
- `PUT /problems/{problem_id}/editorial` (admin/creator/owner)
- `DELETE /problems/{problem_id}/editorial` (admin/creator/owner)

### Tags
- `GET /problems/tags`
- `POST /problems/tags` (admin/creator)

### Leaderboards
- `GET /leaderboards/submissions`
- `GET /leaderboards/creators`

### Submission CRUD
- `POST /problems/{problem_id}/submissions` (authenticated)
- `GET /problems/{problem_id}/submissions` (admin/creator)
- `GET /problems/submissions/{submission_id}` (admin/creator)
- `PUT /problems/submissions/{submission_id}` (admin/creator)
- `PUT /problems/submissions/{submission_id}/status` (admin/creator)
- `DELETE /problems/submissions/{submission_id}` (admin/creator)

## Tests

Place test files under the `test/` folder. Example:

```bash
mkdir -p test
# Add your tests under test/
```

## Swagger Documentation

Access the fully detailed Swagger UI at:
- `http://127.0.0.1:8000/docs`
