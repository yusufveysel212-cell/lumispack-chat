"""
LUMISPAC — Yardım İçerikleri Modülü
Kategoriler ve konular. Markdown benzeri basit format.
"""

KATEGORILER = [
    {
        'slug': 'baslangic',
        'baslik': '🚀 Başlangıç',
        'konular': [
            {
                'slug': 'ilk-kullanim',
                'baslik': 'İlk Kullanım Turu',
                'icerik': '''
LUMİSPAC'a ilk kez giriş yaptığınızda otomatik olarak bir **tanıtım turu** başlar. Bu turda:

1. **Sol menü** — Tüm sayfalara nasıl geçilir
2. **Ürünler** — Maliyet ve fiyat yönetimi
3. **Raporlar** — 25 farklı analiz
4. **Klavye kısayolları** — Hızlı gezinme

Turu tekrar başlatmak için:
- **Ayarlar → Yardım** sekmesindeki **"Turu Yeniden Başlat"** butonuna tıkla
- Ya da **📚 Yardım** sekmesinden **"İlk Kullanım Turu Başlat"** seç
                ''',
            },
            {
                'slug': 'urun-ekle',
                'baslik': 'Yeni Ürün Nasıl Eklenir?',
                'icerik': '''
**1. Ürünler** sekmesine git

**2. "+ Yeni Ürün"** butonuna tıkla (sağ üstte)

**3. Zorunlu alanlar:**
- **Kod** (örn: LUM-150-5)
- **Ürün adı** (örn: 150CC SIZDIRMAZ)
- **Ağırlık** (gram cinsinden, örn: 5)
- **Koli içi adet** (örn: 1000)

**4. Opsiyonel alanlar:**
- Fire oranı (%)
- Nakliye gideri (₺)
- İşçilik gideri (₺)
- Satış fiyatı (₺)

**5. Kaydet** butonuna bas

Sistem **otomatik olarak** maliyeti hesaplar:
- Hammadde maliyeti
- Fire maliyeti
- Toplam koli maliyeti
- Kâr marjı

**İpucu:** Toplu fiyat güncellemesi için **"Toplu Güncelle"** özelliğini kullan.
                ''',
            },
            {
                'slug': 'siparis-olustur',
                'baslik': 'Sipariş Nasıl Oluşturulur?',
                'icerik': '''
**1. Sipariş ve Tır** sekmesine git

**2. Ürün seç** (dropdown'dan)
- Ürün kodu, adı, ağırlığı görünür

**3. Koli adedini** gir

**4. "Sepete Ekle"** butonuna bas

**5. Sepette gözden geçir:**
- Toplam satış (KDV hariç)
- İskonto
- KDV
- Genel toplam
- Tahmini kâr

**6. Müşteri bilgisi** ekle

**7. Kaydet:**
- **"Teklif Kaydet ve Yazdır"** → Teklif oluşturur, PDF üretir
- **"Siparişe Dönüştür"** → Direkt sipariş oluşturur

**Sonraki adım:** Sipariş Detay'dan **plaka/şoför** gir.

**İpucu:** Klavyeden **Ctrl+K** ile hızlı komut paletini açabilirsin.
                ''',
            },
        ],
    },
    {
        'slug': 'raporlar',
        'baslik': '📊 Raporlar',
        'konular': [
            {
                'slug': 'raporlara-genel',
                'baslik': 'Raporlara Genel Bakış',
                'icerik': '''
**📈 Raporlar** sekmesinde **16 farklı analiz** bulunur:

**1. Genel Bakış (Dashboard)** — 12 KPI kartı + mini grafikler

**2. Maliyet Kırılımı** — Her ürün için hammadde/fire/nakliye/işçilik

**3. Kârlılık Analizi** — Tüm ürünlerin marj sıralaması

**4. Duyarlılık Matrisi** — Kur değişince maliyet nasıl değişir (ısı haritası)

**5. Dönemsel Trend** — Günlük/haftalık/aylık satış grafiği

**6. Bayi Performans** — En iyi bayiler, sepet, marj

**7. ABC Analizi** — Pareto: ilk %80 satış hangi ürünler

**8. Sevkiyat/Dolum** — Tır doluluk, m³

**9. Hedef Marj** — Hedefe ulaşmak için gereken fiyatlar

**10. Simülatör** — Anlık maliyet testi

**11. Maliyet Geçmişi** — 12 aylık timeline

**12. Fiyat Önerisi** — Her ürün için önerilen fiyat

**13. Projeksiyon** — Gelecek 3 ay tahmini

**14. Anomali** — Normalden sapan ürünler

**15. Müşteri Segmentasyonu** — RFM analizi

**16. Kar-Zarar Tablosu** — Aylık P&L

Her rapor **Excel'e aktarılabilir** ve **PDF olarak yazdırılabilir**.
                ''',
            },
            {
                'slug': 'karlilik-analizi',
                'baslik': 'Kârlılık Analizi Nasıl Yapılır?',
                'icerik': '''
**📈 Raporlar → Kârlılık** sekmesine git.

**Ne gösterir?**
- Her ürün için **koli maliyeti**
- **Mevcut satış fiyatı** (KDV dahil)
- **Net kâr** (KDV hariç)
- **Marj %**
- **Markup %**
- **Hedefte mi?** kontrolü

**Sıralama:** Marj yüksekten düşüğe

**KPI kartları:**
- Ortalama marj
- Hedefte olan ürün sayısı
- Hedef altı
- Zararda olan

**Filtreler:**
- Kategori seç
- Hedefte olanlar / olmayanlar

**Kullanım:** Hangi ürünün kâr getirdiğini, hangisinin zarar ettiğini hızlı gör.

**İpucu:** Kırmızı işaretli ürünler **hemen müdahale** gerekli.
                ''',
            },
            {
                'slug': 'duyarlilik',
                'baslik': 'Duyarlılık Matrisi Nasıl Okunur?',
                'icerik': '''
**📈 Raporlar → Duyarlılık** sekmesine git.

**Ne gösterir?**
- Kur değişince **maliyet nasıl değişir**
- **13 kur adımı** (mevcut kurdan -30% ile +30%)
- **Isı haritası** (kırmızı=yüksek maliyet, yeşil=düşük)

**Kullanım senaryoları:**

**Senaryo 1: Kur artışı**
> Kur 50₺ → 55₺ olursa, hangi ürünün maliyeti ne kadar artar?

**Senaryo 2: Fiyat planlaması**
> Hangi kur seviyesinde hangi ürünü satmalıyım?

**Senaryo 3: Risk analizi**
> Kur %10 artarsa kâr %kaç düşer?

**Grafikler:**
- **Line chart:** Kur × Ortalama maliyet
- **Isı haritası:** Kur × Ürün matris

**İpucu:** Kırmızı hücreler = yüksek maliyet riski.
                ''',
            },
        ],
    },
    {
        'slug': 'pdf-belgeler',
        'baslik': '💰 PDF & Belgeler',
        'konular': [
            {
                'slug': 'teklif-pdf',
                'baslik': 'Teklif PDF Nasıl Üretilir?',
                'icerik': '''
**İki yol vardır:**

**Yol 1: Teklifler sekmesinden**
1. **📄 Teklifler** sekmesine git
2. Herhangi bir teklifin **🖨️ Yazdır** butonuna bas
3. Dropdown'dan seç:
   - **👁️ Önizle** — Tarayıcıda aç
   - **📥 İndir** — Direkt dosya indir

**Yol 2: Sepetten**
1. Sepette ürünleri doldur
2. **"Teklif Kaydet ve Yazdır"** butonuna bas
3. Otomatik PDF açılır

**PDF içeriği:**
- Header: LUMİSPAC logosu
- FİYAT TEKLİFİ başlığı
- Teklif No, Tarih, Geçerlilik
- Müşteri bilgisi
- Ürün tablosu (fiyat + KDV)
- Toplam kutusu
- Ödeme koşulları
- İmza alanları (LUMİSPAC + Müşteri)

**İpucu:** PDF'i telefondan da üretebilirsin (mobil uyumlu).
                ''',
            },
            {
                'slug': 'irsaliye-plaka',
                'baslik': 'İrsaliye Plaka/Şoför Nasıl Girilir?',
                'icerik': '''
**Sipariş Detay'dan:**

1. **📋 Siparişler** sekmesine git

2. Siparişin yanındaki **"Detay"** butonuna bas

3. Açılan modaldan **"🚚 Sevkiyat Bilgileri"** kartını bul

4. **3 alan doldur:**
   - **Araç Plakası:** `34 ABC 123`
   - **Şoför Adı:** `Mehmet Yılmaz`
   - **Şoför Telefonu:** `0533 123 45 67`

5. **"💾 Sevkiyat Bilgilerini Kaydet"** butonuna bas

6. Yeşil toast: **"✅ Sevkiyat bilgileri kaydedildi"**

**PDF'te nasıl görünür?**

Aynı siparişin **🖨️ Yazdır → 🚚 Sevk İrsaliyesi** seçilince PDF'te:
- 🚚 Araç Plakası: 34 ABC 123
- 👤 Şoför: Mehmet Yılmaz
- 📞 Şoför Telefonu: 0533 123 45 67

**Önemli:**
- Her sipariş **kendi plaka/şoförünü** alır
- Bilgi girilmezse PDF'te **— (tire)** görünür
                ''',
            },
            {
                'slug': 'fatura-pdf',
                'baslik': 'Fatura ve İrsaliye Farkı',
                'icerik': '''
**İki farklı belge tipi:**

**🚚 Sevk İrsaliyesi:**
- **Lojistik** belgesi
- Ürünlerin teslim edildiğini gösterir
- **Fiyat YOK** — sadece koli
- **Ödeme koşulu YOK**
- İmza: **Teslim Alan (Şoför)**
- Toplam: **"📦 Teslim Edilen: X Koli"**

**💰 Fatura:**
- **Ticari** belge (yasal)
- Ödeme talebini gösterir
- **Fiyat VAR** (KDV hariç/dahil)
- **Ödeme koşulu VAR**
- **VKN + Vergi Dairesi** gösterilir
- İmza: **LUMİSPAC**

**Ne zaman hangisi?**

| Durum | Belge |
|-------|-------|
| Mal sevk edildi, teslim alındı | 🚚 İrsaliye |
| Ödeme talebi | 💰 Fatura |
| Müşteri rapor için istedi | 📋 Sipariş Formu |
| Fiyat teklifi | 📄 Teklif |

**Her ikisini de** aynı siparişten üretebilirsin.
                ''',
            },
        ],
    },
    {
        'slug': 'ayarlar-kisayollar',
        'baslik': '⚙️ Ayarlar & Kısayollar',
        'konular': [
            {
                'slug': 'klavye-kisayollari',
                'baslik': 'Tüm Klavye Kısayolları',
                'icerik': '''
**🚀 Navigasyon (G + harf):**

| Kısayol | Sayfa |
|---------|-------|
| `G` + `B` | Genel Bakış |
| `G` + `P` | Ürünler |
| `G` + `R` | Raporlar |
| `G` + `O` | Siparişler |
| `G` + `D` | Bayiler |
| `G` + `Q` | Teklifler |
| `G` + `S` | Sipariş/Tır |
| `G` + `N` | Senaryo |
| `G` + `T` | Ayarlar |

**⚡ Hızlı İşlemler:**

| Kısayol | İşlem |
|---------|-------|
| `?` | Yardım/Kısayol paneli |
| `/` | Ürün arama |
| `Ctrl+K` | Komut paleti |
| `Ctrl+N` | Yeni ürün |
| `Ctrl+E` | Excel indir |
| `Ctrl+S` | Kaydet |
| `Ctrl+Z` | Geri al |
| `Ctrl+Y` | Yinele |
| `Esc` | Modal/Panel kapat |

**Nasıl kullanılır?**

**G + R için:**
1. Klavyede `G` bas → ekranın altında ipucu çıkar
2. Hemen `R` bas → Raporlar sekmesi açılır

**İpucu:** Kısayollar **input alanları içinde çalışmaz**. Önce Esc ile çık.
                ''',
            },
            {
                'slug': 'karanlik-mod',
                'baslik': 'Karanlık Mod',
                'icerik': '''
**Nasıl açılır?**

**Yöntem 1: Sol menü**
- Sol menünün en altında **"Karanlık mod"** butonu var
- Tıkla → tema değişir

**Yöntem 2: Sistem**
- İşletim sistemi karanlık moddaysa otomatik algılanır (bazı tarayıcılar)
- Tercih **localStorage**'a kaydedilir

**Özellikler:**
- ✅ Göz yorgunluğunu azaltır
- ✅ Gece çalışması için ideal
- ✅ Tüm grafikler karanlık uyumlu
- ✅ PDF'ler etkilenmez (beyaz kalır)

**Geri almak için:**
- Aynı butona tekrar tıkla → açık tema

**İpucu:** Karanlık mod tercihi **tarayıcı bazlıdır**. Farklı tarayıcıda ayrı ayar.
                ''',
            },
            {
                'slug': 'bildirimler',
                'baslik': 'Bildirim Sistemi',
                'icerik': '''
**🔔 Bildirim ikonu** sağ üstte.

**Ne zaman bildirim gelir?**

| Olay | Önem |
|------|------|
| 🚨 Gecikmiş sipariş | Kritik |
| 📦 Kritik stok (15 gün) | Kritik |
| 💸 Zararda ürün | Kritik |
| 🎯 Hedef altı ürün | Uyarı |
| 📄 15+ gün bekleyen teklif | Uyarı |
| ⚠️ Maliyet anomalisi | Uyarı |
| 🛒 Bugün yeni sipariş | Bilgi |

**Ayarlar:**
1. **Ayarlar → 🔔 Bildirimler** kartına git
2. Toggle'lar:
   - **Sistem aktif** (ana anahtar)
   - **Tarayıcı bildirimi** (masaüstü bildirim)
   - **Kritik / Uyarı / Bilgi** seviyeleri
3. **Sessiz saatler:** 22:00 - 08:00 (varsayılan)

**Bildirime tıkla** → ilgili sayfaya otomatik atlar.

**Test:** Ayarlardan **"🧪 Test Bildirimi"** butonuna bas.
                ''',
            },
        ],
    },
    {
        'slug': 'sorun-giderme',
        'baslik': '⚙️ Sorun Giderme',
        'konular': [
            {
                'slug': 'kur-gelmiyor',
                'baslik': 'Kur Gelmiyor, Ne Yapmalıyım?',
                'icerik': '''
**Belirti:** Üstteki kırmızı kutuda **"Kur bekleniyor..."** veya **"Bağlantı yok"** yazıyor.

**Sebep:** İnternet bağlantısı sorunu veya tüm 6 kaynak başarısız.

**Kontrol adımları:**

**1.** İnternet var mı?
- Tarayıcıda **google.com** aç
- Açılmıyorsa internet sorunu

**2.** Manuel yenile:
- Chip'in yanındaki **"Yenile"** butonuna bas

**3.** Bekle:
- Sistem **her 2 saniyede** otomatik günceller
- Çalışırsa kur gelir

**4.** Sistem durumu:
- **Ayarlar → Sistem Durumu** (yakında)
- Hangi kaynak başarısız gösterilir

**7 katmanlı kur motoru:**

1. **Harem Altın** (ana kaynak · USD/TRY satış kuru)
2. **Yahoo Finance** (yedek)
3. **biquote.io** (yedek)
4. **Bürküt SDK** (yedek)
5. **TCMB** (resmî yedek)
6. **Darphane CDN** (yedek)
7. **canlidoviz.com** (yedek)

Harem Altın yayınına erişilemezse diğer kaynaklar sırayla denenir.

**Uzun süre gelmiyorsa:**
- Modem'i yeniden başlat
- VPN varsa kapat
- Güvenlik duvarını kontrol et

**İpucu:** Kur **son kayıtlı** değeri korur, sistem çökmez.
                ''',
            },
            {
                'slug': 'yedekten-geri-yukle',
                'baslik': 'Yedekten Nasıl Geri Yüklerim?',
                'icerik': '''
**İki tür yedek var:**

**1. Otomatik yedekler (her gün):**
- Konum: `yedekler/` klasörü
- Format: `lumispac_data_YYYYMMDD.json`

**2. Manuel yedek (Ayarlar'dan):**
- **Ayarlar → Yedekler** kartına git
- **"Yeni Yedek Al"** butonuna bas

**Geri yükleme adımları:**

1. **Ayarlar → Yedekler** sekmesine git

2. Yedek listesinde **hangi tarihe** dönmek istediğini bul

3. **"Geri Yükle"** butonuna bas

4. Onay ister:
   > "Bu yedek geri yüklensin mi? **Mevcut veri otomatik yedeklenir.**"

5. **Evet** de → Sistem geri yükler

**Önemli:**
- ⚠️ Mevcut veri **otomatik yedeklenir** (yanlışlıkla kaybetmezsin)
- ⚠️ Sayfa **yenilenir** (kaydedilmemiş değişiklikler kaybolur)
- ⚠️ Yedek **tarihli** olduğu için hangisini seçtiğine dikkat et

**Acil durum:**

C:\lumispac_yedekler\ klasöründeki dosyalar manuel yedeklerdir. Bir sorun olursa oradan kopyala.
                ''',
            },
            {
                'slug': 'sistem-durumu',
                'baslik': 'Sistem Durumu Nasıl Kontrol Edilir?',
                'icerik': '''
**Genel kontrol:**

**1. Sol menü → Ayarlar** sekmesine git

**2. Sistem durumu kartında:**
- 📊 **Kur kaynağı:** Hangi kaynaktan geliyor
- ⏱️ **Son kontrol:** Kaç saniye önce
- 🔴 **Hata geçmişi:** Son 100 hata
- 💚 **Sağlık:** Her kaynağın durumu (yeşil/kırmızı)

**3. Detaylı kontrol için F12:**
- **Console** sekmesi → JavaScript hataları
- **Network** sekmesi → API çağrıları (200 OK olmalı)
- **Application** → localStorage (tercihler)

**Log dosyası:**
- Konum: `lumispac_hata.log`
- Boyut: Max 1 MB (otomatik rotasyon)
- Yedekler: `lumispac_hata.log.1`, `.2`, `.3`

**Yaygın sorunlar:**

| Belirti | Çözüm |
|---------|-------|
| Kur gelmiyor | İnternet kontrol |
| Kayıt olmuyor | F12 → Console hataları |
| Sayfa boş | Ctrl+F5 (cache temizle) |
| Buton çalışmıyor | F12 → Console |

**İpucu:** Sorun devam ederse **log dosyasını** sakla, destek için.
                ''',
            },
        ],
    },
]


def kategoriler():
    """Tüm kategorileri döner (baslik + slug)."""
    return [{'slug': k['slug'], 'baslik': k['baslik']} for k in KATEGORILER]


def konular(kategori_slug=None):
    """Belirli bir kategorideki konuları döner."""
    if kategori_slug:
        for k in KATEGORILER:
            if k['slug'] == kategori_slug:
                return [{'slug': kn['slug'], 'baslik': kn['baslik']} for kn in k['konular']]
        return []
    # Tüm konular
    out = []
    for k in KATEGORILER:
        for kn in k['konular']:
            out.append({
                'slug': kn['slug'],
                'baslik': kn['baslik'],
                'kategori': k['baslik'],
                'kategori_slug': k['slug'],
            })
    return out


def konu_icerik(slug):
    """Belirli bir konunun içeriğini döner."""
    for k in KATEGORILER:
        for kn in k['konular']:
            if kn['slug'] == slug:
                return {
                    'slug': kn['slug'],
                    'baslik': kn['baslik'],
                    'kategori': k['baslik'],
                    'kategori_slug': k['slug'],
                    'icerik': kn['icerik'].strip(),
                }
    return None