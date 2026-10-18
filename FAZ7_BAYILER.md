# Faz 7-4 — Bayiler

## Kapsam ve kural

- Sipariş sayısı, ciro, maliyet, kâr ve marj hesaplarının ortak kaynağı `services/hesap_service.py` içindeki `siparis_satis_ozeti` fonksiyonudur. Maliyet olarak siparişte saklanan maliyet anlık görüntüsü kullanılır; eksik maliyet için tahmin yapılmaz.
- Bayi listesi API'si merkezi hesaplamadan bayi bazında sipariş/ciro özetini verir. Bayi paneli de aynı merkezi özeti kullanır.
- İptal durumu `services/hesap_service.py` içindeki `siparis_iptal_mi` ile merkezileştirilmiştir. Türkçe `İptal`/`Iptal`, küçük-büyük harf, `İptal edildi`, eski mojibake `�ptal` ve İngilizce `cancelled`/`canceled` değerleri bayi özetinden, son siparişlerden ve trendden aynı şekilde çıkarılır.
- Sipariş başına ciro, kayıtlı maliyet ve kâr `siparis_finans_metrikleri` ile hesaplanır. Bayi paneli özeti, son sipariş satırları ve aylık trend aynı yuvarlama/formül yolunu kullanır; üç görünümde metrikler uzlaştırılır.
- Saha satış kullanıcısı yalnızca `owner_user_id` değeri kendi kullanıcı kimliği olan bayi, teklif ve sipariş kayıtlarını görür. İlişkili sipariş ve teklif için bayi sahipliği de eşleşmelidir. Eski sahipliksiz kayıtlar otomatik atanmaz.
- Bayi oluşturma/güncellemede istek gövdesindeki sahiplik alanı kullanılmaz. Yönetici, Bayiler ekranındaki sahip seçicisinden aktif saha satış kullanıcısını seçer; özel `PATCH /api/dealers/<id>/owner` uç noktası atamayı yapar. Silme ve sahiplik atama olayları kullanıcı/işlem/zaman ayrıntısıyla uygulama işlem geçmişine yazılır.
- Yinelenen bayi kimlikli toplu kayıt isteği reddedilir. Satış kullanıcısının liste isteğinden kayıt çıkarması silme yapmaz; gerçek silme ayrı ve yetki kontrollü uç noktadadır.

## Dashboard veri sınırı

Saha satış rolü `/api/hesap/dashboard` yanıtından şirket geneli maliyet, kâr ve marj metriklerini alamaz. Ortalama marj/kâr, tahmini brüt kâr, maliyet kıyasları, ürün marjları, hedef marj uyarıları ve kritik stok sayısı yanıta eklenmez. Arayüzde ilişkili KPI kartları ve hedef marj banner'ı da gösterilmez. Görünürlük bayrağı yalnızca açık `true` ise maliyet/kâr kartları çizilir; eksik veya eski API bayrağı kapalı kabul edilir. `GET /api/reports/target-alert` bu rol için sunucuda 403 döndürür.

## Testler

Merkezi bayi metrikleri `tests/test_dealer.py`; bayi sahipliği, istemci sahiplik sahteciliği, yinelenen kimlik ve satış Dashboard yanıtı `tests/test_security.py` ile `tests/test_hesap_dashboard.py` içinde doğrulanır.

## Faz 7-5 bütünleştirme denetimi

2026-10-16 tarihinde tamamlandı. Bayi panelindeki ham `status == "Iptal"` filtresi kaldırılarak merkezi iptal kontrolü kullanıldı; özet, son siparişler ve aylık trend için sipariş finans metrikleri ortaklaştırıldı. Regresyonlar Türkçe aksan/kasa varyasyonları, eski `Iptal`/bozuk kodlama, iptal edilmiş ve aktif durumların aynı ölçümlerde tutarlı kalmasını kapsar. Denetimde Dashboard görünürlüğünün eksik API bayrağında açık varsayıldığı görüldü; arayüz artık yalnızca sunucudan `true` geldiğinde şirket maliyet/kâr kartlarını gösterir. Üretim/depo kabulü, hammadde satın alma/ödeme, sipariş stok/ödeme, güvenlik/sahiplik, eski kayıt ve API testleri tam paketle tekrar çalıştırıldı.
