# -*- coding: utf-8 -*-
"""hesap_service.tum_urunler_stok cikti yapisi."""
import sys
sys.path.insert(0, ".")

from services import hesap_service

sonuc = hesap_service.tum_urunler_stok()
print("Toplam urun: %d" % len(sonuc))
print()

if sonuc:
    ilk = sonuc[0]
    print("Ilk urun anahtarlari:")
    for k in sorted(ilk.keys()):
        v = ilk[k]
        if isinstance(v, str):
            v = v[:30]
        print("  %-20s: %s" % (k, v))