"""TCMB döviz kuru servisi."""
import json
import urllib.request
import xml.etree.ElementTree as ET
from urllib.error import URLError

from tekstil_maliyet import constants


class DovizServisi:
    """TCMB kurları: timeout, dosya önbelleği, kontrollü yedek."""

    @staticmethod
    def _cache_oku():
        try:
            with open(constants.KUR_CACHE_YOLU, encoding="utf-8") as f:
                data = json.load(f)
            kurlar = data.get("kurlar") or {}
            if "TL" in kurlar and "USD" in kurlar and "EUR" in kurlar:
                return {
                    "TL": float(kurlar["TL"]),
                    "USD": float(kurlar["USD"]),
                    "EUR": float(kurlar["EUR"]),
                }
        except (OSError, ValueError, TypeError, KeyError):
            return None
        return None

    @staticmethod
    def _cache_yaz(kurlar):
        try:
            with open(constants.KUR_CACHE_YOLU, "w", encoding="utf-8") as f:
                json.dump({"kurlar": kurlar}, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    @classmethod
    def get(cls):
        """
        Returns:
            (kurlar: dict, kaynak: str, uyari: str|None)
            kaynak: 'tcmb' | 'cache' | 'yedek'
        """
        try:
            with urllib.request.urlopen(constants.TCMB_URL, timeout=constants.KUR_TIMEOUT_SN) as response:
                tree = ET.parse(response)
            root = tree.getroot()
            kurlar = {"TL": 1.0}
            for currency in root.findall("Currency"):
                code = currency.get("Kod")
                if code not in ("USD", "EUR"):
                    continue
                node = currency.find("ForexSelling")
                rate = node.text if node is not None else None
                if rate:
                    kurlar[code] = float(rate.replace(",", "."))
            if "USD" not in kurlar or "EUR" not in kurlar:
                raise ValueError("TCMB yanıtında USD/EUR bulunamadı")
            cls._cache_yaz(kurlar)
            return kurlar, "tcmb", None
        except (URLError, TimeoutError, OSError, ET.ParseError, ValueError, TypeError):
            cached = cls._cache_oku()
            if cached:
                return (
                    cached,
                    "cache",
                    "TCMB'den kur alınamadı; son kayıtlı kurlar kullanılıyor.",
                )
            return (
                dict(constants.YEDEK_KURLAR),
                "yedek",
                "TCMB ve önbellek kullanılamadı; varsayılan kurlar ile devam ediliyor.",
            )


