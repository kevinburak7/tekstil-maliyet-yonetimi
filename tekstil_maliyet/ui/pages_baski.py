"""Baskı maliyeti hesaplama sayfası — renk → ürün yapısı."""
import tkinter as tk
from tkinter import ttk

from tekstil_maliyet.constants import (
    FIRE_ORANI_VARSAYILAN,
    FIRE_YUZDE_VARSAYILAN,
    FONT_BASLIK,
    FONT_BOLD,
    FONT_NORMAL,
    IPUCU_BASKI_MIKTAR,
    IPUCU_DOLULUK,
    IPUCU_FIRE,
    RENK_BANNER,
    RENK_BANNER_METIN,
    RENK_BASARI,
    RENK_BG,
    RENK_IKINCIL,
    RENK_KART,
    RENK_METIN,
    RENK_METIN_SOLUK,
    RENK_SIDEBAR,
    RENK_TEHLIKE,
    RENK_VURGU,
)
from tekstil_maliyet.hesaplama import (
    ValidationError,
    fire_carpan_to_yuzde,
    fire_yuzde_to_carpan,
    maliyet_hesapla,
    parse_fire_yuzde,
    parse_pozitif,
    recete_toplam,
)
from tekstil_maliyet.ui.widgets import (
    ModernButton,
    ScrollableFrame,
    ToolTip,
    msg_error,
    msg_info,
    msg_yesno,
    msg_yesnocancel,
)

MAX_RENK = 12
MAX_URUN_RENK = 30


class BaskiMaliyetiPage(ttk.Frame):
    tip = "Baski"

    def __init__(self, parent, controller):
        super().__init__(parent, style="TFrame")
        self.controller = controller
        self.duzenlenen_id = None
        self.renkler = []  # her öğe: renk paneli sözlüğü

        top_panel = tk.Frame(self, bg=RENK_KART, padx=20, pady=16)
        top_panel.pack(fill="x", pady=(0, 12))
        self._top_panel = top_panel

        self.lbl_baslik = tk.Label(
            top_panel,
            text="BASKI MALİYETİ",
            font=FONT_BASLIK,
            bg=RENK_KART,
            fg=RENK_METIN,
        )
        self.lbl_baslik.pack(side="top", pady=(0, 8))

        self.banner = tk.Frame(top_panel, bg=RENK_BANNER, padx=12, pady=8)
        self.lbl_durum = tk.Label(
            self.banner,
            text="",
            font=FONT_BOLD,
            bg=RENK_BANNER,
            fg=RENK_BANNER_METIN,
            anchor="w",
        )
        self.lbl_durum.pack(side="left", fill="x", expand=True)
        ModernButton(
            self.banner,
            text="İptal",
            bg=RENK_IKINCIL,
            fg="white",
            width=8,
            command=self.yeni_recete,
        ).pack(side="right")

        grid_frame = tk.Frame(top_panel, bg=RENK_KART)
        grid_frame.pack()
        self._grid_frame = grid_frame

        tk.Label(
            grid_frame,
            text="Reçete Adı",
            bg=RENK_KART,
            font=FONT_BOLD,
            fg=RENK_METIN_SOLUK,
        ).grid(row=0, column=0, padx=10, sticky="w")
        self.ent_isim = ttk.Entry(grid_frame, width=28, font=FONT_NORMAL)
        self.ent_isim.grid(row=1, column=0, padx=10, pady=5)

        lbl_fire = tk.Label(
            grid_frame,
            text="Fire Oranı (%)",
            bg=RENK_KART,
            font=FONT_BOLD,
            fg=RENK_METIN_SOLUK,
        )
        lbl_fire.grid(row=0, column=1, padx=10, sticky="w")
        self.ent_fire = ttk.Entry(grid_frame, width=12, font=FONT_NORMAL)
        self.ent_fire.insert(0, str(int(FIRE_YUZDE_VARSAYILAN)))
        self.ent_fire.grid(row=1, column=1, padx=10, pady=5)
        ToolTip(self.ent_fire, IPUCU_FIRE)
        ToolTip(lbl_fire, IPUCU_FIRE)

        lbl_renk = tk.Label(
            grid_frame,
            text="Renk Sayısı",
            bg=RENK_KART,
            font=FONT_BOLD,
            fg=RENK_METIN_SOLUK,
        )
        lbl_renk.grid(row=0, column=2, padx=10, sticky="w")
        self.cmb_renk_sayisi = ttk.Combobox(
            grid_frame,
            values=[str(i) for i in range(1, MAX_RENK + 1)],
            width=8,
            state="readonly",
            font=FONT_NORMAL,
        )
        self.cmb_renk_sayisi.set("1")
        self.cmb_renk_sayisi.grid(row=1, column=2, padx=10, pady=5)

        ModernButton(
            grid_frame,
            text="Renkleri Oluştur",
            bg="#2980b9",
            fg="white",
            width=14,
            command=self._renkleri_olustur_tik,
        ).grid(row=1, column=3, padx=10, pady=5)

        self.mid_panel = ScrollableFrame(self)
        self.mid_panel.pack(fill="both", expand=True)

        bot_panel = tk.Frame(self, bg=RENK_SIDEBAR, height=80)
        bot_panel.pack(fill="x", side="bottom")

        res_frame = tk.Frame(bot_panel, bg=RENK_SIDEBAR)
        res_frame.pack(side="left", padx=30, pady=10)

        self.lbl_tl = tk.Label(
            res_frame,
            text="0.00 TL",
            font=("Segoe UI", 18, "bold"),
            bg=RENK_SIDEBAR,
            fg="#e74c3c",
        )
        self.lbl_tl.pack(anchor="w")

        self.lbl_doviz = tk.Label(
            res_frame,
            text="$ 0.00 | € 0.00",
            font=("Segoe UI", 10),
            bg=RENK_SIDEBAR,
            fg="white",
        )
        self.lbl_doviz.pack(anchor="w")

        act_frame = tk.Frame(bot_panel, bg=RENK_SIDEBAR)
        act_frame.pack(side="right", padx=30)

        ModernButton(
            act_frame,
            text="YENİ",
            bg=RENK_IKINCIL,
            fg="white",
            width=10,
            command=self.yeni_recete,
        ).pack(side="left", padx=5)
        ModernButton(
            act_frame,
            text="HESAPLA",
            bg=RENK_VURGU,
            fg="white",
            width=15,
            command=self.hesapla,
        ).pack(side="left", padx=5)
        ModernButton(
            act_frame,
            text="KAYDET",
            bg=RENK_BASARI,
            fg="white",
            width=15,
            command=self.kaydet,
        ).pack(side="left", padx=5)

        self._renkleri_kur(1)

    # --- yardımcı ---

    def _toast(self, msg, kind="ok"):
        if hasattr(self.controller, "toast"):
            self.controller.toast.show(msg, kind=kind)

    def on_show(self):
        self._katalog_comboboxlari_yenile()

    def kurlar_degisti(self):
        try:
            data, fire = self.verileri_al()
            toplam_tl = recete_toplam(
                data, self.tip, 1.0, self.controller.kurlar, fire
            )
        except ValidationError:
            return
        usd = toplam_tl / self.controller.kurlar["USD"]
        eur = toplam_tl / self.controller.kurlar["EUR"]
        self.lbl_tl.config(text=f"{toplam_tl:.4f} TL / Kg")
        self.lbl_doviz.config(text=f"$ {usd:.4f} | € {eur:.4f}")

    def _katalog_adlari(self):
        return [u["ad"] for u in self.controller.db.katalog_listele(sadece_aktif=True)]

    def _katalog_comboboxlari_yenile(self):
        adlar = ["— Katalogdan seç —"] + self._katalog_adlari()
        for renk in self.renkler:
            for row_ref in renk["urunler"]:
                c_kat = row_ref["widgets"][0]
                mevcut = c_kat.get()
                c_kat["values"] = adlar
                if mevcut in adlar:
                    c_kat.set(mevcut)
                else:
                    c_kat.set(adlar[0])

    def _katalog_uygula(self, c_kat, e_ad, e_fiyat, c_para):
        ad = c_kat.get()
        if not ad or ad.startswith("—"):
            return
        urun = self.controller.db.katalog_getir_by_ad(ad)
        if not urun:
            return
        e_ad.delete(0, tk.END)
        e_ad.insert(0, urun["ad"])
        e_fiyat.delete(0, tk.END)
        e_fiyat.insert(0, str(urun["fiyat"]))
        para = urun.get("para") or "TL"
        if para in ("TL", "USD", "EUR"):
            c_para.set(para)

    def _durum_guncelle(self):
        if self.duzenlenen_id:
            self.lbl_durum.config(
                text=(
                    f"Düzenleniyor: Reçete #{self.duzenlenen_id}"
                    " — değişiklikler Kaydet ile yazılır"
                )
            )
            self._banner_goster()
        else:
            self.banner.pack_forget()

    def _banner_goster(self):
        self.lbl_baslik.pack_forget()
        self.banner.pack_forget()
        self._grid_frame.pack_forget()
        self.lbl_baslik.pack(side="top", pady=(0, 8))
        self.banner.pack(fill="x", pady=(0, 12))
        self._grid_frame.pack()

    def _form_kirli_mi(self):
        if self.duzenlenen_id:
            return True
        if self.ent_isim.get().strip():
            return True
        for renk in self.renkler:
            if renk["ent_doluluk"].get().strip():
                if renk["ent_doluluk"].get().strip() not in ("", "50"):
                    return True
            for row_ref in renk["urunler"]:
                e_ad, e_mik, e_fiy, _c_par = row_ref["fields"]
                if e_ad.get().strip() or e_mik.get().strip() or e_fiy.get().strip():
                    return True
        return False

    def yeni_recete(self):
        if self._form_kirli_mi():
            if not msg_yesno(
                self,
                "Onay",
                "Kaydedilmemiş değişiklikler silinecek. Devam edilsin mi?",
            ):
                return
        self._formu_sifirla()

    def _formu_sifirla(self):
        self.duzenlenen_id = None
        self.ent_isim.delete(0, tk.END)
        self.ent_fire.delete(0, tk.END)
        self.ent_fire.insert(0, str(int(FIRE_YUZDE_VARSAYILAN)))
        self.cmb_renk_sayisi.set("1")
        self.lbl_tl.config(text="0.00 TL")
        self.lbl_doviz.config(text="$ 0.00 | € 0.00")
        self._renkleri_kur(1)
        self._durum_guncelle()

    def _renkleri_olustur_tik(self):
        try:
            n = int(self.cmb_renk_sayisi.get())
            if n < 1 or n > MAX_RENK:
                raise ValueError
        except (TypeError, ValueError):
            msg_error(self, "Hata", f"Renk sayısı 1–{MAX_RENK} arasında olmalıdır.")
            return
        if self.renkler and self._form_kirli_mi():
            if not msg_yesno(
                self,
                "Onay",
                f"{n} renk paneli oluşturulacak. Mevcut ürün satırları silinir. Devam?",
            ):
                return
        self._renkleri_kur(n)

    def _temizle_renk_alani(self):
        for widget in self.mid_panel.scrollable_frame.winfo_children():
            widget.destroy()
        self.renkler.clear()

    def _renkleri_kur(self, renk_sayisi, icerik=None):
        """icerik varsa renk_no ile grupla; yoksa boş paneller oluştur."""
        self._temizle_renk_alani()
        gruplar = {}
        if icerik:
            for item in icerik:
                rno = int(item.get("renk_no") or 1)
                gruplar.setdefault(rno, []).append(item)
            numaralar = sorted(gruplar.keys()) or [1]
            self.cmb_renk_sayisi.set(str(len(numaralar)))
            for rno in numaralar:
                self._renk_paneli_ekle(rno, urunler=gruplar.get(rno))
        else:
            for rno in range(1, renk_sayisi + 1):
                self._renk_paneli_ekle(rno, urun_adet=1)

    def _renk_paneli_ekle(self, renk_no, urunler=None, urun_adet=1):
        parent = self.mid_panel.scrollable_frame
        kart = tk.Frame(parent, bg=RENK_KART, padx=12, pady=10, highlightthickness=1)
        kart.configure(highlightbackground="#d0d7de", highlightcolor="#d0d7de")
        kart.pack(fill="x", padx=8, pady=8)

        baslik = tk.Frame(kart, bg=RENK_KART)
        baslik.pack(fill="x")

        tk.Label(
            baslik,
            text=f"{renk_no}. RENK",
            font=FONT_BOLD,
            bg=RENK_KART,
            fg=RENK_METIN,
        ).pack(side="left")

        tk.Label(
            baslik,
            text="Ürün adedi:",
            bg=RENK_KART,
            fg=RENK_METIN_SOLUK,
            font=FONT_NORMAL,
        ).pack(side="left", padx=(16, 4))
        cmb_adet = ttk.Combobox(
            baslik,
            values=[str(i) for i in range(1, MAX_URUN_RENK + 1)],
            width=5,
            state="readonly",
        )
        baslangic_adet = len(urunler) if urunler else urun_adet
        cmb_adet.set(str(max(1, baslangic_adet)))
        cmb_adet.pack(side="left")

        lbl_renk_maliyet = tk.Label(
            baslik,
            text="",
            bg=RENK_KART,
            fg=RENK_VURGU,
            font=FONT_BOLD,
        )
        lbl_renk_maliyet.pack(side="right")

        param_satir = tk.Frame(kart, bg=RENK_KART)
        param_satir.pack(fill="x", pady=(8, 4))
        lbl_dol = tk.Label(
            param_satir,
            text="Doluluk Oranı (%)",
            bg=RENK_KART,
            font=FONT_BOLD,
            fg=RENK_METIN_SOLUK,
        )
        lbl_dol.pack(side="left")
        ent_doluluk = ttk.Entry(param_satir, width=10, font=FONT_NORMAL)
        doluluk_deger = "50"
        if urunler and urunler[0].get("doluluk") is not None:
            doluluk_deger = str(urunler[0]["doluluk"])
        ent_doluluk.insert(0, doluluk_deger)
        ent_doluluk.pack(side="left", padx=8)
        ToolTip(ent_doluluk, IPUCU_DOLULUK)
        ToolTip(lbl_dol, IPUCU_DOLULUK)

        tablo = tk.Frame(kart, bg=RENK_KART)
        tablo.pack(fill="x", pady=(4, 0))

        headers = ["Katalog", "Ürün Adı", "Miktar (g/kg)", "Birim Fiyat", "Para", ""]
        for col, h in enumerate(headers):
            tk.Label(
                tablo, text=h, bg=RENK_KART, font=FONT_BOLD, fg="#95a5a6"
            ).grid(row=0, column=col, padx=5, pady=4, sticky="w")

        renk_ref = {
            "renk_no": renk_no,
            "kart": kart,
            "cmb_adet": cmb_adet,
            "ent_doluluk": ent_doluluk,
            "tablo": tablo,
            "lbl_maliyet": lbl_renk_maliyet,
            "urunler": [],
        }

        ModernButton(
            baslik,
            text="Ürünleri Ayarla",
            bg="#2980b9",
            fg="white",
            width=12,
            command=lambda r=renk_ref: self._urun_adet_uygula(r),
        ).pack(side="left", padx=8)

        if urunler:
            for item in urunler:
                self._urun_satiri_ekle(renk_ref, item)
        else:
            for _ in range(max(1, urun_adet)):
                self._urun_satiri_ekle(renk_ref)

        self.renkler.append(renk_ref)

    def _urun_adet_uygula(self, renk_ref):
        try:
            adet = int(renk_ref["cmb_adet"].get())
            if adet < 1 or adet > MAX_URUN_RENK:
                raise ValueError
        except (TypeError, ValueError):
            msg_error(
                self, "Hata", f"Ürün adedi 1–{MAX_URUN_RENK} arasında olmalıdır."
            )
            return
        mevcut = []
        for row_ref in renk_ref["urunler"]:
            e_ad, e_mik, e_fiy, c_par = row_ref["fields"]
            mevcut.append(
                {
                    "ad": e_ad.get(),
                    "miktar": e_mik.get(),
                    "fiyat": e_fiy.get(),
                    "para": c_par.get() or "TL",
                }
            )
        for row_ref in list(renk_ref["urunler"]):
            for w in row_ref["widgets"]:
                w.destroy()
        renk_ref["urunler"].clear()
        for i in range(adet):
            item = None
            if i < len(mevcut):
                m = mevcut[i]
                if m["ad"].strip() or str(m["miktar"]).strip() or str(m["fiyat"]).strip():
                    item = {
                        "ad": m["ad"],
                        "miktar": m["miktar"] if str(m["miktar"]).strip() else "",
                        "fiyat": m["fiyat"] if str(m["fiyat"]).strip() else "",
                        "para": m["para"],
                    }
            self._urun_satiri_ekle(renk_ref, item)

    def _urun_satiri_ekle(self, renk_ref, item=None):
        tablo = renk_ref["tablo"]
        row = len(renk_ref["urunler"]) + 1
        katalog_adlari = self._katalog_adlari()

        c_kat = ttk.Combobox(
            tablo,
            values=["— Katalogdan seç —"] + katalog_adlari,
            width=18,
            state="readonly",
        )
        c_kat.set("— Katalogdan seç —")
        c_kat.grid(row=row, column=0, padx=5, pady=3)

        e_ad = ttk.Entry(tablo, width=22)
        e_ad.grid(row=row, column=1, padx=5, pady=3)
        e_miktar = ttk.Entry(tablo, width=12)
        e_miktar.grid(row=row, column=2, padx=5, pady=3)
        ToolTip(e_miktar, IPUCU_BASKI_MIKTAR)
        e_fiyat = ttk.Entry(tablo, width=12)
        e_fiyat.grid(row=row, column=3, padx=5, pady=3)
        c_para = ttk.Combobox(
            tablo, values=["TL", "USD", "EUR"], width=6, state="readonly"
        )
        c_para.current(0)
        c_para.grid(row=row, column=4, padx=5, pady=3)

        row_ref = {
            "fields": (e_ad, e_miktar, e_fiyat, c_para),
            "widgets": [c_kat, e_ad, e_miktar, e_fiyat, c_para],
        }
        btn_sil = tk.Button(
            tablo,
            text="✕",
            bg=RENK_TEHLIKE,
            fg="white",
            relief="flat",
            cursor="hand2",
            width=3,
            command=lambda rr=row_ref, rk=renk_ref: self._urun_sil(rk, rr),
        )
        btn_sil.grid(row=row, column=5, padx=5, pady=3)
        row_ref["widgets"].append(btn_sil)

        c_kat.bind(
            "<<ComboboxSelected>>",
            lambda e, ck=c_kat, ea=e_ad, ef=e_fiyat, cp=c_para: self._katalog_uygula(
                ck, ea, ef, cp
            ),
        )

        if item:
            e_ad.insert(0, item.get("ad", "") or "")
            mik = item.get("miktar", "")
            if mik != "" and mik is not None:
                e_miktar.insert(0, str(mik))
            fiy = item.get("fiyat", "")
            if fiy != "" and fiy is not None:
                e_fiyat.insert(0, str(fiy))
            para = item.get("para") or "TL"
            if para in ("TL", "USD", "EUR"):
                c_para.set(para)
            if item.get("ad") in katalog_adlari:
                c_kat.set(item["ad"])

        renk_ref["urunler"].append(row_ref)

    def _urun_sil(self, renk_ref, row_ref):
        if len(renk_ref["urunler"]) <= 1:
            msg_info(self, "Bilgi", "Her renkte en az bir ürün satırı olmalıdır.")
            return
        if row_ref not in renk_ref["urunler"]:
            return
        for w in row_ref["widgets"]:
            w.destroy()
        renk_ref["urunler"].remove(row_ref)
        for i, rr in enumerate(renk_ref["urunler"]):
            for col, widget in enumerate(rr["widgets"]):
                widget.grid(row=i + 1, column=col, padx=5, pady=3)
        renk_ref["cmb_adet"].set(str(len(renk_ref["urunler"])))

    def yukle_recete(self, recete):
        self.duzenlenen_id = recete["id"]
        self.ent_isim.delete(0, tk.END)
        self.ent_isim.insert(0, recete.get("isim", ""))
        self.ent_fire.delete(0, tk.END)
        carpan = float(recete.get("fire_orani", FIRE_ORANI_VARSAYILAN))
        self.ent_fire.insert(0, f"{fire_carpan_to_yuzde(carpan):g}")
        self._renkleri_kur(1, icerik=recete.get("icerik") or [])
        self._durum_guncelle()
        self.hesapla()

    def verileri_al(self):
        fire_orani = fire_yuzde_to_carpan(parse_fire_yuzde(self.ent_fire.get()))
        if not self.renkler:
            raise ValidationError("En az bir renk paneli oluşturun.")

        icerik = []
        for renk in self.renkler:
            rno = renk["renk_no"]
            doluluk = parse_pozitif(
                renk["ent_doluluk"].get(), f"{rno}. renk doluluk oranı (%)"
            )
            dolu_urun = 0
            for satir_no, row_ref in enumerate(renk["urunler"], start=1):
                e_ad, e_mik, e_fiy, c_par = row_ref["fields"]
                ad = e_ad.get().strip()
                if not ad:
                    continue
                para = c_par.get() or "TL"
                if para not in ("TL", "USD", "EUR"):
                    raise ValidationError(
                        f"{rno}. renk / {satir_no}. satır: bilinmeyen para birimi."
                    )
                icerik.append(
                    {
                        "ad": ad,
                        "miktar": parse_pozitif(
                            e_mik.get(), f"{rno}. renk / {satir_no}. satır miktar"
                        ),
                        "birim": "g/kg",
                        "fiyat": parse_pozitif(
                            e_fiy.get(), f"{rno}. renk / {satir_no}. satır fiyat"
                        ),
                        "para": para,
                        "renk_no": rno,
                        "doluluk": doluluk,
                    }
                )
                dolu_urun += 1
            if dolu_urun == 0:
                raise ValidationError(
                    f"{rno}. renkte en az bir ürün adı, miktar ve fiyat girin."
                )

        if not icerik:
            raise ValidationError("Hesaplamak için en az bir ürün satırı doldurun.")
        return icerik, fire_orani

    def hesapla(self):
        try:
            data, fire = self.verileri_al()
            toplam_tl = recete_toplam(
                data, self.tip, 1.0, self.controller.kurlar, fire
            )
        except ValidationError as exc:
            msg_error(self, "Hata", str(exc))
            return None

        # renk alt toplamları
        for renk in self.renkler:
            rno = renk["renk_no"]
            alt = 0.0
            try:
                doluluk = parse_pozitif(renk["ent_doluluk"].get(), "doluluk")
                for row_ref in renk["urunler"]:
                    e_ad, e_mik, e_fiy, c_par = row_ref["fields"]
                    ad = e_ad.get().strip()
                    if not ad:
                        continue
                    item = {
                        "ad": ad,
                        "miktar": parse_pozitif(e_mik.get(), "miktar"),
                        "birim": "g/kg",
                        "fiyat": parse_pozitif(e_fiy.get(), "fiyat"),
                        "para": c_par.get() or "TL",
                        "doluluk": doluluk,
                    }
                    alt += maliyet_hesapla(
                        item, self.tip, 1.0, self.controller.kurlar, fire
                    )
                renk["lbl_maliyet"].config(text=f"Renk maliyeti: {alt:.4f} TL")
            except ValidationError:
                renk["lbl_maliyet"].config(text="")

        usd = toplam_tl / self.controller.kurlar["USD"]
        eur = toplam_tl / self.controller.kurlar["EUR"]
        self.lbl_tl.config(text=f"{toplam_tl:.4f} TL / Kg")
        self.lbl_doviz.config(text=f"$ {usd:.4f} | € {eur:.4f}")
        return toplam_tl

    def kaydet(self):
        isim = self.ent_isim.get().strip()
        if not isim:
            msg_error(self, "Hata", "Reçete adı zorunludur.")
            return
        tutar = self.hesapla()
        if tutar is None:
            return
        try:
            data, fire = self.verileri_al()
        except ValidationError as exc:
            msg_error(self, "Hata", str(exc))
            return

        db = self.controller.db
        param = 1.0

        if self.duzenlenen_id:
            ok = db.guncelle(
                self.duzenlenen_id, self.tip, isim, param, data, fire
            )
            if not ok:
                msg_error(self, "Hata", "Güncellenecek kayıt bulunamadı.")
                return
            self._toast(f"Reçete güncellendi (ID: {self.duzenlenen_id})")
            return

        mevcut_id = db.son_id_by_isim(self.tip, isim)
        if mevcut_id:
            cevap = msg_yesnocancel(
                self,
                "Aynı isimde reçete var",
                f"'{isim}' adında kayıt mevcut (ID: {mevcut_id}).\n\n"
                "Evet: Üzerine yaz\n"
                "Hayır: Yeni kayıt oluştur\n"
                "İptal: Vazgeç",
            )
            if cevap is None:
                return
            if cevap:
                db.guncelle(mevcut_id, self.tip, isim, param, data, fire)
                self.duzenlenen_id = mevcut_id
                self._durum_guncelle()
                self._toast(f"Reçete üzerine yazıldı (ID: {mevcut_id})")
                return

        yeni_id = db.kaydet(self.tip, isim, param, data, fire)
        self.duzenlenen_id = yeni_id
        self._durum_guncelle()
        self._toast(f"Reçete kaydedildi (ID: {yeni_id})")
