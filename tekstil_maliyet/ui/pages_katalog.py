"""Kimyasal katalog sayfası."""
import sqlite3
import tkinter as tk
from tkinter import ttk

from tekstil_maliyet.constants import (
    FONT_BASLIK,
    FONT_BOLD,
    FONT_NORMAL,
    RENK_BASARI,
    RENK_BG,
    RENK_IKINCIL,
    RENK_KART,
    RENK_METIN,
    RENK_METIN_SOLUK,
    RENK_TEHLIKE,
    RENK_VURGU,
)
from tekstil_maliyet.hesaplama import ValidationError, parse_pozitif
from tekstil_maliyet.ui.widgets import (
    EmptyState,
    ModernButton,
    msg_error,
    msg_info,
    msg_yesno,
)


class KatalogPage(ttk.Frame):
    """Kimyasal / boya ürün fiyat kataloğu yönetimi."""

    def __init__(self, parent, controller):
        super().__init__(parent, style="TFrame")
        self.controller = controller
        self._secili_id = None
        self._secili_aktif = True

        tk.Label(
            self,
            text="KİMYASAL KATALOĞU",
            font=FONT_BASLIK,
            bg=RENK_BG,
            fg=RENK_METIN,
        ).pack(pady=20)

        form = tk.Frame(self, bg=RENK_KART, padx=20, pady=15)
        form.pack(fill="x", padx=40)

        tk.Label(
            form, text="Ürün Adı", bg=RENK_KART, font=FONT_BOLD, fg=RENK_METIN_SOLUK
        ).grid(row=0, column=0, sticky="w", padx=5)
        self.ent_ad = ttk.Entry(form, width=28, font=FONT_NORMAL)
        self.ent_ad.grid(row=1, column=0, padx=5, pady=5)

        tk.Label(
            form, text="Birim", bg=RENK_KART, font=FONT_BOLD, fg=RENK_METIN_SOLUK
        ).grid(row=0, column=1, sticky="w", padx=5)
        self.cmb_birim = ttk.Combobox(
            form,
            values=["g/l", "%", "g/l (Apre)", "% (Boya)"],
            width=14,
            state="readonly",
        )
        self.cmb_birim.set("g/l")
        self.cmb_birim.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(
            form, text="Fiyat", bg=RENK_KART, font=FONT_BOLD, fg=RENK_METIN_SOLUK
        ).grid(row=0, column=2, sticky="w", padx=5)
        self.ent_fiyat = ttk.Entry(form, width=12, font=FONT_NORMAL)
        self.ent_fiyat.grid(row=1, column=2, padx=5, pady=5)

        tk.Label(
            form, text="Para", bg=RENK_KART, font=FONT_BOLD, fg=RENK_METIN_SOLUK
        ).grid(row=0, column=3, sticky="w", padx=5)
        self.cmb_para = ttk.Combobox(
            form, values=["TL", "USD", "EUR"], width=8, state="readonly"
        )
        self.cmb_para.set("TL")
        self.cmb_para.grid(row=1, column=3, padx=5, pady=5)

        btns = tk.Frame(form, bg=RENK_KART)
        btns.grid(row=1, column=4, padx=15)
        ModernButton(
            btns,
            text="KAYDET",
            bg=RENK_BASARI,
            fg="white",
            width=10,
            command=self.kaydet,
        ).pack(side="left", padx=3)
        ModernButton(
            btns,
            text="TEMİZLE",
            bg=RENK_IKINCIL,
            fg="white",
            width=10,
            command=self.temizle,
        ).pack(side="left", padx=3)

        self.liste_alani = tk.Frame(self, bg=RENK_BG)
        self.liste_alani.pack(fill="both", expand=True, padx=40, pady=15)

        cols = ("Id", "Ad", "Birim", "Fiyat", "Para", "Aktif")
        self.tree = ttk.Treeview(
            self.liste_alani, columns=cols, show="headings", height=14
        )
        self.tree.heading("Id", text="ID")
        self.tree.heading("Ad", text="ÜRÜN")
        self.tree.heading("Birim", text="BİRİM")
        self.tree.heading("Fiyat", text="FİYAT")
        self.tree.heading("Para", text="PARA")
        self.tree.heading("Aktif", text="AKTİF")
        self.tree.column("Id", width=60, anchor="center")
        self.tree.column("Ad", width=260)
        self.tree.column("Birim", width=100, anchor="center")
        self.tree.column("Fiyat", width=100, anchor="e")
        self.tree.column("Para", width=70, anchor="center")
        self.tree.column("Aktif", width=70, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._secim)

        self.bos_durum = EmptyState(
            self.liste_alani,
            baslik="Katalog boş",
            aciklama="Yukarıdaki formdan ürün ekleyin; hesaplama satırlarında hızlı seçilir.",
        )

        bot = tk.Frame(self, bg=RENK_BG)
        bot.pack(fill="x", padx=40, pady=(0, 20))
        ModernButton(
            bot,
            text="KALICI SİL",
            bg=RENK_TEHLIKE,
            fg="white",
            width=12,
            command=self.kalici_sil,
        ).pack(side="right")
        self.btn_pasif = ModernButton(
            bot,
            text="PASİFE AL",
            bg=RENK_VURGU,
            fg="white",
            width=12,
            command=self.aktiflik_degistir,
        )
        self.btn_pasif.pack(side="right", padx=10)
        ModernButton(
            bot,
            text="YENİLE",
            bg=RENK_IKINCIL,
            fg="white",
            width=10,
            command=self.on_show,
        ).pack(side="right", padx=10)

    def _toast(self, msg, kind="ok"):
        if hasattr(self.controller, "toast"):
            self.controller.toast.show(msg, kind=kind)

    def _bos_goster(self, goster):
        if goster:
            self.tree.pack_forget()
            self.bos_durum.pack(fill="both", expand=True)
        else:
            self.bos_durum.pack_forget()
            self.tree.pack(fill="both", expand=True)

    def on_show(self):
        self.temizle()
        for i in self.tree.get_children():
            self.tree.delete(i)
        urunler = self.controller.db.katalog_listele(sadece_aktif=False)
        for u in urunler:
            self.tree.insert(
                "",
                "end",
                iid=str(u["id"]),
                values=(
                    u["id"],
                    u["ad"],
                    u["birim"],
                    f"{u['fiyat']:.4f}",
                    u["para"],
                    "Evet" if u["aktif"] else "Hayır",
                ),
            )
        self._bos_goster(len(urunler) == 0)

    def _secim(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])["values"]
        self._secili_id = int(vals[0])
        self._secili_aktif = str(vals[5]).lower() in ("evet", "1", "true")
        self.ent_ad.delete(0, tk.END)
        self.ent_ad.insert(0, vals[1])
        self.cmb_birim.set(vals[2])
        self.ent_fiyat.delete(0, tk.END)
        self.ent_fiyat.insert(0, str(vals[3]))
        self.cmb_para.set(vals[4])
        self.btn_pasif.config(
            text="AKTİF ET" if not self._secili_aktif else "PASİFE AL"
        )

    def temizle(self):
        self._secili_id = None
        self._secili_aktif = True
        self.ent_ad.delete(0, tk.END)
        self.ent_fiyat.delete(0, tk.END)
        self.cmb_birim.set("g/l")
        self.cmb_para.set("TL")
        self.btn_pasif.config(text="PASİFE AL")
        self.tree.selection_remove(self.tree.selection())

    def kaydet(self):
        try:
            ad = self.ent_ad.get().strip()
            fiyat = parse_pozitif(self.ent_fiyat.get(), "Fiyat")
            birim = self.cmb_birim.get() or "g/l"
            para = self.cmb_para.get() or "TL"
            if para not in ("TL", "USD", "EUR"):
                raise ValidationError("Para birimi TL, USD veya EUR olmalıdır.")
            if self._secili_id:
                self.controller.db.katalog_guncelle(
                    self._secili_id,
                    ad,
                    birim,
                    fiyat,
                    para,
                    aktif=self._secili_aktif,
                )
                self._toast("Katalog kaydı güncellendi")
            else:
                self.controller.db.katalog_ekle(ad, birim, fiyat, para)
                self._toast("Ürün kataloğa eklendi")
            self.on_show()
        except ValidationError as exc:
            msg_error(self, "Hata", str(exc))
        except sqlite3.IntegrityError:
            msg_error(self, "Hata", "Bu ürün adı katalogda zaten var.")

    def aktiflik_degistir(self):
        if not self._secili_id:
            msg_info(self, "Bilgi", "Önce bir kayıt seçin.")
            return
        yeni_aktif = not self._secili_aktif
        ad = self.ent_ad.get().strip()
        try:
            fiyat = parse_pozitif(self.ent_fiyat.get(), "Fiyat")
        except ValidationError as exc:
            msg_error(self, "Hata", str(exc))
            return
        birim = self.cmb_birim.get() or "g/l"
        para = self.cmb_para.get() or "TL"
        self.controller.db.katalog_guncelle(
            self._secili_id, ad, birim, fiyat, para, aktif=yeni_aktif
        )
        self._toast(
            "Ürün aktif edildi" if yeni_aktif else "Ürün pasife alındı",
            kind="info",
        )
        self.on_show()

    def kalici_sil(self):
        if not self._secili_id:
            msg_info(self, "Bilgi", "Silmek için bir kayıt seçin.")
            return
        if not msg_yesno(
            self,
            "Kalıcı sil",
            "Seçili katalog kaydı kalıcı olarak silinecek. Emin misiniz?",
        ):
            return
        self.controller.db.katalog_sil(self._secili_id)
        self.on_show()
        self._toast("Katalog kaydı kalıcı silindi", kind="info")
