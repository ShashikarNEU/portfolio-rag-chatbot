"""Tests for GitHubService — real GitHub API calls."""

import pytest

from app.services.github_service import GitHubService


@pytest.fixture(autouse=True)
def _reset_singleton() -> None:
    """Reset GitHubService singleton between tests."""
    GitHubService._instance = None


@pytest.fixture()
def service() -> GitHubService:
    return GitHubService.get_instance()


class TestListRepos:
    def test_list_repos_returns_results(self, service: GitHubService) -> None:
        result = service.list_repos()
        assert "portfolio-rag-chatbot" in result.lower()
        assert "**" in result  # bold formatting

    def test_list_repos_cached(self, service: GitHubService) -> None:
        result1 = service.list_repos()
        result2 = service.list_repos()
        assert result1 == result2
        assert "repos" in service._repos_cache  # cache key present


class TestRepoDetails:
    def test_repo_details_returns_metadata(self, service: GitHubService) -> None:
        result = service.get_repo_details("portfolio-rag-chatbot")
        assert "portfolio-rag-chatbot" in result.lower()
        assert "Python" in result
        assert "README" in result

    def test_repo_details_includes_structure(self, service: GitHubService) -> None:
        result = service.get_repo_details("portfolio-rag-chatbot")
        assert "Project Structure" in result
        assert "app" in result

    def test_repo_details_not_found(self, service: GitHubService) -> None:
        result = service.get_repo_details("this-repo-does-not-exist-xyz-12345")
        assert "not found" in result.lower()


class TestReadFile:
    def test_read_file_returns_code(self, service: GitHubService) -> None:
        result = service.read_file("portfolio-rag-chatbot", "pyproject.toml")
        assert "```toml" in result
        assert "portfolio-rag-chatbot" in result
        assert "fastapi" in result.lower()

    def test_read_file_python(self, service: GitHubService) -> None:
        result = service.read_file("portfolio-rag-chatbot", "app/main.py")
        assert "```python" in result
        assert "FastAPI" in result

    def test_read_file_not_found(self, service: GitHubService) -> None:
        result = service.read_file("portfolio-rag-chatbot", "nonexistent_file.xyz")
        assert "not found" in result.lower()


class TestActivity:
    def test_activity_for_repo(self, service: GitHubService) -> None:
        result = service.get_activity("portfolio-rag-chatbot")
        assert "commit" in result.lower()
        # Commits have short SHA format
        assert "`" in result

    def test_activity_for_user(self, service: GitHubService) -> None:
        result = service.get_activity()
        assert "activity" in result.lower() or "No recent" in result
