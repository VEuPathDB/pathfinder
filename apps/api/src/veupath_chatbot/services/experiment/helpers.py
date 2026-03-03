"""Shared helpers for experiment execution and analysis.

Provides gene-list extraction utilities and the progress callback type alias.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from veupath_chatbot.platform.logging import get_logger
from veupath_chatbot.platform.types import JSONObject
from veupath_chatbot.services.experiment.types import GeneInfo

logger = get_logger(__name__)

ProgressCallback = Callable[[JSONObject], Awaitable[None]]
"""Emits an SSE-friendly progress event dict."""


def safe_int(val: object, default: int = 0) -> int:
    """Safely convert a value to int, returning *default* on failure."""
    if isinstance(val, int):
        return val
    if isinstance(val, (float, str)):
        try:
            return int(float(val))
        except ValueError, TypeError:
            pass
    return default


def safe_float(val: object, default: float = 0.0) -> float:
    """Safely convert a value to float, returning *default* on failure."""
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val)
        except ValueError:
            pass
    return default


def coerce_step_id(payload: JSONObject | None) -> int:
    """Extract step ID from a WDK step-creation response.

    WDK ``StepFormatter`` emits the step ID under ``JsonKeys.ID = "id"``
    as a Java long (always int in JSON).

    :param payload: WDK step-creation response.
    :returns: Step ID.
    :raises ValueError: If step ID not found.
    """
    if isinstance(payload, dict):
        raw = payload.get("id")
        if isinstance(raw, int):
            return raw
    raise ValueError("Failed to extract step ID from WDK response")


def _extract_gene_list(
    result: JSONObject,
    section: str,
    key: str,
    *,
    fallback_from_controls: bool = False,
    all_controls: list[str] | None = None,
    hit_ids: set[str] | None = None,
) -> list[GeneInfo]:
    """Extract a gene ID list from control-test result and wrap as GeneInfo."""
    section_data = result.get(section)
    if not isinstance(section_data, dict):
        if fallback_from_controls and all_controls and hit_ids is not None:
            return [GeneInfo(id=g) for g in all_controls if g not in hit_ids]
        return []

    ids_raw = section_data.get(key)
    if isinstance(ids_raw, list):
        return [GeneInfo(id=str(g)) for g in ids_raw if g is not None]

    if fallback_from_controls and all_controls and hit_ids is not None:
        return [GeneInfo(id=g) for g in all_controls if g not in hit_ids]
    return []


def _extract_id_set(
    result: JSONObject,
    section: str,
    key: str,
) -> set[str]:
    """Extract a set of IDs from a control-test result section."""
    section_data = result.get(section)
    if not isinstance(section_data, dict):
        return set()
    ids_raw = section_data.get(key)
    if isinstance(ids_raw, list):
        return {str(g) for g in ids_raw if g is not None}
    return set()


def _enrich_list(
    genes: list[GeneInfo],
    lookup: dict[str, JSONObject],
) -> list[GeneInfo]:
    """Replace bare GeneInfo objects with enriched versions from *lookup*."""
    enriched: list[GeneInfo] = []
    for g in genes:
        meta = lookup.get(g.id)
        if meta:
            enriched.append(
                GeneInfo(
                    id=g.id,
                    name=str(meta.get("geneName", "")) or g.name,
                    organism=str(meta.get("organism", "")) or g.organism,
                    product=str(meta.get("product", "")) or g.product,
                )
            )
        else:
            enriched.append(g)
    return enriched


async def _resolve_gene_lookup(
    site_id: str,
    gene_lists: tuple[list[GeneInfo], ...],
) -> dict[str, JSONObject]:
    """Resolve all unique gene IDs across multiple lists into a lookup dict."""
    from veupath_chatbot.services.gene_lookup.wdk import resolve_gene_ids

    all_ids: list[str] = []
    seen: set[str] = set()
    for gl in gene_lists:
        for g in gl:
            if g.id not in seen:
                all_ids.append(g.id)
                seen.add(g.id)

    if not all_ids:
        return {}

    resolved = await resolve_gene_ids(site_id=site_id, gene_ids=all_ids)
    records = resolved.get("records")
    if not isinstance(records, list):
        return {}

    lookup: dict[str, JSONObject] = {}
    for rec in records:
        if isinstance(rec, dict):
            gid = rec.get("geneId")
            if isinstance(gid, str):
                lookup[gid] = rec
    return lookup


async def extract_and_enrich_genes(
    *,
    site_id: str,
    result: JSONObject,
    negative_controls: list[str] | None = None,
) -> tuple[list[GeneInfo], list[GeneInfo], list[GeneInfo], list[GeneInfo]]:
    """Extract gene lists from a control-test result and enrich with WDK metadata.

    Single entry point that replaces duplicated extract + enrich blocks.

    :returns: (true_positive, false_negative, false_positive, true_negative)
    """
    tp = _extract_gene_list(result, "positive", "intersectionIds")
    fn = _extract_gene_list(result, "positive", "missingIdsSample")
    fp = _extract_gene_list(result, "negative", "intersectionIds")
    tn = _extract_gene_list(
        result,
        "negative",
        "missingIdsSample",
        fallback_from_controls=True,
        all_controls=negative_controls,
        hit_ids=_extract_id_set(result, "negative", "intersectionIds"),
    )

    try:
        lookup = await _resolve_gene_lookup(site_id, (tp, fn, fp, tn))
    except Exception as exc:
        logger.warning("Gene enrichment failed, returning bare IDs", error=str(exc))
        return tp, fn, fp, tn

    if lookup:
        tp = _enrich_list(tp, lookup)
        fn = _enrich_list(fn, lookup)
        fp = _enrich_list(fp, lookup)
        tn = _enrich_list(tn, lookup)

    return tp, fn, fp, tn
