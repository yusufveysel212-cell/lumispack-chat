# Yeni karma saha satış testi — 18 Ekim 2026

Bu dosya test sırasında gözlenen eksikleri toplar. Kullanıcı talebi gereği geliştirme, test tamamlandıktan sonra değerlendirilecek. Tüm kişi, bayi, ödeme ve teslimat bilgileri yerel TEST verisidir; banka/muhasebe bağlantısı yoktur.

## Başlangıç ve sıfırlama

- İş verileri kullanıcı talebiyle temizlendi: eski bayiler, sipariş/kalem/ödeme, teklifler, finans hareketleri, hammadde/tedarikçi/alım/ödeme/tüketim, üretim/kabul, stok ve eski onay/denetim/geri alma kayıtları.
- 23 ürün kartı bütün alanlarıyla korundu. 6 test kullanıcısı, 6 departman, izinler ve uygulama ayarları korundu. Ürünlerin mevcut stok alanları zaten 0 idi; stok hareketleri sıfırlandı.
- Sıfırlama öncesi tam yedek: `test_yedekleri/satis_yeniden_20261018_001135/once.dump`. pg_restore --list doğrulaması başarılı.
- SHA-256: `f3cfc9b1917e171828a6ec6198ca2aa2a2dd1c6c507040d45d33902a64726ee4`.
- Temizleme tek PostgreSQL transaction'ında yapıldı; korunacak tabloların öncesi/sonrası birebir karşılaştırıldı. Son bütünlük: ok, şema 21, 13 FK, geçersiz belge 0.
- Açık satış ekranında eski siparişler ve bayilerin boşaldığı doğrulandı. Yeni kayıtlar Ahmet Demir'in kendi satış ekranında oluşturuldu. Yeni giriş/işlem denetim kayıtları normal olarak tekrar oluşabilir.

## Yeni bayi ve sipariş

- Bayi: Dicle Ambalaj Dağıtım (TEST), Batman.
- Yetkili: Mehmet Acar (TEST). Telefon: 05550000001. Adres: TEST adresi - Batman OSB; gerçek teslimat yok.
- Satış sorumlusu: Ahmet Demir (`ahmet.demir`).
- Yeni sipariş: SIP-2026-0001. Eski silinen senaryonun aynı numarasıyla karıştırılmamalı; yeni sipariş 18.10.2026 tarihli, Dicle bayisine ait.
- 1000 CC SIZDIRMAZ: 110 koli × 600 adet = 66.000 adet.
- 1000 CC BOMBELİ SIZDIRMAZ: 100 koli × 600 adet = 60.000 adet.
- 1250 CC SIZDIRMAZ: 100 koli × 400 adet = 40.000 adet.
- 1500 CC SIZDIRMAZ: 100 koli × 400 adet = 40.000 adet.
- 250 CC SIZDIRMAZ: 100 koli × 1.000 adet = 100.000 adet.
- 2000 CC BOMBELİ SIZDIRMAZ: 100 koli × 400 adet = 40.000 adet.
- Toplam: 6 çeşit, 610 koli, 346.000 adet; KDV hariç 574.500 TL, %20 KDV 114.900 TL, KDV dahil 689.400 TL. İskonto 0.
- Teslimat hedefi: 23.10.2026.
- Kapasite hedefi: kayıtlı tahmini hacimler üzerinden 110×0,150 + 100×0,150 + 100×0,131 + 100×0,131 + 100×0,109 + 100×0,214 = 90 m³. Ürünlerin volume_verified değeri false; fiziksel hacim, yükleme ve araç ağırlık kapasitesi doğrulanmadı. Bir tıra kesin sığma onayı verilmedi; yalnız TEST plan hedefi.
- Ziyaret ve teslimat notlarına TEST kapsamı/kapasite belirsizliği yazıldı.
- Mevcut durak: Taslak; bayi teyidi bekliyor, ödeme 0/689.400 TL. Henüz üretim, stok, ödeme, sevkiyat veya teslimat yapılmadı.

## Test sonunda incelenecek eksikler

- [ ] Kapasite: satış ekranı doluluğu hesaplayamadığında “Hacim doğrulanmadı” ile birlikte “Kalan boşluk: 90,00 m³” yazıyor. Bilinmeyen dolulukta kalan boşluğu kesin gösterme; tahmini ve ölçülmüş hacmi açıkça ayır.
- [ ] Kapasite: satış kataloğu hacmi içermediğinden saha ekranında hedef tır hesabı yapılamıyor. İç maliyetleri açmadan sunucu üzerinden lojistik kapasite özeti sağlama ihtiyacını değerlendir.
- [ ] Sevkiyat yetkisi: Ahmet'in taslak sipariş detayında plaka/şoför/telefon ve “Sevkiyat Bilgilerini Kaydet” alanları görünüyor. Önceki teslim edilmiş siparişte de görünüyordu. Bu turda kaydetme denenmedi; görünürlük ile sunucu yetkisi ayrı doğrulanmalı.
- [ ] Teklif gizliliği: önceki rol kontrolünde Ahmet Teklifler ekranında “Toplam tahmini kâr” ve “NET KÂR” başlıkları ile 0 değerini gördü. Bu yeni senaryoda ayrıca tekrar kontrol edilecek; gerçek maliyet sızıntısı henüz bu gözlemle kanıtlanmış değildir.
- [ ] İlk yükleme: satış oturumunda konsolda yetkisiz marj alarmı isteği HTTP 403 görüldü; yetkisiz isteğin hiç yapılmaması değerlendirilmeli.
- [ ] Bayi düzenleme: form alanları onchange ile ayrı ayrı kaydediliyor; hızlı ardışık doldurmada değişiklikler korunmadı, gerçek klavye girdisi ve alan çıkışından sonra tek tek kaydedildi. Kayıt yarışını tekrar üret; açık kaydetme/başarı durumunu değerlendir.
- [ ] Sipariş detayında açık renk tablo başlıklarının kontrastını değerlendir.
- [ ] Yeni numara üretimi sıfırlama sonrası SIP-2026-0001 ile yeniden başladı. Yedek/eski test kanıtlarının yeni siparişle karışmaması için senaryo kimliği gösterimini değerlendir.

## Birlikte yürütülecek sonraki adımlar

1. Bayi teyidini saha ekranında kaydet.
2. TEST havale bildirimi ve Finans hesabında ayrı simülasyon doğrulaması.
3. Depo stok kontrolü ve üretim açığı.
4. Hammadde ihtiyacı, satın alma/finans/depo kabulü.
5. Üretim, mamul kabulü, sevk hazırlığı ve teslimat simülasyonu.
6. Her aşamada miktar/para/rol/geçmiş mutabakatı; gözlemleri bu dosyaya ekle. Test bitene kadar kod geliştirme yapma.

## 18.10.2026 — Yeniden başlangıç: güncel salt okunur durum

Bu bölüm yukarıdaki eski “mevcut durak” bilgisini günceller. Önceki senaryo geçmiş olarak korunmuştur. Bu incelemede iş kaydı, izin veya kod değiştirilmedi; yalnız bu test notu güncellendi.

- AGENTS.md, PROJECT_STATUS.md ve TEST_CHECKLIST.md etkin kaynak ağacındaki hedefli aramada bulunamadı (yedek/arşivler hariç).
- PostgreSQL şema v21; 23 ürün, 6 kullanıcı, 2 bayi, 2 sipariş mevcut.
- Dicle SIP-2026-0001 iptal edilmiş. Aktif senaryo Batman Ambalaj Sanayi Limited Şirketi / SIP-2026-0002, durum Onaylandı ve üretim bekliyor; altı ürünün toplam açığı 620 koli.
- Bayi teyidi var. İki kabul edilmiş tahsilat 116.760 + 583.800 = 700.560 TL; ikisinin ayrı finans gelir kaydı ve payment/order bağlantıları var. Bu iki satır mükerrer gelir değil.
- Satın alma 1111111111: 10.000 kg × 53 TL = 530.000 TL; accepted, bir ödeme ve aynı ödeme kimliğine bağlı bir finans gideri mevcut. Tek mal kabul hareketi PET stoğuna +10.000 kg yazmış.
- Diğer alımlar: 11111, 100.000 kg × 52 TL = 5.200.000 TL taslak; 2522222222, 10.000 kg ve 0 TL taslak. Bunların hatalı/istenmeyen kayıt olduğu yalnız tutarlarından kesinleştirilemez; kullanıcı kararı beklenir. Silinmedi.
- Aktif PET kartları: PET / raw-47e64e81a892464b; PET BATMAN / raw-669fd2cd52194aa3; PET1 / raw-40bb290b6ea347c2. Üçü de active=true. Tüm satın alma satırları ve tek stok girişi ilk PET kartına bağlı; diğer ikisinde stok hareketi yok.
- Siparişin güncel ürün gramajı × koli içi adet × koli hesabı 5.928 kg PET gerektiriyor. Tek giriş 10.000 kg; üretim hareketi henüz yok. Mevcut sipariş firesiz aynı miktarda üretilirse teorik kalan 4.072 kg olur; henüz stok tüketimi yapılmadı.
- Üretim işi/kabul ve mamul stok hareketi 0. Bunların olmaması üretim başlamadan beklenen durum; sanal üretim kuyruğu fiziksel iş kaydı sayısıyla karıştırılmamalı.

### Öncelikli bulgular ve kök neden

1. P1 / üretimi engelliyor: save_material yalnız kod benzersizliğini kontrol ediyor, farklı kodlarla birden fazla aktif PET oluşturabiliyor. _derive_pet_recipe ise tam bir aktif PET zorunlu tutuyor. Üç aktif kart nedeniyle stok yeterli olsa da otomatik reçete ve sipariş üretim başlangıcı engelleniyor. Reçete formülü matematiksel olarak bozuk değil; malzeme seçimi belirsiz.
2. P1 / yanlış kart düzeltme yolu: mevcut hammadde API'sinde DELETE rotası yok; save_material güncellemesi active alanını da işlemiyor. Bu nedenle kullanılmayan yanlış kartı pasife alma/silme akışı tamamlanmış değil. Stok/alım bağlantılı PET kartı silinmemeli. İki kullanılmayan kartın nasıl düzeltileceği kullanıcı onayıyla belirlenmeli; bu turda işlem yok.
3. P2 / üretim öncesi güvence: start/resume reçete ve ödeme kontrolü yapıyor; gerekli KG stoğunun yeterliliği complete aşamasında kontrol ediliyor. Başlangıçta yetersiz stok reddi ayrı regresyonla doğrulanmalı.
4. Önceki kapasite, rol görünürlüğü ve bayi otomatik kayıt gözlemleri açık; bu turda tarayıcıdan yeniden üretilmedi, yeni doğrulanmış hata olarak sunulmadı.

### Bu turdaki doğrulama

- Veritabanı incelemesi default_transaction_read_only=on oturumlarında SELECT ile yapıldı; mutasyon, sıfırlama, silme veya uygulama yeniden başlatma yok.
- Kaynaktaki _derive_pet_recipe fonksiyonu AST üzerinden alınarak yalnız bellek içi örneklerle 4 kontrol çalıştırıldı: PET yokken ret, tek PET ile 9,6 kg/koli, iki aktif PET ile ret, ikinci PET pasifken başarı. 4/4 geçti. Bu, tam pytest/API veya görünür rol testi yerine geçmez.
- Düzeltme yapılmadı; dolayısıyla düzeltme sonrası test sonucu yok.

### Önerilen devam sırası

1. İlk PET kartını koruyarak iki kullanılmayan aktif PET kartının güvenli pasifleştirilmesi/yanlış kayıt düzeltmesi için kullanıcı kararı; veri silme veya reset yok.
2. Mevcut 530.000 TL ödeme ve 10.000 kg depo kabulünü tekrar oluşturmadan doğrula; diğer taslaklara dokunma.
3. Tek aktif PET seçimi çözüldükten sonra otomatik reçeteyi ve 5.928 kg ihtiyacı kontrol et.
4. Üretim hesabında sipariş işleri → mamul kabulü → sevkiyat/teslimat; miktar ve rol kontrolleri.
5. Son mutabakat: müşteri geliri 700.560 TL, mevcut hammadde gideri 530.000 TL; yeni işlem yoksa fark 170.560 TL (kâr değildir). PET tüketimi, mamul giriş/çıkışları ve yinelenen istekleri tek tek doğrula.
