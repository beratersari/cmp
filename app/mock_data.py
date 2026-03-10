from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.services.user_service import UserService
from app.services.problem_service import ProblemService
from app.schemas import ProblemCreate, Testcase, SubmissionCreate, UserCreate, UserRegister, EditorialCreate
from app.models.user import UserRole
from app.models.problem import SubmissionStatus
from app.repositories.problem_repository import ProblemRepository


def seed_mock_data(db: Session):
    """
    Seed mock data: at least 20 users, 100 problems, 50 submissions.
    """
    user_service = UserService(db)
    problem_service = ProblemService(db)
    problem_repo = ProblemRepository(db)

    # Ensure admin
    admin = user_service.ensure_dummy_admin("admin", "admin@example.com", "admin12345")

    # Create creators and users
    existing_users_result = user_service.list_users(page=1, page_size=100)
    existing_users = existing_users_result["items"]
    if len(existing_users) < 20:
        for i in range(1, 11):
            creator_username = f"creator{i}"
            user_service.create_user_by_admin(
                UserCreate(
                    username=creator_username,
                    email=f"{creator_username}@example.com",
                    role=UserRole.CREATOR,
                    password="creatorpass"
                )
            )
        for i in range(1, 11):
            user_username = f"user{i}"
            user_service.register_user(
                UserRegister(
                    username=user_username,
                    email=f"{user_username}@example.com",
                    password="userpass"
                )
            )

    # Refresh users
    users_result = user_service.list_users(page=1, page_size=100)
    users = users_result["items"]
    creators = [u for u in users if u.role == UserRole.CREATOR]
    if not creators:
        creators = [admin]

    # Ensure tags exist
    tag_names = ["dp", "math", "graphs", "greedy", "strings"]
    for tag in tag_names:
        try:
            problem_service.create_tag(tag, admin)
        except Exception:
            pass

    # Create problems
    problems_result = problem_service.list_problems(admin, page=1, page_size=100)
    if problems_result["total"] < 100:
        for i in range(1, 101):
            owner = creators[i % len(creators)]
            problem_create = ProblemCreate(
                title=f"Problem {i}",
                description=f"Description for problem {i}",
                constraints="1 <= n <= 10^9",
                difficulty=(i % 10) + 1,  # Difficulty between 1-10
                testcases=[Testcase(input="1", output="1"), Testcase(input="2", output="2")],
                tags=[tag_names[i % len(tag_names)]],
                is_published=True,
                is_public=True
            )
            problem_service.create_problem(problem_create, owner_id=owner.id, created_by=owner.username)

    # Create submissions
    problems_result = problem_service.list_problems(admin, page=1, page_size=100)
    problems = problems_result["items"]
    if problems:
        existing_submissions = problem_service.problem_submission_stats(admin)
        if sum(stat.submission_count for stat in existing_submissions) < 50:
            for i in range(50):
                problem = problems[i % len(problems)]
                user = users[i % len(users)]
                submission_create = SubmissionCreate(
                    programming_language="python",
                    code=f"print('submission {i}')"
                )
                problem_service.create_submission(
                    problem.id,
                    submission_create,
                    user_id=user.id,
                    username=user.username,
                    current_user=user
                )

    # Create accepted submissions for streak testing
    # Add accepted submissions for the first few users on consecutive days
    if problems and len(users) > 0:
        # Get existing submissions to check if we've already added accepted ones
        all_submissions = problem_repo.list_all_submissions()
        accepted_count = sum(1 for s in all_submissions if s.status == SubmissionStatus.ACCEPTED.value)
        
        if accepted_count < 20:
            # Create accepted submissions for streak testing
            today = datetime.now()
            test_users = users[:3]  # First 3 users
            
            for day_offset in range(10):  # 10 consecutive days
                submission_date = today - timedelta(days=day_offset)
                for user in test_users:
                    # Each user solves 2-3 problems per day
                    for prob_idx in range(2):
                        problem = problems[(day_offset + prob_idx) % len(problems)]
                        submission = problem_repo.create_submission(
                            problem_id=problem.id,
                            submission_create=SubmissionCreate(
                                programming_language="python",
                                code=f"print('accepted solution day {day_offset}')"
                            ),
                            user_id=user.id,
                            username=user.username
                        )
                        # Update status to ACCEPTED
                        problem_repo.update_submission_status(
                            submission, 
                            SubmissionStatus.ACCEPTED.value, 
                            updated_by="system"
                        )

    # Create editorials
    if problems:
        for i in range(min(10, len(problems))):
            problem = problems[i]
            try:
                problem_service.get_editorial(problem.id, admin)
            except Exception:
                editorial_create = EditorialCreate(
                    description=f"Editorial for problem {problem.title}. Use binary search.",
                    code_solution="def solve(): pass"
                )
                problem_service.create_editorial(problem.id, editorial_create, admin)
