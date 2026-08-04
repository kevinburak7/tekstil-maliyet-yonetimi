"""Reçete hesaplama sayfaları."""
import tkinter as tk
from tkinter import ttk

from tekstil_maliyet.constants import (
    FIRE_ORANI_VARSAYILAN,
    FONT_BASLIK,
    FONT_BOLD,
    FONT_NORMAL,
    IPUCU_FIRE,
    IPUCU_FLOTTE,
    IPUCU_PICKUP,
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
    parse_float,
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


class BasePage(ttk.Frame):
    def __init__(self, parent, controller, title, tip):
        super().__init__(parent, style="TFrame")
        self.controller = controller
        self.tip = tip
        self.duzenlenen_id = None

        top_panel = tk.Frame(self, bg=RENK_KART, padx=20, pady=16)
        top_panel.pack(fill="x", pady=(0, 12))
        self._top_panel = top_panel

        self.lbl_baslik = tk.Label(
            top_panel, text=title, font=FONT_BASLIK, bg=RENK_KART, fg=RENK_METIN
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

        self.lbl_param = tk.Label(
            grid_frame,
            text="Parametre",
            bg=RENK_KART,
            font=FONT_BOLD,
            fg=RENK_METIN_SOLUK,
        )
        self.ent_param = ttk.Entry(grid_frame, width=15, font=FONT_NORMAL)

        col = 1
        if tip == "Kimyasal":
            self.lbl_param.config(text="Flotte (1/X)")
            self.lbl_param.grid(row=0, column=col, padx=10, sticky="w")
            self.ent_param.grid(row=1, column=col, padx=10, pady=5)
            ToolTip(self.ent_param, IPUCU_FLOTTE)
            ToolTip(self.lbl_param, IPUCU_FLOTTE)
            col += 1
        elif tip == "Apre":
            self.lbl_param.config(text="Pick-up (%)")
            self.lbl_param.grid(row=0, column=col, padx=10, sticky="w")
            self.ent_param.grid(row=1, column=col, padx=10, pady=5)
            ToolTip(self.ent_param, IPUCU_PICKUP)
            ToolTip(self.lbl_param, IPUCU_PICKUP)
            col += 1

        lbl_fire = tk.Label(
            grid_frame,
            text="Fire Oranı",
            bg=RENK_KART,
            font=FONT_BOLD,
            fg=RENK_METIN_SOLUK,
        )
        lbl_fire.grid(row=0, column=col, padx=10, sticky="w")
        self.ent_fire = ttk.Entry(grid_frame, width=12, font=FONT_NORMAL)
        self.ent_fire.insert(0, str(FIRE_ORANI_VARSAYILAN))
        self.ent_fire.grid(row=1, column=col, padx=10, pady=5)
        ToolTip(self.ent_fire, IPUCU_FIRE)
        ToolTip(lbl_fire, IPUCU_FIRE)

        self.mid_panel = ScrollableFrame(self)
        self.mid_panel.pack(fill="both", expand=True)
        self.urun_satirlari = []
        self._widths = [20, 20, 10, 10, 10, 7]
        self._headers_hazir = False

        row_bar = tk.Frame(self, bg=RENK_BG)
        row_bar.pack(fill="x", padx=10, pady=(0, 6))
        ModernButton(
            row_bar,
            text="+ Satır Ekle",
            bg="#2980b9",
            fg="white",
            width=14,
            command=self.satir_ekle,
        ).pack(side="left", padx=4)

        tk.Label(
            row_bar, text="Adet:", bg=RENK_BG, fg=RENK_METIN_SOLUK, font=FONT_NORMAL
        ).pack(side="left", padx=(12, 4))
        self.ent_ekle_adet = ttk.Entry(row_bar, width=4, font=FONT_NORMAL)
        self.ent_ekle_adet.insert(0, "1")
        self.ent_ekle_adet.pack(side="left")
        ModernButton(
            row_bar,
            text="Ekle",
            bg="#2980b9",
            fg="white",
            width=6,
            command=self.coklu_satir_ekle,
        ).pack(side="left", padx=4)

        ModernButton(
            row_bar,
            text="Son Satırı Sil",
            bg=RENK_TEHLIKE,
            fg="white",
            width=14,
            command=self.son_satiri_sil,
        ).pack(side="left", padx=8)
        self.lbl_satir_bilgi = tk.Label(
            row_bar, text="Satır: 0", bg=RENK_BG, fg=RENK_METIN_SOLUK, font=FONT_NORMAL
        )
        self.lbl_satir_bilgi.pack(side="left", padx=12)

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

        self.satir_ekle()

    def _toast(self, msg, kind="ok"):
        if hasattr(self.controller, "toast"):
            self.controller.toast.show(msg, kind=kind)

    def on_show(self):
        self._katalog_comboboxlari_yenile()

    def kurlar_degisti(self):
        """Kur yenilendiğinde footer toplamını sessizce güncelle."""
        try:
            data, param, fire = self.verileri_al()
            toplam_tl = recete_toplam(
                data, self.tip, param, self.controller.kurlar, fire
            )
        except ValidationError:
            return
        usd = toplam_tl / self.controller.kurlar["USD"]
        eur = toplam_tl / self.controller.kurlar["EUR"]
        self.lbl_tl.config(text=f"{toplam_tl:.4f} TL / Kg")
        self.lbl_doviz.config(text=f"$ {usd:.4f} | € {eur:.4f}")

    def _katalog_comboboxlari_yenile(self):
        adlar = ["— Katalogdan seç —"] + self._katalog_adlari()
        for row_ref in self.urun_satirlari:
            c_kat = row_ref["widgets"][0]
            mevcut = c_kat.get()
            c_kat["values"] = adlar
            if mevcut in adlar:
                c_kat.set(mevcut)
            else:
                c_kat.set(adlar[0])

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
        if self.tip in ("Kimyasal", "Apre") and self.ent_param.get().strip():
            return True
        for row_ref in self.urun_satirlari:
            e_ad, e_mik, _c_bir, e_fiy, _c_par = row_ref["fields"]
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
        if self.tip in ("Kimyasal", "Apre"):
            self.ent_param.delete(0, tk.END)
        self.ent_fire.delete(0, tk.END)
        self.ent_fire.insert(0, str(FIRE_ORANI_VARSAYILAN))
        for widget in self.mid_panel.scrollable_frame.winfo_children():
            widget.destroy()
        self.urun_satirlari.clear()
        self._headers_hazir = False
        self.lbl_tl.config(text="0.00 TL")
        self.lbl_doviz.config(text="$ 0.00 | € 0.00")
        self.satir_ekle()
        self._durum_guncelle()

    def _katalog_adlari(self):
        return [u["ad"] for u in self.controller.db.katalog_listele(sadece_aktif=True)]

    def _katalog_uygula(self, c_kat, e_ad, c_birim, e_fiyat, c_para):
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
        birim = urun.get("birim") or ""
        if self.tip == "Kimyasal" and birim in ("g/l", "%"):
            c_birim.set(birim)
        elif self.tip == "Apre":
            c_birim.set("g/l (Apre)")
        elif self.tip == "Boya":
            c_birim.set("% (Boya)")

    def _birim_combobox(self, parent, width):
        if self.tip == "Kimyasal":
            c_birim = ttk.Combobox(
                parent, values=["g/l", "%"], width=width, state="readonly"
            )
            c_birim.current(0)
        elif self.tip == "Apre":
            c_birim = ttk.Combobox(
                parent, values=["g/l (Apre)"], width=width, state="disabled"
            )
            c_birim.set("g/l (Apre)")
        else:
            c_birim = ttk.Combobox(
                parent, values=["% (Boya)"], width=width, state="disabled"
            )
            c_birim.set("% (Boya)")
        return c_birim

    def _sayi_guncelle(self):
        n = len(self.urun_satirlari)
        self.lbl_satir_bilgi.config(text=f"Satır: {n}")

    def _basliklari_kur(self):
        frame = self.mid_panel.scrollable_frame
        headers = ["Katalog", "Ürün Adı", "Miktar", "Birim", "Fiyat", "Para", ""]
        for col, h in enumerate(headers):
            tk.Label(
                frame,
                text=h,
                bg=RENK_KART,
                font=FONT_BOLD,
                fg="#95a5a6",
            ).grid(row=0, column=col, padx=5, pady=10, sticky="w")
        self._headers_hazir = True

    def _satir_ekle(self, row, widths, item=None):
        frame = self.mid_panel.scrollable_frame
        katalog_adlari = self._katalog_adlari()
        c_kat = ttk.Combobox(
            frame,
            values=["— Katalogdan seç —"] + katalog_adlari,
            width=widths[0],
            state="readonly",
        )
        c_kat.set("— Katalogdan seç —")
        c_kat.grid(row=row, column=0, padx=5, pady=5)

        e_ad = ttk.Entry(frame, width=widths[1])
        e_ad.grid(row=row, column=1, padx=5, pady=5)
        e_miktar = ttk.Entry(frame, width=widths[2])
        e_miktar.grid(row=row, column=2, padx=5, pady=5)
        c_birim = self._birim_combobox(frame, widths[3])
        c_birim.grid(row=row, column=3, padx=5, pady=5)
        e_fiyat = ttk.Entry(frame, width=widths[4])
        e_fiyat.grid(row=row, column=4, padx=5, pady=5)
        c_para = ttk.Combobox(
            frame, values=["TL", "USD", "EUR"], width=widths[5], state="readonly"
        )
        c_para.current(0)
        c_para.grid(row=row, column=5, padx=5, pady=5)

        row_ref = {
            "fields": (e_ad, e_miktar, c_birim, e_fiyat, c_para),
            "widgets": [c_kat, e_ad, e_miktar, c_birim, e_fiyat, c_para],
        }
        btn_sil = tk.Button(
            frame,
            text="✕",
            bg=RENK_TEHLIKE,
            fg="white",
            relief="flat",
            cursor="hand2",
            width=3,
            command=lambda r=row_ref: self.satir_sil(r),
        )
        btn_sil.grid(row=row, column=6, padx=5, pady=5)
        row_ref["widgets"].append(btn_sil)

        c_kat.bind(
            "<<ComboboxSelected>>",
            lambda e, ck=c_kat, ea=e_ad, cb=c_birim, ef=e_fiyat, cp=c_para: self._katalog_uygula(
                ck, ea, cb, ef, cp
            ),
        )

        if item:
            e_ad.insert(0, item.get("ad", ""))
            e_miktar.insert(0, str(item.get("miktar", "")))
            e_fiyat.insert(0, str(item.get("fiyat", "")))
            birim = item.get("birim") or ""
            if self.tip == "Kimyasal" and birim in ("g/l", "%"):
                c_birim.set(birim)
            elif self.tip == "Apre":
                c_birim.set("g/l (Apre)")
            elif self.tip == "Boya":
                c_birim.set("% (Boya)")
            para = item.get("para") or "TL"
            if para in ("TL", "USD", "EUR"):
                c_para.set(para)
            if item.get("ad") in katalog_adlari:
                c_kat.set(item["ad"])

        self.urun_satirlari.append(row_ref)

    def _satirlari_yeniden_diz(self):
        for i, row_ref in enumerate(self.urun_satirlari):
            for col, widget in enumerate(row_ref["widgets"]):
                widget.grid(row=i + 1, column=col, padx=5, pady=5)

    def satir_ekle(self):
        if not self._headers_hazir:
            for widget in self.mid_panel.scrollable_frame.winfo_children():
                widget.destroy()
            self.urun_satirlari.clear()
            self._basliklari_kur()
        self._satir_ekle(len(self.urun_satirlari) + 1, self._widths)
        self._sayi_guncelle()

    def coklu_satir_ekle(self):
        try:
            adet = int(self.ent_ekle_adet.get().strip())
            if adet < 1 or adet > 50:
                raise ValueError
        except ValueError:
            msg_error(self, "Hata", "Adet 1–50 arasında bir tam sayı olmalıdır.")
            return
        for _ in range(adet):
            self.satir_ekle()

    def satir_sil(self, row_ref):
        if len(self.urun_satirlari) <= 1:
            msg_info(self, "Bilgi", "En az bir satır bulunmalıdır.")
            return
        if row_ref not in self.urun_satirlari:
            return
        for widget in row_ref["widgets"]:
            widget.destroy()
        self.urun_satirlari.remove(row_ref)
        self._satirlari_yeniden_diz()
        self._sayi_guncelle()

    def son_satiri_sil(self):
        if not self.urun_satirlari:
            msg_info(self, "Bilgi", "Silinecek satır yok.")
            return
        self.satir_sil(self.urun_satirlari[-1])

    def tabloyu_olustur(self, icerik=None):
        for widget in self.mid_panel.scrollable_frame.winfo_children():
            widget.destroy()
        self.urun_satirlari.clear()
        self._headers_hazir = False

        sayi = max(len(icerik), 1) if icerik is not None else 1
        self._basliklari_kur()
        for i in range(sayi):
            item = icerik[i] if icerik and i < len(icerik) else None
            self._satir_ekle(i + 1, self._widths, item)
        self._sayi_guncelle()

    def yukle_recete(self, recete):
        self.duzenlenen_id = recete["id"]
        self.ent_isim.delete(0, tk.END)
        self.ent_isim.insert(0, recete.get("isim", ""))
        if self.tip in ("Kimyasal", "Apre"):
            self.ent_param.delete(0, tk.END)
            self.ent_param.insert(0, str(recete.get("parametre", "")))
        self.ent_fire.delete(0, tk.END)
        self.ent_fire.insert(
            0, str(recete.get("fire_orani", FIRE_ORANI_VARSAYILAN))
        )
        self.tabloyu_olustur(icerik=recete.get("icerik") or [])
        self._durum_guncelle()
        self.hesapla()

    def verileri_al(self):
        parametre = 1.0
        if self.tip in ("Kimyasal", "Apre"):
            alan = "Flotte (1/X)" if self.tip == "Kimyasal" else "Pick-up (%)"
            parametre = parse_pozitif(self.ent_param.get(), alan)

        fire_orani = parse_pozitif(self.ent_fire.get(), "Fire oranı")

        icerik = []
        for satir_no, row_ref in enumerate(self.urun_satirlari, start=1):
            e_ad, e_mik, c_bir, e_fiy, c_par = row_ref["fields"]
            ad = e_ad.get().strip()
            if not ad:
                continue
            para = c_par.get() or "TL"
            if para not in ("TL", "USD", "EUR"):
                raise ValidationError(f"{satir_no}. satır: bilinmeyen para birimi.")
            icerik.append(
                {
                    "ad": ad,
                    "miktar": parse_pozitif(e_mik.get(), f"{satir_no}. satır miktar"),
                    "birim": c_bir.get(),
                    "fiyat": parse_pozitif(e_fiy.get(), f"{satir_no}. satır fiyat"),
                    "para": para,
                }
            )

        if not icerik:
            raise ValidationError("Hesaplamak için en az bir ürün satırı doldurun.")
        return icerik, parametre, fire_orani

    def hesapla(self):
        try:
            data, param, fire = self.verileri_al()
            toplam_tl = recete_toplam(
                data, self.tip, param, self.controller.kurlar, fire
            )
        except ValidationError as exc:
            msg_error(self, "Hata", str(exc))
            return None

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
            data, param, fire = self.verileri_al()
        except ValidationError as exc:
            msg_error(self, "Hata", str(exc))
            return

        db = self.controller.db

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


class YardimciKimyasalPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(
            parent, controller, "YARDIMCI KİMYASAL MALİYETİ", "Kimyasal"
        )


class BoyaMaliyetiPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, "BOYA MALİYETİ", "Boya")


class ApreMaliyetiPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, "APRE (BİTİM) MALİYETİ", "Apre")
