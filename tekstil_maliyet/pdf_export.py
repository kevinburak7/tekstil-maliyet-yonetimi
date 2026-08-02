"""PDF dışa aktarım (fpdf2)."""
import os
from datetime import datetime

from tekstil_maliyet.constants import FIRE_ORANI_VARSAYILAN
from tekstil_maliyet.hesaplama import ValidationError, maliyet_hesapla, recete_toplam


def _font_yollari():
    """Windows Arial (Türkçe karakter) yollarını döndürür."""
    windir = os.environ.get("WINDIR", r"C:\Windows")
    fonts = os.path.join(windir, "Fonts")
    regular = os.path.join(fonts, "arial.ttf")
    bold = os.path.join(fonts, "arialbd.ttf")
    if not os.path.isfile(regular):
        raise RuntimeError(
            "PDF için Arial fontu bulunamadı. Windows Fonts klasörünü kontrol edin."
        )
    if not os.path.isfile(bold):
        bold = regular
    return regular, bold


def pdf_aktar(dosya_yolu, receteler, kurlar):
    """Reçete listesini PDF dosyasına yazar. fpdf2 gerekir."""
    try:
        from fpdf import FPDF
    except ImportError as exc:
        raise RuntimeError(
            "PDF aktarımı için fpdf2 gerekli. Kurulum: pip install fpdf2"
        ) from exc

    regular, bold = _font_yollari()

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font("AppFont", "", regular)
    pdf.add_font("AppFont", "B", bold)

    pdf.add_page()
    pdf.set_font("AppFont", "B", 16)
    pdf.cell(0, 10, "Tekstil Maliyet - Reçete Raporu", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("AppFont", "", 10)
    pdf.cell(
        0,
        6,
        f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}  |  "
        f"Kayıt: {len(receteler)}  |  "
        f"USD: {kurlar.get('USD', '-')}  EUR: {kurlar.get('EUR', '-')}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(4)

    # Özet tablo
    pdf.set_font("AppFont", "B", 12)
    pdf.cell(0, 8, "Özet", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("AppFont", "B", 9)
    ozet_cols = [
        ("ID", 15),
        ("Tür", 28),
        ("Reçete", 70),
        ("Fire", 18),
        ("Maliyet TL/kg", 40),
    ]
    for baslik, w in ozet_cols:
        pdf.cell(w, 7, baslik, border=1)
    pdf.ln()

    ozet_veriler = []
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
        ozet_veriler.append((recete, fire, toplam))
        pdf.set_font("AppFont", "", 8)
        isim = str(recete.get("isim") or "")[:40]
        pdf.cell(15, 6, str(recete.get("id", "")), border=1)
        pdf.cell(28, 6, str(recete.get("tur") or ""), border=1)
        pdf.cell(70, 6, isim, border=1)
        pdf.cell(18, 6, f"{fire:.2f}", border=1)
        pdf.cell(40, 6, f"{toplam:.4f}", border=1)
        pdf.ln()

    # Detay sayfaları
    for recete, fire, toplam in ozet_veriler:
        pdf.add_page()
        pdf.set_font("AppFont", "B", 13)
        pdf.cell(
            0,
            8,
            f"#{recete.get('id')} — {recete.get('isim')}",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.set_font("AppFont", "", 10)
        tur = recete.get("tur") or ""
        param = recete.get("parametre")
        if tur == "Kimyasal":
            p_str = f"Flotte: 1/{param}"
        elif tur == "Apre":
            p_str = f"Pick-up: %{param}"
        else:
            p_str = "Parametre yok"
        pdf.cell(
            0,
            6,
            f"Tür: {tur}  |  {p_str}  |  Fire: {fire}  |  "
            f"Tarih: {str(recete.get('tarih') or '-')[:19]}",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.ln(2)

        pdf.set_font("AppFont", "B", 8)
        detay_cols = [
            ("Ürün", 55),
            ("Miktar", 22),
            ("Birim", 28),
            ("Fiyat", 22),
            ("Para", 16),
            ("Maliyet TL", 30),
        ]
        for baslik, w in detay_cols:
            pdf.cell(w, 7, baslik, border=1)
        pdf.ln()

        pdf.set_font("AppFont", "", 8)
        for item in recete.get("icerik") or []:
            try:
                satir = maliyet_hesapla(
                    item, tur, recete["parametre"], kurlar, fire
                )
            except ValidationError:
                satir = 0.0
            pdf.cell(55, 6, str(item.get("ad") or "")[:32], border=1)
            pdf.cell(22, 6, f"{item.get('miktar', '')}", border=1)
            pdf.cell(28, 6, str(item.get("birim") or "")[:16], border=1)
            pdf.cell(22, 6, f"{item.get('fiyat', '')}", border=1)
            pdf.cell(16, 6, str(item.get("para") or ""), border=1)
            pdf.cell(30, 6, f"{satir:.4f}", border=1)
            pdf.ln()

        pdf.ln(3)
        pdf.set_font("AppFont", "B", 11)
        pdf.cell(0, 8, f"Birim maliyet (1 kg kumaş): {toplam:.4f} TL")

    pdf.output(dosya_yolu)
    return dosya_yolu
