"""Spreadconnect catalog normalization."""

from __future__ import annotations

from typing import Any

from app.addons.suppliers.catalog_utils import variant_attributes_from_row, variant_title_from_attributes
from schemas.supplier import (
    POD_INVENTORY_PLACEHOLDER,
    SupplierCatalogItem,
    SupplierCatalogProduct,
    SupplierCatalogVariant,
)


def normalize_spreadconnect_catalog(
    product_types: Any,
    stocks: Any | None = None,
) -> list[SupplierCatalogItem]:
    items: list[SupplierCatalogItem] = []
    types: list[dict[str, Any]] = []
    if isinstance(product_types, list):
        types = [t for t in product_types if isinstance(t, dict)]
    elif isinstance(product_types, dict):
        for key in ("productTypes", "data", "items"):
            val = product_types.get(key)
            if isinstance(val, list):
                types = [t for t in val if isinstance(t, dict)]
                break

    stock_by_variant: dict[str, int] = {}
    if isinstance(stocks, list):
        for row in stocks:
            if not isinstance(row, dict):
                continue
            vid = str(row.get("variantId") or row.get("id") or "")
            qty = row.get("stock") or row.get("quantity") or POD_INVENTORY_PLACEHOLDER
            if vid:
                try:
                    stock_by_variant[vid] = int(qty)
                except (TypeError, ValueError):
                    stock_by_variant[vid] = POD_INVENTORY_PLACEHOLDER

    for ptype in types:
        type_id = str(ptype.get("id") or "")
        type_name = str(ptype.get("name") or type_id or "Spreadconnect product")
        variants = ptype.get("variants") or ptype.get("sizes") or []
        if isinstance(variants, list) and variants:
            for variant in variants:
                if not isinstance(variant, dict):
                    continue
                variant_id = str(variant.get("id") or variant.get("variantId") or "").strip()
                if not variant_id:
                    continue
                size = str(variant.get("size") or variant.get("name") or "")
                name = f"{type_name} — {size}" if size else type_name
                inventory = stock_by_variant.get(variant_id, POD_INVENTORY_PLACEHOLDER)
                items.append(
                    SupplierCatalogItem(
                        external_key=f"spreadconnect:{type_id}:{variant_id}",
                        name=name,
                        description=ptype.get("description"),
                        price_cents=0,
                        sku=f"spc-{type_id}-{variant_id}",
                        image_url=ptype.get("imageUrl") or ptype.get("previewImageUrl"),
                        supplier_value="spreadconnect",
                        supplier_product_id=type_id,
                        supplier_variant_id=variant_id,
                        inventory_quantity=inventory,
                    )
                )
            continue
        if type_id:
            items.append(
                SupplierCatalogItem(
                    external_key=f"spreadconnect:{type_id}",
                    name=type_name,
                    description=ptype.get("description"),
                    price_cents=0,
                    sku=None,
                    image_url=ptype.get("imageUrl"),
                    supplier_value="spreadconnect",
                    supplier_product_id=type_id,
                    supplier_variant_id="",
                    inventory_quantity=0,
                    skip_reason="Spreadconnect product type has no sizes",
                )
            )
    return items


def normalize_spreadconnect_catalog_products(
    product_types: Any,
    stocks: Any | None = None,
) -> list[SupplierCatalogProduct]:
    """Map Spreadconnect product types to grouped catalog products."""
    products: list[SupplierCatalogProduct] = []
    types: list[dict[str, Any]] = []
    if isinstance(product_types, list):
        types = [t for t in product_types if isinstance(t, dict)]
    elif isinstance(product_types, dict):
        for key in ("productTypes", "data", "items"):
            val = product_types.get(key)
            if isinstance(val, list):
                types = [t for t in val if isinstance(t, dict)]
                break

    stock_by_variant: dict[str, int] = {}
    if isinstance(stocks, list):
        for row in stocks:
            if not isinstance(row, dict):
                continue
            vid = str(row.get("variantId") or row.get("id") or "")
            qty = row.get("stock") or row.get("quantity") or POD_INVENTORY_PLACEHOLDER
            if vid:
                try:
                    stock_by_variant[vid] = int(qty)
                except (TypeError, ValueError):
                    stock_by_variant[vid] = POD_INVENTORY_PLACEHOLDER

    for ptype in types:
        type_id = str(ptype.get("id") or "")
        type_name = str(ptype.get("name") or type_id or "Spreadconnect product")
        description = ptype.get("description")
        image_url = ptype.get("imageUrl") or ptype.get("previewImageUrl")
        product_image = str(image_url).strip() if image_url else None
        product_images = [product_image] if product_image else []
        variants_raw = ptype.get("variants") or ptype.get("sizes") or []
        variants: list[SupplierCatalogVariant] = []

        if isinstance(variants_raw, list) and variants_raw:
            for variant in variants_raw:
                if not isinstance(variant, dict):
                    continue
                variant_id = str(variant.get("id") or variant.get("variantId") or "").strip()
                if not variant_id:
                    continue
                attributes = variant_attributes_from_row(variant, "size")
                variant_title = variant_title_from_attributes(
                    type_name,
                    attributes,
                    fallback=type_name,
                )
                inventory = stock_by_variant.get(variant_id, POD_INVENTORY_PLACEHOLDER)
                variants.append(
                    SupplierCatalogVariant(
                        external_key=f"spreadconnect:{type_id}:{variant_id}",
                        title=variant_title,
                        attributes=attributes,
                        price_cents=0,
                        sku=f"spc-{type_id}-{variant_id}",
                        inventory_quantity=inventory,
                        supplier_product_id=type_id,
                        supplier_variant_id=variant_id,
                        image_urls=list(product_images),
                    )
                )
        elif type_id:
            variants.append(
                SupplierCatalogVariant(
                    external_key=f"spreadconnect:{type_id}",
                    title=type_name,
                    attributes={},
                    price_cents=0,
                    sku=None,
                    inventory_quantity=0,
                    supplier_product_id=type_id,
                    supplier_variant_id="",
                    image_urls=product_images,
                    skip_reason="Spreadconnect product type has no sizes",
                )
            )
        else:
            continue

        products.append(
            SupplierCatalogProduct(
                external_product_key=f"spreadconnect:{type_id}",
                name=type_name,
                description=description if isinstance(description, str) else None,
                product_type=None,
                image_urls=product_images,
                image_alt_texts=[],
                variants=variants,
                supplier_value="spreadconnect",
            )
        )
    return products
