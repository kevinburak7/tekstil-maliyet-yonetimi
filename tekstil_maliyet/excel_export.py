"""Excel dışa aktarım."""
from tekstil_maliyet.constants import FIRE_ORANI_VARSAYILAN
from tekstil_maliyet.hesaplama import guvenli_maliyet, guvenli_toplam


def excel_aktar(dosya_yolu, receteler, kurlar):
    """Reçete listesini Excel (.xlsx) dosyasına yazar. openpyxl gerekir."""
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise RuntimeError(
            "Excel aktarımı için openpyxl gerekli. Kurulum: pip install openpyxl"
        ) from exc
    from openpyxl.styles import Font

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
            "Hata",
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
            "Hata",
        ]
    )
    for cell in ws_detay[1]:
        cell.font = Font(bold=True)

    for recete in receteler:
        fire = float(recete.get("fire_orani") or FIRE_ORANI_VARSAYILAN)
        toplam, hata = guvenli_toplam(
            recete["icerik"],
            recete["tur"],
            recete["parametre"],
            kurlar,
            fire,
        )
        ws_ozet.append(
            [
                recete["id"],
                recete["tur"],
                recete["isim"],
                recete["parametre"],
                fire,
                str(recete.get("tarih") or ""),
                None if hata else round(toplam, 6),
                len(recete.get("icerik") or []),
                "Evet" if hata else "",
            ]
        )
        for item in recete.get("icerik") or []:
            satir_maliyet, err = guvenli_maliyet(
                item,
                recete["tur"],
                recete["parametre"],
                kurlar,
                fire,
            )
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
                    None if err else round(satir_maliyet, 6),
                    err or "",
                ]
            )

    wb.save(dosya_yolu)
    return dosya_yolu
