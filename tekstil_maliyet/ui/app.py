"""Ana uygulama penceresi."""
import tkinter as tk
from tkinter import ttk

from tekstil_maliyet.constants import (
    FONT_BASLIK,
    FONT_NORMAL,
    RENK_AKTIF,
    RENK_BG,
    RENK_KART,
    RENK_SIDEBAR,
    TIP_SAYFA,
)
from tekstil_maliyet.db import Veritabani
from tekstil_maliyet.doviz import DovizServisi
from tekstil_maliyet.ui.pages_arsiv import ArsivPage
from tekstil_maliyet.ui.pages_base import (
    ApreMaliyetiPage,
    BoyaMaliyetiPage,
    YardimciKimyasalPage,
)
from tekstil_maliyet.ui.pages_katalog import KatalogPage
from tekstil_maliyet.ui.widgets import ToastBar, msg_error, msg_warning


class MaliyetApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tekstil Maliyet Yönetimi")
        self.geometry("1200x800")
        self.minsize(960, 640)
        self.configure(bg=RENK_BG)

        self.db = Veritabani()
        self.kurlar, self.kur_kaynak, kur_uyari = DovizServisi.get()
        self._menu_buttons = {}
        self._aktif_sayfa = None

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

        content = ttk.Frame(self, style="TFrame")
        content.pack(side="right", fill="both", expand=True)

        self.toast = ToastBar(content)

        self.main_area = ttk.Frame(content, style="TFrame")
        self.main_area.pack(fill="both", expand=True, padx=20, pady=20)
        self.main_area.rowconfigure(0, weight=1)
        self.main_area.columnconfigure(0, weight=1)

        self.pages = {}
        self.create_menu_button("Yardımcı Kimyasal", YardimciKimyasalPage)
        self.create_menu_button("Boya Maliyeti", BoyaMaliyetiPage)
        self.create_menu_button("Apre Maliyeti", ApreMaliyetiPage)
        self.create_menu_button("Kimyasal Kataloğu", KatalogPage)
        self.create_menu_button("Arşiv ve Analiz", ArsivPage)

        kur_frame = tk.Frame(self.sidebar, bg="#2980b9")
        kur_frame.pack(side="bottom", fill="x")
        self.lbl_kur = tk.Label(
            kur_frame,
            text="",
            bg="#2980b9",
            fg="white",
            font=FONT_NORMAL,
            pady=6,
            justify="center",
        )
        self.lbl_kur.pack(fill="x")
        tk.Button(
            kur_frame,
            text="Kurları Yenile",
            bg="#1f6aa5",
            fg="white",
            font=("Segoe UI", 9),
            relief="flat",
            cursor="hand2",
            pady=4,
            command=self.kurlari_yenile,
        ).pack(fill="x")
        self._kur_etiketini_guncelle()

        self.show_page("Yardımcı Kimyasal")

        if kur_uyari:
            self.after(200, lambda: msg_warning(self, "Kur Uyarısı", kur_uyari))

    def _kur_etiketini_guncelle(self):
        kaynak_map = {
            "tcmb": "TCMB",
            "cache": "önbellek",
            "yedek": "varsayılan",
        }
        kaynak = kaynak_map.get(self.kur_kaynak, self.kur_kaynak)
        self.lbl_kur.config(
            text=(
                f"USD {self.kurlar['USD']:.4f}  |  EUR {self.kurlar['EUR']:.4f}\n"
                f"Kaynak: {kaynak}"
            )
        )

    def kurlari_yenile(self):
        self.kurlar, self.kur_kaynak, uyari = DovizServisi.get()
        self._kur_etiketini_guncelle()
        if uyari:
            self.toast.show(uyari, kind="warn")
        else:
            self.toast.show("Kurlar TCMB'den güncellendi.", kind="ok")
        for page in self.pages.values():
            if hasattr(page, "kurlar_degisti"):
                page.kurlar_degisti()

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
        self._menu_buttons[text] = btn
        page = page_class(parent=self.main_area, controller=self)
        self.pages[text] = page
        page.grid(row=0, column=0, sticky="nsew")

    def _nav_guncelle(self, page_name):
        for ad, btn in self._menu_buttons.items():
            if ad == page_name:
                btn.configure(bg=RENK_AKTIF, fg="white")
            else:
                btn.configure(bg=RENK_SIDEBAR, fg="white")

    def show_page(self, page_name):
        frame = self.pages[page_name]
        if hasattr(frame, "on_show"):
            frame.on_show()
        frame.tkraise()
        self._aktif_sayfa = page_name
        self._nav_guncelle(page_name)

    def recete_duzenle(self, recete_id):
        recete = self.db.getir_by_id(recete_id)
        if not recete:
            msg_error(self, "Hata", "Reçete bulunamadı.")
            return
        sayfa_adi = TIP_SAYFA.get(recete["tur"])
        if not sayfa_adi:
            msg_error(self, "Hata", f"Bilinmeyen reçete türü: {recete['tur']}")
            return
        page = self.pages[sayfa_adi]
        page.yukle_recete(recete)
        self.show_page(sayfa_adi)
