"""Site listing, record types, and search catalog endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from veupath_chatbot.integrations.veupathdb.discovery import get_discovery_service
from veupath_chatbot.platform.errors import ErrorCode, NotFoundError
from veupath_chatbot.platform.types import JSONValue
from veupath_chatbot.services import catalog
from veupath_chatbot.transport.http.schemas import (
    RecordTypeResponse,
    SearchDetailsResponse,
    SearchResponse,
    SiteResponse,
)

router = APIRouter(prefix="/api/v1/sites", tags=["sites"])


@router.get("", response_model=list[SiteResponse])
async def list_sites() -> list[SiteResponse]:
    """List all available VEuPathDB sites."""
    sites = await catalog.list_sites()
    return [SiteResponse.model_validate(s) for s in sites if isinstance(s, dict)]


@router.get("/{siteId}", response_model=SiteResponse)
async def get_site(siteId: str) -> SiteResponse:
    """Get a single site by ID."""
    sites = await catalog.list_sites()
    for s in sites:
        if isinstance(s, dict) and s.get("id") == siteId:
            return SiteResponse.model_validate(s)
    raise NotFoundError(
        code=ErrorCode.SITE_NOT_FOUND,
        title="Site not found",
        detail=f"Unknown siteId '{siteId}'.",
    )


@router.get("/{siteId}/record-types", response_model=list[RecordTypeResponse])
async def get_record_types(siteId: str) -> list[RecordTypeResponse]:
    """Get record types available on a site."""
    record_types = await catalog.get_record_types(siteId)
    return [
        RecordTypeResponse.model_validate(rt)
        for rt in record_types
        if isinstance(rt, dict)
    ]


@router.get("/{siteId}/searches", response_model=list[SearchResponse])
async def get_searches(
    siteId: str,
    record_type: Annotated[str | None, Query(alias="recordType")] = None,
) -> list[SearchResponse]:
    """Get searches available on a site, optionally filtered by record type."""
    if record_type:
        searches = await catalog.list_searches(siteId, record_type)
        return [
            SearchResponse.model_validate({**s, "recordType": record_type})
            for s in searches
            if isinstance(s, dict)
        ]

    discovery = get_discovery_service()
    record_types = await discovery.get_record_types(siteId)
    all_searches: list[SearchResponse] = []

    for rt in record_types:
        if not isinstance(rt, dict):
            continue
        rt_url_seg_raw: JSONValue | None = rt.get("urlSegment")
        rt_name_raw: JSONValue | None = rt.get("name")
        url_seg = rt_url_seg_raw if isinstance(rt_url_seg_raw, str) else None
        name = rt_name_raw if isinstance(rt_name_raw, str) else None
        rt_name = url_seg or name or ""
        if rt_name:
            searches = await catalog.list_searches(siteId, rt_name)
            all_searches.extend(
                SearchResponse.model_validate({**s, "recordType": rt_name})
                for s in searches
                if isinstance(s, dict)
            )

    return all_searches


@router.get(
    "/{siteId}/searches/{recordType}/{searchName}", response_model=SearchDetailsResponse
)
async def get_search_details(
    siteId: str,
    recordType: str,
    searchName: str,
) -> SearchDetailsResponse:
    """Get detailed search configuration with parameters."""
    discovery = get_discovery_service()
    result = await discovery.get_search_details(siteId, recordType, searchName)
    return SearchDetailsResponse.model_validate(result)
