#!/usr/bin/env python3
# -*- coding: utf-8 -*-

MAIN_VERSION = '0.1.1'
MAIN_TITLE = f"Байт-о-скоп v{MAIN_VERSION} by pav13"

import sys
import subprocess
import platform
import math
import json
import struct
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from collections import Counter
import mmap
import gc

if sys.version_info < (3, 6):
    print("Ошибка: требуется Python 3.6 или новее.", file=sys.stderr)
    print(f"Ваша версия: {sys.version}", file=sys.stderr)
    print("\nСкачайте последнюю версию Python с: https://www.python.org/downloads/")
    sys.exit(1)

dependencies = [
    ("PyQt5", "PyQt5"),
    ("numpy", "numpy"),
    ("psutil", "psutil"),
]

missing_deps = []
for dep_name, pip_name in dependencies:
    try:
        __import__(dep_name)
    except ImportError:
        missing_deps.append((dep_name, pip_name))

if missing_deps:
    print("\n" + "=" * 60)
    print("Обнаружены отсутствующие зависимости!")
    print("=" * 60)
    for dep_name, pip_name in missing_deps:
        print(f"[X] {dep_name}")
    print("\nУстановите зависимости командой:")
    print(f"pip install {' '.join(pip_name for _, pip_name in missing_deps)}")
    print("\nИли для Python 3 на Linux/macOS:")
    print(f"pip3 install {' '.join(pip_name for _, pip_name in missing_deps)}")
    try:
        response = input("\nУстановить автоматически? (y/n): ").strip().lower()
        if response in ['y', 'yes', 'д', 'да']:
            system = platform.system().lower()
            cmd = ["pip3" if system in ["linux", "darwin"] else "pip", "install"]
            cmd.extend(pip_name for _, pip_name in missing_deps)
            print(f"\nВыполняю: {' '.join(cmd)}")
            subprocess.check_call(cmd)
            print("\n[V] Зависимости установлены. Перезапуск программы...")
            subprocess.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            print("\nУстановите зависимости вручную и перезапустите программу.")
            sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print("\nУстановка отменена.")
        sys.exit(1)
    except Exception as e:
        print(f"\nОшибка при установке: {e}")
        sys.exit(1)
        
import psutil
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QWidget, QAction,
    QHBoxLayout, QVBoxLayout, QPushButton, QSpinBox, QMenu,
    QComboBox, QLabel, QCheckBox, QScrollArea, QLineEdit, QSlider,
    QDialog, QFormLayout, QDialogButtonBox, QDoubleSpinBox,
    QGroupBox, QGridLayout, QColorDialog, QMessageBox, QFrame
)
from PyQt5.QtGui import (
    QImage, QPainter, QPen, QColor, QWheelEvent, QPalette,
    QKeySequence, QCursor, QFont
)
from PyQt5.QtCore import Qt, QPoint, QSize, QTimer, QEvent, QRect


SCALE_MAX = 32
LEFT_PANEL_WIDTH = 260
RIGHT_PANEL_WIDTH = 260
SMALL_BUTTON_WIDTH = 30
PALETTE_SETTINGS_HEIGHT = 230


class BytesView:
    def __init__(self, data: bytes):
        self._data = data
    def __getitem__(self, key):
        return self._data[key]
    def __len__(self):
        return len(self._data)
    def __bytes__(self):
        return self._data
    def __getslice__(self, i, j):
        return self._data[i:j]
    def __iter__(self):
        return iter(self._data)
    def close(self):
        pass


class ThemeManager:
    """Менеджер тем приложения"""
    
    def __init__(self):
        self.is_dark_theme = True
        self.current_theme = self._create_dark_theme()
        
    def toggle_theme(self):
        """Переключение между темной и светлой темами"""
        self.is_dark_theme = not self.is_dark_theme
        self.current_theme = self._create_dark_theme() if self.is_dark_theme else self._create_light_theme()
        return self.current_theme
    
    def get_current_theme(self):
        """Получение текущей темы"""
        return self.current_theme
    
    def _create_dark_theme(self):
        return {"name": "dark", "colors": {k: QColor(*v) for k, v in {
            "window": (45, 45, 45),
            "window_text": (255, 255, 255),
            "base": (30, 30, 30),
            "alternate_base": (40, 40, 40),
            "text": (255, 255, 255),
            "button": (60, 60, 60),
            "button_text": (255, 255, 255),
            "highlight": (70, 130, 180),
            "highlighted_text": (0, 0, 0),
            "disabled_text": (150, 150, 150),
            "disabled_button_text": (150, 150, 150),
            "disabled_window_text": (150, 150, 150),
            "widget_background": (45, 45, 45),
            "scroll_area_background": (40, 40, 40),
            "panorama_bg": (30, 30, 30),
            "panorama_image": (60, 60, 60),
            "panorama_image_border": (100, 100, 100),
            "panorama_viewport": (255, 255, 255, 180),
            "panorama_viewport_border": (255, 0, 0),
        }.items()}, "styles": self._dark_styles}

    def _create_light_theme(self):
        return {"name": "light", "colors": {k: QColor(*v) for k, v in {
            "window": (240, 240, 240),
            "window_text": (0, 0, 0),
            "base": (255, 255, 255),
            "alternate_base": (245, 245, 245),
            "text": (0, 0, 0),
            "button": (240, 240, 240),
            "button_text": (0, 0, 0),
            "highlight": (70, 130, 180),
            "highlighted_text": (255, 255, 255),
            "disabled_text": (120, 120, 120),
            "disabled_button_text": (120, 120, 120),
            "disabled_window_text": (120, 120, 120),
            "widget_background": (240, 240, 240),
            "scroll_area_background": (245, 245, 245),
            "panorama_bg": (220, 220, 220),
            "panorama_image": (180, 180, 180),
            "panorama_image_border": (150, 150, 150),
            "panorama_viewport": (0, 0, 0, 120),
            "panorama_viewport_border": (0, 0, 255),
        }.items()}, "styles": self._light_styles}

    @property
    def _dark_styles(self):
        return {
            "app": """
    QMenu{background-color:#2a2a2a;border:1px solid #555;border-radius:4px;padding:5px;}
    QMenu::item{color:white;background-color:transparent;padding:6px 20px 6px 10px;margin:2px;border-radius:3px;}
    QMenu::item:selected{background-color:#4682B4;}
    QMenu::item:disabled{color:#777;}
    QMenu::separator{height:1px;background-color:#555;margin:5px 10px;}
    QComboBox{color:white;background-color:#303030;selection-background-color:#4682B4;selection-color:white;border:1px solid #555;border-radius:4px;padding:4px 1px 4px 4px;font-size:8pt;}
    QComboBox:hover{border:1px solid #777;background-color:#353535;}
    QComboBox:focus{border:1px solid #4682B4;}
    QComboBox::drop-down{subcontrol-origin:padding;subcontrol-position:top right;width:30px;border-left:1px solid #555;border-top-right-radius:3px;border-bottom-right-radius:3px;background-color:#404040;}
    QComboBox::drop-down:hover{background-color:#505050;}
    QComboBox::down-arrow{width:0;height:0;border-left:5px solid transparent;border-right:5px solid transparent;border-top:7px solid white;margin-right:5px;}
    QComboBox QAbstractItemView{color:white;background-color:#252525;selection-background-color:#4682B4;selection-color:white;border:1px solid #555;border-radius:4px;padding:3px;outline:none;font-size:8pt;}
    QComboBox QAbstractItemView::item{padding:6px 10px;border-radius:3px;}
    QComboBox QAbstractItemView::item:selected{background-color:#4682B4;}
    QComboBox QAbstractItemView::item:hover{background-color:#353535;}
    QComboBox QAbstractItemView QScrollBar:vertical{background-color:#353535;width:10px;border-radius:5px;}
    QComboBox QAbstractItemView QScrollBar::handle:vertical{background-color:#555;border-radius:5px;}
    QSpinBox,QLineEdit,QTextEdit,QPlainTextEdit{color:white;background-color:#303030;selection-background-color:#4682B4;selection-color:white;border:1px solid #555;border-radius:3px;padding:3px;}
    QSpinBox::up-button,QSpinBox::down-button{background-color:#505050;border:1px solid #666;border-radius:2px;}
    QSpinBox::up-button:hover,QSpinBox::down-button:hover{background-color:#606060;}
    QSpinBox::up-arrow,QSpinBox::down-arrow{width:6px;height:6px;color:white;}
    QToolTip{color:white;background-color:#2a2a2a;border:1px solid #555;padding:5px;border-radius:3px;font-size:9pt;}
    QLabel{color:white;}
    QPushButton{color:white;background-color:#505050;border:1px solid #666;border-radius:3px;padding:5px;}
    QPushButton:hover{background-color:#606060;}
    QPushButton:pressed{background-color:#404040;}
    QCheckBox{color:white;}
    QCheckBox::indicator{width:16px;height:16px;border:1px solid #666;border-radius:3px;background-color:#404040;}
    QCheckBox::indicator:checked{background-color:#4682B4;}
    QGroupBox{color:white;border:1px solid #555;border-radius:5px;margin-top:10px;padding-top:10px;}
    QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 5px 0 5px;}
    QScrollArea{background-color:transparent;border:none;}
    QScrollBar:vertical{background-color:#353535;width:12px;border-radius:6px;}
    QScrollBar::handle:vertical{background-color:#555;border-radius:6px;}
    QScrollBar::handle:vertical:hover{background-color:#666;}
    QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0px;}
    QScrollBar:horizontal{background-color:#353535;height:12px;border-radius:6px;}
    QScrollBar::handle:horizontal{background-color:#555;border-radius:6px;min-width:20px;}
    QScrollBar::handle:horizontal:hover{background-color:#666;}
    """,
            "byte_info": "background:#2a2a2a;border:1px solid #555;padding:9px;font-family:monospace;color:white;",
            "hint": "color:white;font-size:9pt;",
            "info_label": "font-size:8pt;color:white;background-color:transparent;"
        }

    @property
    def _light_styles(self):
        return {
            "app": """
    QMenu{background-color:white;border:1px solid #aaa;border-radius:4px;padding:5px;}
    QMenu::item{color:black;background-color:transparent;padding:6px 20px 6px 10px;margin:2px;border-radius:3px;}
    QMenu::item:selected{background-color:#4682B4;color:white;}
    QMenu::item:disabled{color:#aaa;}
    QMenu::separator{height:1px;background-color:#ccc;margin:5px 10px;}
    QComboBox{color:black;background-color:white;selection-background-color:#4682B4;selection-color:white;border:1px solid #aaa;border-radius:4px;padding:4px 1px 4px 4px;font-size:8pt;}
    QComboBox:hover{border:1px solid #888;background-color:#f8f8f8;}
    QComboBox:focus{border:1px solid #4682B4;}
    QComboBox::drop-down{subcontrol-origin:padding;subcontrol-position:top right;width:30px;border-left:1px solid #aaa;border-top-right-radius:3px;border-bottom-right-radius:3px;background-color:#f0f0f0;}
    QComboBox::drop-down:hover{background-color:#e8e8e8;}
    QComboBox::down-arrow{width:0;height:0;border-left:5px solid transparent;border-right:5px solid transparent;border-top:7px solid #666;margin-right:5px;}
    QComboBox QAbstractItemView{color:black;background-color:white;selection-background-color:#4682B4;selection-color:white;border:1px solid #aaa;border-radius:4px;padding:3px;outline:none;font-size:8pt;}
    QComboBox QAbstractItemView::item{padding:6px 10px;border-radius:3px;}
    QComboBox QAbstractItemView::item:selected{background-color:#4682B4;color:white;}
    QComboBox QAbstractItemView::item:hover{background-color:#f0f0f0;}
    QComboBox QAbstractItemView QScrollBar:vertical{background-color:#f5f5f5;width:10px;border-radius:5px;}
    QComboBox QAbstractItemView QScrollBar::handle:vertical{background-color:#c0c0c0;border-radius:5px;}
    QSpinBox,QLineEdit,QTextEdit,QPlainTextEdit{color:black;background-color:white;selection-background-color:#4682B4;selection-color:white;border:1px solid #aaa;border-radius:3px;padding:3px;}
    QSpinBox::up-button,QSpinBox::down-button{background-color:#e0e0e0;border:1px solid #aaa;border-radius:2px;}
    QSpinBox::up-button:hover,QSpinBox::down-button:hover{background-color:#d0d0d0;}
    QSpinBox::up-arrow,QSpinBox::down-arrow{width:6px;height:6px;color:black;}
    QToolTip{color:black;background-color:#f0f0f0;border:1px solid #aaa;padding:5px;border-radius:3px;font-size:9pt;}
    QLabel{color:black;}
    QPushButton{color:black;background-color:#e0e0e0;border:1px solid #aaa;border-radius:3px;padding:5px;}
    QPushButton:hover{background-color:#d0d0d0;}
    QPushButton:pressed{background-color:#c0c0c0;}
    QCheckBox{color:black;}
    QCheckBox::indicator{width:16px;height:16px;border:1px solid #aaa;border-radius:3px;background-color:white;}
    QCheckBox::indicator:checked{background-color:#4682B4;}
    QGroupBox{color:black;border:1px solid #aaa;border-radius:5px;margin-top:10px;padding-top:10px;}
    QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 5px 0 5px;}
    QScrollArea{background-color:transparent;border:none;}
    QScrollBar:vertical{background-color:#f0f0f0;width:12px;border-radius:6px;}
    QScrollBar::handle:vertical{background-color:#c0c0c0;border-radius:6px;}
    QScrollBar::handle:vertical:hover{background-color:#a0a0a0;}
    QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0px;}
    QScrollBar:horizontal{background-color:#f0f0f0;height:12px;border-radius:6px;}
    QScrollBar::handle:horizontal{background-color:#c0c0c0;border-radius:6px;min-width:20px;}
    QScrollBar::handle:horizontal:hover{background-color:#a0a0a0;}
    """,
            "byte_info": "background:#f0f0f0;border:1px solid #aaa;padding:9px;font-family:monospace;color:black;",
            "hint": "color:black;font-size:9pt;",
            "info_label": "font-size:8pt;color:black;background-color:transparent;"
        }
    
    def apply_theme(self, app, window):
        """Упрощенное применение темы без рекурсивного обхода виджетов"""
        theme = self.current_theme
        palette = QPalette()
        colors = theme["colors"]
        
        # Устанавливаем только основные цвета
        palette.setColor(QPalette.Window, colors["window"])
        palette.setColor(QPalette.WindowText, colors["window_text"])
        palette.setColor(QPalette.Base, colors["base"])
        palette.setColor(QPalette.AlternateBase, colors["alternate_base"])
        palette.setColor(QPalette.Text, colors["text"])
        palette.setColor(QPalette.Button, colors["button"])
        palette.setColor(QPalette.ButtonText, colors["button_text"])
        palette.setColor(QPalette.Highlight, colors["highlight"])
        palette.setColor(QPalette.HighlightedText, colors["highlighted_text"])
        
        app.setPalette(palette)
        app.setStyleSheet(theme["styles"]["app"])
        
        return theme
    

class WindowSettingsManager:
    """Менеджер сохранения и загрузки настроек окна"""
    
    def __init__(self, app_name="byte-o-scope"):
        self.app_name = app_name
        
        # Храним настройки в домашней директории пользователя
        self.settings_dir = Path.home() / f".{app_name}"
        self.settings_dir.mkdir(exist_ok=True)
        
        self.settings_file = self.settings_dir / "config.json"
        self.default_settings = {
            "perf_slider_value": 4,
            "window_geometry": None,
            "window_state": None,
            "is_maximized": False,
            "theme": "dark",
            "recent_files": [],
            "last_directory": None
        }
    
    def save_settings(self, window):
        """Сохраняет настройки окна в файл"""
        try:
            settings = self.default_settings.copy()
            settings["perf_slider_value"] = window.perf_slider_value
            
            if not window.isMaximized():
                settings["window_geometry"] = {
                    "x": window.x(),
                    "y": window.y(),
                    "width": window.width(),
                    "height": window.height()
                }
            
            settings["is_maximized"] = window.isMaximized()
            
            if hasattr(window, 'theme_manager'):
                settings["theme"] = "dark" if window.theme_manager.is_dark_theme else "light"
            
            if hasattr(window, 'recent_files'):
                existing_files = []
                for file_path in window.recent_files[:10]:
                    try:
                        if Path(file_path).exists():
                            existing_files.append(file_path)
                    except:
                        continue
                settings["recent_files"] = existing_files
            
            if hasattr(window, 'last_directory') and window.last_directory:
                try:
                    if window.last_directory.exists():
                        settings["last_directory"] = str(window.last_directory)
                except:
                    pass
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
            return False
    
    def load_settings(self):
        """Загружает настройки из файла"""
        try:
            if not self.settings_file.exists():
                return self.default_settings.copy()
            
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            # Объединяем с настройками по умолчанию
            result = self.default_settings.copy()
            result.update(settings)
            
            # Проверяем существование файлов в недавних
            if "recent_files" in result:
                existing_files = []
                for file_path in result["recent_files"]:
                    try:
                        if Path(file_path).exists():
                            existing_files.append(file_path)
                    except:
                        continue
                result["recent_files"] = existing_files
            
            return result
        except json.JSONDecodeError as e:
            print(f"Ошибка чтения файла настроек (неверный формат JSON): {e}")
            return self.default_settings.copy()
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")
            return self.default_settings.copy()
    

class TileManager:
    """Менеджер тайлов для оптимизации отображения больших файлов"""
    
    def __init__(self, parent):
        self.parent = parent
        self.tiles = {}
        self.tile_access_times = {}
        self.current_viewport = QRect()
        self.last_rendered_tiles = set()
        self.image_format = QImage.Format_ARGB32
        
    def get_tile(self, tile_x, tile_y, scale, image_width, image_height, bytes_per_pixel):
        tile_key = (tile_x, tile_y, scale)
        
        if tile_key in self.tiles:
            self.tile_access_times[tile_key] = time.time()
            return self.tiles[tile_key]
        
        if hasattr(self.parent, '_start_render'):
            self.parent._start_render()
        
        try:
            # tile_image = self._create_tile(tile_x, tile_y, scale, image_width, image_height, bytes_per_pixel)
            tile_image = self._create_tile(tile_x, tile_y)
            if tile_image:
                self.tiles[tile_key] = tile_image
                self.tile_access_times[tile_key] = time.time()
                self._cleanup_by_memory()
            
            return tile_image
        finally:
            if hasattr(self.parent, '_end_render'):
                QTimer.singleShot(0, self.parent._end_render)
    
    def _create_tile(self, tile_col, tile_row):
        """ Создаёт QImage для тайла с заданными индексами. """
        if not self.parent or not self.parent.mmap_obj:
            return QImage()

        tile_size = self.parent.tile_size
        image_width = self.parent.canvas.image_width
        image_height = self.parent.canvas.image_height

        if image_width == 0 or image_height == 0:
            return QImage()

        # Вычисляем пиксельные координаты начала тайла
        tile_pixel_x = tile_col * tile_size
        tile_pixel_y = tile_row * tile_size

        # Размер тайла может быть меньше на краях
        tile_width = min(tile_size, image_width - tile_pixel_x)
        tile_height = min(tile_size, image_height - tile_pixel_y)

        if tile_width <= 0 or tile_height <= 0:
            return QImage()

        scale = self.parent.scale
        bytes_per_pixel = self.parent.get_bytes_per_pixel()
        current_palette = self.parent.controls.get_current_palette()

        # Определяем режим рендеринга
        if bytes_per_pixel == 1:
            if (current_palette in self.parent.palette_manager.palettes or
                current_palette == "Оттенки серого"):
                if current_palette == "Оттенки серого":
                    return self._render_grayscale_tile(
                        tile_pixel_x, tile_pixel_y, tile_width, tile_height, scale
                    )
                else:
                    return self._render_singlebyte_tile(
                        tile_pixel_x, tile_pixel_y, tile_width, tile_height, scale
                    )
            else:
                # fallback to "Оттенки серого"
                return self._render_grayscale_tile(
                    tile_pixel_x, tile_pixel_y, tile_width, tile_height, scale
                )
        elif bytes_per_pixel > 1:
            return self._render_multibyte_tile(
                tile_pixel_x, tile_pixel_y, tile_width, tile_height,
                bytes_per_pixel, current_palette, scale
            )
        else:
            # Некорректный bytes_per_pixel
            return QImage()
    
    def _render_singlebyte_tile(self, tile_pixel_x, tile_pixel_y, tile_width, tile_height, scale):
        tile_array = np.zeros((tile_height, tile_width), dtype=np.uint32)

        palette = self.parent.current_palette
        if palette is None:
            palette = [(i, i, i) for i in range(256)]
        palette_argb = np.zeros(256, dtype=np.uint32)
        for i, (r, g, b) in enumerate(palette):
            palette_argb[i] = (0xFF << 24) | (r << 16) | (g << 8) | b

        image_width = self.parent.canvas.image_width
        image_height = self.parent.canvas.image_height
        region_offset = self.parent.offset
        region_end = min(region_offset + (self.parent.length or self.parent.file_size), self.parent.file_size)
        bytes_per_pixel = 1

        for y in range(tile_height):
            for x in range(tile_width):
                gx = tile_pixel_x + x
                gy = tile_pixel_y + y

                # Обратное отражение → исходные координаты
                if self.parent.mirror_horizontal:
                    gx = image_width - 1 - gx
                if self.parent.mirror_vertical:
                    gy = image_height - 1 - gy

                if not (0 <= gx < image_width and 0 <= gy < image_height):
                    continue

                pixel_index = gy * image_width + gx
                byte_offset = region_offset + pixel_index * bytes_per_pixel

                if byte_offset >= region_end:
                    continue

                try:
                    byte_val = self.parent.mmap_obj[byte_offset]
                    tile_array[y, x] = palette_argb[byte_val]
                except (IndexError, OSError):
                    continue

        height, width = tile_array.shape
        bytes_per_line = width * 4
        data = tile_array.tobytes() if tile_array.flags['C_CONTIGUOUS'] else tile_array.copy(order='C').tobytes()
        original_image = QImage(data, width, height, bytes_per_line, QImage.Format_ARGB32)

        if scale > 1:
            return original_image.scaled(width * scale, height * scale, Qt.IgnoreAspectRatio, Qt.FastTransformation)
        return original_image
    
    def _render_multibyte_tile(self, tile_pixel_x, tile_pixel_y, tile_width, tile_height, bytes_per_pixel, palette_name, scale):
        tile_array = np.zeros((tile_height, tile_width), dtype=np.uint32)

        image_width = self.parent.canvas.image_width
        image_height = self.parent.canvas.image_height
        region_offset = self.parent.offset
        region_end = min(region_offset + (self.parent.length or self.parent.file_size), self.parent.file_size)
        params = self.parent.palette_params.get(palette_name, {})

        for y in range(tile_height):
            for x in range(tile_width):
                gx = tile_pixel_x + x
                gy = tile_pixel_y + y

                if self.parent.mirror_horizontal:
                    gx = image_width - 1 - gx
                if self.parent.mirror_vertical:
                    gy = image_height - 1 - gy

                if not (0 <= gx < image_width and 0 <= gy < image_height):
                    continue

                pixel_index = gy * image_width + gx
                byte_offset = region_offset + pixel_index * bytes_per_pixel
                end_offset = byte_offset + bytes_per_pixel

                if end_offset > region_end:
                    continue

                try:
                    pixel_data = self.parent.mmap_obj[byte_offset:end_offset]
                    color = self._get_pixel_color_argb(pixel_data, palette_name, params)
                    tile_array[y, x] = color
                except (IndexError, OSError):
                    continue

        height, width = tile_array.shape
        bytes_per_line = width * 4
        data = tile_array.tobytes() if tile_array.flags['C_CONTIGUOUS'] else tile_array.copy(order='C').tobytes()
        original_image = QImage(data, width, height, bytes_per_line, QImage.Format_ARGB32)

        if scale > 1:
            return original_image.scaled(width * scale, height * scale, Qt.IgnoreAspectRatio, Qt.FastTransformation)
        return original_image
    
    def _render_grayscale_tile(self, tile_pixel_x, tile_pixel_y, tile_width, tile_height, scale):
        tile_array = np.zeros((tile_height, tile_width), dtype=np.uint32)

        image_width = self.parent.canvas.image_width
        image_height = self.parent.canvas.image_height
        region_offset = self.parent.offset
        region_end = min(region_offset + (self.parent.length or self.parent.file_size), self.parent.file_size)
        bytes_per_pixel = 1

        for y in range(tile_height):
            for x in range(tile_width):
                gx = tile_pixel_x + x
                gy = tile_pixel_y + y

                if self.parent.mirror_horizontal:
                    gx = image_width - 1 - gx
                if self.parent.mirror_vertical:
                    gy = image_height - 1 - gy

                if not (0 <= gx < image_width and 0 <= gy < image_height):
                    continue

                pixel_index = gy * image_width + gx
                byte_offset = region_offset + pixel_index * bytes_per_pixel

                if byte_offset >= region_end:
                    continue

                try:
                    byte_val = self.parent.mmap_obj[byte_offset]
                    intensity = byte_val
                    argb_color = (0xFF << 24) | (intensity << 16) | (intensity << 8) | intensity
                    tile_array[y, x] = argb_color
                except (IndexError, OSError):
                    continue

        height, width = tile_array.shape
        bytes_per_line = width * 4
        data = tile_array.tobytes() if tile_array.flags['C_CONTIGUOUS'] else tile_array.copy(order='C').tobytes()
        original_image = QImage(data, width, height, bytes_per_line, QImage.Format_ARGB32)

        if scale > 1:
            return original_image.scaled(width * scale, height * scale, Qt.IgnoreAspectRatio, Qt.FastTransformation)
        return original_image
    
    def _get_pixel_color_argb(self, pixel_data, palette_name, params):
        """Получение цвета пикселя в формате ARGB32"""
        if len(pixel_data) == 0:
            return 0xFF000000  # Черный непрозрачный
        
        r = g = b = 0
        
        if palette_name == "RGBA":
            if len(pixel_data) >= 4:
                r, g, b = pixel_data[0], pixel_data[1], pixel_data[2]
        elif palette_name == "ABGR":
            if len(pixel_data) >= 4:
                b, g, r = pixel_data[1], pixel_data[2], pixel_data[3]
        elif palette_name == "RGB":
            if len(pixel_data) >= 3:
                order = params.get("order", "RGB")
                order_map = {'RGB': (0, 1, 2), 'GBR': (1, 2, 0), 'BRG': (2, 0, 1),
                           'BGR': (2, 1, 0), 'GRB': (1, 0, 2), 'RBG': (0, 2, 1)}
                r_idx, g_idx, b_idx = order_map.get(order, (0, 1, 2))
                channels = [pixel_data[0], pixel_data[1], pixel_data[2]]
                r, g, b = channels[r_idx], channels[g_idx], channels[b_idx]
        else:
            # По умолчанию - первый байт как интенсивность
            intensity = pixel_data[0] if pixel_data else 0
            r = g = b = intensity
        
        # Преобразуем в ARGB32: 0xAARRGGBB
        return (0xFF << 24) | (r << 16) | (g << 8) | b
    
    def _get_pixel_color(self, pixel_data, palette_name, params):
        """Старый метод для совместимости (возвращает tuple RGB)"""
        argb = self._get_pixel_color_argb(pixel_data, palette_name, params)
        # Извлекаем RGB из ARGB
        r = (argb >> 16) & 0xFF
        g = (argb >> 8) & 0xFF
        b = argb & 0xFF
        return (r, g, b)
    
    def _cleanup_by_memory(self):
        if not self.tiles:
            return
        total_bytes = sum(img.byteCount() for img in self.tiles.values())
        if total_bytes <= self.parent.max_cache_bytes:
            return
        target_bytes = int(self.parent.max_cache_bytes * 0.75)
        sorted_tiles = sorted(self.tile_access_times.items(), key=lambda x: x[1])
        deleted = False
        for tile_key, _ in sorted_tiles:
            if total_bytes <= target_bytes:
                break
            if tile_key in self.tiles:
                img = self.tiles.pop(tile_key)
                total_bytes -= img.byteCount()
                self.tile_access_times.pop(tile_key, None)
                deleted = True
        if deleted:
            gc.collect()
    
    def update_viewport(self, viewport_rect):
        self.current_viewport = viewport_rect
    
    def prefetch_tiles(self, visible_tiles, scale, image_width, image_height, bytes_per_pixel):
        if not visible_tiles:
            return
        
        min_x = min(t[0] for t in visible_tiles) - self.parent.tile_prefetch_margin
        max_x = max(t[0] for t in visible_tiles) + self.parent.tile_prefetch_margin
        min_y = min(t[1] for t in visible_tiles) - self.parent.tile_prefetch_margin
        max_y = max(t[1] for t in visible_tiles) + self.parent.tile_prefetch_margin
        
        max_tile_x = (image_width + self.parent.tile_size - 1) // self.parent.tile_size
        max_tile_y = (image_height + self.parent.tile_size - 1) // self.parent.tile_size
        
        for tile_y in range(max(0, min_y), min(max_tile_y, max_y + 1)):
            for tile_x in range(max(0, min_x), min(max_tile_x, max_x + 1)):
                tile_key = (tile_x, tile_y, scale)
                if tile_key not in self.tiles:
                    self.get_tile(
                        tile_x, tile_y, scale,
                        image_width, image_height,
                        bytes_per_pixel
                    )
    
    def clear_cache(self):
        self.tiles.clear()
        self.tile_access_times.clear()
        self.last_rendered_tiles.clear()


class CanvasWidget(QWidget):
    """Виджет для отображения больших файлов с тайлами"""
    
    def __init__(self, parent):
        super().__init__()
        self.parent_ref = parent
        self.tile_manager = TileManager(parent)
        self.scroll_area = parent.scroll_area
        self.setMouseTracking(True)
        self.setMinimumSize(1, 1)
        
        self.image_width = 0
        self.image_height = 0
        self.scale = 1
        self.bytes_per_pixel = 1
        
        self.drag_start = None
        self.hover_addr = None
        self.locked_hover_addr = None
        self.movement_locked = False
        
        self.hover_debounce_timer = QTimer()
        self.hover_debounce_timer.setSingleShot(True)
        self.hover_debounce_timer.timeout.connect(self._apply_hover_position)
        self.pending_hover_addr = None
        self.pending_mouse_global_pos = None
        
        self.prefetch_timer = QTimer()
        self.prefetch_timer.setSingleShot(True)
        self.prefetch_timer.timeout.connect(self._prefetch_tiles)
        self.last_prefetch_tiles = set()
        self.wheel_debounce_timer = QTimer()
        self.wheel_debounce_timer.setSingleShot(True)
        self.wheel_debounce_timer.timeout.connect(self._apply_wheel_zoom)
        self.wheel_accumulated_delta = 0
        self.pending_wheel_cursor_pos = None
        self.force_redraw = False
    
    def update_image(self):
        if hasattr(self.parent_ref, '_start_render'):
            self.parent_ref._start_render()
        
        try:
            if not self._has_valid_data():
                self._clear_image()
                return
            
            offset, length, actual_len = self._get_data_region()
            if actual_len <= 0:
                self._clear_image()
                return
            
            self.bytes_per_pixel = self._get_bytes_per_pixel()
            self.image_width = self._calculate_image_width(actual_len)
            self.image_height = self._calculate_image_height(actual_len)
            self.tile_manager.clear_cache()
            
            if hasattr(self.parent_ref, 'scale'):
                self.scale = self.parent_ref.scale
            
            self.setFixedSize(self._get_scaled_size())
            
            self.force_redraw = True
            self.update()
            
            if hasattr(self.parent_ref, 'update_window_title'):
                self.parent_ref.update_window_title()
        finally:
            if hasattr(self.parent_ref, '_end_render'):
                QTimer.singleShot(50, self.parent_ref._end_render)
    
    def _has_valid_data(self):
        return (self.parent_ref.mmap_obj is not None and 
                self.parent_ref.file_size > 0)
    
    def _clear_image(self):
        self.image_width = 0
        self.image_height = 0
        self.tile_manager.clear_cache()
        self.force_redraw = True
        self.update()
    
    def _get_data_region(self):
        offset = self.parent_ref.offset
        length = self.parent_ref.length or self.parent_ref.file_size
        end = min(offset + length, self.parent_ref.file_size)
        actual_len = end - offset
        return offset, length, actual_len
    
    def _get_bytes_per_pixel(self):
        current_palette = self.parent_ref.controls.get_current_palette() if hasattr(self.parent_ref, 'controls') else ""
        return self.parent_ref.palette_manager.get_bytes_per_pixel(current_palette)
    
    def _calculate_image_width(self, data_len):
        pixels_count = data_len // self.bytes_per_pixel
        
        if self.parent_ref.width_mode == "fixed":
            return self.parent_ref.fixed_width
        elif self.parent_ref.width_mode == "auto":
            return int(math.sqrt(pixels_count)) or 1
        else:
            return self._calculate_power_of_two_width(pixels_count)
    
    def _calculate_power_of_two_width(self, pixels_count, max_width=4096):
        w = 1
        while w * 2 <= pixels_count and w < max_width:
            w *= 2
        return w
    
    def _calculate_image_height(self, data_len):
        pixels_count = data_len // self.bytes_per_pixel
        width = self._calculate_image_width(data_len)
        return (pixels_count + width - 1) // width
    
    def _get_scaled_size(self):
        width = self.image_width * self.scale
        height = self.image_height * self.scale
        return QSize(width, height)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            theme_color = self.parent_ref.theme_manager.current_theme["colors"]["widget_background"]
            painter.fillRect(self.rect(), theme_color)
            
            if self.image_width == 0 or self.image_height == 0:
                return
            
            painter.setRenderHint(QPainter.Antialiasing, False)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
            visible_tiles = self._get_visible_tiles()
            
            if visible_tiles != self.last_prefetch_tiles or self.force_redraw:
                viewport_rect = self._get_visible_tile_region()
                self.tile_manager.update_viewport(viewport_rect)
                
                if not self.prefetch_timer.isActive():
                    self.prefetch_timer.start(50)
                
                self.last_prefetch_tiles = visible_tiles
                self.force_redraw = False
            # Устанавливаем режим композиции для лучшей производительности
            painter.setCompositionMode(QPainter.CompositionMode_Source)
            self._draw_visible_tiles(painter, visible_tiles)
            # Восстанавливаем стандартный режим композиции для выделения
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            self._draw_byte_highlight(painter)
        finally:
            painter.end()
    
    def _draw_visible_tiles(self, painter, visible_tiles):
        """Отрисовка видимых тайлов с использованием быстрого формата"""
        for tile_x, tile_y in visible_tiles:
            tile_image = self.tile_manager.get_tile(
                tile_x, tile_y, self.scale, 
                self.image_width, self.image_height,
                self.bytes_per_pixel
            )
            
            if tile_image:
                tile_pixel_x = tile_x * self.parent_ref.tile_size * self.scale
                tile_pixel_y = tile_y * self.parent_ref.tile_size * self.scale
                
                # Отрисовываем тайл БЕЗ сглаживания
                painter.drawImage(tile_pixel_x, tile_pixel_y, tile_image)
    
    def _get_visible_tile_region(self):
        if not self.parent_ref.scroll_area:
            return QRect()
        
        viewport = self.parent_ref.scroll_area.viewport()
        visible_rect = viewport.rect()
        
        h_bar = self.parent_ref.scroll_area.horizontalScrollBar()
        v_bar = self.parent_ref.scroll_area.verticalScrollBar()
        
        visible_rect.translate(h_bar.value(), v_bar.value())
        
        scale = self.scale
        visible_rect.setLeft(max(0, visible_rect.left() // scale))
        visible_rect.setTop(max(0, visible_rect.top() // scale))
        visible_rect.setRight(min(self.image_width, visible_rect.right() // scale + 1))
        visible_rect.setBottom(min(self.image_height, visible_rect.bottom() // scale + 1))
        
        return visible_rect
    
    def _get_visible_tiles(self):
        visible_rect = self._get_visible_tile_region()
        if visible_rect.isNull():
            return set()
        
        start_tile_x = max(0, visible_rect.left() // self.parent_ref.tile_size)
        start_tile_y = max(0, visible_rect.top() // self.parent_ref.tile_size)
        end_tile_x = min((self.image_width + self.parent_ref.tile_size - 1) // self.parent_ref.tile_size, 
                        visible_rect.right() // self.parent_ref.tile_size + 1)
        end_tile_y = min((self.image_height + self.parent_ref.tile_size - 1) // self.parent_ref.tile_size,
                        visible_rect.bottom() // self.parent_ref.tile_size + 1)
        
        visible_tiles = set()
        for tile_y in range(start_tile_y, end_tile_y):
            for tile_x in range(start_tile_x, end_tile_x):
                visible_tiles.add((tile_x, tile_y))
        
        return visible_tiles
    
    def _prefetch_tiles(self):
        if self.image_width == 0 or self.image_height == 0:
            return
        
        visible_tiles = self._get_visible_tiles()
        if not visible_tiles:
            return
        
        self.tile_manager.prefetch_tiles(
            visible_tiles, 
            self.scale,
            self.image_width,
            self.image_height,
            self.bytes_per_pixel
        )
    
    def _draw_byte_highlight(self, painter):
        addr_to_draw = self.locked_hover_addr if self.movement_locked else self.hover_addr
        
        if addr_to_draw is None:
            return
        
        if not (0 <= addr_to_draw < self.parent_ref.file_size):
            return
        
        scale = self.scale
        w_img = self.image_width
        bytes_per_pixel = self.bytes_per_pixel
        
        pixel_index = (addr_to_draw - self.parent_ref.offset) // bytes_per_pixel
        x_original = pixel_index % w_img
        y_original = pixel_index // w_img
        
        x = x_original
        y = y_original
        
        if self.parent_ref.mirror_horizontal:
            x = w_img - 1 - x
        if self.parent_ref.mirror_vertical:
            y = self.image_height - 1 - y
        
        x_scaled = x * scale
        y_scaled = y * scale
        
        if x_scaled >= w_img * scale or y_scaled >= self.image_height * scale:
            return
        
        try:
            first_byte_addr = pixel_index * bytes_per_pixel + self.parent_ref.offset
            if first_byte_addr < self.parent_ref.file_size:
                byte_value = self.parent_ref.mmap_obj[first_byte_addr]
                if self.parent_ref.current_palette is not None:
                    r, g, b = self.parent_ref.current_palette[byte_value]
                else:
                    r = g = b = byte_value
                
                contour_color = QColor(*[min(255, 285 - c) for c in (r, g, b)])
                painter.setPen(QPen(contour_color, 2, Qt.DashLine))
                painter.drawRect(x_scaled, y_scaled, scale - 1, scale - 1)
        except:
            painter.setPen(QPen(QColor(255, 0, 0), 2, Qt.DashLine))
            painter.drawRect(x_scaled, y_scaled, scale - 1, scale - 1)
    
    def get_byte_address(self, pos_x, pos_y):
        if self.image_width == 0 or self.image_height == 0:
            return None
        
        scale = self.scale
        x, y = pos_x // scale, pos_y // scale
        
        original_x = x
        original_y = y
        
        if self.parent_ref.mirror_horizontal:
            original_x = self.image_width - 1 - original_x
        if self.parent_ref.mirror_vertical:
            original_y = self.image_height - 1 - original_y
        
        if 0 <= original_x < self.image_width and 0 <= original_y < self.image_height:
            pixel_index = original_y * self.image_width + original_x
            addr = pixel_index * self.bytes_per_pixel + self.parent_ref.offset
            
            if 0 <= addr < self.parent_ref.file_size:
                return addr
        
        return None
    
    def mouseMoveEvent(self, event):
        if self.drag_start is not None:
            self._handle_drag(event)
            event.accept()
        else:
            self._handle_hover(event)
    
    def _handle_drag(self, event):
        current_pos = event.globalPos()
        delta = current_pos - self.drag_start
        
        if self.parent_ref.scroll_area:
            h_bar = self.parent_ref.scroll_area.horizontalScrollBar()
            v_bar = self.parent_ref.scroll_area.verticalScrollBar()
            h_bar.setValue(h_bar.value() - delta.x())
            v_bar.setValue(v_bar.value() - delta.y())
            self.drag_start = current_pos
        
        self.force_redraw = True
        self.update()
        if hasattr(self.parent_ref, 'panorama_widget'):
            self.parent_ref.panorama_widget.update_panorama()
    
    def _handle_hover(self, event):
        addr = self.get_byte_address(event.x(), event.y())
        
        self.pending_hover_addr = addr
        self.pending_mouse_global_pos = event.globalPos()
        self.hover_debounce_timer.start(15)
    
    def _apply_hover_position(self):
        if self.movement_locked:
            return
        
        addr = self.pending_hover_addr
        self.hover_addr = addr
        self.parent_ref.byte_info.update_info(addr)
        
        if addr is not None and self.parent_ref.byte_info.popup_checkbox.isChecked():
            pos = self.pending_mouse_global_pos
            if pos:
                self.parent_ref.byte_info.popup.move(pos.x() + 20, pos.y() + 20)
                self.parent_ref.byte_info.popup.show()
        else:
            self.parent_ref.byte_info.popup.hide()
        
        self.update()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self._start_drag(event)
            event.accept()
        elif event.button() == Qt.LeftButton:
            self._handle_left_click(event)
            event.accept()
    
    def _start_drag(self, event):
        self.drag_start = event.globalPos()
        self.setCursor(Qt.ClosedHandCursor)
    
    def _handle_left_click(self, event):
        addr = self.get_byte_address(event.x(), event.y())
        if addr is None:
            return
        
        if self.movement_locked:
            self._unlock_movement(addr)
        else:
            self._lock_movement(addr)
        
        self.parent_ref.byte_info.update_info(addr)
        self.update()
    
    def _lock_movement(self, addr):
        self.movement_locked = True
        self.locked_hover_addr = addr
    
    def _unlock_movement(self, addr):
        self.movement_locked = False
        self.hover_addr = addr
        self.locked_hover_addr = None
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self._end_drag()
            event.accept()
    
    def _end_drag(self):
        self.drag_start = None
        self.setCursor(Qt.ArrowCursor)
    
    def wheelEvent(self, event):
        modifiers = event.modifiers()
        if modifiers & Qt.ControlModifier:
            # Ctrl + колесо → изменение ширины
            if self.parent_ref.controls:
                step = self.parent_ref.controls.width_step_spinbox.value()
                current = self.parent_ref.controls.width_spinbox.value()
                delta = 1 if event.angleDelta().y() > 0 else -1
                new_value = max(1, ((current // step) + delta) * step)
                self.parent_ref.controls.width_spinbox.setValue(new_value)
            event.accept()
        else:
            # Обычное поведение: масштабирование
            if self.parent_ref.auto_scale:
                event.ignore()
                return
            # Накапливаем дельту
            delta = 1 if event.angleDelta().y() > 0 else -1
            self.wheel_accumulated_delta += delta
            self.pending_wheel_cursor_pos = event.pos()
            # Запускаем debounce
            self.wheel_debounce_timer.start(150)
            event.accept()
    
    def _apply_wheel_zoom(self):
        if not self.scroll_area or self.wheel_accumulated_delta == 0 or self.pending_wheel_cursor_pos is None:
            return

        cursor_pos = self.pending_wheel_cursor_pos
        total_delta = self.wheel_accumulated_delta

        # Сбрасываем буферы
        self.wheel_accumulated_delta = 0
        self.pending_wheel_cursor_pos = None

        h_bar = self.scroll_area.horizontalScrollBar()
        v_bar = self.scroll_area.verticalScrollBar()

        old_scale = self.scale
        new_scale = max(1, min(SCALE_MAX, self.scale + total_delta))

        if new_scale == self.scale:
            return

        # === 1. Преобразуем позицию курсора в логические координаты изображения ===
        logical_x = (h_bar.value() + cursor_pos.x()) / old_scale
        logical_y = (v_bar.value() + cursor_pos.y()) / old_scale

        # === 2. Применяем новый масштаб ===
        self.scale = new_scale
        if self.parent_ref.controls:
            self.parent_ref.controls.scale_spinbox.setValue(new_scale)
        self.parent_ref.scale = new_scale

        self.tile_manager.clear_cache()
        self.force_redraw = True
        self.setFixedSize(self._get_scaled_size())

        # === 3. Пересчитываем прокрутку, чтобы логическая точка осталась под курсором ===
        new_h_value = int(logical_x * new_scale - cursor_pos.x())
        new_v_value = int(logical_y * new_scale - cursor_pos.y())

        # Ограничиваем значения прокрутки
        max_h = max(0, self.width() - self.scroll_area.viewport().width())
        max_v = max(0, self.height() - self.scroll_area.viewport().height())

        h_bar.setValue(max(0, min(new_h_value, max_h)))
        v_bar.setValue(max(0, min(new_v_value, max_v)))

        self.update()
        self.parent_ref.apply_settings(self.parent_ref.controls.get_config())
    
    def leaveEvent(self, event):
        if not self.movement_locked:
            self.hover_addr = None
            self.parent_ref.byte_info.schedule_hide()
            self.update()
    
    def resizeEvent(self, event):
        """Обработчик изменения размера виджета"""
        super().resizeEvent(event)
        
        # Обновляем панораму
        if hasattr(self.parent_ref, 'panorama_widget'):
            self.parent_ref.panorama_widget.update_panorama()


class PaletteManager:
    """Менеджер палитр для визуализации файлов"""
    
    DEFAULT_CUSTOM_RULES = [
        {"start": 0, "end": 31, "color": "#FF0000"},
        {"start": 32, "end": 63, "color": "#00FF00"},
        {"start": 64, "end": 95, "color": "#0000FF"},
        {"start": 96, "end": 127, "color": "#FF0080"},
        {"start": 128, "end": 159, "color": "#80FF00"},
        {"start": 160, "end": 191, "color": "#0080FF"},
        {"start": 192, "end": 223, "color": "#FF8000"},
        {"start": 224, "end": 255, "color": "#8000FF"},
    ]
    
    def __init__(self):
        self.palette_groups = {
            "singlebyte": ["Оттенки серого", "Инвертированная", "Тепловая", 
                       "Термальная", "Вирдис", "Плазма",
                       "Радуга", "HSV",
                       "Нули/Единицы", "Не-Ноль", "Установлен старший бит", 
                       "Установлен младший бит", "Полубайты", 
                       "Старший полубайт", "Младший полубайт",
                       "Порог", "Полосы энтропии", "Битовая плоскость", "Частота байтов", 
                       "Повторы", "Пользовательская"]
        }
        
        self.palettes = {
            "Тепловая": self._create_heat,
            "Оттенки серого": self._create_grayscale,
            "Инвертированная": self._create_inverted,
            "Термальная": self._create_thermal,
            "Плазма": self._create_plasma,
            "Вирдис": self._create_viridis,
            "Радуга": self._create_rainbow,
            "HSV": self._create_hsv,
            "Нули/Единицы": self._create_zeros_ones,
            "Не-Ноль": self._create_nonzero,
            "Установлен старший бит": self._create_highbit,
            "Установлен младший бит": self._create_lowbit,
            "Полубайты": self._create_nibbles,
            "Старший полубайт": self._create_high_nibble,
            "Младший полубайт": self._create_low_nibble,
            "Порог": self._create_solarized,
            "Полосы энтропии": self._create_entropy,
            "Битовая плоскость": self._create_bitplane,
            "Пользовательская": self._create_custom,
            "Частота байтов": self._create_byte_frequency,
            "Повторы": self._create_repeats_highlight,
        }
        
        self.palette_configs = {
            "Тепловая": {"configurable": False, "default_params": {}, "bytes_per_pixel": 1},
            "Оттенки серого": {"configurable": False, "default_params": {}, "bytes_per_pixel": 1},
            "Инвертированная": {"configurable": False, "default_params": {}, "bytes_per_pixel": 1},
            "Нули/Единицы": {"configurable": False, "default_params": {}, "bytes_per_pixel": 1},
            "Не-Ноль": {"configurable": False, "default_params": {}, "bytes_per_pixel": 1},
            "Установлен старший бит": {"configurable": False, "default_params": {}, "bytes_per_pixel": 1},
            "Установлен младший бит": {"configurable": False, "default_params": {}, "bytes_per_pixel": 1},
            "Термальная": {"configurable": False, "default_params": {}, "bytes_per_pixel": 1},
            "Плазма": {"configurable": False, "default_params": {}, "bytes_per_pixel": 1},
            "Вирдис": {"configurable": False, "default_params": {}, "bytes_per_pixel": 1},
            "Радуга": {"configurable": False, "default_params": {}, "bytes_per_pixel": 1},
            "HSV": {"configurable": False, "default_params": {}, "bytes_per_pixel": 1},
            "Полубайты": {"configurable": False, "default_params": {}, "bytes_per_pixel": 1},
            "Старший полубайт": {"configurable": False, "default_params": {}, "bytes_per_pixel": 1},
            "Младший полубайт": {"configurable": False, "default_params": {}, "bytes_per_pixel": 1},
            "Порог": {"configurable": True, "default_params": {"threshold": 64}, "bytes_per_pixel": 1},
            "Полосы энтропии": {"configurable": True, "default_params": {"step": 16}, "bytes_per_pixel": 1},
            "Битовая плоскость": {"configurable": True, "default_params": {"plane": 0}, "bytes_per_pixel": 1},
            "Пользовательская": {"configurable": True, "default_params": {
                "rules": self.DEFAULT_CUSTOM_RULES.copy(), 
                "default_color": "#000000"
            }, "bytes_per_pixel": 1},
            "Частота байтов": {"configurable": True, "default_params": {"auto": True}, "bytes_per_pixel": 1},
            "Повторы": {"configurable": True, "default_params": {"auto": True, "min_count": 50}, "bytes_per_pixel": 1},
        }
    
        self.palette_configs.update({
            "RGBA": {"configurable": False, "default_params": {}, "bytes_per_pixel": 4},
            "ABGR": {"configurable": False, "default_params": {}, "bytes_per_pixel": 4},
            "RGB": {"configurable": True, "default_params": {"order": "RGB"}, "bytes_per_pixel": 3},
            "Integer 8": {"configurable": True, "default_params": {"signed": False}, "bytes_per_pixel": 1},
            "Integer 16": {"configurable": True, "default_params": {"endianness": "big", "signed": False}, "bytes_per_pixel": 2},
            "Integer 32": {"configurable": True, "default_params": {"endianness": "big", "signed": False}, "bytes_per_pixel": 4},
            "Integer 64": {"configurable": True, "default_params": {"endianness": "big", "signed": False}, "bytes_per_pixel": 8},
            "Float 32": {"configurable": True, "default_params": {"endianness": "big"}, "bytes_per_pixel": 4},
            "Float 64": {"configurable": True, "default_params": {"endianness": "big"}, "bytes_per_pixel": 8},
        })
        
        self.palette_groups["multibyte"] = [
            "RGBA", "ABGR", "RGB", 
            "Integer 8", "Integer 16", "Integer 32", "Integer 64",
            "Float 32", "Float 64"
        ]
    
    def get_bytes_per_pixel(self, palette_name):
        config = self.palette_configs.get(palette_name, {})
        return config.get("bytes_per_pixel", 1)
    
    def is_configurable(self, palette_name):
        return self.palette_configs.get(palette_name, {}).get("configurable", False)
    
    def get_default_params(self, palette_name):
        return self.palette_configs.get(palette_name, {}).get("default_params", {}).copy()
    
    def create_palette(self, palette_name, params=None, file_data=None):
        if palette_name not in self.palettes:
            return self._create_grayscale({})
        
        if params is None:
            params = self.get_default_params(palette_name)
        
        if palette_name == "Частота байтов":
            params = self._prepare_byte_frequency_params(params, file_data)
        elif palette_name == "Повторы":
            params = self._prepare_repeats_params(params, file_data)
        
        return self.palettes[palette_name](params)
    
    def get_palette_names_for_group(self, group_name):
        return self.palette_groups.get(group_name, [])
    
    def get_all_palette_names(self):
        return list(self.palettes.keys())
    
    def get_grouped_palettes(self):
        result = []
        for group_name, palettes in self.palette_groups.items():
            if result:
                result.append(None)
            result.extend(palettes)
        return result
    
    @staticmethod
    def _create_grayscale(params):
        return [(i, i, i) for i in range(256)]
    
    @staticmethod
    def _create_inverted(params):
        return [(255 - i, 255 - i, 255 - i) for i in range(256)]
    
    @staticmethod
    def _create_zeros_ones(params):
        return [(0, 0, 255) if i == 0 else (255, 255, 0) if i == 255 else (0, 0, 0) for i in range(256)]
    
    @staticmethod
    def _create_nonzero(params):
        return [(0, 255, 0) if i != 0 else (0, 0, 0) for i in range(256)]
    
    @staticmethod
    def _create_highbit(params):
        return [(255, 0, 0) if i & 0x80 else (0, 0, 0) for i in range(256)]
    
    @staticmethod
    def _create_lowbit(params):
        return [(0, 255, 255) if i & 1 else (0, 0, 0) for i in range(256)]
    
    @staticmethod
    def _create_heat(params):
        colors = []
        for i in range(256):
            t = i / 255.0
            if t < 1/6:
                r, g, b = 0, 0, int(255 * 6 * t)
            elif t < 2/6:
                r, g, b = 0, int(255 * (6 * t - 1)), 255
            elif t < 3/6:
                r, g, b = 0, 255, int(255 * (3 - 6 * t))
            elif t < 4/6:
                r, g, b = int(255 * (6 * t - 3)), 255, 0
            elif t < 5/6:
                r, g, b = 255, int(255 * (5 - 6 * t)), 0
            else:
                r, g, b = 255, int(255 * (6 * t - 5)), int(255 * (6 * t - 5))
            colors.append((r, g, b))
        return colors
    
    @staticmethod
    def _create_thermal(params):
        return [(min(255, 3 * i), min(255, 2 * i), i // 2) for i in range(256)]
    
    @staticmethod
    def _create_plasma(params):
        return [
            (
                int(255 * (0.5 + 0.5 * math.sin(2 * math.pi * i / 255))),
                int(255 * (0.5 + 0.5 * math.sin(2 * math.pi * i / 255 + 2 * math.pi / 3))),
                int(255 * (0.5 + 0.5 * math.sin(2 * math.pi * i / 255 + 4 * math.pi / 3)))
            )
            for i in range(256)
        ]
    
    @staticmethod
    def _create_viridis(params):
        return [
            (
                int(68 + (i / 255) * (240 - 68)),
                int(255 * (1 - (1 - (i / 255))**2)),
                int(255 * ((1 - i / 255)**2))
            )
            for i in range(256)
        ]
    
    @staticmethod
    def _create_rainbow(params):
        return [
            (255, i, 0) if i < 128 else (255 - (i - 128) * 2, 255, (i - 128) * 2)
            for i in range(256)
        ]
    
    @staticmethod
    def _create_hsv(params):
        return [
            QColor.fromHsv(int(i * 360 / 255) % 360, 255, 255).getRgb()[:3]
            for i in range(256)
        ]
    
    @staticmethod
    def _create_nibbles(params):
        return [(i & 0xF0, (i << 4) & 0xF0, 0) for i in range(256)]
    
    @staticmethod
    def _create_high_nibble(params):
        return [(i & 0xF0, i & 0xF0, i & 0xF0) for i in range(256)]
    
    @staticmethod
    def _create_low_nibble(params):
        return [((i & 0x0F) << 4, (i & 0x0F) << 4, (i & 0x0F) << 4) for i in range(256)]
    
    @staticmethod
    def _create_solarized(params):
        threshold = params.get("threshold", 64)
        return [
            (7, 54, 101) if i < threshold else (88, 110, 122)
            for i in range(256)
        ]
    
    @staticmethod
    def _create_entropy(params):
        step = max(1, int(params.get("step", 16)))
        colors = []
        for i in range(256):
            band = min(255, (i // step) * step + step // 2)
            r = int(255 * band / 255)
            b = 255 - r
            colors.append((r, 0, b))
        return colors
    
    @staticmethod
    def _create_bitplane(params):
        plane = max(0, min(7, int(params.get("plane", 0))))
        return [(255, 255, 255) if (b >> plane) & 1 else (0, 0, 0) for b in range(256)]
    
    @staticmethod
    def _create_custom(params):
        rules = params.get("rules", [])
        default_color = params.get("default_color", "#000000")
        
        def hex_to_rgb(h):
            h = h.lstrip('#')
            return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
        
        try:
            default_rgb = hex_to_rgb(default_color)
        except:
            default_rgb = (0, 0, 0)
        
        palette = [default_rgb] * 256
        
        for rule in rules:
            start = max(0, min(255, int(rule.get("start", 0))))
            end = max(0, min(255, int(rule.get("end", start))))
            color_str = rule.get("color", "#000000")
            try:
                rgb = hex_to_rgb(color_str)
            except:
                continue
            for i in range(start, end + 1):
                palette[i] = rgb
        
        return palette
    
    @staticmethod
    def _create_byte_frequency(params):
        freq = params.get("freq", [1] * 256)
        max_freq = max(freq) or 1
        colors = []
        for i in range(256):
            t = freq[i] / max_freq
            r = int(255 * t)
            g = int(255 * (1 - t))
            b = 0
            colors.append((r, g, b))
        return colors
    
    @staticmethod
    def _create_repeats_highlight(params):
        repeats = set(params.get("repeats", []))
        return [(255, 0, 0) if i in repeats else (i, i, i) for i in range(256)]
    
    @staticmethod
    def _prepare_byte_frequency_params(params, file_data):
        if params.get("auto", True) and file_data:
            freq = [0] * 256
            for b in file_data:
                freq[b] += 1
            return {"freq": freq}
        return params
    
    @staticmethod
    def _prepare_repeats_params(params, file_data):
        if params.get("auto", True) and file_data:
            min_count = params.get("min_count", 50)
            counts = Counter(file_data)
            repeats = [b for b, c in counts.items() if c >= min_count]
            return {"repeats": repeats}
        return params
    

class PaletteSettingsManager:
    """Менеджер настроек палитры"""
    
    def __init__(self, parent):
        self.parent = parent
        self.rule_widgets = []
    
    def clear_palette_settings(self):
        """Очистка области настроек палитры БЕЗ утечек"""
        layout = self.parent.palette_settings_layout
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
            else:
                # Если это layout — рекурсивно очистить
                self._clear_layout(item.layout())
        
        self.rule_widgets = []
    
    def _clear_layout(self, layout):
        """Рекурсивная очистка вложенного layout'а"""
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()
                else:
                    self._clear_layout(item.layout())
    
    def _add_setting_row(self, label_text, widget):
        """Добавление строки настройки: метка слева, виджет справа"""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(QLabel(label_text))
        row.addWidget(widget)
        row.addStretch()
        self.parent.palette_settings_layout.addLayout(row)
    
    def _add_info_label(self, text):
        """Добавление информационной метки"""
        label = QLabel(text)
        label.setStyleSheet(self.parent.theme_manager.current_theme["styles"]["info_label"])
        label.setWordWrap(True)
        self.parent.palette_settings_layout.addWidget(label)
    
    def _update_color_button(self, button, hex_color):
        """Обновление внешнего вида кнопки цвета"""
        if not hex_color.startswith('#'):
            hex_color = "#000000"
        button.setProperty("color_hex", hex_color)
        
        # Определяем цвет границы в зависимости от темы
        if self.parent.theme_manager.is_dark_theme:
            border_color = "#aaa" if hex_color in ["#000000", "#ffffff"] else "#888"
        else:
            border_color = "#666" if hex_color in ["#000000", "#ffffff"] else "#444"
        
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {hex_color};
                border: 1px solid {border_color};
                border-radius: 3px;
            }}
            QPushButton:hover {{
                border: 2px solid #ccc;
            }}
        """)
    
    def build_palette_settings_ui(self, palette_name):
        """Создание UI для настроек выбранной палитры с подсказками"""
        self.clear_palette_settings()
        params = self.parent.palette_params.get(
            palette_name,
            self.parent.palette_manager.get_default_params(palette_name)
        )

        visible = True

        if palette_name == "Пользовательская":
            self.default_color_btn = QPushButton()
            default_color = params.get("default_color", "#000000")
            self._update_color_button(self.default_color_btn, default_color)
            self.default_color_btn.setFixedHeight(20)
            self.default_color_btn.clicked.connect(self._pick_default_color)
            self._add_setting_row("Цвет вне диапазонов:", self.default_color_btn)
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setFrameShadow(QFrame.Sunken)
            self.parent.palette_settings_layout.addWidget(separator)
            rules_header = QLabel("<b>Правила диапазонов</b>")
            self.parent.palette_settings_layout.addWidget(rules_header)
            self.rules_scroll = QScrollArea()
            self.rules_scroll.setWidgetResizable(True)
            self.rules_scroll.setFixedHeight(200)
            self.rules_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.rules_scroll.setFrameShape(QFrame.NoFrame)
            self.rules_scroll.setStyleSheet("background: transparent;")
            
            self.rules_widget = QWidget()
            self.rules_container = QVBoxLayout(self.rules_widget)
            self.rules_container.setSpacing(6)
            self.rules_container.setContentsMargins(2, 2, 2, 2)
            self.rules_scroll.setWidget(self.rules_widget)
            self.parent.palette_settings_layout.addWidget(self.rules_scroll)
            
            # Список виджетов правил
            self.rule_widgets = []
            
            # Загрузка правил из параметров
            rules = params.get("rules", self.parent.palette_manager.DEFAULT_CUSTOM_RULES.copy())
            for rule in rules:
                self._add_rule_widget(
                    rule.get("start", 0),
                    rule.get("end", 0),
                    rule.get("color", "#FF0000")
                )
            
            # === Кнопки управления правилами ===
            buttons_layout = QHBoxLayout()
            buttons_layout.setContentsMargins(0, 0, 0, 0)
            
            self.add_rule_btn = QPushButton("+ Добавить правило")
            self.add_rule_btn.clicked.connect(self._add_empty_rule)
            buttons_layout.addWidget(self.add_rule_btn)
            
            buttons_layout.addStretch()
            self.parent.palette_settings_layout.addLayout(buttons_layout)

        elif palette_name == "Полосы энтропии":
            self.step_spinbox = QSpinBox()
            self.step_spinbox.setRange(1, 256)
            self.step_spinbox.setValue(params.get("step", 16))
            self.step_spinbox.valueChanged.connect(self.parent.update_current_palette_params)
            self._add_setting_row("Шаг (полосы):", self.step_spinbox)
            self._add_info_label("Высокие значения создают\nменьше цветовых полос,\nнизкие — больше.")

        elif palette_name == "Битовая плоскость":
            self.plane_spinbox = QSpinBox()
            self.plane_spinbox.setRange(0, 7)
            self.plane_spinbox.setValue(params.get("plane", 0))
            self.plane_spinbox.valueChanged.connect(self.parent.update_current_palette_params)
            self._add_setting_row("Битовая плоскость (0–7):", self.plane_spinbox)
            self._add_info_label("0 = младший бит,\n7 = старший бит.")

        elif palette_name == "Порог":
            self.threshold_spin = QSpinBox()
            self.threshold_spin.setRange(0, 255)
            self.threshold_spin.setValue(params.get("threshold", 64))
            self.threshold_spin.valueChanged.connect(self.parent.update_current_palette_params)
            self._add_setting_row("Порог (0–255):", self.threshold_spin)
            self._add_info_label("Байты < порога — тёмно-синие,\n≥ порога — серо-голубые.")

        elif palette_name == "Частота байтов":
            self.auto_freq_checkbox = QCheckBox("Автоматический расчёт")
            self.auto_freq_checkbox.setChecked(params.get("auto", True))
            self.auto_freq_checkbox.toggled.connect(self.parent.update_current_palette_params)
            self.parent.palette_settings_layout.addWidget(self.auto_freq_checkbox)
            self._add_info_label("В автоматическом режиме частота\nсчитается из файла.\nДля файлов до 10 Мб")

        elif palette_name == "Повторы":
            self.auto_repeats_checkbox = QCheckBox("Автоматическое определение")
            self.auto_repeats_checkbox.setChecked(params.get("auto", True))
            self.auto_repeats_checkbox.toggled.connect(self.parent.update_current_palette_params)
            self.parent.palette_settings_layout.addWidget(self.auto_repeats_checkbox)

            self.min_count_spin = QSpinBox()
            self.min_count_spin.setRange(2, 1000)
            self.min_count_spin.setValue(params.get("min_count", 50))
            self.min_count_spin.setEnabled(True)
            self.auto_repeats_checkbox.toggled.connect(
                lambda checked: self.min_count_spin.setEnabled(not checked)
            )
            self.min_count_spin.valueChanged.connect(self.parent.update_current_palette_params)
            self._add_setting_row("Мин. количество повторов:", self.min_count_spin)

            self._add_info_label("В автоматическом режиме\nвыделяются байты,\nвстречающиеся ≥N раз.\nДля файлов до 10 Мб")
        
        # Настройки для многобайтовых палитр
        elif palette_name == "RGB":
            self.rgb_order_combo = QComboBox()
            self.rgb_order_combo.addItems(["RGB", "GBR", "BRG", "BGR", "GRB", "RBG"])
            self.rgb_order_combo.setCurrentText(params.get("order", "RGB"))
            self.rgb_order_combo.currentTextChanged.connect(self.parent.update_current_palette_params)
            self._add_setting_row("Порядок цветов:", self.rgb_order_combo)
            self._add_info_label("Определяет порядок\nбайтов R, G, B.\nRGB = Red, Green, Blue")
        
        elif palette_name == "Integer 8":
            self.int8_signed_checkbox = QCheckBox("Со знаком (signed)")
            self.int8_signed_checkbox.setChecked(params.get("signed", False))
            self.int8_signed_checkbox.toggled.connect(self.parent.update_current_palette_params)
            self.parent.palette_settings_layout.addWidget(self.int8_signed_checkbox)
            self._add_info_label("Со знаком: -128..127\nБез знака: 0..255")

        elif palette_name == "Integer 16":
            self.int16_endian_combo = QComboBox()
            self.int16_endian_combo.addItems(["big", "little"])
            self.int16_endian_combo.setCurrentText(params.get("endianness", "big"))
            self.int16_endian_combo.currentTextChanged.connect(self.parent.update_current_palette_params)
            self._add_setting_row("Порядок байтов:", self.int16_endian_combo)
            
            self.int16_signed_checkbox = QCheckBox("Со знаком (signed)")
            self.int16_signed_checkbox.setChecked(params.get("signed", False))
            self.int16_signed_checkbox.toggled.connect(self.parent.update_current_palette_params)
            self.parent.palette_settings_layout.addWidget(self.int16_signed_checkbox)
            self._add_info_label("Со знаком: -32768..32767\nБез знака: 0..65535")

        elif palette_name == "Integer 32":
            self.int32_endian_combo = QComboBox()
            self.int32_endian_combo.addItems(["big", "little"])
            self.int32_endian_combo.setCurrentText(params.get("endianness", "big"))
            self.int32_endian_combo.currentTextChanged.connect(self.parent.update_current_palette_params)
            self._add_setting_row("Порядок байтов:", self.int32_endian_combo)
            
            self.int32_signed_checkbox = QCheckBox("Со знаком (signed)")
            self.int32_signed_checkbox.setChecked(params.get("signed", False))
            self.int32_signed_checkbox.toggled.connect(self.parent.update_current_palette_params)
            self.parent.palette_settings_layout.addWidget(self.int32_signed_checkbox)
            self._add_info_label("Со знаком: -2147483648..2147483647\nБез знака: 0..4294967295")

        elif palette_name == "Integer 64":
            self.int64_endian_combo = QComboBox()
            self.int64_endian_combo.addItems(["big", "little"])
            self.int64_endian_combo.setCurrentText(params.get("endianness", "big"))
            self.int64_endian_combo.currentTextChanged.connect(self.parent.update_current_palette_params)
            self._add_setting_row("Порядок байтов:", self.int64_endian_combo)
            
            self.int64_signed_checkbox = QCheckBox("Со знаком (signed)")
            self.int64_signed_checkbox.setChecked(params.get("signed", False))
            self.int64_signed_checkbox.toggled.connect(self.parent.update_current_palette_params)
            self.parent.palette_settings_layout.addWidget(self.int64_signed_checkbox)
            self._add_info_label("Со знаком: -9.22e18..9.22e18\nБез знака: 0..1.84e19")

        elif palette_name == "Float 32":
            self.float32_endian_combo = QComboBox()
            self.float32_endian_combo.addItems(["big", "little"])
            self.float32_endian_combo.setCurrentText(params.get("endianness", "big"))
            self.float32_endian_combo.currentTextChanged.connect(self.parent.update_current_palette_params)
            self._add_setting_row("Порядок байтов:", self.float32_endian_combo)
            self._add_info_label("32-битное число\nс плавающей точкой")

        elif palette_name == "Float 64":
            self.float64_endian_combo = QComboBox()
            self.float64_endian_combo.addItems(["big", "little"])
            self.float64_endian_combo.setCurrentText(params.get("endianness", "big"))
            self.float64_endian_combo.currentTextChanged.connect(self.parent.update_current_palette_params)
            self._add_setting_row("Порядок байтов:", self.float64_endian_combo)
            self._add_info_label("64-битное число\nс плавающей точкой")

        else:
            visible = False

        self.parent.palette_settings_area.setVisible(visible)
        self.parent.reset_palette_btn.setVisible(visible)
        self.parent.apply_palette_checkbox.setVisible(visible)
    
    def _add_rule_widget(self, start=0, end=0, color="#FF0000"):
        """Добавление виджета правила в контейнер"""
        rule_widget = QWidget()
        rule_widget.setStyleSheet("background-color: transparent;")
        
        rule_layout = QHBoxLayout(rule_widget)
        rule_layout.setContentsMargins(0, 0, 0, 0)
        rule_layout.setSpacing(6)
        
        # Метка номера правила
        rule_num = len(self.rule_widgets) + 1
        num_label = QLabel(f"{rule_num}.")
        num_label.setFixedWidth(20)
        num_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        num_label.setStyleSheet("color: #ccc;" if self.parent.theme_manager.is_dark_theme else "color: #666;")
        rule_layout.addWidget(num_label)
        
        # Спинбокс начала диапазона
        start_spinbox = QSpinBox()
        start_spinbox.setRange(0, 255)
        start_spinbox.setValue(start)
        start_spinbox.setFixedWidth(70)
        start_spinbox.setToolTip("Начало диапазона (0-255)")
        rule_layout.addWidget(start_spinbox)
        
        # Разделитель
        dash_label = QLabel("–")
        dash_label.setStyleSheet("color: #888;" if self.parent.theme_manager.is_dark_theme else "color: #666;")
        rule_layout.addWidget(dash_label)
        
        # Спинбокс конца диапазона
        end_spinbox = QSpinBox()
        end_spinbox.setRange(0, 255)
        end_spinbox.setValue(end)
        end_spinbox.setFixedWidth(70)
        end_spinbox.setToolTip("Конец диапазона (0-255)")
        rule_layout.addWidget(end_spinbox)
        
        # Кнопка выбора цвета
        color_btn = QPushButton()
        self._update_color_button(color_btn, color)
        color_btn.setFixedSize(SMALL_BUTTON_WIDTH, 25)
        color_btn.setToolTip(f"Цвет: {color}")
        rule_layout.addWidget(color_btn)
        
        # Кнопка удаления правила
        delete_btn = QPushButton("×")
        delete_btn.setFixedSize(25, 25)
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                color: {"red" if self.parent.theme_manager.is_dark_theme else "darkred"};
                font-weight: bold;
                font-size: 12pt;
                border: none;
                background: transparent;
            }}
            QPushButton:hover {{
                background: {"#444" if self.parent.theme_manager.is_dark_theme else "#ddd"};
                border-radius: 3px;
            }}
        """)
        delete_btn.setToolTip("Удалить правило")
        rule_layout.addWidget(delete_btn)
        
        rule_layout.addStretch()
        
        # Подключаем обработчики
        color_btn.clicked.connect(lambda: self._pick_rule_color(color_btn))
        delete_btn.clicked.connect(lambda: self._delete_rule_widget(rule_widget))
        
        # Сохраняем ссылки на виджеты
        rule_data = {
            'widget': rule_widget,
            'start_spinbox': start_spinbox,
            'end_spinbox': end_spinbox,
            'color_btn': color_btn
        }
        
        self.rules_container.addWidget(rule_widget)
        self.rule_widgets.append(rule_data)
        
        # Подключаем сигналы изменений
        start_spinbox.valueChanged.connect(self._update_custom_palette_params)
        end_spinbox.valueChanged.connect(self._update_custom_palette_params)
        
        # Автоматическое применение при изменении
        if self.parent.apply_palette_checkbox.isChecked():
            start_spinbox.valueChanged.connect(lambda: self.parent.apply_settings(self.parent.controls.get_config()))
            end_spinbox.valueChanged.connect(lambda: self.parent.apply_settings(self.parent.controls.get_config()))
        
        return rule_data
    
    def _delete_rule_widget(self, widget):
        """Удаление виджета правила"""
        widget.setParent(None)
        widget.deleteLater()
        
        # Удаляем из списка
        self.rule_widgets = [rw for rw in self.rule_widgets if rw['widget'] != widget]
        
        # Обновляем номера правил
        self._update_rule_numbers()
        
        # Обновляем параметры палитры
        self._update_custom_palette_params()
        
        # Автоматически применяем изменения
        if self.parent.apply_palette_checkbox.isChecked():
            self.parent.apply_settings(self.parent.controls.get_config())
    
    def _update_rule_numbers(self):
        """Обновление номеров правил"""
        for i, rule_data in enumerate(self.rule_widgets, 1):
            # Ищем метку с номером в виджете правила
            layout = rule_data['widget'].layout()
            if layout and layout.count() > 0:
                num_label = layout.itemAt(0).widget()
                if isinstance(num_label, QLabel):
                    num_label.setText(f"{i}.")
    
    def _add_empty_rule(self):
        """Добавление нового пустого правила"""
        # Находим последний использованный диапазон
        if self.rule_widgets:
            last_rule = self.rule_widgets[-1]
            last_end = last_rule['end_spinbox'].value()
            new_start = min(255, last_end + 1)
            new_end = min(255, new_start + 31)
        else:
            new_start = 0
            new_end = 31
        
        # Цвета по умолчанию по очереди
        default_colors = [
            "#FF0000", "#00FF00", "#0000FF", "#FF0080",
            "#80FF00", "#0080FF", "#FF8000", "#8000FF"
        ]
        color_index = len(self.rule_widgets) % len(default_colors)
        
        self._add_rule_widget(new_start, new_end, default_colors[color_index])
        
        # Прокручиваем к новому правилу
        self.rules_scroll.verticalScrollBar().setValue(
            self.rules_scroll.verticalScrollBar().maximum()
        )
        
        # Автоматически применяем изменения
        if self.parent.apply_palette_checkbox.isChecked():
            self.parent.apply_settings(self.parent.controls.get_config())
    
    def _reset_rules_to_default(self):
        """Сброс всех правил к значениям по умолчанию"""
        # Удаляем все текущие правила
        for rule_data in self.rule_widgets:
            rule_data['widget'].setParent(None)
            rule_data['widget'].deleteLater()
        
        self.rule_widgets.clear()
        
        # Добавляем правила по умолчанию
        default_rules = self.parent.palette_manager.DEFAULT_CUSTOM_RULES
        for rule in default_rules:
            self._add_rule_widget(
                rule.get("start", 0),
                rule.get("end", 0),
                rule.get("color", "#FF0000")
            )
        
        # Сбрасываем цвет по умолчанию
        self._update_color_button(self.default_color_btn, "#000000")
        
        # Обновляем параметры палитры
        self._update_custom_palette_params()
        
        # Автоматически применяем изменения
        if self.parent.apply_palette_checkbox.isChecked():
            self.parent.apply_settings(self.parent.controls.get_config())
    
    def _pick_default_color(self):
        """Выбор цвета по умолчанию"""
        self._pick_color_for_button(self.default_color_btn)
    
    def _pick_rule_color(self, button):
        """Выбор цвета для конкретного правила"""
        self._pick_color_for_button(button)
    
    def _pick_color_for_button(self, button):
        """Общий метод выбора цвета для кнопки"""
        current_hex = button.property("color_hex") or "#000000"
        color = QColor(current_hex)
        if not color.isValid():
            color = Qt.black
        
        dialog = QColorDialog(color, self.parent)
        dialog.setOption(QColorDialog.ShowAlphaChannel, False)
        
        if dialog.exec_() == QDialog.Accepted:
            new_color = dialog.selectedColor()
            if new_color.isValid():
                hex_new = new_color.name().lower()
                self._update_color_button(button, hex_new)
                
                # Для кнопок правил обновляем подсказку
                if button != self.default_color_btn:
                    button.setToolTip(f"Цвет: {hex_new}")
                
                # Обновляем параметры
                if self.parent.controls.get_current_palette() == "Пользовательская":
                    self._update_custom_palette_params()
                    # Автоматически применяем изменения
                    if self.parent.apply_palette_checkbox.isChecked():
                        self.parent.apply_settings(self.parent.controls.get_config())
    
    def _update_custom_palette_params(self):
        """Обновление параметров пользовательской палитры"""
        if self.parent.controls.get_current_palette() != "Пользовательская":
            return
        
        # Получаем цвет по умолчанию
        default_color = self.default_color_btn.property("color_hex") or "#000000"
        
        # Собираем правила
        rules = []
        for rule_data in self.rule_widgets:
            start = rule_data['start_spinbox'].value()
            end = rule_data['end_spinbox'].value()
            color = rule_data['color_btn'].property("color_hex") or "#000000"
            
            if start <= end:
                rules.append({
                    "start": start,
                    "end": end,
                    "color": color
                })
        
        # Обновляем параметры
        self.parent.palette_params["Пользовательская"] = {
            "default_color": default_color,
            "rules": rules
        }


class ByteInfoWidget(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.popup_checkbox = QCheckBox("Всплывающая информация о байте")
        layout.addWidget(self.popup_checkbox)
        self.label = QLabel()
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label.setStyleSheet("font-family: monospace; font-size: 9pt;")
        layout.addWidget(self.label)
        layout.addStretch()
        
        self.popup = QLabel()
        self.popup.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.popup.setAttribute(Qt.WA_ShowWithoutActivating)
        self.popup.setStyleSheet(self.parent.theme_manager.current_theme["styles"]["byte_info"])
        
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.popup.hide)
    
    def schedule_hide(self):
        self.hide_timer.start(10)
    
    def format_byte_info(self, addr, byte_val):
        lines = [f"Адрес: <b>0x{addr:08X}</b> ({addr})"]
        context_bytes = []
        for offset in range(-2, 3):  # [-2, -1, 0, +1, +2]
            pos = addr + offset
            if 0 <= pos < self.parent.file_size:
                context_bytes.append(self.parent.mmap_obj[pos])
            else:
                context_bytes.append(None)
        
        # Форматируем контекст
        context_parts = []
        for i, byte in enumerate(context_bytes):
            if i == 2:  # Текущий байт
                context_parts.append(f"<b>0x{byte_val:02X}</b>")
            elif byte is not None:
                context_parts.append(f"{byte:02X}")
            else:
                context_parts.append("---")
        
        context_str = " ".join(context_parts[:2]) + " → " + context_parts[2] + " → " + " ".join(context_parts[3:])
        lines.append(f"Hex: {context_str}")
        
        ascii_parts = []
        for byte in context_bytes:
            if byte is not None and 32 <= byte <= 126:
                ascii_parts.append(chr(byte))
            elif byte is not None:
                ascii_parts.append("")
            else:
                ascii_parts.append("")
        
        ascii_str = "".join(ascii_parts[:2]) + " → " + ascii_parts[2] + " → " + "".join(ascii_parts[3:])
        lines.append(f"ASCII: {ascii_str}")
        
        lines.append(f"Bin: <b>{byte_val:08b}</b>  Dec: <b>{byte_val}</b>")
        return "<br>".join(lines)
    
    def format_multibyte_info(self, addr, data_bytes, data_type, palette_name, params=None):
        lines = [f"Адрес: <b>0x{addr:08X}</b> ({addr})"]
        
        bytes_hex = " ".join([f"{b:02X}" for b in data_bytes])
        lines.append(f"Байты: <b>{bytes_hex}</b>")
        
        try:
            if palette_name == "RGBA":
                if len(data_bytes) >= 4:
                    r, g, b, a = data_bytes[0], data_bytes[1], data_bytes[2], data_bytes[3]
                    lines.append(f"Цвет: RGB({r}, {g}, {b}), A={a}")
                else:
                    lines.append("Недостаточно байтов для RGBA")
            
            elif palette_name == "ABGR":
                if len(data_bytes) >= 4:
                    a, b, g, r = data_bytes[0], data_bytes[1], data_bytes[2], data_bytes[3]
                    lines.append(f"Цвет: RGB({r}, {g}, {b}), A={a}")
                else:
                    lines.append("Недостаточно байтов для ABGR")
            
            elif palette_name == "RGB":
                if len(data_bytes) >= 3:
                    order = params.get("order", "RGB") if params else "RGB"
                    order_map = {'RGB': (0, 1, 2), 'GBR': (1, 2, 0), 'BRG': (2, 0, 1),
                               'BGR': (2, 1, 0), 'GRB': (1, 0, 2), 'RBG': (0, 2, 1)}
                    r_idx, g_idx, b_idx = order_map.get(order, (0, 1, 2))
                    channels = [data_bytes[0], data_bytes[1], data_bytes[2]]
                    r, g, b = channels[r_idx], channels[g_idx], channels[b_idx]
                    lines.append(f"Цвет: {order}({r}, {g}, {b})")
                else:
                    lines.append("Недостаточно байтов для RGB")
            
            elif palette_name in ["Integer 8", "Integer 16", "Integer 32", "Integer 64"]:
                data_length = {
                    "Integer 8": 1,
                    "Integer 16": 2,
                    "Integer 32": 4,
                    "Integer 64": 8
                }[palette_name]
                
                if len(data_bytes) >= data_length:
                    data_bytes_bytes = bytes(data_bytes[:data_length])
                    padded_bytes = data_bytes_bytes + bytes([0] * (data_length - len(data_bytes_bytes)))
                    
                    is_signed = params.get("signed", False) if params else False
                    endianness = params.get("endianness", "big") if params else "big"
                    
                    if palette_name == "Integer 8":
                        value = int.from_bytes(padded_bytes[:1], byteorder='big', signed=is_signed)
                        lines.append(f"8-bit {'signed' if is_signed else 'unsigned'}: {value}")
                        if is_signed:
                            lines.append(f"Диапазон: -128..127, значение: {value}")
                        else:
                            lines.append(f"Диапазон: 0..255, значение: {value}")
                    
                    elif palette_name == "Integer 16":
                        if endianness == 'big':
                            fmt = '>h' if is_signed else '>H'
                        else:
                            fmt = '<h' if is_signed else '<H'
                        try:
                            value = struct.unpack(fmt, padded_bytes[:2])[0]
                            lines.append(f"16-bit {'signed' if is_signed else 'unsigned'} ({endianness}): {value}")
                        except:
                            lines.append("Ошибка преобразования 16-bit")
                    
                    elif palette_name == "Integer 32":
                        if endianness == 'big':
                            fmt = '>i' if is_signed else '>I'
                        else:
                            fmt = '<i' if is_signed else '<I'
                        try:
                            value = struct.unpack(fmt, padded_bytes[:4])[0]
                            lines.append(f"32-bit {'signed' if is_signed else 'unsigned'} ({endianness}): {value}")
                        except:
                            lines.append("Ошибка преобразования 32-bit")
                    
                    elif palette_name == "Integer 64":
                        if endianness == 'big':
                            fmt = '>q' if is_signed else '>Q'
                        else:
                            fmt = '<q' if is_signed else '<Q'
                        try:
                            value = struct.unpack(fmt, padded_bytes[:8])[0]
                            lines.append(f"64-bit {'signed' if is_signed else 'unsigned'} ({endianness}): {value}")
                        except:
                            lines.append("Ошибка преобразования 64-bit")
                else:
                    lines.append(f"Недостаточно байтов для {palette_name}")
            
            elif palette_name in ["Float 32", "Float 64"]:
                data_length = 4 if palette_name == "Float 32" else 8
                endianness = params.get("endianness", "big") if params else "big"
                
                if len(data_bytes) >= data_length:
                    data_bytes_bytes = bytes(data_bytes[:data_length])
                    padded_bytes = data_bytes_bytes + bytes([0] * (data_length - len(data_bytes_bytes)))
                    
                    fmt = '>f' if endianness == 'big' else '<f'
                    if palette_name == "Float 64":
                        fmt = '>d' if endianness == 'big' else '<d'
                    
                    try:
                        value = struct.unpack(fmt, padded_bytes[:data_length])[0]
                        lines.append(f"{palette_name} ({endianness}): {value}")
                        if math.isnan(value):
                            lines.append("Значение: NaN")
                        elif math.isinf(value):
                            lines.append(f"Значение: {'+' if value > 0 else '-'}Infinity")
                        else:
                            lines.append(f"Научная запись: {value:e}")
                    except:
                        lines.append(f"Ошибка преобразования {palette_name}")
                else:
                    lines.append(f"Недостаточно байтов для {palette_name}")
            
            else:
                lines.append(f"Байты: {bytes_hex}")
                
        except Exception as e:
            lines.append(f"Ошибка обработки: {e}")
            import traceback
            lines.append(f"Подробности: {traceback.format_exc()}")
        
        return "<br>".join(lines)
    
    def update_info(self, addr=None):   
        if addr is None or self.parent.mmap_obj is None or not (0 <= addr < self.parent.file_size):
            self.popup.hide()
            self.label.setText("")
            return
        
        current_palette = self.parent.controls.get_current_palette() if hasattr(self.parent, 'controls') else ""
        bytes_per_pixel = self.parent.palette_manager.get_bytes_per_pixel(current_palette)
        
        try:
            data_bytes = []
            for i in range(bytes_per_pixel):
                byte_addr = addr + i
                if byte_addr < self.parent.file_size:
                    data_bytes.append(self.parent.mmap_obj[byte_addr])
                else:
                    break
            
            if not data_bytes:
                self.label.setText("Нет данных")
                return
            
            params = self.parent.palette_params.get(current_palette, {})
            
            if bytes_per_pixel > 1:
                text = self.format_multibyte_info(addr, data_bytes, "multibyte", current_palette, params)
            else:
                byte_val = data_bytes[0]
                text = self.format_byte_info(addr, byte_val)
            
            self.label.setText(text)
            
            if self.popup_checkbox.isChecked():
                self.popup.setText(text)
                self.popup.adjustSize()
            else:
                self.popup.hide()
                
        except Exception as e:
            self.label.setText(f"Ошибка: {e}")
            self.popup.hide()


class PanoramaWidget(QWidget):
    """Виджет панорамы для отображения обзора изображения и видимой области"""
    
    def __init__(self, parent):
        super().__init__()
        self.parent_ref = parent
        self.setFixedHeight(110)
        
        # Инициализация цветов из текущей темы
        self._update_colors_from_theme()
        
        # Параметры для перемещения
        self.is_dragging = False
        self.drag_start_pos = QPoint()
        self.drag_start_viewport = QPoint()
        self.viewport_rect = QRect()  # Прямоугольник видимой области в координатах виджета
        self.last_mouse_pos = QPoint(-1, -1)
        
        # Параметры масштабирования
        self.scale = 1.0
        self.x_offset = 0
        self.y_offset = 0
        self.draw_width = 0
        self.draw_height = 0
        
        # Устанавливаем курсор для интерактивности
        self.setCursor(Qt.ArrowCursor)
        self.setMouseTracking(True)
        
    def _update_colors_from_theme(self):
        """Обновление цветов из текущей темы"""
        if hasattr(self.parent_ref, 'theme_manager'):
            theme = self.parent_ref.theme_manager.get_current_theme()
            colors = theme["colors"]
            
            self.bg_color = colors["panorama_bg"]
            self.image_color = colors["panorama_image"]
            self.image_border_color = colors["panorama_image_border"]
            self.viewport_color = colors["panorama_viewport"]
            self.viewport_border_color = colors["panorama_viewport_border"]
            self.text_color = colors["window_text"]
            self.drag_hover_color = QColor(*[min(255, c + 30) for c in self.viewport_color.getRgb()[:3]] + [180])
        else:
            # Значения по умолчанию для темной темы
            self.bg_color = QColor(30, 30, 30)
            self.image_color = QColor(60, 60, 60)
            self.image_border_color = QColor(100, 100, 100)
            self.viewport_color = QColor(255, 255, 255, 180)
            self.viewport_border_color = QColor(255, 0, 0)
            self.text_color = QColor(150, 150, 150)
            self.drag_hover_color = QColor(255, 255, 255, 210)
    
    def update_theme(self):
        """Обновление цветов при смене темы"""
        self._update_colors_from_theme()
        self.update()
    
    def _calculate_viewport_rect(self):
        """Вычисляет прямоугольник видимой области на основе текущей прокрутки"""
        if not self.parent_ref.canvas or self.parent_ref.canvas.image_width == 0:
            return QRect()
        
        if not self.parent_ref.scroll_area:
            return QRect()
        
        # Получаем текущие параметры прокрутки
        viewport = self.parent_ref.scroll_area.viewport()
        h_bar = self.parent_ref.scroll_area.horizontalScrollBar()
        v_bar = self.parent_ref.scroll_area.verticalScrollBar()
        
        # Размеры изображения
        image_width = self.parent_ref.canvas.image_width
        image_height = self.parent_ref.canvas.image_height
        
        # Вычисляем видимую область в координатах изображения
        view_x = h_bar.value() / self.parent_ref.scale if self.parent_ref.scale > 0 else 0
        view_y = v_bar.value() / self.parent_ref.scale if self.parent_ref.scale > 0 else 0
        
        view_width = viewport.width() / self.parent_ref.scale if self.parent_ref.scale > 0 else 0
        view_height = viewport.height() / self.parent_ref.scale if self.parent_ref.scale > 0 else 0
        
        # Ограничиваем размеры видимой области
        view_width = min(view_width, image_width - view_x)
        view_height = min(view_height, image_height - view_y)
        
        # Преобразуем в координаты виджета панорамы
        view_x_scaled = self.x_offset + int(view_x * self.scale)
        view_y_scaled = self.y_offset + int(view_y * self.scale)
        view_width_scaled = max(4, int(view_width * self.scale))
        view_height_scaled = max(4, int(view_height * self.scale))
        
        return QRect(view_x_scaled, view_y_scaled, view_width_scaled, view_height_scaled)
    
    def paintEvent(self, event):
        """Отрисовка панорамы"""
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing, False)
            
            # Фон
            painter.fillRect(self.rect(), self.bg_color)
            
            # Если нет изображения - ничего не рисуем
            if not self.parent_ref.canvas or self.parent_ref.canvas.image_width == 0:
                painter.setPen(self.text_color)
                painter.drawText(self.rect(), Qt.AlignCenter, "Нет изображения")
                return
            
            # Размеры виджета панорамы
            widget_width = self.width() - 10  # с отступами
            widget_height = self.height() - 10
            
            # Размеры изображения
            image_width = self.parent_ref.canvas.image_width
            image_height = self.parent_ref.canvas.image_height
            
            if image_width == 0 or image_height == 0:
                return
            
            # Масштабируем изображение, чтобы оно вписывалось в виджет
            scale_x = widget_width / image_width
            scale_y = widget_height / image_height
            self.scale = min(scale_x, scale_y)
            
            # Вычисляем размеры прямоугольника изображения
            self.draw_width = int(image_width * self.scale)
            self.draw_height = int(image_height * self.scale)
            
            # Центрируем прямоугольник
            self.x_offset = (self.width() - self.draw_width) // 2
            self.y_offset = (self.height() - self.draw_height) // 2
            
            # Рисуем прямоугольник всего изображения
            painter.fillRect(self.x_offset, self.y_offset, self.draw_width, self.draw_height, self.image_color)
            
            # Рисуем контур изображения
            painter.setPen(self.image_border_color)
            painter.drawRect(self.x_offset, self.y_offset, self.draw_width, self.draw_height)
            
            # Получаем или вычисляем прямоугольник видимой области
            if not self.is_dragging:
                self.viewport_rect = self._calculate_viewport_rect()
            
            # Если есть прямоугольник видимой области, рисуем его
            if not self.viewport_rect.isNull():
                # Рисуем видимую область
                if self.viewport_rect.contains(self.last_mouse_pos) or self.is_dragging:
                    # Подсвечиваем при наведении или перетаскивании
                    painter.fillRect(self.viewport_rect, self.drag_hover_color)
                else:
                    painter.fillRect(self.viewport_rect, self.viewport_color)
                
                # Рисуем контур видимой области
                painter.setPen(self.viewport_border_color)
                painter.drawRect(self.viewport_rect)
                
                # Если идет перетаскивание, рисуем индикатор
                if self.is_dragging:
                    painter.setPen(QPen(QColor(255, 255, 0), 2, Qt.DashLine))
                    painter.drawRect(self.viewport_rect)
        finally:
            # ВАЖНО: Закрываем painter явно
            painter.end()
    
    def mousePressEvent(self, event):
        """Обработка нажатия мыши для начала перетаскивания"""
        if event.button() == Qt.LeftButton:
            # Вычисляем текущий прямоугольник
            current_rect = self._calculate_viewport_rect()
            
            if current_rect.contains(event.pos()):
                self.is_dragging = True
                self.drag_start_pos = event.pos()
                self.drag_start_viewport = current_rect.topLeft()
                self.viewport_rect = current_rect  # Сохраняем текущий прямоугольник
                self.setCursor(Qt.ClosedHandCursor)
                self.update()
                event.accept()
                return
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Обработка движения мыши"""
        self.last_mouse_pos = event.pos()
        
        if self.is_dragging:
            # Вычисляем смещение
            delta = event.pos() - self.drag_start_pos
            
            # Новая позиция прямоугольника
            new_x = self.drag_start_viewport.x() + delta.x()
            new_y = self.drag_start_viewport.y() + delta.y()
            
            # Ограничиваем перемещение в пределах изображения
            new_x = max(self.x_offset, min(new_x, self.x_offset + self.draw_width - self.viewport_rect.width()))
            new_y = max(self.y_offset, min(new_y, self.y_offset + self.draw_height - self.viewport_rect.height()))
            
            # Обновляем прямоугольник
            self.viewport_rect.moveTopLeft(QPoint(new_x, new_y))
            
            # Обновляем отображение
            self.update()
        else:
            # Вычисляем текущий прямоугольник
            current_rect = self._calculate_viewport_rect()
            
            # Меняем курсор при наведении на прямоугольник
            if current_rect.contains(event.pos()):
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            
            # Обновляем отображение для подсветки
            self.update()
    
    def mouseReleaseEvent(self, event):
        """Обработка отпускания мыши для завершения перетаскивания"""
        if event.button() == Qt.LeftButton and self.is_dragging:
            self.is_dragging = False
            
            # Вычисляем новую позицию прокрутки основного изображения
            if self.scale > 0:
                # Преобразуем координаты из виджета панорамы в координаты изображения
                image_x = (self.viewport_rect.x() - self.x_offset) / self.scale
                image_y = (self.viewport_rect.y() - self.y_offset) / self.scale
                
                # Преобразуем в позицию прокрутки с учетом масштаба
                scroll_x = int(image_x * self.parent_ref.scale) if self.parent_ref.scale > 0 else 0
                scroll_y = int(image_y * self.parent_ref.scale) if self.parent_ref.scale > 0 else 0
                
                # Прокручиваем основное изображение
                if self.parent_ref.scroll_area:
                    h_bar = self.parent_ref.scroll_area.horizontalScrollBar()
                    v_bar = self.parent_ref.scroll_area.verticalScrollBar()
                    
                    # Ограничиваем максимальные значения прокрутки
                    max_h = max(0, self.parent_ref.canvas.width() - self.parent_ref.scroll_area.viewport().width())
                    max_v = max(0, self.parent_ref.canvas.height() - self.parent_ref.scroll_area.viewport().height())
                    
                    h_bar.setValue(min(scroll_x, max_h))
                    v_bar.setValue(min(scroll_y, max_v))
            
            # Сбрасываем курсор
            current_rect = self._calculate_viewport_rect()
            if current_rect.contains(event.pos()):
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            
            self.update()
            event.accept()
            return
        
        super().mouseReleaseEvent(event)
    
    def leaveEvent(self, event):
        """Обработка выхода мыши из виджета"""
        self.last_mouse_pos = QPoint(-1, -1)
        self.setCursor(Qt.ArrowCursor)
        self.update()
        super().leaveEvent(event)
    
    def update_panorama(self):
        """Обновление отображения панорамы"""
        if self.is_dragging:
            self.is_dragging = False
            self.setCursor(Qt.ArrowCursor)
        if self.isVisible():
            self.update()


class ControlsPanel(QWidget):
    def __init__(self, open_cb, save_cb, load_cb, reset_cb, export_png_cb, compare_cb, toggle_theme_cb, parent):
        super().__init__()
        self.open_cb = open_cb
        self.save_cb = save_cb
        self.load_cb = load_cb
        self.reset_cb = reset_cb
        self.export_png_cb = export_png_cb
        self.compare_cb = compare_cb
        self.toggle_theme_cb = toggle_theme_cb
        self.parent_ref = parent
        self.palette_manager = PaletteManager()
        self.last_selected_palette = None
        self.init_ui()
    
    def init_ui(self):
        self.setFixedWidth(LEFT_PANEL_WIDTH)
        layout = QVBoxLayout(self)
        
        file_group = QGroupBox("Файл")
        file_layout = QVBoxLayout(file_group)
        row1_layout = QHBoxLayout()
        self.btn_open = OpenFileButton(self)
        self.btn_open._open_file_dialog = self.open_cb
        btn_compare = QPushButton("↔ Сравнить")
        btn_compare.clicked.connect(self.compare_cb)
        row1_layout.addWidget(self.btn_open)
        row1_layout.addWidget(btn_compare)
        file_layout.addLayout(row1_layout)
        row2_layout = QHBoxLayout()
        for txt, cb in [("💾 Сохр", self.save_cb), ("📥 Загр", self.load_cb), ("🖼️ В PNG", self.export_png_cb)]:
            btn = QPushButton(txt)
            btn.clicked.connect(cb)
            row2_layout.addWidget(btn)
        file_layout.addLayout(row2_layout)
        row3_layout = QHBoxLayout()
        btn_reset = QPushButton("↺ Сброс")
        btn_reset.clicked.connect(self.reset_cb)
        self.theme_btn = QPushButton("☀️ Светлая")
        self.theme_btn.clicked.connect(self.toggle_theme_cb)
        row3_layout.addWidget(btn_reset)
        row3_layout.addWidget(self.theme_btn)
        file_layout.addLayout(row3_layout)
        layout.addWidget(file_group)
        
        palettes_group = QGroupBox("Палитры")
        palettes_layout = QVBoxLayout(palettes_group)
        singlebyte_group = QGroupBox("Однобайтовые/битовые")
        singlebyte_layout = QHBoxLayout(singlebyte_group)
        self.singlebyte_combo = QComboBox()
        self.singlebyte_combo.setMaxVisibleItems(15)
        singlebyte_palettes = self.palette_manager.get_palette_names_for_group("singlebyte")
        for palette_name in singlebyte_palettes:
            self.singlebyte_combo.addItem(palette_name)
        self.singlebyte_combo.currentTextChanged.connect(self.on_singlebyte_palette_changed)
        singlebyte_layout.addWidget(self.singlebyte_combo)
        palettes_layout.addWidget(singlebyte_group)
        multibyte_group = QGroupBox("Многобайтовые")
        multibyte_layout = QHBoxLayout(multibyte_group)
        self.multibyte_combo = QComboBox()
        self.multibyte_combo.setMaxVisibleItems(25)
        multibyte_palettes = self.palette_manager.get_palette_names_for_group("multibyte")
        for palette_name in multibyte_palettes:
            self.multibyte_combo.addItem(palette_name)
        self.multibyte_combo.currentTextChanged.connect(self.on_multibyte_palette_changed)
        multibyte_layout.addWidget(self.multibyte_combo)
        palettes_layout.addWidget(multibyte_group)
        layout.addWidget(palettes_group)
        
        region_group = QGroupBox("Регион")
        region_layout = QGridLayout(region_group)
        self.end_label = QLabel("Конец:")
        self.offset_edit = QLineEdit()
        self.offset_edit.setText("0")
        self.end_edit = QLineEdit()
        self.end_edit.setText("0")
        self.reset_region_btn = QPushButton("X")
        self.reset_region_btn.setFixedWidth(SMALL_BUTTON_WIDTH)
        self.reset_region_btn.setToolTip("Сбросить регион (начало=0, конец=размер файла)")
        self.reset_region_btn.clicked.connect(self.reset_region_to_default)
        self.apply_region_btn = QPushButton("✓")
        self.apply_region_btn.setFixedWidth(SMALL_BUTTON_WIDTH)
        self.apply_region_btn.setToolTip("Применить начало и конец/длину")
        self.apply_region_btn.clicked.connect(self.apply_region)
        self.hex_mode_checkbox = QCheckBox("В hex")
        self.hex_mode_checkbox.setToolTip("Использовать шестнадцатеричный ввод")
        self.length_mode_checkbox = QCheckBox("Режим длины")
        self.length_mode_checkbox.setToolTip("Если отмечено — поле 'Конец' интерпретируется как 'Длина'")
        self.length_mode_checkbox.stateChanged.connect(self.on_length_mode_changed)
        
        region_layout.addWidget(QLabel("Начало:"), 0, 0)
        region_layout.addWidget(self.offset_edit, 0, 1)
        region_layout.addWidget(self.reset_region_btn, 0, 2)
        region_layout.addWidget(self.end_label, 1, 0)
        region_layout.addWidget(self.end_edit, 1, 1)
        region_layout.addWidget(self.apply_region_btn, 1, 2)
        region_layout.addWidget(self.length_mode_checkbox, 2, 0, 1, 2)
        region_layout.addWidget(self.hex_mode_checkbox, 2, 2, 1, 1)
        layout.addWidget(region_group)
        
        display_group = QGroupBox("Отображение")
        display_layout = QGridLayout(display_group)
        display_layout.setContentsMargins(6, 6, 6, 6)
        
        display_layout.addWidget(QLabel("Режим ширины:"), 0, 0)
        self.width_mode_combo = QComboBox()
        self.width_mode_combo.addItems(["Ручной", "Авто (1:1)", "Авто (степень 2)"])
        self.width_mode_combo.currentTextChanged.connect(self.on_width_mode_change)
        display_layout.addWidget(self.width_mode_combo, 0, 1)
        
        display_layout.addWidget(QLabel("Ширина:"), 1, 0)
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(1, 65536)
        self.width_spinbox.setValue(128)
        self.width_spinbox.valueChanged.connect(self.on_change)
        display_layout.addWidget(self.width_spinbox, 1, 1)
        
        display_layout.addWidget(QLabel("Шаг ширины:"), 2, 0)
        self.width_step_spinbox = QSpinBox()
        self.width_step_spinbox.setRange(1, 65536)
        self.width_step_spinbox.setValue(8)
        display_layout.addWidget(self.width_step_spinbox, 2, 1)
        
        def fixed_width_wheel_event(event):
            cur = self.width_spinbox.value()
            step = self.width_step_spinbox.value()
            delta = 1 if event.angleDelta().y() > 0 else -1
            new_value = max(1, ((cur // step) + delta) * step)
            self.width_spinbox.setValue(new_value)
            event.accept()
        
        self.width_spinbox.wheelEvent = fixed_width_wheel_event
        
        display_layout.addWidget(QLabel(f"Масштаб:"))
        self.scale_spinbox = QSpinBox()
        self.scale_spinbox.setRange(1, SCALE_MAX)
        self.scale_spinbox.setValue(1)
        self.scale_spinbox.valueChanged.connect(self.on_change)
        display_layout.addWidget(self.scale_spinbox)
        
        self.auto_scale_checkbox = QCheckBox("Автомасштаб")
        self.auto_scale_checkbox.stateChanged.connect(self.on_change)
        display_layout.addWidget(self.auto_scale_checkbox)
        layout.addWidget(display_group)
        layout.addStretch()
    
    def on_length_mode_changed(self, state):
        self.end_label.setText("Длина:" if state else "Конец:")
    
    def update_recent_files_menu(self):
        if hasattr(self, 'btn_open'):
            self.btn_open.update_menu()
        
    def parse_input(self, text: str) -> Optional[int]:
        if not text.strip():
            return None
        
        try:
            if self.hex_mode_checkbox.isChecked():
                return int(text, 16)
            else:
                return int(text)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", f"Некорректное значение: '{text}'")
            return None
    
    def reset_region_to_default(self):
        self.offset_edit.setText("0")
        self.end_edit.setText("0")
        self.length_mode_checkbox.setChecked(False)
        self.apply_region()
    
    def apply_region(self):
        offset_val = self.parse_input(self.offset_edit.text())
        end_or_len_val = self.parse_input(self.end_edit.text())
        if offset_val is None or end_or_len_val is None:
            return

        # Обновляем отображение в нужном формате, но НЕ меняем логику хранения
        if self.hex_mode_checkbox.isChecked():
            self.offset_edit.setText(f"{offset_val:x}")
            self.end_edit.setText(f"{end_or_len_val:x}")
        else:
            self.offset_edit.setText(str(offset_val))
            self.end_edit.setText(str(end_or_len_val))

        self.on_change()
    
    def on_width_mode_change(self, text):
        self.width_spinbox.setEnabled(text == "Ручной")
        self.on_change()
    
    def on_change(self):
        self.parent_ref.apply_settings(self.get_config())
    
    def on_singlebyte_palette_changed(self, palette_name):
        if palette_name:
            self.last_selected_palette = ("singlebyte", palette_name)
            self.multibyte_combo.setCurrentIndex(-1)
            self.parent_ref.on_palette_changed(palette_name)
            self.on_change()

    def on_multibyte_palette_changed(self, palette_name):
        if palette_name:
            self.last_selected_palette = ("multibyte", palette_name)
            self.singlebyte_combo.setCurrentIndex(-1)
            self.parent_ref.on_palette_changed(palette_name)
            self.on_change()
    
    def get_current_palette(self):
        if self.last_selected_palette is None:
            return self.singlebyte_combo.itemText(0)
        _, palette_name = self.last_selected_palette
        return palette_name
    
    def set_config(self, cfg):
        self.blockSignals(True)
        
        palette_name = cfg.get("palette", "Оттенки серого")
        singlebyte_palettes = self.palette_manager.get_palette_names_for_group("singlebyte")
        multibyte_palettes = self.palette_manager.get_palette_names_for_group("multibyte")

        if palette_name in singlebyte_palettes:
            self.singlebyte_combo.setCurrentText(palette_name)
            self.multibyte_combo.setCurrentIndex(-1)
            self.last_selected_palette = ("singlebyte", palette_name)
        elif palette_name in multibyte_palettes:
            self.multibyte_combo.setCurrentText(palette_name)
            self.singlebyte_combo.setCurrentIndex(-1)
            self.last_selected_palette = ("multibyte", palette_name)
        else:
            default_palette = singlebyte_palettes[0]
            self.singlebyte_combo.setCurrentText(default_palette)
            self.multibyte_combo.setCurrentIndex(-1)
            self.last_selected_palette = ("singlebyte", default_palette)
        
        self.scale_spinbox.setValue(cfg.get("scale", 1))
        self.auto_scale_checkbox.setChecked(cfg.get("auto_scale", False))
        
        wm = cfg.get("width_mode", "fixed")
        wm_map = {"fixed": "Ручной", "auto": "Авто (1:1)", "power": "Авто (степень 2)"}
        self.width_mode_combo.setCurrentText(wm_map.get(wm, "Ручной"))
        
        self.width_spinbox.setValue(cfg.get("fixed_width", 128))
        self.width_step_spinbox.setValue(cfg.get("width_step", 8))
        
        offset_val = cfg.get("offset", 0)
        length_val = cfg.get("length", 0)
        length_mode = cfg.get("length_mode", False)
        
        self.length_mode_checkbox.setChecked(length_mode)
        self.end_label.setText("Длина:" if length_mode else "Конец:")
        
        # Восстанавливаем значение в поле end_edit
        if length_mode:
            display_val = length_val
        else:
            display_val = offset_val + length_val

        if self.hex_mode_checkbox.isChecked():
            self.offset_edit.setText(f"{offset_val:x}")
            self.end_edit.setText(f"{display_val:x}")
        else:
            self.offset_edit.setText(str(offset_val))
            self.end_edit.setText(str(display_val))
        
        self.parent_ref.palette_params = cfg.get("palette_params", {})
        
        self.blockSignals(False)
        self.on_change()
    
    def get_config(self):
        wm_text = self.width_mode_combo.currentText()
        wm_map = {"Ручной": "fixed", "Авто (1:1)": "auto", "Авто (степень 2)": "power"}
        wm = wm_map.get(wm_text, "fixed")
        
        offset = self.parse_input(self.offset_edit.text()) or 0
        end_or_len = self.parse_input(self.end_edit.text()) or 0
        length_mode = self.length_mode_checkbox.isChecked()
        
        if length_mode:
            length = end_or_len
        else:
            length = max(0, end_or_len - offset)
        
        return {
            "palette": self.get_current_palette(),
            "palette_params": self.parent_ref.palette_params,
            "scale": self.scale_spinbox.value(),
            "auto_scale": self.auto_scale_checkbox.isChecked(),
            "width_mode": wm,
            "fixed_width": self.width_spinbox.value(),
            "width_step": self.width_step_spinbox.value(),
            "offset": offset,
            "length": length,
            "length_mode": length_mode,
            "mirror_horizontal": self.parent_ref.mirror_horizontal,
            "mirror_vertical": self.parent_ref.mirror_vertical,
        }
    
    def update_theme_button(self, is_dark_theme):
        self.theme_btn.setText("☀️ Светлая" if is_dark_theme else "🌙 Тёмная")


class OpenFileButton(QPushButton):
    """Кастомная кнопка открытия файла с меню последних файлов"""
    
    def __init__(self, parent=None):
        super().__init__("📂 Открыть", parent)
        self.parent_ref = parent
        self.setCursor(Qt.PointingHandCursor)
        
        # Создаем выпадающее меню
        self.menu = QMenu(self)
        
        # Подключаем обработчик закрытия меню
        self.menu.aboutToHide.connect(self._on_menu_hidden)
    
    def mousePressEvent(self, event):
        """Обработка нажатия на кнопку"""
        if event.button() == Qt.LeftButton:
            recent_files = self._get_recent_files()
            
            if recent_files:
                # Если есть последние файлы, показываем/скрываем меню
                if not self.menu.isVisible():
                    # Обновляем содержимое меню
                    self.update_menu()
                    # Показываем меню под кнопкой
                    pos = self.mapToGlobal(QPoint(0, self.height()))
                    self.menu.popup(pos)
                else:
                    self.menu.close()
            else:
                # Если нет последних файлов, сразу открываем диалог
                self._open_file_dialog()
    
    def _on_menu_hidden(self):
        """Обработчик скрытия меню"""
        # Может быть полезно для дополнительных действий при закрытии меню
        pass
    
    def update_menu(self):
        """Обновление меню последних файлов"""
        self.menu.clear()
        
        recent_files = self._get_recent_files()
        
        if not recent_files:
            return
        
        open_new_action = QAction("📂 Открыть другой файл...", self.menu)
        open_new_action.triggered.connect(self._open_file_dialog)
        self.menu.addAction(open_new_action)
        self.menu.addSeparator()
        close_action = QAction("❌ Закрыть текущий файл", self.menu)
        close_action.triggered.connect(self._close_current_file)
        self.menu.addAction(close_action)
        self.menu.addSeparator()
        
        for i, file_path in enumerate(recent_files[:8]):
            try:
                path = Path(file_path)
                if path.exists():
                    display_name = f"{i+1}. {path.name}"
                    if len(display_name) > 25:
                        display_name = display_name[:22] + "..."
                    action = QAction(display_name, self.menu)
                    action.setToolTip(str(path))
                    action.triggered.connect(
                        lambda checked, p=str(path): self._open_recent_file(p)
                    )
                    self.menu.addAction(action)
            except:
                continue
        self.menu.addSeparator()
        clear_action = QAction("🗑️ Очистить список", self.menu)
        clear_action.triggered.connect(self._clear_recent_files)
        self.menu.addAction(clear_action)
    
    def _get_recent_files(self):
        """Получение списка последних файлов из главного окна"""
        if self.parent_ref and hasattr(self.parent_ref, 'parent_ref'):
            parent_window = self.parent_ref.parent_ref
            if hasattr(parent_window, 'recent_files'):
                return parent_window.recent_files
        return []
    
    def _open_recent_file(self, file_path):
        """Открытие выбранного файла из меню"""
        try:
            if self.parent_ref and hasattr(self.parent_ref, 'parent_ref'):
                parent_window = self.parent_ref.parent_ref
                
                if Path(file_path).exists():
                    parent_window.load_file_or_compare([file_path])
                else:
                    # Удаляем несуществующий файл из списка
                    if hasattr(parent_window, 'recent_files'):
                        parent_window.recent_files = [f for f in parent_window.recent_files if f != file_path]
                        parent_window._save_window_settings()
                        self.update_menu()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл:\n{e}")
    
    def _open_file_dialog(self):
        """Открытие диалогового окна выбора файла"""
        if self.parent_ref and hasattr(self.parent_ref, 'parent_ref'):
            self.parent_ref.parent_ref.open_file()
    
    def _clear_recent_files(self):
        """Очистка списка последних файлов"""
        if self.parent_ref and hasattr(self.parent_ref, 'parent_ref'):
            self.parent_ref.parent_ref.clear_recent_files()
    
    def _close_current_file(self):
        """Закрытие текущего файла и возврат к демо-данным"""
        if self.parent_ref and hasattr(self.parent_ref, 'parent_ref'):
            parent_window = self.parent_ref.parent_ref
            if hasattr(parent_window, 'close_current_file'):
                parent_window.close_current_file()


class Visualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self._initialize_demo_data()
        self._initialize_variables()
        self.mirror_horizontal = False
        self.mirror_vertical = False
        self.setWindowTitle(MAIN_TITLE)
        
        self.theme_manager = ThemeManager()
        self.palette_manager = PaletteManager()
        self.palette_settings_manager = PaletteSettingsManager(self)
        self.window_settings_manager = WindowSettingsManager()
        
        self.recent_files = []
        self.last_directory = None
        
        self._load_window_settings()
        self.theme_manager.apply_theme(QApplication.instance(), self)
        self._setup_ui()
        self._setup_shortcuts()
        
        QTimer.singleShot(0, self.apply_default_config)
        self.setAcceptDrops(True)
        QTimer.singleShot(0, lambda: QApplication.restoreOverrideCursor())

    def _initialize_demo_data(self):
        # --- ПАТТЕРН 1: Фиксированная синусоидальная сетка ---
        def pattern1():
            X, Y = np.meshgrid(np.arange(256), np.arange(256))
            pattern = 256 + 255 * np.sin(X / 12) * np.cos(Y / 8)
            return pattern.astype(np.uint8).tobytes()

        # --- ПАТТЕРН 2: Шум ---
        def pattern2():
            h, w = 256, 256
            pattern = np.zeros((h, w), dtype=np.uint8)
            for y in range(h):
                for x in range(w):
                    pattern[y, x] = (x ^ y) % 256
            return pattern.tobytes()

        # --- ПАТТЕРН 3: как бинарный файл ---
        def pattern3():
            h, w = 256, 256
            pattern = np.full((h, w), 150, dtype=np.uint8)
            pattern[0:10, :] = 0
            pattern[2:8, 10:16] = 255
            pattern[2:8, 20:26] = 255
            pattern[2:8, 30:36] = 255
            for i in range(20, 240, 40):
                pattern[i:i+20, 0:20] = 255
                pattern[i+20:i+40, 0:20] = 50
            for y in range(20, 100, 20):
                for x in range(180, 256, 20):
                    if ((x+y)//20) % 2 == 0:
                        pattern[y:y+10, x:x+10] = 255
                    else:
                        pattern[y:y+10, x:x+10] = 0
            for x in range(80, 180, 10):
                if (x//10) % 2 == 0:
                    pattern[100:180, x:x+5] = 200
                else:
                    pattern[100:180, x:x+5] = 80
            pattern[180:256, 180:256] = 30
            for y in range(180, 256, 16):
                for x in range(180, 256, 16):
                    pattern[y:y+8, x:x+8] = 180
            pattern[246:256, :] = 0
            for x in range(0, 256, 40):
                pattern[248:252, x:x+4] = 255
            return pattern.tobytes()

        generators = [pattern1, pattern2, pattern3]
        current_time_struct = time.localtime()
        chosen = generators[current_time_struct.tm_sec % 3]
        demo_bytes = chosen()

        self.mmap_obj = BytesView(demo_bytes)
        self.file_size = len(demo_bytes)
        self.file_path = None
    
    def _initialize_variables(self):
        self.offset = 0
        self.length = 0
        self.byte_freq = [1] * 256
        self.repeats_set = set()
        self.scale = 1
        self.auto_scale = False
        self.width_mode = "auto"
        self.fixed_width = 128
        self.width_step = 8
        self.current_palette = None
        self.hover_addr = None
        self.palette_params = {}
        self.palette_cache = {}
        self.mirror_horizontal = False
        self.mirror_vertical = False
        self.render_in_progress = 0
        self.perf_debounce_timer = QTimer()
        self.perf_debounce_timer.setSingleShot(True)
        self.perf_debounce_timer.timeout.connect(self._apply_perf_settings)
        self.pending_perf_value = None
        self.tile_size = 448
        self.tile_prefetch_margin = 3
        self.max_cache_bytes = 1048576000
        self.perf_slider_value = 4
        
    def _load_window_settings(self):
        settings = self.window_settings_manager.load_settings()
        
        if settings.get("theme") == "light" and self.theme_manager.is_dark_theme:
            self.theme_manager.toggle_theme()
        
        if geometry := settings.get("window_geometry"):
            screen = QApplication.primaryScreen().availableGeometry()
            
            x = max(0, geometry.get("x", 5))
            y = max(34, geometry.get("y", 5))
            width = geometry.get("width", 1200)
            height = geometry.get("height", 700)
            
            if x + width > screen.width():
                x = max(0, screen.width() - width)
            if y + height > screen.height():
                y = max(0, screen.height() - height)
                
            self.setGeometry(x, y, width, height)
        else:
            self.resize(1200, 700)
        
        self.recent_files = settings.get("recent_files", [])
        
        if last_dir := settings.get("last_directory"):
            try:
                if (path := Path(last_dir)).exists():
                    self.last_directory = path
            except:
                self.last_directory = None
        
        self.perf_slider_value = settings.get("perf_slider_value", 4)
        
        if settings.get("is_maximized", False):
            QTimer.singleShot(100, self.showMaximized)
        
        self._apply_perf_settings()
    
    def _save_window_settings(self):
        self.window_settings_manager.save_settings(self)

    def closeEvent(self, event):
        if hasattr(self, 'mmap_obj') and self.mmap_obj:
            try:
                if hasattr(self.mmap_obj, 'close'):
                    self.mmap_obj.close()
            except:
                pass
        self._save_window_settings()
        event.accept()
        
    def resizeEvent(self, event):
        """Обработчик изменения размера окна"""
        super().resizeEvent(event)
        if hasattr(self, 'panorama_widget'):
            self.panorama_widget.update_panorama()
        
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 2, 2, 0)
        
        layout.addWidget(self._create_left_panel())
        layout.addWidget(self._create_center_panel(), 4)
        layout.addWidget(self._create_right_panel())
        
        self.perf_slider.setValue(self.perf_slider_value)
        self._update_performance_from_slider(self.perf_slider_value)
    
    def _create_left_panel(self):
        left_panel = QWidget()
        left_panel.setFixedWidth(LEFT_PANEL_WIDTH)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        
        self.controls = ControlsPanel(
            self.open_file, self.save_config, self.load_config, self.reset_config,
            self.export_png, self.compare_files, self.toggle_theme, self)
        left_layout.addWidget(self.controls)
        return left_panel
    
    def _create_center_panel(self):
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        
        self.canvas = CanvasWidget(self)
        self.scroll_area.setWidget(self.canvas)
        
        # Подключаем сигналы прокрутки для обновления панорамы
        h_bar = self.scroll_area.horizontalScrollBar()
        v_bar = self.scroll_area.verticalScrollBar()
        h_bar.valueChanged.connect(self._on_scroll_changed)
        v_bar.valueChanged.connect(self._on_scroll_changed)
        
        self.hint_container = self._create_hint_container()
        
        canvas_wrapper = QWidget()
        wrapper_layout = QVBoxLayout(canvas_wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(self.scroll_area, 1)
        wrapper_layout.addWidget(self.hint_container, 0)
        return canvas_wrapper
    
    def _create_hint_container(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.hint_label = QLabel(self._get_hint_text())
        self.hint_label.setStyleSheet(self.theme_manager.current_theme["styles"]["hint"])
        self.hint_label.setWordWrap(True)
        self.hint_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        layout.addWidget(self.hint_label)
        layout.addStretch()
        
        return container
    
    def _get_hint_text(self):
        return (
            "<b>БАЙТ-О-СКОП - Визуализатор файлов</b><br><br>"
            "<b>Основное:</b><br>"
            "• Преобразует байты файлов в изображение<br>"
            "• Множество режимов отображения<br>"
            "• Работа с файлами любого размера<br><br>"
            
            "<b>Управление:</b><br>"
            "• ЛКМ/ПКМ — навигация<br>"
            "• Колесо мыши — масштаб<br>"
            "• Ctrl+колесо — ширина<br><br>"
            
            "<b>Возможности:</b><br>"
            "• Анализ скрытых структур<br>"
            "• Сравнение файлов<br>"
            "• Экспорт изображений<br>"
            "• Сохранение настроек<br><br>"
            
            "<b>Подсказки:</b><br>"
            "• Данные о байте справа<br>"
            "• Панорама для навигации<br>"
            "• Настройки палитр справа"
        )
    
    def _create_right_panel(self):
        right_panel = QWidget()
        right_panel.setFixedWidth(RIGHT_PANEL_WIDTH)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 2, 0)
        right_layout.setSpacing(6)
        
        self.byte_info = ByteInfoWidget(self)
        right_layout.addWidget(self.byte_info, alignment=Qt.AlignTop)

        mirror_group = QGroupBox("Зеркальное отражение")
        mirror_layout = QVBoxLayout(mirror_group)
        
        self.mirror_horizontal_checkbox = QCheckBox("Отразить по горизонтали")
        self.mirror_horizontal_checkbox.stateChanged.connect(self.on_mirror_changed)
        mirror_layout.addWidget(self.mirror_horizontal_checkbox)
        
        self.mirror_vertical_checkbox = QCheckBox("Отразить по вертикали")
        self.mirror_vertical_checkbox.stateChanged.connect(self.on_mirror_changed)
        mirror_layout.addWidget(self.mirror_vertical_checkbox)
        
        reset_mirror_btn = QPushButton("Сбросить отражения")
        reset_mirror_btn.clicked.connect(self.reset_mirror)
        mirror_layout.addWidget(reset_mirror_btn)
        
        right_layout.addWidget(mirror_group)

        self.palette_settings_area = QScrollArea()
        self.palette_settings_area.setWidgetResizable(True)
        self.palette_settings_area.setFixedHeight(PALETTE_SETTINGS_HEIGHT)
        self.palette_settings_area.setVisible(False)
        self.palette_settings_area.setFrameShape(QFrame.NoFrame)
        
        self.palette_settings_widget = QWidget()
        self.palette_settings_layout = QVBoxLayout(self.palette_settings_widget)
        self.palette_settings_layout.setContentsMargins(6, 6, 6, 6)
        self.palette_settings_layout.setSpacing(4)
        self.palette_settings_area.setWidget(self.palette_settings_widget)
        right_layout.addWidget(self.palette_settings_area, alignment=Qt.AlignTop)

        palette_btns_layout = QHBoxLayout()
        palette_btns_layout.setContentsMargins(0, 0, 0, 0)
        self.reset_palette_btn = QPushButton("X")
        self.reset_palette_btn.setFixedWidth(SMALL_BUTTON_WIDTH)
        self.reset_palette_btn.setToolTip("Сбросить настройки текущей палитры")
        self.reset_palette_btn.clicked.connect(self.reset_palette_params)
        
        self.apply_palette_checkbox = QCheckBox("Автоприменять настройки")
        self.apply_palette_checkbox.setChecked(True)
        self.apply_palette_checkbox.stateChanged.connect(self.on_palette_settings_changed)
        
        palette_btns_layout.addWidget(self.reset_palette_btn)
        palette_btns_layout.addWidget(self.apply_palette_checkbox)
        palette_btns_layout.addStretch()
        right_layout.addLayout(palette_btns_layout, stretch=0)
        right_layout.setAlignment(Qt.AlignTop)
        panorama_group = QGroupBox("Панорама")
        panorama_layout = QVBoxLayout(panorama_group)
        self.panorama_widget = PanoramaWidget(self)
        panorama_layout.addWidget(self.panorama_widget)
        right_layout.addWidget(panorama_group)
        perf_group = QGroupBox("Производительность")
        perf_layout = QVBoxLayout(perf_group)
        self.memory_label = QLabel("Выделенная память: — МБ")
        perf_layout.addWidget(self.memory_label)
        slider_layout = QHBoxLayout()
        minus_label = QLabel("0.2 Гб")
        minus_label.setAlignment(Qt.AlignRight)
        slider_layout.addWidget(minus_label)

        self.perf_slider = QSlider(Qt.Horizontal)
        self.perf_slider.setRange(1, 20)
        self.perf_slider.setValue(10)
        self.perf_slider.valueChanged.connect(self._on_perf_slider_moved)
        slider_layout.addWidget(self.perf_slider)

        plus_label = QLabel("4 Гб")
        plus_label.setAlignment(Qt.AlignLeft)
        slider_layout.addWidget(plus_label)

        perf_layout.addLayout(slider_layout)
        
        self.busy_label = QLabel("")
        self.busy_label.setFixedHeight(20)
        self.busy_label.setStyleSheet("font-weight: bold; font-size: 9pt;")
        self.busy_label.setAlignment(Qt.AlignCenter)
        perf_layout.addWidget(self.busy_label)

        right_layout.addWidget(perf_group, alignment=Qt.AlignBottom)

        return right_panel
    
    def _on_scroll_changed(self, value):
        """Обработчик изменения прокрутки"""
        if hasattr(self, 'panorama_widget'):
            # Обновляем панораму только если не идет перетаскивание
            if not self.panorama_widget.is_dragging:
                self.panorama_widget.update_panorama()
    
    def _setup_shortcuts(self):
        from PyQt5.QtWidgets import QShortcut
        QShortcut(QKeySequence("Ctrl+O"), self, self.open_file)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_config)
        QShortcut(QKeySequence("Ctrl+L"), self, self.load_config)
        QShortcut(QKeySequence("Ctrl+R"), self, self.reset_config)
        QShortcut(QKeySequence("Ctrl+E"), self, self.export_png)
        QShortcut(QKeySequence("Ctrl+X"), self, self.compare_files)
    
    def toggle_theme(self):
        self.theme_manager.toggle_theme()
        theme = self.theme_manager.apply_theme(QApplication.instance(), self)
        
        if hasattr(self, 'controls'):
            self.controls.update_theme_button(self.theme_manager.is_dark_theme)
        
        if hasattr(self, 'canvas'):
            canvas_color = theme["colors"]["widget_background"]
            self.canvas.setAutoFillBackground(True)
            palette = self.canvas.palette()
            palette.setColor(self.canvas.backgroundRole(), canvas_color)
            self.canvas.setPalette(palette)
            self.canvas.update()
        if hasattr(self, 'panorama_widget'):
            self.panorama_widget.update_theme()
        current_palette = self.controls.get_current_palette() if hasattr(self, 'controls') else ""
        if current_palette and self.palette_settings_area.isVisible():
            self.palette_settings_manager.build_palette_settings_ui(current_palette)
        
        if hasattr(self, 'byte_info'):
            self.byte_info.popup.setStyleSheet(self.theme_manager.current_theme["styles"]["byte_info"])
        
        if hasattr(self, 'hint_label'):
            self.hint_label.setStyleSheet(self.theme_manager.current_theme["styles"]["hint"])
        
        if hasattr(self, 'scroll_area'):
            scroll_color = theme["colors"]["scroll_area_background"]
            self.scroll_area.setAutoFillBackground(True)
            palette = self.scroll_area.palette()
            palette.setColor(self.scroll_area.backgroundRole(), scroll_color)
            self.scroll_area.setPalette(palette)
            self.scroll_area.viewport().setAutoFillBackground(True)
            palette = self.scroll_area.viewport().palette()
            palette.setColor(self.scroll_area.viewport().backgroundRole(), scroll_color)
            self.scroll_area.viewport().setPalette(palette)
        
        if hasattr(self, 'hint_container'):
            hint_color = theme["colors"]["widget_background"]
            self.hint_container.setAutoFillBackground(True)
            palette = self.hint_container.palette()
            palette.setColor(self.hint_container.backgroundRole(), hint_color)
            self.hint_container.setPalette(palette)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        urls = event.mimeData().urls()
        local_paths = [url.toLocalFile() for url in urls if url.isLocalFile()]
        
        if local_paths:
            self.load_file_or_compare(local_paths)
        
        event.acceptProposedAction()
    
    def _load_single_file(self, path):
        self.file_path = Path(path)
        with open(path, "rb") as f:
            self.file_size = f.seek(0, 2)
            self.mmap_obj = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        
        self.offset = 0
        self.length = 0
        
        return self.file_path.with_suffix(self.file_path.suffix + ".b-o-s")
    
    def _load_and_compare_files(self, path1, path2):
        with open(path1, 'rb') as f1, open(path2, 'rb') as f2:
            data1 = f1.read()
            data2 = f2.read()
        
        diff = bytearray(a ^ b for a, b in zip(data1, data2))
        self.file_path = Path(f"[XOR] {Path(path1).name} ^ {Path(path2).name}")
        self.file_size = len(diff)
        self.mmap_obj = BytesView(bytes(diff))
        
        self.offset = 0
        self.length = 0
        
        for p in [path1, path2]:
            viz_path = Path(p).with_suffix(Path(p).suffix + ".b-o-s")
            if viz_path.exists():
                try:
                    with open(viz_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception:
                    continue
        
        return None
    
    def load_file_or_compare(self, paths: list[str]):
        if not paths:
            return
        
        try:
            self.hint_container.setVisible(False)
            
            if len(paths) == 1:
                viz_path = self._load_single_file(paths[0])
                cfg = self._try_load_config(viz_path)
                self._add_recent_file(paths[0])
            else:
                cfg = self._load_and_compare_files(paths[0], paths[1])
            
            self.analyze_file()
            self._apply_configuration(cfg)
            self._update_interface()
            
        except Exception as e:
            self._handle_file_load_error(e, len(paths))
    
    def _try_load_config(self, config_path):
        if config_path.exists():
            try:
                with open(config_path) as f_cfg:
                    return json.load(f_cfg)
            except Exception:
                pass
        return None
    
    def _apply_configuration(self, cfg):
        if cfg is not None and self.controls:
            self.controls.set_config(cfg)
            self.apply_settings(cfg)
        else:
            self.apply_default_config()
    
    def _update_interface(self):
        if self.canvas:
            self.canvas.update_image()
        if hasattr(self, 'panorama_widget'):
            self.panorama_widget.update_panorama()
        self.update_window_title()
    
    def _handle_file_load_error(self, error, num_files):
        action = "открыть файл" if num_files == 1 else "сравнить файлы"
        QMessageBox.critical(self, "Ошибка", f"Не удалось {action}:\n{error}")
    
    def _start_render(self):
        """Начало операции рендеринга"""
        self.render_in_progress += 1
        if self.render_in_progress == 1:  # Первая операция
            if hasattr(self, 'byte_info'):
                self.set_busy(1)
            # Также можно показать индикатор в заголовке окна
            QApplication.setOverrideCursor(Qt.WaitCursor)
    
    def _end_render(self):
        """Завершение операции рендеринга"""
        self.render_in_progress = max(0, self.render_in_progress - 1)
        if self.render_in_progress == 0:
            if hasattr(self, 'byte_info'):
                self.set_busy(0)
            QApplication.restoreOverrideCursor()

            # === Обновляем память ===
            if hasattr(self, 'memory_label'):
                try:
                    process = psutil.Process()
                    mem_mb = process.memory_info().rss / (1024 * 1024)
                    self.memory_label.setText(f"Выделенная память: {mem_mb:.0f} МБ")
                except ImportError:
                    self.memory_label.setText("Выделенная память: --- МБ")
    
    def analyze_file(self):
        all_data = self._get_all_data()
        
        if len(all_data) <= 10_000_000:
            self.repeats_set = self._find_repeated_patterns(all_data)
            self.byte_freq = [0] * 256
            for b in all_data:
                self.byte_freq[b] += 1
        else:
            self.repeats_set = set()
            self.byte_freq = [1] * 256
    
    def _find_repeated_patterns(self, data, window_size=4):
        seen = {}
        repeats = set()
        
        for i in range(len(data) - window_size + 1):
            chunk = tuple(data[i:i + window_size])
            if chunk in seen:
                repeats.update(chunk)
            else:
                seen[chunk] = i
        
        return repeats
    
    def export_png(self):
        if not self._can_export():
            return
        
        default_name = self._get_default_export_name()
        save_path = self._get_save_path(default_name)
        
        if not save_path:
            return
        
        if not save_path.lower().endswith(".png"):
            save_path += ".png"
        
        self._save_png_image(save_path)
    
    def _can_export(self):
        return (self.mmap_obj is not None and 
                self.file_size > 0 and 
                self.canvas and 
                hasattr(self.canvas, 'tile_manager'))
    
    def _get_default_export_name(self):
        if self.file_path:
            return self.file_path.with_suffix(".png").name
        return "output.png"
    
    def _get_save_path(self, default_name):
        base_path = str(self.file_path.parent / default_name) if self.file_path else ""
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить PNG", base_path, "PNG файлы (*.png)")
        return path
    
    def _save_png_image(self, path):
        """Сохранение изображения в PNG БЕЗ сглаживания"""
        if not hasattr(self, 'canvas') or not self.canvas:
            QMessageBox.warning(self, "Ошибка", "Нет изображения для экспорта.")
            return
        
        # Создаем полное изображение для экспорта
        offset, length, actual_len = self._get_data_region_for_export()
        if actual_len <= 0:
            QMessageBox.warning(self, "Ошибка", "Нет данных для экспорта.")
            return

        self.set_busy(2)
        
        # Получаем параметры
        bytes_per_pixel = self.get_bytes_per_pixel()
        image_width = self._calculate_image_width_for_export(actual_len, bytes_per_pixel)
        image_height = self._calculate_image_height_for_export(actual_len, image_width, bytes_per_pixel)
        
        # Создаем полное изображение
        data_slice = self.mmap_obj[offset:offset + actual_len]
        full_image = self._render_full_image(data_slice, image_width, image_height, bytes_per_pixel)
        
        if full_image:
            # Сохраняем БЕЗ сглаживания
            success = full_image.save(path, "PNG", 100)
            if not success:
                QMessageBox.warning(self, "Ошибка", "Не удалось сохранить изображение.")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось создать изображение для экспорта.")
        
        self.set_busy(0)
    
    def _get_data_region_for_export(self):
        offset = self.offset
        length = self.length or self.file_size
        end = min(offset + length, self.file_size)
        actual_len = end - offset
        return offset, length, actual_len
    
    def _calculate_image_width_for_export(self, data_len, bytes_per_pixel):
        pixels_count = data_len // bytes_per_pixel
        
        if self.width_mode == "fixed":
            return self.fixed_width
        elif self.width_mode == "auto":
            return int(math.sqrt(pixels_count)) or 1
        else:
            return self._calculate_power_of_two_width(pixels_count)
    
    def _calculate_image_height_for_export(self, data_len, width, bytes_per_pixel):
        pixels_count = data_len // bytes_per_pixel
        return (pixels_count + width - 1) // width
    
    def _render_full_image(self, data_slice, width, height, bytes_per_pixel):
        """Рендеринг полного изображения для экспорта PNG - оптимизированная версия"""
        current_palette = self.controls.get_current_palette()
        params = self.palette_params.get(
            current_palette,
            self.palette_manager.get_default_params(current_palette)
        )
        
        # Используем ARGB32 формат для экспорта
        arr = np.zeros((height, width), dtype=np.uint32)
        pixels_count = len(data_slice) // bytes_per_pixel
        max_pixels = min(pixels_count, width * height)
        
        # Предварительно вычисляем палитру для быстрого доступа
        palette = self.current_palette
        if palette is not None:
            # Создаем lookup table для палитры
            palette_argb = np.zeros(256, dtype=np.uint32)
            for i, (r, g, b) in enumerate(palette):
                palette_argb[i] = (0xFF << 24) | (r << 16) | (g << 8) | b
        
        for pixel_idx in range(max_pixels):
            byte_idx = pixel_idx * bytes_per_pixel
            y = pixel_idx // width
            x = pixel_idx % width
            
            if y < height and x < width:
                pixel_data = data_slice[byte_idx:byte_idx + bytes_per_pixel]
                
                if current_palette in ["RGBA", "ABGR", "RGB"]:
                    argb_color = self._get_pixel_color_argb_for_export(pixel_data, current_palette, params)
                    arr[y, x] = argb_color
                elif current_palette in ["Integer 8", "Integer 16", "Integer 32", "Integer 64",
                                       "Float 32", "Float 64"]:
                    intensity = self._get_intensity_from_bytes(pixel_data, current_palette, params)
                    argb_color = (0xFF << 24) | (intensity << 16) | (intensity << 8) | intensity
                    arr[y, x] = argb_color
                else:
                    if len(pixel_data) > 0:
                        byte_val = pixel_data[0]
                        if palette is not None:
                            arr[y, x] = palette_argb[byte_val]
                        else:
                            intensity = byte_val
                            argb_color = (0xFF << 24) | (intensity << 16) | (intensity << 8) | intensity
                            arr[y, x] = argb_color
        
        # Применяем зеркальные отражения
        if self.mirror_horizontal:
            arr = np.fliplr(arr)
        if self.mirror_vertical:
            arr = np.flipud(arr)
        
        # Создаем QImage в формате ARGB32
        if arr.size > 0:
            height, width = arr.shape
            bytes_per_line = width * 4  # 4 байта на пиксель
            
            if arr.flags['C_CONTIGUOUS']:
                data = arr.tobytes()
            else:
                data = arr.copy(order='C').tobytes()
            
            return QImage(data, width, height, bytes_per_line, QImage.Format_ARGB32)
        
        return None
    
    def _get_pixel_color_argb_for_export(self, pixel_data, palette_name, params):
        """Получение цвета в формате ARGB32 для экспорта"""
        if len(pixel_data) == 0:
            return 0xFF000000
        
        r = g = b = 0
        
        if palette_name == "RGBA":
            if len(pixel_data) >= 4:
                r, g, b = pixel_data[0], pixel_data[1], pixel_data[2]
        elif palette_name == "ABGR":
            if len(pixel_data) >= 4:
                b, g, r = pixel_data[1], pixel_data[2], pixel_data[3]
        elif palette_name == "RGB":
            if len(pixel_data) >= 3:
                order = params.get("order", "RGB")
                order_map = {'RGB': (0, 1, 2), 'GBR': (1, 2, 0), 'BRG': (2, 0, 1),
                           'BGR': (2, 1, 0), 'GRB': (1, 0, 2), 'RBG': (0, 2, 1)}
                r_idx, g_idx, b_idx = order_map.get(order, (0, 1, 2))
                channels = [pixel_data[0], pixel_data[1], pixel_data[2]]
                r, g, b = channels[r_idx], channels[g_idx], channels[b_idx]
        
        return (0xFF << 24) | (r << 16) | (g << 8) | b
    
    def _get_intensity_from_bytes(self, pixel_data, palette_name, params):
        if len(pixel_data) < len(pixel_data):
            return 0
        
        try:
            if palette_name == "Integer 8":
                is_signed = params.get("signed", False)
                if is_signed:
                    value = struct.unpack('b', bytes([pixel_data[0]]))[0]
                    return int(((value + 128) / 255.0) * 255)
                else:
                    return pixel_data[0]
            
            elif palette_name == "Integer 16":
                is_signed = params.get("signed", False)
                endianness = params.get("endianness", "big")
                if len(pixel_data) >= 2:
                    if endianness == "big":
                        fmt = '>h' if is_signed else '>H'
                    else:
                        fmt = '<h' if is_signed else '<H'
                    value = struct.unpack(fmt, pixel_data[:2])[0]
                    return self._scale_value_to_255(value, is_signed, 16)
            
            elif palette_name == "Integer 32":
                is_signed = params.get("signed", False)
                endianness = params.get("endianness", "big")
                if len(pixel_data) >= 4:
                    if endianness == "big":
                        fmt = '>i' if is_signed else '>I'
                    else:
                        fmt = '<i' if is_signed else '<I'
                    value = struct.unpack(fmt, pixel_data[:4])[0]
                    return self._scale_value_to_255(value, is_signed, 32)
            
            elif palette_name == "Integer 64":
                is_signed = params.get("signed", False)
                endianness = params.get("endianness", "big")
                if len(pixel_data) >= 8:
                    if endianness == "big":
                        fmt = '>q' if is_signed else '>Q'
                    else:
                        fmt = '<q' if is_signed else '<Q'
                    value = struct.unpack(fmt, pixel_data[:8])[0]
                    return self._scale_value_to_255(value, is_signed, 64)
            
            elif palette_name == "Float 32":
                endianness = params.get("endianness", "big")
                if len(pixel_data) >= 4:
                    fmt = '>f' if endianness == "big" else '<f'
                    value = struct.unpack(fmt, pixel_data[:4])[0]
                    return self._scale_float_to_255(value)
            
            elif palette_name == "Float 64":
                endianness = params.get("endianness", "big")
                if len(pixel_data) >= 8:
                    fmt = '>d' if endianness == "big" else '<d'
                    value = struct.unpack(fmt, pixel_data[:8])[0]
                    return self._scale_float_to_255(value)
        
        except:
            pass
        
        return 0
    
    def _scale_value_to_255(self, value, is_signed, bits):
        if is_signed:
            if bits == 16:
                min_val, max_val = -32768, 32767
            elif bits == 32:
                min_val, max_val = -2147483648, 2147483647
            elif bits == 64:
                min_val, max_val = -9223372036854775808, 9223372036854775807
        else:
            if bits == 16:
                min_val, max_val = 0, 65535
            elif bits == 32:
                min_val, max_val = 0, 4294967295
            elif bits == 64:
                min_val, max_val = 0, 18446744073709551615
        
        if max_val == min_val:
            return 0
        
        clamped_value = max(min_val, min(max_val, value))
        return int(((clamped_value - min_val) / (max_val - min_val)) * 255)
    
    def _scale_float_to_255(self, value):
        if math.isnan(value) or math.isinf(value):
            return 0
        return max(0, min(255, int(abs(value) * 255 / 1000)))
    
    def generate_palette(self, name):
        cache_key = self._get_palette_cache_key(name)
        
        if cache_key in self.palette_cache:
            return self.palette_cache[cache_key]
        
        palette = self._create_palette(name)
        self.palette_cache[cache_key] = palette
        
        return palette
    
    def _get_palette_cache_key(self, name):
        params = self.palette_params.get(name, {})
        return f"{name}_{json.dumps(params, sort_keys=True)}"
    
    def _create_palette(self, name):
        params = self.palette_params.get(name, self.palette_manager.get_default_params(name))
        file_data = None
        
        if name in ["Частота байтов", "Повторы"]:
            file_data = self._get_all_data()
        
        return self.palette_manager.create_palette(name, params, file_data)
    
    def _get_all_data(self):
        if hasattr(self.mmap_obj, '_data'):
            return self.mmap_obj._data
        return self.mmap_obj[:]
    
    def get_bytes_per_pixel(self):
        current_palette = self.controls.get_current_palette() if hasattr(self, 'controls') else ""
        return self.palette_manager.get_bytes_per_pixel(current_palette)
    
    def update_window_title(self):
        if self.file_path is None:
            self.setWindowTitle(MAIN_TITLE)
            return
        
        img_w = self._get_image_width()
        img_h = self._get_image_height()
        title = (
            f"{MAIN_TITLE}: "
            f"[{self.file_path.name}] "
            f"[0x{self.file_size:X} / {self.file_size:,} байт] "
            f"[{img_w}×{img_h}]"
        )
        
        self.setWindowTitle(title)
    
    def _get_image_width(self):
        return self.canvas.image_width if self.canvas else 0
    
    def _get_image_height(self):
        return self.canvas.image_height if self.canvas else 0
    
    def _add_recent_file(self, file_path):
        try:
            path_obj = Path(file_path)
            if not path_obj.exists():
                return
                
            try:
                canonical_path = path_obj.resolve()
            except:
                canonical_path = path_obj.absolute()
            
            abs_path_str = str(canonical_path)
            
            def normalize_path_for_comparison(path_str):
                try:
                    p = Path(path_str)
                    if not p.exists():
                        return None
                    resolved = str(p.resolve())
                    if platform.system().lower() == "windows":
                        return resolved.lower()
                    return resolved
                except:
                    return None
            
            current_normalized = normalize_path_for_comparison(abs_path_str)
            if not current_normalized:
                return
            
            new_list = []
            seen = set()
            
            new_list.append(abs_path_str)
            seen.add(current_normalized)
            
            for existing in self.recent_files:
                normalized = normalize_path_for_comparison(existing)
                if normalized and normalized != current_normalized and normalized not in seen:
                    new_list.append(existing)
                    seen.add(normalized)
            
            self.recent_files = new_list[:10]
            self.last_directory = path_obj.parent
            
            if hasattr(self, 'controls') and hasattr(self.controls, 'btn_open'):
                self.controls.btn_open.update_menu()
                
            self._save_window_settings()
                
        except Exception as e:
            print(f"Ошибка добавления файла в список: {e}")

    def clear_recent_files(self):
        self.recent_files = []
        
        if hasattr(self, 'controls') and hasattr(self.controls, 'btn_open'):
            self.controls.btn_open.update_menu()

    def showEvent(self, event):
        super().showEvent(event)
        
        if hasattr(self, 'controls') and hasattr(self.controls, 'btn_open'):
            QTimer.singleShot(100, self.controls.btn_open.update_menu)
    
    def open_file(self):
        start_dir = str(self.last_directory) if self.last_directory else ""
        
        path, _ = QFileDialog.getOpenFileName(
            self, "Открыть файл", start_dir
        )
        
        if path:
            self.last_directory = Path(path).parent
            
            if path not in self.recent_files:
                self.recent_files.insert(0, path)
                if len(self.recent_files) > 10:
                    self.recent_files = self.recent_files[:10]
            
            self._save_window_settings()
            self.load_file_or_compare([path])
    
    def compare_files(self):
        path1, _ = QFileDialog.getOpenFileName(self, "Файл 1")
        if not path1:
            return
        
        path2, _ = QFileDialog.getOpenFileName(self, "Файл 2")
        if not path2:
            return
        
        self.load_file_or_compare([path1, path2])
    
    def close_current_file(self):
        """Закрытие текущего файла и возврат к демо-данным"""
        try:
            if hasattr(self, 'mmap_obj') and self.mmap_obj:
                try:
                    if hasattr(self.mmap_obj, 'close'):
                        self.mmap_obj.close()
                except:
                    pass
            self._initialize_demo_data()
            self.file_size = len(self.mmap_obj._data) if hasattr(self.mmap_obj, '_data') else 0
            self.offset = 0
            self.length = 0
            self.current_palette = None
            self.palette_params = {}
            self.palette_cache = {}
            self.byte_freq = [1] * 256
            self.repeats_set = set()
            
            if hasattr(self, 'canvas') and self.canvas:
                if hasattr(self.canvas, 'tile_manager'):
                    self.canvas.tile_manager.clear_cache()
                self.canvas.update_image()
            if hasattr(self, 'hint_container'):
                self.hint_container.setVisible(True)
            if hasattr(self, 'byte_info'):
                self.byte_info.update_info(None)
            if hasattr(self, 'controls'):
                self.apply_default_config()
            if hasattr(self, 'controls') and hasattr(self.controls, 'btn_open'):
                self.controls.btn_open.menu.close()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось закрыть файл:\n{e}")
            
    def calculate_width(self):
        if self.mmap_obj is None:
            return 0
        
        length = self.length or self.file_size
        actual_len = min(length, self.file_size - self.offset)
        
        bytes_per_pixel = self.get_bytes_per_pixel()
        pixels_count = actual_len // bytes_per_pixel if bytes_per_pixel > 0 else 0
        
        if self.width_mode == "fixed":
            return self.fixed_width
        elif self.width_mode == "auto":
            return int(math.sqrt(pixels_count)) or 1
        else:
            return self._calculate_power_of_two_width(pixels_count)

    def _calculate_power_of_two_width(self, pixels_count, max_width=4096):
        w = 1
        while w * 2 <= pixels_count and w < max_width:
            w *= 2
        return w
    
    def apply_default_config(self):
        default_config = {
            "palette": "Тепловая",
            "palette_params": {},
            "scale": 1,
            "auto_scale": False,
            "width_mode": "auto",
            "fixed_width": 128,
            "width_step": 8,
            "offset": 0,
            "length": 0,
        }
        
        if self.controls:
            self.controls.set_config(default_config)
            self.on_palette_changed(self.controls.get_current_palette())
        
        self.hint_container.setVisible(self.file_path is None)
        self.apply_settings(default_config)
    
    def apply_settings(self, cfg):
        if self.canvas is None:
            return
        
        self._apply_basic_settings(cfg)
        
        self.mirror_horizontal = cfg.get("mirror_horizontal", False)
        self.mirror_vertical = cfg.get("mirror_vertical", False)
        
        if hasattr(self, 'mirror_horizontal_checkbox'):
            self.mirror_horizontal_checkbox.setChecked(self.mirror_horizontal)
        if hasattr(self, 'mirror_vertical_checkbox'):
            self.mirror_vertical_checkbox.setChecked(self.mirror_vertical)
        
        palette_name = cfg["palette"]
        
        is_multibyte = palette_name in [
            "RGBA", "ABGR", "RGB", 
            "Integer 8", "Integer 16", "Integer 32", "Integer 64"
        ]
        
        if not is_multibyte and palette_name in self.palette_manager.get_all_palette_names():
            self.current_palette = self.generate_palette(palette_name)
        else:
            self.current_palette = self.generate_palette("Оттенки серого")
            
            if is_multibyte and palette_name not in self.palette_params:
                default_params = self.palette_manager.get_default_params(palette_name)
                self.palette_params[palette_name] = default_params
        
        if self.auto_scale:
            self.auto_fit_scale()
        if self.canvas:
            self.canvas.update_image()
        if hasattr(self, 'panorama_widget'):
            self.panorama_widget.update_panorama()
    
    def _apply_basic_settings(self, cfg):
        self.scale = max(1, cfg["scale"])
        self.auto_scale = cfg["auto_scale"]
        self.width_mode = cfg["width_mode"]
        self.fixed_width = cfg["fixed_width"]
        self.width_step = cfg.get("width_step", 8)
        self.offset = cfg.get("offset", 0)
        self.length = cfg.get("length", 0)
    
    def auto_fit_scale(self):
        if self.mmap_obj is None or self.file_size == 0 or not self.scroll_area:
            return
        
        width = self.calculate_width()
        length = self.length or self.file_size
        actual_len = min(length, self.file_size - self.offset)
        
        bytes_per_pixel = self.get_bytes_per_pixel()
        pixels_count = actual_len // bytes_per_pixel if bytes_per_pixel > 0 else 0
        height = (pixels_count + width - 1) // width
        
        viewport = self.scroll_area.viewport()
        avail_w = viewport.width() - 20
        avail_h = viewport.height() - 20
        
        scale_w = avail_w // width if width > 0 else 1
        scale_h = avail_h // height if height > 0 else 1
        
        self.scale = max(1, min(scale_w, scale_h, SCALE_MAX))
        
        if self.controls:
            self.controls.scale_spinbox.setValue(self.scale)
    
    def save_config(self):
        if self.file_path is None or not self.file_path.exists():
            return
        
        viz_path = self.file_path.with_suffix(self.file_path.suffix + ".b-o-s")
        self._save_json_config(viz_path, self.controls.get_config())
    
    def _save_json_config(self, path, config):
        try:
            with open(path, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения конфигурации: {e}")
    
    def load_config(self):
        if self.file_path is None or not self.file_path.exists():
            return
        
        viz_path = self.file_path.with_suffix(self.file_path.suffix + ".b-o-s")
        if not viz_path.exists():
            return
        
        cfg = self._load_json_config(viz_path)
        if cfg and self.controls:
            self.controls.set_config(cfg)
            self.apply_settings(cfg)
    
    def _load_json_config(self, path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {e}")
            return None
    
    def reset_config(self):
        if self.file_path is None or not self.file_path.exists():
            return
        self.apply_default_config()

    def reset_palette_params(self):
        name = self.controls.get_current_palette()
        
        if name == "Пользовательская":
            self.palette_settings_manager._reset_rules_to_default()
        else:
            self.palette_params[name] = self.palette_manager.get_default_params(name)
            self.palette_settings_manager.build_palette_settings_ui(name)
        
        if self.apply_palette_checkbox.isChecked():
            self.apply_settings(self.controls.get_config())
    
    def update_current_palette_params(self):
        name = self.controls.get_current_palette()
        
        if name == "Полосы энтропии":
            self.palette_params[name] = {"step": self.palette_settings_manager.step_spinbox.value()}
        elif name == "Битовая плоскость":
            self.palette_params[name] = {"plane": self.palette_settings_manager.plane_spinbox.value()}
        elif name == "Порог":
            self.palette_params[name] = {"threshold": self.palette_settings_manager.threshold_spin.value()}
        elif name == "Частота байтов":
            self.palette_params[name] = {"auto": self.palette_settings_manager.auto_freq_checkbox.isChecked()}
        elif name == "Повторы":
            self.palette_params[name] = {
                "auto": self.palette_settings_manager.auto_repeats_checkbox.isChecked(),
                "min_count": self.palette_settings_manager.min_count_spin.value()}
        elif name == "RGB":
            self.palette_params[name] = {"order": self.palette_settings_manager.rgb_order_combo.currentText()}
        elif name == "Integer 8":
            self.palette_params[name] = {"signed": self.palette_settings_manager.int8_signed_checkbox.isChecked()}
        elif name == "Integer 16":
            self.palette_params[name] = {
                "endianness": self.palette_settings_manager.int16_endian_combo.currentText(),
                "signed": self.palette_settings_manager.int16_signed_checkbox.isChecked()}
        elif name == "Integer 32":
            self.palette_params[name] = {
                "endianness": self.palette_settings_manager.int32_endian_combo.currentText(),
                "signed": self.palette_settings_manager.int32_signed_checkbox.isChecked()}
        elif name == "Integer 64":
            self.palette_params[name] = {
                "endianness": self.palette_settings_manager.int64_endian_combo.currentText(),
                "signed": self.palette_settings_manager.int64_signed_checkbox.isChecked()}
        elif name == "Float 32":
            self.palette_params[name] = {"endianness": self.palette_settings_manager.float32_endian_combo.currentText()}
        elif name == "Float 64":
            self.palette_params[name] = {"endianness": self.palette_settings_manager.float64_endian_combo.currentText()}
        elif name == "Пользовательская":
            pass
        
        if self.apply_palette_checkbox.isChecked():
            self.apply_settings(self.controls.get_config())
    
    def on_palette_settings_changed(self, state):
        if self.apply_palette_checkbox.isChecked():
            self.apply_settings(self.controls.get_config())
    
    def on_palette_changed(self, palette_name):
        if palette_name not in self.palette_params:
            default_params = self.palette_manager.get_default_params(palette_name)
            self.palette_params[palette_name] = default_params
        self.palette_settings_manager.build_palette_settings_ui(palette_name)
    
    def on_mirror_changed(self, state):
        if hasattr(self, 'mirror_horizontal_checkbox'):
            self.mirror_horizontal = self.mirror_horizontal_checkbox.isChecked()
        if hasattr(self, 'mirror_vertical_checkbox'):
            self.mirror_vertical = self.mirror_vertical_checkbox.isChecked()
        
        if self.canvas:
            self.canvas.update_image()
        
        if self.hover_addr is not None:
            self.byte_info.update_info(self.hover_addr)
    
    def reset_mirror(self):
        self.mirror_horizontal = False
        self.mirror_vertical = False
        
        if hasattr(self, 'mirror_horizontal_checkbox'):
            self.mirror_horizontal_checkbox.setChecked(False)
        if hasattr(self, 'mirror_vertical_checkbox'):
            self.mirror_vertical_checkbox.setChecked(False)
        
        if self.canvas:
            self.canvas.update_image()
    
    def _on_perf_slider_moved(self, value):
        self.pending_perf_value = value
        self.perf_debounce_timer.start(1000)
    
    def _apply_perf_settings(self):
        if self.pending_perf_value is None:
            return
        self._update_performance_from_slider(self.pending_perf_value)
        self.pending_perf_value = None
        if hasattr(self, 'canvas') and self.canvas:
            self.canvas.tile_manager.clear_cache()
            self.canvas.force_redraw = True
            self.canvas.update_image()
    
    def _update_performance_from_slider(self, value: int):
        """Обновляет tile_size, margin, cache из значения слайдера"""
        self.perf_slider_value = value
        norm = (value - 1) / 19.0
        log_ts = math.log(128) + norm * (math.log(1024) - math.log(128))
        self.tile_size = max(128, min(1024, int(round(math.exp(log_ts)))))
        log_m = norm * math.log(6)  # log(1) = 0
        self.tile_prefetch_margin = max(1, min(6, int(round(math.exp(log_m)))))
        log_c = math.log(180) + norm * (math.log(4000) - math.log(180))
        cache_mb = max(180, min(4000, int(round(math.exp(log_c)))))
        self.max_cache_bytes = cache_mb * 1024 * 1024
    
    def set_busy(self, type: int):
        """Установка состояния занятости"""
        states = {
            0: "", 1: "Рендеринг", 2: "Сохранение в PNG", 3: "Что-то другое"
        }
        
        text = states.get(type, "")
        if text:
            self.busy_label.setText(f"[⏳ {text}...]")
        else:
            self.busy_label.setText("")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Visualizer()
    window.show()
    sys.exit(app.exec_())