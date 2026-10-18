"""
LUMISPAC — Kur Kaynakları Modülü
7 katmanlı, kademeli kur sistemi + kaynak sağlık takibi + otomatik karantina.
"""
import time
import json
import logging
import threading
from datetime import datetime, timedelta
from collections import deque

import requests

# ==== YENI: Ortak moduller ====
from config import (
    HTTP_TIMEOUT as _CFG_HTTP_TIMEOUT,
    USER_AGENT as _CFG_UA,
)
from utils import num as _parse_num_util
# ==== /YENI ====


HTTP_TIMEOUT = _CFG_HTTP_TIMEOUT
QUARANTINE_SECONDS = 300
FAIL_THRESHOLD = 10
HEALTH_WINDOW = 300

UA = _CFG_UA
SESSION = requests.Session()
SESSION.headers.update(UA)
SESSION.headers.update({'Cache-Control': 'no-cache', 'Pragma': 'no-cache'})


class SourceHealth:
    def __init__(self, name):
        self.name = name
        self.ok = True
        self.last_ok = 0.0
        self.last_fail = 0.0
        self.fails_in_window = deque(maxlen=200)
        self.quarantined_until = 0.0
        self.total_ok = 0
        self.total_fail = 0
        self._last_logged_state = True

    def record_ok(self):
        now = time.time()
        self.ok = True
        self.last_ok = now
        self.total_ok += 1
        if not self._last_logged_state:
            if self.last_fail:
                down = int(now - self.last_fail)
                logging.info('%s: tekrar çalışıyor (%d sn kesinti sonrası)', self.name, down)
            else:
                logging.info('%s: ilk bağlantı başarılı', self.name)
            self._last_logged_state = True

    def record_fail(self, err):
        now = time.time()
        self.ok = False
        self.last_fail = now
        self.total_fail += 1
        self.fails_in_window.append(now)
        if self.recent_fail_count() >= FAIL_THRESHOLD:
            self.quarantined_until = now + QUARANTINE_SECONDS
            if self._last_logged_state:
                logging.warning('%s: %d hata -> %d sn karantina',
                                self.name, self.recent_fail_count(), QUARANTINE_SECONDS)
                self._last_logged_state = False

    def recent_fail_count(self):
        cutoff = time.time() - HEALTH_WINDOW
        return sum(1 for t in self.fails_in_window if t >= cutoff)

    def is_available(self):
        return time.time() >= self.quarantined_until

    def quarantine_remaining(self):
        return max(0, int(self.quarantined_until - time.time()))

    def snapshot(self):
        return {
            'name': self.name,
            'ok': self.ok,
            'last_ok': self.last_ok,
            'last_fail': self.last_fail,
            'recent_fails': self.recent_fail_count(),
            'total_ok': self.total_ok,
            'total_fail': self.total_fail,
            'quarantined': self.quarantine_remaining() > 0,
            'quarantine_remaining': self.quarantine_remaining(),
        }


_parse_num = _parse_num_util  # utils.num alias



# Harem Altın sitesinin kendi canlı USD/TRY yayını. Tek bağlantıyı koruyarak
# her güncellemede yeniden websocket el sıkışması yapmayız.
_HAREM_URL = 'wss://hrmsocketonly.haremaltin.com:443/socket.io/?EIO=4&transport=websocket'
_HAREM_ORIGIN = 'https://www.haremaltin.com'
_harem_lock = threading.Lock()
_harem_socket = None


def _close_harem_socket():
    global _harem_socket
    ws, _harem_socket = _harem_socket, None
    if ws is not None:
        try:
            ws.close()
        except Exception:
            pass


def fetch_harem():
    """Harem Altın USDTRY yayınının satış fiyatını ana kur olarak döndürür."""
    global _harem_socket
    import websocket

    with _harem_lock:
        try:
            if _harem_socket is None:
                _harem_socket = websocket.create_connection(
                    _HAREM_URL,
                    timeout=max(HTTP_TIMEOUT, 4),
                    origin=_HAREM_ORIGIN,
                    header=['User-Agent: ' + UA.get('User-Agent', 'Mozilla/5.0')],
                )
                opening = _harem_socket.recv()
                if not isinstance(opening, str) or not opening.startswith('0'):
                    raise ValueError('Harem Altın bağlantı açılış paketi geçersiz')
                _harem_socket.send('40')

            deadline = time.monotonic() + max(HTTP_TIMEOUT, 4)
            while time.monotonic() < deadline:
                packet = _harem_socket.recv()
                if not isinstance(packet, str):
                    continue
                if packet.startswith('2'):
                    _harem_socket.send('3')
                    continue
                if not packet.startswith('42'):
                    continue
                event = json.loads(packet[2:])
                if not isinstance(event, list) or len(event) < 2 or event[0] != 'price_changed':
                    continue
                payload = event[1] if isinstance(event[1], dict) else {}
                usd = (payload.get('data') or {}).get('USDTRY')
                if not isinstance(usd, dict):
                    continue
                selling = float(str(usd.get('satis', '')).replace(',', '.'))
                buying = float(str(usd.get('alis', 0) or 0).replace(',', '.'))
                if selling <= 0:
                    raise ValueError('Harem Altın USDTRY satış fiyatı geçersiz')
                return {
                    'v': selling,
                    'bid': buying,
                    'hi': float(str(usd.get('yuksek', 0) or 0).replace(',', '.')),
                    'lo': float(str(usd.get('dusuk', 0) or 0).replace(',', '.')),
                    'market': '',
                    'mdate': str(usd.get('tarih') or ''),
                }
            raise TimeoutError('Harem Altın USDTRY verisi zamanında gelmedi')
        except Exception:
            _close_harem_socket()
            raise


def fetch_yahoo():
    r = SESSION.get(
        'https://query1.finance.yahoo.com/v8/finance/chart/USDTRY=X',
        params={'interval': '1m', 'range': '1d'}, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    meta = r.json()['chart']['result'][0]['meta']
    v = float(meta['regularMarketPrice'])
    return {'v': v, 'bid': 0.0, 'hi': 0.0, 'lo': 0.0, 'market': '', 'mdate': ''}


def fetch_biquote():
    r = SESSION.get('https://api.biquote.io/v1/quote',
                    params={'symbols': 'USDTRY,TFX,GA'}, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    usd = data.get('USDTRY') or (data.get('data') or {}).get('USDTRY')
    if not usd:
        if isinstance(data, list):
            for it in data:
                if str(it.get('symbol', '')).upper() == 'USDTRY':
                    usd = it
                    break
    if not usd:
        raise ValueError('USDTRY verisi bulunamadi (biquote)')
    bid = float(usd.get('bid') or usd.get('buy') or 0)
    ask = float(usd.get('ask') or usd.get('sell') or usd.get('price') or 0)
    v = ask if ask > 0 else bid
    if v <= 0:
        raise ValueError('biquote: gecersiz fiyat')
    return {'v': v, 'bid': bid, 'hi': 0.0, 'lo': 0.0, 'market': '', 'mdate': ''}


_burkut_client = None


def _get_burkut():
    global _burkut_client
    if _burkut_client is False:
        return None
    if _burkut_client is not None:
        return _burkut_client
    try:
        from burkut import Burkut
        _burkut_client = Burkut()
        return _burkut_client
    except Exception as e:
        logging.info('Burkut SDK yuklu degil, atlaniyor (%s)', e)
        _burkut_client = False
        return None


def fetch_burkut():
    client = _get_burkut()
    if client is None:
        raise ValueError('Burkut SDK yuklu degil (pip install burkut)')
    usd = None
    for meth in ('currency', 'currencies', 'doviz', 'forex'):
        fn = getattr(client, meth, None)
        if fn:
            try:
                res = fn('USD')
                if res:
                    usd = res
                    break
            except Exception:
                continue
    if not usd:
        raise ValueError('Burkut: USD verisi alinamadi')
    if isinstance(usd, dict):
        v = float(usd.get('selling') or usd.get('sell') or usd.get('satis')
                  or usd.get('rate') or usd.get('value') or 0)
        bid = float(usd.get('buying') or usd.get('buy') or usd.get('alis') or 0)
    else:
        v = float(usd); bid = 0.0
    if v <= 0:
        raise ValueError('Burkut: gecersiz fiyat')
    return {'v': v, 'bid': bid, 'hi': 0.0, 'lo': 0.0, 'market': '', 'mdate': ''}


def fetch_tcmb():
    import xml.etree.ElementTree as ET
    r = SESSION.get('https://www.tcmb.gov.tr/kurlar/today.xml', timeout=HTTP_TIMEOUT + 2)
    r.raise_for_status()
    for c in ET.fromstring(r.content).iter('Currency'):
        if c.get('Kod') == 'USD':
            selling = float(c.find('ForexSelling').text)
            buying_el = c.find('ForexBuying')
            buying = float(buying_el.text) if buying_el is not None else 0.0
            return {'v': selling, 'bid': buying, 'hi': 0.0, 'lo': 0.0,
                    'market': 'KAPALI', 'mdate': datetime.now().strftime('%d/%m/%y')}
    raise ValueError('TCMB: USD bulunamadi')


def fetch_darphane():
    urls = [
        'https://cdn.jsdelivr.net/gh/ozgurgunes/darphane@master/data/usd.json',
        'https://raw.githubusercontent.com/ozgurgunes/darphane/master/data/usd.json',
    ]
    last_err = None
    for url in urls:
        try:
            r = SESSION.get(url, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            v = float(data.get('selling') or data.get('sell') or data.get('Satis')
                      or data.get('satis') or 0)
            bid = float(data.get('buying') or data.get('buy') or data.get('Alis')
                        or data.get('alis') or 0)
            if v > 0:
                return {'v': v, 'bid': bid, 'hi': 0.0, 'lo': 0.0, 'market': '',
                        'mdate': data.get('date', '')}
        except Exception as e:
            last_err = e
            continue
    raise ValueError('Darphane CDN: %s' % (last_err or 'veri yok'))


def fetch_canlidoviz():
    import html as html_lib
    import re
    r = SESSION.get('https://canlidoviz.com/doviz-kurlari/dolar',
                    params={'_': int(time.time())}, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    text = html_lib.unescape(r.text)
    text = re.sub(r'<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>',
                  ' ', text, flags=re.I | re.S)
    text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', text))
    m = re.search(r'(?:USD\s+)?Dolar\s+.*?([0-9][0-9.,]*)\s+([0-9][0-9.,]*)',
                  text, re.I)
    v = bid = 0.0
    if m:
        try:
            bid = _parse_num(m.group(1))
            v = _parse_num(m.group(2))
        except ValueError:
            pass
    if not v:
        m2 = re.search(r'SATIS\s*FIYATI\s*[:]?\s*([0-9][0-9.,]*)', text, re.I)
        if m2:
            try:
                v = _parse_num(m2.group(1))
            except ValueError:
                pass
    if not v:
        raise ValueError('canlidoviz: satis fiyati bulunamadi')
    mm = re.search(r'PIYASA\s*(ACIK|KAPALI)\s*([0-9]{2}/[0-9]{2}/[0-9]{2})?', text)
    market = mm.group(1) if mm else ''
    mdate = (mm.group(2) or '') if mm else ''
    return {'v': v, 'bid': bid, 'hi': 0.0, 'lo': 0.0, 'market': market, 'mdate': mdate}


SOURCES = [
    ('Harem Altın',    fetch_harem,     False),
    ('Yahoo Finance',  fetch_yahoo,     True),
    ('biquote.io',     fetch_biquote,   True),
    ('Burkut SDK',     fetch_burkut,    True),
    ('TCMB (resmi)',   fetch_tcmb,      True),
    ('Darphane CDN',   fetch_darphane,  True),
    ('canlidoviz.com', fetch_canlidoviz, True),
]

HEALTH = {name: SourceHealth(name) for name, _, _ in SOURCES}


def fetch_rate(last_rate=0.0):
    errors = []
    for name, fn, is_fb in SOURCES:
        health = HEALTH[name]
        if not health.is_available():
            errors.append('%s: karantinada (%d sn)' % (name, health.quarantine_remaining()))
            continue
        try:
            t0 = time.time()
            data = fn()
            v = data['v']
            if not (1 < v < 1000):
                raise ValueError('Aralik disi: %s' % v)
            if last_rate and abs(v - last_rate) / last_rate > 0.15:
                raise ValueError('Ani sicrama: %s (onceki %s)' % (v, last_rate))
            health.record_ok()
            data['source'] = name
            data['fallback'] = is_fb
            data['all_failed'] = False
            data['errors'] = errors
            data['elapsed_ms'] = int((time.time() - t0) * 1000)
            return data
        except Exception as e:
            health.record_fail(e)
            errors.append('%s: %s' % (name, e))
    return {
        'v': 0.0, 'bid': 0.0, 'hi': 0.0, 'lo': 0.0, 'market': '', 'mdate': '',
        'source': '', 'fallback': False, 'all_failed': True, 'errors': errors,
    }


def health_snapshot():
    return [HEALTH[name].snapshot() for name, _, _ in SOURCES]