import json
import os
import sqlite3
import tkinter as tk
import urllib.request
import xml.etree.ElementTree as ET
from tkinter import filedialog, messagebox, ttk
from urllib.error import URLError

DB_YOLU = os.path.join(os.path.expanduser("~"), "tekstil_maliyet_pro.db")
KUR_CACHE_YOLU = os.path.join(os.path.expanduser("~"), "tekstil_maliyet_kur_cache.json")
TCMB_URL = "https://www.tcmb.gov.tr/kurlar/today.xml"
KUR_TIMEOUT_SN = 8
# Tekstil fire / proses katsayısı (ayarlanabilir)
FIRE_ORANI = 1.2
YEDEK_KURLAR = {"TL": 1.0, "USD": 35.0, "EUR": 38.0}

RENK_SIDEBAR = "#2c3e50"
RENK_BG = "#ecf0f1"
RENK_KART = "#ffffff"
RENK_VURGU = "#e67e22"
RENK_BUTON = "#34495e"
RENK_AKTIF = "#1abc9c"
FONT_BASLIK = ("Segoe UI", 16, "bold")
FONT_NORMAL = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")


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


def maliyet_hesapla(item, tip, parametre, kurlar, fire_orani=FIRE_ORANI):
    """
    Tek maliyet formülü.
    Kimyasal g/l: miktar * fiyat_tl * flotte / 10 / 100 * fire
    Kimyasal % / Boya: miktar * fiyat_tl / 100 * fire
    Apre: miktar * fiyat_tl / 10 / 100 * pickup * fire
    """
    para = item.get("para", "TL")
    kur = kurlar.get(para, 1.0)
    fiyat_tl = float(item["fiyat"]) * kur
    miktar = float(item["miktar"])
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


def recete_toplam(icerik, tip, parametre, kurlar, fire_orani=FIRE_ORANI):
    return sum(
        maliyet_hesapla(item, tip, parametre, kurlar, fire_orani) for item in icerik
    )


def excel_aktar(dosya_yolu, receteler, kurlar, fire_orani=FIRE_ORANI):
    """Reçete listesini Excel (.xlsx) dosyasına yazar. openpyxl gerekir."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
    except ImportError as exc:
        raise RuntimeError(
            "Excel aktarımı için openpyxl gerekli. Kurulum: pip install openpyxl"
        ) from exc

    wb = Workbook()
    ws_ozet = wb.active
    ws_ozet.title = "Ozet"
    ws_ozet.append(["ID", "Tur", "Isim", "Parametre", "Tarih", "Maliyet_TL_Kg", "Satir_Sayisi"])
    for cell in ws_ozet[1]:
        cell.font = Font(bold=True)

    ws_detay = wb.create_sheet("Detay")
    ws_detay.append(
        [
            "Recete_ID",
            "Recete_Adi",
            "Tur",
            "Urun",
            "Miktar",
            "Birim",
            "Fiyat",
            "Para",
            "Satir_Maliyet_TL",
        ]
    )
    for cell in ws_detay[1]:
        cell.font = Font(bold=True)

    for recete in receteler:
        try:
            toplam = recete_toplam(
                recete["icerik"],
                recete["tur"],
                recete["parametre"],
                kurlar,
                fire_orani,
            )
        except ValidationError:
            toplam = 0.0
        ws_ozet.append(
            [
                recete["id"],
                recete["tur"],
                recete["isim"],
                recete["parametre"],
                str(recete.get("tarih") or ""),
                round(toplam, 6),
                len(recete.get("icerik") or []),
            ]
        )
        for item in recete.get("icerik") or []:
            try:
                satir_maliyet = maliyet_hesapla(
                    item,
                    recete["tur"],
                    recete["parametre"],
                    kurlar,
                    fire_orani,
                )
            except ValidationError:
                satir_maliyet = 0.0
            ws_detay.append(
                [
                    recete["id"],
                    recete["isim"],
                    recete["tur"],
                    item["ad"],
                    item["miktar"],
                    item["birim"],
                    item["fiyat"],
                    item["para"],
                    round(satir_maliyet, 6),
                ]
            )

    wb.save(dosya_yolu)
    return dosya_yolu


class Veritabani:
    def __init__(self):
        self.conn = sqlite3.connect(DB_YOLU)
        self.conn.execute("PRAGMA foreign_keys = ON")
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
                FOREIGN KEY(recete_id) REFERENCES receteler(id) ON DELETE CASCADE
            )
        """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS katalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad TEXT NOT NULL UNIQUE,
                birim TEXT DEFAULT 'g/l',
                fiyat REAL NOT NULL,
                para TEXT DEFAULT 'TL',
                aktif INTEGER DEFAULT 1,
                tarih DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        self.conn.commit()

    def _icerik_ekle(self, recete_id, icerik_listesi):
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

    def _icerik_getir(self, recete_id):
        self.cursor.execute(
            "SELECT ad, miktar, birim, fiyat, para FROM icerikler WHERE recete_id=?",
            (recete_id,),
        )
        return [
            {
                "ad": i[0],
                "miktar": i[1],
                "birim": i[2],
                "fiyat": i[3],
                "para": i[4],
            }
            for i in self.cursor.fetchall()
        ]

    def kaydet(self, tur, isim, parametre, icerik_listesi):
        self.cursor.execute(
            "INSERT INTO receteler (tur, isim, parametre) VALUES (?, ?, ?)",
            (tur, isim, parametre),
        )
        recete_id = self.cursor.lastrowid
        self._icerik_ekle(recete_id, icerik_listesi)
        self.conn.commit()
        return recete_id

    def guncelle(self, recete_id, tur, isim, parametre, icerik_listesi):
        self.cursor.execute(
            """
            UPDATE receteler
            SET tur=?, isim=?, parametre=?, tarih=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (tur, isim, parametre, recete_id),
        )
        if self.cursor.rowcount == 0:
            return False
        self.cursor.execute("DELETE FROM icerikler WHERE recete_id=?", (recete_id,))
        self._icerik_ekle(recete_id, icerik_listesi)
        self.conn.commit()
        return True

    def getir_hepsi(self):
        veriler = []
        self.cursor.execute(
            "SELECT id, tur, isim, parametre, tarih FROM receteler ORDER BY id DESC"
        )
        for r_id, r_tur, r_isim, r_param, r_tarih in self.cursor.fetchall():
            veriler.append(
                {
                    "id": r_id,
                    "tur": r_tur,
                    "isim": r_isim,
                    "parametre": r_param,
                    "tarih": r_tarih or "",
                    "icerik": self._icerik_getir(r_id),
                }
            )
        return veriler

    def getir_by_id(self, recete_id):
        self.cursor.execute(
            "SELECT id, tur, isim, parametre, tarih FROM receteler WHERE id=?",
            (recete_id,),
        )
        row = self.cursor.fetchone()
        if not row:
            return None
        r_id, r_tur, r_isim, r_param, r_tarih = row
        return {
            "id": r_id,
            "tur": r_tur,
            "isim": r_isim,
            "parametre": r_param,
            "tarih": r_tarih or "",
            "icerik": self._icerik_getir(r_id),
        }

    def son_id_by_isim(self, tur, isim):
        self.cursor.execute(
            "SELECT id FROM receteler WHERE tur=? AND isim=? ORDER BY id DESC LIMIT 1",
            (tur, isim),
        )
        row = self.cursor.fetchone()
        return row[0] if row else None

    def sil_by_id(self, recete_id):
        self.cursor.execute("DELETE FROM receteler WHERE id=?", (recete_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    # --- Kimyasal kataloğu ---

    def katalog_listele(self, sadece_aktif=True):
        if sadece_aktif:
            self.cursor.execute(
                """
                SELECT id, ad, birim, fiyat, para, aktif
                FROM katalog WHERE aktif=1 ORDER BY ad COLLATE NOCASE
                """
            )
        else:
            self.cursor.execute(
                """
                SELECT id, ad, birim, fiyat, para, aktif
                FROM katalog ORDER BY ad COLLATE NOCASE
                """
            )
        return [
            {
                "id": r[0],
                "ad": r[1],
                "birim": r[2],
                "fiyat": r[3],
                "para": r[4],
                "aktif": bool(r[5]),
            }
            for r in self.cursor.fetchall()
        ]

    def katalog_ekle(self, ad, birim, fiyat, para):
        ad = ad.strip()
        if not ad:
            raise ValidationError("Ürün adı zorunludur.")
        self.cursor.execute(
            """
            INSERT INTO katalog (ad, birim, fiyat, para, aktif)
            VALUES (?, ?, ?, ?, 1)
            """,
            (ad, birim, fiyat, para),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def katalog_guncelle(self, urun_id, ad, birim, fiyat, para, aktif=True):
        ad = ad.strip()
        if not ad:
            raise ValidationError("Ürün adı zorunludur.")
        self.cursor.execute(
            """
            UPDATE katalog
            SET ad=?, birim=?, fiyat=?, para=?, aktif=?, tarih=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (ad, birim, fiyat, para, 1 if aktif else 0, urun_id),
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    def katalog_sil(self, urun_id):
        self.cursor.execute("DELETE FROM katalog WHERE id=?", (urun_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def katalog_getir_by_ad(self, ad):
        self.cursor.execute(
            "SELECT id, ad, birim, fiyat, para, aktif FROM katalog WHERE ad=? COLLATE NOCASE",
            (ad.strip(),),
        )
        row = self.cursor.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "ad": row[1],
            "birim": row[2],
            "fiyat": row[3],
            "para": row[4],
            "aktif": bool(row[5]),
        }


class DovizServisi:
    """TCMB kurları: timeout, dosya önbelleği, kontrollü yedek."""

    @staticmethod
    def _cache_oku():
        try:
            with open(KUR_CACHE_YOLU, encoding="utf-8") as f:
                data = json.load(f)
            kurlar = data.get("kurlar") or {}
            if "TL" in kurlar and "USD" in kurlar and "EUR" in kurlar:
                return {
                    "TL": float(kurlar["TL"]),
                    "USD": float(kurlar["USD"]),
                    "EUR": float(kurlar["EUR"]),
                }
        except (OSError, ValueError, TypeError, KeyError):
            return None
        return None

    @staticmethod
    def _cache_yaz(kurlar):
        try:
            with open(KUR_CACHE_YOLU, "w", encoding="utf-8") as f:
                json.dump({"kurlar": kurlar}, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    @classmethod
    def get(cls):
        """
        Returns:
            (kurlar: dict, kaynak: str, uyari: str|None)
            kaynak: 'tcmb' | 'cache' | 'yedek'
        """
        try:
            with urllib.request.urlopen(TCMB_URL, timeout=KUR_TIMEOUT_SN) as response:
                tree = ET.parse(response)
            root = tree.getroot()
            kurlar = {"TL": 1.0}
            for currency in root.findall("Currency"):
                code = currency.get("Kod")
                if code not in ("USD", "EUR"):
                    continue
                node = currency.find("ForexSelling")
                rate = node.text if node is not None else None
                if rate:
                    kurlar[code] = float(rate.replace(",", "."))
            if "USD" not in kurlar or "EUR" not in kurlar:
                raise ValueError("TCMB yanıtında USD/EUR bulunamadı")
            cls._cache_yaz(kurlar)
            return kurlar, "tcmb", None
        except (URLError, TimeoutError, OSError, ET.ParseError, ValueError, TypeError):
            cached = cls._cache_oku()
            if cached:
                return (
                    cached,
                    "cache",
                    "TCMB'den kur alınamadı; son kayıtlı kurlar kullanılıyor.",
                )
            return (
                dict(YEDEK_KURLAR),
                "yedek",
                "TCMB ve önbellek kullanılamadı; varsayılan kurlar ile devam ediliyor.",
            )


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

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)


TIP_SAYFA = {
    "Kimyasal": "Yardımcı Kimyasal",
    "Boya": "Boya Maliyeti",
    "Apre": "Apre Maliyeti",
}


class MaliyetApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tekstil Maliyet Yönetimi")
        self.geometry("1200x800")
        self.configure(bg=RENK_BG)

        self.db = Veritabani()
        self.kurlar, self.kur_kaynak, kur_uyari = DovizServisi.get()

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
        self.create_menu_button("Kimyasal Kataloğu", KatalogPage)
        self.create_menu_button("Arşiv ve Analiz", ArsivPage)

        kur_text = f"Dolar: {self.kurlar['USD']:.4f} | Euro: {self.kurlar['EUR']:.4f}"
        if self.kur_kaynak != "tcmb":
            kur_text += " *"
        tk.Label(
            self.sidebar, text=kur_text, bg="#2980b9", fg="white", pady=10
        ).pack(side="bottom", fill="x")

        self.show_page("Yardımcı Kimyasal")

        if kur_uyari:
            self.after(200, lambda: messagebox.showwarning("Kur Uyarısı", kur_uyari))

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

    def recete_duzenle(self, recete_id):
        recete = self.db.getir_by_id(recete_id)
        if not recete:
            messagebox.showerror("Hata", "Reçete bulunamadı.")
            return
        sayfa_adi = TIP_SAYFA.get(recete["tur"])
        if not sayfa_adi:
            messagebox.showerror("Hata", f"Bilinmeyen reçete türü: {recete['tur']}")
            return
        page = self.pages[sayfa_adi]
        page.yukle_recete(recete)
        self.show_page(sayfa_adi)


class BasePage(ttk.Frame):
    def __init__(self, parent, controller, title, tip):
        super().__init__(parent, style="TFrame")
        self.controller = controller
        self.tip = tip
        self.duzenlenen_id = None

        top_panel = tk.Frame(self, bg=RENK_KART, padx=20, pady=20)
        top_panel.pack(fill="x", pady=(0, 20))

        tk.Label(
            top_panel, text=title, font=FONT_BASLIK, bg=RENK_KART, fg="#2c3e50"
        ).pack(side="top", pady=(0, 8))

        self.lbl_durum = tk.Label(
            top_panel,
            text="",
            font=FONT_NORMAL,
            bg=RENK_KART,
            fg="#e67e22",
        )
        self.lbl_durum.pack(side="top", pady=(0, 10))

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
            text="YENİ",
            bg="#7f8c8d",
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
            bg="#16a085",
            fg="white",
            width=15,
            command=self.kaydet,
        ).pack(side="left", padx=5)

    def _durum_guncelle(self):
        if self.duzenlenen_id:
            self.lbl_durum.config(
                text=f"Düzenleme modu — Kayıt ID: {self.duzenlenen_id}"
            )
        else:
            self.lbl_durum.config(text="")

    def yeni_recete(self):
        self.duzenlenen_id = None
        self.ent_isim.delete(0, tk.END)
        self.ent_sayi.delete(0, tk.END)
        if self.tip in ("Kimyasal", "Apre"):
            self.ent_param.delete(0, tk.END)
        for widget in self.mid_panel.scrollable_frame.winfo_children():
            widget.destroy()
        self.urun_satirlari.clear()
        self.lbl_tl.config(text="0.00 TL")
        self.lbl_doviz.config(text="$ 0.00 | € 0.00")
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

        self.urun_satirlari.append((e_ad, e_miktar, c_birim, e_fiyat, c_para))

    def tabloyu_olustur(self, icerik=None):
        for widget in self.mid_panel.scrollable_frame.winfo_children():
            widget.destroy()
        self.urun_satirlari.clear()

        if icerik is not None:
            sayi = max(len(icerik), 1)
            self.ent_sayi.delete(0, tk.END)
            self.ent_sayi.insert(0, str(sayi))
        else:
            try:
                sayi = int(self.ent_sayi.get().strip())
                if sayi <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    "Hata", "Ürün sayısı pozitif bir tam sayı olmalıdır."
                )
                return

        headers = ["Katalog", "Ürün Adı", "Miktar", "Birim", "Fiyat", "Para"]
        widths = [22, 22, 12, 12, 12, 8]
        for col, h in enumerate(headers):
            tk.Label(
                self.mid_panel.scrollable_frame,
                text=h,
                bg=RENK_KART,
                font=FONT_BOLD,
                fg="#95a5a6",
            ).grid(row=0, column=col, padx=5, pady=10, sticky="w")

        for i in range(sayi):
            item = icerik[i] if icerik and i < len(icerik) else None
            self._satir_ekle(i + 1, widths, item)

    def yukle_recete(self, recete):
        self.duzenlenen_id = recete["id"]
        self.ent_isim.delete(0, tk.END)
        self.ent_isim.insert(0, recete.get("isim", ""))
        if self.tip in ("Kimyasal", "Apre"):
            self.ent_param.delete(0, tk.END)
            self.ent_param.insert(0, str(recete.get("parametre", "")))
        self.tabloyu_olustur(icerik=recete.get("icerik") or [])
        self._durum_guncelle()
        self.hesapla()

    def verileri_al(self):
        """Returns (icerik, parametre). ValidationError fırlatabilir."""
        parametre = 1.0
        if self.tip in ("Kimyasal", "Apre"):
            alan = "Flotte (1/X)" if self.tip == "Kimyasal" else "Pick-up (%)"
            parametre = parse_float(self.ent_param.get(), alan)
            if parametre <= 0:
                raise ValidationError(f"{alan} sıfırdan büyük olmalıdır.")

        icerik = []
        for satir_no, (e_ad, e_mik, c_bir, e_fiy, c_par) in enumerate(
            self.urun_satirlari, start=1
        ):
            ad = e_ad.get().strip()
            if not ad:
                continue
            icerik.append(
                {
                    "ad": ad,
                    "miktar": parse_float(e_mik.get(), f"{satir_no}. satır miktar"),
                    "birim": c_bir.get(),
                    "fiyat": parse_float(e_fiy.get(), f"{satir_no}. satır fiyat"),
                    "para": c_par.get() or "TL",
                }
            )

        if not icerik:
            raise ValidationError("Hesaplamak için en az bir ürün satırı doldurun.")
        return icerik, parametre

    def hesapla(self):
        try:
            data, param = self.verileri_al()
            toplam_tl = recete_toplam(
                data, self.tip, param, self.controller.kurlar, FIRE_ORANI
            )
        except ValidationError as exc:
            messagebox.showerror("Hata", str(exc))
            return None

        usd = toplam_tl / self.controller.kurlar["USD"]
        eur = toplam_tl / self.controller.kurlar["EUR"]
        self.lbl_tl.config(text=f"{toplam_tl:.4f} TL / Kg")
        self.lbl_doviz.config(text=f"$ {usd:.4f} | € {eur:.4f}")
        return toplam_tl

    def kaydet(self):
        isim = self.ent_isim.get().strip()
        if not isim:
            messagebox.showerror("Hata", "Reçete adı zorunludur.")
            return
        tutar = self.hesapla()
        if tutar is None:
            return
        try:
            data, param = self.verileri_al()
        except ValidationError as exc:
            messagebox.showerror("Hata", str(exc))
            return

        db = self.controller.db

        if self.duzenlenen_id:
            ok = db.guncelle(self.duzenlenen_id, self.tip, isim, param, data)
            if not ok:
                messagebox.showerror("Hata", "Güncellenecek kayıt bulunamadı.")
                return
            messagebox.showinfo(
                "Başarılı", f"Reçete güncellendi (ID: {self.duzenlenen_id})."
            )
            return

        mevcut_id = db.son_id_by_isim(self.tip, isim)
        if mevcut_id:
            cevap = messagebox.askyesnocancel(
                "Aynı isimde reçete var",
                f"'{isim}' adında kayıt mevcut (ID: {mevcut_id}).\n\n"
                "Evet: Üzerine yaz\n"
                "Hayır: Yeni kayıt oluştur\n"
                "İptal: Vazgeç",
            )
            if cevap is None:
                return
            if cevap:
                db.guncelle(mevcut_id, self.tip, isim, param, data)
                self.duzenlenen_id = mevcut_id
                self._durum_guncelle()
                messagebox.showinfo(
                    "Başarılı", f"Reçete üzerine yazıldı (ID: {mevcut_id})."
                )
                return

        yeni_id = db.kaydet(self.tip, isim, param, data)
        self.duzenlenen_id = yeni_id
        self._durum_guncelle()
        messagebox.showinfo("Başarılı", f"Reçete kaydedildi (ID: {yeni_id}).")


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


class ArsivPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style="TFrame")
        self.controller = controller

        tk.Label(
            self,
            text="REÇETE ARŞİVİ",
            font=FONT_BASLIK,
            bg=RENK_BG,
            fg="#2c3e50",
        ).pack(pady=20)

        cols = ("Id", "Tur", "Isim", "Tarih", "Maliyet")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=15)
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
            text="EXCEL",
            bg="#27ae60",
            fg="white",
            width=10,
            command=self.excel_aktar,
        ).pack(side="right", padx=10)
        ModernButton(
            bot,
            text="DÜZENLE",
            bg="#8e44ad",
            fg="white",
            width=12,
            command=self.duzenle,
        ).pack(side="right", padx=10)
        ModernButton(
            bot,
            text="DETAYLAR",
            bg="#2980b9",
            fg="white",
            width=12,
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

    def _secili_idler(self):
        ids = []
        for item in self.tree.selection():
            vals = self.tree.item(item)["values"]
            if vals:
                ids.append(int(vals[0]))
        return ids

    def on_show(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for recete in self.controller.db.getir_hepsi():
            try:
                tutar = recete_toplam(
                    recete["icerik"],
                    recete["tur"],
                    recete["parametre"],
                    self.controller.kurlar,
                    FIRE_ORANI,
                )
            except ValidationError:
                tutar = 0.0
            tarih = str(recete.get("tarih") or "")[:19]
            self.tree.insert(
                "",
                "end",
                iid=str(recete["id"]),
                values=(
                    recete["id"],
                    recete["tur"],
                    recete["isim"],
                    tarih,
                    f"{tutar:.4f}",
                ),
            )
        self.toplam_guncelle()

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

    def excel_aktar(self):
        ids = self._secili_idler()
        if ids:
            receteler = []
            for rid in ids:
                rec = self.controller.db.getir_by_id(rid)
                if rec:
                    receteler.append(rec)
            etiket = "seçili"
        else:
            receteler = self.controller.db.getir_hepsi()
            etiket = "tüm"
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
            excel_aktar(yol, receteler, self.controller.kurlar, FIRE_ORANI)
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
                    item, tur, param, self.controller.kurlar, FIRE_ORANI
                )
            except ValidationError:
                pass
        msg += "------------------------------------------------------------\n"
        msg += f"BİRİM MALİYET (1 KG Kumaş): {toplam_maliyet:.4f} TL"
        messagebox.showinfo("Reçete Detayı", msg)


if __name__ == "__main__":
    try:
        app = MaliyetApp()
        app.mainloop()
    except Exception as e:
        messagebox.showerror("Kritik Hata", f"Uygulama başlatılamadı:\n{e}")
