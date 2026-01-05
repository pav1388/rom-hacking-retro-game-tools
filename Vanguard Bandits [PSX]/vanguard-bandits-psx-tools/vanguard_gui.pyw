# Vanguard Bandits PSX Tools GUI by pav13 + deepseek
# psx-mode2-en.exe by https://www.romhacking.net/utilities/1417/

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys
import threading
from pathlib import Path
import json
import pickle
import re
import vanguard_tools

try:
    import ctypes
    if os.name == 'nt':
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
except:
    pass

class VanguardToolsGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Vanguard Bandits PSX Tools GUI v0.13")
        
        # Инициализация переменных
        self.settings_dir = Path("__pycache__")
        self.settings_file = self.settings_dir / "gui_settings.pkl"
        self.settings = {}
        
        # Основные переменные для вкладок
        self.unpack_mode = tk.StringVar()
        self.unpack_index = tk.StringVar()
        self.pack_mode = tk.StringVar()
        self.pack_index = tk.StringVar()
        
        # Загружаем настройки и инициализируем интерфейс
        self.load_settings()
        self.initialize_interface()
        
        # Применяем тему и настройки
        self.apply_initial_settings()
        
    def initialize_interface(self):
        """Инициализация всего интерфейса"""
        # Устанавливаем геометрию из настроек или по умолчанию
        if 'window_geometry' in self.settings:
            self.root.geometry(self.settings['window_geometry'])
        else:
            self.root.geometry("1000x600")
        
        # Устанавливаем тему из настроек
        self.theme_mode = self.settings.get('theme_mode', 'light')
        self.paned_position = self.settings.get('paned_position', 700)
        
        # Создаем основной интерфейс
        self.create_split_layout()
        
        # Восстанавливаем последнюю активную вкладку
        current_tab = self.settings.get('current_tab', 0)
        if 0 <= current_tab < self.notebook.index('end'):
            self.notebook.select(current_tab)
        
        # Инициализация размера шрифта консоли
        self.current_font_size = self.settings.get('console_font_size', 8)
        self.base_font_size = self.current_font_size
    
        # Настройка вывода и событий
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
        
        # Левый фрейм для вкладок (70%)
        self.left_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.left_frame, weight=7)
        
        # Правый фрейм для консоли (30%)
        self.right_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.right_frame, weight=3)
        
        # Восстанавливаем положение разделителя
        self.root.update()
        self.root.after(100, self.restore_paned_position)
        
        # Создаем вкладки и консоль
        self.create_tabs()
        self.create_console_panel(self.right_frame)
    
    def create_tabs(self):
        """Создает все вкладки приложения"""
        self.notebook = ttk.Notebook(self.left_frame)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Список вкладок для создания
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
            # Вызываем соответствующий метод создания вкладки
            getattr(self, f'create_{method_name}')(frame)
    
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
        # Анализ таблицы содержания
        ttk.Label(frame, text="Анализ структуры архива или файлов в папке:", 
                 font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        
        # Режим анализа
        self.analyze_mode = tk.StringVar(value=self.settings.get('analyze_mode', "file"))
        ttk.Radiobutton(frame, text="Анализ файла контейнера:", 
                       variable=self.analyze_mode, value="file").grid(
                       row=1, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        
        # Файл для анализа (режим файла)
        self.analyze_file = tk.StringVar(value=self.settings.get('analyze_file', "EPICA.BIN"))
        self.analyze_file_display = tk.StringVar()
        self.create_common_file_selection(frame, 2, "Файл для анализа:", 
                                        self.analyze_file, self.analyze_file_display,
                                        self.browse_analyze_file)
        
        ttk.Radiobutton(frame, text="Анализ всех файлов в папке:", 
                       variable=self.analyze_mode, value="folder").grid(
                       row=3, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        
        # Папка для анализа (режим папки)
        self.analyze_folder = tk.StringVar(value=self.settings.get('analyze_folder', "extracted"))
        self.analyze_folder_display = tk.StringVar()
        self.create_common_file_selection(frame, 4, "Папка для анализа:", 
                                        self.analyze_folder, self.analyze_folder_display,
                                        self.browse_analyze_folder, is_directory=True)
        
        # Файл отчета
        ttk.Label(frame, text="Файл отчета:").grid(row=5, column=0, sticky='w', padx=5, pady=5)
        self.report_file = tk.StringVar(value=self.settings.get('report_file', "report-analysis.txt"))
        self.report_file_display = tk.StringVar()
        ttk.Entry(frame, textvariable=self.report_file, width=50).grid(row=5, column=1, padx=5, pady=5)
        ttk.Button(frame, text="Обзор", command=self.browse_analyze_report).grid(row=5, column=2, padx=5, pady=5)
        
        # Кнопка анализа
        ttk.Button(frame, text="Анализировать", command=self.analyze_archive).grid(row=6, column=0, columnspan=3, pady=10)
    
    def create_extract_tab(self, frame):
        """Вкладка для извлечения файлов из архива"""
        ttk.Label(frame, text="Извлечение файлов из контейнеров:", 
                 font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        
        # Режим извлечения
        self.extract_mode = tk.StringVar(value=self.settings.get('extract_mode', "file"))
        ttk.Radiobutton(frame, text="Извлечь из одного файла контейнера  (например, EPICA.BIN):", 
                       variable=self.extract_mode, value="file").grid(
                       row=1, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        
        # Файл архива (режим файла)
        self.archive_file = tk.StringVar(value=self.settings.get('archive_file', "EPICA.BIN"))
        self.archive_file_display = tk.StringVar()
        self.create_common_file_selection(frame, 2, "Файл контейнера:", 
                                        self.archive_file, self.archive_file_display,
                                        self.browse_archive)
        
        ttk.Radiobutton(frame, text="Извлечь из всех контейнеров в папке:", 
                       variable=self.extract_mode, value="folder").grid(
                       row=3, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        
        # Папка с архивами (режим папки)
        self.archive_folder = tk.StringVar(value=self.settings.get('archive_folder', "archives"))
        self.archive_folder_display = tk.StringVar()
        self.create_common_file_selection(frame, 4, "Папка с контейнерами:", 
                                        self.archive_folder, self.archive_folder_display,
                                        self.browse_archive_folder, is_directory=True)
        
        # Папка для извлечения
        self.extract_dir = tk.StringVar(value=self.settings.get('extract_dir', "extracted"))
        self.extract_dir_display = tk.StringVar()
        self.create_common_file_selection(frame, 5, "Папка для извлечения:", 
                                        self.extract_dir, self.extract_dir_display,
                                        self.browse_extract_dir, is_directory=True)
        
        # Кнопка извлечения
        ttk.Button(frame, text="Извлечь файлы", 
                  command=self.extract_files).grid(row=6, column=0, columnspan=3, pady=10)
    
    def create_lzss_tab(self, frame):
        """Вкладка для операций LZSS"""
        # Распаковка LZSS
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
        
        ttk.Label(frame, text="(file_XXXX.bin → file_XXXX.lzss-dec)", 
                 font=('Arial', 8)).grid(
                 row=4, column=1, columnspan=3, sticky='w', padx=5, pady=2)
        
        ttk.Button(frame, text="Распаковать файл/-ы", 
                  command=self.unpack_lzss).grid(row=5, column=0, columnspan=4, pady=10)
        
        # Упаковка LZSS
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
        
        ttk.Label(frame, text="(file_XXXX.lzss-dec → file_XXXX.bin)", 
                 font=('Arial', 8)).grid(
                 row=11, column=1, columnspan=3, sticky='w', padx=5, pady=2)
        
        ttk.Button(frame, text="Упаковать файл/-ы", 
                  command=self.pack_lzss).grid(row=12, column=0, columnspan=4, pady=10)
    
    def create_found_text_tab(self, frame):
        """Вкладка для поиска и работы с текстом"""
        # === ПОИСК ТЕКСТОВЫХ БЛОКОВ ===
        ttk.Label(frame, text="Поиск текстовых блоков:", 
                 font=('Arial', 9, 'bold')).grid(row=1, column=0, columnspan=4, sticky='w', padx=5, pady=(10,5))
        
        self.text_extract_dir = tk.StringVar(value=self.settings.get('text_extract_dir', "extracted"))
        self.text_extract_dir_display = tk.StringVar()
        self.create_common_file_selection(frame, 2, "Папка с файлами:", 
                                        self.text_extract_dir, self.text_extract_dir_display,
                                        self.browse_text_extract_dir, is_directory=True, width=50)
        
        # Режим поиска
        self.text_find_mode = tk.StringVar(value=self.settings.get('text_find_mode', "single"))
        ttk.Radiobutton(frame, text="Поиск в файле с индексом:", 
                       variable=self.text_find_mode, value="single").grid(
                       row=3, column=0, sticky='w', padx=5, pady=5)
        
        self.text_find_index = tk.StringVar(value=self.settings.get('text_find_index', "0"))
        self.create_index_control(frame, 3, "", self.text_find_index, command_col=1)
        
        ttk.Radiobutton(frame, text="Поиск во всех файлах", 
                       variable=self.text_find_mode, value="all").grid(
                       row=4, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        
        # Дополнительные параметры поиска
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
        
        # === ОБНОВЛЕНИЕ ФАЙЛА С ПЕРЕВОДОМ ===
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
        
        # Кнопки управления переводом
        translate_buttons_frame = ttk.Frame(frame)
        translate_buttons_frame.grid(row=14, column=0, columnspan=4, sticky='w', padx=5, pady=5)
        
        ttk.Button(translate_buttons_frame, text="Открыть файл перевода", 
              command=self.open_text_file).pack(side='left', padx=(0,10))
        ttk.Button(translate_buttons_frame, text="Восстановить из копии", 
              command=self.restore_from_backup).pack(side='left', padx=(0,10))
        ttk.Button(translate_buttons_frame, text="Применить перевод", 
              command=self.update_text_translation_improved).pack(side='left', padx=(0,10))
        
        # === УПРАВЛЕНИЕ ТАБЛИЦЕЙ КОДИРОВКИ ===
        # ttk.Separator(frame, orient='horizontal').grid(row=15, column=0, columnspan=4, sticky='ew', pady=10)
        
        encoding_buttons_frame = ttk.Frame(frame)
        encoding_buttons_frame.grid(row=16, column=0, columnspan=4, sticky='w', padx=5, pady=5)
        
        ttk.Button(encoding_buttons_frame, text="Таблица кодировки", 
                  command=self.open_encoding_table).pack(side='left', padx=(0,10))
        ttk.Button(encoding_buttons_frame, text="Диагностика таблицы кодировки", 
              command=self.debug_encoding_table).pack(side='left', padx=(0,10))
              
        # Информация об обновлении
        update_info_texts = [
            "* Создаются резервные копии (.bak) с защитой от перезаписи.   * Не забываем упаковать LZSS после перевода!",
            "* Приоритет: file_XXXX.lzss-dec, если его нет, то file_XXXX.bin.         *** ТЕСТОВЫЙ ФУНКЦИНАЛ ***",
        ]
        
        for i, text in enumerate(update_info_texts, 17):
            ttk.Label(frame, text=text, font=('Arial', 9)).grid(
                row=i, column=0, columnspan=4, sticky='w', padx=5, pady=1)
        
        # === СТАТУС И ИНФОРМАЦИЯ ===
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
        
        # Опции
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
        self.target_file = tk.StringVar(value=self.settings.get('target_file', "\EPICA.BIN"))
        target_combo = ttk.Combobox(frame, textvariable=self.target_file, 
                                   values=["\EPICA.BIN", "\SLUS_010.70", "\STELLA.XA", "\SYSTEM.CNF"], 
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
        
        # Запуск эмулятора
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
        
        # Переключатель темы
        ttk.Label(frame, text="Тема приложения:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.theme_var = tk.StringVar(value=self.theme_mode)
        ttk.Radiobutton(frame, text="Светлая", variable=self.theme_var, value="light", 
                       command=self.apply_theme).grid(row=2, column=0, sticky='w', padx=5, pady=2)
        ttk.Radiobutton(frame, text="Тёмная", variable=self.theme_var, value="dark", 
                       command=self.apply_theme).grid(row=3, column=0, sticky='w', padx=5, pady=2)
        
        ttk.Separator(frame, orient='horizontal').grid(row=4, column=0, columnspan=2, sticky='ew', pady=10)
        
        ttk.Label(frame, text="Настройки и параметры сохраняются при закрытии приложения.", 
                 font=('Arial', 10, 'bold')).grid(row=5, column=0, columnspan=2, sticky='w', padx=5, pady=5)
        ttk.Label(frame, text="Для сброса настроек удалить папку '__pycache__'.", 
                 font=('Arial', 10, 'bold')).grid(row=6, column=0, columnspan=2, sticky='w', padx=5, pady=5)

    # УНИВЕРСАЛЬНЫЕ МЕТОДЫ ДЛЯ РАБОТЫ С ПУТЯМИ И ИНДЕКСАМИ
    
    def format_path(self, path, is_directory=False):
        """Форматирует путь для отображения (универсальный метод)"""
        if not path:
            return ""
        path_obj = Path(path)
        if is_directory:
            parts = list(path_obj.parts)
            if len(parts) >= 2:
                return f".../{parts[-2]}/{parts[-1]}"
            return path
        else:
            if path_obj.is_file():
                return f".../{path_obj.parent.name}/{path_obj.name}"
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
    
    # МЕТОДЫ ДЛЯ РАБОТЫ С НАСТРОЙКАМИ
    
    def load_settings(self):
        """Загружает настройки из файла"""
        try:
            self.settings_dir.mkdir(exist_ok=True)
            if self.settings_file.exists():
                with open(self.settings_file, 'rb') as f:
                    self.settings = pickle.load(f)
            
            # Инициализируем размер шрифта консоли если его нет в настройках
            if 'console_font_size' not in self.settings:
                self.settings['console_font_size'] = 8
                
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")
            self.settings = {}
    
    def save_settings(self):
        """Сохраняет настройки в файл"""
        try:
            self.save_field_values()
            self.settings['current_tab'] = self.notebook.index(self.notebook.select())
            self.save_paned_position()
            
            # Сохраняем размер шрифта консоли
            if hasattr(self, 'current_font_size'):
                self.settings['console_font_size'] = self.current_font_size
            
            self.settings_dir.mkdir(exist_ok=True)
            with open(self.settings_file, 'wb') as f:
                pickle.dump(self.settings, f)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
    
    def save_field_values(self):
        """Сохраняет значения всех полей в настройки"""
        # Собираем все настройки в словарь для удобства
        settings_map = {
            # Вкладка извлечения
            'extract_mode': self.extract_mode,
            'archive_file': self.archive_file,
            'archive_folder': self.archive_folder,
            'extract_dir': self.extract_dir,
            # Вкладка сборки
            'alignment': self.alignment,
            'verify_build': self.verify_build,
            'detailed_build': self.detailed_build,
            # Вкладка анализа
            'analyze_mode': self.analyze_mode,
            'analyze_file': self.analyze_file,
            'analyze_folder': self.analyze_folder,
            'report_file': self.report_file,
            # Вкладка LZSS
            'unpack_mode': self.unpack_mode,
            'unpack_index': self.unpack_index,
            'pack_mode': self.pack_mode,
            'pack_index': self.pack_index,
            # Вкладка замены в PSX образе
            'target_file': self.target_file,
            'emulator_file': self.emulator_file,
            'emulator_args': self.emulator_args,
            # Вкладка текста
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
                self.settings[key] = getattr(self, key).get()
    
    def on_closing(self):
        """Сохраняет настройки перед закрытием"""
        if hasattr(self, 'main_paned'):
            self.save_paned_position()
        if self.root.state() == 'normal':
            self.settings['window_geometry'] = self.root.geometry()
        
        self.save_settings()
        self.root.destroy()
    
    # МЕТОДЫ ДЛЯ РАБОТЫ С ИНТЕРФЕЙСОМ
    
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
            print(f"Ошибка при восстановлении положения разделителя: {e}")
    
    def save_paned_position(self):
        """Сохраняет текущее положение разделителя"""
        if hasattr(self, 'main_paned'):
            try:
                current_pos = self.main_paned.sashpos(0)
                if current_pos and current_pos > 0:
                    self.settings['paned_position'] = current_pos
            except Exception as e:
                print(f"Ошибка при сохранении положения разделителя: {e}")
    
    # МЕТОДЫ ДЛЯ РАБОТЫ С ТЕМОЙ
    
    def set_theme(self, theme_mode):
        """Устанавливает тему приложения"""
        self.theme_mode = theme_mode
        style = ttk.Style()
        
        if theme_mode == 'dark':
            self.apply_dark_theme(style)
        else:
            self.apply_light_theme(style)
        
        # Сохраняем тему в настройках
        self.settings['theme_mode'] = theme_mode
    
    def apply_dark_theme(self, style):
        """Применяет темную тему"""
        try:
            style.theme_use('clam')
        except:
            style.theme_use('default')
        
        # Цвета для темной темы
        bg_color = '#2b2b2b'
        fg_color = 'white'
        entry_bg = '#3c3c3c'
        button_bg = '#4c4c4c'
        selected_bg = '#5c5c5c'
        
        # Настраиваем основные цвета
        self.root.configure(bg=bg_color)
        
        # Конфигурация стилей
        self.configure_theme_styles(style, bg_color, fg_color, entry_bg, selected_bg, button_bg)
        
        # Настройка текстовых полей
        if hasattr(self, 'log_text'):
            self.log_text.configure(
                bg='#2d2d2d', 
                fg='#e0e0e0', 
                insertbackground='#e0e0e0',
                selectbackground='#555555',
                inactiveselectbackground='#3d3d3d'
            )
        
        # Настройка состояний
        self.configure_theme_states(style, selected_bg, fg_color, entry_bg, button_bg, bg_color)
        
        # Принудительно обновляем все виджеты
        self.update_all_widgets(bg_color, fg_color)
    
    def apply_light_theme(self, style):
        """Применяет светлую тему"""
        try:
            style.theme_use('clam')
        except:
            style.theme_use('default')
                
        # Стандартные цвета
        bg_color = 'SystemButtonFace'
        fg_color = 'black'
        entry_bg = 'white'
        selected_bg = 'SystemHighlight'
        selected_fg = 'SystemHighlightText'
        active_fg = fg_color
        
        self.root.configure(bg=bg_color)
        
        # Сбрасываем стили к стандартным
        self.configure_theme_styles(style, bg_color, fg_color, entry_bg, selected_bg, selected_fg)
        
        # Сбрасываем текстовые поля
        if hasattr(self, 'log_text'):
            self.log_text.configure(
                bg='white', 
                fg='black', 
                insertbackground='black',
                selectbackground='#c0c0c0',
                inactiveselectbackground='#e0e0e0'
            )
        
        # Сбрасываем состояния
        self.configure_theme_states(style, selected_bg, active_fg, entry_bg, bg_color, bg_color)
        
        # Принудительно обновляем все виджеты
        self.update_all_widgets(bg_color, fg_color)
    
    def configure_theme_styles(self, style, bg_color, fg_color, field_bg, select_bg, select_fg):
        """Конфигурирует основные стили темы"""
        style.configure('.', 
                       background=bg_color, 
                       foreground=fg_color,
                       fieldbackground=field_bg,
                       selectbackground=select_bg,
                       selectforeground=select_fg)
        
        # Конфигурация отдельных элементов
        elements = ['TFrame', 'TLabel', 'TButton', 'TEntry', 'TCombobox', 
                   'TCheckbutton', 'TRadiobutton', 'TNotebook', 'TNotebook.Tab', 'TSeparator']
        
        for element in elements:
            style.configure(element, background=bg_color, foreground=fg_color)
        
        # Специфические настройки
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
            
            # Рекурсивно обходим дочерние виджеты
            try:
                for child in widget.winfo_children():
                    update_widget(child)
            except:
                pass
        
        update_widget(self.root)
    
    def apply_theme(self):
        """Применяет выбранную тему"""
        self.set_theme(self.theme_var.get())
    
    def apply_theme_force(self):
        """Принудительно применяет тему ко всем элементам"""
        self.set_theme(self.theme_mode)
        self.root.update_idletasks()
    
    # МЕТОДЫ ДЛЯ РАБОТЫ С КОНСОЛЬЮ
    
    def create_console_panel(self, parent):
        """Создает панель консоли с постоянным выводом и ручным управлением шрифтом"""
        console_frame = ttk.LabelFrame(parent, text="Консольный вывод", padding=5)
        console_frame.pack(fill='both', expand=True)
        
        # Загружаем сохраненный размер шрифта или используем значение по умолчанию
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
        
        # Левая часть - основные кнопки
        left_frame = ttk.Frame(button_frame)
        left_frame.pack(side='left')
        
        ttk.Button(left_frame, text="Очистить лог", command=self.clear_log).pack(side='left', padx=(0, 5))
        ttk.Button(left_frame, text="Копировать", command=self.copy_log).pack(side='left')
        
        # Правая часть - управление шрифтом
        right_frame = ttk.Frame(button_frame)
        right_frame.pack(side='right')
        
        # Метка с текущим размером шрифта
        self.font_size_label = ttk.Label(right_frame, text=f"{self.current_font_size}pt", width=4)
        self.font_size_label.pack(side='left', padx=(5, 2))
        
        # Кнопки изменения размера шрифта
        ttk.Button(right_frame, text="a-", width=3, 
                   command=lambda: self.change_font_size(-1)).pack(side='left', padx=(0, 2))
        ttk.Button(right_frame, text="A+", width=3, 
                   command=lambda: self.change_font_size(1)).pack(side='left')

    def change_font_size(self, delta):
        """Ручное изменение размера шрифта с сохранением"""
        min_font_size = 6
        max_font_size = 20
        
        new_size = self.current_font_size + delta
        
        if min_font_size <= new_size <= max_font_size:
            self.current_font_size = new_size
            
            # Применяем новый шрифт
            self.log_text.configure(font=('Consolas', self.current_font_size))
            self.font_size_label.config(text=f"{self.current_font_size}pt")
            
            # Сохраняем в настройках
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
        """Очистить лог"""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
    
    def copy_log(self):
        """Копирует содержимое лога в буфер обмена"""
        try:
            self.log_text.config(state='normal')
            text = self.log_text.get(1.0, tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.log_text.config(state='disabled')
        except Exception as e:
            print(f"Ошибка при копировании лога: {e}")
    
    # УНИВЕРСАЛЬНЫЕ МЕТОДЫ ДЛЯ ВЫПОЛНЕНИЯ ОПЕРАЦИЙ
    
    def run_in_thread(self, func, *args):
        """Запускает функцию в отдельном потоке"""
        thread = threading.Thread(target=func, args=args)
        thread.daemon = True
        thread.start()
    
    def execute_operation(self, operation_name, operation_func, success_message=None):
        """Универсальный метод для выполнения операций с обработкой ошибок"""
        def do_operation():
            try:
                operation_func()
                if success_message:
                    messagebox.showinfo("Успех", success_message)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при {operation_name}: {str(e)}")
                print(f"Ошибка: {str(e)}")
        
        self.run_in_thread(do_operation)
    
    # МЕТОДЫ ДЛЯ ОБЗОРА ФАЙЛОВ
    
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
    
    # Методы обзора файлов (сохранены для обратной совместимости)
    def browse_archive(self):
        if self.browse_file("Выберите файл архива", [("BIN files", "*.bin"), ("All files", "*.*")], self.archive_file):
            self.archive_file_display.set(self.format_path(self.archive_file.get()))
            self.settings['archive_file'] = self.archive_file.get()
    
    def browse_archive_folder(self):
        """Выбор папки с архивами для режима папки"""
        if self.browse_directory("Выберите папку с архивами", self.archive_folder):
            self.archive_folder_display.set(self.format_path(self.archive_folder.get(), True))
            self.settings['archive_folder'] = self.archive_folder.get()
        
    def browse_analyze_folder(self):
        """Выбор папки для анализа"""
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
    
    # ОСНОВНЫЕ МЕТОДЫ ОПЕРАЦИЙ
    
    def analyze_archive(self):
        """Анализ архива или файлов в папке"""
        def do_analyze():
            try:
                report_file = self.report_file.get() if self.report_file.get() else None
                
                if not report_file:
                    messagebox.showerror("Ошибка", "Укажите файл для сохранения отчета")
                    return
                
                if self.analyze_mode.get() == "file":
                    # Режим анализа одного файла архива
                    archive = self.analyze_file.get()
                    
                    if not os.path.exists(archive):
                        messagebox.showerror("Ошибка", f"Файл контейнера не найден: {archive}")
                        return
                    
                    print(f"Анализ контейнера {archive}...")
                    vanguard_tools.analyze(file_name=archive, output_file=report_file)
                    print("Анализ контейнера завершен!")
                    
                else:
                    # Режим анализа всех файлов в папке
                    folder = self.analyze_folder.get()
                    
                    if not os.path.exists(folder):
                        messagebox.showerror("Ошибка", f"Папка не найдена: {folder}")
                        return
                    
                    print(f"Анализ всех файлов в папке {folder}...")
                    vanguard_tools.analyze(folder_path=folder, output_file=report_file)
                    print("Анализ файлов в папке завершен!")
                    
                messagebox.showinfo("Успех", "Анализ завершен!")
                
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при анализе: {str(e)}")
                print(f"Ошибка: {str(e)}")
        
        self.run_in_thread(do_analyze)
    
    def extract_files(self):
        """Извлечение файлов из архива(ов)"""
        def do_extract():
            try:
                mode = self.extract_mode.get()
                output_dir = self.extract_dir.get()
                
                if mode == "file":
                    # Режим одного файла
                    archive = self.archive_file.get()
                    
                    if not os.path.exists(archive):
                        messagebox.showerror("Ошибка", f"Файл контейнера не найден: {archive}")
                        return
                    
                    print(f"Извлечение файлов из {archive}...")
                    files_extracted = vanguard_tools.split(
                        file_name=archive, 
                        output_dir=output_dir
                    )
                    print(f"Извлечение завершено! Извлечено файлов: {files_extracted}")
                    
                else:
                    # Режим папки
                    folder = self.archive_folder.get()
                    
                    if not os.path.exists(folder):
                        messagebox.showerror("Ошибка", f"Папка с контейнерами не найдена: {folder}")
                        return
                    
                    print(f"Обработка всех контейнеров в папке {folder}...")
                    total_files_extracted = vanguard_tools.split(
                        folder_path=folder,
                        output_dir=output_dir
                    )
                    print(f"Обработка завершена! Всего извлечено файлов: {total_files_extracted}")
                
                messagebox.showinfo("Успех", "Извлечение файлов завершено!")
                
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при извлечении файлов: {str(e)}")
                print(f"Ошибка: {str(e)}")
        
        self.run_in_thread(do_extract)
    
    def build_archive(self):
        """Создание контейнера из файлов"""
        def do_build():
            input_dir = self.build_dir.get()
            output_file = self.output_file.get()
            alignment = int(self.alignment.get(), 0)
            
            if not os.path.exists(input_dir):
                messagebox.showerror("Ошибка", f"Папка не найдена: {input_dir}")
                return
            
            print(f"Создание контейнера {output_file} из папки {input_dir}...")
            
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
                messagebox.showerror("Ошибка", f"Папка не найдена: {folder}")
                return
            
            if self.unpack_mode.get() == "all":
                print(f"Распаковка LZSS файлов по сигнатурам из {folder}...")
                count = vanguard_tools.unpack_lzss(unpack_all=True, search_folder=folder)
                print(f"Распаковка завершена! Обработано файлов: {count}")
            else:
                index = int(self.unpack_index.get())
                input_file = os.path.join(folder, f"file_{index:04d}.bin")
                output_file = os.path.join(folder, f"file_{index:04d}.lzss-dec")
                
                if not os.path.exists(input_file):
                    messagebox.showerror("Ошибка", f"Входной файл не найден: {input_file}")
                    return
                
                print(f"Распаковка файла {input_file} в {output_file}...")
                vanguard_tools.unpack_lzss(input_file=input_file, output_file=output_file, unpack_all=False)
                print("Распаковка файла завершена!")
        
        self.execute_operation("распаковке LZSS", do_unpack, "Распаковка LZSS завершена!")
    
    def pack_lzss(self):
        """Упаковка LZSS файлов"""
        def do_pack():
            folder = self.pack_dir.get()
            
            if not folder or not os.path.exists(folder):
                messagebox.showerror("Ошибка", f"Папка не найдена: {folder}")
                return
            
            if self.pack_mode.get() == "all":
                print(f"Упаковка всех LZSS файлов из {folder}...")
                vanguard_tools.repack_lzss("", "", compress_all=True, search_folder=folder)
                print("Упаковка всех файлов завершена!")
            else:
                index = int(self.pack_index.get())
                input_file = os.path.join(folder, f"file_{index:04d}.lzss-dec")
                output_file = os.path.join(folder, f"file_{index:04d}.bin")
                
                if not os.path.exists(input_file):
                    messagebox.showerror("Ошибка", f"Входной файл не найден: {input_file}")
                    return
                
                print(f"Упаковка файла {input_file} в {output_file}...")
                vanguard_tools.repack_lzss(input_file=input_file, output_file=output_file, compress_all=False)
                print("Упаковка файла завершена!")
        
        self.execute_operation("упаковке LZSS", do_pack, "Упаковка LZSS завершена!")
    
    def replace_file_in_image(self):
        """Замена файла в PSX образе с использованием psx-mode2-en.exe"""
        def do_replace():
            import os
            import subprocess
            
            bin_file = self.bin_file.get()
            target = self.target_file.get()
            replacement = self.replacement_file.get()
            
            if not bin_file or not os.path.exists(bin_file):
                messagebox.showerror("Ошибка", f"BIN файл образа не найден: {bin_file}")
                return
            
            if not replacement or not os.path.exists(replacement):
                messagebox.showerror("Ошибка", f"Файл для замены не найден: {replacement}")
                return
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            util_path = os.path.join(script_dir, "tools\psx-mode2-en.exe")
            
            if not os.path.exists(util_path):
                messagebox.showerror("Ошибка", "Утилита psx-mode2-en.exe не найдена в папке tools!")
                return
            
            print(f"\nЗамена файла {target} в PSX образе...")
            
            cmd = [util_path, bin_file, target, replacement]
            print(f"Выполняется команда: {' '.join(cmd)}")
            
            if os.name == 'nt':
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', 
                                      errors='ignore', creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            
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
                print(f"Ошибка при замене файла! Код возврата: {result.returncode}")
                messagebox.showerror("Ошибка", f"Ошибка при замене файла! Код возврата: {result.returncode}")
        
        self.run_in_thread(do_replace)
    
    def launch_emulator(self):
        """Запуск эмулятора с текущим BIN файлом и аргументами"""
        def do_launch():
            import subprocess
            
            emulator_path = self.emulator_file.get()
            bin_file_path = self.bin_file.get()
            emulator_args = self.emulator_args.get()
            
            if not emulator_path or not os.path.exists(emulator_path):
                messagebox.showerror("Ошибка", "Файл эмулятора не найден или не указан")
                return
            
            if not bin_file_path or not os.path.exists(bin_file_path):
                messagebox.showerror("Ошибка", "BIN файл образа не найден или не указан")
                return
            
            print(f"Запуск эмулятора: {emulator_path}")
            print(f"Аргументы: {emulator_args}")
            print(f"Файл образа: {bin_file_path}")
            
            import shlex
            cmd = [emulator_path]
            
            if emulator_args.strip():
                args_list = shlex.split(emulator_args)
                cmd.extend(args_list)
            
            cmd.append(bin_file_path)
            
            print(f"Полная команда: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            print("Эмулятор запущен!")
        
        self.run_in_thread(do_launch)
    
    # МЕТОДЫ ДЛЯ РАБОТЫ С ТЕКСТОМ
    
    def open_text_file(self):
        """Открытие TXT файла по индексу"""
        try:
            folder = self.text_update_dir.get()
            index = int(self.text_update_index.get())
            
            if not folder or not os.path.exists(folder):
                messagebox.showerror("Ошибка", f"Папка не найдена: {folder}")
                return
            
            txt_file = Path(folder) / f"file_{index:04d}-text.txt"
            
            if not txt_file.exists():
                messagebox.showerror("Ошибка", f"TXT файл не найден: {txt_file}")
                return
            
            if os.name == 'nt':
                os.startfile(txt_file)
            else:
                import subprocess
                subprocess.run(['xdg-open', str(txt_file)])
            
            print(f"Открыт файл: {txt_file}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при открытии файла: {str(e)}")
            print(f"Ошибка: {str(e)}")
    
    def restore_from_backup(self):
        """Восстановление файла из резервной копии"""
        def do_restore():
            try:
                folder = self.text_update_dir.get()
                index = int(self.text_update_index.get())
                
                if not folder or not os.path.exists(folder):
                    messagebox.showerror("Ошибка", f"Папка не найдена: {folder}")
                    return
                
                # Определяем целевой файл и его резервную копию
                target_file_bin = Path(folder) / f"file_{index:04d}.bin"
                target_file_lzss = Path(folder) / f"file_{index:04d}.lzss-dec"
                
                backup_file_bin = target_file_bin.with_suffix(target_file_bin.suffix + '.bak')
                backup_file_lzss = target_file_lzss.with_suffix(target_file_lzss.suffix + '.bak')
                
                # Определяем какой файл восстанавливать
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
                    # Проверяем какие резервные копии вообще есть
                    available_backups = []
                    if backup_file_lzss.exists():
                        available_backups.append(f"file_{index:04d}.lzss-dec.bak")
                    if backup_file_bin.exists():
                        available_backups.append(f"file_{index:04d}.bin.bak")
                    
                    if not available_backups:
                        messagebox.showerror("Ошибка", 
                                           f"Резервные копии не найдены для файла с индексом {index}\n"
                                           f"Ожидаемые файлы:\n"
                                           f"- {backup_file_lzss.name}\n"
                                           f"- {backup_file_bin.name}")
                        return
                    else:
                        # Используем первую доступную резервную копию
                        if backup_file_lzss.exists():
                            target_file = target_file_lzss
                            backup_file = backup_file_lzss
                            file_type = "LZSS-dec"
                        else:
                            target_file = target_file_bin
                            backup_file = backup_file_bin
                            file_type = "BIN"
                
                print(f"🔄 Восстановление файла из резервной копии:")
                print(f"   📁 Целевой файл: {target_file.name}")
                print(f"   💾 Резервная копия: {backup_file.name}")
                self.text_status_var.set("Восстановление...")
                
                # Подтверждение действия
                if not messagebox.askyesno("Подтверждение", 
                                         f"Восстановить файл {target_file.name} из резервной копии?\n\n"
                                         f"Текущий файл будет перезаписан!"):
                    print(" Восстановление отменено пользователем")
                    self.text_status_var.set("Восстановление отменено")
                    return
                
                # Выполняем восстановление
                import shutil
                shutil.copy2(backup_file, target_file)
                
                print(f" Файл успешно восстановлен из резервной копии!")
                print(f"    Размер восстановленного файла: {target_file.stat().st_size} байт")
                
                self.text_status_var.set("Файл восстановлен")
                messagebox.showinfo("Успех", 
                                  f"Файл успешно восстановлен из резервной копии!\n\n"
                                  f" Восстановленный файл: {target_file.name}\n"
                                  f" Источник: {backup_file.name}\n"
                                  f" Размер: {target_file.stat().st_size} байт")
                
            except Exception as e:
                self.text_status_var.set("Ошибка восстановления")
                messagebox.showerror("Ошибка", f"Ошибка при восстановлении файла: {str(e)}")
                print(f" Ошибка: {str(e)}")
                import traceback
                traceback.print_exc()
        
        self.run_in_thread(do_restore)
    
    def debug_encoding_table(self):
        """Диагностика таблицы кодировки"""
        def do_debug():
            try:
                from vanguard_text import debug_encoding_table
                debug_encoding_table()
            except ImportError as e:
                print(f" Ошибка: не удалось импортировать debug_encoding_table: {e}")
            except Exception as e:
                print(f" Ошибка диагностики кодировки: {e}")
                import traceback
                traceback.print_exc()
        
        self.run_in_thread(do_debug)
    
    def open_encoding_table(self):
        """Открывает файл таблицы кодировки для редактирования"""
        def do_open():
            try:
                encoding_file = Path("tools/encoding_table.txt")
                
                # Просто проверяем существование файла
                if not encoding_file.exists():
                    messagebox.showerror("Ошибка", 
                                      f"Файл таблицы кодировки не найден:\n{encoding_file}\n\n"
                                      f"Создайте файл вручную или проверьте путь.")
                    return
                
                print(f" Открытие таблицы кодировки: {encoding_file}")
                
                if os.name == 'nt':
                    os.startfile(encoding_file)
                else:
                    import subprocess
                    # Пробуем разные редакторы
                    for editor in ['xdg-open', 'gedit', 'vim', 'nano']:
                        try:
                            subprocess.run([editor, str(encoding_file)], check=False)
                            break
                        except FileNotFoundError:
                            continue
                    else:
                        print(" Не найден подходящий текстовый редактор")
                        messagebox.showerror("Ошибка", "Не найден текстовый редактор для открытия файла")
                        return
                
                print(" Таблица кодировки открыта для редактирования")
                print(" После изменений используйте 'Диагностика кодировки'")
                
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось открыть таблицу кодировки: {str(e)}")
                print(f" Ошибка открытия таблицы кодировки: {e}")
        
        self.run_in_thread(do_open)
    
    def find_text_blocks_improved(self):
        """Улучшенный поиск текстовых блоков с использованием vanguard_text.py"""
        def do_find():
            try:
                folder = self.text_extract_dir.get()
                
                if not folder or not os.path.exists(folder):
                    messagebox.showerror("Ошибка", f"Папка не найдена: {folder}")
                    return
                
                max_blocks = int(self.text_max_blocks.get())
                min_length = int(self.text_min_length.get())
                
                print(f" Улучшенный поиск текстовых блоков в папке: {folder}")
                self.text_status_var.set("Поиск текстовых блоков...")
                
                if self.text_find_mode.get() == "all":
                    # Используем функцию из vanguard_text.py для поиска во всех файлах
                    from vanguard_text import find_text_in_folder
                    
                    result = find_text_in_folder(folder, max_blocks, min_length)
                    
                    self.text_status_var.set(f"Найдено {result['total_blocks']} блоков в {result['processed_files']} файлах")
                    messagebox.showinfo("Успех", 
                                      f"Поиск текстовых блоков завершен!\n"
                                      f"Обработано файлов: {result['processed_files']}\n"
                                      f"Найдено блоков: {result['total_blocks']}\n"
                                      f"Найдено строк: {result['total_strings']}")
                    
                else:
                    # Поиск в одном файле
                    index = int(self.text_find_index.get())
                    file_path = Path(folder) / f"file_{index:04d}.bin"
                    
                    unpack_file = file_path.with_suffix('.lzss-dec')
                    if unpack_file.exists():
                        input_file = str(unpack_file)
                        file_type = "LZSS-dec"
                    else:
                        input_file = str(file_path)
                        file_type = "BIN"
                    
                    output_file = str(file_path.with_name(file_path.stem + "-text.txt"))
                    
                    if not os.path.exists(input_file):
                        messagebox.showerror("Ошибка", f"Файл не найден: {input_file}")
                        return
                    
                    print(f" Поиск текстовых блоков в файле [{file_type}]: {Path(input_file).name}")
                    self.text_status_var.set(f"Поиск в file_{index:04d}...")
                    
                    try:
                        from vanguard_text import find_text_blocks_improved, save_text_blocks_to_file
                        
                        blocks = find_text_blocks_improved(input_file, max_blocks, min_length)
                        print(f" Результаты поиска:")
                        print(f"   Найдено блоков: {len(blocks)}")
                        
                        if blocks:
                            save_text_blocks_to_file(input_file, blocks, output_file)
                            print(f"    Блоки сохранены в: {Path(output_file).name}")
                            
                            # Детальная статистика
                            blocks_with_headers = sum(1 for b in blocks if b['has_header'])
                            validated_blocks = sum(1 for b in blocks if b.get('validated', False))
                            total_strings = sum(block['string_count'] for block in blocks)
                            total_pointers = sum(len(block['pointers']) for block in blocks)
                            
                            print(f"    Блоков с заголовками: {blocks_with_headers}/{len(blocks)}")
                            print(f"    Валидированных блоков: {validated_blocks}/{len(blocks)}")
                            print(f"    Всего строк: {total_strings}")
                            print(f"    Всего поинтеров: {total_pointers}")
                            
                            self.text_status_var.set(f"Найдено {len(blocks)} блоков, {total_strings} строк")
                            
                            messagebox.showinfo("Успех", 
                                              f"Найдено текстовых блоков: {len(blocks)}\n"
                                              f"Строк: {total_strings}\n"
                                              f"Валидированных: {validated_blocks}\n"
                                              f"Сохранено в: {Path(output_file).name}")
                        else:
                            self.text_status_var.set("Блоки не найдены")
                            messagebox.showinfo("Информация", "Текстовые блоки не найдены")
                            
                    except Exception as e:
                        self.text_status_var.set("Ошибка поиска")
                        messagebox.showerror("Ошибка", f"Ошибка при поиске текстовых блоков: {str(e)}")
                        print(f" Ошибка: {str(e)}")
                        
            except Exception as e:
                self.text_status_var.set("Ошибка")
                messagebox.showerror("Ошибка", f"Ошибка при поиске текстовых блоков: {str(e)}")
                print(f" Ошибка: {str(e)}")
        
        self.run_in_thread(do_find)

    def update_text_translation_improved(self):
        """Улучшенное обновление файла с переводом с использованием vanguard_text.py"""
        def do_update():
            try:
                folder = self.text_update_dir.get()
                index = int(self.text_update_index.get())
                
                if not folder or not os.path.exists(folder):
                    messagebox.showerror("Ошибка", f"Папка не найдена: {folder}")
                    return
                
                # Определяем целевой файл
                target_file_bin = Path(folder) / f"file_{index:04d}.bin"
                target_file_lzss = Path(folder) / f"file_{index:04d}.lzss-dec"
                
                if target_file_lzss.exists():
                    target_file = target_file_lzss
                    file_type = "LZSS-dec"
                elif target_file_bin.exists():
                    target_file = target_file_bin
                    file_type = "BIN"
                else:
                    messagebox.showerror("Ошибка", f"Файл не найден для индекса {index}")
                    self.text_status_var.set("Ошибка: файл не найден")
                    return
                
                translation_file = Path(folder) / f"file_{index:04d}-text.txt"
                
                if not translation_file.exists():
                    messagebox.showerror("Ошибка", f"Файл перевода не найден: {translation_file}")
                    return
                
                print(f" Обновление файла с переводом: {translation_file.name}")
                print(f" Целевой файл [{file_type}]: {target_file.name}")
                self.text_status_var.set("Обновление перевода...")
                
                try:
                    from vanguard_text import update_all_blocks_in_file
                    
                    success = update_all_blocks_in_file(
                        original_filename=str(target_file),
                        translation_filename=str(translation_file),
                        output_filename=str(target_file),
                        use_translate=True
                    )
                    
                    if success:
                        print(f" Файл успешно обновлен!")
                        self.text_status_var.set("Обновление завершено")
                        messagebox.showinfo("Успех", 
                                          f"Файл успешно обновлен!\n"
                                          f" Целевой файл: {target_file.name}\n"
                                          f" Создана резервная копия: {target_file.name}.bak")
                    else:
                        print(f" Ошибка при обновлении файла")
                        self.text_status_var.set("Ошибка обновления")
                        messagebox.showerror("Ошибка", "Не удалось обновить файл!")
                        
                except Exception as e:
                    self.text_status_var.set("Ошибка обновления")
                    messagebox.showerror("Ошибка", f"Ошибка при обновлении файла: {str(e)}")
                    print(f" Ошибка: {str(e)}")
                    import traceback
                    traceback.print_exc()
                            
            except Exception as e:
                self.text_status_var.set("Ошибка")
                messagebox.showerror("Ошибка", f"Ошибка при обновлении файла: {str(e)}")
                print(f" Ошибка: {str(e)}")
        
        self.run_in_thread(do_update)
    
def main():
    try:
        import vanguard_tools
    except ImportError:
        print("Создание модуля vanguard_tools...")
        current_script = __file__
        if current_script.endswith('.py'):
            import shutil
            shutil.copy(current_script, 'vanguard_tools.py')
            import vanguard_tools
    
    root = tk.Tk()
    app = VanguardToolsGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()