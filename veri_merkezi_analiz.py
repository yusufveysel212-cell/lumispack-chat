# -*- coding: utf-8 -*-
"""Veri merkezi baglanti analizi."""
import io, os, re

# 1) Raporlar - hangi endpoint'leri kullaniyor?
print("=" * 70)
print("1. RAPORLAR (reports-*.js) - API cagrilari")
print("=" * 70)

for f in ["reports-core.js", "reports-main.js",
          "reports-advanced.js", "reports-final.js"]:
    yol = "static/js/modules/" + f
    if not os.path.exists(yol):
        continue
    with io.open(yol, "r", encoding="utf-8") as fh:
        ic = fh.read()
    
    # rptApi cagrilari
    cagrilar = re.findall(r"rptApi\(['\"]([^'\"]+)", ic)
    print()
    print("%s (%d endpoint):" % (f, len(cagrilar)))
    for c in sorted(set(cagrilar)):
        print("  - %s" % c)

# 2) Dashboard - hangi hesaplar?
print()
print("=" * 70)
print("2. DASHBOARD (ui-core.js) - renderOverview icerigi")
print("=" * 70)

with io.open("static/js/modules/ui-core.js", "r", encoding="utf-8") as f:
    ic = f.read()

# renderOverview fonksiyonu
bas = ic.find("function renderOverview")
if bas > 0:
    son = ic.find("function ", bas + 10)
    blok = ic[bas:son]
    # API cagrilari
    cagrilar = re.findall(r"api\(['\"]([^'\"]+)", blok)
    print("API cagrilari:")
    for c in sorted(set(cagrilar)):
        print("  - %s" % c)
    
    # Kendi hesabi
    print()
    print("Kendi hesap fonksiyonlari:")
    for fn in ["calc(", "AP(", "P.filter", "Q.reduce", "O.filter"]:
        if fn in blok:
            print("  - %s" % fn)

# 3) Finans - hangi API?
print()
print("=" * 70)
print("3. FINANS (finans.js) - API cagrilari")
print("=" * 70)

with io.open("static/js/modules/finans.js", "r", encoding="utf-8") as f:
    ic = f.read()

cagrilar = re.findall(r"api\(['\"]([^'\"]+)", ic)
for c in sorted(set(cagrilar)):
    print("  - %s" % c)

# 4) Bayiler
print()
print("=" * 70)
print("4. BAYILER (dealers.js) - API cagrilari")
print("=" * 70)

with io.open("static/js/modules/dealers.js", "r", encoding="utf-8") as f:
    ic = f.read()

cagrilar = re.findall(r"api\(['\"]([^'\"]+)", ic)
for c in sorted(set(cagrilar)):
    print("  - %s" % c)

# 5) Benim
print()
print("=" * 70)
print("5. BENIM (benim.js) - API cagrilari")
print("=" * 70)

with io.open("static/js/modules/benim.js", "r", encoding="utf-8") as f:
    ic = f.read()

cagrilar = re.findall(r"api\(['\"]([^'\"]+)", ic)
for c in sorted(set(cagrilar)):
    print("  - %s" % c)

# 6) hesap_service.py - mevcut fonksiyonlar
print()
print("=" * 70)
print("6. hesap_service.py - mevcut fonksiyonlar")
print("=" * 70)

with io.open("services/hesap_service.py", "r", encoding="utf-8") as f:
    ic = f.read()

for i, satir in enumerate(ic.split("\n"), 1):
    if satir.startswith("def "):
        print("  L%d: %s" % (i, satir.strip()[:100]))