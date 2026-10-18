# -*- coding: utf-8 -*-
"""
LUMISPAC - Ortak Yardımcı Fonksiyonlar
Tum modullerin kullandigi fonksiyonlar burada toplanmistir.

Kullanim:
    from utils import f, read_json, write_json, num, fmt, TL, yuzde
"""
import os
import json
import logging
import secrets
import hashlib
from datetime import datetime

log = logging.getLogger(__name__)


# =========================================================
# SAYI DONUSUMU
# =========================================================
def f(v, d=0.0):
    """Guvenli float donusumu. Hata olursa varsayilan dondurur."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def num(v, d=0.0):
    """String'den sayi cikarma (Turkce virgul destegi)."""
    if v is None:
        return d
    try:
        s = str(v).strip().replace(' ', '')
        if ',' in s and '.' in s:
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            s = s.replace(',', '.')
        return float(s)
    except (TypeError, ValueError):
        return d


def int_f(v, d=0):
    """Guvenli integer donusumu."""
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return d


# =========================================================
# FORMATLAMA
# =========================================================
def fmt(n, d=2):
    """Turkce sayi formati: 1234.56 -> '1.234,56'"""
    if n is None:
        return '-'
    try:
        n = float(n)
        if not (n == n):  # NaN kontrolu
            return '-'
        return f'{n:,.{d}f}'.replace(',', '_').replace('.', ',').replace('_', '.')
    except (TypeError, ValueError):
        return '-'


def TL(n, d=2):
    """Turk Lirasi formati: 1234.56 -> '1.234,56 TL'"""
    if n is None:
        return '-'
    return fmt(n, d) + ' TL'


def pct(v, d=2):
    """Yuzde formati: 0.25 -> '%25,00'"""
    if v is None:
        return '-'
    try:
        return fmt(v * 100, d) + '%'
    except (TypeError, ValueError):
        return '-'


def yuzde(v, d=2):
    """Yuzde formati (alternatif): 25.0 -> '%25,00'"""
    return pct(v / 100.0 if v else 0, d)


# =========================================================
# DOSYA OKUMA/YAZMA (JSON)
# =========================================================
class DataIntegrityError(RuntimeError):
    """Kalıcı veri dosyası okunamadığında sessiz veri kaybını önleyen hata."""


def read_json(path, default=None):
    """JSON oku; yalnızca bulunmayan dosyada varsayılanı kullan.

    Bozuk veya erişilemeyen dosyayı boş veri gibi ele almak, sonraki yazımda
    kayıtların üzerine yazılmasına neden olabilir. Bu nedenle veri hatası yükseltilir.
    """
    if default is None:
        default = {}
    try:
        try:
            from storage_adapter import get_storage_adapter
            adapter = get_storage_adapter()
            if adapter is not None and adapter.managed_json_path(path):
                return adapter.read_document(path, default)
        except ImportError:
            pass
        with open(path, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default
    except (OSError, json.JSONDecodeError) as exc:
        log.exception('Kalıcı JSON verisi okunamadı: %s', path)
        raise DataIntegrityError('Kalıcı veri dosyası okunamadı; kayıtlar korunmak üzere işlem durduruldu.') from exc


def write_json(path, data):
    """JSON/SQLite kalıcı kaydını dayanıklı biçimde yazar."""
    try:
        from storage_adapter import get_storage_adapter
        adapter = get_storage_adapter()
        if adapter is not None and adapter.managed_json_path(path):
            adapter.write_documents({path: data})
            return
    except ImportError:
        pass
    from tempfile import mkstemp

    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = mkstemp(prefix=os.path.basename(path) + '.', suffix='.tmp', dir=directory)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2, allow_nan=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


# =========================================================
# KIMLIK VE HASH
# =========================================================
def write_json_many(values):
    """Birden fazla kayıt dosyasını SQLite modunda tek işlemde yazar."""
    values = dict(values or {})
    if not values:
        return
    try:
        from storage_adapter import get_storage_adapter
        adapter = get_storage_adapter()
        managed = ([adapter.managed_json_path(path) for path in values]
                   if adapter is not None else [False] * len(values))
        if all(managed):
            adapter.write_documents(values)
            return
        if any(managed):
            raise ValueError("Tek işlemde JSON ve SQLite kayıtları karıştırılamaz.")
    except ImportError:
        pass
    for path, data in values.items():
        write_json(path, data)


def yeni_id(uzunluk=12):
    """Rastgele ID uretir. Ornek: 'a1b2c3d4e5f6'"""
    return secrets.token_hex(uzunluk // 2)


def hash_sifre(sifre, tuz='lumispac_v2_salt'):
    """Sifreyi SHA-256 ile hashler."""
    return hashlib.sha256((tuz + sifre).encode('utf-8')).hexdigest()


def sifre_dogrula(sifre, sifre_hash, tuz='lumispac_v2_salt'):
    """Sifre dogru mu?"""
    return hash_sifre(sifre, tuz) == sifre_hash


# =========================================================
# ZAMAN
# =========================================================
def simdi_iso(kisa=False):
    """ISO formatinda simdiki zaman."""
    if kisa:
        return datetime.now().isoformat(timespec='minutes')
    return datetime.now().isoformat(timespec='seconds')


def bugun_str():
    """Bugunun tarihi: 'YYYY-MM-DD'"""
    return datetime.now().strftime('%Y-%m-%d')


def tarih_parse(s):
    """String'i datetime'a cevirir. Hata olursa None."""
    if not s:
        return None
    for fmt_str in ('%Y-%m-%d', '%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S',
                    '%d.%m.%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(str(s)[:19], fmt_str)
        except (ValueError, TypeError):
            continue
    return None


# =========================================================
# STRING YARDIMCILARI
# =========================================================
def temizle(s, varsayilan=''):
    """String'i temizler (None kontrolu + strip)."""
    if s is None:
        return varsayilan
    return str(s).strip()


def kisalt(s, uzunluk=100):
    """Uzun string'i kirpar."""
    s = str(s or '')
    return s[:uzunluk] + ('...' if len(s) > uzunluk else '')


def guvenli_ad(s):
    """Dosya adi icin guvenli hale getirir."""
    return ''.join(c if c.isalnum() or c in '_-' else '_' for c in str(s))
