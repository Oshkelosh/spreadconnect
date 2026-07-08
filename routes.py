"""Spreadconnect addon routes."""

from typing import Any

from app.addons.suppliers.shared_routes import build_supplier_routers


def _parse_form(form: Any) -> tuple[dict[str, Any], bool]:
    return {
        "api_key": form.get("api_key", ""),
        "is_active": form.get("is_active") == "on",
        "use_staging": form.get("use_staging") == "on",
        "auto_confirm": form.get("auto_confirm") == "on",
    }, form.get("is_active") == "on"


admin_router, api_router, _env = build_supplier_routers(
    "spreadconnect",
    template_name="config.html",
    page_title="Spreadconnect",
    parse_config_form=_parse_form,
)
