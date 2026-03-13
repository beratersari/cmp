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
- **5 contests with 30 problems each (150 contest problems total)**.
- **Contest announcements for each contest**.
- **Contest discussions with comments for each contest**.
- **Contest registrations for private contests (some approved, some pending)**.
- **Contest submissions for each contest (mix of on-time and late submissions)**.
- **Contest managers for team collaboration**.
- **Contest tickets with responses (clarification system)**.

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
- **Submissions** (each submission tracks `user_id`, `username`, `programming_language`, `code`, `status`, `submission_time`, and contest-related fields)
- **Visibility**: Published/Unpublished, Public/Private
- **Allowed Users** (for private problems)

## Submission Entity

A `Submission` contains:
- **problem_id** (required)
- **user_id** (required)
- **username** (required)
- **programming_language** (required)
- **code** (required)
- **status** (PENDING, ACCEPTED, WRONG_ANSWER, etc.)
- **submission_time** (timestamp)
- **contest_id** (optional) - The contest ID if submitted during a contest
- **is_contest_submission** (boolean) - Whether this was submitted via contest endpoint
- **is_late_submission** (boolean) - Whether this contest submission was made after contest end time

### Submission Separation

Submissions are separated into two categories:

1. **Individual Problem Submissions**: Made via `POST /problems/{problem_id}/submissions`
   - These are NOT associated with any contest
   - When listing submissions for a problem, contest submissions are excluded by default

2. **Contest Submissions**: Made via `POST /contests/{contest_id}/problems/{problem_id}/submissions`
   - These are linked to a specific contest via `contest_id`
   - Marked with `is_contest_submission=True`
   - If submitted after contest end time, marked with `is_late_submission=True`
   - When listing submissions for a contest, only contest submissions are shown

This separation ensures that contest submissions don't pollute individual problem submission lists, similar to Codeforces and LeetCode.

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

### Contests
Contests allow you to organize problems into timed competitions.

#### Contest Types
Contests can have three types:
- **public**: Visible to everyone, problems visible to everyone
- **private**: Visible to everyone, but problems only visible to registered (approved) users
- **archived**: Only visible to owner/admin (used for historical contests)

#### Contest CRUD
- `POST /contests` - Create a new contest (admin/creator)
- `GET /contests` - List all contests (filtered by visibility)
- `GET /contests/upcoming` - List upcoming contests
- `GET /contests/active` - List currently running contests
- `GET /contests/past` - List past contests
- `GET /contests/{contest_id}` - Get contest details with problems
- `PUT /contests/{contest_id}` - Update a contest (admin/owner)
- `DELETE /contests/{contest_id}` - Delete a contest (admin/owner)

#### Contest Problem Management
- `POST /contests/{contest_id}/problems` - Add problems to a contest
- `DELETE /contests/{contest_id}/problems` - Remove problems from a contest
- `PUT /contests/{contest_id}/problems/order` - Reorder problems in a contest

#### Contest Registration
For private contests, users must register and be approved to see problems:
- `POST /contests/{contest_id}/register` - Register for a contest
- `GET /contests/{contest_id}/registration` - Get my registration status
- `DELETE /contests/{contest_id}/registration` - Cancel my registration
- `GET /contests/{contest_id}/registrations` - List all registrations (admin/owner)
- `PUT /contests/{contest_id}/registrations/{registration_id}` - Approve/reject registration (admin/owner)
- `GET /contests/{contest_id}/registrations/summary` - Get registration summary (admin/owner)
- `GET /contests/my/registrations` - List all my contest registrations

**Registration Status Values:**
- `pending` - Registration awaiting approval
- `approved` - User can see problems in private contests
- `rejected` - User's registration was denied

#### Contest Announcements
Admins and contest creators can create announcements for contests:
- `POST /contests/{contest_id}/announcements` - Create an announcement (admin/owner)
- `GET /contests/{contest_id}/announcements` - List announcements for a contest (paginated)
- `GET /contests/{contest_id}/announcements/{announcement_id}` - Get a specific announcement
- `PUT /contests/{contest_id}/announcements/{announcement_id}` - Update an announcement (admin/owner)
- `DELETE /contests/{contest_id}/announcements/{announcement_id}` - Delete an announcement (admin/owner)

**Announcement Features:**
- Announcements have a title and content
- Can be published or unpublished (draft mode)
- Only admins and contest owners can create/edit/delete announcements
- Regular users can only see published announcements
- Announcements are ordered by creation date (newest first)

#### Contest Submissions
Contest submissions are separated from individual problem submissions:

- `POST /contests/{contest_id}/problems/{problem_id}/submissions` - Submit code for a contest problem
- `GET /contests/{contest_id}/submissions` - List all contest submissions (admin/owner only)
- `GET /contests/{contest_id}/my/submissions` - List my contest submissions
- `GET /contests/{contest_id}/problems/{problem_id}/submissions` - List contest submissions for a specific problem (admin/owner only)

**Submission Features:**
- Contest submissions are linked to the contest via `contest_id`
- Marked with `is_contest_submission=True`
- If submitted after contest end time, marked with `is_late_submission=True`
- Contest submissions do NOT appear when listing submissions for a problem outside the contest
- Individual problem submissions do NOT appear when listing contest submissions

#### Contest Managers (Team Collaboration)
Contest managers allow team collaboration on contests. Managers can be added by owners/admins and have full edit permissions:

- `POST /contests/{contest_id}/managers/{user_id}` - Add a manager to a contest (admin/owner only)
- `DELETE /contests/{contest_id}/managers/{user_id}` - Remove a manager from a contest (admin/owner only)
- `GET /contests/{contest_id}/managers` - List all managers for a contest

**Manager Permissions:**
Managers have the same permissions as owners (except adding/removing other managers):
- View contest problems (including private contests)
- Edit contest details (title, description, dates, type)
- Add/remove problems from the contest
- Reorder problems
- View and manage registrations (approve/reject)
- Create/edit/delete announcements
- View unpublished announcements
- View all contest submissions

**Notes:**
- Only contest owners and admins can add/remove managers
- Cannot add the contest owner as a manager (they already have full access)
- Cannot add a user who is already a manager

#### Contest Tickets (Clarification System)
Contest tickets allow contestants to ask questions about problems during a contest, similar to Codeforces and other competitive programming platforms:

- `POST /contests/{contest_id}/tickets` - Create a ticket/clarification
- `GET /contests/{contest_id}/tickets` - List tickets for a contest (paginated)
- `GET /contests/tickets/my` - List my tickets across all contests
- `GET /contests/tickets/{ticket_id}` - Get a specific ticket with responses
- `PUT /contests/tickets/{ticket_id}` - Update a ticket
- `PUT /contests/tickets/{ticket_id}/status` - Update ticket status
- `DELETE /contests/tickets/{ticket_id}` - Delete a ticket
- `POST /contests/tickets/{ticket_id}/responses` - Create a response (managers only)
- `PUT /contests/ticket-responses/{response_id}` - Update a response
- `DELETE /contests/ticket-responses/{response_id}` - Delete a response

**Ticket Fields:**
- **title**: Ticket title (required, 1-200 characters)
- **content**: The question/clarification (required)
- **problem_id**: Problem ID this ticket is about (optional)
- **is_public**: Whether this ticket is visible to all contestants (default: false)

**Ticket Status:**
- `open`: Ticket is awaiting response
- `answered`: Ticket has been answered by staff
- `closed`: Ticket is closed

**Visibility Rules:**
- Regular users see their own tickets and public tickets
- Managers (admin/owner/managers) see all tickets
- When a manager responds to a ticket, its status is automatically changed to "answered"

**Authorization:**
- Any registered user can create tickets
- Ticket authors can update their own tickets and close them
- Only managers can respond to tickets and change ticket status
- Ticket authors and managers can delete tickets

### Contest Discussions
Discussions attached to specific contests (LeetCode-style):

- `POST /contests/{contest_id}/discussions` - Create a discussion thread for a contest
- `GET /contests/{contest_id}/discussions` - List discussions for a contest (paginated)
- `GET /contests/discussions/{discussion_id}` - Get a discussion with comment tree
- `PUT /contests/discussions/{discussion_id}` - Update a discussion (author/admin)
- `DELETE /contests/discussions/{discussion_id}` - Delete a discussion (author/admin)
- `POST /contests/discussions/{discussion_id}/comments` - Add a comment or reply
- `GET /contests/discussions/{discussion_id}/comments` - Get discussion comments (tree)
- `GET /contests/discussion-comments/{comment_id}` - Get a discussion comment
- `PUT /contests/discussion-comments/{comment_id}` - Update a discussion comment
- `DELETE /contests/discussion-comments/{comment_id}` - Delete a discussion comment

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

### Create a Contest
```bash
curl -X POST "http://localhost:8000/contests" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "title": "Weekly Contest 1",
    "description": "A weekly programming contest",
    "start_date": "2024-02-01T10:00:00Z",
    "end_date": "2024-02-01T12:00:00Z",
    "contest_type": "public",
    "problem_ids": [1, 2, 3, 4, 5]
  }'
```

### Create a Private Contest
```bash
curl -X POST "http://localhost:8000/contests" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "title": "Private Contest 1",
    "description": "A private contest requiring registration",
    "start_date": "2024-02-01T10:00:00Z",
    "end_date": "2024-02-01T12:00:00Z",
    "contest_type": "private",
    "problem_ids": [1, 2, 3, 4, 5]
  }'
```

### Register for a Contest
```bash
curl -X POST "http://localhost:8000/contests/1/register" \
  -H "Authorization: Bearer <token>"
```

### Get My Registration Status
```bash
curl -X GET "http://localhost:8000/contests/1/registration" \
  -H "Authorization: Bearer <token>"
```

### Approve a Registration (admin/owner)
```bash
curl -X PUT "http://localhost:8000/contests/1/registrations/1" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "status": "approved"
  }'
```

### Get Registration Summary
```bash
curl -X GET "http://localhost:8000/contests/1/registrations/summary" \
  -H "Authorization: Bearer <token>"
```

### List My Registrations
```bash
curl -X GET "http://localhost:8000/contests/my/registrations" \
  -H "Authorization: Bearer <token>"
```

### Get Contest Details
```bash
curl -X GET "http://localhost:8000/contests/1" \
  -H "Authorization: Bearer <token>"
```

### Add Problems to a Contest
```bash
curl -X POST "http://localhost:8000/contests/1/problems" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "problem_ids": [6, 7, 8]
  }'
```

### Reorder Problems in a Contest
```bash
curl -X PUT "http://localhost:8000/contests/1/problems/order" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "problems": [
      {"problem_id": 1, "order": 2},
      {"problem_id": 2, "order": 0},
      {"problem_id": 3, "order": 1}
    ]
  }'
```

### Create a Contest Discussion
```bash
curl -X POST "http://localhost:8000/contests/1/discussions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "title": "How was the contest?",
    "content": "What did you think about today'\''s contest?"
  }'
```

### Add a Comment to a Contest Discussion
```bash
curl -X POST "http://localhost:8000/contests/discussions/1/comments" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "content": "Great contest! I enjoyed problem 2."
  }'
```

### Get Contest Discussion with Comments
```bash
curl -X GET "http://localhost:8000/contests/discussions/1" \
  -H "Authorization: Bearer <token>"
```

### Create a Contest Announcement (admin/owner)
```bash
curl -X POST "http://localhost:8000/contests/1/announcements" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "title": "Contest Delayed by 10 Minutes",
    "content": "Due to technical difficulties, the contest will start 10 minutes later than scheduled. We apologize for the inconvenience.",
    "is_published": true
  }'
```

### List Contest Announcements
```bash
curl -X GET "http://localhost:8000/contests/1/announcements?page=1&page_size=10" \
  -H "Authorization: Bearer <token>"
```

### Get a Specific Announcement
```bash
curl -X GET "http://localhost:8000/contests/1/announcements/1" \
  -H "Authorization: Bearer <token>"
```

### Update an Announcement (admin/owner)
```bash
curl -X PUT "http://localhost:8000/contests/1/announcements/1" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "title": "Contest Delayed by 15 Minutes",
    "content": "Due to technical difficulties, the contest will start 15 minutes later than scheduled. We apologize for the inconvenience."
  }'
```

### Delete an Announcement (admin/owner)
```bash
curl -X DELETE "http://localhost:8000/contests/1/announcements/1" \
  -H "Authorization: Bearer <token>"
```

### Create a Contest Ticket (Clarification)
```bash
curl -X POST "http://localhost:8000/contests/1/tickets" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "title": "Clarification on input constraints",
    "content": "The problem states that n can be up to 10^5, but the sample input has n=10^6. Which one is correct?",
    "problem_id": 1,
    "is_public": false
  }'
```

### List Contest Tickets
```bash
curl -X GET "http://localhost:8000/contests/1/tickets?page=1&page_size=10" \
  -H "Authorization: Bearer <token>"
```

### Get a Specific Ticket
```bash
curl -X GET "http://localhost:8000/contests/tickets/1" \
  -H "Authorization: Bearer <token>"
```

### Respond to a Ticket (managers only)
```bash
curl -X POST "http://localhost:8000/contests/tickets/1/responses" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "content": "Thank you for your question. The constraint should be 1 <= n <= 10^6. We have updated the problem statement accordingly."
  }'
```

### Update Ticket Status
```bash
curl -X PUT "http://localhost:8000/contests/tickets/1/status" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "status": "closed"
  }'
```

### Add a Manager to a Contest
```bash
curl -X POST "http://localhost:8000/contests/1/managers/2" \
  -H "Authorization: Bearer <token>"
```

### List Contest Managers
```bash
curl -X GET "http://localhost:8000/contests/1/managers" \
  -H "Authorization: Bearer <token>"
```
