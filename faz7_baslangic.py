# -*- coding: utf-8 -*-
"""YAPILACAKLAR.md - Faz 7 ekle."""
import io

with io.open("YAPILACAKLAR.md", "r", encoding="utf-8") as f:
    ic = f.read()

YENI = """## Faz 7: Veri Merkezi Tamamlama (SIRADAKI - BASLADI 15.10.2026)

**Amac:** Tum moduller merkezi hesap kullansin.

**Kapsam:**
- [ ] 7-1: reports/base.py → merkezi
- [ ] 7-2: Dashboard → /api/hesap/dashboard
- [ ] 7-3: Benim → hesap_service
- [ ] 7-4: Bayiler → hesap_service
- [ ] 7-5: Test + Dokumante

**Sure:** ~4 saat

**Neden:** Raporlar kendi hesabi yapiyor → tutarsizlik riski.

**Hedef:** %100 merkezi — tum sayfalar ayni veriyi gosterir.

### Faz 6 (Denetim Izi) - ERTELENDI

Faz 7 sonrasi yapilacak.

---

## Faz 6: Denetim Izi (Eski)

**Amac:** Tum kullanici islemlerini kaydet ve izle.
"""

# "## Siradaki Is: Faz 6" -> yerine Faz 7
eski = "## Siradaki Is: Faz 6 (Denetim Izi)"
if eski in ic:
    ic = ic.replace(eski, YENI + "\n## Eski Faz 6 Notlari", 1)
    print("[OK] Faz 7 eklendi, Faz 6 ertelendi")
else:
    # En basa ekle
    ic = ic.replace("## Bugun Yapilanlar (15 Ekim 2026)",
                    YENI + "\n## Bugun Yapilanlar (15 Ekim 2026)", 1)
    print("[OK] Faz 7 basa eklendi")

with io.open("YAPILACAKLAR.md", "w", encoding="utf-8") as f:
    f.write(ic)

print()
print("Kontrol:")
with io.open("YAPILACAKLAR.md", "r", encoding="utf-8") as f:
    for i, satir in enumerate(f.readlines(), 1):
        if "Faz 7" in satir or "Faz 6" in satir:
            print("  L%d: %s" % (i, satir.strip()[:100]))