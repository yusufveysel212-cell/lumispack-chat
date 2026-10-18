# -*- coding: utf-8 -*-
"""
LUMISPAC v3 - IMPORT DENETCISI (v1)

Her .py dosyasinda kullanilan ama import edilmeyen global isimleri bulur.

Kullanim:
    python import_denetci.py
"""
import os
import ast
import sys

BASE = os.path.dirname(os.path.abspath(__file__))

# Taranacak klasorler
TARA = ['.', 'api', 'services', 'reports']

# Kontrol edilecek ozel isimler (built-in'ler haric)
OZEL_ISIMLER = {
    'io', 'logging', 'lock', 'send_file', 'Response', 'request',
    'jsonify', 'Blueprint', 'json', 'os', 're', 'uuid', 'time',
    'shutil', 'secrets', 'hashlib', 'datetime', 'Path', 'deque',
    'webbrowser', 'threading', 'requests',
}


def dosyalari_bul():
    """Taranacak .py dosyalarini bul."""
    dosyalar = []
    for klasor in TARA:
        yol = os.path.join(BASE, klasor) if klasor != '.' else BASE
        if not os.path.isdir(yol):
            continue
        for f in os.listdir(yol):
            if f.endswith('.py') and not f.startswith('_'):
                dosyalar.append(os.path.join(yol, f))
    return sorted(set(dosyalar))


def kullanilan_isimler(tree):
    """AST'ten kullanilan global isimleri cikar."""
    kullanilan = set()
    for node in ast.walk(tree):
        # Name kullanimi (ornek: io, logging)
        if isinstance(node, ast.Name):
            kullanilan.add(node.id)
        # Attribute erisimi (ornek: io.BytesIO -> io)
        elif isinstance(node, ast.Attribute):
            # En distaki Name'i bul
            n = node
            while isinstance(n, ast.Attribute):
                n = n.value
            if isinstance(n, ast.Name):
                kullanilan.add(n.id)
    return kullanilan


def import_edilen_isimler(tree):
    """AST'ten import edilen isimleri cikar."""
    importlanan = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                isim = alias.asname if alias.asname else alias.name.split('.')[0]
                importlanan.add(isim)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                isim = alias.asname if alias.asname else alias.name
                importlanan.add(isim)
    return importlanan


def tanimlanan_isimler(tree):
    """AST'ten tanimlanan (fonksiyon, class, degisken) isimleri cikar."""
    tanimli = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            tanimli.add(node.name)
        elif isinstance(node, ast.AsyncFunctionDef):
            tanimli.add(node.name)
        elif isinstance(node, ast.ClassDef):
            tanimli.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    tanimli.add(t.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                tanimli.add(node.target.id)
    return tanimli


def main():
    print('=' * 70)
    print('  LUMISPAC v3 - IMPORT DENETCISI')
    print('=' * 70)
    print()

    dosyalar = dosyalari_bul()
    print('  Taranan dosya: ' + str(len(dosyalar)))
    print()

    toplam_sorun = 0

    for dosya in dosyalar:
        try:
            with open(dosya, 'r', encoding='utf-8') as f:
                icerik = f.read()
            tree = ast.parse(icerik)
        except Exception as e:
            print('[!!] ' + os.path.relpath(dosya, BASE) + ' -> okunamadi: ' + str(e))
            continue

        kullanilan = kullanilan_isimler(tree)
        importlanan = import_edilen_isimler(tree)
        tanimli = tanimlanan_isimler(tree)

        # Ozel isimlerden hangileri kullaniliyor ama tanimli/import degil?
        eksik = set()
        for isim in OZEL_ISIMLER:
            if isim in kullanilan and isim not in importlanan and isim not in tanimli:
                eksik.add(isim)

        if eksik:
            toplam_sorun += len(eksik)
            rel = os.path.relpath(dosya, BASE)
            print('[!!] ' + rel)
            for isim in sorted(eksik):
                print('       - ' + isim + ' (import edilmemis)')

    print()
    print('=' * 70)
    if toplam_sorun == 0:
        print('  [OK] Hicbir sorun bulunamadi.')
    else:
        print('  [UYARI] Toplam ' + str(toplam_sorun) + ' eksik import!')
    print('=' * 70)


if __name__ == '__main__':
    main()