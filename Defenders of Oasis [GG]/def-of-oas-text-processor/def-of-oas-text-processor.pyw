# python 3.4+

import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys
import string
import re
import random

MAIN_VERSION = "0.9"
MAIN_BG_COLOR = "#BEBEBE"
CONSOLE_BG_COLOR = "#BBBBBB"

WINDOW_SIZE = 8192
LENGTHS = (11,10,9,8,7,6,5,4) # оригинальный алгоритм сжатия
LENGTHS_EFFICIENCY = (11,10,9,8,7,6,5) # более эффективный алгоритм сжатия
MAX_NUM_SKIPS = 20
MAX_SKIP_NUMBERS = 100

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
        
        self.info_label = tk.Label(btn_frame1, text="", bg=MAIN_BG_COLOR,
                    fg="#A40026", font=(None, 11, "bold"))
        self.info_label.pack(side=tk.LEFT, padx=(10, 5))
	
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

        self.best_compress_btn = tk.Button(btn_frame2, text="Случайный подбор\nлучшего сжатия",
                    command=self.find_best_compression, width=20, height=3,
                    bg="#f7dc6f", fg="black", activebackground="#f4d03f", activeforeground="black",
                    font=(None, 10, "bold"))
        self.best_compress_btn.pack(side=tk.LEFT, padx=5)

        self.clear_logs_btn = tk.Button(btn_frame2, text="Очистить\nлоги",
                    command=self.clear_logs, width=12, height=3,
                    bg="#abebc6", fg="black", activebackground="#82e0aa", activeforeground="black",
                    font=(None, 10, "bold"))
        self.clear_logs_btn.pack(side=tk.RIGHT, padx=5)
        
        # Объединение checkbox и spinbox в одной строке
        controls_frame = tk.Frame(root, bg=MAIN_BG_COLOR)
        controls_frame.pack(pady=5, anchor='w', padx=10, fill=tk.X)
        
        self.debug_var = tk.IntVar(value=0)
        self.debug_check = tk.Checkbutton(controls_frame, text="Вывод подробных логов",
                    variable=self.debug_var, font=(None, 10, "bold"), 
                    bg=MAIN_BG_COLOR, activebackground=MAIN_BG_COLOR)
        self.debug_check.pack(side=tk.LEFT)
        
        self.attempts_var = tk.StringVar(value="50")
        self.attempts_spinbox = tk.Spinbox(controls_frame, from_=2, to=100000, width=6, 
                                           font=(None, 10, "bold"), textvariable=self.attempts_var)
        self.attempts_spinbox.pack(side=tk.LEFT, padx=(30, 5))
        
        self.attempts_label = tk.Label(controls_frame, text="Количество попыток подбора", 
                                            bg=MAIN_BG_COLOR, font=(None, 10, "bold"))
        self.attempts_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.efficiency_var = tk.IntVar(value=1)
        self.efficiency_check = tk.Checkbutton(controls_frame, text="Улучшенное сжатие",
                    variable=self.efficiency_var, font=(None, 10, "bold"), 
                    bg=MAIN_BG_COLOR, activebackground=MAIN_BG_COLOR)
        self.efficiency_check.pack(side=tk.LEFT)
        
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
        
        len_map = {0:4, 1:4, 2:5, 3:5, 4:6, 5:6, 6:7, 7:7, 8:8,
                   9:8, 10:9, 11:9, 12:10, 13:10, 14:11, 15:11}
        mult_map_odd = {0:15, 1:14, 2:13, 3:12, 4:11, 5:10, 6:9, 7:8,
                        8:7, 9:6, 10:5, 11:4, 12:3, 13:2, 14:1, 15:0}
        mult_map_even = {0:31, 1:30, 2:29, 3:28, 4:27, 5:26, 6:25, 7:24,
                         8:23, 9:22, 10:21, 11:20, 12:19, 13:18, 14:17, 15:16}

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
                        multiplier = mult_map_odd[low]
                    else:
                        multiplier = mult_map_even[low]
                    
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
        if skip_pattern is None:
            skip_pattern = set()
        
        if not skip_pattern:
            self.log_info("Начало кодирования")
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
        
        if self.efficiency_var.get():
            lengths = LENGTHS_EFFICIENCY
        else:
            lengths = LENGTHS

        hash_table = {}
        src_pos_mapping = []
        
        len_map = {4:0, 5:2, 6:4, 7:6, 8:8, 9:10, 10:12, 11:14}
                
        mult_map = {31:0, 30:1, 29:2, 28:3, 27:4, 26:5, 25:6, 24:7, 23:8, 
                    22:9, 21:10, 20:11, 19:12, 18:13, 17:14, 16:15,
                    15:0, 14:1, 13:2, 12:3, 11:4, 10:5, 9:6, 8:7,
                    7:8, 6:9, 5:10, 4:11, 3:12, 2:13, 1:14, 0:15}
        
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
                # has_zero = False
                # for k in range(length - 1):
                    # if data[i + k] == 0x00:
                        # has_zero = True
                        # break
                
                # if has_zero:
                    # continue
                
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

            if length >= 4:
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
    
    def find_best_compression(self):
        """Подбирает наилучшее сжатие путем перебора случайных комбинаций пропуска ссылок"""
        self.log_info("=== ПОДБОР ЛУЧШЕГО СЖАТИЯ ===")
        
        try:
            attempts = int(self.attempts_spinbox.get())
            if attempts < 2:
                attempts = 2
            elif attempts > 100000:
                attempts = 100000
                self.log_warning("Количество попыток ограничено 100 000")
        except ValueError:
            self.log_error("Неверное значение. Используется 50 попыток")
            attempts = 50
        
        self.log_info("Количество попыток: " + str(attempts))
        
        filename = filedialog.askopenfilename(title="Выберите файл для подбора сжатия", 
                                               filetypes=[("All files", "*.*")])
        if not filename:
            self.log_info("Операция отменена пользователем")
            return
        
        self.info_label.configure(text="Интерфейс может\nне отвечать,\nно программа работает.")
        file_size = os.path.getsize(filename)
        self.log_info("Файл: " + os.path.basename(filename) + 
                     " (" + str(file_size) + " bytes)")
        
        # Определяем тип файла (текстовый или бинарный) по расширению
        is_text = filename.lower().endswith('.txt')
        
        try:
            # Читаем данные
            if is_text:
                with open(filename, 'r', encoding='utf-8') as f:
                    text = f.read()
                data = self.parse_special_bytes(text)
                self.log_info("После парсинга спецбайтов: " + str(len(data)) + " байт")
            else:
                with open(filename, 'rb') as f:
                    data = f.read()
            
            self.log_info("Начальные данные: " + str(len(data)) + " байт")
            
            old_debug = self.debug_var.get()
            self.debug_var.set(0)
            
            best_data = None
            best_size = float('inf')
            best_pattern = None
            best_markers = 0
            best_skipped = 0
            
            # Эталонное сжатие
            self.log_info("\n--- Попытка 1/" + str(attempts) + " (ЭТАЛОН) ---")
            compressed_default = self.encode_data(data, skip_pattern=set())
            default_size = len(compressed_default)
            best_size = default_size
            best_data = compressed_default
            best_pattern = set()
            best_markers = self.marker_count
            best_skipped = 0
            self.log_info("  Размер: " + str(default_size) + " байт (эталон)")
            
            max_num_skips = MAX_NUM_SKIPS
            max_skip_numbers = MAX_SKIP_NUMBERS
            
            for attempt in range(2, attempts + 1):
                # Генерируем случайное количество пропускаемых ссылок (от 1 до 20)
                num_skips = random.randint(1, max_num_skips)
                # Генерируем случайные номера ссылок для пропуска (от 1 до 150)
                skip_numbers = set()
                while len(skip_numbers) < num_skips:
                    skip_numbers.add(random.randint(1, max_skip_numbers))
                
                self.log_info("--- Попытка " + str(attempt) + "/" + str(attempts) +  " ---")
                
                # Сжимаем с пропуском указанных ссылок
                compressed = self.encode_data(data, skip_pattern=skip_numbers)
                compressed_size = len(compressed)
                
                if compressed_size < best_size:
                    best_size = compressed_size
                    best_data = compressed
                    best_pattern = skip_numbers
                    best_markers = self.marker_count
                    best_skipped = num_skips
                    self.log_info("        >>> НОВЫЙ РЕКОРД! Размер: " + str(best_size) + " байт (улучшение на " + 
                                 str(default_size - best_size) + " байт)")
                else:
                    improvement = default_size - compressed_size
                    if improvement > 0:
                        self.log_info("        Размер: " + str(compressed_size) + " байт (лучше на " + 
                                     str(improvement) + " байт)")
                    else:
                        self.log_info("        Размер: " + str(compressed_size) + " байт (хуже на " + 
                                     str(compressed_size - default_size) + " байт)")
            
            self.debug_var.set(old_debug)
            self.info_label.configure(text="")
            
            # Сохраняем лучший результат
            if best_data:
                out_file = filename + "-best-compressed.bin"
                with open(out_file, 'wb') as f:
                    f.write(best_data)
                
                compression_ratio = (1 - best_size / file_size) * 100
                default_ratio = (1 - default_size / file_size) * 100
                
                result_msg = "Подбор сжатия завершен!\n\n"
                result_msg += "Лучший результат:\n"
                result_msg += "  Сжатый размер: " + str(best_size) + " байт\n"
                result_msg += "  Улучшение: " + str(default_size - best_size) + " байт (" + \
                             format((1 - best_size/default_size)*100, ".1f") + "%)\n"
                result_msg += "  Коэффициент сжатия: " + format(compression_ratio, ".1f") + "%\n"
                result_msg += "  Использовано ссылок: " + str(best_markers) + "\n"
                result_msg += "  Пропущенно ссылок: " + str(best_skipped) + "\n"
                result_msg += "  Пропущенные ссылки: " + (str(sorted(best_pattern)) if best_pattern else "нет") + "\n\n"
                result_msg += "Для сравнения (эталон без пропуска):\n"
                result_msg += "  Размер: " + str(default_size) + " байт\n"
                result_msg += "  Коэффициент сжатия: " + format(default_ratio, ".1f") + "%\n\n"
                result_msg += "Перебрано вариантов: " + str(attempts) + "\n"
                result_msg += "Сохранено в: " + out_file
                
                self.log_info(result_msg)
                messagebox.showinfo("Подбор сжатия завершен", result_msg)
            else:
                self.log_error("Не удалось получить сжатые данные")
                messagebox.showerror("Ошибка", "Не удалось получить сжатые данные")
            
        except Exception as e:
            self.info_label.configure(text="")
            self.log_error("Ошибка: " + str(e))
            messagebox.showerror("Ошибка", str(e))
    
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
    FF       D9        1F
    ||       ||        ||-- множитель (зависит от чётности полубайта длины)
    |        |         |-- длина сегмента
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