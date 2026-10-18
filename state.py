"""
LUMISPAC v3 - Global State ve Baslatma (state.py)

Bu modul, uygulamanin global durumunu ve baslatma fonksiyonlarini icerir.
lumispac_app.py'den ayrilmistir.
"""
import os
import logging
import threading
import time
import json
import re
from datetime import datetime, date, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path

import requests

# utils ve config'ten gerekli olanlar
from utils import read_json, write_json, simdi_iso
from data_repository import list_products as repository_list_products, read_settings as repository_read_settings
from data_repository import replace_products as repository_replace_products, save_settings as repository_save_settings
from config import (
    BASE, DATA_FILE, SET_FILE, QUOTE_FILE, DEALER_FILE, ORDER_FILE,
    LOG_FILE, USERS_FILE, BACKUP_DIR,
    POLL_SECONDS, HTTP_TIMEOUT, USER_AGENT,
    DEFAULT_SETTINGS, SEED_PRODUCTS, SEED_PRODUCT_VOLUME_ESTIMATES, DEFAULT_VOLUME,
)


# ==== GLOBAL STATE ====
_lock = threading.RLock()
_rate_cache = {'rate': None, 'ts': 0, 'source': 'yok', 'history': [], 'ok_at': 0,
               'bid': 0.0, 'hi': 0.0, 'lo': 0.0, 'market': '', 'mdate': '',
               'fallback': False, 'elapsed_ms': 0, 'status': 'Kur bekleniyor', 'checked_at': None}
_errors = []
_sessions = {}
_sessions_lock = threading.RLock()


def get_lock():
    """Global kilidi doner."""
    return _lock


def get_rate_cache():
    """Kur cache'ini doner."""
    return _rate_cache


def push_error(mesaj):
    """Hata listesine ekle (son 100 kayit tutulur)."""
    _errors.append({'ts': simdi_iso(), 'mesaj': str(mesaj)})
    if len(_errors) > 100:
        _errors.pop(0)


def get_errors():
    """Hata listesini doner."""
    return list(_errors)


def clear_errors():
    """Hatalari temizle."""
    _errors.clear()



def get_sessions():
    """Aktif oturumlari doner."""
    return _sessions


def get_sessions_lock():
    """Oturum kilidini doner."""
    return _sessions_lock


# ==== LOG YONETIMI ====
def setup_logging():
    """Rotating log kur."""
    os.makedirs(os.path.dirname(os.path.abspath(LOG_FILE)), exist_ok=True)
    handler = RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=5, encoding='utf-8'
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    ))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # Cift handler'i engelle
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        root.addHandler(handler)


# ==== KUR YONETIMI ====
def save_rate(rate, source='bilinmiyor', details=None):
    """Kuru ve sağlayıcı bilgisini cache'e yazar; ayar dosyasını yalnızca kur değişince günceller."""
    global _rate_cache
    now = time.time()
    previous = _rate_cache.get('rate')
    changed = previous is None or abs(float(previous or 0) - float(rate or 0)) > 0.0000001
    details = details if isinstance(details, dict) else {}
    _rate_cache.update({
        'rate': rate, 'ts': now, 'source': source, 'ok_at': int(now),
        'bid': details.get('bid', _rate_cache.get('bid', 0.0)),
        'hi': details.get('hi', _rate_cache.get('hi', 0.0)),
        'lo': details.get('lo', _rate_cache.get('lo', 0.0)),
        'market': details.get('market', _rate_cache.get('market', '')),
        'mdate': details.get('mdate', _rate_cache.get('mdate', '')),
        'fallback': bool(details.get('fallback', False)),
        'elapsed_ms': details.get('elapsed_ms', _rate_cache.get('elapsed_ms', 0)),
        'status': 'Güncel',
        'checked_at': datetime.now().isoformat(timespec='seconds'),
    })
    history = _rate_cache.setdefault('history', [])
    if changed or not history:
        history.append({'t': simdi_iso(), 'v': rate})
        if len(history) > 100:
            del history[:-100]
    # Sık arka plan kontrolünde gereksiz disk yazımını önle.
    if changed:
        try:
            settings = repository_read_settings(SET_FILE, dict(DEFAULT_SETTINGS))
            settings['rate'] = rate
            repository_save_settings(settings, SET_FILE)
        except Exception as e:
            push_error(f'save_rate: {e}')


def update_rate(sess=None):
    """Kur'u kaynaklardan cek."""
    try:
        from rate_sources import fetch_rate
        sonuc = fetch_rate(_rate_cache.get('rate'))
        if sonuc and sonuc.get('v'):
            save_rate(sonuc['v'], sonuc.get('source', 'bilinmiyor'), sonuc)
            return True
    except Exception as e:
        push_error(f'update_rate: {e}')
    return False


def rate_poller():
    """Arka planda kur'u guncelleyen thread."""
    while True:
        started = time.monotonic()
        try:
            update_rate()
        except Exception as e:
            push_error(f'rate_poller: {e}')
        time.sleep(max(0.0, POLL_SECONDS - (time.monotonic() - started)))


# ==== YEDEK YONETIMI ====
_DAILY_FULL_BACKUP = re.compile(r'^lumispac_full_(\d{8})\.(?:dump|backup|sqlite3)$')
_DAILY_JSON_BACKUP = re.compile(r'^lumispac_data_(\d{4}-\d{2}-\d{2})\.json$')
BACKUP_RETENTION_DAYS = 30


def _prune_daily_backups(today=None):
    """Remove only app-generated daily snapshots older than the retention window."""
    today = today or date.today()
    cutoff = today - timedelta(days=BACKUP_RETENTION_DAYS - 1)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    removed = 0
    for name in os.listdir(BACKUP_DIR):
        match = _DAILY_FULL_BACKUP.fullmatch(name)
        if match:
            snapshot_date = datetime.strptime(match.group(1), '%Y%m%d').date()
        else:
            match = _DAILY_JSON_BACKUP.fullmatch(name)
            if not match:
                continue
            snapshot_date = date.fromisoformat(match.group(1))
        if snapshot_date < cutoff:
            path = os.path.join(BACKUP_DIR, name)
            if os.path.isfile(path):
                os.remove(path)
                removed += 1
    return removed


def daily_backup():
    """Create one full snapshot per day and prune daily snapshots past 30 days."""
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        from storage_adapter import get_storage_adapter
        adapter = get_storage_adapter()
        if adapter is not None:
            bugun = date.today().strftime('%Y%m%d')
            extension = getattr(adapter, 'BACKUP_EXTENSION', '.backup')
            hedef = os.path.join(BACKUP_DIR, f'lumispac_full_{bugun}{extension}')
            if not os.path.isfile(hedef) or os.path.getsize(hedef) <= 0:
                adapter.backup_database(hedef)
            if not os.path.isfile(hedef) or os.path.getsize(hedef) <= 0:
                raise RuntimeError('Günlük tam yedek dosyası doğrulanamadı.')
        else:
            bugun = date.today().isoformat()
            hedef = os.path.join(BACKUP_DIR, f'lumispac_data_{bugun}.json')
            if not os.path.exists(hedef):
                data = read_json(DATA_FILE, [])
                write_json(hedef, data)
        _prune_daily_backups()
        return hedef
    except Exception as e:
        push_error(f'daily_backup: {e}')
        return None


def stamp_backup(aciklama=''):
    """Elle yedek al."""
    try:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        from storage_adapter import get_storage_adapter
        adapter = get_storage_adapter()
        if adapter is not None:
            extension = getattr(adapter, 'BACKUP_EXTENSION', '.backup')
            hedef = os.path.join(BACKUP_DIR, f'lumispac_full_{ts}{extension}')
            adapter.backup_database(hedef)
            return hedef
        hedef = os.path.join(BACKUP_DIR, f'lumispac_data_{ts}.json')
        data = read_json(DATA_FILE, [])
        write_json(hedef, data)
        return hedef
    except Exception as e:
        push_error(f'stamp_backup: {e}')
        return None


def backup_poller():
    """Retry daily backup and retention checks hourly while the app is running."""
    while True:
        time.sleep(60 * 60)
        daily_backup()


# ==== VERI YUKLEME ====
def load_products():
    """Ürünleri etkin repository’den oku."""
    return repository_list_products(DATA_FILE)


def load_settings():
    """Ayarları etkin repository’den oku."""
    return repository_read_settings(SET_FILE, dict(DEFAULT_SETTINGS))


# ==== SESSION YARDIMCILARI ====
def _session_al():
    """Aktif oturumu cookie'den okur."""
    from flask import request
    sessions = get_sessions()
    with get_sessions_lock():
        # Eski istemciler süresi geçmiş X-Auth-Token gönderebilir. Geçersiz
        # başlık, tarayıcının geçerli HttpOnly oturum çerezini gölgelemesin.
        for token in (request.headers.get('X-Auth-Token'), request.cookies.get('lum_token')):
            if not token:
                continue
            session = sessions.get(token)
            if not session:
                continue
            if session.get('expires', 0) < time.time():
                sessions.pop(token, None)
                continue
            # Oturum ekranı gerçek etkinliği göstersin; sabit son kullanma süresini uzatmaz.
            session['last_seen'] = time.time()
            return session
        return None


def _session_bilgi():
    """Aktif oturum + kullanici bilgisi doner."""
    import auth_module
    s = _session_al()
    if not s:
        return None, None
    k = auth_module.kullanici_getir(s['user_id'])
    return s, k



# ==== FAZ 3: TASINDI ====
def merge_seed(items):
    """Var olan urunlere dokunmaz (fire/nakliye/isclik/fiyat aynen kalir);
    yalnizca eksikleri ekler."""
    from helpers import normalize, same
    items = [dict(p) for p in items]
    added = 0
    for code, name, w, q, sale in SEED_PRODUCTS:
        cand = {'name': name, 'weight': w, 'qty': q}
        hit = next((p for p in items if same(p, cand)), None)
        if hit:
            if hit.get('code') in (None, '', 'LUM-PAK'):
                hit['code'] = code
            if hit.get('sale') is None and sale is not None:
                hit['sale'] = float(sale)
        else:
            volume = SEED_PRODUCT_VOLUME_ESTIMATES.get(code)
            items.append(normalize({'code': code, 'name': name, 'weight': w, 'qty': q, 'sale': sale,
                                    'volume': volume or 0,
                                    'volume_source': 'estimate' if volume else 'unknown'}))
            added += 1
    return items, added


def startup_seed():
    s = load_settings()
    if s.get('seed_v1'):
        return
    with _lock:
        items, _ = merge_seed(load_products())
        daily_backup()
        repository_replace_products(items, DATA_FILE)
        s['seed_v1'] = True
        repository_save_settings(s, SET_FILE)
