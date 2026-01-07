"""GitHub repository content fetcher optimized for Kubernetes operators."""

import base64
from dataclasses import dataclass
from typing import Generator
from urllib.parse import urlparse
from github import Github
from github.GithubException import GithubException
from rich.console import Console

from app.config import settings

console = Console()


@dataclass
class GitHubFile:
    """A file from a GitHub repository."""
    path: str
    content: str
    url: str
    file_type: str  # readme, api_types, crd, rbac, sample, docs, code


class GitHubFetcher:
    """Fetch content from GitHub repositories with operator-aware prioritization."""
    
    # Priority files to always fetch
    PRIORITY_FILES = [
        "README.md", "readme.md", "README.rst",
        "CONTRIBUTING.md", "CHANGELOG.md", "ARCHITECTURE.md",
        "docs/README.md", "doc/README.md",
    ]
    
    # Directories with documentation
    DOC_DIRS = ["docs", "doc", "documentation", "examples", "samples"]
    
    # Operator-specific directories
    OPERATOR_DIRS = [
        "api",                    # API types
        "apis",                   # Alternative API location
        "config/crd",             # CRD manifests
        "config/rbac",            # RBAC rules
        "config/samples",         # Sample CRs
        "bundle/manifests",       # OLM bundle
        "charts",                 # Helm charts
        "deploy",                 # Deployment manifests
        "hack",                   # Scripts and tools
    ]
    
    def __init__(self, repo_url: str, max_files: int = 100):
        self.repo_url = repo_url
        self.max_files = max_files
        self.fetched_count = 0
        
        # Parse repository URL
        parsed = urlparse(repo_url)
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) >= 2:
            self.owner = path_parts[0]
            self.repo_name = path_parts[1].replace(".git", "")
        else:
            raise ValueError(f"Invalid GitHub URL: {repo_url}")
        
        # Initialize GitHub client
        self.github = Github(settings.github_token) if settings.github_token else Github()
    
    def fetch(self) -> Generator[GitHubFile, None, None]:
        """Fetch relevant files from the repository."""
        console.print(f"[blue]Fetching from GitHub:[/blue] {self.owner}/{self.repo_name}")
        
        try:
            repo = self.github.get_repo(f"{self.owner}/{self.repo_name}")
            
            # Fetch priority files first
            for file_path in self.PRIORITY_FILES:
                if self.fetched_count >= self.max_files:
                    break
                try:
                    content = repo.get_contents(file_path)
                    if not isinstance(content, list):
                        yield from self._process_file(content, "readme")
                except GithubException:
                    pass
            
            # Fetch operator-specific directories
            for dir_path in self.OPERATOR_DIRS:
                if self.fetched_count >= self.max_files:
                    break
                yield from self._fetch_directory(repo, dir_path, self._get_file_type(dir_path))
            
            # Fetch documentation directories
            for dir_path in self.DOC_DIRS:
                if self.fetched_count >= self.max_files:
                    break
                yield from self._fetch_directory(repo, dir_path, "docs")
            
            console.print(f"[green]GitHub fetch complete:[/green] {self.fetched_count} files")
            
        except GithubException as e:
            console.print(f"[red]GitHub error:[/red] {e}")
    
    def _fetch_directory(self, repo, path: str, file_type: str, depth: int = 0) -> Generator[GitHubFile, None, None]:
        """Recursively fetch files from a directory."""
        if depth > 4 or self.fetched_count >= self.max_files:
            return
        
        try:
            contents = repo.get_contents(path)
            if not isinstance(contents, list):
                contents = [contents]
            
            for item in contents:
                if self.fetched_count >= self.max_files:
                    break
                
                if item.type == "dir":
                    yield from self._fetch_directory(repo, item.path, file_type, depth + 1)
                elif item.type == "file":
                    yield from self._process_file(item, file_type)
                    
        except GithubException:
            pass
    
    def _process_file(self, file_content, file_type: str) -> Generator[GitHubFile, None, None]:
        """Process a single file."""
        # Skip large files and binaries
        if file_content.size > 500000:  # 500KB
            return
        
        # Only process relevant file types
        relevant_extensions = {
            ".md", ".rst", ".txt", ".adoc",  # Docs
            ".go", ".py", ".yaml", ".yml", ".json",  # Code/config
            ".sh", ".bash",  # Scripts
        }
        
        ext = "." + file_content.path.split(".")[-1] if "." in file_content.path else ""
        if ext.lower() not in relevant_extensions and file_content.path not in self.PRIORITY_FILES:
            return
        
        try:
            # Decode content
            content = base64.b64decode(file_content.content).decode("utf-8")
            
            self.fetched_count += 1
            console.print(f"  [dim]Fetched ({self.fetched_count}):[/dim] {file_content.path}")
            
            yield GitHubFile(
                path=file_content.path,
                content=content,
                url=file_content.html_url,
                file_type=file_type
            )
            
        except Exception as e:
            console.print(f"  [red]Error processing {file_content.path}:[/red] {e}")
    
    def _get_file_type(self, dir_path: str) -> str:
        """Determine file type based on directory."""
        if "api" in dir_path:
            return "api_types"
        elif "crd" in dir_path:
            return "crd"
        elif "rbac" in dir_path:
            return "rbac"
        elif "sample" in dir_path:
            return "sample"
        elif "chart" in dir_path or "helm" in dir_path:
            return "helm_chart"
        elif "bundle" in dir_path:
            return "olm_bundle"
        else:
            return "code"


@dataclass
class GitHubIssue:
    """A GitHub issue with its discussion."""
    number: int
    title: str
    body: str
    state: str  # open, closed
    labels: list[str]
    url: str
    comments: list[str]


class GitHubIssuesFetcher:
    """Fetch issues from GitHub repositories."""
    
    def __init__(self, repo_url: str, max_issues: int = 100, include_closed: bool = True):
        self.repo_url = repo_url
        self.max_issues = max_issues
        self.include_closed = include_closed
        
        # Parse repository URL
        parsed = urlparse(repo_url)
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) >= 2:
            self.owner = path_parts[0]
            self.repo_name = path_parts[1].replace(".git", "")
        else:
            raise ValueError(f"Invalid GitHub URL: {repo_url}")
        
        # Initialize GitHub client
        self.github = Github(settings.github_token) if settings.github_token else Github()
    
    def fetch(self) -> Generator[GitHubIssue, None, None]:
        """Fetch issues from the repository."""
        console.print(f"[blue]Fetching GitHub issues:[/blue] {self.owner}/{self.repo_name}")
        
        try:
            repo = self.github.get_repo(f"{self.owner}/{self.repo_name}")
            fetched = 0
            
            # Fetch open issues
            for issue in repo.get_issues(state="open", sort="updated", direction="desc"):
                if fetched >= self.max_issues:
                    break
                if issue.pull_request:  # Skip PRs
                    continue
                yield from self._process_issue(issue)
                fetched += 1
            
            # Fetch closed issues (often have solutions!)
            if self.include_closed:
                for issue in repo.get_issues(state="closed", sort="updated", direction="desc"):
                    if fetched >= self.max_issues:
                        break
                    if issue.pull_request:
                        continue
                    yield from self._process_issue(issue)
                    fetched += 1
            
            console.print(f"[green]GitHub issues fetched:[/green] {fetched} issues")
            
        except GithubException as e:
            console.print(f"[red]GitHub issues error:[/red] {e}")
    
    def _process_issue(self, issue) -> Generator[GitHubIssue, None, None]:
        """Process a single issue."""
        # Get comments (limited to avoid rate limits)
        comments = []
        try:
            for comment in issue.get_comments()[:10]:  # Max 10 comments per issue
                if comment.body:
                    comments.append(comment.body)
        except GithubException:
            pass
        
        labels = [label.name for label in issue.labels]
        
        yield GitHubIssue(
            number=issue.number,
            title=issue.title,
            body=issue.body or "",
            state=issue.state,
            labels=labels,
            url=issue.html_url,
            comments=comments
        )


