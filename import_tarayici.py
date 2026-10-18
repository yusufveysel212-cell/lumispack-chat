# import_tarayici.py
# Blueprint'lerdeki eksik import'lari bulur.

import ast
from pathlib import Path

# Hangi fonksiyon nereden gelmeli?
GEREKLI = {
    # state.py'den
    'daily_backup': 'state',
    'merge_seed': 'state',
    'stamp_backup': 'state',
    'load_products': 'state',
    'load_settings': 'state',
    'get_lock': 'state',
    'get_rate_cache': 'state',
    'get_sessions': 'state',
    'get_sessions_lock': 'state',
    'get_errors': 'state',
    'push_error': 'state',
    'save_rate': 'state',
    'update_rate': 'state',
    '_session_al': 'state',
    '_session_bilgi': 'state',
    
    # utils.py'den
    'f': 'utils',
    'num': 'utils',
    'fmt': 'utils',
    'TL': 'utils',
    'pct': 'utils',
    'write_json': 'utils',
    'read_json': 'utils',
    'yeni_id': 'utils',
    'hash_sifre': 'utils',
    'sifre_dogrula': 'utils',
    'simdi_iso': 'utils',
    'bugun_str': 'utils',
    
    # helpers.py'den
    'normalize': 'helpers',
    'validate': 'helpers',
    'calc': 'helpers',
    'xlsx_response': 'helpers',
    'parse_num': 'helpers',
    'order_lines': 'helpers',
    'norm_dealer': 'helpers',
    'sig': 'helpers',
    'same': 'helpers',
    
    # config.py'den
    'DATA_FILE': 'config',
    'SET_FILE': 'config',
    'DEFAULT_SETTINGS': 'config',
    'SEED_PRODUCTS': 'config',
}

# Bunlar Python'un kendi built-in'leri veya framework'ten gelir, atla
YOKSAY = {
    'jsonify', 'request', 'send_file', 'send_from_directory',
    'Blueprint', 'render_template', 'redirect', 'url_for',
    'print', 'len', 'str', 'int', 'float', 'dict', 'list', 'set', 'tuple',
    'range', 'enumerate', 'zip', 'sorted', 'sum', 'min', 'max', 'abs',
    'round', 'open', 'isinstance', 'hasattr', 'getattr', 'setattr',
    'datetime', 'time', 'os', 'io', 'json', 're', 'uuid', 'secrets',
    'session', 'abort', 'make_response', 'Response',
}

api_klasoru = Path('api')
sorunlu = []
temiz = []

print("=" * 60)
print("  BLUEPRINT IMPORT TARAYICISI")
print("=" * 60)

for dosya in sorted(api_klasoru.glob('*.py')):
    if dosya.name == '__init__.py':
        continue
    
    icerik = dosya.read_text(encoding='utf-8')
    tree = ast.parse(icerik)
    
    # Import edilenleri topla
    import_edilenler = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                isim = alias.asname if alias.asname else alias.name
                import_edilenler.add(isim)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                isim = alias.asname if alias.asname else alias.name
                import_edilenler.add(isim.split('.')[0])
    
    # Kullanilan fonksiyonlari topla
    kullanilanlar = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                kullanilanlar.add(node.func.id)
    
    # Eksikleri bul
    eksikler = []
    for kullanim in sorted(kullanilanlar):
        if kullanim in YOKSAY:
            continue
        if kullanim in GEREKLI and kullanim not in import_edilenler:
            eksikler.append((kullanim, GEREKLI[kullanim]))
    
    if eksikler:
        print(f"\n[HATA] {dosya.name}")
        for func, kaynak in eksikler:
            print(f"   EKSIK: {func:25} -> {kaynak}.py'den import edilmeli")
        sorunlu.append(dosya.name)
    else:
        print(f"[OK]   {dosya.name}")
        temiz.append(dosya.name)

print()
print("=" * 60)
print(f"  OZET: {len(temiz)} temiz, {len(sorunlu)} sorunlu")
print("=" * 60)

if sorunlu:
    print("\nSorunlu dosyalar:")
    for d in sorunlu:
        print(f"   - {d}")