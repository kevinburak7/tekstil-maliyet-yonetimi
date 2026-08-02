"""Maliyet hesaplama ve validasyon."""
from tekstil_maliyet.constants import FIRE_ORANI_VARSAYILAN


class ValidationError(Exception):
    """Kullanıcıya gösterilecek giriş hatası."""


def parse_float(val, alan_adi="Değer"):
    """Boş veya geçersiz sayıda hata fırlatır; sessizce 0 dönmez."""
    if val is None:
        raise ValidationError(f"{alan_adi} boş olamaz.")
    text = str(val).strip().replace(",", ".")
    if not text:
        raise ValidationError(f"{alan_adi} boş olamaz.")
    try:
        return float(text)
    except ValueError as exc:
        raise ValidationError(f"{alan_adi} geçerli bir sayı değil: {val!r}") from exc


def maliyet_hesapla(item, tip, parametre, kurlar, fire_orani=FIRE_ORANI_VARSAYILAN):
    """
    Tek maliyet formülü.
    Kimyasal g/l: miktar * fiyat_tl * flotte / 10 / 100 * fire
    Kimyasal % / Boya: miktar * fiyat_tl / 100 * fire
    Apre: miktar * fiyat_tl / 10 / 100 * pickup * fire
    """
    para = item.get("para", "TL")
    kur = kurlar.get(para, 1.0)
    fiyat_tl = float(item["fiyat"]) * kur
    miktar = float(item["miktar"])
    birim = item.get("birim") or ""

    if tip == "Kimyasal":
        if birim == "g/l":
            if not parametre or parametre <= 0:
                raise ValidationError("Flotte (1/X) sıfırdan büyük olmalıdır.")
            return miktar * fiyat_tl / (10.0 / parametre) / 100.0 * fire_orani
        return miktar * fiyat_tl / 100.0 * fire_orani

    if tip == "Apre":
        if not parametre or parametre <= 0:
            raise ValidationError("Pick-up (%) sıfırdan büyük olmalıdır.")
        return miktar * fiyat_tl / 10.0 / 100.0 * parametre * fire_orani

    if tip == "Boya":
        return miktar * fiyat_tl / 100.0 * fire_orani

    raise ValidationError(f"Bilinmeyen işlem türü: {tip}")


def recete_toplam(icerik, tip, parametre, kurlar, fire_orani=FIRE_ORANI_VARSAYILAN):
    return sum(
        maliyet_hesapla(item, tip, parametre, kurlar, fire_orani) for item in icerik
    )


