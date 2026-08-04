"""Reçete karşılaştırma diyaloğu."""
import tkinter as tk
from tkinter import messagebox, ttk

from tekstil_maliyet.constants import FONT_BASLIK, FONT_BOLD, FONT_NORMAL, RENK_BG, RENK_KART
from tekstil_maliyet.karsilastirma import karsilastir
from tekstil_maliyet.ui.widgets import ModernButton


class KarsilastirDialog(tk.Toplevel):
    def __init__(self, parent, receteler, kurlar):
        super().__init__(parent)
        self.title("Reçete Karşılaştırma")
        self.configure(bg=RENK_BG)
        self.geometry("920x560")
        self.minsize(780, 480)
        self.transient(parent)
        self.grab_set()

        try:
            sonuc = karsilastir(receteler, kurlar)
        except ValueError as exc:
            messagebox.showerror("Hata", str(exc), parent=self)
            self.destroy()
            return

        self.sonuc = sonuc
        ozetler = sonuc["ozetler"]

        tk.Label(
            self,
            text="REÇETE KARŞILAŞTIRMA",
            font=FONT_BASLIK,
            bg=RENK_BG,
            fg="#2c3e50",
        ).pack(pady=(16, 4))

        en_ucuz = next(o for o in ozetler if o["en_ucuz"])
        tk.Label(
            self,
            text=(
                f"En ucuz: #{en_ucuz['id']} {en_ucuz['isim']} — "
                f"{en_ucuz['maliyet']:.4f} TL/kg"
            ),
            font=FONT_BOLD,
            bg=RENK_BG,
            fg="#27ae60",
        ).pack(pady=(0, 10))

        # Özet tablo
        ozet_frame = tk.LabelFrame(
            self, text="Özet", bg=RENK_KART, font=FONT_BOLD, fg="#2c3e50", padx=8, pady=8
        )
        ozet_frame.pack(fill="x", padx=16, pady=(0, 8))

        ozet_cols = (
            "Id",
            "Isim",
            "Tur",
            "Param",
            "Fire",
            "Maliyet",
            "FarkTL",
            "FarkYuzde",
        )
        self.tree_ozet = ttk.Treeview(
            ozet_frame, columns=ozet_cols, show="headings", height=min(6, len(ozetler) + 1)
        )
        headings = {
            "Id": ("ID", 50),
            "Isim": ("Reçete", 180),
            "Tur": ("Tür", 80),
            "Param": ("Parametre", 100),
            "Fire": ("Fire", 60),
            "Maliyet": ("TL/kg", 90),
            "FarkTL": ("Fark TL", 80),
            "FarkYuzde": ("Fark %", 70),
        }
        for col, (baslik, w) in headings.items():
            self.tree_ozet.heading(col, text=baslik)
            self.tree_ozet.column(col, width=w, anchor="center" if col != "Isim" else "w")
        self.tree_ozet.tag_configure("ucuz", background="#d5f5e3")
        self.tree_ozet.pack(fill="x")

        for o in ozetler:
            tags = ("ucuz",) if o["en_ucuz"] else ()
            if o.get("hata"):
                maliyet_s = "HATA"
                fark_tl_s = "—"
                fark_y_s = "—"
            else:
                maliyet_s = f"{o['maliyet']:.4f}"
                fark_tl_s = f"{o['fark_tl']:+.4f}" if not o["en_ucuz"] else "—"
                fark_y_s = f"{o['fark_yuzde']:+.1f}%" if not o["en_ucuz"] else "—"
            self.tree_ozet.insert(
                "",
                "end",
                values=(
                    o["id"],
                    o["isim"][:40],
                    o["tur"],
                    o["param_metin"],
                    f"{o['fire_orani']:.2f}",
                    maliyet_s,
                    fark_tl_s,
                    fark_y_s,
                ),
                tags=tags,
            )

        # Ürün satırları
        urun_frame = tk.LabelFrame(
            self,
            text="Ürün bazlı maliyet (TL)",
            bg=RENK_KART,
            font=FONT_BOLD,
            fg="#2c3e50",
            padx=8,
            pady=8,
        )
        urun_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        urun_cols = ["Urun"] + [f"R{o['id']}" for o in ozetler]
        self.tree_urun = ttk.Treeview(
            urun_frame, columns=urun_cols, show="headings", height=12
        )
        self.tree_urun.heading("Urun", text="Ürün")
        self.tree_urun.column("Urun", width=180, anchor="w")
        for o in ozetler:
            col = f"R{o['id']}"
            self.tree_urun.heading(col, text=f"#{o['id']}")
            self.tree_urun.column(col, width=110, anchor="e")
        self.tree_urun.tag_configure("fark", background="#fdebd0")

        scroll = ttk.Scrollbar(urun_frame, orient="vertical", command=self.tree_urun.yview)
        self.tree_urun.configure(yscrollcommand=scroll.set)
        self.tree_urun.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        for satir in sonuc["urun_satirlari"]:
            vals = [satir["ad"]]
            farkli = False
            mevcut = [d for d in satir["degerler"] if d is not None]
            if len(set(round(d, 4) for d in mevcut)) > 1:
                farkli = True
            for d in satir["degerler"]:
                vals.append(f"{d:.4f}" if d is not None else "—")
            self.tree_urun.insert(
                "", "end", values=vals, tags=("fark",) if farkli else ()
            )

        bot = tk.Frame(self, bg=RENK_BG)
        bot.pack(fill="x", padx=16, pady=(0, 14))
        tk.Label(
            bot,
            text="Yeşil = en ucuz  ·  Turuncu satır = ürün maliyetleri farklı",
            bg=RENK_BG,
            fg="#7f8c8d",
            font=FONT_NORMAL,
        ).pack(side="left")
        ModernButton(
            bot, text="Kapat", bg="#7f8c8d", fg="white", width=10, command=self.destroy
        ).pack(side="right")
