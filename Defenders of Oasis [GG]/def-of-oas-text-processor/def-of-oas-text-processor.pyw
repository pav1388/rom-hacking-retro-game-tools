# python 3.4+

import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys
import string
import re
import random

MAIN_VERSION = "0.10.1"
MAIN_BG_COLOR = "#BEBEBE"
CONSOLE_BG_COLOR = "#BBBBBB"

WINDOW_SIZE = 8192
LENGTHS = (11,10,9,8,7,6,5,4) # оригинальный алгоритм сжатия
LENGTHS_EFFICIENCY = (11,10,9,8,7,6,5) # более эффективный пропуск коротких фрагментов
LEN_MAP_ENCODE = {4:0, 5:2, 6:4, 7:6, 8:8, 9:10, 10:12, 11:14}
MULT_MAP_ENCODE = {31:0, 30:1, 29:2, 28:3, 27:4, 26:5, 25:6, 24:7, 23:8, 
                   22:9, 21:10, 20:11, 19:12, 18:13, 17:14, 16:15,
                   15:0, 14:1, 13:2, 12:3, 11:4, 10:5, 9:6, 8:7,
                   7:8, 6:9, 5:10, 4:11, 3:12, 2:13, 1:14, 0:15}
LEN_MAP_DECODE = {0:4, 1:4, 2:5, 3:5, 4:6, 5:6, 6:7, 7:7, 8:8,
                    9:8, 10:9, 11:9, 12:10, 13:10, 14:11, 15:11}
MULT_MAP_DECODE =  {0:15, 1:14, 2:13, 3:12, 4:11, 5:10, 6:9, 7:8,
                    8:7, 9:6, 10:5, 11:4, 12:3, 13:2, 14:1, 15:0}

class TextProcessor:
    def __init__(self, root):
        self.root = root
        root.configure(bg=MAIN_BG_COLOR)
        root.title("Defenders of Oasis [GG] - Text processor v" + MAIN_VERSION + " by pav13")
        root.geometry("900x550")
        
        btn_frame1 = tk.Frame(root, bg=MAIN_BG_COLOR)
        btn_frame1.pack(pady=5, anchor='w', padx=10, fill=tk.X)
        
        self.decode_bin_btn = tk.Button(btn_frame1, text="Распаковать\nв бинарный файл",
            command=lambda: self.decode_file(as_text=False), width=20, height=3,
            bg="#3A92CC", fg="black", activebackground="#356A8D", activeforeground="black",
            font=(None, 10, "bold"))
        self.decode_bin_btn.pack(side=tk.LEFT, padx=5)

        self.encode_bin_btn = tk.Button(btn_frame1, text="Сжать файл",
                    command=self.encode_file, width=20, height=3,
                    bg="#f1c40f", fg="black", activebackground="#d4ac0d", activeforeground="black",
                    font=(None, 10, "bold"))
        self.encode_bin_btn.pack(side=tk.LEFT, padx=5)
        
        self.compression_plus_var = tk.IntVar(value=1)
        self.compression_plus_check = tk.Checkbutton(btn_frame1, text="Сжатие ++",
                    variable=self.compression_plus_var, font=(None, 10, "bold"), 
                    bg=MAIN_BG_COLOR, activebackground=MAIN_BG_COLOR)
        self.compression_plus_check.pack(side=tk.LEFT)
        
        self.exit_btn = tk.Button(btn_frame1, text="Выход",
                    command=self.root.destroy, width=12, height=3,
                    bg="#ff6b6b", fg="black", activebackground="#ee5253", activeforeground="black",
                    font=(None, 10, "bold"))
        self.exit_btn.pack(side=tk.RIGHT, padx=5)

        btn_frame2 = tk.Frame(root, bg=MAIN_BG_COLOR)
        btn_frame2.pack(pady=5, anchor='w', padx=10, fill=tk.X)

        self.decode_txt_btn = tk.Button(btn_frame2, text="Распаковать\nв текстовый файл",
                    command=lambda: self.decode_file(as_text=True), width=20, height=3,
                    bg="#5dade2", fg="black", activebackground="#3498db", activeforeground="black",
                    font=(None, 10, "bold"))
        self.decode_txt_btn.pack(side=tk.LEFT, padx=5)

        self.best_compress_btn = tk.Button(btn_frame2, text="Эвристическое\nсжатие",
                    command=self.find_best_compression, width=20, height=3,
                    bg="#f7dc6f", fg="black", activebackground="#f4d03f", activeforeground="black",
                    font=(None, 10, "bold"))
        self.best_compress_btn.pack(side=tk.LEFT, padx=5)
        
        self.info_label = tk.Label(btn_frame2, text="", bg=MAIN_BG_COLOR,
                    fg="#A40026", font=(None, 11, "bold"))
        self.info_label.pack(side=tk.LEFT, padx=(10, 5))

        self.clear_logs_btn = tk.Button(btn_frame2, text="Очистить\nлоги",
                    command=self.clear_logs, width=12, height=3,
                    bg="#abebc6", fg="black", activebackground="#82e0aa", activeforeground="black",
                    font=(None, 10, "bold"))
        self.clear_logs_btn.pack(side=tk.RIGHT, padx=5)
        
        controls_frame = tk.Frame(root, bg=MAIN_BG_COLOR)
        controls_frame.pack(pady=5, anchor='w', padx=10, fill=tk.X)
        
        self.debug_var = tk.IntVar(value=0)
        self.debug_check = tk.Checkbutton(controls_frame, text="Вывод подробных логов",
                    variable=self.debug_var, font=(None, 10, "bold"), 
                    bg=MAIN_BG_COLOR, activebackground=MAIN_BG_COLOR)
        self.debug_check.pack(side=tk.LEFT)
        
        self.depth_var = tk.StringVar(value="100")
        self.depth_spinbox = tk.Spinbox(controls_frame, from_=10, to=10000, width=6, 
                                           font=(None, 10, "bold"), textvariable=self.depth_var)
        self.depth_spinbox.pack(side=tk.LEFT, padx=(30, 5))
        
        self.depth_label = tk.Label(controls_frame, text="Глубина эвристики (больше = лучше, но дольше)", 
                                            bg=MAIN_BG_COLOR, font=(None, 10, "bold"))
        self.depth_label.pack(side=tk.LEFT, padx=(0, 10))
        
        text_frame = tk.Frame(root, bg=MAIN_BG_COLOR)
        text_frame.pack(pady=5, fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(text_frame, wrap=tk.WORD, height=10, bg=CONSOLE_BG_COLOR, 
                                font=("Courier", 10, "bold"))
        scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.decoded_data = None
        self.original_filename = None
        self.original_compressed_data = None
        self.error_count = 0
        self.warning_count = 0
        self.marker_count = 0
        self.log_to_console("   ________               _____                        .___")
        self.log_to_console("   \______ \     ____   _/ ____\   ____     ____     __| _/   ____   _______    ______")
        self.log_to_console("    |    |  \  _/ __ \  \   __\  _/ __ \   /    \   / __ |  _/ __ \  \_  __ \  /  ___/")
        self.log_to_console("    |    `   \ \  ___/   |  |    \  ___/  |   |  \ / /_/ |  \  ___/   |  | \/  \___ \ ")
        self.log_to_console("   /_______  /  \___  >  |__|     \___  > |___|  / \____ |   \___  >  |__|    /____  >")
        self.log_to_console("           \/       \/                \/       \/       \/       \/                \/")
        self.log_to_console("                      _____      ________                      .__")
        self.log_to_console("             ____   _/ ____\     \_____  \   _____      ______ |__|   ______")
        self.log_to_console("            /  _ \  \   __\       /   |   \  \__  \    /  ___/ |  |  /  ___/")
        self.log_to_console("           (  <_> )  |  |        /    |    \  / __ \_  \___ \  |  |  \___ \ ")
        self.log_to_console("            \____/   |__|        \_______  / (____  / /____  > |__| /____  >")
        self.log_to_console("                                         \/       \/       \/            \/")
        self.log_to_console("                                                                             1992:2026\n")
    
    def clear_logs(self):
        self.log_text.delete(1.0, tk.END)
    
    def log_to_console(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def log_info(self, msg):
        formatted_msg = "[I] " + msg
        print(formatted_msg)
        self.log_to_console(formatted_msg)
    
    def log_warning(self, msg):
        self.warning_count += 1
        formatted_msg = "[!!] " + msg
        print(formatted_msg)
        self.log_to_console(formatted_msg)
    
    def log_error(self, msg):
        self.error_count += 1
        formatted_msg = "[ERR] " + msg
        print(formatted_msg)
        self.log_to_console(formatted_msg)
    
    def log_debug(self, msg):
        if self.debug_var.get():
            formatted_msg = "[D] " + msg
            print(formatted_msg)
            self.log_to_console(formatted_msg)
    
    def process_special_bytes(self, data):
        """Преобразует непечатные символы в формат [XX] для отображения"""
        self.log_debug("process_special_bytes: начало обработки")
        # перенос строки после этих байтов для визуального разграничения
        line_break_bytes = [0x00, 0x02, 0x03]
        
        result = bytearray()
        
        for b in data:
            if 32 <= b <= 126:
                result.append(b)
            else:
                hex_str = '[' + format(b, '02X') + ']'
                result.extend(hex_str.encode('ascii'))
            
            if b in line_break_bytes:
                result.append(10)
        
        self.log_debug("process_special_bytes: завершено")
        return bytes(result)
    
    def parse_special_bytes(self, text):
        """Парсит текст с форматом [XX] обратно в бинарные байты"""
        self.log_debug("parse_special_bytes: начало парсинга")
        result = bytearray()
        i = 0
        
        text = text.replace('\n', '').replace('\r', '')
        text_len = len(text)
        
        while i < text_len:
            if text[i] == '[' and i + 3 < text_len:
                hex_str = text[i+1:i+3]
                if text[i+3] == ']' and all(c in '0123456789ABCDEFabcdef' for c in hex_str):
                    byte_val = int(hex_str, 16)
                    result.append(byte_val)
                    i += 4
                    continue
            
            result.append(ord(text[i]))
            i += 1
        
        self.log_debug("parse_special_bytes: завершено, обработано байт: " + str(len(result)))
        return bytes(result)
    
    def decode_data(self, data):
        """Декодирует сжатые данные"""
        self.log_info("Начало декодирования")
        self.log_info("Размер входных данных: " + str(len(data)) + " байт")
        self.log_info("Подождите ...")
        self.log_debug(" number | address | link    | length | offset | multiplier | src_address | text")

        
        result = bytearray()
        i = 0
        data_len = len(data)
        markers = 0
        errors = 0
        is_debug = bool(self.debug_var.get())
        len_map = LEN_MAP_DECODE
        mult_map = MULT_MAP_DECODE
        
        res_append = result.append
        res_extend = result.extend

        while i < data_len:
            if data[i] == 0xFF:
                if i + 2 < data_len:
                    b1 = data[i+1]
                    b2 = data[i+2]
                    
                    if b1 == 0xFF and b2 == 0xFF:
                        self.log_debug("decode_data: пропуск FFFFFF @" + format(i, '06X'))
                        res_append(0xFF)
                        res_append(0xFF)
                        res_append(0xFF)
                        i += 3
                        continue
                    
                    markers += 1
                    high = (b2 >> 4) & 0x0F
                    low = b2 & 0x0F
                    length = len_map[high]
                    
                    if high & 1:
                        multiplier = mult_map[low]
                    else:
                        multiplier = mult_map[low] + 16
                    
                    offset = (multiplier << 8) + (b1 ^ 0xFF) + 1
                    src_pos = i - offset
                    
                    if src_pos < 0 or src_pos + length > data_len:
                        self.log_warning("Одиночный FF @" + format(i, '06X'))
                        res_append(0xFF)
                        i += 1
                        errors += 1
                        continue
                    
                    res_extend(data[src_pos:src_pos+length])
                    if is_debug:
                        self.log_debug(" #{:<8}x{:<9}xFF{:02X}{:02X}   {:<9}{:<8} {:<13}x{:06X}       '{}'".format(markers, format(i, '06X'), b1, b2, length, offset, multiplier, src_pos, ''.join(chr(b) if 32 <= b <= 126 else ("[" + format(b, '02X') + "]") for b in data[src_pos:src_pos+length])))
                    i += 3
                else:
                    self.log_warning("Одиночный FF @" + format(i, '06X'))
                    res_append(0xFF)
                    i += 1
            else:
                res_append(data[i])
                i += 1
        
        self.marker_count = markers
        self.error_count = errors
        self.log_info("Декодировано: ссылок=" + str(markers) + ", ошибок=" + str(errors))
        self.log_info("Размер выходных данных: " + str(len(result)) + " байт")
        return bytes(result)
    
    def encode_data(self, data, skip_pattern=None):
        """Сжимает данные с возможностью пропуска указанных ссылок по их номеру"""
        compression_plus = bool(self.compression_plus_var.get())
        
        if skip_pattern is None:
            skip_pattern = set()
        
        if not skip_pattern:
            self.log_info("Начало кодирования" + (" (сжатие ++)" if compression_plus else ""))
            self.log_info("Размер исходных данных: " + str(len(data)) + " байт")
            self.log_info("Подождите ...")
            self.log_debug(" number | address | link      | length | offset | multiplier | src_address | text")
        
        result = bytearray()
        i = 0
        data_len = len(data)
        markers = 0
        current_marker_number = 0
        skipped_markers = 0
        window_size = WINDOW_SIZE

        res_append = result.append
        res_extend = result.extend
        is_debug = bool(self.debug_var.get())
        log_debug = self.log_debug
        
        if compression_plus:
            lengths = LENGTHS_EFFICIENCY
        else:
            lengths = LENGTHS
            
        min_length = min(lengths)
        hash_table = {}
        src_pos_mapping = []
        len_map = LEN_MAP_ENCODE
        mult_map = MULT_MAP_ENCODE
        
        while i < data_len:
            max_length = 0
            best_offset = 0
            best_src_pos = 0
            res_len = len(result)
            start_pos = max(0, res_len - window_size)

            for length in lengths:
                if i + length > data_len:
                    continue
		
                if 0x00 in data[i:i + length - 1]:
                    continue 
                
                key = (data[i] << 8) | data[i+1]
                candidates = hash_table.get(key, [])

                for idx in range(len(candidates)-1, -1, -1):
                    pos = candidates[idx]
                    
                    if pos < start_pos:
                        continue
                    match = True
                    for k in range(length):
                        if pos + k >= res_len or result[pos + k] != data[i + k]:
                            match = False
                            break
                    if match:
                        max_length = length
                        best_offset = res_len - pos
                        
                        if is_debug:
                            best_src_pos = src_pos_mapping[pos] if pos < len(src_pos_mapping) else 0
                        
                        break
                if max_length > 0:
                    break

            length = max_length
            offset = best_offset

            if length >= min_length:
                current_marker_number += 1
                
                # Проверяем, нужно ли пропустить эту ссылку
                if current_marker_number in skip_pattern:
                    # Вместо ссылки записываем сырые данные
                    for j in range(length):
                        res_append(data[i + j])
                        if is_debug:
                            src_pos_mapping.append(i + j)
                        
                        # Обновляем хеш-таблицу для сырых байтов
                        if res_len + j + 1 < len(result) + 1:
                            key = tuple(result[res_len + j: res_len + j + 2])
                            hash_table.setdefault(key, []).append(res_len + j)
                    
                    i += length
                    skipped_markers += 1
                    continue
                
                # Ленивый алгоритм
                if compression_plus and i + 1 < data_len:
                    # Проверяем, не будет ли следующая позиция лучше
                    next_len, next_offset, next_src = self._find_best_match(
                        data, i+1, result, lengths, hash_table, src_pos_mapping, window_size
                    )
                    
                    if next_len > length:
                        # Текущий байт лучше вывести как есть, а ссылку сделать со следующей позиции
                        res_append(data[i])
                        if is_debug:
                            src_pos_mapping.append(i)
                        
                        # Обновляем хеш-таблицу
                        if i + 1 < data_len:
                            key = (data[i] << 8) | data[i+1]
                            hash_table.setdefault(key, []).append(res_len)
                        
                        i += 1
                        current_marker_number -= 1
                        continue
                
                # Создает ссылку на основе смещения и длины
                temp_offset = offset - 1
                multiplier = temp_offset >> 8
                ref_bytes = bytes([0xFF, (0xFF - (temp_offset & 0xFF)) & 0xFF, 
                   ((len_map[length] + (multiplier < 16)) << 4) | mult_map[multiplier]])
                
                res_extend(ref_bytes)
                markers += 1
                
                if is_debug:
                    for j in range(length):
                        src_pos_mapping.append(i + j)
                    
                    raw_fragment = data[i:i+length]
                    raw_text = []
                    
                    for b in raw_fragment:
                        if 32 <= b <= 126:
                            raw_text.append(chr(b))
                        else:
                            raw_text.append('[' + '{:02X}'.format(b) + ']')
                    
                    self.log_debug(" #{:<8}x{:<9}x{}     {:<9}{:<8} {:<13}x{:06X}       '{}'".format(markers, format(i, '06X'), "".join(format(x, '02X') for x in ref_bytes), length, offset, multiplier, best_src_pos, ''.join(raw_text)))
                
                i += length
                    
                for j in range(length):
                    if res_len + j + 1 < len(result):
                        key = tuple(result[res_len + j: res_len + j + 2])
                        hash_table.setdefault(key, []).append(res_len + j)
                continue

            res_append(data[i])
            
            if is_debug:
                src_pos_mapping.append(i)
            
            if i + 1 < data_len:
                key = (data[i] << 8) | data[i+1]
                hash_table.setdefault(key, []).append(res_len)
            i += 1

        self.marker_count = markers
        
        if not skip_pattern:
            self.log_info("Сжатие завершено. Размер: {} байт, ссылок: {}, пропущено ссылок: {}".format(len(result), markers, skipped_markers))
        
        return bytes(result)
    
    def _find_best_match(self, data, i, result, lengths, hash_table, src_pos_mapping, window_size):
        """Метод для поиска лучшего совпадения"""
        max_length = 0
        best_offset = 0
        best_src_pos = 0
        res_len = len(result)
        start_pos = max(0, res_len - window_size)
        
        for length in lengths:
            if i + length > len(data):
                continue
            
            if 0x00 in data[i:i + length - 1]:
                continue
            
            key = (data[i] << 8) | data[i+1]
            candidates = hash_table.get(key, [])
            
            for idx in range(len(candidates)-1, -1, -1):
                pos = candidates[idx]
                
                if pos < start_pos:
                    continue
                
                match = True
                for k in range(length):
                    if pos + k >= res_len or result[pos + k] != data[i + k]:
                        match = False
                        break
                
                if match:
                    max_length = length
                    best_offset = res_len - pos
                    if pos < len(src_pos_mapping):
                        best_src_pos = src_pos_mapping[pos]
                    break
            
            if max_length > 0:
                break
        
        return max_length, best_offset, best_src_pos
    
    def find_best_compression(self):
        self.log_info("=== ЭВРИСТИЧЕСКИЙ ПОДБОР ЛУЧШЕГО СЖАТИЯ ===")
        
        try:
            depth = int(self.depth_spinbox.get())
            if depth < 10:
                depth = 10
            elif depth > 10000:
                depth = 10000
                self.log_warning("Количество попыток ограничено 10000")
        except ValueError:
            self.log_error("Неверное значение. Используется 100 ссылок")
            depth = 100
        
        self.log_info("Глубина поиска: " + str(depth) + " ссылок")
        
        filename = filedialog.askopenfilename(title="Выберите файл для сжатия", 
                                               filetypes=[("All files", "*.*")])
        if not filename:
            self.log_info("Операция отменена пользователем")
            return
        
        self.info_label.configure(text="Интерфейс может\nне отвечать,\nно программа работает.")
        file_size = os.path.getsize(filename)
        self.log_info("Файл: " + os.path.basename(filename) + 
                     " (" + str(file_size) + " bytes)")
        
        is_text = filename.lower().endswith('.txt')
        
        try:
            if is_text:
                with open(filename, 'r', encoding='utf-8') as f:
                    text = f.read()
                data = self.parse_special_bytes(text)
                self.log_info("После парсинга спецбайтов: " + str(len(data)) + " байт")
            else:
                with open(filename, 'rb') as f:
                    data = f.read()
            
            old_debug = self.debug_var.get()
            self.debug_var.set(0)
            
            self.log_info("Шаг 1: Эталонное сжатие...")
            compressed_default = self.encode_data(data, skip_pattern=set())
            default_size = len(compressed_default)
            best_size = default_size
            best_data = compressed_default
            best_skips = set()
            
            self.log_info("  Эталонный размер: " + str(default_size) + " байт")
            self.log_info("Шаг 2: Эвристический поиск...")
            
            all_references = self.get_all_references(data)
            
            if not all_references:
                self.log_warning("Ссылки не найдены, улучшение невозможно")
                self.info_label.configure(text="")
                messagebox.showinfo("Результат", "Ссылки не найдены, улучшение невозможно")
                return
            
            current_skips = set()
            current_data = compressed_default
            
            for ref_num in sorted(all_references.keys())[:depth]:
                test_skips = current_skips | {ref_num}
                test_compressed = self.encode_data(data, skip_pattern=test_skips)
                test_size = len(test_compressed)
                
                if test_size < best_size:
                    best_size = test_size
                    best_data = test_compressed
                    best_skips = test_skips
                    current_skips = test_skips
                    improvement = default_size - test_size
                    self.log_info("  [+] #" + str(ref_num) + "/" + str(depth) + ": " + str(improvement) + 
                                    " байт (всего " + str(len(current_skips)) + " пропущено)")
                else:
                    if len(current_skips) > 0:
                        temp_skips = set(list(current_skips)[:-1]) | {ref_num}
                        test_compressed = self.encode_data(data, skip_pattern=temp_skips)
                        test_size = len(test_compressed)
                        
                        if test_size < best_size:
                            best_size = test_size
                            best_data = test_compressed
                            best_skips = temp_skips
                            current_skips = temp_skips
                            improvement = default_size - test_size
                            self.log_info("  [~] Замена #" + str(ref_num) + ": " + str(improvement) + " байт")
            
            self.log_info("Шаг 3: Оптимизация...")
            optimized = False
            for ref_num in list(best_skips):
                test_skips = best_skips - {ref_num}
                test_compressed = self.encode_data(data, skip_pattern=test_skips)
                test_size = len(test_compressed)
                
                if test_size <= best_size:
                    best_size = test_size
                    best_data = test_compressed
                    best_skips = test_skips
                    optimized = True
                    self.log_info("  [-] Удален пропуск #" + str(ref_num) + ", размер не изменился")
            
            self.debug_var.set(old_debug)
            self.info_label.configure(text="")
            
            if best_data:
                out_file = filename + "-best-compressed.bin"
                with open(out_file, 'wb') as f:
                    f.write(best_data)
                
                improvement = default_size - best_size
                compression_ratio = (1 - best_size / file_size) * 100
                default_ratio = (1 - default_size / file_size) * 100
                
                result_msg = "ЭВРИСТИЧЕСКИЙ АЛГОРИТМ ЗАВЕРШЕН\n\n"
                result_msg += "РЕЗУЛЬТАТ:\n"
                result_msg += "  Размер: " + str(best_size) + " байт\n"
                result_msg += "  Коэф. сжатия: " + format(compression_ratio, '.1f') + "%\n"
                result_msg += "  Улучшение: " + str(improvement) + " байт"
                if default_size > 0:
                    result_msg += " (" + format((1 - best_size/default_size)*100, '.1f') + "%)\n"
                result_msg += "  Пропущено ссылок: " + str(len(best_skips)) + "\n"
                if best_skips:
                    result_msg += "  Номера: " + str(sorted(best_skips)) + "\n"
                result_msg += "\nЭТАЛОН (без пропуска):\n"
                result_msg += "  Размер: " + str(default_size) + " байт\n"
                result_msg += "  Коэф. сжатия: " + format(default_ratio, '.1f') + "%\n\n"
                result_msg += "Сохранено: " + out_file
                
                self.log_info(result_msg)
                messagebox.showinfo("Подбор сжатия завершен", result_msg)
            else:
                self.log_error("Не удалось получить сжатые данные")
                messagebox.showerror("Ошибка", "Не удалось получить сжатые данные")
            
        except Exception as e:
            self.info_label.configure(text="")
            self.log_error("Ошибка: " + str(e))
            messagebox.showerror("Ошибка", str(e))

    def get_all_references(self, data):
        """Получает словарь со всеми ссылками и их длинами"""
        self.log_info("Анализ ссылок в данных...")
        
        references = {}
        window_size = WINDOW_SIZE
        len_map = LEN_MAP_ENCODE
        mult_map = MULT_MAP_ENCODE
        compression_plus = bool(self.compression_plus_var.get())
        lengths = LENGTHS_EFFICIENCY if compression_plus else LENGTHS
        
        result = bytearray()
        i = 0
        data_len = len(data)
        ref_counter = 0
        
        hash_table = {}
        min_length = min(lengths)
        
        while i < data_len:
            max_length = 0
            best_offset = 0
            res_len = len(result)
            start_pos = max(0, res_len - window_size)
            
            # Ищем лучшую ссылку
            for length in lengths:
                if i + length > data_len:
                    continue
                
                if 0x00 in data[i:i + length - 1]:
                    continue
                
                key = (data[i] << 8) | data[i+1]
                candidates = hash_table.get(key, [])
                
                for pos in reversed(candidates):
                    if pos < start_pos:
                        continue
                    
                    match = True
                    for k in range(length):
                        if pos + k >= res_len or result[pos + k] != data[i + k]:
                            match = False
                            break
                    
                    if match:
                        max_length = length
                        best_offset = res_len - pos
                        break
                
                if max_length > 0:
                    break
            
            if max_length >= min_length:
                ref_counter += 1
                references[ref_counter] = {
                    'position': i,
                    'length': max_length,
                    'offset': best_offset
                }
                
                # Добавляем ссылку в результат
                temp_offset = best_offset - 1
                multiplier = temp_offset >> 8
                
                
                ref_bytes = bytes([0xFF, (0xFF - (temp_offset & 0xFF)) & 0xFF, 
                                   ((len_map[max_length] + (multiplier < 16)) << 4) | mult_map[multiplier]])
                
                result.extend(ref_bytes)
                
                # Обновляем хеш-таблицу
                for j in range(max_length):
                    if res_len + j + 1 < len(result):
                        key = tuple(result[res_len + j: res_len + j + 2])
                        hash_table.setdefault(key, []).append(res_len + j)
                
                i += max_length
            else:
                result.append(data[i])
                
                # Обновляем хеш-таблицу для сырого байта
                if i + 1 < data_len:
                    key = (data[i] << 8) | data[i+1]
                    hash_table.setdefault(key, []).append(res_len)
                
                i += 1
        
        self.log_info("Найдено ссылок: " + str(len(references)))
        return references
    
    def decode_file(self, as_text=False):
        """Метод распаковки"""
        mode_str = "В ТЕКСТОВЫЙ ФАЙЛ" if as_text else "В БИНАРНЫЙ ФАЙЛ"
        self.log_info("=== РАСПАКОВКА " + mode_str + " ===")
        
        filename = filedialog.askopenfilename(title="Выберите сжатый файл")
        if not filename:
            self.log_info("Операция отменена пользователем")
            return
        
        self.info_label.configure(text="Интерфейс может\nне отвечать,\nно программа работает.")
        
        self.error_count = 0
        self.warning_count = 0
        self.marker_count = 0
        
        file_size = os.path.getsize(filename)
        self.log_info("Файл: " + os.path.basename(filename) + 
                     " (" + str(file_size) + " bytes)")
        
        try:
            with open(filename, 'rb') as f:
                self.original_compressed_data = f.read()
            self.log_debug("Данные прочитаны успешно")
            
            decoded_raw = self.decode_data(self.original_compressed_data)
            
            if as_text:
                self.decoded_data = self.process_special_bytes(decoded_raw)
                out_file = filename + "-decompressed.txt"
            else:
                self.decoded_data = decoded_raw
                out_file = filename + "-decompressed.bin"
            
            self.info_label.configure(text="")
            
            if self.decoded_data:
                with open(out_file, 'wb') as f:
                    f.write(self.decoded_data)
                
                self.log_info("Готово! Файл декодирован и сохранён")
                result_msg = "Размер файла: " + str(len(self.decoded_data)) + " байт\n"
                result_msg += "Ссылок: " + str(self.marker_count) + "\n"
                result_msg += "Ошибок: " + str(self.error_count) + "\n"
                result_msg += "Предупреждений: " + str(self.warning_count) + "\n"
                result_msg += "Сохранено в: " + out_file + "\n\n"
                self.log_to_console("="*50)
                self.log_to_console(result_msg)
                messagebox.showinfo("Готово", result_msg)
            
        except Exception as e:
            self.info_label.configure(text="")
            self.log_error("Ошибка: " + str(e))
            messagebox.showerror("Ошибка", str(e))
    
    def encode_file(self):
        """Метод сжатия"""
        self.log_info("=== СЖАТИЕ ФАЙЛА ===")
        
        filename = filedialog.askopenfilename(title="Выберите файл для сжатия",
                                                filetypes=[("All files", "*.*")])
        if not filename:
            self.log_info("Операция отменена пользователем")
            return
        
        self.info_label.configure(text="Интерфейс может\nне отвечать,\nно программа работает.")
        is_text = filename.lower().endswith('.txt')
        
        self.error_count = 0
        self.warning_count = 0
        self.marker_count = 0
        
        file_size = os.path.getsize(filename)
        self.log_info("Файл: " + os.path.basename(filename) + 
                     " (" + str(file_size) + " bytes)")
        
        try:
            if is_text:
                with open(filename, 'r', encoding='utf-8') as f:
                    text = f.read()
                self.log_debug("Данные прочитаны успешно")
                data = self.parse_special_bytes(text)
                self.log_info("После парсинга спецбайтов: " + str(len(data)) + " байт")
            else:
                with open(filename, 'rb') as f:
                    data = f.read()
                self.log_debug("Данные прочитаны успешно")
            
            compressed_data = self.encode_data(data, skip_pattern=set())
            
            out_file = filename + "-compressed.bin"
            with open(out_file, 'wb') as f:
                f.write(compressed_data)
            
            self.info_label.configure(text="")
            self.log_info("Готово! Файл сжат и сохранён")
            result_msg = "Сжатый размер: " + str(len(compressed_data)) + " байт\n"
            result_msg += "Коэффициент сжатия: " + format(
                            (1 - len(compressed_data)/file_size)*100, ".1f") + "%\n"
            result_msg += "Ссылок использовано: " + str(self.marker_count) + "\n"
            result_msg += "Сохранено в: " + out_file + "\n\n"
            self.log_to_console("="*50)
            self.log_to_console(result_msg)
            messagebox.showinfo("Сжатие завершено", result_msg)
            
        except Exception as e:
            self.info_label.configure(text="")
            self.log_error("Ошибка: " + str(e))
            messagebox.showerror("Ошибка", str(e))
        
if __name__ == "__main__":
    root = tk.Tk()
    app = TextProcessor(root)
    root.mainloop()


"""
***********************************************************************
ФОРМАТ ССЫЛКИ (FF D9 1F) 3 байта

Структура ссылки:
    FF       D9                   1F
    ||       ||                   ||-- множитель (зависит от чётности полубайта длины)
    |        |                    |-- длина сегмента
    |        |-- остаток смещения
    |-- маркер начала ссылки

***********************************************************************
ФОРМУЛА ВЫЧИСЛЕНИЯ СМЕЩЕНИЯ:

    смещение = адрес_маркера - (0xFF - остаток_смещения + множитель * 256 + 1)

***********************************************************************
ТАБЛИЦА ДЛИНЫ СЕГМЕНТА (полубайт длины -> кол-во байт):

    0x0 -> 4 байта      0x8 -> 8 байт
    0x1 -> 4 байта      0x9 -> 8 байт
    0x2 -> 5 байт       0xA -> 9 байт
    0x3 -> 5 байт       0xB -> 9 байт
    0x4 -> 6 байт       0xC -> 10 байт
    0x5 -> 6 байт       0xD -> 10 байт
    0x6 -> 7 байт       0xE -> 11 байт
    0x7 -> 7 байт       0xF -> 11 байт

***********************************************************************
ТАБЛИЦА МНОЖИТЕЛЕЙ (полубайт множителя -> множитель):

    Значение   |  Нечётный полубайт  |  Чётный полубайт
               |        длины        |      длины
    -----------|---------------------|------------------
    0x0        |         15          |        31
    0x1        |         14          |        30
    0x2        |         13          |        29
    0x3        |         12          |        28
    0x4        |         11          |        27
    0x5        |         10          |        26
    0x6        |          9          |        25
    0x7        |          8          |        24
    0x8        |          7          |        23
    0x9        |          6          |        22
    0xA        |          5          |        21
    0xB        |          4          |        20
    0xC        |          3          |        19
    0xD        |          2          |        18
    0xE        |          1          |        17
    0xF        |          0          |        16

***********************************************************************
"""