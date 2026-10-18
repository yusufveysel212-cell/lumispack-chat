"""Production entry point: one process, shared sessions, bounded worker threads."""
import json
import logging
import os
from pathlib import Path
import threading
import time
import uuid


def configure_environment():
    root = Path(os.environ.get("LUMISPAC_DATA_HOME") or
                Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "LUMISPAC")
    settings_file = root / "config" / "server.json"
    settings = json.loads(settings_file.read_text(encoding="utf-8")) if settings_file.exists() else {}
    os.environ.setdefault("LUMISPAC_DATA_HOME", str(root))
    os.environ.setdefault("LUMISPAC_STORAGE", "postgresql")
    if os.environ["LUMISPAC_STORAGE"] not in ("postgres", "postgresql"):
        raise RuntimeError("Üretim sunucusu yalnız PostgreSQL ile çalışır; JSON'a otomatik geçiş yok.")
    os.environ.setdefault("LUMISPAC_DATABASE_URL", settings.get("database_url", "postgresql://lumispac_app@127.0.0.1:5432/lumispac"))
    os.environ.setdefault("PGPASSFILE", str(root / "postgresql" / "pgpass.conf"))
    os.environ.setdefault("LUMISPAC_DB_POOL", "on")
    os.environ.setdefault("LUMISPAC_DB_POOL_SIZE", str(settings.get("pool_size", 10)))
    for name in ("logs", "backups", "data/documents", "run"):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root, settings


def install_observability(app):
    from flask import g, jsonify, request

    @app.get("/livez")
    def live():
        return jsonify(status="ok", service="lumispac", runtime="waitress-v1")

    @app.before_request
    def started():
        g.request_started = time.perf_counter()
        g.request_id = uuid.uuid4().hex

    app.before_request_funcs[None].insert(0, app.before_request_funcs[None].pop())

    @app.after_request
    def completed(response):
        started_at = getattr(g, "request_started", None)
        if started_at is not None:
            elapsed = round((time.perf_counter() - started_at) * 1000, 1)
            response.headers["X-Request-ID"] = g.request_id
            response.headers["X-Response-Time-Ms"] = str(elapsed)
            if elapsed >= 1000:
                logging.warning("slow_request id=%s method=%s path=%s status=%s ms=%s",
                                g.request_id, request.method, request.path, response.status_code, elapsed)
        return response


def main():
    root, settings = configure_environment()
    from waitress import serve
    from lumispac_app import app
    from state import backup_poller, daily_backup, rate_poller

    install_observability(app)
    # Backups run independently; a slow dump never blocks the HTTP listener.
    def backups():
        daily_backup()
        backup_poller()
    threading.Thread(target=backups, daemon=True, name="lumispac-backups").start()
    threading.Thread(target=rate_poller, daemon=True, name="lumispac-rates").start()
    (root / "run" / "server.pid").write_text(str(os.getpid()), encoding="ascii")
    try:
        serve(app, host=os.environ.get("LUMISPAC_HOST", settings.get("host", "127.0.0.1")),
              port=int(os.environ.get("LUMISPAC_PORT", settings.get("port", 5001))),
              threads=max(4, min(32, int(settings.get("threads", 8)))),
              connection_limit=100, channel_timeout=60,
              max_request_body_size=12 * 1024 * 1024, expose_tracebacks=False)
    finally:
        from postgres_pool import close_pools
        close_pools()
        (root / "run" / "server.pid").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
