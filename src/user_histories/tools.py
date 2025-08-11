from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ReadAnalysisJSONInput(BaseModel):
    analysis_path: str = Field(..., description="Path to analysis.json file")


class ReadAnalysisJSONTool(BaseTool):
    name: str = "read_analysis_json"
    description: str = (
        "Read the analysis.json and return its JSON content as string. "
        "If the file does not exist or is invalid JSON, return an empty JSON string '{}'."
    )
    args_schema: Type[BaseModel] = ReadAnalysisJSONInput

    def _run(self, analysis_path: str) -> str:
        p = Path(analysis_path)
        if not p.exists():
            return "{}"
        try:
            return p.read_text(encoding="utf-8")
        except Exception:
            return "{}"


class WriteMarkdownInput(BaseModel):
    output_dir: str = Field(..., description="Directory to write markdown files into")
    filename: str = Field(..., description="Target filename (without path)")
    content: str = Field(..., description="Markdown content to write")


class WriteMarkdownTool(BaseTool):
    name: str = "write_markdown_file"
    description: str = "Write a markdown file to disk"
    args_schema: Type[BaseModel] = WriteMarkdownInput

    def _run(self, output_dir: str, filename: str, content: str) -> str:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / filename
        path.write_text(content, encoding="utf-8")
        return str(path)


# ---- Gherkin story generator ----

class GenerateGherkinStoriesInput(BaseModel):
    analysis_path: str = Field(..., description="Path to analysis.json file")
    output_dir: str = Field(..., description="Directory to write markdown files into")
    group_by_persona: bool = Field(
        default=True, description="If true, create subdirectories per persona"
    )
    strict_mode: bool = Field(
        default=True,
        description=(
            "If true, do not invent scenarios beyond business rules. Steps will be generic to avoid assumptions."
        ),
    )


class GenerateGherkinStoriesTool(BaseTool):
    name: str = "generate_gherkin_stories"
    description: str = (
        "Generate Gherkin user stories (.md) strictly from business rules present in analysis.json. "
        "Separates files by persona and module. Returns JSON list of written file paths."
    )
    args_schema: Type[BaseModel] = GenerateGherkinStoriesInput

    def _detect_persona(self, rule_text: str) -> str:
        text = rule_text.lower()
        if any(k in text for k in ["admin", "administrador", "moderador", "operador"]):
            return "Administrador"
        if any(k in text for k in ["jogador", "player"]):
            return "Jogador"
        if any(k in text for k in ["sistema", "api", "serviço", "servico"]):
            return "Sistema"
        if any(k in text for k in ["usuário", "usuario", "user"]):
            return "Usuário"
        return "Usuário"

    def _sanitize_filename(self, name: str) -> str:
        safe = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_"))
        return safe.strip().replace(" ", "_") or "module"

    def _run(self, analysis_path: str, output_dir: str, group_by_persona: bool = True, strict_mode: bool = True) -> str:
        p = Path(analysis_path)
        if not p.exists():
            return json.dumps({"written": [], "error": f"analysis.json não encontrado ou inválido em {analysis_path}"})
        try:
            analysis = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            return json.dumps({"written": [], "error": f"analysis.json não encontrado ou inválido em {analysis_path}"})

        modules = analysis.get("modules", [])
        written: List[str] = []

        for module in modules:
            module_name = module.get("name", "Module")
            functional_domain = module.get("functional_domain", "")
            business_rules = module.get("business_rules", [])
            # Group rules by persona
            persona_to_rules: Dict[str, List[dict]] = {}
            for br in business_rules:
                rule_text = br.get("rule", "")
                persona = self._detect_persona(rule_text)
                persona_to_rules.setdefault(persona, []).append(br)

            for persona, rules in persona_to_rules.items():
                # Compose content
                lines: List[str] = []
                lines.append(f"Feature: {module_name} ({functional_domain})")
                lines.append("")
                lines.append(f"# Persona: {persona}")
                lines.append("")
                for idx, br in enumerate(rules, start=1):
                    title = br.get("rule", "Regra")
                    files = br.get("files", [])
                    lines.append(f"Scenario: {title}")
                    # Strict mode: generic steps to avoid inventing details
                    lines.append("  Given uma situação relevante para a regra")
                    lines.append("  When a condição descrita na regra ocorre")
                    lines.append(f"  Then {title}")
                    # Traceability comments
                    for fref in files:
                        path = fref.get("path", "")
                        ln = fref.get("line_numbers", "")
                        lines.append(f"  # evidence: {path} {ln}")
                    lines.append("")

                # Write file
                base_dir = Path(output_dir)
                if group_by_persona:
                    base_dir = base_dir / persona
                base_dir.mkdir(parents=True, exist_ok=True)
                filename = f"{self._sanitize_filename(module_name)}.md"
                filepath = base_dir / filename
                filepath.write_text("\n".join(lines), encoding="utf-8")
                written.append(str(filepath))

        return json.dumps({"written": written})

