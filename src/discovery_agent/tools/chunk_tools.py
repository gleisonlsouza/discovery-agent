from __future__ import annotations

import os
from typing import Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class GetFileInfoInput(BaseModel):
    file_path: str = Field(..., description="Absolute path to the file")


class GetFileInfoTool(BaseTool):
    name: str = "get_file_info"
    description: str = (
        "Return basic file metadata including size in bytes and line count."
    )
    args_schema: Type[BaseModel] = GetFileInfoInput

    def _run(self, file_path: str) -> str:
        size_bytes = 0
        line_count = 0
        try:
            size_bytes = os.path.getsize(file_path)
            with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                for _ in fh:
                    line_count += 1
        except Exception:
            pass
        import json

        return json.dumps(
            {"path": file_path, "size_bytes": size_bytes, "line_count": line_count}
        )


class ReadFileChunkInput(BaseModel):
    file_path: str = Field(..., description="Absolute path to the file")
    start_line: int = Field(..., description="1-based start line")
    num_lines: int = Field(..., description="Number of lines to read from start_line")
    max_chars: Optional[int] = Field(
        default=4000, description="Max characters to return (truncate if exceeded)"
    )


class ReadFileChunkTool(BaseTool):
    name: str = "read_file_chunk"
    description: str = (
        "Read a slice of a file by line numbers, returning the snippet and actual end line."
    )
    args_schema: Type[BaseModel] = ReadFileChunkInput

    def _run(self, file_path: str, start_line: int, num_lines: int, max_chars: int | None = 4000) -> str:
        if start_line < 1:
            start_line = 1
        end_line = start_line + num_lines - 1
        content = ""
        actual_end = start_line - 1
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                for idx, line in enumerate(fh, start=1):
                    if idx < start_line:
                        continue
                    if idx > end_line:
                        break
                    content += line
                    actual_end = idx
        except Exception:
            pass

        if max_chars is not None and len(content) > max_chars:
            content = content[:max_chars]

        import json

        return json.dumps(
            {
                "path": file_path,
                "line_start": start_line,
                "line_end": actual_end,
                "code_snippet": content.strip(),
            }
        )


