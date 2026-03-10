# Codeforces Clone API

This project provides a FastAPI-based backend for a Codeforces-like platform. It follows a strict **N-Layered Architecture** and includes authentication, role-based authorization, problem management, submission tracking, leaderboards, and user streaks.

## Architecture Overview

- **API Layer** (`app/api`): HTTP routes and Swagger documentation.
- **Service Layer** (`app/services`): Business logic for users, problems, submissions, and leaderboards.
- **Repository Layer** (`app/repositories`): Database interaction using SQLAlchemy.
- **Models Layer** (`app/models`): ORM models for users, problems, testcases, submissions, and educations.
- **Core Layer** (`app/core`): Security utilities and configuration.

## Requirements

- Python 3.11+ (Pydantic v2 supports Python 3.12+).
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

This project includes a lightweight startup migration helper that automatically adds new columns and join tables when the schema evolves (e.g., `is_published`, `is_public`, `owner_id`, `difficulty`, `educations` table, etc.).

The migration runs automatically on application startup.

### Mock Data on Startup

On startup, the application creates:
- The dummy admin user (if missing).
- 20 users (10 creators, 10 regular users).
- 100 problems with various difficulties (1-10) and tags.
- 50+ submissions (mix of pending and accepted).
- Accepted submissions for streak testing (consecutive days).
- Sample editorials for problems.

## Authentication and Roles

### Dummy Admin User
On startup, the system automatically creates a dummy admin:
- **Username**: `admin`
- **Email**: `admin@example.com`
- **Password**: `admin12345`

Use this account to log in and create additional admin/creator users via the admin-only endpoint.

### Roles
- **ADMIN**: Full access to all endpoints and resources.
- **CREATOR**: Can create/manage problems, view submissions, and manage private problems.
- **USER**: Can view published problems, submit solutions, and track progress.

### Public Registration
- `POST /auth/register` creates **user** accounts only. Optionally accepts education entries.

### Admin User Creation
- `POST /auth/admin/create-user` allows admins to create **admin** or **creator** accounts.
- `PUT /auth/admin/users/{username}/active` lets admins ban or reactivate users.

## Problem Entity

A `Problem` contains:
- **Title** (unique)
- **Description**
- **Constraints**
- **Difficulty** (integer 1-10)
- **Testcases** (array of `{input, output}` pairs)
- **Tags** (list of tag names)
- **Editorial** (detailed explanation and reference code solution)
- **Submissions** (each submission tracks `user_id`, `username`, `programming_language`, `code`, `status`, and `submission_time`)
- **Visibility**: Published/Unpublished, Public/Private
- **Allowed Users** (for private problems)

## User Education

Users can add education entries to their profile:
- **Institution** (required)
- **Degree** (required)
- **Field of Study** (optional)
- **Start Year** (required, 1900-2100)
- **End Year** (optional, null means currently studying)
- **Description** (optional)

Education can be added during registration or later via dedicated endpoints.

## API Overview

### Auth Endpoints
- `POST /auth/register` - Register with optional educations
- `POST /auth/login`
- `POST /auth/admin/create-user` - Create admin/creator users
- `GET /auth/admin/users` - List all users (paginated, searchable)
- `PUT /auth/admin/users/{username}/active` - Ban/reactivate user

### User Education Endpoints
- `POST /auth/users/{user_id}/education` - Add education entry
- `PUT /auth/users/education/{education_id}` - Update education
- `DELETE /auth/users/education/{education_id}` - Delete education

### Problem CRUD
- `POST /problems` (admin/creator) - Create problem with difficulty
- `GET /problems` (paginated, searchable, tag filter)
- `GET /problems/{problem_id}`
- `PUT /problems/{problem_id}` (admin/creator)
- `DELETE /problems/{problem_id}` (admin/creator)
- `GET /problems/grouped-by-owner` (admin/creator)

### Problem Access Control
- `POST /problems/{problem_id}/allowed-users/{username}` (admin/creator)
- `DELETE /problems/{problem_id}/allowed-users/{username}` (admin/creator)

### Testcases
- `POST /problems/{problem_id}/testcases` (admin/creator) - Add testcase
- `DELETE /problems/{problem_id}/testcases/{testcase_id}` (admin/creator) - Delete testcase

### Editorials
- `GET /problems/{problem_id}/editorial`
- `POST /problems/{problem_id}/editorial` (admin/creator/owner)
- `PUT /problems/{problem_id}/editorial` (admin/creator/owner)
- `DELETE /problems/{problem_id}/editorial` (admin/creator/owner)

### Tags (Paginated & Searchable)
- `GET /problems/tags?page=1&page_size=20&search=algo`
- `POST /problems/tags` (admin/creator)

### Leaderboards (Paginated & Searchable)
- `GET /leaderboards/submissions?page=1&page_size=20&search=john` - By accepted submissions
- `GET /leaderboards/submissions/last-7-days?page=1&page_size=20&search=john` - By accepted submissions in last 7 days
- `GET /leaderboards/submissions/last-30-days?page=1&page_size=20&search=john` - By accepted submissions in last 30 days
- `GET /leaderboards/submissions/last-year?page=1&page_size=20&search=john` - By accepted submissions in last year
- `GET /leaderboards/creators?page=1&page_size=20&search=jane` - By problems created
- `GET /leaderboards/creators/last-7-days?page=1&page_size=20&search=jane` - By problems created in last 7 days
- `GET /leaderboards/creators/last-30-days?page=1&page_size=20&search=jane` - By problems created in last 30 days
- `GET /leaderboards/creators/last-year?page=1&page_size=20&search=jane` - By problems created in last year

### User Submission History
- `GET /users/me/submission-history?start_date=2024-01-01&end_date=2024-01-31`
  - Returns daily submission counts within date range
  - Shows total submissions and per-date breakdown
- `GET /users/me/submission-history/last-7-days`
- `GET /users/me/submission-history/last-30-days`
- `GET /users/me/submission-history/last-year`

### User Follows
- `GET /users/me/follows` - Follow stats + following list
- `GET /users/admin/{user_id}/followers` - Followers list (admin-only)
- `POST /users/me/follow/{target_user_id}` - Follow a user
- `DELETE /users/me/follow/{target_user_id}` - Unfollow a user

### User Streaks
- `GET /users/me/streaks`
  - **Daily Streak**: Consecutive days with accepted submissions
  - Tracks both current and maximum streaks (current + max)
  - Only ACCEPTED submissions count toward streaks

### Submission CRUD
- `POST /problems/{problem_id}/submissions` (authenticated)
- `GET /problems/{problem_id}/submissions` (admin/creator)
- `GET /problems/submissions/{submission_id}` (admin/creator)
- `PUT /problems/submissions/{submission_id}` (admin/creator)
- `PUT /problems/submissions/{submission_id}/status` (admin/creator) - Update status
- `DELETE /problems/submissions/{submission_id}` (admin/creator)

### Statistics
- `GET /problems/stats/creators` - Problem counts per creator
- `GET /problems/stats/submissions` - Submission counts per problem

## Pagination & Search

Most listing endpoints support pagination and search:

### Query Parameters
- `page`: Page number (1-indexed, default: 1)
- `page_size`: Items per page (1-100, default: 20)
- `search`: Search term (case-insensitive)

### Paginated Response Format
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "pages": 8,
  "has_next": true,
  "has_prev": false
}
```

### Searchable Endpoints
- `GET /problems?search=binary` - Search by title/description
- `GET /problems/tags?search=dp` - Search tags by name
- `GET /auth/admin/users?search=john` - Search users by username/email
- `GET /leaderboards/submissions?search=alice` - Search leaderboard by username

## Submission Status Values

- `PENDING` - Submission is being evaluated
- `ACCEPTED` - Solution is correct
- `WRONG_ANSWER` - Solution produced incorrect output
- `TIME_LIMIT_EXCEEDED` - Solution took too long
- `MEMORY_LIMIT_EXCEEDED` - Solution used too much memory
- `SYNTAX_ERROR` - Solution has compilation/syntax errors

## Tests

Place test files under the `test/` folder. Example:

```bash
mkdir -p test
# Add your tests under test/
```

Run tests:
```bash
PYTHONPATH=/testbed/cmp python3 test/test_auth.py
```

## Swagger Documentation

Access the fully detailed Swagger UI at:
- `http://127.0.0.1:8000/docs`

## Example Usage

### Register with Education
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "password123",
    "educations": [
      {
        "institution": "MIT",
        "degree": "Bachelor of Science",
        "field_of_study": "Computer Science",
        "start_year": 2020,
        "end_year": 2024
      }
    ]
  }'
```

### Get User Streaks
```bash
curl -X GET "http://localhost:8000/users/me/streaks" \
  -H "Authorization: Bearer <token>"
```

### Get Submission History
```bash
curl -X GET "http://localhost:8000/users/me/submission-history?start_date=2024-01-01&end_date=2024-01-31" \
  -H "Authorization: Bearer <token>"
```

### Follow a User
```bash
curl -X POST "http://localhost:8000/users/me/follow/2" \
  -H "Authorization: Bearer <token>"
```

### Get Follow Stats
```bash
curl -X GET "http://localhost:8000/users/me/follows" \
  -H "Authorization: Bearer <token>"
```
