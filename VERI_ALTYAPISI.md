# LUMISPAC veri altyapısı

## Tek bilgisayar kurulumu

LUMISPAC şu anda Windows'taki yerel PostgreSQL 18 sunucusunu kullanır. Veritabanı `lumispac`, uygulama rolü `lumispac_app`, bağlantı adresi `127.0.0.1:5432`'dir. Masaüstü başlatıcısı `LUMISPAC_STORAGE=postgresql` ve parola içermeyen DSN ile açılır; uygulama parolasını yalnızca kullanıcı hesabına ACL ile sınırlandırılmış `%LOCALAPPDATA%\LUMISPAC\postgresql\pgpass.conf` dosyasından alır. Parola kaynak koda, komut satırına veya günlüklere konmaz. Uygulama yalnızca `127.0.0.1` adresinden dinler.

SQLite veritabanı `%LOCALAPPDATA%\LUMISPAC\data\lumispac.sqlite3` konumunda korunur; PostgreSQL aktarımından önce alınan kopya `%LOCALAPPDATA%\LUMISPAC\backups` altındadır. SQLite artık aktif çalışma kaynağı değildir; geri dönüş ve karşılaştırma için korunmaktadır. Başka bilgisayarlardan eşzamanlı kullanım gerekirse PostgreSQL sunucusunun ağ güvenliği ayrıca yapılandırılmalıdır.

## İlişkisel geçiş durumu

İş verileri için ilişkisel SQLite tabloları kaynak olacak şekilde Faz 20’nin kod geçişi tamamlandı. v16 açılış migration’ı, `data_documents` köprüsünü kapatmadan önce bilinen her iş belgesinin SQL projeksiyonunu payload düzeyinde karşılaştırır; hata varsa migration durur ve köprü korunur. Bilinmeyen eski yardımcı belgeler özeti doğrulanarak salt-okunur `legacy_document_archive` tablosuna alınır. Tam parite başarılı olduğunda `data_documents` kaldırılır. Şema yükseltmesinde eski aynaların SQL tablolarını boşaltmasını önlemek için ilk projeksiyon yalnızca ilişkisel kaynak işareti henüz yoksa yapılır. v17 sipariş ödeme sırasını açık `position` alanında korur; v18 iptal/tarih rapor bayraklarını merkezi kurallardan üretip rapor sorgusundaki yerel SQLite fonksiyonlarını kaldırır. Canlı SQLite verisi 16 Ekim 2026'da PostgreSQL 18'e aktarılmıştır. Aktarım öncesi SQLite yedeği ve aktarım sonrası tablo bazında satır/içerik özeti karşılaştırması tamamlanmıştır. SQLite kaynak ve yedek dosyaları silinmemiştir.

Depo seçimi için `storage_adapter.py` ortak arayüzü eklendi; servisler ve JSON yardımcıları veritabanı sürücüsünü doğrudan seçmiyor. Yedek/geri yükleme de aktif adaptöre yönlendiriliyor. PostgreSQL bağlantısı `LUMISPAC_DATABASE_URL` ortam değişkeninden alınır; parola kaynak koduna veya günlük kayıtlarına konmaz. Belgeler, günlükler ve yedekler `%LOCALAPPDATA%\LUMISPAC` altında tutulur. Masaüstü başlatıcısının varsayılanı PostgreSQL'dir. `postgres_store.py` ortak depo sözleşmesini sunar; PostgreSQL seçimi ancak sürücü yüklü, şema v18 aktarılmış ve ilişkisel kaynak işaretleri doğrulanmışsa açılır. Sunucu/driver/parite doğrulaması yapılmadan varsayılan backend değiştirilmez.

### PostgreSQL uyumluluk denetimi

İlk kod taramasında SQLite'a özel kullanımlar `sqlite_store.py` ve `db_migrations.py` içinde yoğunlaşıyor: `PRAGMA`/`sqlite_master` şema keşfi ve bütünlük sorguları, `BEGIN IMMEDIATE`, `INSERT OR REPLACE`, `AUTOINCREMENT`, eski şemada ödeme sırasına düşen `rowid` ve SQLite çevrimiçi yedekleme API'si. Servis/adaptör sözleşmesindeki `?` parametreleri de PostgreSQL sürücüsünün parametre biçimine çevrilmelidir. Bu nedenle yalnızca bir PostgreSQL bağlantı dizesi eklemek veya SQLite dosyasını sunucuya kopyalamak geçiş sayılmaz. Bu uyumluluk katmanı gerçek PostgreSQL 18 sunucusunda kullanıldı. v1-v18 şeması, canlı kayıt aktarımı ve satır içerik paritesi doğrulandı; sürücü, dialect, depo, migration ve transfer testleri kalite paketine dahildir. PostgreSQL API iş akışları ayrıca `tools/postgres_isolated_e2e.py` ile rastgele adlandırılan geçici bir şemada çalıştırılır; test sonunda bu şema kaldırılır. Yönetici ve satış oturumu, API okumaları ve temel sipariş/teklif/stok/satın alma/finans/üretim yazımları gerçek PostgreSQL 18 üzerinde doğrulanmıştır.

## Yedek ve geri yükleme

SQLite modundaki elle ve günlük yedekler, SQLite çevrimiçi yedekleme API'siyle alınan tam veritabanı kopyalarıdır. Yerleri `%LOCALAPPDATA%\LUMISPAC\backups` olur. Geri yükleme öncesi geçerli veritabanı ayrıca yedeklenir; geri yüklenecek dosya bütünlük kontrolünden geçmezse işlem reddedilir. Geri yükleme ürün, kullanıcı, sipariş, stok, finans, üretim, denetim ve diğer veritabanı belgelerinin tamamını etkiler.

Uygulamayı veya veritabanı dosyalarını OneDrive ile eşzamanlamayın. Başka bilgisayarlardan eş zamanlı kullanım gerekirse SQLite dosyasını ağ klasörüne koymak yerine merkezi sunucu veritabanına geçiş planlanmalıdır.

## Geliştirme/test

Uygulama başlatıcısı PostgreSQL'i seçer. Genel regresyon paketi JSON depolamasında, SQLite saklama/migration testleri ise kendi geçici veritabanlarında çalışır. Genel kalite paketi JSON modunda; SQLite migration/store ve PostgreSQL sürücü/depo testleri izole fixture'larda çalışır. Gerçek PostgreSQL iş akışı ayrı, disposable şema kullanan E2E aracıyla doğrulanır; üretim şemasına yazmaz. Çalışan uygulamanın verisini taşıma sırasında uygulama kapalı olmalıdır.

`tests/test_sqlite_app_e2e.py`, ayrı süreçte kendi geçici SQLite veri kökünde Flask uygulamasını açar; yönetici oturumuyla sipariş/finans yazımını ve temel modül API okumalarını, ayrıca saha satış oturumuyla sipariş sahipliğini ve finans alanı gizliliğini doğrular. Bu E2E senaryosu tüm test fixture'larının SQLite'a taşındığı anlamına gelmez; genel paket hâlâ JSON kipinde kalite kapısıdır.

SQLite E2E ayrıca oturum açmış yöneticiyle uygulamadaki parametresiz API GET yollarını otomatik tarar; beklenen yetki/parametre redleri kabul edilir, sunucu hataları testi düşürür. Bu tarama eski siparişlerde müşteri alanı eksik olduğunda sipariş Excel dışa aktarımının 500 vermesini yakaladı; dışa aktarma bu eski kayıt biçimine karşı dayanıklı hale getirildi.

Güncelleme öncesi tekrarlanabilir denetim için proje kökünde `python tools/check_quality.py` çalıştırılabilir. Gerçek PostgreSQL E2E için PowerShell'de `LUMISPAC_DATABASE_URL` ve `PGPASSFILE` ayarlanıp `python tools/postgres_isolated_e2e.py` çalıştırılır; araç canlı public şemaya dokunmadan geçici şemayı sonunda siler. Bu komut kaynak Python/JavaScript sözdizimini, tam regresyon paketini ve uygulama katmanında doğrudan SQLite importu yapılmadığını denetler; test süresi dosyaları geçici klasörde tutulur.

Canlı DB geçiş komutu `python tools/migrate_live_sqlite_v18.py` ile önce geçici kopyada prova edilir. Yalnız uygulama tamamen kapalıyken `python tools/migrate_live_sqlite_v18.py --apply` canlı geçişi başlatır; komut süreç/port kontrolü, kalıcı çevrimiçi yedek ve kaynak-yedek eşitliği doğrulanmadan yazmaya başlamaz. Başarısız doğrulamada yedek korunur ve işlem hata verir.


## Canlı SQLite geçiş kaydı (16 Ekim 2026)

Canlı veritabanı v13'ten v18'e geçiş aracının korumalı `--apply` akışıyla yükseltildi. Önce LUMISPAC başlatıcısı ve sunucusu kapatıldı; kalıcı v13 yedeğinin kaynakla eşitliği doğrulandı. Migration sonucu SQLite `integrity_check=ok`, 15/15 iş belgesi ilişkisel paritesi ve eski yardımcı belge arşivi doğrulandı. Yedek: `sqlite_v18_canli_oncesi_20261016_095711.sqlite3` (SHA-256: `1734d3be3ccda32aa53d543c1139a3f2a57d1b503574876b5ee6de09cf00ccde`). Bu SQLite v18 yedeği PostgreSQL aktarımı boyunca korunmuştur; PostgreSQL'e geçiş kaydı aşağıdadır.

### PostgreSQL fazının güncel durumu

`postgres_migrations.py` ortak v1–v18 şemasını ayrı transaction’larda uygular; migration sürüm ve ad geçmişi doğrulanır. `postgres_connection.py` qmark, catalog ve bağlantı uyumunu sağlar; `postgres_store.py` ortak ilişkisel sorgu sözleşmesini, fail-closed açılışı, arşiv/ilişkisel belge kontrollerini ve `pg_dump`/`pg_restore` yedeklerini sağlar. `tools/migrate_sqlite_to_postgres.py` varsayılan olarak salt-okunur prova yapar; uygulama kapalı, hedef boş ve kalıcı SQLite yedeği doğrulanmadan `--apply` yazmaz; aktarımda tüm tabloların kolon, satır ve içerik özetlerini karşılaştırır. `requirements-postgresql.txt` opsiyonel psycopg kurulumunu tanımlar.

PostgreSQL 18 servisi (5432) ve psycopg sürücüsü kurulu. `lumispac_app` rolü parola içermeyen DSN ile `%LOCALAPPDATA%\LUMISPAC\postgresql\pgpass.conf` üzerinden kimlik doğrular. 16 Ekim 2026 canlı aktarımı `mode=applied`, şema v18, 42 tablo/596 satır, `postgres_integrity=ok` ve kaynak-hedef bütün tablo içerik özeti eşleşmesiyle tamamlandı. Aktarım öncesi SQLite yedeği: `%LOCALAPPDATA%\LUMISPAC\backups\sqlite_postgresql_aktarim_oncesi_20261016_131758.sqlite3`. Son doğrulanmış PostgreSQL dump yedeği: `%LOCALAPPDATA%\LUMISPAC\backups\postgres_verified_20261016_133359.dump` (custom format; `pg_restore --list` doğrulaması başarılı). Kaynak SQLite dosyası korunuyor.

PostgreSQL bağlantı smoke kontrolü v18 şema, 7 kullanıcı, 26 ürün ve 1 sipariş okudu. Masaüstü PowerShell başlatıcısı ve Python launcher PostgreSQL'i seçiyor; uygulama `http://127.0.0.1:5001/` üzerinden HTTP 200 döndürdü. Başlatıcıların önceki kopyaları `yedekler_v2\postgres_launcher_before_20261016` içindedir. Genel regresyon testi JSON/SQLite izole fixture'ları kullanır; bunlar gerçek PostgreSQL üzerinde tüm modül CRUD işlemlerinin kanıtı değildir. PostgreSQL backend `tools/postgres_isolated_e2e.py` ile geçici şemada test edildi: aktarım 42 tablo/112 fixture satırında bütünlük kontrolünü geçti; teklif/sipariş/finans/stok/satın alma/ödeme akışları, üretim planı-başlatma-tamamlama-depo kabulü ve audit_events kalıcılığı doğrulandı. Finans rolünün üretim ekranına, üretim rolünün finans verisine erişimi reddedildi; API E2E çıkışı 0 oldu. Genel kalite kapısı 16 Ekim 2026'da 328 test, 106 Python sözdizimi ve 32 JavaScript sözdizimi kontrolüyle geçti. Geçiş aracındaki eksik `tempfile` importu, cursor üzerinden `executemany` çağrısı ve PostgreSQL JSON yol yönlendirmesi düzeltildi. Canlı yedekleme sırasında bulunan desteklenmeyen `pg_dump --exit-on-error` seçeneği kaldırıldı ve regresyon testi eklendi.

Geri yükleme güvenliği: `/api/restore`, geri yüklemeyi başlatmadan önce yeni tam yedeğin başarıyla oluşturulduğunu ve dosyanın mevcut olduğunu şart koşar; yedekleme başarısızsa 503 döner ve mevcut veriye dokunmaz. Bu davranış `tests/test_backups.py` ile doğrulandı.


## Günlük işletim

Günlük yedek, yönetici sağlık ekranı, geri yükleme provası ve 10 fazın sonuçları için POSTGRESQL_RUNBOOK.md dosyasına bakın.
