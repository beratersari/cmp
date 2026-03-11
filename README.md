# Codeforces Clone API

This project provides a FastAPI-based backend for a Codeforces-like platform. It follows a strict **N-Layered Architecture** and includes authentication, role-based authorization, problem management, submission tracking, leaderboards, user streaks, voting, and a forum system.

## Architecture Overview

- **API Layer** (`app/api`): HTTP routes and Swagger documentation.
- **Service Layer** (`app/services`): Business logic for users, problems, submissions, leaderboards, voting, and forum.
- **Repository Layer** (`app/repositories`): Database interaction using SQLAlchemy.
- **Models Layer** (`app/models`): ORM models for users, problems, testcases, submissions, educations, votes, and forum posts/comments.
- **Core Layer** (`app/core`): Security utilities, logging configuration, and application settings.

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

### Logging Configuration

The application includes a comprehensive logging system with configurable log levels and colorful console output.

**Log Levels:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

**Configuration (in `app/core/config.py`):**
```python
# Set the minimum log level
LOG_LEVEL = LogLevel.DEBUG  # Shows DEBUG and above

# Enable/disable colored output
COLORED_LOGS = True

# Enable file logging
FILE_LOGGING = True
LOG_FILE = "app.log"
```

**Color Scheme:**
- `DEBUG` - Cyan
- `INFO` - Green
- `WARNING` - Yellow
- `ERROR` - Red
- `CRITICAL` - Magenta
- Timestamps - Gray
- Logger names - Blue

### Mock Data on Startup

On startup, the application creates:
- The dummy admin user (if missing).
- 20 users (10 creators, 10 regular users).
- 100 problems with various difficulties (1-10) and tags.
- 50+ submissions (mix of pending and accepted).
- Accepted submissions for streak testing (consecutive days).
- Sample editorials for problems.
- **3 forum posts with 30+ comments and nested replies**.

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

### Problem Discussions (LeetCode-style)
- `POST /problems/{problem_id}/discussions` - Create a discussion thread for a problem
- `GET /problems/{problem_id}/discussions` - List discussions for a problem (paginated)
- `GET /problems/discussions/{discussion_id}` - Get a discussion with comment tree
- `PUT /problems/discussions/{discussion_id}` - Update a discussion (author/admin)
- `DELETE /problems/discussions/{discussion_id}` - Delete a discussion (author/admin)
- `POST /problems/discussions/{discussion_id}/comments` - Add a comment or reply
- `GET /problems/discussions/{discussion_id}/comments` - Get discussion comments (tree)
- `GET /problems/discussion-comments/{comment_id}` - Get a discussion comment
- `PUT /problems/discussion-comments/{comment_id}` - Update a discussion comment
- `DELETE /problems/discussion-comments/{comment_id}` - Delete a discussion comment

### Problem Bookmarks
- `POST /problems/{problem_id}/bookmarks` - Bookmark a problem
- `DELETE /problems/{problem_id}/bookmarks` - Remove a bookmark
- `GET /problems/bookmarks` - List your bookmarked problems (paginated)
- `GET /problems/{problem_id}/bookmarks/me` - Check if a problem is bookmarked

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

### Following Leaderboards (Authenticated)
Leaderboards consisting only of users you follow (plus yourself):
- `GET /leaderboards/following?page=1&page_size=20` - By accepted submissions
- `GET /leaderboards/following/last-7-days?page=1&page_size=20` - By accepted submissions in last 7 days
- `GET /leaderboards/following/last-30-days?page=1&page_size=20` - By accepted submissions in last 30 days
- `GET /leaderboards/following/last-year?page=1&page_size=20` - By accepted submissions in last year

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

### Voting (Likes/Dislikes)
Users can vote on problems and editorials:
- `POST /problems/{problem_id}/vote` - Cast a like/dislike vote on a problem
- `GET /problems/{problem_id}/votes` - Get vote statistics for a problem
- `POST /problems/{problem_id}/editorial/vote` - Cast a like/dislike vote on an editorial
- `GET /problems/{problem_id}/editorial/votes` - Get vote statistics for an editorial
- `GET /problems/stats/votes` - Get vote statistics grouped by creator
- `DELETE /problems/{problem_id}/vote` - Remove your vote from a problem
- `DELETE /problems/{problem_id}/editorial/vote` - Remove your vote from an editorial

**Vote Types:** `LIKE`, `DISLIKE`

### Forum
A tree-structured forum system for community discussions:

#### Posts
- `POST /forum/posts` - Create a new forum post
- `GET /forum/posts` - List all forum posts (paginated)
  - Regular users see only published posts
  - Admins can see all posts including unpublished/deleted
- `GET /forum/posts/{post_id}` - Get a specific post with all comments (tree structure)
- `PUT /forum/posts/{post_id}` - Update a post (author or admin only)
- `DELETE /forum/posts/{post_id}` - Delete a post (soft delete by default)
- `PUT /forum/posts/{post_id}/publish` - Publish or unpublish a post

#### Comments (Tree Structure)
- `POST /forum/posts/{post_id}/comments` - Create a comment or reply
  - Set `parent_id` to reply to an existing comment
  - Without `parent_id`, creates a top-level comment
- `GET /forum/posts/{post_id}/comments` - Get all comments in tree structure
- `GET /forum/comments/{comment_id}` - Get a specific comment
- `PUT /forum/comments/{comment_id}` - Update a comment (author or admin only)
- `DELETE /forum/comments/{comment_id}` - Delete a comment (soft delete by default)

#### Emoji Reactions
Users can react to posts and comments with emoji strings like `:happy:`, `:angry:`, `:sad:`.
Each user can only have **one reaction per post/comment** (adding a new reaction updates the existing one).

- `GET /forum/emojis` - Get list of valid emoji strings
- `POST /forum/posts/{post_id}/reactions` - Add/update emoji reaction on a post
- `GET /forum/posts/{post_id}/reactions` - Get all emoji reactions for a post
- `GET /forum/posts/{post_id}/reactions/me` - Get current user's reaction on a post
- `DELETE /forum/posts/{post_id}/reactions` - Remove emoji reaction from a post
- `POST /forum/comments/{comment_id}/reactions` - Add/update emoji reaction on a comment
- `GET /forum/comments/{comment_id}/reactions` - Get all emoji reactions for a comment
- `GET /forum/comments/{comment_id}/reactions/me` - Get current user's reaction on a comment
- `DELETE /forum/comments/{comment_id}/reactions` - Remove emoji reaction from a comment

**Valid Emojis:** `:happy:`, `:sad:`, `:angry:`, `:laugh:`, `:love:`, `:thumbsup:`, `:thumbsdown:`, `:wow:`, `:cool:`, `:confused:`, `:fire:`, `:rocket:`, `:clap:`, `:thinking:`

**Comment Tree Structure:** Comments support nested replies. Each comment can have replies, which can have their own replies, creating a tree structure. The API returns comments organized hierarchically with a `replies` array for each comment.

**Visibility Rules:**
- Only published posts can be commented on
- Users can only edit/delete their own posts/comments
- Admins can manage all posts/comments
- Soft-deleted content is hidden from regular users but visible to admins

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

### Create a Forum Post
```bash
curl -X POST "http://localhost:8000/forum/posts" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "title": "Tips for Beginners",
    "content": "Here are some tips for getting started with competitive programming..."
  }'
```

### Add a Comment to a Post
```bash
curl -X POST "http://localhost:8000/forum/posts/1/comments" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "content": "Great post! Thanks for sharing."
  }'
```

### Reply to a Comment (Nested Reply)
```bash
curl -X POST "http://localhost:8000/forum/posts/1/comments" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "content": "I agree with your point!",
    "parent_id": 1
  }'
```

### Get Post with Comment Tree
```bash
curl -X GET "http://localhost:8000/forum/posts/1" \
  -H "Authorization: Bearer <token>"
```

### Vote on a Problem
```bash
curl -X POST "http://localhost:8000/problems/1/vote" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "vote_type": "LIKE"
  }'
```

### Create a Problem Discussion
```bash
curl -X POST "http://localhost:8000/problems/1/discussions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "title": "My Approach",
    "content": "Here is how I solved this problem..."
  }'
```

### Add a Comment to a Discussion
```bash
curl -X POST "http://localhost:8000/problems/discussions/1/comments" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "content": "Interesting solution!",
    "parent_id": null
  }'
```

### Get Discussion with Comment Tree
```bash
curl -X GET "http://localhost:8000/problems/discussions/1" \
  -H "Authorization: Bearer <token>"
```

### Add Emoji Reaction to a Post
```bash
curl -X POST "http://localhost:8000/forum/posts/1/reactions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "emoji": ":happy:"
  }'
```

### Get Emoji Reactions for a Post
```bash
curl -X GET "http://localhost:8000/forum/posts/1/reactions" \
  -H "Authorization: Bearer <token>"
```

### Add Emoji Reaction to a Comment
```bash
curl -X POST "http://localhost:8000/forum/comments/1/reactions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "emoji": ":thumbsup:"
  }'
```

### Get Valid Emoji List
```bash
curl -X GET "http://localhost:8000/forum/emojis" \
  -H "Authorization: Bearer <token>"
```

### Get Following Leaderboard
```bash
curl -X GET "http://localhost:8000/leaderboards/following?page=1&page_size=10" \
  -H "Authorization: Bearer <token>"
```

### Get Following Leaderboard (Last 7 Days)
```bash
curl -X GET "http://localhost:8000/leaderboards/following/last-7-days?page=1&page_size=10" \
  -H "Authorization: Bearer <token>"
```
