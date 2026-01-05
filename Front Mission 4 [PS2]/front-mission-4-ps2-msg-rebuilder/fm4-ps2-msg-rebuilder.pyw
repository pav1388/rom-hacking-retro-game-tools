#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
if sys.version_info < (3, 6):
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Требуется более новая версия Python",
            "Этот инструмент требует Python 3.6 или новее.\n"
            f"Ваша версия: {sys.version}\n\n"
            "Скачайте последнюю версию Python с:\n"
            "https://www.python.org/downloads/"
        )
        root.destroy()
    except Exception:
        print("Ошибка: требуется Python 3.6 или новее.", file=sys.stderr)
        print(f"Ваша версия: {sys.version}", file=sys.stderr)
    sys.exit(1)
import os
import struct
import json
import re
import glob
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import time
from datetime import datetime
import traceback
import tempfile
import argparse

MAIN_VERSION = '0.5'
MAIN_DATE = '5.1.2025'
MAIN_TITLE = f"Front Mission 4 (PS2) MSG Rebuilder v{MAIN_VERSION} /{MAIN_DATE}/ by pav13"


class TextContextMenu:
    def __init__(self, root, on_change_callback=None):
        self.root = root
        self.current_widget = None
        self.on_change_callback = on_change_callback 
        self.create_menu()
    
    def create_menu(self):
        self.menu = tk.Menu(self.root, tearoff=0)
        actions = [
            ("Вырезать", lambda: self._handle_action('cut')),
            ("Копировать", lambda: self._handle_action('copy')),
            ("Вставить", lambda: self._handle_action('paste')),
            ("-", None),
            ("Выделить все", lambda: self._handle_action('select_all'))]
        for label, cmd in actions:
            if label == "-":
                self.menu.add_separator()
            else:
                self.menu.add_command(label=label, command=cmd)
    
    def bind_to_widget(self, widget):
        if hasattr(widget, '_has_context_menu'):
            return
        if isinstance(widget, (tk.Text, tk.Entry, scrolledtext.ScrolledText)):
            widget.bind("<Button-3>", lambda e: self._show_menu(e, widget))
            widget.bind("<Control-c>", lambda e: self._hotkey_action(e, 'copy'), add='+')
            widget.bind("<Control-x>", lambda e: self._hotkey_action(e, 'cut'), add='+')
            widget.bind("<Control-v>", lambda e: self._hotkey_action(e, 'paste'), add='+')
            widget.bind("<Control-a>", lambda e: self._hotkey_action(e, 'select_all'), add='+')
        widget._has_context_menu = True
    
    def _show_menu(self, event, widget):
        self.current_widget = widget
        widget.focus_set()
        self.menu.tk_popup(event.x_root, event.y_root)
        return "break"
    
    def _handle_action(self, action):
        if not self.current_widget:
            return
        widget = self.current_widget
        if action == 'cut':
            widget.event_generate("<<Cut>>")
            if self.on_change_callback:
                self.on_change_callback()
        elif action == 'copy':
            widget.event_generate("<<Copy>>")
        elif action == 'paste':
            widget.event_generate("<<Paste>>")
            if self.on_change_callback:
                self.on_change_callback()
        elif action == 'select_all':
            if isinstance(widget, tk.Entry):
                widget.select_range(0, tk.END)
            else:
                widget.tag_add("sel", "1.0", "end")
    
    def _hotkey_action(self, event, action):
        widget = event.widget
        if action == 'cut':
            widget.event_generate("<<Cut>>")
            if self.on_change_callback:
                self.on_change_callback()
        elif action == 'copy':
            widget.event_generate("<<Copy>>")
        elif action == 'paste':
            widget.event_generate("<<Paste>>")
            if self.on_change_callback:
                self.on_change_callback()
        elif action == 'select_all':
            if isinstance(widget, tk.Entry):
                widget.select_range(0, tk.END)
            else:
                widget.tag_add("sel", "1.0", "end")
        return "break"
        
   
class ChunkParser:
    def __init__(self, mapping_data=None, debug=False, use_jis0208=True):
        self.debug = debug
        self.use_jis0208 = use_jis0208
        self.mappings = self.load_mappings_from_data(mapping_data)
        self.reverse_mappings = self._build_reverse_mappings()
        self.alph_reverse = {}
        for char, info in self.mappings.get("alph", {}).items():
            repl = info["replacement"]
            if repl.startswith("0x"):
                self.alph_reverse[char] = bytes([int(repl, 16)])
            else:
                self.alph_reverse[char] = repl.encode("utf-8")
        self.jis0208 = self.load_jis0208_index() if use_jis0208 else None
        self.jis0208_cp_to_ptr = self._build_jis0208_reverse_index()
        self.sorted_keys = {
            "01ff": sorted(self.mappings["01ff"].keys(), key=lambda x: -len(x)),
            "02ff": sorted(self.mappings["02ff"].keys(), key=lambda x: -len(x)),
        }

    def load_jis0208_index(self):
        index = {}
        path = Path("index-jis0208.txt")
        if not path.exists():
            return None
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) < 2:
                    continue
                try:
                    pointer = int(parts[0])
                    cp = int(parts[1], 16) if parts[1].startswith('0x') else int(parts[1])
                    index[pointer] = cp
                except ValueError:
                    continue
        return index

    def _build_jis0208_reverse_index(self):
        if self.jis0208 is None:
            return None
        rev = {}
        for ptr, cp in self.jis0208.items():
            if cp not in rev:
                rev[cp] = ptr
        return rev

    def _build_reverse_mappings(self):
        rev = {"01ff": {}, "02ff": {}}
        for sig_type in ["01ff", "02ff"]:
            for code_bytes, info in self.mappings[sig_type].items():
                rev[sig_type][info["replacement"]] = code_bytes
        return rev

    def load_mappings_from_data(self, mapping_data):
        return parse_mapping_data(mapping_data)

    def _format_debug_dump(self, data, xor_start=0):
        lines = ["# DEBUG", f"#   Chunk dump (XOR from 0x{xor_start:02X})",
                 "#            0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F"]
        for i in range(0, len(data), 16):
            chunk = bytearray(data[i:i+16])
            for j in range(len(chunk)):
                if i + j >= xor_start:
                    chunk[j] ^= 0xFF
            hex_str = ' '.join(f'{b:02X}' for b in chunk)
            lines.append(f"# {i:08X}: {hex_str}")
        return lines

    def decode_with_mapping(self, data, mapping_type="01ff"):
        result = []
        i = 0
        data_len = len(data)
        mappings = self.mappings[mapping_type]
        keys = self.sorted_keys[mapping_type]
        while i < data_len:
            matched = False
            for key in keys:
                if data.startswith(key, i):
                    result.append(mappings[key]['replacement'])
                    i += len(key)
                    matched = True
                    break
            if matched:
                continue
            b = data[i]
            if 0x20 <= b <= 0x7E:
                result.append(chr(b))
                i += 1
            elif 0xA1 <= b <= 0xDF:
                result.append(chr(0xFF61 + (b - 0xA1)))
                i += 1
            elif (0x81 <= b <= 0x9F) or (0xE0 <= b <= 0xFC):
                if i + 1 >= data_len:
                    result.append(f'[${b:02X}$]')
                    i += 1
                    continue
                b2 = data[i + 1]
                if not ((0x40 <= b2 <= 0x7E) or (0x80 <= b2 <= 0xFC)):
                    result.append(f'[$sjis_bad2_{b:02X}{b2:02X}$]')
                    i += 2
                    continue
                offset = 0x40 if b2 < 0x7F else 0x41
                lead_offset = 0x81 if b < 0xA0 else 0xC1
                pointer = (b - lead_offset) * 188 + (b2 - offset)
                if 8836 <= pointer <= 10715:
                    result.append(chr(0xE000 - 8836 + pointer))
                    i += 2
                elif self.jis0208 and pointer in self.jis0208:
                    result.append(chr(self.jis0208[pointer]))
                    i += 2
                else:
                    try:
                        char = data[i:i+2].decode('cp932') #shift_jis
                        if len(char) == 1 and ord(char) >= 0x80:
                            result.append(char)
                            i += 2
                            continue
                    except UnicodeDecodeError:
                        pass
                    result.append(f'[$sjis_unkn_{b:02X}{b2:02X}$]')
                    i += 2
            else:
                result.append(f'[${b:02X}$]')
                i += 1
        return ''.join(result)

    def encode_with_mapping(self, text, mapping_type="01ff"):
        result = bytearray()
        i = 0
        while i < len(text):
            if text.startswith('[$', i):
                end = text.find('$]', i)
                if end != -1:
                    inner = text[i+2:end]
                    if len(inner) == 2 and all(c in '0123456789ABCDEFabcdef' for c in inner):
                        result.append(int(inner, 16))
                        i = end + 2
                        continue
            char = text[i]
            if char in self.alph_reverse:
                result.extend(self.alph_reverse[char])
                i += 1
                continue
            matched = False
            for token in sorted(self.reverse_mappings[mapping_type], key=len, reverse=True):
                if text.startswith(token, i):
                    result.extend(self.reverse_mappings[mapping_type][token])
                    i += len(token)
                    matched = True
                    break
            if matched:
                continue
            cp = ord(char)
            if 0x20 <= cp <= 0x7E:
                result.append(cp)
                i += 1
            elif 0xFF61 <= cp <= 0xFF9F:
                result.append(cp - 0xFF61 + 0xA1)
                i += 1
            elif self.jis0208_cp_to_ptr and cp in self.jis0208_cp_to_ptr:
                pointer = self.jis0208_cp_to_ptr[cp]
                if 8272 <= pointer <= 8835:
                    result.extend(b'?')
                    i += 1
                    continue
                lead = pointer // 188
                lead_offset = 0x81 if lead < 0x1F else 0xC1
                trail = pointer % 188
                offset = 0x40 if trail < 0x3F else 0x41
                b1 = lead + lead_offset
                b2 = trail + offset
                if (0x81 <= b1 <= 0x9F or 0xE0 <= b1 <= 0xFC) and ((0x40 <= b2 <= 0x7E) or (0x80 <= b2 <= 0xFC)):
                    result.append(b1)
                    result.append(b2)
                    i += 1
                else:
                    result.extend(b'?')
                    i += 1
            else:
                try:
                    encoded = char.encode('cp932') #shift_jis
                    if len(encoded) in (1, 2):
                        result.extend(encoded)
                        i += 1
                        continue
                except (UnicodeEncodeError, AttributeError):
                    pass
                result.extend(b'?')
                i += 1
        return bytes(result)

    def split_by_iterate_markers(self, text, mapping_type="01ff"):
        markers = [(m['replacement'], m['mode']) for m in self.mappings.get(mapping_type, {}).values() if m['mode'] > 0]
        if not markers:
            return [text]
        parts = [text]
        for marker, mode in markers:
            new_parts = []
            for part in parts:
                if mode == 1:
                    split = part.split(marker)
                    for idx, sp in enumerate(split):
                        if idx > 0:
                            new_parts.append(marker)
                        if sp:
                            new_parts.append(sp)
                elif mode == 2:
                    split = part.split(marker)
                    for idx, sp in enumerate(split):
                        if sp:
                            new_parts.append(sp)
                        if idx < len(split) - 1:
                            new_parts.append(marker)
                elif mode == 3:
                    tokens = part.split(marker)
                    for idx, tok in enumerate(tokens):
                        if tok:
                            new_parts.append(tok)
                        if idx < len(tokens) - 1:
                            new_parts.append(marker)
                else:
                    new_parts.append(part)
            parts = new_parts
        return [p for p in parts if p]

    def parse_01ff(self, data):
        total_size = len(data)
        if total_size < 8:
            raise ValueError("File too short for 01FF")
        resource_name = None
        if data[2:6] == b'\xF0\x00\x50\x00' and total_size >= 8:
            data_size = struct.unpack('<H', data[6:8])[0]
            pos = 8
            signature = data[:6].hex().upper()
        elif total_size >= 20:
            data_size = struct.unpack('<H', data[18:20])[0]
            pos = 20
            signature = data[:18].hex().upper()
            resource_name = data[2:18].rstrip(b'\x00').decode('ascii', errors='ignore')
        else:
            raise ValueError("Invalid 01FF header")
        if pos + data_size != total_size:
            raise ValueError(f"Declared data size {data_size} != actual {total_size - pos}")
        decoded_data = bytes(b ^ 0xFF for b in data[pos:pos + data_size])
        full_text = self.decode_with_mapping(decoded_data, "01ff")
        lines = self.split_by_iterate_markers(full_text, "01ff")
        output = [
            "[FILE INFO]",
            f"SIGNATURE: {signature}",
            f"RESOURCE_NAME: {resource_name}",
            f"DATA: {data_size}",
            "",
            "[CONTENT]"
        ]
        for i, line in enumerate(lines):
            output.append(f"LINE_{i:03d}_ORIG: {line}")
            output.append(f"LINE_{i:03d}_TRAN: {line}")
            output.append("")
        if self.debug:
            output.extend(self._format_debug_dump(data, pos))
        return '\n'.join(output)

    def parse_02ff(self, data):
        total_size = len(data)
        if total_size < 4:
            raise ValueError("File too short for 02FF")
        if data[2:6] == b'\xF0\x00\x50\x00' and total_size > 7:
            signature = data[:6].hex().upper()
            expected_count = data[7] + 1
            offset_table_start = 8
        elif data[2:3] == b'\x00' and total_size > 3:
            signature = data[:3].hex().upper()
            expected_count = data[3] + 1
            offset_table_start = 4
        else:
            raise ValueError("02FF: unknown header format")
        offsets = []
        pos = offset_table_start
        while pos + 2 <= total_size:
            val = struct.unpack('<H', data[pos:pos+2])[0]
            if val == 0xFFFF:
                pos += 2
                break
            offsets.append(val)
            pos += 2
        else:
            raise ValueError("02FF: offset table not terminated with FFFF")
        data_start = pos
        decoded_data = bytes(b ^ 0xFF for b in data[data_start:])
        output = [
            "[FILE INFO]",
            f"SIGNATURE: {signature}",
            f"OFFSETS: {expected_count}",
            "",
            "[CONTENT]"
        ]
        for i in range(expected_count):
            start_abs = offsets[i] if i < len(offsets) else len(data)
            end_abs = offsets[i+1] if (i+1 < len(offsets)) else len(data)
            if start_abs < data_start:
                text = ""
            else:
                rel_start = start_abs - data_start
                rel_end = min(end_abs - data_start, len(decoded_data))
                if rel_start >= rel_end or rel_start >= len(decoded_data):
                    text = ""
                else:
                    text = self.decode_with_mapping(decoded_data[rel_start:rel_end], "02ff")
            for line in self.split_by_iterate_markers(text, "02ff"):
                if line.strip() or text == "":
                    output.append(f"LINE_{i:03d}_ORIG: {line}")
                    output.append(f"LINE_{i:03d}_TRAN: {line}")
                    output.append("")
        if self.debug:
            output.extend(self._format_debug_dump(data, data_start))
        return '\n'.join(output)

    def build_01ff(self, txt_content):
        lines = txt_content.splitlines()
        signature = ""
        for line in lines:
            if line.startswith("SIGNATURE: "):
                signature = line.split(":", 1)[1].strip()
        content_lines = []
        in_content = False
        for line in lines:
            if line == "[CONTENT]":
                in_content = True
            elif in_content and line.startswith("LINE_") and "_TRAN: " in line:
                content_lines.append(line.split(": ", 1)[1])
        full_text = "".join(content_lines)
        decoded_bytes = self.encode_with_mapping(full_text, "01ff")
        encoded_bytes = bytes(b ^ 0xFF for b in decoded_bytes)
        actual_size = len(encoded_bytes)
        header = bytes.fromhex(signature) + struct.pack('<H', actual_size)
        return header + encoded_bytes

    def build_02ff(self, txt_content):
        lines = txt_content.splitlines()
        signature = ""
        expected_offsets = 0
        for line in lines:
            if line.startswith("SIGNATURE: "):
                signature = line.split(":", 1)[1].strip()
            elif line.startswith("OFFSETS: "):
                try:
                    expected_offsets = int(line.split(":", 1)[1].strip())
                except:
                    expected_offsets = 0
        content_by_index = {}
        in_content = False
        for line in lines:
            if line == "[CONTENT]":
                in_content = True
            elif in_content and line.startswith("LINE_") and "_TRAN: " in line:
                idx_match = re.match(r'LINE_(\d+)_TRAN:', line)
                if idx_match:
                    idx = int(idx_match.group(1))
                    text = line.split(": ", 1)[1]
                    content_by_index.setdefault(idx, []).append(text)
        record_count = expected_offsets if expected_offsets > 0 else (max(content_by_index.keys()) + 1 if content_by_index else 0)
        raw_records = ["".join(content_by_index.get(i, [])) for i in range(record_count)]
        decoded_fragments = [self.encode_with_mapping(r, "02ff") for r in raw_records]
        if signature == "02FFF0005000":
            base_header = bytes.fromhex("02FFF0005000") + bytes([0, len(decoded_fragments) - 1])
        else:
            base_header = bytes.fromhex("02FF00") + bytes([len(decoded_fragments) - 1])
        rel_offsets = []
        current = 0
        for frag in decoded_fragments:
            rel_offsets.append(current)
            current += len(frag)
        data_start_abs = len(base_header) + len(rel_offsets) * 2 + 2
        abs_offsets = [off + data_start_abs for off in rel_offsets]
        offset_bytes = b"".join(struct.pack("<H", off) for off in abs_offsets) + b"\xFF\xFF"
        encoded_full = b"".join(bytes(b ^ 0xFF for b in frag) for frag in decoded_fragments)
        return base_header + offset_bytes + encoded_full


# ===== ПАРСЕР MAPPING =====
def parse_mapping_data(raw_text):
    mappings = {"01ff": {}, "02ff": {}, "alph": {}}
    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = re.split(r'\s+', line)
        sig_type = parts[0].lower()
        if sig_type in ("01ff", "02ff"):
            if len(parts) < 4:
                continue
            code = parts[1].upper()
            mode = min(3, max(0, int(parts[2])))
            repl = f"[${parts[3]}$]"
            mappings[sig_type][bytes.fromhex(code)] = {'replacement': repl, 'mode': mode}
        elif sig_type == "alph" and len(parts) >= 3:
            char, repl = parts[1], parts[2]
            mappings["alph"][char] = {'replacement': repl, 'mode': 0}
    return mappings


class FM4MSGTool:
    def __init__(self, root):
        self.root = root
        self.root.title(MAIN_TITLE)
        self.root.geometry("900x600")
        self.root.minsize(600, 400)
        self.initial_geometry = self.root.geometry()
        self.colors = {"ALPH":"#F3D0D0","01FF":"#D6F3D0","02FF":"#D3E3F3","bg_log":"#E1E1E1","accent_g":"#4CAF50","accent_b":"#2196F3","accent_o":"#F3A621","accent_r":"#fe6666"}
        self.text_context_menu = TextContextMenu(self.root)
        self.mapping_context_menu = TextContextMenu(self.root, on_change_callback=self.on_mapping_change)
        self.config_path = Path(tempfile.gettempdir()) / "fm4-ps2-msg-rebuilder-config.json"
        self.default_mapping_file = "mapping.txt"
        self.load_initial_mapping()
        self.setup_gui()
        self.load_config()
        self.mapping_modified = False
        for w in (self.alph_text, self.ff01_text, self.ff02_text):
            w.bind("<KeyRelease>", self.on_mapping_change)
            w.bind("<Control-v>", self.on_mapping_change)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind("<Configure>", self.on_window_configure)
            
    def on_mapping_change(self, event=None):
        self.mapping_modified = True
    
    def load_initial_mapping(self):
        if Path(self.default_mapping_file).exists():
            with open(self.default_mapping_file, 'r', encoding='utf-8') as f:
                self.mapping_text = f.read()
        else:
            self.mapping_text = ("")

    def on_window_configure(self, event):
        if event.widget == self.root:
            self.window_geometry = self.root.geometry()

    def setup_gui(self):
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.setup_log_panel(right_frame)
        
        self.notebook = tk.Frame(left_frame)
        tabs_frame = tk.Frame(left_frame)
        tabs_frame.pack(fill=tk.X, pady=(0, 5))
        self.tab_buttons = []
        self.tabs = []
        for i, (text, command) in enumerate([
            ("-MSG-", lambda: self.show_tab(0)),
            ("-ALPH-", lambda: self.show_tab(1)),
            ("-01FF-", lambda: self.show_tab(2)),
            ("-02FF-", lambda: self.show_tab(3)),
            ("-Настройки-", lambda: self.show_tab(4))
        ]):
            btn = tk.Button(tabs_frame, text=text, width=12 if i < 4 else 15,
                            command=command, bg='#B6B6B6',
                            font=('Arial', 10, 'bold'), relief=tk.RAISED)
            btn.pack(side=tk.LEFT, padx=0)
            self.tab_buttons.append(btn)

        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.setup_msg_tab()
        self.setup_mapping_tab("ALPH", "Формат: ALPH\t<символ>\t<замена>\t<#примечание>\nПример: ALPH\tА\tA\t# 'А' кириллическая -> 'A' латинская\n\tALPH\tВ\t0x42\t# 'В' кириллическая -> байт 0x42 ('B')")
        self.setup_mapping_tab("01FF", "Формат: 01FF\t<HEX>\t<режим>\t<замена_без_пробелов>\t<#примечание>\nРежим разделения на подстроки: 0=не делить, 1=перед, 2=после, 3=перед и после\nПример: 01FF\tFF03\t3\tln_break_FF03\t# перенос строки")
        self.setup_mapping_tab("02FF", "Формат: 02FF\t<HEX>\t<режим>\t<замена_без_пробелов>\t<#примечание>\nРежим разделения на подстроки: 0=не делить, 1=перед, 2=после, 3=перед и после\nПример: 02FF\tFD3F\t0\tstart_FD3F\t# начало записи")
        self.setup_settings_tab()
        self.show_tab(0)

    def show_tab(self, tab_index):
        for i, btn in enumerate(self.tab_buttons):
            if i == tab_index:
                btn.config(relief=tk.SUNKEN, bg='#e0e0e0')
            else:
                btn.config(relief=tk.RAISED, bg='SystemButtonFace')
        for widget in self.notebook.winfo_children():
            widget.pack_forget()
        self.tabs[tab_index].pack(fill=tk.BOTH, expand=True)

    def setup_msg_tab(self):
        msg_frame = tk.Frame(self.notebook)
        self.tabs.append(msg_frame)

        extract_frame = tk.LabelFrame(msg_frame, text="ИЗВЛЕЧЕНИЕ текста из MSG")
        extract_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(extract_frame, text="Входной MSG:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.extract_input_path_var = tk.StringVar()
        self.extract_input_entry = tk.Entry(extract_frame, textvariable=self.extract_input_path_var, width=40)
        self.extract_input_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        self.text_context_menu.bind_to_widget(self.extract_input_entry)
        btn_frame1 = tk.Frame(extract_frame)
        btn_frame1.grid(row=0, column=2, padx=5, pady=5)
        tk.Button(btn_frame1, text="Файл", command=self.select_extract_input_file, width=8).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame1, text="Папка", command=self.select_extract_input_folder, width=8).pack(side=tk.LEFT, padx=2)

        tk.Label(extract_frame, text="Выходная папка:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.extract_output_path_var = tk.StringVar(value=str(Path.cwd() / "extracted-txt"))
        extract_output_entry = tk.Entry(extract_frame, textvariable=self.extract_output_path_var, width=40)
        extract_output_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        self.text_context_menu.bind_to_widget(extract_output_entry)
        tk.Button(extract_frame, text="Обзор", command=self.select_extract_output_folder, width=10).grid(row=1, column=2, padx=5, pady=5)

        tk.Button(extract_frame, text="ИЗВЛЕЧЬ ТЕКСТ",
                  command=self.start_parsing, bg=self.colors["accent_g"],
                  font=('Arial', 10, 'bold'), height=2).grid(
            row=2, column=0, columnspan=3, pady=(10, 5), padx=5, sticky=tk.EW)
        self.extract_status_var = tk.StringVar(value="")
        tk.Label(extract_frame, textvariable=self.extract_status_var,
                 fg='blue', font=('Arial', 10)).grid(row=3, column=0, columnspan=3, pady=(0, 5))
        extract_frame.grid_columnconfigure(1, weight=1)

        build_frame = tk.LabelFrame(msg_frame, text="СБОРКА MSG из текста")
        build_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(build_frame, text="Папка с TXT:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.build_input_path_var = tk.StringVar()
        build_input_entry = tk.Entry(build_frame, textvariable=self.build_input_path_var, width=40)
        build_input_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        self.text_context_menu.bind_to_widget(build_input_entry)
        tk.Button(build_frame, text="Обзор", command=self.select_build_input_folder, width=10).grid(row=0, column=2, padx=5, pady=5)

        tk.Label(build_frame, text="Выходная папка:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.build_output_path_var = tk.StringVar(value=str(Path.cwd() / "builded-msg"))
        build_output_entry = tk.Entry(build_frame, textvariable=self.build_output_path_var, width=40)
        build_output_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        self.text_context_menu.bind_to_widget(build_output_entry)
        tk.Button(build_frame, text="Обзор", command=self.select_build_output_folder, width=10).grid(row=1, column=2, padx=5, pady=5)

        tk.Button(build_frame, text="СОБРАТЬ MSG",
                  command=self.start_building, bg=self.colors["accent_b"],
                  font=('Arial', 10, 'bold'), height=2).grid(
            row=2, column=0, columnspan=3, pady=(10, 5), padx=5, sticky=tk.EW)
        
        self.build_status_var = tk.StringVar(value="")
        tk.Label(build_frame, textvariable=self.build_status_var,
                 fg='blue', font=('Arial', 10)).grid(row=3, column=0, columnspan=3, pady=(0, 5))
        build_frame.grid_columnconfigure(1, weight=1)
        hint_frame = tk.Frame(msg_frame)
        hint_frame.pack(fill=tk.X, padx=5, pady=(0, 10))
        tk.Label(hint_frame, text="Папка с TXT файлами = Выходная папка при извлечении",
                 justify=tk.LEFT, font=('Arial', 8), wraplength=400).pack(anchor=tk.W)

    def setup_mapping_tab(self, prefix: str, hint_text: str):
        frame = tk.Frame(self.notebook)
        self.tabs.append(frame)
        hint = tk.Label(frame, text=hint_text, justify=tk.LEFT, anchor="w")
        hint.pack(anchor=tk.W, padx=5, pady=(5, 0))
        text_widget = scrolledtext.ScrolledText(frame,
            wrap=tk.NONE, font=('Consolas', 10, 'bold'), height=15, bg=self.colors[prefix])
        text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.mapping_context_menu.bind_to_widget(text_widget)
        if prefix == "ALPH":
            self.alph_text = text_widget
        elif prefix == "01FF":
            self.ff01_text = text_widget
        elif prefix == "02FF":
            self.ff02_text = text_widget
        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        search_var = tk.StringVar()
        search_entry = tk.Entry(btn_frame, textvariable=search_var, width=20, bg=self.colors[prefix], font=('Consolas', 10, 'bold'))
        search_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.text_context_menu.bind_to_widget(search_entry)
        def find_next():
            query = search_var.get()
            if not query:
                return
            text_widget.tag_remove('search', '1.0', tk.END)
            text_widget.tag_config('search', background='black', foreground='white')
            start_idx = text_widget.index(tk.INSERT)
            pos = text_widget.search(query, start_idx, tk.END, nocase=False)
            if not pos:
                pos = text_widget.search(query, '1.0', tk.END, nocase=False)
            if pos:
                end_pos = f"{pos}+{len(query)}c"
                text_widget.tag_add('search', pos, end_pos)
                text_widget.mark_set(tk.INSERT, end_pos)
                text_widget.see(pos)

        tk.Button(btn_frame, text="Найти", bg=self.colors["accent_o"], command=find_next, width=8).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(btn_frame, text="Загрузить", bg=self.colors["accent_b"],
                  command=lambda p=prefix, w=text_widget: self.load_mapping_section(p, w),
                  width=12).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="Сохранить", bg=self.colors["accent_g"],
                  command=lambda p=prefix, w=text_widget: self.save_mapping_section(p, w),
                  width=12).pack(side=tk.RIGHT, padx=5)
        self.load_mapping_section(prefix, text_widget)
    
    def load_mapping_section(self, prefix: str, text_widget):
        raw_text = ""
        file_path = Path(self.default_mapping_file)
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_text = f.read()
                success = True
            except Exception as e:
                self.log_message(f"[X] Не удалось прочитать {file_path}: {e}")
                success = False
        else:
            self.log_message(f"[!] Файл {file_path} не найден — пустой {prefix} маппинг")
            success = False
        lines = []
        for line in raw_text.splitlines():
            stripped = line.strip()
            if stripped.startswith(prefix):
                lines.append(stripped)
        text_widget.delete(1.0, tk.END)
        text_widget.insert(tk.END, '\n'.join(lines))
        self.mapping_text = raw_text
        if success:
            self.log_message(f"{prefix} маппинг загружен из {file_path}")

    def save_mapping_section(self, prefix: str, text_widget):
        input_lines = text_widget.get(1.0, tk.END).strip().splitlines()
        valid_lines = [line.strip() for line in input_lines if line.strip().startswith(prefix)]
        filtered_lines = [
            line for line in self.mapping_text.splitlines()
            if not line.strip().startswith(prefix)
        ]
        updated_lines = filtered_lines + valid_lines
        self.mapping_text = '\n'.join(updated_lines)
        with open(self.default_mapping_file, 'w', encoding='utf-8') as f:
            f.write(self.mapping_text)
        self.mapping_modified = False
        self.log_message(f"{prefix} маппинг сохранён в файл")

    def setup_settings_tab(self):
        settings_frame = tk.Frame(self.notebook)
        self.tabs.append(settings_frame)
        self.log_showall_var = tk.BooleanVar(value=False)
        tk.Checkbutton(settings_frame, text="Показывать подробные логи (медленнее)",
                       variable=self.log_showall_var).pack(anchor=tk.W, pady=2)
        self.auto_save_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="Автосохранение настроек при выходе",
                       variable=self.auto_save_var).pack(anchor=tk.W, pady=2)
        self.save_window_geometry_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="Сохранять положение и размер окна",
                       variable=self.save_window_geometry_var).pack(anchor=tk.W, pady=2)
        self.debug_output_var = tk.BooleanVar(value=False)
        tk.Checkbutton(settings_frame, text="Вывод отладочной информации в txt файлах при извлечении",
                       variable=self.debug_output_var).pack(anchor=tk.W, pady=2)
        self.use_jis0208_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="Использовать index-jis0208.txt для японской кодировки (рекомендуется)",
                       variable=self.use_jis0208_var).pack(anchor=tk.W, pady=2)
        btn_frame = tk.Frame(settings_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        tk.Button(btn_frame, text="Сохранить настройки", bg=self.colors["accent_g"],
                  command=self.save_config, width=20, height=2).pack(pady=2)
        tk.Button(btn_frame, text="Загрузить настройки", bg=self.colors["accent_b"],
                  command=self.load_config, width=20, height=2).pack(pady=2)
        tk.Button(btn_frame, text="Сбросить все настройки", bg=self.colors["accent_r"],
                  command=self.reset_all_settings, width=20, height=2).pack(pady=2)

    def setup_log_panel(self, parent):
        log_frame = tk.LabelFrame(parent, text="Логи")
        log_frame.pack(fill=tk.BOTH, expand=True)
        text_frame = tk.Frame(log_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=('Consolas', 9), height=15, bg=self.colors["bg_log"])
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.text_context_menu.bind_to_widget(self.log_text)
        btn_frame = tk.Frame(log_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        tk.Button(btn_frame, text="Очистить", command=self.clear_logs, width=15).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Копировать", command=self.copy_logs, width=15).pack(side=tk.RIGHT, padx=2)

    def select_extract_input_file(self):
        filename = filedialog.askopenfilename(title="Выберите MSG файл",
                                              filetypes=[("MSG files", "*.msg"), ("All files", "*.*")])
        if filename:
            path = Path(filename)
            self.extract_input_path_var.set(str(path))
            if not self.extract_output_path_var.get():
                self.extract_output_path_var.set(str(path.parent / "extracted-txt"))

    def select_extract_input_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку с MSG файлами")
        if folder:
            self.extract_input_path_var.set(Path(folder))

    def select_extract_output_folder(self):
        folder = filedialog.askdirectory(title="Выберите выходную папку")
        if folder:
            self.extract_output_path_var.set(Path(folder))

    def select_build_input_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку с TXT файлами")
        if folder:
            self.build_input_path_var.set(Path(folder))

    def select_build_output_folder(self):
        folder = filedialog.askdirectory(title="Выберите выходную папку для MSG")
        if folder:
            self.build_output_path_var.set(Path(folder))
    
    def get_current_mapping_text(self):
        return (
            self.alph_text.get(1.0, tk.END).strip() + "\n" +
            self.ff01_text.get(1.0, tk.END).strip() + "\n" +
            self.ff02_text.get(1.0, tk.END).strip()
        )
    
    def validate_current_mapping(self):
        raw_text = self.get_current_mapping_text()
        lines = [line.strip() for line in raw_text.splitlines() if line.strip() and not line.strip().startswith('#')]
        errors = []
        alph_chars = []
        ff01_entries = []
        ff02_entries = []

        for line_num, line in enumerate(lines, start=1):
            parts = re.split(r'\s+', line)
            if len(parts) < 3:
                continue
            prefix = parts[0].upper()
            if prefix == "ALPH":
                if len(parts) >= 2:
                    alph_chars.append(parts[1])
            elif prefix in ("01FF", "02FF"):
                if len(parts) < 4:
                    errors.append(f"{prefix}: строка #{line_num} — недостаточно полей (ожидается минимум 4)")
                    continue
                hex_str = parts[1].upper()
                repl = parts[3]

                if not re.fullmatch(r'[0-9A-F]+', hex_str):
                    errors.append(f"{prefix}: строка #{line_num} — HEX не корректен: '{hex_str}'")
                    continue
                if len(hex_str) % 2 != 0:
                    errors.append(f"{prefix}: строка #{line_num} — HEX должен быть чётной длины: '{hex_str}'")
                    continue

                try:
                    mode = int(parts[2])
                    if mode not in (0, 1, 2, 3):
                        errors.append(f"{prefix}: строка #{line_num} — некорректный режим: {mode} (допустимо: 0-3)")
                except ValueError:
                    errors.append(f"{prefix}: строка #{line_num} — режим не является целым числом: '{parts[2]}'")
                    mode = -1

                if mode in (0, 1, 2, 3):
                    (ff01_entries if prefix == "01FF" else ff02_entries).append((hex_str, mode, repl))

        seen = set()
        for char in alph_chars:
            if char in seen:
                errors.append(f"ALPH: повторяющийся символ {char}")
            seen.add(char)

        seen_hex = set()
        seen_repl = set()
        for hex_str, mode, repl in ff01_entries:
            if hex_str in seen_hex:
                errors.append(f"01FF: дублирующийся HEX {hex_str}")
            if repl in seen_repl:
                errors.append(f"01FF: дублирующаяся замена {repl}")
            seen_hex.add(hex_str)
            seen_repl.add(repl)

        seen_hex = set()
        seen_repl = set()
        for hex_str, mode, repl in ff02_entries:
            if hex_str in seen_hex:
                errors.append(f"02FF: дублирующийся HEX {hex_str}")
            if repl in seen_repl:
                errors.append(f"02FF: дублирующаяся замена {repl}")
            seen_hex.add(hex_str)
            seen_repl.add(repl)

        if errors:
            return False, errors
        return True, None
    
    def start_parsing(self):
        input_path = self.extract_input_path_var.get().strip()
        if not input_path:
            messagebox.showerror("Ошибка", "Укажите входной файл или папку")
            return
        input_path = Path(input_path)
        if not input_path.exists():
            messagebox.showerror("Ошибка", "Указанный путь не существует")
            return
        is_valid, errors = self.validate_current_mapping()
        if not is_valid:
            for err in errors:
                self.log_message(f"[X МАППИНГА] {err}")
            self.log_message("Извлечение отменено из-за ошибок в маппинге.")
            return
        output_path = Path(self.extract_output_path_var.get().strip() or str(Path.cwd() / "extracted-txt"))
        if not output_path.exists():
            try:
                output_path.mkdir(parents=True)
                self.log_message(f"Создана выходная папка: {output_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать выходную папку:\n{str(e)}")
                return
        self.extract_status_var.set("Извлечение текста...")
        self.root.update()
        self.parse_msg_files(input_path, output_path)
        self.extract_status_var.set("")

    def parse_msg_files(self, input_path: Path, output_path: Path):
        try:
            files_to_process = []
            if input_path.is_file():
                if input_path.suffix.lower() == '.msg':
                    files_to_process = [input_path]
                else:
                    self.log_message(f"Файл не является .msg: {input_path}")
                    return
            elif input_path.is_dir():
                files_to_process = list(input_path.glob("*.msg"))
                self.log_message(f"Найдено {len(files_to_process)} MSG файлов")
            else:
                self.log_message(f"Неверный путь: {input_path}")
                return
            if not files_to_process:
                self.log_message("Не найдено MSG файлов для обработки")
                return
            total_files = len(files_to_process)
            parser = ChunkParser(mapping_data=self.get_current_mapping_text(),
                    debug=self.debug_output_var.get(), use_jis0208=self.use_jis0208_var.get())
            processed_files = 0
            for file_path in files_to_process:
                try:
                    self.parse_single_msg(file_path, output_path, parser)
                    processed_files += 1
                    self.extract_status_var.set(f"Обработано: {processed_files}/{total_files}")
                    self.root.update()
                except Exception as e:
                    self.log_message(f"Ошибка обработки {file_path.name}: {str(e)}")
                    traceback.print_exc()
            self.log_message(f"Извлечение завершено. Обработано файлов: {processed_files}/{total_files}")
            messagebox.showinfo("Завершено", f"Извлечение завершено.\nОбработано файлов: {processed_files}/{total_files}")
        except Exception as e:
            self.log_message(f"Критическая ошибка: {str(e)}")
            traceback.print_exc()
        finally:
            self.extract_status_var.set("")

    def parse_single_msg(self, file_path: Path, output_path: Path, parser: ChunkParser):
        try:
            with open(file_path, 'rb') as f:
                signature = f.read(4)
                if signature != b'MSG\x00':
                    self.log_message(f"Неверная сигнатура в {file_path.name}")
                    return
                file_size = struct.unpack('<I', f.read(4))[0]
                actual_file_size = file_path.stat().st_size
                if file_size != actual_file_size:
                    self.log_message(f"  [X] Несоответствие размера в {file_path.name}: {file_size} != {actual_file_size}")

                offsets = []
                while True:
                    raw = f.read(4)
                    if len(raw) < 4:
                        raise ValueError("Неожиданный конец файла при чтении смещений")
                    val = struct.unpack('<I', raw)[0]
                    if val == 0xFFFFFFFF:
                        break
                    offsets.append(val)
                if not offsets:
                    self.log_message(f"Таблица смещений в {file_path.name} пуста")
                    return
                if self.log_showall_var.get():
                    self.log_message(f" {file_path.name} | {file_size} байт | {len(offsets)} чанков")

                txt_dir = output_path / Path(file_path).stem
                txt_dir.mkdir(exist_ok=True)
                for i in range(len(offsets)):
                    start = offsets[i]
                    end = file_size if i == len(offsets) - 1 else offsets[i + 1]
                    if end <= start:
                        continue
                    f.seek(start)
                    data = f.read(end - start)
                    sig = data[:2].hex().upper()
                    txt_name = f"{i:04d}.txt"
                    txt_path = txt_dir / txt_name
                    if sig == "01FF":
                        txt_content = parser.parse_01ff(data)
                    elif sig == "02FF":
                        txt_content = parser.parse_02ff(data)
                    else:
                        continue
                    txt_path.write_text(txt_content, encoding='utf-8')
                    if self.log_showall_var.get():
                        self.log_message(f"  Сохранён: {txt_name}")
                self.log_message(f" {len(offsets)} TXT файлов сохранено в: {txt_dir}")
        except Exception as e:
            self.log_message(f"Ошибка при обработке {file_path}: {str(e)}")
            raise

    def start_building(self):
        input_path = self.build_input_path_var.get().strip()
        if not input_path:
            messagebox.showerror("Ошибка", "Укажите папку с TXT файлами")
            return
        input_path = Path(input_path)
        if not input_path.exists():
            messagebox.showerror("Ошибка", "Указанная папка не существует")
            return
        is_valid, errors = self.validate_current_mapping()
        if not is_valid:
            for err in errors:
                self.log_message(f"[X МАППИНГА] {err}")
            self.log_message("Сборка отменена из-за ошибок в маппинге.")
            return
        output_path = Path(self.build_output_path_var.get().strip() or str(Path.cwd() / "builded-msg"))
        if not output_path.exists():
            try:
                output_path.mkdir(parents=True)
                self.log_message(f"Создана выходная папка: {output_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать выходную папку:\n{str(e)}")
                return
        self.build_status_var.set("Сборка...")
        self.root.update()
        try:
            self.build_msg_files(input_path, output_path)
            self.build_status_var.set("")
        except Exception as e:
            self.log_message(f"Ошибка сборки: {str(e)}")
            traceback.print_exc()
            self.build_status_var.set("Ошибка")

    def build_msg_files(self, input_path: Path, output_path: Path):
        subfolders = [f for f in input_path.iterdir() if f.is_dir()]
        if not subfolders:
            self.log_message("В указанной папке нет подпапок с TXT файлами")
            return
        self.log_message(f"Найдено {len(subfolders)} подпапок для сборки")
        total_folders = len(subfolders)
        parser = ChunkParser(
            mapping_data=self.get_current_mapping_text(),
            debug=self.debug_output_var.get(),
            use_jis0208=self.use_jis0208_var.get()
        )
        processed_folders = 0
        for folder in subfolders:
            try:
                self.build_single_msg(folder, output_path, parser)
                processed_folders += 1
                self.build_status_var.set(f"Обработано: {processed_folders}/{total_folders}")
                self.root.update()
            except Exception as e:
                self.log_message(f"Ошибка сборки из {folder.name}: {str(e)}")
                traceback.print_exc()
        self.log_message(f"Сборка завершена. Обработано папок: {processed_folders}/{total_folders}")
        messagebox.showinfo("Завершено", f"Сборка завершена.\nОбработано папок: {processed_folders}/{total_folders}")

    def build_single_msg(self, folder: Path, output_path: Path, parser: ChunkParser):
        if self.log_showall_var.get():
            self.log_message(f"Сборка MSG из папки: {folder.name}")
        txt_files = sorted(folder.glob("*.txt"))
        if not txt_files:
            self.log_message(f"В папке {folder.name} нет TXT файлов")
            return
        txt_cache = {}
        chunks_data = []
        valid_txt_files = []

        for txt_file in txt_files:
            try:
                content = txt_file.read_text(encoding='utf-8')
            except Exception as e:
                self.log_message(f"[X] Не удалось прочитать {txt_file.name}: {e}")
                continue
            txt_cache[txt_file] = content
            sig_line = next((l for l in content.splitlines() if l.startswith("SIGNATURE: ")), "")
            if "01FF" in sig_line:
                chunk_data = parser.build_01ff(content)
            elif "02FF" in sig_line:
                chunk_data = parser.build_02ff(content)
            else:
                self.log_message(f"[!] Пропущен файл без корректной сигнатуры: {txt_file.name}")
                continue
            chunks_data.append(chunk_data)
            valid_txt_files.append(txt_file)
        if not valid_txt_files:
            self.log_message(f"Нет валидных TXT-файлов в {folder.name} — пропуск")
            return
        output_file = output_path / f"{folder.name}.msg"
        try:
            with open(output_file, 'wb') as f:
                f.write(b'MSG\x00')
                f.write(struct.pack('<I', 0))
                offset_table_start = f.tell()
                current_offset = offset_table_start + (len(chunks_data) + 1) * 4  # +1 для 0xFFFFFFFF
                for chunk in chunks_data:
                    f.write(struct.pack('<I', current_offset))
                    current_offset += len(chunk)
                f.write(struct.pack('<I', 0xFFFFFFFF))
                for chunk in chunks_data:
                    f.write(chunk)
                final_size = f.tell()
                f.seek(4)
                f.write(struct.pack('<I', final_size))
            self.log_message(f"Собран MSG файл: {output_file.name} ({final_size} байт)")
        except Exception as e:
            self.log_message(f"[X] Не удалось записать {output_file.name}: {e}")
            raise

    def log_message(self, message):
        log_entry = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        self.log_text.insert(tk.END, log_entry + "\n")
        self.log_text.see(tk.END)
        self.root.update()

    def clear_logs(self):
        self.log_text.delete(1.0, tk.END)

    def copy_logs(self):
        try:
            text = self.log_text.get(1.0, tk.END)
            if text.strip():
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                self.log_message("Логи скопированы в буфер обмена")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скопировать логи: {str(e)}")

    def save_config(self):
        try:
            geometry = self.root.geometry()
            config = {
                'version': MAIN_VERSION,
                'extract_input_path': self.extract_input_path_var.get(),
                'extract_output_path': self.extract_output_path_var.get(),
                'build_input_path': self.build_input_path_var.get(),
                'build_output_path': self.build_output_path_var.get(),
                'log_showall': self.log_showall_var.get(),
                'auto_save': self.auto_save_var.get(),
                'save_window_geometry': self.save_window_geometry_var.get(),
                'debug_output': self.debug_output_var.get(),
                'use_jis0208': self.use_jis0208_var.get(),
                'window_geometry': geometry if self.save_window_geometry_var.get() else self.initial_geometry,
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.log_message(f"Конфигурация сохранена в {self.config_path}")
        except Exception as e:
            self.log_message(f"Ошибка сохранения конфигурации: {str(e)}")

    def load_config(self):
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.extract_input_path_var.set(config.get('extract_input_path', ''))
                self.extract_output_path_var.set(config.get('extract_output_path', str(Path.cwd() / "extracted-txt")))
                self.build_input_path_var.set(config.get('build_input_path', ''))
                self.build_output_path_var.set(config.get('build_output_path', str(Path.cwd() / "builded-msg")))
                self.log_showall_var.set(config.get('log_showall', False))
                self.auto_save_var.set(config.get('auto_save', True))
                self.save_window_geometry_var.set(config.get('save_window_geometry', True))
                self.debug_output_var.set(config.get('debug_output', False))
                self.use_jis0208_var.set(config.get('use_jis0208', True))
                geometry = config.get('window_geometry', self.initial_geometry)
                if self.save_window_geometry_var.get() and geometry:
                    self.root.geometry(geometry)
                self.log_message(f"Конфигурация загружена")
            else:
                self.log_message("Конфигурационный файл не найден")
        except Exception as e:
            self.log_message(f"Ошибка загрузки конфигурации: {str(e)}")

    def reset_all_settings(self):
        if messagebox.askyesno("Подтверждение", "Сбросить ВСЕ настройки к значениям по умолчанию?"):
            self.extract_input_path_var.set("")
            self.extract_output_path_var.set(str(Path.cwd() / "extracted-txt"))
            self.build_input_path_var.set("")
            self.build_output_path_var.set(str(Path.cwd() / "builded-msg"))
            self.log_showall_var.set(False)
            self.auto_save_var.set(True)
            self.save_window_geometry_var.set(True)
            self.debug_output_var.set(False)
            self.use_jis0208_var.set(True)
            self.root.geometry("900x600")
            if self.config_path.exists():
                try:
                    self.config_path.unlink()
                    self.log_message("Конфигурационный файл удалён")
                except Exception as e:
                    self.log_message(f"Не удалось удалить конфиг: {str(e)}")
            self.log_message("Все настройки сброшены")

    def on_closing(self):
        if self.mapping_modified:
            result = messagebox.askyesnocancel(
                "Несохранённые изменения",
                "В маппингах есть несохранённые изменения. Сохранить перед выходом?"
            )
            if result is True:
                self.save_mapping_section("ALPH", self.alph_text)
                self.save_mapping_section("01FF", self.ff01_text)
                self.save_mapping_section("02FF", self.ff02_text)
            elif result is None:
                return
        if self.auto_save_var.get():
            self.save_config()
        self.root.destroy()


def main():
    root = tk.Tk()
    root.title(MAIN_TITLE)
    try:
        app = FM4MSGTool(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Критическая ошибка", f"Не удалось запустить программу:\n{str(e)}\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()