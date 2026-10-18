"""Bounded process-local connections; callers retain explicit transaction ownership."""
import atexit
import os
import threading

_lock = threading.Lock()
_pools = {}


def acquire(dsn, options):
    from psycopg_pool import ConnectionPool

    key = (os.getpid(), dsn)
    with _lock:
        pool = _pools.get(key)
        if pool is None:
            size = max(2, min(32, int(os.environ.get("LUMISPAC_DB_POOL_SIZE", "10"))))
            connection_options = dict(options)
            connection_options.setdefault("options", (os.environ.get("PGOPTIONS", "") +
                " -c statement_timeout=30000 -c lock_timeout=10000 -c idle_in_transaction_session_timeout=60000").strip())
            pool = ConnectionPool(dsn, min_size=1, max_size=size, max_waiting=32,
                                  timeout=5, kwargs=connection_options, open=False)
            try:
                pool.open(wait=True, timeout=5)
            except Exception:
                pool.close()
                raise
            _pools[key] = pool
    raw = pool.getconn(timeout=5)

    def release(connection):
        try:
            if not connection.closed:
                connection.rollback()
        except Exception:
            connection.close()
        finally:
            pool.putconn(connection)

    return raw, release


def close_pools():
    with _lock:
        pools = list(_pools.values())
        _pools.clear()
    for pool in pools:
        pool.close()


atexit.register(close_pools)
