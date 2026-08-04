"""Reçete karşılaştırma mantığı."""
from tekstil_maliyet.constants import FIRE_ORANI_VARSAYILAN
from tekstil_maliyet.hesaplama import guvenli_maliyet, guvenli_toplam


def _param_metin(tur, param):
    if tur == "Kimyasal":
        return f"Flotte 1/{param}"
    if tur == "Apre":
        return f"Pick-up %{param}"
    return "-"


def recete_ozet(recete, kurlar):
    """Tek reçetenin karşılaştırma özetini üretir."""
    fire = float(recete.get("fire_orani") or FIRE_ORANI_VARSAYILAN)
    maliyet, hata = guvenli_toplam(
        recete.get("icerik") or [],
        recete["tur"],
        recete["parametre"],
        kurlar,
        fire,
    )

    satir_maliyetleri = {}
    for item in recete.get("icerik") or []:
        ad = str(item.get("ad") or "").strip() or "(adsız)"
        m, err = guvenli_maliyet(
            item, recete["tur"], recete["parametre"], kurlar, fire
        )
        if err:
            hata = True
            continue
        satir_maliyetleri[ad] = satir_maliyetleri.get(ad, 0.0) + m

    return {
        "id": recete.get("id"),
        "isim": recete.get("isim") or "",
        "tur": recete.get("tur") or "",
        "parametre": recete.get("parametre"),
        "param_metin": _param_metin(recete.get("tur"), recete.get("parametre")),
        "fire_orani": fire,
        "tarih": str(recete.get("tarih") or "")[:19],
        "maliyet": 0.0 if hata else maliyet,
        "hata": hata,
        "satir_sayisi": len(recete.get("icerik") or []),
        "satir_maliyetleri": satir_maliyetleri,
    }


def karsilastir(receteler, kurlar):
    """
    2+ reçeteyi karşılaştırır.

    Dönüş:
      ozetler: liste (maliyet farkları doldurulmuş)
      urun_satirlari: ürün adına göre yan yana maliyetler
      en_ucuz_id: en düşük maliyetli reçete id
    """
    if len(receteler) < 2:
        raise ValueError("Karşılaştırma için en az 2 reçete gerekir.")

    ozetler = [recete_ozet(r, kurlar) for r in receteler]
    gecerli = [o for o in ozetler if not o.get("hata")]
    if not gecerli:
        raise ValueError("Karşılaştırılacak geçerli maliyet bulunamadı.")

    min_maliyet = min(o["maliyet"] for o in gecerli)
    en_ucuz = next(o for o in gecerli if o["maliyet"] == min_maliyet)

    for o in ozetler:
        if o.get("hata"):
            o["fark_tl"] = None
            o["fark_yuzde"] = None
            o["en_ucuz"] = False
            continue
        fark = o["maliyet"] - min_maliyet
        o["fark_tl"] = fark
        o["fark_yuzde"] = (
            (fark / min_maliyet * 100.0) if min_maliyet > 0 else 0.0
        )
        o["en_ucuz"] = abs(fark) < 1e-9

    urunler = set()
    for o in ozetler:
        urunler.update(o["satir_maliyetleri"].keys())

    urun_satirlari = []
    for ad in sorted(urunler, key=lambda s: s.lower()):
        degerler = []
        for o in ozetler:
            degerler.append(o["satir_maliyetleri"].get(ad))
        mevcut = [d for d in degerler if d is not None]
        urun_satirlari.append(
            {
                "ad": ad,
                "degerler": degerler,
                "min": min(mevcut) if mevcut else None,
                "max": max(mevcut) if mevcut else None,
            }
        )

    return {
        "ozetler": ozetler,
        "urun_satirlari": urun_satirlari,
        "en_ucuz_id": en_ucuz["id"],
        "en_ucuz_maliyet": min_maliyet,
    }
