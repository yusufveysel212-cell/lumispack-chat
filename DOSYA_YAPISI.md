# LUMISPAC v3 - DOSYA YAPISI VE MIMARI

## Üretim ve depo kabul akışı (15 Ekim 2026)

- `services/production_service.py`: sipariş açığı/minimum stok kuyruğu, üretim durum geçmişi, fire/geri dönüşüm, depo kabul/ret ve idempotent stok kabul işlemleri.
- `api/production.py`: `/api/production/board`, `/queue`, `/receipts`, `/reasons`, `/plans`, `/jobs/...` uçları.
- `static/js/modules/production.js`: Üretim & Depo panosu, kuyruk işlemleri, kabul talepleri ve yönetici duruş nedeni ekranı.
- `tests/test_production.py`: rol/yetki, süreç geçişleri, kabul/ret, yinelenen talep, stok idempotensi ve dosya yazım/geri alma hataları.
- `config.py`: `PRODUCTION_FILE` süreç kaydı yolu (`lumispac_uretim.json`); başlangıç verisi otomatik oluşturulmaz.
- `auth_module.py`, `api/security.py`: `uretim` ve `uretim_depo` sunucu yetki modülleri.

Üretim kabulü kullanılabilir stoğu yalnızca depo onayında artırır. Fire miktarı kullanıcı tarafından girilir ve geri dönüşüm stoğunda ayrı tutulur. Reçete kullanıcı tarafından KG/koli olarak girilebilir; reçete yoksa üretim tamamlama hammaddeden otomatik düşmez.

## Hammadde ve satın alma (15 Ekim 2026)

- `services/raw_material_service.py`, `api/raw_materials.py`: KG bazlı PET/PP ve diğer hammadde kataloğu, bayilerden ayrı tedarikçiler, satın alma belgeleri, depo kabulü, stok hareketleri ve kullanıcı tanımlı ürün reçeteleri.
- `static/js/modules/raw-materials.js`: Hammadde / Satın Alma / Hammadde Alım Ödemeleri arayüzü.
- `auth_module.py`, `api/security.py`: `satinalma_odeme` modülü; yönetici tam, muhasebe yazar, diğer departmanlar kapalı.
- `lumispac_raw_materials.json`: İlk işlemde oluşturulan kayıt deposu; başlangıç verisi otomatik yüklenmez.
- `hammadde_belgeleri/`: Özel klasörde tutulan, yalnız yetkili API ile indirilebilen satın alma ekleri.
- `tests/test_raw_materials.py`, `tests/test_production.py`: Yetki, satın alma ödemesi/kur/audit, belge, kabul/ret, idempotensi ve reçete tüketimi.


## 15 EKIM 2026 GUNCELLEMESI - MERKEZI HESAP + KOD SISTEMI

### Yeni Dosyalar
- services/hesap_service.py - Merkezi hesaplama motoru
- api/hesap.py - 5 endpoint
- static/js/modules/ayarlar.js - Ayarlar v3

### Yeni Endpoint'ler
- GET /api/hesap/urunler-stok - Tum urunler + guncel stok
- GET /api/hesap/urun/<kod>/stok - Tek urun stok
- GET /api/hesap/dashboard - Dashboard ozet
- GET /api/hesap/stok-ozet - Stok ozeti
- GET /api/hesap/kritik-stok - Kritik stok listesi

### Degisen Dosyalar
- services/order_service.py - _siparis_stok_hareket + stok entegrasyon
- services/product_service.py - benzersiz_kod_uret (akilli)
- static/js/modules/products.js - STOK sutunu guncellendi
- static/js/modules/stok.js - Otomatik senkron
- static/js/modules/orders.js - lineSnap + stok senkron

### Yeni Ozellikler
1. Merkezi hesap (tek dogruluk kaynagi)
2. Urunler -> stok otomatik
3. Stok -> tum sayfalar senkron
4. Siparis -> stok dusme
5. Akilli urun kodu (LUM-{hacim}{tip})


## FAZ 5 GUNCELLEMESI (14 Ekim 2026 - TAMAM)

### Faz 5'te degisen dosyalar:
- YENI: services/finans_service.py, api/finans.py, static/js/modules/finans.js
- YENI: services/stok_service.py, api/stok.py, static/js/modules/stok.js
- YENI: services/dealer_service.py (bayi_panel)
- YENI: services/dashboard_service.py, api/benim.py, static/js/modules/benim.js
- GUNCELLENDI: app.js (NAV - finans, stok, benim eklendi)
- GUNCELLENDI: index.html (v-finans, v-stok, v-benim sayfalari)
- GUNCELLENDI: ui.js (SOLM_RAPOR temizlendi, solMenuKur fix)
- GUNCELLENDI: static/smoke_test.html (85 test)

## FAZ 4c GUNCELLEMESI (14 Ekim 2026 - TAMAM)

### Modul Yukleme Sirasi (index.html) - DEGISTIRILEMEZ

utils -> notifications -> auth -> shortcuts -> tour -> pdf -> users -> cart -> orders -> quotes -> settings -> scenario -> reports -> products -> dealers -> app -> ui

## JS MODULLERI (static/js/modules/) - 19 MODUL

### utils.js (~2.42 KB, 11 fonksiyon)
Genel yardimcilar: $, esc, fmt, TL, pct, num, toast, pbar, api, cnt, setTheme

### notifications.js (~17.19 KB, 22 fonksiyon)
Bildirim sistemi (panel, ayar, ses)

### auth.js (~16.26 KB, 25 fonksiyon)
Login/logout/token/yetki. fetch override.

### shortcuts.js (~4.55 KB)
Klavye kisayollari

### tour.js (~7.38 KB)
Ilk kullanim turu

### pdf.js (~5.60 KB, 6 fonksiyon)
PDF islemleri

### users.js (~22.03 KB, 19 fonksiyon)
Kullanici ve departman yonetimi

### cart.js (~4.78 KB, 9 fonksiyon)
Sepet modulu

### orders.js (~9.42 KB, 9 fonksiyon)
Siparisler + STAT, scls, lineSnap

### quotes.js (~6.07 KB, 6 fonksiyon)
Teklifler

### settings.js (~2.20 KB, 5 fonksiyon)
Ayarlar, yedek listesi

### products.js (~22.75 KB, 41 fonksiyon)
Urun yonetimi (3 asama: cekirdek, kolon/undo, tablo/toplu)

### dealers.js (~4.10 KB, 9 fonksiyon)
Bayiler

### scenario.js (~7.38 KB, 8 fonksiyon)
Kur takibi, senaryo analizi

### reports-core.js (~11.85 KB, ~15 fonksiyon)
Altyapi: rptCounter, rptKpi, rptChart, rptChartSil, rptRenkler,
rptYukle, rptApi, rptPanelYukle, rptHata, rptGrupSec,
_rptAltSekmeleriYukle, _rptSekmeAc + 29 window atama

### reports-main.js (~25.16 KB, 7 fonksiyon)
Temel raporlar: rptDashYukle, rptCostYukle, rptProfitYukle,
rptSensYukle, rptTrendYukle, rptDealerYukle, rptAbcYukle

### reports-advanced.js (~36.54 KB, ~10 fonksiyon)
Ileri raporlar: rptShipYukle, rptTargetYukle, rptAnomaliDetay,
rptMusteriYukle, rptKategoriYukle, rptGramajYukle, rptTeklifTakipYukle
Sabitler: SEG_RENK, GUN_ADLARI, KAT_RENK, KAT_IKON,
         YD_RENK, YD_ISIM, YD_ACIKLAMA

### reports-final.js (~19.38 KB, ~3 fonksiyon)
Son raporlar: rptMarjAlarmYukle, rptAnomaliYukle, rptAiTahminYukle

### ui-core.js (~14.21 KB, 17 fonksiyon)
closeModal, renderOverview, renderTape, ovExtra, applyPrefs,
setPref, loadPrefs, renderPref, decorateKpis, ovCharts, confetti,
enterApp, flashRow, repRows, renderReports, renderAll, go
Sabitler: ACC, PREF, IC, KIC, CAT_COL, EMPTY, CNT_IDS

### ui-palette.js (~1.54 KB, 4 fonksiyon)
CMDS, openPal, palList, runPal

### ui-menu.js (~6.07 KB, 8 fonksiyon)
mobilMenuToggle, mobilMenuKapat, setTopH, modernConfirm,
modernConfirmOnayla, solMenuKur, solMGo, solMKatAc
Sabitler: SOLM_RAPOR, SOLM_GRUP

### ui-init.js (~6.05 KB)
Event listener'lar, Init IIFE ([P,S,R,Q,D,O] = await Promise.all),
window.X atamalari (28 adet), go() yetki kontrolu override
- Overview, prefs, charts (A)
- Komut paleti, confetti (B1)
- Cekirdek UI: enterApp, go, renderAll (B2)
- Mobil menu (C1)
- modernConfirm + init IIFE (C3)
- Sol menu: SOLM_RAPOR, solMenuKur, solMGo (C4)
- go() yetki kontrol override (en sonda)

## static/js/app.js (~7.82 KB)

Global state + paylasilan sabitler:
- P, S, R, cart, Q, B, D, O, curDealer
- NAV, calc, cat, cc, catOrder, TM, AP, warns, round2, _entered
- Tum let/const -> var (global scope icin)

## static/js/modules/finans.js (~23 KB)
Finans modulu (Faz 5-1, 5-2): gelir/gider, kasa ozeti, aylik rapor, grafikler

## static/js/modules/stok.js (~11 KB)
Stok modulu (Faz 5-3a): giris/cikis, kalan stok, kritik uyari

## static/js/modules/benim.js (~4.5 KB)
Kisisel dashboard (Faz 5-5): rol bazli ozet + aktiviteler

## PYTHON MODULLERI

### lumispac_app.py (~8 KB)
Flask baslatma, 12 blueprint kaydi, error handler

### api/ (13 blueprint - FAZ 2 + FAZ 5 + 15 EKIM)
products, orders, quotes, dealers, backups, help, pdf, auth, users,
finans, stok, benim

### services/ (8 py servis - FAZ 3 + FAZ 5 + 15 EKIM)
product_service, order_service, quote_service,
finans_service, stok_service, dealer_service, dashboard_service

### helpers.py, state.py, utils.py, config.py
Temel yardimcilar

### auth_module.py, pdf_module.py, rate_sources.py
Auth, PDF, kur motoru

### reports/ (8 modul, 26 rapor)
Mixin pattern

### ARACLAR
- yedek_v2.py: Yedekleme (v3)
- temizlik_v2.py: Temizlik
- import_denetci.py: Import tarayicisi
- import_tarayici.py: Blueprint tarayici
- smoke_test.html: Frontend smoke test (85 test)

## KRITIK NOTLAR

### 1. JS modul sirasi (DEGISTIRILEMEZ)
utils -> notifications -> auth -> shortcuts -> tour -> pdf -> users -> cart -> orders -> quotes -> settings -> scenario -> reports -> products -> dealers -> app -> ui

### 2. Global erisim
Her JS modulu sonunda window.X = X ile global erisim vermeli.

### 3. Global degisken paylasimi
P, S, R, cart, Q, B, D, O, curDealer - app.js'te **var** olarak kalir.
Paylasilan sabitler: NAV, calc, cat, cc, catOrder, TM, AP, warns.

### 4. Script sirasi (app.js -> ui.js)
app.js once (global state), ui.js sonra (init IIFE + override).

### 5. go() override
ui.js'in EN SONUNA tasindi - `go` tanimlandiktan sonra override calisir.

### 6. fetch override
auth.js window.fetch'i override ediyor (X-Auth-Token ekler).

### 7. HTML onclick
Bircok elemanda onclick="fonkAdi()" var. window.X = X sart.

### 8. rate_sources.fetch_rate() donusu
{'v': 49.36, 'source': 'Yahoo Finance'} - 'rate' DEGIL 'v'

### 9. POST /api/products TUZAGI
Tum listeyi degistirir. Tek urun gonderme!

### 10. pct() STRING doner
'25,00%' seklinde. Sayisal icin v*100.

### 11. reports/ Mixin Pattern
Raporlar sinifi MRO ile mixin'leri birlestirir.

## VERI DOSYALARI (JSON)
- lumispac_data.json (urunler)
- lumispac_settings.json
- lumispac_users.json
- lumispac_orders.json
- lumispac_quotes.json
- lumispac_dealers.json
- lumispac_finans.json (gelir/gider)
- lumispac_stok.json (stok hareketleri)

## ONEMLI KOMUTLAR

### Uygulamayi Baslat
cd /d "C:/Users/yusuf/OneDrive/Masaustu/DEPSPEK/lumispac_v3"
python lumispac_app.py

### Test
python -m pytest tests/ -v

### Yedek
python yedek_v2.py al "aciklama"

### Import Denetimi
python import_denetci.py

### Temizlik
python temizlik_v2.py test
python temizlik_v2.py sil

### Cache Temizle
rmdir /s /q __pycache__ api\__pycache__ reports\__pycache__ services\__pycache__

## DOSYA BOYUTLARI (Faz 4c)

| Dosya | Once | Sonra |
|-------|------|-------|
| lumispac_app.py | 470 KB | ~8 KB |
| static/js/app.js | 299 KB | **7.82 KB** |
| modules/utils.js | yok | 2.42 KB |
| modules/notifications.js | yok | 17.19 KB |
| modules/auth.js | yok | 16.26 KB |
| modules/shortcuts.js | yok | 4.55 KB |
| modules/tour.js | yok | 7.38 KB |
| modules/pdf.js | yok | 5.60 KB |
| modules/users.js | yok | 22.03 KB |
| modules/cart.js | yok | 4.78 KB |
| modules/orders.js | yok | 9.42 KB |
| modules/quotes.js | yok | 6.07 KB |
| modules/settings.js | yok | 2.20 KB |
| modules/products.js | yok | 22.75 KB |
| modules/dealers.js | yok | 4.10 KB |
| modules/scenario.js | yok | 7.38 KB |
| modules/reports.js | yok | 154.73 KB |
| modules/ui.js | yok | 28.22 KB |
| modules/finans.js | yok | 23.11 KB |
| modules/stok.js | yok | 10.72 KB |
| modules/benim.js | yok | 4.47 KB |

---

Son guncelleme: 2026-10-15 (Merkezi Hesap + Kod + Temizlik TAMAM)
