# Spreadconnect (`spreadconnect`)

EU print-on-demand via Spreadconnect (SPOD) API.

## Overview

| | |
|---|---|
| Addon ID | `spreadconnect` |
| Category | supplier |
| Version | 1.0.0 |
| Category guide | [../README.md](../README.md) |
| Fulfillment key | `spreadconnect` |

Multiple suppliers can be enabled at the same time. Fulfillment runs when an order becomes **paid**.

## Enable and configure

1. Install this package under `app/addons/suppliers/spreadconnect/`
2. Open **Admin → Suppliers → Spreadconnect** at `/admin/suppliers/spreadconnect`
3. Enter API credentials and enable the addon

## Configuration schema

| Field | Type | Description |
|-------|------|-------------|
| `api_key` | secret | Spreadconnect API key |
| `is_active` | bool | Whether the addon is active |
| `use_staging` | bool | Use staging environment |
| `auto_confirm` | bool | Auto-confirm after order create |

## Routes

### Public API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/suppliers/spreadconnect/products` | List catalog products |

### Admin

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/suppliers/spreadconnect` | Config form |
| POST | `/admin/suppliers/spreadconnect/save` | Save config |
| POST | `/admin/suppliers/spreadconnect/sync` | Trigger catalog sync |

## Core integration

- **Variant supplier fields:** paid-order fulfillment reads SPOD type/variant IDs from each **ProductVariant** row
- **Fulfillment:** creates SPOD order; optional auto-confirm; staging env when `use_staging` is true
- **Grouping:** line items grouped by fulfillment key `spreadconnect`

## Variant supplier fields

| Field | Description |
|-------|-------------|
| `supplier_addon_id` | `spreadconnect` |
| `supplier_product_id` | SPOD product type id |
| `supplier_variant_id` | SPOD size/variant id |

Both IDs are required (`requires_variant_id=True`). Orders can fall back to `articleId`-only in some cases.

## Catalog sync

Supported. Admin sync at `/admin/suppliers/spreadconnect` or `POST /api/v1/admin/suppliers/spreadconnect/sync`.

**Import model:** grouped products; one variant per size/option.

| Key | Format |
|-----|--------|
| Variant dedup key | `spreadconnect:{typeId}:{variantId}` |

**Prerequisites:**

- Product types imported with optional stock API checks.

## Provider setup

- Obtain API key from Spreadconnect/SPOD.

## Package layout

```
spreadconnect/
├── README.md
├── addon.py
├── catalog.py
├── client.py
├── routes.py
└── templates/
```

## See also

- [Supplier addon development](../README.md)
- [Oshkelosh addon guide](../../README.md)
