# -*- coding: utf-8 -*-
"""LUMISPAC için açıkça çalıştırılan, tekrar çalıştırılabilir demo veri aracı.

Komut satırından `python demo_veri.py yukle` veya `python demo_veri.py sifirla`
ile çalıştırılır. Uygulama başlangıcında çağrılmaz.
"""
import copy
import json
import os
import shutil
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

from config import BASE
from utils import hash_sifre


DEMO_USERS = [
    ("TEST-DEMO-USER-ADMIN", "test_admin", "TEST - Yönetici", "yonetici", "TestOnly-Admin-5001!", {}),
    ("TEST-DEMO-USER-SALES", "test_satis", "TEST - Saha Satış", "satis", "TestOnly-Satis-5001!", {"siparis_sevk": "yazar"}),
    ("TEST-DEMO-USER-PROD", "test_uretim", "TEST - Üretim Şefi", "uretim", "TestOnly-Uretim-5001!", {}),
    ("TEST-DEMO-USER-WH", "test_depo", "TEST - Depo Sorumlusu", "depo", "TestOnly-Depo-5001!", {}),
    ("TEST-DEMO-USER-FIN", "test_finans", "TEST - Finans", "muhasebe", "TestOnly-Finans-5001!", {}),
]

PRODUCTS = [
    {"id": "TEST-DEMO-PRODUCT-READY", "code": "TEST-READY-01", "name": "TEST - Stoklu Numune", "weight": 1, "qty": 10, "fire": 0, "shipping": 0, "labor": 0, "volume": 0.01, "sale": 100, "stock": 0, "active": True},
    {"id": "TEST-DEMO-PRODUCT-SHORTAGE", "code": "TEST-PRODUCTION-01", "name": "TEST - Üretim Gereken Numune", "weight": 1, "qty": 10, "fire": 0, "shipping": 0, "labor": 0, "volume": 0.01, "sale": 100, "stock": 0, "active": True},
]

DEALERS = [
    {"id": "TEST-DEMO-DEALER-READY", "name": "TEST - Hazır Stok Bayisi", "contact": "TEST - Demo İrtibatı", "discount": 0, "prices": {}, "owner_user_id": "TEST-DEMO-USER-SALES"},
    {"id": "TEST-DEMO-DEALER-SHORTAGE", "name": "TEST - Üretim Bayisi", "contact": "TEST - Demo İrtibatı", "discount": 0, "prices": {}, "owner_user_id": "TEST-DEMO-USER-SALES"},
]


def _line(code, name, boxes, total):
    return {"code": code, "name": name, "weight": 1, "qty": 10, "volume": 0.01,
            "boxes": boxes, "koli": boxes, "unit": total / boxes, "sale": total / boxes,
            "cost": 0, "profit": total, "price": total / boxes, "total": total}


def _order(order_id, number, dealer_id, customer, code, product, boxes, amount, status="Taslak", payments=None):
    today = date.today().isoformat()
    return {
        "id": order_id, "no": number, "date": datetime.now().isoformat(timespec="minutes"),
        "dealerId": dealer_id, "owner_user_id": "TEST-DEMO-USER-SALES", "customer": customer,
        "quoteNo": "", "status": status, "history": [{"s": status, "at": datetime.now().isoformat(timespec="minutes"), "by": "TEST-DEMO-USER-ADMIN", "gerekce": "TEST - hazır senaryo"}],
        "delivery": {"date": today, "note": "TEST - demo teslimat"},
        "lines": [_line(code, product, boxes, amount)], "d": 0, "vatRate": 0,
        "sale": amount, "disc": 0, "vat": 0, "grand": amount,
        "cost": 0, "profit": amount, "paid_total": sum(p.get("amount", 0) for p in (payments or [])),
        "payments": copy.deepcopy(payments or []),
        "plate": "TEST-ARAC-01" if status == "Hazırlanıyor" else "",
        "driver": "TEST - Sürücü 01" if status == "Hazırlanıyor" else "",
        "driver_phone": "",
    }


def _fixtures():
    ready_code, ready_name = "TEST-READY-01", "TEST - Stoklu Numune"
    short_code, short_name = "TEST-PRODUCTION-01", "TEST - Üretim Gereken Numune"
    orders = [
        _order("TEST-DEMO-ORDER-READY", "TEST - SIP-HAZIR", DEALERS[0]["id"], DEALERS[0]["name"], ready_code, ready_name, 3, 300),
        _order("TEST-DEMO-ORDER-SHORTAGE", "TEST - SIP-EKSIK", DEALERS[1]["id"], DEALERS[1]["name"], short_code, short_name, 2, 200),
        _order("TEST-DEMO-ORDER-UNPAID", "TEST - SIP-ODEMESIZ", DEALERS[0]["id"], DEALERS[0]["name"], ready_code, ready_name, 1, 100, "Hazırlanıyor"),
        _order("TEST-DEMO-ORDER-PARTIAL", "TEST - SIP-KISMI", DEALERS[0]["id"], DEALERS[0]["name"], ready_code, ready_name, 1, 100, "Hazırlanıyor", [{"id": "TEST-DEMO-PAY-PARTIAL", "amount": 40, "method": "nakit", "date": date.today().isoformat(), "created_by": "TEST-DEMO-USER-FIN", "demo_tag": "TEST -"}]),
        _order("TEST-DEMO-ORDER-FULL", "TEST - SIP-TAM", DEALERS[0]["id"], DEALERS[0]["name"], ready_code, ready_name, 1, 100, "Hazırlanıyor", [{"id": "TEST-DEMO-PAY-FULL", "amount": 100, "method": "nakit", "date": date.today().isoformat(), "created_by": "TEST-DEMO-USER-FIN", "demo_tag": "TEST -"}]),
        _order("TEST-DEMO-ORDER-CHECK", "TEST - SIP-CEK", DEALERS[0]["id"], DEALERS[0]["name"], ready_code, ready_name, 1, 100, "Hazırlanıyor", [{"id": "TEST-DEMO-PAY-CHECK", "amount": 100, "method": "cek", "accepted": True, "status": "kabul edildi", "due_date": "2099-12-31", "date": date.today().isoformat(), "created_by": "TEST-DEMO-USER-FIN", "demo_tag": "TEST -"}]),
    ]
    movements = [{
        "id": "TEST-DEMO-STOCK-OPENING", "urunId": ready_code, "urunAd": ready_name,
        "tip": "giris", "miktar": 12, "tarih": date.today().isoformat(),
        "kaynak": "TEST - Açılış stoğu", "aciklama": "TEST - demo başlangıç stoğu",
        "demo_tag": "TEST -",
    }]
    for index in range(1, 5):
        movements.append({
            "id": "TEST-DEMO-STOCK-SHIP-%02d" % index, "urunId": ready_code, "urunAd": ready_name,
            "tip": "cikis", "miktar": 1, "tarih": date.today().isoformat(),
            "kaynak": "TEST - Hazırlanmış sevk senaryosu", "aciklama": "TEST - önceden hazırlanmış sevk",
            "idempotency_key": "TEST-DEMO-STOCK-SHIP-%02d" % index, "demo_tag": "TEST -",
        })
    machine_fixture = {
        "demo_tag": "TEST -", "machine": {"id": "TEST-DEMO-MACHINE-1", "name": "TEST - Makine 1", "status": "hazir"},
        "mold": {"id": "TEST-DEMO-MOLD-1", "name": "TEST - Kalıp 1"},
        "raw_materials": [
            {"id": "TEST-DEMO-RAW-PET", "name": "TEST - PET Granül", "quantity": 100, "unit": "kg", "recycled": False},
            {"id": "TEST-DEMO-RAW-RECYCLED", "name": "TEST - Geri Dönüşüm Granülü", "quantity": 0, "unit": "kg", "recycled": True},
        ],
        "minimum_stock": {ready_code: 10, short_code: 5},
        "downtime_reasons": [
            {"id": "TEST-DEMO-STOP-CHANGEOVER", "name": "TEST - Kalıp değişimi"},
            {"id": "TEST-DEMO-STOP-MAINTENANCE", "name": "TEST - Bakım"},
            {"id": "TEST-DEMO-STOP-MATERIAL", "name": "TEST - Hammadde bekleme"},
        ],
        "notice": "TEST - Referans veri; mevcut üretim/depo arayüzü bu dosyayı henüz kullanmıyor.",
    }
    return orders, movements, machine_fixture


def _read_json(path, default):
    if not path.exists():
        return copy.deepcopy(default)
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _backup(paths, root):
    existing = [path for path in paths if path.exists()]
    if not existing:
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    folder = root / "yedekler_v2" / ("demo_veri_" + stamp)
    folder.mkdir(parents=True, exist_ok=False)
    for path in existing:
        shutil.copy2(path, folder / path.name)
    return folder


def _commit(changes):
    """JSON dosyalarını birlikte güncelle; yazım hatasında özgün baytları geri koy."""
    originals = {path: path.read_bytes() if path.exists() else None for path, _ in changes}
    try:
        for path, data in changes:
            if data is None:
                path.unlink(missing_ok=True)
            else:
                _write_json(path, data)
    except Exception:
        for path, content in originals.items():
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                fd, temp_name = tempfile.mkstemp(prefix=path.name + ".rollback.", suffix=".tmp", dir=str(path.parent))
                try:
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(content)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(temp_name, path)
                finally:
                    if os.path.exists(temp_name):
                        os.unlink(temp_name)
        raise


def _merge_by_id(rows, additions, expected_prefix="TEST -"):
    if not isinstance(rows, list):
        raise ValueError("Liste biçimindeki veri bekleniyordu")
    result = copy.deepcopy(rows)
    by_id = {row.get("id"): index for index, row in enumerate(result) if isinstance(row, dict)}
    for item in additions:
        found = by_id.get(item["id"])
        if found is None:
            result.append(copy.deepcopy(item))
            by_id[item["id"]] = len(result) - 1
        else:
            current = result[found]
            marker = (current.get("name") or current.get("ad_soyad") or current.get("no")
                      or current.get("urunAd") or current.get("kaynak") or "")
            if not str(marker).startswith(expected_prefix):
                raise ValueError("Demo kimliği test olmayan kayıtla çakışıyor: " + item["id"])
            result[found] = copy.deepcopy(item)
    return result


def yukle(root=BASE):
    root = Path(root)
    users_path, products_path = root / "lumispac_users.json", root / "lumispac_data.json"
    dealers_path, orders_path, stock_path = root / "lumispac_dealers.json", root / "lumispac_orders.json", root / "lumispac_stok.json"
    fixture_path = root / "lumispac_demo_uretim.json"
    paths = [users_path, products_path, dealers_path, orders_path, stock_path, fixture_path]
    users = _read_json(users_path, {"departmanlar": [], "kullanicilar": [], "log": []})
    products = _read_json(products_path, [])
    dealers = _read_json(dealers_path, [])
    orders = _read_json(orders_path, [])
    stock = _read_json(stock_path, {"hareketler": [], "esikler": {}})
    if not isinstance(users, dict) or not isinstance(stock, dict):
        raise ValueError("Kullanıcı veya stok JSON yapısı geçersiz; dosyalar değiştirilmedi")
    if not all(isinstance(rows, list) for rows in (users.get("kullanicilar", []), products, dealers, orders, stock.get("hareketler", []))):
        raise ValueError("Veri listelerinden biri geçersiz; dosyalar değiştirilmedi")

    demo_user_records = [{
        "id": uid, "kullanici_adi": username, "ad_soyad": label, "email": "",
        "sifre_hash": hash_sifre(password), "departman_id": department, "aktif": True,
        "olusturma": datetime.now().isoformat(timespec="minutes"), "son_giris": None,
        "ilk_giris": False, "not": "TEST - demo hesabı", "izinler": copy.deepcopy(overrides),
    } for uid, username, label, department, password, overrides in DEMO_USERS]
    current_users = users.get("kullanicilar", [])
    existing_usernames = {row.get("kullanici_adi"): row for row in current_users if isinstance(row, dict)}
    for demo in demo_user_records:
        conflict = existing_usernames.get(demo["kullanici_adi"])
        if conflict and (conflict.get("id") != demo["id"] or not str(conflict.get("ad_soyad", "")).startswith("TEST -")):
            raise ValueError("Test hesabı adı mevcut kullanıcıyla çakışıyor; mevcut kullanıcı korunuyor: " + demo["kullanici_adi"])
        id_conflict = next((row for row in current_users if row.get("id") == demo["id"]), None)
        if id_conflict and not str(id_conflict.get("ad_soyad", "")).startswith("TEST -"):
            raise ValueError("Demo kullanıcı kimliği test olmayan kayıtla çakışıyor: " + demo["id"])
    user_updates = [row for row in demo_user_records if not any(x.get("id") == row["id"] for x in current_users)]
    for demo in demo_user_records:
        for index, current in enumerate(current_users):
            if current.get("id") == demo["id"]:
                current_users[index] = demo
                break
    user_records = _merge_by_id(current_users, user_updates)
    desired_orders, desired_movements, process_fixture = _fixtures()
    next_products = _merge_by_id(products, PRODUCTS)
    next_dealers = _merge_by_id(dealers, DEALERS)
    next_orders = _merge_by_id(orders, desired_orders)
    stock["hareketler"] = _merge_by_id(stock.get("hareketler", []), desired_movements, "TEST -")
    stock.setdefault("esikler", {}).update({"TEST-READY-01": 10, "TEST-PRODUCTION-01": 5})
    users["kullanicilar"] = user_records

    _backup(paths, root)
    _commit([(users_path, users), (products_path, next_products), (dealers_path, next_dealers),
             (orders_path, next_orders), (stock_path, stock), (fixture_path, process_fixture)])
    return {"users": len(demo_user_records), "products": len(PRODUCTS), "dealers": len(DEALERS),
            "orders": len(desired_orders), "stock_movements": len(desired_movements)}


def sifirla(root=BASE):
    root = Path(root)
    users_path, products_path = root / "lumispac_users.json", root / "lumispac_data.json"
    dealers_path, orders_path, stock_path = root / "lumispac_dealers.json", root / "lumispac_orders.json", root / "lumispac_stok.json"
    fixture_path = root / "lumispac_demo_uretim.json"
    paths = [users_path, products_path, dealers_path, orders_path, stock_path, fixture_path]
    users = _read_json(users_path, {"departmanlar": [], "kullanicilar": [], "log": []})
    products, dealers, orders = _read_json(products_path, []), _read_json(dealers_path, []), _read_json(orders_path, [])
    stock = _read_json(stock_path, {"hareketler": [], "esikler": {}})
    demo_ids = {row[0] for row in DEMO_USERS}
    product_ids = {row["id"] for row in PRODUCTS}
    dealer_ids = {row["id"] for row in DEALERS}
    order_ids = {row["id"] for row in _fixtures()[0]}
    movement_ids = {row["id"] for row in _fixtures()[1]}
    def checked_filter(rows, ids, marker_fields, label):
        for row in rows:
            if row.get("id") in ids and not any(str(row.get(field) or "").startswith("TEST -") for field in marker_fields):
                raise ValueError("TEST imzası olmayan %s kaydı korunuyor: %s" % (label, row.get("id")))
        return [row for row in rows if row.get("id") not in ids]

    fixture_data = _read_json(fixture_path, {}) if fixture_path.exists() else None
    if fixture_data is not None and not (
        fixture_data.get("demo_tag") == "TEST -"
        and fixture_data.get("machine", {}).get("name", "").startswith("TEST -")
    ):
        raise ValueError("Üretim demo dosyası TEST imzası taşımıyor; silinmedi")
    _backup(paths, root)
    users["kullanicilar"] = checked_filter(users.get("kullanicilar", []), demo_ids, ("ad_soyad",), "kullanıcı")
    products = checked_filter(products, product_ids, ("name",), "ürün")
    dealers = checked_filter(dealers, dealer_ids, ("name",), "bayi")
    orders = checked_filter(orders, order_ids, ("no", "customer"), "sipariş")
    stock["hareketler"] = checked_filter(stock.get("hareketler", []), movement_ids,
                                           ("urunAd", "kaynak", "aciklama"), "stok hareketi")
    for code in ("TEST-READY-01", "TEST-PRODUCTION-01"):
        stock.get("esikler", {}).pop(code, None)
    _commit([(users_path, users), (products_path, products), (dealers_path, dealers),
             (orders_path, orders), (stock_path, stock), (fixture_path, None)])
    return {"users_removed": len(demo_ids), "products_removed": len(product_ids),
            "dealers_removed": len(dealer_ids), "orders_removed": len(order_ids),
            "stock_movements_removed": len(movement_ids)}


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    if argv == ["yukle"]:
        print(json.dumps(yukle(), ensure_ascii=False, indent=2))
        return 0
    if argv == ["sifirla"]:
        print(json.dumps(sifirla(), ensure_ascii=False, indent=2))
        return 0
    print("Kullanım: python demo_veri.py yukle | sifirla")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
