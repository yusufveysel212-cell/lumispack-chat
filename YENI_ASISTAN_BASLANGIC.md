# YENI ASISTAN BASLANGIC REHBERI

**Son guncelleme:** 15 Ekim 2026 (Merkezi Hesap + Kod + Temizlik TAMAM)

---

## MERHABA YENI ASISTAN!

Yusuf'un LUMISPAC v3 projesine hos geldin.

Bu dosya, ILK OKUYACAGIN dosyadir.

---

## 1. HIZLI OZET

### Proje Nedir?
B2B ambalaj sektoru icin maliyet + siparis + kur + PDF + rapor yonetim sistemi.

- Kullanici: Kucuk/orta ambalaj ureticisi (1-10 kisi)
- Amac: Excel'den kurtulmak isteyenler icin tam cozum
- Sahibi: Yusuf (kod yazmayi ogreniyor)
- Dil: Turkce

### Su An Nerede?
15 Ekim 2026 - Merkezi Hesap + Kod Sistemi + Buyuk Temizlik TAMAM.

- app.js: 248.65 KB -> 7.82 KB (%97!)
- reports.js: 158 KB -> 4 parca
- ui.js: 28 KB -> 4 parca
- 27 JS modulu, 13 Blueprint, 8 py servis
- 142 backend + 85 smoke test geciyor
- Kok dizin: 16 py (94 -> 16, %83 temizlik)
- Yedek: ~19.6 MB kazanc

### Sonraki Ne?
**Faz 6** (Denetim Izi) - 3-4 saat

**Yapilan (15 Ekim 2026):**
- Merkezi Hesap Sistemi
- Akilli Kod Sistemi
- Siparis -> Stok Dusme
- 78 py + 244 .bak temizligi

---

## 1.5. FAZ 5 TAMAM (14 Ekim 2026)

Faz 5'te 5 buyuk ozellik eklendi:
- Finans Modulu (22 test)
- Grafikler (8 test)
- Stok Modulu (24 test)
- Bayi Paneli (15 test)
- Kisisel Dashboard (7 test)

## 1.5b. 15 EKIM 2026 - MERKEZI HESAP + TEMIZLIK TAMAM

**Buyuk Ozellikler:**
- Merkezi Hesap Servisi (tek dogruluk kaynagi)
- 5 API endpoint
- Urunler -> stok otomatik
- Stok -> tum sayfalar senkron
- Siparis -> stok dusme
- Akilli kod: LUM-{hacim}{tip}

**Temizlik:**
- 78 py silindi (230 KB)
- 244 .bak silindi (7.34 MB)
- 8 eski yedek (8.73 MB)
- 3 log yedegi (2.86 MB)
- Toplam: ~19.6 MB

**Sonraki:** Faz 6 (Denetim Izi)

### Faz 4d Ozeti:

Faz 4d (14.10.2026) TAMAM:
- renderPref bug fix
- Bildirim sesi kilidi
- Bildirim ac/kapa kontrolu
- Yorum temizligi (10.26 -> 7.82 KB)
- JS smoke test (58 -> 85 test)
- let/var kontrolu (bilincli: let kaldi)

### Faz 5 TAMAM:

5 buyuk ozellik eklendi (Faz 5-1, 5-2, 5-3a, 5-4, 5-5):
- Finans Modulu (22 test)
- Grafikler (8 test)
- Stok Modulu (24 test)
- Bayi Paneli (15 test)
- Kisisel Dashboard (7 test)

### Sirada:

- **Faz 6:** Denetim Izi (tum kullanici islemleri loglama) - SIRADAKI
- **Faz 5-6:** AI Uretim Kontrolu - sonra

### Yapilanlar (15 Ekim 2026):

- Merkezi Hesap Servisi (hesap_service.py)
- 5 endpoint (/api/hesap/...)
- Urunler -> stok baglantisi (readonly)
- Stok -> otomatik senkron
- Siparis -> stok dusme (Onaylandi/Iptal)
- Akilli kod: LUM-{hacim}{tip}
- 27 urun kod yenileme
- 78 py + 244 .bak + 8 yedek temizligi (~19.6 MB)

---

## 1.6. STANDART IS AKISI (Her Gorev Icin)

1. Analiz - Sorunu anla
2. Yedek - python yedek_v2.py al "X oncesi"
3. Degisiklik - Notepad + script
4. Test - pytest + tarayici
5. Dogrulama - Console hata yok
6. Faz Sonu - temizlik + yedek

---

## 1.7. ORNEK: renderPref Bug Cozumu

**Yusuf der:** "renderPref bug'i cozelim"

**Sen boyle yaparsin:**

### Adim 1: Analiz
findstr /C:"function renderPref" static\js\modules\ui.js
findstr /C:"prefBox" app\templates\index.html

### Adim 2: Yedek
python yedek_v2.py al "renderPref fix oncesi"

### Adim 3: Sorunu bul
ui.js'te renderPref'i oku. $('prefBox') var mi?
HTML'de div id="prefBox" var mi?

### Adim 4: Duzelt
HTML'de prefBox yoksa ekle
renderPref yanlis ID kullaniyorsa duzelt

### Adim 5: Test
Tarayicida Ayarlar -> Gorunum kutusu dolu mu?

### Adim 6: Rapor
"RenderPref duzeltildi. Once bos idi, simdi dolu."

**Bu pattern'i her gorev icin kullan!**

---

## 2. PROJE KONUMU

C:/Users/yusuf/OneDrive/Masaustu/DEPSPEK/lumispac_v3

### Calisma Komutu
cd /d "C:/Users/yusuf/OneDrive/Masaustu/DEPSPEK/lumispac_v3"

### Uygulamayi Baslat
python lumispac_app.py

- Tarayici: http://127.0.0.1:5000
- Giris: admin / 123456

---

## 3. ILK MESAJ

Yusuf yeni sohbete boyle baslar:

Merhaba! LUMISPAC v3 projesine devam ediyoruz.
Lutfen su dosyalari oku:
1. YENI_ASISTAN_BASLANGIC.md (bu dosya)
2. PROJE_GECMISI.md
3. YAPILACAKLAR.md
4. README.md
5. DOSYA_YAPISI.md
6. ASISTAN_KILAVUZU.md
7. ASISTAN_NOTLARI.md
Okuyup kaldigimiz yerden devam edelim.

Sen boyle cevap ver:
1. Once dosyalari oku (7 MD)
2. Kisa ozet ver: Anladim. Su noktadayiz: 15 Ekim 2026 - Merkezi Hesap + Kod + Temizlik TAMAM. Sirada Faz 6 (Denetim Izi).
3. Sonraki adimi sor: Faz 6'ya baslayalim mi?
4. Standart is akisina uy

---

## 4. OKUMA SIRASI (ONEMLI!)

Yeni sohbette bu sirayla oku:

1. YENI_ASISTAN_BASLANGIC.md (bu dosya) - genel bakis
2. PROJE_GECMISI.md - kronolojik tarihce
3. YAPILACAKLAR.md - ne yapildi, ne kaldi
4. README.md - kurulum, modul listesi
5. DOSYA_YAPISI.md - teknik harita
6. ASISTAN_KILAVUZU.md - davranis kurallari + modul/ozellik ekleme (EK 1-2)
7. ASISTAN_NOTLARI.md - teknik dersler

---

## 5. DOSYA YAPISI (OZET)

lumispac_v3/
  lumispac_app.py         (~8 KB Flask ana)
  config.py, state.py, utils.py, helpers.py
  auth_module.py, pdf_module.py, rate_sources.py
  users_ui.py, help_content.py, reports_api.py
  yedek_v2.py, temizlik_v2.py, import_denetci.py

  api/                    (12 blueprint)
  services/               (7 py servis)
  reports/                (8 modul)
  tests/                  (142 test)

  static/
    css/style.css
    js/
      app.js              (~7.82 KB, global state)
      modules/            (19 modul)

  app/templates/index.html
  yedekler_v2/
  _arsiv/

  *.md dosyalari

---

## 6. KURALLAR (OZET)

### Iletisim
- Turkce konus
- Karakter/uzunluk uyarisi YAPMA
- Kisa cumleler, madde isaretleri
- Tablolar kullan
- Basarilari kutla: MUKEMMEL! HARIKA!

### Guvenlik
- Her degisiklikten once YEDEK AL
- Adim adim ilerle
- Test etmeden devam etme
- Yedekten geri donus hazir

### Teknik
- AST kullan (regex degil)
- UTF-8 kodlama
- CMD komutlari tek satir
- Python 3.10 uyumlulugu

### KRITIK: Calisma Pattern'i (Yusuf ile anlasma)
1. Asistan CMD kodu verir: `type nul > script.py && notepad script.py`
2. Yusuf Notepad'e kodu yapistirir, Ctrl+S, Alt+F4
3. Yusuf CMD'de calistirir: `python script.py`
4. Ciktiyi asistana yapistirir
5. Asistan sonraki adimi soyler

**Uzun kod icin ASLA yapistirilacak metin verme -> script ver.**
Yusuf CMD'ye uzun kod yapistiramaz.

---

## 7. YUSUF'UN TARZI

### Genel
- Samimi, ogrenmeye acik, hizli karar veren
- Vizyoner (Finans, AI, grafik, paneller)
- Hata yapmaktan korkar -> yedek + test
- Neden? sorar -> MUTLAKA cevap ver

### Hassas Noktalar
1. HATA YAPMAKTAN KORKAR
2. UZUN BEKLEME SEVMEZ
3. KARMASIK ACIKLAMA SEVMEZ
4. BELIRSIZLIK SEVMEZ

### Motivasyon
1. Kazanc gormek (KB, %)
2. Ilerleme gormek (once/sonra tablolari)
3. Ogrenmek (kavram isimleri)
4. Tamamlama hissi

### Iletisim
- Turkce
- Kisa cumleler
- Madde isaretleri
- Bol bosluk
- Emoji (kutlama)

---

## 8. STANDART IS AKISI

### Adim 1: Analiz
Analiz scripti calistir. Ciktisini incele, plani yap.

### Adim 2: Yedek
python yedek_v2.py al "aciklama"

### Adim 3: Degisiklik
AST ile syntax kontrolu
Dosyayi yaz

### Adim 4: Test
python -m pytest tests/ -v
python lumispac_app.py

### Adim 5: Dogrulama
Yusuf tarayicida test eder, sonucu bildirir.

### Adim 6: Faz Sonu
python import_denetci.py
python temizlik_v2.py test
python temizlik_v2.py sil
python yedek_v2.py al "X tamam"

---

## 9. SIK KULLANILAN KOMUTLAR

### Uygulamayi Baslat
python lumispac_app.py

### Test
python -m pytest tests/ -v

### Yedek
python yedek_v2.py al "aciklama"
python yedek_v2.py liste
python yedek_v2.py geri YEDEK_ADI

### Import Denetimi
python import_denetci.py

### Temizlik
python temizlik_v2.py test
python temizlik_v2.py sil

### Cache Temizle
rmdir /s /q __pycache__ api\__pycache__ reports\__pycache__ services\__pycache__ 2>nul

---

## 10. KRITIK DERSLER (FAZ 4c)

### 1. Script Sirasi (DEGISTIRILEMEZ)
utils -> notifications -> auth -> shortcuts -> tour -> pdf -> users -> cart -> orders -> quotes -> settings -> scenario -> reports -> products -> dealers -> app -> ui

app.js once, ui.js son!

### 2. Global State var Olmali
P, S, R, cart, Q, B, D, O, curDealer - app.js'te var olarak kalir.
let/const -> var yapilmali (global scope icin).

### 3. go() Override
ui.js'in EN SONUNA tasindi.
Sebep: app.js once yuklenir, go ui.js'te tanimli, override ui.js sonunda calisir.

### 4. Modul Tasima 3 Adim
1. modules/X.js olustur (window.X = X ekle)
2. app.js'ten fonksiyonlari sil
3. index.html'e script tag ekle (dogru sirada)

### 5. Cift Tanimlama Kontrolu
Her tasimadan sonra app.js ve modul.js karsilastir.

---

## 11. YAPILMAMASI GEREKENLER

1. Toplu degisiklik yapma (tek seferde bir sey)
2. Test etmeden devam etme
3. Regex ile toplu degistirme (AST kullan)
4. Uzun cevaplar verme
5. Ingilizce karistirma
6. Karmasik cozumler onerme
7. Yedek almadan degisiklik yapma

---

## 12. YAPILMASI GEREKENLER

1. Her script'te syntax kontrolu
2. Kazanclari say (KB, %)
3. Basariyi kutla (MUKEMMEL! HARIKA!)
4. Sonraki adimi soyle
5. Yusuf'a secenek sun ama yonlendir
6. Hatalari acikla (ne, neden, nasil)
7. Ogretıcı ol (kavram isimleri)

---

## 13. ACIL DURUMLAR

### Uygulama acilmiyor
copy static\js\app.js.bak_X static\js\app.js

### Console'da hata
1. F12 -> Console
2. Kirmizi hatayi oku
3. Hatanin satirini kontrol et
4. Yedekten don

### Bir sey ters gitti
python yedek_v2.py liste
python yedek_v2.py geri YEDEK_ADI

---

## 14. BASARI KRITERI

1. Kullanici Excel'e donmek istemiyorum diyor mu?
2. Yeni ozellik eklemek kolay mi? (<30 dakika)
3. Hata orani dusuk mu? (<1/hafta)
4. Kod okunabilir mi?
5. Test kapsami yeterli mi?

---

## 15. YENI OZELLIK / MODUL

Detayli rehber icin ASISTAN_KILAVUZU.md sonuna bak:
- **EK 1: YENI MODUL EKLEME** - Mevcut kodu ayirma
- **EK 2: YENI OZELLIK EKLEME** - Yeni ozellik ekleme (Finans, AI vs.)

Ornek: Finans modulu -> EK 2'de adim adim

---


## 16. YUSUF ILE CMD CALISMA DETAYLARI

### CMD Temel Kurallar

1. Her komut ayri satirda (bazen Yusuf birlestirir, uyar)
2. cd /d "..." kullan (yol degistirmek icin)
3. UTF-8 kodlama (Turkce karakterler icin)
4. Uzun kod CMD'ye yapistirilmaz -> Notepad script
5. Ctrl+C ile durdur (Flask sunucusu)

### Standart 6 Adim

1. Analiz - findstr, dir ile dosya kesfi
2. Yedek - python yedek_v2.py al "X oncesi"
3. Degisiklik - type nul > script.py && notepad script.py + python script.py
4. Test - python -m pytest tests/ -v + tarayici F12
5. Dogrulama - Console hata yok
6. Faz Sonu - import_denetci.py + temizlik_v2.py + yedek_v2.py al "X tamam"

### Script Pattern (Uzun Python Kodu Icin)

Komut:
  type nul > fix_X.py && notepad fix_X.py

Notepad'de:
  1. Kodu yapistir
  2. Ctrl+S (kaydet)
  3. Alt+F4 (kapat)

CMD'de:
  python fix_X.py

### Test Pattern

Backend:
  python -m pytest tests/ -v
  Beklenen: 142/142

Frontend (tarayici):
  1. python lumispac_app.py ile Flask baslat
  2. Tarayicida http://127.0.0.1:5000 ac
  3. F12 -> Console ac
  4. Test et

Smoke test:
  http://127.0.0.1:5000/static/smoke_test.html
  Beklenen: 85/85

### Yedek Pattern

Al:
  python yedek_v2.py al "aciklama"

Listele:
  python yedek_v2.py liste

Geri don:
  python yedek_v2.py geri YEDEK_ADI

### Flask Cache Temizleme

Kod degisince TAMAMEN yenile:
  rmdir /s /q __pycache__ api\__pycache__ services\__pycache__ 2>nul
  python lumispac_app.py

### Temizlik

Test (ne silinecek goster):
  python temizlik_v2.py test

Uygula:
  python temizlik_v2.py sil

### Import Denetimi

  python import_denetci.py
  Tum Python importlarini kontrol eder.

### SIK KARSILASILAN SORUNLAR

| Sorun | Cozum |
|-------|-------|
| Flask calismiyor | rmdir /s /q __pycache__ + restart |
| API 404 | Flask restart edilmemis |
| API 401 | Token suresi dolmus -> login |
| "X is not defined" | Script sirasi kontrol (index.html) |
| Menu yanlis yerde | insertBefore |
| Turkce karakter bozuk | Bozuk karakter ile eslestir |
| CMD komut tanimiyor | Ayri satirda calistir |
| Modul yuklenmiyor | index.html'e script tag ekle |

### Onemli Notlar

- Yusuf tek satirda birden fazla komut yapistirabilir -> Uyar
- Yusuf uzun ciktlari yapistirir -> Onemli kismi alintila
- Yusuf panik yapmaz -> Sakin anlat
- Yusuf Neden? sorar -> MUTLAKA cevap ver
- Yusuf ogrenmek ister -> Kucuk notlar ver

### Calisma Tarzi

- OneDrive klasorunde calisir (bazen 2-3 sn senkronizasyon bekle)
- Windows 11, Python 3.10
- CMD'de tek satir komutlar
- Notepad'de kod yapistirmayi sever
- Uzun oturumlar yapabilir (3-4 saat)

### Basari Kriteri

1. Kullanici "Excel'e donmek istemiyorum" diyor mu?
2. Yeni ozellik eklemek kolay mi? (<30 dakika)
3. Hata orani dusuk mu? (<1/hafta)
4. Kod okunabilir mi?
5. Test kapsami yeterli mi?

---

## 17. GELISTIRME NASIL YAPILIR?

### Yeni Ozellik Eklemek

Ornek: "Kargo Takip" ozelligi

1. Analiz - NE, NEDEN, NASIL, NEREDE
2. Yedek - python yedek_v2.py al "kargo takip oncesi"
3. Backend:
   - api/kargo.py (Blueprint)
   - services/kargo_service.py (is mantigi)
   - lumispac_app.py'ye kayit
   - tests/test_kargo.py (~10 test)
4. Frontend:
   - static/js/modules/kargo.js
   - index.html'e script tag + sayfa
   - app.js'te NAV'a ekle
5. Test:
   - python -m pytest tests/ -v
   - Tarayici F12 test
6. Dokumante:
   - PROJE_GECMISI.md, README.md, YAPILACAKLAR.md, DOSYA_YAPISI.md

### Yeni Modul Eklemek (Buyuk Kodu Bolmek)

Ornek: reports.js cok buyudu, 4 parca yap

1. Analiz - Hangi fonksiyonlar hangi parcaya gidecek?
2. Yedek - python yedek_v2.py al "reports bol oncesi"
3. Yeni dosyalar olustur:
   - reports-core.js (altyapi)
   - reports-main.js (temel raporlar)
   - reports-advanced.js (ileri)
   - reports-final.js (son)
4. index.html'e script tag ekle (sirayla)
5. reports.js'i SIL
6. Test:
   - python -m pytest tests/ -v
   - Tarayici F12
   - Smoke test
7. Dokumante

### Bug Fix Yapmak

Ornek: "Bildirim sesi gelmiyor"

1. Analiz - Sorun nerede?
   findstr /N /C:"function" static\js\modules\notifications.js
2. Yedek - python yedek_v2.py al "bildirim sesi fix oncesi"
3. Teshis - Console'dan test et
4. Duzeltme - Script ile
5. Test - Tarayicida
6. Dokumante

### Buyuk Yeniden Yapilandirma

Ornek: "app.js'i 5 modullere bol"

1. Analiz - AST ile fonksiyon sinirlarini bul
2. Yedek - python yedek_v2.py al "app.js bol oncesi"
3. Asamali tasima:
   - Asama 1: Fonksiyon grubu 1 -> Test
   - Asama 2: Fonksiyon grubu 2 -> Test
   - ...
4. Her asama sonrasi test
5. Dokumante

---

## 18. DOSYA YERLERI (HIZLI REFERANS)

### Ana Klasorler

| Klasor | Icerik | Sayi |
|--------|--------|------|
| api/ | Blueprint'ler | 12 |
| services/ | Py servisler | 7 |
| reports/ | Rapor modulleri | 8 |
| tests/ | Pytest testleri | 142 |
| static/js/modules/ | JS modulleri | 19 |
| app/templates/ | HTML | 1 |
| yedekler_v2/ | Yedekler | 150+ |
| _arsiv/ | Arsiv | - |

### Onemli Dosyalar

| Dosya | Amac |
|-------|------|
| lumispac_app.py | Flask ana (~8 KB) |
| static/js/app.js | Global state (7.82 KB) |
| config.py | Sabitler + dosya yollari |
| state.py | Global state |
| utils.py | Yardimcilar |
| helpers.py | Yardimcilar |
| auth_module.py | Auth |
| pdf_module.py | PDF |
| rate_sources.py | Kur motoru |
| app/templates/index.html | HTML |
| static/css/style.css | CSS |
| static/smoke_test.html | Smoke test |

### Araclar

| Arac | Amac |
|------|------|
| yedek_v2.py | Yedekleme (v3) |
| temizlik_v2.py | Cache temizleme |
| import_denetci.py | Import tarayici |
| import_tarayici.py | Blueprint tarayici |

---

## 19. HATA COZUM REFERANSI (BUGUNUN HATALARI)

| # | Sorun | Cozum |
|---|-------|-------|
| 1 | renderPref bug | NAV.find null kontrolu |
| 2 | Bildirim sesi | _sesKilidiAc: click/keydown |
| 3 | Bildirim ac/kapa | if(!_a.aktif) kontrolu |
| 4 | </script> HTML sorunu | <\/script> escape |
| 5 | api() method parametresi | api(url, 'POST', data) |
| 6 | Stok API modul yuklenmemis | Script tag'ler eklendi |
| 7 | Doughnut chart veri yok | Trend + kategori endpoint |
| 8 | Bayi paneli tablo tasmasi | table-layout:fixed + modal 760px |
| 9 | Rapor duplicate | Regex ile birlestirme |
| 10 | Sol menu yeri | insertBefore ile Raporlar'dan sonra |
| 11 | MD Turkce karakter | Bozuk karakterle eslestirme |
| 12 | Flask cache | rmdir __pycache__ + restart |

---

## SON SOZ

Yusuf sana guveniyor.
Sabirli ol, guvenli ol, aciklayici ol.
Turkce konus, basarilari kutla, adim adim ilerle.

Basarilar!

---

**Son guncelleme:** 2026-10-15 (Merkezi Hesap + Temizlik TAMAM)
