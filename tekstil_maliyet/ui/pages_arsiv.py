"""Reçete arşiv sayfası."""
import tkinter as tk
from tkinter import filedialog, ttk

from tekstil_maliyet.constants import (
    FIRE_ORANI_VARSAYILAN,
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
from tekstil_maliyet.excel_export import excel_aktar
from tekstil_maliyet.hesaplama import guvenli_maliyet, guvenli_toplam
from tekstil_maliyet.pdf_export import pdf_aktar
from tekstil_maliyet.ui.karsilastir_dialog import KarsilastirDialog
from tekstil_maliyet.ui.widgets import (
    EmptyState,
    ModernButton,
    msg_error,
    msg_info,
    msg_yesno,
)


class DetayDialog(tk.Toplevel):
    """Reçete detayını okunabilir bir pencerede gösterir."""

    def __init__(self, parent, recete, kurlar):
        super().__init__(parent)
        self.title(f"Reçete Detayı — #{recete['id']}")
        self.configure(bg=RENK_BG)
        self.geometry("640x480")
        self.minsize(480, 360)
        self.transient(parent)
        self.grab_set()

        tur = recete["tur"]
        param = recete["parametre"]
        fire = float(recete.get("fire_orani") or FIRE_ORANI_VARSAYILAN)
        icerik = recete["icerik"] or []

        if tur == "Kimyasal":
            p_str = f"Flotte: 1/{param}"
        elif tur == "Apre":
            p_str = f"Pick-up: %{param}"
        else:
            p_str = "Parametre yok"

        header = tk.Frame(self, bg=RENK_KART, padx=16, pady=12)
        header.pack(fill="x", padx=16, pady=(16, 8))
        tk.Label(
            header,
            text=f"{recete['isim']}  ({tur})",
            font=FONT_BASLIK,
            bg=RENK_KART,
            fg=RENK_METIN,
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            header,
            text=(
                f"ID: {recete['id']}  ·  {p_str}  ·  Fire: {fire}  ·  "
                f"{recete.get('tarih') or '-'}"
            ),
            font=FONT_NORMAL,
            bg=RENK_KART,
            fg=RENK_METIN_SOLUK,
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

        cols = ("Ad", "Miktar", "Birim", "Fiyat", "Para", "Maliyet")
        tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        for c, t, w, a in (
            ("Ad", "ÜRÜN", 180, "w"),
            ("Miktar", "MİKTAR", 70, "e"),
            ("Birim", "BİRİM", 90, "center"),
            ("Fiyat", "FİYAT", 80, "e"),
            ("Para", "PARA", 60, "center"),
            ("Maliyet", "TL", 90, "e"),
        ):
            tree.heading(c, text=t)
            tree.column(c, width=w, anchor=a)
        tree.pack(fill="both", expand=True, padx=16, pady=8)

        toplam = 0.0
        hata_var = False
        for item in icerik:
            maliyet, err = guvenli_maliyet(item, tur, param, kurlar, fire)
            if err:
                hata_var = True
                maliyet_str = "HATA"
            else:
                toplam += maliyet
                maliyet_str = f"{maliyet:.4f}"
            tree.insert(
                "",
                "end",
                values=(
                    item.get("ad", ""),
                    item.get("miktar", ""),
                    item.get("birim", ""),
                    item.get("fiyat", ""),
                    item.get("para", ""),
                    maliyet_str,
                ),
            )

        footer = tk.Frame(self, bg=RENK_BG, padx=16, pady=12)
        footer.pack(fill="x")
        if hata_var:
            tk.Label(
                footer,
                text="Bazı satırlar hesaplanamadı (HATA).",
                font=FONT_NORMAL,
                bg=RENK_BG,
                fg=RENK_TEHLIKE,
            ).pack(side="left", padx=(0, 12))
            toplam_text = "Birim maliyet: —"
            toplam_fg = RENK_TEHLIKE
        else:
            toplam_text = f"Birim maliyet (1 kg kumaş): {toplam:.4f} TL"
            toplam_fg = RENK_BASARI
        tk.Label(
            footer,
            text=toplam_text,
            font=("Segoe UI", 12, "bold"),
            bg=RENK_BG,
            fg=toplam_fg,
        ).pack(side="left")
        ModernButton(
            footer,
            text="Kapat",
            bg=RENK_IKINCIL,
            fg="white",
            width=10,
            command=self.destroy,
        ).pack(side="right")


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
            fg=RENK_METIN,
        ).pack(pady=(20, 10))

        filtre = tk.Frame(self, bg=RENK_KART, padx=12, pady=10)
        filtre.pack(fill="x", padx=40, pady=(0, 8))

        tk.Label(
            filtre, text="Ara", bg=RENK_KART, font=FONT_BOLD, fg=RENK_METIN_SOLUK
        ).pack(side="left", padx=(0, 6))
        self.ent_ara = ttk.Entry(filtre, width=28, font=FONT_NORMAL)
        self.ent_ara.pack(side="left", padx=(0, 16))
        self.ent_ara.bind("<KeyRelease>", lambda e: self._filtrele())

        tk.Label(
            filtre, text="Tür", bg=RENK_KART, font=FONT_BOLD, fg=RENK_METIN_SOLUK
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
            bg=RENK_IKINCIL,
            fg="white",
            width=10,
            command=self._filtre_temizle,
        ).pack(side="left")

        self.lbl_filtre_ozet = tk.Label(
            filtre, text="", bg=RENK_KART, fg=RENK_METIN_SOLUK, font=FONT_NORMAL
        )
        self.lbl_filtre_ozet.pack(side="right")

        self.liste_alani = tk.Frame(self, bg=RENK_BG)
        self.liste_alani.pack(fill="both", expand=True, padx=40, pady=10)

        cols = ("Id", "Tur", "Isim", "Tarih", "Maliyet")
        self.tree = ttk.Treeview(
            self.liste_alani, columns=cols, show="headings", height=14
        )
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
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Button-1>", self.toggle_selection)
        self.tree.bind("<Double-1>", self._cift_tik)

        self.bos_durum = EmptyState(
            self.liste_alani,
            baslik="Henüz reçete yok",
            aciklama="Hesaplama sayfalarından reçete kaydedince burada listelenir.",
            aksiyon_metni="Yardımcı Kimyasal'a git",
            aksiyon=lambda: self.controller.show_page("Yardımcı Kimyasal"),
        )

        bot = tk.Frame(self, bg=RENK_BG)
        bot.pack(fill="x", padx=40, pady=20)

        sol = tk.Frame(bot, bg=RENK_BG)
        sol.pack(side="left")
        self.lbl_secim = tk.Label(
            sol,
            text="Seçili: 0",
            font=FONT_BOLD,
            bg=RENK_BG,
            fg=RENK_METIN,
        )
        self.lbl_secim.pack(anchor="w")
        self.lbl_secim_toplam = tk.Label(
            sol,
            text="Toplam: 0.00 TL",
            font=("Segoe UI", 12),
            bg=RENK_BG,
            fg=RENK_BASARI,
        )
        self.lbl_secim_toplam.pack(anchor="w")

        sag = tk.Frame(bot, bg=RENK_BG)
        sag.pack(side="right")

        ModernButton(
            sag,
            text="YENİLE",
            bg=RENK_IKINCIL,
            fg="white",
            width=10,
            command=self.on_show,
        ).pack(side="left", padx=4)
        ModernButton(
            sag,
            text="DETAYLAR",
            bg="#2980b9",
            fg="white",
            width=12,
            command=self.detay_goster,
        ).pack(side="left", padx=4)
        ModernButton(
            sag,
            text="DÜZENLE",
            bg=RENK_VURGU,
            fg="white",
            width=12,
            command=self.duzenle,
        ).pack(side="left", padx=4)
        ModernButton(
            sag,
            text="KARŞILAŞTIR",
            bg=RENK_BASARI,
            fg="white",
            width=14,
            command=self.karsilastir,
        ).pack(side="left", padx=4)

        self.mb_aktar = tk.Menubutton(
            sag,
            text="DIŞA AKTAR ▾",
            bg="#27ae60",
            fg="white",
            font=("Segoe UI", 11),
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=8,
            direction="above",
        )
        self.mb_aktar.pack(side="left", padx=4)
        aktar_menu = tk.Menu(self.mb_aktar, tearoff=0)
        aktar_menu.add_command(label="Excel (.xlsx)", command=self.excel_aktar)
        aktar_menu.add_command(label="PDF", command=self.pdf_aktar)
        self.mb_aktar.config(menu=aktar_menu)

        ModernButton(
            sag,
            text="SİL",
            bg=RENK_TEHLIKE,
            fg="white",
            width=8,
            command=self.sil,
        ).pack(side="left", padx=(12, 0))

    def _toast(self, msg, kind="ok"):
        if hasattr(self.controller, "toast"):
            self.controller.toast.show(msg, kind=kind)

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

    def _bos_goster(self, mod):
        """mod: None=liste, 'bos'=hiç kayıt, 'filtre'=eşre sonucu yok."""
        if mod is None:
            self.bos_durum.pack_forget()
            self.tree.pack(fill="both", expand=True)
            return
        self.tree.pack_forget()
        if mod == "bos":
            self.bos_durum.guncelle(
                "Henüz reçete yok",
                "Hesaplama sayfalarından reçete kaydedince burada listelenir.",
                "Yardımcı Kimyasal'a git",
                lambda: self.controller.show_page("Yardımcı Kimyasal"),
            )
        else:
            self.bos_durum.guncelle(
                "Sonuç bulunamadı",
                "Arama / tür filtresine uyan reçete yok. Filtreyi temizleyin.",
                "Filtreyi temizle",
                self._filtre_temizle,
            )
        self.bos_durum.pack(fill="both", expand=True)

    def _tabloyu_doldur(self, kayitlar):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for kayit in kayitlar:
            if kayit.get("hata"):
                maliyet_str = "HATA"
            else:
                maliyet_str = f"{kayit['tutar']:.4f}"
            self.tree.insert(
                "",
                "end",
                iid=str(kayit["id"]),
                values=(
                    kayit["id"],
                    kayit["tur"],
                    kayit["isim"],
                    kayit["tarih"],
                    maliyet_str,
                ),
            )
        self.lbl_filtre_ozet.config(
            text=f"{len(kayitlar)} / {len(self._kayitlar)} kayıt"
        )
        if len(self._kayitlar) == 0:
            self._bos_goster("bos")
        elif len(kayitlar) == 0:
            self._bos_goster("filtre")
        else:
            self._bos_goster(None)
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
            tutar, hata = guvenli_toplam(
                recete["icerik"],
                recete["tur"],
                recete["parametre"],
                self.controller.kurlar,
                fire,
            )
            self._kayitlar.append(
                {
                    "id": recete["id"],
                    "tur": recete["tur"],
                    "isim": recete["isim"],
                    "tarih": str(recete.get("tarih") or "")[:19],
                    "tutar": 0.0 if hata else tutar,
                    "hata": hata,
                }
            )
        self._filtrele()

    def kurlar_degisti(self):
        self.on_show()

    def toggle_selection(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            if item in self.tree.selection():
                self.tree.selection_remove(item)
            else:
                self.tree.selection_add(item)
            self.toplam_guncelle()
            return "break"

    def _cift_tik(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        # Toggle çift tıkta seçimi kaldırmış olabilir; zorla seç.
        self.tree.selection_set(item)
        self.toplam_guncelle()
        self.duzenle()

    def toplam_guncelle(self):
        sel = self.tree.selection()
        toplam = 0.0
        hata_say = 0
        for i in sel:
            vals = self.tree.item(i)["values"]
            if not vals:
                continue
            if str(vals[4]).upper() == "HATA":
                hata_say += 1
            else:
                try:
                    toplam += float(vals[4])
                except (TypeError, ValueError):
                    hata_say += 1
        n = len(sel)
        self.lbl_secim.config(text=f"Seçili: {n}")
        if hata_say:
            self.lbl_secim_toplam.config(
                text=f"Toplam: {toplam:.4f} TL  ({hata_say} hatalı)",
                fg=RENK_TEHLIKE,
            )
        else:
            self.lbl_secim_toplam.config(
                text=f"Toplam: {toplam:.4f} TL",
                fg=RENK_BASARI,
            )

    def sil(self):
        ids = self._secili_idler()
        if not ids:
            msg_info(self, "Bilgi", "Silmek için en az bir kayıt seçin.")
            return
        if not msg_yesno(
            self,
            "Onay",
            f"{len(ids)} kayıt silinecek. Emin misiniz?",
        ):
            return
        for recete_id in ids:
            self.controller.db.sil_by_id(recete_id)
        self.on_show()
        self._toast(f"{len(ids)} kayıt silindi", kind="info")

    def duzenle(self):
        ids = self._secili_idler()
        if not ids:
            msg_info(self, "Bilgi", "Düzenlemek için bir kayıt seçin.")
            return
        if len(ids) > 1:
            msg_info(self, "Bilgi", "Düzenleme için yalnızca bir kayıt seçin.")
            return
        self.controller.recete_duzenle(ids[0])

    def _aktarilacak_receteler(self):
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

    def _aktar_onay(self, etiket, adet):
        if etiket == "filtrelenmiş":
            return msg_yesno(
                self,
                "Dışa aktar",
                f"Seçim yok; görünür {adet} reçete aktarılacak. Devam edilsin mi?",
            )
        return True

    def excel_aktar(self):
        receteler, etiket = self._aktarilacak_receteler()
        if not receteler:
            msg_info(self, "Bilgi", "Aktarılacak reçete yok.")
            return
        if not self._aktar_onay(etiket, len(receteler)):
            return
        yol = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
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
            msg_error(self, "Hata", str(exc))
            return
        except OSError as exc:
            msg_error(self, "Hata", f"Dosya yazılamadı:\n{exc}")
            return
        self._toast(f"{len(receteler)} reçete Excel'e aktarıldı")

    def pdf_aktar(self):
        receteler, etiket = self._aktarilacak_receteler()
        if not receteler:
            msg_info(self, "Bilgi", "Aktarılacak reçete yok.")
            return
        if not self._aktar_onay(etiket, len(receteler)):
            return
        yol = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
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
            msg_error(self, "Hata", str(exc))
            return
        except OSError as exc:
            msg_error(self, "Hata", f"Dosya yazılamadı:\n{exc}")
            return
        self._toast(f"{len(receteler)} reçete PDF'e aktarıldı")

    def karsilastir(self):
        ids = self._secili_idler()
        if len(ids) < 2:
            msg_info(self, "Bilgi", "Karşılaştırma için en az 2 reçete seçin.")
            return
        if len(ids) > 5:
            msg_info(self, "Bilgi", "En fazla 5 reçete karşılaştırılabilir.")
            return
        receteler = []
        for rid in ids:
            rec = self.controller.db.getir_by_id(rid)
            if rec:
                receteler.append(rec)
        if len(receteler) < 2:
            msg_error(self, "Hata", "Seçilen reçeteler yüklenemedi.")
            return
        turler = {r["tur"] for r in receteler}
        if len(turler) > 1:
            if not msg_yesno(
                self,
                "Farklı türler",
                "Seçilen reçeteler farklı işlem türlerinde "
                f"({', '.join(sorted(turler))}).\n"
                "Karşılaştırma yine de yapılsın mı?",
            ):
                return
        KarsilastirDialog(self, receteler, self.controller.kurlar)

    def detay_goster(self):
        ids = self._secili_idler()
        if not ids:
            msg_info(self, "Bilgi", "Detay için bir kayıt seçin.")
            return
        if len(ids) > 1:
            msg_info(self, "Bilgi", "Detay için yalnızca bir kayıt seçin.")
            return
        recete = self.controller.db.getir_by_id(ids[0])
        if not recete:
            msg_error(self, "Hata", "Detay bulunamadı.")
            return
        DetayDialog(self, recete, self.controller.kurlar)
