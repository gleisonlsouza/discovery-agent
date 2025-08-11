from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from .search_repo_patterns import SearchRepoPatternsTool


class RobustSearchInput(BaseModel):
    payload: str = Field(
        ...,
        description=(
            "Raw string payload. Can be a JSON object or array as string. "
            "Expected to contain a JSON object with keys {repo_root, patterns, include_globs?, exclude_globs?, max_matches_per_file?, context_lines?, max_files?}."
        ),
    )


class RobustSearchRepoPatternsTool(BaseTool):
    name: str = "robust_search_repo_patterns"
    description: str = (
        "Lenient search that accepts messy payloads (array or stringified JSON) and extracts the first valid config for search_repo_patterns. "
        "Usage: pass ANY content under {payload: ""...""}. The tool will parse and sanitize before searching."
    )
    args_schema: Type[BaseModel] = RobustSearchInput

    def _try_parse(self, payload: str) -> Optional[Dict[str, Any]]:
        try:
            data = json.loads(payload)
        except Exception:
            return None

        # Single object case
        if isinstance(data, dict) and "repo_root" in data and "patterns" in data:
            return data

        # Array case: find first dict with needed keys
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "repo_root" in item and "patterns" in item:
                    return item
        return None

    def _heuristic_extract(self, payload: str) -> Dict[str, Any]:
        # Try to find a path-like token
        path_match = re.search(r"[A-Za-z]:\\\\[^\"\n]+|/[^\"\n\s]+", payload)
        repo_root = path_match.group(0) if path_match else "."
        # Default patterns if not found
        patterns = [
            r"export default",
            r"export const",
            r"export function",
            r"class\\s+\\w+",
            r"def\\s+\\w+\\(",
        ]
        return {"repo_root": repo_root, "patterns": patterns}

    def _run(self, payload: str) -> str:
        cfg = self._try_parse(payload)
        if cfg is None:
            cfg = self._heuristic_extract(payload)

        repo_root = cfg.get("repo_root", ".")
        patterns = cfg.get("patterns", [])
        include_globs = cfg.get("include_globs")
        exclude_globs = cfg.get("exclude_globs")
        max_matches_per_file = cfg.get("max_matches_per_file", 5)
        context_lines = cfg.get("context_lines", 2)
        max_files = cfg.get("max_files", 2000)

        # Delegate to the strict tool
        inner = SearchRepoPatternsTool()
        return inner._run(
            repo_root=repo_root,
            patterns=patterns,
            include_globs=include_globs,
            exclude_globs=exclude_globs,
            max_matches_per_file=max_matches_per_file,
            context_lines=context_lines,
            max_files=max_files,
        )


