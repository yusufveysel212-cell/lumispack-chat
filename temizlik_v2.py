 
# -*- coding: utf-8 -*-
"""
LUMISPAC v3 - TEMIZLIK ARACI (v2)
----------------------------------
Kalici temizlik araci. Her cagrida guncel tarihle arsiv olusturur.

Silinenler:
  - Cop dosyalar (yanlis komut artiklari)
  - Python cache (__pycache__)
  - Pytest cache (.pytest_cache)
  - Log dosyalari (*.log)

Arsive tasinanlar:
  - Tek seferlik script'ler (analiz_*.py, *_tasi.py, fix_*.py vb.)
  - Gecici metin dosyalari (auth_blok.txt, fonksiyonlar.txt)
  - Dagink yedekler (*.bak_*, *.faz*_seed_*)

Korunanlar:
  - Tum .py modulleri
  - Tum .md dokumanlari
  - Tum .json veri dosyalari
  - api/, services/, reports/, tests/, static/, app/
  - yedekler_v2/, _arsiv/

Kullanim:
    python temizlik_v2.py test    -> sadece gosterir, hicbir sey yapmaz
    python temizlik_v2.py sil     -> gercekten temizler
"""
import os
import sys
import shutil
import fnmatch
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
BUGUN = datetime.now().strftime('%Y%m%d_%H%M%S')

# ============================================================
# SILINECEK COP DOSYALAR (pattern ile eslesme)
# ============================================================
SIL_DOSYA_PATTERN = [
    '({}))',
    '0)}',
    'm',
    'n',
    '{v',
    '*.log',
]

# ============================================================
# SILINECEK COP KLASORLER
# ============================================================
SIL_KLASOR = [
    '__pycache__',
    '.pytest_cache',
]

# ============================================================
# ARSIVE TASINACAKLAR (pattern ile)
# ============================================================
ARSIV_PATTERN = [
    'analiz_*.py',
    '*_tasi.py',
    'tasi_*.py',
    'fix_*.py',
    'ekle_*.py',
    'duzelt_*.py',
    'guncelle_*.py',
    'temizle_*.py',
    'kontrol_*.py',
    'geri_yukle_*.py',
    'temizlik.py',
    'temizlik_guvenli.py',
    'auth_blok.txt',
    'fonksiyonlar.txt',
    'app_output.txt',
    'python',
]

# ============================================================
# YEDEKLER_V2'YE TASINACAKLAR (dagink yedekler)
# ============================================================
YEDEK_PATTERN = [
    '*.bak_*',
    '*.faz*_seed_*',
    '*.faz3_seed_*',
]

# ============================================================
# KORUNANLAR (asla dokunma)
# ============================================================
KORU_DOSYA = {
    'lumispac_app.py',
    'helpers.py',
    'state.py',
    'config.py',
    'utils.py',
    'auth_module.py',
    'pdf_module.py',
    'rate_sources.py',
    'users_ui.py',
    'help_content.py',
    'reports_api.py',
    'yedek_v2.py',
    'temizlik_v2.py',
    'import_tarayici.py',
    'lumispac_baslat.bat',
    'pytest.ini',
    'requirements.txt',
}

KORU_KLASOR = {
    'api',
    'services',
    'reports',
    'tests',
    'static',
    'app',
    'yedekler',
    'yedekler_v2',
    '_arsiv',
}

KORU_UZANTI = {'.py', '.json', '.md', '.ini', '.bat', '.txt', '.css', '.html'}


def boyut(yol):
    """KB cinsinden boyut."""
    if os.path.isfile(yol):
        try:
            return os.path.getsize(yol) / 1024
        except OSError:
            return 0
    toplam = 0
    for root, dirs, files in os.walk(yol):
        for f in files:
            try:
                toplam += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return toplam / 1024


def pattern_esles(ad, pattern_liste):
    """Dosya adi pattern'lerden birine uyuyor mu?"""
    for p in pattern_liste:
        if fnmatch.fnmatch(ad, p):
            return True
    return False


def main():
    mod = sys.argv[1] if len(sys.argv) > 1 else 'test'
    test_modu = (mod != 'sil')

    arsiv_klasor = '_arsiv/temizlik_' + BUGUN

    print('=' * 70)
    print('  LUMISPAC v3 - TEMIZLIK ARACI (v2)')
    print('  Mod     : ' + ('TEST (hicbir sey yapilmaz)' if test_modu else 'SIL (gercek islem)'))
    print('  Tarih   : ' + BUGUN)
    print('  Arsiv   : ' + arsiv_klasor)
    print('=' * 70)
    print()

    silinen_dosya = 0
    silinen_boyut = 0
    tasinan = 0

    # ----------------------------------------------------------
    # 1) SILINECEK COP DOSYALAR
    # ----------------------------------------------------------
    print('--- SILINECEK COP DOSYALAR ---')
    bulundu = False
    for ad in sorted(os.listdir(BASE)):
        yol = os.path.join(BASE, ad)
        if not os.path.isfile(yol):
            continue
        if ad in KORU_DOSYA:
            continue
        if not pattern_esles(ad, SIL_DOSYA_PATTERN):
            continue
        b = boyut(yol)
        print('  [SIL] ' + ad.ljust(50) + ' ' + str(round(b, 2)) + ' KB')
        bulundu = True
        if not test_modu:
            try:
                os.remove(yol)
                silinen_dosya += 1
                silinen_boyut += b
            except OSError as e:
                print('    [HATA] ' + str(e))
    if not bulundu:
        print('  (temiz)')

    # ----------------------------------------------------------
    # 2) SILINECEK COP KLASORLER
    # ----------------------------------------------------------
    print()
    print('--- SILINECEK COP KLASORLER ---')
    bulundu = False
    for ad in SIL_KLASOR:
        yol = os.path.join(BASE, ad)
        if not os.path.isdir(yol):
            continue
        b = boyut(yol)
        print('  [SIL] ' + ad.ljust(50) + ' ' + str(round(b, 2)) + ' KB')
        bulundu = True
        if not test_modu:
            try:
                shutil.rmtree(yol)
                silinen_dosya += 1
                silinen_boyut += b
            except OSError as e:
                print('    [HATA] ' + str(e))
    if not bulundu:
        print('  (temiz)')

    # ----------------------------------------------------------
    # 3) ARSIVE TASINACAKLAR
    # ----------------------------------------------------------
    print()
    print('--- ARSIVE TASINACAKLAR (' + arsiv_klasor + ') ---')
    arsiv_dir = os.path.join(BASE, arsiv_klasor)
    if not test_modu:
        os.makedirs(arsiv_dir, exist_ok=True)

    bulundu = False
    for ad in sorted(os.listdir(BASE)):
        yol = os.path.join(BASE, ad)
        if not os.path.isfile(yol):
            continue
        if ad in KORU_DOSYA:
            continue
        if not pattern_esles(ad, ARSIV_PATTERN):
            continue
        print('  [TASI] ' + ad)
        bulundu = True
        if not test_modu:
            try:
                shutil.move(yol, os.path.join(arsiv_dir, ad))
                tasinan += 1
            except OSError as e:
                print('    [HATA] ' + str(e))
    if not bulundu:
        print('  (temiz)')

    # ----------------------------------------------------------
    # 4) YEDEKLER_V2'YE TASINACAKLAR
    # ----------------------------------------------------------
    print()
    print('--- YEDEKLER_V2 YE TASINACAKLAR ---')
    yedek_dir = os.path.join(BASE, 'yedekler_v2')

    bulundu = False
    for ad in sorted(os.listdir(BASE)):
        yol = os.path.join(BASE, ad)
        if not os.path.isfile(yol):
            continue
        if ad in KORU_DOSYA:
            continue
        if not pattern_esles(ad, YEDEK_PATTERN):
            continue
        print('  [TASI] ' + ad + '  ->  yedekler_v2/')
        bulundu = True
        if not test_modu:
            try:
                hedef = os.path.join(yedek_dir, ad)
                # Cakismayi onle: ayni adli varsa sonuna _2 ekle
                if os.path.exists(hedef):
                    hedef = hedef + '_' + BUGUN
                shutil.move(yol, hedef)
                tasinan += 1
            except OSError as e:
                print('    [HATA] ' + str(e))
    if not bulundu:
        print('  (temiz)')

    # ----------------------------------------------------------
    # 5) GUVENLIK KONTROLU
    # ----------------------------------------------------------
    print()
    print('--- GUVENLIK KONTROLU ---')
    eksik = []
    for ad in KORU_DOSYA:
        if not os.path.exists(os.path.join(BASE, ad)):
            eksik.append(ad)
    for ad in KORU_KLASOR:
        if not os.path.exists(os.path.join(BASE, ad)):
            eksik.append(ad + '/')

    if eksik:
        print('  [UYARI] Su dosyalar bulunamadi:')
        for ad in eksik:
            print('    - ' + ad)
    else:
        print('  [OK] Tum korunan dosya/klasorler yerinde.')

    # ----------------------------------------------------------
    # 6) OZET
    # ----------------------------------------------------------
    print()
    print('=' * 70)
    if test_modu:
        print('  TEST MODU - HICBIR SEY YAPILMADI')
        print('  Gercekten yapmak icin: python temizlik_v2.py sil')
    else:
        print('  TEMIZLIK TAMAMLANDI')
        print('  Silinen dosya/klasor : ' + str(silinen_dosya))
        print('  Arsive tasinan       : ' + str(tasinan))
        print('  Kazanilan alan       : ' + str(round(silinen_boyut, 2)) + ' KB')
    print('=' * 70)


if __name__ == '__main__':
    main()