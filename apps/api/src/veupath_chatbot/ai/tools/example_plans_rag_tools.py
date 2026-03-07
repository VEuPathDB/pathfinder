"""AI tools for retrieving example plans from Qdrant.

Thin delegation layer — all logic lives in ``services.catalog.rag_search``.
"""

from veupath_chatbot.platform.types import JSONArray
from veupath_chatbot.services.catalog.rag_search import RagSearchService


class ExamplePlansRagTools:
    def __init__(self, *, site_id: str) -> None:
        self.site_id = site_id
        self._svc = RagSearchService(site_id=site_id)

    async def rag_search_example_plans(
        self,
        query: str,
        limit: int = 5,
    ) -> JSONArray:
        return await self._svc.search_example_plans(query=query, limit=limit)
