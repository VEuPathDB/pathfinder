"""Deterministic mock chat stream for tests and E2E runs.

Matches the semantic event contract produced by ``stream_chat()``.
Moved here from ``services.chat.orchestrator`` to keep production code
free of test-only logic.
"""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

from veupath_chatbot.platform.types import JSONObject

# Real WDK organism values per VEuPathDB site (verified against live APIs).
_SITE_ORGANISMS: dict[str, str] = {
    "plasmodb": "Plasmodium falciparum 3D7",
    "toxodb": "Toxoplasma gondii ME49",
    "tritrypdb": "Leishmania major strain Friedlin",
    "cryptodb": "Cryptosporidium parvum Iowa II",
    "fungidb": "Aspergillus fumigatus Af293",
}


def _build_real_plan(site_id: str) -> JSONObject:
    """Build a planning artifact plan with *real* WDK search names.

    Uses ``GenesByTaxon`` which is available on every VEuPathDB site.
    The organism parameter matches the site so the strategy can be
    built against the real WDK API.
    """
    organism = _SITE_ORGANISMS.get(site_id, _SITE_ORGANISMS["plasmodb"])
    return {
        "recordType": "gene",
        "root": {
            "id": "step_1",
            "searchName": "GenesByTaxon",
            "displayName": f"All {organism} genes",
            "parameters": {"organism": f'["{organism}"]'},
        },
        "metadata": {"name": f"{organism} gene search"},
    }


async def mock_stream_chat(
    *,
    message: str,
    strategy_id: str | None = None,
    site_id: str | None = None,
) -> AsyncIterator[JSONObject]:
    """Deterministic, offline-friendly stream for tests/E2E runs.

    Matches the semantic event contract produced by ``stream_chat()``.
    """
    deltas = [
        "[mock] ",
        "I received your message: ",
        message,
    ]
    message_id = str(uuid4())
    for d in deltas:
        if "slow" in message.lower():
            await asyncio.sleep(0.2)
        yield {"type": "assistant_delta", "data": {"messageId": message_id, "delta": d}}

    msg_lower = message.lower()
    effective_site = site_id or "plasmodb"

    if "artifact graph" in msg_lower:
        now = datetime.now(UTC).isoformat()
        yield {
            "type": "planning_artifact",
            "data": {
                "planningArtifact": {
                    "id": "mock_exec_graph_artifact",
                    "title": "Mock graph artifact",
                    "summaryMarkdown": "A deterministic multi-step artifact for E2E graph interaction tests.",
                    "assumptions": [],
                    "parameters": {},
                    "proposedStrategyPlan": _build_real_plan(effective_site),
                    "createdAt": now,
                }
            },
        }
    elif "delegation draft" in msg_lower:
        now = datetime.now(UTC).isoformat()
        organism = _SITE_ORGANISMS.get(effective_site, _SITE_ORGANISMS["plasmodb"])
        yield {
            "type": "planning_artifact",
            "data": {
                "planningArtifact": {
                    "id": "delegation_draft",
                    "title": "Delegation draft",
                    "summaryMarkdown": "Build a gene strategy using an ortholog transform and a combine.",
                    "assumptions": [],
                    "parameters": {
                        "delegationGoal": "Build a gene strategy using an ortholog transform and a combine.",
                        "delegationPlan": {
                            "tasks": [
                                {
                                    "id": "task_search",
                                    "type": "search",
                                    "searchName": "GenesByTaxon",
                                    "context": f"Find genes in {organism}",
                                },
                                {
                                    "id": "task_transform",
                                    "type": "transform",
                                    "searchName": "GenesByOrthologPattern",
                                    "context": "Ortholog transform",
                                    "dependsOn": ["task_search"],
                                },
                                {
                                    "id": "task_combine",
                                    "type": "combine",
                                    "operator": "UNION",
                                    "context": "Combine search and transform",
                                    "dependsOn": ["task_search", "task_transform"],
                                },
                            ]
                        },
                    },
                    "createdAt": now,
                }
            },
        }
    elif "delegate_strategy_subtasks" in msg_lower or "delegation" in msg_lower:
        organism = _SITE_ORGANISMS.get(effective_site, _SITE_ORGANISMS["plasmodb"])
        yield {
            "type": "subkani_task_start",
            "data": {"task": "delegate:build-strategy"},
        }
        yield {
            "type": "subkani_tool_call_start",
            "data": {
                "task": "delegate:build-strategy",
                "id": "tc_delegate_1",
                "name": "search_for_searches",
                "arguments": '{"query":"ortholog transform","record_type":"gene","limit":3}',
            },
        }
        yield {
            "type": "subkani_tool_call_end",
            "data": {
                "task": "delegate:build-strategy",
                "id": "tc_delegate_1",
                "result": '{"rag":{"data":[],"note":""},"wdk":{"data":[],"note":"mock"}}',
            },
        }
        yield {
            "type": "subkani_task_end",
            "data": {"task": "delegate:build-strategy", "status": "done"},
        }

        gid = strategy_id or "mock_graph_delegation"
        yield {
            "type": "strategy_update",
            "data": {
                "graphId": gid,
                "step": {
                    "graphId": gid,
                    "stepId": "step_1",
                    "kind": "search",
                    "displayName": f"All {organism} genes",
                    "searchName": "GenesByTaxon",
                    "parameters": {"organism": f'["{organism}"]'},
                    "recordType": "gene",
                    "graphName": "Delegation-built strategy",
                    "description": "A deterministic delegated strategy for E2E.",
                },
            },
        }
        yield {
            "type": "strategy_update",
            "data": {
                "graphId": gid,
                "step": {
                    "graphId": gid,
                    "stepId": "step_2",
                    "kind": "transform",
                    "displayName": "Ortholog transform",
                    "searchName": "GenesByOrthologPattern",
                    "primaryInputStepId": "step_1",
                    "parameters": {},
                    "recordType": "gene",
                },
            },
        }
        yield {
            "type": "strategy_update",
            "data": {
                "graphId": gid,
                "step": {
                    "graphId": gid,
                    "stepId": "step_3",
                    "kind": "combine",
                    "displayName": "Combined results",
                    "operator": "UNION",
                    "primaryInputStepId": "step_2",
                    "secondaryInputStepId": "step_1",
                    "parameters": {},
                    "recordType": "gene",
                },
            },
        }

        yield {
            "type": "assistant_message",
            "data": {
                "messageId": message_id,
                "content": "[mock] Delegation complete. Built a multi-step strategy and emitted sub-kani activity.",
            },
        }
        yield {"type": "message_end", "data": {}}
        return

    yield {
        "type": "assistant_message",
        "data": {"messageId": message_id, "content": "".join(deltas)},
    }

    yield {"type": "message_end", "data": {}}
