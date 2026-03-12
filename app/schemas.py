from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional, List, Generic, TypeVar
from datetime import datetime
from app.models.user import UserRole
from app.models.problem import SubmissionStatus, VoteType, VoteTargetType
from app.models.contest import ContestType, ContestRegistrationStatus

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T] = Field(..., description="List of items for the current page")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")

    model_config = ConfigDict(from_attributes=True)

class UserBase(BaseModel):
    username: str = Field(..., description="The unique username of the user", example="john_doe")
    email: EmailStr = Field(..., description="The email address of the user", example="john@example.com")
    role: UserRole = Field(default=UserRole.USER, description="The role of the user (admin, creator, user)", example="user")
    is_active: bool = Field(default=True, description="Whether the user account is active")

class EducationBase(BaseModel):
    institution: str = Field(..., description="Name of the educational institution", example="MIT")
    degree: str = Field(..., description="Degree earned or pursuing", example="Bachelor of Science")
    field_of_study: Optional[str] = Field(None, description="Field of study or major", example="Computer Science")
    start_year: int = Field(..., description="Year started", ge=1900, le=2100, example=2020)
    end_year: Optional[int] = Field(None, description="Year ended (null if currently studying)", ge=1900, le=2100, example=2024)
    description: Optional[str] = Field(None, description="Additional details about the education")

class EducationCreate(EducationBase):
    pass

class EducationUpdate(BaseModel):
    institution: Optional[str] = Field(None, description="Name of the educational institution")
    degree: Optional[str] = Field(None, description="Degree earned or pursuing")
    field_of_study: Optional[str] = Field(None, description="Field of study or major")
    start_year: Optional[int] = Field(None, description="Year started", ge=1900, le=2100)
    end_year: Optional[int] = Field(None, description="Year ended (null if currently studying)", ge=1900, le=2100)
    description: Optional[str] = Field(None, description="Additional details about the education")

class EducationOut(EducationBase):
    id: int = Field(..., description="The unique education entry ID", example=1)
    user_id: int = Field(..., description="The user ID this education belongs to")
    created_at: datetime = Field(..., description="When the education entry was created")
    updated_at: datetime = Field(..., description="When the education entry was last updated")

    model_config = ConfigDict(from_attributes=True)

class UserRegister(BaseModel):
    username: str = Field(..., description="The unique username of the user", example="john_doe")
    email: EmailStr = Field(..., description="The email address of the user", example="john@example.com")
    password: str = Field(..., description="The password for the user, must be at least 8 characters", min_length=8, example="strong_password123")
    educations: Optional[List[EducationCreate]] = Field(default=None, description="Optional list of education entries")

class UserCreate(UserBase):
    password: str = Field(..., description="The password for the user, must be at least 8 characters", min_length=8, example="strong_password123")
    educations: Optional[List[EducationCreate]] = Field(default=None, description="Optional list of education entries")

class UserActiveUpdate(BaseModel):
    is_active: bool = Field(..., description="Whether the user is active")

class UserOut(UserBase):
    id: int = Field(..., description="The unique internal ID of the user", example=1)
    created_by: Optional[str] = Field(None, description="The username that created this user")
    updated_by: Optional[str] = Field(None, description="The username that last updated this user")
    update_time: Optional[datetime] = Field(None, description="The last time this user record was updated")
    educations: List[EducationOut] = Field(default=[], description="List of user's education entries")
    followers_count: int = Field(0, description="Number of followers")
    following_count: int = Field(0, description="Number of users this user follows")

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str = Field(..., description="The generated JWT access token", example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    token_type: str = Field(..., description="The type of the token", example="bearer")

class TokenData(BaseModel):
    username: Optional[str] = Field(None, description="The username extracted from the token")
    role: Optional[str] = Field(None, description="The role extracted from the token")

class LoginRequest(BaseModel):
    username: str = Field(..., description="The username of the user attempting to log in")
    password: str = Field(..., description="The password of the user attempting to log in")

class Testcase(BaseModel):
    input: str = Field(..., description="The raw input string for the testcase", example="1 2")
    output: str = Field(..., description="The expected output string for the testcase", example="3")

class TestcaseCreate(BaseModel):
    input: str = Field(..., description="The raw input string for the testcase", example="1 2")
    output: str = Field(..., description="The expected output string for the testcase", example="3")

class TestcaseOut(BaseModel):
    id: int = Field(..., description="The unique testcase identifier", example=1)
    input: str = Field(..., description="The raw input string for the testcase", example="1 2")
    output: str = Field(..., description="The expected output string for the testcase", example="3")

    model_config = ConfigDict(from_attributes=True)

class ProblemBase(BaseModel):
    title: str = Field(..., description="The title of the problem", example="Sum of Two Numbers")
    description: str = Field(..., description="The detailed problem description", example="Given two integers, return their sum.")
    constraints: str = Field(..., description="Constraints for the problem", example="1 <= a, b <= 10^9")
    difficulty: int = Field(..., description="Difficulty level of the problem (1-10)", ge=1, le=10, example=5)
    testcases: List[Testcase] = Field(..., description="List of testcases with input/output pairs")
    tags: List[str] = Field(default=[], description="List of tags applied to this problem")
    is_published: bool = Field(default=False, description="Whether the problem is published and visible to users")
    is_public: bool = Field(default=True, description="Whether the problem is public or private")

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: int) -> int:
        if v < 1 or v > 10:
            raise ValueError("Difficulty must be between 1 and 10")
        return v

class ProblemCreate(ProblemBase):
    pass

class ProblemUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Updated title of the problem", example="Sum of Two Numbers - Updated")
    description: Optional[str] = Field(None, description="Updated problem description")
    constraints: Optional[str] = Field(None, description="Updated constraints")
    difficulty: Optional[int] = Field(None, description="Updated difficulty level (1-10)", ge=1, le=10)
    testcases: Optional[List[Testcase]] = Field(None, description="Updated list of testcases")
    is_published: Optional[bool] = Field(None, description="Updated published status")
    is_public: Optional[bool] = Field(None, description="Updated public/private status")

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 10):
            raise ValueError("Difficulty must be between 1 and 10")
        return v

class ProblemOut(ProblemBase):
    id: int = Field(..., description="The unique problem identifier", example=1)
    owner_id: int = Field(..., description="The user ID of the problem owner")
    tags: List[str] = Field(default=[], description="Tags applied to the problem")
    created_by: Optional[str] = Field(None, description="The username that created the problem")
    updated_by: Optional[str] = Field(None, description="The username that last updated the problem")
    update_time: Optional[datetime] = Field(None, description="The last time the problem was updated")
    created_at: datetime = Field(..., description="The creation timestamp of the problem")
    allowed_user_ids: List[int] = Field(default=[], description="List of user IDs allowed to access/edit if private")

    model_config = ConfigDict(from_attributes=True)

class SubmissionBase(BaseModel):
    programming_language: str = Field(..., description="The programming language used in the submission", example="python")
    code: str = Field(..., description="The raw code submitted by the user")

class SubmissionCreate(SubmissionBase):
    pass

class SubmissionStatusUpdate(BaseModel):
    status: SubmissionStatus = Field(..., description="New status for the submission")

class SubmissionUpdate(BaseModel):
    programming_language: Optional[str] = Field(None, description="Updated programming language", example="cpp")
    code: Optional[str] = Field(None, description="Updated raw code submitted by the user")

class UserListOut(UserOut):
    pass

class UserSummaryOut(BaseModel):
    id: int = Field(..., description="The unique internal ID of the user", example=1)
    username: str = Field(..., description="The unique username of the user", example="john_doe")

    model_config = ConfigDict(from_attributes=True)

class UserFollowStatsOut(BaseModel):
    user_id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    followers_count: int = Field(..., description="Number of followers")
    following_count: int = Field(..., description="Number of users this user follows")
    following: List[UserSummaryOut] = Field(default=[], description="Users this user follows")

class UserFollowersOut(BaseModel):
    user_id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    followers: List[UserSummaryOut] = Field(default=[], description="Followers list")

class TagCreate(BaseModel):
    name: str = Field(..., description="Tag name", example="dp")

class TagOut(BaseModel):
    id: int = Field(..., description="Tag ID", example=1)
    name: str = Field(..., description="Tag name", example="dp")
    created_by: Optional[str] = Field(None, description="The username that created the tag")
    updated_by: Optional[str] = Field(None, description="The username that last updated the tag")
    update_time: Optional[datetime] = Field(None, description="The last time the tag was updated")

    model_config = ConfigDict(from_attributes=True)

class LeaderboardEntryOut(BaseModel):
    username: str = Field(..., description="Username")
    accepted_problem_count: int = Field(..., description="Number of unique problems solved with ACCEPTED submissions")

class CreatorLeaderboardEntryOut(BaseModel):
    username: str = Field(..., description="Creator username")
    created_problem_count: int = Field(..., description="Number of problems created")

class ProblemsByOwnerOut(BaseModel):
    owner_username: str = Field(..., description="The username of the problem owner")
    problems: List[ProblemOut] = Field(..., description="Problems created by this owner")

class CreatorProblemStatsOut(BaseModel):
    username: str = Field(..., description="The creator's username")
    problem_count: int = Field(..., description="Number of problems created by this user")

class ProblemSubmissionStatsOut(BaseModel):
    problem_id: int = Field(..., description="Problem ID")
    title: str = Field(..., description="Problem title")
    submission_count: int = Field(..., description="Number of submissions for this problem")

class SubmissionOut(SubmissionBase):
    id: int = Field(..., description="The unique submission identifier", example=1001)
    problem_id: int = Field(..., description="The associated problem ID", example=1)
    user_id: int = Field(..., description="The ID of the user submitting the code", example=42)
    username: str = Field(..., description="The username of the submitter", example="john_doe")
    status: SubmissionStatus = Field(..., description="Current submission status")
    created_by: Optional[str] = Field(None, description="The username that created the submission")
    updated_by: Optional[str] = Field(None, description="The username that last updated the submission")
    update_time: Optional[datetime] = Field(None, description="The last time the submission was updated")
    submission_time: datetime = Field(..., description="The timestamp when the submission was made")

    model_config = ConfigDict(from_attributes=True)

class EditorialBase(BaseModel):
    description: str = Field(..., description="The detailed editorial explanation")
    code_solution: str = Field(..., description="The reference code solution for the problem")

class EditorialCreate(EditorialBase):
    pass

class EditorialUpdate(BaseModel):
    description: Optional[str] = Field(None, description="Updated editorial explanation")
    code_solution: Optional[str] = Field(None, description="Updated reference code solution")

class EditorialOut(EditorialBase):
    id: int = Field(..., description="The unique editorial identifier")
    problem_id: int = Field(..., description="The associated problem ID")
    created_by: Optional[str] = Field(None, description="The username that created the editorial")
    updated_by: Optional[str] = Field(None, description="The username that last updated the editorial")
    update_time: datetime = Field(..., description="The last time the editorial was updated")

    model_config = ConfigDict(from_attributes=True)

class SubmissionHistoryEntry(BaseModel):
    date: str = Field(..., description="Date in YYYY-MM-DD format", example="2024-01-15")
    submission_count: int = Field(..., description="Number of submissions on this date", example=5)

class UserSubmissionHistoryOut(BaseModel):
    user_id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    start_date: str = Field(..., description="Start date of the range", example="2024-01-01")
    end_date: str = Field(..., description="End date of the range", example="2024-01-31")
    daily_submissions: List[SubmissionHistoryEntry] = Field(..., description="Submission count per date")
    total_submissions: int = Field(..., description="Total submissions in the date range")

class StreakInfo(BaseModel):
    current_streak: int = Field(..., description="Current consecutive days with accepted submissions")
    max_streak: int = Field(..., description="Maximum daily streak achieved")
    last_accepted_date: Optional[str] = Field(None, description="Date of last accepted submission")

class UserStreakOut(BaseModel):
    user_id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    streak_info: StreakInfo = Field(..., description="Streak information")


class VoteCreate(BaseModel):
    vote_type: VoteType = Field(..., description="Type of vote: like or dislike", example="like")


class VoteOut(BaseModel):
    id: int = Field(..., description="Vote ID")
    user_id: int = Field(..., description="User ID who cast the vote")
    target_id: int = Field(..., description="ID of the target (problem or editorial)")
    target_type: VoteTargetType = Field(..., description="Type of target: problem or editorial")
    vote_type: VoteType = Field(..., description="Type of vote: like or dislike")
    created_at: datetime = Field(..., description="When the vote was created")
    updated_at: datetime = Field(..., description="When the vote was last updated")

    model_config = ConfigDict(from_attributes=True)


class VoteStats(BaseModel):
    likes: int = Field(..., description="Number of likes")
    dislikes: int = Field(..., description="Number of dislikes")
    total: int = Field(..., description="Total number of votes")
    like_rate: float = Field(..., description="Like rate (likes / total), 0.0 if no votes")


class ProblemVoteStatsOut(BaseModel):
    problem_id: int = Field(..., description="Problem ID")
    title: str = Field(..., description="Problem title")
    votes: VoteStats = Field(..., description="Vote statistics for the problem")


class EditorialVoteStatsOut(BaseModel):
    editorial_id: int = Field(..., description="Editorial ID")
    problem_id: int = Field(..., description="Associated problem ID")
    votes: VoteStats = Field(..., description="Vote statistics for the editorial")


class CreatorVoteStatsOut(BaseModel):
    username: str = Field(..., description="Creator username")
    total_problems: int = Field(..., description="Total number of problems created")
    total_likes: int = Field(..., description="Total likes across all problems")
    total_dislikes: int = Field(..., description="Total dislikes across all problems")
    total_votes: int = Field(..., description="Total votes across all problems")
    overall_like_rate: float = Field(..., description="Overall like rate (total_likes / total_votes)")
    problems: List[ProblemVoteStatsOut] = Field(..., description="Vote stats for each problem")


# Problem Discussion Schemas
class DiscussionCreate(BaseModel):
    title: str = Field(..., description="Discussion title", min_length=1, max_length=200)
    content: str = Field(..., description="Discussion content", min_length=1)


class DiscussionUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Discussion title", min_length=1, max_length=200)
    content: Optional[str] = Field(None, description="Discussion content", min_length=1)


class DiscussionOut(BaseModel):
    id: int
    problem_id: int
    title: str
    content: str
    author_id: int
    author_username: Optional[str]
    is_published: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DiscussionCommentCreate(BaseModel):
    content: str = Field(..., description="Comment content", min_length=1)
    parent_id: Optional[int] = Field(None, description="Parent comment ID for replies")


class DiscussionCommentUpdate(BaseModel):
    content: str = Field(..., description="Comment content", min_length=1)


class DiscussionCommentOut(BaseModel):
    id: int
    discussion_id: int
    content: str
    author_id: int
    author_username: Optional[str]
    parent_id: Optional[int]
    is_published: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DiscussionTreeOut(BaseModel):
    id: int
    content: str
    author_id: int
    author_username: Optional[str]
    discussion_id: int
    parent_id: Optional[int]
    is_published: bool
    is_deleted: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    replies: List["DiscussionTreeOut"] = []


class DiscussionDetailOut(DiscussionOut):
    comments: List[DiscussionTreeOut] = []


# Bookmark Schemas
class BookmarkCreate(BaseModel):
    problem_id: int = Field(..., description="Problem ID to bookmark")


class BookmarkOut(BaseModel):
    id: int
    user_id: int
    problem_id: int
    problem_title: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Contest Schemas
class ContestBase(BaseModel):
    title: str = Field(..., description="The title of the contest", example="Weekly Contest 1")
    description: Optional[str] = Field(None, description="Description of the contest")
    start_date: datetime = Field(..., description="Start date and time of the contest")
    end_date: datetime = Field(..., description="End date and time of the contest")
    contest_type: ContestType = Field(default=ContestType.PUBLIC, description="Type of contest: public, private, or archived")

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: datetime, info) -> datetime:
        start_date = info.data.get("start_date")
        if start_date and v <= start_date:
            raise ValueError("End date must be after start date")
        return v


class ContestCreate(ContestBase):
    problem_ids: List[int] = Field(default=[], description="List of problem IDs to include in the contest")


class ContestUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Updated title of the contest")
    description: Optional[str] = Field(None, description="Updated description")
    start_date: Optional[datetime] = Field(None, description="Updated start date and time")
    end_date: Optional[datetime] = Field(None, description="Updated end date and time")
    contest_type: Optional[ContestType] = Field(None, description="Updated contest type")

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: Optional[datetime], info) -> Optional[datetime]:
        if v is not None:
            start_date = info.data.get("start_date")
            if start_date and v <= start_date:
                raise ValueError("End date must be after start date")
        return v


class ContestProblemOut(BaseModel):
    id: int = Field(..., description="Problem ID")
    title: str = Field(..., description="Problem title")
    difficulty: int = Field(..., description="Problem difficulty")

    model_config = ConfigDict(from_attributes=True)


class ContestOut(BaseModel):
    id: int = Field(..., description="The unique contest identifier")
    title: str = Field(..., description="The title of the contest")
    description: Optional[str] = Field(None, description="Description of the contest")
    start_date: datetime = Field(..., description="Start date and time of the contest")
    end_date: datetime = Field(..., description="End date and time of the contest")
    contest_type: ContestType = Field(..., description="Type of contest: public, private, or archived")
    owner_id: int = Field(..., description="The user ID of the contest owner")
    created_by: Optional[str] = Field(None, description="The username that created the contest")
    updated_by: Optional[str] = Field(None, description="The username that last updated the contest")
    update_time: Optional[datetime] = Field(None, description="The last time the contest was updated")
    created_at: datetime = Field(..., description="The creation timestamp of the contest")
    problem_ids: List[int] = Field(default=[], description="List of problem IDs in the contest")

    model_config = ConfigDict(from_attributes=True)


class ContestDetailOut(ContestOut):
    problems: List[ContestProblemOut] = Field(default=[], description="List of problems in the contest")


class ContestAddProblems(BaseModel):
    problem_ids: List[int] = Field(..., description="List of problem IDs to add to the contest")


class ContestRemoveProblems(BaseModel):
    problem_ids: List[int] = Field(..., description="List of problem IDs to remove from the contest")


class ContestProblemOrder(BaseModel):
    problem_id: int = Field(..., description="Problem ID")
    order: int = Field(..., description="Order position (0-indexed)")


class ContestReorderProblems(BaseModel):
    problems: List[ContestProblemOrder] = Field(..., description="List of problem IDs with their new order positions")


# Contest Discussion Schemas
class ContestDiscussionCreate(BaseModel):
    title: str = Field(..., description="Discussion title", min_length=1, max_length=200)
    content: str = Field(..., description="Discussion content", min_length=1)


class ContestDiscussionUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Discussion title", min_length=1, max_length=200)
    content: Optional[str] = Field(None, description="Discussion content", min_length=1)


class ContestDiscussionOut(BaseModel):
    id: int
    contest_id: int
    title: str
    content: str
    author_id: int
    author_username: Optional[str]
    is_published: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ContestDiscussionCommentCreate(BaseModel):
    content: str = Field(..., description="Comment content", min_length=1)
    parent_id: Optional[int] = Field(None, description="Parent comment ID for replies")


class ContestDiscussionCommentUpdate(BaseModel):
    content: str = Field(..., description="Comment content", min_length=1)


class ContestDiscussionCommentOut(BaseModel):
    id: int
    discussion_id: int
    content: str
    author_id: int
    author_username: Optional[str]
    parent_id: Optional[int]
    is_published: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ContestDiscussionTreeOut(BaseModel):
    id: int
    content: str
    author_id: int
    author_username: Optional[str]
    discussion_id: int
    parent_id: Optional[int]
    is_published: bool
    is_deleted: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    replies: List["ContestDiscussionTreeOut"] = []


class ContestDiscussionDetailOut(ContestDiscussionOut):
    comments: List[ContestDiscussionTreeOut] = []


# Contest Registration Schemas
class ContestRegistrationCreate(BaseModel):
    """Schema for registering to a contest."""
    pass  # No additional fields needed - user_id comes from auth, contest_id from path


class ContestRegistrationUpdate(BaseModel):
    """Schema for updating registration status (admin/owner only)."""
    status: ContestRegistrationStatus = Field(..., description="New registration status: pending, approved, or rejected")


class ContestRegistrationOut(BaseModel):
    """Schema for contest registration output."""
    id: int = Field(..., description="Registration ID")
    contest_id: int = Field(..., description="Contest ID")
    user_id: int = Field(..., description="User ID")
    username: Optional[str] = Field(None, description="Username of registered user")
    status: ContestRegistrationStatus = Field(..., description="Registration status")
    registered_at: datetime = Field(..., description="When the user registered")
    approved_at: Optional[datetime] = Field(None, description="When the registration was approved")
    approved_by: Optional[int] = Field(None, description="User ID who approved the registration")
    approver_username: Optional[str] = Field(None, description="Username of approver")

    model_config = ConfigDict(from_attributes=True)


class ContestRegistrationSummaryOut(BaseModel):
    """Summary of registrations for a contest."""
    contest_id: int = Field(..., description="Contest ID")
    total_registrations: int = Field(..., description="Total number of registrations")
    pending_count: int = Field(..., description="Number of pending registrations")
    approved_count: int = Field(..., description="Number of approved registrations")
    rejected_count: int = Field(..., description="Number of rejected registrations")


class UserRegistrationOut(BaseModel):
    """Schema for user's contest registration."""
    contest_id: int = Field(..., description="Contest ID")
    contest_title: str = Field(..., description="Contest title")
    status: ContestRegistrationStatus = Field(..., description="Registration status")
    registered_at: datetime = Field(..., description="When the user registered")

    model_config = ConfigDict(from_attributes=True)


# Contest Announcement Schemas
class ContestAnnouncementCreate(BaseModel):
    """Schema for creating a contest announcement."""
    title: str = Field(..., description="Announcement title", min_length=1, max_length=200)
    content: str = Field(..., description="Announcement content", min_length=1)
    is_published: bool = Field(default=True, description="Whether the announcement is published")


class ContestAnnouncementUpdate(BaseModel):
    """Schema for updating a contest announcement."""
    title: Optional[str] = Field(None, description="Announcement title", min_length=1, max_length=200)
    content: Optional[str] = Field(None, description="Announcement content", min_length=1)
    is_published: Optional[bool] = Field(None, description="Whether the announcement is published")


class ContestAnnouncementOut(BaseModel):
    """Schema for contest announcement output."""
    id: int = Field(..., description="Announcement ID")
    contest_id: int = Field(..., description="Contest ID")
    title: str = Field(..., description="Announcement title")
    content: str = Field(..., description="Announcement content")
    author_id: int = Field(..., description="Author user ID")
    author_username: Optional[str] = Field(None, description="Author username")
    is_published: bool = Field(..., description="Whether the announcement is published")
    created_at: datetime = Field(..., description="When the announcement was created")
    updated_at: Optional[datetime] = Field(None, description="When the announcement was last updated")

    model_config = ConfigDict(from_attributes=True)
