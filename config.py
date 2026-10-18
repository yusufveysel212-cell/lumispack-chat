# -*- coding: utf-8 -*-
"""
LUMISPAC - Merkezi Sabitler ve Yapilandirma
Tum dosya yollari, sabitler ve varsayilan degerler burada.

Kullanim:
    from config import BASE, DATA_FILE, SET_FILE, DEFAULT_SETTINGS
"""
import os

# =========================================================
# KLASOR VE DOSYA YOLLARI
# =========================================================
BASE = os.path.dirname(os.path.abspath(__file__))

# Yerel tek bilgisayar kurulumunda kalıcı kullanıcı verileri OneDrive'daki
# proje kodundan ayrı tutulur. SQLite Python ile birlikte gelir.
STORAGE_BACKEND = os.environ.get('LUMISPAC_STORAGE', 'json').strip().lower()
SQL_BACKENDS = frozenset({'sqlite', 'postgres', 'postgresql'})
DATABASE_URL = os.environ.get('LUMISPAC_DATABASE_URL', '').strip()
LOCAL_DATA_HOME = os.environ.get('LUMISPAC_DATA_HOME') or os.path.join(
    os.environ.get('LOCALAPPDATA', os.path.join(os.path.expanduser('~'), 'AppData', 'Local')),
    'LUMISPAC',
)
DB_FILE = os.path.join(LOCAL_DATA_HOME, 'data', 'lumispac.sqlite3')

# Veri dosyalari
DATA_FILE    = os.path.join(BASE, 'lumispac_data.json')
SET_FILE     = os.path.join(BASE, 'lumispac_settings.json')
QUOTE_FILE   = os.path.join(BASE, 'lumispac_quotes.json')
DEALER_FILE  = os.path.join(BASE, 'lumispac_dealers.json')
ORDER_FILE   = os.path.join(BASE, 'lumispac_orders.json')
USERS_FILE   = os.path.join(BASE, 'lumispac_users.json')
FINANS_FILE  = os.path.join(BASE, 'lumispac_finans.json')
STOK_FILE    = os.path.join(BASE, 'lumispac_stok.json')
PRODUCTION_FILE = os.path.join(BASE, 'lumispac_uretim.json')
RAW_MATERIAL_FILE = os.path.join(BASE, 'lumispac_raw_materials.json')
RAW_DOCUMENT_DIR = (os.path.join(LOCAL_DATA_HOME, 'data', 'documents')
                    if STORAGE_BACKEND in SQL_BACKENDS
                    else os.path.join(BASE, 'hammadde_belgeleri'))
LOG_FILE     = (os.path.join(LOCAL_DATA_HOME, 'logs', 'lumispac_hata.log')
                if STORAGE_BACKEND in SQL_BACKENDS
                else os.path.join(BASE, 'lumispac_hata.log'))

# Klasorler
BACKUP_DIR   = (os.path.join(LOCAL_DATA_HOME, 'backups')
                if STORAGE_BACKEND in SQL_BACKENDS
                else os.path.join(BASE, 'yedekler'))
STATIC_DIR   = os.path.join(BASE, 'static')
CSS_DIR      = os.path.join(STATIC_DIR, 'css')
JS_DIR       = os.path.join(STATIC_DIR, 'js')

# =========================================================
# UYGULAMA AYARLARI
# =========================================================
POLL_SECONDS = 15          # Dış kur kaynağı yenileme aralığı (saniye)
HTTP_TIMEOUT = 4           # HTTP istek zaman asimi
# A missing carton volume is unknown. Never substitute a guessed value in
# shipping/truck calculations; the product editor asks for an explicit value.
DEFAULT_VOLUME = 0.0

# =========================================================
# IS SABITLERI
# =========================================================
STATUSES = ['Taslak', 'Onaylandı', 'Hazırlanıyor', 'Sevk edildi', 'Teslim edildi', 'İptal']

VAT_DEFAULT = 20.0
TRUCK_M3_DEFAULT = 90.0
TARGET_MARGIN_DEFAULT = 30.0

# =========================================================
# VARSAYILAN AYARLAR
# =========================================================
DEFAULT_SETTINGS = {
    'raw_usd': 1.23,
    'vat': VAT_DEFAULT,
    'truck_m3': TRUCK_M3_DEFAULT,
    'rate': 0.0,
    'target_margin': TARGET_MARGIN_DEFAULT,
    'company': 'LUMİSPAC AMBALAJ SANAYİ',
    'iban': '',
    'note': 'Ödeme %50 peşin, bakiye sevkiyat günü alınır.',
    'vkn': '',
    'tax_office': '',
    'address': '',
}

# =========================================================
# HTTP HEADERS
# =========================================================
USER_AGENT = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  'Chrome/128 Safari/537.36',
    'Accept-Language': 'tr-TR,tr;q=0.9',
}

# =========================================================
# SEED URUNLERI (pet.xlsx'ten)
# =========================================================
SEED_PRODUCTS = [
    ('LUM-150-5', '150CC SIZDIRMAZ', 5, 1000, 660),
    ('LUM-249-6', '249 CC SIZDIRMAZ', 6, 1000, 714),
    ('LUM-250-7', '250 CC SIZDIRMAZ', 7, 1000, 840),
    ('LUM-375-8', '375 CC SIZDIRMAZ', 8, 1000, 942),
    ('LUM-500-10', '500 CC SIZDIRMAZ', 10, 1000, 1182),
    ('LUM-500D-12.5', '500 CC DİKDÖRTGEN SIZDIRMAZ', 12.5, 600, None),
    ('LUM-750-14', '750 CC SIZDIRMAZ', 14, 600, 996),
    ('LUM-750-16', '750 CC SIZDIRMAZ', 16, 600, 1164),
    ('LUM-1000-16', '1000CC SIZDIRMAZ', 16, 600, 1140),
    ('LUM-1000-20', '1000CC SIZDIRMAZ', 20, 600, None),
    ('LUM-1250-23', '1250 CC SIZDIRMAZ', 23, 400, 1116),
    ('LUM-1500-25', '1500CC SIZDIRMAZ', 25, 400, 1224),
    ('LUM-1750-28', '1750 CC SIZDIRMAZ', 28, 400, 1320),
    ('LUM-2000-30', '2000CC SIZDIRMAZ', 30, 600, 1440),
    ('LUM-750B-14', '750 CC BOMBELİ SIZDIRMAZ', 14, 600, 996),
    ('LUM-1000B-16', '1000 CC BOMBELİ SIZDIRMAZ', 16, 600, 1140),
    ('LUM-1000B-20', '1000 CC BOMBELİ SIZDIRMAZ', 20, 600, None),
    ('LUM-1250B-23', '1250 CC BOMBELİ SIZDIRMAZ', 23, 400, None),
    ('LUM-1500B-25', '1500 CC BOMBELİ SIZDIRMAZ', 25, 400, 1116),
    ('LUM-1750B-28', '1750 CC BOMBELİ SIZDIRMAZ', 28, 400, 1224),
    ('LUM-2000B-30', '2000 CC BOMBELİ SIZDIRMAZ', 30, 400, 1320),
    ('LUM-500P-12', '500 CC SIZDIRMAZ PEYNİR', 12, 800, 1170),
    ('LUM-500P-16', '500 CC SIZDIRMAZ PEYNİR', 16, 800, 1560),
]

# Provisional outer-carton m³ values for newly seeded test/demo products only.
# They are estimates from manufacturer-published carton dimensions, not measured
# LUMISPAC cartons. Existing product records are deliberately never overwritten.
# Sources: PETSA product sheet https://docs.tuyap.online/FDOCS/Firma2/7964.pdf
# and Perapet catalog https://perapet.com/tr/anasayfa/ .
SEED_PRODUCT_VOLUME_ESTIMATES = {
    # PETSA PSK 150/250/375: 600 x 520 x 470 mm, 1,000 pcs/carton.
    'LUM-150-5': 0.14664,
    'LUM-249-6': 0.14664,  # 250 cc benchmark
    'LUM-250-7': 0.14664,
    'LUM-375-8': 0.14664,
    # PETSA PSK 500: 600 x 500 x 550 mm, 1,000 pcs/carton.
    'LUM-500-10': 0.165,
    # FolyoTerm FT 208 KD 500: 530 x 480 x 590 mm, 600 pcs/carton.
    'LUM-500D-12.5': 0.150204,
    # PETSA PSK 750/1000: 600 x 540 x 505 mm, 600 pcs/carton.
    'LUM-750-14': 0.16362,
    'LUM-750-16': 0.16362,
    'LUM-1000-16': 0.16362,
    'LUM-1000-20': 0.16362,
    # Perapet 750/1000 dome: 590 x 570 x 510 mm, 600 pcs/carton.
    'LUM-750B-14': 0.171513,
    'LUM-1000B-16': 0.171513,
    'LUM-1000B-20': 0.171513,
    # Perapet 1250/1500/1750 g range: 710 x 590 x 470 mm, 400 pcs/carton.
    'LUM-1250-23': 0.196873,
    'LUM-1500-25': 0.196873,
    'LUM-1750-28': 0.196873,
    # PETSA PPY 500 cheese: 500 x 470 x 620 mm, 800 pcs/carton.
    'LUM-500P-12': 0.1457,
    'LUM-500P-16': 0.1457,
}
