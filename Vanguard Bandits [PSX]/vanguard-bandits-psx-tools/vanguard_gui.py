# Vanguard Bandits PSX Tools GUI by pav13 + deepseek
# psx-mode2-en.exe by https://www.romhacking.net/utilities/1417/

import ctypes
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import threading
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

import vanguard_tools
import vanguard_text

MAIN_VERSION = "0.14"


class VanguardToolsGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Vanguard Bandits PSX Tools GUI v" + MAIN_VERSION)
        
        self.settings_file = Path("settings.json")
        self.settings = {}
        self.unpack_mode = tk.StringVar()
        self.unpack_index = tk.StringVar()
        self.pack_mode = tk.StringVar()
        self.pack_index = tk.StringVar()
        self.load_settings()
        self.initialize_interface()
        self.apply_initial_settings()
        
    def initialize_interface(self):
        """Инициализация всего интерфейса"""
        if 'window_geometry' in self.settings:
            self.root.geometry(self.settings['window_geometry'])
        else:
            self.root.geometry("1000x600")
        
        self.theme_mode = self.settings.get('theme_mode', 'light')
        self.paned_position = self.settings.get('paned_position', 700)
        
        self.create_split_layout()
        
        current_tab = self.settings.get('current_tab', 0)
        if 0 <= current_tab < self.notebook.index('end'):
            self.notebook.select(current_tab)
        
        self.current_font_size = self.settings.get('console_font_size', 8)
        self.base_font_size = self.current_font_size
    
        self.redirect_stdout()
        self.setup_event_handlers()
    
    def apply_initial_settings(self):
        """Применяет начальные настройки темы и интерфейса"""
        self.set_theme(self.theme_mode)
        self.apply_theme_force()
    
    def setup_event_handlers(self):
        """Настройка обработчиков событий"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind('<Configure>', self.on_window_configure)
    
    def create_split_layout(self):
        """Создает разделенный интерфейс с вкладками слева и консолью справа"""
        # Главный фрейм для разделения
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.left_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.left_frame, weight=7)
        
        self.right_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.right_frame, weight=3)
        
        self.root.update()
        self.root.after(100, self.restore_paned_position)
        
        self.create_tabs()
        self.create_console_panel(self.right_frame)
    
    def create_tabs(self):
        """Создает все вкладки приложения"""
        self.notebook = ttk.Notebook(self.left_frame)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        tabs = [
            ('analyze_tab', '  Анализ     '),
            ('extract_tab', '  Извлечение     '),
            ('lzss_tab', '  LZSS     '),
            ('found_text_tab', '  Найти текст     '),
            ('build_tab', '  Сборка контейнера     '),
            ('replace_tab', '  Сборка образа PSX     '),
            ('settings_tab', '  Настройки     ')
        ]
        
        for method_name, tab_text in tabs:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=tab_text)
            getattr(self, 'create_' + method_name)(frame)
    
    def create_common_file_selection(self, parent, row, text, file_var, display_var, 
                                   browse_command, is_directory=False, width=50):
        """Универсальный метод создания элементов выбора файла/папки"""
        ttk.Label(parent, text=text).grid(row=row, column=0, sticky='w', padx=5, pady=5)
        
        display_var.set(self.format_path(file_var.get(), is_directory))
        ttk.Entry(parent, textvariable=display_var, width=width, state='readonly').grid(
            row=row, column=1, padx=5, pady=5)
        ttk.Button(parent, text="Обзор", command=browse_command).grid(
            row=row, column=2, padx=5, pady=5)
    
    def create_index_control(self, parent, row, text, index_var, command_col=1):
        """Создает универсальный контрол для управления индексом с кнопками +/-"""
        ttk.Label(parent, text=text).grid(row=row, column=0, sticky='w', padx=5, pady=5)
        
        index_frame = ttk.Frame(parent)
        index_frame.grid(row=row, column=command_col, sticky='w', padx=5, pady=5)
        
        ttk.Button(index_frame, text="-", width=3, 
                  command=lambda: self.decrement_index(index_var)).grid(row=0, column=0, padx=(0, 2))
        ttk.Entry(index_frame, textvariable=index_var, width=8).grid(row=0, column=1, padx=2)
        ttk.Button(index_frame, text="+", width=3, 
                  command=lambda: self.increment_index(index_var)).grid(row=0, column=2, padx=(2, 0))
    
    def create_analyze_tab(self, frame):
        """Вкладка для анализа архива"""
        ttk.Label(frame, text="Анализ структуры архива или файлов в папке:", 
                 font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        
        self.analyze_mode = tk.StringVar(value=self.settings.get('analyze_mode', "file"))
        ttk.Radiobutton(frame, text="Анализ файла контейнера:",
                       variable=self.analyze_mode, value="file").grid(
                       row=1, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        
        self.analyze_file = tk.StringVar(value=self.settings.get('analyze_file', "EPICA.BIN"))
        self.analyze_file_display = tk.StringVar()
        self.create_common_file_selection(frame, 2, "Файл для анализа:", 
                                        self.analyze_file, self.analyze_file_display,
                                        self.browse_analyze_file)
        
        ttk.Radiobutton(frame, text="Анализ всех файлов в папке:", 
                       variable=self.analyze_mode, value="folder").grid(
                       row=3, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        
        self.analyze_folder = tk.StringVar(value=self.settings.get('analyze_folder', "extracted"))
        self.analyze_folder_display = tk.StringVar()
        self.create_common_file_selection(frame, 4, "Папка для анализа:", 
                                        self.analyze_folder, self.analyze_folder_display,
                                        self.browse_analyze_folder, is_directory=True)
        
        ttk.Label(frame, text="Файл отчета:").grid(row=5, column=0, sticky='w', padx=5, pady=5)
        self.report_file = tk.StringVar(value=self.settings.get('report_file', "report-analysis.txt"))
        self.report_file_display = tk.StringVar()
        ttk.Entry(frame, textvariable=self.report_file, width=50).grid(row=5, column=1, padx=5, pady=5)
        ttk.Button(frame, text="Обзор", command=self.browse_analyze_report).grid(row=5, column=2, padx=5, pady=5)
        
        ttk.Button(frame, text="Анализировать", command=self.analyze_archive).grid(row=6, column=0, columnspan=3, pady=10)
    
    def create_extract_tab(self, frame):
        """Вкладка для извлечения файлов из архива"""
        ttk.Label(frame, text="Извлечение файлов из контейнеров:", 
                 font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        
        self.extract_mode = tk.StringVar(value=self.settings.get('extract_mode', "file"))
        ttk.Radiobutton(frame, text="Извлечь из одного файла контейнера  (например, EPICA.BIN):", 
                       variable=self.extract_mode, value="file").grid(
                       row=1, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        
        self.archive_file = tk.StringVar(value=self.settings.get('archive_file', "EPICA.BIN"))
        self.archive_file_display = tk.StringVar()
        self.create_common_file_selection(frame, 2, "Файл контейнера:", 
                                        self.archive_file, self.archive_file_display,
                                        self.browse_archive)
        
        ttk.Radiobutton(frame, text="Извлечь из всех контейнеров в папке:", 
                       variable=self.extract_mode, value="folder").grid(
                       row=3, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        
        self.archive_folder = tk.StringVar(value=self.settings.get('archive_folder', "archives"))
        self.archive_folder_display = tk.StringVar()
        self.create_common_file_selection(frame, 4, "Папка с контейнерами:", 
                                        self.archive_folder, self.archive_folder_display,
                                        self.browse_archive_folder, is_directory=True)
        
        self.extract_dir = tk.StringVar(value=self.settings.get('extract_dir', "extracted"))
        self.extract_dir_display = tk.StringVar()
        self.create_common_file_selection(frame, 5, "Папка для извлечения:", 
                                        self.extract_dir, self.extract_dir_display,
                                        self.browse_extract_dir, is_directory=True)

        ttk.Button(frame, text="Извлечь файлы", 
                  command=self.extract_files).grid(row=6, column=0, columnspan=3, pady=10)
    
    def create_lzss_tab(self, frame):
        """Вкладка для операций LZSS"""
        ttk.Label(frame, text="Распаковка LZSS:", 
                 font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=4, sticky='w', padx=5, pady=5)
        
        self.unpack_mode = tk.StringVar(value=self.settings.get('unpack_mode', "all"))
        self.unpack_dir = tk.StringVar(value=self.settings.get('unpack_dir', "extracted"))
        self.unpack_dir_display = tk.StringVar()
        
        self.create_common_file_selection(frame, 1, "Папка с файлами:", 
                                        self.unpack_dir, self.unpack_dir_display,
                                        self.browse_unpack_dir, is_directory=True, width=50)
        
        ttk.Radiobutton(frame, text="Распаковать один файл с индексом", 
                       variable=self.unpack_mode, value="single").grid(
                       row=2, column=0, columnspan=1, sticky='w', padx=5, pady=5)
        
        self.unpack_index = tk.StringVar(value=self.settings.get('unpack_index', "0"))
        self.create_index_control(frame, 2, "", self.unpack_index, command_col=1)
        
        ttk.Radiobutton(frame, text="Распаковать все файлы по сигнатурам", 
                       variable=self.unpack_mode, value="all").grid(
                       row=3, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        
        ttk.Label(frame, text="(file_XXXX.bin -> file_XXXX.lzss-dec)", 
                 font=('Arial', 8)).grid(
                 row=4, column=1, columnspan=3, sticky='w', padx=5, pady=2)
        
        ttk.Button(frame, text="Распаковать файл/-ы", 
                  command=self.unpack_lzss).grid(row=5, column=0, columnspan=4, pady=10)
        
        ttk.Separator(frame, orient='horizontal').grid(row=6, column=0, columnspan=4, sticky='ew', pady=10)
        ttk.Label(frame, text="Упаковка LZSS:", 
                 font=('Arial', 10, 'bold')).grid(row=7, column=0, columnspan=4, sticky='w', padx=5, pady=5)
        
        self.pack_mode = tk.StringVar(value=self.settings.get('pack_mode', "single"))
        self.pack_dir = tk.StringVar(value=self.settings.get('pack_dir', "extracted"))
        self.pack_dir_display = tk.StringVar()
        
        self.create_common_file_selection(frame, 8, "Папка с файлами:", 
                                        self.pack_dir, self.pack_dir_display,
                                        self.browse_pack_dir, is_directory=True, width=50)
        
        ttk.Radiobutton(frame, text="Упаковать один файл с индексом", 
                       variable=self.pack_mode, value="single").grid(
                       row=9, column=0, columnspan=2, sticky='w', padx=5, pady=5)
        
        self.pack_index = tk.StringVar(value=self.settings.get('pack_index', "0"))
        self.create_index_control(frame, 9, "", self.pack_index, command_col=1)
        
        ttk.Radiobutton(frame, text="Упаковать все файлы в папке (долго, ~ 15 минут)", 
                       variable=self.pack_mode, value="all").grid(
                       row=10, column=0, columnspan=2, sticky='w', padx=5, pady=5)
        
        ttk.Label(frame, text="(file_XXXX.lzss-dec -> file_XXXX.bin)", 
                 font=('Arial', 8)).grid(
                 row=11, column=1, columnspan=3, sticky='w', padx=5, pady=2)
        
        ttk.Button(frame, text="Упаковать файл/-ы", 
                  command=self.pack_lzss).grid(row=12, column=0, columnspan=4, pady=10)
    
    def create_found_text_tab(self, frame):
        """Вкладка для поиска и работы с текстом"""
        ttk.Label(frame, text="Поиск текстовых блоков:", 
                 font=('Arial', 9, 'bold')).grid(row=1, column=0, columnspan=4, sticky='w', padx=5, pady=(10,5))
        
        self.text_extract_dir = tk.StringVar(value=self.settings.get('text_extract_dir', "extracted"))
        self.text_extract_dir_display = tk.StringVar()
        self.create_common_file_selection(frame, 2, "Папка с файлами:", 
                                        self.text_extract_dir, self.text_extract_dir_display,
                                        self.browse_text_extract_dir, is_directory=True, width=50)
        
        self.text_find_mode = tk.StringVar(value=self.settings.get('text_find_mode', "single"))
        ttk.Radiobutton(frame, text="Поиск в файле с индексом:", 
                       variable=self.text_find_mode, value="single").grid(
                       row=3, column=0, sticky='w', padx=5, pady=5)
        
        self.text_find_index = tk.StringVar(value=self.settings.get('text_find_index', "0"))
        self.create_index_control(frame, 3, "", self.text_find_index, command_col=1)
        
        ttk.Radiobutton(frame, text="Поиск во всех файлах", 
                       variable=self.text_find_mode, value="all").grid(
                       row=4, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        
        params_frame = ttk.Frame(frame)
        params_frame.grid(row=5, column=0, columnspan=4, sticky='w', padx=5, pady=5)
        
        ttk.Label(params_frame, text="Мин. длина строки:").grid(row=0, column=0, sticky='w', padx=(0,5), pady=2)
        self.text_min_length = tk.StringVar(value=self.settings.get('text_min_length', "6"))
        ttk.Entry(params_frame, textvariable=self.text_min_length, width=8).grid(row=0, column=1, sticky='w', padx=(0,15), pady=2)
        
        ttk.Label(params_frame, text="Макс. блоков:").grid(row=0, column=2, sticky='w', padx=(0,5), pady=2)
        self.text_max_blocks = tk.StringVar(value=self.settings.get('text_max_blocks', "1000"))
        ttk.Entry(params_frame, textvariable=self.text_max_blocks, width=8).grid(row=0, column=3, sticky='w', padx=(0,5), pady=2)
        
        ttk.Button(frame, text="Найти текст", 
                  command=self.find_text_blocks_improved).grid(row=6, column=0, columnspan=4, pady=10)
        
        # Информация о поиске
        # info_texts = [
            # "file_XXXX.bin → file_XXXX-text.txt,  file_XXXX.lzss-dec → file_XXXX-text.txt",
        # ]
        
        # for i, text in enumerate(info_texts, 7):
            # ttk.Label(frame, text=text, font=('Arial', 8)).grid(
                # row=i, column=0, columnspan=4, sticky='w', padx=5, pady=1)
        
        ttk.Separator(frame, orient='horizontal').grid(row=10, column=0, columnspan=4, sticky='ew', pady=10)
        ttk.Label(frame, text="Применение перевода к файлу:", 
                 font=('Arial', 9, 'bold')).grid(row=11, column=0, columnspan=4, sticky='w', padx=5, pady=(5,5))
        
        self.text_update_dir = tk.StringVar(value=self.settings.get('text_update_dir', "extracted"))
        self.text_update_dir_display = tk.StringVar()
        self.create_common_file_selection(frame, 12, "Папка с файлами:", 
                                        self.text_update_dir, self.text_update_dir_display,
                                        self.browse_text_update_dir, is_directory=True, width=50)
        
        self.text_update_index = tk.StringVar(value=self.settings.get('text_update_index', "0"))
        self.create_index_control(frame, 13, "Индекс файла для обновления:", self.text_update_index)
        
        translate_buttons_frame = ttk.Frame(frame)
        translate_buttons_frame.grid(row=14, column=0, columnspan=4, sticky='w', padx=5, pady=5)
        
        ttk.Button(translate_buttons_frame, text="Открыть файл перевода", 
              command=self.open_text_file).pack(side='left', padx=(0,10))
        ttk.Button(translate_buttons_frame, text="Восстановить из копии", 
              command=self.restore_from_backup).pack(side='left', padx=(0,10))
        ttk.Button(translate_buttons_frame, text="Применить перевод", 
              command=self.update_text_translation_improved).pack(side='left', padx=(0,10))
        
        # ttk.Separator(frame, orient='horizontal').grid(row=15, column=0, columnspan=4, sticky='ew', pady=10)
        
        encoding_buttons_frame = ttk.Frame(frame)
        encoding_buttons_frame.grid(row=16, column=0, columnspan=4, sticky='w', padx=5, pady=5)
        
        ttk.Button(encoding_buttons_frame, text="Таблица кодировки", 
                  command=self.open_encoding_table).pack(side='left', padx=(0,10))
        ttk.Button(encoding_buttons_frame, text="Диагностика таблицы кодировки", 
              command=self.debug_encoding_table).pack(side='left', padx=(0,10))
              
        update_info_texts = [
            "* Создаются резервные копии (.bak) с защитой от перезаписи.   * Не забываем упаковать LZSS после перевода!",
            "* Приоритет: file_XXXX.lzss-dec, если его нет, то file_XXXX.bin.         *** ТЕСТОВЫЙ ФУНКЦИНАЛ ***",
        ]
        
        for i, text in enumerate(update_info_texts, 17):
            ttk.Label(frame, text=text, font=('Arial', 9)).grid(
                row=i, column=0, columnspan=4, sticky='w', padx=5, pady=1)
        
        ttk.Separator(frame, orient='horizontal').grid(row=19, column=0, columnspan=4, sticky='ew', pady=10)
        
        status_frame = ttk.Frame(frame)
        status_frame.grid(row=20, column=0, columnspan=4, sticky='w', padx=5, pady=5)
        
        ttk.Label(status_frame, text="Статус:", font=('Arial', 9, 'bold')).pack(side='left')
        self.text_status_var = tk.StringVar(value="Готов")
        ttk.Label(status_frame, textvariable=self.text_status_var, font=('Arial', 9)).pack(side='left', padx=(5,0))
    
    def create_build_tab(self, frame):
        """Вкладка для упаковки файлов в архив"""
        ttk.Label(frame, text="Сборка файлов обратно в новый контейнер (например, EPICA.BIN):", 
                 font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        
        self.build_dir = tk.StringVar(value=self.settings.get('build_dir', "extracted"))
        self.build_dir_display = tk.StringVar()
        self.create_common_file_selection(frame, 1, "Папка с файлами:", 
                                        self.build_dir, self.build_dir_display,
                                        self.browse_build_dir, is_directory=True)
        
        self.output_file = tk.StringVar(value=self.settings.get('output_file', "EPICA.BIN"))
        self.output_file_display = tk.StringVar()
        self.create_common_file_selection(frame, 2, "Выходной файл:", 
                                        self.output_file, self.output_file_display,
                                        self.browse_output_file)
        
        ttk.Label(frame, text="Выравнивание:").grid(row=3, column=0, sticky='w', padx=5, pady=5)
        self.alignment = tk.StringVar(value=self.settings.get('alignment', "0x800"))
        ttk.Entry(frame, textvariable=self.alignment, width=10).grid(row=3, column=1, sticky='w', padx=5, pady=5)
        
        self.verify_build = tk.BooleanVar(value=self.settings.get('verify_build', False))
        ttk.Checkbutton(frame, text="Проверить целостность контейнера", 
                       variable=self.verify_build).grid(row=4, column=0, columnspan=2, sticky='w', padx=5, pady=5)
        
        self.detailed_build = tk.BooleanVar(value=self.settings.get('detailed_build', False))
        ttk.Checkbutton(frame, text="Подробный вывод (медленно)", 
                       variable=self.detailed_build).grid(row=5, column=0, columnspan=2, sticky='w', padx=5, pady=5)
        
        ttk.Button(frame, text="Собрать контейнер", 
                  command=self.build_archive).grid(row=6, column=0, columnspan=3, pady=10)
    
    def create_replace_tab(self, frame):
        """Вкладка для замены файлов в PSX образе"""
        ttk.Label(frame, text="Замена файлов в PSX образе Vanguard Bandits:", 
                 font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        
        self.bin_file = tk.StringVar(value=self.settings.get('bin_file', ""))
        self.bin_file_display = tk.StringVar()
        self.create_common_file_selection(frame, 1, "BIN файл образа игры:", 
                                        self.bin_file, self.bin_file_display,
                                        self.browse_bin_file)
        
        ttk.Label(frame, text="Заменить файл:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.target_file = tk.StringVar(value=self.settings.get('target_file', "\\EPICA.BIN"))
        target_combo = ttk.Combobox(frame, textvariable=self.target_file, 
                                   values=["\\EPICA.BIN", "\\SLUS_010.70", "\\STELLA.XA", "\\SYSTEM.CNF"], 
                                   state="readonly")
        target_combo.grid(row=2, column=1, sticky='w', padx=5, pady=5)
        
        self.replacement_file = tk.StringVar(value=self.settings.get('replacement_file', ""))
        self.replacement_file_display = tk.StringVar()
        self.create_common_file_selection(frame, 3, "Новый файл для замены:", 
                                        self.replacement_file, self.replacement_file_display,
                                        self.browse_replacement_file)
        
        ttk.Button(frame, text="Собрать образ", 
                  command=self.replace_file_in_image).grid(row=4, column=0, columnspan=3, pady=10)
        
        ttk.Label(frame, text="Внимание! Файл образа будет перезаписан.", 
                 font=('Arial', 9, 'bold')).grid(
                 row=5, column=0, columnspan=3, sticky='w', padx=5, pady=2)
        
        ttk.Separator(frame, orient='horizontal').grid(row=6, column=0, columnspan=3, sticky='ew', pady=10)
        ttk.Label(frame, text="Запуск эмулятора PSX:", 
                 font=('Arial', 10, 'bold')).grid(row=7, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        
        ttk.Label(frame, text="Файл эмулятора:").grid(row=8, column=0, sticky='w', padx=5, pady=5)
        self.emulator_file = tk.StringVar(value=self.settings.get('emulator_file', ""))
        emulator_entry = ttk.Entry(frame, textvariable=self.emulator_file, width=50)
        emulator_entry.grid(row=8, column=1, padx=5, pady=5)
        ttk.Button(frame, text="Обзор", command=self.browse_emulator_file).grid(row=8, column=2, padx=5, pady=5)
        
        ttk.Label(frame, text="Аргументы эмулятора:").grid(row=9, column=0, sticky='w', padx=5, pady=5)
        self.emulator_args = tk.StringVar(value=self.settings.get('emulator_args', "-batch"))
        emulator_args_entry = ttk.Entry(frame, textvariable=self.emulator_args, width=50)
        emulator_args_entry.grid(row=9, column=1, padx=5, pady=5)
        
        ttk.Label(frame, text="Пример: -batch -fullscreen", 
                 font=('Arial', 8)).grid(row=10, column=1, sticky='w', padx=5, pady=2)
        
        ttk.Button(frame, text="Запустить эмулятор", 
                  command=self.launch_emulator).grid(row=11, column=0, columnspan=3, pady=10)
        
        ttk.Label(frame, text="Укажите путь к эмулятору и аргументы. Файл образа будет добавлен автоматически.", 
                 font=('Arial', 8)).grid(
                 row=12, column=0, columnspan=3, sticky='w', padx=5, pady=2)
    
    def create_settings_tab(self, frame):
        """Вкладка настроек приложения"""
        ttk.Label(frame, text="Настройки приложения:", 
                 font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=2, sticky='w', padx=5, pady=10)
        
        ttk.Label(frame, text="Тема приложения:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.theme_var = tk.StringVar(value=self.theme_mode)
        ttk.Radiobutton(frame, text="Светлая", variable=self.theme_var, value="light", 
                       command=self.apply_theme).grid(row=2, column=0, sticky='w', padx=5, pady=2)
        ttk.Radiobutton(frame, text="Тёмная", variable=self.theme_var, value="dark", 
                       command=self.apply_theme).grid(row=3, column=0, sticky='w', padx=5, pady=2)
        
        ttk.Separator(frame, orient='horizontal').grid(row=4, column=0, columnspan=2, sticky='ew', pady=10)
        
        ttk.Label(frame, text="Настройки и параметры сохраняются при закрытии приложения.", 
                 font=('Arial', 10, 'bold')).grid(row=5, column=0, columnspan=2, sticky='w', padx=5, pady=5)
        ttk.Label(frame, text="Для сброса настроек удалить 'settings.json'.", 
                 font=('Arial', 10, 'bold')).grid(row=6, column=0, columnspan=2, sticky='w', padx=5, pady=5)

    def format_path(self, path, is_directory=False):
        """Форматирует путь для отображения (универсальный метод)"""
        if not path:
            return ""
        path_obj = Path(path)
        if is_directory:
            parts = list(path_obj.parts)
            if len(parts) >= 2:
                return ".../" + parts[-2] + "/" + parts[-1]
            return path
        else:
            if path_obj.is_file():
                return ".../" + path_obj.parent.name + "/" + path_obj.name
            return path
    
    def increment_index(self, index_var):
        """Увеличивает значение переменной индекса на 1"""
        try:
            current = int(index_var.get())
            index_var.set(str(current + 1))
        except ValueError:
            index_var.set("0")

    def decrement_index(self, index_var):
        """Уменьшает значение переменной индекса на 1"""
        try:
            current = int(index_var.get())
            if current > 0:
                index_var.set(str(current - 1))
        except ValueError:
            index_var.set("0")
    
    def load_settings(self):
        """Загружает настройки из файла"""
        try:
            if self.settings_file.exists():
                with open(str(self.settings_file), 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
            else:
                self.settings = {}

            if 'console_font_size' not in self.settings:
                self.settings['console_font_size'] = 8

        except Exception as e:
            print("Error loading settings: " + str(e))
            self.settings = {}

    def save_settings(self):
        """Сохраняет настройки в файл"""
        try:
            self.save_field_values()
            self.settings['current_tab'] = self.notebook.index(self.notebook.select())
            self.save_paned_position()
            
            if hasattr(self, 'current_font_size'):
                self.settings['console_font_size'] = self.current_font_size
            
            serializable_settings = {}
            for key, value in self.settings.items():
                if hasattr(value, '__fspath__'):
                    serializable_settings[key] = str(value)
                else:
                    serializable_settings[key] = value
            
            with open(str(self.settings_file), 'w', encoding='utf-8') as f:
                json.dump(serializable_settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("Error saving settings: " + str(e))

    def save_field_values(self):
        """Сохраняет значения всех полей в настройки"""
        settings_map = {
            'extract_mode': self.extract_mode,
            'archive_file': self.archive_file,
            'archive_folder': self.archive_folder,
            'extract_dir': self.extract_dir,
            'alignment': self.alignment,
            'verify_build': self.verify_build,
            'detailed_build': self.detailed_build,
            'analyze_mode': self.analyze_mode,
            'analyze_file': self.analyze_file,
            'analyze_folder': self.analyze_folder,
            'report_file': self.report_file,
            'unpack_mode': self.unpack_mode,
            'unpack_index': self.unpack_index,
            'pack_mode': self.pack_mode,
            'pack_index': self.pack_index,
            'target_file': self.target_file,
            'emulator_file': self.emulator_file,
            'emulator_args': self.emulator_args,
            'text_find_mode': self.text_find_mode,
            'text_find_index': self.text_find_index,
            'text_max_blocks': self.text_max_blocks,
            'text_min_length': self.text_min_length,
            'text_update_index': self.text_update_index,
            'text_update_dir': self.text_update_dir,
            'text_extract_dir': self.text_extract_dir
        }
        
        for key, var in settings_map.items():
            if hasattr(self, key) and hasattr(getattr(self, key), 'get'):
                value = getattr(self, key).get()
                if hasattr(value, '__fspath__'):
                    value = str(value)
                self.settings[key] = value

    def on_closing(self):
        """Сохраняет настройки перед закрытием"""
        if hasattr(self, 'main_paned'):
            self.save_paned_position()
        if self.root.state() == 'normal':
            self.settings['window_geometry'] = self.root.geometry()
        
        self.save_settings()
        self.root.destroy()
    
    def on_window_configure(self, event=None):
        """Сохраняет позицию и размер окна при изменении"""
        if event.widget == self.root and self.root.state() == 'normal':
            self.settings['window_geometry'] = self.root.geometry()
    
    def restore_paned_position(self):
        """Восстанавливает положение разделителя после создания интерфейса"""
        try:
            if hasattr(self, 'main_paned') and 'paned_position' in self.settings:
                paned_position = self.settings['paned_position']
                window_width = self.root.winfo_width()
                
                if paned_position and 100 < paned_position < window_width - 100:
                    self.main_paned.sashpos(0, paned_position)
                else:
                    default_position = int(window_width * 0.7)
                    self.main_paned.sashpos(0, default_position)
        except Exception as e:
            print("Error restoring paned position: " + str(e))
    
    def save_paned_position(self):
        """Сохраняет текущее положение разделителя"""
        if hasattr(self, 'main_paned'):
            try:
                current_pos = self.main_paned.sashpos(0)
                if current_pos and current_pos > 0:
                    self.settings['paned_position'] = current_pos
            except Exception as e:
                print("Error saving paned position: " + str(e))
    
    def set_theme(self, theme_mode):
        """Устанавливает тему приложения"""
        self.theme_mode = theme_mode
        style = ttk.Style()
        
        if theme_mode == 'dark':
            self.apply_dark_theme(style)
        else:
            self.apply_light_theme(style)
        
        self.settings['theme_mode'] = theme_mode
    
    def apply_dark_theme(self, style):
        """Применяет темную тему"""
        try:
            style.theme_use('clam')
        except:
            style.theme_use('default')
        
        bg_color = '#2b2b2b'
        fg_color = 'white'
        entry_bg = '#3c3c3c'
        button_bg = '#4c4c4c'
        selected_bg = '#5c5c5c'
        
        self.root.configure(bg=bg_color)
        
        self.configure_theme_styles(style, bg_color, fg_color, entry_bg, selected_bg, button_bg)
        
        if hasattr(self, 'log_text'):
            self.log_text.configure(
                bg='#2d2d2d', 
                fg='#e0e0e0', 
                insertbackground='#e0e0e0',
                selectbackground='#555555',
                inactiveselectbackground='#3d3d3d'
            )
        
        self.configure_theme_states(style, selected_bg, fg_color, entry_bg, button_bg, bg_color)
        
        self.update_all_widgets(bg_color, fg_color)
    
    def apply_light_theme(self, style):
        """Применяет светлую тему"""
        try:
            style.theme_use('clam')
        except:
            style.theme_use('default')
                
        bg_color = 'SystemButtonFace'
        fg_color = 'black'
        entry_bg = 'white'
        selected_bg = 'SystemHighlight'
        selected_fg = 'SystemHighlightText'
        active_fg = fg_color
        
        self.root.configure(bg=bg_color)
        
        self.configure_theme_styles(style, bg_color, fg_color, entry_bg, selected_bg, selected_fg)
        
        if hasattr(self, 'log_text'):
            self.log_text.configure(
                bg='white', 
                fg='black', 
                insertbackground='black',
                selectbackground='#c0c0c0',
                inactiveselectbackground='#e0e0e0'
            )
        
        self.configure_theme_states(style, selected_bg, active_fg, entry_bg, bg_color, bg_color)
        
        self.update_all_widgets(bg_color, fg_color)
    
    def configure_theme_styles(self, style, bg_color, fg_color, field_bg, select_bg, select_fg):
        """Конфигурирует основные стили темы"""
        style.configure('.', 
                       background=bg_color, 
                       foreground=fg_color,
                       fieldbackground=field_bg,
                       selectbackground=select_bg,
                       selectforeground=select_fg)
        
        elements = ['TFrame', 'TLabel', 'TButton', 'TEntry', 'TCombobox', 
                   'TCheckbutton', 'TRadiobutton', 'TNotebook', 'TNotebook.Tab', 'TSeparator']
        
        for element in elements:
            style.configure(element, background=bg_color, foreground=fg_color)
        
        style.configure('TEntry', fieldbackground=field_bg, foreground=fg_color)
        style.configure('TCombobox', fieldbackground=field_bg, foreground=fg_color)
        style.configure('TNotebook.Tab', background=bg_color, foreground=fg_color)
    
    def configure_theme_states(self, style, active_bg, active_fg, field_bg, button_bg, bg_color):
        """Конфигурирует состояния для темы"""
        style.map('TButton',
                 background=[('active', active_bg), ('pressed', active_bg)],
                 foreground=[('active', active_fg), ('pressed', active_fg)])
        
        style.map('TNotebook.Tab',
                 background=[('selected', active_bg), ('active', active_bg)],
                 foreground=[('selected', active_fg), ('active', active_fg)])
        
        style.map('TCombobox',
                 fieldbackground=[('readonly', field_bg)],
                 background=[('readonly', button_bg)],
                 foreground=[('readonly', active_fg)])
        
        style.map('TCheckbutton',
                 background=[('active', bg_color), ('pressed', bg_color)],
                 foreground=[('active', active_fg), ('pressed', active_fg)],
                 indicatorcolor=[('selected', active_fg), ('pressed', active_fg)])
        
        style.map('TRadiobutton',
                 background=[('active', bg_color), ('pressed', bg_color)],
                 foreground=[('active', active_fg), ('pressed', active_fg)],
                 indicatorcolor=[('selected', active_fg), ('pressed', active_fg)])
    
    def update_all_widgets(self, bg_color, fg_color):
        """Рекурсивно обновляет все виджеты для применения темы"""
        def update_widget(widget):
            try:
                if isinstance(widget, (tk.Frame, tk.LabelFrame)):
                    widget.configure(bg=bg_color)
                elif isinstance(widget, (tk.Label, tk.Button)):
                    widget.configure(bg=bg_color, fg=fg_color)
                elif isinstance(widget, (tk.Entry, tk.Text)):
                    widget.configure(bg='#3c3c3c' if bg_color == '#2b2b2b' else 'white', 
                                   fg=fg_color, 
                                   insertbackground=fg_color)
                elif isinstance(widget, tk.Listbox):
                    widget.configure(bg='#3c3c3c' if bg_color == '#2b2b2b' else 'white', 
                                   fg=fg_color,
                                   selectbackground='#5c5c5c' if bg_color == '#2b2b2b' else 'SystemHighlight')
            except:
                pass
            
            try:
                for child in widget.winfo_children():
                    update_widget(child)
            except:
                pass
        
        update_widget(self.root)
    
    def apply_theme(self):
        self.set_theme(self.theme_var.get())
    
    def apply_theme_force(self):
        self.set_theme(self.theme_mode)
        self.root.update_idletasks()
    
    def create_console_panel(self, parent):
        """Создает панель консоли с постоянным выводом и ручным управлением шрифтом"""
        console_frame = ttk.LabelFrame(parent, text="Консольный вывод", padding=5)
        console_frame.pack(fill='both', expand=True)
        
        self.current_font_size = self.settings.get('console_font_size', 8)
        
        self.log_text = scrolledtext.ScrolledText(
            console_frame, 
            wrap=tk.WORD, 
            width=40, 
            height=30, 
            state='disabled',
            font=('Consolas', self.current_font_size)
        )
        self.log_text.pack(fill='both', expand=True)
        
        button_frame = ttk.Frame(console_frame)
        button_frame.pack(fill='x', pady=(5, 0))
        
        left_frame = ttk.Frame(button_frame)
        left_frame.pack(side='left')
        
        ttk.Button(left_frame, text="Очистить лог", command=self.clear_log).pack(side='left', padx=(0, 5))
        ttk.Button(left_frame, text="Копировать", command=self.copy_log).pack(side='left')
        
        right_frame = ttk.Frame(button_frame)
        right_frame.pack(side='right')
        
        self.font_size_label = ttk.Label(right_frame, text=str(self.current_font_size) + "pt", width=4)
        self.font_size_label.pack(side='left', padx=(5, 2))
        
        ttk.Button(right_frame, text="a-", width=3, 
                   command=lambda: self.change_font_size(-1)).pack(side='left', padx=(0, 2))
        ttk.Button(right_frame, text="A+", width=3, 
                   command=lambda: self.change_font_size(1)).pack(side='left')

    def change_font_size(self, delta):
        """Manually change font size with saving"""
        min_font_size = 6
        max_font_size = 20
        
        new_size = self.current_font_size + delta
        
        if min_font_size <= new_size <= max_font_size:
            self.current_font_size = new_size
            
            self.log_text.configure(font=('Consolas', self.current_font_size))
            self.font_size_label.config(text=str(self.current_font_size) + "pt")
            
            self.settings['console_font_size'] = self.current_font_size
    
    def redirect_stdout(self):
        """Перенаправляем stdout в текстовое поле лога"""
        class StdoutRedirector:
            def __init__(self, text_widget):
                self.text_widget = text_widget
                
            def write(self, string):
                self.text_widget.config(state='normal')
                self.text_widget.insert('end', string)
                self.text_widget.see('end')
                self.text_widget.config(state='disabled')
                self.text_widget.update_idletasks()
                
            def flush(self):
                pass
                
        sys.stdout = StdoutRedirector(self.log_text)
    
    def clear_log(self):
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
    
    def copy_log(self):
        try:
            self.log_text.config(state='normal')
            text = self.log_text.get(1.0, tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.log_text.config(state='disabled')
        except Exception as e:
            print("Error copying log: " + str(e))
    
    def run_in_thread(self, func, *args):
        """Запускает функцию в отдельном потоке"""
        thread = threading.Thread(target=func, args=args)
        thread.setDaemon(True)
        thread.start()
    
    def execute_operation(self, operation_name, operation_func, success_message=None):
        """Универсальный метод для выполнения операций с обработкой ошибок"""
        def do_operation():
            try:
                operation_func()
                if success_message:
                    messagebox.showinfo("Успех", success_message)
            except Exception as e:
                messagebox.showerror("Ошибка", "Ошибка при " + operation_name + ": " + str(e))
                print("Ошибка: " + str(e))
        
        self.run_in_thread(do_operation)
    
    def browse_file(self, title, file_types, var_to_set, is_save=False):
        """Универсальный метод для выбора файла"""
        if is_save:
            filename = filedialog.asksaveasfilename(title=title, defaultextension=".bin", filetypes=file_types)
        else:
            filename = filedialog.askopenfilename(title=title, filetypes=file_types)
        
        if filename:
            var_to_set.set(filename)
            return True
        return False
    
    def browse_directory(self, title, var_to_set):
        """Универсальный метод для выбора папки"""
        directory = filedialog.askdirectory(title=title)
        if directory:
            var_to_set.set(directory)
            return True
        return False
    
    def browse_archive(self):
        if self.browse_file("Выберите файл архива", [("BIN files", "*.bin"), ("All files", "*.*")], self.archive_file):
            self.archive_file_display.set(self.format_path(self.archive_file.get()))
            self.settings['archive_file'] = self.archive_file.get()
    
    def browse_archive_folder(self):
        if self.browse_directory("Выберите папку с архивами", self.archive_folder):
            self.archive_folder_display.set(self.format_path(self.archive_folder.get(), True))
            self.settings['archive_folder'] = self.archive_folder.get()
        
    def browse_analyze_folder(self):
        if self.browse_directory("Выберите папку для анализа", self.analyze_folder):
            self.analyze_folder_display.set(self.format_path(self.analyze_folder.get(), True))
            self.settings['analyze_folder'] = self.analyze_folder.get()
        
    def browse_extract_dir(self):
        if self.browse_directory("Выберите папку для извлечения", self.extract_dir):
            self.extract_dir_display.set(self.format_path(self.extract_dir.get(), True))
            self.settings['extract_dir'] = self.extract_dir.get()
    
    def browse_build_dir(self):
        if self.browse_directory("Выберите папку с файлами для упаковки", self.build_dir):
            self.build_dir_display.set(self.format_path(self.build_dir.get(), True))
            self.settings['build_dir'] = self.build_dir.get()
    
    def browse_output_file(self):
        if self.browse_file("Сохранить архив как", [("BIN files", "*.bin"), ("All files", "*.*")], self.output_file, True):
            self.output_file_display.set(self.format_path(self.output_file.get()))
            self.settings['output_file'] = self.output_file.get()
    
    def browse_analyze_file(self):
        if self.browse_file("Выберите файл для анализа", [("BIN files", "*.bin"), ("All files", "*.*")], self.analyze_file):
            self.analyze_file_display.set(self.format_path(self.analyze_file.get()))
            self.settings['analyze_file'] = self.analyze_file.get()
    
    def browse_analyze_report(self):
        if self.browse_file("Сохранить отчет как", [("Text files", "*.txt"), ("All files", "*.*")], self.report_file, True):
            self.report_file_display.set(self.format_path(self.report_file.get()))
            self.settings['report_file'] = self.report_file.get()
    
    def browse_unpack_dir(self):
        if self.browse_directory("Выберите папку с файлами LZSS", self.unpack_dir):
            self.unpack_dir_display.set(self.format_path(self.unpack_dir.get(), True))
            self.settings['unpack_dir'] = self.unpack_dir.get()
    
    def browse_pack_dir(self):
        if self.browse_directory("Выберите папку с файлами", self.pack_dir):
            self.pack_dir_display.set(self.format_path(self.pack_dir.get(), True))
            self.settings['pack_dir'] = self.pack_dir.get()
    
    def browse_bin_file(self):
        if self.browse_file("Выберите исходный BIN файл", [("BIN files", "*.bin"), ("All files", "*.*")], self.bin_file):
            self.bin_file_display.set(self.format_path(self.bin_file.get()))
            self.settings['bin_file'] = self.bin_file.get()
    
    def browse_replacement_file(self):
        if self.browse_file("Выберите файл для замены", [("All files", "*.*")], self.replacement_file):
            self.replacement_file_display.set(self.format_path(self.replacement_file.get()))
            self.settings['replacement_file'] = self.replacement_file.get()
    
    def browse_text_extract_dir(self):
        if self.browse_directory("Выберите папку extracted", self.text_extract_dir):
            self.text_extract_dir_display.set(self.format_path(self.text_extract_dir.get(), True))
            self.settings['text_extract_dir'] = self.text_extract_dir.get()
    
    def browse_text_update_dir(self):
        if self.browse_directory("Выберите папку с файлами для обновления", self.text_update_dir):
            self.text_update_dir_display.set(self.format_path(self.text_update_dir.get(), True))
            self.settings['text_update_dir'] = self.text_update_dir.get()
    
    def browse_emulator_file(self):
        if self.browse_file("Выберите файл эмулятора", [("Executable files", "*.exe"), ("All files", "*.*")], self.emulator_file):
            self.settings['emulator_file'] = self.emulator_file.get()
    
    def analyze_archive(self):
        """Анализ архива или файлов в папке"""
        def do_analyze():
            try:
                report_file = self.report_file.get() if self.report_file.get() else None
                
                if not report_file:
                    messagebox.showerror("Ошибка", "Укажите файл для сохранения отчета")
                    return
                
                if self.analyze_mode.get() == "file":
                    archive = self.analyze_file.get()
                    
                    if not os.path.exists(archive):
                        messagebox.showerror("Ошибка", "Файл контейнера не найден: " + archive)
                        return
                    
                    print("Анализ контейнера " + archive + "...")
                    vanguard_tools.analyze(file_name=archive, output_file=report_file)
                    print("Анализ контейнера завершен!")
                    
                else:
                    folder = self.analyze_folder.get()
                    
                    if not os.path.exists(folder):
                        messagebox.showerror("Ошибка", "Папка не найдена: " + folder)
                        return
                    
                    print("Анализ всех файлов в папке " + folder + "...")
                    vanguard_tools.analyze(folder_path=folder, output_file=report_file)
                    print("Анализ файлов в папке завершен!")
                    
                messagebox.showinfo("Успех", "Анализ завершен!")
                
            except Exception as e:
                messagebox.showerror("Ошибка", "Ошибка при анализе: " + str(e))
                print("Ошибка: " + str(e))
        
        self.run_in_thread(do_analyze)
    
    def extract_files(self):
        """Извлечение файлов из архива(ов)"""
        def do_extract():
            try:
                mode = self.extract_mode.get()
                output_dir = self.extract_dir.get()
                
                if mode == "file":
                    archive = self.archive_file.get()
                    
                    if not os.path.exists(archive):
                        messagebox.showerror("Ошибка", "Файл контейнера не найден: " + archive)
                        return
                    
                    print("Извлечение файлов из " + archive + "...")
                    files_extracted = vanguard_tools.split(
                        file_name=archive, 
                        output_dir=output_dir
                    )
                    print("Извлечение завершено! Извлечено файлов: " + str(files_extracted))
                    
                else:
                    folder = self.archive_folder.get()
                    
                    if not os.path.exists(folder):
                        messagebox.showerror("Ошибка", "Папка с контейнерами не найдена: " + folder)
                        return
                    
                    print("Обработка всех контейнеров в папке " + folder + "...")
                    total_files_extracted = vanguard_tools.split(
                        folder_path=folder,
                        output_dir=output_dir
                    )
                    print("Обработка завершена! Всего извлечено файлов: " + str(total_files_extracted))
                
                messagebox.showinfo("Успех", "Извлечение файлов завершено!")
                
            except Exception as e:
                messagebox.showerror("Ошибка", "Ошибка при извлечении файлов: " + str(e))
                print("Ошибка: " + str(e))
        
        self.run_in_thread(do_extract)
    
    def build_archive(self):
        """Создание контейнера из файлов"""
        def do_build():
            input_dir = self.build_dir.get()
            output_file = self.output_file.get()
            alignment = int(self.alignment.get(), 0)
            
            if not os.path.exists(input_dir):
                messagebox.showerror("Ошибка", "Папка не найдена: " + input_dir)
                return
            
            print("Создание контейнера " + output_file + " из папки " + input_dir + "...")
            
            vanguard_tools.build(
                input_dir=input_dir,
                output_file=output_file,
                alignment=alignment,
                verify=self.verify_build.get(),
                detailed=self.detailed_build.get()
            )
            
            print("Создание контейнера завершено!")
        
        self.execute_operation("создании контейнера", do_build, "Контейнер успешно создан!")
    
    def unpack_lzss(self):
        """Распаковка LZSS файлов"""
        def do_unpack():
            folder = self.unpack_dir.get()
            
            if not folder or not os.path.exists(folder):
                messagebox.showerror("Ошибка", "Папка не найдена: " + folder)
                return
            
            if self.unpack_mode.get() == "all":
                print("Распаковка LZSS файлов по сигнатурам из " + folder + "...")
                count = vanguard_tools.unpack_lzss(unpack_all=True, search_folder=folder)
                print("Распаковка завершена! Обработано файлов: " + str(count))
            else:
                index = int(self.unpack_index.get())
                input_file = os.path.join(folder, "file_{0:04d}.bin".format(index))
                output_file = os.path.join(folder, "file_{0:04d}.lzss-dec".format(index))
                
                if not os.path.exists(input_file):
                    messagebox.showerror("Ошибка", "Входной файл не найден: " + input_file)
                    return
                
                print("Распаковка файла " + input_file + " to " + output_file + "...")
                vanguard_tools.unpack_lzss(input_file=input_file, output_file=output_file, unpack_all=False)
                print("Распаковка файла завершена!")
        
        self.execute_operation("распаковке LZSS", do_unpack, "Распаковка LZSS завершена!")
    
    def pack_lzss(self):
        """Упаковка LZSS файлов"""
        def do_pack():
            folder = self.pack_dir.get()
            
            if not folder or not os.path.exists(folder):
                messagebox.showerror("Ошибка", "Папка не найдена: " + folder)
                return
            
            if self.pack_mode.get() == "all":
                print("Упаковка всех LZSS файлов из " + folder + "...")
                vanguard_tools.repack_lzss("", "", compress_all=True, search_folder=folder)
                print("Упаковка всех файлов завершена!")
            else:
                index = int(self.pack_index.get())
                input_file = os.path.join(folder, "file_{0:04d}.lzss-dec".format(index))
                output_file = os.path.join(folder, "file_{0:04d}.bin".format(index))
                
                if not os.path.exists(input_file):
                    messagebox.showerror("Ошибка", "Входной файл не найден: " + input_file)
                    return
                
                print("Упаковка файла " + input_file + " в " + output_file + "...")
                vanguard_tools.repack_lzss(input_file=input_file, output_file=output_file, compress_all=False)
                print("Упаковка файла завершена!")
        
        self.execute_operation("упаковке LZSS", do_pack, "Упаковка LZSS завершена!")
    
    def replace_file_in_image(self):
        """Замена файла в PSX образе с использованием psx-mode2-en.exe"""
        def do_replace():            
            bin_file = self.bin_file.get()
            target = self.target_file.get()
            replacement = self.replacement_file.get()
            
            if not bin_file or not os.path.exists(bin_file):
                messagebox.showerror("Ошибка", "BIN файл образа не найден: " + bin_file)
                return
            
            if not replacement or not os.path.exists(replacement):
                messagebox.showerror("Ошибка", "Файл для замены не найден: " + replacement)
                return
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            util_path = os.path.join(script_dir, "tools\\psx-mode2-en.exe")
            
            if not os.path.exists(util_path):
                messagebox.showerror("Ошибка", "Утилита psx-mode2-en.exe не найдена в папке tools!")
                return
            
            print("\nЗамена файла " + target + " в PSX образе...")
            
            cmd = [util_path, bin_file, target, replacement]
            print("Выполняется команда: " + ' '.join(cmd))
            
            if os.name == 'nt':
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    creationflags=0x08000000
                )
            else:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
            stdout, stderr = process.communicate()
            class Result(object):
                pass
            result = Result()
            result.stdout = stdout
            result.stderr = stderr
            result.returncode = process.returncode
            
            if result.stdout:
                print("Вывод утилиты:")
                print(result.stdout)
            
            if result.stderr:
                print("Ошибки утилиты:")
                print(result.stderr)
            
            if result.returncode == 0:
                print("Замена файла завершена успешно!")
                messagebox.showinfo("Успех", "Замена файла в PSX образе завершена успешно!")
            else:
                print("Ошибка при замене файла! Код возврата: " + str(result.returncode))
                messagebox.showerror("Ошибка", "Ошибка при замене файла! Код возврата: " + str(result.returncode))
        
        self.run_in_thread(do_replace)
    
    def launch_emulator(self):
        """Запуск эмулятора с текущим BIN файлом и аргументами"""
        def do_launch():            
            emulator_path = self.emulator_file.get()
            bin_file_path = self.bin_file.get()
            emulator_args = self.emulator_args.get()
            
            if not emulator_path or not os.path.exists(emulator_path):
                messagebox.showerror("Ошибка", "Файл эмулятора не найден или не указан")
                return
            
            if not bin_file_path or not os.path.exists(bin_file_path):
                messagebox.showerror("Ошибка", "BIN файл образа не найден или не указан")
                return
            
            print("Запуск эмулятора: " + emulator_path)
            print("Аргументы: " + emulator_args)
            print("Файл образа: " + bin_file_path)
            
            cmd = [emulator_path]
            
            if emulator_args.strip():
                args_list = shlex.split(emulator_args)
                cmd.extend(args_list)
            
            cmd.append(bin_file_path)
            
            print("Полная команда: " + ' '.join(cmd))
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            print("Эмулятор запущен!")
        
        self.run_in_thread(do_launch)
    
    def open_text_file(self):
        """Открытие TXT файла по индексу"""
        try:
            folder = self.text_update_dir.get()
            index = int(self.text_update_index.get())
            
            if not folder or not os.path.exists(folder):
                messagebox.showerror("Ошибка", "Папка не найдена: " + folder)
                return
            
            txt_file = Path(folder) / ("file_{0:04d}-text.txt".format(index))
            
            if not txt_file.exists():
                messagebox.showerror("Ошибка", "TXT файл не найден: " + str(txt_file))
                return
            
            if os.name == 'nt':
                os.startfile(str(txt_file))
            else:
                subprocess.Popen(['xdg-open', str(txt_file)])
            
            print("Открыт файл: " + str(txt_file))
            
        except Exception as e:
            messagebox.showerror("Ошибка", "Ошибка при открытии файла: " + str(e))
            print("Ошибка: " + str(e))
    
    def restore_from_backup(self):
        """Восстановление файла из резервной копии"""
        def do_restore():
            try:
                folder = self.text_update_dir.get()
                index = int(self.text_update_index.get())
                
                if not folder or not os.path.exists(folder):
                    messagebox.showerror("Ошибка", "Папка не найдена: " + folder)
                    return
                
                target_file_bin = Path(folder) / ("file_{0:04d}.bin".format(index))
                target_file_lzss = Path(folder) / ("file_{0:04d}.lzss-dec".format(index))
                
                backup_file_bin = Path(str(target_file_bin) + '.bak')
                backup_file_lzss = Path(str(target_file_lzss) + '.bak')
                
                target_file = None
                backup_file = None
                file_type = ""
                
                if target_file_lzss.exists() and backup_file_lzss.exists():
                    target_file = target_file_lzss
                    backup_file = backup_file_lzss
                    file_type = "LZSS-dec"
                elif target_file_bin.exists() and backup_file_bin.exists():
                    target_file = target_file_bin
                    backup_file = backup_file_bin
                    file_type = "BIN"
                else:
                    available_backups = []
                    if backup_file_lzss.exists():
                        available_backups.append("file_{0:04d}.lzss-dec.bak".format(index))
                    if backup_file_bin.exists():
                        available_backups.append("file_{0:04d}.bin.bak".format(index))
                    
                    if not available_backups:
                        messagebox.showerror("Ошибка", 
                                           "Резервные копии не найдены для файла с индексом {0}\nОжидаемые файлы:\n- {1}\n- {2}".format(
                                           index, backup_file_lzss.name, backup_file_bin.name))
                        return
                    else:
                        if backup_file_lzss.exists():
                            target_file = target_file_lzss
                            backup_file = backup_file_lzss
                            file_type = "LZSS-dec"
                        else:
                            target_file = target_file_bin
                            backup_file = backup_file_bin
                            file_type = "BIN"
                
                print("[+] Восстановление файла из резервной копии:")
                print("   Целевой файл: " + target_file.name)
                print("   Резервная копия: " + backup_file.name)
                self.text_status_var.set("Restoring...")
                
                if not messagebox.askyesno("Подтверждение", 
                                         "Восстановить файл {0} из резервной копии?\n\nТекущий файл будет перезаписан!".format(target_file.name)):
                    print("[!] Восстановление отменено пользователем")
                    self.text_status_var.set("Восстановление отменено")
                    return
                
                shutil.copy2(backup_file, target_file)
                
                print("[+] Файл успешно восстановлен из резервной копии!")
                print("    Размер восстановленного файла: " + str(target_file.stat().st_size) + " bytes")
                
                self.text_status_var.set("Файл восстановлен")
                messagebox.showinfo("Успех", 
                                  "Файл успешно восстановлен из резервной копии!\n\n[+] Восстановленный файл: {0}\n[+] Источник: {1}\n[+] Размер: {2} bytes".format(
                                  target_file.name, backup_file.name, target_file.stat().st_size))
                
            except Exception as e:
                self.text_status_var.set("Ошибка восстановления")
                messagebox.showerror("Ошибка", "Ошибка при восстановлении файла: " + str(e))
                print("[!] Ошибка: " + str(e))
                traceback.print_exc()
        
        self.run_in_thread(do_restore)
    
    def debug_encoding_table(self):
        """Диагностика таблицы кодировки"""
        def do_debug():
            try:
                vanguard_text.debug_encoding_table()
            except Exception as e:
                print("[!] Ошибка диагностики кодировки: " + str(e))
                traceback.print_exc()
        
        self.run_in_thread(do_debug)
    
    def open_encoding_table(self):
        """Открывает файл таблицы кодировки для редактирования"""
        def do_open():
            try:
                encoding_file = Path("tools/encoding_table.txt")
                
                if not encoding_file.exists():
                    messagebox.showerror("Ошибка", 
                                      "Файл таблицы кодировки не найден:\n{0}\n\nСоздайте файл вручную или проверьте путь.".format(encoding_file))
                    return
                
                print("[+] Открытие таблицы кодировки: " + str(encoding_file))
                
                if os.name == 'nt':
                    os.startfile(str(encoding_file))
                else:
                    for editor in ['xdg-open', 'gedit', 'vim', 'nano']:
                        try:
                            subprocess.Popen([editor, str(encoding_file)])
                            break
                        except OSError:
                            continue
                    else:
                        print("[!] Не найден подходящий текстовый редактор")
                        messagebox.showerror("Ошибка", "Не найден текстовый редактор для открытия файла")
                        return
                
                print(" Таблица кодировки открыта для редактирования")
                print(" После изменений используйте 'Диагностика кодировки'")
                
            except Exception as e:
                messagebox.showerror("Ошибка", "Не удалось открыть таблицу кодировки: " + str(e))
                print("[!] Ошибка открытия таблицы кодировки: " + str(e))
        
        self.run_in_thread(do_open)
    
    def find_text_blocks_improved(self):
        """Улучшенный поиск текстовых блоков с использованием vanguard_text.py"""
        def do_find():
            try:
                folder = self.text_extract_dir.get()
                
                if not folder or not os.path.exists(folder):
                    messagebox.showerror("Ошибка", "Папка не найдена: " + folder)
                    return
                
                max_blocks = int(self.text_max_blocks.get())
                min_length = int(self.text_min_length.get())
                
                print("[+] Улучшенный поиск текстовых блоков в папке: " + folder)
                self.text_status_var.set("Поиск текстовых блоков...")
                
                if self.text_find_mode.get() == "all":
                    result = vanguard_text.find_text_in_folder(folder, max_blocks, min_length)
                    
                    self.text_status_var.set("Найдено {0} блоков в {1} файлах".format(result['total_blocks'], result['processed_files']))
                    messagebox.showinfo("Успех", 
                                      "Поиск текстовых блоков завершен!\nОбработано файлов: {0}\nНайдено блоков: {1}\nНайдено строк: {2}".format(
                                      result['processed_files'], result['total_blocks'], result['total_strings']))
                    
                else:
                    index = int(self.text_find_index.get())
                    file_path = Path(folder) / ("file_{0:04d}.bin".format(index))
                    
                    unpack_file = Path(str(file_path) + '.lzss-dec')
                    if unpack_file.exists():
                        input_file = str(unpack_file)
                        file_type = "LZSS-dec"
                    else:
                        input_file = str(file_path)
                        file_type = "BIN"
                    
                    output_file = str(file_path.parent / (file_path.stem + "-text.txt"))
                    
                    if not os.path.exists(input_file):
                        messagebox.showerror("Ошибка", "Файл не найден: " + input_file)
                        return
                    
                    print(" Поиск текстовых блоков в файле [{0}]: {1}".format(file_type, Path(input_file).name))
                    self.text_status_var.set("Поиск в file_{0:04d}...".format(index))
                    
                    try:
                        blocks = vanguard_text.find_text_blocks_improved(input_file, max_blocks, min_length)
                        print(" Результаты поиска:")
                        print("   Найдено блоков: " + str(len(blocks)))
                        
                        if blocks:
                            vanguard_text.save_text_blocks_to_file(input_file, blocks, output_file)
                            print("    Блоки сохранены в: " + Path(output_file).name)
                            
                            blocks_with_headers = sum(1 for b in blocks if b['has_header'])
                            validated_blocks = sum(1 for b in blocks if b.get('validated', False))
                            total_strings = sum(block['string_count'] for block in blocks)
                            total_pointers = sum(len(block['pointers']) for block in blocks)
                            
                            print("    Блоков с заголовками: {0}/{1}".format(blocks_with_headers, len(blocks)))
                            print("    Валидированных блоков: {0}/{1}".format(validated_blocks, len(blocks)))
                            print("    Всего строк: " + str(total_strings))
                            print("    Всего поинтеров: " + str(total_pointers))
                            
                            self.text_status_var.set("Найдено {0} блоков, {1} строк".format(len(blocks), total_strings))
                            
                            messagebox.showinfo("Успех", 
                                              "Найдено текстовых блоков: {0}\nСтрок: {1}\nВалидированных: {2}\nСохранено в: {3}".format(
                                              len(blocks), total_strings, validated_blocks, Path(output_file).name))
                        else:
                            self.text_status_var.set("Блоки не найдены")
                            messagebox.showinfo("Информация", "Текстовые блоки не найдены")
                            
                    except Exception as e:
                        self.text_status_var.set("Ошибка поиска")
                        messagebox.showerror("Ошибка", "Ошибка при поиске текстовых блоков: " + str(e))
                        print("[!] Ошибка: " + str(e))
                        
            except Exception as e:
                self.text_status_var.set("Ошибка")
                messagebox.showerror("Ошибка", "Ошибка при поиске текстовых блоков: " + str(e))
                print("[!] Ошибка: " + str(e))
        
        self.run_in_thread(do_find)

    def update_text_translation_improved(self):
        """Улучшенное обновление файла с переводом с использованием vanguard_text.py"""
        def do_update():
            try:
                folder = self.text_update_dir.get()
                index = int(self.text_update_index.get())
                
                if not folder or not os.path.exists(folder):
                    messagebox.showerror("Ошибка", "Папка не найдена: " + folder)
                    return
                
                target_file_bin = Path(folder) / ("file_{0:04d}.bin".format(index))
                target_file_lzss = Path(folder) / ("file_{0:04d}.lzss-dec".format(index))
                
                if target_file_lzss.exists():
                    target_file = target_file_lzss
                    file_type = "LZSS-dec"
                elif target_file_bin.exists():
                    target_file = target_file_bin
                    file_type = "BIN"
                else:
                    messagebox.showerror("Ошибка", "Файл не найден для индекса " + str(index))
                    self.text_status_var.set("Ошибка: файл не найден")
                    return
                
                translation_file = Path(folder) / ("file_{0:04d}-text.txt".format(index))
                
                if not translation_file.exists():
                    messagebox.showerror("Ошибка", "Файл перевода не найден: " + str(translation_file))
                    return
                
                print(" Обновление файла с переводом: " + translation_file.name)
                print(" Целевой файл [{0}]: {1}".format(file_type, target_file.name))
                self.text_status_var.set("Обновление перевода...")
                
                try:
                    success = vanguard_text.update_all_blocks_in_file(
                        original_filename=str(target_file),
                        translation_filename=str(translation_file),
                        output_filename=str(target_file),
                        use_translate=True
                    )
                    
                    if success:
                        print(" Файл успешно обновлен!")
                        self.text_status_var.set("Обновление завершено")
                        messagebox.showinfo("Успех", 
                                          "Файл успешно обновлен!\n Целевой файл: {0}\n Создана резервная копия: {1}.bak".format(
                                          target_file.name, target_file.name))
                    else:
                        print("[!] Ошибка при обновлении файла")
                        self.text_status_var.set("Ошибка обновления")
                        messagebox.showerror("Ошибка", "Не удалось обновить файл!")
                        
                except Exception as e:
                    self.text_status_var.set("Ошибка обновления")
                    messagebox.showerror("Ошибка", "Ошибка при обновлении файла: " + str(e))
                    print("[!] Ошибка: " + str(e))
                    traceback.print_exc()
                            
            except Exception as e:
                self.text_status_var.set("Ошибка")
                messagebox.showerror("Ошибка", "Ошибка при обновлении файла: " + str(e))
                print("[!] Ошибка: " + str(e))
        
        self.run_in_thread(do_update)
    
def main():
    # try:
        # if os.name == 'nt':
            # ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    # except:
        # pass
    root = tk.Tk()
    app = VanguardToolsGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()