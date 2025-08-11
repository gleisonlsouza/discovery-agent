from __future__ import annotations

import os
import re
from typing import List, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ScanEndpointsInput(BaseModel):
    repo_root: str = Field(..., description="Absolute path to repo root")
    include_globs: List[str] = Field(
        default_factory=lambda: [
            "**/*.ts",
            "**/*.tsx",
            "**/*.js",
            "**/*.jsx",
            "**/*.py",
            "**/*.go",
            "**/*.java",
            "**/*.cs",
            "**/*.rb",
            "**/*.php",
            "**/*.yml",
            "**/*.yaml",
            "**/*.json",
            "**/.env*",
        ],
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
        ],
        description="File globs to exclude",
    )


class EndpointScannerTool(BaseTool):
    name: str = "scan_endpoints"
    description: str = (
        "Scan repository for external endpoints and client usage: axios/fetch, socket.io URLs, ws/wss, and raw http(s) URLs."
    )
    args_schema: Type[BaseModel] = ScanEndpointsInput

    def _run(
        self,
        repo_root: str,
        include_globs: List[str] | None = None,
        exclude_globs: List[str] | None = None,
    ) -> str:
        include_globs = include_globs or []
        exclude_globs = exclude_globs or []

        # Patterns
        patterns = {
            # Raw URLs
            "http_url": re.compile(r"https?://[\w\.-:/?#%=&]+", re.IGNORECASE),
            # fetch('https://...') and fetch(`https://...`)
            "fetch_literal": re.compile(r"\bfetch\s*\(\s*['\"](https?://[^'\"]+)['\"]", re.IGNORECASE),
            "fetch_tmpl": re.compile(r"\bfetch\s*\(\s*`(https?://[^`]+)`", re.IGNORECASE),
            # axios
            "axios_create": re.compile(r"axios\.create\s*\(\s*\{[^}]*baseURL\s*:\s*['\"](.*?)['\"]", re.IGNORECASE | re.DOTALL),
            "axios_call_literal": re.compile(r"axios\.(get|post|put|delete|patch)\s*\(\s*['\"](https?://[^'\"]+)['\"]", re.IGNORECASE),
            "axios_call_tmpl": re.compile(r"axios\.(get|post|put|delete|patch)\s*\(\s*`(https?://[^`]+)`", re.IGNORECASE),
            # got
            "got_literal": re.compile(r"\bgot\s*\(\s*['\"](https?://[^'\"]+)['\"]", re.IGNORECASE),
            # GraphQL endpoint URLs in fetch/axios/got bodies
            "graphql_http": re.compile(r"/graphql(\?|$)", re.IGNORECASE),
            # WebSocket / Socket.IO
            "socket_io": re.compile(r"io\s*\(\s*['\"](ws[s]?:|https?://)[^'\"]+['\"]", re.IGNORECASE),
            "websocket_new": re.compile(r"new\s+WebSocket\s*\(\s*['\"](ws[s]?://[^'\"]+)['\"]", re.IGNORECASE),
            # Env-like URLs
            "env_url": re.compile(r"(URL|ENDPOINT|BASE_URL|SOCKET_URL|WS_URL)\s*=\s*['\"](https?|ws)[^'\"]+['\"]", re.IGNORECASE),
        }

        from pathlib import Path
        import fnmatch

        root = Path(repo_root)
        results: List[dict] = []

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
                try:
                    with open(abs_path, "r", encoding="utf-8", errors="ignore") as fh:
                        lines = fh.readlines()
                except Exception:
                    continue

                for idx, line in enumerate(lines, start=1):
                    for key, regex in patterns.items():
                        for m in regex.finditer(line):
                            url = m.group(1) if m.groups() else m.group(0)
                            results.append(
                                {
                                    "path": abs_path,
                                    "line_numbers": f"L{idx}-{idx}",
                                    "category": key,
                                    "value": url,
                                    "code_snippet": line.strip(),
                                }
                            )

        import json
        return json.dumps({"endpoint_matches": results})


