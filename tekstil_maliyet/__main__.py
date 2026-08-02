"""python -m tekstil_maliyet"""
from tkinter import messagebox

from tekstil_maliyet.ui.app import MaliyetApp


def main():
    try:
        app = MaliyetApp()
        app.mainloop()
    except Exception as e:
        messagebox.showerror("Kritik Hata", f"Uygulama başlatılamadı:\n{e}")


if __name__ == "__main__":
    main()
