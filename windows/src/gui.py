"""晴红千牛发货助手 — GUI 主界面。"""

from __future__ import annotations

import tkinter as tk
import webbrowser
from pathlib import Path

import customtkinter as ctk
import tksheet
from PIL import Image

from .ai_client import QinghongAIClient
from .colors import COLOR_PRESETS, normalize_hex
from .batch_io import batch_replace_in_results, import_from_xlsx, read_text_file, results_to_tsv
from .config import app_dir, load_config, resource_path, save_config
from .exporter import export_to_xlsx
from .history import get_history_entry, load_history, save_history_entry
from .keywords import apply_keyword_hits
from .parser import parse_batch
from .ui_utils import (
    apply_window_icon,
    ask_color,
    ask_open_file,
    ask_save_xlsx,
    china_today_export_name,
    enable_textbox_context_menu,
    open_dialog_window,
    setup_windows_app_id,
    show_error,
    show_info,
    show_warning,
)
from .usage_guide import USAGE_GUIDE
from .template_columns import read_template_headers, result_to_row, sync_row_to_result
from .validators import apply_phone_validation

APP_NAME = "晴红千牛发货助手"
APP_VERSION = "1.4.3"
CONTACT_WECHAT = "ziyouxiaoqi123"
CONTACT_NOTE = "备注来意"
FONT_FAMILY = "Microsoft YaHei UI"
FONT_MIN = 10
FONT_MAX = 24
SEPARATOR_LABELS = {
    "auto": "自动（空行优先）",
    "blank_line": "空行分隔",
    "newline": "每行一条",
    "semicolon": "分号分隔",
    "custom": "自定义分隔符",
}


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.config_data = load_config()
        self.results = []
        self.template_path = self._find_template()
        self.table_headers = read_template_headers(self.template_path)

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1280x820")
        self.minsize(1024, 680)

        setup_windows_app_id()
        apply_window_icon(self)

        self._build_ui()
        self._load_sample_hint()

    def _set_header_logo(self, header, logo_path: Path):
        """加载页头 Logo；CTkImage 失败时用 tk PhotoImage 兜底，避免 exe 崩溃。"""
        if not logo_path.exists():
            return
        try:
            pil_img = Image.open(logo_path)
            if pil_img.mode not in ("RGB", "RGBA"):
                pil_img = pil_img.convert("RGBA")
            self._logo_pil = pil_img.copy()
            self._logo_image = ctk.CTkImage(light_image=self._logo_pil, dark_image=self._logo_pil, size=(48, 48))
            ctk.CTkLabel(header, image=self._logo_image, text="").grid(row=0, column=0, padx=(16, 8), pady=12)
        except Exception:
            try:
                self._logo_photo = tk.PhotoImage(file=str(logo_path))
                tk.Label(header, image=self._logo_photo, bg="#FFF5F5", borderwidth=0).grid(row=0, column=0, padx=(16, 8), pady=12)
            except Exception:
                pass

    def _highlight_colors(self) -> dict:
        defaults = {"keyword_hit": "#FF4444", "parse_warn": "#FFFF99"}
        cfg = self.config_data.get("highlight_colors", {})
        return {
            "keyword_hit": normalize_hex(cfg.get("keyword_hit", defaults["keyword_hit"]), defaults["keyword_hit"]),
            "parse_warn": normalize_hex(cfg.get("parse_warn", defaults["parse_warn"]), defaults["parse_warn"]),
        }

    def _find_template(self) -> Path:
        for name in ("5.15新表格.xlsx", "5.15(3).新表格.xlsx", "template.xlsx"):
            path = resource_path(name)
            if path.exists():
                return path
        return resource_path("template.xlsx")

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color="#FFF5F5", corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        logo_path = resource_path("1.png")
        self._set_header_logo(header, logo_path)

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.grid(row=0, column=1, sticky="w", pady=12)
        ctk.CTkLabel(title_box, text=APP_NAME, font=ctk.CTkFont(size=22, weight="bold"), text_color="#C0392B").pack(anchor="w")
        ctk.CTkLabel(
            title_box,
            text="Powered by 晴红AI · 复杂地址 AI 兜底 · 更多能力请访问 www.qinghong.tech",
            font=ctk.CTkFont(size=13),
            text_color="#666666",
        ).pack(anchor="w")

        ctk.CTkButton(
            header, text="使用说明", width=90, fg_color="#E67E22", hover_color="#D35400",
            command=self.open_usage_guide,
        ).grid(row=0, column=2, padx=(16, 4), pady=12)
        ctk.CTkButton(
            header, text="AI配置", width=90, fg_color="#8E44AD", hover_color="#7D3C98",
            command=self.open_ai_settings,
        ).grid(row=0, column=3, padx=(4, 4), pady=12)
        ctk.CTkButton(
            header, text="注册晴红AI", width=110,
            command=lambda: webbrowser.open(self.config_data["ai"].get("register_url", "https://www.qinghong.tech/")),
        ).grid(row=0, column=4, padx=(4, 4), pady=12)
        ctk.CTkButton(
            header, text="API文档", width=80, fg_color="#666666", hover_color="#555555",
            command=lambda: webbrowser.open(self.config_data["ai"].get("docs_url", "https://qinghongkeji.apifox.cn/")),
        ).grid(row=0, column=5, padx=(4, 4), pady=12)
        ctk.CTkButton(
            header, text="联系开发者", width=100, fg_color="#27AE60", hover_color="#219653",
            command=self.open_contact,
        ).grid(row=0, column=6, padx=(4, 16), pady=12)

        tool_bar = ctk.CTkFrame(self)
        tool_bar.grid(row=1, column=0, sticky="ew", padx=12, pady=(8, 2))
        for i in range(12):
            tool_bar.grid_columnconfigure(i, weight=0)
        tool_bar.grid_columnconfigure(12, weight=1)

        buttons = [
            ("开始解析", self.on_parse, 90),
            ("导出Excel", self.on_export, 90),
            ("导入txt", self.on_import_txt, 80),
            ("导入xlsx", self.on_import_xlsx, 85),
            ("复制TSV", self.on_copy_tsv, 80),
            ("批量替换", self.open_batch_replace, 80),
            ("历史记录", self.open_history, 80),
            ("字体大小", self.open_font_settings, 80),
            ("选项开关", self.open_options_panel, 80),
            ("重新开始", self.on_reset, 80),
        ]
        for col, (text, cmd, width) in enumerate(buttons):
            ctk.CTkButton(tool_bar, text=text, width=width, command=cmd).grid(row=0, column=col, padx=3, pady=4)

        self.order_d_var = tk.BooleanVar(value=self.config_data.get("extract_order_no_to_d", False))
        ctk.CTkCheckBox(tool_bar, text="D列订单号", variable=self.order_d_var, command=self.on_toggle_options).grid(row=0, column=10, padx=6)
        self.use_ai_var = tk.BooleanVar(value=self.config_data["ai"].get("enabled", True))
        ctk.CTkCheckBox(tool_bar, text="晴红AI兜底", variable=self.use_ai_var, command=self.on_toggle_ai).grid(row=0, column=11, padx=6)

        self.stats_label = ctk.CTkLabel(tool_bar, text="就绪", text_color="#666666")
        self.stats_label.grid(row=0, column=12, sticky="e", padx=8)

        body = ctk.CTkFrame(self)
        body.grid(row=2, column=0, sticky="nsew", padx=12, pady=8)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        sep_label = SEPARATOR_LABELS.get(self.config_data.get("record_separator", "auto"), "自动")
        ctk.CTkLabel(left, text=f"粘贴收货文字（分隔：{sep_label}）", anchor="w").grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        self.input_box = ctk.CTkTextbox(left, wrap="word")
        self.input_box.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        enable_textbox_context_menu(self.input_box)

        kw_frame = ctk.CTkFrame(left)
        kw_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=8)
        kw_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(kw_frame, text="关键词整行标红").grid(row=0, column=0, padx=4, pady=4)
        self.kw_entry = ctk.CTkEntry(kw_frame, placeholder_text="输入关键词后回车")
        self.kw_entry.grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        self.kw_entry.bind("<Return>", lambda _e: self.add_keyword())
        ctk.CTkButton(kw_frame, text="添加", width=60, command=self.add_keyword).grid(row=0, column=2, padx=4)
        self.kw_tags_frame = ctk.CTkFrame(left, fg_color="transparent")
        self.kw_tags_frame.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 8))
        self._render_keyword_tags()

        right = ctk.CTkFrame(body)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right, text="解析预览（A~I 列与千牛模板一致 · 双击可编辑 · 关键词整行标红）", anchor="w").grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))

        table_wrap = tk.Frame(right, bg="#FFFFFF")
        table_wrap.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        table_wrap.grid_rowconfigure(0, weight=1)
        table_wrap.grid_columnconfigure(0, weight=1)

        self.sheet = tksheet.Sheet(
            table_wrap,
            headers=self.table_headers,
            theme="light blue",
            show_row_index=True,
            empty_horizontal=0,
            empty_vertical=0,
        )
        self.sheet.pack(fill="both", expand=True)
        self.sheet.enable_bindings((
            "single_select", "row_select", "column_width_resize", "arrowkeys",
            "edit_cell", "copy", "cut", "paste", "delete", "undo",
        ))
        self.sheet.extra_bindings([("end_edit_cell", self._on_cell_edited)])
        self._apply_font_sizes()

    def _font_cfg(self) -> dict:
        defaults = {"input_left": 14, "table_right": 13}
        cfg = self.config_data.get("font_sizes", {})
        return {
            "input_left": max(FONT_MIN, min(FONT_MAX, int(cfg.get("input_left", defaults["input_left"])))),
            "table_right": max(FONT_MIN, min(FONT_MAX, int(cfg.get("table_right", defaults["table_right"])))),
        }

    def _apply_font_sizes(self) -> None:
        sizes = self._font_cfg()
        self.input_box.configure(font=ctk.CTkFont(family=FONT_FAMILY, size=sizes["input_left"]))
        font_tuple = (FONT_FAMILY, sizes["table_right"], "normal")
        try:
            self.sheet.set_options(font=font_tuple, header_font=font_tuple, index_font=font_tuple)
        except Exception:
            self.sheet.font(font_tuple)
            self.sheet.header_font(font_tuple)
            self.sheet.index_font(font_tuple)
        self.sheet.redraw()

    def open_font_settings(self):
        win = self._open_toplevel("字体大小", "480x340")
        win.grid_columnconfigure(1, weight=1)
        sizes = self._font_cfg()

        ctk.CTkLabel(
            win,
            text="分别调节左侧输入框与右侧预览表格字体，保存后写入 config.json",
            text_color="#888888",
            wraplength=420,
        ).grid(row=0, column=0, columnspan=3, padx=16, pady=(16, 12), sticky="w")

        left_val = tk.IntVar(value=sizes["input_left"])
        right_val = tk.IntVar(value=sizes["table_right"])

        def _bind_slider(slider, var, label):
            def on_change(v):
                n = int(round(float(v)))
                var.set(n)
                label.configure(text=f"{n} 号")
            slider.configure(command=on_change)

        ctk.CTkLabel(win, text="左侧输入框", anchor="w").grid(row=1, column=0, padx=16, pady=8, sticky="w")
        left_slider = ctk.CTkSlider(win, from_=FONT_MIN, to=FONT_MAX, number_of_steps=FONT_MAX - FONT_MIN, width=260)
        left_slider.set(sizes["input_left"])
        left_slider.grid(row=1, column=1, padx=8, pady=8, sticky="ew")
        left_label = ctk.CTkLabel(win, text=f"{sizes['input_left']} 号", width=50)
        left_label.grid(row=1, column=2, padx=8, pady=8)
        _bind_slider(left_slider, left_val, left_label)

        ctk.CTkLabel(win, text="右侧预览表", anchor="w").grid(row=2, column=0, padx=16, pady=8, sticky="w")
        right_slider = ctk.CTkSlider(win, from_=FONT_MIN, to=FONT_MAX, number_of_steps=FONT_MAX - FONT_MIN, width=260)
        right_slider.set(sizes["table_right"])
        right_slider.grid(row=2, column=1, padx=8, pady=8, sticky="ew")
        right_label = ctk.CTkLabel(win, text=f"{sizes['table_right']} 号", width=50)
        right_label.grid(row=2, column=2, padx=8, pady=8)
        _bind_slider(right_slider, right_val, right_label)

        preset_frame = ctk.CTkFrame(win, fg_color="transparent")
        preset_frame.grid(row=3, column=0, columnspan=3, padx=16, pady=8, sticky="w")
        ctk.CTkLabel(preset_frame, text="快捷：").pack(side="left", padx=(0, 6))

        def apply_preset(left, right):
            left_slider.set(left)
            right_slider.set(right)
            left_val.set(left)
            right_val.set(right)
            left_label.configure(text=f"{left} 号")
            right_label.configure(text=f"{right} 号")

        for text, lv, rv in [("小", 11, 10), ("默认", 14, 13), ("大", 16, 15), ("特大", 18, 17)]:
            ctk.CTkButton(preset_frame, text=text, width=52, command=lambda a=lv, b=rv: apply_preset(a, b)).pack(side="left", padx=3)

        def save_fonts():
            fs = self.config_data.setdefault("font_sizes", {})
            fs["input_left"] = int(round(left_slider.get()))
            fs["table_right"] = int(round(right_slider.get()))
            save_config(self.config_data)
            self._apply_font_sizes()
            win.destroy()
            show_info(self, "已保存", "字体大小已更新")

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.grid(row=4, column=0, columnspan=3, padx=16, pady=16, sticky="e")
        ctk.CTkButton(btn_frame, text="保存", width=90, command=save_fonts).pack(side="left")

    def _load_sample_hint(self):
        self.stats_label.configure(text=f"模板：{self.template_path.name}")

    def _render_keyword_tags(self):
        for child in self.kw_tags_frame.winfo_children():
            child.destroy()
        keywords = self.config_data.get("keywords", [])
        for idx, kw in enumerate(keywords):
            tag = ctk.CTkFrame(self.kw_tags_frame, fg_color="#FFE5E5", corner_radius=16)
            tag.grid(row=0, column=idx, padx=4, pady=4)
            ctk.CTkLabel(tag, text=kw, text_color="#C0392B").pack(side="left", padx=(10, 2), pady=4)
            ctk.CTkButton(tag, text="×", width=24, height=24, fg_color="transparent", text_color="#C0392B", command=lambda k=kw: self.remove_keyword(k)).pack(side="left", padx=(0, 6))

    def add_keyword(self):
        kw = self.kw_entry.get().strip()
        if not kw:
            return
        keywords = self.config_data.setdefault("keywords", [])
        if kw not in keywords:
            keywords.append(kw)
            save_config(self.config_data)
        self.kw_entry.delete(0, "end")
        self._render_keyword_tags()
        if self.results:
            self.refresh_table()

    def remove_keyword(self, kw: str):
        keywords = self.config_data.get("keywords", [])
        if kw in keywords:
            keywords.remove(kw)
            save_config(self.config_data)
        self._render_keyword_tags()
        if self.results:
            self.refresh_table()

    def on_toggle_options(self):
        self.config_data["extract_order_no_to_d"] = self.order_d_var.get()
        save_config(self.config_data)
        if self.results:
            self.refresh_table()

    def on_toggle_ai(self):
        self.config_data.setdefault("ai", {})["enabled"] = self.use_ai_var.get()
        save_config(self.config_data)

    def _scan_config(self) -> dict:
        return self.config_data.get("keyword_scan", {})

    def _keyword_mode(self) -> str:
        return self.config_data.get("keyword_mode", "contains")

    def sync_from_sheet(self):
        if not self.results:
            return
        data = self.sheet.get_sheet_data()
        extract_d = self.order_d_var.get()
        for i, row in enumerate(data):
            if i >= len(self.results):
                break
            sync_row_to_result(self.results[i], row, extract_order_no_to_d=extract_d)
        apply_phone_validation(self.results)
        apply_keyword_hits(self.results, self.config_data.get("keywords", []), self._scan_config(), self._keyword_mode())

    def _on_cell_edited(self, event):
        self.sync_from_sheet()
        self.refresh_table()

    def refresh_table(self):
        apply_keyword_hits(
            self.results,
            self.config_data.get("keywords", []),
            self._scan_config(),
            self._keyword_mode(),
        )

        extract_d = self.order_d_var.get()
        data = []
        hit_rows, warn_rows = [], []

        for i, item in enumerate(self.results):
            data.append(result_to_row(item, extract_order_no_to_d=extract_d))
            if item.hit_keywords:
                hit_rows.append(i)
            elif item.error or not item.ok:
                warn_rows.append(i)

        self.sheet.headers(self.table_headers)
        self.sheet.set_sheet_data(data)
        self.sheet.dehighlight_all()
        colors = self._highlight_colors()
        for i in hit_rows:
            self.sheet.highlight_rows(rows=[i], bg=colors["keyword_hit"], fg="#000000", redraw=False)
        for i in warn_rows:
            self.sheet.highlight_rows(rows=[i], bg=colors["parse_warn"], fg="#000000", redraw=False)
        self.sheet.redraw()

        ok_count = sum(1 for r in self.results if r.ok)
        ai_used = sum(1 for r in self.results if r.source == "ai")
        hit_count = len(hit_rows)
        fail_count = len(warn_rows)
        self.stats_label.configure(
            text=f"共{len(self.results)}条 | 成功{ok_count} | 标红{hit_count} | 待处理{fail_count} | AI{ai_used}条"
        )

    def _ai_client(self) -> QinghongAIClient | None:
        ai = self.config_data.get("ai", {})
        if not ai.get("enabled", True) or not self.use_ai_var.get():
            return None
        return QinghongAIClient(ai.get("base_url", ""), ai.get("api_key", ""), ai.get("model", "gpt-4o-mini"))

    def on_reset(self):
        """清空左侧输入与右侧预览，便于录入下一批，无需重启程序。"""
        from tkinter import messagebox

        text = self.input_box.get("1.0", "end-1c").strip()
        if text or self.results:
            if not messagebox.askyesno(
                "重新开始",
                "将清空左侧收货文字与右侧预览表，便于录入下一批。\n是否继续？",
                parent=self,
            ):
                return

        self.input_box.delete("1.0", "end")
        self.results = []
        self.sheet.set_sheet_data([])
        self.sheet.dehighlight_all()
        self.sheet.redraw()
        self.stats_label.configure(text="就绪")

    def on_parse(self):
        raw = self.input_box.get("1.0", "end").strip()
        if not raw:
            show_warning(self, "提示", "请先粘贴或导入收货文字")
            return

        self.stats_label.configure(text="解析中...")
        self.update_idletasks()

        client = self._ai_client()
        ai_cfg = self.config_data.get("ai", {})
        self.results = parse_batch(
            raw,
            ai_client=client,
            use_ai=bool(client),
            separator=self.config_data.get("record_separator", "auto"),
            custom_sep=self.config_data.get("custom_separator", ""),
            custom_system_prompt=ai_cfg.get("system_prompt", ""),
        )
        apply_phone_validation(self.results)
        self.refresh_table()
        save_history_entry(raw, self.results)

    def on_export(self):
        if not self.results:
            show_warning(self, "提示", "请先解析后再导出")
            return
        try:
            self.sync_from_sheet()
        except Exception as exc:
            show_error(self, "导出失败", f"读取预览表失败：{exc}")
            return

        default_name = china_today_export_name()
        path = ask_save_xlsx(self, default_name, initialdir=app_dir())
        if not path:
            return
        try:
            colors = self._highlight_colors()
            export_to_xlsx(
                self.results, path,
                template_path=self.template_path,
                extract_order_no_to_d=self.order_d_var.get(),
                hit_color=colors["keyword_hit"],
                warn_color=colors["parse_warn"],
            )
            show_info(self, "导出成功", f"已保存到：\n{path}")
        except Exception as exc:
            show_error(self, "导出失败", str(exc))

    def on_import_txt(self):
        path = ask_open_file(self, "导入 txt", [("文本文件", "*.txt"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            text = read_text_file(path)
            self.input_box.delete("1.0", "end")
            self.input_box.insert("1.0", text)
            show_info(self, "导入成功", f"已加载：{Path(path).name}")
        except Exception as exc:
            show_error(self, "导入失败", str(exc))

    def on_import_xlsx(self):
        path = ask_open_file(self, "导入 xlsx", [("Excel 文件", "*.xlsx"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            self.results = import_from_xlsx(path)
            apply_phone_validation(self.results)
            self.refresh_table()
            show_info(self, "导入成功", f"已加载 {len(self.results)} 条")
        except Exception as exc:
            show_error(self, "导入失败", str(exc))

    def on_copy_tsv(self):
        if not self.results:
            show_warning(self, "提示", "暂无数据")
            return
        self.sync_from_sheet()
        tsv = results_to_tsv(self.results, self.order_d_var.get(), headers=self.table_headers)
        self.clipboard_clear()
        self.clipboard_append(tsv)
        show_info(self, "已复制", "表格数据已复制到剪贴板（TSV格式，可直接粘贴到Excel）")

    def open_batch_replace(self):
        if not self.results:
            show_warning(self, "提示", "请先解析数据")
            return
        win = self._open_toplevel("批量替换", "420x280")

        ctk.CTkLabel(win, text="查找").grid(row=0, column=0, padx=16, pady=10, sticky="w")
        find_ent = ctk.CTkEntry(win, width=280)
        find_ent.grid(row=0, column=1, padx=16, pady=10)

        ctk.CTkLabel(win, text="替换为").grid(row=1, column=0, padx=16, pady=10, sticky="w")
        repl_ent = ctk.CTkEntry(win, width=280)
        repl_ent.grid(row=1, column=1, padx=16, pady=10)

        var_name = tk.BooleanVar(value=False)
        var_addr = tk.BooleanVar(value=True)
        var_phone = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(win, text="收件人", variable=var_name).grid(row=2, column=1, sticky="w", padx=16)
        ctk.CTkCheckBox(win, text="收货地址", variable=var_addr).grid(row=3, column=1, sticky="w", padx=16)
        ctk.CTkCheckBox(win, text="手机号", variable=var_phone).grid(row=4, column=1, sticky="w", padx=16)

        def do_replace():
            fields = []
            if var_name.get():
                fields.append("name")
            if var_addr.get():
                fields.append("address")
            if var_phone.get():
                fields.append("phone")
            if not fields:
                show_warning(win, "提示", "请至少选择一个字段")
                return
            n = batch_replace_in_results(self.results, find_ent.get(), repl_ent.get(), tuple(fields))
            win.destroy()
            self.refresh_table()
            show_info(self, "完成", f"已替换 {n} 处")

        ctk.CTkButton(win, text="执行替换", command=do_replace).grid(row=5, column=1, padx=16, pady=16, sticky="e")

    def open_history(self):
        entries = load_history()
        win = self._open_toplevel("历史记录（最近5批）", "520x360")

        if not entries:
            ctk.CTkLabel(win, text="暂无历史记录").pack(padx=20, pady=40)
            return

        listbox = tk.Listbox(win, font=("Microsoft YaHei UI", 11))
        listbox.pack(fill="both", expand=True, padx=16, pady=16)
        for i, e in enumerate(entries):
            listbox.insert("end", f"{e.get('time')} — {e.get('count')}条")

        def load_selected():
            sel = listbox.curselection()
            if not sel:
                return
            data = get_history_entry(sel[0])
            if not data:
                return
            raw, results = data
            self.input_box.delete("1.0", "end")
            self.input_box.insert("1.0", raw)
            self.results = results
            self.refresh_table()
            win.destroy()

        ctk.CTkButton(win, text="恢复选中批次", command=load_selected).pack(pady=(0, 16))

    def _open_toplevel(self, title: str, geometry: str) -> ctk.CTkToplevel:
        return open_dialog_window(self, title, geometry)

    def open_usage_guide(self):
        win = self._open_toplevel("使用说明", "680x620")
        win.grid_rowconfigure(0, weight=1)
        win.grid_columnconfigure(0, weight=1)
        box = ctk.CTkTextbox(win, wrap="word", font=ctk.CTkFont(family="Microsoft YaHei UI", size=13))
        box.grid(row=0, column=0, sticky="nsew", padx=16, pady=(16, 8))
        box.insert("1.0", USAGE_GUIDE.strip())
        box.configure(state="disabled")
        ctk.CTkButton(win, text="关闭", width=80, command=win.destroy).grid(row=1, column=0, pady=(0, 16))

    def open_contact(self):
        win = self._open_toplevel("联系开发者", "420x220")
        ctk.CTkLabel(win, text="如有问题或定制需求，请微信联系开发者", font=ctk.CTkFont(size=14)).pack(padx=20, pady=(24, 12))
        ctk.CTkLabel(win, text=f"微信号：{CONTACT_WECHAT}", font=ctk.CTkFont(size=16, weight="bold"), text_color="#27AE60").pack(pady=8)
        ctk.CTkLabel(win, text=f"添加时请{CONTACT_NOTE}", text_color="#666666").pack(pady=4)

        def copy_wechat():
            self.clipboard_clear()
            self.clipboard_append(CONTACT_WECHAT)
            show_info(win, "已复制", f"微信号 {CONTACT_WECHAT} 已复制到剪贴板\n添加时请{CONTACT_NOTE}")

        ctk.CTkButton(win, text="复制微信号", command=copy_wechat).pack(pady=16)

    def open_ai_settings(self):
        """页头「AI配置」：保存后写入 exe 同目录 config.json。"""
        win = self._open_toplevel("AI 配置", "520x360")
        win.grid_columnconfigure(1, weight=1)

        ai = self.config_data.setdefault("ai", {})
        cfg_file = app_dir() / "config.json"

        ctk.CTkLabel(
            win,
            text=f"保存位置：{cfg_file}",
            text_color="#888888",
            wraplength=460,
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, padx=16, pady=(16, 8), sticky="w")

        entries = {}
        fields = [
            ("API 地址", "base_url"),
            ("API Key", "api_key"),
            ("模型名称", "model"),
        ]
        for idx, (label, key) in enumerate(fields):
            row = idx + 1
            ctk.CTkLabel(win, text=label, anchor="w").grid(row=row, column=0, padx=16, pady=10, sticky="w")
            ent = ctk.CTkEntry(win, width=340, show="*" if key == "api_key" else None)
            ent.grid(row=row, column=1, padx=16, pady=10, sticky="ew")
            ent.insert(0, ai.get(key, ""))
            entries[key] = ent

        enabled_var = tk.BooleanVar(value=ai.get("enabled", True))
        ctk.CTkCheckBox(win, text="启用晴红AI 兜底（规则失败时自动调用）", variable=enabled_var).grid(
            row=len(fields) + 1, column=0, columnspan=2, padx=16, pady=8, sticky="w"
        )

        ctk.CTkLabel(
            win,
            text="填写后点「保存」，配置立即写入 config.json，下次打开自动加载。",
            text_color="#888888",
            wraplength=460,
            anchor="w",
        ).grid(row=len(fields) + 2, column=0, columnspan=2, padx=16, pady=4, sticky="w")

        def test_ai_connection():
            client = QinghongAIClient(
                entries["base_url"].get().strip(),
                entries["api_key"].get().strip(),
                entries["model"].get().strip() or "gpt-4o-mini",
            )
            ok, msg = client.test_connection()
            if ok:
                show_info(win, "连接测试", msg)
            else:
                show_error(win, "连接测试", msg)

        def save_ai():
            for key, ent in entries.items():
                ai[key] = ent.get().strip()
            if not ai.get("model"):
                ai["model"] = "gpt-4o-mini"
            ai["enabled"] = enabled_var.get()
            self.config_data["ai"] = ai
            save_config(self.config_data)
            self.use_ai_var.set(ai["enabled"])
            win.destroy()
            show_info(self, "已保存", f"AI 配置已写入：\n{cfg_file}")

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.grid(row=len(fields) + 3, column=0, columnspan=2, padx=16, pady=16, sticky="e")
        ctk.CTkButton(
            btn_frame, text="测试连接", width=90, fg_color="#27AE60", hover_color="#1E8449",
            command=test_ai_connection,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_frame, text="保存", width=90, command=save_ai).pack(side="left")

    def open_options_panel(self):
        win = self._open_toplevel("功能开关", "520x640")

        scan = self.config_data.setdefault("keyword_scan", {})
        colors_cfg = self.config_data.setdefault("highlight_colors", {})
        row = 0

        ctk.CTkLabel(win, text="标记颜色（预览 + 导出 Excel 同步）", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=row, column=0, columnspan=3, padx=16, pady=(16, 8), sticky="w"
        )
        row += 1

        hit_var = tk.StringVar(value=colors_cfg.get("keyword_hit", "#FF4444"))
        warn_var = tk.StringVar(value=colors_cfg.get("parse_warn", "#FFFF99"))

        def _color_row(label, var, r):
            ctk.CTkLabel(win, text=label).grid(row=r, column=0, padx=16, pady=6, sticky="w")
            ent = ctk.CTkEntry(win, width=100, textvariable=var)
            ent.grid(row=r, column=1, padx=4, pady=6, sticky="w")
            preview = tk.Frame(win, width=36, height=24, bg=normalize_hex(var.get()))
            preview.grid(row=r, column=2, padx=4, pady=6)

            def pick():
                _, hexval = ask_color(win, f"选择{label}", normalize_hex(var.get()))
                if hexval:
                    var.set(hexval.upper())
                    preview.configure(bg=hexval)

            def on_preset(name):
                var.set(COLOR_PRESETS[name])
                preview.configure(bg=COLOR_PRESETS[name])

            ctk.CTkButton(win, text="选色", width=60, command=pick).grid(row=r, column=3, padx=4, pady=6)
            return ent, preview

        _color_row("关键词命中色", hit_var, row)
        row += 1
        _color_row("待处理/警告色", warn_var, row)
        row += 1

        preset_frame = ctk.CTkFrame(win, fg_color="transparent")
        preset_frame.grid(row=row, column=0, columnspan=4, padx=16, pady=4, sticky="w")
        ctk.CTkLabel(preset_frame, text="快捷：").pack(side="left", padx=(0, 4))
        for idx, (name, hexval) in enumerate(COLOR_PRESETS.items()):
            ctk.CTkButton(
                preset_frame, text=name, width=52, height=24,
                fg_color=hexval, hover_color=hexval, text_color="#000000",
                command=lambda h=hexval, v=hit_var: v.set(h),
            ).pack(side="left", padx=2)
        row += 1

        ctk.CTkLabel(win, text="点击快捷色块可填入「关键词命中色」", text_color="#888888").grid(
            row=row, column=0, columnspan=4, padx=16, pady=(0, 8), sticky="w"
        )
        row += 1

        ctk.CTkLabel(win, text="记录分隔符", font=ctk.CTkFont(size=14, weight="bold")).grid(row=row, column=0, columnspan=2, padx=16, pady=(16, 8), sticky="w")
        row += 1
        sep_var = tk.StringVar(value=self.config_data.get("record_separator", "auto"))
        sep_display = ctk.CTkOptionMenu(
            win, variable=sep_var,
            values=list(SEPARATOR_LABELS.keys()),
            width=200,
        )
        sep_display.grid(row=row, column=0, columnspan=2, padx=16, sticky="w")
        row += 1
        ctk.CTkLabel(win, text="自定义分隔符").grid(row=row, column=0, padx=16, pady=6, sticky="w")
        custom_sep_ent = ctk.CTkEntry(win, width=200, placeholder_text="如 |||")
        custom_sep_ent.insert(0, self.config_data.get("custom_separator", ""))
        custom_sep_ent.grid(row=row, column=1, padx=16, pady=6, sticky="w")
        row += 1

        ctk.CTkLabel(win, text="关键词匹配模式", font=ctk.CTkFont(size=14, weight="bold")).grid(row=row, column=0, columnspan=2, padx=16, pady=(16, 8), sticky="w")
        row += 1
        kw_mode_var = tk.StringVar(value=self.config_data.get("keyword_mode", "contains"))
        ctk.CTkRadioButton(win, text="包含匹配", variable=kw_mode_var, value="contains").grid(row=row, column=0, padx=16, sticky="w")
        ctk.CTkRadioButton(win, text="正则匹配", variable=kw_mode_var, value="regex").grid(row=row, column=1, padx=16, sticky="w")
        row += 1

        ctk.CTkLabel(win, text="导出 / 扫描开关", font=ctk.CTkFont(size=14, weight="bold")).grid(row=row, column=0, columnspan=2, padx=16, pady=(16, 8), sticky="w")
        row += 1
        self.order_d_var.set(self.config_data.get("extract_order_no_to_d", False))
        ctk.CTkCheckBox(win, text="D列：平台订单号", variable=self.order_d_var).grid(row=row, column=0, columnspan=2, padx=16, pady=4, sticky="w")
        row += 1

        scan_vars = {}
        for key, label in [("name", "A列：收件人"), ("address", "C列：收货地址"), ("phone", "B列：手机号"), ("remark", "I列：备注")]:
            var = tk.BooleanVar(value=scan.get(key, False))
            scan_vars[key] = var
            ctk.CTkCheckBox(win, text=label, variable=var).grid(row=row, column=0, columnspan=2, padx=16, pady=4, sticky="w")
            row += 1

        def save_options():
            self.config_data["record_separator"] = sep_var.get()
            self.config_data["custom_separator"] = custom_sep_ent.get()
            self.config_data["keyword_mode"] = kw_mode_var.get()
            self.config_data["extract_order_no_to_d"] = self.order_d_var.get()
            colors_cfg["keyword_hit"] = normalize_hex(hit_var.get())
            colors_cfg["parse_warn"] = normalize_hex(warn_var.get())
            for key, var in scan_vars.items():
                scan[key] = var.get()
            save_config(self.config_data)
            win.destroy()
            if self.results:
                self.refresh_table()
            show_info(self, "已保存", "选项已保存")

        ctk.CTkButton(win, text="保存", command=save_options).grid(row=row, column=1, padx=16, pady=16, sticky="e")


def run_app():
    setup_windows_app_id()
    app = App()
    app.mainloop()


if __name__ == "__main__":
    run_app()
