# API Yetki Kataloğu

Bu katalog `api/security.py` merkezi filtresi ve uç noktaların kendi rol/süreç kontrolleri birlikte okunarak hazırlanmıştır. Yeni bir `/api/...` rotası eklenince merkezi eşlemede tanımlanmadıysa istek **403** ile kapatılır. Olmayan rotalar normal **404** döner.

## Temel kurallar

- Modül seviyeleri: `okur` GET/HEAD, `yazar` POST/PATCH, `tam` DELETE. Yedek geri yükleme ve yönetici işlemleri için ayrıca `tam` ya da yönetici rolü gerekir.
- `siparis_sevk:yazar` sevkiyat alanlarını düzenleme ve sevk geçişi iznidir. Yönetici departman veya kullanıcı bazında bu izni verir; kullanıcı izni varsa departman ayarının önüne geçer.
- Sevkiyat alanlarını düzenleme ve `transition` içindeki `ship` eylemi, `siparisler:yazar` gereksiniminden bağımsız olarak yalnız `siparis_sevk:yazar` ile yetkilendirilir. Diğer sipariş işlemleri sipariş modül iznini kullanır.
- `yonetici_only`: yalnızca `yonetici` departmanı.
- `public`: oturum açmadan erişilebilir.
- `auth-only`: geçerli oturum gerekir.
- `satis` rolünde bayi, teklif ve sipariş liste/rapor/PDF verileri yalnızca `owner_user_id` oturum kullanıcısına ve aynı kullanıcıya atanmış bayiye bağlıysa görünür. Eşleşmeyen kayıt 404 gibi davranır.
- Yeni satış kayıtlarının sahibi istek gövdesinden değil oturumdan alınır. Eski kayıtta sahibi yoksa satış rolüne gösterilmez.

## Uç noktalar

| Yöntem | Yol | Modül / gereken işlem | Ek kural |
|---|---|---|---|
| POST | `/api/auth/login` | public | Başarısız giriş 401 |
| POST | `/api/auth/logout` | public | Varsa oturumu iptal eder |
| GET | `/api/auth/me` | auth-only | Kullanıcı/rol bilgisi |
| POST | `/api/auth/change-password` | auth-only | Eski parola doğrulanır; tüm oturumları kapatır |
| GET | `/api/auth/logs` | yonetici_only | — |
| POST | `/api/auth/logs/clear` | yonetici_only | 410; denetim geçmişi silinmez |
| GET | `/api/audit/logs` | yonetici_only | Arama, kullanıcı, işlem, tarih aralığı ve sayfalama filtreleri; yeni ve eski kayıtlar |
| GET | `/api/audit/export.csv` | yonetici_only | Aynı filtreler, CSV formül enjeksiyonu önlemi |
| POST | `/api/audit/undo/<id>` | yonetici_only | Yalnız bayi, ürün ve teklif değişiklikleri; sonradan değişmiş kaydı geri almaz; her deneme denetim izine yazılır |
| GET | `/api/users` | yonetici_only | — |
| POST | `/api/users` | yonetici_only | — |
| PATCH | `/api/users/<uid>` | yonetici_only | Devre dışı bırakınca oturumlar iptal |
| DELETE | `/api/users/<uid>` | yonetici_only | Son yönetici silinemez |
| POST | `/api/users/<uid>/reset-password` | yonetici_only | Hedef kullanıcının oturumları iptal |
| GET | `/api/departments` | yonetici_only | Finans ve stok modüllerini içerir |
| POST | `/api/departments` | yonetici_only | Geçersiz modül seviyesi `gormez` olur |
| PATCH | `/api/departments/<dep_id>` | yonetici_only | Yönetici sistem rolü değiştirilemez |
| DELETE | `/api/departments/<dep_id>` | yonetici_only | Sistem departmanı silinemez |
| GET | `/api/ownership/unassigned` | yonetici_only | Sahipliği tamamlanmamış kayıtları ve aktif satış kullanıcılarını listeler |
| GET | `/api/products` | urunler:okur | — |
| POST | `/api/products` | urunler:yazar | — |
| POST | `/api/seed` | urunler:yazar | — |
| GET | `/api/settings` | ayarlar:okur | — |
| POST | `/api/settings` | ayarlar:yazar | — |
| GET | `/api/rate` | urunler:okur | — |
| POST | `/api/rate/refresh` | urunler:yazar | — |
| GET | `/api/export/products` | urunler:okur | — |
| GET | `/api/orders` | siparisler:okur | Satış rolü yalnızca sahibi olduğu siparişleri görür |
| POST | `/api/orders` | siparisler:yazar | Yalnız satış veya yönetici; yeni kayıt daima Taslak başlar; satış yalnız atanmış bayisine |
| PATCH | `/api/orders/<oid>` | siparisler:yazar; yalnız sevkiyat alanları için `siparis_sevk:yazar` | Teslimat güncellemesi sipariş modül iznini ister; sevkiyat alanları Hazırlanıyor aşamasında sevk izniyle güncellenir |
| DELETE | `/api/orders/<oid>` | siparisler:tam + yönetici | Yalnız Taslak sipariş silinebilir |
| POST | `/api/orders/<oid>/transition` | siparisler:yazar; `ship` eylemi için bağımsız `siparis_sevk:yazar` | Sevk öncesi bakiye sıfır olmalı; onay ve stok hareketi tek idempotent geçiştir |
| POST | `/api/orders/<oid>/availability` | siparis_depo:yazar | Depo stok kontrolü; eksik miktar için tahmini tarih zorunlu, sonuç siparişe ve üretim kuyruğuna yazılır |
| GET | `/api/production/queue` | uretim:okur | Sadece sipariş kaynaklı ve üretim açığı bekleyen kayıtlar; `depo` da okur izniyle görebilir |
| POST | `/api/orders/<oid>/payments` | finans:yazar + muhasebe/yönetici | Taslak/iptal siparişe veya kalan bakiyeyi aşan tutara izin verilmez |
| PATCH | `/api/orders/<oid>/owner` | yonetici_only | Önce bayi aynı aktif satış kullanıcısına atanmış olmalı |
| GET | `/api/export/orders` | siparisler:okur | Satış rolü yalnız kendi siparişlerini dışa aktarır |
| POST | `/api/export/cart` | sepet:yazar | — |
| GET | `/api/quotes` | teklifler:okur | Satış rolü yalnız sahibi olduğu ve kendi bayisine bağlı teklifleri görür |
| POST | `/api/quotes` | teklifler:yazar | Satış rolü yalnız atanmış bayisine teklif oluşturur; sahip sunucudan atanır |
| DELETE | `/api/quotes/<qid>` | teklifler:tam + satış/yönetici | Satış rolü yalnız kendi teklifini silebilir |
| PATCH | `/api/quotes/<qid>/owner` | yonetici_only | Önce bağlı bayi aynı satış kullanıcısına atanmış olmalı |
| GET | `/api/dealers` | bayiler:okur | Satış rolü yalnız kendisine atanmış bayileri görür |
| POST | `/api/dealers` | bayiler:yazar + satış/yönetici | Satış rolü sadece kendi kayıtlarını günceller; listeden çıkarma silmez |
| DELETE | `/api/dealers/<did>` | bayiler:tam + satış/yönetici | Satış rolü yalnız kendi bayisini ve bağlı kayıt yoksa silebilir |
| PATCH | `/api/dealers/<did>/owner` | yonetici_only | Yalnız aktif satış kullanıcısına atanır |
| GET | `/api/dealers/<did>/panel` | bayiler:okur | Satış rolünde bayi ve sipariş sahipliği birlikte doğrulanır |
| GET | `/api/finans` | finans:okur | `raporlar` yetkisi finans erişimi vermez |
| POST | `/api/finans` | finans:yazar | — |
| DELETE | `/api/finans/<kid>` | finans:tam | — |
| GET | `/api/finans/kasa` | finans:okur | — |
| GET | `/api/finans/aylik` | finans:okur | — |
| GET | `/api/finans/kategoriler` | finans:okur | — |
| GET | `/api/finans/trend` | finans:okur | — |
| GET | `/api/finans/ozet-kategori` | finans:okur | — |
| GET | `/api/stok` | stok:okur | `siparisler` yetkisi stok erişimi vermez |
| POST | `/api/stok` | stok:yazar | — |
| DELETE | `/api/stok/<hid>` | stok:tam | — |
| GET | `/api/stok/kalan` | stok:okur | — |
| GET | `/api/stok/kritik` | stok:okur | — |
| GET | `/api/stok/ozet` | stok:okur | — |
| POST | `/api/stok/esik` | stok:yazar | — |
| GET | `/api/hesap/urunler-stok` | urunler:okur | Ürün liste ekranının ortak stok görünümü |
| GET | `/api/hesap/urun/<kod>/stok` | stok:okur | — |
| GET | `/api/hesap/stok-ozet` | stok:okur | — |
| GET | `/api/hesap/kritik-stok` | stok:okur | — |
| GET | `/api/hesap/dashboard` | genel_bakis:okur | Satış rolüne açık bayi/sipariş özeti; şirket geneli maliyet, kâr, marj ve kritik stok alanları API yanıtından çıkarılır |
| GET | `/api/benim/dashboard` | genel_bakis:okur | Profil ve aktivite yalnız oturum kullanıcısına aittir. Kartlar ilgili `siparisler`, `teklifler`, `bayiler`, `stok`, `uretim`, `urunler`, `raporlar` veya `finans` okuma izniyle sunulur; satış metriklerinde açık bayi ve kayıt sahipliği birlikte doğrulanır. |
| GET | `/api/reports/overview` | raporlar:okur | Satış rolünde veri sahibi filtreleri uygulanır |
| GET | `/api/reports/cost` | kar_maliyet:okur | Yalnız sistem yöneticisi ve finans |
| GET | `/api/reports/profitability` | kar_maliyet:okur | Yalnız sistem yöneticisi ve finans |
| GET | `/api/reports/sensitivity` | kar_maliyet:okur | Yalnız sistem yöneticisi ve finans |
| GET | `/api/reports/trend` | raporlar:okur | Satış rolünde veri sahibi filtreleri uygulanır |
| GET | `/api/reports/dealers` | raporlar:okur | Satış rolünde veri sahibi filtreleri uygulanır |
| GET | `/api/reports/abc` | raporlar:okur | `baz=kar` için ayrıca kar_maliyet:okur; diğer ölçütler rapor iznini kullanır |
| GET | `/api/reports/shipping` | raporlar:okur | Satış rolünde veri sahibi filtreleri uygulanır |
| GET | `/api/reports/target-margin` | kar_maliyet:okur | Yalnız sistem yöneticisi ve finans |
| POST | `/api/reports/simulator` | raporlar:yazar | — |
| GET | `/api/reports/cost-history` | kar_maliyet:okur | Yalnız sistem yöneticisi ve finans |
| GET | `/api/reports/target-alert` | kar_maliyet:okur | Yalnız sistem yöneticisi ve finans |
| GET | `/api/reports/price-suggestion` | kar_maliyet:okur | Yalnız sistem yöneticisi ve finans |
| GET | `/api/reports/projection` | raporlar:okur | Satış rolünde veri sahibi filtreleri uygulanır |
| GET | `/api/reports/anomaly` | kar_maliyet:okur | Yalnız sistem yöneticisi ve finans |
| GET | `/api/reports/customer-segments` | raporlar:okur | Satış rolünde veri sahibi filtreleri uygulanır |
| GET | `/api/reports/shipping-calendar` | raporlar:okur | Satış rolünde veri sahibi filtreleri uygulanır |
| GET | `/api/reports/stock-forecast` | raporlar:okur | Satış rolünde veri sahibi filtreleri uygulanır |
| GET | `/api/reports/quote-tracking` | raporlar:okur | Satış rolünde veri sahibi filtreleri uygulanır |
| GET | `/api/reports/comparison` | raporlar:okur | Satış rolünde veri sahibi filtreleri uygulanır |
| GET | `/api/reports/category` | raporlar:okur | Satış rolünde veri sahibi filtreleri uygulanır |
| GET | `/api/reports/weight-analysis` | kar_maliyet:okur | Yalnız sistem yöneticisi ve finans |
| GET | `/api/reports/product-lifecycle` | raporlar:okur | Satış rolünde veri sahibi filtreleri uygulanır |
| GET | `/api/reports/profit-loss` | kar_maliyet:okur | Yalnız sistem yöneticisi ve finans |
| GET | `/api/reports/ai-forecast` | raporlar:okur | Satış rolünde veri sahibi filtreleri uygulanır |
| GET | `/api/reports/export` | disa_aktar + kar_maliyet:okur | Yalnız sistem yöneticisi ve finans |
| GET | `/api/notifications` | raporlar:okur | Satış rolünde veri sahibi filtreleri uygulanır |
| GET | `/api/sources/health` | raporlar:okur | — |
| GET | `/api/errors/recent` | yonetici_only | — |
| GET | `/api/pdf/order/<oid>` | siparisler:okur | Satış rolü sahiplik + bayi sahipliği doğrular |
| GET | `/api/pdf/waybill/<oid>` | siparisler:okur | Satış rolü sahiplik + bayi sahipliği doğrular |
| GET | `/api/pdf/invoice/<oid>` | siparisler:okur | Satış rolü sahiplik + bayi sahipliği doğrular |
| GET | `/api/pdf/quote/<qid>` | teklifler:okur | Satış rolü sahiplik + bayi sahipliği doğrular |
| GET | `/api/help/categories` | public | — |
| GET | `/api/help/topics` | public | — |
| GET | `/api/help/topic/<slug>` | genel_bakis:okur | — |
| GET | `/api/help/tour-seen` | genel_bakis:okur | — |
| POST | `/api/help/tour-seen` | genel_bakis:yazar | — |
| POST | `/api/help/tour-reset` | genel_bakis:yazar | — |
| POST | `/api/backups` | ayarlar:yazar | — |
| GET | `/api/backups` | ayarlar:okur | — |
| POST | `/api/restore` | ayarlar:tam | — |

## Hammadde ve satın alma API'leri

| Yöntem | Yol | Modül / gereken işlem | Ek kural |
|---|---|---|---|
| GET, POST | `/api/raw-materials` | `hammaddeler:okur/yazar` | Birim KG; PET, PP ve diğer hammadde kayıtları |
| PATCH | `/api/raw-materials/<material_id>` | `hammaddeler:yazar` | Fiyat/katalog güncelleme |
| GET, POST | `/api/raw-materials/suppliers` | `satinalma:okur/yazar` | Tedarikçi bayi kayıtlarından ayrıdır |
| GET, POST, PATCH | `/api/raw-materials/purchases[/*]` | `satinalma:okur/yazar` | Taslak, satırlar, gönderim ve belge eki |
| DELETE | `/api/raw-materials/purchases/<id>` | `satinalma:tam` | Yalnız ödemesiz taslak veya reddedilmiş belge; silme geçmişe kaydedilir |
| GET | `/api/raw-materials/purchases/<id>/payments` | `satinalma_odeme:okur` | Ödeme hareketleri ve toplam/ödenen/kalan/durum özeti |
| POST | `/api/raw-materials/purchases/<id>/payments` | `satinalma_odeme:yazar` | Finans yetkilisi manuel kayıt ekler; idempotency key zorunlu, güncelleme/silme rotası yok |
| POST | `/api/raw-materials/purchases/<id>/submit` | `satinalma:yazar` | Sunucu %100 ödemeyi doğrular, sonra depo kabul kuyruğuna gönderir |
| GET | `/api/raw-materials/receipts` | `hammadde_depo:okur` | Bekleyen satın alma kabulleri |
| PATCH | `/api/raw-materials/purchases/<id>/receipt` | `hammadde_depo:yazar` | Tam kabul veya gerekçeli ret; kabul stoğa bir kez yansır |
| POST, GET | `/api/raw-materials/purchases/<id>/document` | `satinalma:yazar/okur` | Özel belge klasörü, doğrulanmış dosya adı; indirme oturum ve yetki ister |
| GET | `/api/raw-materials/recipes` | `receteler:okur` | Ürün başına kullanıcı tanımlı KG/koli reçetesi |
| PUT | `/api/raw-materials/recipes/<product_code>` | `receteler:yazar` | Reçete yoksa üretim otomatik hammadde düşmez |

API eşlemesinde tanımsız yollar merkezi güvenlik filtresinde kapalıdır. `satinalma_odeme` modülünde yönetici tam, muhasebe yazar, diğer roller kapalı başlar. Ödeme kaydı yalnız yerel muhasebe hareketidir; banka/ödeme servisi çağrılmaz. Döviz ödemesinde kur, kur tarihi ve kaynağı kullanıcı tarafından kaydedilir; oran "1 ödeme para birimi = X satın alma para birimi" yönündedir. Canlı kur kullanıldığı iddia edilmez. Eski para birimi alanı olmayan alımlar tarihsel varsayılan olarak TL ve ödemesi yok kabul edilir; bekleyen eski kayıt ödeme kapanmadan depoya görünmez/kabul edilmez.

Denetim API'si yalnız yöneticiye açıktır. `POST /api/auth/logs/clear` eski istemciler için korunur ancak 410 döndürür; log silme/temizleme yapılmaz. Yeni mutasyon kayıtları `lumispac_audit.json` dosyasına atomik, eklemeli yazılır. Yalnız kullanıcı kimliği/adı, zaman, HTTP yöntemi/yolu ve sonuç kodu saklanır; istek gövdesi, başlıklar, IP, parola, oturum anahtarı ve ödeme alanları kaydedilmez. Audit yazımı başarısız olursa iş API'si `AUDIT_WRITE_FAILED` ve `retry_safe: false` ile 500 döndürür; işlem tamamlanmış olabileceği için istemciye önce kaydı kontrol etmesi söylenir. Eski `lumispac_users.json` log satırları yeni yönetici listesi ve CSV'de normalize edilerek gösterilir; kişisel dashboard yalnız oturum kullanıcısının kayıtlarını döndürür.

Geri alma günlüğü yalnızca bayi, ürün ve teklif kayıtlarını kapsar. Düzenlemelerde sadece değişen alanların önceki değerleri, silmelerde kaydı geri yüklemek için gereken önceki kayıt tutulur. Sonraki kayıt içeriği yerine çakışma denetimi için SHA-256 parmak izi saklanır. Parola, oturum, token, kimlik doğrulama ve hash alanları günlüğe alınmaz. Denetim ekranındaki düğme yöneticiye özeldir; kayıt işlemden sonra değiştiyse çakışma nedeniyle geri alma reddedilir. Bir geri alma başarılı/başarısız API işlemi olarak yeni denetim olayı üretir. Sipariş, stok, üretim, satın alma ve finans kayıtları bu ilk sürümün kapsamı dışındadır.

## Sipariş iş akışı

| İşlem | Rol | İzin verilen geçiş / koşul |
|---|---|---|
| Sipariş oluşturma | Satış, yönetici | Yeni sipariş daima `Taslak`; satış sadece atanmış bayisine |
| Onaylama | Yönetici | Önce depo denetiminde `sevkiyata_hazir` olmalı; geçiş anında mevcut stok tekrar doğrulanır, sonra `Taslak → Onaylandı` ve stok çıkışı tek işlem akışında yapılır |
| Hazırlama | Depo, yönetici | `Onaylandı → Hazırlanıyor` |
| Sevk | `siparis_sevk:yazar` izni olan kullanıcı | `Hazırlanıyor → Sevk edildi`; plaka/şoför zorunlu, ödeme bakiyesi kapanmış olmalı. Vadesi ileri tarihli olsa da muhasebenin kabul ettiği çek ödenmiş sayılır |
| Teslim | Depo, yönetici | `Sevk edildi → Teslim edildi` |
| İptal | Satış, yönetici | Satış sadece kendi taslağını; yönetici taslak/onaylı/hazırlanan siparişi iptal eder; stok onaylı siparişte geri alınır |
| Yeniden açma | Yönetici | Sadece iptal edilmiş sipariş gerekçe ile Taslak'a alınır; eski depo uygunluğu sıfırlanır ve yeniden kontrol gerekir |
| Ödeme | Muhasebe, yönetici | Sipariş Taslak/İptal olamaz; tutar kalan bakiyeyi aşamaz |
| Silme | Yönetici | Sadece Taslak sipariş; ekran diğer durumlarda silme düğmesi göstermez |

## Sahipliği olmayan tarihsel veriler

Sahibi bulunmayan bayi/teklif/sipariş hiçbir satış kullanıcısına otomatik atanmaz ve satış listesinden gizli kalır. Yönetici ekranındaki **Geçmiş Kayıt Sahipliği** paneli kayıtları gösterir. Önce bayiyi gerçekten yöneten satış kullanıcısına atayın; sonra o bayiye bağlı teklif ve siparişleri aynı kullanıcıya aktarın. Bağı doğrulanamıyorsa kayıt atanmadan kalır. Atamalar `/api/dealers/<did>/owner`, `/api/quotes/<qid>/owner` ve `/api/orders/<oid>/owner` ile yapılır; yalnız aktif `satis` kullanıcısı hedeflenebilir.

## Sipariş ve stok tutarlılığı

Sipariş onaylama ve stok hareketleri `get_lock()` altında yürür. Aynı sipariş geçişinin stok hareketleri `idempotency_key` ile tekilleştirilir. Stok yazımı başarısızsa onay/iptal durumu kaydedilmez; sipariş durumu yazımı başarısız olursa o geçişte eklenen stok hareketleri geri alınır. Tekrarlanan geçiş geçersiz durum kuralıyla reddedilir ve stoğu ikinci kez değiştirmez.

Depo uygunluk denetimi `siparis_depo:yazar` ile ayrıca sınırlandırılır (varsayılan yalnız yönetici ve depo). Katalogdaki stok hareketi olmayan ürünü 0 mevcut stok sayar. Sipariş yeterliyse `sevkiyata_hazir`, açık varsa miktarları ve tahmini tarihiyle `uretim_bekliyor` olarak işaretler. Sipariş kaydı ve üretim kuyruğu aynı sipariş JSON belgesinde saklanır; tarihsel siparişlere alan eklemek gerekmez. Yeni `uretim` modülü eski departmanlara güvenli varsayılanla eklenir (yönetici tam, üretim yazar, depo okur, diğerleri görmez).

## Yetki yönetimi, finansal gizlilik ve kritik onaylar (16 Ekim 2026)

- `kar_maliyet` şirket geneli maliyet, kâr, marj, zarar ve fiyat duyarlılığı gibi hassas alanları korur. Sabit gizlilik kuralı gereği yalnız yönetici ve finans (`muhasebe`/`finans`) departmanında açılabilir; departman veya kişi istisnası bu sınırı aşamaz. Yetkisiz API yanıtlarından maliyet girdileri ve sonuçları sunucu tarafında ayıklanır; maliyet raporu, menüsü, ekran hesaplaması ve Excel alanları gizlenir. Satış tutarı/cirosu korunur. Finans etkisi olmayan kullanıcılar maliyet hesabı belirleyen ayarları da değiştiremez.
- `disa_aktar` dışa aktarmayı ayrı izinle sınırlar; görüntüleme izni otomatik olarak Excel/CSV indirme izni vermez.
- Departman profilleri (`satis`, `uretim`, `depo`, `finans`) yeni ve mevcut departmanlar için başlangıç şablonudur. Yönetici profili değiştirilemez. Modül düzeyindeki departman yetkisi, kullanıcıdaki açık istisnayla; geçici izinse en fazla 30 günlüğüne birleştirilir.
- Departman veya kişi yetkisi kaydedilmeden önce etki önizlemesi; etkilenecek aktif kullanıcıları, açılacak modülleri ve hassas finans verisi uyarısını gösterir. Geçici yetki verme/kaldırma kullanıcı işlem geçmişine eklenir.
- `kritik_onay` kuyruğu ikinci bir aktif yönetici (finans işlemlerinde finans yetkilisi de olabilir) tarafından sonuçlandırılır. İsteği açan kullanıcı kendi isteğini onaylayamaz; reddetme gerekçesi zorunludur. İstek sahibinin bekleyen talebi iptal edilebilir. Desteklenen kritik işlemler: sipariş, bayi, teklif, hammadde, stok ve finans kaydı silme; elle stok girişi; sipariş/hammadde alımında TL karşılığı 50.000 ₺ ve üzeri ödeme. Bu işlemler ikinci onay gelmeden uygulanmaz. Eşik bu sürümde sabit 50.000 ₺'dir.
- Onay isteğinin gövdesi yalnız bekleyen işlemi güvenle uygulayabilmek için `lumispac_approvals.json` içinde saklanır; kullanıcı arayüzündeki liste gövdeyi ve iç yolu göstermez. Onay kararı ve asıl işlem API denetim izine yazılır.
- Kullanıcı kendi açık oturumlarını cihaz/tarayıcı bilgisi, açılış ve son etkinlik zamanıyla görebilir; diğer oturumlarını iptal edebilir. Oturum anahtarı listelenmez. Son yönetici hesabı devre dışı bırakılamaz, başka departmana taşınamaz veya silinemez.
- Yeni departman açılırken izin seviyesi doğrulanır; bilinmeyen değer `gormez` olarak kalır.

### Birlikte deneme adımları

1. Yönetici hesabında **Departmanlar** ekranını açın; satış departmanını düzenleyin, profili ve etki önizlemesini inceleyin. Kaydetmeden önce hassas veri uyarısının göründüğünü kontrol edin.
2. Bir test kullanıcısında **Kullanıcılar → Düzenle** bölümünden sadece `kar_maliyet` iznini kapatın. Bu hesapta maliyet/kâr rapor sekmelerinin kaybolduğunu, ciro/satış tutarlarının durduğunu ve izinli olmayan API isteklerinin reddedildiğini kontrol edin.
3. Bir test kullanıcısına kısa süreli modül izni verin; süre dolmadan erişimi, izni kaldırınca veya son tarih geçince erişimin kapanmasını kontrol edin.
4. Ayrı bir kullanıcıyla desteklenen kritik işlem isteği oluşturun. İstek sahibinin kendi kendine onaylayamadığını, ikinci yetkilinin gerekçeyle reddedebildiğini veya onayladığında işlemin yalnız bir kez uygulandığını kontrol edin.
5. **Ayarlar → Oturumlar** bölümünde güncel etkinlik zamanını ve başka tarayıcı oturumunu kapatma davranışını doğrulayın. Son yönetici korumasını gerçek hesabı devre dışı bırakarak denemeyin; API reddini kontrollü inceleyin.

Bu değişiklikler geliştirme kopyasında kodlanmıştır; uygulama üzerinde henüz birlikte kullanıcı testi yapılmamıştır.


## Ekip hiyerarşisi ve kalıcı kişi izinleri

- Kullanıcılar yönetici tarafından bir ekip yöneticisine (`amir_id`) bağlanabilir; ekip yöneticisi işareti (`ekip_yoneticisi`) yalnız yönetici tarafından verilir.
- Yönetici şirket genelindeki kullanıcıları ve departman temel izinlerini yönetir. Ekip yöneticisi yalnız doğrudan ve dolaylı bağlı kullanıcıların kalıcı kişi izinlerini değiştirebilir.
- Ekip yöneticisinin verdiği seviye hem kendi etkin seviyesini hem hedef kullanıcının departman temel seviyesini aşamaz. Ekip yöneticisi departman değiştiremez, kullanıcı silemez, parola sıfırlayamaz ve yeni kullanıcı açamaz.
- Finansal kâr/marj/maliyet sınırı sunucu tarafında korunur; bu bilgiler yalnız yönetici ve finans/muhasebe departmanlarında açılabilir.
- Eski süreli izin satırları veri dosyasında ve geçmiş denetim kayıtlarında korunur; artık etkin izin hesabına katılmaz, API ile verilemez/kaldırılamaz ve kullanıcı listesinde gösterilmez.
- İzin değişiklikleri kullanıcı, hedef ve yapılan işlem bilgisiyle Denetim İzi’ne yazılır.
