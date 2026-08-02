# Tekstil Maliyet Yönetimi

Tekstil boya / yardımcı kimyasal / apre (bitim) reçeteleri için birim maliyet (TL/kg) hesaplama uygulaması.

## Özellikler

- Yardımcı kimyasal, boya ve apre maliyet hesaplama
- TCMB günlük kuru ile TL / USD / EUR dönüşümü
- Reçete kaydı (SQLite)
- Arşiv: gruplama, çoklu seçim, silme, detay

## Çalıştırma

```bash
pip install -r requirements.txt
python maliyet.py
# veya
python -m tekstil_maliyet
```

Python 3.10+ ve Tkinter gerekir. Excel aktarımı için `openpyxl` kullanılır.

## EXE derleme

```bash
build_exe.bat
```

Çıktı: `dist/TekstilMaliyetYonetimi.exe`

## Proje yapısı

```
tekstil_maliyet/     # ana paket
  constants.py
  hesaplama.py
  db.py
  doviz.py
  excel_export.py
  ui/
maliyet.py           # giriş noktası (uyumluluk)
tests/
```

## Veritabanı

Reçeteler kullanıcı klasöründe saklanır:

`~/tekstil_maliyet_pro.db`
