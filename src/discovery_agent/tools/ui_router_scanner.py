from __future__ import annotations

import os
import re
from typing import List, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ScanUIRoutesInput(BaseModel):
    repo_root: str = Field(..., description="Absolute path to repo root")
    include_globs: List[str] = Field(
        default_factory=lambda: ["**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx", "**/*.vue", "**/*.tsx"],
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
            "**/coverage/**",
            "**/*.spec.*",
            "**/*.test.*",
            "**/*.stories.*",
            "**/*.css",
            "**/*.scss",
            "**/*.sass",
        ],
        description="File globs to exclude",
    )


class UIRouterScannerTool(BaseTool):
    name: str = "scan_ui_routes"
    description: str = (
        "Scan front-end code for router definitions and route entries across Vue Router, React Router and Angular Router."
    )
    args_schema: Type[BaseModel] = ScanUIRoutesInput

    def _run(
        self,
        repo_root: str,
        include_globs: List[str] | None = None,
        exclude_globs: List[str] | None = None,
    ) -> str:
        include_globs = include_globs or []
        exclude_globs = exclude_globs or []

        # Heuristic regexes for typical router definitions/routes
        regexes = {
            # Vue Router
            "vue_router_create": re.compile(r"createRouter\s*\(.*?routes\s*:\s*\[", re.DOTALL),
            "vue_route_entry": re.compile(r"\bpath\s*:\s*['\"][^'\"]+['\"],\s*name\s*:\s*['\"][^'\"]+['\"]", re.DOTALL),
            # React Router v6
            "react_router_create": re.compile(r"create(Browser|Memory|Hash)Router\s*\(\s*\[", re.DOTALL),
            "react_route_entry": re.compile(r"\bpath\s*:\s*['\"][^'\"]+['\"]", re.DOTALL),
            "react_router_legacy": re.compile(r"<Route\s+path=", re.IGNORECASE),
            # Angular Router
            "angular_routes": re.compile(r"const\s+routes\s*:\s*Routes\s*=\s*\[", re.DOTALL),
            # Next.js (App Router / Pages) – hints of routing structure
            "next_app_router": re.compile(r"/app/.*(page|layout)\.(tsx?|jsx?)$"),
            "next_pages_router": re.compile(r"/pages/.*\.(tsx?|jsx?)$"),
            "next_link": re.compile(r"from\s+['\"]next/link['\"]|export\s+const\s+dynamic\s*=", re.DOTALL),
        }

        from pathlib import Path
        import fnmatch

        root = Path(repo_root)
        matches: List[dict] = []
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
                if include_globs and not any(fnmatch.fnmatch(rel, pat) for pat in include_globs):
                    continue
                if any(fnmatch.fnmatch(rel, pat) for pat in exclude_globs):
                    continue
                abs_path = str(root / rel)
                # For Next.js routing structure, we can detect by filepath alone
                if regexes["next_app_router"].search(rel) or regexes["next_pages_router"].search(rel):
                    matches.append(
                        {
                            "path": abs_path,
                            "line_numbers": "L1-1",
                            "category": "next_route_file",
                            "code_snippet": rel,
                        }
                    )

                try:
                    with open(abs_path, "r", encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                except Exception:
                    continue

                for key in [
                    "vue_router_create",
                    "vue_route_entry",
                    "react_router_create",
                    "react_route_entry",
                    "react_router_legacy",
                    "angular_routes",
                    "next_link",
                ]:
                    rx = regexes[key]
                    if rx.search(content):
                        first = rx.search(content)
                        if not first:
                            continue
                        start_char = first.start()
                        line_start = content[:start_char].count("\n") + 1
                        snippet = content[max(0, start_char - 200) : first.end() + 200]
                        line_end = line_start + snippet.count("\n")
                        matches.append(
                            {
                                "path": abs_path,
                                "line_numbers": f"L{line_start}-{line_end}",
                                "category": key,
                                "code_snippet": snippet.strip(),
                            }
                        )

        import json
        return json.dumps({"ui_route_matches": matches})


