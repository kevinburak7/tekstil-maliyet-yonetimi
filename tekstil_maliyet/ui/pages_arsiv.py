"""Reçete arşiv sayfası."""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from tekstil_maliyet.constants import (
    FIRE_ORANI_VARSAYILAN,
    FONT_BASLIK,
    FONT_BOLD,
    FONT_NORMAL,
    RENK_BG,
    RENK_KART,
)
from tekstil_maliyet.excel_export import excel_aktar
from tekstil_maliyet.hesaplama import ValidationError, maliyet_hesapla, recete_toplam
from tekstil_maliyet.pdf_export import pdf_aktar
from tekstil_maliyet.ui.karsilastir_dialog import KarsilastirDialog
from tekstil_maliyet.ui.widgets import ModernButton


class ArsivPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style="TFrame")
        self.controller = controller
        self._kayitlar = []

        tk.Label(
            self,
            text="REÇETE ARŞİVİ",
            font=FONT_BASLIK,
            bg=RENK_BG,
            fg="#2c3e50",
        ).pack(pady=(20, 10))

        filtre = tk.Frame(self, bg=RENK_KART, padx=12, pady=10)
        filtre.pack(fill="x", padx=40, pady=(0, 8))

        tk.Label(
            filtre, text="Ara", bg=RENK_KART, font=FONT_BOLD, fg="#7f8c8d"
        ).pack(side="left", padx=(0, 6))
        self.ent_ara = ttk.Entry(filtre, width=28, font=FONT_NORMAL)
        self.ent_ara.pack(side="left", padx=(0, 16))
        self.ent_ara.bind("<KeyRelease>", lambda e: self._filtrele())

        tk.Label(
            filtre, text="Tür", bg=RENK_KART, font=FONT_BOLD, fg="#7f8c8d"
        ).pack(side="left", padx=(0, 6))
        self.cmb_tur = ttk.Combobox(
            filtre,
            values=["Tümü", "Kimyasal", "Boya", "Apre"],
            width=12,
            state="readonly",
        )
        self.cmb_tur.set("Tümü")
        self.cmb_tur.pack(side="left", padx=(0, 16))
        self.cmb_tur.bind("<<ComboboxSelected>>", lambda e: self._filtrele())

        ModernButton(
            filtre,
            text="Temizle",
            bg="#7f8c8d",
            fg="white",
            width=10,
            command=self._filtre_temizle,
        ).pack(side="left")

        self.lbl_filtre_ozet = tk.Label(
            filtre, text="", bg=RENK_KART, fg="#7f8c8d", font=FONT_NORMAL
        )
        self.lbl_filtre_ozet.pack(side="right")

        cols = ("Id", "Tur", "Isim", "Tarih", "Maliyet")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=14)
        self.tree.heading("Id", text="ID")
        self.tree.heading("Tur", text="TÜR")
        self.tree.heading("Isim", text="REÇETE ADI")
        self.tree.heading("Tarih", text="TARİH")
        self.tree.heading("Maliyet", text="MALİYET (TL/KG)")
        self.tree.column("Id", anchor="center", width=70)
        self.tree.column("Tur", anchor="center", width=110)
        self.tree.column("Isim", width=260)
        self.tree.column("Tarih", anchor="center", width=150)
        self.tree.column("Maliyet", anchor="e", width=140)
        self.tree.pack(fill="both", expand=True, padx=40, pady=10)
        self.tree.bind("<Button-1>", self.toggle_selection)
        self.tree.bind("<Double-1>", lambda e: self.duzenle())

        bot = tk.Frame(self, bg=RENK_BG)
        bot.pack(fill="x", padx=40, pady=20)

        self.lbl_secim_toplam = tk.Label(
            bot,
            text="Seçilenlerin Toplamı: 0.00 TL",
            font=("Segoe UI", 14, "bold"),
            bg=RENK_BG,
            fg="#27ae60",
        )
        self.lbl_secim_toplam.pack(side="left")

        ModernButton(
            bot,
            text="SEÇİLENLERİ SİL",
            bg="#c0392b",
            fg="white",
            width=18,
            command=self.sil,
        ).pack(side="right")
        ModernButton(
            bot,
            text="PDF",
            bg="#e67e22",
            fg="white",
            width=8,
            command=self.pdf_aktar,
        ).pack(side="right", padx=6)
        ModernButton(
            bot,
            text="EXCEL",
            bg="#27ae60",
            fg="white",
            width=10,
            command=self.excel_aktar,
        ).pack(side="right", padx=6)
        ModernButton(
            bot,
            text="KARŞILAŞTIR",
            bg="#16a085",
            fg="white",
            width=14,
            command=self.karsilastir,
        ).pack(side="right", padx=6)
        ModernButton(
            bot,
            text="DÜZENLE",
            bg="#8e44ad",
            fg="white",
            width=12,
            command=self.duzenle,
        ).pack(side="right", padx=6)
        ModernButton(
            bot,
            text="DETAYLAR",
            bg="#2980b9",
            fg="white",
            width=12,
            command=self.detay_goster,
        ).pack(side="right", padx=6)
        ModernButton(
            bot,
            text="YENİLE",
            bg="#7f8c8d",
            fg="white",
            width=10,
            command=self.on_show,
        ).pack(side="right", padx=6)

    def _filtre_temizle(self):
        self.ent_ara.delete(0, tk.END)
        self.cmb_tur.set("Tümü")
        self._filtrele()

    def _filtrele(self):
        q = self.ent_ara.get().strip().lower()
        tur = self.cmb_tur.get()
        sonuc = []
        for kayit in self._kayitlar:
            if tur != "Tümü" and kayit["tur"] != tur:
                continue
            if q and q not in kayit["isim"].lower() and q not in str(kayit["id"]):
                continue
            sonuc.append(kayit)
        self._tabloyu_doldur(sonuc)

    def _tabloyu_doldur(self, kayitlar):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for kayit in kayitlar:
            self.tree.insert(
                "",
                "end",
                iid=str(kayit["id"]),
                values=(
                    kayit["id"],
                    kayit["tur"],
                    kayit["isim"],
                    kayit["tarih"],
                    f"{kayit['tutar']:.4f}",
                ),
            )
        self.lbl_filtre_ozet.config(
            text=f"{len(kayitlar)} / {len(self._kayitlar)} kayıt"
        )
        self.toplam_guncelle()

    def _secili_idler(self):
        ids = []
        for item in self.tree.selection():
            vals = self.tree.item(item)["values"]
            if vals:
                ids.append(int(vals[0]))
        return ids

    def on_show(self):
        self._kayitlar = []
        for recete in self.controller.db.getir_hepsi():
            fire = float(recete.get("fire_orani") or FIRE_ORANI_VARSAYILAN)
            try:
                tutar = recete_toplam(
                    recete["icerik"],
                    recete["tur"],
                    recete["parametre"],
                    self.controller.kurlar,
                    fire,
                )
            except ValidationError:
                tutar = 0.0
            self._kayitlar.append(
                {
                    "id": recete["id"],
                    "tur": recete["tur"],
                    "isim": recete["isim"],
                    "tarih": str(recete.get("tarih") or "")[:19],
                    "tutar": tutar,
                }
            )
        self._filtrele()

    def toggle_selection(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            if item in self.tree.selection():
                self.tree.selection_remove(item)
            else:
                self.tree.selection_add(item)
            self.toplam_guncelle()
            return "break"

    def toplam_guncelle(self):
        sel = self.tree.selection()
        toplam = 0.0
        for i in sel:
            vals = self.tree.item(i)["values"]
            if vals:
                toplam += float(vals[4])
        self.lbl_secim_toplam.config(
            text=f"Seçilenlerin Toplamı: {toplam:.4f} TL"
        )

    def sil(self):
        ids = self._secili_idler()
        if not ids:
            messagebox.showinfo("Bilgi", "Silmek için en az bir kayıt seçin.")
            return
        if not messagebox.askyesno(
            "Onay",
            f"{len(ids)} kayıt silinecek. Emin misiniz?",
        ):
            return
        for recete_id in ids:
            self.controller.db.sil_by_id(recete_id)
        self.on_show()

    def duzenle(self):
        ids = self._secili_idler()
        if not ids:
            messagebox.showinfo("Bilgi", "Düzenlemek için bir kayıt seçin.")
            return
        if len(ids) > 1:
            messagebox.showinfo("Bilgi", "Düzenleme için yalnızca bir kayıt seçin.")
            return
        self.controller.recete_duzenle(ids[0])

    def _aktarilacak_receteler(self):
        """Seçili varsa onları, yoksa görünür (filtrelenmiş) kayıtları döndürür."""
        ids = self._secili_idler()
        if ids:
            receteler = []
            for rid in ids:
                rec = self.controller.db.getir_by_id(rid)
                if rec:
                    receteler.append(rec)
            return receteler, "seçili"
        gorunen_idler = {int(i) for i in self.tree.get_children()}
        receteler = [
            r
            for r in self.controller.db.getir_hepsi()
            if r["id"] in gorunen_idler
        ]
        return receteler, "filtrelenmiş"

    def excel_aktar(self):
        receteler, etiket = self._aktarilacak_receteler()
        if not receteler:
            messagebox.showinfo("Bilgi", "Aktarılacak reçete yok.")
            return
        yol = filedialog.asksaveasfilename(
            title=f"{etiket.capitalize()} reçeteleri Excel'e aktar",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="recete_arsivi.xlsx",
        )
        if not yol:
            return
        try:
            excel_aktar(yol, receteler, self.controller.kurlar)
        except RuntimeError as exc:
            messagebox.showerror("Hata", str(exc))
            return
        except OSError as exc:
            messagebox.showerror("Hata", f"Dosya yazılamadı:\n{exc}")
            return
        messagebox.showinfo(
            "Başarılı",
            f"{len(receteler)} reçete Excel'e aktarıldı:\n{yol}",
        )

    def pdf_aktar(self):
        receteler, etiket = self._aktarilacak_receteler()
        if not receteler:
            messagebox.showinfo("Bilgi", "Aktarılacak reçete yok.")
            return
        yol = filedialog.asksaveasfilename(
            title=f"{etiket.capitalize()} reçeteleri PDF'e aktar",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile="recete_raporu.pdf",
        )
        if not yol:
            return
        try:
            pdf_aktar(yol, receteler, self.controller.kurlar)
        except RuntimeError as exc:
            messagebox.showerror("Hata", str(exc))
            return
        except OSError as exc:
            messagebox.showerror("Hata", f"Dosya yazılamadı:\n{exc}")
            return
        messagebox.showinfo(
            "Başarılı",
            f"{len(receteler)} reçete PDF'e aktarıldı:\n{yol}",
        )

    def karsilastir(self):
        ids = self._secili_idler()
        if len(ids) < 2:
            messagebox.showinfo(
                "Bilgi",
                "Karşılaştırma için en az 2 reçete seçin.",
            )
            return
        if len(ids) > 5:
            messagebox.showinfo(
                "Bilgi",
                "En fazla 5 reçete karşılaştırılabilir.",
            )
            return
        receteler = []
        for rid in ids:
            rec = self.controller.db.getir_by_id(rid)
            if rec:
                receteler.append(rec)
        if len(receteler) < 2:
            messagebox.showerror("Hata", "Seçilen reçeteler yüklenemedi.")
            return
        KarsilastirDialog(self, receteler, self.controller.kurlar)

    def detay_goster(self):
        ids = self._secili_idler()
        if not ids:
            messagebox.showinfo("Bilgi", "Detay için bir kayıt seçin.")
            return
        recete = self.controller.db.getir_by_id(ids[0])
        if not recete:
            messagebox.showerror("Hata", "Detay bulunamadı.")
            return
        tur = recete["tur"]
        isim = recete["isim"]
        param = recete["parametre"]
        fire = float(recete.get("fire_orani") or FIRE_ORANI_VARSAYILAN)
        icerik = recete["icerik"]
        if tur == "Kimyasal":
            p_str = f"Flotte: 1/{param}"
        elif tur == "Apre":
            p_str = f"Pick-up: %{param}"
        else:
            p_str = "Parametre Yok"
        msg = (
            f"ID: {recete['id']}\n"
            f"Reçete: {isim} ({tur})\n{p_str}\n"
            f"Fire Oranı: {fire}\n"
            f"Tarih: {recete.get('tarih') or '-'}\n\n"
            f"{'ÜRÜN ADI':<20} {'MİKTAR':<8} {'BİRİM':<8} {'FİYAT':<8}\n"
            + "------------------------------------------------------------\n"
        )
        toplam_maliyet = 0.0
        for item in icerik:
            msg += (
                f"{item['ad']:<20} {item['miktar']:<8} {item['birim']:<8} "
                f"{item['fiyat']} {item['para']}\n"
            )
            try:
                toplam_maliyet += maliyet_hesapla(
                    item, tur, param, self.controller.kurlar, fire
                )
            except ValidationError:
                pass
        msg += "------------------------------------------------------------\n"
        msg += f"BİRİM MALİYET (1 KG Kumaş): {toplam_maliyet:.4f} TL"
        messagebox.showinfo("Reçete Detayı", msg)
