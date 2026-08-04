"""Maliyet hesaplama ve validasyon."""
from tekstil_maliyet.constants import FIRE_ORANI_VARSAYILAN

GECERLI_PARALAR = frozenset({"TL", "USD", "EUR"})


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


def parse_pozitif(val, alan_adi="Değer"):
    """Sıfırdan büyük sayı zorunlu."""
    sayi = parse_float(val, alan_adi)
    if sayi <= 0:
        raise ValidationError(f"{alan_adi} sıfırdan büyük olmalıdır.")
    return sayi


def maliyet_hesapla(item, tip, parametre, kurlar, fire_orani=FIRE_ORANI_VARSAYILAN):
    """
    Tek maliyet formülü.
    Kimyasal g/l: miktar * fiyat_tl * flotte / 10 / 100 * fire
    Kimyasal % / Boya: miktar * fiyat_tl / 100 * fire
    Apre: miktar * fiyat_tl / 10 / 100 * pickup * fire
    """
    para = item.get("para", "TL") or "TL"
    if para not in kurlar:
        raise ValidationError(f"Bilinmeyen para birimi: {para}")
    kur = kurlar[para]
    fiyat = float(item["fiyat"])
    miktar = float(item["miktar"])
    if miktar <= 0:
        raise ValidationError("Miktar sıfırdan büyük olmalıdır.")
    if fiyat <= 0:
        raise ValidationError("Fiyat sıfırdan büyük olmalıdır.")
    if fire_orani is None or float(fire_orani) <= 0:
        raise ValidationError("Fire oranı sıfırdan büyük olmalıdır.")

    fiyat_tl = fiyat * kur
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


def guvenli_maliyet(item, tip, parametre, kurlar, fire_orani=FIRE_ORANI_VARSAYILAN):
    """(maliyet|None, hata_mesaji|None) — export/detay için."""
    try:
        return maliyet_hesapla(item, tip, parametre, kurlar, fire_orani), None
    except ValidationError as exc:
        return None, str(exc)


def guvenli_toplam(icerik, tip, parametre, kurlar, fire_orani=FIRE_ORANI_VARSAYILAN):
    """(toplam|None, hata_var: bool). Hatalı satır varsa toplam None."""
    if not icerik:
        return 0.0, False
    toplam = 0.0
    for item in icerik:
        m, err = guvenli_maliyet(item, tip, parametre, kurlar, fire_orani)
        if err:
            return None, True
        toplam += m
    return toplam, False
