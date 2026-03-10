from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Table
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base
import enum

class SubmissionStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    WRONG_ANSWER = "WRONG_ANSWER"
    TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
    MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED"
    SYNTAX_ERROR = "SYNTAX_ERROR"

problem_allowed_users = Table(
    "problem_allowed_users",
    Base.metadata,
    Column("problem_id", Integer, ForeignKey("problems.id"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
)

problem_tags = Table(
    "problem_tags",
    Base.metadata,
    Column("problem_id", Integer, ForeignKey("problems.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)

class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)
    update_time = Column(DateTime(timezone=True), server_default=func.now())

    problems = relationship("Problem", secondary=problem_tags, back_populates="_tags")

class Problem(Base):
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    constraints = Column(Text, nullable=False)
    difficulty = Column(Integer, nullable=False)
    is_published = Column(Boolean, default=False, nullable=False)
    is_public = Column(Boolean, default=True, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)
    update_time = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", foreign_keys=[owner_id])
    allowed_users = relationship("User", secondary=problem_allowed_users)
    _tags = relationship("Tag", secondary=problem_tags, back_populates="problems")
    testcases = relationship("Testcase", back_populates="problem", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="problem", cascade="all, delete-orphan")
    editorial = relationship("Editorial", back_populates="problem", uselist=False, cascade="all, delete-orphan")

    # Computed properties for Pydantic v2 compatibility
    @property
    def tags(self) -> list[str]:
        return [t.name for t in self._tags]

    @tags.setter
    def tags(self, value):
        # This setter is needed for the relationship to work
        # but we ignore string lists - tags should be set via _tags relationship
        if hasattr(value, '__iter__') and all(isinstance(v, str) for v in value):
            return  # Ignore string lists
        self._tags = value

    @property
    def allowed_user_ids(self) -> list[int]:
        return [u.id for u in self.allowed_users]

    @allowed_user_ids.setter
    def allowed_user_ids(self, value):
        pass  # Ignore - this is a computed property

class Testcase(Base):
    __tablename__ = "testcases"

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    input = Column(Text, nullable=False)
    output = Column(Text, nullable=False)

    problem = relationship("Problem", back_populates="testcases")

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    user_id = Column(Integer, nullable=False)
    username = Column(String, nullable=False)
    programming_language = Column(String, nullable=False)
    code = Column(Text, nullable=False)
    status = Column(String, default=SubmissionStatus.PENDING.value, nullable=False)
    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)
    update_time = Column(DateTime(timezone=True), server_default=func.now())
    submission_time = Column(DateTime(timezone=True), server_default=func.now())

    problem = relationship("Problem", back_populates="submissions")

class Editorial(Base):
    __tablename__ = "editorials"

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    code_solution = Column(Text, nullable=False)
    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)
    update_time = Column(DateTime(timezone=True), server_default=func.now())

    problem = relationship("Problem", back_populates="editorial")
