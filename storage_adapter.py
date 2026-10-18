# -*- coding: utf-8 -*-
"""Runtime selection for persistence adapters.

Business and utility modules must depend on this small selector instead of
importing a database driver's implementation directly. Adapters expose the
document, relational-query, transaction, initialization, and backup functions
used by the application. JSON remains the legacy file adapter (None here).
"""
from functools import lru_cache
import importlib

import config


_ADAPTERS = {
    "sqlite": "sqlite_store",
    "postgresql": "postgres_store",
    "postgres": "postgres_store",
}

# This is the behavioral boundary shared by SQLite and future server adapters.
# Keep it aligned with data_repository.py, utils.py, auth, services and backups.
ADAPTER_METHODS = (
    "ensure_initialized", "managed_json_path", "read_document", "write_documents",
    "document_exists", "list_order_records", "count_order_records",
    "list_dealer_records", "list_product_records", "read_settings_records",
    "replace_product_records", "replace_dealer_records", "replace_settings_records",
    "mutate_documents", "document_transaction", "list_quote_records",
    "dashboard_order_totals", "read_raw_material_records", "read_stock_records",
    "backup_database", "restore_database", "integrity_check",
)


class StorageBackendError(RuntimeError):
    """Raised when a configured persistence backend is unavailable or invalid."""


@lru_cache(maxsize=None)
def _load_adapter(module_name):
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        raise StorageBackendError(
            "Yapılandırılan veri deposu adaptörü yüklenemedi: %s" % module_name
        ) from exc


def get_storage_adapter():
    """Return the active SQL adapter, or None while legacy JSON is selected."""
    backend = str(getattr(config, "STORAGE_BACKEND", "json") or "json").strip().lower()
    if backend in ("json", "file"):
        return None
    module_name = _ADAPTERS.get(backend)
    if module_name is None:
        raise StorageBackendError("Bilinmeyen veri deposu: %s" % backend)
    if backend in ("postgres", "postgresql") and not getattr(config, "DATABASE_URL", ""):
        raise StorageBackendError(
            "PostgreSQL etkinleştirilmeden önce LUMISPAC_DATABASE_URL yapılandırılmalı."
        )
    adapter = _load_adapter(module_name)
    missing = [name for name in ADAPTER_METHODS
               if not callable(getattr(adapter, name, None))]
    if missing:
        raise StorageBackendError(
            "Veri deposu adaptörü sözleşmeyi karşılamıyor (%s): %s" %
            (module_name, ", ".join(missing))
        )
    return adapter


def clear_adapter_cache():
    """Clear imports in tests after they monkeypatch the selected backend."""
    _load_adapter.cache_clear()
