"""Small, isolated Tk widgets shared by the graphical interface."""
from __future__ import annotations
import tkinter as tk

class Tooltip:
    """Display lightweight contextual help without a matplotlib dependency."""

    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.popup = None
        widget.bind("<Enter>", self.show_tip, add="+")
        widget.bind("<Leave>", self.hide_tip, add="+")
        widget.bind("<ButtonPress>", self.hide_tip, add="+")

    def show_tip(self, event=None):
        if self.popup is not None or not self.text:
            return
        popup = tk.Toplevel(self.widget)
        popup.withdraw()
        popup.wm_overrideredirect(True)
        popup.attributes("-topmost", True)
        tk.Label(popup, text=self.text, justify="left", background="#fffde8",
                 foreground="#202020", relief="solid", borderwidth=1,
                 padx=7, pady=5, wraplength=350).pack()
        x = self.widget.winfo_rootx() + 15
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        popup.wm_geometry(f"+{x}+{y}")
        popup.deiconify()
        self.popup = popup

    def hide_tip(self, event=None):
        if self.popup is not None:
            self.popup.destroy()
            self.popup = None
