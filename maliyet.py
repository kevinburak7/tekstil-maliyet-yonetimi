"""Geriye uyumlu giriş noktası: python maliyet.py

Asıl kod tekstil_maliyet/ paketindedir.
"""

from tekstil_maliyet.constants import (
    DB_YOLU,
    FIRE_ORANI_VARSAYILAN,
    FONT_BASLIK,
    FONT_BOLD,
    FONT_NORMAL,
    KUR_CACHE_YOLU,
    KUR_TIMEOUT_SN,
    RENK_AKTIF,
    RENK_BASARI,
    RENK_BG,
    RENK_BIRINCIL,
    RENK_BUTON,
    RENK_IKINCIL,
    RENK_KART,
    RENK_SIDEBAR,
    RENK_TEHLIKE,
    RENK_VURGU,
    TCMB_URL,
    TIP_SAYFA,
    YEDEK_KURLAR,
)
from tekstil_maliyet.db import Veritabani
from tekstil_maliyet.doviz import DovizServisi
from tekstil_maliyet.excel_export import excel_aktar
from tekstil_maliyet.hesaplama import (
    ValidationError,
    guvenli_maliyet,
    guvenli_toplam,
    maliyet_hesapla,
    parse_float,
    parse_pozitif,
    recete_toplam,
)
from tekstil_maliyet.karsilastirma import karsilastir, recete_ozet
from tekstil_maliyet.pdf_export import pdf_aktar
from tekstil_maliyet.ui.app import MaliyetApp
from tekstil_maliyet.ui.pages_arsiv import ArsivPage
from tekstil_maliyet.ui.pages_base import (
    ApreMaliyetiPage,
    BasePage,
    BoyaMaliyetiPage,
    YardimciKimyasalPage,
)
from tekstil_maliyet.ui.pages_katalog import KatalogPage
from tekstil_maliyet.ui.widgets import (
    EmptyState,
    ModernButton,
    ScrollableFrame,
    ToastBar,
    ToolTip,
)

__all__ = [
    "DB_YOLU",
    "FIRE_ORANI_VARSAYILAN",
    "FONT_BASLIK",
    "FONT_BOLD",
    "FONT_NORMAL",
    "KUR_CACHE_YOLU",
    "KUR_TIMEOUT_SN",
    "RENK_AKTIF",
    "RENK_BASARI",
    "RENK_BG",
    "RENK_BIRINCIL",
    "RENK_BUTON",
    "RENK_IKINCIL",
    "RENK_KART",
    "RENK_SIDEBAR",
    "RENK_TEHLIKE",
    "RENK_VURGU",
    "TCMB_URL",
    "TIP_SAYFA",
    "YEDEK_KURLAR",
    "Veritabani",
    "DovizServisi",
    "excel_aktar",
    "pdf_aktar",
    "karsilastir",
    "recete_ozet",
    "ValidationError",
    "guvenli_maliyet",
    "guvenli_toplam",
    "maliyet_hesapla",
    "parse_float",
    "parse_pozitif",
    "recete_toplam",
    "MaliyetApp",
    "ArsivPage",
    "ApreMaliyetiPage",
    "BasePage",
    "BoyaMaliyetiPage",
    "YardimciKimyasalPage",
    "KatalogPage",
    "EmptyState",
    "ModernButton",
    "ScrollableFrame",
    "ToastBar",
    "ToolTip",
]


if __name__ == "__main__":
    from tekstil_maliyet.__main__ import main

    main()
