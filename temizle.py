# temizle.py - LUMISPAC klasör temizliği
# Kullanım:
#   python temizle.py                       -> sadece listeler (silmez)
#   python temizle.py --uygula              -> varsayılan temizliği yapar
#   python temizle.py --eski-yedekler       -> yedekler, _arsiv, test_yedekleri de listeye eklenir
#   python temizle.py --yedek-tut 5         -> yedekler_v2 içinde en yeni 5'i tutar, kalanı listeler
#   (herhangi bir kombinasyonu --uygula ile birlikte çalıştırabilirsin)

import argparse
import os
import shutil
import stat
from pathlib import Path

KOK = Path(__file__).resolve().parent
KORUNAN_KOKLER = {"yedekler_v2", "yedekler", "_arsiv", "test_yedekleri"}


def boyut(yol: Path) -> int:
    if yol.is_file():
        return yol.stat().st_size
    toplam = 0
    for dizin, _, dosyalar in os.walk(yol):
        for ad in dosyalar:
            try:
                toplam += (Path(dizin) / ad).stat().st_size
            except OSError:
                pass
    return toplam


def mb(bayt: int) -> str:
    return f"{bayt / 1024 / 1024:.1f} MB"


def hata_isleyici(islev, yol, _):
    # Salt okunur dosyalarda (OneDrive/Windows) izin verip tekrar dene
    os.chmod(yol, stat.S_IWRITE)
    islev(yol)


def sil(yol: Path):
    if yol.is_dir():
        shutil.rmtree(yol, onerror=hata_isleyici)
    else:
        os.chmod(yol, stat.S_IWRITE)
        yol.unlink()


def pycache_bul():
    sonuc = []
    for dizin, alt, _ in os.walk(KOK):
        # Yedek klasörlerinin içine girme
        if Path(dizin) == KOK:
            alt[:] = [a for a in alt if a not in KORUNAN_KOKER_ADLARI]
        if "__pycache__" in alt:
            sonuc.append(Path(dizin) / "__pycache__")
            alt.remove("__pycache__")
    return sonuc


KORUNAN_KOKER_ADLARI = KORUNAN_KOKLER


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uygula", action="store_true", help="Gerçekten sil (yoksa sadece listeler)")
    ap.add_argument("--eski-yedekler", action="store_true", help="yedekler, _arsiv, test_yedekleri de silinsin")
    ap.add_argument("--yedek-tut", type=int, default=None, metavar="N",
                    help="yedekler_v2 içinde en yeni N klasörü tut, kalanı sil")
    args = ap.parse_args()

    if not (KOK / "lumispac_app.py").exists():
        raise SystemExit("Bu betik LUMISPAC klasörüne konmalı (lumispac_app.py bulunamadı). İptal.")

    hedefler = []

    # 1) pytest geçici klasörleri
    for desen in (".pytest_tmp_*", ".pytest_cache"):
        hedefler += [p for p in KOK.glob(desen) if p.is_dir()]

    # 2) __pycache__
    hedefler += pycache_bul()

    # 3) kök dizindeki .bak dosyaları
    hedefler += [p for p in KOK.glob("*.bak") if p.is_file()]

    # 4) isteğe bağlı: eski yedek klasörleri
    if args.eski_yedekler:
        for ad in ("yedekler", "_arsiv", "test_yedekleri"):
            p = KOK / ad
            if p.is_dir():
                hedefler.append(p)

    # 5) isteğe bağlı: yedekler_v2'de sadece en yeni N'i tut
    if args.yedek_tut is not None:
        v2 = KOK / "yedekler_v2"
        if v2.is_dir():
            klasorler = sorted((p for p in v2.iterdir() if p.is_dir()),
                               key=lambda p: p.stat().st_mtime, reverse=True)
            hedefler += klasorler[max(args.yedek_tut, 0):]

    if not hedefler:
        print("Silinecek bir şey bulunamadı.")
        return

    toplam = 0
    print(("SİLİNİYOR" if args.uygula else "LİSTE (silinmedi)") + f" - {len(hedefler)} öğe\n")
    for p in hedefler:
        b = boyut(p)
        toplam += b
        print(f"  {mb(b):>10}  {p.relative_to(KOK)}")
    print(f"\nToplam: {mb(toplam)}")

    if not args.uygula:
        print("\nBir şey silinmedi. Onaylıyorsan aynı komutu --uygula ile tekrar çalıştır.")
        return

    basarisiz = 0
    for p in hedefler:
        try:
            sil(p)
        except Exception as e:
            basarisiz += 1
            print(f"  ! Silinemedi: {p.relative_to(KOK)} ({e})")
    print(f"\nBitti. Silinemeyen: {basarisiz}")


if __name__ == "__main__":
    main()
