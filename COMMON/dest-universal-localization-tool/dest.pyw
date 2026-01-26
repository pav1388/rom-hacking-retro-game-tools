import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import re
import os
import subprocess
import json
import tempfile
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Set
import functools
import sys
import gc
import time
import threading

# ==================== ВСПОМОГАТЕЛЬНЫЕ КЛАССЫ ====================

class TextContextMenu:
    """Контекстное меню с горячими клавишами"""
    
    def __init__(self, root, colors):
        self.root = root
        self.current_widget = None
        self.create_menu(colors)
    
    def create_menu(self, colors):
        self.menu = tk.Menu(self.root, tearoff=0)
        
        # Пункты меню
        actions = [
            ("Вырезать", lambda: self._handle_action('cut')),
            ("Копировать", lambda: self._handle_action('copy')),
            ("Вставить", lambda: self._handle_action('paste')),
            ("-", None),
            ("Выделить все", lambda: self._handle_action('select_all'))
        ]
        
        for label, cmd in actions:
            if label == "-":
                self.menu.add_separator()
            else:
                self.menu.add_command(label=label, command=cmd)
        
        self.update_colors(colors)
    
    def bind_to_widget(self, widget):
        """Привязать все обработчики к виджету"""
        if isinstance(widget, (tk.Text, tk.Entry, scrolledtext.ScrolledText)):
            # Контекстное меню
            widget.bind("<Button-3>", lambda e: self._show_menu(e, widget))
            
            # Горячие клавиши
            widget.bind("<Control-c>", lambda e: self._hotkey_action(e, 'copy'), add='+')
            widget.bind("<Control-x>", lambda e: self._hotkey_action(e, 'cut'), add='+')
            widget.bind("<Control-v>", lambda e: self._hotkey_action(e, 'paste'), add='+')
            widget.bind("<Control-a>", lambda e: self._hotkey_action(e, 'select_all'), add='+')
    
    def _show_menu(self, event, widget):
        self.current_widget = widget
        widget.focus_set()
        self.menu.tk_popup(event.x_root, event.y_root)
        return "break"
    
    def _handle_action(self, action):
        """Обработчик для контекстного меню"""
        if not self.current_widget:
            return
        
        widget = self.current_widget
        
        if action == 'cut':
            widget.event_generate("<<Cut>>")
        elif action == 'copy':
            widget.event_generate("<<Copy>>")
        elif action == 'paste':
            widget.event_generate("<<Paste>>")
        elif action == 'select_all':
            if isinstance(widget, tk.Entry):
                widget.select_range(0, tk.END)
            else:
                widget.tag_add("sel", "1.0", "end")
    
    def _hotkey_action(self, event, action):
        """Обработчик для горячих клавиш"""
        widget = event.widget
        
        if action == 'cut':
            widget.event_generate("<<Cut>>")
        elif action == 'copy':
            widget.event_generate("<<Copy>>")
        elif action == 'paste':
            widget.event_generate("<<Paste>>")
        elif action == 'select_all':
            if isinstance(widget, tk.Entry):
                widget.select_range(0, tk.END)
            else:
                widget.tag_add("sel", "1.0", "end")
        
        return "break"
    
    def update_colors(self, colors):
        self.menu.config(
            bg=colors.get('text_bg', '#F0F0F0'),
            fg=colors.get('text_fg', '#000000'),
            activebackground=colors.get('primary', '#0078D7'),
            activeforeground='white'
        )


class DebugInfo:
    """Класс для сбора отладочной информации"""
    
    _psutil_available = None  # Кэш доступности psutil
    
    @classmethod
    def _check_psutil(cls):
        """Проверка доступности psutil с кэшированием"""
        if cls._psutil_available is None:
            try:
                import psutil
                cls._psutil_available = True
            except ImportError:
                cls._psutil_available = False
        return cls._psutil_available
    
    @staticmethod
    def get_memory_usage():
        """Получить информацию об использовании памяти"""
        if not DebugInfo._check_psutil():
            return {'rss_mb': 0, 'percent': 0}
        
        try:
            import psutil
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            return {
                'rss_mb': mem_info.rss / (1024 * 1024),
                'percent': process.memory_percent()
            }
        except:
            return {'rss_mb': 0, 'percent': 0}
    
    @staticmethod
    def get_system_memory():
        """Получить информацию о системной памяти"""
        if not DebugInfo._check_psutil():
            return {'available_mb': 0, 'percent': 0}
        
        try:
            import psutil
            memory = psutil.virtual_memory()
            return {
                'available_mb': memory.available / (1024 * 1024),
                'percent': memory.percent
            }
        except:
            return {'available_mb': 0, 'percent': 0}
    
    @staticmethod
    def format_operation_info(operation=None, start_time=None, extra_info=None):
        """Форматировать информацию об операции"""
        debug_lines = []
        
        # Время выполнения
        if operation and start_time:
            elapsed = time.time() - start_time
            if elapsed < 0.001:
                time_str = f"{elapsed*1000:.1f} мс"
            elif elapsed < 1:
                time_str = f"{elapsed*1000:.0f} мс"
            else:
                time_str = f"{elapsed:.3f} сек"
            debug_lines.append(f"{operation}: {time_str}")
        
        # Память процесса (только если есть данные)
        if DebugInfo._check_psutil():
            mem_usage = DebugInfo.get_memory_usage()
            if mem_usage['rss_mb'] > 0:
                debug_lines.append(f"Память: {mem_usage['rss_mb']:.1f} MB ({mem_usage['percent']:.1f}%)")
            
            # Системная память для длительных операций
            if start_time and (time.time() - start_time) > 1.0:  # Если операция длилась больше 1 секунды
                sys_memory = DebugInfo.get_system_memory()
                if sys_memory['available_mb'] > 0:
                    debug_lines.append(f"Свободно памяти: {sys_memory['available_mb']:.0f} MB")
        
        # Дополнительная информация
        if extra_info:
            # Если extra_info - список, добавляем каждую строку
            if isinstance(extra_info, list):
                for info in extra_info:
                    debug_lines.append(f"{info}")
            else:
                debug_lines.append(f"{extra_info}")
        
        return debug_lines
    
    @staticmethod
    def get_system_summary():
        """Получить краткую сводку о системе (для старта программы)"""
        summary = []
        
        # Информация о Python
        import platform
        if sys.maxsize > 2**32:
            bitness = "64-bit"
        else:
            bitness = "32-bit"
        
        summary.append(f"Python {sys.version.split()[0]} ({bitness})")
        summary.append(f"Платформа: {platform.platform().split('-')[0]}")
        
        # Информация о psutil
        if not DebugInfo._check_psutil():
            summary.append("   ⚠️ psutil: не установлен")
        
        return summary


class ThemeManager:
    """Управление темами приложения"""
    
    THEMES = {
        'light': {
            'bg': '#E8E8E8',          # Основной фон светлой темы
            'fg': '#1A1A1A',          # Основной текст (темно-серый, почти черный)
            'primary': '#B2B2B2',     # Основной акцентный цвет (нейтральный серый)
            'secondary': '#D2D2D2',   # Вторичный акцент (светлее primary)
            'danger': '#F45451',      # Цвет для ошибок и опасных действий (красный)
            'success': '#52BD56',     # Цвет успешных операций и подтверждений (зеленый)
            'warning': '#FFAA2A',     # Цвет предупреждений (оранжевый/желтый)
            'entry_bg': '#F7F7F7',    # Фон текстовых полей ввода (светлее основного фона)
            'entry_fg': '#000000',    # Цвет текста в полях ввода (черный)
            'text_bg': '#F7F7F7',     # Фон текстовых виджетов (Text, ScrolledText)
            'text_fg': '#000000',     # Цвет текста в текстовых виджетах
            'status': '#B2B2B2',      # Цвет фона строки статуса (совпадает с primary для единства)
        },
        'dark': {
            'bg': '#3A3A3A',          # Основной фон темной темы (темно-серый)
            'fg': '#E5E5E5',          # Основной текст (светло-серый)
            'primary': '#323232',     # Основной акцент (чуть темнее основного фона)
            'secondary': '#525252',   # Вторичный акцент (светлее primary)
            'danger': '#BA2A2A',      # Цвет для ошибок (темно-красный)
            'success': '#286D2C',     # Цвет успешных операций (темно-зеленый)
            'warning': '#D16800',     # Цвет предупреждений (темно-оранжевый)
            'entry_bg': '#444444',    # Фон полей ввода (темнее основного фона)
            'entry_fg': '#FFFFFF',    # Цвет текста в полях ввода (белый)
            'text_bg': '#444444',     # Фон текстовых виджетов
            'text_fg': '#FFFFFF',     # Цвет текста в текстовых виджетах
            'status': '#323232',      # Фон строки статуса (совпадает с primary)
        }
    }
    
    def __init__(self):
        self.current_theme = 'light'
        self.colors = self.THEMES[self.current_theme]
    
    def toggle(self):
        """Переключение темы"""
        self.current_theme = 'dark' if self.current_theme == 'light' else 'light'
        self.colors = self.THEMES[self.current_theme]
        return self.colors
    
    def get_button_text(self):
        """Текст для кнопки переключения темы"""
        return "🌛" if self.current_theme == 'light' else "🌞"
    
    def set_theme(self, theme_name):
        """Установить конкретную тему"""
        if theme_name in self.THEMES:
            self.current_theme = theme_name
            self.colors = self.THEMES[theme_name]
    
    @staticmethod
    def darken_color(color, factor=0.7):
        """Затемнить цвет"""
        if not color.startswith('#'):
            return color
        
        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            r = int(r * factor)
            g = int(g * factor)
            b = int(b * factor)
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            return f'#{r:02x}{g:02x}{b:02x}'
        except:
            return color


class ConfigManager:
    """Управление конфигурацией приложения"""
    
    DEFAULT_VALUES = {
        'input_file': '',
        'original_strings_file': '_original_strings.txt',
        'translation_file': '_translation.txt',
        'output_file': '_localized_output.txt',
        'search_pattern_before': '"',
        'search_pattern_after': '"',
        'escape_char': '\\',
        'search_regex': r'"(?:\\.|[^"\\])*"',
        'single_line_comment': '//',
        'multi_line_comment_start': '/*',
        'multi_line_comment_end': '*/',
        'encoding': 'UTF-8',
        'auto_detect_encoding': True,
        'line_limit': 50000,
        'enable_line_limit': True,
        'show_debug_logs': False,
        'apply_lists_to_raw_strings': False,
    }
    
    DEFAULT_FILTERS = {
        'only_digits': True,
        'only_non_letters': True,
        'only_latin': False,
        'only_non_latin': False,
        'special_chars_only': False,
        'single_char': True,
        'whitespace_only': True,
        'file_paths': False,
        'urls': False,
        'emails': False,
        'html_tags': False,
        'hex_codes': False,
        'short_strings': False
    }
    
    COMMENT_TEMPLATES = {
        'Bash/Shell': {'single': '#', 'multi_start': '', 'multi_end': ''},
        'C#': {'single': '//', 'multi_start': '/*', 'multi_end': '*/'},
        'C++': {'single': '//', 'multi_start': '/*', 'multi_end': '*/'},
        'CSS': {'single': '', 'multi_start': '/*', 'multi_end': '*/'},
        'Dart': {'single': '//', 'multi_start': '/*', 'multi_end': '*/'},
        'Go': {'single': '//', 'multi_start': '/*', 'multi_end': '*/'},
        'HTML': {'single': '', 'multi_start': '<!--', 'multi_end': '-->'},
        'Java': {'single': '//', 'multi_start': '/*', 'multi_end': '*/'},
        'JavaScript': {'single': '//', 'multi_start': '/*', 'multi_end': '*/'},
        'Kotlin': {'single': '//', 'multi_start': '/*', 'multi_end': '*/'},
        'Lua': {'single': '--', 'multi_start': '--[[', 'multi_end': '--]]'},
        'Perl': {'single': '#', 'multi_start': '=pod', 'multi_end': '=cut'},
        'PHP': {'single': '//', 'multi_start': '/*', 'multi_end': '*/'},
        'Python': {'single': '#', 'multi_start': '"""', 'multi_end': '"""'},
        'Ruby': {'single': '#', 'multi_start': '=begin', 'multi_end': '=end'},
        'Rust': {'single': '//', 'multi_start': '/*', 'multi_end': '*/'},
        'Scala': {'single': '//', 'multi_start': '/*', 'multi_end': '*/'},
        'SQL': {'single': '--', 'multi_start': '/*', 'multi_end': '*/'},
        'Swift': {'single': '//', 'multi_start': '/*', 'multi_end': '*/'},
        'TypeScript': {'single': '//', 'multi_start': '/*', 'multi_end': '*/'},
    }
    
    ENCODINGS = [
        'UTF-8', 'UTF-8-SIG', 'UTF-16', 'UTF-16-LE', 'UTF-16-BE',
        'UTF-32', 'UTF-32-LE', 'UTF-32-BE', 'CP1251', 'CP1252',
        'ISO-8859-1', 'ISO-8859-5', 'KOI8-R', 'KOI8-U', 'ASCII', 'MacCyrillic',
    ]
    
    def __init__(self):
        self.config_file = os.path.join(tempfile.gettempdir(), "DEST-config.json")
    
    def save(self, state):
        """Сохранить конфигурацию в файл"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            raise Exception(f"Ошибка сохранения: {str(e)}")
    
    def load(self):
        """Загрузить конфигурацию из файла"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            raise Exception(f"Ошибка загрузки: {str(e)}")
        return {}


class FilterManager:
    """Управление фильтрами"""
    
    def __init__(self):
        self.blacklist: List[str] = []
        self.whitelist: List[str] = []
    
    def apply_black_white_list(self, list_type: str, text: str) -> None:
        """Применить фильтр-список (черный или белый) из текстового виджета"""
        lines = [
            line.strip() for line in text.strip().split('\n') 
            if line.strip()]
        if list_type.lower() == 'black':
            self.blacklist = lines
        elif list_type.lower() == 'white':
            self.whitelist = lines
        
    def is_in_black_white_list(self, list_type: str, text: str) -> bool:
        """Проверить текст на наличие в указанном (черный или белый) фильтр-списке"""
        text = text.strip()
        list_mapping = {
            'black': self.blacklist,
            'white': self.whitelist
        }
        return any( pattern.strip() and pattern.strip() in text
                    for pattern in list_mapping[list_type] )
    
    @staticmethod
    def only_digits(text: str) -> bool:
        """Строка состоит только из цифр"""
        if not text or not text.strip():
            return False
        return text.strip().isdigit()
    
    @staticmethod
    def only_non_letters(text: str) -> bool:
        """Строка не содержит букв"""
        if not text or not text.strip():
            return False
        text = text.strip()
        return not any(c.isalpha() for c in text)
    
    @staticmethod
    def only_latin(text: str) -> bool:
        """Строка содержит только латинские буквы"""
        if not text or not text.strip():
            return False
        text = text.strip()
        
        if not any(c.isalpha() for c in text):
            return False
        
        for char in text:
            if char.isalpha():
                char_lower = char.lower()
                if 'a' <= char_lower <= 'z':
                    continue
                elif '\u00C0' <= char <= '\u00FF':
                    continue
                elif '\u0100' <= char <= '\u017F':
                    continue
                elif '\u0180' <= char <= '\u024F':
                    continue
                else:
                    return False
        return True
    
    @staticmethod
    def only_non_latin(text: str) -> bool:
        """Строка содержит только нелатинские буквы"""
        if not text or not text.strip():
            return False
        text = text.strip()
        
        if not any(c.isalpha() for c in text):
            return False
        
        for char in text:
            if char.isalpha():
                char_lower = char.lower()
                if 'a' <= char_lower <= 'z':
                    return False
                elif '\u00C0' <= char <= '\u00FF':
                    return False
                elif '\u0100' <= char <= '\u017F':
                    return False
                elif '\u0180' <= char <= '\u024F':
                    return False
        return any(c.isalpha() for c in text)
    
    @staticmethod
    def special_chars_only(text: str) -> bool:
        """Строка состоит только из специальных символов"""
        if not text or not text.strip():
            return False
        text = text.strip()
        
        for char in text:
            if char.isalnum():
                return False
        return True
    
    @staticmethod
    def single_char(text: str) -> bool:
        """Строка состоит из одного символа"""
        if not text:
            return False
        text = text.strip()
        return len(text) == 1
    
    @staticmethod
    def whitespace_only(text: str) -> bool:
        """Строка состоит только из пробелов"""
        if not text:
            return True
        return text.isspace()
    
    @staticmethod
    def file_paths(text: str) -> bool:
        """Строка является путем к файлу"""
        if not text or not text.strip():
            return False
        text = text.strip()
        
        patterns = [
            r'^[A-Za-z]:[\\/](?:[^\\/]+[\\/])*[^\\/]+$',
            r'^[\\/](?:[^\\/]+[\\/])+[^\\/]+$',
            r'^\.[\\/]|^\.[\.\\/]',
            r'\.(?:exe|dll|txt|pdf|docx?|xlsx?|pptx?|jpg|png|gif|zip|rar)$',
        ]
        
        path_indicators = ['/', '\\', ':', '.', '..']
        has_path_indicators = any(indicator in text for indicator in path_indicators)
        
        if len(text) < 5 and text.count('/') + text.count('\\') == 1:
            return False
        
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return has_path_indicators and len(text) > 10
    
    @staticmethod
    def urls(text: str) -> bool:
        """Строка является URL"""
        if not text or not text.strip():
            return False
        text = text.strip()
        
        url_patterns = [
            r'^(?:https?|ftp|ftps|sftp)://[^\s<>"\'{}|\\^`\[\]]+',
            r'^www\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\/[^\s]*)?$',
            r'^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\/[^\s]*)?$',
            r'^[^\s]+\.(?:com|org|net|edu|gov|mil|info|biz|io|ru|ua|by|kz)[^\s]*$',
        ]
        
        for pattern in url_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                if '.' in text and not text.startswith('.'):
                    return True
        
        return False
    
    @staticmethod
    def emails(text: str) -> bool:
        """Строка является email"""
        if not text or not text.strip():
            return False
        text = text.strip()
        
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if re.match(email_regex, text, re.IGNORECASE):
            if text.startswith('.') or text.endswith('.'):
                return False
            if text.count('@') != 1:
                return False
            local_part, domain_part = text.split('@')
            if domain_part.startswith('.') or domain_part.endswith('.'):
                return False
            if '.' not in domain_part:
                return False
            if len(domain_part) < 4:
                return False
            
            return True
        
        return False
    
    @staticmethod
    def html_tags(text: str) -> bool:
        """Строка содержит HTML теги"""
        if not text or not text.strip():
            return False
        text = text.strip()
        
        html_patterns = [
            r'<[a-zA-Z][^>]*>',
            r'</[a-zA-Z][^>]*>',
            r'<[a-zA-Z][^>]*/>',
            r'&[a-zA-Z]+;',
            r'&#[0-9]+;',
            r'&#x[0-9a-fA-F]+;',
            r'<!DOCTYPE[^>]*>',
            r'<\?xml[^>]*\?>',
            r'<!--.*?-->',
        ]
        
        for pattern in html_patterns:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                return True
        
        return False
    
    @staticmethod
    def hex_codes(text: str) -> bool:
        """Строка является hex кодом"""
        if not text or not text.strip():
            return False
        text = text.strip()
        
        if re.match(r'^#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?$', text):
            return True
        
        if re.match(r'^0x[0-9A-Fa-f]+$', text):
            hex_part = text[2:]
            if len(hex_part) >= 2 and all(c in '0123456789ABCDEFabcdef' for c in hex_part):
                return True
        
        if re.match(r'^[0-9A-Fa-f]{6,}$', text) and len(text) >= 6:
            if len(text) in [3, 6, 8] and all(c in '0123456789ABCDEFabcdef' for c in text):
                return True
        
        return False
    
    @staticmethod
    def short_strings(text: str, min_length: int = 2) -> bool:
        """Строка короче минимальной длины"""
        if not text or not text.strip():
            return False
        
        text = text.strip()
        return len(text) < min_length


class FileProcessor:
    """Обработчик файлов и поиска строк"""
    
    def __init__(self, config_manager: ConfigManager, filter_manager: FilterManager):
        self.config_manager = config_manager
        self.filter_manager = filter_manager
    
    def detect_encoding(self, file_path: str, auto_detect: bool, manual_encoding: str) -> str:
        """Определить кодировку файла"""
        if not auto_detect:
            return manual_encoding
        
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(4096)
            
            # Проверка BOM
            bom_map = {
                b'\xef\xbb\xbf': 'utf-8-sig',
                b'\xff\xfe\x00\x00': 'utf-32-le',
                b'\x00\x00\xfe\xff': 'utf-32-be',
                b'\xff\xfe': 'utf-16-le',
                b'\xfe\xff': 'utf-16-be',
            }
            
            for bom, encoding in bom_map.items():
                if raw_data.startswith(bom):
                    return encoding
            
            # Попытка декодирования
            encodings_to_try = [
                'utf-8', 'utf-8-sig', 'cp1251', 'cp1252',
                'iso-8859-1', 'iso-8859-5', 'koi8-r', 'koi8-u',
                'mac-cyrillic', 'utf-16-le', 'utf-16-be',
                'utf-32-le', 'utf-32-be', 'ascii',
            ]
            
            for encoding in encodings_to_try:
                try:
                    raw_data.decode(encoding, errors='strict')
                    return encoding
                except (UnicodeDecodeError, LookupError):
                    continue
            
            # Использование chardet, если установлен
            try:
                import chardet
                result = chardet.detect(raw_data)
                if result['confidence'] > 0.7:
                    return result['encoding'].lower()
            except ImportError:
                pass
            
        except Exception:
            pass
        
        return 'utf-8'
    
    def extract_string_content(self, quoted_string: str, use_custom_regex: bool, 
                             search_pattern_before: str, search_pattern_after: str) -> str:
        """Извлечь содержимое строки из кавычек"""
        if not quoted_string or use_custom_regex:
            return quoted_string
        
        result = quoted_string
        if search_pattern_before and result.startswith(search_pattern_before):
            result = result[len(search_pattern_before):]
        if search_pattern_after and result.endswith(search_pattern_after):
            result = result[:-len(search_pattern_after)]
        
        return result
    
    def preprocess_content_for_comments(self, content: str,
                                  single_line_comment: str, multi_line_comment_start: str,
                                  multi_line_comment_end: str) -> str:
        """Предварительная обработка комментариев"""
        if not single_line_comment and not multi_line_comment_start:
            return content
        
        lines = content.split('\n')
        result_lines = []
        in_multiline_comment = False
        len_single_line_comment = len(single_line_comment)
        len_multi_line_comment_start = len(multi_line_comment_start)
        len_multi_line_comment_end = len(multi_line_comment_end)
        
        for line in lines:
            current_line = line
            processed_line = ""
            i = 0
            
            while i < len(current_line):
                # Если внутри многострочного комментария
                if in_multiline_comment:
                    # Проверяем, не закончился ли комментарий
                    if i + len_multi_line_comment_end <= len(current_line) and \
                       current_line[i:i + len_multi_line_comment_end] == multi_line_comment_end:
                        i += len_multi_line_comment_end
                        in_multiline_comment = False
                        continue
                    else:
                        i += 1
                        continue
                
                # Проверяем начало многострочного комментария
                if multi_line_comment_start and \
                   i + len_multi_line_comment_start <= len(current_line) and \
                   current_line[i:i + len_multi_line_comment_start] == multi_line_comment_start:
                    
                    # Добавляем часть до комментария
                    i += len_multi_line_comment_start
                    in_multiline_comment = True
                    
                    # Проверяем, не закончился ли комментарий сразу
                    if multi_line_comment_end and \
                       i + len(multi_line_comment_end) <= len(current_line) and \
                       current_line[i:i + len(multi_line_comment_end)] == multi_line_comment_end:
                        i += len(multi_line_comment_end)
                        in_multiline_comment = False
                    
                    continue
                
                # Проверяем однострочный комментарий
                if single_line_comment and \
                   i + len_single_line_comment <= len(current_line) and \
                   current_line[i:i + len_single_line_comment] == single_line_comment:
                    break
                
                # Если не в комментарии и не однострочный комментарий - добавляем символ
                processed_line += current_line[i]
                i += 1
            
            # Добавляем обработанную строку в результат, если она не пустая
            if processed_line.strip():  # Проверяем, содержит ли строка не только пробелы
                result_lines.append(processed_line.rstrip())
        
        return '\n'.join(result_lines)
    

# ==================== КАСТОМНЫЕ TK ВИДЖЕТЫ ====================

class CustomButton(tk.Button):
    """Кастомная кнопка с поддержкой тем"""
    
    def __init__(self, parent, **kwargs):
        self.style = kwargs.pop('style', 'primary')
        super().__init__(parent, **kwargs)
        self.config(
            # padx=8,    # 
            pady=5,    # высота кнопок
            font=('Segoe UI', 9),
            relief=tk.RAISED,
            bd=1,
            cursor='hand2'
        )
        
    def set_colors(self, theme_manager):
        """Установить цвета в соответствии с темой"""
        colors = theme_manager.colors
        
        # Вспомогательная функция для настройки hover эффектов
        def setup_button_style(normal_bg, normal_fg, hover_bg, hover_fg):
            """Настроить цвета и hover эффекты для кнопки"""
            # Отвязываем старые события
            self.unbind('<Enter>')
            self.unbind('<Leave>')
            
            # Настройка цветов
            self.config(
                bg=normal_bg,
                fg=normal_fg,
                activebackground=hover_bg,
                activeforeground=hover_fg,
                relief=tk.RAISED,
                bd=1,
                font=('Segoe UI', 9),
                cursor='hand2'
            )
            
            # Привязываем hover события
            self.bind('<Enter>', 
                lambda e, h=hover_bg, hf=hover_fg: self.config(bg=h, fg=hf))
            self.bind('<Leave>', 
                lambda e, n=normal_bg, nf=normal_fg: self.config(bg=n, fg=nf))
        
        # Выбираем цвета в зависимости от стиля
        if self.style == 'primary':
            normal_bg = colors['primary']
            normal_fg = colors['text_fg']
            hover_bg = ThemeManager.darken_color(colors['primary'])
            hover_fg = colors['text_fg']
            
        elif self.style == 'success':
            normal_bg = colors['success']
            normal_fg = colors['text_fg']
            hover_bg = ThemeManager.darken_color(colors['success'])
            hover_fg = colors['text_fg']
            
        elif self.style == 'warning':
            normal_bg = colors['warning']
            normal_fg = colors['text_fg']
            hover_bg = ThemeManager.darken_color(colors['warning'])
            hover_fg = colors['text_fg']
            
        elif self.style == 'danger':
            normal_bg = colors['danger']
            normal_fg = colors['text_fg']
            hover_bg = ThemeManager.darken_color(colors['danger'])
            hover_fg = colors['text_fg']
            
        else:  # default/primary
            normal_bg = colors['primary']
            normal_fg = colors['text_fg']
            hover_bg = ThemeManager.darken_color(colors['primary'])
            hover_fg = colors['text_fg']
        
        # Применяем настройки
        setup_button_style(normal_bg, normal_fg, hover_bg, hover_fg)


class CustomComboBox(tk.Frame):
    """Виджет для выбора варианта из списка (замена для ComboBox)"""
    
    def __init__(self, parent, values=None, items_per_row=None, **kwargs):
        super().__init__(parent)
        self.values = values or []
        self.selected_value = tk.StringVar()
        self.buttons = []
        self.items_per_row = items_per_row  # Количество элементов в строке (None = все в одну строку)
        
        # Фрейм для кнопок-вариантов
        self.options_frame = tk.Frame(self)
        self.options_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Фрейм для текущей строки
        self.current_row_frame = None
        
        self.create_options()
        
        # Устанавливаем начальное значение если есть
        if self.values:
            self.selected_value.set(self.values[0])
            self.update_display()
    
    def create_options(self):
        """Создать кликабельные варианты с переносами"""
        # Очищаем предыдущие варианты
        for widget in self.options_frame.winfo_children():
            widget.destroy()
        self.buttons = []
        
        # Создаем первый фрейм для строки
        self.current_row_frame = tk.Frame(self.options_frame)
        self.current_row_frame.pack(side=tk.TOP, fill=tk.X, expand=True)
        
        # Создаем варианты
        items_in_current_row = 0
        
        for i, value in enumerate(self.values):
            # Если нужно сделать перенос и текущая строка уже заполнена
            if self.items_per_row and items_in_current_row >= self.items_per_row:
                # Создаем новую строку
                self.current_row_frame = tk.Frame(self.options_frame)
                self.current_row_frame.pack(side=tk.TOP, fill=tk.X, expand=True)
                items_in_current_row = 0
            
            btn = tk.Label(self.current_row_frame,
                         text=value,
                         font=('Segoe UI', 9),
                         cursor='hand2',
                         padx=5,
                         pady=2)
            btn.pack(side=tk.LEFT, padx=2)
            
            # Привязываем событие клика
            btn.bind('<Button-1>', lambda e, v=value: self.select_option(v))
            
            # Сохраняем ссылку для обновления стиля
            self.buttons.append((value, btn))
            
            items_in_current_row += 1
    
    def select_option(self, value):
        """Выбрать вариант"""
        self.selected_value.set(value)
        self.update_display()
        # Генерируем событие выбора
        self.event_generate('<<OptionSelected>>')
    
    def update_display(self):
        """Обновить отображение при выборе"""
        selected = self.selected_value.get()
        for value, btn in self.buttons:
            if value == selected:
                btn.config(text=f"• {value} •", font=('Segoe UI', 11, 'bold'))
            else:
                btn.config(text=value, font=('Segoe UI', 9))
    
    def set_colors(self, theme_manager):
        """Установить цвета в соответствии с темой"""
        colors = theme_manager.colors
        self.theme_manager = theme_manager
        self.options_frame.config(bg=colors['bg'])
        
        # Обновляем все фреймы строк
        for frame in self.options_frame.winfo_children():
            frame.config(bg=colors['bg'])
        
        for value, btn in self.buttons:
            btn.config(
                bg=colors['bg'],
                fg=colors['fg'],
                activebackground=colors['bg']
            )
        
        # Обновляем отображение точек
        self.update_display()
    
    def get(self):
        """Получить текущее значение"""
        return self.selected_value.get()
    
    def set(self, value):
        """Установить значение"""
        if value in self.values:
            self.selected_value.set(value)
            self.update_display()
    
    def config(self, **kwargs):
        """Конфигурация виджета"""
        if 'values' in kwargs:
            self.values = kwargs.pop('values')
            self.create_options()
            if self.values:
                self.selected_value.set(self.values[0])
                self.update_display()
        
        if 'items_per_row' in kwargs:
            self.items_per_row = kwargs.pop('items_per_row')
            self.create_options()


class CustomNotebook(tk.Frame):
    """Кастомный Notebook с корректной обработкой тем и hover эффектов"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent)
        self.tabs = {}
        self.current_tab = None
        self.tab_buttons = []
        self.theme_manager = None
        
        # Контейнер для кнопок вкладок с прокруткой
        self.tab_container = tk.Frame(self)
        self.tab_container.pack(side=tk.TOP, fill=tk.X)
        
        # Canvas для прокрутки кнопок вкладок
        self.tab_canvas = tk.Canvas(self.tab_container, height=35, highlightthickness=0)
        self.tab_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Фрейм для кнопок вкладок внутри Canvas
        self.tab_buttons_frame = tk.Frame(self.tab_canvas)
        self.tab_canvas.create_window((0, 0), window=self.tab_buttons_frame, anchor='nw')
        
        # Кнопки прокрутки (если много вкладок)
        self.scroll_left_btn = tk.Button(self.tab_container, text="◀", width=2,
                                        command=self.scroll_left)
        self.scroll_right_btn = tk.Button(self.tab_container, text="▶", width=2,
                                        command=self.scroll_right)
        
        # Фрейм для содержимого вкладок
        self.content_frame = tk.Frame(self)
        self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.tab_canvas.bind("<Configure>", self.on_tab_canvas_configure)
        
        # Флаг для показа кнопок прокрутки
        self.show_scroll_buttons = False
        
        # Словарь для хранения цветов кнопок
        self.button_colors = {}
    
    def get_tab_index(self, widget):
        """Получить индекс вкладки по виджету"""
        for tab_id, tab_info in self.tabs.items():
            if tab_info['content'] == widget:
                return tab_id
        return None
    
    def on_tab_canvas_configure(self, event=None):
        """Обработчик изменения размера Canvas"""
        # Обновляем область прокрутки
        self.tab_canvas.configure(scrollregion=self.tab_canvas.bbox("all"))
        
        # Проверяем, нужно ли показывать кнопки прокрутки
        tab_buttons_width = self.tab_buttons_frame.winfo_reqwidth()
        canvas_width = self.tab_canvas.winfo_width()
        
        if tab_buttons_width > canvas_width:
            if not self.show_scroll_buttons:
                self.show_scroll_buttons = True
                self.scroll_left_btn.pack(side=tk.LEFT, padx=(0, 2))
                self.scroll_right_btn.pack(side=tk.RIGHT, padx=(2, 0))
        else:
            if self.show_scroll_buttons:
                self.show_scroll_buttons = False
                self.scroll_left_btn.pack_forget()
                self.scroll_right_btn.pack_forget()
    
    def scroll_left(self):
        """Прокрутить влево"""
        self.tab_canvas.xview_scroll(-12, "units")
    
    def scroll_right(self):
        """Прокрутить вправо"""
        self.tab_canvas.xview_scroll(12, "units")
    
    def add(self, child, text=""):
        """Добавить вкладку"""
        # Создаем кнопку для вкладки
        tab_id = len(self.tabs)
        
        btn = tk.Button(self.tab_buttons_frame, text=text, 
                       command=lambda: self.select(tab_id),
                       relief=tk.RAISED, bd=1, padx=10, pady=5,
                       height=1, font=('Segoe UI', 9),
                       cursor='hand2')
        
        btn.pack(side=tk.LEFT, padx=(0, 1))
        self.tab_buttons.append(btn)
        
        # Сохраняем содержимое вкладки
        self.tabs[tab_id] = {
            'content': child,
            'text': text,
            'button': btn
        }
        
        # Инициализируем цвета для этой кнопки
        self.button_colors[tab_id] = {
            'normal_bg': None,
            'normal_fg': None,
            'hover_bg': None,
            'hover_fg': None,
            'is_active': False
        }
        
        # Скрываем содержимое, если это не первая вкладка
        if tab_id == 0:
            self.select(0)
        else:
            child.pack_forget()
        
        # Обновляем размеры Canvas
        self.tab_canvas.after(10, self.on_tab_canvas_configure)
        
        return child
    
    def select(self, tab_id):
        """Выбрать вкладку"""
        if tab_id in self.tabs:
            # Скрываем предыдущую вкладку
            if self.current_tab is not None:
                self.tabs[self.current_tab]['content'].pack_forget()
                # Сбрасываем кнопку предыдущей вкладки
                self.update_tab_button(self.current_tab, is_active=False)
            
            # Показываем новую вкладку
            self.tabs[tab_id]['content'].pack(in_=self.content_frame, 
                                             fill=tk.BOTH, expand=True)
            
            # Устанавливаем кнопку текущей вкладки в активное состояние
            self.update_tab_button(tab_id, is_active=True)
            
            self.current_tab = tab_id
            
            # Генерируем событие смены вкладки
            self.event_generate('<<NotebookTabChanged>>')
    
    def update_tab_button(self, tab_id, is_active):
        """Обновить внешний вид кнопки вкладки"""
        if tab_id not in self.tabs:
            return
        
        btn = self.tabs[tab_id]['button']
        
        if not hasattr(self, 'theme_manager') or not self.theme_manager:
            return
        
        colors = self.theme_manager.colors
        
        # Определяем цвета для этого состояния
        if is_active:
            # Активная вкладка
            normal_bg = colors['secondary']
            normal_fg = colors['text_fg']
            hover_bg = ThemeManager.darken_color(colors['primary'])
            hover_fg = colors['text_fg']
            relief = tk.SUNKEN
        else:
            # Неактивная вкладка
            normal_bg = colors['primary']
            normal_fg = colors['text_fg']
            hover_bg = ThemeManager.darken_color(colors['primary'])
            hover_fg = colors['text_fg']
            relief = tk.RAISED
        
        # Сохраняем цвета для этой кнопки
        self.button_colors[tab_id] = {
            'normal_bg': normal_bg,
            'normal_fg': normal_fg,
            'hover_bg': hover_bg,
            'hover_fg': hover_fg,
            'is_active': is_active
        }
        
        # Отвязываем старые события
        btn.unbind('<Enter>')
        btn.unbind('<Leave>')
        
        # Устанавливаем начальные цвета
        btn.config(
            bg=normal_bg,
            fg=normal_fg,
            relief=relief,
            activebackground=hover_bg,
            activeforeground=hover_fg
        )
        
        # Создаем замыкания с текущими цветами
        def on_enter(event, button=btn, hbg=hover_bg, hfg=hover_fg):
            button.config(bg=hbg, fg=hfg)
        
        def on_leave(event, button=btn, nbg=normal_bg, nfg=normal_fg):
            button.config(bg=nbg, fg=nfg)
        
        # Привязываем hover события
        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)
    
    def nametowidget(self, name):
        """Получить виджет по имени"""
        # В упрощенной реализации просто возвращаем текущую вкладку
        if self.current_tab is not None:
            return self.tabs[self.current_tab]['content']
        return None
    
    def set_colors(self, theme_manager):
        """Установить цвета в соответствии с темой"""
        self.theme_manager = theme_manager
        colors = theme_manager.colors
        
        # Обновляем фон контейнеров
        self.tab_container.config(bg=colors['bg'])
        self.tab_canvas.config(bg=colors['bg'])
        self.tab_buttons_frame.config(bg=colors['bg'])
        self.content_frame.config(bg=colors['bg'])
        
        # Обновляем все кнопки вкладок
        for tab_id in self.tabs:
            is_active = (tab_id == self.current_tab)
            self.update_tab_button(tab_id, is_active)
        
        # Кнопки прокрутки
        if hasattr(self, 'scroll_left_btn'):
            # Вспомогательная функция для настройки hover эффектов кнопок прокрутки
            def setup_scroll_button_hover(scroll_btn):
                # Отвязываем старые события
                scroll_btn.unbind('<Enter>')
                scroll_btn.unbind('<Leave>')
                
                # Настройка цветов
                scroll_btn.config(
                    bg=colors['primary'],
                    fg=colors['text_fg'],
                    activebackground=colors['secondary'],
                    activeforeground=colors['text_fg'],
                    relief=tk.RAISED,
                    bd=1,
                    font=('Segoe UI', 9),
                    cursor='hand2'
                )
                
                # Создаем замыкания для hover эффектов
                def scroll_on_enter(event, button=scroll_btn):
                    button.config(bg=colors['secondary'])
                
                def scroll_on_leave(event, button=scroll_btn):
                    button.config(bg=colors['primary'])
                
                # Привязываем hover события
                scroll_btn.bind('<Enter>', scroll_on_enter)
                scroll_btn.bind('<Leave>', scroll_on_leave)
            
            setup_scroll_button_hover(self.scroll_left_btn)
            setup_scroll_button_hover(self.scroll_right_btn)


# ==================== ГЛАВНЫЙ КЛАСС ПРИЛОЖЕНИЯ ====================

class DEST:
    def __init__(self, root, icon_path):
        self.root = root
        self.root.title("DEST - Universal Localization Tool")
        try:
            self.root.iconbitmap(default=icon_path)
        except Exception as e:
            print(f"Ошибка загрузки иконки: {e}")
        
        self.root.withdraw()
        self.root.geometry("1180x750")
        self.root.minsize(700, 400)
        self.last_normal_geometry = "1180x750"
        self.window_is_zoomed = False
        
        self.last_active_tab_index = None
        self.is_processing = False  # Флаг выполнения операции
        self.cancel_requested = False  # Флаг запроса отмены
        self.cancel_button = None  # Ссылка на кнопку отмены
        
        # Инициализация менеджеров
        self.theme_manager = ThemeManager()
        self.config_manager = ConfigManager()
        self.filter_manager = FilterManager()
        self.file_processor = FileProcessor(self.config_manager, self.filter_manager)
        
        # Переменные интерфейса
        self.theme_button = None
        self.input_files: List[str] = []
        self.context_menu = None
        self.log_lines: List[str] = []
        
        # Переменные для кэширования информации о файлах
        self.total_files_count = 0
        self.total_files_size = 0  # в байтах
        self.total_files_lines = 0
        self.file_info_cache = {}  # {file_path: {'size': int, 'lines': int}}
        
        # Переменные для буферизации сообщений
        self.message_buffer = []  # Буфер сообщений
        self.buffer_enabled = False  # Включена ли буферизация
        self.buffer_threshold = 50  # Порог срабатывания буфера (сообщений)
        self.buffer_flush_count = 0  # Счетчик срабатываний буфера
    
        self.initialize_variables()
        self.setup_ui()
        self.load_config()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.update_idletasks()
        self.root.after(100, self.apply_theme)
        self.root.bind("<Configure>", self.on_window_configure)
        self.check_dependencies()
        try:
            self.root.deiconify()
            self.root.focus_force()
        except Exception as e:
            print(f"Ошибка при отображении окна: {e}")
            self.root.deiconify()
        
        if self.show_debug_logs.get():
            system_summary = DebugInfo.get_system_summary()
            for line in system_summary:
                self.log_message(f"{line}", 'debug')
        
        self.setup_mousewheel()
        self.update_status('Готов')
        
    def check_dependencies(self):
        """Проверка необходимых зависимостей"""
        dependencies = {
            'psutil': ("Для подробного вывода отладки установите: pip install psutil", 'warning'),
            'tips': ("Файл tips.py отсутствует. Подсказки будут недоступны.", 'warning'),
            'chardet': ("Для автоматического определения кодировок установите: pip install chardet", 'warning')
        }
        
        for dep, (message, level) in dependencies.items():
            try:
                __import__(dep)
                setattr(self, f"{dep}_available", True)
            except ImportError:
                setattr(self, f"{dep}_available", False)
                self.log_message(f"{message}", level)
            
    def initialize_variables(self):
        """Инициализация переменных интерфейса"""
        # Строковые переменные
        self.input_file = tk.StringVar(value='')
        self.original_strings_file = tk.StringVar(
            value=self.config_manager.DEFAULT_VALUES['original_strings_file']
        )
        self.translation_file = tk.StringVar(
            value=self.config_manager.DEFAULT_VALUES['translation_file']
        )
        self.output_file = tk.StringVar(
            value=self.config_manager.DEFAULT_VALUES['output_file']  # '_localized_output.txt'
        )
        
        # Переменные поиска
        self.search_pattern_before = tk.StringVar(
            value=self.config_manager.DEFAULT_VALUES['search_pattern_before']
        )
        self.search_pattern_after = tk.StringVar(
            value=self.config_manager.DEFAULT_VALUES['search_pattern_after']
        )
        self.escape_char = tk.StringVar(
            value=self.config_manager.DEFAULT_VALUES['escape_char']
        )
        self.use_custom_regex = tk.BooleanVar(value=False)
        self.custom_regex = tk.StringVar(
            value=self.config_manager.DEFAULT_VALUES['search_regex']
        )
        
        # Переменные комментариев
        self.single_line_comment = tk.StringVar(
            value=self.config_manager.DEFAULT_VALUES['single_line_comment']
        )
        self.multi_line_comment_start = tk.StringVar(
            value=self.config_manager.DEFAULT_VALUES['multi_line_comment_start']
        )
        self.multi_line_comment_end = tk.StringVar(
            value=self.config_manager.DEFAULT_VALUES['multi_line_comment_end']
        )
        self.ignore_comments = tk.BooleanVar(value=False)
        self.selected_language = tk.StringVar(value='C++')
        
        # Переменные настроек
        self.show_all_logs = tk.BooleanVar(value=True)
        self.show_debug_logs = tk.BooleanVar(
            value=self.config_manager.DEFAULT_VALUES['show_debug_logs']
        )
        self.auto_open_files = tk.BooleanVar(value=False)
        self.dark_mode = tk.BooleanVar(value=False)
        self.encoding = tk.StringVar(
            value=self.config_manager.DEFAULT_VALUES['encoding']
        )
        self.auto_detect_encoding = tk.BooleanVar(
            value=self.config_manager.DEFAULT_VALUES['auto_detect_encoding']
        )
        self.line_limit = tk.StringVar(
            value=str(self.config_manager.DEFAULT_VALUES['line_limit'])
        )
        self.enable_line_limit = tk.BooleanVar(
            value=self.config_manager.DEFAULT_VALUES['enable_line_limit']
        )
        
        # Переменные фильтров
        self.filter_active_vars = {}
        self.filter_mode_vars = {}
        
        for filter_name, default_value in self.config_manager.DEFAULT_FILTERS.items():
            self.filter_active_vars[filter_name] = tk.BooleanVar(value=default_value)
            self.filter_mode_vars[filter_name] = tk.StringVar(value="exclude")
        
        self.short_strings_length = tk.StringVar(value="2")
        self.apply_lists_to_raw_strings = tk.BooleanVar(value=False)
        self.blacklist_text = tk.StringVar(value='')
        self.whitelist_text = tk.StringVar(value='')
        self.save_mode = tk.StringVar(value='single_file')
    
    def setup_ui(self):
        """Настройка основного интерфейса"""
        self.context_menu = TextContextMenu(self.root, self.theme_manager.colors)
        
        main_container = tk.Frame(self.root, bg=self.theme_manager.colors['bg'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        self.setup_header(main_container)
        
        content_frame = tk.Frame(main_container, bg=self.theme_manager.colors['bg'])
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        left_panel = tk.Frame(content_frame, bg=self.theme_manager.colors['primary'], width=220)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        self.setup_sidebar(left_panel)
        
        right_panel = tk.Frame(content_frame, bg=self.theme_manager.colors['bg'])
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.setup_tabs(right_panel)
        self.setup_status_bar(main_container)
        
    def setup_header(self, parent):
        """Настройка заголовка"""
        header = tk.Frame(parent, bg=self.theme_manager.colors['primary'], height=45)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)
        
        tk.Label(header, 
                text="🔍📝 DEST - DeepExtract/SeekTranslate v1.3 by pav13",
                font=('Segoe UI', 12, 'bold'),
                fg='white',
                bg=self.theme_manager.colors['primary']).pack(side=tk.LEFT, padx=12)
        
        # Фрейм для правых кнопок
        right_frame = tk.Frame(header, bg=self.theme_manager.colors['primary'])
        right_frame.pack(side=tk.RIGHT, padx=10)
        
        # Создаем кнопку отмены ЗАРАНЕЕ, но скрываем
        self.cancel_button = CustomButton(right_frame,
                                       text="⏹ Отмена",
                                       command=self.cancel_operation,
                                       style='danger',
                                       width=20)
        self.cancel_button.pack(side=tk.RIGHT, padx=(0, 20))
        self.cancel_button.pack_forget()  # Сразу скрываем
        
        self.theme_button = CustomButton(right_frame,
                                      text=self.theme_manager.get_button_text(),
                                      command=self.toggle_theme,
                                      style='warning',
                                      width=4)
        self.theme_button.pack(side=tk.RIGHT)
    
    def setup_sidebar(self, parent):
        """Настройка боковой панели"""
        colors = self.theme_manager.colors
        
        separator = tk.Frame(parent, height=1, bg=colors['secondary'])
        separator.pack(fill=tk.X, pady=10, padx=15)
        
        tk.Label(parent,
                text="🚀 Быстрые действия",
                font=('Segoe UI', 10, 'bold'),
                fg='white',
                bg=colors['primary']).pack(pady=(5, 5), padx=10, anchor=tk.W)
        
        actions = [
            ("📁 Выбрать файл/-ы", lambda: self.browse_input_files()),
            ("🔍 Извлечь строки", lambda: self.extract_strings()),
            ("🔄 Применить перевод", lambda: self.apply_translation()),
            ("💾 Сохранить профиль", lambda: self.save_profile()),
            ("📂 Загрузить профиль", lambda: self.load_profile()),
            ("📝 Отчет", lambda: self.toggle_logs_tab()),
        ]
        
        for text, command in actions:
            btn = CustomButton(parent,
                           text=text,
                           command=command,
                           style='primary',
                           width=25)
            btn.pack(fill=tk.X, pady=4, padx=10)
            
        separator = tk.Frame(parent, height=1, bg=colors['secondary'])
        separator.pack(fill=tk.X, pady=10, padx=15)
        
        tk.Label(parent,
                text="📂 Быстрый доступ",
                font=('Segoe UI', 10, 'bold'),
                fg='white',
                bg=colors['primary']).pack(pady=(5, 5), padx=10, anchor=tk.W)
        
        files = [
            ("📂 Входной/-ые", lambda: self.open_input_files()),
            ("📂 Оригиналы", lambda: self.open_file(self.original_strings_file.get())),
            ("📂 Перевод", lambda: self.open_file(self.translation_file.get())),
            ("📂 Выходной", lambda: self.open_output_file())
        ]
        
        for label, cmd in files:
            btn = CustomButton(parent,
                           text=label,
                           command=cmd,
                           style='primary',
                           width=25)
            btn.pack(fill=tk.X, pady=2, padx=10)
    
    def setup_tabs(self, parent):
        """Настройка вкладок"""
        self.notebook = CustomNotebook(parent)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.tabs = {}
        tab_info = {
            'files': "📁 Файлы",
            'comments': "💬 Комментарии",
            'search': "🔍 Поиск",
            'blackwhite': "⚫⚪ Ч/Б списки",
            'filters': "🎯 Фильтрация",
            'settings': "⚙️ Настройки",
            'logs': "📝 Отчет",
        }
        for tab_name, tab_title in tab_info.items():
            if tab_name == 'logs':
                self.tabs[tab_name] = self.create_logs_tab()
                self.notebook.add(self.tabs[tab_name], text=tab_title)
            else:
                tab = self.create_scrollable_tab(tab_title)
                self.tabs[tab_name] = tab.content_frame
                self.notebook.add(tab, text=tab_title)
        
        self.setup_files_tab()
        self.setup_comments_tab()
        self.setup_search_tab()
        self.setup_blackwhite_tab()
        self.setup_filters_tab()
        self.setup_settings_tab()
    
    def create_scrollable_tab(self, title):
        """Создать вкладку с прокруткой"""
        colors = self.theme_manager.colors
        tab = tk.Frame(self.notebook, bg=colors['bg'])
        
        # Canvas с прокруткой
        canvas = tk.Canvas(tab, bg=colors['bg'], highlightthickness=0)
        
        # Создаем скроллбар
        scrollbar = tk.Scrollbar( tab, orient='vertical', command=canvas.yview,
            repeatdelay=100, repeatinterval=10, width=16)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        content_frame = tk.Frame(canvas, bg=colors['bg'])
        canvas_window = canvas.create_window((0, 0), window=content_frame, anchor='nw')
        
        content_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas_window, width=e.width))
        
        tab.content_frame = content_frame
        tab.canvas = canvas
        tab.scrollbar = scrollbar
        
        return tab

    def create_logs_tab(self):
        """Создать вкладку логов"""
        colors = self.theme_manager.colors
        tab = tk.Frame(self.notebook, bg=colors['bg'])
        
        self.log_text = scrolledtext.ScrolledText( tab, height=20, font=('Consolas', 9),
            bg=colors['text_bg'], fg=colors['text_fg'], relief=tk.SOLID, bd=1, wrap=tk.WORD)
            
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.add_context_menu(self.log_text)

        btn_frame = tk.Frame(tab, bg=colors['bg'])
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        CustomButton(btn_frame, text="🗑 Очистить",
                  command=self.clear_logs, style='danger').pack(side=tk.LEFT, padx=2)
        
        CustomButton(btn_frame, text="💾 Сохранить в файл",
                  command=self.save_logs_to_file, style='success').pack(side=tk.RIGHT, padx=2)
        
        CustomButton(btn_frame, text="📋 Копировать",
                  command=self.copy_logs, style='warning').pack(side=tk.RIGHT, padx=2)
        
        return tab
    
    def setup_files_tab(self):
        """Настройка вкладки файлов"""
        tab = self.tabs['files']
        colors = self.theme_manager.colors
        
        # Список выбранных файлов
        self.file_list_frame = tk.LabelFrame(tab,
                                           text=" Список входных файлов ",
                                           font=('Segoe UI', 10, 'bold'),
                                           bg=colors['bg'],
                                           fg=colors['fg'],
                                           relief=tk.GROOVE,
                                           bd=1)
        self.file_list_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=10)
        
        # Контейнер для списка файлов и кнопок
        list_container = tk.Frame(self.file_list_frame, bg=colors['text_bg'])
        list_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Listbox с прокруткой
        listbox_frame = tk.Frame(list_container, bg=colors['text_bg'])
        listbox_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar для Listbox
        scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Сам Listbox
        self.file_listbox = tk.Listbox(
            listbox_frame,
            font=('Consolas', 9),
            bg=colors['text_bg'],
            fg=colors['text_fg'],
            selectbackground=colors['primary'],
            selectforeground=colors['text_fg'],
            relief=tk.SOLID,
            bd=1,
            yscrollcommand=scrollbar.set,
            selectmode=tk.EXTENDED,
            activestyle='none',
            selectborderwidth=2
        )
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.file_listbox.yview)
        
        # Панель кнопок управления списком
        buttons_panel = tk.Frame(list_container, bg=colors['text_bg'], width=190)
        buttons_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        buttons_panel.pack_propagate(False)
        
        CustomButton(buttons_panel,
                  text="📁 Добавить файлы",
                  command=self.browse_input_files,
                  style='primary').pack(fill=tk.X, padx=5, pady=3)
        
        CustomButton(buttons_panel,
                  text="📁 Добавить папку",
                  command=self.browse_folder,
                  style='primary').pack(fill=tk.X, padx=5, pady=3)
        
        CustomButton(buttons_panel,
                  text="🗑 Удалить выбранные",
                  command=self.remove_selected_files,
                  style='danger').pack(fill=tk.X, padx=5, pady=3)
        
        CustomButton(buttons_panel,
                  text="🗑 Очистить список",
                  command=self.clear_file_list,
                  style='danger').pack(fill=tk.X, padx=5, pady=3)
        
        # Информационная панель
        info_frame = tk.Frame(self.file_list_frame, bg=colors['text_bg'])
        info_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        self.files_info_label = tk.Label(
            info_frame,
            text="Файлов: 0 |  Размер: 0 байт |  Строк: 0",
            font=('Segoe UI', 9),
            bg=colors['text_bg'],
            fg=colors['text_fg']
        )
        self.files_info_label.pack(side=tk.LEFT)
        
         # Поля ввода файлов
        file_fields = [
            ("Файл оригиналов:", self.original_strings_file, self.browse_original_strings_file),
            ("Файл перевода:", self.translation_file, self.browse_translation_file),
        ]
        
        for i, (label, var, cmd) in enumerate(file_fields):
            frame = tk.Frame(tab, bg=colors['bg'])
            frame.pack(fill=tk.X, pady=5, padx=10)
            
            tk.Label(frame,
                    text=label,
                    font=('Segoe UI', 9),
                    bg=colors['bg'],
                    fg=colors['fg'],
                    width=15,
                    anchor=tk.W).pack(side=tk.LEFT)
            
            entry = tk.Entry(frame,
                           textvariable=var,
                           font=('Segoe UI', 9),
                           bg=colors['entry_bg'],
                           fg=colors['entry_fg'],
                           relief=tk.SOLID,
                           bd=1)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            self.add_context_menu(entry)
            
            CustomButton(frame,
                      text="Обзор",
                      command=cmd,
                      style='primary',
                      width=12).pack(side=tk.RIGHT)
        
        # Режим сохранения
        save_mode_frame = tk.Frame(tab, bg=colors['bg'])
        save_mode_frame.pack(fill=tk.X, pady=5, padx=10)
        
        tk.Label(save_mode_frame,
                text="Режим сохранения:",
                font=('Segoe UI', 9),
                bg=colors['bg'],
                fg=colors['fg'],
                width=15,
                anchor=tk.W).pack(side=tk.LEFT)
        
        save_modes = [
            ('Один файл (с разделителем)', 'single_file'),
            ('Папка с оригинальными именами файлов', 'folder_with_names'),
            ('Папка с оригинальными именами/структурой файлов', 'folder_with_structure')
        ]
        
        # Создаем новый виджет
        self.save_mode_selector = CustomComboBox(
            save_mode_frame,
            values=[mode[0] for mode in save_modes],
            items_per_row=1
        )
        self.save_mode_selector.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.save_mode_selector.bind('<<OptionSelected>>', self.on_save_mode_changed)
        
        # Словарь для соответствия отображаемых значений и внутренних кодов
        self.save_mode_map = {mode[0]: mode[1] for mode in save_modes}
        self.save_mode_reverse_map = {mode[1]: mode[0] for mode in save_modes}
        
        # Поле для выходного файла/папки
        output_frame = tk.Frame(tab, bg=colors['bg'])
        output_frame.pack(fill=tk.X, pady=5, padx=10)
        
        # Создаем Label для заголовка (будем менять его текст)
        self.output_label = tk.Label(output_frame,
                                    text="Выходной файл:",
                                    font=('Segoe UI', 9),
                                    bg=colors['bg'],
                                    fg=colors['fg'],
                                    width=15,
                                    anchor=tk.W)
        self.output_label.pack(side=tk.LEFT)
        
        self.output_entry = tk.Entry(output_frame,
                                   textvariable=self.output_file,
                                   font=('Segoe UI', 9),
                                   bg=colors['entry_bg'],
                                   fg=colors['entry_fg'],
                                   relief=tk.SOLID,
                                   bd=1)
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.add_context_menu(self.output_entry)
        
        self.browse_output_btn = CustomButton(output_frame,
                                           text="Обзор",
                                           command=self.browse_output,
                                           style='primary',
                                           width=12)
        self.browse_output_btn.pack(side=tk.RIGHT)
        
        # Кнопки действий
        action_frame = tk.Frame(tab, bg=colors['bg'])
        action_frame.pack(fill=tk.X, pady=15, padx=10)
        
        CustomButton(action_frame, text="🔍 Извлечь строки",
                  command=self.extract_strings, style='success').pack(side=tk.LEFT, padx=10)
        
        CustomButton(action_frame, text="🔄 Применить перевод",
                  command=self.apply_translation, style='warning').pack(side=tk.LEFT, padx=10)
        
        # Подсказка
        self.add_tip_widget(tab, "PROCESS_TIP_TEXT")
    
    def setup_comments_tab(self):
        """Настройка вкладки комментариев"""
        tab = self.tabs['comments']
        colors = self.theme_manager.colors
        
        tk.Label(tab,
                text="Обработка комментариев",
                font=('Segoe UI', 11, 'bold'),
                bg=colors['bg'],
                fg=colors['fg']).pack(anchor=tk.W, pady=(10, 5), padx=10)
        
        check_frame = tk.Frame(tab, bg=colors['bg'])
        check_frame.pack(fill=tk.X, pady=5, padx=10)
        
        tk.Checkbutton(check_frame,
                      text="Игнорировать комментарии",
                      variable=self.ignore_comments,
                      font=('Segoe UI', 10),
                      bg=colors['bg'],
                      fg=colors['fg'],
                      selectcolor=colors['bg'],
                      activebackground=colors['bg'],
                      activeforeground=colors['fg']).pack(side=tk.LEFT, anchor=tk.W)
        
        lang_frame = tk.Frame(tab, bg=colors['bg'])
        lang_frame.pack(fill=tk.X, pady=5, padx=10)
        
        tk.Label(lang_frame,
                text="Выберите шаблон: ",
                font=('Segoe UI', 9),
                bg=colors['bg'],
                fg=colors['fg']).pack(side=tk.LEFT)
        
        self.language_selector = CustomComboBox(
            lang_frame,
            values=list(self.config_manager.COMMENT_TEMPLATES.keys()),
            items_per_row=7
        )
        self.language_selector.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.language_selector.bind('<<OptionSelected>>', self.on_language_selected)
        
        # Устанавливаем начальное значение
        self.language_selector.set(self.selected_language.get())
        
        comment_fields = [
            ("Однострочные: ", self.single_line_comment),
            ("Начало многострочного: ", self.multi_line_comment_start),
            ("Конец многострочного: ", self.multi_line_comment_end)
        ]
        
        for label, var in comment_fields:
            frame = tk.Frame(tab, bg=colors['bg'])
            frame.pack(fill=tk.X, pady=3, padx=10)
            
            tk.Label(frame,
                    text=label,
                    font=('Segoe UI', 9),
                    bg=colors['bg'],
                    fg=colors['fg'],
                    width=20,
                    anchor=tk.W).pack(side=tk.LEFT)
            
            entry = tk.Entry(frame,
                           textvariable=var,
                           font=('Consolas', 9),
                           bg=colors['entry_bg'],
                           fg=colors['entry_fg'],
                           relief=tk.SOLID,
                           bd=1)
            entry.pack(side=tk.RIGHT, fill=tk.X, expand=True)
            
            self.add_context_menu(entry)
        
        btn_frame = tk.Frame(tab, bg=colors['bg'])
        btn_frame.pack(fill=tk.X, pady=10, padx=10)
        
        CustomButton(btn_frame,
                  text="🔄 Сбросить",
                  command=self.reset_comments_settings,
                  style='danger').pack(side=tk.LEFT, padx=2)
        
        test_frame = tk.LabelFrame(tab, text=" 🧪 Тестирование обработки комментариев ", 
                                  font=('Segoe UI', 10, 'bold'),
                                  bg=colors['bg'],
                                  fg=colors['fg'],
                                  relief=tk.GROOVE,
                                  bd=1)
        test_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        test_text_frame = tk.Frame(test_frame, bg=colors['bg'])
        test_text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(test_text_frame,
                text="Исходный текст:",
                font=('Segoe UI', 9),
                bg=colors['bg'],
                fg=colors['fg']).pack(anchor=tk.W, pady=(0, 5))
        
        self.comment_test_input = scrolledtext.ScrolledText(test_text_frame,
                                                  height=10,
                                                  font=('Consolas', 9),
                                                  bg=colors['text_bg'],
                                                  fg=colors['text_fg'],
                                                  relief=tk.SOLID,
                                                  bd=1)
        self.comment_test_input.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.add_context_menu(self.comment_test_input)
        
        tk.Label(test_text_frame,
                text="Результат:",
                font=('Segoe UI', 9),
                bg=colors['bg'],
                fg=colors['fg']).pack(anchor=tk.W, pady=(0, 5))
        
        self.comment_test_output = scrolledtext.ScrolledText(test_text_frame,
                                                   height=10,
                                                   font=('Consolas', 9),
                                                   bg=colors['text_bg'],
                                                   fg=colors['text_fg'],
                                                   relief=tk.SOLID,
                                                   bd=1,
                                                   state='disabled')
        self.comment_test_output.pack(fill=tk.BOTH, expand=True)
        
        self.add_context_menu(self.comment_test_output)
        
        test_btn_frame = tk.Frame(test_frame, bg=colors['bg'])
        test_btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        CustomButton(test_btn_frame,
                  text="▶ Тестировать",
                  command=self.test_comments_processing,
                  style='success').pack(side=tk.LEFT)
        
        # Подсказка
        self.add_tip_widget(tab, "COMMENT_TIP_TEXT")
    
    def setup_search_tab(self):
        """Настройка вкладки поиска"""
        tab = self.tabs['search']
        colors = self.theme_manager.colors
        
        tk.Label(tab,
                 text="Параметры поиска",
                 font=('Segoe UI', 11, 'bold'),
                 bg=colors['bg'],
                 fg=colors['fg']).pack(anchor=tk.W, pady=(5, 5), padx=10)
        
        tk.Label(tab,
                 text="Простой режим:",
                 font=('Segoe UI', 9, 'bold'),
                 bg=colors['bg'],
                 fg=colors['fg']).pack(anchor=tk.W, pady=(10, 5), padx=10)
        
        input_tip_container = tk.Frame(tab, bg=colors['bg'])
        input_tip_container.pack(fill=tk.X, pady=5, padx=10)
        
        left_frame = tk.Frame(input_tip_container, bg=colors['bg'])
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        fields = [
            ("Символы перед строкой:", self.search_pattern_before),
            ("Символы после строки:", self.search_pattern_after),
            ("Символы экранирования:", self.escape_char)
        ]
        
        for label, var in fields:
            frame = tk.Frame(left_frame, bg=colors['bg'])
            frame.pack(fill=tk.X, pady=3)
            
            tk.Label(frame,
                     text=label,
                     font=('Segoe UI', 9),
                     bg=colors['bg'],
                     fg=colors['fg'],
                     width=25,
                     anchor=tk.W).pack(side=tk.LEFT)
            
            entry = tk.Entry(frame,
                             textvariable=var,
                             font=('Consolas', 9),
                             bg=colors['entry_bg'],
                             fg=colors['entry_fg'],
                             relief=tk.SOLID,
                             bd=1,
                             width=20)
            entry.pack(side=tk.LEFT, padx=(0, 10))
            
            self.add_context_menu(entry)
        
        right_frame = tk.Frame(input_tip_container, bg=colors['bg'])
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        simple_tip_text = """ \"(?:\\\\.|[^"\\\\])*\"\n Где:\n " - начальный символ из Символы перед\n (?:\\\\.|[^"\\\\])* - любая\n                 последовательность символов\n \\\\. - любой экраниранированный символ\n                 (например \\", \\n, \\t)\n [^"\\\\] - любой символ, кроме кавычки "\n                 и обратного слеша \\\n " - конечный символ из Символы после"""
        
        simple_tip_label = tk.Label(right_frame,
                                    text=simple_tip_text,
                                    font=('Consolas', 8),
                                    bg=colors['bg'],
                                    fg=colors['fg'],
                                    justify=tk.LEFT,
                                    anchor=tk.W,
                                    relief=tk.SOLID,
                                    bd=1,
                                    padx=5,
                                    pady=5)
        simple_tip_label.pack(fill=tk.BOTH, expand=True, padx=10)
        
        regex_frame = tk.Frame(tab, bg=colors['bg'])
        regex_frame.pack(fill=tk.X, pady=10, padx=10)
        
        tk.Checkbutton(regex_frame,
                       text="Использовать регулярное выражение",
                       variable=self.use_custom_regex,
                       command=self.toggle_regex_mode,
                       font=('Segoe UI', 9, 'bold'),
                       bg=colors['bg'],
                       fg=colors['fg'],
                       selectcolor=colors['bg'],
                       activebackground=colors['bg'],
                       activeforeground=colors['fg']).pack(anchor=tk.W)
        
        # Фрейм для поля ввода regex и кнопки сброса
        regex_input_frame = tk.Frame(regex_frame, bg=colors['bg'])
        regex_input_frame.pack(fill=tk.X, pady=5)
        
        self.regex_entry = tk.Entry(regex_input_frame,
                                    textvariable=self.custom_regex,
                                    font=('Consolas', 11),
                                    bg=colors['entry_bg'],
                                    fg=colors['entry_fg'],
                                    disabledbackground=colors['entry_bg'],
                                    disabledforeground=colors['entry_fg'],
                                    relief=tk.SOLID,
                                    bd=1,
                                    state='disabled')
        self.regex_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # Кнопка сброса справа от поля
        CustomButton(regex_input_frame,
                     text="🔄 Сбросить",
                     command=self.reset_search_settings,
                     style='danger',
                     width=15).pack(side=tk.RIGHT)
        
        self.add_context_menu(self.regex_entry)
        
        test_frame = tk.LabelFrame(tab, text=" 🧪 Тестирование поиска ", 
                                   font=('Segoe UI', 10, 'bold'),
                                   bg=colors['bg'],
                                   fg=colors['fg'],
                                   relief=tk.GROOVE,
                                   bd=1)
        test_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        test_text_frame = tk.Frame(test_frame, bg=colors['bg'])
        test_text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Панель управления текстом
        text_control_frame = tk.Frame(test_text_frame, bg=colors['bg'])
        text_control_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(text_control_frame,
                 text="Исходный текст:",
                 font=('Segoe UI', 9),
                 bg=colors['bg'],
                 fg=colors['fg']).pack(side=tk.LEFT)
        
        # Кнопки управления текстом
        CustomButton(text_control_frame,
                     text="🗑 Очистить",
                     command=lambda: self.clear_list_or_text('test'),
                     style='danger',
                     width=15).pack(side=tk.RIGHT, padx=3) 
        
        CustomButton(text_control_frame,
                     text="📂 Загрузить",
                     command=lambda: self.load_list_or_text('test'),
                     style='warning',
                     width=15).pack(side=tk.RIGHT, padx=3)
        
        CustomButton(text_control_frame,
                     text="💾 Сохранить",
                     command=lambda: self.save_list_or_text('test'),
                     style='success',
                     width=15).pack(side=tk.RIGHT, padx=3)
        
        # Поле для исходного текста
        self.search_test_input = scrolledtext.ScrolledText(test_text_frame,
                                                           height=10,
                                                           font=('Consolas', 9),
                                                           bg=colors['text_bg'],
                                                           fg=colors['text_fg'],
                                                           relief=tk.SOLID,
                                                           bd=1)
        self.search_test_input.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.add_context_menu(self.search_test_input)
        
        tk.Label(test_text_frame,
                 text="Найденные строки:",
                 font=('Segoe UI', 9),
                 bg=colors['bg'],
                 fg=colors['fg']).pack(anchor=tk.W, pady=(0, 5))
        
        self.search_test_output = scrolledtext.ScrolledText(test_text_frame,
                                                            height=10,
                                                            font=('Consolas', 9),
                                                            bg=colors['text_bg'],
                                                            fg=colors['text_fg'],
                                                            relief=tk.SOLID,
                                                            bd=1,
                                                            state='disabled')
        self.search_test_output.pack(fill=tk.BOTH, expand=True)
        
        self.add_context_menu(self.search_test_output)
        
        test_btn_frame = tk.Frame(test_frame, bg=colors['bg'])
        test_btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        CustomButton(test_btn_frame,
                     text="▶ Тестировать поиск",
                     command=self.test_search_pattern_embedded,
                     style='success').pack(side=tk.LEFT)
        
        # Подсказка
        self.add_tip_widget(tab, "SEARCH_TIP_TEXT")
    
    def setup_filters_tab(self):
        """Настройка вкладки фильтров"""
        tab = self.tabs['filters']
        colors = self.theme_manager.colors
        
        def create_filter_widget(parent, filter_name, label):
            frame = tk.Frame(parent, bg=colors['bg'])
            frame.pack(fill=tk.X, pady=2, padx=10)
            
            name_label = tk.Label(frame,
                                 text=label,
                                 font=('Segoe UI', 9),
                                 bg=colors['bg'],
                                 fg=colors['fg'],
                                 width=22,
                                 anchor=tk.W)
            name_label.pack(side=tk.LEFT)
            
            radio_frame = tk.Frame(frame, bg=colors['bg'])
            radio_frame.pack(side=tk.LEFT)
            
            tk.Radiobutton(radio_frame,
                          text="Исключить",
                          variable=self.filter_mode_vars[filter_name],
                          value="exclude",
                          command=lambda fn=filter_name: self.on_filter_mode_changed(fn, "exclude"),
                          font=('Segoe UI', 9),
                          bg=colors['bg'],
                          fg=colors['fg'],
                          selectcolor=colors['bg'],
                          activebackground=colors['bg'],
                          activeforeground=colors['fg']).pack(side=tk.LEFT, padx=2)
            
            tk.Radiobutton(radio_frame,
                          text="Включить",
                          variable=self.filter_mode_vars[filter_name],
                          value="include",
                          command=lambda fn=filter_name: self.on_filter_mode_changed(fn, "include"),
                          font=('Segoe UI', 9),
                          bg=colors['bg'],
                          fg=colors['fg'],
                          selectcolor=colors['bg'],
                          activebackground=colors['bg'],
                          activeforeground=colors['fg']).pack(side=tk.LEFT, padx=2)
            
            active_cb = tk.Checkbutton(radio_frame,
                                      text="Активен",
                                      variable=self.filter_active_vars[filter_name],
                                      command=lambda fn=filter_name: self.on_filter_active_changed(fn),
                                      font=('Segoe UI', 9, 'bold'),
                                      bg=colors['bg'],
                                      fg=colors['fg'],
                                      selectcolor=colors['bg'],
                                      activebackground=colors['bg'],
                                      activeforeground=colors['fg'])
            active_cb.pack(side=tk.LEFT, padx=(10, 0))
            
            return frame
        
        tk.Label(tab,
                text="Фильтрация строк",
                font=('Segoe UI', 11, 'bold'),
                bg=colors['bg'],
                fg=colors['fg']).pack(anchor=tk.W, pady=(10, 5), padx=10)
        
        explanation_frame = tk.Frame(tab, bg=colors['bg'])
        explanation_frame.pack(fill=tk.X, pady=(0, 10), padx=10)
        
        tk.Label(explanation_frame,
                text="◯ - Исключить только такие строки    ◯ - Включить только такие строки    ☑ - Активировать",
                font=('Segoe UI', 9, 'bold'),
                bg=colors['bg'],
                fg=colors['warning']).pack(anchor=tk.W, pady=(2, 0))
        
        main_filter_frame = tk.Frame(tab, bg=colors['bg'])
        main_filter_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        filters_column = tk.LabelFrame(main_filter_frame, 
                                      text=" Фильтры ",
                                      font=('Segoe UI', 9, 'bold'),
                                      bg=colors['bg'],
                                      fg=colors['fg'],
                                      relief=tk.GROOVE,
                                      bd=1)
        filters_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        buttons_column = tk.Frame(main_filter_frame,
                                 bg=colors['bg'])
        buttons_column.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        filters_all = [
            ("only_digits", "Цифры"),
            ("only_non_letters", "Не-буквы"),
            ("only_latin", "Латиница"),
            ("only_non_latin", "Нелатинские буквы"),
            ("special_chars_only", "Спецсимволы"),
            ("single_char", "Одиночные символы"),
            ("whitespace_only", "Пробелы/пустые"),
            ("file_paths", "Пути к файлам"),
            ("urls", "URL-адреса"),
            ("emails", "Email-адреса"),
            ("html_tags", "HTML теги"),
            ("hex_codes", "Hex-коды"),
            ("short_strings", "Короткие строки")
        ]
        
        for filter_name, label in filters_all:
            widget = create_filter_widget(filters_column, filter_name, label)
            
            if filter_name == "short_strings":
                len_frame = tk.Frame(filters_column, bg=colors['bg'])
                len_frame.pack(anchor=tk.W, padx=30, pady=2)
                
                tk.Label(len_frame,
                        text="Меньше ",
                        font=('Segoe UI', 9),
                        bg=colors['bg'],
                        fg=colors['fg']).pack(side=tk.LEFT)
                
                entry = tk.Entry(len_frame,
                               textvariable=self.short_strings_length,
                               font=('Segoe UI', 10),
                               width=5,
                               bg=colors['entry_bg'],
                               fg=colors['entry_fg'],
                               relief=tk.SOLID,
                               bd=1)
                entry.pack(side=tk.LEFT, padx=5)
                
                self.add_context_menu(entry)
                
                tk.Label(len_frame,
                        text="символов",
                        font=('Segoe UI', 10),
                        bg=colors['bg'],
                        fg=colors['fg']).pack(side=tk.LEFT)
        
        exclude_frame = tk.LabelFrame(buttons_column,
                                     text="◯ Исключить ",
                                     font=('Segoe UI', 9),
                                     bg=colors['bg'],
                                     fg=colors['fg'],
                                     relief=tk.GROOVE,
                                     bd=1)
        exclude_frame.pack(fill=tk.X, pady=(0, 10))
        
        CustomButton(exclude_frame,
                  text="☑ Активировать все",
                  command=self.activate_all_exclude,
                  style='success',
                  width=25).pack(pady=2, padx=5)
        
        CustomButton(exclude_frame,
                  text="⏹ Деактивировать все",
                  command=self.deactivate_all_exclude,
                  style='danger',
                  width=25).pack(pady=2, padx=5)
        
        include_frame = tk.LabelFrame(buttons_column,
                                     text="◯ Включить ",
                                     font=('Segoe UI', 9),
                                     bg=colors['bg'],
                                     fg=colors['fg'],
                                     relief=tk.GROOVE,
                                     bd=1)
        include_frame.pack(fill=tk.X, pady=(0, 10))
        
        CustomButton(include_frame,
                  text="☑ Активировать все",
                  command=self.activate_all_include,
                  style='success',
                  width=25).pack(pady=2, padx=5)
        
        CustomButton(include_frame,
                  text="⏹ Деактивировать все",
                  command=self.deactivate_all_include,
                  style='danger',
                  width=25).pack(pady=2, padx=5)
        
        reset_frame = tk.LabelFrame(buttons_column,
                                   text="☑ Сброс ",
                                   font=('Segoe UI', 9),
                                   bg=colors['bg'],
                                   fg=colors['fg'],
                                   relief=tk.GROOVE,
                                   bd=1)
        reset_frame.pack(fill=tk.X)
        
        CustomButton(reset_frame,
                  text="⏹ Деактивировать все",
                  command=self.deactivate_all_filters,
                  style='warning',
                  width=25).pack(pady=2, padx=5)
        
        CustomButton(reset_frame,
                  text="🔄 По умолчанию",
                  command=self.reset_filters,
                  style='danger',
                  width=25).pack(pady=2, padx=5)
        
        # Подсказка
        self.add_tip_widget(tab, "FILTERS_TIP_TEXT")
    
    def setup_blackwhite_tab(self):
        """Настройка вкладки черного/белого списка"""
        tab = self.tabs['blackwhite']
        colors = self.theme_manager.colors

        # --- ЧЕРНЫЙ СПИСОК ---
        black_frame = tk.LabelFrame(tab,
                                   text=" ⚫ Черный список (исключить всегда) ",
                                   font=('Segoe UI', 10, 'bold'),
                                   bg=colors['bg'],
                                   fg=colors['fg'],
                                   relief=tk.GROOVE,
                                   bd=1)
        black_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=10)

        tk.Label(black_frame,
                text="Строки/слова/символы для исключения (разделитель новая строка):",
                font=('Segoe UI', 9, 'bold'),
                bg=colors['bg'],
                fg=colors['fg']).pack(anchor=tk.W, padx=10, pady=(5, 5))

        black_content_frame = tk.Frame(black_frame, bg=colors['bg'])
        black_content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Текстовое поле
        self.blacklist_text_widget = scrolledtext.ScrolledText(
            black_content_frame,
            height=10,
            wrap='word',
            font=('Consolas', 9),
            bg=colors['text_bg'],
            fg=colors['text_fg'],
            relief=tk.GROOVE,
            bd=1,
        )
        self.blacklist_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.add_context_menu(self.blacklist_text_widget)

        # Фрейм для кнопок (без фиксированной ширины — теперь каждая кнопка сама задаёт размер)
        black_buttons_frame = tk.Frame(black_content_frame, bg=colors['bg'], width=150)
        black_buttons_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))

        # Вспомогательная функция для создания кнопки фиксированной ширины
        def make_button(parent, text, cmd, style, width_px=160):
            frame = tk.Frame(parent, width=width_px, height=32, bg=parent['bg'])
            frame.pack_propagate(False)
            frame.pack(pady=(0, 5), padx=5)
            btn = CustomButton(frame, text=text, command=cmd, style=style)
            btn.pack(fill=tk.BOTH, expand=True)
            return btn

        # Кнопки чёрного списка
        make_button(black_buttons_frame, "🗑 Очистить", lambda: self.clear_list_or_text('black'), 'danger')
        make_button(black_buttons_frame, "📂 Загрузить", lambda: self.load_list_or_text('black'), 'warning')
        make_button(black_buttons_frame, "💾 Сохранить", lambda: self.save_list_or_text('black'), 'success')


        # --- БЕЛЫЙ СПИСОК ---
        white_frame = tk.LabelFrame(tab,
                                   text=" ⚪ Белый список (включить всегда) ",
                                   font=('Segoe UI', 10, 'bold'),
                                   bg=colors['bg'],
                                   fg=colors['fg'],
                                   relief=tk.GROOVE,
                                   bd=1)
        white_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=10)

        tk.Label(white_frame,
                text="Строки/слова/символы для включения (разделитель новая строка):",
                font=('Segoe UI', 9, 'bold'),
                bg=colors['bg'],
                fg=colors['fg']).pack(anchor=tk.W, padx=10, pady=(5, 5))

        white_content_frame = tk.Frame(white_frame, bg=colors['bg'])
        white_content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.whitelist_text_widget = scrolledtext.ScrolledText(
            white_content_frame,
            height=10,
            wrap='word',
            font=('Consolas', 9),
            bg=colors['text_bg'],
            fg=colors['text_fg'],
            relief=tk.SOLID,
            bd=1,
        )
        self.whitelist_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.add_context_menu(self.whitelist_text_widget)

        white_buttons_frame = tk.Frame(white_content_frame, bg=colors['bg'], width=150)
        white_buttons_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))

        # Кнопки белого списка
        make_button(white_buttons_frame, "🗑 Очистить", lambda: self.clear_list_or_text('white'), 'danger')
        make_button(white_buttons_frame, "📂 Загрузить", lambda: self.load_list_or_text('white'), 'warning')
        make_button(white_buttons_frame, "💾 Сохранить", lambda: self.save_list_or_text('white'), 'success')

        # --- ГЛОБАЛЬНАЯ ОПЦИЯ ---
        option_frame = tk.Frame(tab, bg=colors['bg'])
        option_frame.pack(fill=tk.X, pady=(10, 5), padx=10)

        tk.Checkbutton(option_frame,
                       text="Применять списки к исходным строкам (с кавычками)",
                       variable=self.apply_lists_to_raw_strings,
                       font=('Segoe UI', 9, 'bold'),
                       bg=colors['bg'],
                       fg=colors['fg'],
                       selectcolor=colors['bg'],
                       activebackground=colors['bg'],
                       activeforeground=colors['fg']).pack(anchor=tk.W)

        tk.Label(option_frame,
                 text="⚠️ По умолчанию списки применяются к содержимому строк (без кавычек)",
                 font=('Segoe UI', 9),
                 bg=colors['bg'],
                 fg=colors['warning']).pack(anchor=tk.W, pady=(2, 0))

        # --- ПОДСКАЗКА ---
        self.add_tip_widget(tab, "BLACK_WHITE_LISTS_TIP_TEXT")
    
    def setup_settings_tab(self):
        """Настройка вкладки настроек"""
        tab = self.tabs['settings']
        colors = self.theme_manager.colors
        
        tk.Label(tab,
                text="Настройки приложения",
                font=('Segoe UI', 11, 'bold'),
                bg=colors['bg'],
                fg=colors['fg']).pack(anchor=tk.W, pady=(10, 5), padx=10)
        
        btn_frame = tk.Frame(tab, bg=colors['bg'])
        btn_frame.pack(fill=tk.X, pady=(5, 10), padx=10)
         
        CustomButton(btn_frame,
                  text="🔄 Сбросить все настройки",
                  command=self.reset_all,
                  style='danger').pack(side=tk.RIGHT, padx=5)
        
        CustomButton(btn_frame,
                  text="📂 Загрузить профиль",
                  command=self.load_profile,
                  style='warning').pack(side=tk.RIGHT, padx=5)
       
        CustomButton(btn_frame,
                  text="💾 Сохранить профиль",
                  command=self.save_profile,
                  style='success').pack(side=tk.RIGHT, padx=5)
        
        encoding_frame = tk.LabelFrame(tab,
                                      text=" Кодировка файлов ",
                                      font=('Segoe UI', 10, 'bold'),
                                      bg=colors['bg'],
                                      fg=colors['fg'],
                                      relief=tk.GROOVE,
                                      bd=1)
        encoding_frame.pack(fill=tk.X, pady=(0, 15), padx=10)
        
        auto_frame = tk.Frame(encoding_frame, bg=colors['bg'])
        auto_frame.pack(fill=tk.X, pady=5, padx=10)
        
        tk.Checkbutton(auto_frame,
                      text="Автоопределение кодировки входных файлов",
                      variable=self.auto_detect_encoding,
                      command=self.toggle_encoding_manual,
                      font=('Segoe UI', 9),
                      bg=colors['bg'],
                      fg=colors['fg'],
                      selectcolor=colors['bg'],
                      activebackground=colors['bg'],
                      activeforeground=colors['fg']).pack(side=tk.LEFT)
        
        enc_frame = tk.Frame(encoding_frame, bg=colors['bg'])
        enc_frame.pack(fill=tk.X, pady=5, padx=10)
        
        self.encoding_selector = CustomComboBox(
            enc_frame,
            values=self.config_manager.ENCODINGS,
            items_per_row=8
        )
        self.encoding_selector.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.encoding_selector.bind('<<OptionSelected>>', self.on_encoding_selected)
        
        limit_frame = tk.LabelFrame(tab,
                           text=" Лимит строк ",
                           font=('Segoe UI', 10, 'bold'),
                           bg=colors['bg'],
                           fg=colors['fg'],
                           relief=tk.GROOVE,
                           bd=1)
        limit_frame.pack(fill=tk.X, pady=(0, 15), padx=10)

        # Основной фрейм для всех элементов в одной строке
        control_frame = tk.Frame(limit_frame, bg=colors['bg'])
        control_frame.pack(fill=tk.X, pady=5, padx=10)

        # Чекбокс слева
        checkbutton = tk.Checkbutton(control_frame,
                                   text="Предупреждение о превышении лимита:",
                                   variable=self.enable_line_limit,
                                   command=self.toggle_line_limit,
                                   font=('Segoe UI', 9),
                                   bg=colors['bg'],
                                   fg=colors['fg'],
                                   selectcolor=colors['bg'],
                                   activebackground=colors['bg'],
                                   activeforeground=colors['fg'])
        checkbutton.pack(side=tk.LEFT, padx=(0, 5))

        # Поле ввода по центру
        self.limit_entry = tk.Entry(control_frame,
                                  textvariable=self.line_limit,
                                  font=('Segoe UI', 9),
                                  width=10,
                                  bg=colors['entry_bg'],
                                  fg=colors['entry_fg'],
                                  relief=tk.SOLID,
                                  bd=1)
        self.limit_entry.pack(side=tk.LEFT, padx=5)
        self.add_context_menu(self.limit_entry)

        # Метка справа
        tk.Label(control_frame,
                text="строк",
                font=('Segoe UI', 9),
                bg=colors['bg'],
                fg=colors['fg']).pack(side=tk.LEFT)
        
        app_frame = tk.LabelFrame(tab,
                         text=" Разное ",
                         font=('Segoe UI', 10, 'bold'),
                         bg=colors['bg'],
                         fg=colors['fg'],
                         relief=tk.GROOVE,
                         bd=1)
        app_frame.pack(fill=tk.X, pady=(0, 15), padx=10)

        # Создаем фрейм для двух колонок
        columns_frame = tk.Frame(app_frame, bg=colors['bg'])
        columns_frame.pack(fill=tk.X, pady=10, padx=10)

        # Настройки для двух колонок
        settings = [
            ("Показывать подробные логи в отчете", self.show_all_logs, None),
            ("Показывать отладочную информацию", self.show_debug_logs, None),
            ("Автоматически открывать созданные файлы", self.auto_open_files, None),
            ("Темная тема", self.dark_mode, self.apply_theme)
        ]

        # Разделяем настройки на две колонки
        mid_index = len(settings) // 2 + len(settings) % 2  # 2 для четного, 3 для нечетного
        left_settings = settings[:mid_index]
        right_settings = settings[mid_index:]

        # Левая колонка
        left_frame = tk.Frame(columns_frame, bg=colors['bg'])
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        for text, var, cmd in left_settings:
            cb = tk.Checkbutton(left_frame,
                               text=text,
                               variable=var,
                               command=cmd,
                               font=('Segoe UI', 9),
                               bg=colors['bg'],
                               fg=colors['fg'],
                               selectcolor=colors['bg'],
                               activebackground=colors['bg'],
                               activeforeground=colors['fg'],
                               anchor='w')
            cb.pack(fill=tk.X, pady=3)

        # Правая колонка
        right_frame = tk.Frame(columns_frame, bg=colors['bg'])
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        for text, var, cmd in right_settings:
            cb = tk.Checkbutton(right_frame,
                               text=text,
                               variable=var,
                               command=cmd,
                               font=('Segoe UI', 9),
                               bg=colors['bg'],
                               fg=colors['fg'],
                               selectcolor=colors['bg'],
                               activebackground=colors['bg'],
                               activeforeground=colors['fg'],
                               anchor='w')
            cb.pack(fill=tk.X, pady=3)
        
        # Подсказка
        self.add_tip_widget(tab, "SETTINGS_TIP_TEXT")
    
    def setup_status_bar(self, parent):
        """Настройка строки состояния"""
        colors = self.theme_manager.colors
        
        # Создаем основной фрейм строки состояния
        self.status_bar = tk.Frame(parent, bg=colors['status'], height=25)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_bar.pack_propagate(False)  # Фиксируем высоту
        
        # Создаем переменную для текста статуса
        self.status_var = tk.StringVar(value="")
        
        self.status_label = tk.Label(
            self.status_bar,  # Родитель - сам status_bar
            textvariable=self.status_var,
            font=('Segoe UI', 10),
            fg=colors['text_fg'],      # Цвет текста
            bg=colors['status'],       # Цвет фона
            anchor='w'                 # Выравнивание текста по левому краю
        )
        self.status_label.pack(side=tk.LEFT, padx=15, fill=tk.Y)
    
    # ==================== ОСНОВНЫЕ МЕТОДЫ РАБОТЫ ====================
    
    def on_tab_changed(self, event):
        """Обработчик смены вкладки"""
        # Получаем индекс текущей вкладки
        current_tab_index = self.notebook.current_tab
        
        # Если есть текущая вкладка
        if current_tab_index is not None:
            # Получаем содержимое текущей вкладки
            current_tab_content = self.notebook.tabs[current_tab_index]['content']
            
            # Проверяем, что это не вкладка логов
            if current_tab_content != self.tabs['logs']:
                self.last_active_tab_index = current_tab_index
    
    def on_window_configure(self, event):
        """Отслеживаем изменение окна: сохраняем нормальную геометрию, если не в zoomed"""
        if event.widget != self.root:
            return

        try:
            current_state = self.root.wm_state()
            if current_state == 'zoomed':
                self.window_is_zoomed = True
            else:
                self.window_is_zoomed = False
                self.last_normal_geometry = self.root.geometry()
        except:
            pass
    
    def browse_input_files(self):
        """Выбор нескольких файлов"""
        start_time = time.time()
        files = filedialog.askopenfilenames(title="Выберите входные файлы")
        
        if self.show_debug_logs.get():
            debug_info = DebugInfo.format_operation_info("Выбор файлов", start_time)
            for line in debug_info:
                self.log_message(f"{line}", 'debug')
        
        if files:
            new_files = list(files)
            added_count = 0
            
            for file in new_files:
                if file not in self.input_files:
                    # Добавляем файл в список
                    self.input_files.append(file)
                    
                    # Получаем информацию о файле и добавляем к общим счетчикам
                    info = self.get_file_info(file)
                    self.file_info_cache[file] = info
                    self.total_files_count += 1
                    self.total_files_size += info['size']
                    self.total_files_lines += info['lines']
                    
                    added_count += 1
            
            self.update_file_list()
            self.log_message(f"+ Добавлено файлов: {added_count}")
    
    def browse_folder(self):
        """Добавление всех файлов из папки"""
        start_time = time.time()
        folder = filedialog.askdirectory(title="Выберите папку")
        
        if self.show_debug_logs.get():
            debug_info = DebugInfo.format_operation_info("Выбор папки", start_time)
            for line in debug_info:
                self.log_message(f"{line}", 'debug')
        
        if folder:
            added_count = 0
            
            # Собираем все файлы из папки
            all_files = []
            for root_dir, dirs, files in os.walk(folder):
                for file in files:
                    file_path = os.path.join(root_dir, file)
                    all_files.append(file_path)
            
            # Включаем буферизацию логов
            buffer_threshold = min(max(50, len(all_files) * 5), 1000)
            self.enable_message_buffer(buffer_threshold)
            
            for file_path in all_files:
                if file_path not in self.input_files:
                    self.input_files.append(file_path)
                    
                    # Получаем информацию о файле
                    info = self.get_file_info(file_path)
                    self.file_info_cache[file_path] = info
                    self.total_files_count += 1
                    self.total_files_size += info['size']
                    self.total_files_lines += info['lines']
                    
                    added_count += 1
            
            self.update_file_list()
            self.log_message(f"+ Добавлено файлов из папки: {added_count}")
            
            # Выключаем буферизацию и сбрасываем оставшиеся сообщения
            self.disable_message_buffer()
    
    def remove_selected_files(self):
        """Удаление выбранных файлов из списка (поддержка множественного выделения)"""
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showinfo("Информация", "Выделите файлы для удаления")
            return
        
        selected_count = len(selection)
        
        # Подтверждение удаления с информацией о количестве
        if selected_count == 1:
            # Для одного файла показываем имя
            index = selection[0]
            filename = os.path.basename(self.input_files[index])
            message = f"Удалить файл из списка?\n\n{filename}\n\n"
        else:
            # Для нескольких файлов показываем количество
            message = f"Удалить {selected_count} файл(ов) из списка?\n\n"
        
        message += "Файлы не будут удалены с диска, только из списка в программе."
        
        response = messagebox.askyesno("Подтверждение", message)
        
        if not response:
            return
        
        # Собираем информацию об удаляемых файлах
        removed_files_info = []
        total_size_removed = 0
        total_lines_removed = 0
        
        # Удаляем файлы в обратном порядке (чтобы индексы не смещались)
        for index in sorted(selection, reverse=True):
            if 0 <= index < len(self.input_files):
                removed_file = self.input_files[index]
                filename = os.path.basename(removed_file)
                
                # Собираем информацию для лога
                if removed_file in self.file_info_cache:
                    info = self.file_info_cache.pop(removed_file)
                    total_size_removed += info['size']
                    total_lines_removed += info['lines']
                    removed_files_info.append(f"{filename} ({info['size']/1024:.1f} КБ)")
                else:
                    removed_files_info.append(filename)
                
                # Удаляем файл из списка
                del self.input_files[index]
        
        # Обновляем счетчики
        self.total_files_count -= selected_count
        self.total_files_size -= total_size_removed
        self.total_files_lines -= total_lines_removed
        
        # Обновляем отображение
        self.update_file_list()
        
        # Логируем результат
        self.log_message(f"— Удалено файлов: {selected_count}")
        
        self.update_status(f"Удалено файлов: {selected_count}", 'success')
    
    def clear_file_list(self):
        """Очистка списка файлов"""
        if not self.input_files:
            return
        
        # Сбрасываем все счетчики и кэш
        self.file_info_cache = {}
        self.total_files_count = 0
        self.total_files_size = 0
        self.total_files_lines = 0
        
        files_to_clear = self.input_files
        self.input_files = []
        del files_to_clear
        
        self.update_file_list()
        self.log_message("Список файлов очищен")
    
    def update_all_files_cache(self):
        """Обновить кэш информации о всех файлах"""
        start_time = time.time()
        
        # Проверяем, можно ли использовать существующий кэш
        if (self.file_info_cache and 
            self.validate_file_info_cache(self.input_files)):
            
            if self.show_debug_logs.get():
                self.log_message("Используется актуальный кэш информации о файлах", 'debug')
            return
        
        # Если кэш неактуален или пуст, пересчитываем
        self.total_files_count = len(self.input_files)
        self.total_files_size = 0
        self.total_files_lines = 0
        self.file_info_cache = {}
        
        if not self.input_files:
            if self.show_debug_logs.get():
                self.log_message("Нет файлов для кэширования", 'debug')
            return
        
        files_count = len(self.input_files)
        
        if self.show_debug_logs.get():
            self.log_message(f"Начинается обновление кэша для {files_count} файлов", 'debug')
        
        processed = 0
        for file_path in self.input_files:
            info = self.get_file_info(file_path)
            self.file_info_cache[file_path] = info
            self.total_files_size += info['size']
            self.total_files_lines += info['lines']
            processed += 1
            
            # Прогресс для отладки
            if self.show_debug_logs.get() and processed % 10 == 0:
                self.log_message(f"Прогресс обновления кэша: {processed}/{files_count} файлов", 'debug')
        
        self.update_file_info()
        
        if self.show_debug_logs.get():
            debug_info = DebugInfo.format_operation_info(
                f"Кэш обновлен: файлов {self.total_files_count}, {self.total_files_size} байт, {self.total_files_lines} строк", 
                start_time
            )
            for line in debug_info:
                self.log_message(f"{line}", 'debug')
    
    def get_file_info(self, file_path):
        """Получить информацию о файле (размер и количество строк)"""
        start_time = time.time()
        
        if not os.path.exists(file_path):
            if self.show_debug_logs.get():
                self.log_message(f"Файл не существует: {os.path.basename(file_path)}", 'debug')
            return {'size': 0, 'lines': 0}
        
        try:
            # Получаем размер файла
            file_size = os.path.getsize(file_path)
            
            # Получаем количество строк (оптимизированно)
            lines_count = 0
            encoding_used = 'неизвестно'
            
            try:
                # Пробуем определить кодировку для быстрого чтения
                encoding_used = self.file_processor.detect_encoding(
                    file_path,
                    self.auto_detect_encoding.get(),
                    self.encoding.get()
                )
                
                with open(file_path, 'r', encoding=encoding_used, errors='ignore') as f:
                    # Используем оптимизированный подсчет строк
                    chunk_size = 8192
                    read_chunk = functools.partial(f.read, chunk_size)
                    for chunk in iter(read_chunk, ''):
                        lines_count += chunk.count('\n')
                    
                    # Если файл не заканчивается новой строкой
                    f.seek(0)
                    if f.read()[-1:] != '\n':
                        lines_count += 1
                        
            except Exception as e:
                # Если не удалось определить кодировку или прочитать, используем простой метод
                if self.show_debug_logs.get():
                    self.log_message(f"Используется бинарный режим для {os.path.basename(file_path)}: {str(e)}", 'debug')
                
                encoding_used = 'binary'
                with open(file_path, 'rb') as f:
                    for chunk in iter(functools.partial(f.read, 8192), b''):
                        lines_count += chunk.count(b'\n')
            
            result = {'size': file_size, 'lines': lines_count}
            
            if self.show_debug_logs.get():
                size_kb = file_size / 1024
                debug_info = DebugInfo.format_operation_info(f"Файл: {os.path.basename(file_path)}, {size_kb:.1f} КБ, строк {lines_count}, {encoding_used}", start_time)
                for line in debug_info:
                    self.log_message(f"{line}", 'debug')
            
            return result
            
        except Exception as e:
            if self.show_debug_logs.get():
                debug_time = time.time() - start_time
                self.log_message(f"Ошибка получения информации о файле {os.path.basename(file_path)}: {str(e)}, время: {debug_time:.3f} сек", 'debug')
            return {'size': 0, 'lines': 0}
    
    def update_file_info(self):
        """Обновление информации о файлах"""
        if self.show_debug_logs.get():
            start_time = time.time()
        
        count = self.total_files_count
        
        # Форматируем размер
        if self.total_files_size < 1024 * 1024:
            size_text = f"{self.total_files_size / 1024:.1f} КБ"
        else:
            size_text = f"{self.total_files_size / (1024 * 1024):.1f} МБ"

        if hasattr(self, 'files_info_label'):
            self.files_info_label.config(
                text=f"Файлов: {count} |  Размер: {size_text} |  Строк: {self.total_files_lines}")
        
        if self.show_debug_logs.get():
            debug_info = DebugInfo.format_operation_info(f"Обновлено: файлов {count}, {size_text}, строк {self.total_files_lines}", start_time)
            for line in debug_info:
                self.log_message(f"{line}", 'debug')
    
    def update_file_list(self):
        """Обновить отображение списка файлов в Listbox"""
        if not hasattr(self, 'file_listbox') or not self.file_listbox:
            if self.show_debug_logs.get():
                self.log_message("Список файлов недоступен для обновления", 'debug')
            return
        
        start_time = time.time()
        self.file_listbox.delete(0, tk.END)
        
        files_count = len(self.input_files)
        max_digits = len(str(files_count))
        
        for i, file in enumerate(self.input_files, 1):
            filename = os.path.basename(file)
            parent_dir = os.path.basename(os.path.dirname(file))
            
            # Получаем вторую родительскую папку
            parent_full = os.path.dirname(file)
            second_parent = os.path.basename(os.path.dirname(parent_full))
            
            formatted_number = str(i).zfill(max_digits)
            display_text = f"{formatted_number}. {filename}"
            
            # Добавляем информацию о папках, если они существуют
            if second_parent and parent_dir:
                display_text += f" ({second_parent}\\{parent_dir})"
            elif parent_dir:
                display_text += f" ({parent_dir})"
            
            self.file_listbox.insert(tk.END, display_text)
        
        self.update_file_info()
    
    def extract_strings(self):
        """Извлечение строк из файлов"""
        self.toggle_cancel_button(True)
        self.root.update()
        
        start_time = time.time()
        
        # Проверяем, не запрошена ли отмена
        if self.cancel_requested:
            self.log_message("Операция отменена", 'warning')
            self.toggle_cancel_button(False)
            return
        
        if not self.input_files:
            self.log_message("Не выбраны входные файлы", 'error')
            self.update_status("Нет файлов", 'error')
            messagebox.showwarning("Внимание", "Нет входных файлов. Добавьте файлы для обработки")
            self.toggle_cancel_button(False)
            return
        
        # Получение шаблона поиска
        pattern = self.get_search_pattern()
        if not pattern:
            self.log_message("Ошибка в шаблоне поиска", 'error')
            self.update_status("Ошибка шаблона", 'error')
            self.toggle_cancel_button(False)
            messagebox.showerror("Ошибка", "Неверный шаблон поиска")
            return
        
        # Проверка настроек
        if not self.validate_settings():
            self.toggle_cancel_button(False)
            return
        
        # Проверка общего лимита строк всех файлов
        if self.enable_line_limit.get():
            try:
                limit = int(self.line_limit.get())
                total_lines = self.total_files_lines
                
                if total_lines > limit:
                    self.log_message(f"Общее количество строк всех файлов: {total_lines}, превышает лимит {limit}", 'warning')
                    
                    response = messagebox.askyesno(
                        "Внимание", 
                        f"Общее количество строк всех файлов: {total_lines}, превышает лимит {limit} (вкладка Настройки).\n\n"
                        "Продолжить обработку всех файлов?"
                    )
                    
                    if not response:
                        self.log_message("Обработка отменена пользователем")
                        self.toggle_cancel_button(False)
                        return
                    
            except ValueError:
                pass
        
        # Применение списков
        try:
            self.apply_lists()
        except Exception as e:
            self.toggle_cancel_button(False)
            return
        
        self.update_status("Извлечение...", 'working')
        all_strings = []
        total_files = len(self.input_files)
        
        # Включаем буферизацию логов
        buffer_threshold = min(max(50, total_files * 5), 5000)
        self.enable_message_buffer(buffer_threshold)
        
        if self.show_debug_logs.get():
            debug_info = DebugInfo.format_operation_info("Начало извлечения строк")
            for line in debug_info:
                self.log_message(f"{line}", 'debug')
        
        for file_idx, input_file in enumerate(self.input_files, 1):
            # Проверка отмены на каждом файле
            if self.cancel_requested:
                self.log_message(f"Операция отменена пользователем на файле {file_idx}/{total_files}", 'warning')
                break
            
            self.log_message(f"🔍 Обработка файла {file_idx}/{total_files}: {os.path.basename(input_file)}")
            
            try:
                file_start_time = time.time()
                file_encoding = self.file_processor.detect_encoding(
                    input_file,
                    self.auto_detect_encoding.get(),
                    self.encoding.get()
                )
                self.log_message(f"Кодировка: {file_encoding}")
                
                with open(input_file, 'r', encoding=file_encoding) as f:
                    content = f.read()
                
                if self.show_debug_logs.get():
                    file_size = os.path.getsize(input_file) if os.path.exists(input_file) else 0
                    self.log_message(f"Файл {os.path.basename(input_file)}: {len(content)} символов, {file_size} байт, {file_encoding}", 'debug')
                
                if self.ignore_comments.get():
                    content = self.file_processor.preprocess_content_for_comments(
                        content,
                        self.single_line_comment.get(),
                        self.multi_line_comment_start.get(),
                        self.multi_line_comment_end.get()
                    )
                
                found_strings = re.findall(pattern, content, re.DOTALL)
                
                if self.show_debug_logs.get():
                    file_time = time.time() - file_start_time
                    self.log_message(f"Найдено строк: {len(found_strings)}, время поиска: {file_time:.3f} сек", 'debug')
                else:
                    self.log_message(f"Найдено строк: {len(found_strings)}")
                
                filtered_strings = self.filter_strings(found_strings)
                all_strings.extend(filtered_strings)
                
            except Exception as e:
                self.log_message(f"Ошибка обработки файла: {str(e)}", 'error')
                continue
        
        # Выключаем буферизацию и сбрасываем оставшиеся сообщения
        self.disable_message_buffer()
        
        # Проверка отмены перед сохранением
        if self.cancel_requested:
            self.log_message("Операция отменена, результаты не сохранены", 'warning')
            self.toggle_cancel_button(False)
            self.update_status("Отменено", 'warning')
            messagebox.showwarning("Операция отменена", "Операция отменена, результаты не сохранены")
            return
        
        # Сохраняем порядок появления строк
        unique_strings = []
        seen = set()
        for string in all_strings:
            if string not in seen:
                seen.add(string)
                unique_strings.append(string)
        
        if self.show_debug_logs.get():
            operation_info = DebugInfo.format_operation_info(
                operation="Извлечение строк",
                start_time=start_time,
                extra_info=[
                    f"Файлов: {total_files}",
                    f"Найдено строк: {len(found_strings) if found_strings else 0}",
                    f"Уникальных строк: {len(unique_strings)}"
                ]
            )
            for line in operation_info:
                self.log_message(f"{line}", 'debug')
        
        overall_time = time.time() - start_time
        self.log_message(f"Поиск завершен ({overall_time:.3f} сек)", 'success')
        self.save_extraction_results(unique_strings, total_files)
        self.toggle_cancel_button(False)
        self.update_status(f"Найдено строк: {len(unique_strings)}", 'success')
        
        
    
    def apply_translation(self):
        """Применение перевода"""
        self.toggle_cancel_button(True)
        self.root.update()
    
        start_time = time.time()
        
        # Проверяем отмену
        if self.cancel_requested:
            self.log_message("Операция отменена", 'warning')
            self.toggle_cancel_button(False)
            return
        
        if not self.input_files:
            self.log_message("Не выбраны входные файлы", 'error')
            self.update_status("Нет файлов", 'error')
            messagebox.showwarning("Внимание", "Нет входных файлов. Добавьте файлы для обработки")
            self.toggle_cancel_button(False)
            return
        
        if self.show_debug_logs.get():
            debug_info = DebugInfo.format_operation_info("Начало применения перевода")
            for line in debug_info:
                self.log_message(f"{line}", 'debug')
        
        try:
            # Чтение файлов перевода
            original_strings = self.read_strings_file(self.original_strings_file.get())
            translation_strings = self.read_strings_file(self.translation_file.get())
            
            if not original_strings or not translation_strings:
                self.log_message("Файл(ы) пуст(ы)", 'error')
                self.toggle_cancel_button(False)
                return
            
            # Включаем буферизацию логов
            buffer_threshold = min(max(50, len(original_strings) * 2), 1000)
            self.enable_message_buffer(buffer_threshold)
            
            # Применение перевода
            total_replaced = self.apply_translation_to_files(original_strings, translation_strings)
            
            # Выключаем буферизацию логов
            self.disable_message_buffer()
            
            # Проверка отмены
            if self.cancel_requested:
                self.log_message("Операция отменена пользователем", 'warning')
                self.toggle_cancel_button(False)
                self.update_status("Отменено", 'warning')
                return
            
            # Открытие результата
            if self.auto_open_files.get():
                self.open_output_file()
            
            if self.show_debug_logs.get():
                debug_info = DebugInfo.format_operation_info("Завершение применения перевода", start_time)
                for line in debug_info:
                    self.log_message(f"{line}", 'debug')
            
            self.toggle_cancel_button(False)
            self.update_status(f"Заменено строк: {total_replaced}", 'success')
            
        except Exception as e:
            # Выключаем буферизацию
            self.disable_message_buffer()
                
            self.log_message(f"Ошибка: {str(e)}", 'error')
            self.toggle_cancel_button(False)
            self.update_status("Ошибка", 'error')
    
    # ==================== МЕТОДЫ РАБОТЫ С ТЕМОЙ ====================
    
    def toggle_theme(self):
        """Переключение темы"""
        start_time = time.time()
        self.dark_mode.set(not self.dark_mode.get())
        self.apply_theme()
        
        if self.show_debug_logs.get():
            debug_info = DebugInfo.format_operation_info("Переключение темы", start_time)
            for line in debug_info:
                self.log_message(f"{line}", 'debug')
    
    def apply_theme(self):
        """Применить текущую тему ко всему интерфейсу"""
        # Обновление менеджера тем
        if self.dark_mode.get() != (self.theme_manager.current_theme == 'dark'):
            self.theme_manager.set_theme('dark' if self.dark_mode.get() else 'light')
        
        colors = self.theme_manager.colors
        
        # Обновление текста кнопки темы
        self.theme_button.config(text=self.theme_manager.get_button_text())
        
        # Меняем цвет фона/рамки главного окна
        self.root.configure(bg=colors['primary'])
        
        # Обновление цветов стандартных/кастомных виджетов рекурсивно
        self.update_widget_colors(self.root)
        
        # Обновление контекстных меню
        if self.context_menu:
            self.context_menu.update_colors(colors)
        
        # Обновление строки статуса
        if hasattr(self, 'status_bar'):
            self.status_bar.config(bg=colors['status'])
        if hasattr(self, 'status_label'):
            self.status_label.config(
                bg=colors['status'],
                fg=colors['text_fg'])
    
    def update_widget_colors(self, widget):
        """Обновить цвета виджета и его дочерних элементов"""
        colors = self.theme_manager.colors
        try:
            widget_type = type(widget).__name__
            
            if widget_type == 'Frame':
                widget.config(bg=colors['bg'])
            elif widget_type == 'Label':
                widget.config(bg=colors['bg'], fg=colors['fg'])
            elif widget_type == 'Entry':
                widget.config(
                    bg=colors['entry_bg'],
                    fg=colors['entry_fg'],
                    disabledbackground=colors['entry_bg'],
                    disabledforeground=colors['entry_fg'],
                    insertbackground=colors['entry_fg']
                )
            elif widget_type == 'Text':
                widget.config(
                    bg=colors['text_bg'],
                    fg=colors['text_fg'],
                    insertbackground=colors['text_fg']
                )
            elif widget_type == 'ScrolledText':
                widget.config(
                    bg=colors['text_bg'],
                    fg=colors['text_fg']
                )
            elif widget_type in ['Checkbutton', 'Radiobutton']:
                widget.config(
                    bg=colors['bg'],
                    fg=colors['fg'],
                    selectcolor=colors['primary'],
                    activebackground=colors['bg'],
                    activeforeground=colors['fg']
                )
            elif widget_type == 'Listbox':
                widget.config(
                    bg=colors['text_bg'],
                    fg=colors['text_fg'],
                    selectbackground=colors['primary'],
                    selectforeground=colors['text_fg']
                )
                for i in range(widget.size()):
                    widget.itemconfig(i, bg=colors['text_bg'])
            elif widget_type == 'LabelFrame':
                widget.config(bg=colors['bg'], fg=colors['fg'])
            elif widget_type == 'Button':
                widget.config(
                    bg=colors['primary'],
                    fg=colors['text_fg'],
                    activebackground=colors['secondary'],
                    activeforeground=colors['text_fg']
                )
            elif widget_type == 'CustomButton':
                widget.set_colors(self.theme_manager)
            elif widget_type == 'CustomNotebook':
                widget.set_colors(self.theme_manager)
            elif widget_type == 'CustomComboBox':
                widget.set_colors(self.theme_manager)
            elif widget_type == 'Canvas':
                widget.config(bg=colors['bg'])
            
            # Рекурсивное обновление дочерних виджетов
            for child in widget.winfo_children():
                self.update_widget_colors(child)
                
        except Exception as e:
            pass
    

 # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================
    
    def add_tip_widget(self, parent, tip_key: str, height: Optional[int] = None):
        # Получаем текст справки
        try:
            import tips
            tip_text = getattr(tips, tip_key, "⚠️ Справка не найдена")
        except ImportError:
            tip_text = "⚠️ Файл tips.py отсутствует"
        except Exception:
            tip_text = f"⚠️ Ошибка загрузки справки: {tip_key}"
        
        # Определяем высоту
        if height is None:
            line_count = tip_text.count('\n') + 2
            height = max(line_count, 8)
        
        # Создаём фрейм
        tip_frame = tk.Frame(parent, bg=self.theme_manager.colors['bg'])
        tip_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=10)
        
        tk.Label(tip_frame,
                 text="🍄 СПРАВКА:",
                 font=('Segoe UI', 10, 'bold'),
                 bg=self.theme_manager.colors['bg'],
                 fg=self.theme_manager.colors['fg'],
                 anchor=tk.W).pack(fill=tk.X, pady=(0, 5))
                 
        # Создаём текстовое поле
        tip_widget = tk.Text(
            tip_frame,
            font=('Consolas', 9),
            bg=self.theme_manager.colors['text_bg'],
            fg=self.theme_manager.colors['text_fg'],
            relief=tk.SOLID,
            bd=1,
            wrap=tk.WORD,
            padx=5,
            pady=5,
            height=height
        )
        tip_widget.pack(fill=tk.BOTH, expand=True)
        
        # Добавляем контекстное меню и заполняем текст
        self.add_context_menu(tip_widget)
        tip_widget.insert('1.0', tip_text)
        tip_widget.configure(state='disabled')
        
        return tip_widget
    
    def add_context_menu(self, widget):
        """Привязать контекстное меню к виджету"""
        if self.context_menu and isinstance(widget, (tk.Text, tk.Entry, scrolledtext.ScrolledText)):
            self.context_menu.bind_to_widget(widget)
    
    def get_search_pattern(self):
        """Получить шаблон простого поиска"""
        if self.use_custom_regex.get():
            return self.custom_regex.get()
        else:
            before = re.escape(self.search_pattern_before.get())
            after = re.escape(self.search_pattern_after.get())
            escape = re.escape(self.escape_char.get())
            
            if not before and not after:
                return None
            
            return f"{before}(?:{escape}.|[^{escape}{after}])*{after}"
    
    def validate_settings(self):
        """Проверить настройки перед выполнением"""
        if self.ignore_comments.get():
            multi_start = self.multi_line_comment_start.get()
            multi_end = self.multi_line_comment_end.get()
            
            if not multi_start or not multi_end:
                response = messagebox.askyesno(
                    "Внимание", 
                    "Не указано начало или конец многострочного комментария.\n\n"
                    "Продолжить?"
                )
                if not response:
                    self.log_message("Отменено пользователем", 'warning')
                    return False
        
        # Проверка фильтра коротких строк
        if self.filter_active_vars['short_strings'].get():
            try:
                min_len = int(self.short_strings_length.get())
                if min_len <= 0:
                    self.log_message("Длина коротких строк должна быть указана больше 0", 'error')
                    messagebox.showerror("Ошибка", "Длина коротких строк должна быть указана больше 0 (вкладка Фильтрация)")
                    return False
            except ValueError:
                self.log_message("Неверное значение длины коротких строк", 'error')
                messagebox.showerror("Ошибка", "Введите число для длины коротких строк на вкладке Фильтрация")
                return False
        
        # Проверка лимита строк
        if self.enable_line_limit.get():
            try:
                limit = int(self.line_limit.get())
                if limit <= 0:
                    self.log_message("Лимит строк должен быть больше 0", 'error')
                    messagebox.showerror("Ошибка", "Лимит строк должен быть больше 0 (вкладка Настройки)")
                    return False
            except ValueError:
                self.log_message("Неверное значение лимита строк", 'error')
                messagebox.showerror("Ошибка", "Введите число для лимита строк на вкладке Настройки")
                return False
        
        # Предупреждение о режиме применения списков
        if self.apply_lists_to_raw_strings.get():
            self.log_message("Включен режим: Применять Ч/Б списки к исходным строкам", 'warning')
            response = messagebox.askyesno(
                "Внимание", 
                "Включен режим 'Применять Ч/Б списки к исходным строкам'.\n"
                "Теперь Ч/Б списки будут проверяться с учетом кавычек и разделителей.\n"
                "Например, для исключения строки \"Error\" нужно указывать в списке: \"Error\"\n\n"
                "Продолжить?"
            )
            if not response:
                self.log_message("Отменено пользователем", 'warning')
                return False
            
        return True
    
    def apply_lists(self):
        """Применить черный и белый списки"""
        try:
            blacklist_content = self.blacklist_text_widget.get(1.0, tk.END).strip()
            whitelist_content = self.whitelist_text_widget.get(1.0, tk.END).strip()
            
            self.filter_manager.apply_black_white_list('black', blacklist_content)
            self.filter_manager.apply_black_white_list('white', whitelist_content)
            
            if self.show_debug_logs.get():
                self.log_message(f"Черный список: {len(self.filter_manager.blacklist)} элементов", 'debug')
                self.log_message(f"Белый список: {len(self.filter_manager.whitelist)} элементов", 'debug')
            
        except Exception as e:
            self.log_message(f"Ошибка обработки Ч/Б списков: {str(e)}", 'error')
            messagebox.showerror("Ошибка", f"Ошибка обработки Ч/Б списков:\n{str(e)}")
            raise
    
    def filter_strings(self, found_strings):
        """Отфильтровать найденные строки"""
        filtered = []
        
        excluded_by_blacklist = 0
        included_by_whitelist = 0
        excluded_by_filters = 0
        passed = 0
        
        filter_start_time = time.time()
        
        for quoted_string in found_strings:
            content_str = self.file_processor.extract_string_content(
                quoted_string,
                self.use_custom_regex.get(),
                self.search_pattern_before.get(),
                self.search_pattern_after.get()
            )
            
            # Определить, к какой строке применять списки
            if self.apply_lists_to_raw_strings.get():
                text_to_check = quoted_string  # С кавычками/разделителями
            else:
                text_to_check = content_str    # Без кавычек
            
            # Проверка белого списка
            if self.filter_manager.is_in_black_white_list('white', text_to_check):
                filtered.append(quoted_string)
                passed += 1
                included_by_whitelist += 1
                if self.show_all_logs.get():
                    display_text = text_to_check[:55] + "..." if len(text_to_check) > 55 else text_to_check
                    self.log_message(f"✓ Принято (белый список): {display_text}")
                continue
            
            # Проверка черного списка
            if self.filter_manager.is_in_black_white_list('black', text_to_check):
                excluded_by_blacklist += 1
                if self.show_all_logs.get():
                    display_text = text_to_check[:55] + "..." if len(text_to_check) > 55 else text_to_check
                    self.log_message(f" ✗ Отклонено (черный список): {display_text}")
                continue
            
            # Применение фильтров (всегда к содержимому без кавычек)
            should_include = self.should_include_string(content_str)
            if should_include:
                filtered.append(quoted_string)
                passed += 1
            else:
                excluded_by_filters += 1
        
        # Логирование режима
        if self.show_all_logs.get() and self.apply_lists_to_raw_strings.get():
            self.log_message(f"Внимание! Ч/Б списки применяются к исходным строкам (с кавычками)")
        
        if self.show_all_logs.get():
            self.log_message(f"⚫ Итог: принято {passed}, отклонено {excluded_by_filters}, черный список {excluded_by_blacklist}, белый список {included_by_whitelist}")
        
        if self.show_debug_logs.get():
            filter_time = time.time() - filter_start_time
            self.log_message(f"Фильтрация: {len(found_strings)} -> {len(filtered)} строк, время: {filter_time:.3f} сек", 'debug')
        
        return filtered


    def should_include_string(self, text):
        """Определить, следует ли включать строку"""
        any_include_filters_active = False
        any_include_filters_matched = False
        matched_filter_name = None
        
        for filter_name in self.filter_active_vars.keys():
            if self.filter_active_vars[filter_name].get():
                # Получить метод фильтра
                filter_method = getattr(self.filter_manager, filter_name, None)
                
                # Для фильтра коротких строк нужен дополнительный параметр
                if filter_name == "short_strings":
                    try:
                        min_len = int(self.short_strings_length.get())
                        should_filter = self.filter_manager.short_strings(text, min_len)
                    except:
                        should_filter = self.filter_manager.short_strings(text)
                elif filter_method:
                    should_filter = filter_method(text)
                else:
                    should_filter = False
                
                if should_filter:
                    mode = self.filter_mode_vars[filter_name].get()
                    
                    if mode == "exclude":
                        if self.show_all_logs.get():
                            display_text = text[:55] + "..." if len(text) > 55 else text
                            self.log_message(f" ✗ Отклонено ({filter_name}): {self.search_pattern_before.get()}{display_text}{self.search_pattern_after.get()}")
                        return False
                    else:
                        any_include_filters_matched = True
                        any_include_filters_active = True
                        matched_filter_name = filter_name
                else:
                    mode = self.filter_mode_vars[filter_name].get()
                    if mode == "include":
                        any_include_filters_active = True
        
        if any_include_filters_active:
            if any_include_filters_matched:
                if self.show_all_logs.get():
                    display_text = text[:55] + "..." if len(text) > 55 else text
                    self.log_message(f"✓ Принято (фильтр 'Включить'): {self.search_pattern_before.get()}{display_text}{self.search_pattern_after.get()}")
                return True
            else:
                if self.show_all_logs.get():
                    display_text = text[:55] + "..." if len(text) > 55 else text
                    self.log_message(f" ✗ Отклонено (фильтр 'Включить'): {self.search_pattern_before.get()}{display_text}{self.search_pattern_after.get()}")
                return False
        
        if self.show_all_logs.get():
            display_text = text[:55] + "..." if len(text) > 55 else text
            self.log_message(f"✓ Принято: {self.search_pattern_before.get()}{display_text}{self.search_pattern_after.get()}")
        return True
    
    def save_extraction_results(self, unique_strings, total_files):
        """Сохранить результаты извлечения"""
        if unique_strings:
            self.save_strings_file(self.original_strings_file.get(), unique_strings, "оригинал")
            self.save_strings_file(self.translation_file.get(), unique_strings, "перевода")
            
            if self.auto_open_files.get():
                self.open_file(self.translation_file.get())
            
            self.log_message(f"⚫ Итого уникальных строк: {len(unique_strings)}", 'success')
            self.update_status(f"Извлечено: {len(unique_strings)} строк из {total_files} файлов", 'success')
            messagebox.showinfo("Готов", "Поиск завершен")
        else:
            self.log_message("Нет строк для сохранения", 'warning')
            self.update_status("Нет строк", 'error')
    
    def apply_translation_to_files(self, original_strings, translation_strings):
        """Применить перевод к файлам"""
        
        # Проверяем соответствие количества строк в обоих файлах
        if len(original_strings) != len(translation_strings):
            self.update_status("Количество строк не совпадает!", 'error')
            self.log_message(f"Количество строк не совпадает! {len(original_strings)} != {len(translation_strings)}", 'error')
            
            messagebox.showerror(
                "Ошибка соответствия", 
                f"Количество строк не совпадает!\n\n"
                f"Оригинал: {len(original_strings)} строк\n"
                f"Перевод: {len(translation_strings)} строк\n\n"
            )
            return 0
        
        # Получаем выбранный режим сохранения
        display_value = self.save_mode.get()
        save_mode = self.save_mode_map.get(display_value, 'single_file')
        output_path = self.output_file.get()
        
        # Создаем словарь замен для ускорения
        replacements = {}
        for orig_str, trans_str in zip(original_strings, translation_strings):
            if orig_str != trans_str:
                replacements[orig_str] = trans_str
        
        total_replaced = 0
        total_files = len(self.input_files)
        overall_start_time = time.time()
        
        for file_idx, input_file in enumerate(self.input_files, 1):
            # ПРОВЕРКА ОТМЕНЫ НА КАЖДОМ ФАЙЛЕ
            if self.cancel_requested:
                self.log_message(f"Операция отменена пользователем на файле {file_idx}/{total_files}", 'warning')
                break
            
            file_start_time = time.time()
            filename = os.path.basename(input_file)
            
            # Логирование начала обработки файла
            if self.show_all_logs.get():
                self.log_message(f"📝 Обработка файла {file_idx}/{total_files}: {filename}")
            else:
                if file_idx == 1:
                    self.log_message(f"Применение перевода к {total_files} файлам...", 'success')
            
            try:
                # Чтение файла
                file_encoding = self.file_processor.detect_encoding(
                    input_file,
                    self.auto_detect_encoding.get(),
                    self.encoding.get()
                )
                
                with open(input_file, 'r', encoding=file_encoding) as f:
                    content = f.read()
                
                # Замена строк
                result = content
                replaced = 0
                file_replacements_details = []
                
                # Производим все замены в файле
                for orig_str, trans_str in replacements.items():
                    count = result.count(orig_str)
                    if count > 0:
                        result = result.replace(orig_str, trans_str)
                        replaced += count
                        
                        # Детальная информация о заменах если включены все логи
                        if self.show_all_logs.get():
                            # Добавляем детали замены
                            file_replacements_details.append({
                                'original': orig_str,
                                'translated': trans_str,
                                'count': count
                            })
                
                # Детальное логирование замен
                if self.show_all_logs.get() and replaced > 0:
                    self.log_message(f"📊 Файл {filename}: найдено {replaced} замен в {len(file_replacements_details)} строках")
                    
                    # Выводим детали замен
                    for idx, replacement in enumerate(file_replacements_details, 1):
                        orig = replacement['original']
                        trans = replacement['translated']
                        count = replacement['count']
                        orig_display = orig[:40] + "..." if len(orig) > 40 else orig
                        trans_display = trans[:40] + "..." if len(trans) > 40 else trans
                        self.log_message(f"{idx}. {orig_display} -> {trans_display} (замен: {count})")
                    
                total_replaced += replaced
                
                # Определение имени выходного файла в зависимости от режима
                if save_mode == 'single_file':
                    # Все в один файл
                    if file_idx == 1:
                        output_file = output_path
                        # Сохраняем первый файл
                        with open(output_file, 'w', encoding=file_encoding) as f:
                            f.write(result)
                    else:
                        # Для остальных файлов добавляем к существующему
                        with open(output_file, 'a', encoding=file_encoding) as f:
                            f.write(f"\n\n\n{'#'*80}\n\n")
                            f.write(f"Файл: {os.path.basename(input_file)}\n")
                            f.write('='*80 + '\n\n')
                            f.write(result)
                
                elif save_mode == 'folder_with_names':
                    # В папку с сохранением имен файлов
                    if not os.path.exists(output_path):
                        os.makedirs(output_path)
                    
                    output_filename = os.path.basename(input_file)
                    output_file = os.path.join(output_path, output_filename)
                    
                    with open(output_file, 'w', encoding=file_encoding) as f:
                        f.write(result)
                
                elif save_mode == 'folder_with_structure':
                    # В папку с сохранением структуры
                    if not os.path.exists(output_path):
                        os.makedirs(output_path)
                    
                    # Сохраняем относительный путь от первого входного файла
                    if file_idx == 1:
                        # Определяем базовую директорию (директорию первого файла)
                        first_file_dir = os.path.dirname(input_file)
                        relative_path = os.path.relpath(input_file, first_file_dir)
                    else:
                        relative_path = os.path.relpath(input_file, os.path.commonpath(self.input_files))
                    
                    output_file = os.path.join(output_path, relative_path)
                    
                    # Создаем директории если нужно
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    
                    with open(output_file, 'w', encoding=file_encoding) as f:
                        f.write(result)
                
                if self.show_debug_logs.get():
                    debug_info = DebugInfo.format_operation_info(f"Файл {filename}: {replaced} замен", file_start_time)
                    for line in debug_info:
                        self.log_message(f"{line}", 'debug')
                elif self.show_all_logs.get():
                    self.log_message(f"Файл {filename}: {replaced} замен)")
                
            except Exception as e:
                self.log_message(f"Ошибка обработки файла {filename}: {str(e)}", 'error')
                continue
        
        # Общая статистика
        overall_time = time.time() - overall_start_time
        
        if self.cancel_requested:
            processed_files = file_idx - 1 if file_idx > 1 else 0
            self.log_message(f"Операция отменена. Обработано {processed_files} из {total_files} файлов", 'warning')
            self.log_message(f"Общее время работы: {overall_time:.3f} сек", 'info')
            return total_replaced
        
        # Финальное сообщение
        self.log_message(f"Всего заменено: {total_replaced} строк в {total_files} файлах ({overall_time:.3f} сек)", 'success')
        
        return total_replaced
    
    # ==================== МЕТОДЫ РАБОТЫ С ФАЙЛАМИ ====================
    
    def save_strings_file(self, filename, strings, label):
        """Сохранить строки в файл"""
        try:
            encoding = self.encoding.get() if not self.auto_detect_encoding.get() else 'UTF-8'
            
            with open(filename, 'w', encoding=encoding) as f:
                # f.write(f"# Файл {label}\n# Формат: номер: \\\"{self.search_pattern_before.get()}строка{self.search_pattern_after.get()}\\\"\n{'#'*50}\n\n")
                for idx, quoted_string in enumerate(strings, 1):
                    escaped = quoted_string.replace('\\', '\\\\').replace('"', '\\"')
                    f.write(f'{idx}: "{escaped}"\n')
            
            self.log_message(f"Сохранен: {filename}", 'success')
            
            if self.show_debug_logs.get():
                file_size = os.path.getsize(filename) if os.path.exists(filename) else 0
                self.log_message(f"Файл {label}: {len(strings)} строк, {file_size} байт", 'debug')
                
        except Exception as e:
            self.log_message(f"Ошибка сохранения: {str(e)}", 'error')
    
    def read_strings_file(self, filename):
        """Прочитать строки из файла"""
        strings = []
        if not os.path.exists(filename):
            return strings
        
        try:
            encoding = self.file_processor.detect_encoding(
                filename,
                self.auto_detect_encoding.get(),
                self.encoding.get()
            )
            
            with open(filename, 'r', encoding=encoding) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and ':' in line:
                        content = line.split(':', 1)[1].strip()
                        if (content.startswith('"') and content.endswith('"')) or \
                           (content.startswith("'") and content.endswith("'")):
                            content = content[1:-1]
                            
                            # Обработка экранированных символов
                            result = ""
                            i = 0
                            while i < len(content):
                                if content[i] == '\\' and i + 1 < len(content):
                                    next_char = content[i + 1]
                                    if next_char == '\\':
                                        result += '\\'
                                        i += 2
                                    elif next_char == '"':
                                        result += '"'
                                        i += 2
                                    elif next_char == "'":
                                        result += "'"
                                        i += 2
                                    else:
                                        result += content[i]
                                        i += 1
                                else:
                                    result += content[i]
                                    i += 1
                            
                            strings.append(result)
            
            if self.show_debug_logs.get():
                self.log_message(f"Прочитано строк из {filename}: {len(strings)}", 'debug')
                
            return strings
        except Exception as e:
            self.log_message(f"Ошибка чтения: {str(e)}", 'error')
            return []
    
    # ==================== МЕТОДЫ ЛОГИРОВАНИЯ И СТАТУСА ====================
    
    def log_message(self, message, level='info'):
        """Добавить сообщение в лог с поддержкой буферизации"""
        # Фильтрация сообщений
        if level == 'info' and not self.show_all_logs.get():
            return
        
        if level == 'debug' and not self.show_debug_logs.get():
            return
        
        # Подготовка сообщения
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Добавляем символы для уровней
        if level == 'error':
            symbol = '❌'
        elif level == 'success':
            symbol = '✅'
        elif level == 'warning':
            symbol = '⚠️'
        elif level == 'debug':
            symbol = '    🍄 debug:'
        else:
            symbol = ''
        
        formatted = f"[{timestamp}] {symbol} {message}"
        
        # Если буферизация включена, добавляем в буфер
        if self.buffer_enabled:
            self.message_buffer.append(formatted)
            
            # Если буфер достиг порога, сбрасываем его
            if len(self.message_buffer) >= self.buffer_threshold:
                self.flush_message_buffer()
                
            return
        
        # Вставляем в лог
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, formatted + "\n")
        self.log_text.see(tk.END)
        self.log_lines.append(formatted)
        self.log_text.config(state='disabled')
    
    def enable_message_buffer(self, threshold=None):
        """Включить буферизацию сообщений"""
        if threshold:
            self.buffer_threshold = threshold
        
        self.buffer_enabled = True
        self.message_buffer = []
        self.buffer_flush_count = 0
        
        if self.show_debug_logs.get():
            self.log_message(f"Буферизация сообщений включена (порог: {self.buffer_threshold})", 'debug')

    def disable_message_buffer(self):
        """Выключить буферизацию сообщений и сбросить буфер"""
        if self.buffer_enabled:
            self.flush_message_buffer()
            self.buffer_enabled = False
            
            if self.show_debug_logs.get():
                self.log_message(f"Буферизация сообщений выключена, сбросов буфера: {self.buffer_flush_count}", 'debug')

    def flush_message_buffer(self):
        """Сбросить буфер сообщений в виджет лога"""
        if not self.message_buffer:
            return
        
        # Выводим все сообщения из буфера
        self.log_text.config(state='normal')
        for message in self.message_buffer:
            self.log_text.insert(tk.END, message + "\n")
            self.log_lines.append(message)
        
        # Прокручиваем к концу
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        
        # Сбрасываем статистику
        flushed_count = len(self.message_buffer)
        self.message_buffer = []
        self.buffer_flush_count += 1
        
        if self.show_debug_logs.get():
            self.log_message(f"Сброс буфера сообщений: {flushed_count} сообщений", 'debug')
        
    def update_status(self, message, level=None):
        """Обновить статус"""
        if level == 'error':
            symbol = '❌'
        elif level == 'success':
            symbol = '✅'
        elif level == 'warning':
            symbol = '⚠️'
        elif level == 'working':
            symbol = '🔄'
        else:
            symbol = '🍄'
        
        self.status_var.set(f"{symbol} {message}")
    
    # ==================== МЕТОДЫ КОНФИГУРАЦИИ ====================
    
    def save_config(self):
        """Сохранить конфигурацию"""
        try:
            state = self.get_current_state()
            self.config_manager.save(state)
        
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка сохранения настроек: {str(e)}")
    
    def load_config(self):
        """Загрузить конфигурацию"""
        start_time = time.time()
        try:
            state = self.config_manager.load()
            if state:
                self.apply_state(state)
                self.log_message(f"Настройки загружены из {self.config_manager.config_file}")
                
                if self.show_debug_logs.get():
                    debug_info = DebugInfo.format_operation_info("Загрузка настроек", start_time)
                    for line in debug_info:
                        self.log_message(f"{line}", 'debug')
            else:
                self.toggle_regex_mode()
                self.toggle_encoding_manual()
                self.toggle_line_limit()                
        except Exception as e:
            self.log_message(f"Ошибка загрузки настроек: {str(e)}", 'error')
    
    def get_current_state(self):
        """Получить текущее состояние приложения"""
        blacklist_content = ""
        whitelist_content = ""
        
        if hasattr(self, 'blacklist_text_widget'):
            blacklist_content = self.blacklist_text_widget.get(1.0, tk.END).strip()
        
        if hasattr(self, 'whitelist_text_widget'):
            whitelist_content = self.whitelist_text_widget.get(1.0, tk.END).strip()
        
        language_value = self.selected_language.get()
        if hasattr(self, 'language_selector') and self.language_selector:
            language_value = self.language_selector.get()
        
        save_mode_value = self.save_mode.get()
        if hasattr(self, 'save_mode_selector') and self.save_mode_selector:
            save_mode_value = self.save_mode_selector.get()
        
        encoding_value = self.encoding.get()
        if hasattr(self, 'encoding_selector') and self.encoding_selector:
            encoding_value = self.encoding_selector.get()
        
        return {
            'geometry': self.last_normal_geometry,
            'window_is_zoomed': self.window_is_zoomed,
            'input_files': self.input_files,
            'file_info_cache': self.file_info_cache,
            'total_files_count': self.total_files_count,
            'total_files_size': self.total_files_size,
            'total_files_lines': self.total_files_lines,
            'original_strings_file': self.original_strings_file.get(),
            'translation_file': self.translation_file.get(),
            'output_file': self.output_file.get(),
            'search_pattern_before': self.search_pattern_before.get(),
            'search_pattern_after': self.search_pattern_after.get(),
            'escape_char': self.escape_char.get(),
            'use_custom_regex': self.use_custom_regex.get(),
            'custom_regex': self.custom_regex.get(),
            'single_line_comment': self.single_line_comment.get(),
            'multi_line_comment_start': self.multi_line_comment_start.get(),
            'multi_line_comment_end': self.multi_line_comment_end.get(),
            'ignore_comments': self.ignore_comments.get(),
            'show_all_logs': self.show_all_logs.get(),
            'show_debug_logs': self.show_debug_logs.get(),
            'auto_open_files': self.auto_open_files.get(),
            'dark_mode': self.dark_mode.get(),
            'filter_active': {name: var.get() for name, var in self.filter_active_vars.items()},
            'filter_mode': {name: var.get() for name, var in self.filter_mode_vars.items()},
            'short_strings_length': self.short_strings_length.get(),
            'auto_detect_encoding': self.auto_detect_encoding.get(),
            'line_limit': self.line_limit.get(),
            'enable_line_limit': self.enable_line_limit.get(),
            'apply_lists_to_raw_strings': self.apply_lists_to_raw_strings.get(),
            'blacklist_content': blacklist_content,
            'whitelist_content': whitelist_content,
            'current_theme': self.theme_manager.current_theme,
            'selected_language': language_value,
            'encoding': encoding_value,
            'save_mode': self.save_mode_map.get(save_mode_value, 'single_file'),
        }
    
    def apply_state(self, state):
        """Применить состояние"""
        if 'geometry' in state:
            self.root.geometry(state['geometry'])
            self.last_normal_geometry = state['geometry']

        if state.get('window_is_zoomed', False):
            try:
                self.root.wm_state('zoomed')
                self.window_is_zoomed = True
            except:
                self.window_is_zoomed = False
        else:
            self.window_is_zoomed = False
        
        if 'show_all_logs' in state:
            self.show_all_logs.set(state['show_all_logs'])
            
        if 'show_debug_logs' in state:
            self.show_debug_logs.set(state['show_debug_logs'])
            if self.show_debug_logs:
                self.log_message(f"🍄 Режим отладки включен")
            
        if 'input_files' in state:
            self.input_files = state['input_files']
            # Пробуем загрузить кэшированную информацию
            if ('file_info_cache' in state and 
                'total_files_count' in state and
                'total_files_size' in state and
                'total_files_lines' in state):
                
                self.file_info_cache = state['file_info_cache']
                self.total_files_count = state['total_files_count']
                self.total_files_size = state['total_files_size']
                self.total_files_lines = state['total_files_lines']
                
                if self.show_debug_logs.get():
                    self.log_message(f"Загружен кэш информации о файлах: {self.total_files_count} файлов, {self.total_files_size} байт, {self.total_files_lines} строк", 'debug')
            else:
                # Если кэша нет, пересчитываем
                self.update_all_files_cache()
            
            self.update_file_list()
        
        if 'current_theme' in state:
            self.theme_manager.set_theme(state['current_theme'])
            self.dark_mode.set(self.theme_manager.current_theme == 'dark')
        
        self.apply_state_values(state)
        self.apply_theme()
    
    def apply_state_values(self, state):
        """Применить значения из состояния"""
        var_mapping = {
            'original_strings_file': self.original_strings_file,
            'translation_file': self.translation_file,
            'output_file': self.output_file,
            'search_pattern_before': self.search_pattern_before,
            'search_pattern_after': self.search_pattern_after,
            'escape_char': self.escape_char,
            'custom_regex': self.custom_regex,
            'single_line_comment': self.single_line_comment,
            'multi_line_comment_start': self.multi_line_comment_start,
            'multi_line_comment_end': self.multi_line_comment_end,
            'short_strings_length': self.short_strings_length,
            'encoding': self.encoding,
            'line_limit': self.line_limit,
            'selected_language': self.selected_language,
        }
        
        bool_mapping = {
            'use_custom_regex': self.use_custom_regex,
            'ignore_comments': self.ignore_comments,
            'show_all_logs': self.show_all_logs,
            'show_debug_logs': self.show_debug_logs,
            'auto_open_files': self.auto_open_files,
            'dark_mode': self.dark_mode,
            'auto_detect_encoding': self.auto_detect_encoding,
            'enable_line_limit': self.enable_line_limit,
        }
        
        # Применение значений
        for key, var in var_mapping.items():
            if key in state:
                var.set(state[key])
        
        for key, var in bool_mapping.items():
            if key in state:
                var.set(state[key])
        
        if 'show_all_logs' in state:
            self.show_all_logs.set(state['show_all_logs'])
            mode = "подробный" if state['show_all_logs'] else "краткий"
            self.log_message(f"Режим логирования: {mode}", 'success')
        
        # Применение фильтров
        if 'filter_active' in state:
            for name, value in state['filter_active'].items():
                if name in self.filter_active_vars:
                    self.filter_active_vars[name].set(value)
        
        if 'filter_mode' in state:
            for name, value in state['filter_mode'].items():
                if name in self.filter_mode_vars:
                    self.filter_mode_vars[name].set(value)
        
        # Применение списков
        if 'apply_lists_to_raw_strings' in state:
            self.apply_lists_to_raw_strings.set(state['apply_lists_to_raw_strings'])
        
        if 'blacklist_content' in state and hasattr(self, 'blacklist_text_widget'):
            self.blacklist_text_widget.delete(1.0, tk.END)
            self.blacklist_text_widget.insert(1.0, state['blacklist_content'])
        
        if 'whitelist_content' in state and hasattr(self, 'whitelist_text_widget'):
            self.whitelist_text_widget.delete(1.0, tk.END)
            self.whitelist_text_widget.insert(1.0, state['whitelist_content'])
        
        if 'selected_language' in state and hasattr(self, 'language_selector'):
            self.language_selector.set(state['selected_language'])
        
        if 'encoding' in state and hasattr(self, 'encoding_selector'):
            self.encoding_selector.set(state['encoding'])
        
        if 'save_mode' in state:
            # Конвертируем внутреннее значение в отображаемое
            internal_value = state['save_mode']
            display_value = self.save_mode_reverse_map.get(internal_value, 
                                                          'Один файл (с разделителем)')
            self.save_mode.set(display_value)
            if hasattr(self, 'save_mode_selector'):
                self.save_mode_selector.set(display_value)
            # Принудительно вызываем обработчик изменения режима
            self.on_save_mode_changed()
        
        # Обновление UI элементов
        self.toggle_regex_mode()
        self.toggle_encoding_manual()
        self.toggle_line_limit()
    
    def save_profile(self):
        """Сохранить профиль в файл"""
        start_time = time.time()
        filename = filedialog.asksaveasfilename(
            title="Сохранить профиль",
            defaultextension=".json",
            filetypes=[("JSON файлы", "*.json"), ("Все файлы", "*.*")]
        )
        if filename:
            try:
                state = self.get_current_state()
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(state, f, ensure_ascii=False, indent=2)
                self.log_message(f"Профиль сохранен в {filename}", 'success')
                
                if self.show_debug_logs.get():
                    debug_info = DebugInfo.format_operation_info("Сохранение профиля", start_time)
                    for line in debug_info:
                        self.log_message(f"{line}", 'debug')
                        
            except Exception as e:
                self.log_message(f"Ошибка сохранения профиля: {str(e)}", 'error')
    
    def load_profile(self):
        """Загрузить профиль из файла"""
        start_time = time.time()
        filename = filedialog.askopenfilename(
            title="Загрузить профиль",
            filetypes=[("JSON файлы", "*.json"), ("Все файлы", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                self.apply_state(state)
                self.log_message(f"Профиль загружен из {filename}", 'success')
                
                if self.show_debug_logs.get():
                    debug_info = DebugInfo.format_operation_info("Загрузка профиля", start_time)
                    for line in debug_info:
                        self.log_message(f"{line}", 'debug')
                        
            except Exception as e:
                self.log_message(f"Ошибка загрузки профиля: {str(e)}", 'error')
    
    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ИНТЕРФЕЙСА ====================
    
    def toggle_cancel_button(self, show=False):
        """Показать/скрыть кнопку отмены"""
        if show and not self.is_processing:
            # Показываем кнопку отмены
            self.cancel_button.pack(side=tk.RIGHT, padx=(0, 10))
            self.cancel_button.config(state='normal', text="⏹ Отмена")
            self.is_processing = True
            self.cancel_requested = False
            
        elif not show and self.cancel_button:
            # Скрываем кнопку отмены
            self.cancel_button.pack_forget()
            self.is_processing = False
            self.cancel_requested = False
    
    def cancel_operation(self):
        """Отменить текущую операцию"""
        if self.is_processing and not self.cancel_requested:
            self.cancel_requested = True
            self.cancel_button.config(state='disabled', text="⏹ Отмена...")
            self.log_message("Запрошена отмена операции...", 'warning')
            self.update_status("Отмена...", 'warning')
        
    def toggle_logs_tab(self):
        """Переключиться на вкладку логов или обратно"""
        # Находим индекс вкладки логов
        logs_tab_index = self.notebook.get_tab_index(self.tabs['logs'])
        
        if logs_tab_index is None:
            return  # Вкладка логов не найдена
        
        # Получаем индекс текущей вкладки
        current_index = self.notebook.current_tab
        
        # Если сейчас открыта вкладка логов, переключаемся на последнюю активную
        if current_index == logs_tab_index:
            if hasattr(self, 'last_active_tab_index') and self.last_active_tab_index is not None:
                self.notebook.select(self.last_active_tab_index)
        else:
            # Сохраняем текущую вкладку и переключаемся на логи
            self.last_active_tab_index = current_index
            self.notebook.select(logs_tab_index)
    
    def clear_logs(self):
        """Очистить логи"""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_lines = []
        self.log_text.config(state='disabled')
        self.log_message("Логи очищены")
    
    def copy_logs(self):
        """Скопировать логи в буфер обмена"""
        logs = self.log_text.get(1.0, tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(logs)
        self.log_message("Логи скопированы в буфер обмена")
    
    def save_logs_to_file(self):
        """Сохранить логи в файл"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Текстовые файлы", "*.txt")]
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.log_text.get(1.0, tk.END))
            self.log_message(f"Логи сохранены: {filename}", 'success')

    def open_file(self, filename):
        """Открыть файл в ассоциированной программе"""
        if filename and os.path.exists(filename):
            try:
                if os.name == 'nt':
                    os.startfile(filename)
                elif os.name == 'posix':
                    subprocess.run(['xdg-open', filename])
            except Exception as e:
                self.log_message(f"Ошибка открытия: {str(e)}", 'error')
    
    def open_input_files(self):
        """Открыть выбранные входные файлы"""
        if not self.input_files:
            return
        
        # Проверяем выделение в Listbox
        selection = self.file_listbox.curselection()
        
        if selection:
            response = True
            # Если файлов 5 и более - спрашиваем
            if len(selection) > 4:
                response = messagebox.askyesno(
                    "Открытие файлов",
                    f"В списке выбрано {len(selection)} файлов. Хотите открыть все?"
                )
                
            if response:
                # Открываем ВЫДЕЛЕННЫЕ файлы
                opened_count = 0
                
                for idx, index in enumerate(selection, 1):
                    if 0 <= index < len(self.input_files):
                        selected_file = self.input_files[index]
                        if os.path.exists(selected_file):
                            self.open_file(selected_file)
                            opened_count += 1
                        else:
                            self.log_message(f"Файл не найден: {os.path.basename(selected_file)}", 'error')
                
                self.log_message(f"Открыто файлов: {opened_count} из {len(selection)}")
                self.update_status(f"Открыто файлов: {opened_count}", 'success')
            else:
                self.log_message("Открытие файлов отменено пользователем")
            
        elif len(self.input_files) == 1:
            # Если файл всего один, открываем его
            single_file = self.input_files[0]
            if os.path.exists(single_file):
                self.open_file(single_file)
                self.log_message(f"Открыт файл: {os.path.basename(single_file)}")
                self.update_status("Файл открыт", 'success')
            else:
                self.log_message(f"Файл не найден: {os.path.basename(single_file)}", 'error')
                self.update_status("Файл не найден", 'error')
        
        else:
            # Если файлов несколько и ни один не выделен - спрашиваем
            response = messagebox.askyesno(
                "Открытие файлов",
                f"В списке {len(self.input_files)} файлов. Хотите открыть все?\n\n"
                f"Чтобы открыть конкретные файлы, выделите их в списке (Ctrl+клик или Shift+клик) и нажмите кнопку снова."
            )
            
            if response:
                # Открываем все файлы
                opened_count = 0
                
                self.update_status(f"Открытие {len(self.input_files)} файлов...", 'working')
                self.root.update()
                
                for idx, file in enumerate(self.input_files, 1):
                    if os.path.exists(file):
                        self.open_file(file)
                        opened_count += 1
                    else:
                        self.log_message(f"Файл не найден: {os.path.basename(file)}", 'error')
                    
                self.log_message(f"Открыто файлов: {opened_count} из {len(self.input_files)}")
                self.update_status(f"Открыто файлов: {opened_count}", 'success')
            else:
                self.log_message("Открытие файлов отменено пользователем")
    
    def open_output_file(self):
        """Открыть выходной файл или папку"""
        output_path = self.output_file.get()
        if not output_path:
            return
        
        if os.path.exists(output_path):
            if os.path.isfile(output_path):
                # Это файл - открываем его
                self.open_file(output_path)
            elif os.path.isdir(output_path):
                # Это папка - открываем проводник
                try:
                    if os.name == 'nt':
                        os.startfile(output_path)
                    elif os.name == 'posix':
                        subprocess.run(['xdg-open', output_path])
                except Exception as e:
                    self.log_message(f"Ошибка открытия папки: {str(e)}", 'error')
    
    def on_closing(self):
        """Обработка закрытия окна"""
        try:
            if self.root.wm_state() != 'zoomed':
                self.last_normal_geometry = self.root.geometry()
        except:
            pass
        
        self.save_config()
        self.root.destroy()
    
    # ==================== МЕТОДЫ ТЕСТИРОВАНИЯ ====================
    
    def test_search_pattern_embedded(self):
        """Тестирование поиска строк"""
        start_time = time.time()
        test_text = self.search_test_input.get(1.0, tk.END)
        pattern = self.get_search_pattern()
        
        if not pattern:
            return
        
        try:
            found = re.findall(pattern, test_text, re.DOTALL)
            
            self.search_test_output.config(state='normal')
            self.search_test_output.delete(1.0, tk.END)
            
            self.search_test_output.insert(tk.END, f"Шаблон: {pattern}\n")
            self.search_test_output.insert(tk.END, f"Найдено строк: {len(found)}\n\n")
            
            for i, s in enumerate(found, 1):
                content = self.file_processor.extract_string_content(
                    s,
                    self.use_custom_regex.get(),
                    self.search_pattern_before.get(),
                    self.search_pattern_after.get()
                )
                escaped = content.replace('\n', '\\n').replace('\t', '\\t').replace('\r', '\\r')
                
                display_content = escaped[:40] + "..." if len(escaped) > 40 else escaped
                display_original = s[:40] + "..." if len(s) > 40 else s
                
                self.search_test_output.insert(tk.END, f"{i}. {display_original}\n")
                
                if content != s:
                    self.search_test_output.insert(tk.END, f"   Извлечено: '{display_content}'\n")
            
            self.search_test_output.config(state='disabled')
            
            if self.show_debug_logs.get():
                test_time = time.time() - start_time
                debug_info = DebugInfo.format_operation_info("Тестирование поиска", start_time)
                for line in debug_info:
                    self.log_message(f"{line}", 'debug')
            
        except re.error as e:
            self.search_test_output.config(state='normal')
            self.search_test_output.delete(1.0, tk.END)
            self.search_test_output.insert(tk.END, f"Ошибка в шаблоне: {str(e)}")
            self.search_test_output.config(state='disabled')
    
    def test_comments_processing(self):
        """Тестирование обработки комментариев"""
        start_time = time.time()
        test_text = self.comment_test_input.get(1.0, tk.END)
        processed = self.file_processor.preprocess_content_for_comments(
            test_text, self.single_line_comment.get(),
            self.multi_line_comment_start.get(), self.multi_line_comment_end.get())
        
        self.comment_test_output.config(state='normal')
        self.comment_test_output.delete(1.0, tk.END)
        self.comment_test_output.insert(tk.END, processed)
        self.comment_test_output.config(state='disabled')
        
        if self.show_debug_logs.get():
            test_time = time.time() - start_time
            debug_info = DebugInfo.format_operation_info("Тестирование комментариев", start_time)
            for line in debug_info:
                self.log_message(f"{line}", 'debug')
    
    # ==================== МЕТОДЫ УПРАВЛЕНИЯ ФИЛЬТРАМИ ====================
    
    def on_encoding_selected(self, event=None):
        """Обработка выбора кодировки"""
        encoding = self.encoding_selector.get()
        self.encoding.set(encoding)
        self.log_message(f"Ручной выбор кодировки {encoding}")
    
    def on_save_mode_changed(self, event=None):
        """Обработка изменения режима сохранения"""
        # Получаем выбранный режим из селектора
        if hasattr(self, 'save_mode_selector'):
            display_value = self.save_mode_selector.get()
        else:
            display_value = self.save_mode.get()
        
        # Конвертируем отображаемое значение во внутреннее
        internal_value = self.save_mode_map.get(display_value, 'single_file')
        
        # Обновляем текст заголовка в зависимости от режима
        if internal_value == 'single_file':
            # Режим одного файла
            if hasattr(self, 'output_label'):
                self.output_label.config(text="Выходной файл:")
            
            # Устанавливаем значение по умолчанию для файла, если поле пустое или содержит путь к папке
            current_value = self.output_file.get()
            if not current_value or current_value.endswith(os.sep):
                self.output_file.set('_localized_output.txt')
            elif os.path.isdir(current_value):
                # Если указана существующая папка, меняем на файл
                self.output_file.set(os.path.join(current_value, '_localized_output.txt'))
            
            # Обновляем текст кнопки "Обзор"
            if hasattr(self, 'browse_output_btn'):
                self.browse_output_btn.config(text="Обзор")
        else:
            # Режимы папки
            if hasattr(self, 'output_label'):
                self.output_label.config(text="Выходная папка:")
            
            # Устанавливаем значение по умолчанию для папки
            current_value = self.output_file.get()
            
            if not current_value:
                self.output_file.set('_localized')
            elif current_value.endswith('.txt'):
                # Если это путь к файлу .txt, меняем расширение
                base_name = os.path.splitext(current_value)[0]
                self.output_file.set(base_name)
            elif not current_value.endswith(os.sep) and '.' in os.path.basename(current_value):
                # Если это похоже на файл (с расширением), меняем на папку
                base_name = os.path.splitext(current_value)[0]
                self.output_file.set(base_name)
            elif not current_value.endswith(os.sep):
                # Если нет слеша в конце, добавляем его
                self.output_file.set(current_value + os.sep)
            
            # Обновляем текст кнопки "Обзор"
            if hasattr(self, 'browse_output_btn'):
                self.browse_output_btn.config(text="Выбрать папку")
    
    def on_filter_mode_changed(self, filter_name, mode):
        """Обработка изменения режима фильтра"""
        if self.filter_active_vars[filter_name].get():
            self.log_message(f"Фильтр '{filter_name}' переключен в режим: {mode}")
    
    def on_filter_active_changed(self, filter_name):
        """Обработка активации/деактивации фильтра"""
        if self.filter_active_vars[filter_name].get():
            mode = self.filter_mode_vars[filter_name].get()
            self.log_message(f"Фильтр '{filter_name}' активирован в режиме: {mode}")
        else:
            self.log_message(f"Фильтр '{filter_name}' деактивирован")
    
    def activate_all_exclude(self):
        """Активировать все фильтры в режиме исключения"""
        for filter_name in self.filter_active_vars.keys():
            self.filter_active_vars[filter_name].set(True)
            self.filter_mode_vars[filter_name].set("exclude")
        self.log_message("Все фильтры активированы в режиме 'Исключить'")
    
    def activate_all_include(self):
        """Активировать все фильтры в режиме включения"""
        for filter_name in self.filter_active_vars.keys():
            self.filter_active_vars[filter_name].set(True)
            self.filter_mode_vars[filter_name].set("include")
        self.log_message("Все фильтры активированы в режиме 'Включить'")
    
    def deactivate_all_exclude(self):
        """Деактивировать все фильтры в режиме исключения"""
        for filter_name in self.filter_active_vars.keys():
            if self.filter_mode_vars[filter_name].get() == "exclude":
                self.filter_active_vars[filter_name].set(False)
        self.log_message("Все фильтры 'Исключить' деактивированы")
    
    def deactivate_all_include(self):
        """Деактивировать все фильтры в режиме включения"""
        for filter_name in self.filter_active_vars.keys():
            if self.filter_mode_vars[filter_name].get() == "include":
                self.filter_active_vars[filter_name].set(False)
        self.log_message("Все фильтры 'Включить' деактивированы")
    
    def deactivate_all_filters(self):
        """Деактивировать все фильтры"""
        for var in self.filter_active_vars.values():
            var.set(False)
        self.log_message("Все фильтры деактивированы")
    
    def reset_filters(self):
        """Сбросить фильтры к значениям по умолчанию"""
        for name, default_value in self.config_manager.DEFAULT_FILTERS.items():
            self.filter_active_vars[name].set(default_value)
            self.filter_mode_vars[name].set("exclude")
        
        self.short_strings_length.set("2")
        self.log_message("Фильтры сброшены к значениям по умолчанию")
    
    # ==================== МЕТОДЫ СБРОСА НАСТРОЕК ====================
    
    def reset_all(self):
        """Сбросить все настройки"""
        start_time = time.time()
        self.clear_logs()
        self.clear_file_list()
        
        # Сброс к значениям по умолчанию
        for key, value in self.config_manager.DEFAULT_VALUES.items():
            if hasattr(self, key):
                var = getattr(self, key)
                if isinstance(var, tk.StringVar):
                    var.set(value)
        
        # Сброс режима сохранения к значению по умолчанию
        default_display = 'Один файл (с разделителем)'
        self.save_mode.set(default_display)
        if hasattr(self, 'save_mode_selector'):
            self.save_mode_selector.set(default_display)
        self.on_save_mode_changed()
        
        self.reset_comments_settings()
        self.reset_search_settings()
        self.clear_list_or_text('test')
        self.clear_list_or_text('black')
        self.clear_list_or_text('white')
        self.reset_filters()
        self.dark_mode.set(False)
        self.apply_theme()
        
        if self.show_debug_logs.get():
            debug_info = DebugInfo.format_operation_info("Сброс настроек", start_time)
            for line in debug_info:
                self.log_message(f"{line}", 'debug')
        
        self.log_message("Все настройки приложения сброшены", 'success')
    
    def reset_search_settings(self):
        """Сбросить настройки поиска"""
        self.search_pattern_before.set(self.config_manager.DEFAULT_VALUES['search_pattern_before'])
        self.search_pattern_after.set(self.config_manager.DEFAULT_VALUES['search_pattern_after'])
        self.escape_char.set(self.config_manager.DEFAULT_VALUES['escape_char'])
        self.use_custom_regex.set(False)
        self.custom_regex.set(self.config_manager.DEFAULT_VALUES['search_regex'])
        self.toggle_regex_mode()
        self.log_message("Настройки поиска сброшены")
    
    def reset_comments_settings(self):
        """Сбросить настройки комментариев"""
        self.single_line_comment.set(self.config_manager.DEFAULT_VALUES['single_line_comment'])
        self.multi_line_comment_start.set(self.config_manager.DEFAULT_VALUES['multi_line_comment_start'])
        self.multi_line_comment_end.set(self.config_manager.DEFAULT_VALUES['multi_line_comment_end'])
        self.ignore_comments.set(False)
        
        self.selected_language.set('C++')
        if hasattr(self, 'language_selector'):
            self.language_selector.set('C++')
        
        self.log_message("Настройки комментариев сброшены")
    
    def clear_list_or_text(self, content_type):
        """Очистить список или текст"""
        if content_type not in ('test', 'black', 'white'):
            return
        
        try:
            # Конфигурация для разных типов контента
            config = {
                'test': {
                    'widget_name': 'search_test_input',
                    'message': 'Поле тестового текста очищено',
                    'clear_filter': False
                },
                'black': {
                    'widget_name': 'blacklist_text_widget',
                    'message': 'Черный список очищен',
                    'clear_filter': True,
                    'filter_attr': 'blacklist'
                },
                'white': {
                    'widget_name': 'whitelist_text_widget',
                    'message': 'Белый список очищен',
                    'clear_filter': True,
                    'filter_attr': 'whitelist'
                }
            }
            
            cfg = config[content_type]
            
            # Очищаем текстовый виджет, если он существует
            widget_name = cfg['widget_name']
            if hasattr(self, widget_name):
                widget = getattr(self, widget_name)
                if widget:
                    widget.delete(1.0, tk.END)
            
            # Очищаем соответствующий фильтр, если существует filter_manager
            if cfg.get('clear_filter'):
                if hasattr(self, 'filter_manager') and self.filter_manager:
                    filter_attr = cfg['filter_attr']
                    setattr(self.filter_manager, filter_attr, [])
            
            self.log_message(cfg['message'])
            
        except Exception as e:
            error_message = f"Ошибка при очистке {content_type}: {str(e)}"
            self.log_message(error_message, 'error')
    
    # ==================== МЕТОДЫ УПРАВЛЕНИЯ UI ====================
    
    def toggle_regex_mode(self):
        """Переключение режима регулярных выражений"""
        state = 'normal' if self.use_custom_regex.get() else 'disabled'
        self.regex_entry.config(state=state)
    
    def toggle_encoding_manual(self):
        """Переключение ручного выбора кодировки"""
        is_enabled = not self.auto_detect_encoding.get()
        encoding_name = ''
        if hasattr(self, 'encoding_selector'):
            # Обновляем состояние всех кнопок в селекторе
            for value, btn in self.encoding_selector.buttons:
                if is_enabled:
                    # Включаем
                    btn.config(cursor='hand2', state='normal')
                    # Перепривязываем событие клика
                    btn.unbind('<Button-1>')
                    btn.bind('<Button-1>', lambda e, v=value: self.encoding_selector.select_option(v))
                else:
                    # Выключаем
                    btn.config(cursor='arrow', state='disabled')
                    btn.unbind('<Button-1>')
        
        if is_enabled:
            self.on_encoding_selected()
        else:
            self.log_message("Автоопределение кодировки")
    
    def toggle_line_limit(self):
        """Переключение лимита строк"""
        state = 'normal' if self.enable_line_limit.get() else 'disabled'
        self.limit_entry.config(state=state)
    
    def on_language_selected(self, event=None):
        """Обработка выбора языка"""
        language = self.language_selector.get()
        self.selected_language.set(language)
        self.apply_language_template()
    
    def apply_language_template(self):
        """Применить шаблон комментариев для выбранного языка"""
        language = self.language_selector.get() if hasattr(self, 'language_selector') else self.selected_language.get()
        if language in self.config_manager.COMMENT_TEMPLATES:
            template = self.config_manager.COMMENT_TEMPLATES[language]
            self.single_line_comment.set(template['single'])
            self.multi_line_comment_start.set(template['multi_start'])
            self.multi_line_comment_end.set(template['multi_end'])
            self.log_message(f"Применен шаблон комментариев для {language}")
    
    # ==================== МЕТОДЫ РАБОТЫ С ФАЙЛАМИ (UI) ====================
    
    def save_list_or_text(self, content_type):
        """Сохранить список или тестовый текст в файл"""
        if content_type not in ('black', 'white', 'test'):
            return
        
        # Конфигурация для разных типов контента
        config = {
            'black': {
                'title': 'Сохранить список исключений',
                'description': 'исключений',
                'widget': self.blacklist_text_widget,
                'get_content': lambda: self.blacklist_text_widget.get(1.0, tk.END).strip()
            },
            'white': {
                'title': 'Сохранить список включений',
                'description': 'включений',
                'widget': self.whitelist_text_widget,
                'get_content': lambda: self.whitelist_text_widget.get(1.0, tk.END).strip()
            },
            'test': {
                'title': 'Сохранить тестовый текст',
                'description': 'тестовый текст',
                'widget': self.search_test_input,
                'get_content': lambda: self.search_test_input.get(1.0, tk.END).strip(),
            }
        }
        
        cfg = config[content_type]
        content = cfg['get_content']()
        if not content:
            messagebox.showwarning("Внимание", "Поле для текста пустое")
            return
        
        filename = filedialog.asksaveasfilename(
            title=cfg['title'],
            defaultextension=".txt",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            # Получаем содержимое
            content = cfg['get_content']()
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            file_basename = os.path.basename(filename)
            self.log_message(f"Список {cfg['description']} сохранен: {file_basename}", 'success')
        
        except Exception as e:
            self.log_message(f"Ошибка сохранения списка {cfg['description']}: {str(e)}", 'error')
    
    def load_list_or_text(self, content_type):
        """Загрузить список или тестовый текст из файла"""
        if content_type not in ('black', 'white', 'test'):
            return
        
        # Конфигурация для разных типов контента
        config = {
            'black': {
                'title': 'Выберите файл со списком исключений',
                'description': 'исключений',
                'widget': self.blacklist_text_widget
            },
            'white': {
                'title': 'Выберите файл со списком включений',
                'description': 'включений',
                'widget': self.whitelist_text_widget
            },
            'test': {
                'title': 'Загрузить тестовый текст',
                'description': 'тестовый текст',
                'widget': self.search_test_input,
            }
        }
        
        cfg = config[content_type]
        
        filename = filedialog.askopenfilename(
            title=cfg['title'],
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            if hasattr(self, 'auto_detect_encoding') and hasattr(self, 'encoding'):
                encoding = self.file_processor.detect_encoding(
                    filename,
                    self.auto_detect_encoding.get(),
                    self.encoding.get()
                )
            else:
                encoding = 'utf-8'
            
            with open(filename, 'r', encoding=encoding) as f:
                content = f.read()
            
            # Очищаем и вставляем текст в соответствующий виджет
            cfg['widget'].delete(1.0, tk.END)
            cfg['widget'].insert(1.0, content.strip())
            
            file_basename = os.path.basename(filename)
            self.log_message(f"Список {cfg['description']} загружен: {file_basename}", 'success')
        
        except Exception as e:
            self.log_message(f"Ошибка загрузки списка {cfg['description']}: {str(e)}", 'error')
    
    def browse_original_strings_file(self):
        """Выбрать файл для сохранения оригинальных строк"""
        filename = filedialog.asksaveasfilename(title="Сохранить оригинальные строки", defaultextension=".txt")
        if filename:
            self.original_strings_file.set(filename)
    
    def browse_translation_file(self):
        """Выбрать файл перевода"""
        filename = filedialog.askopenfilename(title="Выберите файл перевода")
        if filename:
            self.translation_file.set(filename)
    
    def browse_output(self):
        """Выбрать выходной файл или папку в зависимости от режима"""
        # Получаем текущий режим
        if hasattr(self, 'save_mode_selector'):
            display_value = self.save_mode_selector.get()
        else:
            display_value = self.save_mode.get()
        
        internal_value = self.save_mode_map.get(display_value, 'single_file')
        
        if internal_value == 'single_file':
            # Режим одного файла
            current_value = self.output_file.get()
            
            # Определяем начальный путь и имя файла
            if current_value and os.path.isabs(current_value):
                initialdir = os.path.dirname(current_value)
                initialfile = os.path.basename(current_value)
            else:
                initialdir = os.getcwd()
                initialfile = current_value if current_value else '_localized_output.txt'
            
            filename = filedialog.asksaveasfilename(
                title="Сохранить результат",
                defaultextension=".txt",
                initialfile=initialfile,
                initialdir=initialdir,
                filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
            )
            if filename:
                self.output_file.set(filename)
        else:
            # Режимы папки
            current_value = self.output_file.get()
            
            # Определяем начальную папку
            if current_value and os.path.exists(current_value):
                initialdir = current_value
            elif current_value and os.path.exists(os.path.dirname(current_value)):
                initialdir = os.path.dirname(current_value)
            else:
                initialdir = os.getcwd()
            
            foldername = filedialog.askdirectory(
                title="Выберите папку для сохранения",
                initialdir=initialdir
            )
            if foldername:
                self.output_file.set(foldername)
    
    def setup_mousewheel(self):
        """Упрощенная прокрутка - только Canvas на активной вкладке"""
        def on_mousewheel_simple(event):
            """Обработчик колеса мыши"""
            try:
                current_tab_id = self.notebook.current_tab
                if current_tab_id is None:
                    return
                
                tab_content = self.notebook.tabs[current_tab_id]['content']
                
                canvases = []
                for child in tab_content.winfo_children():
                    if isinstance(child, tk.Canvas):
                        canvases.append(child)
                
                if not canvases:
                    return
                
                if event.delta:
                    delta = -int(event.delta / 120)
                else:
                    delta = -1 if event.num == 5 else 1
                
                canvases[0].yview_scroll(delta, "units")
                return "break"
                
            except Exception as e:
                if self.show_debug_logs.get():
                    self.log_message(f"Ошибка прокрутки: {str(e)}", 'debug')
        
        self.root.bind_all("<MouseWheel>", on_mousewheel_simple)
        self.root.bind_all("<Button-4>", on_mousewheel_simple)
        self.root.bind_all("<Button-5>", on_mousewheel_simple)
    

def main():
    """Главная функция приложения"""
    root = tk.Tk()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(script_dir, 'icon.ico')
    app = DEST(root, icon_path)
    root.mainloop()


if __name__ == "__main__":
    main()