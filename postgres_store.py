"""PostgreSQL adapter for LUMISPAC's normalized relational store.

The document/domain query functions are shared with ``sqlite_store``; its
connection factory routes them through the active PostgreSQL DB-API wrapper.
Initialization is intentionally fail-closed: an empty PostgreSQL database
must be populated by the explicit, parity-checked SQLite transfer tool first.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

import config
import sqlite_store as _relational
from postgres_connection import connect
from postgres_migrations import apply_pending


BACKUP_EXTENSION = ".dump"
_initialized = set()


def _current_schema_version():
    from db_migrations import MIGRATIONS
    return MIGRATIONS[-1].version


# These operations are backend-neutral relational queries/transactions.
def managed_json_path(path):
    """Claim application JSON paths for PostgreSQL document projections.

    The SQLite implementation intentionally returns False outside SQLite mode;
    PostgreSQL needs its own path predicate so utils.read_json/write_json never
    fall through to legacy project JSON files.
    """
    candidate = Path(path).resolve()
    root = Path(config.BASE).resolve()
    return (candidate.parent == root and candidate.name.startswith("lumispac_")
            and candidate.suffix == ".json")
read_document = _relational.read_document
write_documents = _relational.write_documents
document_exists = _relational.document_exists
list_order_records = _relational.list_order_records
count_order_records = _relational.count_order_records
list_dealer_records = _relational.list_dealer_records
list_product_records = _relational.list_product_records
read_settings_records = _relational.read_settings_records
replace_product_records = _relational.replace_product_records
replace_dealer_records = _relational.replace_dealer_records
replace_settings_records = _relational.replace_settings_records
mutate_documents = _relational.mutate_documents
document_transaction = _relational.document_transaction
list_quote_records = _relational.list_quote_records
dashboard_order_totals = _relational.dashboard_order_totals
read_raw_material_records = _relational.read_raw_material_records
read_stock_records = _relational.read_stock_records


def _dsn():
    value = str(getattr(config, "DATABASE_URL", "") or "").strip()
    if not value:
        raise RuntimeError("PostgreSQL için LUMISPAC_DATABASE_URL yapılandırılmalı.")
    return value


def initialize():
    """Apply shared schema migrations without importing stale JSON files."""
    connection = connect(_dsn())
    try:
        version = apply_pending(connection)
        expected_version = _current_schema_version()
        if version != expected_version:
            raise RuntimeError("PostgreSQL şeması beklenen v%s sürümüne ulaşmadı." % expected_version)
        # The shared SQLite migrations create this compatibility bridge, but
        # PostgreSQL is populated only by the verified relational transfer.
        # Retire the bridge here only when it is empty; never discard data from
        # an unexpectedly initialized target.
        if _relational._has_table(connection, "data_documents"):
            count = connection.execute("SELECT COUNT(*) FROM data_documents").fetchone()[0]
            if count:
                raise RuntimeError(
                    "PostgreSQL JSON köprüsünde kayıt var; güvenli biçimde kapatılamıyor."
                )
            connection.execute("DROP TABLE data_documents")
        connection.execute(
            "DELETE FROM app_metadata WHERE key='document_bridge_retirement_pending'"
        )
    finally:
        connection.close()


def ensure_initialized():
    """Require an explicitly transferred, verified relational database."""
    dsn = _dsn()
    if dsn in _initialized:
        return
    connection = connect(dsn)
    try:
        has_history = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone()
        if not has_history:
            raise RuntimeError("PostgreSQL migration şeması bulunamadı.")
        version = connection.execute(
            "SELECT COALESCE(MAX(version),0) FROM schema_migrations"
        ).fetchone()[0]
        metadata = connection.execute(
            "SELECT key,value FROM app_metadata WHERE key IN ('migration_complete','relational_source')"
        ).fetchall() if version >= 13 else []
        flags = {row[0]: row[1] for row in metadata}
        # Only migrate a database that was already explicitly transferred and
        # verified. This permits additive upgrades but still refuses an empty
        # or unverified PostgreSQL database.
        if (version >= 13 and flags.get("migration_complete") == "1"
                and flags.get("relational_source") == "1"):
            version = apply_pending(connection)
    except Exception as exc:
        raise RuntimeError("PostgreSQL şeması kurulmamış; veri aktarımı tamamlanmadı.") from exc
    finally:
        connection.close()
    if (version != _current_schema_version() or flags.get("migration_complete") != "1"
            or flags.get("relational_source") != "1"):
        raise RuntimeError(
            "PostgreSQL veritabanı henüz SQLite'tan doğrulanmış biçimde aktarılmadı."
        )
    check = integrity_check()
    if not check.get("ok"):
        raise RuntimeError("PostgreSQL veri bütünlüğü doğrulanamadı; uygulama başlatılmadı.")
    _initialized.add(dsn)


def integrity_check():
    """Check schema, all reconstructed relational documents and archive hashes."""
    connection = None
    invalid = []
    try:
        connection = connect(_dsn())
        version = connection.execute(
            "SELECT COALESCE(MAX(version),0) FROM schema_migrations"
        ).fetchone()[0]
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        if version != _current_schema_version():
            invalid.append("schema_migrations:version")
        from db_migrations import _WORKFLOW_FOREIGN_KEYS
        foreign_key_constraints = connection.execute(
            "SELECT COUNT(*) FROM information_schema.table_constraints "
            "WHERE table_schema=current_schema() AND constraint_type='FOREIGN KEY'"
        ).fetchone()[0]
        if foreign_key_constraints < len(_WORKFLOW_FOREIGN_KEYS):
            invalid.append("schema_migrations:workflow_foreign_keys")
        if "data_documents" in tables:
            invalid.append("data_documents:bridge_not_retired")
        if "app_metadata" in tables:
            metadata = connection.execute(
                "SELECT key,value FROM app_metadata "
                "WHERE key IN ('migration_complete','relational_source')"
            ).fetchall()
            flags = {row[0]: row[1] for row in metadata}
            if flags.get("migration_complete") != "1" or flags.get("relational_source") != "1":
                invalid.append("app_metadata:source_not_verified")
        else:
            invalid.append("missing_table:app_metadata")
        required = {
            "products", "dealers", "application_settings", "users", "departments",
            "orders", "order_lines", "order_payments", "quotes", "quote_lines",
            "stock_movements", "stock_thresholds", "raw_materials", "suppliers",
            "raw_material_purchases", "production_jobs", "finance_entries",
            "approval_requests", "audit_events", "undo_actions",
        }
        missing = required.difference(tables)
        invalid.extend("missing_table:" + name for name in sorted(missing))
        if not missing:
            defaults = {
                "lumispac_data.json": [], "lumispac_dealers.json": [],
                "lumispac_settings.json": {}, "lumispac_users.json": {},
                "lumispac_orders.json": [], "lumispac_quotes.json": [],
                "lumispac_stok.json": {}, "lumispac_raw_materials.json": {},
                "lumispac_uretim.json": {}, "lumispac_finans.json": {},
                "lumispac_approvals.json": [], "lumispac_audit.json": [],
                "lumispac_geri_alma.json": [], "lumispac_geri_alma_islemleri.json": [],
            }
            for name, default in defaults.items():
                try:
                    value = _relational._read_relational_document(connection, name, default)
                    if not isinstance(value, type(default)):
                        invalid.append(name + ":document_type")
                except Exception:
                    invalid.append(name + ":projection")
        archived = 0
        if "legacy_document_archive" in tables:
            rows = connection.execute(
                "SELECT name,payload,sha256 FROM legacy_document_archive"
            ).fetchall()
            archived = len(rows)
            for name, payload, digest in rows:
                if hashlib.sha256(payload.encode("utf-8")).hexdigest() != digest:
                    invalid.append("archive:" + name)
        row_count = sum(connection.execute(
            'SELECT COUNT(*) FROM "' + table + '"'
        ).fetchone()[0] for table in sorted(tables) if table != "schema_migrations")
        return {"ok": not invalid, "integrity": "ok" if not invalid else "invalid",
                "schema_version": version, "documents": 14,
                "archived_legacy_documents": archived, "rows": row_count,
                "invalid_documents": invalid,
                "foreign_key_constraints": foreign_key_constraints}
    except Exception as exc:
        return {"ok": False, "integrity": "error", "documents": 0,
                "invalid_documents": [str(exc)]}
    finally:
        if connection is not None:
            connection.close()


def _pg_tool_environment():
    """Move credentials out of pg_dump/pg_restore command-line arguments."""
    dsn = _dsn()
    parts = urlsplit(dsn)
    if parts.scheme not in ("postgres", "postgresql"):
        raise RuntimeError("Yedekleme için PostgreSQL URI biçiminde bağlantı dizesi gerekli.")
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    username = unquote(parts.username or query.get("user") or os.environ.get("PGUSER", ""))
    password = unquote(parts.password or query.get("password") or os.environ.get("PGPASSWORD", ""))
    database = unquote(parts.path.lstrip("/") or query.get("dbname", ""))
    host = parts.hostname or query.get("host", "localhost")
    port = str(parts.port or query.get("port", "5432"))
    if not username or not database:
        raise RuntimeError("PostgreSQL yedeklemesi için kullanıcı ve veritabanı gerekli.")
    safe_host = "[%s]" % host if ":" in host and not host.startswith("[") else host
    safe_netloc = quote(username, safe="") + "@" + safe_host + (":" + port if port else "")
    safe_query = {key: value for key, value in query.items()
                  if key not in ("password", "user", "dbname", "host", "port")}
    safe_dsn = urlunsplit((parts.scheme, safe_netloc, "/" + quote(database, safe=""),
                           urlencode(safe_query), ""))
    environment = os.environ.copy()
    environment.update({"PGUSER": username, "PGPASSWORD": password,
                        "PGHOST": host, "PGPORT": port, "PGDATABASE": database})
    if "sslmode" in query:
        environment["PGSSLMODE"] = query["sslmode"]
    return safe_dsn, environment


def _pg_command(name):
    command = shutil.which(name)
    if command:
        return command
    executable = name if name.lower().endswith(".exe") else name + ".exe"
    candidates = []
    for root_name in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(root_name)
        if root:
            candidates.extend(Path(root).glob("PostgreSQL/*/bin/" + executable))
    if candidates:
        return str(sorted(candidates, key=lambda path: path.parent.parent.name)[-1])
    raise RuntimeError("PostgreSQL istemci aracı bulunamadı: %s" % name)


def backup_database(target):
    """Create and validate a custom-format PostgreSQL dump atomically."""
    check = integrity_check()
    if not check.get("ok"):
        raise RuntimeError("Bütünlük kontrolü başarısız; PostgreSQL yedeği alınmadı.")
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    safe_dsn, environment = _pg_tool_environment()
    descriptor, temporary = tempfile.mkstemp(prefix=target_path.name + ".",
                                              suffix=".tmp", dir=str(target_path.parent))
    os.close(descriptor)
    try:
        result = subprocess.run(
            [_pg_command("pg_dump"), "--format=custom", "--no-owner", "--no-acl", "--file", temporary, "--dbname", safe_dsn],
            env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=False,
            timeout=300,
        )
        if result.returncode:
            raise RuntimeError("pg_dump yedeği oluşturamadı; kaynak veritabanı değişmedi.")
        listing = subprocess.run(
            [_pg_command("pg_restore"), "--list", temporary],
            env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False, timeout=60,
        )
        if listing.returncode:
            raise RuntimeError("Oluşturulan PostgreSQL yedeği doğrulanamadı.")
        os.replace(temporary, target_path)
        return target_path
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def restore_database(source_path):
    """Restore a custom dump in one transaction after an explicit caller backup."""
    source = Path(source_path)
    if not source.is_file() or source.suffix.lower() != BACKUP_EXTENSION:
        raise RuntimeError("PostgreSQL yedeği bulunamadı veya biçimi geçersiz.")
    check = subprocess.run(
        [_pg_command("pg_restore"), "--list", str(source)],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, check=False, timeout=60,
    )
    if check.returncode:
        raise RuntimeError("PostgreSQL yedek dosyası okunamıyor.")
    safe_dsn, environment = _pg_tool_environment()
    result = subprocess.run(
        [_pg_command("pg_restore"), "--clean", "--if-exists", "--no-owner",
         "--no-acl", "--exit-on-error", "--single-transaction",
         "--dbname", safe_dsn, str(source)],
        env=environment, stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        check=False, timeout=600,
    )
    if result.returncode:
        raise RuntimeError("PostgreSQL geri yüklemesi başarısız; tek işlem geri alındı.")
    _initialized.discard(_dsn())
    outcome = integrity_check()
    if not outcome.get("ok"):
        raise RuntimeError("Geri yüklenen PostgreSQL verisi bütünlük kontrolünden geçmedi.")
    return outcome
