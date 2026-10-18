# LUMISPAC demo senaryoları

Bu veri yalnızca sahte test içeriğidir. Hiçbir gerçek kişi, müşteri, vergi, banka hesabı, kart, çek numarası veya iletişim bilgisi içermez. Sipariş ödeme satırları yalnızca arayüzde sevk bakiyesi kontrollerini sınamak için sentetik tutarlardır.

## Yükleme ve sıfırlama

Uygulama başlangıcında demo verisi yüklenmez. `ChatGPT geliştirme` klasöründe açıkça çalıştırın:

```powershell
python demo_veri.py yukle
```

Tekrar çalıştırmak mükerrer kayıt oluşturmaz. Her yükleme/sıfırlamadan önce mevcut JSON dosyalarının kopyası `yedekler_v2/demo_veri_*` altına alınır. Temizleme yalnızca bu araçta sabitlenmiş `TEST-DEMO-*` kimliklerini ve `TEST -` imzalı üretim örnek dosyasını hedefler:

```powershell
python demo_veri.py sifirla
```

## Test hesapları

| Hesap | Şifre | Kullanılabilecek arayüz adımları |
|---|---|---|
| `test_admin` | `TestOnly-Admin-5001!` | Departmanlar/kullanıcılar ekranı, demo kayıtlarını görme, yönetici akışları |
| `test_satis` | `TestOnly-Satis-5001!` | Atanmış iki TEST bayisini görme, iki TEST siparişini inceleme/oluşturma, demo sevk yetkisiyle sevk senaryosu |
| `test_uretim` | `TestOnly-Uretim-5001!` | Üretim kuyruğu, minimum stok planı, üretimi başlatma/durdurma/devam/tamamlama, fire/ıskarta ve depo kabul talebi |
| `test_depo` | `TestOnly-Depo-5001!` | Stok ve sipariş ekranı, depo uygunluk kontrolü, sevk ve üretim kabul taleplerini kabul/ret |
| `test_finans` | `TestOnly-Finans-5001!` | Hammadde alım ödeme hareketi ekleme ve kur/kaynak/tarih geçmişini görme; gerçek ödeme başlatılmaz |

Hammadde alımı denemesinde `test_admin` TEST hammadde/tedarikçi ve satın alma belgesini hazırlar; `test_finans` ödeme veya kısmi ödeme kaydı girer; tam ödeme sonrası `test_admin` kabul talebini gönderir; `test_depo` tüm miktarı kabul veya gerekçeli ret eder. Demo kaydı eklemek istemiyorsanız bu adımları mevcut boş kayıtlarla başlatmayın. İş kuralı: depo kabul kuyruğuna gönderimden önce borç toplamının %100'ü finans tarafından kaydedilmiş olmalıdır.

`test_satis` hesabına yalnızca bu test kullanıcısında `siparis_sevk:yazar` istisnası tanımlanmıştır; gerçek satış kullanıcıları değiştirilmez. Hesapları yalnızca yerel uygulamada kullanın ve demo bittikten sonra `sifirla` çalıştırın.

## Arayüzde denenebilen senaryolar

1. `test_satis` ile girip Bayiler/Siparişler ekranında yalnızca kendisine atanmış `TEST -` bayi ve siparişleri doğrulayın.
2. `TEST - SIP-HAZIR` siparişinde **Depo Kontrolü** seçin. Demo açılış stoğundan sonra kalan miktar 8; istenen 3 olduğundan “sevkiyata hazır” bilgisi görünür.
3. `TEST - SIP-EKSIK` siparişinde **Depo Kontrolü** seçip tahmini tarihi girin. Üründe stok hareketi olmadığı için sipariş üretim kuyruğuna kaydedilir ve tarih gösterilir.
4. Sipariş detayında sevkiyat bilgilerini kaydedin. Hazırlanmış test siparişlerinde araç `TEST-ARAC-01`, şoför `TEST - Sürücü 01` olarak gelir; değerler tamamen sahtedir.
5. Sevk durumuna geçişte `TEST - SIP-ODEMESIZ` ve `TEST - SIP-KISMI` reddedilir. `TEST - SIP-TAM` ve vadesi 2099 olan kabul edilmiş `TEST - SIP-CEK` tam bakiye sayılarak sevke geçebilir. `test_satis` ve `test_depo` hesaplarında sevk yetkisi vardır.
6. Sevk edilmiş siparişin detayındaki PDF menüsünden irsaliyeyi yerel olarak önizleyin/indirin. Bu yalnızca yerel belge üretimidir.

## Üretimden depo kabulüne arayüz senaryoları

1. `test_admin` ile **Üretim & Depo** ekranına girip `TEST - Kalıp ayarı` gibi bir duruş nedeni ekleyin. Bu işlem yönetici yetkisi ister.
2. `test_satis` ile `TEST - SIP-EKSIK` siparişinde **Depo Kontrolü** çalıştırıp tahmini tarihi kaydedin. Sonra `test_uretim` ile **Üretim & Depo** ekranını açın; sipariş eksiği ve minimum stok ihtiyacı listelenir. Minimum stok satırından ayrıca üretim planı oluşturulabilir.
3. Üretim kuyruğundaki işi başlatın; durdururken yönetici tarafından tanımlı nedeni seçin; devam ettirip tamamlayın. Toplam miktar ve varsa fire miktarı kullanıcı tarafından koli olarak girilir; fire için gerekçe gerekir ve fire kullanılabilir stoğa eklenmez.
4. Tamamlanan işte **Depo Kabul Talebi** gönderin. `test_depo` ile talebi açıp tüm miktarı kabul edin veya gerekçeli reddedin. Ret stoğu artırmaz; `test_uretim` ile işi düzeltip yeniden tamamlayarak yeni kabul talebi gönderin.
5. Depo tam kabul verdiğinde kullanılabilir stok yalnızca bir kez artar. İlgili siparişin tamamlanan ürün ihtiyacı karşılandıysa sipariş sevkiyata hazır hale gelir.

İşlem geçmişinde kullanıcı, zaman, miktar, önceki/yeni durum ve gerekçe tutulur. Demo akışında tek makine ve tek kalıp kullanılır. Uygulamanın üretim kayıtları ilk üretim işlemiyle `lumispac_uretim.json` dosyasına yazılır; uygulama açılışında otomatik demo verisi yüklenmez.

## Mevcut arayüzde bulunmayan adımlar

- Ürün reçetesi ve hammadde tüketim miktarları henüz tanımlı değil; bu nedenle üretimden hammadde düşümü uygulanmıyor. Bu sonraki geliştirme dilimidir.
- Üretim kabul-ret, stok hareketi ve sipariş durum güncellemesi sunucu tarafında birlikte yürütülür; dosya yazımı/geri alma hataları açık hata olarak raporlanır.
- Siparişe ödeme/tahsilat ekleme arayüzü yok. API servisinde ödeme kayıt uç noktası mevcut olsa da test kullanıcısı için arayüzden ödeme girildiği iddia edilmemelidir. Sevk ödeme senaryoları önceden yüklenmiş sentetik sipariş ödeme durumlarıyla denenir.
- Harici mesaj, ödeme sağlayıcısı, e-fatura/irsaliye servisi veya başka dış servis bu demoda çağrılmaz.
