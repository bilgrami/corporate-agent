"""Multi-repo workspace manager."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from genai_cli.analyzer import DependencyAnalyzer
from genai_cli.config import ConfigManager
from genai_cli.display import Display
from genai_cli.git_ops import GitOperations


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class RepoConfig:
    """Configuration for a single repository in a workspace."""

    name: str
    path: str
    is_active: bool = False
    remote_url: str = ""
    description: str = ""


@dataclass
class WorkspaceConfig:
    """Configuration for a multi-repo workspace."""

    name: str
    repos: list[RepoConfig] = field(default_factory=list)
    workspace_root: str = ""
    created_at: str = ""


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class WorkspaceManager:
    """Manage multi-repo workspaces for cross-repo operations."""

    WORKSPACE_FILE = ".genai-workspace.yaml"

    def __init__(self, config: ConfigManager, display: Display) -> None:
        self._config = config
        self._display = display
        self._workspace: WorkspaceConfig | None = None

    def create_workspace(
        self, name: str, root: Path | str
    ) -> WorkspaceConfig:
        """Create a new workspace at the given root directory."""
        root_path = Path(root).resolve()
        root_path.mkdir(parents=True, exist_ok=True)

        self._workspace = WorkspaceConfig(
            name=name,
            workspace_root=str(root_path),
            created_at=datetime.now(tz=timezone.utc).isoformat(),
        )
        self.save_workspace()
        self._display.print_success(f"Created workspace: {name}")
        return self._workspace

    def load_workspace(self, path: Path | str) -> WorkspaceConfig | None:
        """Load a workspace from a .genai-workspace.yaml file."""
        ws_path = Path(path)
        if ws_path.is_dir():
            ws_path = ws_path / self.WORKSPACE_FILE

        if not ws_path.is_file():
            self._display.print_error(
                f"Workspace file not found: {ws_path}"
            )
            return None

        try:
            data = yaml.safe_load(ws_path.read_text())
        except Exception as e:
            self._display.print_error(f"Failed to load workspace: {e}")
            return None

        repos = [
            RepoConfig(**r) for r in data.get("repos", [])
        ]
        self._workspace = WorkspaceConfig(
            name=data.get("name", ""),
            repos=repos,
            workspace_root=data.get("workspace_root", str(ws_path.parent)),
            created_at=data.get("created_at", ""),
        )
        return self._workspace

    def save_workspace(self) -> None:
        """Save the current workspace config to disk."""
        if not self._workspace:
            return

        ws_root = Path(self._workspace.workspace_root)
        ws_path = ws_root / self.WORKSPACE_FILE

        data = {
            "name": self._workspace.name,
            "workspace_root": self._workspace.workspace_root,
            "created_at": self._workspace.created_at,
            "repos": [
                {
                    "name": r.name,
                    "path": r.path,
                    "is_active": r.is_active,
                    "remote_url": r.remote_url,
                    "description": r.description,
                }
                for r in self._workspace.repos
            ],
        }

        ws_path.write_text(yaml.dump(data, default_flow_style=False))

    # --- Repo management ---

    def add_repo(
        self,
        name: str,
        path: str | Path,
        remote_url: str = "",
        description: str = "",
    ) -> RepoConfig:
        """Add a repository to the workspace."""
        if not self._workspace:
            raise RuntimeError("No workspace loaded")

        resolved = str(Path(path).resolve())
        repo = RepoConfig(
            name=name,
            path=resolved,
            is_active=len(self._workspace.repos) == 0,
            remote_url=remote_url,
            description=description,
        )
        self._workspace.repos.append(repo)
        self.save_workspace()
        self._display.print_success(f"Added repo: {name} ({resolved})")
        return repo

    def remove_repo(self, name: str) -> bool:
        """Remove a repository from the workspace."""
        if not self._workspace:
            raise RuntimeError("No workspace loaded")

        original_len = len(self._workspace.repos)
        self._workspace.repos = [
            r for r in self._workspace.repos if r.name != name
        ]
        removed = len(self._workspace.repos) < original_len

        if removed:
            self.save_workspace()
            self._display.print_success(f"Removed repo: {name}")
        else:
            self._display.print_error(f"Repo not found: {name}")

        return removed

    def list_repos(self) -> list[RepoConfig]:
        """List all repositories in the workspace."""
        if not self._workspace:
            return []
        return list(self._workspace.repos)

    def switch_repo(self, name: str) -> bool:
        """Switch the active repository."""
        if not self._workspace:
            raise RuntimeError("No workspace loaded")

        found = False
        for repo in self._workspace.repos:
            if repo.name == name:
                repo.is_active = True
                found = True
            else:
                repo.is_active = False

        if found:
            self.save_workspace()
            self._display.print_success(f"Switched to repo: {name}")
        else:
            self._display.print_error(f"Repo not found: {name}")

        return found

    def get_active_repo(self) -> RepoConfig | None:
        """Get the currently active repository."""
        if not self._workspace:
            return None
        for repo in self._workspace.repos:
            if repo.is_active:
                return repo
        return None

    # --- Cross-repo operations ---

    def move_file(
        self,
        source_repo: str,
        source_path: str,
        target_repo: str,
        target_path: str,
    ) -> bool:
        """Move a file from one repo to another."""
        if not self._workspace:
            raise RuntimeError("No workspace loaded")

        src_repo = self._get_repo(source_repo)
        tgt_repo = self._get_repo(target_repo)
        if not src_repo or not tgt_repo:
            return False

        src_full = Path(src_repo.path) / source_path
        tgt_full = Path(tgt_repo.path) / target_path

        if not src_full.is_file():
            self._display.print_error(f"Source file not found: {src_full}")
            return False

        tgt_full.parent.mkdir(parents=True, exist_ok=True)

        import shutil

        shutil.copy2(src_full, tgt_full)

        git = GitOperations(self._config, self._display)

        git.add([target_path], Path(tgt_repo.path))
        git.rm([source_path], work_dir=Path(src_repo.path))

        self._display.print_success(
            f"Moved {source_path} from {source_repo} to {target_repo}"
        )
        return True

    def cross_repo_analysis(self) -> str:
        """Run dependency analysis across all repos in workspace."""
        if not self._workspace:
            return "No workspace loaded"

        analyzer = DependencyAnalyzer(self._config, self._display)
        lines: list[str] = [
            f"# Cross-Repo Analysis: {self._workspace.name}",
            "",
        ]

        for repo in self._workspace.repos:
            repo_path = Path(repo.path)
            if not repo_path.is_dir():
                lines.append(f"## {repo.name} (not found)")
                continue

            report = analyzer.analyze([str(repo_path)], str(repo_path))
            lines.append(f"## {repo.name}")
            lines.append(f"  Modules: {report.total_modules}")
            lines.append(f"  Imports: {report.total_imports}")
            lines.append(f"  Cycles: {len(report.cycles)}")
            lines.append("")

        return "\n".join(lines)

    def find_file(self, filename: str) -> list[tuple[str, str]]:
        """Find a file across all repos. Returns [(repo_name, path)]."""
        if not self._workspace:
            return []

        results: list[tuple[str, str]] = []
        for repo in self._workspace.repos:
            repo_path = Path(repo.path)
            for match in repo_path.rglob(filename):
                try:
                    rel = str(match.relative_to(repo_path))
                except ValueError:
                    rel = str(match)
                results.append((repo.name, rel))

        return results

    def get_repo_for_path(self, path: str) -> RepoConfig | None:
        """Determine which repo a path belongs to."""
        if not self._workspace:
            return None

        resolved = Path(path).resolve()
        for repo in self._workspace.repos:
            repo_path = Path(repo.path).resolve()
            try:
                resolved.relative_to(repo_path)
                return repo
            except ValueError:
                continue

        return None

    def _get_repo(self, name: str) -> RepoConfig | None:
        """Get a repo by name."""
        if not self._workspace:
            return None
        for repo in self._workspace.repos:
            if repo.name == name:
                return repo
        self._display.print_error(f"Repo not found: {name}")
        return None
