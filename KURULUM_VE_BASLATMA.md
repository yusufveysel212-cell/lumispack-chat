# LUMISPAC Son Sürüm

- Bu klasör, güncel kaynak/test kopyasından üretildi.
- `LUMISPAC_Baslat.bat` uygulama başlatıcısını açar.
- Başlatıcı uygulamayı PostgreSQL 18'e (`127.0.0.1:5432/lumispac`) bağlar; PostgreSQL hizmeti açık ve `%LOCALAPPDATA%\LUMISPAC\postgresql\pgpass.conf` hazır olmalıdır.
- Kalıcı iş verileri bu kaynak klasöründe değildir; PostgreSQL ve `%LOCALAPPDATA%\LUMISPAC` altındadır. Kaynak klasörünü silmek/taşımak mevcut PostgreSQL kayıtlarını silmez.
- Başlatıcı Chrome uygulama penceresini `http://127.0.0.1:5001/` adresinde açar.
