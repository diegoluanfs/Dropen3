"""Graphical report for the system doctor."""
from __future__ import annotations
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from dropen3.system.doctor import collect_diagnostics, render_text


def show_doctor(parent):
    import customtkinter as ctk
    window = ctk.CTkToplevel(parent)
    window.title("Dropen3 System Doctor")
    window.geometry("780x580")
    window.transient(parent)
    window.lift()
    ctk.CTkLabel(window, text="System Doctor", font=("Arial", 24, "bold")).pack(pady=(16, 6))
    ctk.CTkLabel(window, text="Check local runtime dependencies and video capabilities.").pack(pady=(0, 12))
    report_area = ctk.CTkTextbox(window, wrap="word", font=("Consolas", 12))
    report_area.pack(fill="both", expand=True, padx=16, pady=8)
    buttons = ctk.CTkFrame(window, fg_color="transparent")
    buttons.pack(fill="x", padx=16, pady=(4, 16))
    state = {"report": None}

    def refresh():
        report = collect_diagnostics(check_display=False)
        state["report"] = report
        report_area.delete("1.0", "end")
        report_area.insert("1.0", render_text(report))

    def save_report():
        if state["report"] is None:
            refresh()
        path = filedialog.asksaveasfilename(parent=window, title="Save Diagnostic Report",
                                            defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            try:
                with open(path, "w", encoding="utf-8") as output:
                    json.dump(state["report"], output, indent=2, ensure_ascii=True)
            except OSError as error:
                messagebox.showerror("Save Failed", str(error), parent=window)

    ctk.CTkButton(buttons, text="Run Again", command=refresh).pack(side="left", padx=4)
    ctk.CTkButton(buttons, text="Export JSON", command=save_report).pack(side="left", padx=4)
    ctk.CTkButton(buttons, text="Close", command=window.destroy).pack(side="right", padx=4)
    refresh()
    return window
