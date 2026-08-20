"""窗口图标、对话框置顶等 UI 工具。"""

from __future__ import annotations

import sys
import tkinter as tk
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tkinter import Misc, colorchooser, filedialog, messagebox

import customtkinter as ctk

from .config import app_dir, resource_path

APP_ID = "Qinghong.Qianniu.ShipAssist.1.1"


def get_icon_path() -> Path | None:
    """Mac 优先 PNG；Win 优先 ICO。"""
    names = ("1.png", "app_icon.png", "1.ico") if sys.platform == "darwin" else ("1.ico", "1.png", "app_icon.png")
    for name in names:
        path = resource_path(name)
        if path.exists():
            return path
    return None


def setup_windows_app_id() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


def apply_window_icon(window: Misc) -> None:
    icon = get_icon_path()
    if not icon:
        return
    try:
        if sys.platform == "darwin" or icon.suffix.lower() != ".ico":
            # macOS / PNG：用 PhotoImage；大图缩到 64 避免 Tk 限制
            try:
                from PIL import Image, ImageTk

                pil = Image.open(icon)
                if pil.mode not in ("RGB", "RGBA"):
                    pil = pil.convert("RGBA")
                pil = pil.resize((64, 64), Image.Resampling.LANCZOS)
                img = ImageTk.PhotoImage(pil)
            except Exception:
                img = tk.PhotoImage(file=str(icon))
            window.iconphoto(True, img)
            window._qh_icon_ref = img  # noqa: SLF001
        else:
            window.iconbitmap(default=str(icon))
    except Exception:
        pass


def _text_inner(widget) -> tk.Text:
    """CTkTextbox 取内部 Text，普通 Text 直接返回。"""
    return getattr(widget, "_textbox", widget)


def enable_textbox_context_menu(widget) -> None:
    """为文本框补全右键复制/粘贴菜单（Win/Mac）。"""
    inner = _text_inner(widget)
    root = inner.winfo_toplevel()

    menu = tk.Menu(inner, tearoff=0)

    def _run(action: str) -> None:
        try:
            inner.event_generate(action)
        except tk.TclError:
            pass

    def _select_all() -> None:
        inner.tag_add("sel", "1.0", "end-1c")
        inner.mark_set("insert", "end-1c")
        inner.see("insert")

    menu.add_command(label="复制", command=lambda: _run("<<Copy>>"))
    menu.add_command(label="剪切", command=lambda: _run("<<Cut>>"))
    menu.add_command(label="粘贴", command=lambda: _run("<<Paste>>"))
    menu.add_separator()
    menu.add_command(label="全选", command=_select_all)

    def _show_menu(event):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    # Win: Button-3；Mac: Button-2 或 Control-Button-1
    inner.bind("<Button-3>", _show_menu)
    if sys.platform == "darwin":
        inner.bind("<Button-2>", _show_menu)
        inner.bind("<Control-Button-1>", _show_menu)
    root._qh_text_menus = getattr(root, "_qh_text_menus", [])
    root._qh_text_menus.append(menu)


def china_today_export_name() -> str:
    """中国时区导出默认文件名，如 2026.7.3-15.30.xlsx（含时分，避免同日覆盖）。"""
    cn_tz = timezone(timedelta(hours=8))
    now = datetime.now(cn_tz)
    return f"{now.year}.{now.month}.{now.day}-{now.hour}.{now.minute:02d}.xlsx"


def _prepare_dialog(master: Misc) -> None:
    """CustomTkinter 下 native 对话框/弹窗易被主窗遮挡。"""
    try:
        master.lift()
        master.focus_force()
        master.attributes("-topmost", True)
        master.update_idletasks()
    except Exception:
        pass


def _restore_dialog(master: Misc) -> None:
    try:
        master.attributes("-topmost", False)
        master.lift()
        master.focus_force()
    except Exception:
        pass


def show_info(master: Misc, title: str, message: str) -> None:
    _prepare_dialog(master)
    try:
        messagebox.showinfo(title, message, parent=master)
    finally:
        _restore_dialog(master)


def show_warning(master: Misc, title: str, message: str) -> None:
    _prepare_dialog(master)
    try:
        messagebox.showwarning(title, message, parent=master)
    finally:
        _restore_dialog(master)


def show_error(master: Misc, title: str, message: str) -> None:
    _prepare_dialog(master)
    try:
        messagebox.showerror(title, message, parent=master)
    finally:
        _restore_dialog(master)


def ask_color(master: Misc, title: str, color: str):
    _prepare_dialog(master)
    try:
        return colorchooser.askcolor(color=color, title=title, parent=master)
    finally:
        _restore_dialog(master)


def ask_save_xlsx(master: Misc, initialfile: str, initialdir=None) -> str:
    _prepare_dialog(master)
    try:
        kwargs = {
            "parent": master,
            "title": "导出 Excel",
            "defaultextension": ".xlsx",
            "initialfile": initialfile,
            "filetypes": [("Excel 文件", "*.xlsx"), ("所有文件", "*.*")],
        }
        if initialdir:
            kwargs["initialdir"] = str(initialdir)
        return filedialog.asksaveasfilename(**kwargs) or ""
    finally:
        _restore_dialog(master)


def ask_open_file(master: Misc, title: str, filetypes: list[tuple[str, str]]) -> str:
    _prepare_dialog(master)
    try:
        return (
            filedialog.askopenfilename(
                parent=master,
                title=title,
                filetypes=filetypes,
                initialdir=str(app_dir()),
            )
            or ""
        )
    finally:
        _restore_dialog(master)


def open_dialog_window(parent: ctk.CTk, title: str, geometry: str) -> ctk.CTkToplevel:
    """打开置顶的子窗口，避免被主窗遮挡。"""
    win = ctk.CTkToplevel(parent)
    win.title(title)
    win.geometry(geometry)
    apply_window_icon(win)
    try:
        win.transient(parent)
    except Exception:
        pass
    win.lift()
    win.focus_force()
    win.attributes("-topmost", True)
    win.after(80, lambda: win.attributes("-topmost", False))
    win.grab_set()
    return win
