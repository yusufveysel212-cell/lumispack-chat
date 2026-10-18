"""Versioned SQLite schema migrations.

Each migration is applied exactly once inside its own IMMEDIATE transaction.
Migration functions receive the active sqlite3 connection and must be
deterministic, local, and safe to retry after rollback.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import json


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    apply: object


def _document_store(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS data_documents (
            name TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)


def _master_data_projection(conn):
    """Typed relational projections for products and dealers."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            weight REAL,
            qty REAL,
            volume REAL,
            stock REAL,
            sale REAL,
            active INTEGER NOT NULL DEFAULT 1,
            payload TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_products_active_name ON products(active,name)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dealers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            contact TEXT,
            phone TEXT,
            city TEXT,
            discount REAL,
            owner_user_id TEXT,
            payload TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_dealers_owner_name ON dealers(owner_user_id,name)")


def _projection_order(conn):
    conn.execute("ALTER TABLE products ADD COLUMN position INTEGER NOT NULL DEFAULT 0")
    conn.execute("ALTER TABLE dealers ADD COLUMN position INTEGER NOT NULL DEFAULT 0")


def _identity_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            parent_id TEXT,
            manager_user_id TEXT,
            system_department INTEGER NOT NULL DEFAULT 0,
            payload TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_departments_parent ON departments(parent_id,name)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            full_name TEXT,
            department_id TEXT,
            manager_user_id TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            password_hash TEXT,
            payload TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_department_active ON users(department_id,active)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_manager ON users(manager_user_id)")


def _orders_and_quotes(conn):
    """Typed order/quote headers, item lines and payment schedules."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY, number TEXT, dealer_id TEXT, customer TEXT,
            order_date TEXT, delivery_date TEXT, status TEXT, owner_user_id TEXT,
            gross_total REAL, net_profit REAL, payload TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_status_date ON orders(status,order_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_owner_dealer ON orders(owner_user_id,dealer_id)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS order_lines (
            order_id TEXT NOT NULL, line_position INTEGER NOT NULL, product_code TEXT,
            product_name TEXT, quantity REAL, boxes REAL, sale REAL, cost REAL,
            profit REAL, total REAL, payload TEXT NOT NULL,
            PRIMARY KEY(order_id,line_position)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_order_lines_product ON order_lines(product_code)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS order_payments (
            order_id TEXT NOT NULL, payment_id TEXT NOT NULL, amount REAL,
            payment_date TEXT, status TEXT, method TEXT, payload TEXT NOT NULL,
            PRIMARY KEY(order_id,payment_id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_order_payments_status_date ON order_payments(status,payment_date)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id TEXT PRIMARY KEY, number TEXT, dealer_id TEXT, customer TEXT,
            quote_date TEXT, status TEXT, owner_user_id TEXT, gross_total REAL,
            net_profit REAL, payload TEXT NOT NULL, position INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_quotes_owner_dealer ON quotes(owner_user_id,dealer_id)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quote_lines (
            quote_id TEXT NOT NULL, line_position INTEGER NOT NULL, product_code TEXT,
            product_name TEXT, quantity REAL, boxes REAL, sale REAL, cost REAL,
            profit REAL, total REAL, payload TEXT NOT NULL,
            PRIMARY KEY(quote_id,line_position)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_quote_lines_product ON quote_lines(product_code)")


def _inventory_movements(conn):
    """Normalized stock movement ledger and per-product alert thresholds."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_movements (
            id TEXT PRIMARY KEY, product_id TEXT, product_name TEXT,
            movement_type TEXT, quantity REAL, movement_date TEXT,
            source TEXT, description TEXT, payload TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_stock_movements_product_date ON stock_movements(product_id,movement_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_stock_movements_type_date ON stock_movements(movement_type,movement_date)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_thresholds (
            product_code TEXT PRIMARY KEY, threshold REAL, payload TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0
        )
    """)


def _raw_material_purchasing(conn):
    """Normalized raw materials, suppliers, purchase lines, payments and stock ledger."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw_materials (
            id TEXT PRIMARY KEY, code TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            material_type TEXT, unit TEXT, price_per_kg REAL, active INTEGER NOT NULL DEFAULT 1,
            payload TEXT NOT NULL, position INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_materials_type_active ON raw_materials(material_type,active)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
            payload TEXT NOT NULL, position INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_suppliers_active_name ON suppliers(active,name)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw_material_purchases (
            id TEXT PRIMARY KEY, supplier_id TEXT, supplier_name TEXT, document_no TEXT,
            purchase_date TEXT, status TEXT, total REAL, receipt_id TEXT, payload TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_purchases_supplier_date ON raw_material_purchases(supplier_id,purchase_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_purchases_status_date ON raw_material_purchases(status,purchase_date)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw_purchase_lines (
            purchase_id TEXT NOT NULL, line_position INTEGER NOT NULL, material_id TEXT,
            material_code TEXT, material_name TEXT, quantity_kg REAL, unit TEXT,
            unit_price REAL, line_total REAL, payload TEXT NOT NULL,
            PRIMARY KEY(purchase_id,line_position)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_purchase_lines_material ON raw_purchase_lines(material_id,material_code)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw_purchase_payments (
            purchase_id TEXT NOT NULL, payment_id TEXT NOT NULL, amount REAL, currency TEXT,
            payment_date TEXT, method TEXT, idempotency_key TEXT, payload TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(purchase_id,payment_id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_purchase_payments_date ON raw_purchase_payments(payment_date)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw_material_stock_movements (
            id TEXT PRIMARY KEY, purchase_id TEXT, material_id TEXT, material_code TEXT,
            movement_type TEXT, quantity_kg REAL, unit TEXT, unit_price REAL,
            previous_status TEXT, new_status TEXT, occurred_at TEXT,
            idempotency_key TEXT, payload TEXT NOT NULL, position INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_stock_material_date ON raw_material_stock_movements(material_id,occurred_at)")


def _production_records(conn):
    """Normalized production jobs, runs, receipts, reasons and event history."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS downtime_reasons (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
            payload TEXT NOT NULL, position INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS production_jobs (
            id TEXT PRIMARY KEY, product_code TEXT, product_name TEXT, status TEXT,
            planned_qty REAL, produced_qty REAL, scrap_qty REAL, usable_qty REAL,
            machine TEXT, mold TEXT, source_type TEXT, last_run_id TEXT,
            payload TEXT NOT NULL, position INTEGER NOT NULL DEFAULT 0, updated_at TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_production_jobs_status_updated ON production_jobs(status,updated_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_production_jobs_product ON production_jobs(product_code,status)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS production_runs (
            job_id TEXT NOT NULL, run_position INTEGER NOT NULL, id TEXT,
            produced_qty REAL, scrap_qty REAL, usable_qty REAL, created_at TEXT,
            payload TEXT NOT NULL, PRIMARY KEY(job_id,run_position)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS production_job_history (
            job_id TEXT NOT NULL, history_position INTEGER NOT NULL, action TEXT,
            previous_status TEXT, new_status TEXT, quantity REAL, occurred_at TEXT,
            user_id TEXT, reason TEXT, payload TEXT NOT NULL,
            PRIMARY KEY(job_id,history_position)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS production_receipts (
            id TEXT PRIMARY KEY, job_id TEXT, run_id TEXT, product_code TEXT,
            product_name TEXT, quantity REAL, status TEXT, decided_at TEXT,
            payload TEXT NOT NULL, position INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_production_receipts_status_job ON production_receipts(status,job_id)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS production_receipt_history (
            receipt_id TEXT NOT NULL, history_position INTEGER NOT NULL, action TEXT,
            previous_status TEXT, new_status TEXT, occurred_at TEXT,
            user_id TEXT, reason TEXT, payload TEXT NOT NULL,
            PRIMARY KEY(receipt_id,history_position)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS production_reason_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, previous_status TEXT,
            new_status TEXT, quantity REAL, occurred_at TEXT, user_id TEXT,
            reason TEXT, payload TEXT NOT NULL, position INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recycled_movements (
            id TEXT PRIMARY KEY, movement_type TEXT, quantity REAL, occurred_at TEXT,
            user_id TEXT, reason TEXT, payload TEXT NOT NULL, position INTEGER NOT NULL DEFAULT 0
        )
    """)


def _finance_and_approvals(conn):
    """Typed finance ledger, its category lists and approval workflow records."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS finance_entries (
            id TEXT PRIMARY KEY, number TEXT, entry_type TEXT, amount REAL,
            entry_date TEXT, category TEXT, customer TEXT, payment_method TEXT,
            description TEXT, payload TEXT NOT NULL, position INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_finance_entries_date_type ON finance_entries(entry_date,entry_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_finance_entries_category ON finance_entries(category,entry_type)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS finance_categories (
            category_type TEXT PRIMARY KEY, payload TEXT NOT NULL, position INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS approval_requests (
            id TEXT PRIMARY KEY, requester_id TEXT, requester_name TEXT,
            requester_department TEXT, method TEXT, path TEXT, status TEXT,
            created_at TEXT, summary TEXT, payload_hash TEXT,
            payload TEXT NOT NULL, position INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_approval_status_created ON approval_requests(status,created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_approval_requester ON approval_requests(requester_id,created_at)")


def _audit_and_undo(conn):
    """Normalized append-only audit events and reversible change records."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_events (
            event_id TEXT PRIMARY KEY, occurred_at TEXT, user_id TEXT,
            username TEXT, action TEXT, source TEXT, method TEXT, path TEXT,
            status_code INTEGER, result TEXT, undo_id TEXT, payload TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_time_action ON audit_events(occurred_at,action)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_user_time ON audit_events(user_id,occurred_at)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS undo_actions (
            id TEXT PRIMARY KEY, action_type TEXT, status TEXT, user_id TEXT,
            username TEXT, occurred_at TEXT, description TEXT, payload TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_undo_status_time ON undo_actions(status,occurred_at)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS undo_changes (
            undo_id TEXT NOT NULL, change_position INTEGER NOT NULL, record_id TEXT,
            previous_order REAL, next_order REAL, previous_payload TEXT,
            next_payload TEXT, payload TEXT NOT NULL,
            PRIMARY KEY(undo_id,change_position)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS undo_operation_events (
            event_id TEXT PRIMARY KEY, occurred_at TEXT, user_id TEXT,
            username TEXT, action TEXT, source TEXT, status_code INTEGER,
            result TEXT, undo_id TEXT, payload TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_undo_events_time ON undo_operation_events(occurred_at)")


def _permission_assignments(conn):
    """Store department defaults and per-user permission overrides as rows."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS department_permissions (
            department_id TEXT NOT NULL, permission_key TEXT NOT NULL,
            permission_level TEXT NOT NULL, position INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(department_id,permission_key)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_department_permission_key ON department_permissions(permission_key,permission_level)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_permission_overrides (
            user_id TEXT NOT NULL, permission_key TEXT NOT NULL,
            permission_level TEXT NOT NULL, position INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id,permission_key)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user_permission_key ON user_permission_overrides(permission_key,permission_level)")


def _order_reporting_totals(conn):
    """Add a central-formula revenue snapshot for SQL reporting aggregates."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(orders)")}
    if "net_sales_total" not in columns:
        conn.execute("ALTER TABLE orders ADD COLUMN net_sales_total REAL")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_reporting_date_owner ON orders(order_date,owner_user_id,dealer_id)")


def _application_settings(conn):
    """Project top-level settings into relational key/value rows."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS application_settings (
            setting_key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )
    """)
    row = conn.execute("SELECT payload FROM data_documents WHERE name='lumispac_settings.json'").fetchone()
    if row is None:
        return
    values = json.loads(row[0])
    if not isinstance(values, dict):
        raise ValueError("Ayar belgesi sözlük biçiminde değil; ilişkisel geçiş durduruldu.")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.executemany(
        "INSERT INTO application_settings(setting_key,value_json,position,updated_at) VALUES(?,?,?,?)",
        [(str(key), json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False), position, now)
         for position, (key, value) in enumerate(values.items())],
    )


def _relational_document_metadata(conn):
    """Normalize document extension fields and user-defined material recipes."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS document_metadata (
            document_name TEXT NOT NULL,
            metadata_key TEXT NOT NULL,
            value_json TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(document_name,metadata_key)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_document_metadata_name_position ON document_metadata(document_name,position,metadata_key)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw_material_history (
            event_id TEXT PRIMARY KEY,
            event_position INTEGER NOT NULL,
            action TEXT,
            occurred_at TEXT,
            user_id TEXT,
            payload TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_material_history_action_time ON raw_material_history(action,occurred_at)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS material_recipes (
            id TEXT PRIMARY KEY,
            product_code TEXT NOT NULL UNIQUE,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT,
            updated_at TEXT,
            payload TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS material_recipe_lines (
            recipe_id TEXT NOT NULL,
            line_position INTEGER NOT NULL,
            material_id TEXT,
            material_code TEXT,
            material_name TEXT,
            kg_per_box REAL,
            payload TEXT NOT NULL,
            PRIMARY KEY(recipe_id,line_position)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_material_recipe_lines_material ON material_recipe_lines(material_id)")


def _relational_document_registry(conn):
    """Track imported document identities independently of their frozen archive."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS relational_document_registry (
            document_name TEXT PRIMARY KEY,
            registered_at TEXT NOT NULL
        )
    """)


def _prepare_document_bridge_retirement(conn):
    """Create a read-only archive for imported documents outside the SQL model."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS legacy_document_archive (
            name TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            archived_at TEXT NOT NULL
        )
    """)
    conn.execute("INSERT OR REPLACE INTO app_metadata(key,value) VALUES('document_bridge_retirement_pending','1')")


def _order_payment_position(conn):
    """Persist payment order explicitly instead of relying on SQLite rowid."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(order_payments)")}
    if "position" not in columns:
        conn.execute("ALTER TABLE order_payments ADD COLUMN position INTEGER NOT NULL DEFAULT 0")
    legacy_order = "payment_id" if getattr(conn, "dialect", "sqlite") == "postgresql" else "rowid"
    for order_id, in conn.execute("SELECT DISTINCT order_id FROM order_payments").fetchall():
        payments = conn.execute(
            "SELECT payment_id FROM order_payments WHERE order_id=? ORDER BY " + legacy_order,
            (order_id,)
        ).fetchall()
        for position, (payment_id,) in enumerate(payments):
            conn.execute("UPDATE order_payments SET position=? WHERE order_id=? AND payment_id=?",
                         (position, order_id, payment_id))
    conn.execute("CREATE INDEX IF NOT EXISTS idx_order_payments_order_position ON order_payments(order_id,position)")


def _portable_order_reporting_flags(conn):
    """Persist centrally-derived cancellation and month/date reporting flags."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(orders)")}
    if "is_cancelled" not in columns:
        conn.execute("ALTER TABLE orders ADD COLUMN is_cancelled INTEGER NOT NULL DEFAULT 0")
    if "report_month" not in columns:
        conn.execute("ALTER TABLE orders ADD COLUMN report_month TEXT NOT NULL DEFAULT ''")
    if "report_date_valid" not in columns:
        conn.execute("ALTER TABLE orders ADD COLUMN report_date_valid INTEGER NOT NULL DEFAULT 0")
    from services.hesap_service import siparis_iptal_mi, siparis_rapor_tarih_bilgisi
    rows = conn.execute("SELECT id,payload FROM orders").fetchall()
    for order_id, payload in rows:
        order = json.loads(payload)
        date_info = siparis_rapor_tarih_bilgisi(order)
        conn.execute("UPDATE orders SET is_cancelled=?,report_month=?,report_date_valid=? WHERE id=?",
                     (int(siparis_iptal_mi(order)), date_info["month_key"],
                      int(date_info["valid_date"]), order_id))
    conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_reporting_month_cancelled ON orders(is_cancelled,report_month,report_date_valid)")


def _unique_idempotency_keys(conn):
    """Enforce retry keys at the database boundary for purchase ledger writes."""
    for table in ("raw_purchase_payments", "raw_material_stock_movements"):
        duplicates = conn.execute(
            "SELECT idempotency_key,COUNT(*) FROM %s "
            "WHERE idempotency_key IS NOT NULL AND TRIM(idempotency_key)<>'' "
            "GROUP BY idempotency_key HAVING COUNT(*)>1 LIMIT 1" % table
        ).fetchone()
        if duplicates:
            raise ValueError(
                "Tekrarlı işlem anahtarı bulundu (%s); güvenli migration durduruldu." % table
            )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_%s_idempotency_key "
            "ON %s(idempotency_key) WHERE idempotency_key IS NOT NULL "
            "AND TRIM(idempotency_key)<>''" % (table, table)
        )


_WORKFLOW_FOREIGN_KEYS = (
    ("order_lines", "order_id", "orders", "id"),
    ("order_payments", "order_id", "orders", "id"),
    ("quote_lines", "quote_id", "quotes", "id"),
    ("raw_purchase_lines", "purchase_id", "raw_material_purchases", "id"),
    ("raw_purchase_payments", "purchase_id", "raw_material_purchases", "id"),
    ("raw_material_stock_movements", "purchase_id", "raw_material_purchases", "id"),
    ("production_runs", "job_id", "production_jobs", "id"),
    ("production_job_history", "job_id", "production_jobs", "id"),
    ("production_receipts", "job_id", "production_jobs", "id"),
    ("production_receipt_history", "receipt_id", "production_receipts", "id"),
    ("material_recipe_lines", "recipe_id", "material_recipes", "id"),
    ("department_permissions", "department_id", "departments", "id"),
    ("user_permission_overrides", "user_id", "users", "id"),
)


def _workflow_foreign_keys(conn):
    """Enforce stable parent-child links without deleting historical parents.

    Existing orphan rows stop the migration and the enclosing transaction is
    rolled back. PostgreSQL gets real FK constraints; SQLite gets equivalent
    insert/update guards because ALTER TABLE cannot add an FK to an existing
    table without rebuilding it and losing portable table metadata.
    """
    is_postgres = getattr(conn, "dialect", "sqlite") == "postgresql"
    for child, child_key, parent, parent_key in _WORKFLOW_FOREIGN_KEYS:
        orphan = conn.execute(
            "SELECT COUNT(*) FROM {child} c LEFT JOIN {parent} p "
            "ON p.{parent_key}=c.{child_key} "
            "WHERE c.{child_key} IS NOT NULL AND p.{parent_key} IS NULL".format(
                child=child, child_key=child_key, parent=parent, parent_key=parent_key
            )
        ).fetchone()[0]
        if orphan:
            raise ValueError(
                "İlişkisel bütünlük migration'ı durdu: %s.%s alanında %s ebeveynsiz kayıt var."
                % (child, child_key, orphan)
            )

        index = "idx_fk_%s_%s" % (child, child_key)
        conn.execute("CREATE INDEX IF NOT EXISTS %s ON %s(%s)" % (index, child, child_key))
        if is_postgres:
            constraint = "fk_%s_%s" % (child, child_key)
            exists = conn.execute(
                "SELECT COUNT(*) FROM pg_constraint c "
                "JOIN pg_class child ON child.oid=c.conrelid "
                "JOIN pg_namespace ns ON ns.oid=child.relnamespace "
                "JOIN pg_class parent ON parent.oid=c.confrelid "
                "JOIN pg_attribute ca ON ca.attrelid=child.oid AND ca.attnum=c.conkey[1] "
                "JOIN pg_attribute pa ON pa.attrelid=parent.oid AND pa.attnum=c.confkey[1] "
                "WHERE c.contype='f' AND ns.nspname=current_schema() "
                "AND child.relname=? AND ca.attname=? "
                "AND parent.relname=? AND pa.attname=? "
                "AND array_length(c.conkey,1)=1 AND array_length(c.confkey,1)=1",
                (child, child_key, parent, parent_key),
            ).fetchone()[0]
            if not exists:
                conn.execute(
                    "ALTER TABLE %s ADD CONSTRAINT %s FOREIGN KEY (%s) REFERENCES %s(%s) "
                    "DEFERRABLE INITIALLY DEFERRED"
                    % (child, constraint, child_key, parent, parent_key)
                )
        else:
            trigger_base = "guard_%s_%s" % (child, child_key)
            conn.execute(
                "CREATE TRIGGER IF NOT EXISTS %s_insert BEFORE INSERT ON %s "
                "WHEN NEW.%s IS NOT NULL AND NOT EXISTS "
                "(SELECT 1 FROM %s WHERE %s=NEW.%s) "
                "BEGIN SELECT RAISE(ABORT,'%s reference missing'); END"
                % (trigger_base, child, child_key, parent, parent_key, child_key, parent)
            )
            conn.execute(
                "CREATE TRIGGER IF NOT EXISTS %s_update BEFORE UPDATE OF %s ON %s "
                "WHEN NEW.%s IS NOT NULL AND NOT EXISTS "
                "(SELECT 1 FROM %s WHERE %s=NEW.%s) "
                "BEGIN SELECT RAISE(ABORT,'%s reference missing'); END"
                % (trigger_base, child_key, child, child_key, parent, parent_key, child_key, parent)
            )
            conn.execute(
                "CREATE TRIGGER IF NOT EXISTS %s_delete BEFORE DELETE ON %s "
                "WHEN EXISTS (SELECT 1 FROM %s WHERE %s=OLD.%s) "
                "BEGIN SELECT RAISE(ABORT,'%s has dependent rows'); END"
                % (trigger_base, parent, child, child_key, parent_key, parent)
            )


MIGRATIONS = (
    Migration(1, "document_store_baseline", _document_store),
    Migration(2, "relational_master_data_projection", _master_data_projection),
    Migration(3, "stable_master_data_order", _projection_order),
    Migration(4, "relational_users_and_departments", _identity_tables),
    Migration(5, "relational_orders_and_quotes", _orders_and_quotes),
    Migration(6, "relational_stock_movements_and_thresholds", _inventory_movements),
    Migration(7, "relational_raw_material_purchasing", _raw_material_purchasing),
    Migration(8, "relational_production_records", _production_records),
    Migration(9, "relational_finance_and_approvals", _finance_and_approvals),
    Migration(10, "relational_audit_and_undo", _audit_and_undo),
    Migration(11, "relational_permission_assignments", _permission_assignments),
    Migration(12, "relational_order_reporting_totals", _order_reporting_totals),
    Migration(13, "relational_application_settings", _application_settings),
    Migration(14, "relational_document_metadata_and_recipes", _relational_document_metadata),
    Migration(15, "relational_document_registry", _relational_document_registry),
    Migration(16, "prepare_document_bridge_retirement", _prepare_document_bridge_retirement),
    Migration(17, "explicit_order_payment_position", _order_payment_position),
    Migration(18, "portable_order_reporting_flags", _portable_order_reporting_flags),
    Migration(19, "unique_raw_ledger_idempotency_keys", _unique_idempotency_keys),
    Migration(20, "workflow_parent_reference_integrity", _workflow_foreign_keys),
    # v20 was already deployed by an older release with eight FKs. Keep that
    # history intact and make the expanded relationship set an additive step.
    Migration(21, "complete_workflow_parent_reference_integrity", _workflow_foreign_keys),
)


def apply_pending(conn):
    """Apply registered schema migrations and return the current version."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
    """)
    current = conn.execute(
        "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
    ).fetchone()[0]
    for migration in MIGRATIONS:
        if migration.version <= current:
            continue
        conn.execute("BEGIN IMMEDIATE")
        try:
            migration.apply(conn)
            conn.execute(
                "INSERT INTO schema_migrations(version,name,applied_at) VALUES(?,?,?)",
                (migration.version, migration.name,
                 datetime.now(timezone.utc).isoformat(timespec="seconds")),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        current = migration.version
    return current
