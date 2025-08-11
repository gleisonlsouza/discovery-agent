from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class BusinessRuleFileRef(BaseModel):
    path: str = Field(..., description="Caminho do arquivo onde a regra foi encontrada")
    code_snippet: str = Field(..., description="Trecho de código relevante para a regra")
    line_numbers: str = Field(..., description="Intervalo de linhas no formato 'Lx-Ly'")


class BusinessRule(BaseModel):
    rule: str = Field(..., description="Descrição da regra de negócio")
    files: List[BusinessRuleFileRef] = Field(
        default_factory=list, description="Referências de arquivos/snippets relacionados"
    )


class ModuleReport(BaseModel):
    name: str
    functional_domain: str
    business_rules: List[BusinessRule] = Field(default_factory=list)
    main_concepts: List[str] = Field(default_factory=list)
    relationships: List[str] = Field(default_factory=list)
    interactions: List[str] = Field(default_factory=list)


class MainEntity(BaseModel):
    name: str
    description: str


class ArchitectureRecommendation(BaseModel):
    type: str
    benefits: List[str] = Field(default_factory=list)


class TechnologyStack(BaseModel):
    backend: List[str] = Field(default_factory=list)
    frontend: List[str] = Field(default_factory=list)


class ModernizationSuggestion(BaseModel):
    modernization_overview: str
    architecture_recommendation: ArchitectureRecommendation
    technology_stack: TechnologyStack
    implementation_roadmap: List[str] = Field(default_factory=list)


class FinalAnalysisReport(BaseModel):
    summary: str
    modules: List[ModuleReport] = Field(default_factory=list)
    main_entities: List[MainEntity] = Field(default_factory=list)
    modernization_suggestion: ModernizationSuggestion


