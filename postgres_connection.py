"""DB-API compatibility wrapper for the future psycopg-backed store.

The wrapper deliberately implements only operations with PostgreSQL
equivalents. It is not the store adapter; backup, schema migration and domain
operations remain the responsibility of postgres_store.py.
"""
import re

from postgres_dialect import UnsupportedSqlDialect, translate_sql


_TABLE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class HybridRow:
    """A row addressable by both numeric index and column name."""

    __slots__ = ("_values", "_names", "_mapping")

    def __init__(self, names, values):
        self._names = tuple(names)
        self._values = tuple(values)
        self._mapping = dict(zip(self._names, self._values))

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._mapping[key]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def keys(self):
        return self._names


class CursorAdapter:
    def __init__(self, cursor):
        self._cursor = cursor

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description

    @property
    def lastrowid(self):
        return None

    def _row(self, values):
        if values is None:
            return None
        names = [getattr(column, "name", None) or column[0]
                 for column in (self._cursor.description or ())]
        return HybridRow(names, values)

    def fetchone(self):
        return self._row(self._cursor.fetchone())

    def fetchall(self):
        return [self._row(row) for row in self._cursor.fetchall()]

    def __iter__(self):
        for row in self._cursor:
            yield self._row(row)


class PostgresConnection:
    """Expose the subset of sqlite3.Connection used by LUMISPAC."""

    def __init__(self, connection, release=None):
        self._connection = connection
        self._release = release
        self._closed = False
        self.dialect = "postgresql"
        self.row_factory = None  # Accepted for API compatibility; rows are hybrid.

    @staticmethod
    def _prepare(sql):
        match = re.match(r"^\s*PRAGMA\s+table_info\s*\(\s*([^)]+)\s*\)\s*;?\s*$",
                         sql, flags=re.IGNORECASE)
        if match:
            table = match.group(1).strip().strip('"')
            if not _TABLE_NAME.fullmatch(table):
                raise UnsupportedSqlDialect("Güvensiz tablo adı PRAGMA table_info içinde reddedildi.")
            query = """SELECT (c.ordinal_position - 1)::integer AS cid,
                              c.column_name AS name,
                              c.data_type AS type,
                              (c.is_nullable = 'NO') AS \"notnull\",
                              c.column_default AS dflt_value,
                              COALESCE(k.ordinal_position, 0)::integer AS pk
                       FROM information_schema.columns AS c
                       LEFT JOIN information_schema.table_constraints AS t
                         ON t.table_schema = c.table_schema AND t.table_name = c.table_name
                        AND t.constraint_type = 'PRIMARY KEY'
                       LEFT JOIN information_schema.key_column_usage AS k
                         ON k.constraint_schema = t.constraint_schema
                        AND k.constraint_name = t.constraint_name
                        AND k.table_schema = c.table_schema AND k.table_name = c.table_name
                        AND k.column_name = c.column_name
                       WHERE c.table_schema = current_schema() AND c.table_name = %s
                       ORDER BY c.ordinal_position"""
            return query, (table,)
        if re.match(r"^\s*PRAGMA\s+integrity_check\b", sql, flags=re.IGNORECASE):
            raise UnsupportedSqlDialect(
                "PostgreSQL bütünlük kontrolü domain ve catalog doğrulamalarıyla ayrıca uygulanmalı."
            )
        if re.match(r"^\s*PRAGMA\s+(foreign_keys|busy_timeout|synchronous|journal_mode)\b",
                    sql, flags=re.IGNORECASE):
            # PostgreSQL enforces FK constraints and has no SQLite journal/busy pragmas.
            return None, None
        return translate_sql(sql), None

    def execute(self, sql, parameters=()):
        # SQLite's BEGIN IMMEDIATE takes the database-wide writer reservation
        # before the transaction reads any rows. A plain PostgreSQL BEGIN
        # permits two read/modify/write transactions to race and overwrite one
        # another. Use one transaction-scoped advisory lock for every such
        # write transaction so separate app processes retain SQLite's
        # serialized-writer behavior. PostgreSQL releases it on commit/rollback.
        if re.match(r"^\s*BEGIN\s+IMMEDIATE\s*;?\s*$", sql, flags=re.IGNORECASE):
            self._connection.execute("BEGIN")
            self._connection.execute("SELECT pg_advisory_xact_lock(1279872578, 1296842307)")
            return CursorAdapter(_EmptyCursor())
        query, generated_parameters = self._prepare(sql)
        if query is None:
            return CursorAdapter(_EmptyCursor())
        parameters = generated_parameters if generated_parameters is not None else parameters
        cursor = self._connection.execute(query, parameters)
        return CursorAdapter(cursor)

    def executemany(self, sql, parameters):
        query, generated_parameters = self._prepare(sql)
        if query is None:
            return CursorAdapter(_EmptyCursor())
        if generated_parameters is not None:
            raise UnsupportedSqlDialect("PRAGMA table_info çoklu parametreyle çağrılamaz.")
        cursor = self._connection.cursor()
        cursor.executemany(query, parameters)
        return CursorAdapter(cursor)

    def cursor(self):
        return CursorAdapter(self._connection.cursor())

    def commit(self):
        return self._connection.commit()

    def rollback(self):
        return self._connection.rollback()

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._release is not None:
            return self._release(self._connection)
        return self._connection.close()


class _EmptyCursor:
    description = None
    rowcount = 0

    def fetchone(self):
        return None

    def fetchall(self):
        return []

    def __iter__(self):
        return iter(())


def connect(dsn):
    """Load psycopg only when PostgreSQL is selected and open one connection."""
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("PostgreSQL için psycopg sürücüsü kurulu değil.") from exc
    # SQLite's isolation_level=None behavior is autocommit between explicit
    # BEGIN/commit pairs. Match it so each schema migration and store write has
    # the same transaction boundary instead of psycopg's implicit transaction.
    # Fail quickly when the local PostgreSQL service is stopped so the desktop
    # launcher can show a useful error instead of appearing to hang.
    import re
    options = {"autocommit": True}
    if not re.search(r"(?:[?&]connect_timeout=|(?:^|\s)connect_timeout\s*=)", str(dsn), re.IGNORECASE):
        options["connect_timeout"] = 5
    import os
    if os.environ.get("LUMISPAC_DB_POOL", "off").lower() == "on":
        from postgres_pool import acquire
        raw, release = acquire(dsn, options)
        return PostgresConnection(raw, release)
    return PostgresConnection(psycopg.connect(dsn, **options))
