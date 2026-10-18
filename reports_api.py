"""
LUMISPAC — Raporlama API Modülü
13 endpoint: 10 rapor + Excel export + sağlık + hata geçmişi.

Ana uygulamaya bağlanır:
    from reports_api import register_reports_api
    register_reports_api(app, load_products, load_orders, load_quotes, load_dealers, load_settings, recent_errors, rate_cache)
"""
import io
import logging
from datetime import datetime
from flask import jsonify, request, send_file, g

from reports import Raporlar, excel_rapor
import auth_module

log = logging.getLogger(__name__)

_URETIM_DURUM_ETIKETLERI = {
    "uretimde": "Üretimde",
    "duraklatildi": "Üretim duraklatıldı",
    "tamamlandi": "Üretim tamamlandı",
    "depo_kabul_bekliyor": "Depo kabulü bekliyor",
    "depoya_kabul_edildi": "Depoya kabul edildi",
    "kabul_reddedildi": "Depo kabulü reddedildi",
    "sevkiyata_hazir": "Sevkiyata hazır",
    "sevk_edildi": "Sevk edildi",
    "teslim_edildi": "Teslim edildi",
}


def _uretim_durum_bildirimleri(orders, user):
    """Saha satışa yalnızca kendi siparişlerinin son üretim adımlarını göster."""
    if not isinstance(user, dict) or user.get("departman_id") != "satis":
        return []
    user_id = user.get("id")
    if not user_id:
        return []
    if not auth_module.yetki_kontrol(user_id, "siparisler", "okur"):
        return []
    notifications = []
    for order in orders if isinstance(orders, list) else []:
        if not isinstance(order, dict) or str(order.get("owner_user_id") or "") != str(user_id):
            continue
        fulfillment = order.get("fulfillment") or {}
        dealer = str(order.get("customer") or "Bayisi belirtilmemiş")
        order_no = str(order.get("no") or "Sipariş")

        # Sipariş sahibine süreçteki önemli eşikleri ayrı olaylar olarak ilet.
        # Üretim geçmişi satır başına tutulur; sevkiyata hazır ise sipariş
        # seviyesinde tek bir eşik bildirimi olmalıdır.
        fulfillment_history = fulfillment.get("gecmis") or []
        ready_event = next((event for event in reversed(fulfillment_history)
                            if isinstance(event, dict)
                            and event.get("yeni_durum") == "sevkiyata_hazir"
                            and event.get("onceki_durum") != "sevkiyata_hazir"), None)
        if ready_event:
            event_time = str(ready_event.get("zaman") or "")
            notifications.append({
                "bildirim_id": "order:%s:ready:%s" % (order.get("id") or order_no, event_time),
                "bildirim_zamani": event_time,
                "tip": "siparis_asama",
                "onem": "bilgi",
                "baslik": order_no + " · Sevkiyata hazır",
                "mesaj": dealer + " siparişinin ürünleri depo stoğuna kabul edildi.",
                "ikon": "📦",
                "sayfa": "orders",
                "kayit_id": order.get("id"),
                "olay_sayisi": 1,
            })

        for event in order.get("history") or []:
            if not isinstance(event, dict) or event.get("action") not in ("ship", "deliver"):
                continue
            action = event["action"]
            event_time = str(event.get("at") or "")
            state = "sevk_edildi" if action == "ship" else "teslim_edildi"
            notifications.append({
                "bildirim_id": "order:%s:%s:%s" % (order.get("id") or order_no, action, event_time),
                "bildirim_zamani": event_time,
                "tip": "siparis_asama",
                "onem": "bilgi",
                "baslik": order_no + " · " + _URETIM_DURUM_ETIKETLERI[state],
                "mesaj": dealer + " siparişi " + _URETIM_DURUM_ETIKETLERI[state].lower() + ".",
                "ikon": "🚚" if action == "ship" else "✅",
                "sayfa": "orders",
                "kayit_id": order.get("id"),
                "olay_sayisi": 1,
            })

        events = fulfillment.get("uretim_gecmisi") or []
        latest_by_product = {}
        for event in events:
            if not isinstance(event, dict) or event.get("durum") not in _URETIM_DURUM_ETIKETLERI:
                continue
            key = str(event.get("urun_kodu") or event.get("urun_adi") or "")
            if key:
                latest_by_product[key] = event
        for event in latest_by_product.values():
            label = _URETIM_DURUM_ETIKETLERI[event["durum"]]
            name = str(event.get("urun_adi") or "Ürün")
            try:
                quantity = max(0.0, float(event.get("miktar_koli") or 0))
            except (TypeError, ValueError):
                quantity = 0.0
            notifications.append({
                "bildirim_id": str(event.get("id") or event.get("zaman") or ""),
                "bildirim_zamani": str(event.get("zaman") or ""),
                "tip": "uretim_durum",
                "onem": "uyari" if event["durum"] in ("duraklatildi", "kabul_reddedildi") else "bilgi",
                "baslik": order_no + " · Üretim durumu güncellendi",
                "mesaj": dealer + " · " + name + " · " + label + " · " + ("%.0f koli" % quantity),
                "ikon": "🏭",
                "sayfa": "orders",
                "kayit_id": order.get("id"),
                "olay_sayisi": 1,
            })
    notifications.sort(key=lambda row: row.get("bildirim_zamani", ""), reverse=True)
    return notifications[:50]


def _bildirimleri_rolle_filtrele(sonuc, user):
    """Return only notifications backed by the current user's module rights."""
    if not isinstance(sonuc, dict) or not isinstance(user, dict):
        return {"bildirimler": [], "ozet": {
            "toplam": 0, "kritik": 0, "uyari": 0, "bilgi": 0,
            "en_yuksek_onem": "yok",
        }}

    department = user.get("departman_id")
    manager = department == "yonetici"
    def can(module):
        return manager or bool(user.get("id") and auth_module.yetki_kontrol(
            user["id"], module, "okur"))

    # Module permission alone is too broad for team notifications: finance can
    # read orders but should not receive the sales team's new-order alerts.
    # The manager can oversee all teams; other roles receive only their own
    # workstream's alerts and must still hold the corresponding module access.
    requirements = {
        "kritik_stok": ("stok", {"depo", "uretim", "satinalma"}),
        "gecikmis_siparis": ("siparisler", {"satis"}),
        "bugun_siparis": ("siparisler", {"satis"}),
        "teklif_bekliyor": ("teklifler", {"satis"}),
        "bugun_teklif": ("teklifler", {"satis"}),
        "hedef_alti": ("kar_maliyet", {"finans"}),
        "zararda": ("kar_maliyet", {"finans"}),
        "maliyet_anomalisi": ("kar_maliyet", {"finans"}),
        "uretim_durum": ("siparisler", {"satis"}),
        "siparis_asama": ("siparisler", {"satis"}),
    }
    rows = [row for row in (sonuc.get("bildirimler") or [])
            if isinstance(row, dict)
            and (manager or (row.get("tip") in requirements and
                 (department in requirements[row["tip"]][1]
                  and can(requirements[row["tip"]][0]))))]
    summary = {
        "toplam": len(rows),
        "kritik": sum(1 for row in rows if row.get("onem") == "kritik"),
        "uyari": sum(1 for row in rows if row.get("onem") == "uyari"),
        "bilgi": sum(1 for row in rows if row.get("onem") == "bilgi"),
    }
    summary["en_yuksek_onem"] = next(
        (level for level in ("kritik", "uyari", "bilgi") if summary[level]), "yok")
    if isinstance(sonuc.get("ozet"), dict) and "kontrol_zamani" in sonuc["ozet"]:
        summary["kontrol_zamani"] = sonuc["ozet"]["kontrol_zamani"]
    return {"bildirimler": rows, "ozet": summary}


def _satis_bildirimlerini_sahiplikle_sinirl(sonuc, orders, quotes, user, now=None):
    """Satış özet bildirimlerini yalnızca oturum sahibinin kayıtlarından üret."""
    if not isinstance(sonuc, dict) or not isinstance(user, dict) or user.get("departman_id") != "satis":
        return sonuc
    user_id = user.get("id")
    if not user_id:
        return {**sonuc, "bildirimler": []}

    now = now or datetime.now()
    today = now.strftime("%Y-%m-%d")
    order_rows = [o for o in (orders or []) if isinstance(o, dict)
                  and str(o.get("owner_user_id") or "") == str(user_id)]
    quote_rows = [q for q in (quotes or []) if isinstance(q, dict)
                  and str(q.get("owner_user_id") or "") == str(user_id)]
    excluded = {"teslim edildi", "iptal", "cancelled", "canceled"}

    def status_text(row):
        return str(row.get("status") or "").replace("İ", "i").replace("I", "i").replace("ı", "i").lower().strip()

    # Rapor servisi şirket geneli sayıları üretir. Satış kullanıcılarında bu
    # özetleri kaldırıp aynı bildirim tiplerini yalnız kendi kayıtlarından kur.
    rows = [row for row in (sonuc.get("bildirimler") or [])
            if not isinstance(row, dict) or row.get("tip") not in {
                "gecikmis_siparis", "bugun_siparis", "teklif_bekliyor", "bugun_teklif"}]

    if auth_module.yetki_kontrol(user_id, "siparisler", "okur"):
        today_order_rows = [o for o in order_rows if str(o.get("date") or "")[:10] == today]
        today_orders = [o for o in today_order_rows if status_text(o) not in excluded]
        if today_orders:
            rows.append({
                # Stable while an order advances through the workflow, but a
                # newly created same-day order produces a fresh notification.
                "bildirim_id": "sales:%s:orders:%s:%s" % (
                    user_id, today, ",".join(sorted(
                        str(o.get("id") or o.get("no") or "") for o in today_order_rows))),
                "bildirim_zamani": today,
                "tip": "bugun_siparis", "onem": "bilgi",
                "baslik": "Bugün " + str(len(today_orders)) + " yeni sipariş",
                "mesaj": "Sana atanan siparişleri Siparişler ekranından inceleyin.",
                "ikon": "🛒", "sayfa": "orders", "olay_sayisi": len(today_orders),
            })

        overdue = []
        for order in order_rows:
            if status_text(order) in excluded:
                continue
            date_text = str((order.get("delivery") or {}).get("date") or "")[:10]
            try:
                days = (now.date() - datetime.strptime(date_text, "%Y-%m-%d").date()).days
            except (ValueError, TypeError):
                continue
            if days > 0:
                overdue.append((order, days))
        if overdue:
            longest = max(overdue, key=lambda pair: pair[1])
            order, days = longest
            rows.append({
                "bildirim_id": "sales:%s:overdue:%s" % (
                    user_id, ",".join(sorted(str(o.get("id") or o.get("no") or "") for o, _ in overdue))),
                "bildirim_zamani": today,
                "tip": "gecikmis_siparis",
                "onem": "kritik" if len(overdue) >= 3 or days >= 7 else "uyari",
                "baslik": str(len(overdue)) + " sipariş gecikmiş!",
                "mesaj": "En uzun: " + str(order.get("no") or "Sipariş") + " · " +
                         str(order.get("customer") or "Bayisi belirtilmemiş") + " · " + str(days) + " gün gecikmiş",
                "ikon": "🚨", "sayfa": "calendar", "olay_sayisi": len(overdue),
            })

    if auth_module.yetki_kontrol(user_id, "teklifler", "okur"):
        today_quotes = [q for q in quote_rows if str(q.get("date") or "")[:10] == today]
        if today_quotes:
            rows.append({
                "bildirim_id": "sales:%s:quotes:%s:%s" % (
                    user_id, today, ",".join(sorted(
                        str(q.get("id") or q.get("no") or "") for q in today_quotes))),
                "bildirim_zamani": today,
                "tip": "bugun_teklif", "onem": "bilgi",
                "baslik": "Bugün " + str(len(today_quotes)) + " yeni teklif",
                "mesaj": "Sana ait teklifleri Teklifler ekranından inceleyin.",
                "ikon": "📝", "sayfa": "quotes", "olay_sayisi": len(today_quotes),
            })

        accepted_quote_numbers = {str(o.get("quoteNo")) for o in order_rows if o.get("quoteNo")}
        waiting = []
        for quote in quote_rows:
            if str(quote.get("no") or "") in accepted_quote_numbers:
                continue
            try:
                days = (now.date() - datetime.strptime(str(quote.get("date") or "")[:10], "%Y-%m-%d").date()).days
            except (ValueError, TypeError):
                continue
            if 15 < days <= 30:
                waiting.append((quote, days))
        if waiting:
            critical = [item for item in waiting if item[1] > 25]
            rows.append({
                "bildirim_id": "sales:%s:quotes-waiting:%s" % (
                    user_id, ",".join(sorted(str(q.get("id") or q.get("no") or "") for q, _ in waiting))),
                "bildirim_zamani": today,
                "tip": "teklif_bekliyor",
                "onem": "kritik" if critical else "uyari",
                "baslik": (str(len(critical)) + " teklif 25+ gündür bekliyor!" if critical
                           else str(len(waiting)) + " teklif 15+ gündür bekliyor"),
                "mesaj": "Sana ait teklifleri müşterilerle takip edin.",
                "ikon": "📄", "sayfa": "quotes-track", "olay_sayisi": len(waiting),
            })

    sonuc = {**sonuc, "bildirimler": rows}
    return sonuc


def register_reports_api(app, load_products, load_orders, load_quotes,
                          load_dealers, load_settings,
                          recent_errors_ref=None, rate_cache_ref=None):
    """
    Raporlama endpoint'lerini Flask uygulamasına kaydeder.
    
    Args:
        app: Flask uygulaması
        load_products: () -> list[dict]
        load_orders: () -> list[dict]
        load_quotes: () -> list[dict]
        load_dealers: () -> list[dict]
        load_settings: () -> dict
        recent_errors_ref: deque referansı (hata geçmişi için, opsiyonel)
        rate_cache_ref: rate_cache dict referansı (sağlık durumu için, opsiyonel)
    """
    
    def _raporlar():
        """Her istekte güncel Raporlar instance'ı oluştur."""
        products = load_products()
        orders = load_orders()
        quotes = load_quotes()
        dealers = load_dealers()
        try:
            from helpers import _session_bilgi
            _, user = _session_bilgi()
            if user and user.get('departman_id') == 'satis':
                owner_id = user.get('id')
                dealers = [d for d in dealers if d.get('owner_user_id') == owner_id]
                dealer_ids = {d.get('id') for d in dealers}
                orders = [o for o in orders if o.get('owner_user_id') == owner_id and o.get('dealerId') in dealer_ids]
                quotes = [q for q in quotes if q.get('owner_user_id') == owner_id and q.get('dealerId') in dealer_ids]
        except Exception:
            # Kimlik bağlamı okunamıyorsa veri kapsamını genişletme.
            orders, quotes, dealers = [], [], []
        return Raporlar(
            products=products,
            orders=orders,
            quotes=quotes,
            dealers=dealers,
            settings=load_settings(),
        )
    
    # =========================================================
    # 1) GENEL ÖZET DASHBOARD
    # =========================================================
    @app.get('/api/reports/overview')
    def api_reports_overview():
        try:
            r = _raporlar()
            return jsonify(r.genel_ozet())
        except Exception as e:
            log.exception('Rapor overview hatası')
            return jsonify({'error': str(e)}), 500
    
    # =========================================================
    # 2) MALİYET KIRILIMI
    # =========================================================
    @app.get('/api/reports/cost')
    def api_reports_cost():
        try:
            urun_id = request.args.get('urun_id') or None
            r = _raporlar()
            return jsonify(r.maliyet_kirilimi(urun_id=urun_id))
        except Exception as e:
            log.exception('Rapor cost hatası')
            return jsonify({'error': str(e)}), 500
    
    # =========================================================
    # 3) KÂRLILIK ANALİZİ
    # =========================================================
    @app.get('/api/reports/profitability')
    def api_reports_profitability():
        try:
            r = _raporlar()
            return jsonify(r.karlilik_analizi())
        except Exception as e:
            log.exception('Rapor profitability hatası')
            return jsonify({'error': str(e)}), 500
    
    # =========================================================
    # 4) DUYARLILIK MATRİSİ
    # =========================================================
    @app.get('/api/reports/sensitivity')
    def api_reports_sensitivity():
        try:
            urun_id = request.args.get('urun_id') or None
            r = _raporlar()
            return jsonify(r.duyarlilik(urun_id=urun_id))
        except Exception as e:
            log.exception('Rapor sensitivity hatası')
            return jsonify({'error': str(e)}), 500
    
    # =========================================================
    # 5) DÖNEMSEL TREND
    # =========================================================
    @app.get('/api/reports/trend')
    def api_reports_trend():
        try:
            tarih_bas = request.args.get('bas')
            tarih_son = request.args.get('son')
            gruplama = request.args.get('gruplama', 'gun')
            if gruplama not in ('gun', 'hafta', 'ay', 'yil'):
                gruplama = 'gun'
            r = _raporlar()
            return jsonify(r.donemsel_trend(tarih_bas=tarih_bas, tarih_son=tarih_son, gruplama=gruplama))
        except Exception as e:
            log.exception('Rapor trend hatası')
            return jsonify({'error': str(e)}), 500
    
    # =========================================================
    # 6) BAYİ PERFORMANS
    # =========================================================
    @app.get('/api/reports/dealers')
    def api_reports_dealers():
        try:
            r = _raporlar()
            return jsonify(r.bayi_performans())
        except Exception as e:
            log.exception('Rapor dealers hatası')
            return jsonify({'error': str(e)}), 500
    
    # =========================================================
    # 7) ABC ANALİZİ
    # =========================================================
    @app.get('/api/reports/abc')
    def api_reports_abc():
        try:
            baz = request.args.get('baz', 'satis')
            if baz not in ('satis', 'kar', 'koli'):
                baz = 'satis'
            r = _raporlar()
            return jsonify(r.abc_analizi(baz=baz))
        except Exception as e:
            log.exception('Rapor abc hatası')
            return jsonify({'error': str(e)}), 500
    
    # =========================================================
    # 8) SEVKİYAT / DOLUM
    # =========================================================
    @app.get('/api/reports/shipping')
    def api_reports_shipping():
        try:
            siparis_id = request.args.get('siparis_id') or None
            r = _raporlar()
            return jsonify(r.sevkiyat_dolum(siparis_id=siparis_id))
        except Exception as e:
            log.exception('Rapor shipping hatası')
            return jsonify({'error': str(e)}), 500
    
    # =========================================================
    # 9) HEDEF MARJ
    # =========================================================
    @app.get('/api/reports/target-margin')
    def api_reports_target_margin():
        try:
            r = _raporlar()
            return jsonify(r.hedef_marj())
        except Exception as e:
            log.exception('Rapor target-margin hatası')
            return jsonify({'error': str(e)}), 500
    
    # =========================================================
    # 10) MALİYET SİMÜLATÖRÜ
    # =========================================================
    @app.post('/api/reports/simulator')
    def api_reports_simulator():
        try:
            d = request.get_json(silent=True) or {}
            def _safe_num(v, default=None):
                try:
                    if v is None or v == '':
                        return default
                    return float(v)
                except (TypeError, ValueError):
                    return default
            kur = _safe_num(d.get('kur'))
            ham_usd = _safe_num(d.get('ham_usd'))
            satis_adedi = _safe_num(d.get('satis_adedi'))
            hedef_marj = _safe_num(d.get('hedef_marj'))
            r = _raporlar()
            return jsonify(r.maliyet_simulator(
                kur=kur, ham_usd=ham_usd,
                satis_adedi=satis_adedi, hedef_marj=hedef_marj))
        except Exception as e:
            log.exception('Rapor simulator hatası')
            return jsonify({'error': str(e)}), 500
    
    # =========================================================
    # 11) EXCEL EXPORT — Çoklu Sayfa
    # =========================================================
    @app.get('/api/reports/cost-history')
    def api_reports_cost_history():
        """Maliyet geçmişi (timeline) — son N ay."""
        try:
            try:
                ay_sayisi = int(request.args.get('ay_sayisi', 12) or 12)
            except (TypeError, ValueError):
                ay_sayisi = 12
            ay_sayisi = max(1, min(36, ay_sayisi))
            return jsonify(_raporlar().maliyet_gecmisi(ay_sayisi=ay_sayisi))
        except Exception as e:
            log.exception('cost-history hatasi')
            return jsonify({'error': str(e)}), 500
    @app.get('/api/reports/target-alert')
    def api_reports_target_alert():
        """Hedef marj alarmı — hedef altı ürünler."""
        if getattr(g, 'current_user', {}).get('departman_id') == 'satis':
            return jsonify({'status': 'error', 'message': 'Bu marj özeti rolünüz için kullanılamaz'}), 403
        try:
            return jsonify(_raporlar().hedef_alarm())
        except Exception as e:
            log.exception('target-alert hatasi')
            return jsonify({'error': str(e)}), 500
    @app.get('/api/reports/price-suggestion')
    def api_reports_price_suggestion():
        """Fiyat önerisi motoru — hedef marja ulaşmak için gereken fiyatlar."""
        try:
            hedef = request.args.get('hedef_marj')
            hedef_marj = None
            if hedef is not None and hedef != '':
                try:
                    hedef_marj = float(hedef)
                except (TypeError, ValueError):
                    hedef_marj = None
            return jsonify(_raporlar().fiyat_onerisi(hedef_marj=hedef_marj))
        except Exception as e:
            log.exception('price-suggestion hatasi')
            return jsonify({'error': str(e)}), 500

    @app.get('/api/reports/projection')
    def api_reports_projection():
        """Kâr projeksiyonu — gelecek 3 ay tahmini."""
        try:
            try:
                ay_tahmin = int(request.args.get('ay', 3) or 3)
            except (TypeError, ValueError):
                ay_tahmin = 3
            ay_tahmin = max(1, min(12, ay_tahmin))
            return jsonify(_raporlar().kar_projeksiyonu(ay_tahmin=ay_tahmin))
        except Exception as e:
            log.exception('projection hatasi')
            return jsonify({'error': str(e)}), 500
    @app.get('/api/reports/anomaly')
    def api_reports_anomaly():
        """Maliyet anomalisi tespiti — normalden sapan ürünler."""
        try:
            return jsonify(_raporlar().maliyet_anomalisi())
        except Exception as e:
            log.exception('anomaly hatasi')
            return jsonify({'error': str(e)}), 500
    @app.get('/api/reports/customer-segments')
    def api_reports_customer_segments():
        """Müşteri segmentasyonu — RFM analizi."""
        try:
            return jsonify(_raporlar().musteri_segmentasyonu())
        except Exception as e:
            log.exception('customer-segments hatasi')
            return jsonify({'error': str(e)}), 500

    @app.get('/api/reports/shipping-calendar')
    def api_reports_shipping_calendar():
        """Sevkiyat takvimi — teslim tarihine göre gruplar."""
        try:
            try:
                gun = int(request.args.get('gun', 30) or 30)
            except (TypeError, ValueError):
                gun = 30
            gun = max(7, min(90, gun))
            return jsonify(_raporlar().sevkiyat_takvimi(gun_sayisi=gun))
        except Exception as e:
            log.exception('shipping-calendar hatasi')
            return jsonify({'error': str(e)}), 500

    @app.get('/api/reports/stock-forecast')
    def api_reports_stock_forecast():
        """Stok tahmini — günlük satış hızı ve tükenme tarihi."""
        try:
            try:
                pencere = int(request.args.get('pencere', 30) or 30)
            except (TypeError, ValueError):
                pencere = 30
            pencere = max(7, min(180, pencere))
            return jsonify(_raporlar().stok_tahmini(pencere_gun=pencere))
        except Exception as e:
            log.exception('stock-forecast hatasi')
            return jsonify({'error': str(e)}), 500
    @app.get('/api/reports/quote-tracking')
    def api_reports_quote_tracking():
        """Teklif takip sistemi — teklif durumları ve istatistikler."""
        try:
            try:
                gecerlilik = int(request.args.get('gecerlilik', 30) or 30)
            except (TypeError, ValueError):
                gecerlilik = 30
            gecerlilik = max(7, min(180, gecerlilik))
            return jsonify(_raporlar().teklif_takip(gecerlilik_gun=gecerlilik))
        except Exception as e:
            log.exception('quote-tracking hatasi')
            return jsonify({'error': str(e)}), 500
    @app.get('/api/reports/comparison')
    def api_reports_comparison():
        """Karşılaştırmalı rapor — 3 dönem yan yana."""
        try:
            mod = request.args.get('mod', 'bu_ay')
            if mod not in ('bu_ay', 'bu_ceyrek', 'bu_yil'):
                mod = 'bu_ay'
            return jsonify(_raporlar().karsilastirma(mod=mod))
        except Exception as e:
            log.exception('comparison hatasi')
            return jsonify({'error': str(e)}), 500
    @app.get('/api/reports/category')
    def api_reports_category():
        """Kategori raporu — Düz/Dikdörtgen/Bombeli/Peynir karşılaştırma."""
        try:
            return jsonify(_raporlar().kategori_raporu())
        except Exception as e:
            log.exception('category hatasi')
            return jsonify({'error': str(e)}), 500


    @app.get('/api/reports/weight-analysis')
    def api_reports_weight_analysis():
        """Gramaj raporu — hangi gramajlar daha kârlı?"""
        try:
            return jsonify(_raporlar().gramaj_raporu())
        except Exception as e:
            log.exception('weight-analysis hatasi')
            return jsonify({'error': str(e)}), 500

    @app.get('/api/reports/product-lifecycle')
    def api_reports_product_lifecycle():
        """Ürün yaşam döngüsü — yeni/yükselen/yıldız/düşen/ölü."""
        try:
            return jsonify(_raporlar().yasam_dongusu())
        except Exception as e:
            log.exception('product-lifecycle hatasi')
            return jsonify({'error': str(e)}), 500

    @app.get('/api/reports/profit-loss')
    def api_reports_profit_loss():
        """Kar-Zarar tablosu (P&L) — yıllık, aylık detaylı."""
        try:
            yil = request.args.get('yil')
            if yil:
                try:
                    yil = int(yil)
                except (TypeError, ValueError):
                    yil = None
            return jsonify(_raporlar().kar_zarar_tablosu(yil=yil))
        except Exception as e:
            log.exception('profit-loss hatasi')
            return jsonify({'error': str(e)}), 500

    @app.get('/api/notifications')
    def api_notifications():
        """Bildirim motoru — kritik olaylar."""
        try:
            min_onem = request.args.get('min_onem', 'bilgi')
            if min_onem not in ('bilgi', 'uyari', 'kritik'):
                min_onem = 'bilgi'
            result = _raporlar().bildirimler(min_onem=min_onem)
            user = getattr(g, "current_user", None)
            response = _bildirimleri_rolle_filtrele(result, user)
            response = _satis_bildirimlerini_sahiplikle_sinirl(
                response, load_orders(), load_quotes(), user)
            response["bildirimler"].extend(_uretim_durum_bildirimleri(load_orders(), user))
            rows = response["bildirimler"]
            response["ozet"].update({
                "toplam": len(rows),
                "kritik": sum(1 for row in rows if row.get("onem") == "kritik"),
                "uyari": sum(1 for row in rows if row.get("onem") == "uyari"),
                "bilgi": sum(1 for row in rows if row.get("onem") == "bilgi"),
            })
            response["ozet"]["en_yuksek_onem"] = next(
                (level for level in ("kritik", "uyari", "bilgi") if response["ozet"][level]), "yok")
            return jsonify(response)
        except Exception as e:
            log.exception('notifications hatasi')
            return jsonify({'error': str(e)}), 500
   
    # =========================================================
    # PDF ENDPOINT'LERİ
    # =========================================================
    # =========================================================
    # SİPARİŞ / İRSALİYE / FATURA PDF ENDPOINT'LERİ
    # =========================================================
    @app.get('/api/pdf/order/<oid>')
    def api_pdf_order(oid):
        """Sipariş Formu PDF'i."""
        try:
            mod = request.args.get('mod', 'inline')
            orders = load_orders()
            o = next((x for x in orders if x.get('id') == oid), None)
            if not o:
                return jsonify({'error': 'Sipariş bulunamadı'}), 404
            from pdf_module import siparis_pdf
            ayarlar = load_settings()
            buf = siparis_pdf(o, ayarlar)
            ad = f'Siparis_{o.get("no", "belirsiz")}.pdf'
            return send_file(
                buf,
                as_attachment=(mod == 'download'),
                download_name=ad,
                mimetype='application/pdf',
            )
        except ImportError as e:
            log.exception('pdf_module yuklenemedi')
            return jsonify({'error': 'PDF modülü yüklenemedi: ' + str(e)}), 500
        except Exception as e:
            log.exception('order pdf hatasi')
            return jsonify({'error': str(e)}), 500

    @app.get('/api/pdf/waybill/<oid>')
    def api_pdf_waybill(oid):
        """Sevk İrsaliyesi PDF'i."""
        try:
            mod = request.args.get('mod', 'inline')
            orders = load_orders()
            o = next((x for x in orders if x.get('id') == oid), None)
            if not o:
                return jsonify({'error': 'Sipariş bulunamadı'}), 404
            from pdf_module import irsaliye_pdf
            ayarlar = load_settings()
            buf = irsaliye_pdf(o, ayarlar)
            ad = f'Irsaliye_{o.get("no", "belirsiz")}.pdf'
            return send_file(
                buf,
                as_attachment=(mod == 'download'),
                download_name=ad,
                mimetype='application/pdf',
            )
        except ImportError as e:
            log.exception('pdf_module yuklenemedi')
            return jsonify({'error': 'PDF modülü yüklenemedi: ' + str(e)}), 500
        except Exception as e:
            log.exception('waybill pdf hatasi')
            return jsonify({'error': str(e)}), 500

    @app.get('/api/pdf/invoice/<oid>')
    def api_pdf_invoice(oid):
        """Fatura PDF'i."""
        try:
            mod = request.args.get('mod', 'inline')
            orders = load_orders()
            o = next((x for x in orders if x.get('id') == oid), None)
            if not o:
                return jsonify({'error': 'Sipariş bulunamadı'}), 404
            from pdf_module import fatura_pdf
            ayarlar = load_settings()
            buf = fatura_pdf(o, ayarlar)
            ad = f'Fatura_{o.get("no", "belirsiz")}.pdf'
            return send_file(
                buf,
                as_attachment=(mod == 'download'),
                download_name=ad,
                mimetype='application/pdf',
            )
        except ImportError as e:
            log.exception('pdf_module yuklenemedi')
            return jsonify({'error': 'PDF modülü yüklenemedi: ' + str(e)}), 500
        except Exception as e:
            log.exception('invoice pdf hatasi')
            return jsonify({'error': str(e)}), 500
    
    @app.get('/api/pdf/quote/<qid>')
    def api_pdf_quote(qid):
        """Teklif PDF'i — indir veya önizle."""
        try:
            mod = request.args.get('mod', 'inline')
            quotes = load_quotes()
            q = next((x for x in quotes if x.get('id') == qid), None)
            if not q:
                return jsonify({'error': 'Teklif bulunamadı'}), 404
            from pdf_module import teklif_pdf
            ayarlar = load_settings()
            buf = teklif_pdf(q, ayarlar)
            ad = f'Teklif_{q.get("no", "belirsiz")}.pdf'
            return send_file(
                buf,
                as_attachment=(mod == 'download'),
                download_name=ad,
                mimetype='application/pdf',
            )
        except ImportError as e:
            log.exception('pdf_module yuklenemedi')
            return jsonify({'error': 'PDF modülü yüklenemedi: ' + str(e)}), 500
        except Exception as e:
            log.exception('quote pdf hatasi')
            return jsonify({'error': str(e)}), 500
    # =========================================================
    # YARDIM SISTEMI API
    # =========================================================
    @app.get('/api/help/categories')
    def help_categories():
        try:
            from help_content import kategoriler
            return jsonify({'kategoriler': kategoriler()})
        except Exception as e:
            log.exception('help categories hatasi')
            return jsonify({'error': str(e)}), 500

    @app.get('/api/help/topics')
    def help_topics():
        try:
            from help_content import konular
            kat = request.args.get('kategori') or None
            return jsonify({'konular': konular(kat)})
        except Exception as e:
            log.exception('help topics hatasi')
            return jsonify({'error': str(e)}), 500

    @app.get('/api/help/topic/<slug>')
    def help_topic(slug):
        try:
            from help_content import konu_icerik
            k = konu_icerik(slug)
            if not k:
                return jsonify({'error': 'Konu bulunamadi'}), 404
            return jsonify(k)
        except Exception as e:
            log.exception('help topic hatasi')
            return jsonify({'error': str(e)}), 500

    @app.get('/api/reports/ai-forecast')
    def api_reports_ai_forecast():
        """AI Tahmin — gelecek 3 ay için satış tahmini."""
        try:
            return jsonify(_raporlar().ai_tahmin())
        except Exception as e:
            log.exception('ai-forecast hatasi')
            return jsonify({'error': str(e)}), 500


    @app.get('/api/reports/export')
    def api_reports_export():
        try:
            r = _raporlar()
            buf = excel_rapor(r)
            ad = 'Lumispac_Raporlar_%s.xlsx' % datetime.now().strftime('%Y%m%d_%H%M')
            return send_file(
                buf, as_attachment=True, download_name=ad,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        except ImportError as e:
            log.error('Excel export hatası: %s', e)
            return jsonify({'error': 'openpyxl yüklü değil. Kur: pip install openpyxl'}), 500
        except Exception as e:
            log.exception('Rapor export hatası')
            return jsonify({'error': str(e)}), 500
    
    # =========================================================
    # 12) KAYNAK SAĞLIK DURUMU
    # =========================================================
    @app.get('/api/sources/health')
    def api_sources_health():
        try:
            from state import get_rate_cache
            from rate_sources import health_snapshot

            live_cache = get_rate_cache()
            return jsonify({
                'sources': health_snapshot(),
                'rate': live_cache.get('rate') or 0,
                'source': live_cache.get('source') or '',
                'status': live_cache.get('status') or '',
                'checked_at': live_cache.get('checked_at'),
                'elapsed_ms': live_cache.get('elapsed_ms', 0),
                'zaman': datetime.now().isoformat(timespec='seconds'),
            })
        except Exception as e:
            log.exception('Sağlık hatası')
            return jsonify({'error': str(e)}), 500
    
    # =========================================================
    # 13) HATA GEÇMİŞİ (son 100 hata)
    # =========================================================
    @app.get('/api/errors/recent')
    def api_errors_recent():
        try:
            if recent_errors_ref is None:
                return jsonify({'errors': [], 'note': 'recent_errors referansı yok'})
            errors = list(recent_errors_ref)
            # Filtre: source veya içerik
            kaynak = request.args.get('kaynak')
            limit = min(100, int(request.args.get('limit', 50) or 50))
            if kaynak:
                errors = [e for e in errors if e.get('source') == kaynak]
            return jsonify({
                'errors': errors[:limit],
                'toplam': len(errors),
                'gosterilen': len(errors[:limit]),
            })
        except Exception as e:
            log.exception('Hata geçmişi hatası')
            return jsonify({'error': str(e)}), 500
    
    log.info('Raporlama API: 13 endpoint kaydedildi')
