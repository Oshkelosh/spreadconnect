"""Spreadconnect (SPOD) print-on-demand supplier integration."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel, Field, SecretStr

from app.addons.suppliers.base import SupplierAddon
from app.addons.suppliers.catalog_utils import row_lacks_variant_list
from app.addons.suppliers.spreadconnect.catalog import normalize_spreadconnect_catalog_products
from app.addons.suppliers.spreadconnect.client import SpreadconnectAPIError, SpreadconnectClient
from schemas.supplier import SupplierCatalogProduct
from app.addons.log import info, warning
from app.addons.config_serialization import dump_addon_config


class SpreadconnectConfig(BaseModel):
    api_key: SecretStr = Field(default=..., description="Spreadconnect API key")
    is_active: bool = Field(default=False)
    use_staging: bool = Field(default=False)
    auto_confirm: bool = Field(default=True)

    @classmethod
    def config_model(cls):
        return cls


def _map_address(address: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "firstName": address.get("first_name", ""),
        "lastName": address.get("last_name", ""),
        "street": address.get("line1", ""),
        "city": address.get("city", ""),
        "zipCode": address.get("zip", ""),
        "country": address.get("country", ""),
        "email": address.get("email", ""),
        "phone": address.get("phone", ""),
    }


class SpreadconnectAddon(SupplierAddon):
    requires_variant_id = True

    addon_id: str = "spreadconnect"
    addon_name: str = "Spreadconnect"
    addon_description: str = "EU print-on-demand via Spreadconnect (SPOD) API."
    addon_category: str = "supplier"
    version: str = "1.0.0"

    _config: Dict[str, Any] | None = None
    _client: SpreadconnectClient | None = None

    @classmethod
    def config_schema(cls):
        return SpreadconnectConfig

    async def initialize(self, config: dict) -> None:
        validated = SpreadconnectConfig(**config)
        self._config = dump_addon_config(validated)
        self._client = SpreadconnectClient(
            validated.api_key.get_secret_value(),
            staging=validated.use_staging,
        )
        self.is_enabled = validated.is_active
        info("Spreadconnect", "Initialized staging={}", validated.use_staging)

    async def validate_config(self, config: dict) -> None:
        from app.core.exceptions import ValidationError

        validated = SpreadconnectConfig(**config)
        api_key = validated.api_key.get_secret_value()
        if not api_key:
            return
        client = SpreadconnectClient(api_key, staging=validated.use_staging)
        try:
            await client.list_product_types()
        except SpreadconnectAPIError as exc:
            if exc.status_code == 401:
                raise ValidationError(message="Invalid API key — check your credentials") from exc
            if exc.status_code == 403:
                raise ValidationError(
                    message="API key is valid but missing required permissions: catalog:read"
                ) from exc
            raise ValidationError(message=f"Spreadconnect API error: {exc}") from exc

    async def shutdown(self) -> None:
        self._client = None
        self._config = None
        self.is_enabled = False

    def _require_client(self) -> SpreadconnectClient:
        if self._client is None:
            raise SpreadconnectAPIError("Spreadconnect addon is not initialized")
        return self._client

    def _parse_product_types(self, types: Any) -> list[dict[str, Any]]:
        if isinstance(types, list):
            return [t for t in types if isinstance(t, dict)]
        if isinstance(types, dict):
            for key in ("productTypes", "data"):
                val = types.get(key)
                if isinstance(val, list):
                    return [t for t in val if isinstance(t, dict)]
        return []

    async def _expand_product_types(self, client: SpreadconnectClient, types: Any) -> list[dict[str, Any]]:
        parsed = self._parse_product_types(types)
        expanded: list[dict[str, Any]] = []
        for ptype in parsed:
            if row_lacks_variant_list(ptype, "variants", "sizes"):
                type_id = str(ptype.get("id") or "").strip()
                if type_id:
                    try:
                        detail = await client.get_product_type(type_id)
                        if isinstance(detail, dict):
                            ptype = {**ptype, **detail}
                    except SpreadconnectAPIError as exc:
                        warning(
                            "Spreadconnect",
                            "catalog sync: get_product_type({}) failed: {}",
                            type_id,
                            exc,
                        )
            expanded.append(ptype)
        return expanded

    async def list_products(self, **kwargs: Any) -> List[Dict[str, Any]]:
        types = await self._require_client().list_product_types()
        return self._parse_product_types(types)

    async def fetch_catalog_for_import(self, **kwargs: Any) -> List[SupplierCatalogProduct]:
        client = self._require_client()
        types = await self._expand_product_types(client, await client.list_product_types())
        try:
            stocks = await client.list_stocks()
        except SpreadconnectAPIError:
            stocks = None
        return normalize_spreadconnect_catalog_products(types, stocks)

    async def get_product(self, product_id: str) -> Dict[str, Any]:
        for row in await self.list_products():
            if str(row.get("id") or "") == product_id:
                return row
        return {"error": f"Spreadconnect product type '{product_id}' not found"}

    async def create_order(
        self,
        items: List[Dict[str, Any]],
        shipping_address: Dict[str, Any],
        *,
        external_id: str | None = None,
        supplier_ref: str | None = None,
    ) -> Dict[str, Any]:
        del supplier_ref
        client = self._require_client()
        cfg = self._config or {}
        try:
            order_items = []
            for item in items:
                product_id = str(item.get("supplier_product_id") or "").strip()
                if not product_id:
                    continue
                entry: Dict[str, Any] = {
                    "quantity": int(item.get("quantity") or 1),
                }
                variant_id = str(item.get("supplier_variant_id") or "").strip()
                if variant_id:
                    entry["productTypeId"] = product_id
                    entry["sizeId"] = variant_id
                else:
                    entry["articleId"] = product_id
                order_items.append(entry)
            if not order_items:
                return {"success": False, "error": "No valid Spreadconnect line items"}

            payload: Dict[str, Any] = {
                "orderItems": order_items,
                "address": _map_address(shipping_address),
            }
            if external_id:
                payload["externalOrderId"] = external_id

            data = await client.create_order(payload)
            order_id = str(data.get("id") or data.get("orderId") or "")
            if bool(cfg.get("auto_confirm", True)) and order_id:
                await client.confirm_order(order_id)
            return {
                "success": True,
                "order_id": order_id,
                "status": data.get("status", "created"),
                "spreadconnect_order_id": order_id,
            }
        except SpreadconnectAPIError as exc:
            warning("Spreadconnect", "create_order error: {}", exc)
            return {"success": False, "error": str(exc)}

    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        try:
            data = await self._require_client().get_order(order_id)
            return {"order_id": order_id, "status": data.get("status", "unknown")}
        except SpreadconnectAPIError as exc:
            return {"order_id": order_id, "status": "error", "detail": str(exc)}

    async def sync_inventory(self) -> None:
        products = await self.list_products()
        info("Spreadconnect", "Catalog has {} product types", len(products))

    def get_routers(self) -> List[APIRouter]:
        from app.addons.suppliers.spreadconnect.routes import api_router

        return [api_router]

    def get_admin_routes(self) -> List[APIRouter]:
        from app.addons.suppliers.spreadconnect.routes import admin_router

        return [admin_router]

    def get_admin_templates(self) -> str:
        from pathlib import Path

        return str(Path(__file__).resolve().parent / "templates")

    def get_admin_static(self) -> str:
        from pathlib import Path

        return str(Path(__file__).resolve().parent / "static")
