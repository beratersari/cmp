from sqlalchemy.orm import Session
from app.services.user_service import UserService
from app.services.problem_service import ProblemService
from app.schemas import ProblemCreate, Testcase, SubmissionCreate, UserCreate, UserRegister, EditorialCreate
from app.models.user import UserRole


def seed_mock_data(db: Session):
    """
    Seed mock data: at least 20 users, 100 problems, 50 submissions.
    """
    user_service = UserService(db)
    problem_service = ProblemService(db)

    # Ensure admin
    admin = user_service.ensure_dummy_admin("admin", "admin@example.com", "admin12345")

    # Create creators and users
    existing_users = user_service.list_users()
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
    users = user_service.list_users()
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
    problems = problem_service.list_problems(admin)
    if len(problems) < 100:
        for i in range(1, 101):
            owner = creators[i % len(creators)]
            problem_create = ProblemCreate(
                title=f"Problem {i}",
                description=f"Description for problem {i}",
                constraints="1 <= n <= 10^9",
                testcases=[Testcase(input="1", output="1"), Testcase(input="2", output="2")],
                tags=[tag_names[i % len(tag_names)]],
                is_published=True,
                is_public=True
            )
            problem_service.create_problem(problem_create, owner_id=owner.id, created_by=owner.username)

    # Create submissions
    problems = problem_service.list_problems(admin)
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
