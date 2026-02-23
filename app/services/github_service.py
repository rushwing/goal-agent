"""GitHub integration: auto-commit plans and reports as Markdown."""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from github import Github, GithubException
from github.Repository import Repository

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="github")


def _get_repo() -> Repository:
    g = Github(settings.GITHUB_PAT)
    return g.get_repo(settings.GITHUB_DATA_REPO)


def _upsert_file_sync(
    file_path: str, content: str, commit_message: str
) -> tuple[str, str]:
    """
    Create or update a file in the GitHub data repo.
    Returns (commit_sha, file_path).
    """
    repo = _get_repo()
    committer = {
        "name": settings.GITHUB_COMMITTER_NAME,
        "email": settings.GITHUB_COMMITTER_EMAIL,
    }
    try:
        existing = repo.get_contents(file_path)
        result = repo.update_file(
            path=file_path,
            message=commit_message,
            content=content,
            sha=existing.sha,  # type: ignore[union-attr]
            committer=committer,
        )
    except GithubException as exc:
        if exc.status == 404:
            result = repo.create_file(
                path=file_path,
                message=commit_message,
                content=content,
                committer=committer,
            )
        else:
            raise

    commit_sha: str = result["commit"].sha
    return commit_sha, file_path


async def upsert_file(
    file_path: str, content: str, commit_message: str
) -> tuple[str, str]:
    """Async wrapper – runs sync PyGithub call in thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor, _upsert_file_sync, file_path, content, commit_message
    )


async def commit_plan(
    pupil_name: str,
    vacation_type: str,
    vacation_year: int,
    plan_title: str,
    content_md: str,
) -> tuple[str, str]:
    """Commit a generated plan markdown file."""
    safe_name = pupil_name.lower().replace(" ", "_")
    file_path = f"plans/{safe_name}/{vacation_type}_{vacation_year}/plan.md"
    commit_msg = f"Add study plan: {plan_title}"
    return await upsert_file(file_path, content_md, commit_msg)


async def commit_report(
    pupil_name: str,
    report_type: str,
    year: int,
    period_label: str,
    content_md: str,
) -> tuple[str, str]:
    """Commit a report markdown file."""
    safe_name = pupil_name.lower().replace(" ", "_")
    file_path = f"reports/{safe_name}/{year}/{report_type}/{period_label}.md"
    commit_msg = f"Add {report_type} report: {period_label}"
    return await upsert_file(file_path, content_md, commit_msg)
