"""Kimyasal katalog sayfası."""
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from tekstil_maliyet.constants import FONT_BASLIK, FONT_BOLD, FONT_NORMAL, RENK_BG, RENK_KART
from tekstil_maliyet.hesaplama import ValidationError, parse_float
from tekstil_maliyet.ui.widgets import ModernButton


class KatalogPage(ttk.Frame):
    """Kimyasal / boya ürün fiyat kataloğu yönetimi."""

    def __init__(self, parent, controller):
        super().__init__(parent, style="TFrame")
        self.controller = controller
        self._secili_id = None

        tk.Label(
            self,
            text="KİMYASAL KATALOĞU",
            font=FONT_BASLIK,
            bg=RENK_BG,
            fg="#2c3e50",
        ).pack(pady=20)

        form = tk.Frame(self, bg=RENK_KART, padx=20, pady=15)
        form.pack(fill="x", padx=40)

        tk.Label(form, text="Ürün Adı", bg=RENK_KART, font=FONT_BOLD, fg="#7f8c8d").grid(
            row=0, column=0, sticky="w", padx=5
        )
        self.ent_ad = ttk.Entry(form, width=28, font=FONT_NORMAL)
        self.ent_ad.grid(row=1, column=0, padx=5, pady=5)

        tk.Label(form, text="Birim", bg=RENK_KART, font=FONT_BOLD, fg="#7f8c8d").grid(
            row=0, column=1, sticky="w", padx=5
        )
        self.cmb_birim = ttk.Combobox(
            form, values=["g/l", "%", "g/l (Apre)", "% (Boya)"], width=14, state="readonly"
        )
        self.cmb_birim.set("g/l")
        self.cmb_birim.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(form, text="Fiyat", bg=RENK_KART, font=FONT_BOLD, fg="#7f8c8d").grid(
            row=0, column=2, sticky="w", padx=5
        )
        self.ent_fiyat = ttk.Entry(form, width=12, font=FONT_NORMAL)
        self.ent_fiyat.grid(row=1, column=2, padx=5, pady=5)

        tk.Label(form, text="Para", bg=RENK_KART, font=FONT_BOLD, fg="#7f8c8d").grid(
            row=0, column=3, sticky="w", padx=5
        )
        self.cmb_para = ttk.Combobox(
            form, values=["TL", "USD", "EUR"], width=8, state="readonly"
        )
        self.cmb_para.set("TL")
        self.cmb_para.grid(row=1, column=3, padx=5, pady=5)

        btns = tk.Frame(form, bg=RENK_KART)
        btns.grid(row=1, column=4, padx=15)
        ModernButton(
            btns, text="KAYDET", bg="#16a085", fg="white", width=10, command=self.kaydet
        ).pack(side="left", padx=3)
        ModernButton(
            btns, text="TEMİZLE", bg="#7f8c8d", fg="white", width=10, command=self.temizle
        ).pack(side="left", padx=3)

        cols = ("Id", "Ad", "Birim", "Fiyat", "Para", "Aktif")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=14)
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
        self.tree.pack(fill="both", expand=True, padx=40, pady=15)
        self.tree.bind("<<TreeviewSelect>>", self._secim)

        bot = tk.Frame(self, bg=RENK_BG)
        bot.pack(fill="x", padx=40, pady=(0, 20))
        ModernButton(
            bot, text="SİL", bg="#c0392b", fg="white", width=12, command=self.sil
        ).pack(side="right")
        ModernButton(
            bot, text="YENİLE", bg="#7f8c8d", fg="white", width=10, command=self.on_show
        ).pack(side="right", padx=10)

    def on_show(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for u in self.controller.db.katalog_listele(sadece_aktif=False):
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

    def _secim(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])["values"]
        self._secili_id = int(vals[0])
        self.ent_ad.delete(0, tk.END)
        self.ent_ad.insert(0, vals[1])
        self.cmb_birim.set(vals[2])
        self.ent_fiyat.delete(0, tk.END)
        self.ent_fiyat.insert(0, str(vals[3]))
        self.cmb_para.set(vals[4])

    def temizle(self):
        self._secili_id = None
        self.ent_ad.delete(0, tk.END)
        self.ent_fiyat.delete(0, tk.END)
        self.cmb_birim.set("g/l")
        self.cmb_para.set("TL")
        self.tree.selection_remove(self.tree.selection())

    def kaydet(self):
        try:
            ad = self.ent_ad.get().strip()
            fiyat = parse_float(self.ent_fiyat.get(), "Fiyat")
            birim = self.cmb_birim.get() or "g/l"
            para = self.cmb_para.get() or "TL"
            if self._secili_id:
                self.controller.db.katalog_guncelle(
                    self._secili_id, ad, birim, fiyat, para, aktif=True
                )
                messagebox.showinfo("Başarılı", "Katalog kaydı güncellendi.")
            else:
                self.controller.db.katalog_ekle(ad, birim, fiyat, para)
                messagebox.showinfo("Başarılı", "Ürün kataloğa eklendi.")
            self.temizle()
            self.on_show()
        except ValidationError as exc:
            messagebox.showerror("Hata", str(exc))
        except sqlite3.IntegrityError:
            messagebox.showerror("Hata", "Bu ürün adı katalogda zaten var.")

    def sil(self):
        if not self._secili_id:
            messagebox.showinfo("Bilgi", "Silmek için bir kayıt seçin.")
            return
        if not messagebox.askyesno("Onay", "Seçili katalog kaydı silinsin mi?"):
            return
        self.controller.db.katalog_sil(self._secili_id)
        self.temizle()
        self.on_show()


