# Hammadde ve satın alma deneme adımları

Bu akış yalnız yerel uygulama kayıtlarını değiştirir. Gerçek ödeme, mesaj veya harici servis çağrısı yapmaz. Test kayıtlarını `TEST -` önekiyle adlandırın. Test hesaplarının giriş bilgileri `DEMO_TEST_TALIMATI.md` içindedir.

## Hammadde ve tedarikçi tanımlama

1. `test_admin` ile giriş yapıp **Hammadde / Satın Alma** ekranını açın.
2. PET için `TEST - PET hammadde`, PP için `TEST - PP hammadde` gibi ayrı kayıtlar oluşturun. Birim KG'dir; KG fiyatını elle girin.
3. **Tedarikçiler** alanında `TEST - Hammadde Tedarikçisi` oluşturun. Bu kayıt bayi listesine eklenmez.

## Satın alma ve depo kabulü

1. Satın Alma bölümünde TEST tedarikçisini, belge numarası/tarihini, borç para birimini (TL/USD) ve hammadde satırlarını (KG miktarı ve elle girilen birim fiyat) seçin.
2. İsterseniz yalnız sahte içerikli PDF/JPG/PNG ekleyin. Dosya uygulamanın özel belge klasöründe tutulur.
3. Taslağı kaydedin. Ödeme bölümünde `test_finans` ile giriş yapıp bu satın alma için bir veya daha fazla ödeme hareketi ekleyin. TL borç/TL ödeme veya USD borç/USD ödeme için kur 1:1 kaydedilir. Çapraz para biriminde kur alanı "1 ödeme para birimi = X borç para birimi" şeklindedir; kur kaynağı ve tarihi elle girin.
4. Toplamın %100'ü ödenmeden **Depo kabulüne gönder** çalışmaz; API de bu geçişi reddeder. Gerçek ödeme yapılmaz. Deneme kayıtlarını sahte `TEST -` açıklamasıyla tutun.
   Sıfır toplamlı belge gönderilemez; satır fiyatlarını önce doğrulayın.
5. Ödeme tamamlandıktan sonra satın alma yetkisi olan kullanıcı depo talebini gönderir. `test_depo` ile **Depo Kabulü** kuyruğunda tüm miktarı kabul edin veya gerekçe yazarak reddedin. Ret stok eklemez; kabul stok hareketini bir kez oluşturur.

## Reçete ve üretim tüketimi

1. Kullanıcı tarafından belirlenmiş reçete bilgisi varsa `test_admin` ile ürün başına KG/koli değerini kaydedin. Bilinmeyen oranları tahmin etmeyin.
2. Üretim şefi `test_uretim` ile üretimi tamamlayabilir. Reçete yoksa hammadde stoğu otomatik değişmez; reçete varsa ihtiyaç hesaplanır ve yetersiz stokta tamamlama reddedilir.

## Yetki notları

- `yonetici`: katalog, tedarikçi, satın alma, kabul ve reçete yönetimi.
- `depo`: hammadde okuma ve depo kabulü.
- `uretim`: hammadde okuma ve reçete düzenleme.
- `muhasebe`: katalog ve satın alma okuma. Satın alma yazma gerekiyorsa yönetici Kullanıcılar/Departmanlar ekranından `satinalma:yazar` atamalıdır.
- `muhasebe`: ayrıca `satinalma_odeme:yazar` ile ödeme ekleyebilir ve döviz kur/kaynak/tarih bilgilerini denetim izine kaydeder. Bu kayıt ödeme/banka işlemi başlatmaz.
- Satın alma belgeleri yalnız `satinalma` okuma/yazma izniyle API üzerinden erişilir.

Bu kopyada veri dosyası `lumispac_raw_materials.json` ilk gerçek işlemde oluşturulur; uygulama açılışında demo kayıt eklenmez. Kayıt silme veya sıfırlama adımı yoktur; var olan/test kullanıcı verisini koruyun.

## Otomatik PET reçetesinde hammadde seçimi

Birden fazla aktif PET hammaddesi varsa yönetici, Hammadde & Satın Alma ekranındaki "Otomatik reçete PET hammaddesi" alanından tüketilecek stoğu seçer. Seçim PUT /api/raw-materials/recipes/default-pet üzerinden kaydedilir; yalnız sistem yöneticisine açıktır. Tek aktif PET varsa seçim olmadan otomatik kullanılır. Seçilmiş PET pasifleşirse başka stoğa kendiliğinden geçilmez. Seçim sonraki üretim hesaplarında kullanılır; geçmiş stok hareketleri değiştirilmez.

## Hammadde kataloğunu düzenleme ve silme

Hammadde kataloğundaki Düzenle düğmesi, hammaddeler:yazar yetkisi ile kod, ad ve tür değiştirir. Maliyet yetkisi olmayan kullanıcı fiyatı değiştiremez. Sil düğmesi hammaddeler:tam yetkisi ister. Sistem yöneticisi hammaddeyi doğrudan silebilir; diğer kullanıcılar mevcut ikinci yetkili onay akışına tabidir. Stok hareketi, satın alma veya reçete bağlantısı bulunan hammadde silinemez. Otomatik reçetede seçili PET silinemez ve türü değiştirilemez; önce reçete PET seçimi değiştirilmelidir.
