from __future__ import annotations

import os
import re
from typing import List, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ScanVisualIdentityInput(BaseModel):
    repo_root: str = Field(..., description="Absolute path to repo root")
    include_globs: List[str] = Field(
        default_factory=lambda: [
            "**/*.css",
            "**/*.scss",
            "**/*.sass",
            "**/*.less",
            "**/*.ts",
            "**/*.js",
            "**/*.tsx",
            "**/*.jsx",
            "**/tailwind.config.*",
            "**/theme.*",
            "**/*.svg",
            "**/*.png",
            "**/*.jpg",
            "**/*.jpeg",
            "**/*.ico",
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


class VisualIdentityScannerTool(BaseTool):
    name: str = "scan_visual_identity"
    description: str = (
        "Scan repository for visual identity hints: CSS frameworks, theme tokens (colors/fonts), variables, and brand assets (logo/favicon)."
    )
    args_schema: Type[BaseModel] = ScanVisualIdentityInput

    def _run(
        self,
        repo_root: str,
        include_globs: List[str] | None = None,
        exclude_globs: List[str] | None = None,
    ) -> str:
        include_globs = include_globs or []
        exclude_globs = exclude_globs or []

        framework_patterns = [
            ("tailwind", re.compile(r"tailwind\.config\.(js|ts)", re.IGNORECASE)),
            ("bootstrap", re.compile(r"bootstrap(\.min)?\.css|@import\s+['\"]bootstrap", re.IGNORECASE)),
            ("material", re.compile(r"@mui|material(-ui)?|@angular/material", re.IGNORECASE)),
            ("chakra", re.compile(r"@chakra-ui/|extendTheme\(", re.IGNORECASE)),
            ("ant-design", re.compile(r"antd|ant-design", re.IGNORECASE)),
        ]

        token_patterns = {
            "css_var": re.compile(r"--[a-z0-9\-_]+\s*:\s*[^;]+;", re.IGNORECASE),
            "scss_var": re.compile(r"\$[a-z0-9\-_]+\s*:\s*[^;]+;", re.IGNORECASE),
            "font_face": re.compile(r"@font-face|font-family\s*:\s*", re.IGNORECASE),
            "color_hex": re.compile(r"#[0-9a-fA-F]{3,8}", re.IGNORECASE),
        }

        asset_name_patterns = re.compile(r"logo|brand|favicon|icon|logo-?\w*", re.IGNORECASE)

        from pathlib import Path
        import fnmatch

        root = Path(repo_root)
        frameworks: List[dict] = []
        tokens: List[dict] = []
        assets: List[dict] = []

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

                # Framework hits by filename/content hints
                for fw_name, fw_rx in framework_patterns:
                    if fw_rx.search(rel):
                        frameworks.append(
                            {
                                "framework": fw_name,
                                "path": abs_path,
                                "line_numbers": "L1-1",
                                "code_snippet": rel,
                            }
                        )

                # Assets
                if asset_name_patterns.search(f):
                    assets.append(
                        {
                            "path": abs_path,
                            "line_numbers": "L1-1",
                            "code_snippet": f,
                        }
                    )

                # Open and scan for tokens if text file
                try:
                    with open(abs_path, "r", encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                except Exception:
                    continue

                for key, rx in token_patterns.items():
                    for m in rx.finditer(content):
                        start = m.start()
                        line_start = content[:start].count("\n") + 1
                        snippet = content[max(0, start - 120) : m.end() + 120]
                        line_end = line_start + snippet.count("\n")
                        tokens.append(
                            {
                                "type": key,
                                "path": abs_path,
                                "line_numbers": f"L{line_start}-{line_end}",
                                "code_snippet": snippet.strip(),
                            }
                        )

        import json
        return json.dumps({
            "visual_identity": {
                "frameworks": frameworks,
                "tokens": tokens,
                "assets": assets,
            }
        })


