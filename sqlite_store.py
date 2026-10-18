# -*- coding: utf-8 -*-
"""SQLite document store used as a low-risk migration layer for legacy JSON data.

The application keeps its existing domain payloads while SQLite provides a
single durable database, atomic multi-document writes and consistent snapshots.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone


RELATIONAL_DOCUMENTS = frozenset({
    "lumispac_data.json", "lumispac_dealers.json", "lumispac_settings.json",
    "lumispac_users.json", "lumispac_orders.json", "lumispac_quotes.json",
    "lumispac_stok.json", "lumispac_raw_materials.json", "lumispac_uretim.json",
    "lumispac_finans.json", "lumispac_approvals.json", "lumispac_audit.json",
    "lumispac_geri_alma.json", "lumispac_geri_alma_islemleri.json",
})

BACKUP_EXTENSION = ".sqlite3"


class StoreError(RuntimeError):
    """Stored data or database failed validation."""


class MigrationError(StoreError):
    """Legacy JSON could not be imported without risking data loss."""


_initialized = set()


def _settings():
    import config
    return config


def database_path():
    return _settings().DB_FILE


def _float_or_none(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError, OverflowError):
        raise StoreError("İlişkisel kayıt alanı sayısal değere dönüştürülemedi.")


def _text_or_json(value):
    if value is None or isinstance(value, (str, int, float)):
        return value
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _production_projection(conn, source):
    """Rebuild the legacy-shaped production document from typed SQL rows."""
    projected = _document_metadata_projection(conn, "lumispac_uretim.json", source)
    for key, table in (("downtime_reasons", "downtime_reasons"),
                       ("reason_history", "production_reason_history"),
                       ("recycled_movements", "recycled_movements")):
        if key in source:
            projected[key] = [json.loads(item[0]) for item in conn.execute(
                "SELECT payload FROM %s ORDER BY position,id" % table).fetchall()]
    if "jobs" in source:
        jobs = []
        for row in conn.execute("SELECT id,payload FROM production_jobs ORDER BY position,id").fetchall():
            job = json.loads(row["payload"])
            has_runs, has_history = job.pop("_sql_has_runs", True), job.pop("_sql_has_history", True)
            if has_runs:
                job["runs"] = [json.loads(item[0]) for item in conn.execute(
                    "SELECT payload FROM production_runs WHERE job_id=? ORDER BY run_position",
                    (row["id"],)).fetchall()]
            if has_history:
                job["history"] = [json.loads(item[0]) for item in conn.execute(
                    "SELECT payload FROM production_job_history WHERE job_id=? ORDER BY history_position",
                    (row["id"],)).fetchall()]
            jobs.append(job)
        projected["jobs"] = jobs
    if "receipts" in source:
        receipts = []
        for row in conn.execute("SELECT id,payload FROM production_receipts ORDER BY position,id").fetchall():
            receipt = json.loads(row["payload"])
            if receipt.pop("_sql_has_history", True):
                receipt["history"] = [json.loads(item[0]) for item in conn.execute(
                    "SELECT payload FROM production_receipt_history WHERE receipt_id=? ORDER BY history_position",
                    (row["id"],)).fetchall()]
            receipts.append(receipt)
        projected["receipts"] = receipts
    return projected


def _raw_material_projection(conn, source):
    """Rebuild the complete raw-material document from normalized SQL rows."""
    projected = dict(source)
    for row in conn.execute("""
        SELECT metadata_key,value_json FROM document_metadata
        WHERE document_name='lumispac_raw_materials.json' ORDER BY position,metadata_key
    """):
        projected[row["metadata_key"]] = json.loads(row["value_json"])
    for key, table in (("materials", "raw_materials"), ("suppliers", "suppliers"),
                       ("stock_movements", "raw_material_stock_movements")):
        projected[key] = [json.loads(row[0]) for row in conn.execute(
            "SELECT payload FROM %s ORDER BY position,id" % table).fetchall()]
    purchases = []
    for header in conn.execute("SELECT id,payload FROM raw_material_purchases ORDER BY position,id"):
        purchase = json.loads(header["payload"])
        if purchase.pop("_sql_has_lines", True):
            purchase["lines"] = [json.loads(row[0]) for row in conn.execute(
                "SELECT payload FROM raw_purchase_lines WHERE purchase_id=? ORDER BY line_position",
                (header["id"],))]
        if purchase.pop("_sql_has_payments", True):
            purchase["payments"] = [json.loads(row[0]) for row in conn.execute(
                "SELECT payload FROM raw_purchase_payments WHERE purchase_id=? ORDER BY position,payment_id",
                (header["id"],))]
        purchases.append(purchase)
    projected["purchases"] = purchases
    projected["history"] = [json.loads(row[0]) for row in conn.execute(
        "SELECT payload FROM raw_material_history ORDER BY event_position,event_id")]
    recipes = []
    for header in conn.execute("SELECT id,payload FROM material_recipes ORDER BY position,id"):
        recipe = json.loads(header["payload"])
        if recipe.pop("_sql_has_lines", True):
            recipe["lines"] = [json.loads(row[0]) for row in conn.execute(
                "SELECT payload FROM material_recipe_lines WHERE recipe_id=? ORDER BY line_position",
                (header["id"],))]
        recipes.append(recipe)
    projected["recipes"] = recipes
    return projected


def _stock_projection(conn, source):
    projected = dict(source)
    has_metadata = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='document_metadata'").fetchone()
    if has_metadata:
        for row in conn.execute("""
            SELECT metadata_key,value_json FROM document_metadata
            WHERE document_name='lumispac_stok.json' ORDER BY position,metadata_key
        """):
            projected[row["metadata_key"]] = json.loads(row["value_json"])
    projected["hareketler"] = [json.loads(row[0]) for row in conn.execute(
        "SELECT payload FROM stock_movements ORDER BY position,id")]
    projected["esikler"] = {row[0]: json.loads(row[1]) for row in conn.execute(
        "SELECT product_code,payload FROM stock_thresholds ORDER BY position,product_code")}
    return projected


def _audit_undo_projection(conn, name, source):
    if name in {"lumispac_audit.json", "lumispac_geri_alma_islemleri.json"}:
        table = "audit_events" if name == "lumispac_audit.json" else "undo_operation_events"
        return [json.loads(row[0]) for row in conn.execute(
            "SELECT payload FROM %s ORDER BY position,event_id" % table).fetchall()]
    if name == "lumispac_geri_alma.json":
        actions = []
        for row in conn.execute("SELECT id,payload FROM undo_actions ORDER BY position,id").fetchall():
            action = json.loads(row["payload"])
            if action.pop("_sql_has_changes", True):
                action["degisiklikler"] = [json.loads(item[0]) for item in conn.execute(
                    "SELECT payload FROM undo_changes WHERE undo_id=? ORDER BY change_position",
                    (row["id"],)).fetchall()]
            actions.append(action)
        return actions
    raise ValueError("Bilinmeyen denetim belgesi")


def _document_metadata_projection(conn, name, source):
    projected = dict(source or {})
    table_exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='document_metadata'").fetchone()
    if not table_exists:
        return projected
    for row in conn.execute(
            "SELECT metadata_key,value_json FROM document_metadata WHERE document_name=? ORDER BY position,metadata_key",
            (name,)):
        projected[row["metadata_key"]] = json.loads(row["value_json"])
    return projected


def _identity_projection(conn, source):
    """Rebuild identity documents with permission maps from normalized rows."""
    projected = _document_metadata_projection(conn, "lumispac_users.json", source)
    for key, table, id_key, permission_field in (
        ("departmanlar", "departments", "id", "moduller"),
        ("kullanicilar", "users", "id", "izinler"),
    ):
        rows = conn.execute("SELECT id,payload FROM %s ORDER BY position,id" % table).fetchall()
        result = []
        for row in rows:
            record = json.loads(row["payload"])
            has_permissions = record.pop("_sql_has_permissions", True)
            if has_permissions:
                permission_table = "department_permissions" if table == "departments" else "user_permission_overrides"
                fk = "department_id" if table == "departments" else "user_id"
                record[permission_field] = {item[0]: item[1] for item in conn.execute(
                    "SELECT permission_key,permission_level FROM %s WHERE %s=? ORDER BY position,permission_key" %
                    (permission_table, fk), (row["id"],)).fetchall()}
            result.append(record)
        projected[key] = result
    return projected


def _sync_append_only_events(conn, table, events, event_id_key="event_id"):
    """Insert immutable event payloads; reject removal or mutation of old events."""
    if not isinstance(events, list):
        raise StoreError("Denetim olay listesi geçersiz; SQL eşitlemesi durduruldu.")
    incoming = set()
    for position, event in enumerate(events):
        if not isinstance(event, dict) or not event.get(event_id_key):
            raise StoreError("Denetim olayı kimliği eksik; SQL eşitlemesi durduruldu.")
        event_id = str(event[event_id_key])
        if event_id in incoming:
            raise StoreError("Yinelenen denetim olayı kimliği; SQL eşitlemesi durduruldu.")
        incoming.add(event_id)
        payload = json.dumps(event, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        existing = conn.execute("SELECT payload FROM %s WHERE event_id=?" % table, (event_id,)).fetchone()
        if existing and existing[0] != payload:
            raise StoreError("Denetim kaydı değiştirilemez; SQL eşitlemesi durduruldu.")
        if not existing:
            if table == "audit_events":
                conn.execute("""INSERT INTO audit_events
                    (event_id,occurred_at,user_id,username,action,source,method,path,status_code,result,undo_id,payload,position)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (event_id, event.get("zaman"), event.get("kullanici_id"), event.get("kullanici_adi"),
                     event.get("islem"), event.get("kaynak"), event.get("yontem"), event.get("yol"),
                     event.get("durum_kodu"), event.get("sonuc"), event.get("undo_id"), payload, position))
            else:
                conn.execute("""INSERT INTO undo_operation_events
                    (event_id,occurred_at,user_id,username,action,source,status_code,result,undo_id,payload,position)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (event_id, event.get("zaman"), event.get("kullanici_id"), event.get("kullanici_adi"),
                     event.get("islem"), event.get("kaynak"), event.get("durum_kodu"), event.get("sonuc"),
                     event.get("undo_id"), payload, position))
        else:
            conn.execute("UPDATE %s SET position=? WHERE event_id=?" % table, (position, event_id))
    existing_ids = {row[0] for row in conn.execute("SELECT event_id FROM %s" % table)}
    if existing_ids != incoming:
        raise StoreError("Denetim geçmişinden olay çıkarılamaz; SQL eşitlemesi durduruldu.")


def _sync_relational_documents(conn, names, documents=None):
    """Refresh typed relational projections inside the caller's transaction."""
    def source_document(name, default):
        if documents is not None and name in documents:
            return documents[name]
        row = conn.execute("SELECT payload FROM data_documents WHERE name=?", (name,)).fetchone()
        return json.loads(row[0]) if row else default

    def sync_metadata(document_name, document, relational_keys):
        values = [(key, value) for key, value in document.items() if key not in relational_keys]
        conn.execute("DELETE FROM document_metadata WHERE document_name=?", (document_name,))
        conn.executemany("INSERT INTO document_metadata(document_name,metadata_key,value_json,position) VALUES(?,?,?,?)",
                         [(document_name, str(key), json.dumps(value, ensure_ascii=False,
                           separators=(",", ":"), allow_nan=False), position)
                          for position, (key, value) in enumerate(values)])
    if "lumispac_data.json" in names:
        products = source_document("lumispac_data.json", [])
        if not isinstance(products, list):
            raise StoreError("Ürün belgesi liste biçiminde değil; SQL eşitlemesi durduruldu.")
        conn.execute("DELETE FROM products")
        values = []
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for position, product in enumerate(products):
            if not isinstance(product, dict) or not product.get("id") or not product.get("code"):
                raise StoreError("Ürün kaydının kimliği/kodu eksik; SQL eşitlemesi durduruldu.")
            payload = json.dumps(product, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            values.append((str(product["id"]), str(product["code"]), str(product.get("name") or ""),
                           _float_or_none(product.get("weight")), _float_or_none(product.get("qty")),
                           _float_or_none(product.get("volume")), _float_or_none(product.get("stock")),
                           _float_or_none(product.get("sale")), int(bool(product.get("active", True))),
                           payload, now, position))
        conn.executemany("""
            INSERT INTO products(id,code,name,weight,qty,volume,stock,sale,active,payload,updated_at,position)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """, values)

    if "lumispac_dealers.json" in names:
        dealers = source_document("lumispac_dealers.json", [])
        if not isinstance(dealers, list):
            raise StoreError("Bayi belgesi liste biçiminde değil; SQL eşitlemesi durduruldu.")
        conn.execute("DELETE FROM dealers")
        values = []
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for position, dealer in enumerate(dealers):
            if not isinstance(dealer, dict) or not dealer.get("id"):
                raise StoreError("Bayi kaydının kimliği eksik; SQL eşitlemesi durduruldu.")
            payload = json.dumps(dealer, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            values.append((str(dealer["id"]), str(dealer.get("name") or ""),
                           dealer.get("contact"), dealer.get("phone"), dealer.get("city"),
                           _float_or_none(dealer.get("discount")), dealer.get("owner_user_id"),
                           payload, now, position))
        conn.executemany("""
            INSERT INTO dealers(id,name,contact,phone,city,discount,owner_user_id,payload,updated_at,position)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, values)

    if "lumispac_settings.json" in names:
        settings = source_document("lumispac_settings.json", {})
        if not isinstance(settings, dict):
            raise StoreError("Ayar belgesi sözlük biçiminde değil; SQL eşitlemesi durduruldu.")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        conn.execute("DELETE FROM application_settings")
        conn.executemany("""
            INSERT INTO application_settings(setting_key,value_json,position,updated_at)
            VALUES(?,?,?,?)
        """, [(str(key), json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
               position, now) for position, (key, value) in enumerate(settings.items())])

    if "lumispac_users.json" in names:
        identity = source_document("lumispac_users.json", {})
        if not isinstance(identity, dict):
            raise StoreError("Kullanıcı belgesi sözlük biçiminde değil; SQL eşitlemesi durduruldu.")
        departments = identity.get("departmanlar", [])
        users = identity.get("kullanicilar", [])
        if not isinstance(departments, list) or not isinstance(users, list):
            raise StoreError("Departman/kullanıcı listesi geçersiz; SQL eşitlemesi durduruldu.")
        sync_metadata("lumispac_users.json", identity, {"departmanlar", "kullanicilar"})
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        department_values, department_permissions = [], []
        for position, department in enumerate(departments):
            if not isinstance(department, dict) or not department.get("id"):
                raise StoreError("Departman kimliği eksik; SQL eşitlemesi durduruldu.")
            permissions = department.get("moduller", {})
            if not isinstance(permissions, dict) or any(not isinstance(k, str) or not isinstance(v, str)
                                                        for k, v in permissions.items()):
                raise StoreError("Departman izinleri geçersiz; SQL eşitlemesi durduruldu.")
            department_parent = {key: value for key, value in department.items() if key != "moduller"}
            department_parent["_sql_has_permissions"] = "moduller" in department
            department_values.append((str(department["id"]), str(department.get("ad") or ""),
                                      department.get("ust_departman_id"), department.get("yonetici_id"),
                                      int(bool(department.get("sistem", False))),
                                      json.dumps(department_parent, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
                                      position, now))
            department_permissions.extend((str(department["id"]), key, value, perm_position)
                                          for perm_position, (key, value) in enumerate(permissions.items()))
        user_values, user_permissions = [], []
        for position, user in enumerate(users):
            if not isinstance(user, dict) or not user.get("id") or not user.get("kullanici_adi"):
                raise StoreError("Kullanıcı kimliği/adı eksik; SQL eşitlemesi durduruldu.")
            permissions = user.get("izinler", {})
            if not isinstance(permissions, dict) or any(not isinstance(k, str) or not isinstance(v, str)
                                                        for k, v in permissions.items()):
                raise StoreError("Kullanıcı izin istisnaları geçersiz; SQL eşitlemesi durduruldu.")
            user_parent = {key: value for key, value in user.items() if key != "izinler"}
            user_parent["_sql_has_permissions"] = "izinler" in user
            user_values.append((str(user["id"]), str(user["kullanici_adi"]), user.get("ad_soyad"),
                                user.get("departman_id"), user.get("yonetici_id"),
                                int(bool(user.get("aktif", True))), user.get("sifre_hash"),
                                json.dumps(user_parent, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
                                position, now))
            user_permissions.extend((str(user["id"]), key, value, perm_position)
                                    for perm_position, (key, value) in enumerate(permissions.items()))
        # Clear both projections in the same transaction as their source document.
        conn.execute("DELETE FROM department_permissions")
        conn.execute("DELETE FROM user_permission_overrides")
        conn.execute("DELETE FROM users")
        conn.execute("DELETE FROM departments")
        conn.executemany("""
            INSERT INTO departments(id,name,parent_id,manager_user_id,system_department,payload,position,updated_at)
            VALUES(?,?,?,?,?,?,?,?)
        """, department_values)
        conn.executemany("""
            INSERT INTO users(id,username,full_name,department_id,manager_user_id,active,password_hash,payload,position,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, user_values)
        conn.executemany("INSERT INTO department_permissions(department_id,permission_key,permission_level,position) VALUES(?,?,?,?)",
                         department_permissions)
        conn.executemany("INSERT INTO user_permission_overrides(user_id,permission_key,permission_level,position) VALUES(?,?,?,?)",
                         user_permissions)

    for document_name, header_table, line_table, payment_table in (
        ("lumispac_orders.json", "orders", "order_lines", "order_payments"),
        ("lumispac_quotes.json", "quotes", "quote_lines", None),
    ):
        if document_name not in names:
            continue
        records = source_document(document_name, [])
        if not isinstance(records, list):
            raise StoreError("Sipariş/teklif belgesi liste biçiminde değil; SQL eşitlemesi durduruldu.")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        conn.execute("DELETE FROM %s" % line_table)
        if payment_table:
            conn.execute("DELETE FROM %s" % payment_table)
        conn.execute("DELETE FROM %s" % header_table)
        headers, lines, payments = [], [], []
        order_columns = {row[1] for row in conn.execute("PRAGMA table_info(orders)")} if header_table == "orders" else set()
        has_reporting_flags = {"is_cancelled", "report_month", "report_date_valid"}.issubset(order_columns)
        for position, record in enumerate(records):
            if not isinstance(record, dict) or not record.get("id"):
                raise StoreError("Sipariş/teklif kimliği eksik; SQL eşitlemesi durduruldu.")
            record_id = str(record["id"])
            child_lines = record.get("lines", [])
            child_payments = record.get("payments", []) if payment_table else []
            if not isinstance(child_lines, list) or not isinstance(child_payments, list):
                raise StoreError("Sipariş/teklif kalem veya ödeme listesi geçersiz; SQL eşitlemesi durduruldu.")
            parent = {key: value for key, value in record.items()
                      if key not in {"lines", "payments"}}
            parent["_sql_has_lines"] = "lines" in record
            parent["_sql_has_payments"] = "payments" in record
            payload = json.dumps(parent, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            is_order = header_table == "orders"
            net_sales_total = None
            reporting_flags = ()
            if is_order:
                from services.hesap_service import (siparis_finans_metrikleri, siparis_iptal_mi,
                                                    siparis_rapor_tarih_bilgisi)
                net_sales_total = siparis_finans_metrikleri(record)["ciro"]
                if has_reporting_flags:
                    date_info = siparis_rapor_tarih_bilgisi(record)
                    reporting_flags = (int(siparis_iptal_mi(record)), date_info["month_key"],
                                        int(date_info["valid_date"]))
            headers.append((record_id, record.get("no"), record.get("dealerId"), record.get("customer"),
                            record.get("date"), record.get("delivery", {}).get("date")
                            if isinstance(record.get("delivery"), dict) else record.get("delivery"),
                            record.get("status"), record.get("owner_user_id"),
                            _float_or_none(record.get("grand")), _float_or_none(record.get("profit")),
                            net_sales_total, payload, position, now) + reporting_flags if is_order else
                           (record_id, record.get("no"), record.get("dealerId"), record.get("customer"),
                            record.get("date"), record.get("status"), record.get("owner_user_id"),
                            _float_or_none(record.get("grand")), _float_or_none(record.get("profit")),
                            payload, position, now))
            for line_position, line in enumerate(child_lines):
                if not isinstance(line, dict):
                    raise StoreError("Sipariş/teklif kalemi geçersiz; SQL eşitlemesi durduruldu.")
                line_payload = json.dumps(line, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
                lines.append((record_id, line_position, line.get("code") or line.get("kod") or line.get("id"),
                              line.get("name") or line.get("ad"), _float_or_none(line.get("qty")),
                              _float_or_none(line.get("boxes") or line.get("koli")),
                              _float_or_none(line.get("sale") or line.get("price")),
                              _float_or_none(line.get("cost")), _float_or_none(line.get("profit")),
                              _float_or_none(line.get("total")), line_payload))
            for payment_position, payment in enumerate(child_payments):
                if not isinstance(payment, dict):
                    raise StoreError("Sipariş ödeme kaydı geçersiz; SQL eşitlemesi durduruldu.")
                payment_id = str(payment.get("id") or payment_position)
                payment_payload = json.dumps(payment, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
                payments.append((record_id, payment_id, _float_or_none(payment.get("amount")),
                                 payment.get("date"), payment.get("status"), payment.get("method"),
                                 payment_payload, payment_position))
        if header_table == "orders":
            if has_reporting_flags:
                conn.executemany("""INSERT INTO orders
                    (id,number,dealer_id,customer,order_date,delivery_date,status,owner_user_id,gross_total,net_profit,net_sales_total,payload,position,updated_at,is_cancelled,report_month,report_date_valid)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", headers)
            else:
                conn.executemany("""INSERT INTO orders
                    (id,number,dealer_id,customer,order_date,delivery_date,status,owner_user_id,gross_total,net_profit,net_sales_total,payload,position,updated_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", [header[:14] for header in headers])
        else:
            conn.executemany("""INSERT INTO quotes
                (id,number,dealer_id,customer,quote_date,status,owner_user_id,gross_total,net_profit,payload,position,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", headers)
        parent_column = "order_id" if header_table == "orders" else "quote_id"
        conn.executemany("INSERT INTO %s(%s,line_position,product_code,product_name,quantity,boxes,sale,cost,profit,total,payload) VALUES(?,?,?,?,?,?,?,?,?,?,?)" % (line_table, parent_column), lines)
        if payment_table:
            if "position" in {row[1] for row in conn.execute("PRAGMA table_info(order_payments)")}:
                conn.executemany("INSERT INTO order_payments(order_id,payment_id,amount,payment_date,status,method,payload,position) VALUES(?,?,?,?,?,?,?,?)", payments)
            else:
                conn.executemany("INSERT INTO order_payments(order_id,payment_id,amount,payment_date,status,method,payload) VALUES(?,?,?,?,?,?,?)",
                                 [payment[:-1] for payment in payments])

    if "lumispac_stok.json" in names:
        stock = source_document("lumispac_stok.json", {})
        if not isinstance(stock, dict) or not isinstance(stock.get("hareketler", []), list) or not isinstance(stock.get("esikler", {}), dict):
            raise StoreError("Stok hareket/eşik belgesi geçersiz; SQL eşitlemesi durduruldu.")
        sync_metadata("lumispac_stok.json", stock, {"hareketler", "esikler"})
        conn.execute("DELETE FROM stock_movements")
        conn.execute("DELETE FROM stock_thresholds")
        movements = []
        for position, movement in enumerate(stock.get("hareketler", [])):
            if not isinstance(movement, dict):
                raise StoreError("Stok hareketi kayıt biçimi geçersiz; SQL eşitlemesi durduruldu.")
            movement_id = str(movement.get("id") or ("legacy-%d" % position))
            movement_payload = json.dumps(movement, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            movements.append((movement_id, movement.get("urunId"), movement.get("urunAd"),
                              movement.get("tip"), _float_or_none(movement.get("miktar")),
                              movement.get("tarih"), movement.get("kaynak"), movement.get("aciklama"),
                              movement_payload, position))
        thresholds = []
        for position, (product_code, value) in enumerate(stock.get("esikler", {}).items()):
            thresholds.append((str(product_code), _float_or_none(value),
                               json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
                               position))
        conn.executemany("""INSERT INTO stock_movements
            (id,product_id,product_name,movement_type,quantity,movement_date,source,description,payload,position)
            VALUES(?,?,?,?,?,?,?,?,?,?)""", movements)
        conn.executemany("INSERT INTO stock_thresholds(product_code,threshold,payload,position) VALUES(?,?,?,?)", thresholds)

    if "lumispac_raw_materials.json" in names:
        raw = source_document("lumispac_raw_materials.json", {})
        if not isinstance(raw, dict):
            raise StoreError("Hammadde belgesi sözlük biçiminde değil; SQL eşitlemesi durduruldu.")
        materials = raw.get("materials", [])
        suppliers = raw.get("suppliers", [])
        purchases = raw.get("purchases", [])
        movements = raw.get("stock_movements", [])
        if not all(isinstance(value, list) for value in (materials, suppliers, purchases, movements)):
            raise StoreError("Hammadde/satın alma listesi geçersiz; SQL eşitlemesi durduruldu.")
        sync_metadata("lumispac_raw_materials.json", raw,
                      {"materials", "suppliers", "purchases", "stock_movements", "recipes", "history"})
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for table in ("raw_purchase_lines", "raw_purchase_payments",
                      "raw_material_stock_movements", "raw_material_purchases",
                      "raw_materials", "suppliers",
                      "raw_material_history", "material_recipe_lines", "material_recipes"):
            conn.execute("DELETE FROM %s" % table)
        material_rows, supplier_rows, purchase_rows = [], [], []
        line_rows, payment_rows, movement_rows = [], [], []
        history_rows, recipe_rows, recipe_line_rows = [], [], []
        for position, item in enumerate(materials):
            if not isinstance(item, dict) or not item.get("id") or not item.get("code"):
                raise StoreError("Hammadde kimliği/kodu eksik; SQL eşitlemesi durduruldu.")
            material_rows.append((str(item["id"]), str(item["code"]), str(item.get("name") or ""),
                                  item.get("material_type"), item.get("unit"),
                                  _float_or_none(item.get("price_per_kg")), int(bool(item.get("active", True))),
                                  json.dumps(item, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
                                  position, now))
        for position, item in enumerate(suppliers):
            if not isinstance(item, dict) or not item.get("id"):
                raise StoreError("Tedarikçi kimliği eksik; SQL eşitlemesi durduruldu.")
            supplier_rows.append((str(item["id"]), str(item.get("name") or ""),
                                  int(bool(item.get("active", True))),
                                  json.dumps(item, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
                                  position, now))
        for position, item in enumerate(purchases):
            if not isinstance(item, dict) or not item.get("id"):
                raise StoreError("Satın alma kimliği eksik; SQL eşitlemesi durduruldu.")
            item_lines, item_payments = item.get("lines", []), item.get("payments", [])
            if not isinstance(item_lines, list) or not isinstance(item_payments, list):
                raise StoreError("Satın alma kalem/ödeme listesi geçersiz; SQL eşitlemesi durduruldu.")
            header = {key: value for key, value in item.items() if key not in {"lines", "payments"}}
            header["_sql_has_lines"] = "lines" in item
            header["_sql_has_payments"] = "payments" in item
            purchase_rows.append((str(item["id"]), item.get("supplier_id"), item.get("supplier_name"),
                                  item.get("document_no"), item.get("date"), item.get("status"),
                                  _float_or_none(item.get("total")), item.get("receipt_id"),
                                  json.dumps(header, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
                                  position, now))
            for line_position, line in enumerate(item_lines):
                if not isinstance(line, dict):
                    raise StoreError("Satın alma kalemi geçersiz; SQL eşitlemesi durduruldu.")
                line_rows.append((str(item["id"]), line_position, line.get("material_id"),
                                  line.get("material_code"), line.get("material_name"),
                                  _float_or_none(line.get("quantity_kg")), line.get("unit"),
                                  _float_or_none(line.get("unit_price")), _float_or_none(line.get("line_total")),
                                  json.dumps(line, ensure_ascii=False, separators=(",", ":"), allow_nan=False)))
            for payment_position, payment in enumerate(item_payments):
                if not isinstance(payment, dict):
                    raise StoreError("Satın alma ödeme kaydı geçersiz; SQL eşitlemesi durduruldu.")
                payment_rows.append((str(item["id"]), str(payment.get("id") or payment_position),
                                     _float_or_none(payment.get("amount")), payment.get("currency"),
                                     payment.get("date"), payment.get("method"), payment.get("idempotency_key"),
                                     json.dumps(payment, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
                                     payment_position))
        for position, movement in enumerate(movements):
            if not isinstance(movement, dict) or not movement.get("id"):
                raise StoreError("Hammadde stok hareketi kimliği eksik; SQL eşitlemesi durduruldu.")
            movement_rows.append((str(movement["id"]), movement.get("purchase_id"), movement.get("material_id"),
                                  movement.get("material_code"), movement.get("type"),
                                  _float_or_none(movement.get("quantity_kg")), movement.get("unit"),
                                  _float_or_none(movement.get("unit_price")), movement.get("previous_status"),
                                  movement.get("new_status"), movement.get("at"), movement.get("idempotency_key"),
                                  json.dumps(movement, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
                                  position))
        for position, event in enumerate(raw.get("history", [])):
            if not isinstance(event, dict):
                raise StoreError("Hammadde geçmiş kaydı geçersiz; SQL eşitlemesi durduruldu.")
            history_rows.append(("raw-history-%d" % position, position, event.get("action"),
                                 event.get("at"), event.get("user_id"),
                                 json.dumps(event, ensure_ascii=False, separators=(",", ":"), allow_nan=False)))
        for position, recipe in enumerate(raw.get("recipes", [])):
            if not isinstance(recipe, dict) or not recipe.get("id") or not recipe.get("product_code"):
                raise StoreError("Reçete kimliği/ürün kodu eksik; SQL eşitlemesi durduruldu.")
            lines = recipe.get("lines", [])
            if not isinstance(lines, list):
                raise StoreError("Reçete satırları geçersiz; SQL eşitlemesi durduruldu.")
            parent = {key: value for key, value in recipe.items() if key != "lines"}
            parent["_sql_has_lines"] = "lines" in recipe
            recipe_rows.append((str(recipe["id"]), str(recipe["product_code"]),
                                int(bool(recipe.get("active", True))), recipe.get("created_at"),
                                recipe.get("updated_at"), json.dumps(parent, ensure_ascii=False,
                                separators=(",", ":"), allow_nan=False), position))
            for line_position, line in enumerate(lines):
                if not isinstance(line, dict):
                    raise StoreError("Reçete satırı geçersiz; SQL eşitlemesi durduruldu.")
                recipe_line_rows.append((str(recipe["id"]), line_position, line.get("material_id"),
                    line.get("material_code"), line.get("material_name"),
                    _float_or_none(line.get("kg_per_box")),
                    json.dumps(line, ensure_ascii=False, separators=(",", ":"), allow_nan=False)))
        conn.executemany("INSERT INTO raw_materials(id,code,name,material_type,unit,price_per_kg,active,payload,position,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)", material_rows)
        conn.executemany("INSERT INTO suppliers(id,name,active,payload,position,updated_at) VALUES(?,?,?,?,?,?)", supplier_rows)
        conn.executemany("INSERT INTO raw_material_purchases(id,supplier_id,supplier_name,document_no,purchase_date,status,total,receipt_id,payload,position,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", purchase_rows)
        conn.executemany("INSERT INTO raw_purchase_lines(purchase_id,line_position,material_id,material_code,material_name,quantity_kg,unit,unit_price,line_total,payload) VALUES(?,?,?,?,?,?,?,?,?,?)", line_rows)
        conn.executemany("INSERT INTO raw_purchase_payments(purchase_id,payment_id,amount,currency,payment_date,method,idempotency_key,payload,position) VALUES(?,?,?,?,?,?,?,?,?)", payment_rows)
        conn.executemany("INSERT INTO raw_material_stock_movements(id,purchase_id,material_id,material_code,movement_type,quantity_kg,unit,unit_price,previous_status,new_status,occurred_at,idempotency_key,payload,position) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", movement_rows)
        conn.executemany("INSERT INTO raw_material_history(event_id,event_position,action,occurred_at,user_id,payload) VALUES(?,?,?,?,?,?)", history_rows)
        conn.executemany("INSERT INTO material_recipes(id,product_code,active,created_at,updated_at,payload,position) VALUES(?,?,?,?,?,?,?)", recipe_rows)
        conn.executemany("INSERT INTO material_recipe_lines(recipe_id,line_position,material_id,material_code,material_name,kg_per_box,payload) VALUES(?,?,?,?,?,?,?)", recipe_line_rows)

    if "lumispac_uretim.json" in names:
        production = source_document("lumispac_uretim.json", {})
        list_keys = ("downtime_reasons", "jobs", "receipts", "reason_history", "recycled_movements")
        if not isinstance(production, dict) or any(not isinstance(production.get(key, []), list) for key in list_keys):
            raise StoreError("Üretim belgesi veya listeleri geçersiz; SQL eşitlemesi durduruldu.")
        sync_metadata("lumispac_uretim.json", production,
                      {"downtime_reasons", "reason_history", "recycled_movements", "jobs", "receipts"})
        for table in ("production_runs", "production_job_history", "production_receipt_history",
                      "production_reason_history", "production_receipts", "production_jobs",
                      "downtime_reasons", "recycled_movements"):
            conn.execute("DELETE FROM %s" % table)
        reason_rows, job_rows, run_rows, job_history_rows = [], [], [], []
        receipt_rows, receipt_history_rows, reason_history_rows, recycled_rows = [], [], [], []
        for position, item in enumerate(production.get("downtime_reasons", [])):
            if not isinstance(item, dict) or not item.get("id"):
                raise StoreError("Duruş nedeni kimliği eksik; SQL eşitlemesi durduruldu.")
            reason_rows.append((str(item["id"]), str(item.get("name") or ""), int(bool(item.get("active", True))),
                                json.dumps(item, ensure_ascii=False, separators=(",", ":"), allow_nan=False), position))
        for position, job in enumerate(production.get("jobs", [])):
            if not isinstance(job, dict) or not job.get("id"):
                raise StoreError("Üretim işi kimliği eksik; SQL eşitlemesi durduruldu.")
            runs, history = job.get("runs", []), job.get("history", [])
            if not isinstance(runs, list) or not isinstance(history, list):
                raise StoreError("Üretim işi çalışma/geçmiş listesi geçersiz; SQL eşitlemesi durduruldu.")
            parent = {key: value for key, value in job.items() if key not in {"runs", "history"}}
            parent["_sql_has_runs"] = "runs" in job
            parent["_sql_has_history"] = "history" in job
            job_rows.append((str(job["id"]), job.get("product_code"), job.get("product_name"), job.get("status"),
                             _float_or_none(job.get("planned_qty")), _float_or_none(job.get("produced_qty")),
                             _float_or_none(job.get("scrap_qty")), _float_or_none(job.get("usable_qty")),
                             _text_or_json(job.get("machine")), _text_or_json(job.get("mold")),
                             job.get("source_type"), job.get("last_run_id"),
                             json.dumps(parent, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
                             position, job.get("updated_at")))
            for run_position, run in enumerate(runs):
                if not isinstance(run, dict):
                    raise StoreError("Üretim çalışma kaydı geçersiz; SQL eşitlemesi durduruldu.")
                run_rows.append((str(job["id"]), run_position, run.get("id"),
                                 _float_or_none(run.get("produced_qty")), _float_or_none(run.get("scrap_qty")),
                                 _float_or_none(run.get("usable_qty")), run.get("created_at"),
                                 json.dumps(run, ensure_ascii=False, separators=(",", ":"), allow_nan=False)))
            for history_position, event in enumerate(history):
                if not isinstance(event, dict):
                    raise StoreError("Üretim geçmiş kaydı geçersiz; SQL eşitlemesi durduruldu.")
                job_history_rows.append((str(job["id"]), history_position, event.get("islem"),
                                         event.get("onceki_durum"), event.get("yeni_durum"),
                                         _float_or_none(event.get("miktar")), event.get("zaman"),
                                         event.get("kullanici_id"), event.get("gerekce"),
                                         json.dumps(event, ensure_ascii=False, separators=(",", ":"), allow_nan=False)))
        for position, receipt in enumerate(production.get("receipts", [])):
            if not isinstance(receipt, dict) or not receipt.get("id"):
                raise StoreError("Üretim kabul kaydı kimliği eksik; SQL eşitlemesi durduruldu.")
            history = receipt.get("history", [])
            if not isinstance(history, list):
                raise StoreError("Üretim kabul geçmişi geçersiz; SQL eşitlemesi durduruldu.")
            parent = {key: value for key, value in receipt.items() if key != "history"}
            parent["_sql_has_history"] = "history" in receipt
            receipt_rows.append((str(receipt["id"]), receipt.get("job_id"), receipt.get("run_id"),
                                 receipt.get("product_code"), receipt.get("product_name"),
                                 _float_or_none(receipt.get("quantity")), receipt.get("status"),
                                 receipt.get("decided_at"),
                                 json.dumps(parent, ensure_ascii=False, separators=(",", ":"), allow_nan=False), position))
            for history_position, event in enumerate(history):
                if not isinstance(event, dict):
                    raise StoreError("Üretim kabul geçmiş kaydı geçersiz; SQL eşitlemesi durduruldu.")
                receipt_history_rows.append((str(receipt["id"]), history_position, event.get("islem"),
                                             event.get("onceki_durum"), event.get("yeni_durum"), event.get("zaman"),
                                             event.get("kullanici_id"), event.get("gerekce"),
                                             json.dumps(event, ensure_ascii=False, separators=(",", ":"), allow_nan=False)))
        for position, event in enumerate(production.get("reason_history", [])):
            if not isinstance(event, dict):
                raise StoreError("Üretim neden geçmiş kaydı geçersiz; SQL eşitlemesi durduruldu.")
            reason_history_rows.append((event.get("islem"), event.get("onceki_durum"), event.get("yeni_durum"),
                                        _float_or_none(event.get("miktar")), event.get("zaman"),
                                        event.get("kullanici_id"), event.get("gerekce"),
                                        json.dumps(event, ensure_ascii=False, separators=(",", ":"), allow_nan=False), position))
        for position, movement in enumerate(production.get("recycled_movements", [])):
            if not isinstance(movement, dict):
                raise StoreError("Geri dönüşüm hareketi geçersiz; SQL eşitlemesi durduruldu.")
            movement_id = str(movement.get("id") or ("legacy-%d" % position))
            recycled_rows.append((movement_id, movement.get("type"), _float_or_none(movement.get("quantity")),
                                  movement.get("at"), movement.get("user_id"), movement.get("reason"),
                                  json.dumps(movement, ensure_ascii=False, separators=(",", ":"), allow_nan=False), position))
        conn.executemany("INSERT INTO downtime_reasons(id,name,active,payload,position) VALUES(?,?,?,?,?)", reason_rows)
        conn.executemany("INSERT INTO production_jobs(id,product_code,product_name,status,planned_qty,produced_qty,scrap_qty,usable_qty,machine,mold,source_type,last_run_id,payload,position,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", job_rows)
        conn.executemany("INSERT INTO production_runs(job_id,run_position,id,produced_qty,scrap_qty,usable_qty,created_at,payload) VALUES(?,?,?,?,?,?,?,?)", run_rows)
        conn.executemany("INSERT INTO production_job_history(job_id,history_position,action,previous_status,new_status,quantity,occurred_at,user_id,reason,payload) VALUES(?,?,?,?,?,?,?,?,?,?)", job_history_rows)
        conn.executemany("INSERT INTO production_receipts(id,job_id,run_id,product_code,product_name,quantity,status,decided_at,payload,position) VALUES(?,?,?,?,?,?,?,?,?,?)", receipt_rows)
        conn.executemany("INSERT INTO production_receipt_history(receipt_id,history_position,action,previous_status,new_status,occurred_at,user_id,reason,payload) VALUES(?,?,?,?,?,?,?,?,?)", receipt_history_rows)
        conn.executemany("INSERT INTO production_reason_history(action,previous_status,new_status,quantity,occurred_at,user_id,reason,payload,position) VALUES(?,?,?,?,?,?,?,?,?)", reason_history_rows)
        conn.executemany("INSERT INTO recycled_movements(id,movement_type,quantity,occurred_at,user_id,reason,payload,position) VALUES(?,?,?,?,?,?,?,?)", recycled_rows)

    if "lumispac_finans.json" in names:
        finance = source_document("lumispac_finans.json", {})
        entries = finance.get("kayitlar", []) if isinstance(finance, dict) else None
        categories = finance.get("kategoriler", {}) if isinstance(finance, dict) else None
        if not isinstance(entries, list) or not isinstance(categories, dict):
            raise StoreError("Finans kaydı/kategori yapısı geçersiz; SQL eşitlemesi durduruldu.")
        sync_metadata("lumispac_finans.json", finance, {"kayitlar", "kategoriler"})
        conn.execute("DELETE FROM finance_entries")
        conn.execute("DELETE FROM finance_categories")
        entry_rows, category_rows = [], []
        for position, entry in enumerate(entries):
            if not isinstance(entry, dict) or not entry.get("id"):
                raise StoreError("Finans hareket kimliği eksik; SQL eşitlemesi durduruldu.")
            entry_rows.append((str(entry["id"]), entry.get("no"), entry.get("tip"),
                               _float_or_none(entry.get("tutar")), entry.get("tarih"),
                               entry.get("kategori"), entry.get("musteri"), entry.get("odeme"),
                               entry.get("aciklama"),
                               json.dumps(entry, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
                               position))
        for position, (kind, values) in enumerate(categories.items()):
            category_rows.append((str(kind), json.dumps(values, ensure_ascii=False,
                                  separators=(",", ":"), allow_nan=False), position))
        conn.executemany("INSERT INTO finance_entries(id,number,entry_type,amount,entry_date,category,customer,payment_method,description,payload,position) VALUES(?,?,?,?,?,?,?,?,?,?,?)", entry_rows)
        conn.executemany("INSERT INTO finance_categories(category_type,payload,position) VALUES(?,?,?)", category_rows)

    if "lumispac_approvals.json" in names:
        approvals = source_document("lumispac_approvals.json", [])
        if not isinstance(approvals, list):
            raise StoreError("Onay belgesi liste biçiminde değil; SQL eşitlemesi durduruldu.")
        conn.execute("DELETE FROM approval_requests")
        approval_rows = []
        for position, approval in enumerate(approvals):
            if not isinstance(approval, dict) or not approval.get("id"):
                raise StoreError("Onay talebi kimliği eksik; SQL eşitlemesi durduruldu.")
            approval_rows.append((str(approval["id"]), approval.get("isteyen_id"), approval.get("isteyen"),
                                  approval.get("isteyen_departman"), approval.get("method"),
                                  approval.get("path"), approval.get("durum"), approval.get("olusturma"),
                                  approval.get("ozet"), approval.get("payload_hash"),
                                  json.dumps(approval, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
                                  position))
        conn.executemany("INSERT INTO approval_requests(id,requester_id,requester_name,requester_department,method,path,status,created_at,summary,payload_hash,payload,position) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", approval_rows)

    if "lumispac_audit.json" in names:
        _sync_append_only_events(conn, "audit_events", source_document("lumispac_audit.json", []))

    if "lumispac_geri_alma_islemleri.json" in names:
        _sync_append_only_events(conn, "undo_operation_events", source_document("lumispac_geri_alma_islemleri.json", []))

    if "lumispac_geri_alma.json" in names:
        actions = source_document("lumispac_geri_alma.json", [])
        if not isinstance(actions, list):
            raise StoreError("Geri alma belgesi liste biçiminde değil; SQL eşitlemesi durduruldu.")
        conn.execute("DELETE FROM undo_changes")
        conn.execute("DELETE FROM undo_actions")
        action_rows, change_rows = [], []
        for position, action in enumerate(actions):
            if not isinstance(action, dict) or not action.get("id"):
                raise StoreError("Geri alma kaydı kimliği eksik; SQL eşitlemesi durduruldu.")
            changes = action.get("degisiklikler", [])
            if not isinstance(changes, list):
                raise StoreError("Geri alma değişiklik listesi geçersiz; SQL eşitlemesi durduruldu.")
            parent = {key: value for key, value in action.items() if key != "degisiklikler"}
            parent["_sql_has_changes"] = "degisiklikler" in action
            action_rows.append((str(action["id"]), action.get("tur"), action.get("durum"),
                                action.get("kullanici_id"), action.get("kullanici_adi"),
                                action.get("zaman"), action.get("aciklama"),
                                json.dumps(parent, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
                                position))
            for change_position, change in enumerate(changes):
                if not isinstance(change, dict):
                    raise StoreError("Geri alma değişikliği kayıt biçimi geçersiz; SQL eşitlemesi durduruldu.")
                previous = change.get("onceki")
                following = change.get("sonraki")
                change_rows.append((str(action["id"]), change_position, change.get("kayit_id"),
                                    _float_or_none(change.get("onceki_sira")),
                                    _float_or_none(change.get("sonraki_sira")),
                                    json.dumps(previous, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
                                    if "onceki" in change else None,
                                    json.dumps(following, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
                                    if "sonraki" in change else None,
                                    json.dumps(change, ensure_ascii=False, separators=(",", ":"), allow_nan=False)))
        conn.executemany("INSERT INTO undo_actions(id,action_type,status,user_id,username,occurred_at,description,payload,position) VALUES(?,?,?,?,?,?,?,?,?)", action_rows)
        conn.executemany("INSERT INTO undo_changes(undo_id,change_position,record_id,previous_order,next_order,previous_payload,next_payload,payload) VALUES(?,?,?,?,?,?,?,?)", change_rows)


def managed_json_path(path):
    config = _settings()
    if config.STORAGE_BACKEND != "sqlite":
        return False
    candidate = Path(path).resolve()
    root = Path(config.BASE).resolve()
    return candidate.parent == root and candidate.name.startswith("lumispac_") and candidate.suffix == ".json"


def _connect(db_path=None):
    config = _settings()
    if getattr(config, "STORAGE_BACKEND", "sqlite") in ("postgres", "postgresql"):
        if db_path is not None:
            raise StoreError("PostgreSQL bağlantısına SQLite dosya yolu verilemez.")
        from postgres_connection import connect
        return connect(getattr(config, "DATABASE_URL", ""))
    path = Path(db_path or database_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=20.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=20000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=FULL")
    return conn


def _has_table(conn, name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _order_payment_order(conn):
    """Prefer portable explicit order; retain reads for schemas awaiting v17."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(order_payments)")}
    return "position,payment_id" if "position" in columns else "rowid"


def _retire_document_bridge(conn):
    """Verify every known document against SQL, archive unknown imports, then drop the bridge."""
    if not _has_table(conn, "data_documents"):
        return
    source = conn.execute("SELECT value FROM app_metadata WHERE key='relational_source'").fetchone()
    if not source or source[0] != "1":
        raise MigrationError("JSON köprüsü kapatılamadı; ilişkisel kaynak doğrulanmamış.")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for row in conn.execute("SELECT name,payload,sha256,updated_at FROM data_documents ORDER BY name").fetchall():
        if row["name"] not in RELATIONAL_DOCUMENTS:
            if hashlib.sha256(row["payload"].encode("utf-8")).hexdigest() != row["sha256"]:
                raise MigrationError("Arşivlenecek eski belgenin özeti uyuşmuyor: %s" % row["name"])
            conn.execute("""
                INSERT INTO legacy_document_archive(name,payload,sha256,updated_at,archived_at)
                VALUES(?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET payload=excluded.payload,
                sha256=excluded.sha256,updated_at=excluded.updated_at,archived_at=excluded.archived_at
            """, (row["name"], row["payload"], row["sha256"], row["updated_at"], now))
            continue
        if hashlib.sha256(row["payload"].encode("utf-8")).hexdigest() != row["sha256"]:
            raise MigrationError("Köprü belgesinin özeti uyuşmuyor: %s" % row["name"])
        expected = json.loads(row["payload"])
        projected = _read_relational_document(conn, row["name"], expected)
        if projected != expected:
            raise MigrationError("İlişkisel parite doğrulanamadı; köprü korunuyor: %s" % row["name"])
    conn.execute("DROP TABLE data_documents")
    conn.execute("INSERT OR REPLACE INTO app_metadata(key,value) VALUES('document_bridge_retired','1')")
    conn.execute("DELETE FROM app_metadata WHERE key='document_bridge_retirement_pending'")


def initialize(db_path=None, source_dir=None, documents_source=None, documents_target=None):
    """Create the store and import every valid lumispac_*.json exactly once."""
    config = _settings()
    source = Path(source_dir or config.BASE)
    conn = _connect(db_path)
    imported = 0
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        import db_migrations
        existing_tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        previous_schema_version = (conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] or 0
                                   if "schema_migrations" in existing_tables else 0)
        db_migrations.apply_pending(conn)
        current_schema_version = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] or 0
        conn.execute("BEGIN IMMEDIATE")
        migration_done = conn.execute(
            "SELECT value FROM app_metadata WHERE key='migration_complete'"
        ).fetchone()
        relational_source = conn.execute(
            "SELECT value FROM app_metadata WHERE key='relational_source'"
        ).fetchone()
        needs_initial_projection = (migration_done is None or migration_done[0] != "1" or
                                    (current_schema_version > previous_schema_version and relational_source is None) or
                                    (current_schema_version >= 15 and relational_source is None))
        count = conn.execute("SELECT COUNT(*) FROM data_documents").fetchone()[0] if _has_table(conn, "data_documents") else 0
        if not migration_done and count == 0:
            pending = []
            for legacy in sorted(source.glob("lumispac_*.json")):
                try:
                    raw = legacy.read_text(encoding="utf-8")
                    value = json.loads(raw)
                    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
                except (OSError, UnicodeError, ValueError) as exc:
                    raise MigrationError(
                        "SQL geçişi durduruldu; kaynak JSON korunuyor: %s" % legacy.name
                    ) from exc
                pending.append((legacy.name, payload,
                                hashlib.sha256(payload.encode("utf-8")).hexdigest(),
                                datetime.now(timezone.utc).isoformat(timespec="seconds")))
            if not pending:
                raise MigrationError("SQL geçişi durduruldu; aktarılacak kaynak JSON dosyası bulunamadı.")
            conn.executemany(
                "INSERT INTO data_documents(name,payload,sha256,updated_at) VALUES(?,?,?,?)",
                pending,
            )
            imported = len(pending)
            conn.execute(
                "INSERT OR REPLACE INTO app_metadata(key,value) VALUES(?,?)",
                ("migration_source", str(source.resolve())),
            )
        # Import is a one-time operation. Never repopulate a deliberately empty
        # database from stale JSON mirrors after the first successful startup.
        conn.execute(
            "INSERT OR REPLACE INTO app_metadata(key,value) VALUES('migration_complete','1')"
        )
        if needs_initial_projection:
            _sync_relational_documents(conn, RELATIONAL_DOCUMENTS)
        if current_schema_version >= 15:
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            conn.executemany("INSERT OR IGNORE INTO relational_document_registry(document_name,registered_at) VALUES(?,?)",
                             [(name, now) for name in RELATIONAL_DOCUMENTS])
            conn.execute("INSERT OR REPLACE INTO app_metadata(key,value) VALUES('relational_source','1')")
        if current_schema_version >= 16:
            _retire_document_bridge(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    if documents_source is None and config.STORAGE_BACKEND == "sqlite":
        documents_source = source / "hammadde_belgeleri"
    if documents_target is None and config.STORAGE_BACKEND == "sqlite":
        documents_target = config.RAW_DOCUMENT_DIR
    if documents_source and documents_target:
        src, dst = Path(documents_source), Path(documents_target)
        if src.exists() and src.resolve() != dst.resolve():
            for item in src.rglob("*"):
                if not item.is_file():
                    continue
                rel = item.relative_to(src)
                target = dst / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    shutil.copy2(item, target)

    active_db = str(Path(db_path or database_path()).resolve())
    verified = integrity_check(active_db)
    if not verified["ok"]:
        raise StoreError("SQLite veritabanı bütünlük kontrolünden geçmedi; uygulama güvenli modda durduruldu.")
    _initialized.add(active_db)
    return {"imported_documents": imported, "database": active_db}


def ensure_initialized():
    if _settings().STORAGE_BACKEND in ("postgres", "postgresql"):
        import postgres_store
        return postgres_store.ensure_initialized()
    active_db = str(Path(database_path()).resolve())
    if active_db not in _initialized:
        initialize()


def _read_relational_document(conn, name, default=None):
    """Rebuild a legacy service document from relational rows without a mirror."""
    base = default
    if name == "lumispac_data.json":
        return [json.loads(row[0]) for row in conn.execute(
            "SELECT payload FROM products ORDER BY position,id")]
    if name == "lumispac_dealers.json":
        return [json.loads(row[0]) for row in conn.execute(
            "SELECT payload FROM dealers ORDER BY position,id")]
    if name == "lumispac_settings.json":
        result = dict(base or {})
        result.update({row[0]: json.loads(row[1]) for row in conn.execute(
            "SELECT setting_key,value_json FROM application_settings ORDER BY position,setting_key")})
        return result
    if name == "lumispac_users.json":
        return _identity_projection(conn, base if isinstance(base, dict) else {})
    if name == "lumispac_stok.json":
        return _stock_projection(conn, base if isinstance(base, dict) else {})
    if name == "lumispac_raw_materials.json":
        return _raw_material_projection(conn, base if isinstance(base, dict) else {})
    if name == "lumispac_uretim.json":
        source = _document_metadata_projection(conn, name, base if isinstance(base, dict) else {})
        for key in ("downtime_reasons", "jobs", "receipts", "reason_history", "recycled_movements"):
            source.setdefault(key, [])
        return _production_projection(conn, source)
    if name == "lumispac_finans.json":
        result = dict(base) if isinstance(base, dict) else {}
        result["kayitlar"] = [json.loads(row[0]) for row in conn.execute(
            "SELECT payload FROM finance_entries ORDER BY position,id")]
        result["kategoriler"] = {row[0]: json.loads(row[1]) for row in conn.execute(
            "SELECT category_type,payload FROM finance_categories ORDER BY position,category_type")}
        return result
    if name == "lumispac_approvals.json":
        return [json.loads(row[0]) for row in conn.execute(
            "SELECT payload FROM approval_requests ORDER BY position,id")]
    if name in {"lumispac_audit.json", "lumispac_geri_alma.json",
                "lumispac_geri_alma_islemleri.json"}:
        return _audit_undo_projection(conn, name, base if base is not None else [])
    if name in {"lumispac_orders.json", "lumispac_quotes.json"}:
        table = "orders" if name == "lumispac_orders.json" else "quotes"
        line_table = "order_lines" if table == "orders" else "quote_lines"
        projected = []
        for header in conn.execute("SELECT id,payload FROM %s ORDER BY position,id" % table):
            record = json.loads(header["payload"])
            has_lines = record.pop("_sql_has_lines", True)
            has_payments = record.pop("_sql_has_payments", table == "orders")
            child_column = "order_id" if table == "orders" else "quote_id"
            if has_lines:
                record["lines"] = [json.loads(row[0]) for row in conn.execute(
                    "SELECT payload FROM %s WHERE %s=? ORDER BY line_position" % (line_table, child_column),
                    (header["id"],))]
            if table == "orders" and has_payments:
                record["payments"] = [json.loads(row[0]) for row in conn.execute(
                    "SELECT payload FROM order_payments WHERE order_id=? ORDER BY " + _order_payment_order(conn),
                    (header["id"],))]
            projected.append(record)
        return projected
    return base


def _read_document_snapshot(conn, name, default):
    """Read from SQL first and use an existing mirror only as a parity check."""
    relational_source = conn.execute(
        "SELECT value FROM app_metadata WHERE key='relational_source'"
    ).fetchone()
    if relational_source and relational_source[0] == "1" and name in RELATIONAL_DOCUMENTS:
        return _read_relational_document(conn, name, default)
    row = (conn.execute("SELECT payload,sha256 FROM data_documents WHERE name=?", (name,)).fetchone()
           if _has_table(conn, "data_documents") else None)
    if row is None and _has_table(conn, "legacy_document_archive"):
        row = conn.execute("SELECT payload,sha256 FROM legacy_document_archive WHERE name=?", (name,)).fetchone()
    if row is None:
        return _read_relational_document(conn, name, default)
    if hashlib.sha256(row["payload"].encode("utf-8")).hexdigest() != row["sha256"]:
        raise StoreError("SQLite kayıt bütünlük özeti uyuşmuyor: %s" % name)
    source = json.loads(row["payload"])
    projected = _read_relational_document(conn, name, source)
    if projected != source:
        raise StoreError("İlişkisel kayıt ile geçiş belgesi uyuşmuyor: %s" % name)
    return projected


def read_document(path, default=None):
    ensure_initialized()
    name = Path(path).name
    conn = _connect()
    try:
        relational_source = conn.execute(
            "SELECT value FROM app_metadata WHERE key='relational_source'"
        ).fetchone()
        if relational_source and relational_source[0] == "1" and name in RELATIONAL_DOCUMENTS:
            return _read_relational_document(conn, name, default)
        row = (conn.execute("SELECT payload,sha256 FROM data_documents WHERE name=?", (name,)).fetchone()
               if _has_table(conn, "data_documents") else None)
        if row is None and _has_table(conn, "legacy_document_archive"):
            row = conn.execute("SELECT payload,sha256 FROM legacy_document_archive WHERE name=?", (name,)).fetchone()
        if row is None:
            return _read_relational_document(conn, name, default)
        payload = row["payload"]
        if hashlib.sha256(payload.encode("utf-8")).hexdigest() != row["sha256"]:
            raise StoreError("SQLite kayıt bütünlük özeti uyuşmuyor: %s" % name)
        if name in {"lumispac_data.json", "lumispac_dealers.json", "lumispac_users.json", "lumispac_settings.json",
                    "lumispac_orders.json", "lumispac_quotes.json", "lumispac_stok.json",
                    "lumispac_raw_materials.json", "lumispac_uretim.json",
                    "lumispac_finans.json", "lumispac_approvals.json",
                    "lumispac_audit.json", "lumispac_geri_alma.json",
                    "lumispac_geri_alma_islemleri.json"}:
            version = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] or 0
            required_version = (13 if name == "lumispac_settings.json" else
                                11 if name == "lumispac_users.json" else
                                10 if name in {"lumispac_audit.json", "lumispac_geri_alma.json",
                                               "lumispac_geri_alma_islemleri.json"} else
                                9 if name in {"lumispac_finans.json", "lumispac_approvals.json"} else
                                8 if name == "lumispac_uretim.json" else
                                7 if name == "lumispac_raw_materials.json" else
                                6 if name == "lumispac_stok.json" else
                                4 if name == "lumispac_users.json" else
                                5 if name in {"lumispac_orders.json", "lumispac_quotes.json"} else 3)
            if version >= required_version:
                if name == "lumispac_settings.json":
                    source = json.loads(payload)
                    projected = {item["setting_key"]: json.loads(item["value_json"])
                                 for item in conn.execute(
                                     "SELECT setting_key,value_json FROM application_settings ORDER BY position,setting_key")}
                    if projected != source:
                        raise StoreError("İlişkisel ayar kayıtları ile geçiş belgesi uyuşmuyor.")
                    return projected
                if name in {"lumispac_audit.json", "lumispac_geri_alma.json",
                            "lumispac_geri_alma_islemleri.json"}:
                    source = json.loads(payload)
                    projected = _audit_undo_projection(conn, name, source)
                    if projected != source:
                        raise StoreError("İlişkisel kayıt ile geçiş belgesi uyuşmuyor: %s" % name)
                    return projected
                if name == "lumispac_users.json":
                    source = json.loads(payload)
                    projected = _identity_projection(conn, source)
                    if projected != source:
                        raise StoreError("İlişkisel kayıt ile geçiş belgesi uyuşmuyor: %s" % name)
                    return projected
                if name == "lumispac_stok.json":
                    source = json.loads(payload)
                    projected = _stock_projection(conn, source)
                    if projected != source:
                        raise StoreError("İlişkisel kayıt ile geçiş belgesi uyuşmuyor: %s" % name)
                    return projected
                if name == "lumispac_uretim.json":
                    source = json.loads(payload)
                    projected = _production_projection(conn, source)
                    if projected != source:
                        raise StoreError("İlişkisel kayıt ile geçiş belgesi uyuşmuyor: %s" % name)
                    return projected
                if name == "lumispac_finans.json":
                    source = json.loads(payload)
                    projected = dict(source)
                    projected["kayitlar"] = [json.loads(item[0]) for item in conn.execute(
                        "SELECT payload FROM finance_entries ORDER BY position,id").fetchall()]
                    projected["kategoriler"] = {item[0]: json.loads(item[1]) for item in conn.execute(
                        "SELECT category_type,payload FROM finance_categories ORDER BY position,category_type").fetchall()}
                    if projected != source:
                        raise StoreError("İlişkisel kayıt ile geçiş belgesi uyuşmuyor: %s" % name)
                    return projected
                if name == "lumispac_approvals.json":
                    source = json.loads(payload)
                    projected = [json.loads(item[0]) for item in conn.execute(
                        "SELECT payload FROM approval_requests ORDER BY position,id").fetchall()]
                    if projected != source:
                        raise StoreError("İlişkisel kayıt ile geçiş belgesi uyuşmuyor: %s" % name)
                    return projected
                if name == "lumispac_raw_materials.json":
                    source = json.loads(payload)
                    projected = _raw_material_projection(conn, source)
                    if projected != source:
                        raise StoreError("İlişkisel kayıt ile geçiş belgesi uyuşmuyor: %s" % name)
                    return projected
                if name in {"lumispac_orders.json", "lumispac_quotes.json"}:
                    source = json.loads(payload)
                    table = "orders" if name == "lumispac_orders.json" else "quotes"
                    line_table = "order_lines" if table == "orders" else "quote_lines"
                    projected = []
                    headers = conn.execute("SELECT id,payload FROM %s ORDER BY position,id" % table).fetchall()
                    for header in headers:
                        record = json.loads(header["payload"])
                        has_lines = record.pop("_sql_has_lines", True)
                        has_payments = record.pop("_sql_has_payments", table == "orders")
                        lines = [json.loads(item["payload"]) for item in conn.execute(
                            "SELECT payload FROM %s WHERE %s=? ORDER BY line_position" %
                            (line_table, "order_id" if table == "orders" else "quote_id"),
                            (header["id"],)).fetchall()]
                        if has_lines:
                            record["lines"] = lines
                        if table == "orders" and has_payments:
                            record["payments"] = [json.loads(item["payload"]) for item in conn.execute(
                                "SELECT payload FROM order_payments WHERE order_id=? ORDER BY " + _order_payment_order(conn),
                                (header["id"],)).fetchall()]
                        projected.append(record)
                    if projected != source:
                        raise StoreError("İlişkisel kayıt ile geçiş belgesi uyuşmuyor: %s" % name)
                    return projected
                if name == "lumispac_users.json":
                    source = json.loads(payload)
                    projected = dict(source)
                    for key, table in (("departmanlar", "departments"), ("kullanicilar", "users")):
                        rows = conn.execute("SELECT payload FROM %s ORDER BY position,id" % table).fetchall()
                        projected[key] = [json.loads(item["payload"]) for item in rows]
                    if projected != source:
                        raise StoreError("İlişkisel kayıt ile geçiş belgesi uyuşmuyor: %s" % name)
                    return projected
                table = "products" if name == "lumispac_data.json" else "dealers"
                rows = conn.execute("SELECT payload FROM %s ORDER BY position,id" % table).fetchall()
                projected = [json.loads(item["payload"]) for item in rows]
                if projected != json.loads(payload):
                    raise StoreError("İlişkisel kayıt ile geçiş belgesi uyuşmuyor: %s" % name)
                return projected
    finally:
        conn.close()
    try:
        return json.loads(payload)
    except ValueError as exc:
        raise StoreError("SQLite kaydı çözümlenemedi: %s" % name) from exc


def list_order_records(owner_user_id=None, limit=None, offset=0):
    """Read order rows directly from indexed SQL while preserving document shape.

    When supplied, owner_user_id scopes both the order and its assigned dealer
    in SQL before records are materialized. Optional limit/offset support
    bounded pages without changing existing API response shapes.
    """
    ensure_initialized()
    conn = _connect()
    try:
        sql = "SELECT o.id,o.payload FROM orders o"
        params = []
        if owner_user_id is not None:
            sql += " JOIN dealers d ON d.id=o.dealer_id"
            sql += " WHERE o.owner_user_id=? AND d.owner_user_id=?"
            params.extend((str(owner_user_id), str(owner_user_id)))
        sql += " ORDER BY o.position DESC,o.id DESC"
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend((max(1, min(1000, int(limit))), max(0, int(offset or 0))))
        headers = conn.execute(sql, params).fetchall()
        result = []
        for header in headers:
            record = json.loads(header["payload"])
            has_lines = record.pop("_sql_has_lines", True)
            has_payments = record.pop("_sql_has_payments", True)
            if has_lines:
                record["lines"] = [json.loads(row[0]) for row in conn.execute(
                    "SELECT payload FROM order_lines WHERE order_id=? ORDER BY line_position",
                    (header["id"],)).fetchall()]
            if has_payments:
                record["payments"] = [json.loads(row[0]) for row in conn.execute(
                    "SELECT payload FROM order_payments WHERE order_id=? ORDER BY " + _order_payment_order(conn),
                    (header["id"],)).fetchall()]
            result.append(record)
        return result
    finally:
        conn.close()


def read_raw_material_records(default=None):
    """Rebuild the hammadde/satın alma domain object directly from SQL rows."""
    ensure_initialized()
    conn = _connect()
    try:
        return _raw_material_projection(conn, default or {})
    finally:
        conn.close()


def read_stock_records(default=None):
    """Rebuild inventory movements and thresholds from normalized SQL tables."""
    ensure_initialized()
    conn = _connect()
    try:
        result = dict(default or {})
        for row in conn.execute("""
            SELECT metadata_key,value_json FROM document_metadata
            WHERE document_name='lumispac_stok.json' ORDER BY position,metadata_key
        """):
            result[row["metadata_key"]] = json.loads(row["value_json"])
        result["hareketler"] = [json.loads(row[0]) for row in conn.execute(
            "SELECT payload FROM stock_movements ORDER BY position,id")]
        result["esikler"] = {row[0]: json.loads(row[1]) for row in conn.execute(
            "SELECT product_code,payload FROM stock_thresholds ORDER BY position,product_code")}
        return result
    finally:
        conn.close()


def count_order_records(owner_user_id=None):
    """Count orders under the same SQL ownership scope as list_order_records."""
    ensure_initialized()
    conn = _connect()
    try:
        if owner_user_id is None:
            return conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        return conn.execute("""SELECT COUNT(*) FROM orders o
            JOIN dealers d ON d.id=o.dealer_id
            WHERE o.owner_user_id=? AND d.owner_user_id=?""",
            (str(owner_user_id), str(owner_user_id))).fetchone()[0]
    finally:
        conn.close()


def dashboard_order_totals(owner_user_id=None, month=None):
    """Aggregate count and sales in SQL using the central cancellation rule.

    `net_sales_total` is written with hesap_service.siparis_finans_metrikleri,
    so SQL only sums the already rounded per-order values and never duplicates
    the business formula.
    """
    ensure_initialized()
    conn = _connect()
    try:
        order_columns = {row[1] for row in conn.execute("PRAGMA table_info(orders)")}
        portable_flags = {"is_cancelled", "report_month", "report_date_valid"}.issubset(order_columns)
        if portable_flags:
            cancel_condition = "o.is_cancelled=0"
        else:
            from services.hesap_service import siparis_iptal_mi
            conn.create_function("is_cancelled_order", 1,
                                 lambda status: int(siparis_iptal_mi({"status": status})))
            cancel_condition = "is_cancelled_order(o.status)=0"
        sql = "SELECT COUNT(*),COALESCE(SUM(o.net_sales_total),0) FROM orders o"
        params = []
        if owner_user_id is not None:
            sql += " JOIN dealers d ON d.id=o.dealer_id WHERE o.owner_user_id=? AND d.owner_user_id=? AND " + cancel_condition
            params.extend((str(owner_user_id), str(owner_user_id)))
        else:
            sql += " WHERE " + cancel_condition
        total_count, total_sales = conn.execute(sql, params).fetchone()
        month_count, month_sales = 0, 0.0
        if month:
            if portable_flags:
                month_sql = """SELECT
                    COALESCE(SUM(CASE WHEN o.report_month=? THEN 1 ELSE 0 END),0),
                    COALESCE(SUM(CASE WHEN o.report_month=? AND o.report_date_valid=1
                        THEN o.net_sales_total ELSE 0 END),0) FROM orders o"""
            else:
                month_sql = """SELECT
                    COALESCE(SUM(CASE WHEN substr(o.order_date,1,7)=? THEN 1 ELSE 0 END),0),
                    COALESCE(SUM(CASE WHEN substr(o.order_date,1,7)=?
                        AND date(substr(o.order_date,1,10)) IS NOT NULL
                        THEN o.net_sales_total ELSE 0 END),0) FROM orders o"""
            month_params = [str(month), str(month)]
            if owner_user_id is not None:
                month_sql += " JOIN dealers d ON d.id=o.dealer_id WHERE o.owner_user_id=? AND d.owner_user_id=? AND " + cancel_condition
                month_params.extend((str(owner_user_id), str(owner_user_id)))
            else:
                month_sql += " WHERE " + cancel_condition
            month_count, month_sales = conn.execute(month_sql, month_params).fetchone()
        return {"count": int(total_count), "sales": round(float(total_sales or 0), 2),
                "month_count": int(month_count), "month_sales": round(float(month_sales or 0), 2)}
    finally:
        conn.close()


def list_dealer_records(owner_user_id=None):
    """Read dealer records from normalized SQL with optional owner scoping."""
    ensure_initialized()
    conn = _connect()
    try:
        if owner_user_id is None:
            rows = conn.execute("SELECT payload FROM dealers ORDER BY position,id").fetchall()
        else:
            rows = conn.execute("SELECT payload FROM dealers WHERE owner_user_id=? ORDER BY position,id",
                                (str(owner_user_id),)).fetchall()
        return [json.loads(row[0]) for row in rows]
    finally:
        conn.close()


def list_product_records():
    """Read products from the normalized SQL table in stable order."""
    ensure_initialized()
    conn = _connect()
    try:
        return [json.loads(row[0]) for row in conn.execute(
            "SELECT payload FROM products ORDER BY position,id").fetchall()]
    finally:
        conn.close()


def read_settings_records(default=None):
    """Read application settings from their typed-key SQL table."""
    ensure_initialized()
    conn = _connect()
    try:
        rows = conn.execute("SELECT setting_key,value_json FROM application_settings ORDER BY position,setting_key").fetchall()
        if rows:
            return {row["setting_key"]: json.loads(row["value_json"]) for row in rows}
        exists = conn.execute("SELECT 1 FROM relational_document_registry WHERE document_name='lumispac_settings.json'").fetchone()
        if exists:
            return {}
        exists = conn.execute("SELECT 1 FROM app_metadata WHERE key='migration_complete' AND value='1'").fetchone()
        return {} if exists else ({} if default is None else default)
    finally:
        conn.close()


def _store_mirror_document(conn, name, value, now):
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    conn.execute("""
        INSERT INTO data_documents(name,payload,sha256,updated_at) VALUES(?,?,?,?)
        ON CONFLICT(name) DO UPDATE SET payload=excluded.payload,
            sha256=excluded.sha256,updated_at=excluded.updated_at
    """, (name, payload, digest, now))


def replace_product_records(records):
    """Replace SQL products; retire only the product mirror after parity passes."""
    ensure_initialized()
    if not isinstance(records, list):
        raise StoreError("Ürün listesi geçerli değil.")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    values = []
    ids, codes = set(), set()
    for position, item in enumerate(records):
        if not isinstance(item, dict) or not item.get("id") or not item.get("code"):
            raise StoreError("Ürün kaydının kimliği/kodu eksik; kayıt yapılmadı.")
        product_id, code = str(item["id"]), str(item["code"])
        if product_id in ids or code in codes:
            raise StoreError("Ürün kimliği veya kodu yineleniyor; kayıt yapılmadı.")
        ids.add(product_id); codes.add(code)
        payload = json.dumps(item, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        values.append((product_id, code, str(item.get("name") or ""),
                       _float_or_none(item.get("weight")), _float_or_none(item.get("qty")),
                       _float_or_none(item.get("volume")), _float_or_none(item.get("stock")),
                       _float_or_none(item.get("sale")), int(bool(item.get("active", True))),
                       payload, now, position))
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM products")
        conn.executemany("""
            INSERT INTO products(id,code,name,weight,qty,volume,stock,sale,active,payload,updated_at,position)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """, values)
        actual = [json.loads(row[0]) for row in conn.execute(
            "SELECT payload FROM products ORDER BY position,id").fetchall()]
        if actual != records:
            raise StoreError("Ürün SQL kaydı doğrulanamadı; geçiş aynası korunuyor.")
        if not _retire_verified_document_mirror(conn, "lumispac_data.json", records):
            _store_mirror_document(conn, "lumispac_data.json", records, now)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def replace_dealer_records(records):
    """Replace SQL dealers; retire the dealer mirror only after parity passes."""
    ensure_initialized()
    if not isinstance(records, list):
        raise StoreError("Bayi listesi geçerli değil.")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    values, ids = [], set()
    for position, item in enumerate(records):
        if not isinstance(item, dict) or not item.get("id"):
            raise StoreError("Bayi kimliği eksik; kayıt yapılmadı.")
        dealer_id = str(item["id"])
        if dealer_id in ids:
            raise StoreError("Bayi kimliği yineleniyor; kayıt yapılmadı.")
        ids.add(dealer_id)
        payload = json.dumps(item, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        values.append((dealer_id, str(item.get("name") or ""), item.get("contact"),
                       item.get("phone"), item.get("city"), _float_or_none(item.get("discount")),
                       item.get("owner_user_id"), payload, now, position))
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM dealers")
        conn.executemany("""
            INSERT INTO dealers(id,name,contact,phone,city,discount,owner_user_id,payload,updated_at,position)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, values)
        actual = [json.loads(row[0]) for row in conn.execute(
            "SELECT payload FROM dealers ORDER BY position,id").fetchall()]
        if actual != records:
            raise StoreError("Bayi SQL kayıtları doğrulanamadı; geçiş aynası korunuyor.")
        if not _retire_verified_document_mirror(conn, "lumispac_dealers.json", records):
            _store_mirror_document(conn, "lumispac_dealers.json", records, now)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def replace_settings_records(settings):
    """Replace SQL settings; retire the settings mirror only after parity passes."""
    ensure_initialized()
    if not isinstance(settings, dict):
        raise StoreError("Ayarlar sözlük biçiminde olmalı; kayıt yapılmadı.")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    values = [(str(key), json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False), position, now)
              for position, (key, value) in enumerate(settings.items())]
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM application_settings")
        conn.executemany("""
            INSERT INTO application_settings(setting_key,value_json,position,updated_at)
            VALUES(?,?,?,?)
        """, values)
        actual = {row[0]: json.loads(row[1]) for row in conn.execute(
            "SELECT setting_key,value_json FROM application_settings ORDER BY position,setting_key")}
        if actual != settings:
            raise StoreError("Ayar SQL kayıtları doğrulanamadı; geçiş aynası korunuyor.")
        if not _retire_verified_document_mirror(conn, "lumispac_settings.json", settings):
            _store_mirror_document(conn, "lumispac_settings.json", settings, now)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_quote_records(owner_user_id=None):
    """Read quote headers/lines directly from SQL, enforcing dealer ownership."""
    ensure_initialized()
    conn = _connect()
    try:
        sql = "SELECT q.id,q.payload FROM quotes q"
        params = []
        if owner_user_id is not None:
            sql += " JOIN dealers d ON d.id=q.dealer_id"
            sql += " WHERE q.owner_user_id=? AND d.owner_user_id=?"
            params.extend((str(owner_user_id), str(owner_user_id)))
        sql += " ORDER BY q.position DESC,q.id DESC"
        result = []
        for header in conn.execute(sql, params).fetchall():
            record = json.loads(header["payload"])
            record.pop("_sql_has_payments", None)
            if record.pop("_sql_has_lines", True):
                record["lines"] = [json.loads(row[0]) for row in conn.execute(
                    "SELECT payload FROM quote_lines WHERE quote_id=? ORDER BY line_position",
                    (header["id"],)).fetchall()]
            result.append(record)
        return result
    finally:
        conn.close()


def document_exists(path):
    ensure_initialized()
    name = Path(path).name
    conn = _connect()
    try:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='relational_document_registry'").fetchone():
            if conn.execute("SELECT 1 FROM relational_document_registry WHERE document_name=?", (name,)).fetchone():
                return True
        for table in ("data_documents", "legacy_document_archive"):
            if _has_table(conn, table) and conn.execute(
                    "SELECT 1 FROM %s WHERE name=?" % table, (name,)).fetchone() is not None:
                return True
        return (name in RELATIONAL_DOCUMENTS and conn.execute(
            "SELECT 1 FROM app_metadata WHERE key='migration_complete' AND value='1'").fetchone() is not None)
    finally:
        conn.close()


def _retire_verified_document_mirror(conn, name, expected):
    """Retire one mirror only after its relational reconstruction matches exactly."""
    relational_source = conn.execute(
        "SELECT value FROM app_metadata WHERE key='relational_source'").fetchone()
    if not relational_source or relational_source[0] != "1":
        return False
    projected = _read_relational_document(conn, name, expected)
    if projected != expected:
        raise StoreError("İlişkisel kayıt doğrulanamadı; geçiş aynası korunuyor: %s" % name)
    if _has_table(conn, "data_documents"):
        conn.execute("DELETE FROM data_documents WHERE name=?", (name,))
    conn.execute("INSERT OR REPLACE INTO app_metadata(key,value) VALUES(?, '1')",
                 ("document_mirror_retired:" + name,))
    return True


def _store_compatibility_mirrors(conn, serialized):
    """Persist only documents whose SQL cutover has not retired the mirror."""
    if not _has_table(conn, "data_documents"):
        unsupported = [name for name, *_ in serialized if name not in RELATIONAL_DOCUMENTS]
        if unsupported:
            raise StoreError("İlişkisel SQL kaydı olmayan belge yazılamaz: %s" % ", ".join(unsupported))
        return
    pending = []
    for name, payload, digest, updated_at in serialized:
        retired = conn.execute(
            "SELECT 1 FROM app_metadata WHERE key=? AND value='1'",
            ("document_mirror_retired:" + name,),
        ).fetchone()
        if not retired:
            pending.append((name, payload, digest, updated_at))
    if pending:
        conn.executemany("""
            INSERT INTO data_documents(name,payload,sha256,updated_at) VALUES(?,?,?,?)
            ON CONFLICT(name) DO UPDATE SET payload=excluded.payload,
                sha256=excluded.sha256, updated_at=excluded.updated_at
        """, pending)


def write_documents(values):
    """Atomically update one or more JSON-compatible documents in one SQL transaction."""
    if not values:
        return
    ensure_initialized()
    serialized = []
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for path, value in values.items():
        name = Path(path).name
        if not name.startswith("lumispac_") or not name.endswith(".json"):
            raise ValueError("SQLite veri anahtarı geçersiz: %s" % name)
        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        serialized.append((name, payload, digest, now))
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        _store_compatibility_mirrors(conn, serialized)
        import db_migrations
        version = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
        if version is None or version < 3:
            raise StoreError("Ürün/bayi ilişkisel şeması uygulanmamış; yazma durduruldu.")
        if "lumispac_users.json" in {Path(path).name for path in values} and version < 11:
            raise StoreError("Kullanıcı/departman ilişkisel şeması uygulanmamış; yazma durduruldu.")
        names = {Path(path).name for path in values}
        if names.intersection({"lumispac_orders.json", "lumispac_quotes.json"}) and version < 5:
            raise StoreError("Sipariş/teklif ilişkisel şeması uygulanmamış; yazma durduruldu.")
        if "lumispac_orders.json" in names and version < 12:
            raise StoreError("Sipariş rapor şeması uygulanmamış; yazma durduruldu.")
        if "lumispac_settings.json" in names and version < 13:
            raise StoreError("Ayar ilişkisel şeması uygulanmamış; yazma durduruldu.")
        if "lumispac_stok.json" in names and version < 6:
            raise StoreError("Stok ilişkisel şeması uygulanmamış; yazma durduruldu.")
        if "lumispac_raw_materials.json" in names and version < 7:
            raise StoreError("Hammadde ilişkisel şeması uygulanmamış; yazma durduruldu.")
        if names.intersection({"lumispac_stok.json", "lumispac_raw_materials.json"}) and version < 14:
            raise StoreError("Stok/hammadde metadata ilişkisel şeması uygulanmamış; yazma durduruldu.")
        if "lumispac_uretim.json" in names and version < 8:
            raise StoreError("Üretim ilişkisel şeması uygulanmamış; yazma durduruldu.")
        if names.intersection({"lumispac_finans.json", "lumispac_approvals.json"}) and version < 9:
            raise StoreError("Finans/onay ilişkisel şeması uygulanmamış; yazma durduruldu.")
        if names.intersection({"lumispac_audit.json", "lumispac_geri_alma.json",
                               "lumispac_geri_alma_islemleri.json"}) and version < 10:
            raise StoreError("Denetim/geri alma ilişkisel şeması uygulanmamış; yazma durduruldu.")
        _sync_relational_documents(conn, names, {Path(path).name: value for path, value in values.items()})
        for name in names.intersection({"lumispac_users.json", "lumispac_finans.json",
                                        "lumispac_approvals.json", "lumispac_audit.json",
                                        "lumispac_geri_alma.json", "lumispac_geri_alma_islemleri.json"}):
            _retire_verified_document_mirror(
                conn, name, {Path(path).name: value for path, value in values.items()}[name])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def document_transaction(defaults):
    """Yield a transactionally locked document snapshot for domain mutations.

    The write lock covers both the initial read and the final projection write,
    preventing cross-process lost updates in legacy document-shaped services.
    """
    if not isinstance(defaults, dict) or not defaults:
        raise ValueError("Belge işlemi için varsayılanlar gerekli.")
    ensure_initialized()
    entries = [(Path(path).name, default) for path, default in defaults.items()]
    for name, _ in entries:
        if not name.startswith("lumispac_") or not name.endswith(".json"):
            raise ValueError("SQLite veri anahtarı geçersiz: %s" % name)
    names = {name for name, _ in entries}
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        documents = {}
        for name, default in entries:
            documents[name] = _read_document_snapshot(conn, name, default)
        yield documents
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        serialized = []
        for name in names:
            payload = json.dumps(documents[name], ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            serialized.append((name, payload, hashlib.sha256(payload.encode("utf-8")).hexdigest(), now))
        _store_compatibility_mirrors(conn, serialized)
        version = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] or 0
        if names.intersection({"lumispac_orders.json", "lumispac_quotes.json"}) and version < 5:
            raise StoreError("Sipariş/teklif ilişkisel şeması uygulanmamış; yazma durduruldu.")
        if "lumispac_stok.json" in names and version < 6:
            raise StoreError("Stok ilişkisel şeması uygulanmamış; yazma durduruldu.")
        if "lumispac_raw_materials.json" in names and version < 7:
            raise StoreError("Hammadde ilişkisel şeması uygulanmamış; yazma durduruldu.")
        if names.intersection({"lumispac_stok.json", "lumispac_raw_materials.json"}) and version < 14:
            raise StoreError("Stok/hammadde metadata ilişkisel şeması uygulanmamış; yazma durduruldu.")
        if "lumispac_uretim.json" in names and version < 8:
            raise StoreError("Üretim ilişkisel şeması uygulanmamış; yazma durduruldu.")
        if names.intersection({"lumispac_finans.json", "lumispac_approvals.json"}) and version < 9:
            raise StoreError("Finans/onay ilişkisel şeması uygulanmamış; yazma durduruldu.")
        if names.intersection({"lumispac_audit.json", "lumispac_geri_alma.json",
                               "lumispac_geri_alma_islemleri.json"}) and version < 10:
            raise StoreError("Denetim/geri alma ilişkisel şeması uygulanmamış; yazma durduruldu.")
        if "lumispac_users.json" in names and version < 11:
            raise StoreError("Yetki ilişkisel şeması uygulanmamış; yazma durduruldu.")
        if "lumispac_settings.json" in names and version < 13:
            raise StoreError("Uygulama ayarları ilişkisel şeması uygulanmamış; yazma durduruldu.")
        _sync_relational_documents(conn, names, documents)
        for name in names.intersection({"lumispac_stok.json", "lumispac_raw_materials.json",
                                       "lumispac_uretim.json", "lumispac_audit.json",
                                       "lumispac_geri_alma.json",
                                       "lumispac_geri_alma_islemleri.json"}):
            _retire_verified_document_mirror(conn, name, documents[name])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def mutate_documents(defaults, mutator):
    """Read, change and project selected documents under one write lock.

    This closes the read-modify-write race that exists when a service reads a
    whole JSON-compatible collection and writes it back later. The temporary
    document mirror and all relational projections commit or roll back as one.
    """
    if not isinstance(defaults, dict) or not defaults or not callable(mutator):
        raise ValueError("Belge değişikliği için varsayılanlar ve işlem gerekli.")
    ensure_initialized()
    entries = []
    for path, default in defaults.items():
        name = Path(path).name
        if not name.startswith("lumispac_") or not name.endswith(".json"):
            raise ValueError("SQLite veri anahtarı geçersiz: %s" % name)
        entries.append((name, default))
    names = {name for name, _ in entries}
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        documents = {}
        for name, default in entries:
            documents[name] = _read_document_snapshot(conn, name, default)

        result = mutator(documents)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        serialized = []
        for name in names:
            payload = json.dumps(documents[name], ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            serialized.append((name, payload, hashlib.sha256(payload.encode("utf-8")).hexdigest(), now))
        _store_compatibility_mirrors(conn, serialized)
        version = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] or 0
        if names.intersection({"lumispac_orders.json", "lumispac_quotes.json"}) and version < 5:
            raise StoreError("Sipariş/teklif ilişkisel şeması uygulanmamış; yazma durduruldu.")
        if "lumispac_stok.json" in names and version < 6:
            raise StoreError("Stok ilişkisel şeması uygulanmamış; yazma durduruldu.")
        if "lumispac_raw_materials.json" in names and version < 7:
            raise StoreError("Hammadde ilişkisel şeması uygulanmamış; yazma durduruldu.")
        if names.intersection({"lumispac_stok.json", "lumispac_raw_materials.json"}) and version < 14:
            raise StoreError("Stok/hammadde metadata ilişkisel şeması uygulanmamış; yazma durduruldu.")
        _sync_relational_documents(conn, names, documents)
        for name in names.intersection({"lumispac_orders.json", "lumispac_quotes.json", "lumispac_stok.json",
                                        "lumispac_raw_materials.json", "lumispac_uretim.json",
                                        "lumispac_finans.json", "lumispac_approvals.json",
                                        "lumispac_audit.json", "lumispac_geri_alma.json",
                                        "lumispac_geri_alma_islemleri.json"}):
            _retire_verified_document_mirror(conn, name, documents[name])
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def backup_database(target):
    """Create a consistent snapshot without applying pending migrations first."""
    source_path = Path(database_path())
    if not source_path.is_file():
        raise StoreError("Yedek alınacak SQLite veritabanı bulunamadı.")
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.resolve() == source_path.resolve():
        raise StoreError("Yedek hedefi etkin veritabanı olamaz.")
    descriptor, temporary_name = tempfile.mkstemp(prefix=target_path.name + ".",
                                                  suffix=".tmp", dir=str(target_path.parent))
    os.close(descriptor)
    try:
        source = _connect()
        destination = None
        try:
            destination = sqlite3.connect(temporary_name)
            source.backup(destination)
            check = destination.execute("PRAGMA integrity_check").fetchone()[0]
            if check != "ok":
                raise StoreError("Oluşturulan SQLite yedeği bütünlük kontrolünden geçmedi.")
            destination.commit()
        finally:
            if destination is not None:
                destination.close()
            source.close()
        verified = integrity_check(temporary_name)
        if not verified["ok"]:
            raise StoreError("Oluşturulan SQLite yedeğinin belge/projeksiyon kontrolü başarısız.")
        os.replace(temporary_name, target_path)
        return target_path
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def restore_database(source_path):
    """Restore a verified snapshot into the active DB through SQLite backup API."""
    source_path = Path(source_path)
    if source_path.resolve() == Path(database_path()).resolve():
        raise StoreError("Etkin veritabanı kendi üzerine geri yüklenemez.")
    check = integrity_check(str(source_path))
    if not check["ok"]:
        raise StoreError("Veritabanı yedeği bütünlük kontrolünden geçmedi; geri yükleme durduruldu.")
    source = sqlite3.connect(str(source_path), timeout=20.0)
    destination = _connect()
    try:
        source.backup(destination)
        result = destination.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise StoreError("Geri yüklenen veritabanı bütünlük kontrolünden geçmedi.")
    finally:
        destination.close()
        source.close()
    _initialized.add(str(Path(database_path()).resolve()))
    return check


def integrity_check(db_path=None):
    path = Path(db_path or database_path())
    if not path.is_file():
        return {"ok": False, "integrity": "missing", "documents": 0,
                "invalid_documents": []}
    conn = sqlite3.connect(str(path), timeout=20.0)
    conn.row_factory = sqlite3.Row
    try:
        # Keep the document hashes and relational projections in one SQLite
        # snapshot. Without an explicit read transaction, the background rate
        # poller could update settings between these queries and produce a
        # transient false integrity failure.
        conn.execute("BEGIN")
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        invalid = []
        foreign_key_violations = []
        if "schema_migrations" in tables:
            from db_migrations import _WORKFLOW_FOREIGN_KEYS
            for child, child_key, parent, parent_key in _WORKFLOW_FOREIGN_KEYS:
                if child not in tables or parent not in tables:
                    continue
                count = conn.execute(
                    "SELECT COUNT(*) FROM {child} c LEFT JOIN {parent} p "
                    "ON p.{parent_key}=c.{child_key} "
                    "WHERE c.{child_key} IS NOT NULL AND p.{parent_key} IS NULL".format(
                        child=child, child_key=child_key, parent=parent, parent_key=parent_key
                    )
                ).fetchone()[0]
                if count:
                    foreign_key_violations.append("%s.%s:%s" % (child, child_key, count))
            invalid.extend("foreign_key:" + item for item in foreign_key_violations)
        docs = (conn.execute("SELECT name,payload,sha256 FROM data_documents").fetchall()
                if "data_documents" in tables else [])
        legacy_document_count = len(docs)
        invalid.extend(row["name"] for row in docs
                       if hashlib.sha256(row["payload"].encode("utf-8")).hexdigest() != row["sha256"])
        if "legacy_document_archive" in tables:
            invalid.extend("archive:" + row["name"] for row in conn.execute(
                "SELECT name,payload,sha256 FROM legacy_document_archive"
            ) if hashlib.sha256(row["payload"].encode("utf-8")).hexdigest() != row["sha256"])
        # A document mirror is optional after relational cutover. When it is
        # absent, reconstruct a validation snapshot from SQL so startup never
        # treats the removed mirror as an empty business database.
        document_defaults = {
            "lumispac_data.json": [], "lumispac_dealers.json": [],
            "lumispac_settings.json": {}, "lumispac_users.json": {},
            "lumispac_orders.json": [], "lumispac_quotes.json": [],
            "lumispac_stok.json": {}, "lumispac_raw_materials.json": {},
            "lumispac_uretim.json": {}, "lumispac_finans.json": {},
            "lumispac_approvals.json": [], "lumispac_audit.json": [],
            "lumispac_geri_alma.json": [], "lumispac_geri_alma_islemleri.json": [],
        }
        available = {row["name"]: row for row in docs}
        projection_docs = list(docs)
        for name, default in document_defaults.items():
            if name not in available:
                try:
                    projection_docs.append({"name": name, "payload": json.dumps(
                        _read_relational_document(conn, name, default), ensure_ascii=False,
                        separators=(",", ":"), allow_nan=False), "sha256": ""})
                except sqlite3.OperationalError:
                    # Older schemas are validated only against tables they own.
                    continue
        docs = projection_docs
        if "products" in tables:
            document = next((row["payload"] for row in docs if row["name"] == "lumispac_data.json"), "[]")
            expected = {str(item.get("id")): json.dumps(item, ensure_ascii=False,
                        separators=(",", ":"), allow_nan=False) for item in json.loads(document)}
            actual = {row["id"]: row["payload"] for row in conn.execute("SELECT id,payload FROM products")}
            if expected != actual:
                invalid.append("lumispac_data.json:products_projection")
        if "dealers" in tables:
            document = next((row["payload"] for row in docs if row["name"] == "lumispac_dealers.json"), "[]")
            expected = {str(item.get("id")): json.dumps(item, ensure_ascii=False,
                        separators=(",", ":"), allow_nan=False) for item in json.loads(document)}
            actual = {row["id"]: row["payload"] for row in conn.execute("SELECT id,payload FROM dealers")}
            if expected != actual:
                invalid.append("lumispac_dealers.json:dealers_projection")
        if "application_settings" in tables:
            document = next((row["payload"] for row in docs if row["name"] == "lumispac_settings.json"), "{}")
            expected = json.loads(document)
            actual = {row["setting_key"]: json.loads(row["value_json"]) for row in conn.execute(
                "SELECT setting_key,value_json FROM application_settings ORDER BY position,setting_key")}
            if expected != actual:
                invalid.append("lumispac_settings.json:settings_projection")
        if {"departments", "users"}.issubset(tables):
            document = next((row["payload"] for row in docs if row["name"] == "lumispac_users.json"), "{}")
            identity = json.loads(document)
            if {"department_permissions", "user_permission_overrides"}.issubset(tables):
                if _identity_projection(conn, identity) != identity:
                    invalid.append("lumispac_users.json:permission_projection")
            else:
                for key, table in (("departmanlar", "departments"), ("kullanicilar", "users")):
                    expected = {str(item.get("id")): json.dumps(item, ensure_ascii=False,
                                separators=(",", ":"), allow_nan=False) for item in identity.get(key, [])}
                    actual = {row["id"]: row["payload"] for row in conn.execute("SELECT id,payload FROM %s" % table)}
                    if expected != actual:
                        invalid.append("lumispac_users.json:%s_projection" % table)
        for document_name, table, line_table, payment_table in (
            ("lumispac_orders.json", "orders", "order_lines", "order_payments"),
            ("lumispac_quotes.json", "quotes", "quote_lines", None),
        ):
            if table not in tables or line_table not in tables:
                continue
            source = json.loads(next((row["payload"] for row in docs
                                      if row["name"] == document_name), "[]"))
            actual_rows = conn.execute("SELECT id,payload FROM %s ORDER BY position,id" % table).fetchall()
            projected = []
            for header in actual_rows:
                record = json.loads(header["payload"])
                has_lines = record.pop("_sql_has_lines", True)
                has_payments = record.pop("_sql_has_payments", table == "orders")
                child_col = "order_id" if table == "orders" else "quote_id"
                lines = [json.loads(item[0]) for item in conn.execute(
                    "SELECT payload FROM %s WHERE %s=? ORDER BY line_position" % (line_table, child_col),
                    (header["id"],)).fetchall()]
                if has_lines:
                    record["lines"] = lines
                if payment_table and has_payments:
                    record["payments"] = [json.loads(item[0]) for item in conn.execute(
                        "SELECT payload FROM %s WHERE order_id=? ORDER BY %s" %
                        (payment_table, _order_payment_order(conn)),
                        (header["id"],)).fetchall()]
                projected.append(record)
            if source != projected:
                invalid.append("%s:%s_projection" % (document_name, table))
            if table == "orders" and "net_sales_total" in {
                    row[1] for row in conn.execute("PRAGMA table_info(orders)")}:
                from services.hesap_service import (siparis_finans_metrikleri, siparis_iptal_mi,
                                                    siparis_rapor_tarih_bilgisi)
                expected_sales = {str(order.get("id")): siparis_finans_metrikleri(order)["ciro"]
                                  for order in source if isinstance(order, dict)}
                actual_sales = {row["id"]: row["net_sales_total"] for row in conn.execute(
                    "SELECT id,net_sales_total FROM orders")}
                if expected_sales != actual_sales:
                    invalid.append("lumispac_orders.json:net_sales_projection")
                order_columns = {row[1] for row in conn.execute("PRAGMA table_info(orders)")}
                if {"is_cancelled", "report_month", "report_date_valid"}.issubset(order_columns):
                    expected_flags = {
                        str(order.get("id")): (
                            int(siparis_iptal_mi(order)),
                            siparis_rapor_tarih_bilgisi(order)["month_key"],
                            int(siparis_rapor_tarih_bilgisi(order)["valid_date"]),
                        ) for order in source if isinstance(order, dict)
                    }
                    actual_flags = {row["id"]: (row["is_cancelled"], row["report_month"],
                                                  row["report_date_valid"])
                                    for row in conn.execute(
                                        "SELECT id,is_cancelled,report_month,report_date_valid FROM orders")}
                    if expected_flags != actual_flags:
                        invalid.append("lumispac_orders.json:reporting_flags_projection")
        if {"stock_movements", "stock_thresholds"}.issubset(tables):
            source = json.loads(next((row["payload"] for row in docs
                                      if row["name"] == "lumispac_stok.json"), "{}"))
            projected = _stock_projection(conn, source)
            if source != projected:
                invalid.append("lumispac_stok.json:stock_projection")
        raw_tables = {"raw_materials", "suppliers", "raw_material_purchases", "raw_purchase_lines",
                      "raw_purchase_payments", "raw_material_stock_movements", "raw_material_history",
                      "material_recipes", "material_recipe_lines", "document_metadata"}
        if raw_tables.issubset(tables):
            source = json.loads(next((row["payload"] for row in docs
                                      if row["name"] == "lumispac_raw_materials.json"), "{}"))
            projected = _raw_material_projection(conn, source)
            if source != projected:
                invalid.append("lumispac_raw_materials.json:raw_material_projection")
        production_tables = {"downtime_reasons", "production_jobs", "production_runs",
                             "production_job_history", "production_receipts", "production_receipt_history",
                             "production_reason_history", "recycled_movements"}
        if production_tables.issubset(tables):
            source = json.loads(next((row["payload"] for row in docs
                                      if row["name"] == "lumispac_uretim.json"), "{}"))
            if _production_projection(conn, source) != source:
                invalid.append("lumispac_uretim.json:production_projection")
        if {"finance_entries", "finance_categories"}.issubset(tables):
            source = json.loads(next((row["payload"] for row in docs
                                      if row["name"] == "lumispac_finans.json"), "{}"))
            projected = dict(source)
            projected["kayitlar"] = [json.loads(item[0]) for item in conn.execute(
                "SELECT payload FROM finance_entries ORDER BY position,id").fetchall()]
            projected["kategoriler"] = {item[0]: json.loads(item[1]) for item in conn.execute(
                "SELECT category_type,payload FROM finance_categories ORDER BY position,category_type").fetchall()}
            if source != projected:
                invalid.append("lumispac_finans.json:finance_projection")
        if "approval_requests" in tables:
            source = json.loads(next((row["payload"] for row in docs
                                      if row["name"] == "lumispac_approvals.json"), "[]"))
            projected = [json.loads(item[0]) for item in conn.execute(
                "SELECT payload FROM approval_requests ORDER BY position,id").fetchall()]
            if source != projected:
                invalid.append("lumispac_approvals.json:approval_projection")
        audit_tables = {"audit_events", "undo_actions", "undo_changes", "undo_operation_events"}
        if audit_tables.issubset(tables):
            for name in ("lumispac_audit.json", "lumispac_geri_alma.json",
                         "lumispac_geri_alma_islemleri.json"):
                source = json.loads(next((row["payload"] for row in docs if row["name"] == name),
                                         "{}" if name == "lumispac_geri_alma.json" else "[]"))
                if _audit_undo_projection(conn, name, source) != source:
                    invalid.append(name + ":audit_undo_projection")
        permission_tables = {"department_permissions", "user_permission_overrides"}
        if permission_tables.issubset(tables) and {"departments", "users"}.issubset(tables):
            source = json.loads(next((row["payload"] for row in docs
                                      if row["name"] == "lumispac_users.json"), "{}"))
            if _identity_projection(conn, source) != source:
                invalid.append("lumispac_users.json:permission_projection")
        return {"ok": result == "ok" and not invalid, "integrity": result,
                "documents": legacy_document_count,
                "relational_documents": len(docs), "invalid_documents": invalid,
                "foreign_key_violations": foreign_key_violations}
    finally:
        conn.close()
