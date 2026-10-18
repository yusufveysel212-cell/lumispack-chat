# -*- coding: utf-8 -*-
"""
LUMISPAC - Gelismis Yedekleme Sistemi v3
v3: Alt klasorleri de yedekler (static/, app/, api/, services/, reports/, tests/)

Kullanim:
    python yedek_v2.py al "asama2 baslangic"
    python yedek_v2.py liste
    python yedek_v2.py geri asama2_baslangic_20261013_034500
"""
import os
import sys
import shutil
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
YEDEK_ANA = os.path.join(BASE, 'yedekler_v2')

# Yedeklenecek uzantilar
UZANTILAR = ('.py', '.json', '.bat', '.html', '.css', '.js', '.txt', '.md')

# Atlanacak klasorler (yedeklenmez)
ATLA_DIR = {
    'yedekler_v2', 'yedekler_asamali', 'yedekler_otomatik', 'yedekler',
    '_tam_yedek', '_tam_yedek_v2', '__pycache__', '.git',
    '.pytest_cache', '_arsiv', 'node_modules', '.vscode', '.idea',
}

# Atlanacak dosya pattern'leri (bunlari yedekleme)
ATLA_DOSYA = {
    '_ACIKLAMA.txt',
}


def _temiz_ad(metin):
    """Dosya adi icin guvenli hale getir."""
    return ''.join(c if c.isalnum() or c in '_-' else '_' for c in metin)


def _klasor_atla_mi(klasor_adi):
    """Bu klasor yedeklenmeli mi?"""
    if klasor_adi in ATLA_DIR:
        return True
    if klasor_adi.startswith('.'):
        return True
    if klasor_adi.endswith('_bak') or '_bak_' in klasor_adi:
        return True
    return False


def _dosya_al_mi(dosya_adi):
    """Bu dosya yedeklenmeli mi?"""
    if dosya_adi in ATLA_DOSYA:
        return False
    if not dosya_adi.endswith(UZANTILAR):
        return False
    # .bak_ dosyalari da yedeklensin (geri donus icin degerli)
    return True


def yedek_al(aciklama=''):
    os.makedirs(YEDEK_ANA, exist_ok=True)
    damga = datetime.now().strftime('%Y%m%d_%H%M%S')
    ad = _temiz_ad(aciklama)[:40] if aciklama else 'yedek'
    hedef = os.path.join(YEDEK_ANA, ad + '_' + damga)
    os.makedirs(hedef, exist_ok=True)

    sayi = 0
    boyut = 0
    atlanan_klasor = 0

    # os.walk ile alt klasorleri de tara
    for kok, klasorler, dosyalar in os.walk(BASE):
        # Alt klasorleri filtrele (yerinde degistir)
        klasorler[:] = [k for k in klasorler if not _klasor_atla_mi(k)]

        # BASE'in kendisindeki yedekler_v2'yi de atla
        if kok == BASE:
            klasorler[:] = [k for k in klasorler if k != 'yedekler_v2']

        for dosya in dosyalar:
            if not _dosya_al_mi(dosya):
                continue

            kaynak = os.path.join(kok, dosya)
            # Hedef yol: alt klasor yapisini koru
            rel = os.path.relpath(kaynak, BASE)
            hedef_yol = os.path.join(hedef, rel)

            # Alt klasor olustur
            os.makedirs(os.path.dirname(hedef_yol), exist_ok=True)

            try:
                shutil.copy2(kaynak, hedef_yol)
                sayi += 1
                boyut += os.path.getsize(kaynak)
            except Exception as e:
                print('[HATA] ' + rel + ': ' + str(e))

    # Aciklama dosyasi
    with open(os.path.join(hedef, '_ACIKLAMA.txt'), 'w', encoding='utf-8') as f:
        f.write('Yedek: ' + ad + '\n')
        f.write('Tarih: ' + datetime.now().strftime('%d.%m.%Y %H:%M:%S') + '\n')
        f.write('Aciklama: ' + (aciklama or '(yok)') + '\n')
        f.write('Dosya sayisi: ' + str(sayi) + '\n')
        f.write('Surum: v3 (alt klasorler dahil)\n')

    print('=' * 60)
    print('  [OK] YEDEK ALINDI (v3)')
    print('=' * 60)
    print('  Ad       : ' + ad + '_' + damga)
    print('  Dosya    : ' + str(sayi))
    print('  Boyut    : ' + str(round(boyut / 1024, 1)) + ' KB')
    print('  Konum    : ' + hedef)
    print('=' * 60)
    return ad + '_' + damga


def liste():
    if not os.path.isdir(YEDEK_ANA):
        print('Henuz yedek yok.')
        return
    klasorler = sorted(os.listdir(YEDEK_ANA), reverse=True)
    if not klasorler:
        print('Henuz yedek yok.')
        return
    print('=' * 60)
    print('  MEVCUT YEDEKLER (' + str(len(klasorler)) + ' adet)')
    print('=' * 60)
    for k in klasorler:
        yol = os.path.join(YEDEK_ANA, k)
        if not os.path.isdir(yol):
            continue
        aciklama_yolu = os.path.join(yol, '_ACIKLAMA.txt')
        aciklama = ''
        surum = ''
        if os.path.exists(aciklama_yolu):
            try:
                with open(aciklama_yolu, 'r', encoding='utf-8') as f:
                    for satir in f:
                        if satir.startswith('Aciklama: '):
                            aciklama = satir.replace('Aciklama: ', '').strip()
                        elif satir.startswith('Surum: '):
                            surum = satir.replace('Surum: ', '').strip()
            except Exception:
                pass
        # Toplam boyut (alt klasorler dahil)
        boyut = 0
        dosya_sayi = 0
        for kok, _, dosyalar in os.walk(yol):
            for f in dosyalar:
                boyut += os.path.getsize(os.path.join(kok, f))
                dosya_sayi += 1
        print('  ' + k)
        print('    -> ' + (aciklama or '(aciklama yok)') + '  |  ' + str(dosya_sayi) + ' dosya, ' + str(round(boyut / 1024, 1)) + ' KB' + ('  [' + surum + ']' if surum else ''))
    print('=' * 60)


def geri(ad):
    kaynak = os.path.join(YEDEK_ANA, ad)
    if not os.path.isdir(kaynak):
        print('[HATA] Yedek bulunamadi: ' + ad)
        print('Once "python yedek_v2.py liste" ile yedekleri gorun.')
        return

    # Mevcut durumu once guvene al
    print('Once mevcut durum guvene aliniyor...')
    yedek_al('geri_almadan_once')

    print()
    print('Yedek geri yukleniyor: ' + ad)
    sayi = 0

    # os.walk ile alt klasorleri de geri yukle
    for kok, klasorler, dosyalar in os.walk(kaynak):
        klasorler[:] = [k for k in klasorler if not _klasor_atla_mi(k)]
        for dosya in dosyalar:
            if dosya == '_ACIKLAMA.txt':
                continue
            kaynak_yol = os.path.join(kok, dosya)
            rel = os.path.relpath(kaynak_yol, kaynak)
            hedef_yol = os.path.join(BASE, rel)

            # Hedef klasor yoksa olustur
            os.makedirs(os.path.dirname(hedef_yol), exist_ok=True)

            try:
                shutil.copy2(kaynak_yol, hedef_yol)
                sayi += 1
                print('  [OK] ' + rel)
            except Exception as e:
                print('  [HATA] ' + rel + ': ' + str(e))

    print()
    print('=' * 60)
    print('  [OK] ' + str(sayi) + ' dosya geri yuklendi.')
    print('=' * 60)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    komut = sys.argv[1].lower()

    if komut == 'al':
        aciklama = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else ''
        yedek_al(aciklama)
    elif komut == 'liste':
        liste()
    elif komut == 'geri':
        if len(sys.argv) < 3:
            print('[HATA] Yedek adi gerekli.')
            print('Kullanim: python yedek_v2.py geri YEDEK_ADI')
            return
        geri(sys.argv[2])
    else:
        print('Bilinmeyen komut: ' + komut)
        print(__doc__)


if __name__ == '__main__':
    main()