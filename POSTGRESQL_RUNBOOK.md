# LUMISPAC PostgreSQL İşletim ve Sağlamlaştırma Planı

Tek bilgisayarlı kurulum: PostgreSQL 18, `lumispac` veritabanı, uygulama rolü `lumispac_app`, yalnızca `127.0.0.1:5432`. Parola proje dosyasında tutulmaz; Windows kullanıcı alanındaki ACL korumalı `pgpass.conf` kullanılır.

## Fazların durumu

1. **Geri yükleme provası — geçti.** `postgres_verified_20261016_133359.dump`, canlı veritabanından ayrı, geçici PostgreSQL 18 kümesine geri yüklendi. Şema 18, 43 tablo ve 596 satır; `integrity_check` başarılı, uygulama ana sayfası HTTP 200. Test kümesi kapatılıp kaldırıldı.
2. **Otomatik yedek ve saklama — geçti.** Uygulama açılışında günlük tam yedek alınır; uygulama açıkken saatlik kontrol, gece yarısını kaçıran çalıştırmaları yakalar. Yalnızca adlandırma kuralına uyan otomatik günlük yedekler 30 gün tutulur. Elle alınan zaman damgalı ve aktarım öncesi yedekler bu temizlikten etkilenmez. 16 Ekim 2026 günlük yedeği `lumispac_full_20261016.dump` oluşturuldu ve 99.031 bayt olarak doğrulandı.
3. **Yönetici sistem sağlığı — geçti.** Ayarlar → Hakkında altında veritabanı bağlantısı/bütünlüğü, şema ve satır/tablo sayısı, en yeni tam yedek yaşı ve disk boş alanı görünür. `/api/system/health` yalnız sistem yöneticisine açıktır; bağlantı hatasında veriyi açmak yerine uyarı verir.
4. **İş verisi mutabakatı — geçti (güncel v20 kontrolü).** 2026-10-17 canlı PostgreSQL salt okunur mutabakatı 23 ürün, 6 kullanıcı, 1 bayi, 4 sipariş/22 satır/2 tahsilat, 5 finans kaydı, 3 hammadde alımı, 12 üretim işi ve 12 depo kabulü raporladı. Sipariş toplam farkı 0; temel ilişkilerde sahipsiz kayıt 0; v20 şemasında 8 yabancı anahtar kısıtı var ve durum `ok`. Önceki FK eksikliği riski v20 migration ile giderildi.
5. **Yetki ve denetim E2E — geçti.** Gerçek PostgreSQL’in rastgele geçici şemasında teklif/sipariş, stok, satın alma/ödeme, finans ve üretim planı-başlatma-tamamlama-depo kabulü; departmanlar arası finans/üretim redleri ve `audit_events` kalıcılığı doğrulandı. Fixture veritabanı 42 tablo/112 satırda temizlendi.
6. **Kesinti ve yeniden bağlanma — geçti.** İzole küme durdurulunca sağlık kontrolü `warning`/bağlantısız duruma geçti; aynı uygulama süreci sunucu yeniden başladığında `ok` durumuna döndü. Yeni PostgreSQL bağlantı denemeleri varsayılan olarak 5 saniyede zaman aşımına uğrar; DSN’de açıkça verilen süre korunur.
7. **Performans, indeks ve ilişki kısıtları — geçti.** Siparişler, sipariş satırları/ödemeleri, üretim işleri, satın alma kalemleri, finans ve denetim tablolarındaki iş indeksleri incelendi; mevcut küçük veri hacminde fazladan indeks eklenmedi. v20 ile 8 foreign key kısıtı da doğrulandı; bu başlıktaki önceki eksiklik kapandı.
8. **Masaüstü kabul kontrolü — başlatma doğrulaması geçti.** UTF-8 BOM kodlamalı güncel başlatıcı Windows PowerShell ile gerçek OneDrive yolunu çözüyor; 5001 sunucusunu PostgreSQL kipinde başlattı, LUMISPAC Chrome profilini açtı, ana sayfa ve güncel senaryo JavaScript'i HTTP 200 verdi ve Chrome başlangıç devrinden sonra sunucu portu açık kaldı. Altı rolün canlı ekran matrisi saha akışı notlarında ayrıca doğrulandı; bu açılışta tarayıcı konsolu ayrıca incelenmedi.
9. **Sürüm geri alma — prosedür hazır.** Her kod değişikliğinden önce dosya kopyaları `yedekler_v2` altında saklandı; canlı DB için doğrulanmış dump ve aktarım öncesi SQLite kopyası korunuyor. Güncelleme öncesi yeni dump al, önce geçici kümeye yükle ve kontrol et. Geri yükleme canlı DB’de bütün kayıtları yedek tarihine döndürür; yalnızca uygulama durdurulup doğru hedef/son yedek doğrulandıktan sonra bakım işlemi olarak yürütülmeli. Güncel yedek: `%LOCALAPPDATA%\LUMISPAC\backups\lumispac_full_20261016.dump`.
10. **Çok bilgisayarlı büyüme planı — hazır, ağ açılmadı.** Tek bilgisayar kullanımında PostgreSQL yalnız localhost’ta kalır. Birden fazla bilgisayar gerektiğinde ayrı sunucu/host, TLS, ayrı en az yetkili uygulama rolü, yalnız fabrika LAN’ına firewall izni, ACL korumalı sır dağıtımı, uzaktan yedek hedefi ve eşzamanlı yazma yük testi birlikte planlanmalı. Bu adımlar yapılmadan 5432 dış ağa açılmamalı.

## Günlük kullanma ve sorun giderme

- Başlatıcı uygulama sunucusunu ve tarayıcı penceresini birlikte yönetir. Sunucu hata verirse önce `%LOCALAPPDATA%\LUMISPAC\logs\server-error.log` ve `lumispac_hata.log` incelenir.
- Yönetici, Ayarlar → Hakkında → Sistem sağlığı bölümünden durum ve son yedeği yenileyebilir.
- Salt okunur veri mutabakatı: proje kökünde `python tools/postgres_reconcile.py` (PostgreSQL DSN ve PGPASSFILE ortamı gerekir).
- Geri yükleme provası canlıya uygulanmaz; benzersiz geçici PostgreSQL kümesinde yapılır. Her prova sonunda küme durdurulur ve yalnızca işaretli geçici dizin kaldırılır.
- Açılışta günlük yedek alınır; uygulama bir günden uzun kapalı kalırsa kapalı olduğu sırada yedek üretilemez. Yeniden açılışta günlük yedek kontrolü yapılır.

## Mutabakat takibi

Canlı sipariş kimliği `TEST-DEMO-ORDER-CHECK` görünüyor. Tutarlar tutarlı ve bağlı kayıtları sağlam; bu kaydın iş amaçlı mı test amaçlı mı olduğu veritabanından anlaşılamadığı için silinmedi veya değiştirilmedi. Yönetici, iş kayıtları ekranından iş anlamını teyit edebilir.

## 2026-10-17 son migration doğrulaması

Bu bölüm yukarıdaki eski şema 18 / FK yok bilgilerini günceller. Canlı test veritabanı şema v20'ye yükseltildi; migration öncesi dump doğrulandı: `%LOCALAPPDATA%\LUMISPAC\backups\lumispac_before_schema_v20_20261017.dump` (SHA-256 `3dfcd1afbeed59c1a0e27a60618681116bae18ce036dea32d5fd48f1ecd44c71`). Migration sonrası 8 foreign key var; salt okunur mutabakat `ok`, sahipsiz ilişki ve sipariş toplam farkı yok, depo bütünlük kontrolü `ok` (1.076 satır). İzole PostgreSQL siparişten teslimata E2E senaryosu geçti. `tools/check_quality.py`, arşivlenmiş `work/backups/` içindeki eski kod ve testleri hariç tutacak şekilde düzeltildi; standart kalite komutu **364 test**, Python 112 dosya, JavaScript 32 dosya ve depolama sınırı denetimlerini başarıyla tamamladı.

## 2026-10-17 — gerçek kaynak doğrulaması ve rol ekranları

Bu ek, yukarıdaki 456/364 test sayısı ile “5001 kapalı” kaydını günceller. OneDrive gerçek kaynak ağacının yedek ve kullanıcı verileri dışarıda tutulan izole kopyasında, gerekli `lumispac_users.json` rol fixture'ı ile standart kalite kapısı **457/457 test** geçti; Python 115, JavaScript 32 sözdizimi ve depolama sınırı kontrolü başarılı. `LUMISPAC_STORAGE=json` kullanıldı; testler canlı PostgreSQL verisine yazmadı. Yerel mevcut uygulama sekmesinde yönetici, satış, finans, üretim, depo ve satın alma hesaplarıyla rol bazlı ekran kontrolü yapıldı; test sonunda Finans oturumu geri yüklendi. Yönetici/Finans kâr-marj-kur verisini görüyor, Satış/Üretim/Depo/Satın Alma hesaplarında bu şirket geneli hassas alanlar ve ilgili menüler görünmüyor. PostgreSQL canlı şeması 20, 8 FK, mutabakat `ok`, sahipsiz kayıt ve sipariş toplam farkı 0, belge bütünlüğü `ok` olarak kaldı. PP test alımı ve yinelenen taslak siparişler korunuyor; PDF blob URL'si tarayıcı güvenlik politikası nedeniyle görsel olarak incelenemedi.

## 2026-10-17 — satış katalog varyant koruması ve son kalite kapısı

Satış sipariş seçicisinde tam aynı izinli alanlara sahip (ürün adı, koli içi adet, satış fiyatı) birden fazla SKU oluşursa, ürün kodu veya gramajı açmadan tarafsız “Seçenek 1/2” ayrımı eklendi; etiket sepette korunuyor. Güncel canlı katalogda bu üç alanı tamamen aynı olan çift bulunmuyor; var olan aynı adlı ürünler fiyatla ayrışıyor, fiyatı olmayan seçenekler devre dışı. Gerçek uygulama sayfası yeni script cache anahtarıyla yenilendi ve Ahmet hesabında ürün listesi okundu; sepet boş kaldı, sipariş oluşturulmadı. İzole kopyada Node davranış kontrolü ve `tests/test_ui_privacy.py` 39/39 geçti; tam kalite kapısı **458/458**, Python 115 / JavaScript 32 / depolama sınırı kontrolleri başarılı. `cart.js`, `index.html` ve regresyon testi OneDrive gerçek kaynakta yedeklenip hash doğrulamasıyla güncellendi. Bu UI değişikliği PostgreSQL şemasını veya iş verisini değiştirmedi; v20/8 FK/önceki mutabakat sonucu etkilenmedi. PP-TEST, yinelenen taslaklar ve canlı PDF blob incelemesi açık iş olarak kaldı.

## 2026-10-17 — sağlık göstergesinde bağlantı ve bütünlük

Eski yönetici kartı `connected` değerini bütünlük denetiminin `ok` sonucundan türetiyordu; adaptörün `ok` alanı olmayan eski/alternatif yanıtlarda bağlantı var olduğu halde sorun gösterebilirdi. `lumispac_app.py` bağlantıyı açık `connected` alanından, yoksa bütünlük etiketinden belirliyor; `postgres_store.integrity_check()` bağlantı başarılıysa `connected=true` döndürüyor. Yönetici kartı bağlantı ile bütünlüğü ayrı metin olarak gösteriyor ve geçersiz belge kimliklerini kaçışlanmış biçimde sunuyor. Regresyon eklendi; izole gerçek kaynakta kalite kapısı **459/459** geçti. Beş güncel dosya gerçek kaynakta önceden yedeklenip SHA-256 ile doğrulandı.

Canlı PostgreSQL salt okunur mutabakatı şema v20, 43 tablo, 1.085 satır, 8 FK ve `ok` bütünlük verdi; sahipsiz ilişki ve sipariş toplam farkı yok. Uygulama sunucusu 5001'de doğrulanmış LUMISPAC süreci olarak yeniden başlatıldı. Oturumsuz health API isteği beklenen 401 döndürdü. Tarayıcı otomasyonu yenileme sonrası ana sayfaya döndü ve Hakkında sekmesinin canlı görsel doğrulaması tamamlanamadı; bu teyit açık kalıyor. Canlı iş verisine dokunulmadı.

## 2026-10-17 — Canlı sağlık kartı son teyidi

Önceki paragraftaki görsel teyit açığı kapandı. Sunucu tam kaynak dosyasının mutlak yolu ile, boşlukları doğru alıntılayarak başlatıldı; 5001 portu ve ana sayfa HTTP 200 doğrulandı. Admin oturumuyla sağlık API'si `status=ok`, `connected=true`, `integrity=ok`, schema v20, 1.089 satır/43 tablo döndürdü. Admin Hakkında kartında “Genel durum: Sağlıklı / Bağlantı: Bağlı / Bütünlük: Doğrulandı” canlı ekranda görüldü. Son salt okunur mutabakat: 433 audit olayı, 8 FK, sahipsiz kayıt 0, sipariş toplam farkı 0; `status=ok`. Oturumsuz erişim 401 olarak korundu.

## 2026-10-17 — Başlatıcı kaynak yolu

`LUMISPAC_Baslat.ps1` göreli `lumispac_app.py` argümanı yerine proje kökünden oluşturulmuş tam ve tırnaklı dosya yolunu kullanıyor. Önceki sürüm `.before-absolute-launch-20261017.bak` ile korunuyor. PowerShell Parser hatasız; argüman çözümlenmesi OneDrive gerçek kaynak dosyasını gösteriyor. Canlı uygulama zaten güncel kaynakla ayaktaydı; masaüstü başlatıcısını ayrıca çalıştırıp fazladan Chrome penceresi açılmadı.

## 2026-10-17 — Kur yedeğine geçiş nedeninin görünür kılınması

- [x] Birincil sağlayıcı önceliği korundu; yedek kaynak yalnızca ana kaynak hata/karantina/geçersiz kur durumunda seçiliyor ve sonraki sorgularda ana sağlayıcı yeniden deneniyor.
- [x] Yedek kullanıldığında durum çipi artık kaynak adını ve kısa nedeni gösteriyor; üzerine gelince otomatik geri dönüş davranışını açıklıyor. Neden metni kullanıcıya teknik hata ayrıntısı sızdırmayan sınırlı kategorilerden üretiliyor.
- [x] Kaynak değişimi alanı cache'te korunuyor. İzole gerçek kaynakta 459/459 regresyon, Python 115 dosya, JavaScript 32 dosya ve depolama sınırı kontrolleri başarılı.
- [x] 5001'deki LUMISPAC sunucusu PostgreSQL yapılandırmasıyla yeniden başlatıldı; ana sayfa ve güncellenmiş senaryo JavaScript'i HTTP 200 verdi. İş kayıtlarına dokunulmadı.
- [ ] Canlı PDF blob önizlemesinin görsel teyidi hâlâ tarayıcı güvenlik sınırına takılıyor; bu sınırı aşmadan kapatılamıyor.
- [ ] PP test alımı ile SIP-2026-0001/-0002 taslakları korundu; silme/ters kayıt için henüz güvenli, kayıt bazlı işlem yapılmadı.

## 2026-10-17 — Güncel yol haritası mutabakatı

- Faz 4 ve 7'de tarihsel olarak yazan “foreign key yok/açık” durumu güncel değildir; canlı şema v20'de 8 FK, sıfır sahipsiz kayıt ve sıfır sipariş toplam farkı doğrulandı. Bu risk kapandı.
- Güncel canlı mutabakat `tools/postgres_reconcile.py`: 23 ürün, 6 kullanıcı, 1 bayi, 4 sipariş, 22 sipariş satırı, 2 tahsilat, 5 finans kaydı, 3 satın alma, 12 üretim işi/12 depo kabulü, 433 denetim olayı; 43 tablo ve 1.089 satır. `status=ok`.
- Kaynak yedeğine geçiş açıklaması gerçek kaynakta uygulandı; 459/459 kalite kapısı, 115 Python / 32 JavaScript sözdizimi ve depolama sınırı denetimleri geçti. 5001 sunucusu PostgreSQL ile yeniden başlatıldı; ana sayfa ve güncel senaryo JS HTTP 200 verdi.
- Masaüstü başlatıcısı kaynak kodu Windows PowerShell'de UTF-8 BOM olmadan kaydedildiğinde Türkçe OneDrive yolunu bozuk okuyordu; doğru BOM ve başlangıç sonrası sunucuyu erken durdurmama düzeltmeleri yapıldı. Windows PowerShell yolu `Test-Path=True` doğruladı; gerçek başlatıcı doğru kaynakla server 23848'i açtı, ana sayfa/senaryo JS HTTP 200 verdi ve Chrome profilinde 7 süreçle port açık kaldı. Başlatıcı hata günlüklemesi de eklendi; masaüstü başlatma doğrulaması geçti.
- Canlı PDF blob görseli güvenlik kısıtı nedeniyle açık; PP alımı ve SIP-2026-0001/-0002 taslakları veri kaybı riski nedeniyle korunuyor.
## 2026-10-17 — Masaüstü başlatıcı yaşam döngüsü doğrulaması

- [x] `.ps1` dosyası UTF-8 BOM ile kaydedildi; Windows PowerShell Türkçe OneDrive proje yolunu doğru okuyor ve `lumispac_app.py` dosyasını buluyor.
- [x] Chrome uygulama başlatma komutu kısa ömürlü/başka Chrome sürecine devredildiğinde, sunucunun `finally` bloğunda erken durmaması sağlandı. Başlatıcı başarıyla bağlanan sunucuyu açık bırakıyor; başarısız ilk açılışta sunucuyu temizliyor. Başlatıcı hataları yerel loga yazılıyor.
- [x] Gerçek başlatıcı açılışında PostgreSQL kipindeki doğru kaynak süreç (PID 23848), ana sayfa HTTP 200, güncel senaryo JS HTTP 200 ve Chrome profilinin 7 süreçlik ağacı doğrulandı; 5001 portu açık kaldı. İş verisi değişmedi.
- [x] PowerShell Parser başarılı; gerçek kaynak ve çalışma kopyasındaki başlatıcı SHA-256 değerleri eşleşiyor.

## 2026-10-17 — Sipariş durum görünümü ve irsaliye PDF akışı

- [x] Sipariş tablosundaki durum açıklamaları dar kolonlarda taşma yapmasın diye durum alanı esnek genişlik ve güvenli metin kaydırma ile düzenlendi.
- [x] Sevk yetkili kullanıcı, hazırlanan sipariş için irsaliye PDF'si oluşturmadan önce teslimat tarihi, plaka, şoför ve telefon bilgilerini formda girebilir. Değerler yalnız PDF önizleme/indirme isteğinde kullanılır, siparişe kaydedilmez. Sunucu sevk yazma yetkisini, sipariş sahibi erişimini ve sipariş durumunu doğrular.
- [x] PDF uçları hem bellek akışı hem bayt dönüşünü destekliyor; belge üreticisinin BytesIO çıktısı API katmanında tekrar hatalı sarmalanmıyor.
- [x] Hedefli testler 64/64, tam test paketi 460/460 geçti. Canlı sipariş verisi değiştirilmedi.

- [x] Önizleme-only irsaliye POST isteği iş kaydı değiştirmediği için denetim günlüğünde mutasyon gibi yazılmıyor.


## 2026-10-17 — Test verisi sıfırlama (ürün kartları korundu)

- Tam PostgreSQL yedeği alındı ve pg_restore --list ile doğrulandı: work\backups\before-products-only-reset-20261017-185457\lumispac-before-reset.dump; SHA-256 2A60259796636F12AA5354E38FD1DAB9517F1815D5E93B926502C4D7840F82A5 (569 arşiv girdisi).
- Kullanıcının talebiyle tüm test/iş kayıtları temizlendi. 23 ürün kartı ve ürün ana alanları değişmeden korundu; ürün stok miktarları 0 yapıldı. Tek dmin yöneticisi, sistem departman/yetki yapılandırması, uygulama ayarları ve şema v20 korundu.
- Son mutabakat: ürün 23; kullanıcı 1; bayi, sipariş/satır/ödeme/teklif, finans, hammadde/alım, üretim işi/kabul ve denetim kaydı 0. Sekiz FK, sahipsiz ilişki 0, sipariş toplam farkı 0; status=ok.
- LUMISPAC sunucusu PostgreSQL kipinde yeniden başlatıldı; http://127.0.0.1:5001/ HTTP 200 verdi. İş verisi için yeniden test başlangıç noktası hazır.

