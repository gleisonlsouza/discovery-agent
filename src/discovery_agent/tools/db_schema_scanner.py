from __future__ import annotations

import os
import re
from typing import List, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ScanDbSchemaInput(BaseModel):
    repo_root: str = Field(..., description="Absolute path to repo root")
    include_globs: List[str] = Field(
        default_factory=lambda: [
            "**/*.prisma",
            "**/*.sql",
            "**/*.ts",
            "**/*.js",
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


class DbSchemaScannerTool(BaseTool):
    name: str = "scan_db_schema"
    description: str = (
        "Scan repository for database or ORM schema definitions (Prisma/TypeORM/Sequelize/SQLAlchemy/SQL) to infer entities and relations."
    )
    args_schema: Type[BaseModel] = ScanDbSchemaInput

    def _run(
        self,
        repo_root: str,
        include_globs: List[str] | None = None,
        exclude_globs: List[str] | None = None,
    ) -> str:
        include_globs = include_globs or []
        exclude_globs = exclude_globs or []

        patterns = {
            # Prisma models
            "prisma_model": re.compile(r"\bmodel\s+\w+\s*\{", re.IGNORECASE),
            # TypeORM decorators
            "typeorm_entity": re.compile(r"@Entity\(.*?\)\s*export\s+class\s+\w+", re.DOTALL),
            "typeorm_relation": re.compile(r"@(OneToOne|OneToMany|ManyToOne|ManyToMany)\(", re.IGNORECASE),
            # Sequelize define
            "sequelize_define": re.compile(r"sequelize\.define\s*\(\s*['\"]\w+['\"]", re.IGNORECASE),
            # SQLAlchemy declarative
            "sqlalchemy_model": re.compile(r"class\s+\w+\(Base\):\s*\n\s*__tablename__\s*=\s*['\"]\w+['\"]", re.IGNORECASE),
            # SQL DDL
            "sql_create_table": re.compile(r"CREATE\s+TABLE\s+\w+\s*\(", re.IGNORECASE),
            "sql_foreign_key": re.compile(r"FOREIGN\s+KEY|REFERENCES\s+\w+", re.IGNORECASE),
            # Django models
            "django_model": re.compile(r"class\s+\w+\(models\.Model\):"),
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
        return json.dumps({"db_schema_matches": matches})


