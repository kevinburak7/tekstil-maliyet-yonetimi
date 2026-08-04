"""Ortak UI bileşenleri."""
import tkinter as tk
from tkinter import messagebox, ttk

from tekstil_maliyet.constants import (
    FONT_NORMAL,
    RENK_BASARI,
    RENK_IKINCIL,
    RENK_KART,
    RENK_METIN,
    RENK_METIN_SOLUK,
    RENK_TEHLIKE,
    RENK_VURGU,
)


class ModernButton(tk.Button):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(font=("Segoe UI", 11), relief="flat", cursor="hand2", pady=8)


def _parent(widget):
    try:
        return widget.winfo_toplevel()
    except tk.TclError:
        return None


def msg_info(widget, title, message):
    messagebox.showinfo(title, message, parent=_parent(widget))


def msg_error(widget, title, message):
    messagebox.showerror(title, message, parent=_parent(widget))


def msg_warning(widget, title, message):
    messagebox.showwarning(title, message, parent=_parent(widget))


def msg_yesno(widget, title, message):
    return messagebox.askyesno(title, message, parent=_parent(widget))


def msg_yesnocancel(widget, title, message):
    return messagebox.askyesnocancel(title, message, parent=_parent(widget))


class ToolTip:
    """Widget üzerine gelince kısa ipucu gösterir."""

    def __init__(self, widget, text, delay_ms=400):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id = None
        self._tip = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<Destroy>", self._on_destroy, add="+")

    def _on_destroy(self, _event=None):
        self._hide()

    def _schedule(self, _event=None):
        self._cancel()
        try:
            self._after_id = self.widget.after(self.delay_ms, self._show)
        except tk.TclError:
            self._after_id = None

    def _cancel(self):
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _show(self):
        if self._tip or not self.text:
            return
        try:
            if not self.widget.winfo_exists():
                return
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        except tk.TclError:
            return
        try:
            self._tip = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            tk.Label(
                tw,
                text=self.text,
                background="#2c3e50",
                foreground="white",
                font=FONT_NORMAL,
                padx=8,
                pady=4,
                justify="left",
                wraplength=280,
            ).pack()
        except tk.TclError:
            self._tip = None

    def _hide(self, _event=None):
        self._cancel()
        if self._tip:
            try:
                self._tip.destroy()
            except tk.TclError:
                pass
            self._tip = None


class ScrollableFrame(ttk.Frame):
    _instances = []
    _global_bound = False

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
        self._canvas = canvas

        ScrollableFrame._instances.append(self)
        self.bind("<Destroy>", self._on_destroy, add="+")
        if not ScrollableFrame._global_bound:
            self.after_idle(self._bind_global)

    def _on_destroy(self, _event=None):
        if self in ScrollableFrame._instances:
            ScrollableFrame._instances.remove(self)

    def _bind_global(self):
        if ScrollableFrame._global_bound:
            return
        try:
            root = self.winfo_toplevel()
        except tk.TclError:
            return
        root.bind_all("<MouseWheel>", ScrollableFrame._dispatch, add="+")
        ScrollableFrame._global_bound = True

    @staticmethod
    def _dispatch(event):
        for inst in list(ScrollableFrame._instances):
            try:
                if not inst.winfo_exists():
                    continue
                canvas = inst._canvas
                x, y = canvas.winfo_pointerxy()
                hedef = canvas.winfo_containing(x, y)
            except tk.TclError:
                continue
            w = hedef
            while w is not None:
                if w == canvas or w == inst:
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                    return "break"
                w = getattr(w, "master", None)
        return None


class EmptyState(tk.Frame):
    """Liste/tablo boşken gösterilen yönlendirici alan."""

    def __init__(
        self,
        master,
        baslik,
        aciklama="",
        aksiyon_metni=None,
        aksiyon=None,
        **kwargs,
    ):
        super().__init__(master, bg=RENK_KART, **kwargs)
        self._lbl_baslik = tk.Label(
            self,
            text=baslik,
            font=("Segoe UI", 13, "bold"),
            bg=RENK_KART,
            fg=RENK_METIN,
        )
        self._lbl_baslik.pack(pady=(40, 8))
        self._lbl_aciklama = tk.Label(
            self,
            text=aciklama,
            font=FONT_NORMAL,
            bg=RENK_KART,
            fg=RENK_METIN_SOLUK,
            wraplength=420,
            justify="center",
        )
        self._lbl_aciklama.pack(pady=(0, 16))
        self._btn = None
        self._aksiyon = aksiyon
        if aksiyon_metni and aksiyon:
            self._btn = ModernButton(
                self,
                text=aksiyon_metni,
                bg=RENK_VURGU,
                fg="white",
                width=22,
                command=aksiyon,
            )
            self._btn.pack(pady=(0, 40))

    def guncelle(self, baslik, aciklama="", aksiyon_metni=None, aksiyon=None):
        self._lbl_baslik.config(text=baslik)
        self._lbl_aciklama.config(text=aciklama)
        if self._btn is not None:
            self._btn.pack_forget()
            self._btn.destroy()
            self._btn = None
        if aksiyon_metni and aksiyon:
            self._btn = ModernButton(
                self,
                text=aksiyon_metni,
                bg=RENK_VURGU,
                fg="white",
                width=22,
                command=aksiyon,
            )
            self._btn.pack(pady=(0, 40))


class ToastBar(tk.Frame):
    """Ana pencerede kısa süreli durum mesajı."""

    _RENK = {
        "ok": RENK_BASARI,
        "info": "#2980b9",
        "warn": RENK_VURGU,
        "error": RENK_TEHLIKE,
    }

    def __init__(self, master, **kwargs):
        super().__init__(master, bg=RENK_IKINCIL, height=0, **kwargs)
        self.pack_propagate(False)
        self._label = tk.Label(
            self, text="", bg=RENK_IKINCIL, fg="white", font=FONT_NORMAL, pady=6
        )
        self._label.pack(fill="x")
        self._after_id = None
        self.pack_forget()

    def show(self, message, kind="ok", sure_ms=3200):
        bg = self._RENK.get(kind, self._RENK["info"])
        self.configure(bg=bg, height=28)
        self._label.configure(text=message, bg=bg)
        self.pack(side="bottom", fill="x")
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
        self._after_id = self.after(sure_ms, self.hide)

    def hide(self):
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        self.pack_forget()
