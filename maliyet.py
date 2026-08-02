import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request
import xml.etree.ElementTree as ET
import sqlite3
import os

DB_YOLU = os.path.join(os.path.expanduser("~"), "tekstil_maliyet_pro.db")

RENK_SIDEBAR = "#2c3e50"
RENK_BG = "#ecf0f1"
RENK_KART = "#ffffff"
RENK_VURGU = "#e67e22"
RENK_BUTON = "#34495e"
RENK_AKTIF = "#1abc9c"
FONT_BASLIK = ("Segoe UI", 16, "bold")
FONT_NORMAL = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")


class Veritabani:
    def __init__(self):
        self.conn = sqlite3.connect(DB_YOLU)
        self.cursor = self.conn.cursor()
        self.tablo_olustur()

    def tablo_olustur(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS receteler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tur TEXT,
                isim TEXT,
                parametre REAL,
                tarih DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS icerikler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recete_id INTEGER,
                ad TEXT,
                miktar REAL,
                birim TEXT,
                fiyat REAL,
                para TEXT,
                FOREIGN KEY(recete_id) REFERENCES receteler(id)
            )
        """
        )
        self.conn.commit()

    def kaydet(self, tur, isim, parametre, icerik_listesi):
        self.cursor.execute(
            "INSERT INTO receteler (tur, isim, parametre) VALUES (?, ?, ?)",
            (tur, isim, parametre),
        )
        recete_id = self.cursor.lastrowid
        for item in icerik_listesi:
            self.cursor.execute(
                """
                INSERT INTO icerikler (recete_id, ad, miktar, birim, fiyat, para) 
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    recete_id,
                    item["ad"],
                    item["miktar"],
                    item["birim"],
                    item["fiyat"],
                    item["para"],
                ),
            )
        self.conn.commit()

    def getir_hepsi(self):
        veriler = []
        self.cursor.execute(
            "SELECT id, tur, isim, parametre FROM receteler ORDER BY id DESC"
        )
        receteler = self.cursor.fetchall()
        for r in receteler:
            r_id, r_tur, r_isim, r_param = r
            self.cursor.execute(
                "SELECT ad, miktar, birim, fiyat, para FROM icerikler WHERE recete_id=?",
                (r_id,),
            )
            items = []
            for i in self.cursor.fetchall():
                items.append(
                    {
                        "ad": i[0],
                        "miktar": i[1],
                        "birim": i[2],
                        "fiyat": i[3],
                        "para": i[4],
                    }
                )
            veriler.append(
                {
                    "id": r_id,
                    "tur": r_tur,
                    "isim": r_isim,
                    "parametre": r_param,
                    "icerik": items,
                }
            )
        return veriler

    def sil_grup(self, tur, isim):
        self.cursor.execute(
            "SELECT id FROM receteler WHERE tur=? AND isim=?", (tur, isim)
        )
        ids = self.cursor.fetchall()
        for (r_id,) in ids:
            self.cursor.execute("DELETE FROM icerikler WHERE recete_id=?", (r_id,))
            self.cursor.execute("DELETE FROM receteler WHERE id=?", (r_id,))
        self.conn.commit()

    def getir_detay_grup(self, tur, isim):
        self.cursor.execute(
            "SELECT id, parametre FROM receteler WHERE tur=? AND isim=? ORDER BY id DESC LIMIT 1",
            (tur, isim),
        )
        row = self.cursor.fetchone()
        if not row:
            return None
        recete_id, parametre = row
        self.cursor.execute(
            "SELECT ad, miktar, birim, fiyat, para FROM icerikler WHERE recete_id=?",
            (recete_id,),
        )
        items = []
        for i in self.cursor.fetchall():
            items.append(
                {
                    "ad": i[0],
                    "miktar": i[1],
                    "birim": i[2],
                    "fiyat": i[3],
                    "para": i[4],
                }
            )
        return {"parametre": parametre, "icerik": items}


def hesapla_formul(miktar, fiyat, para_birimi, islem_turu, parametre, kurlar):
    try:
        kur = kurlar.get(para_birimi, 1.0)
        fiyat_tl = fiyat * kur
        if islem_turu == "Apre":
            return miktar * fiyat_tl / 10.0 / 100.0 * parametre * 1.2
        if islem_turu == "Boya":
            return miktar * fiyat_tl / 100.0 * 1.2
        return 0.0
    except Exception:
        return 0.0


class DovizServisi:
    @staticmethod
    def get():
        try:
            url = "https://www.tcmb.gov.tr/kurlar/today.xml"
            response = urllib.request.urlopen(url)
            tree = ET.parse(response)
            root = tree.getroot()
            kurlar = {"TL": 1.0}
            for currency in root.findall("Currency"):
                code = currency.get("Kod")
                if code not in ("USD", "EUR"):
                    continue
                rate = currency.find("ForexSelling").text
                if rate:
                    kurlar[code] = float(rate.replace(",", "."))
            return kurlar
        except Exception:
            return {"TL": 1.0, "USD": 35.0, "EUR": 38.0}


class ModernButton(tk.Button):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(font=("Segoe UI", 11), relief="flat", cursor="hand2", pady=8)


class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self, bg=RENK_KART, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas, style="Card.TFrame")
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


class MaliyetApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tekstil Maliyet Yönetimi")
        self.geometry("1200x800")
        self.configure(bg=RENK_BG)

        self.db = Veritabani()
        self.kurlar = DovizServisi.get()

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TFrame", background=RENK_BG)
        self.style.configure("Card.TFrame", background=RENK_KART)
        self.style.configure("Sidebar.TFrame", background=RENK_SIDEBAR)
        self.style.configure(
            "Header.TLabel",
            background=RENK_BG,
            font=FONT_BASLIK,
            foreground="#34495e",
        )

        self.sidebar = ttk.Frame(self, width=250, style="Sidebar.TFrame")
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        lbl_logo = tk.Label(
            self.sidebar,
            text="MALİYET\nSİSTEMİ",
            bg=RENK_SIDEBAR,
            fg="white",
            font=("Segoe UI", 20, "bold"),
            pady=30,
        )
        lbl_logo.pack(fill="x")

        self.main_area = ttk.Frame(self, style="TFrame")
        self.main_area.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        self.pages = {}
        self.create_menu_button("Yardımcı Kimyasal", YardimciKimyasalPage)
        self.create_menu_button("Boya Maliyeti", BoyaMaliyetiPage)
        self.create_menu_button("Apre Maliyeti", ApreMaliyetiPage)
        self.create_menu_button("Arşiv ve Analiz", ArsivPage)

        kur_text = f"Dolar: {self.kurlar['USD']} | Euro: {self.kurlar['EUR']}"
        tk.Label(
            self.sidebar, text=kur_text, bg="#2980b9", fg="white", pady=10
        ).pack(side="bottom", fill="x")

        self.show_page("Yardımcı Kimyasal")

    def create_menu_button(self, text, page_class):
        btn = tk.Button(
            self.sidebar,
            text=text,
            bg=RENK_SIDEBAR,
            fg="white",
            font=("Segoe UI", 11),
            relief="flat",
            anchor="w",
            padx=20,
            pady=12,
            activebackground=RENK_AKTIF,
            activeforeground="white",
            cursor="hand2",
            command=lambda: self.show_page(text),
        )
        btn.pack(fill="x", pady=2)
        page = page_class(parent=self.main_area, controller=self)
        self.pages[text] = page
        page.grid(row=0, column=0, sticky="nsew")

    def show_page(self, page_name):
        frame = self.pages[page_name]
        if hasattr(frame, "on_show"):
            frame.on_show()
        frame.tkraise()


class BasePage(ttk.Frame):
    def __init__(self, parent, controller, title, tip):
        super().__init__(parent, style="TFrame")
        self.controller = controller
        self.tip = tip

        top_panel = tk.Frame(self, bg=RENK_KART, padx=20, pady=20)
        top_panel.pack(fill="x", pady=(0, 20))

        tk.Label(
            top_panel, text=title, font=FONT_BASLIK, bg=RENK_KART, fg="#2c3e50"
        ).pack(side="top", pady=(0, 15))

        grid_frame = tk.Frame(top_panel, bg=RENK_KART)
        grid_frame.pack()

        tk.Label(
            grid_frame,
            text="Reçete Adı",
            bg=RENK_KART,
            font=FONT_BOLD,
            fg="#7f8c8d",
        ).grid(row=0, column=0, padx=10, sticky="w")
        self.ent_isim = ttk.Entry(grid_frame, width=25, font=FONT_NORMAL)
        self.ent_isim.grid(row=1, column=0, padx=10, pady=5)

        tk.Label(
            grid_frame,
            text="Ürün Sayısı",
            bg=RENK_KART,
            font=FONT_BOLD,
            fg="#7f8c8d",
        ).grid(row=0, column=1, padx=10, sticky="w")
        self.ent_sayi = ttk.Entry(grid_frame, width=15, font=FONT_NORMAL)
        self.ent_sayi.grid(row=1, column=1, padx=10, pady=5)

        self.lbl_param = tk.Label(
            grid_frame,
            text="Parametre",
            bg=RENK_KART,
            font=FONT_BOLD,
            fg="#7f8c8d",
        )
        self.ent_param = ttk.Entry(grid_frame, width=15, font=FONT_NORMAL)

        if tip == "Kimyasal":
            self.lbl_param.config(text="Flotte (1/X)")
            self.lbl_param.grid(row=0, column=2, padx=10, sticky="w")
            self.ent_param.grid(row=1, column=2, padx=10, pady=5)
            btn_col = 3
        elif tip == "Apre":
            self.lbl_param.config(text="Pick-up (%)")
            self.lbl_param.grid(row=0, column=2, padx=10, sticky="w")
            self.ent_param.grid(row=1, column=2, padx=10, pady=5)
            btn_col = 3
        else:
            btn_col = 2

        ModernButton(
            grid_frame,
            text="Listeyi Oluştur",
            bg="#27ae60",
            fg="white",
            width=15,
            command=self.tabloyu_olustur,
        ).grid(row=1, column=btn_col, padx=20, sticky="e")

        self.mid_panel = ScrollableFrame(self)
        self.mid_panel.pack(fill="both", expand=True)
        self.urun_satirlari = []

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
            text="HESAPLA",
            bg=RENK_VURGU,
            fg="white",
            width=15,
            command=self.hesapla,
        ).pack(side="left", padx=5)
        ModernButton(
            act_frame,
            text="KAYDET",
            bg="#16a085",
            fg="white",
            width=15,
            command=self.kaydet,
        ).pack(side="left", padx=5)

    def float_yap(self, val):
        try:
            return float(val.replace(",", "."))
        except Exception:
            return 0.0

    def tabloyu_olustur(self):
        for widget in self.mid_panel.scrollable_frame.winfo_children():
            widget.destroy()
        self.urun_satirlari.clear()
        try:
            sayi = int(self.ent_sayi.get())
        except Exception:
            return

        headers = ["Ürün Adı", "Miktar", "Birim", "Fiyat", "Para Birimi"]
        widths = [30, 15, 15, 15, 10]
        for col, h in enumerate(headers):
            tk.Label(
                self.mid_panel.scrollable_frame,
                text=h,
                bg=RENK_KART,
                font=FONT_BOLD,
                fg="#95a5a6",
            ).grid(row=0, column=col, padx=5, pady=10, sticky="w")

        for i in range(sayi):
            row = i + 1
            e_ad = ttk.Entry(self.mid_panel.scrollable_frame, width=widths[0])
            e_ad.grid(row=row, column=0, padx=5, pady=5)
            e_miktar = ttk.Entry(self.mid_panel.scrollable_frame, width=widths[1])
            e_miktar.grid(row=row, column=1, padx=5, pady=5)

            if self.tip == "Kimyasal":
                c_birim = ttk.Combobox(
                    self.mid_panel.scrollable_frame,
                    values=["g/l", "%"],
                    width=widths[2],
                    state="readonly",
                )
                c_birim.current(0)
            elif self.tip == "Apre":
                c_birim = ttk.Combobox(
                    self.mid_panel.scrollable_frame,
                    values=["g/l (Apre)"],
                    width=widths[2],
                    state="disabled",
                )
                c_birim.set("g/l (Apre)")
            else:
                c_birim = ttk.Combobox(
                    self.mid_panel.scrollable_frame,
                    values=["% (Boya)"],
                    width=widths[2],
                    state="disabled",
                )
                c_birim.set("% (Boya)")
            c_birim.grid(row=row, column=2, padx=5, pady=5)

            e_fiyat = ttk.Entry(self.mid_panel.scrollable_frame, width=widths[3])
            e_fiyat.grid(row=row, column=3, padx=5, pady=5)

            c_para = ttk.Combobox(
                self.mid_panel.scrollable_frame,
                values=["TL", "USD", "EUR"],
                width=widths[4],
                state="readonly",
            )
            c_para.current(0)
            c_para.grid(row=row, column=4, padx=5, pady=5)

            self.urun_satirlari.append((e_ad, e_miktar, c_birim, e_fiyat, c_para))

    def verileri_al(self):
        icerik = []
        parametre = 1.0
        if self.tip in ("Kimyasal", "Apre"):
            parametre = self.float_yap(self.ent_param.get())
            if parametre <= 0:
                return (None, "Parametre hatası")
        for e_ad, e_mik, c_bir, e_fiy, c_par in self.urun_satirlari:
            ad = e_ad.get()
            if not ad:
                continue
            icerik.append(
                {
                    "ad": ad,
                    "miktar": self.float_yap(e_mik.get()),
                    "birim": c_bir.get(),
                    "fiyat": self.float_yap(e_fiy.get()),
                    "para": c_par.get(),
                }
            )
        return (icerik, parametre)

    def hesapla(self):
        data, param = self.verileri_al()
        if data is None:
            messagebox.showerror(
                "Hata", "Lütfen tüm sayısal alanları kontrol ediniz."
            )
            return None

        toplam_tl = 0.0
        for item in data:
            fiyat_tl = item["fiyat"] * self.controller.kurlar.get(item["para"], 1.0)
            if self.tip == "Kimyasal":
                if item["birim"] == "g/l":
                    val = item["miktar"] * fiyat_tl / (10 / param) / 100 * 1.2
                else:
                    val = item["miktar"] * fiyat_tl / 100 * 1.2
            else:
                val = hesapla_formul(
                    item["miktar"],
                    item["fiyat"],
                    item["para"],
                    self.tip,
                    param,
                    self.controller.kurlar,
                )
            toplam_tl += val

        usd = toplam_tl / self.controller.kurlar["USD"]
        eur = toplam_tl / self.controller.kurlar["EUR"]
        self.lbl_tl.config(text=f"{toplam_tl:.4f} TL / Kg")
        self.lbl_doviz.config(text=f"$ {usd:.4f} | € {eur:.4f}")
        return toplam_tl

    def kaydet(self):
        tutar = self.hesapla()
        isim = self.ent_isim.get()
        data, param = self.verileri_al()
        if tutar is not None and isim and data:
            self.controller.db.kaydet(self.tip, isim, param, data)
            messagebox.showinfo("Başarılı", "Reçete veritabanına kaydedildi.")


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


class ArsivPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style="TFrame")
        self.controller = controller

        tk.Label(
            self,
            text="REÇETE ARŞİVİ VE ANALİZ",
            font=FONT_BASLIK,
            bg=RENK_BG,
            fg="#2c3e50",
        ).pack(pady=20)

        cols = ("Tur", "Isim", "Adet", "ToplamMaliyet")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=15)
        self.tree.heading("Tur", text="TÜR")
        self.tree.heading("Isim", text="REÇETE ADI")
        self.tree.heading("Adet", text="KAYIT SAYISI")
        self.tree.heading("ToplamMaliyet", text="TOPLAM (TL)")
        self.tree.column("Tur", anchor="center", width=150)
        self.tree.column("Isim", width=300)
        self.tree.column("Adet", anchor="center", width=100)
        self.tree.column("ToplamMaliyet", anchor="e", width=200)
        self.tree.pack(fill="both", expand=True, padx=40, pady=10)
        self.tree.bind("<Button-1>", self.toggle_selection)

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
            text="SEÇİLEN GRUPLARI SİL",
            bg="#c0392b",
            fg="white",
            width=20,
            command=self.sil,
        ).pack(side="right")
        ModernButton(
            bot,
            text="DETAYLAR",
            bg="#2980b9",
            fg="white",
            width=15,
            command=self.detay_goster,
        ).pack(side="right", padx=10)
        ModernButton(
            bot,
            text="YENİLE",
            bg="#7f8c8d",
            fg="white",
            width=10,
            command=self.on_show,
        ).pack(side="right", padx=10)

    def on_show(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        raw_data = self.controller.db.getir_hepsi()
        grouped = {}
        for recete in raw_data:
            recete_toplam = 0.0
            param = recete["parametre"]
            for item in recete["icerik"]:
                fiyat_tl = item["fiyat"] * self.controller.kurlar.get(
                    item["para"], 1.0
                )
                if recete["tur"] == "Kimyasal":
                    if item["birim"] == "g/l":
                        val = item["miktar"] * fiyat_tl / (10 / param) / 100 * 1.2
                    else:
                        val = item["miktar"] * fiyat_tl / 100 * 1.2
                else:
                    val = hesapla_formul(
                        item["miktar"],
                        item["fiyat"],
                        item["para"],
                        recete["tur"],
                        param,
                        self.controller.kurlar,
                    )
                recete_toplam += val
            key = (recete["tur"], recete["isim"])
            if key not in grouped:
                grouped[key] = {"adet": 0, "tutar": 0.0}
            grouped[key]["adet"] += 1
            grouped[key]["tutar"] += recete_toplam
        for (tur, isim), val in grouped.items():
            self.tree.insert(
                "",
                "end",
                values=(tur, isim, val["adet"], f"{val['tutar']:.4f}"),
            )

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
        toplam = sum(float(self.tree.item(i)["values"][3]) for i in sel)
        self.lbl_secim_toplam.config(
            text=f"Seçilenlerin Toplamı: {toplam:.4f} TL"
        )

    def sil(self):
        sel = self.tree.selection()
        if not sel:
            return
        if not messagebox.askyesno(
            "Onay",
            "Seçili reçete gruplarını silmek istediğinize emin misiniz?",
        ):
            return
        for item in sel:
            vals = self.tree.item(item)["values"]
            self.controller.db.sil_grup(vals[0], vals[1])
        self.on_show()
        self.toplam_guncelle()

    def detay_goster(self):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])["values"]
        tur, isim = vals[0], vals[1]
        detay_data = self.controller.db.getir_detay_grup(tur, isim)
        if not detay_data:
            messagebox.showerror("Hata", "Detay bulunamadı.")
            return
        param = detay_data["parametre"]
        icerik = detay_data["icerik"]
        if tur == "Kimyasal":
            p_str = f"Flotte: 1/{param}"
        elif tur == "Apre":
            p_str = f"Pick-up: %{param}"
        else:
            p_str = "Parametre Yok"
        msg = (
            f"Reçete: {isim} ({tur})\n{p_str}\n\n"
            f"{'ÜRÜN ADI':<20} {'MİKTAR':<8} {'BİRİM':<8} {'FİYAT':<8}\n"
            + "------------------------------------------------------------\n"
        )
        toplam_maliyet = 0.0
        for item in icerik:
            msg += (
                f"{item['ad']:<20} {item['miktar']:<8} {item['birim']:<8} "
                f"{item['fiyat']} {item['para']}\n"
            )
            fiyat_tl = item["fiyat"] * self.controller.kurlar.get(item["para"], 1.0)
            if tur == "Kimyasal":
                if item["birim"] == "g/l":
                    val = item["miktar"] * fiyat_tl / (10 / param) / 100 * 1.2
                else:
                    val = item["miktar"] * fiyat_tl / 100 * 1.2
            else:
                val = hesapla_formul(
                    item["miktar"],
                    item["fiyat"],
                    item["para"],
                    tur,
                    param,
                    self.controller.kurlar,
                )
            toplam_maliyet += val
        msg += "------------------------------------------------------------\n"
        msg += f"BİRİM MALİYET (1 KG Kumaş): {toplam_maliyet:.4f} TL"
        messagebox.showinfo("Reçete Detayı", msg)


if __name__ == "__main__":
    try:
        app = MaliyetApp()
        app.mainloop()
    except Exception as e:
        messagebox.showerror("Kritik Hata", f"Uygulama başlatılamadı:\n{e}")
