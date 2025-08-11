from __future__ import annotations

import os
import re
from typing import List, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ScanValidatorsInput(BaseModel):
    repo_root: str = Field(..., description="Absolute path to repo root")
    include_globs: List[str] = Field(
        default_factory=lambda: [
            "**/*.ts",
            "**/*.tsx",
            "**/*.js",
            "**/*.jsx",
            "**/*.py",
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
            "**/*.spec.*",
            "**/*.test.*",
        ],
        description="File globs to exclude",
    )


class ValidatorScannerTool(BaseTool):
    name: str = "scan_validators"
    description: str = (
        "Scan repository for validation rules (Zod/Yup/Joi/Pydantic) to surface candidate business rules and constraints."
    )
    args_schema: Type[BaseModel] = ScanValidatorsInput

    def _run(
        self,
        repo_root: str,
        include_globs: List[str] | None = None,
        exclude_globs: List[str] | None = None,
    ) -> str:
        include_globs = include_globs or []
        exclude_globs = exclude_globs or []

        # Heuristic regex for common validation libraries
        patterns = {
            # Zod
            "zod_schema": re.compile(r"\bz\.(object|string|number|boolean|array|enum|union|literal)\(", re.IGNORECASE),
            "zod_rule": re.compile(r"\.min\(|\.max\(|\.regex\(|\.length\(|\.email\(\)|\.url\(\)|\.nonempty\(\)", re.IGNORECASE),
            "zod_refine": re.compile(r"\.refine\(", re.IGNORECASE),
            # Yup
            "yup_schema": re.compile(r"\byup\.(object|string|number|bool|array|mixed)\(\)", re.IGNORECASE),
            "yup_rule": re.compile(r"\.required\(\)|\.min\(|\.max\(|\.matches\(|\.email\(\)|\.url\(\)", re.IGNORECASE),
            # Joi
            "joi_schema": re.compile(r"\bJoi\.(object|string|number|boolean|array)\(\)", re.IGNORECASE),
            "joi_rule": re.compile(r"\.min\(|\.max\(|\.regex\(|\.pattern\(|\.required\(\)", re.IGNORECASE),
            # Pydantic
            "pydantic_model": re.compile(r"class\s+\w+\(BaseModel\):"),
            "pydantic_field": re.compile(r"\bField\s*\(.*?(ge|gt|le|lt|min_length|max_length|regex)\s*=\s*", re.IGNORECASE),
            "pydantic_validator": re.compile(r"@validator\(\w*\)", re.IGNORECASE),
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
                if any(fnmatch.fnmatch(full + "/", pat) for pat in exclude_globs):
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
                        content = fh.read()
                except Exception:
                    continue

                for key, rx in patterns.items():
                    for m in rx.finditer(content):
                        start = m.start()
                        line_start = content[:start].count("\n") + 1
                        snippet = content[max(0, start - 160) : m.end() + 160]
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
        return json.dumps({"validator_matches": matches})


