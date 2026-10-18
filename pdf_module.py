"""
LUMISPAC — PDF Üretim Modülü
4 belge tipi: Teklif, Sipariş, Sevk İrsaliyesi, Fatura
"""
import io
import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
)
from reportlab.pdfgen import canvas as canvas_module
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

# ==== YENI: Ortak moduller ====
from utils import TL as _tl_util
# ==== /YENI ====



# =========================================================
# 1) TÜRKÇE FONT KAYIT
# =========================================================
def _font_kayit():
    adaylar = [
        (r'C:\Windows\Fonts\arial.ttf', r'C:\Windows\Fonts\arialbd.ttf', 'ArialTR', 'ArialTR-Bold'),
        (r'C:\Windows\Fonts\segoeui.ttf', r'C:\Windows\Fonts\segoeuib.ttf', 'SegoeTR', 'SegoeTR-Bold'),
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 'DejaVuTR', 'DejaVuTR-Bold'),
    ]
    for normal, bold, ad_n, ad_b in adaylar:
        try:
            if os.path.exists(normal):
                pdfmetrics.registerFont(TTFont(ad_n, normal))
                if os.path.exists(bold):
                    pdfmetrics.registerFont(TTFont(ad_b, bold))
                else:
                    ad_b = ad_n
                return ad_n, ad_b
        except Exception:
            continue
    return 'Helvetica', 'Helvetica-Bold'

FONT_N, FONT_B = _font_kayit()


# =========================================================
# 2) RENK PALETİ
# =========================================================
class R:
    KIRMIZI      = HexColor('#C8102E')
    KIRMIZI_KOYU = HexColor('#8B0A1F')
    KIRMIZI_ACIK = HexColor('#FEF2F4')
    BEYAZ        = HexColor('#FFFFFF')
    SIYAH        = HexColor('#0A0E14')
    METIN        = HexColor('#1B1F27')
    METIN_ACIK   = HexColor('#4B5563')
    GRI_KOYU     = HexColor('#374151')
    GRI          = HexColor('#6B7280')
    GRI_ORTA     = HexColor('#9CA3AF')
    GRI_ACIK     = HexColor('#E5E7EB')
    GRI_CUKUR    = HexColor('#F3F4F6')


# =========================================================
# 3) SAYFA BOYUTLARI
# =========================================================
SAYFA_G, SAYFA_Y = A4
KENAR = 1.4 * cm


# =========================================================
# 4) ÖZEL CANVAS — Header, Footer, Filigran, Logo
# =========================================================
class LumispacCanvas(canvas_module.Canvas):
    def __init__(self, *args, **kwargs):
        self._baslik = kwargs.pop('baslik', '')
        self._firma = kwargs.pop('firma', 'LUMİSPAC AMBALAJ SANAYİ')
        self._sayfa_no = 0
        super().__init__(*args, **kwargs)

    def showPage(self):
        self._sayfa_no += 1
        self._ciz_arka()
        super().showPage()

    def _ciz_arka(self):
        w, h = A4

        # --- FİLİGRAN ---
        self.saveState()
        self.setFillColor(R.KIRMIZI)
        self.setFillAlpha(0.012)
        self.setFont(FONT_B, 58)
        self.translate(w / 2 + 10, h / 2 + 60)
        self.rotate(28)
        self.drawCentredString(0, 0, 'LUMİSPAC')
        self.restoreState()

        # --- HEADER BANT ---
        bant_y = h - 2.5 * cm
        self.setFillColor(R.KIRMIZI)
        self.rect(0, bant_y, w, 2.5 * cm, fill=1, stroke=0)

        # Dekoratif çapraz şerit
        self.saveState()
        self.setFillColor(R.KIRMIZI_KOYU)
        self.setFillAlpha(0.4)
        p = self.beginPath()
        p.moveTo(w - 2 * cm, bant_y)
        p.lineTo(w, bant_y)
        p.lineTo(w, bant_y + 2.5 * cm)
        p.lineTo(w - 3.5 * cm, bant_y + 2.5 * cm)
        p.close()
        self.drawPath(p, fill=1, stroke=0)
        self.restoreState()

        # --- LOGO (beyaz kare içinde kırmızı LP) ---
        logox = KENAR
        logoy = bant_y + 0.5 * cm
        logob = 1.5 * cm
        self.saveState()
        self.setFillColor(R.BEYAZ)
        self.roundRect(logox, logoy, logob, logob, 6, fill=1, stroke=0)
        self.setFillColor(R.KIRMIZI)
        self.setFont(FONT_B, 15)
        self.drawCentredString(logox + logob / 2, logoy + logob / 2 - 5, 'LP')
        self.restoreState()

        # --- FIRMA ADI ---
        self.setFillColor(R.BEYAZ)
        self.setFont(FONT_B, 13)
        self.drawString(logox + logob + 12, bant_y + 1.55 * cm, self._firma)
        self.setFillAlpha(0.85)
        self.setFont(FONT_N, 8)
        self.drawString(logox + logob + 12, bant_y + 1.05 * cm, 'B2B Finans & Üretim Yönetimi')

        # --- SAĞ ÜST ---
        self.setFillAlpha(0.9)
        self.setFont(FONT_N, 7.5)
        self.drawRightString(w - KENAR, bant_y + 1.55 * cm, 'LUMISPAC SİSTEMİ')
        self.setFont(FONT_N, 7)
        self.drawRightString(w - KENAR, bant_y + 1.15 * cm, datetime.now().strftime('%d.%m.%Y'))
        self.setFillAlpha(1)

        # --- FOOTER ---
        footer_y = 1.2 * cm
        self.setStrokeColor(R.KIRMIZI)
        self.setLineWidth(0.7)
        self.line(KENAR, footer_y + 0.4 * cm, w - KENAR, footer_y + 0.4 * cm)
        self.setFont(FONT_N, 7)
        self.setFillColor(R.GRI)
        yil = datetime.now().year
        self.drawString(KENAR, footer_y, f'{self._firma} © {yil}')
        if self._baslik:
            self.drawCentredString(w / 2, footer_y, self._baslik[:55])
        self.drawRightString(w - KENAR, footer_y, f'Sayfa {self._sayfa_no}')


# =========================================================
# 5) YAZI STİLLERİ
# =========================================================
def _stiller():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle('Baslik', fontName=FONT_B, fontSize=20,
                          textColor=R.KIRMIZI, leading=24, spaceAfter=2))
    s.add(ParagraphStyle('BolumBas', fontName=FONT_B, fontSize=10.5,
                          textColor=R.KIRMIZI, leading=14))
    s.add(ParagraphStyle('Metin', fontName=FONT_N, fontSize=9.5,
                          textColor=R.METIN, leading=13))
    s.add(ParagraphStyle('Huc', fontName=FONT_N, fontSize=9,
                          textColor=R.METIN, leading=12))
    s.add(ParagraphStyle('HucK', fontName=FONT_B, fontSize=9,
                          textColor=R.METIN, leading=12))
    s.add(ParagraphStyle('KucukK', fontName=FONT_B, fontSize=8,
                          textColor=R.GRI, leading=11))
    return s


# =========================================================
# 6) PARA BİRİMİ FORMATI
# =========================================================
def _tl(v):
    return _tl_util(v, 2)



# =========================================================
# 7) BELGE TİP SÖZLÜĞÜ
# =========================================================
def _belge_tipler():
    return {
        'teklif': {
            'baslik': 'FİYAT TEKLİFİ',
            'no_label': 'TEKLİF NO',
            'tarih_label': 'TEKLİF TARİHİ',
            'gecerlilik': 'Geçerlilik: 30 gün',
            'musteri_label': 'SAYIN',
            'imza_sol': 'LUMİSPAC',
            'imza_sag': 'MÜŞTERİ ONAYI',
            'kolon_fiyat': True,
            'kolon_adet': True,
            'kolon_toplam': True,
            'toplam_kutusu': True,
            'odeme_kosulu': True,
            'ozel_alanlar': [],
        },
        'siparis': {
            'baslik': 'SİPARİŞ FORMU',
            'no_label': 'SİPARİŞ NO',
            'tarih_label': 'SİPARİŞ TARİHİ',
            'gecerlilik': '',
            'musteri_label': 'SAYIN',
            'imza_sol': 'LUMİSPAC',
            'imza_sag': 'MÜŞTERİ ONAYI',
            'kolon_fiyat': True,
            'kolon_adet': True,
            'kolon_toplam': True,
            'toplam_kutusu': True,
            'odeme_kosulu': False,
            'ozel_alanlar': ['teslimat'],
        },
        'irsaliye': {
            'baslik': 'SEVK İRSALİYESİ',
            'no_label': 'İRSALİYE NO',
            'tarih_label': 'DÜZENLEME TARİHİ',
            'gecerlilik': '',
            'musteri_label': 'SEVK EDİLEN',
            'imza_sol': 'TESLİM EDEN (LUMİSPAC)',
            'imza_sag': 'TESLİM ALAN (ŞOFÖR)',
            'kolon_fiyat': False,
            'kolon_adet': False,
            'kolon_toplam': False,
            'toplam_kutusu': False,
            'odeme_kosulu': False,
            'ozel_alanlar': ['teslimat', 'arac'],
        },
        'fatura': {
            'baslik': 'FATURA',
            'no_label': 'FATURA NO',
            'tarih_label': 'FATURA TARİHİ',
            'gecerlilik': '',
            'musteri_label': 'SAYIN',
            'imza_sol': 'LUMİSPAC',
            'imza_sag': '',
            'kolon_fiyat': True,
            'kolon_adet': True,
            'kolon_toplam': True,
            'toplam_kutusu': True,
            'odeme_kosulu': True,
            'ozel_alanlar': ['fatura'],
        },
    }


# =========================================================
# 8) ORTAK BELGE ÜRETİCİ (Başlangıç)
# =========================================================
def ortak_belge_pdf(belge, ayarlar, tip='teklif'):
    buf = io.BytesIO()
    s = _stiller()
    firma = ayarlar.get('company') or 'LUMİSPAC AMBALAJ SANAYİ'
    iban = ayarlar.get('iban') or ''
    not_metni = ayarlar.get('note') or 'Ödeme %50 peşin, bakiye sevkiyat günü alınır.'
    vat = float(ayarlar.get('vat') or 20)

    t = _belge_tipler().get(tip, _belge_tipler()['teklif'])

    bno = belge.get('no') or '—'
    tarih_str = (belge.get('date') or '')[:10]
    try:
        tarih = datetime.strptime(tarih_str, '%Y-%m-%d').strftime('%d.%m.%Y')
    except (ValueError, TypeError):
        tarih = tarih_str or '—'

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=KENAR, rightMargin=KENAR,
        topMargin=2.9 * cm, bottomMargin=1.6 * cm,
        title=f'{t["baslik"]} {bno}',
        author=firma,
    )

    hikaye = []

    # ---------- BAŞLIK BLOĞU ----------
    baslik_par = Paragraph(
        f'<font color="#FFFFFF" size="20"><b>{t["baslik"]}</b></font>',
        s['Baslik']
    )
    qno_par = Paragraph(
        f'<para align="right">'
        f'<font color="#FFFFFF" size="8">{t["no_label"]}</font><br/>'
        f'<font color="#FFFFFF" size="14"><b>{bno}</b></font>'
        f'</para>',
        s['Metin']
    )
    baslik_kutu = Table(
        [[baslik_par, qno_par]],
        colWidths=[10.5 * cm, 6.6 * cm]
    )
    baslik_kutu.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), R.KIRMIZI),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (0, 0), 16),
        ('RIGHTPADDING', (1, 0), (1, 0), 16),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))
    hikaye.append(baslik_kutu)
    hikaye.append(Spacer(1, 10))

    # ---------- MÜŞTERİ BİLGİ KUTUSU ----------
    musteri = belge.get('customer') or '—'
    sag_html = (
        f'<para align="right">'
        f'<font size="7.5" color="#6B7280">{t["tarih_label"]}</font><br/>'
        f'<font size="11"><b>{tarih}</b></font>'
    )
    if t.get('gecerlilik'):
        sag_html += f'<br/><font size="7.5" color="#6B7280">{t["gecerlilik"]}</font>'
    sag_html += '</para>'

    musteri_kutu = Table(
        [[
            Paragraph(
                f'<font size="7.5" color="#6B7280">{t["musteri_label"]}</font><br/>'
                f'<font size="12" color="#C8102E"><b>{musteri}</b></font>',
                s['Metin']
            ),
            Paragraph(sag_html, s['Metin'])
        ]],
        colWidths=[10 * cm, 7.1 * cm]
    )
    musteri_kutu.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), R.GRI_CUKUR),
        ('BOX', (0, 0), (-1, -1), 0.5, R.GRI_ACIK),
        ('LEFTPADDING', (0, 0), (-1, -1), 14),
        ('RIGHTPADDING', (0, 0), (-1, -1), 14),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    hikaye.append(musteri_kutu)
    hikaye.append(Spacer(1, 8))

    # ---------- ÖZEL BİLGİ KUTUSU ----------
    ozel = t.get('ozel_alanlar') or []
    bilgi_listesi = []

    if 'teslimat' in ozel:
        dl = belge.get('delivery') or {}
        d_tarih = (dl.get('date') or '').strip()
        d_not = (dl.get('note') or '').strip()
        if d_tarih:
            bilgi_listesi.append(('📅', 'Teslimat Tarihi', d_tarih, True))
        if d_not:
            bilgi_listesi.append(('📝', 'Teslimat Notu', d_not, False))

    if 'arac' in ozel:
        arac = belge.get('plate') or ayarlar.get('default_plate') or ''
        sofor = belge.get('driver') or ayarlar.get('default_driver') or ''
        telefon = belge.get('driver_phone') or ayarlar.get('default_driver_phone') or ''
        if arac:
            bilgi_listesi.append(('🚚', 'Araç Plakası', arac, True))
        if sofor:
            bilgi_listesi.append(('👤', 'Şoför', sofor, False))
        if telefon:
            bilgi_listesi.append(('📞', 'Şoför Telefonu', telefon, False))

    if 'fatura' in ozel:
        vkn = ayarlar.get('vkn') or ''
        vd = ayarlar.get('tax_office') or ''
        adres = ayarlar.get('address') or ''
        if vkn:
            bilgi_listesi.append(('🔢', 'VKN / TCKN', vkn, True))
        if vd:
            bilgi_listesi.append(('🏢', 'Vergi Dairesi', vd, False))
        if adres:
            bilgi_listesi.append(('📍', 'Adres', adres, False))

    if bilgi_listesi:
        satir_listesi = []
        for ikon, etiket, deger, kalin in bilgi_listesi:
            if kalin:
                html = (
                    f'<font size="10" color="#6B7280">{ikon}</font>  '
                    f'<font size="7.5" color="#6B7280">{etiket}:</font>  '
                    f'<font size="10" color="#1B1F27"><b>{deger}</b></font>'
                )
            else:
                html = (
                    f'<font size="9" color="#6B7280">{ikon}</font>  '
                    f'<font size="7.5" color="#6B7280">{etiket}:</font>  '
                    f'<font size="9.5" color="#1B1F27">{deger}</font>'
                )
            satir_listesi.append([Paragraph(html, s['Metin'])])

        bilgi_tablo = Table(satir_listesi, colWidths=[17.1 * cm])
        bilgi_tablo.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), R.GRI_CUKUR),
            ('BOX', (0, 0), (-1, -1), 0.5, R.GRI_ACIK),
            ('LEFTPADDING', (0, 0), (-1, -1), 14),
            ('RIGHTPADDING', (0, 0), (-1, -1), 14),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROUNDEDCORNERS', [6, 6, 6, 6]),
        ]))
        hikaye.append(bilgi_tablo)
        hikaye.append(Spacer(1, 8))

    # ---------- ÜRÜN TABLOSU ----------
    kolon_fiyat = t.get('kolon_fiyat', True)
    kolon_adet = t.get('kolon_adet', True)
    kolon_toplam = t.get('kolon_toplam', True)

    b = [
        Paragraph('<font color="#FFFFFF" size="8"><b>#</b></font>', s['Metin']),
        Paragraph('<font color="#FFFFFF" size="8"><b>ÜRÜN KODU</b></font>', s['Metin']),
        Paragraph('<font color="#FFFFFF" size="8"><b>ÜRÜN AÇIKLAMASI</b></font>', s['Metin']),
        Paragraph('<para align="right"><font color="#FFFFFF" size="8"><b>KOLİ</b></font></para>', s['Metin']),
    ]
    if kolon_adet:
        b.append(Paragraph('<para align="right"><font color="#FFFFFF" size="8"><b>ADET</b></font></para>', s['Metin']))
    if kolon_fiyat:
        b.append(Paragraph('<para align="right"><font color="#FFFFFF" size="8"><b>BİRİM FİYAT</b></font></para>', s['Metin']))
    if kolon_toplam:
        b.append(Paragraph('<para align="right"><font color="#FFFFFF" size="8"><b>TOPLAM</b></font></para>', s['Metin']))

    satirlar = [b]
    zebra = []
    lines = belge.get('lines') or []

    for idx, l in enumerate(lines):
        birim = float(l.get('price') or 0)
        toplam = float(l.get('total') or 0)
        kod = str(l.get('code') or '')
        ad = str(l.get('name') or '')
        boxes = int(float(l.get('boxes') or 0))
        weight = l.get('weight')
        qty_per_box = int(float(l.get('qty') or 0))
        toplam_adet = boxes * qty_per_box if qty_per_box else 0

        ad_html = f'<b>{ad}</b>'
        if weight:
            ad_html += f' <font size="7" color="#6B7280">({weight}g)</font>'

        satir = [
            Paragraph(f'<font color="#6B7280" size="9">{idx+1}</font>', s['Metin']),
            Paragraph(f'<font size="8.5" color="#4B5563"><b>{kod}</b></font>', s['Metin']),
            Paragraph(ad_html, s['Huc']),
            Paragraph(f'<para align="right"><b>{boxes:,}</b></para>'.replace(',', '.'), s['Huc']),
        ]
        if kolon_adet:
            satir.append(Paragraph(f'<para align="right">{toplam_adet:,}</para>'.replace(',', '.'), s['Huc']))
        if kolon_fiyat:
            satir.append(Paragraph(f'<para align="right">{_tl(birim)}</para>', s['Huc']))
        if kolon_toplam:
            satir.append(Paragraph(f'<para align="right"><b>{_tl(toplam)}</b></para>', s['HucK']))

        satirlar.append(satir)
        if idx % 2 == 1:
            zebra.append(('BACKGROUND', (0, idx + 1), (-1, idx + 1), R.GRI_CUKUR))

    sutun_sayisi = 4 + (1 if kolon_adet else 0) + (1 if kolon_fiyat else 0) + (1 if kolon_toplam else 0)
    if sutun_sayisi == 4:
        col_w = [1.0 * cm, 3.2 * cm, 10.5 * cm, 2.4 * cm]
    elif sutun_sayisi == 5:
        col_w = [1.0 * cm, 3.0 * cm, 8.5 * cm, 2.3 * cm, 2.3 * cm]
    elif sutun_sayisi == 6:
        col_w = [0.9 * cm, 2.8 * cm, 6.5 * cm, 2.0 * cm, 2.0 * cm, 2.9 * cm]
    else:
        col_w = [0.8 * cm, 2.3 * cm, 4.6 * cm, 1.5 * cm, 1.8 * cm, 2.6 * cm, 3.5 * cm]

    tablo = Table(satirlar, colWidths=col_w)
    tablo.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), R.KIRMIZI),
        ('TEXTCOLOR', (0, 0), (-1, 0), R.BEYAZ),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, 0), 1.2, R.KIRMIZI),
        ('LINEBELOW', (0, 1), (-1, -1), 0.4, R.GRI_ACIK),
    ] + zebra))
    hikaye.append(tablo)
    hikaye.append(Spacer(1, 12))

    # ---------- TOPLAM KUTUSU VEYA TESLİM ÖZETİ ----------
    if t.get('toplam_kutusu', True):
        ara_toplam = float(belge.get('sale') or 0)
        iskonto = float(belge.get('disc') or 0)
        iskonto_pct = float(belge.get('d') or 0)
        kdv = float(belge.get('vat') or 0)
        genel = float(belge.get('grand') or 0)

        toplam_satirlari = [
            [Paragraph('<font size="9.5" color="#4B5563">Ara Toplam</font>', s['Metin']),
             Paragraph(f'<para align="right"><font size="10">{_tl(ara_toplam)}</font></para>', s['Metin'])],
        ]
        if iskonto > 0:
            toplam_satirlari.append([
                Paragraph(f'<font size="9.5" color="#4B5563">İskonto (%{iskonto_pct:.1f})</font>', s['Metin']),
                Paragraph(f'<para align="right"><font size="10" color="#C8102E">− {_tl(iskonto)}</font></para>', s['Metin']),
            ])
        toplam_satirlari.append([
            Paragraph(f'<font size="9.5" color="#4B5563">KDV (%{vat:.0f})</font>', s['Metin']),
            Paragraph(f'<para align="right"><font size="10">{_tl(kdv)}</font></para>', s['Metin']),
        ])
        toplam_satirlari.append([
            Paragraph('<font size="11" color="#FFFFFF"><b>GENEL TOPLAM</b></font>', s['Metin']),
            Paragraph(f'<para align="right"><font size="13" color="#FFFFFF"><b>{_tl(genel)}</b></font></para>', s['Metin']),
        ])

        toplam_tablo = Table(toplam_satirlari, colWidths=[4 * cm, 4 * cm])
        toplam_tablo.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 14),
            ('RIGHTPADDING', (0, 0), (-1, -1), 14),
            ('TOPPADDING', (0, 0), (-1, -2), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -2), 6),
            ('TOPPADDING', (0, -1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
            ('BACKGROUND', (0, -1), (-1, -1), R.KIRMIZI),
            ('BOX', (0, -1), (-1, -1), 1, R.KIRMIZI),
        ]))

        sarmal = Table([['', toplam_tablo]], colWidths=[9.1 * cm, 8 * cm])
        sarmal.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, 0), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        hikaye.append(sarmal)
        hikaye.append(Spacer(1, 12))
    else:
        # İrsaliye: Teslim özeti
        top_koli = sum(int(float(l.get('boxes') or 0)) for l in lines)
        ozet_html = (
            f'<para align="center">'
            f'<font size="12" color="#6B7280">📦  TESLİM EDİLEN:</font>'
            f'  '
            f'<font size="16" color="#C8102E"><b>{top_koli:,}</b></font>'
            f'<font size="12" color="#6B7280"> KOLİ</font>'
            f'</para>'
        ).replace(',', '.')
        ozet_par = Paragraph(ozet_html, s['Metin'])
        ozet_tablo = Table([[ozet_par]], colWidths=[17.1 * cm])
        ozet_tablo.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), R.KIRMIZI_ACIK),
            ('BOX', (0, 0), (-1, -1), 1.2, R.KIRMIZI),
            ('LEFTPADDING', (0, 0), (-1, -1), 14),
            ('RIGHTPADDING', (0, 0), (-1, -1), 14),
            ('TOPPADDING', (0, 0), (-1, -1), 14),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROUNDEDCORNERS', [8, 8, 8, 8]),
        ]))
        hikaye.append(ozet_tablo)
        hikaye.append(Spacer(1, 12))

    # ---------- ÖDEME KOŞULLARI ----------
    if t.get('odeme_kosulu') and (not_metni or iban):
        kosul_satirlari = []
        if not_metni:
            kosul_satirlari.append([Paragraph(f'<font size="9">{not_metni}</font>', s['Metin'])])
        if iban:
            kosul_satirlari.append([
                Paragraph(f'<font size="9"><b>IBAN:</b> {iban}</font>', s['Metin'])
            ])

        kosul_tablo = Table(kosul_satirlari, colWidths=[17.1 * cm])
        kosul_tablo.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), R.KIRMIZI_ACIK),
            ('BOX', (0, 0), (-1, -1), 1, R.KIRMIZI),
            ('LEFTPADDING', (0, 0), (-1, -1), 14),
            ('RIGHTPADDING', (0, 0), (-1, -1), 14),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('ROUNDEDCORNERS', [6, 6, 6, 6]),
        ]))

        baslik_kosul = Paragraph(
            '<font color="#C8102E" size="10.5"><b>🔒 ÖDEME KOŞULLARI</b></font>',
            s['Metin']
        )
        hikaye.append(KeepTogether([baslik_kosul, Spacer(1, 4), kosul_tablo]))
        hikaye.append(Spacer(1, 14))

    # ---------- İMZA ALANLARI ----------
    imza_sol_html = f'<font size="8" color="#6B7280">{t["imza_sol"]}</font>'
    if t['imza_sag']:
        imza_sag_html = f'<para align="right"><font size="8" color="#6B7280">{t["imza_sag"]}</font></para>'
        imza_tablo = Table(
            [[Paragraph(imza_sol_html, s['Metin']), Paragraph(imza_sag_html, s['Metin'])]],
            colWidths=[8.55 * cm, 8.55 * cm],
            rowHeights=[1.3 * cm]
        )
        imza_tablo.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ('LEFTPADDING', (0, 0), (0, 0), 0),
            ('RIGHTPADDING', (0, 0), (0, 0), 20),
            ('LEFTPADDING', (1, 0), (1, 0), 20),
            ('RIGHTPADDING', (1, 0), (1, 0), 0),
            ('LINEBELOW', (0, 0), (0, 0), 0.8, R.GRI_KOYU),
            ('LINEBELOW', (1, 0), (1, 0), 0.8, R.GRI_KOYU),
        ]))
    else:
        imza_tablo = Table(
            [[Paragraph(imza_sol_html, s['Metin']), '']],
            colWidths=[8.55 * cm, 8.55 * cm],
            rowHeights=[1.3 * cm]
        )
        imza_tablo.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ('LEFTPADDING', (0, 0), (0, 0), 0),
            ('RIGHTPADDING', (0, 0), (0, 0), 20),
            ('LINEBELOW', (0, 0), (0, 0), 0.8, R.GRI_KOYU),
        ]))
    hikaye.append(imza_tablo)

    # ---------- PDF ÜRET ----------
    def _cv(*args, **kwargs):
        return LumispacCanvas(*args, baslik=f'{t["baslik"]} — {bno}', firma=firma, **kwargs)

    doc.build(hikaye, canvasmaker=_cv)
    buf.seek(0)
    return buf


# =========================================================
# 9) KISA FONKSİYONLAR — 4 BELGE TİPİ
# =========================================================
def teklif_pdf(belge, ayarlar):
    return ortak_belge_pdf(belge, ayarlar, tip='teklif')


def siparis_pdf(belge, ayarlar):
    return ortak_belge_pdf(belge, ayarlar, tip='siparis')


def irsaliye_pdf(belge, ayarlar):
    return ortak_belge_pdf(belge, ayarlar, tip='irsaliye')


def fatura_pdf(belge, ayarlar):
    return ortak_belge_pdf(belge, ayarlar, tip='fatura')


# =========================================================
# 10) TEST BLOĞU
# =========================================================
if __name__ == '__main__':
    test_ayarlar = {
        'company': 'LUMİSPAC AMBALAJ SANAYİ LTD. ŞTİ.',
        'iban': 'TR12 3456 7890 1234 5678 9012 34',
        'note': 'Ödeme %50 peşin, bakiye sevkiyat günü alınır.',
        'vat': 20,
        'vkn': '1234567890',
        'tax_office': 'İstanbul - Kadıköy',
        'address': 'Örnek Mah. Sanayi Cad. No:42 Kadıköy / İstanbul',
        'default_plate': '34 ABC 123',
        'default_driver': 'Ahmet Yılmaz',
        'default_driver_phone': '0532 123 45 67',
    }

    test_belge = {
        'no': 'TKF-2026-0042',
        'date': '2026-10-12',
        'customer': 'ÖRNEK MÜŞTERİ A.Ş.',
        'sale': 12500.00,
        'disc': 1250.00,
        'd': 10.0,
        'vat': 2250.00,
        'grand': 13500.00,
        'delivery': {
            'date': '15.10.2026',
            'note': 'Sabah 09:00 - 12:00 arası teslim.',
        },
        'plate': '34 ABC 123',
        'driver': 'Ahmet Yılmaz',
        'driver_phone': '0532 123 45 67',
        'lines': [
            {'code': 'LP-001', 'name': 'Kraft Kutu 30x20x15', 'boxes': 100, 'qty': 50, 'price': 12.50, 'total': 1250.00, 'weight': 180},
            {'code': 'LP-002', 'name': 'Oluklu Mukavva Kutu 40x30x20', 'boxes': 80, 'qty': 40, 'price': 22.00, 'total': 1760.00, 'weight': 250},
            {'code': 'LP-003', 'name': 'Ambalaj Bandı 48mm', 'boxes': 200, 'qty': 12, 'price': 8.75, 'total': 1750.00},
            {'code': 'LP-004', 'name': 'Streç Film 500mm', 'boxes': 50, 'qty': 6, 'price': 45.00, 'total': 2250.00, 'weight': 2100},
            {'code': 'LP-005', 'name': 'Hava Kabarcıklı Naylon 100cm', 'boxes': 30, 'qty': 25, 'price': 18.50, 'total': 555.00},
        ],
    }

    import sys
    cikti_klasor = os.path.dirname(os.path.abspath(__file__))

    for tip, fn in [('teklif', teklif_pdf), ('siparis', siparis_pdf),
                    ('irsaliye', irsaliye_pdf), ('fatura', fatura_pdf)]:
        try:
            pdf_data = fn(test_belge, test_ayarlar)
            dosya = os.path.join(cikti_klasor, f'test_{tip}.pdf')
            with open(dosya, 'wb') as f:
                f.write(pdf_data.getvalue())
            print(f'[OK] {tip:10s} -> {dosya}  ({len(pdf_data.getvalue()):,} bayt)')
        except Exception as e:
            print(f'[HATA] {tip:10s} -> {e}', file=sys.stderr)

    print('\nTest tamamlandı. 4 PDF dosyası oluşturuldu.')