"""Git operations manager using subprocess."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from genai_cli.config import ConfigManager
from genai_cli.display import Display


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class GitStatus:
    """Status of a git repository."""

    is_repo: bool = False
    branch: str = ""
    clean: bool = True
    staged: list[str] = field(default_factory=list)
    unstaged: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)


@dataclass
class GitResult:
    """Result of a git command."""

    success: bool
    command: str
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


class GitOperations:
    """Safe wrapper around git CLI operations."""

    def __init__(
        self,
        config: ConfigManager,
        display: Display,
        work_dir: Path | None = None,
    ) -> None:
        self._config = config
        self._display = display
        self._work_dir = work_dir or Path.cwd()

    def _run_git(
        self,
        args: list[str],
        work_dir: Path | None = None,
        timeout: int = 30,
    ) -> GitResult:
        """Run a git command and return the result."""
        cmd = ["git"] + args
        cwd = work_dir or self._work_dir
        cmd_str = " ".join(cmd)

        try:
            result = subprocess.run(  # noqa: S603, S607
                cmd,
                capture_output=True,
                text=True,
                cwd=str(cwd),
                timeout=timeout,
            )
            return GitResult(
                success=result.returncode == 0,
                command=cmd_str,
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip(),
                return_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return GitResult(
                success=False,
                command=cmd_str,
                stderr=f"Command timed out after {timeout}s",
                return_code=-1,
            )
        except FileNotFoundError:
            return GitResult(
                success=False,
                command=cmd_str,
                stderr="git not found in PATH",
                return_code=-1,
            )

    # --- Status ---

    def status(self, work_dir: Path | None = None) -> GitStatus:
        """Get comprehensive git status."""
        cwd = work_dir or self._work_dir

        if not self.is_repo(cwd):
            return GitStatus(is_repo=False)

        branch = self.current_branch(cwd)

        staged_result = self._run_git(
            ["diff", "--cached", "--name-only"], cwd
        )
        staged = (
            staged_result.stdout.splitlines() if staged_result.success else []
        )

        unstaged_result = self._run_git(["diff", "--name-only"], cwd)
        unstaged = (
            unstaged_result.stdout.splitlines()
            if unstaged_result.success
            else []
        )

        untracked_result = self._run_git(
            ["ls-files", "--others", "--exclude-standard"], cwd
        )
        untracked = (
            untracked_result.stdout.splitlines()
            if untracked_result.success
            else []
        )

        clean = not staged and not unstaged and not untracked

        return GitStatus(
            is_repo=True,
            branch=branch,
            clean=clean,
            staged=staged,
            unstaged=unstaged,
            untracked=untracked,
        )

    def is_repo(self, work_dir: Path | None = None) -> bool:
        """Check if the directory is a git repository."""
        result = self._run_git(
            ["rev-parse", "--is-inside-work-tree"],
            work_dir or self._work_dir,
        )
        return result.success and result.stdout == "true"

    def current_branch(self, work_dir: Path | None = None) -> str:
        """Get the current branch name."""
        result = self._run_git(
            ["rev-parse", "--abbrev-ref", "HEAD"],
            work_dir or self._work_dir,
        )
        return result.stdout if result.success else ""

    def is_clean(self, work_dir: Path | None = None) -> bool:
        """Check if the working tree is clean."""
        result = self._run_git(
            ["status", "--porcelain"],
            work_dir or self._work_dir,
        )
        return result.success and result.stdout == ""

    # --- Repo operations ---

    def init(self, path: Path) -> GitResult:
        """Initialize a new git repository."""
        path.mkdir(parents=True, exist_ok=True)
        return self._run_git(["init"], path)

    def add(
        self, paths: list[str], work_dir: Path | None = None
    ) -> GitResult:
        """Stage files for commit."""
        return self._run_git(["add"] + paths, work_dir)

    def commit(
        self, message: str, work_dir: Path | None = None
    ) -> GitResult:
        """Create a commit."""
        return self._run_git(["commit", "-m", message], work_dir)

    def create_branch(
        self, name: str, work_dir: Path | None = None
    ) -> GitResult:
        """Create a new branch."""
        return self._run_git(["branch", name], work_dir)

    def checkout(
        self, branch: str, work_dir: Path | None = None
    ) -> GitResult:
        """Switch to a branch."""
        return self._run_git(["checkout", branch], work_dir)

    # --- File operations ---

    def mv(
        self, src: str, dst: str, work_dir: Path | None = None
    ) -> GitResult:
        """Move/rename a file using git mv."""
        return self._run_git(["mv", src, dst], work_dir)

    def rm(
        self,
        paths: list[str],
        cached: bool = False,
        work_dir: Path | None = None,
    ) -> GitResult:
        """Remove files from tracking (and optionally disk)."""
        args = ["rm"]
        if cached:
            args.append("--cached")
        args.extend(paths)
        return self._run_git(args, work_dir)

    # --- Advanced ---

    def subtree_split(
        self, prefix: str, branch: str, work_dir: Path | None = None
    ) -> GitResult:
        """Split a subdirectory into its own branch."""
        return self._run_git(
            ["subtree", "split", "--prefix", prefix, "-b", branch],
            work_dir,
        )

    def add_remote(
        self, name: str, url: str, work_dir: Path | None = None
    ) -> GitResult:
        """Add a remote."""
        return self._run_git(["remote", "add", name, url], work_dir)

    def create_gitignore(self, path: Path, patterns: list[str]) -> None:
        """Create a .gitignore file with given patterns."""
        gitignore = path / ".gitignore"
        gitignore.write_text("\n".join(patterns) + "\n")

    # --- Safety ---

    def ensure_clean(self, work_dir: Path | None = None) -> bool:
        """Ensure working tree is clean, warn if not."""
        if not self.is_clean(work_dir):
            self._display.print_warning(
                "Working tree has uncommitted changes."
            )
            return False
        return True

    def create_checkpoint(
        self, message: str, work_dir: Path | None = None
    ) -> GitResult:
        """Stage everything and create a checkpoint commit."""
        cwd = work_dir or self._work_dir
        self._run_git(["add", "-A"], cwd)
        return self._run_git(
            ["commit", "-m", f"checkpoint: {message}"], cwd
        )

    def rollback_to(
        self, commit_hash: str, work_dir: Path | None = None
    ) -> GitResult:
        """Roll back to a specific commit (with confirmation)."""
        if not self._display.confirm(
            f"Roll back to {commit_hash[:8]}? This will discard changes."
        ):
            return GitResult(
                success=False,
                command="git reset",
                stderr="Cancelled by user",
            )
        return self._run_git(
            ["reset", "--hard", commit_hash],
            work_dir,
        )
