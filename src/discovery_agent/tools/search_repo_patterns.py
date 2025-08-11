from __future__ import annotations

import os
import re
from typing import List, Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class SearchRepoPatternsInput(BaseModel):
    repo_root: str = Field(..., description="Absolute path to repo root")
    patterns: List[str] = Field(
        default_factory=list, description="Regex patterns to search for"
    )
    include_globs: List[str] = Field(
        default_factory=lambda: ["**/*.py", "**/*.ts", "**/*.js", "**/*.go", "**/*.java", "**/*.cs", "**/*.rb"],
        description="File globs to include",
    )
    exclude_globs: List[str] = Field(
        default_factory=lambda: [
            "**/.git/**",
            "**/node_modules/**",
            "**/.venv/**",
            "**/dist/**",
            "**/build/**",
            "**/.next/**",
        ],
        description="File globs to exclude",
    )
    max_matches_per_file: int = Field(
        default=5, description="Maximum matches returned per file"
    )
    context_lines: int = Field(
        default=2, description="Number of context lines around the match"
    )
    max_files: int = Field(
        default=2000, description="Cap the number of files to scan to reduce tokens"
    )


class SearchRepoPatternsTool(BaseTool):
    name: str = "search_repo_patterns"
    description: str = (
        "Search repository files for regex patterns and return compact snippets with line ranges. "
        "Use to find candidate code for modules, entities and business rules, minimizing tokens. "
        "Action Input MUST be a JSON object with keys: {repo_root, patterns, include_globs?, exclude_globs?, max_matches_per_file?, context_lines?, max_files?}. "
        "Example: {\"repo_root\": \"/abs/path\", \"patterns\": [\"class \\w+\"], \"include_globs\": [\"**/*.ts\"]}."
    )
    args_schema: Type[BaseModel] = SearchRepoPatternsInput

    def _run(
        self,
        repo_root: str,
        patterns: List[str],
        include_globs: List[str] | None = None,
        exclude_globs: List[str] | None = None,
        max_matches_per_file: int = 5,
        context_lines: int = 2,
        max_files: int = 2000,
    ) -> str:
        # Use a comprehensive default set of languages to avoid missing candidates
        include_globs = include_globs or [
            "**/*.py",
            "**/*.ts",
            "**/*.tsx",
            "**/*.js",
            "**/*.jsx",
            "**/*.go",
            "**/*.java",
            "**/*.cs",
            "**/*.rb",
            "**/*.php",
            "**/*.kt",
            "**/*.scala",
        ]
        exclude_globs = exclude_globs or [
            "**/.git/**",
            "**/node_modules/**",
            "**/.venv/**",
            "**/dist/**",
            "**/build/**",
            "**/.next/**",
            "**/coverage/**",
        ]
        compiled = [re.compile(p) for p in patterns if p]
        if not compiled:
            import json
            return json.dumps({"matches": []})

        from pathlib import Path
        import fnmatch

        root = Path(repo_root)
        results: List[dict] = []
        file_count = 0
        for dirpath, dirnames, filenames in os.walk(root):
            rel_dir = Path(dirpath).relative_to(root)
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
                abs_path = str(root / rel)
                file_count += 1
                if file_count > max_files:
                    break
                try:
                    with open(abs_path, "r", encoding="utf-8", errors="ignore") as fh:
                        lines = fh.readlines()
                except Exception:
                    continue
                matches_in_file = 0
                for idx, line in enumerate(lines, start=1):
                    for creg in compiled:
                        if creg.search(line):
                            start = max(1, idx - context_lines)
                            end = min(len(lines), idx + context_lines)
                            snippet = "".join(lines[start - 1 : end]).strip()
                            results.append(
                                {
                                    "path": abs_path,
                                    "line_start": start,
                                    "line_end": end,
                                    "code_snippet": snippet,
                                }
                            )
                            matches_in_file += 1
                            if matches_in_file >= max_matches_per_file:
                                break
                    if matches_in_file >= max_matches_per_file:
                        break
            if file_count > max_files:
                break

        import json

        return json.dumps({"matches": results})


