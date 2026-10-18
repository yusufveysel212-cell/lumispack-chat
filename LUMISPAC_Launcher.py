"""Open the desktop client; the independent background task owns the server."""
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request

LOCAL = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'LUMISPAC'
CHROME = Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
CREATE_NO_WINDOW = 0x08000000


def ready():
    try:
        with urllib.request.urlopen('http://127.0.0.1:5001/livez', timeout=2) as response:
            data = json.load(response)
            return data.get('service') == 'lumispac' and data.get('runtime') == 'waitress-v1'
    except Exception:
        return False


def main():
    if not ready():
        result = subprocess.run(['schtasks', '/Run', '/TN', 'LUMISPAC Server'],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                creationflags=CREATE_NO_WINDOW)
        if result.returncode:
            raise RuntimeError('LUMISPAC Server arka plan görevi başlatılamadı.')
        for _ in range(60):
            if ready():
                break
            time.sleep(.5)
        else:
            raise RuntimeError('Sunucu hazır değil. LUMISPAC logs klasörünü kontrol edin.')
    if not CHROME.is_file():
        raise RuntimeError('Google Chrome bulunamadı.')
    profile = LOCAL / 'ChromeProfile'
    profile.mkdir(parents=True, exist_ok=True)
    subprocess.Popen([str(CHROME), '--app=http://127.0.0.1:5001/',
                      '--user-data-dir=' + str(profile), '--no-first-run',
                      '--disable-background-mode', '--disable-features=Translate'],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror('LUMISPAC', str(error), parent=root)
        root.destroy()
