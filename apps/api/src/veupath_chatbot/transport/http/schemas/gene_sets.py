"""HTTP request/response schemas for gene sets."""

from __future__ import annotations

from pydantic import BaseModel, Field

from veupath_chatbot.services.experiment.types.core import EnrichmentAnalysisType
from veupath_chatbot.services.gene_sets.types import GeneSetSource


class CreateGeneSetRequest(BaseModel):
    """Create a gene set from IDs, strategy, or upload."""

    name: str = Field(max_length=200)
    site_id: str = Field(alias="siteId")
    gene_ids: list[str] = Field(alias="geneIds")
    source: GeneSetSource = "paste"
    wdk_strategy_id: int | None = Field(None, alias="wdkStrategyId")
    wdk_step_id: int | None = Field(None, alias="wdkStepId")
    search_name: str | None = Field(None, alias="searchName")
    record_type: str | None = Field(None, alias="recordType")
    parameters: dict | None = None

    model_config = {"populate_by_name": True}


class GeneSetResponse(BaseModel):
    """Gene set response DTO."""

    id: str
    name: str
    site_id: str = Field(alias="siteId")
    gene_ids: list[str] = Field(alias="geneIds")
    source: GeneSetSource
    gene_count: int = Field(alias="geneCount")
    wdk_strategy_id: int | None = Field(None, alias="wdkStrategyId")
    wdk_step_id: int | None = Field(None, alias="wdkStepId")
    search_name: str | None = Field(None, alias="searchName")
    record_type: str | None = Field(None, alias="recordType")
    parameters: dict | None = None
    parent_set_ids: list[str] = Field(default_factory=list, alias="parentSetIds")
    operation: str | None = None
    created_at: str = Field(alias="createdAt")
    step_count: int = Field(1, alias="stepCount")

    model_config = {"populate_by_name": True}


class SetOperationRequest(BaseModel):
    """Perform set operations between two gene sets."""

    set_a_id: str = Field(alias="setAId")
    set_b_id: str = Field(alias="setBId")
    operation: str  # "intersect" | "union" | "minus"
    name: str = Field(max_length=200)

    model_config = {"populate_by_name": True}


class GeneSetEnrichRequest(BaseModel):
    """Run enrichment on a gene set."""

    enrichment_types: list[EnrichmentAnalysisType] = Field(alias="enrichmentTypes")

    model_config = {"populate_by_name": True}


class RunGeneSetAnalysisRequest(BaseModel):
    """Run a WDK step analysis on a gene set."""

    analysis_name: str = Field(alias="analysisName")
    parameters: dict = Field(default_factory=dict)

    model_config = {"populate_by_name": True}
