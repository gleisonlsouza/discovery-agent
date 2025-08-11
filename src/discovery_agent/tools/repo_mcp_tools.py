from __future__ import annotations

import os
import sys
from typing import List, Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ListRepositoryFilesInput(BaseModel):
    """Input for listing repository files via MCP provider or local FS fallback."""

    repo_root: str = Field(..., description="Absolute path to the repository root to scan")
    include_globs: List[str] = Field(
        default_factory=lambda: ["**/*"],
        description="Glob patterns to include (e.g., ['**/*.py', '**/*.ts'])",
    )
    exclude_globs: List[str] = Field(
        default_factory=lambda: ["**/.git/**", "**/node_modules/**", "**/.venv/**"],
        description="Glob patterns to exclude from scan",
    )
    max_files: int = Field(
        default=5000, description="Maximum number of files to return to avoid large prompts"
    )
    output_file: Optional[str] = Field(
        default=None,
        description="Optional path to write full result JSON. If set, tool will only return a short summary with the file path.",
    )


class ListRepositoryFilesTool(BaseTool):
    name: str = "list_repository_files"
    description: str = (
        "List repository files using the local filesystem only. Returns a JSON with file paths and extensions."
    )
    args_schema: Type[BaseModel] = ListRepositoryFilesInput

    def _run(
        self,
        repo_root: str,
        include_globs: List[str] | None = None,
        exclude_globs: List[str] | None = None,
        max_files: int = 5000,
        output_file: Optional[str] = None,
    ) -> str:
        include_globs = include_globs or ["**/*"]
        exclude_globs = exclude_globs or ["**/.git/**", "**/node_modules/**", "**/.venv/**"]

        files: List[str] = self._scan_local_fs(repo_root, include_globs, exclude_globs)

        # Cap number of files to reduce token size
        if len(files) > max_files:
            files = files[:max_files]

        # Build extension stats
        extensions: dict[str, int] = {}
        for path in files:
            ext = os.path.splitext(path)[1].lower() or "<no_ext>"
            extensions[ext] = extensions.get(ext, 0) + 1

        import json
        result = {"files": files, "extensions": extensions, "count": len(files)}

        if output_file:
            try:
                with open(output_file, "w", encoding="utf-8") as fh:
                    json.dump(result, fh)
                # Return compact summary only
                return json.dumps({
                    "message": "files written",
                    "output_file": output_file,
                    "count": len(files),
                    "ext_top": sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:10],
                })
            except Exception:
                # Fallback to returning inline
                return json.dumps(result)

        return json.dumps(result)

    def _scan_local_fs(
        self, repo_root: str, include_globs: List[str], exclude_globs: List[str]
    ) -> List[str]:
        from pathlib import Path
        import fnmatch

        root = Path(repo_root)
        if not root.exists():
            return []

        matched: List[str] = []
        for dirpath, dirnames, filenames in os.walk(root):
            rel_dir = Path(dirpath).relative_to(root)

            # Exclude directories early
            pruned_dirnames = []
            for d in dirnames:
                full = str(rel_dir / d).replace("\\", "/")
                if any(fnmatch.fnmatch(full + "/", pattern) for pattern in exclude_globs):
                    continue
                pruned_dirnames.append(d)
            dirnames[:] = pruned_dirnames

            for f in filenames:
                rel = str((rel_dir / f)).replace("\\", "/")
                if any(fnmatch.fnmatch(rel, pattern) for pattern in exclude_globs):
                    continue
                if include_globs and not any(
                    fnmatch.fnmatch(rel, pattern) for pattern in include_globs
                ):
                    continue
                matched.append(str(root / rel))

        return matched


class ReadRepositoryFileInput(BaseModel):
    """Input for reading a single repository file via MCP provider or local FS."""

    file_path: str = Field(..., description="Absolute path to the file to read")
    start_line: Optional[int] = Field(
        default=None, description="Optional 1-based start line to slice the content"
    )
    end_line: Optional[int] = Field(
        default=None, description="Optional 1-based end line (inclusive) to slice the content"
    )


class ReadRepositoryFileTool(BaseTool):
    name: str = "read_repository_file"
    description: str = (
        "Read a file's content from the local filesystem. Can optionally slice by line numbers."
    )
    args_schema: Type[BaseModel] = ReadRepositoryFileInput

    def _run(
        self,
        file_path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> str:
        content: Optional[str] = None
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return ""

        if start_line is not None or end_line is not None:
            # 1-based slicing
            lines = content.splitlines()
            s = 1 if start_line is None else max(1, start_line)
            e = len(lines) if end_line is None else max(s, end_line)
            sliced = lines[s - 1 : e]
            return "\n".join(sliced)
        return content


