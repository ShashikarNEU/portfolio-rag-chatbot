from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from cachetools import TTLCache

from app.config import settings


class GitHubService:
    """Singleton wrapper for the GitHub REST API with TTL caching."""

    _instance: GitHubService | None = None

    def __init__(self) -> None:
        headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"

        self._client = httpx.Client(
            base_url="https://api.github.com",
            headers=headers,
            timeout=10.0,
        )
        self._username = settings.github_username

        # Caches: repos list (1 hr), repo details (5 min), activity (5 min)
        self._repos_cache: TTLCache[str, str] = TTLCache(maxsize=1, ttl=3600)
        self._details_cache: TTLCache[str, str] = TTLCache(maxsize=32, ttl=300)
        self._activity_cache: TTLCache[str, str] = TTLCache(maxsize=16, ttl=300)
        self._file_cache: TTLCache[str, str] = TTLCache(maxsize=64, ttl=300)

    @classmethod
    def get_instance(cls) -> GitHubService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── public methods ───────────────────────────────────────────────

    def list_repos(self) -> str:
        """List public repositories for the configured user."""
        cache_key = "repos"
        if cache_key in self._repos_cache:
            return self._repos_cache[cache_key]

        try:
            resp = self._client.get(
                f"/users/{self._username}/repos",
                params={"sort": "updated", "per_page": 30},
            )
            resp.raise_for_status()
            repos = resp.json()

            if not repos:
                return "No public repositories found."

            # For repos without a description, fetch the first line of the README
            missing_desc = [
                r["name"] for r in repos if not r.get("description")
            ]
            readme_summaries = self._fetch_readme_summaries(missing_desc)

            lines: list[str] = [f"**{self._username}'s GitHub Repositories:**\n"]
            for r in repos:
                stars = r.get("stargazers_count", 0)
                lang = r.get("language") or "N/A"
                desc = (
                    r.get("description")
                    or readme_summaries.get(r["name"])
                    or "No description"
                )
                lines.append(
                    f"- **{r['name']}** ({lang}, {stars} stars): {desc}"
                )

            result = "\n".join(lines)
            self._repos_cache[cache_key] = result
            return result

        except httpx.TimeoutException:
            return "GitHub API is taking too long. Please try again in a moment."
        except httpx.HTTPStatusError as e:
            return self._handle_http_error(e)
        except httpx.HTTPError:
            return "Unable to connect to GitHub right now. Please try again later."

    def get_repo_details(self, repo_name: str) -> str:
        """Get detailed info for a single repository."""
        cache_key = repo_name.lower()
        if cache_key in self._details_cache:
            return self._details_cache[cache_key]

        try:
            base = f"/repos/{self._username}/{repo_name}"

            # 1. Metadata
            meta_resp = self._client.get(base)
            meta_resp.raise_for_status()
            meta = meta_resp.json()

            parts: list[str] = [
                f"**{meta['full_name']}**",
                f"- Description: {meta.get('description') or 'N/A'}",
                f"- Stars: {meta.get('stargazers_count', 0)} | "
                f"Forks: {meta.get('forks_count', 0)} | "
                f"Open Issues: {meta.get('open_issues_count', 0)}",
                f"- Default Branch: {meta.get('default_branch', 'main')}",
                f"- URL: {meta.get('html_url', '')}",
            ]

            # 2. Languages
            try:
                lang_resp = self._client.get(f"{base}/languages")
                lang_resp.raise_for_status()
                langs = lang_resp.json()
                if langs:
                    total = sum(langs.values())
                    lang_parts = [
                        f"{k} ({v * 100 // total}%)" for k, v in langs.items()
                    ]
                    parts.append(f"- Languages: {', '.join(lang_parts)}")
            except httpx.HTTPError:
                pass

            # 3. README snippet
            try:
                readme_resp = self._client.get(
                    f"{base}/readme",
                    headers={"Accept": "application/vnd.github.raw+json"},
                )
                readme_resp.raise_for_status()
                readme_text = readme_resp.text[:1500]
                parts.append(f"\n**README (preview):**\n{readme_text}")
            except httpx.HTTPError:
                pass

            # 4. File tree (top-level)
            try:
                tree_resp = self._client.get(
                    f"{base}/git/trees/{meta.get('default_branch', 'main')}",
                )
                tree_resp.raise_for_status()
                tree = tree_resp.json().get("tree", [])
                if tree:
                    file_list = [
                        f"  {'[dir]' if item['type'] == 'tree' else '     '} {item['path']}"
                        for item in tree[:30]
                    ]
                    parts.append("\n**Project Structure:**\n" + "\n".join(file_list))
            except httpx.HTTPError:
                pass

            result = "\n".join(parts)
            self._details_cache[cache_key] = result
            return result

        except httpx.TimeoutException:
            return "GitHub API is taking too long. Please try again in a moment."
        except httpx.HTTPStatusError as e:
            return self._handle_http_error(e, repo_name)
        except httpx.HTTPError:
            return "Unable to connect to GitHub right now. Please try again later."

    def get_activity(self, repo_name: str = "") -> str:
        """Get recent commit activity for a repo, or recent events for user."""
        cache_key = f"activity:{repo_name or 'user'}"
        if cache_key in self._activity_cache:
            return self._activity_cache[cache_key]

        try:
            if repo_name:
                resp = self._client.get(
                    f"/repos/{self._username}/{repo_name}/commits",
                    params={"per_page": 10},
                )
                resp.raise_for_status()
                commits = resp.json()

                if not commits:
                    return f"No recent commits found in {repo_name}."

                lines = [f"**Recent commits in {repo_name}:**\n"]
                for c in commits:
                    sha = c["sha"][:7]
                    msg = c["commit"]["message"].split("\n")[0]
                    date = c["commit"]["author"]["date"][:10]
                    lines.append(f"- `{sha}` {msg} ({date})")
            else:
                resp = self._client.get(
                    f"/users/{self._username}/events/public",
                    params={"per_page": 15},
                )
                resp.raise_for_status()
                events = resp.json()

                if not events:
                    return "No recent public activity found."

                lines = [f"**{self._username}'s recent GitHub activity:**\n"]
                for ev in events:
                    repo = ev.get("repo", {}).get("name", "unknown")
                    etype = ev["type"].replace("Event", "")
                    date = ev.get("created_at", "")[:10]
                    lines.append(f"- {etype} on **{repo}** ({date})")

            result = "\n".join(lines)
            self._activity_cache[cache_key] = result
            return result

        except httpx.TimeoutException:
            return "GitHub API is taking too long. Please try again in a moment."
        except httpx.HTTPStatusError as e:
            return self._handle_http_error(e, repo_name)
        except httpx.HTTPError:
            return "Unable to connect to GitHub right now. Please try again later."

    def read_file(self, repo_name: str, file_path: str) -> str:
        """Read a file's raw content from a repository."""
        cache_key = f"{repo_name.lower()}:{file_path}"
        if cache_key in self._file_cache:
            return self._file_cache[cache_key]

        try:
            resp = self._client.get(
                f"/repos/{self._username}/{repo_name}/contents/{file_path}",
                headers={"Accept": "application/vnd.github.raw+json"},
            )
            resp.raise_for_status()
            content = resp.text

            # Detect language for code block formatting
            ext = file_path.rsplit(".", 1)[-1] if "." in file_path else ""
            lang_map = {
                "py": "python", "js": "javascript", "ts": "typescript",
                "yml": "yaml", "yaml": "yaml", "md": "markdown",
                "json": "json", "toml": "toml", "sh": "bash",
            }
            lang = lang_map.get(ext, ext)

            truncated = ""
            if len(content) > 4000:
                content = content[:4000]
                truncated = "\n\n*[File truncated — showing first 4000 characters]*"

            result = f"**{repo_name}/{file_path}:**\n```{lang}\n{content}\n```{truncated}"
            self._file_cache[cache_key] = result
            return result

        except httpx.TimeoutException:
            return "GitHub API is taking too long. Please try again in a moment."
        except httpx.HTTPStatusError as e:
            return self._handle_http_error(e, repo_name, file_path)
        except httpx.HTTPError:
            return "Unable to connect to GitHub right now. Please try again later."

    # ── private helpers ──────────────────────────────────────────────

    def _fetch_readme_summaries(self, repo_names: list[str]) -> dict[str, str]:
        """Fetch the first meaningful line of each repo's README concurrently.

        Returns {repo_name: summary_line} for repos where a README exists.
        """
        if not repo_names:
            return {}

        def _fetch_one(name: str) -> tuple[str, str]:
            resp = self._client.get(
                f"/repos/{self._username}/{name}/readme",
                headers={"Accept": "application/vnd.github.raw+json"},
                timeout=5.0,
            )
            resp.raise_for_status()
            return name, self._extract_first_line(resp.text)

        summaries: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(_fetch_one, n): n for n in repo_names}
            for future in as_completed(futures):
                try:
                    name, summary = future.result()
                    if summary:
                        summaries[name] = summary
                except Exception:
                    continue
        return summaries

    @staticmethod
    def _extract_first_line(readme_text: str) -> str:
        """Extract the first meaningful line from README content."""
        for line in readme_text.splitlines():
            stripped = line.strip()
            # Skip blank lines, markdown headers, badges, HTML tags
            if not stripped:
                continue
            if stripped.startswith(("#", "![", "<", "---", "***", "===")):
                continue
            # Remove inline markdown links/bold/italic for a clean summary
            return stripped[:150]
        return ""

    @staticmethod
    def _handle_http_error(
        exc: httpx.HTTPStatusError,
        repo_name: str = "",
        file_path: str = "",
    ) -> str:
        status = exc.response.status_code
        if status == 404:
            if file_path:
                return f"File '{file_path}' not found in repository '{repo_name}'."
            if repo_name:
                return f"Repository '{repo_name}' not found."
            return "The requested resource was not found on GitHub."
        if status == 403:
            return "GitHub API rate limit reached. Please try again in a few minutes."
        return f"GitHub returned an error (HTTP {status}). Please try again."
