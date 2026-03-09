import httpx
import respx


async def test_open_strategy_requires_site_id_when_creating_new(
    authed_client: httpx.AsyncClient,
) -> None:
    # When neither strategyId nor wdkStrategyId is provided, siteId is required.
    resp = await authed_client.post("/api/v1/strategies/open", json={})
    assert resp.status_code == 422


async def test_sync_wdk_deletes_internal_control_test_strategies(
    authed_client: httpx.AsyncClient, wdk_respx: respx.Router
) -> None:
    base = "https://plasmodb.org/plasmo/service"

    wdk_respx.get(f"{base}/users/current").respond(200, json={"id": "guest"})
    wdk_respx.get(f"{base}/users/guest/strategies").respond(
        200,
        json=[
            {
                "strategyId": 329824883,
                "name": "__pathfinder_internal__:Pathfinder control test",
                "isSaved": False,
            }
        ],
    )
    delete_route = wdk_respx.delete(f"{base}/users/guest/strategies/329824883").respond(
        204
    )

    resp = await authed_client.post(
        "/api/v1/strategies/sync-wdk", params={"siteId": "plasmodb"}
    )
    assert resp.status_code == 200, resp.text
    assert delete_route.called
