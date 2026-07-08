"""Unit tests for Spreadconnect catalog normalization."""

from unittest.mock import AsyncMock

import pytest

from app.addons.suppliers.spreadconnect.addon import SpreadconnectAddon
from app.addons.suppliers.spreadconnect.catalog import normalize_spreadconnect_catalog


def test_spreadconnect_variant_keys():
    items = normalize_spreadconnect_catalog(
        [{"id": "10", "name": "Hoodie", "variants": [{"id": "20", "size": "M"}]}]
    )
    assert items[0].external_key == "spreadconnect:10:20"
    assert items[0].supplier_variant_id == "20"


def test_spreadconnect_sizes_normalize_to_variants():
    items = normalize_spreadconnect_catalog(
        [{"id": "10", "name": "Hoodie", "sizes": [{"id": "30", "name": "L"}]}]
    )
    assert len(items) == 1
    assert items[0].external_key == "spreadconnect:10:30"
    assert items[0].supplier_variant_id == "30"
    assert items[0].skip_reason is None


def test_spreadconnect_type_without_sizes_is_skipped():
    items = normalize_spreadconnect_catalog([{"id": "10", "name": "Hoodie"}])
    assert len(items) == 1
    assert items[0].skip_reason == "Spreadconnect product type has no sizes"
    assert items[0].supplier_variant_id == ""


@pytest.mark.asyncio
async def test_fetch_catalog_expands_product_types_missing_sizes():
    addon = SpreadconnectAddon()
    addon._client = AsyncMock()
    addon._config = {"api_key": "key", "is_active": True}
    addon._client.list_product_types.return_value = [{"id": "10", "name": "Hoodie"}]
    addon._client.get_product_type.return_value = {
        "id": "10",
        "name": "Hoodie",
        "sizes": [{"id": "20", "size": "M"}],
    }
    addon._client.list_stocks.return_value = []

    items = await addon.fetch_catalog_for_import()

    addon._client.get_product_type.assert_awaited_once_with("10")
    importable_variants = [
        variant for product in items for variant in product.variants if not variant.skip_reason
    ]
    assert len(importable_variants) == 1
    assert importable_variants[0].supplier_variant_id == "20"
