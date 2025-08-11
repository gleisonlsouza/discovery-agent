from __future__ import annotations

import os
import re
from typing import List, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ScanApiContractsInput(BaseModel):
    repo_root: str = Field(..., description="Absolute path to repo root")
    include_globs: List[str] = Field(
        default_factory=lambda: [
            "**/*.yaml",
            "**/*.yml",
            "**/*.json",
            "**/*.graphql",
            "**/*.gql",
            "**/*.ts",
            "**/*.js",
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


class ApiContractScannerTool(BaseTool):
    name: str = "scan_api_contracts"
    description: str = (
        "Scan for OpenAPI/Swagger and GraphQL schemas and extract endpoints/operations hints."
    )
    args_schema: Type[BaseModel] = ScanApiContractsInput

    def _run(
        self,
        repo_root: str,
        include_globs: List[str] | None = None,
        exclude_globs: List[str] | None = None,
    ) -> str:
        include_globs = include_globs or []
        exclude_globs = exclude_globs or []

        from pathlib import Path
        import fnmatch

        root = Path(repo_root)
        matches: List[dict] = []

        # Heuristics
        openapi_key = re.compile(r"\bopenapi\s*:\s*\d|\bswagger\s*:\s*\d", re.IGNORECASE)
        openapi_path_entry_yaml = re.compile(r"^\s*/[^\s:]+\s*:\s*$", re.MULTILINE)
        openapi_path_entry_json = re.compile(r"\"/(?:[^\"]+)\"\s*:\s*\{", re.MULTILINE)
        graphql_type = re.compile(r"\b(type|input|enum|interface|union|scalar)\s+\w+\s*\{", re.IGNORECASE)
        graphql_op = re.compile(r"\b(query|mutation|subscription)\s+\w*\s*\(", re.IGNORECASE)
        gql_tag = re.compile(r"gql\s*`[\s\S]*?`", re.IGNORECASE)

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

                # OpenAPI YAML/JSON
                if rel.lower().endswith((".yaml", ".yml", ".json")) and openapi_key.search(content):
                    # extract a few path keys as hints
                    path_keys = set()
                    for m in openapi_path_entry_yaml.finditer(content):
                        key = m.group(0).strip().rstrip(":").strip()
                        path_keys.add(key)
                    for m in openapi_path_entry_json.finditer(content):
                        key = m.group(0)
                        # crude extraction of "/path"
                        key_str = key.split("\"")[1] if '"' in key else key
                        path_keys.add(key_str)

                    head = sorted(list(path_keys))[:50]
                    snippet = "\n".join(head)
                    line_start = 1
                    line_end = min(content.count("\n"), 200)
                    matches.append(
                        {
                            "path": abs_path,
                            "line_numbers": f"L{line_start}-{line_end}",
                            "category": "openapi_paths",
                            "code_snippet": snippet or content[:400],
                        }
                    )
                    continue

                # GraphQL schema or operations
                if rel.lower().endswith((".graphql", ".gql")) or graphql_type.search(content) or graphql_op.search(content) or gql_tag.search(content):
                    # extract first 400 chars around a type/op
                    m = graphql_type.search(content) or graphql_op.search(content) or gql_tag.search(content)
                    if m:
                        start = m.start()
                        line_start = content[:start].count("\n") + 1
                        snippet = content[max(0, start - 200) : m.end() + 200]
                        line_end = line_start + snippet.count("\n")
                        matches.append(
                            {
                                "path": abs_path,
                                "line_numbers": f"L{line_start}-{line_end}",
                                "category": "graphql_schema_or_operation",
                                "code_snippet": snippet.strip(),
                            }
                        )

        import json
        return json.dumps({"api_contract_matches": matches})


