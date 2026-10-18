"""
LUMISPAC — Kimlik ve Yetki Modulu
Departman, kullanici, yetki ve log yonetimi.
"""
import os
import json
import hashlib
import secrets
import threading
from copy import deepcopy
from datetime import datetime, timedelta

from flask import g, has_request_context, request

# ==== YENI: Ortak moduller ====
from utils import (
    yeni_id, hash_sifre, sifre_dogrula,
    simdi_iso, bugun_str, tarih_parse,
    f, num, fmt, TL, read_json, write_json,
)
from config import BASE, USERS_FILE
# ==== /YENI ====


# =========================================================
# DOSYA YOLLARI
# =========================================================
# Global kilit
_lock = threading.RLock()


# =========================================================
# SABITLER
# =========================================================

# Modul listesi (sabit, degismez)
MODULLER = [
    {'id': 'genel_bakis', 'ad': 'Genel Bakış', 'ikon': '🏠'},
    {'id': 'urunler', 'ad': 'Ürünler ve Maliyet', 'ikon': '📦'},
    {'id': 'senaryo', 'ad': 'Senaryo', 'ikon': '🎯'},
    {'id': 'sepet', 'ad': 'Sipariş ve Tır', 'ikon': '🛒'},
    {'id': 'teklifler', 'ad': 'Teklifler', 'ikon': '📄'},
    {'id': 'siparisler', 'ad': 'Siparişler', 'ikon': '📋'},
    {'id': 'bayiler', 'ad': 'Bayiler', 'ikon': '🏪'},
    {'id': 'raporlar', 'ad': 'Raporlar', 'ikon': '📈'},
    {'id': 'ayarlar', 'ad': 'Ayarlar', 'ikon': '⚙️'},
    {'id': 'finans', 'ad': 'Finans', 'ikon': '💰'},
    {'id': 'stok', 'ad': 'Stok', 'ikon': '📦'},
    {'id': 'siparis_sevk', 'ad': 'Sipariş Sevk Yetkisi', 'ikon': '🚚'},
    {'id': 'uretim', 'ad': 'Üretim Planlama', 'ikon': '🏭'},
    {'id': 'siparis_depo', 'ad': 'Sipariş Depo Kontrolü', 'ikon': '🔎'},
    {'id': 'uretim_depo', 'ad': 'Üretim Depo Kabul Yetkisi', 'ikon': '📥'},
    {'id': 'hammaddeler', 'ad': 'Hammadde Kataloğu ve Stok', 'ikon': '🧱'},
    {'id': 'satinalma', 'ad': 'Hammadde Tedarik ve Satın Alma', 'ikon': '🧾'},
    {'id': 'satinalma_odeme', 'ad': 'Hammadde Alım Ödemeleri', 'ikon': '💳'},
    {'id': 'hammadde_depo', 'ad': 'Hammadde Depo Kabulü', 'ikon': '📥'},
    {'id': 'receteler', 'ad': 'Ürün Reçeteleri', 'ikon': '🧪'},
    {'id': 'kar_maliyet', 'ad': 'Kâr, Marj ve Maliyet Verileri', 'ikon': '🔒'},
    {'id': 'disa_aktar', 'ad': 'Excel/CSV Dışa Aktarma', 'ikon': '📤'},
    {'id': 'kritik_onay', 'ad': 'Kritik İşlem Onayı', 'ikon': '🛡️'},
    {'id': 'kullanicilar', 'ad': 'Bağlı Ekip İzinleri', 'ikon': '👥'},
]

# Yetki seviyeleri
YETKI_PROFILLERI = {
    'satis': {'ad': 'Satış ekibi', 'aciklama': 'Satış ve bayi kayıtları; maliyet/kâr kapalı.', 'moduller': {
        'genel_bakis': 'okur', 'urunler': 'okur', 'senaryo': 'tam', 'sepet': 'tam',
        'teklifler': 'tam', 'siparisler': 'tam', 'bayiler': 'tam', 'raporlar': 'okur',
        'kar_maliyet': 'gormez', 'finans': 'gormez', 'uretim': 'gormez', 'disa_aktar': 'yazar', 'kritik_onay': 'gormez'}},
    'uretim': {'ad': 'Üretim ekibi', 'aciklama': 'Üretim operasyonu; şirket maliyet ve kâr verileri kapalı.', 'moduller': {
        'genel_bakis': 'okur', 'urunler': 'okur', 'stok': 'yazar', 'uretim': 'yazar',
        'hammaddeler': 'okur', 'receteler': 'yazar', 'kar_maliyet': 'gormez', 'disa_aktar': 'gormez', 'kritik_onay': 'gormez'}},
    'depo': {'ad': 'Depo ekibi', 'aciklama': 'Stok, sevk ve kabul operasyonları; maliyet/kâr kapalı.', 'moduller': {
        'genel_bakis': 'okur', 'siparisler': 'yazar', 'siparis_sevk': 'yazar', 'stok': 'tam',
        'uretim': 'okur', 'siparis_depo': 'yazar', 'uretim_depo': 'yazar',
        'hammaddeler': 'okur', 'hammadde_depo': 'yazar', 'kar_maliyet': 'gormez', 'disa_aktar': 'gormez', 'kritik_onay': 'gormez'}},
    'finans': {'ad': 'Finans ekibi', 'aciklama': 'Finans, şirket geneli satış, maliyet ve kârlılık raporları.', 'moduller': {
        'genel_bakis': 'okur', 'urunler': 'okur', 'siparisler': 'okur', 'teklifler': 'okur',
        'bayiler': 'okur', 'raporlar': 'tam', 'finans': 'tam', 'hammaddeler': 'okur',
        'satinalma': 'okur', 'satinalma_odeme': 'yazar', 'kar_maliyet': 'tam', 'disa_aktar': 'tam', 'kritik_onay': 'gormez'}},
}

YETKI_SEVIYELERI = {
    'gormez': 0,   # Gormez
    'okur': 1,     # Sadece gorur
    'yazar': 2,    # İşlem yapar
    'onay': 3,     # Onay işlemi
    'tam': 4,      # Modülü yönetir
}

# Departman ikonlari (dropdown icin)
DEPARTMAN_IKONLARI = ['👑', '📦', '🏭', '💼', '💰', '👁️', '🔧', '📊', '🛡️', '⚙️', '🚚', '🔒']

# Departman renkleri (dropdown icin)
DEPARTMAN_RENKLERI = ['#C8102E', '#0891B2', '#059669', '#D97706', '#7C3AED', '#6B7280', '#E11D48', '#0EA5E9', '#F59E0B', '#10B981']


# Varsayilan departmanlar (ilk kurulumda olusturulur)
VARSAYILAN_DEPARTMANLAR = [
    {
        'id': 'yonetici',
        'ad': 'Yönetici',
        'ikon': '👑',
        'renk': '#C8102E',
        'aciklama': 'Tam yetkili yönetici',
        'sistem': True,  # Silinemez
        'moduller': {m['id']: 'tam' for m in MODULLER},
    },
    {
        'id': 'depo',
        'ad': 'Depo Sorumlusu',
        'ikon': '📦',
        'renk': '#0891B2',
        'aciklama': 'Stok ve sevkiyat yönetimi',
        'sistem': False,
        'moduller': {
            'genel_bakis': 'okur',
            'siparisler': 'yazar',
            'siparis_sevk': 'yazar',
            'raporlar': 'okur',
            'stok': 'tam',
            'uretim': 'okur',
            'siparis_depo': 'yazar',
            'uretim_depo': 'yazar',
            'hammaddeler': 'okur',
            'hammadde_depo': 'yazar',
        },
    },
    {
        'id': 'uretim',
        'ad': 'Üretim Şefi',
        'ikon': '🏭',
        'renk': '#059669',
        'aciklama': 'Üretim kaydı',
        'sistem': False,
        'moduller': {
            'genel_bakis': 'okur',
            'urunler': 'okur',
            'raporlar': 'okur',
            'stok': 'yazar',
            'uretim': 'yazar',
            'hammaddeler': 'okur',
            'receteler': 'yazar',
        },
    },
    {
        'id': 'satis',
        'ad': 'Satış Temsilcisi',
        'ikon': '💼',
        'renk': '#D97706',
        'aciklama': 'Teklif ve sipariş',
        'sistem': False,
        'moduller': {
            'genel_bakis': 'okur',
            'urunler': 'okur',
            'senaryo': 'tam',
            'sepet': 'tam',
            'teklifler': 'tam',
            'siparisler': 'tam',
            'bayiler': 'tam',
            'raporlar': 'okur',
            'finans': 'gormez',
            'stok': 'gormez',
            'hammaddeler': 'gormez',
            'satinalma': 'gormez',
            'satinalma_odeme': 'gormez',
            'hammadde_depo': 'gormez',
            'receteler': 'gormez',
            'kar_maliyet': 'gormez',
            'disa_aktar': 'yazar',
            'kritik_onay': 'gormez',
        },
    },
    {
        'id': 'muhasebe',
        'ad': 'Muhasebe',
        'ikon': '💰',
        'renk': '#7C3AED',
        'aciklama': 'Finansal raporlar',
        'sistem': False,
        'moduller': {
            'genel_bakis': 'okur',
            'urunler': 'okur',
            'siparisler': 'okur',
            'teklifler': 'okur',
            'bayiler': 'okur',
            'raporlar': 'tam',
            'finans': 'tam',
            'stok': 'gormez',
            'hammaddeler': 'okur',
            'satinalma': 'okur',
            'satinalma_odeme': 'yazar',
            'kar_maliyet': 'gormez',
            'disa_aktar': 'tam',
            'kritik_onay': 'yazar',
        },
    },
]


# =========================================================
# DOSYA ISLEMLERI
# =========================================================
def _read():
    """Aynı GET isteğinde kimlik verisini tekrar tekrar depodan okumaz."""
    if not has_request_context() or request.method not in ('GET', 'HEAD'):
        return _read_uncached()
    cache = g.setdefault('_identity_read_cache', {})
    if USERS_FILE not in cache:
        cache[USERS_FILE] = _read_uncached()
    return deepcopy(cache[USERS_FILE])


def _read_uncached():
    """Kullanıcı kayıtlarını ortak ve bütünlük denetimli depodan okur."""
    data = read_json(USERS_FILE, None)
    if data is None:
        from storage_adapter import get_storage_adapter
        adapter = get_storage_adapter()
        exists = (adapter.document_exists(USERS_FILE)
                  if adapter is not None and adapter.managed_json_path(USERS_FILE)
                  else os.path.exists(USERS_FILE))
        if exists:
            raise RuntimeError("Kullanıcı veri dosyasının biçimi geçersiz; kayıtlar korunmak üzere işlem durduruldu.")
        return _varsayilan_olustur()
    if not isinstance(data, dict):
        raise RuntimeError("Kullanıcı veri dosyasının biçimi geçersiz; kayıtlar korunmak üzere işlem durduruldu.")
    # Eski versiyon uyumlulugu
    if 'departmanlar' not in data:
        data['departmanlar'] = []
    if 'kullanicilar' not in data:
        data['kullanicilar'] = []
    if 'log' not in data:
        data['log'] = []
    # Eski departman kayıtlarına yeni modülleri güvenli varsayılanlarla ekle.
    for dep in data['departmanlar']:
        moduller = dep.setdefault('moduller', {})
        varsayilan = {
            'yonetici': {'finans': 'tam', 'stok': 'tam'},
            'depo': {'finans': 'gormez', 'stok': 'tam'},
            'uretim': {'finans': 'gormez', 'stok': 'yazar'},
            'satis': {'finans': 'gormez', 'stok': 'gormez'},
            'muhasebe': {'finans': 'tam', 'stok': 'gormez'},
        }.get(dep.get('id'), {'finans': 'gormez', 'stok': 'gormez'})
        for module in ('finans', 'stok'):
            moduller.setdefault(module, varsayilan[module])
        moduller.setdefault('siparis_sevk',
                            {'yonetici': 'tam', 'depo': 'tam'}.get(dep.get('id'), 'gormez'))
        moduller.setdefault('uretim', {
            'yonetici': 'tam', 'uretim': 'yazar', 'depo': 'okur'
        }.get(dep.get('id'), 'gormez'))
        moduller.setdefault('siparis_depo',
                            {'yonetici': 'tam', 'depo': 'yazar'}.get(dep.get('id'), 'gormez'))
        if dep.get('id') not in ('yonetici', 'finans'):
            moduller['kar_maliyet'] = 'gormez'
        moduller.setdefault('uretim_depo',
                            {'yonetici': 'tam', 'depo': 'yazar'}.get(dep.get('id'), 'gormez'))
        moduller.setdefault('hammaddeler',
                            {'yonetici': 'tam', 'depo': 'okur', 'uretim': 'okur', 'muhasebe': 'okur'}.get(dep.get('id'), 'gormez'))
        moduller.setdefault('satinalma',
                            {'yonetici': 'tam', 'muhasebe': 'okur'}.get(dep.get('id'), 'gormez'))
        moduller.setdefault('satinalma_odeme',
                            {'yonetici': 'tam', 'muhasebe': 'yazar'}.get(dep.get('id'), 'gormez'))
        moduller.setdefault('hammadde_depo',
                            {'yonetici': 'tam', 'depo': 'yazar'}.get(dep.get('id'), 'gormez'))
        moduller.setdefault('receteler',
                            {'yonetici': 'tam', 'uretim': 'yazar'}.get(dep.get('id'), 'gormez'))
        moduller.setdefault('kar_maliyet',
                            {'yonetici': 'tam', 'finans': 'tam'}.get(dep.get('id'), 'gormez'))
        moduller.setdefault('disa_aktar',
                            {'yonetici': 'tam', 'muhasebe': 'tam', 'satis': 'yazar'}.get(dep.get('id'), 'gormez'))
        moduller.setdefault('kritik_onay',
                            {'yonetici': 'tam', 'muhasebe': 'yazar'}.get(dep.get('id'), 'gormez'))
        if dep.get('id') not in ('yonetici', 'muhasebe'):
            moduller['kritik_onay'] = 'gormez'
        if dep.get('id') == 'depo' and moduller.get('siparisler') == 'okur':
            moduller['siparisler'] = 'yazar'
    return data


def _write(data):
    """Kullanıcı kayıtlarını ortak dayanıklı depoya yazar."""
    if has_request_context():
        g.pop('_identity_read_cache', None)
    write_json(USERS_FILE, data)


def _varsayilan_olustur():
    """Ilk kurulum: varsayilan departman + admin kullanici."""
    data = {
        'departmanlar': VARSAYILAN_DEPARTMANLAR,
        'kullanicilar': [
            {
                'id': yeni_id(),
                'kullanici_adi': 'admin',
                'ad_soyad': 'Sistem Yöneticisi',
                'email': '',
                'sifre_hash': hash_sifre('admin123'),
                'departman_id': 'yonetici',
                'aktif': True,
                'olusturma': datetime.now().isoformat(timespec='minutes'),
                'son_giris': None,
                'ilk_giris': True,  # Sifre degistirmek zorunda
                'not': 'Varsayilan admin. Ilk girişte şifre değiştirin.',
            }
        ],
        'log': [
            {
                'zaman': datetime.now().isoformat(timespec='minutes'),
                'kullanici_id': None,
                'kullanici_adi': 'sistem',
                'islem': 'kurulum',
                'detay': 'Varsayilan kullanicilar ve departmanlar olusturuldu',
                'ip': '',
            }
        ],
    }
    _write(data)
    return data
# =========================================================
# KULLANICI FONKSIYONLARI
# =========================================================
def ekip_alt_kullanicilar(amir_id, data=None):
    """Amire doğrudan ve dolaylı bağlı kullanıcı kimliklerini döndürür."""
    data = data or _read()
    users = data.get('kullanicilar', [])
    found, frontier = set(), {amir_id}
    while frontier:
        children = {u.get('id') for u in users if u.get('amir_id') in frontier and u.get('id') not in found}
        found.update(children)
        frontier = children
    return found


def ekip_kullanici_yonetebilir(actor, target_id):
    """Yönetici tüm kullanıcıları; ekip yöneticisi yalnız alt ekibini yönetebilir."""
    if not actor:
        return False
    if actor.get('departman_id') == 'yonetici':
        return True
    if not actor.get('ekip_yoneticisi'):
        return False
    return target_id in ekip_alt_kullanicilar(actor.get('id'))


def ekip_izin_guncelle(actor, target_id, proposed):
    """Ekip yöneticisi izinleri kendi ve departman sınırları içinde günceller."""
    with _lock:
        data = _read()
        actor_row = next((u for u in data.get('kullanicilar', []) if u.get('id') == actor.get('id')), None)
        target = next((u for u in data.get('kullanicilar', []) if u.get('id') == target_id), None)
        if not target or not actor_row or not ekip_kullanici_yonetebilir(actor_row, target_id):
            return {'status': 'error', 'message': 'Bu kullanıcı ekibinizde değil'}
        if target.get('departman_id') == 'yonetici':
            return {'status': 'error', 'message': 'Yönetici izinleri ekip yöneticisi tarafından değiştirilemez'}
        clean = _izinleri_temizle(proposed)
        if actor_row.get('departman_id') != 'yonetici':
            leader_levels = etkin_moduller(actor_row)
            department = departman_getir(target.get('departman_id')) or {}
            base_levels = department.get('moduller') or {}
            for module, level in clean.items():
                rank = YETKI_SEVIYELERI.get(level, 0)
                if rank > YETKI_SEVIYELERI.get(leader_levels.get(module, 'gormez'), 0):
                    return {'status': 'error', 'message': 'Kendi sahip olmadığınız bir yetkiyi veremezsiniz: ' + module}
                if rank > YETKI_SEVIYELERI.get(base_levels.get(module, 'gormez'), 0):
                    return {'status': 'error', 'message': 'Kişi bazlı izin departman sınırını aşamaz: ' + module}
        if target.get('departman_id') not in ('yonetici', 'finans') and clean.get('kar_maliyet') not in (None, 'gormez'):
            return {'status': 'error', 'message': 'Kâr, marj ve maliyet erişimi yalnız yönetici ve finans birimlerinde açılabilir'}
        before = dict(target.get('izinler') or {})
        target['izinler'] = clean
        log_ekle_ic(data, actor_row.get('id'), actor_row.get('ad_soyad') or actor_row.get('kullanici_adi'),
                    'ekip_izin_guncelle', '{} kullanıcısının kalıcı kişi izinleri güncellendi'.format(target.get('kullanici_adi')))
        _write(data)
    return {'status': 'success', 'onceki': before, 'izinler': clean}


def kullanici_listele():
    """Tum kullanicilari (sifresiz) listeler."""
    data = _read()
    sonuc = []
    for k in data.get('kullanicilar', []):
        k2 = dict(k)
        k2.pop('sifre_hash', None)
        # Legacy temporary grants are retained in storage/history but not exposed or applied.
        k2.pop('gecici_izinler', None)
        # Departman adini ekle
        dep = next((d for d in data.get('departmanlar', []) if d['id'] == k.get('departman_id')), None)
        k2.setdefault('amir_id', None)
        k2.setdefault('ekip_yoneticisi', False)
        manager = next((u for u in data.get('kullanicilar', []) if u.get('id') == k2.get('amir_id')), None)
        k2['amir_ad'] = manager.get('ad_soyad') if manager else ''
        k2['departman_ad'] = dep['ad'] if dep else '?'
        k2['departman_ikon'] = dep['ikon'] if dep else '?'
        k2['departman_renk'] = dep['renk'] if dep else '#666666'
        sonuc.append(k2)
    return sonuc


def kullanici_getir(uid):
    """Tek kullanici getirir."""
    data = _read()
    k = next((x for x in data.get('kullanicilar', []) if x['id'] == uid), None)
    if not k:
        return None
    k2 = dict(k)
    k2.pop('sifre_hash', None)
    return k2


def kullanici_ekle(veri, islem_yapan_id=None, islem_yapan_ad='sistem'):
    """Yeni kullanici ekler."""
    kadi = (veri.get('kullanici_adi') or '').strip().lower()
    ad = (veri.get('ad_soyad') or '').strip()
    sifre = veri.get('sifre') or ''
    dep_id = veri.get('departman_id') or ''
    email = (veri.get('email') or '').strip()
    aktif = veri.get('aktif', True)
    
    # Dogrulama
    if not kadi or len(kadi) < 3:
        return {'status': 'error', 'message': 'Kullanici adi en az 3 karakter olmali'}
    if not kadi.replace('_', '').replace('.', '').replace('-', '').isalnum():
        return {'status': 'error', 'message': 'Kullanici adi sadece harf, rakam, _, ., - icerebilir'}
    if not ad:
        return {'status': 'error', 'message': 'Ad soyad zorunlu'}
    if len(sifre) < 6:
        return {'status': 'error', 'message': 'Sifre en az 6 karakter olmali'}
    if not dep_id:
        return {'status': 'error', 'message': 'Departman secilmeli'}
    
    with _lock:
        data = _read()
        
        # Kullanici adi benzersiz mi?
        if any(k['kullanici_adi'] == kadi for k in data['kullanicilar']):
            return {'status': 'error', 'message': 'Bu kullanici adi zaten var'}
        
        # Departman var mi?
        if not any(d['id'] == dep_id for d in data['departmanlar']):
            return {'status': 'error', 'message': 'Departman bulunamadi'}
        amir_id = veri.get('amir_id') or None
        if amir_id and not any(x.get('id') == amir_id and (x.get('ekip_yoneticisi') or x.get('departman_id') == 'yonetici') and x.get('aktif', True) for x in data['kullanicilar']):
            return {'status': 'error', 'message': 'Bağlı yönetici aktif bir ekip yöneticisi olmalı'}
        
        gecerli_modul_yetkileri = set(YETKI_SEVIYELERI)
        yeni = {
            'id': yeni_id(),
            'kullanici_adi': kadi,
            'ad_soyad': ad,
            'email': email,
            'sifre_hash': hash_sifre(sifre),
            'departman_id': dep_id,
            'aktif': bool(aktif),
            'olusturma': datetime.now().isoformat(timespec='minutes'),
            'son_giris': None,
            'ilk_giris': True,
            'not': '',
            'izinler': _izinleri_temizle(veri.get('izinler')),
            'amir_id': veri.get('amir_id') or None,
            'ekip_yoneticisi': bool(veri.get('ekip_yoneticisi', False)),
        }
        data['kullanicilar'].append(yeni)
        log_ekle_ic(data, islem_yapan_id, islem_yapan_ad, 'kullanici_ekle',
                    f'Yeni kullanici: {kadi} ({ad})')
        _write(data)
    
    return {'status': 'success', 'id': yeni['id']}


def kullanici_guncelle(uid, veri, islem_yapan_id=None, islem_yapan_ad='sistem'):
    """Kullaniciyi gunceller."""
    with _lock:
        data = _read()
        k = next((x for x in data['kullanicilar'] if x['id'] == uid), None)
        if not k:
            return {'status': 'error', 'message': 'Kullanici bulunamadi'}
        if 'amir_id' in veri and veri.get('amir_id'):
            amir_id = veri.get('amir_id')
            amir = next((x for x in data['kullanicilar'] if x.get('id') == amir_id), None)
            if not amir or not (amir.get('ekip_yoneticisi') or amir.get('departman_id') == 'yonetici') or amir.get('id') == uid or amir_id in ekip_alt_kullanicilar(uid, data):
                return {'status': 'error', 'message': 'Bağlı yönetici geçersiz veya hiyerarşi döngüsü oluşturuyor'}
        
        # Kullanici adi kontrolu
        if 'kullanici_adi' in veri:
            kadi = (veri['kullanici_adi'] or '').strip().lower()
            if len(kadi) < 3:
                return {'status': 'error', 'message': 'Kullanici adi en az 3 karakter'}
            if any(x['kullanici_adi'] == kadi and x['id'] != uid for x in data['kullanicilar']):
                return {'status': 'error', 'message': 'Bu kullanici adi zaten var'}
            k['kullanici_adi'] = kadi
        
        if 'ad_soyad' in veri:
            ad = (veri['ad_soyad'] or '').strip()
            if not ad:
                return {'status': 'error', 'message': 'Ad soyad bos olamaz'}
            k['ad_soyad'] = ad
        
        if 'email' in veri:
            k['email'] = (veri['email'] or '').strip()
        
        target_department = veri.get('departman_id', k.get('departman_id'))
        target_active = bool(veri.get('aktif', k.get('aktif', True)))
        if k.get('departman_id') == 'yonetici' and (target_department != 'yonetici' or not target_active):
            active_admins = sum(1 for x in data['kullanicilar']
                               if x.get('departman_id') == 'yonetici' and x.get('aktif', True))
            if active_admins <= 1:
                return {'status': 'error', 'message': 'Son aktif yöneticinin yetkisi kapatılamaz veya departmanı değiştirilemez'}

        if 'departman_id' in veri:
            if not any(d['id'] == veri['departman_id'] for d in data['departmanlar']):
                return {'status': 'error', 'message': 'Departman bulunamadi'}
            k['departman_id'] = veri['departman_id']
        
        if 'aktif' in veri:
            k['aktif'] = bool(veri['aktif'])
        
        if 'not' in veri:
            k['not'] = str(veri['not'])[:300]

        if 'izinler' in veri:
            k['izinler'] = _izinleri_temizle(veri.get('izinler'))
        if 'amir_id' in veri:
            k['amir_id'] = veri.get('amir_id') or None
        if 'ekip_yoneticisi' in veri:
            k['ekip_yoneticisi'] = bool(veri.get('ekip_yoneticisi'))
        
        log_ekle_ic(data, islem_yapan_id, islem_yapan_ad, 'kullanici_guncelle',
                    f'Kullanici guncellendi: {k["kullanici_adi"]}')
        _write(data)
    
    return {'status': 'success'}


def kullanici_sil(uid, islem_yapan_id=None, islem_yapan_ad='sistem'):
    """Kullaniciyi siler."""
    with _lock:
        data = _read()
        k = next((x for x in data['kullanicilar'] if x['id'] == uid), None)
        if not k:
            return {'status': 'error', 'message': 'Kullanici bulunamadi'}
        
        # Kendini silmeyi engelle
        if islem_yapan_id == uid:
            return {'status': 'error', 'message': 'Kendinizi silemezsiniz'}
        
        # Son admin'i silmeyi engelle
        admin_dep = 'yonetici'
        yonetici_sayisi = sum(1 for x in data['kullanicilar'] if x['departman_id'] == admin_dep and x['aktif'])
        if k['departman_id'] == admin_dep and yonetici_sayisi <= 1:
            return {'status': 'error', 'message': 'Son yönetici silinemez'}
        
        data['kullanicilar'] = [x for x in data['kullanicilar'] if x['id'] != uid]
        log_ekle_ic(data, islem_yapan_id, islem_yapan_ad, 'kullanici_sil',
                    f'Kullanici silindi: {k["kullanici_adi"]}')
        _write(data)
    
    return {'status': 'success'}


def kullanici_sifre_sifirla(uid, yeni_sifre, islem_yapan_id=None, islem_yapan_ad='sistem'):
    """Admin tarafindan sifre sifirlama."""
    if len(yeni_sifre) < 6:
        return {'status': 'error', 'message': 'Sifre en az 6 karakter olmali'}
    
    with _lock:
        data = _read()
        k = next((x for x in data['kullanicilar'] if x['id'] == uid), None)
        if not k:
            return {'status': 'error', 'message': 'Kullanici bulunamadi'}
        
        k['sifre_hash'] = hash_sifre(yeni_sifre)
        k['ilk_giris'] = True  # Tekrar sifre degistirsin
        log_ekle_ic(data, islem_yapan_id, islem_yapan_ad, 'sifre_sifirla',
                    f'Sifre sifirlandi: {k["kullanici_adi"]}')
        _write(data)
    
    return {'status': 'success'}


def kullanici_sifre_degistir(uid, eski_sifre, yeni_sifre):
    """Kullanici kendi sifresini degistirir."""
    if len(yeni_sifre) < 6:
        return {'status': 'error', 'message': 'Yeni sifre en az 6 karakter olmali'}
    
    with _lock:
        data = _read()
        k = next((x for x in data['kullanicilar'] if x['id'] == uid), None)
        if not k:
            return {'status': 'error', 'message': 'Kullanici bulunamadi'}
        
        if not sifre_dogrula(eski_sifre, k['sifre_hash']):
            return {'status': 'error', 'message': 'Eski sifre yanlis'}
        
        k['sifre_hash'] = hash_sifre(yeni_sifre)
        k['ilk_giris'] = False
        log_ekle_ic(data, uid, k['kullanici_adi'], 'sifre_degistir',
                    'Sifre degistirildi')
        _write(data)
    
    return {'status': 'success'}


# =========================================================
# GIRIS / YETKI
# =========================================================
def giris_kontrol(kullanici_adi, sifre):
    """Kullanici adi + sifre dogrular."""
    kadi = (kullanici_adi or '').strip().lower()
    
    with _lock:
        data = _read()
        k = next((x for x in data['kullanicilar'] if x['kullanici_adi'] == kadi), None)
        
        if not k:
            log_ekle_ic(data, None, kadi or '?', 'giris_basarisiz',
                        'Kullanici bulunamadi', commit=True)
            return {'status': 'error', 'message': 'Kullanici adi veya sifre yanlis'}
        
        if not k.get('aktif', True):
            log_ekle_ic(data, k['id'], k['kullanici_adi'], 'giris_basarisiz',
                        'Hesap pasif', commit=True)
            return {'status': 'error', 'message': 'Hesabiniz pasif durumda'}
        
        if not sifre_dogrula(sifre, k['sifre_hash']):
            log_ekle_ic(data, k['id'], k['kullanici_adi'], 'giris_basarisiz',
                        'Yanlis sifre', commit=True)
            return {'status': 'error', 'message': 'Kullanici adi veya sifre yanlis'}
        
        # Basarili
        k['son_giris'] = datetime.now().isoformat(timespec='minutes')
        log_ekle_ic(data, k['id'], k['kullanici_adi'], 'giris',
                    'Basarili giris', commit=True)
        
        # Departman bilgisi
        dep = next((d for d in data['departmanlar'] if d['id'] == k.get('departman_id')), None)
        
        return {
            'status': 'success',
            'kullanici': {
                'id': k['id'],
                'kullanici_adi': k['kullanici_adi'],
                'ad_soyad': k['ad_soyad'],
                'email': k.get('email', ''),
                'departman_id': k.get('departman_id'),
                'amir_id': k.get('amir_id'),
                'ekip_yoneticisi': bool(k.get('ekip_yoneticisi', False)),
                'departman_ad': dep['ad'] if dep else '?',
                'departman_ikon': dep['ikon'] if dep else '?',
                'departman_renk': dep['renk'] if dep else '#666',
                'moduller': etkin_moduller(k),
                'ilk_giris': k.get('ilk_giris', False),
            }
        }


def etkin_moduller(kullanici):
    """Departman izinleri ve kalıcı kişi istisnalarını birleştirir; eski geçici kayıtlar etkisizdir."""
    if not kullanici:
        return {}
    dep = departman_getir(kullanici.get('departman_id'))
    if not dep:
        return {}
    resolved = {m['id']: (dep.get('moduller') or {}).get(m['id'], 'gormez') for m in MODULLER}
    resolved.update(_izinleri_temizle(kullanici.get('izinler')))
    if kullanici.get('departman_id') == 'yonetici':
        return {m['id']: 'tam' for m in MODULLER}
    if kullanici.get('ekip_yoneticisi'):
        resolved['kullanicilar'] = 'yazar'
    # Company-wide cost/profit data is a fixed separation-of-duties boundary:
    # user-level and temporary grants cannot expose it outside management/finance.
    if kullanici.get('departman_id') not in ('yonetici', 'finans'):
        resolved['kar_maliyet'] = 'gormez'
    # Only management and accounting can decide critical approval requests.
    # Department and person-level grants must not advertise an unusable queue.
    if kullanici.get('departman_id') not in ('yonetici', 'muhasebe'):
        resolved['kritik_onay'] = 'gormez'
    return resolved


def yetki_kontrol(kullanici_id, modul_id, gerekli='okur'):
    """Kullanıcının modül için yeterli ve halen geçerli yetkisi var mı?"""
    required = YETKI_SEVIYELERI.get(gerekli, 1)
    with _lock:
        data = _read()
        user = next((x for x in data['kullanicilar'] if x.get('id') == kullanici_id), None)
        if not user or not user.get('aktif', True):
            return False
        level = etkin_moduller(user).get(modul_id, 'gormez')
        return YETKI_SEVIYELERI.get(level, 0) >= required


def yetki_profilleri():
    return YETKI_PROFILLERI


def yetki_onizleme(dep_id, proposed):
    data = _read()
    dep = next((x for x in data.get('departmanlar', []) if x.get('id') == dep_id), None) if dep_id else None
    if dep_id and not dep:
        return {'status': 'error', 'message': 'Departman bulunamadı'}
    levels = _izinleri_temizle(proposed)
    members = [x for x in data.get('kullanicilar', []) if x.get('departman_id') == dep_id and x.get('aktif', True)]
    # Match the actual effective policy shown in the preview: only management/finance
    # can receive the company-wide cost/profit module.
    if dep_id not in ('yonetici', 'finans'):
        levels['kar_maliyet'] = 'gormez'
    if dep_id not in ('yonetici', 'muhasebe'):
        levels['kritik_onay'] = 'gormez'
    visible = [m['ad'] for m in MODULLER if levels.get(m['id'], 'gormez') != 'gormez']
    warnings = []
    if levels.get('kar_maliyet', 'gormez') != 'gormez' and dep_id not in ('yonetici', 'finans'):
        warnings.append('Bu ayar departmana şirket geneli kâr, marj ve maliyet verilerini açar.')
    if levels.get('disa_aktar', 'gormez') != 'gormez':
        warnings.append('Kullanıcılar izinli kayıtları Excel/CSV olarak dışa aktarabilir.')
    return {'status': 'success', 'departman': dep.get('ad') if dep else 'Yeni departman', 'etkilenen_aktif_kullanici': len(members),
            'kullanici_ornekleri': [x.get('ad_soyad') for x in members[:8]], 'acik_moduller': visible,
            'hassas_veri_acik': levels.get('kar_maliyet', 'gormez') != 'gormez', 'uyarilar': warnings}

def _izinleri_temizle(izinler):
    """Yalnız tanımlı modüllere ait geçerli kullanıcı izinlerini saklar."""
    if not isinstance(izinler, dict):
        return {}
    modul_ids = {m['id'] for m in MODULLER}
    approval_modules = {'siparis_sevk', 'siparis_depo', 'uretim_depo', 'satinalma_odeme', 'hammadde_depo', 'kritik_onay'}
    return {key: value for key, value in izinler.items()
            if key in modul_ids and value in YETKI_SEVIYELERI
            and (value != 'onay' or key in approval_modules)}


# =========================================================
# DEPARTMAN FONKSIYONLARI
# =========================================================
def departman_listele():
    """Tum departmanlari listeler."""
    data = _read()
    return data.get('departmanlar', [])


def departman_getir(dep_id):
    """Tek departman getirir."""
    data = _read()
    return next((d for d in data.get('departmanlar', []) if d['id'] == dep_id), None)


def departman_ekle(veri, islem_yapan_id=None, islem_yapan_ad='sistem'):
    """Yeni departman ekler."""
    ad = (veri.get('ad') or '').strip()
    ikon = veri.get('ikon') or '👤'
    renk = veri.get('renk') or '#6B7280'
    aciklama = (veri.get('aciklama') or '').strip()[:200]
    moduller = veri.get('moduller') or {}
    gecerli_modul_yetkileri = set(YETKI_SEVIYELERI)
    
    if not ad:
        return {'status': 'error', 'message': 'Departman adi zorunlu'}
    if len(ad) < 2:
        return {'status': 'error', 'message': 'Departman adi en az 2 karakter'}
    
    with _lock:
        data = _read()
        
        # Ad benzersiz mi?
        if any(d['ad'].lower() == ad.lower() for d in data['departmanlar']):
            return {'status': 'error', 'message': 'Bu isimde departman zaten var'}
        
        dep_id = ad.lower().replace(' ', '_').replace('ç', 'c').replace('ğ', 'g').replace('ı', 'i').replace('ö', 'o').replace('ş', 's').replace('ü', 'u')
        dep_id = ''.join(c for c in dep_id if c.isalnum() or c == '_')
        
        if not dep_id:
            dep_id = yeni_id()
        
        # ID benzersiz mi?
        while any(d['id'] == dep_id for d in data['departmanlar']):
            dep_id = dep_id + '_' + yeni_id()[:4]
        
        yeni = {
            'id': dep_id,
            'ad': ad,
            'ikon': ikon,
            'renk': renk,
            'aciklama': aciklama,
            'sistem': False,
            'moduller': {
                m['id']: (moduller.get(m['id']) if moduller.get(m['id']) in gecerli_modul_yetkileri else 'gormez')
                for m in MODULLER
            },
        }
        if dep_id not in ('yonetici', 'finans'):
            yeni['moduller']['kar_maliyet'] = 'gormez'
        data['departmanlar'].append(yeni)
        log_ekle_ic(data, islem_yapan_id, islem_yapan_ad, 'departman_ekle',
                    f'Yeni departman: {ad}')
        _write(data)
    
    return {'status': 'success', 'id': dep_id}


def departman_guncelle(dep_id, veri, islem_yapan_id=None, islem_yapan_ad='sistem'):
    """Departman gunceller."""
    with _lock:
        data = _read()
        d = next((x for x in data['departmanlar'] if x['id'] == dep_id), None)
        if not d:
            return {'status': 'error', 'message': 'Departman bulunamadi'}
        
        # Yonetici departmani silinemez/degistirilemez
        if d.get('sistem') and d['id'] == 'yonetici':
            if 'ad' in veri and veri['ad'] != d['ad']:
                return {'status': 'error', 'message': 'Yönetici departmanı düzenlenemez'}
        
        if 'ad' in veri:
            ad = (veri['ad'] or '').strip()
            if len(ad) < 2:
                return {'status': 'error', 'message': 'Departman adi en az 2 karakter'}
            if any(x['ad'].lower() == ad.lower() and x['id'] != dep_id for x in data['departmanlar']):
                return {'status': 'error', 'message': 'Bu isimde departman zaten var'}
            d['ad'] = ad
        
        if 'ikon' in veri:
            d['ikon'] = veri['ikon'] or '👤'
        
        if 'renk' in veri:
            d['renk'] = veri['renk'] or '#6B7280'
        
        if 'aciklama' in veri:
            d['aciklama'] = (veri['aciklama'] or '').strip()[:200]
        
        if 'moduller' in veri and isinstance(veri['moduller'], dict):
            # Yonetici departmani yetkileri degistirilemez
            if d['id'] == 'yonetici':
                return {'status': 'error', 'message': 'Yönetici yetkileri değiştirilemez'}
            d['moduller'] = {
                m['id']: (veri['moduller'].get(m['id']) if veri['moduller'].get(m['id']) in YETKI_SEVIYELERI else 'gormez')
                for m in MODULLER
            }
            if dep_id not in ('yonetici', 'finans'):
                d['moduller']['kar_maliyet'] = 'gormez'
        
        log_ekle_ic(data, islem_yapan_id, islem_yapan_ad, 'departman_guncelle',
                    f'Departman guncellendi: {d["ad"]}')
        _write(data)
    
    return {'status': 'success'}


def departman_sil(dep_id, islem_yapan_id=None, islem_yapan_ad='sistem'):
    """Departmani siler."""
    with _lock:
        data = _read()
        d = next((x for x in data['departmanlar'] if x['id'] == dep_id), None)
        if not d:
            return {'status': 'error', 'message': 'Departman bulunamadi'}
        
        if d.get('sistem'):
            return {'status': 'error', 'message': 'Sistem departmanı silinemez'}
        
        # Bu departmanda kullanici var mi?
        uyeler = [k for k in data['kullanicilar'] if k.get('departman_id') == dep_id]
        if uyeler:
            return {'status': 'error', 'message': f'Bu departmanda {len(uyeler)} kullanıcı var. Önce onları taşıyın.'}
        
        data['departmanlar'] = [x for x in data['departmanlar'] if x['id'] != dep_id]
        log_ekle_ic(data, islem_yapan_id, islem_yapan_ad, 'departman_sil',
                    f'Departman silindi: {d["ad"]}')
        _write(data)
    
    return {'status': 'success'}


# =========================================================
# LOG FONKSIYONLARI
# =========================================================
def log_ekle_ic(data, kullanici_id, kullanici_adi, islem, detay, commit=False):
    """IC kullanim: data dict'ine log ekler."""
    if 'log' not in data:
        data['log'] = []
    data['log'].append({
        'zaman': datetime.now().isoformat(timespec='seconds'),
        'kullanici_id': kullanici_id,
        'kullanici_adi': kullanici_adi or '?',
        'islem': islem,
        'detay': str(detay)[:300],
        'ip': '',
    })
    # Temizlik: 30 gunden eski loglari sil
    kesme = (datetime.now() - timedelta(days=30)).isoformat(timespec='seconds')
    data['log'] = [l for l in data['log'] if l.get('zaman', '') >= kesme]
    if commit:
        _write(data)


def log_ekle(kullanici_id, kullanici_adi, islem, detay, ip=''):
    """Public: log ekle."""
    with _lock:
        data = _read()
        log_ekle_ic(data, kullanici_id, kullanici_adi, islem, detay, commit=True)


def log_listele(limit=200):
    """Son N log kaydini doner (en yeni once)."""
    data = _read()
    loglar = data.get('log', [])
    return list(reversed(loglar[-limit:]))


def log_temizle():
    """Tum log kayitlarini siler."""
    with _lock:
        data = _read()
        data['log'] = []
        _write(data)
    return {'status': 'success'}


# =========================================================
# YARDIMCI
# =========================================================
def modul_listesi():
    """Tum modulleri doner."""
    return MODULLER


def departman_istatistik():
    """Departman bazli kullanici sayilari."""
    data = _read()
    stats = {}
    for d in data.get('departmanlar', []):
        dep_id = d['id']
        aktif = sum(1 for k in data['kullanicilar'] if k.get('departman_id') == dep_id and k.get('aktif'))
        toplam = sum(1 for k in data['kullanicilar'] if k.get('departman_id') == dep_id)
        stats[dep_id] = {'aktif': aktif, 'toplam': toplam}
    return stats


# =========================================================
# TEST
# =========================================================
if __name__ == '__main__':
    print('=' * 60)
    print('LUMISPAC - Kimlik Modulu Test')
    print('=' * 60)
    
    # Dosya var mi?
    if not os.path.exists(USERS_FILE):
        print('Kullanicilar dosyasi olusturuluyor...')
        _varsayilan_olustur()
    
    print()
    print('Departmanlar:')
    for d in departman_listele():
        print(f'  {d["ikon"]} {d["ad"]:25s} ({d["id"]})')
    
    print()
    print('Kullanicilar:')
    for k in kullanici_listele():
        print(f'  {k["kullanici_adi"]:15s} | {k["ad_soyad"]:25s} | {k["departman_ad"]}')
    
    print()
    print('Test giris (admin/admin123):')
    r = giris_kontrol('admin', 'admin123')
    print(f'  Status: {r["status"]}')
    if r['status'] == 'success':
        print(f'  Kullanici: {r["kullanici"]["ad_soyad"]}')
        print(f'  Departman: {r["kullanici"]["departman_ad"]}')
        print(f'  Ilk giris: {r["kullanici"]["ilk_giris"]}')
    
    print()
    print('Basarili!')

