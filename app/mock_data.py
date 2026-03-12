from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.services.user_service import UserService
from app.services.problem_service import ProblemService
from app.services.forum_service import ForumService
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

    # Create forum posts and comments
    forum_service = ForumService(db)
    seed_forum_data(forum_service, users, admin)

    # Create problem discussions and comments
    from app.services.problem_discussion_service import ProblemDiscussionService
    discussion_service = ProblemDiscussionService(db)
    seed_problem_discussions(discussion_service, problems, users, admin)

    # Create bookmarks
    from app.services.bookmark_service import BookmarkService
    bookmark_service = BookmarkService(db)
    seed_bookmarks(bookmark_service, problems, users)

    # Create contests
    from app.services.contest_service import ContestService
    contest_service = ContestService(db)
    seed_contests(contest_service, problem_service, problems, creators, admin)

    # Create contest discussions
    from app.services.contest_discussion_service import ContestDiscussionService
    contest_discussion_service = ContestDiscussionService(db)
    seed_contest_discussions(contest_discussion_service, contest_service, users, admin)

    # Create contest registrations
    seed_contest_registrations(contest_service, contest_service.contest_repo, users, admin)

    # Create contest announcements
    seed_contest_announcements(contest_service, contest_service.contest_repo, admin)


def seed_forum_data(forum_service: ForumService, users, admin):
    """
    Seed forum data: at least 3 posts and 30+ comments/replies.
    """
    # Check if we already have forum posts
    posts_result = forum_service.list_posts(page=1, page_size=10)
    if posts_result["total"] >= 3:
        return  # Already have enough posts

    # Get some users for creating posts and comments
    regular_users = [u for u in users if u.role == UserRole.USER][:5]
    creators = [u for u in users if u.role == UserRole.CREATOR][:3]
    all_authors = regular_users + creators + [admin]

    if len(all_authors) < 3:
        all_authors = users[:5]  # Use any available users

    # Create 3 forum posts
    posts_data = [
        {
            "title": "Welcome to the Competitive Programming Forum!",
            "content": """Welcome everyone to our new competitive programming forum!

This is a place to discuss algorithms, share solutions, ask questions, and help each other improve.

Feel free to:
- Ask questions about problems
- Share your solutions and approaches
- Discuss algorithmic techniques
- Get help with debugging
- Connect with other competitive programmers

Let's build a helpful community together!""",
            "author": admin
        },
        {
            "title": "Tips for Beginners: Getting Started with CP",
            "content": """Hey everyone! I wanted to share some tips for beginners just starting out with competitive programming:

1. **Start with the basics**: Make sure you're comfortable with your programming language of choice.

2. **Learn fundamental algorithms**: Sorting, searching, recursion, and basic data structures.

3. **Practice consistently**: Solve problems daily, even if it's just one or two.

4. **Read editorials**: After attempting a problem, read the editorial to learn new approaches.

5. **Participate in contests**: Even if you solve just one problem, participating helps you learn.

6. **Don't give up**: CP is challenging, but persistence pays off!

What tips would you add?""",
            "author": regular_users[0] if regular_users else all_authors[0]
        },
        {
            "title": "Dynamic Programming Discussion Thread",
            "content": """Let's discuss Dynamic Programming (DP) techniques!

DP is one of the most important topics in competitive programming. Here are some common patterns:

- **Knapsack problems**
- **Longest Common Subsequence (LCS)**
- **Longest Increasing Subsequence (LIS)**
- **Matrix chain multiplication**
- **Coin change problems**
- **Interval DP**

What are your favorite DP problems? Any tips for recognizing DP patterns?

Looking forward to hearing your insights!""",
            "author": creators[0] if creators else all_authors[1]
        }
    ]

    created_posts = []
    for post_data in posts_data:
        post = forum_service.create_post(
            title=post_data["title"],
            content=post_data["content"],
            author_id=post_data["author"].id
        )
        created_posts.append(post)

    # Create 30+ comments across all posts
    # Comments for Post 1 (Welcome post)
    comments_post1 = [
        ("Thanks for setting this up! Excited to be here.", regular_users[0] if len(regular_users) > 0 else all_authors[0]),
        ("Great initiative! Looking forward to learning from everyone.", regular_users[1] if len(regular_users) > 1 else all_authors[1]),
        ("Hello everyone! I'm new to CP, hope to improve with your help.", regular_users[2] if len(regular_users) > 2 else all_authors[2]),
        ("Welcome! Don't hesitate to ask questions, we're all here to help.", creators[0] if creators else all_authors[0]),
        ("Is there a Discord server as well?", regular_users[0] if len(regular_users) > 0 else all_authors[0]),
        ("Not yet, but we're considering it! Stay tuned.", admin),
    ]

    # Comments for Post 2 (Beginner tips)
    comments_post2 = [
        ("Great tips! I would add: practice problems in increasing difficulty order.", creators[0] if creators else all_authors[1]),
        ("Thanks for sharing! The consistency tip is really important.", regular_users[1] if len(regular_users) > 1 else all_authors[2]),
        ("Can you recommend some good resources for learning algorithms?", regular_users[3] if len(regular_users) > 3 else all_authors[0]),
        ("I recommend CLRS for theory and CP-Algorithms for competitive programming specific topics.", creators[1] if len(creators) > 1 else all_authors[1]),
        ("YouTube channels like WilliamFiset and Abdul Bari are also great!", regular_users[0] if len(regular_users) > 0 else all_authors[2]),
        ("Thanks for the recommendations!", regular_users[3] if len(regular_users) > 3 else all_authors[0]),
        ("No problem! Feel free to ask if you need more specific recommendations.", regular_users[0] if len(regular_users) > 0 else all_authors[0]),
        ("How long did it take you to become good at CP?", regular_users[4] if len(regular_users) > 4 else all_authors[2]),
        ("It varies for everyone, but consistent practice for 6-12 months makes a big difference.", creators[0] if creators else all_authors[1]),
    ]

    # Comments for Post 3 (DP discussion)
    comments_post3 = [
        ("DP used to be my weakness. The key is to practice the classic problems first.", regular_users[0] if len(regular_users) > 0 else all_authors[0]),
        ("Totally agree! Once you know the patterns, it becomes much easier.", regular_users[1] if len(regular_users) > 1 else all_authors[1]),
        ("Can someone explain the difference between top-down and bottom-up DP?", regular_users[2] if len(regular_users) > 2 else all_authors[2]),
        ("Top-down uses recursion with memoization, bottom-up builds the solution iteratively. Both have their uses!", creators[0] if creators else all_authors[1]),
        ("Top-down is often more intuitive to write, but bottom-up can be more memory efficient.", creators[1] if len(creators) > 1 else all_authors[0]),
        ("Thanks for the explanation! I'll practice both approaches.", regular_users[2] if len(regular_users) > 2 else all_authors[2]),
        ("What's the best way to optimize space in DP problems?", regular_users[3] if len(regular_users) > 3 else all_authors[0]),
        ("Often you only need the previous row or a few previous states. Look for rolling array optimizations.", creators[0] if creators else all_authors[1]),
        ("Also, sometimes you can reduce 2D DP to 1D if the recurrence only depends on the previous row.", regular_users[0] if len(regular_users) > 0 else all_authors[0]),
        ("Great point! Space optimization is crucial in contests with tight memory limits.", creators[1] if len(creators) > 1 else all_authors[1]),
        ("Does anyone have a good resource for DP on trees?", regular_users[4] if len(regular_users) > 4 else all_authors[2]),
        ("Tree DP is fascinating! The key is to think about what information you need from subtrees.", creators[0] if creators else all_authors[1]),
        ("I found the AtCoder DP contest really helpful for practicing various DP patterns.", regular_users[1] if len(regular_users) > 1 else all_authors[1]),
        ("Second that! The AtCoder DP contest has excellent problems covering most DP patterns.", regular_users[0] if len(regular_users) > 0 else all_authors[0]),
        ("Thanks everyone for the helpful discussion!", regular_users[4] if len(regular_users) > 4 else all_authors[2]),
    ]

    # Add comments to posts
    created_comments = {1: [], 2: [], 3: []}  # Track created comments for replies

    # Add comments to Post 1
    for content, author in comments_post1:
        comment = forum_service.create_comment(
            content=content,
            post_id=created_posts[0].id,
            author_id=author.id
        )
        created_comments[1].append(comment)

    # Add comments to Post 2
    for content, author in comments_post2:
        comment = forum_service.create_comment(
            content=content,
            post_id=created_posts[1].id,
            author_id=author.id
        )
        created_comments[2].append(comment)

    # Add comments to Post 3
    for content, author in comments_post3:
        comment = forum_service.create_comment(
            content=content,
            post_id=created_posts[2].id,
            author_id=author.id
        )
        created_comments[3].append(comment)

    # Add some nested replies (replies to comments)
    # Reply to a comment on Post 1
    if len(created_comments[1]) >= 2:
        forum_service.create_comment(
            content="Absolutely! The community here is very welcoming.",
            post_id=created_posts[0].id,
            author_id=all_authors[1].id,
            parent_id=created_comments[1][1].id  # Reply to second comment
        )

    # Replies to comments on Post 2
    if len(created_comments[2]) >= 4:
        forum_service.create_comment(
            content="GeeksforGeeks also has a good collection of problems sorted by difficulty.",
            post_id=created_posts[1].id,
            author_id=all_authors[2].id,
            parent_id=created_comments[2][2].id  # Reply to resource question
        )

    if len(created_comments[2]) >= 6:
        forum_service.create_comment(
            content="I'll check those out, thanks!",
            post_id=created_posts[1].id,
            author_id=all_authors[0].id,
            parent_id=created_comments[2][5].id  # Reply to thanks
        )

    # Replies to comments on Post 3 (DP discussion)
    if len(created_comments[3]) >= 3:
        forum_service.create_comment(
            content="I struggled with this too. Start with the Fibonacci sequence to understand the concept.",
            post_id=created_posts[2].id,
            author_id=all_authors[0].id,
            parent_id=created_comments[3][2].id  # Reply to top-down/bottom-up question
        )

    if len(created_comments[3]) >= 6:
        forum_service.create_comment(
            content="Can you give an example of rolling array optimization?",
            post_id=created_posts[2].id,
            author_id=all_authors[2].id,
            parent_id=created_comments[3][5].id  # Reply to space optimization
        )

    if len(created_comments[3]) >= 10:
        forum_service.create_comment(
            content="The CSES problem set has a section on tree algorithms that's quite good.",
            post_id=created_posts[2].id,
            author_id=all_authors[1].id,
            parent_id=created_comments[3][9].id  # Reply to tree DP question
        )

    # More nested replies
    if len(created_comments[3]) >= 12:
        forum_service.create_comment(
            content="How long does it typically take to complete that contest?",
            post_id=created_posts[2].id,
            author_id=all_authors[2].id,
            parent_id=created_comments[3][11].id  # Reply to AtCoder mention
        )

    # Even deeper nesting (reply to a reply)
    all_post3_comments = forum_service.get_post_comments(created_posts[2].id)
    reply_comments = [c for c in all_post3_comments if c.parent_id is not None]
    if reply_comments:
        forum_service.create_comment(
            content="It depends on your level, but most people take a few days to work through all problems.",
            post_id=created_posts[2].id,
            author_id=all_authors[0].id,
            parent_id=reply_comments[0].id  # Reply to a reply
        )

    # Add emoji reactions to posts and comments
    seed_emoji_reactions(forum_service, created_posts, all_authors)


def seed_emoji_reactions(forum_service, posts, users):
    """
    Seed emoji reactions for posts and comments.
    """
    from app.services.emoji_reaction_service import EmojiReactionService, VALID_EMOJIS
    from app.repositories.forum_repository import ForumRepository
    
    # Get the database session from forum_service
    db = forum_service.forum_repo.db
    
    emoji_service = EmojiReactionService(db)
    forum_repo = ForumRepository(db)
    
    # Get all comments for the posts
    all_comments = []
    for post in posts:
        comments = forum_repo.get_comments_by_post(post.id)
        all_comments.extend(comments)
    
    # Sample emojis to use
    emojis = list(VALID_EMOJIS)
    
    # Add reactions to posts
    for i, post in enumerate(posts):
        # Each post gets some reactions from different users
        num_reactions = min(5, len(users))
        for j in range(num_reactions):
            user = users[j]
            emoji = emojis[(i + j) % len(emojis)]
            try:
                emoji_service.add_or_update_reaction(
                    user_id=user.id,
                    target_type="post",
                    target_id=post.id,
                    emoji=emoji
                )
            except Exception as e:
                pass  # User might have already reacted
    
    # Add reactions to comments
    for i, comment in enumerate(all_comments[:20]):  # React to first 20 comments
        num_reactions = min(3, len(users))
        for j in range(num_reactions):
            user = users[j]
            emoji = emojis[(i + j + 3) % len(emojis)]
            try:
                emoji_service.add_or_update_reaction(
                    user_id=user.id,
                    target_type="comment",
                    target_id=comment.id,
                    emoji=emoji
                )
            except Exception as e:
                pass  # User might have already reacted


def seed_problem_discussions(discussion_service, problems, users, admin):
    """
    Seed problem discussions and comments for a few problems.
    """
    if not problems:
        return

    # Use a subset of problems
    problem_subset = problems[:3]
    regular_users = [u for u in users if u.role == UserRole.USER][:5]
    creators = [u for u in users if u.role == UserRole.CREATOR][:3]
    authors = regular_users + creators + [admin]

    # Ensure authors list isn't empty
    if not authors:
        authors = [admin]

    # Create discussions per problem
    discussions = []
    for idx, problem in enumerate(problem_subset):
        try:
            discussion = discussion_service.create_discussion(
                problem_id=problem.id,
                title=f"Discussion: {problem.title}",
                content=f"Let's discuss approaches for '{problem.title}'. Share your ideas and questions!",
                author_id=authors[idx % len(authors)].id
            )
            discussions.append(discussion)
        except Exception as e:
            # Continue seeding other discussions
            pass

    # Add comments and replies
    for discussion in discussions:
        # Create top-level comments
        comments = []
        for i in range(5):
            author = authors[i % len(authors)]
            try:
                comment = discussion_service.create_comment(
                    discussion_id=discussion.id,
                    content=f"Comment {i+1} on discussion {discussion.id}. Here's my thought...",
                    author_id=author.id
                )
                comments.append(comment)
            except Exception:
                pass

        # Add replies to some comments
        for i, comment in enumerate(comments[:3]):
            author = authors[(i + 1) % len(authors)]
            try:
                discussion_service.create_comment(
                    discussion_id=discussion.id,
                    content=f"Reply to comment {comment.id}: I agree with your point!",
                    author_id=author.id,
                    parent_id=comment.id
                )
            except Exception:
                pass


def seed_bookmarks(bookmark_service, problems, users):
    """
    Seed bookmarks for some users.
    """
    if not problems or not users:
        return

    # Bookmark first 5 problems for the first 3 users
    problem_subset = problems[:5]
    user_subset = users[:3]

    for user in user_subset:
        for problem in problem_subset:
            try:
                bookmark_service.add_bookmark(user.id, problem.id)
            except Exception:
                pass


def seed_contests(contest_service, problem_service, problems, creators, admin):
    """
    Seed contests with problems.
    Creates 5 contests with 30 problems each.
    """
    from app.schemas import ContestCreate, ProblemCreate, Testcase
    from app.models.contest import ContestType
    from datetime import datetime, timedelta, timezone

    # Check if we already have contests
    existing_contests = contest_service.list_contests(current_user=admin)
    if existing_contests["total"] >= 5:
        return  # Already have enough contests

    owners = creators if creators else [admin]
    
    # Create additional problems for contests (30 problems per contest, 5 contests = 150 problems)
    # We'll create new problems specifically for contests
    contest_problems = []
    
    # Create 150 problems for contests
    for i in range(150):
        owner = owners[i % len(owners)]
        problem_create = ProblemCreate(
            title=f"Contest Problem {i + 1}",
            description=f"Description for contest problem {i + 1}. This is a challenging problem for competitive programming.",
            constraints="1 <= n <= 10^5",
            difficulty=(i % 10) + 1,
            testcases=[Testcase(input="1", output="1"), Testcase(input="2", output="2")],
            tags=[],
            is_published=True,
            is_public=True
        )
        try:
            problem = problem_service.create_problem(problem_create, owner_id=owner.id, created_by=owner.username)
            contest_problems.append(problem)
        except Exception:
            pass

    if len(contest_problems) < 150:
        # If we couldn't create enough problems, use existing ones too
        contest_problems = list(problems) + contest_problems

    # Create 5 contests
    now = datetime.now(timezone.utc)
    contest_data = [
        {
            "title": "Weekly Contest 1",
            "description": "First weekly contest with a mix of easy, medium, and hard problems. Perfect for beginners and intermediate programmers!",
            "start_offset_days": -7,  # Past contest
            "duration_hours": 2,
            "contest_type": ContestType.PUBLIC,
        },
        {
            "title": "Weekly Contest 2",
            "description": "Second weekly contest featuring dynamic programming and graph problems.",
            "start_offset_days": -3,  # Recent past contest
            "duration_hours": 2,
            "contest_type": ContestType.PUBLIC,
        },
        {
            "title": "Biweekly Contest 1",
            "description": "Biweekly contest with more challenging problems. Test your skills in algorithms and data structures!",
            "start_offset_days": 1,  # Upcoming contest
            "duration_hours": 2,
            "contest_type": ContestType.PRIVATE,  # Private contest - requires registration
        },
        {
            "title": "Monthly Challenge - March",
            "description": "Monthly challenge with 30 problems covering various topics. Compete for the top spot on the leaderboard!",
            "start_offset_days": 5,  # Future contest
            "duration_hours": 24,
            "contest_type": ContestType.PUBLIC,
        },
        {
            "title": "Special Algorithm Contest",
            "description": "A special contest focused on advanced algorithms: segment trees, suffix arrays, and more!",
            "start_offset_days": 10,  # Future contest
            "duration_hours": 3,
            "contest_type": ContestType.PRIVATE,  # Private contest - requires registration
        },
    ]

    created_contests = []
    for i, data in enumerate(contest_data):
        start_date = now + timedelta(days=data["start_offset_days"])
        end_date = start_date + timedelta(hours=data["duration_hours"])
        
        # Select 30 problems for this contest
        start_idx = i * 30
        end_idx = start_idx + 30
        contest_problem_ids = [p.id for p in contest_problems[start_idx:end_idx]]
        
        contest_create = ContestCreate(
            title=data["title"],
            description=data["description"],
            start_date=start_date,
            end_date=end_date,
            contest_type=data["contest_type"],
            problem_ids=contest_problem_ids
        )
        
        try:
            contest = contest_service.create_contest(
                contest_create,
                owner_id=admin.id,
                created_by=admin.username
            )
            created_contests.append(contest)
        except Exception as e:
            pass

    return created_contests


def seed_contest_discussions(contest_discussion_service, contest_service, users, admin):
    """
    Seed discussions for contests.
    """
    # Get existing contests
    contests_result = contest_service.list_contests(current_user=admin)
    contests = contests_result.get("items", [])
    
    if not contests:
        return

    regular_users = [u for u in users if u.role == UserRole.USER][:5]
    creators = [u for u in users if u.role == UserRole.CREATOR][:3]
    authors = regular_users + creators + [admin]

    if not authors:
        authors = [admin]

    # Discussion topics for contests
    discussion_topics = [
        ("How was the contest?", "What did you think about today's contest? Which problems did you find most challenging?"),
        ("Problem Discussion", "Let's discuss the approaches used to solve the problems. Share your solutions!"),
        ("Tips for this contest", "Here are some tips that might help you in this contest..."),
    ]

    created_discussions = []
    for contest in contests[:5]:  # Create discussions for first 5 contests
        for topic_idx, (title, content) in enumerate(discussion_topics):
            author = authors[topic_idx % len(authors)]
            try:
                discussion = contest_discussion_service.create_discussion(
                    contest_id=contest.id,
                    title=title,
                    content=content,
                    author_id=author.id
                )
                created_discussions.append(discussion)
            except Exception:
                pass

    # Add comments to discussions
    for discussion in created_discussions[:10]:  # Add comments to first 10 discussions
        for i in range(3):
            author = authors[i % len(authors)]
            try:
                contest_discussion_service.create_comment(
                    discussion_id=discussion.id,
                    content=f"Great discussion! Here's my thought on this topic...",
                    author_id=author.id
                )
            except Exception:
                pass


def seed_contest_registrations(contest_service, contest_repo, users, admin):
    """
    Seed contest registrations for contests.
    Creates at least 40 registrations with different statuses.
    """
    from app.models.contest import ContestType, ContestRegistrationStatus
    from app.repositories.contest_registration_repository import ContestRegistrationRepository
    import random
    
    # Get all contests
    contests_result = contest_service.list_contests(current_user=admin)
    contests = contests_result.get("items", [])
    
    if not contests:
        return
    
    # Get the db session from contest_repo
    db = contest_repo.db
    registration_repo = ContestRegistrationRepository(db)
    
    # Get all users except admin
    regular_users = [u for u in users if u.role == UserRole.USER]
    creators = [u for u in users if u.role == UserRole.CREATOR]
    all_users = regular_users + creators
    
    if not all_users:
        return
    
    # Track total registrations
    total_registrations = 0
    target_registrations = 40
    
    # Register users for all contests (both public and private)
    for contest in contests:
        if total_registrations >= target_registrations:
            break
            
        # Determine how many users to register for this contest
        users_to_register = min(8, len(all_users), target_registrations - total_registrations)
        
        for i in range(users_to_register):
            user = all_users[i % len(all_users)]
            try:
                # Check if already registered
                existing = registration_repo.get_registration_by_contest_and_user(contest.id, user.id)
                if existing:
                    continue
                
                # Create registration
                registration = registration_repo.create_registration(contest.id, user.id)
                total_registrations += 1
                
                # Assign different statuses based on position
                # First 3 users get approved, next 2 get rejected, rest stay pending
                if i < 3:
                    registration_repo.update_registration_status(
                        registration,
                        ContestRegistrationStatus.APPROVED,
                        approved_by=admin.id
                    )
                elif i < 5:
                    registration_repo.update_registration_status(
                        registration,
                        ContestRegistrationStatus.REJECTED,
                        approved_by=admin.id
                    )
                # Remaining registrations stay pending
            except Exception:
                pass
    
    # If we still need more registrations, create additional ones
    while total_registrations < target_registrations:
        for contest in contests:
            if total_registrations >= target_registrations:
                break
            # Try to register more users
            for user in all_users:
                if total_registrations >= target_registrations:
                    break
                try:
                    existing = registration_repo.get_registration_by_contest_and_user(contest.id, user.id)
                    if existing:
                        continue
                    
                    registration = registration_repo.create_registration(contest.id, user.id)
                    total_registrations += 1
                    
                    # Vary the status
                    status_choice = random.choice([
                        ContestRegistrationStatus.APPROVED,
                        ContestRegistrationStatus.PENDING,
                        ContestRegistrationStatus.REJECTED
                    ])
                    
                    if status_choice == ContestRegistrationStatus.APPROVED:
                        registration_repo.update_registration_status(
                            registration,
                            ContestRegistrationStatus.APPROVED,
                            approved_by=admin.id
                        )
                    elif status_choice == ContestRegistrationStatus.REJECTED:
                        registration_repo.update_registration_status(
                            registration,
                            ContestRegistrationStatus.REJECTED,
                            approved_by=admin.id
                        )
                except Exception:
                    pass
    
    print(f"Created {total_registrations} contest registrations")


def seed_contest_announcements(contest_service, contest_repo, admin):
    """
    Seed announcements for contests.
    Creates announcements for each contest with various types of content.
    """
    from app.schemas import ContestAnnouncementCreate
    
    # Get all contests
    contests_result = contest_service.list_contests(current_user=admin)
    contests = contests_result.get("items", [])
    
    if not contests:
        return
    
    # Get the db session from contest_repo
    db = contest_repo.db
    
    # Announcement templates
    announcement_templates = [
        {
            "title": "Welcome to the Contest!",
            "content": "Welcome everyone to this exciting contest! We have prepared a variety of problems for you. Good luck and have fun!",
            "is_published": True
        },
        {
            "title": "Clarification on Problem A",
            "content": "There was a typo in the problem statement for Problem A. The constraint should be 1 <= n <= 10^6, not 10^5. We apologize for the confusion.",
            "is_published": True
        },
        {
            "title": "Time Extended by 15 Minutes",
            "content": "Due to technical difficulties at the start, we are extending the contest duration by 15 minutes. The new end time has been updated accordingly.",
            "is_published": True
        },
        {
            "title": "Reminder: Check Your Code",
            "content": "Please make sure to test your code thoroughly before submitting. Remember that wrong answers will result in a 5-minute penalty.",
            "is_published": True
        },
        {
            "title": "Draft: Post-Contest Analysis",
            "content": "This is a draft announcement for post-contest analysis. It will be published after the contest ends.",
            "is_published": False
        },
    ]
    
    total_announcements = 0
    
    for contest in contests:
        # Create 2-3 announcements per contest
        num_announcements = min(3, len(announcement_templates))
        
        for i in range(num_announcements):
            template = announcement_templates[i % len(announcement_templates)]
            try:
                contest_service.create_announcement(
                    contest_id=contest.id,
                    announcement_create=ContestAnnouncementCreate(
                        title=template["title"],
                        content=template["content"],
                        is_published=template["is_published"]
                    ),
                    current_user=admin
                )
                total_announcements += 1
            except Exception:
                pass
    
    print(f"Created {total_announcements} contest announcements")

