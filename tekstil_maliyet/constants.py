"""Uygulama sabitleri."""
import os

DB_YOLU = os.path.join(os.path.expanduser("~"), "tekstil_maliyet_pro.db")
KUR_CACHE_YOLU = os.path.join(os.path.expanduser("~"), "tekstil_maliyet_kur_cache.json")
TCMB_URL = "https://www.tcmb.gov.tr/kurlar/today.xml"
KUR_TIMEOUT_SN = 8
FIRE_ORANI_VARSAYILAN = 1.2
YEDEK_KURLAR = {"TL": 1.0, "USD": 35.0, "EUR": 38.0}

RENK_SIDEBAR = "#2c3e50"
RENK_BG = "#ecf0f1"
RENK_KART = "#ffffff"
RENK_VURGU = "#e67e22"
RENK_BUTON = "#34495e"
RENK_AKTIF = "#1abc9c"
FONT_BASLIK = ("Segoe UI", 16, "bold")
FONT_NORMAL = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")

TIP_SAYFA = {
    "Kimyasal": "Yardımcı Kimyasal",
    "Boya": "Boya Maliyeti",
    "Apre": "Apre Maliyeti",
}
