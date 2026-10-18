# -*- coding: utf-8 -*-
"""
Test verilerini sifirla.
- Stok: TUM hareketler silinir (hepsi test)
- Siparisler: []
- Teklifler: []
- Finans: {"kayitlar": [], "kategoriler": [...]}
"""
import io, json, os
from datetime import datetime

# Once guvenlik yedegi
TARIH = datetime.now().strftime("%Y%m%d_%H%M%S")
YEDEK_DIR = "_arsiv/veri_yedek_%s" % TARIH
os.makedirs(YEDEK_DIR, exist_ok=True)

DOSYALAR = [
    "lumispac_stok.json",
    "lumispac_orders.json",
    "lumispac_quotes.json",
    "lumispac_finans.json",
]

# 1) Yedek
print("=" * 70)
print("1. YEDEK ALINIYOR")
print("=" * 70)
for d in DOSYALAR:
    if os.path.exists(d):
        with io.open(d, "r", encoding="utf-8") as f:
            ic = f.read()
        with io.open(os.path.join(YEDEK_DIR, d), "w", encoding="utf-8") as f:
            f.write(ic)
        print("  [YEDEK] %s -> %s" % (d, YEDEK_DIR))
    else:
        print("  [ATLA] %s yok" % d)

print()

# 2) Sifirla
print("=" * 70)
print("2. VERILER SIFIRLANIYOR")
print("=" * 70)

# Stok
with io.open("lumispac_stok.json", "w", encoding="utf-8") as f:
    json.dump({"hareketler": [], "esikler": {}}, f, ensure_ascii=False, indent=2)
print("  [OK] lumispac_stok.json -> bos")

# Siparisler
with io.open("lumispac_orders.json", "w", encoding="utf-8") as f:
    json.dump([], f, ensure_ascii=False, indent=2)
print("  [OK] lumispac_orders.json -> bos")

# Teklifler
with io.open("lumispac_quotes.json", "w", encoding="utf-8") as f:
    json.dump([], f, ensure_ascii=False, indent=2)
print("  [OK] lumispac_quotes.json -> bos")

# Finans
with io.open("lumispac_finans.json", "r", encoding="utf-8") as f:
    finans = json.load(f)
finans["kayitlar"] = []
with io.open("lumispac_finans.json", "w", encoding="utf-8") as f:
    json.dump(finans, f, ensure_ascii=False, indent=2)
print("  [OK] lumispac_finans.json -> kayitlar bos, kategoriler korundu")

print()
print("=" * 70)
print("3. KONTROL")
print("=" * 70)
for d in DOSYALAR:
    if os.path.exists(d):
        with io.open(d, "r", encoding="utf-8") as f:
            v = json.load(f)
        if isinstance(v, list):
            print("  %s -> %d kayit" % (d, len(v)))
        elif isinstance(v, dict):
            k = ", ".join("%s=%d" % (kk, len(vv) if isinstance(vv, (list, dict)) else 1) for kk, vv in v.items())
            print("  %s -> %s" % (d, k))

print()
print("Yedek: %s" % YEDEK_DIR)