from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from app.models.user import UserRole
from app.models.problem import SubmissionStatus

class UserBase(BaseModel):
    username: str = Field(..., description="The unique username of the user", example="john_doe")
    email: EmailStr = Field(..., description="The email address of the user", example="john@example.com")
    role: UserRole = Field(default=UserRole.USER, description="The role of the user (admin, creator, user)", example="user")
    is_active: bool = Field(default=True, description="Whether the user account is active")

class UserRegister(BaseModel):
    username: str = Field(..., description="The unique username of the user", example="john_doe")
    email: EmailStr = Field(..., description="The email address of the user", example="john@example.com")
    password: str = Field(..., description="The password for the user, must be at least 8 characters", min_length=8, example="strong_password123")

class UserCreate(UserBase):
    password: str = Field(..., description="The password for the user, must be at least 8 characters", min_length=8, example="strong_password123")

class UserActiveUpdate(BaseModel):
    is_active: bool = Field(..., description="Whether the user is active")

class UserOut(UserBase):
    id: int = Field(..., description="The unique internal ID of the user", example=1)
    created_by: Optional[str] = Field(None, description="The username that created this user")
    updated_by: Optional[str] = Field(None, description="The username that last updated this user")
    update_time: Optional[datetime] = Field(None, description="The last time this user record was updated")

    class Config:
        orm_mode = True

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

class ProblemBase(BaseModel):
    title: str = Field(..., description="The title of the problem", example="Sum of Two Numbers")
    description: str = Field(..., description="The detailed problem description", example="Given two integers, return their sum.")
    constraints: str = Field(..., description="Constraints for the problem", example="1 <= a, b <= 10^9")
    testcases: List[Testcase] = Field(..., description="List of testcases with input/output pairs")
    tags: List[str] = Field(default=[], description="List of tags applied to this problem")
    is_published: bool = Field(default=False, description="Whether the problem is published and visible to users")
    is_public: bool = Field(default=True, description="Whether the problem is public or private")

class ProblemCreate(ProblemBase):
    pass

class ProblemUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Updated title of the problem", example="Sum of Two Numbers - Updated")
    description: Optional[str] = Field(None, description="Updated problem description")
    constraints: Optional[str] = Field(None, description="Updated constraints")
    testcases: Optional[List[Testcase]] = Field(None, description="Updated list of testcases")
    is_published: Optional[bool] = Field(None, description="Updated published status")
    is_public: Optional[bool] = Field(None, description="Updated public/private status")

class ProblemOut(ProblemBase):
    id: int = Field(..., description="The unique problem identifier", example=1)
    owner_id: int = Field(..., description="The user ID of the problem owner")
    tags: List[str] = Field(default=[], description="Tags applied to the problem")
    created_by: Optional[str] = Field(None, description="The username that created the problem")
    updated_by: Optional[str] = Field(None, description="The username that last updated the problem")
    update_time: Optional[datetime] = Field(None, description="The last time the problem was updated")
    created_at: datetime = Field(..., description="The creation timestamp of the problem")
    allowed_user_ids: List[int] = Field(default=[], description="List of user IDs allowed to access/edit if private")

    class Config:
        orm_mode = True

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

class TagCreate(BaseModel):
    name: str = Field(..., description="Tag name", example="dp")

class TagOut(BaseModel):
    id: int = Field(..., description="Tag ID", example=1)
    name: str = Field(..., description="Tag name", example="dp")
    created_by: Optional[str] = Field(None, description="The username that created the tag")
    updated_by: Optional[str] = Field(None, description="The username that last updated the tag")
    update_time: Optional[datetime] = Field(None, description="The last time the tag was updated")

    class Config:
        orm_mode = True

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

    class Config:
        orm_mode = True

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

    class Config:
        orm_mode = True
