from sqlalchemy.orm import Session
from app.models.problem import Problem, Testcase, Submission, Tag, Editorial
from app.models.user import User
from app.schemas import ProblemCreate, ProblemUpdate, SubmissionCreate, SubmissionUpdate, EditorialCreate, EditorialUpdate

class ProblemRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_problem(self, problem_create: ProblemCreate, owner_id: int, created_by: str) -> Problem:
        problem = Problem(
            title=problem_create.title,
            description=problem_create.description,
            constraints=problem_create.constraints,
            is_published=problem_create.is_published,
            is_public=problem_create.is_public,
            owner_id=owner_id,
            created_by=created_by,
            updated_by=created_by
        )
        self.db.add(problem)
        self.db.flush()

        for testcase in problem_create.testcases:
            self.db.add(Testcase(problem_id=problem.id, input=testcase.input, output=testcase.output))

        if problem_create.tags:
            tags = self.get_tags_by_names(problem_create.tags)
            existing_names = {tag.name for tag in tags}
            missing = [name for name in problem_create.tags if name not in existing_names]
            if missing:
                raise ValueError(f"Tags not found: {', '.join(missing)}")
            problem.tags = tags

        self.db.commit()
        self.db.refresh(problem)
        return problem

    def get_problem_by_id(self, problem_id: int):
        return self.db.query(Problem).filter(Problem.id == problem_id).first()

    def get_problem_by_title(self, title: str):
        return self.db.query(Problem).filter(Problem.title == title).first()

    def list_problems(self):
        return self.db.query(Problem).all()

    def list_problems_by_tag(self, tag_name: str):
        return (
            self.db.query(Problem)
            .join(Problem.tags)
            .filter(Tag.name == tag_name)
            .all()
        )

    def get_tag_by_name(self, name: str):
        return self.db.query(Tag).filter(Tag.name == name).first()

    def get_tags_by_names(self, names: list[str]):
        return self.db.query(Tag).filter(Tag.name.in_(names)).all()

    def list_tags(self):
        return self.db.query(Tag).all()

    def create_tag(self, name: str, created_by: str):
        tag = Tag(name=name, created_by=created_by, updated_by=created_by)
        self.db.add(tag)
        self.db.commit()
        self.db.refresh(tag)
        return tag

    def add_tags_to_problem(self, problem: Problem, tags: list[Tag], updated_by: str):
        problem.tags = tags
        problem.updated_by = updated_by
        self.db.commit()
        self.db.refresh(problem)
        return problem

    def update_problem(self, problem: Problem, problem_update: ProblemUpdate, updated_by: str):
        if problem_update.title is not None:
            problem.title = problem_update.title
        if problem_update.description is not None:
            problem.description = problem_update.description
        if problem_update.constraints is not None:
            problem.constraints = problem_update.constraints
        if problem_update.is_published is not None:
            problem.is_published = problem_update.is_published
        if problem_update.is_public is not None:
            problem.is_public = problem_update.is_public
        if problem_update.testcases is not None:
            problem.testcases.clear()
            for testcase in problem_update.testcases:
                problem.testcases.append(Testcase(input=testcase.input, output=testcase.output))
        if problem_update.tags is not None:
            tags = self.get_tags_by_names(problem_update.tags)
            existing_names = {tag.name for tag in tags}
            missing = [name for name in problem_update.tags if name not in existing_names]
            if missing:
                raise ValueError(f"Tags not found: {', '.join(missing)}")
            problem.tags = tags
        problem.updated_by = updated_by
        self.db.commit()
        self.db.refresh(problem)
        return problem

    def add_allowed_user(self, problem: Problem, user: User):
        if user not in problem.allowed_users:
            problem.allowed_users.append(user)
            self.db.commit()
            self.db.refresh(problem)
        return problem

    def remove_allowed_user(self, problem: Problem, user: User):
        if user in problem.allowed_users:
            problem.allowed_users.remove(user)
            self.db.commit()
            self.db.refresh(problem)
        return problem

    def delete_problem(self, problem: Problem):
        self.db.delete(problem)
        self.db.commit()

    def create_submission(self, problem_id: int, submission_create: SubmissionCreate, user_id: int, username: str):
        submission = Submission(
            problem_id=problem_id,
            user_id=user_id,
            username=username,
            programming_language=submission_create.programming_language,
            code=submission_create.code,
            status="PENDING",
            created_by=username,
            updated_by=username
        )
        self.db.add(submission)
        self.db.commit()
        self.db.refresh(submission)
        return submission

    def list_submissions_for_problem(self, problem_id: int):
        return self.db.query(Submission).filter(Submission.problem_id == problem_id).all()

    def list_all_submissions(self):
        return self.db.query(Submission).all()

    def get_submission_by_id(self, submission_id: int):
        return self.db.query(Submission).filter(Submission.id == submission_id).first()

    def update_submission(self, submission: Submission, submission_update: SubmissionUpdate, updated_by: str):
        if submission_update.programming_language is not None:
            submission.programming_language = submission_update.programming_language
        if submission_update.code is not None:
            submission.code = submission_update.code
        submission.updated_by = updated_by
        self.db.commit()
        self.db.refresh(submission)
        return submission

    def update_submission_status(self, submission: Submission, status: str, updated_by: str):
        submission.status = status
        submission.updated_by = updated_by
        self.db.commit()
        self.db.refresh(submission)
        return submission

    def delete_submission(self, submission: Submission):
        self.db.delete(submission)
        self.db.commit()

    def get_editorial_by_problem_id(self, problem_id: int):
        return self.db.query(Editorial).filter(Editorial.problem_id == problem_id).first()

    def create_editorial(self, problem_id: int, editorial_create: EditorialCreate, created_by: str):
        editorial = Editorial(
            problem_id=problem_id,
            description=editorial_create.description,
            code_solution=editorial_create.code_solution,
            created_by=created_by,
            updated_by=created_by
        )
        self.db.add(editorial)
        self.db.commit()
        self.db.refresh(editorial)
        return editorial

    def update_editorial(self, editorial: Editorial, editorial_update: EditorialUpdate, updated_by: str):
        if editorial_update.description is not None:
            editorial.description = editorial_update.description
        if editorial_update.code_solution is not None:
            editorial.code_solution = editorial_update.code_solution
        editorial.updated_by = updated_by
        self.db.commit()
        self.db.refresh(editorial)
        return editorial

    def delete_editorial(self, editorial: Editorial):
        self.db.delete(editorial)
        self.db.commit()
