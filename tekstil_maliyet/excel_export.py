"""Excel dışa aktarım."""
from tekstil_maliyet.constants import FIRE_ORANI_VARSAYILAN
from tekstil_maliyet.hesaplama import ValidationError, maliyet_hesapla, recete_toplam


def excel_aktar(dosya_yolu, receteler, kurlar):
    """Reçete listesini Excel (.xlsx) dosyasına yazar. openpyxl gerekir."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
    except ImportError as exc:
        raise RuntimeError(
            "Excel aktarımı için openpyxl gerekli. Kurulum: pip install openpyxl"
        ) from exc

    wb = Workbook()
    ws_ozet = wb.active
    ws_ozet.title = "Ozet"
    ws_ozet.append(
        [
            "ID",
            "Tur",
            "Isim",
            "Parametre",
            "Fire_Orani",
            "Tarih",
            "Maliyet_TL_Kg",
            "Satir_Sayisi",
        ]
    )
    for cell in ws_ozet[1]:
        cell.font = Font(bold=True)

    ws_detay = wb.create_sheet("Detay")
    ws_detay.append(
        [
            "Recete_ID",
            "Recete_Adi",
            "Tur",
            "Fire_Orani",
            "Urun",
            "Miktar",
            "Birim",
            "Fiyat",
            "Para",
            "Satir_Maliyet_TL",
        ]
    )
    for cell in ws_detay[1]:
        cell.font = Font(bold=True)

    for recete in receteler:
        fire = float(recete.get("fire_orani") or FIRE_ORANI_VARSAYILAN)
        try:
            toplam = recete_toplam(
                recete["icerik"],
                recete["tur"],
                recete["parametre"],
                kurlar,
                fire,
            )
        except ValidationError:
            toplam = 0.0
        ws_ozet.append(
            [
                recete["id"],
                recete["tur"],
                recete["isim"],
                recete["parametre"],
                fire,
                str(recete.get("tarih") or ""),
                round(toplam, 6),
                len(recete.get("icerik") or []),
            ]
        )
        for item in recete.get("icerik") or []:
            try:
                satir_maliyet = maliyet_hesapla(
                    item,
                    recete["tur"],
                    recete["parametre"],
                    kurlar,
                    fire,
                )
            except ValidationError:
                satir_maliyet = 0.0
            ws_detay.append(
                [
                    recete["id"],
                    recete["isim"],
                    recete["tur"],
                    fire,
                    item["ad"],
                    item["miktar"],
                    item["birim"],
                    item["fiyat"],
                    item["para"],
                    round(satir_maliyet, 6),
                ]
            )

    wb.save(dosya_yolu)
    return dosya_yolu


