# -*- coding: utf-8 -*-
"""Portable read repository for normalized business records.

Services depend on these functions rather than a database driver's SQL
surface. SQLite is the active local adapter; a PostgreSQL adapter can implement
the same small contract without changing business modules.
"""
from contextlib import contextmanager

import config
from storage_adapter import get_storage_adapter
from utils import read_json


def list_orders(owner_user_id=None, limit=None, offset=0):
    adapter = get_storage_adapter()
    if adapter is not None:
        return adapter.list_order_records(owner_user_id, limit, offset)
    records = read_json(config.ORDER_FILE, [])
    if owner_user_id is not None:
        dealers = {row.get("id") for row in read_json(config.DEALER_FILE, [])
                   if row.get("owner_user_id") == owner_user_id}
        records = [row for row in records if row.get("owner_user_id") == owner_user_id
                   and row.get("dealerId") in dealers]
    records = list(reversed(records))
    if limit is not None:
        start = max(0, int(offset or 0))
        records = records[start:start + max(1, min(1000, int(limit)))]
    return records


def count_orders(owner_user_id=None):
    adapter = get_storage_adapter()
    if adapter is not None:
        return adapter.count_order_records(owner_user_id)
    return len(list_orders(owner_user_id))


def list_dealers(owner_user_id=None, path=None):
    adapter = get_storage_adapter()
    if adapter is not None:
        return adapter.list_dealer_records(owner_user_id)
    records = read_json(path or config.DEALER_FILE, [])
    if owner_user_id is not None:
        records = [row for row in records if row.get("owner_user_id") == owner_user_id]
    return records


def list_products(path=None):
    """Read products from the active normalized persistence adapter."""
    adapter = get_storage_adapter()
    if adapter is not None:
        return adapter.list_product_records()
    return read_json(path or config.DATA_FILE, [])


def read_settings(path=None, default=None):
    """Read settings from relational keys when SQLite is active."""
    adapter = get_storage_adapter()
    if adapter is not None:
        return adapter.read_settings_records(default)
    return read_json(path or config.SET_FILE, {} if default is None else default)


def replace_products(records, path=None):
    """Replace products through a transaction in the active persistence adapter."""
    adapter = get_storage_adapter()
    if adapter is not None:
        return adapter.replace_product_records(records)
    from utils import write_json
    write_json(path or config.DATA_FILE, records)


def replace_dealers(records, path=None):
    """Replace dealers through a transaction in the active persistence adapter."""
    adapter = get_storage_adapter()
    if adapter is not None:
        return adapter.replace_dealer_records(records)
    from utils import write_json
    write_json(path or config.DEALER_FILE, records)


def save_settings(settings, path=None):
    """Save settings through a transaction in the active persistence adapter."""
    adapter = get_storage_adapter()
    if adapter is not None:
        return adapter.replace_settings_records(settings)
    from utils import write_json
    write_json(path or config.SET_FILE, settings)


def mutate_documents(defaults, mutator):
    """Apply a read-modify-write operation under the active adapter boundary."""
    if not isinstance(defaults, dict) or not defaults or not callable(mutator):
        raise ValueError("Belge değişikliği için varsayılanlar ve işlem gerekli.")
    adapter = get_storage_adapter()
    if adapter is not None:
        return adapter.mutate_documents(defaults, mutator)
    import os
    paths_by_name = {os.path.basename(path): path for path in defaults}
    documents = {name: read_json(path, defaults[path]) for name, path in paths_by_name.items()}
    result = mutator(documents)
    from utils import write_json_many
    write_json_many({paths_by_name[name]: value for name, value in documents.items()})
    return result


@contextmanager
def document_transaction(defaults):
    """Hold an adapter transaction over a complete read-modify-write block."""
    if not isinstance(defaults, dict) or not defaults:
        raise ValueError("Belge işlemi için varsayılanlar gerekli.")
    adapter = get_storage_adapter()
    if adapter is not None:
        with adapter.document_transaction(defaults) as documents:
            yield documents
        return
    import os
    paths_by_name = {os.path.basename(path): path for path in defaults}
    documents = {name: read_json(path, defaults[path]) for name, path in paths_by_name.items()}
    yield documents
    from utils import write_json_many
    originals = {path: open(path, "rb").read() if os.path.exists(path) else None
                 for path in paths_by_name.values()}
    try:
        write_json_many({paths_by_name[name]: value for name, value in documents.items()})
    except Exception:
        import tempfile
        rollback_errors = []
        for path, content in originals.items():
            try:
                if content is None:
                    if os.path.exists(path):
                        os.unlink(path)
                else:
                    directory = os.path.dirname(os.path.abspath(path))
                    fd, temp_path = tempfile.mkstemp(prefix=os.path.basename(path) + ".restore.",
                                                     suffix=".tmp", dir=directory)
                    try:
                        with os.fdopen(fd, "wb") as stream:
                            stream.write(content)
                            stream.flush()
                            os.fsync(stream.fileno())
                        os.replace(temp_path, path)
                    finally:
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
            except Exception as rollback_error:
                rollback_errors.append("%s: %s" % (os.path.basename(path), rollback_error))
        if rollback_errors:
            raise RuntimeError("[PARTIAL_UPDATE] Yazım başarısız; geri alma da başarısız: %s" %
                               "; ".join(rollback_errors))
        raise


def list_quotes(owner_user_id=None):
    adapter = get_storage_adapter()
    if adapter is not None:
        return adapter.list_quote_records(owner_user_id)
    records = read_json(config.QUOTE_FILE, [])
    if owner_user_id is not None:
        dealers = {row.get("id") for row in read_json(config.DEALER_FILE, [])
                   if row.get("owner_user_id") == owner_user_id}
        records = [row for row in records if row.get("owner_user_id") == owner_user_id
                   and row.get("dealerId") in dealers]
    return list(reversed(records))


def dashboard_order_totals(owner_user_id=None, month=None, records=None):
    adapter = get_storage_adapter()
    if adapter is not None:
        return adapter.dashboard_order_totals(owner_user_id, month)
    from services.hesap_service import (siparis_iptal_mi, siparis_finans_metrikleri,
                                        siparis_rapor_tarih_bilgisi)
    rows = list(records) if records is not None else list_orders(owner_user_id)
    active = [row for row in rows if not siparis_iptal_mi(row)]
    date_info = {id(row): siparis_rapor_tarih_bilgisi(row) for row in active}
    month_rows = [row for row in active if date_info[id(row)]["month_key"] == str(month)] if month else []
    revenue = round(sum(siparis_finans_metrikleri(row)["ciro"] for row in active), 2)
    month_revenue = 0.0
    for row in month_rows:
        if not date_info[id(row)]["valid_date"]:
            continue
        month_revenue += siparis_finans_metrikleri(row)["ciro"]
    return {"count": len(active), "sales": revenue, "month_count": len(month_rows),
            "month_sales": round(month_revenue, 2)}
