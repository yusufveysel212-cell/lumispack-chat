"""Run the shared, versioned schema migrations through PostgreSQL DB-API.

The migration definitions remain single-source in :mod:`db_migrations`; this
module supplies an explicit PostgreSQL entry point and rejects an unexpected
schema history. The caller must pass a connection from ``postgres_connection``.
"""
from datetime import datetime, timezone


class PostgresMigrationError(RuntimeError):
    """PostgreSQL schema history is invalid or a migration failed."""


def apply_pending(connection):
    """Apply pending shared migrations, one explicit transaction at a time."""
    from db_migrations import MIGRATIONS

    expected_versions = [item.version for item in MIGRATIONS]
    if expected_versions != list(range(1, len(expected_versions) + 1)):
        raise PostgresMigrationError("Şema migration sürümleri ardışık değil.")

    connection.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
    """)
    rows = connection.execute(
        "SELECT version,name FROM schema_migrations ORDER BY version"
    ).fetchall()
    applied = [int(row[0]) for row in rows]
    if applied != list(range(1, len(applied) + 1)):
        raise PostgresMigrationError("PostgreSQL şema geçmişinde sürüm boşluğu var.")
    known = {item.version: item.name for item in MIGRATIONS}
    legacy_names = {20: {"aggregate_foreign_keys_v1"}}
    if any(row[1] != known.get(int(row[0]))
           and row[1] not in legacy_names.get(int(row[0]), set()) for row in rows):
        raise PostgresMigrationError("PostgreSQL migration geçmişi kodla eşleşmiyor.")
    current = applied[-1] if applied else 0
    if current > len(MIGRATIONS):
        raise PostgresMigrationError("Veritabanı bu kodun tanımadığı daha yeni bir şemada.")

    for migration in MIGRATIONS:
        if migration.version <= current:
            continue
        connection.execute("BEGIN")
        try:
            migration.apply(connection)
            connection.execute(
                "INSERT INTO schema_migrations(version,name,applied_at) VALUES(?,?,?)",
                (migration.version, migration.name,
                 datetime.now(timezone.utc).isoformat(timespec="seconds")),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        current = migration.version
    return current
