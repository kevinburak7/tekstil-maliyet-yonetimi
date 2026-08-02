"""Ana uygulama penceresi."""
import tkinter as tk
from tkinter import messagebox, ttk

from tekstil_maliyet.constants import (
    FONT_BASLIK,
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


