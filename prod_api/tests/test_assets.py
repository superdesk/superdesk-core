from unittest.mock import AsyncMock, patch

import pytest

from superdesk.flask import url_for


async def test_assets_require_auth(prodapi_app, prodapi_client):
    async with prodapi_app.test_request_context("/"):
        response = await prodapi_client.get(url_for("assets.prod_get_upload_as_data_uri", media_id="missing"))

    assert response.status_code == 401


@pytest.mark.parametrize("issued_tokens", [(("ARCHIVE_READ",),)], indirect=True)
async def test_assets_use_archive_read_scope(issued_tokens, prodapi_app, prodapi_client):
    access_token = issued_tokens[0]["access_token"]
    with patch("prod_api.assets._get_upload_as_data_uri", new_callable=AsyncMock) as get_asset:
        get_asset.return_value = "asset response"

        async with prodapi_app.test_request_context("/"):
            response = await prodapi_client.get(
                url_for("assets.prod_get_upload_as_data_uri", media_id="asset-id"),
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert response.status_code == 200
    assert await response.get_data() == b"asset response"
    get_asset.assert_awaited_once_with("asset-id")


@pytest.mark.parametrize("issued_tokens", [(("DESKS_READ",),)], indirect=True)
async def test_assets_reject_other_scopes(issued_tokens, prodapi_app, prodapi_client):
    access_token = issued_tokens[0]["access_token"]

    async with prodapi_app.test_request_context("/"):
        response = await prodapi_client.get(
            url_for("assets.prod_get_upload_as_data_uri", media_id="asset-id"),
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 403
