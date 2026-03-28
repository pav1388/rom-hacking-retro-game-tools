import tkinter as tk
from tkinter import filedialog, messagebox
import os
import json

MAIN_VERSION = "0.2"
SETTING_FILE = "text-width-checker-settings.json"

class WidthCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Проверка ширины строк v" + MAIN_VERSION)
        self.root.geometry("900x500")
        
        # Словарь ширины символов
        self.width_dict = {}
        self.current_dict_file = "widths.txt"
        
        # Переменные
        self.limit_width = tk.IntVar(value=80)
        self.default_width = tk.IntVar(value=8)
        self.font_size = tk.IntVar(value=11)
        self.highlight_missing = tk.BooleanVar(value=False)
        self.errors = []  # Список строк с ошибками
        self.current_error_index = -1
        self.missing_chars = set()  # Множество отсутствующих символов
        self.dict_exists = False
        
        # Переменные для сохранения состояния окна
        self.window_state = None
        self.window_position = None
        
        # Загрузка настроек
        self.load_settings()
        
        # Загрузка словаря
        self.load_width_dict(self.current_dict_file)
        
        # Создание интерфейса
        self.create_widgets()
        
        # Привязка событий окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind("<Configure>", self.on_window_configure)
        
    def load_settings(self):
        """Загрузка настроек из JSON файла"""
        if os.path.exists(SETTING_FILE):
            try:
                with open(SETTING_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.limit_width.set(settings.get('limit_width', 80))
                    self.default_width.set(settings.get('default_width', 8))
                    self.current_dict_file = settings.get('dict_file', 'widths.txt')
                    self.font_size.set(settings.get('font_size', 11))
                    self.highlight_missing.set(settings.get('highlight_missing', False))
                    
                    # Загрузка состояния окна
                    self.window_state = settings.get('window_state', 'normal')
                    window_geometry = settings.get('window_geometry', '900x500+10+10')
                    if self.window_state == 'zoomed':
                        self.root.state('zoomed')
                    else:
                        self.root.geometry(window_geometry)
            except Exception as e:
                print(f"Ошибка загрузки настроек: {e}")
    
    def save_settings(self):
        """Сохранение настроек в JSON файл"""
        # Получаем текущую геометрию окна
        if self.root.state() == 'zoomed':
            window_state = 'zoomed'
            window_geometry = self.window_position if self.window_position else self.root.geometry()
        else:
            window_state = 'normal'
            window_geometry = self.root.geometry()
        
        settings = {
            'limit_width': self.limit_width.get(),
            'default_width': self.default_width.get(),
            'dict_file': self.current_dict_file,
            'font_size': self.font_size.get(),
            'highlight_missing': self.highlight_missing.get(),
            'window_state': window_state,
            'window_geometry': window_geometry
        }
        try:
            with open(SETTING_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
    
    def on_window_configure(self, event):
        """Сохранение позиции и размера окна при изменении"""
        if event.widget == self.root and self.root.state() != 'zoomed':
            self.window_position = self.root.geometry()
    
    def load_width_dict(self, filename):
        """Загрузка словаря ширины символов из файла"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    self.width_dict.clear()
                    for line in f:
                        # НЕ используем strip() или используем rstrip() только для удаления \n
                        line = line.rstrip('\n\r')
                        if line and '=' in line:
                            # Разделяем по первому знаку равенства
                            parts = line.split('=', 1)
                            if len(parts) == 2:
                                char = parts[0]
                                
                                # Сохраняем пробел как есть
                                # Если char пустая строка или состоит только из пробелов
                                if char == '' or char.isspace():
                                    char = ' '
                                
                                # Обработка специальных символов
                                elif char == '\\n':
                                    char = '\n'
                                elif char == '\\t':
                                    char = '\t'
                                elif char == '\\\\':
                                    char = '\\'
                                elif char == '\\"':
                                    char = '"'
                                elif char == '\\r':
                                    char = '\r'
                                
                                try:
                                    width = int(parts[1])
                                    self.width_dict[char] = width
                                except ValueError:
                                    continue
                print(f"Загружено {len(self.width_dict)} символов из {filename}")
                # Проверяем наличие пробела в словаре
                if ' ' in self.width_dict:
                    print(f"Пробел загружен с шириной {self.width_dict[' ']}")
                else:
                    print("Пробел не найден в словаре")
                self.dict_exists = True
                return True
            else:
                self.width_dict.clear()
                self.dict_exists = False
                print("Словарь не найден, используется ширина по умолчанию")
                return False
        except Exception as e:
            print(f"Ошибка загрузки словаря: {e}")
            messagebox.showerror("Ошибка", f"Не удалось загрузить словарь: {e}")
            self.dict_exists = False
            return False
    
    def get_char_width(self, char):
        """Получение ширины символа с учетом ширины по умолчанию"""
        if char in self.width_dict:
            return self.width_dict[char]
        else:
            return self.default_width.get()
    
    def get_string_width_and_missing(self, text):
        """Вычисление ширины строки и поиск отсутствующих символов"""
        total_width = 0
        i = 0
        missing_in_line = set()
        
        while i < len(text):
            # Проверка на многоточие
            if i + 2 < len(text) and text[i:i+3] == '...':
                if '...' in self.width_dict:
                    total_width += self.width_dict['...']
                else:
                    total_width += self.default_width.get()
                    missing_in_line.add('...')
                i += 3
            else:
                char = text[i]
                if char in self.width_dict:
                    total_width += self.width_dict[char]
                else:
                    total_width += self.default_width.get()
                    missing_in_line.add(char)
                i += 1
        
        return total_width, missing_in_line
    
    def get_line_info(self):
        """Получение информации о всех строках"""
        text = self.text_area.get("1.0", tk.END).rstrip('\n')
        lines = text.split('\n')
        
        line_info = []
        all_missing_chars = set()
        limit = self.limit_width.get()
        
        for i, line in enumerate(lines):
            current_width = 0
            char_positions = []
            char_widths = []
            missing_in_line = set()
            
            # Разбор строки на символы с учетом многоточия
            j = 0
            while j < len(line):
                if j + 2 < len(line) and line[j:j+3] == '...':
                    if '...' in self.width_dict:
                        width = self.width_dict['...']
                    else:
                        width = self.default_width.get()
                        missing_in_line.add('...')
                    char_widths.append(width)
                    char_positions.append((j, j+3, '...'))
                    current_width += width
                    j += 3
                else:
                    char = line[j]
                    if char in self.width_dict:
                        width = self.width_dict[char]
                    else:
                        width = self.default_width.get()
                        missing_in_line.add(char)
                    char_widths.append(width)
                    char_positions.append((j, j+1, char))
                    current_width += width
                    j += 1
            
            all_missing_chars.update(missing_in_line)
            
            # Определение позиции превышения лимита
            overflow_start = None
            overflow_char_index = None
            cumulative_width = 0
            
            for idx, width in enumerate(char_widths):
                if cumulative_width + width > limit:
                    overflow_start = cumulative_width
                    overflow_char_index = idx
                    break
                cumulative_width += width
            
            line_info.append({
                'line': line,
                'total_width': current_width,
                'overflow': current_width > limit,
                'overflow_start': overflow_start,
                'overflow_char_index': overflow_char_index,
                'char_positions': char_positions,
                'missing_chars': missing_in_line
            })
        
        return line_info, all_missing_chars
    
    def update_colors(self):
        """Обновление цветов строк на основе ширины"""
        line_info, all_missing_chars = self.get_line_info()
        
        # Поиск строк с ошибками
        self.errors = [i for i, info in enumerate(line_info) if info['overflow']]
        self.missing_chars = all_missing_chars
        # Обновляем current_error_index, сохраняя позицию если возможно
        if not self.errors:
            self.current_error_index = -1
        else:
            # Проверяем, существует ли текущий индекс
            if self.current_error_index >= len(self.errors):
                self.current_error_index = 0
            # Если current_error_index = -1, устанавливаем в 0 если есть ошибки
            if self.current_error_index == -1 and self.errors:
                self.current_error_index = 0
        
        # Очистка всех тегов
        self.text_area.tag_remove("error_part", "1.0", tk.END)
        self.text_area.tag_remove("missing_char", "1.0", tk.END)
        
        # Подсветка превышающих частей
        for i, info in enumerate(line_info):
            if info['overflow'] and info['overflow_char_index'] is not None:
                line_start = f"{i+1}.0"
                line_end = f"{i+1}.end"
                
                # Находим позицию начала превышения в тексте
                char_pos = info['char_positions']
                if info['overflow_char_index'] < len(char_pos):
                    start_char_pos = char_pos[info['overflow_char_index']][0]
                    # Подсвечиваем от символа превышения до конца строки
                    error_start = f"{i+1}.{start_char_pos}"
                    self.text_area.tag_add("error_part", error_start, line_end)
        
        # Подсветка отсутствующих символов (если включено)
        if self.highlight_missing.get():
            for i, info in enumerate(line_info):
                for start, end, char in info['char_positions']:
                    # Проверяем, отсутствует ли символ в словаре
                    if char not in self.width_dict:
                        char_start = f"{i+1}.{start}"
                        char_end = f"{i+1}.{end}"
                        self.text_area.tag_add("missing_char", char_start, char_end)
        
        # Обновление статистики
        total_lines = len(line_info)
        errors_count = len(self.errors)
        missing_count = len(self.missing_chars)
        
        warning_text = f"Нет символов в словаре: {missing_count}"
        if missing_count > 0 and self.highlight_missing.get():
            # Показываем первые 10 отсутствующих символов
            missing_list = list(self.missing_chars)
            display_chars = []
            for char in missing_list[:10]:
                if char == ' ':
                    display_chars.append('[пробел]')
                elif char == '\n':
                    display_chars.append('[перенос]')
                elif char == '\t':
                    display_chars.append('[таб]')
                else:
                    display_chars.append(char)
            
            warning_text += f" ({', '.join(display_chars)}"
            if missing_count > 10:
                warning_text += "..."
            warning_text += ")"
        elif missing_count > 0 and not self.highlight_missing.get():
            warning_text += " (подсветка отключена)"
        
        self.error_count_label.config(
            text=f"Ошибок: {errors_count} | Всего строк: {total_lines} | {warning_text}",
            fg="red" if errors_count > 0 else "green"
        )
        
        # Обновление индикатора
        if self.errors:
            self.error_indicator.config(text="⚠", fg="red", font=("Arial", 20, "bold"))
            if self.nav_buttons_frame.winfo_ismapped() == 0:
                self.nav_buttons_frame.pack(side=tk.RIGHT, padx=5)
        else:
            self.error_indicator.config(text="✓", fg="green", font=("Arial", 20, "bold"))
            self.nav_buttons_frame.pack_forget()
    
    def on_text_change(self, event=None):
        """Обработчик изменения текста"""
        self.update_colors()
    
    def on_limit_change(self, event=None):
        """Обработчик изменения лимита ширины"""
        self.update_colors()
    
    def on_default_width_change(self, event=None):
        """Обработчик изменения ширины по умолчанию"""
        self.update_colors()
    
    def on_highlight_missing_change(self):
        """Обработчик изменения чекбокса подсветки"""
        self.update_colors()
    
    def change_font_size(self, delta):
        """Изменение размера шрифта"""
        new_size = self.font_size.get() + delta
        if 8 <= new_size <= 24:
            self.font_size.set(new_size)
            font_tuple = ("Courier", new_size)
            self.text_area.config(font=font_tuple)
    
    def load_dict_file(self):
        """Загрузка другого файла словаря"""
        filename = filedialog.askopenfilename(
            title="Выберите файл словаря",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            if self.load_width_dict(filename):
                self.current_dict_file = filename
                # Обновляем отображение имени словаря
                if self.dict_exists:
                    self.dict_name_label.config(text=os.path.basename(filename), fg="blue")
                else:
                    self.dict_name_label.config(text="НЕТ СЛОВАРЯ widths.txt", fg="red")
                self.update_colors()
                messagebox.showinfo("Успех", f"Словарь загружен из {filename}")
    
    def get_current_line(self):
        """Получение номера текущей строки курсора"""
        try:
            cursor_pos = self.text_area.index("insert")
            line_number = int(cursor_pos.split('.')[0])
            return line_number - 1  # Возвращаем 0-индексацию
        except:
            return 0

    def goto_next_error(self):
        """Переход к следующей строке с ошибкой после текущей позиции курсора"""
        if not self.errors:
            return
        
        current_line = self.get_current_line()
        
        # Ищем первую ошибку после текущей строки
        next_error = None
        for error_line in self.errors:
            if error_line > current_line:
                next_error = error_line
                break
        
        # Если не нашли после текущей, ищем с начала
        if next_error is None and self.errors:
            next_error = self.errors[0]
        
        # Обновляем индекс
        if next_error is not None:
            self.current_error_index = self.errors.index(next_error)
            line_number = next_error + 1
            
            # Получаем информацию о строке
            line_info, _ = self.get_line_info()
            info = line_info[next_error]
            
            # Устанавливаем курсор в начало превышения (если есть)
            if info['overflow_char_index'] is not None:
                char_pos = info['char_positions'][info['overflow_char_index']][0]
                cursor_pos = f"{line_number}.{char_pos}"
            else:
                cursor_pos = f"{line_number}.0"
            
            self.text_area.see(cursor_pos)
            self.text_area.mark_set("insert", cursor_pos)
            self.text_area.focus_set()
            
            # Временное выделение всей строки
            self.text_area.tag_remove("highlight", "1.0", tk.END)
            self.text_area.tag_add("highlight", f"{line_number}.0", f"{line_number}.end")
            self.root.after(1000, lambda: self.text_area.tag_remove("highlight", "1.0", tk.END))
            
            # Обновление метки с текущей позицией
            self.error_pos_label.config(text=f"{self.current_error_index + 1}/{len(self.errors)}")

    def goto_prev_error(self):
        """Переход к предыдущей строке с ошибкой перед текущей позицией курсора"""
        if not self.errors:
            return
        
        current_line = self.get_current_line()
        
        # Ищем первую ошибку перед текущей строкой
        prev_error = None
        for error_line in reversed(self.errors):
            if error_line < current_line:
                prev_error = error_line
                break
        
        # Если не нашли перед текущей, ищем с конца
        if prev_error is None and self.errors:
            prev_error = self.errors[-1]
        
        # Обновляем индекс
        if prev_error is not None:
            self.current_error_index = self.errors.index(prev_error)
            line_number = prev_error + 1
            
            # Получаем информацию о строке
            line_info, _ = self.get_line_info()
            info = line_info[prev_error]
            
            # Устанавливаем курсор в начало превышения (если есть)
            if info['overflow_char_index'] is not None:
                char_pos = info['char_positions'][info['overflow_char_index']][0]
                cursor_pos = f"{line_number}.{char_pos}"
            else:
                cursor_pos = f"{line_number}.0"
            
            self.text_area.see(cursor_pos)
            self.text_area.mark_set("insert", cursor_pos)
            self.text_area.focus_set()
            
            # Временное выделение всей строки
            self.text_area.tag_remove("highlight", "1.0", tk.END)
            self.text_area.tag_add("highlight", f"{line_number}.0", f"{line_number}.end")
            self.root.after(1000, lambda: self.text_area.tag_remove("highlight", "1.0", tk.END))
            
            # Обновление метки с текущей позицией
            self.error_pos_label.config(text=f"{self.current_error_index + 1}/{len(self.errors)}")
    
    def clear_text(self):
        """Очистка текстового поля"""
        # Подтверждение очистки
        if self.text_area.get("1.0", tk.END).strip():
            self.text_area.delete("1.0", tk.END)
            self.update_colors()
        else:
            # Если текст уже пустой, просто обновляем
            self.update_colors()
    
    def show_help(self):
        """Показать информацию о программе"""
        dict_display = os.path.basename(self.current_dict_file) if self.dict_exists else "НЕТ СЛОВАРЯ widths.txt"
        info_text = f"""Программа проверки ширины строк
 Версия {MAIN_VERSION}, pav13
 
 ЗАГРУЖЕННЫЕ ДАННЫЕ:
   Файл словаря: {dict_display}
   Загружено символов из словаря: {len(self.width_dict)}
   Текущий лимит ширины: {self.limit_width.get()}
   Ширина по умолчанию: {self.default_width.get()}
   Подсветка отсутствующих символов: {"включена" if self.highlight_missing.get() else "выключена"}
 
 ФУНКЦИОНАЛ:
   • Строки, превышающие лимит, подсвечиваются красным цветом
   • Символы, отсутствующие в словаре, подсвечиваются желтым (если включено)
   • Отсутствующим символам присваивается ширина по умолчанию
   • Кнопки навигации перемещают курсор к следующей/предыдущей ошибке
 
 РАБОТА СО СЛОВАРЕМ:
   • Формат файла словаря: символ=ширина (например, А=8, пробел=4)
   • Поддерживаются специальные символы: \\n, \\t, \\\\, \\", \\r, ...
   • Кнопка "Создать шаблон словаря" создает файл со всеми печатными
     символами (латиница, кириллица, цифры, знаки препинания)
 
 НАСТРОЙКИ:
   • Все настройки автоматически сохраняются при закрытии программы
 
 УПРАВЛЕНИЕ:
   • A- / A+ - уменьшение/увеличение размера шрифта
   • Очистить текст - удаление всего текста из поля ввода
   • Загрузить словарь - выбор другого файла словаря
   • Создать шаблон словаря - генерация шаблона со всеми символами
 
 СОВЕТЫ:
   • Для многоточия (...) можно задать отдельную ширину в словаре
   • Включайте подсветку отсутствующих символов, чтобы быстро найти символы,
     которые нужно добавить в словарь"""
        messagebox.showinfo("Справка", info_text)
    
    def on_closing(self):
        """Обработчик закрытия окна"""
        self.save_settings()
        self.root.destroy()
    
    def create_dict_template(self):
        """Создание шаблона словаря со всеми печатными символами"""
        # Запрашиваем имя файла для сохранения
        filename = filedialog.asksaveasfilename(
            title="Сохранить шаблон словаря",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="widths_template.txt"
        )
        
        if not filename:
            return
        
        # Получаем текущую ширину по умолчанию
        default_width = self.default_width.get()
        
        # Создаем список символов для шаблона
        # Латинские буквы (верхний и нижний регистр)
        latin_upper = [chr(i) for i in range(ord('A'), ord('Z') + 1)]
        latin_lower = [chr(i) for i in range(ord('a'), ord('z') + 1)]
        
        # Цифры
        digits = [chr(i) for i in range(ord('0'), ord('9') + 1)]
        
        # Основные знаки препинания и символы
        punctuation = '!@#$%^&*()_+-=[]{}|;:,.<>?/\\~`'
        
        # Русские буквы (кириллица)
        # Верхний регистр
        russian_upper = 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
        # Нижний регистр
        russian_lower = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
        
        # Собираем все символы
        all_chars = (
            list(latin_upper) + 
            list(latin_lower) + 
            list(digits) + 
            list(punctuation) + 
            list(russian_upper) + 
            list(russian_lower)
        )
        
        # Удаляем дубликаты, сохраняя порядок
        seen = set()
        unique_chars = []
        for char in all_chars:
            if char not in seen:
                seen.add(char)
                unique_chars.append(char)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                # Записываем пробел отдельно (в начале для наглядности)
                f.write(f" ={default_width}\n")
                
                # Записываем остальные символы
                for char in unique_chars:
                    # Для специальных символов, которые могут вызвать проблемы
                    if char == ' ':
                        continue  # пробел уже записан
                    elif char == '\n':
                        f.write(f"\\n={default_width}\n")
                    elif char == '\t':
                        f.write(f"\\t={default_width}\n")
                    elif char == '\\':
                        f.write(f"\\\\={default_width}\n")
                    elif char == '"':
                        f.write(f'\\"={default_width}\n')
                    else:
                        f.write(f"{char}={default_width}\n")
                
                # Добавляем многоточие как специальный символ
                f.write(f"...={default_width}\n")
            
            messagebox.showinfo("Успех", f"Шаблон словаря сохранен в:\n{filename}")
            
            # Спрашиваем, загрузить ли созданный словарь
            if messagebox.askyesno("Загрузить словарь", "Загрузить созданный шаблон словаря?"):
                if self.load_width_dict(filename):
                    self.current_dict_file = filename
                    if self.dict_exists:
                        self.dict_name_label.config(text=os.path.basename(filename), fg="blue")
                    else:
                        self.dict_name_label.config(text="НЕТ СЛОВАРЯ", fg="red")
                    self.update_colors()
                    
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать шаблон словаря:\n{e}")
    
    def show_context_menu(self, event):
        """Показать контекстное меню при нажатии правой кнопки мыши"""
        # Создаем контекстное меню
        context_menu = tk.Menu(self.root, tearoff=0)
        
        # Функции для работы с буфером обмена
        def cut_text():
            try:
                if self.text_area.selection_get():
                    self.text_area.event_generate("<<Cut>>")
            except tk.TclError:
                pass
        
        def copy_text():
            try:
                if self.text_area.selection_get():
                    self.text_area.event_generate("<<Copy>>")
            except tk.TclError:
                pass
        
        def paste_text():
            self.text_area.event_generate("<<Paste>>")
        
        def delete_text():
            try:
                if self.text_area.selection_get():
                    self.text_area.delete("sel.first", "sel.last")
            except tk.TclError:
                pass
        
        # Проверяем, есть ли выделенный текст
        try:
            has_selection = bool(self.text_area.selection_get())
        except tk.TclError:
            has_selection = False
        
        # Добавляем пункты меню
        context_menu.add_command(label="Вырезать", command=cut_text, state=tk.NORMAL if has_selection else tk.DISABLED)
        context_menu.add_command(label="Копировать", command=copy_text, state=tk.NORMAL if has_selection else tk.DISABLED)
        context_menu.add_command(label="Вставить", command=paste_text)
        context_menu.add_separator()
        context_menu.add_command(label="Удалить", command=delete_text, state=tk.NORMAL if has_selection else tk.DISABLED)
        
        # Показываем меню в позиции курсора
        context_menu.post(event.x_root, event.y_root)
    
    def create_widgets(self):
        """Создание всех виджетов интерфейса"""
        # Верхняя панель с индикатором и навигацией
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Индикатор ошибок
        self.error_indicator = tk.Label(top_frame, text="✓", fg="green", font=("Arial", 20, "bold"))
        self.error_indicator.pack(side=tk.LEFT, padx=10)
        
        # Метка с количеством ошибок, строк и предупреждений
        self.error_count_label = tk.Label(top_frame, text="Ошибок: 0 | Всего строк: 0 | Предупреждение: 0", 
                                         font=("Arial", 10))
        self.error_count_label.pack(side=tk.LEFT, padx=5)
        
        # Кнопки навигации
        self.nav_buttons_frame = tk.Frame(top_frame)
        
        self.prev_error_btn = tk.Button(self.nav_buttons_frame, text="< Пред. ошибка", 
                                        command=self.goto_prev_error, state=tk.NORMAL)
        self.prev_error_btn.pack(side=tk.LEFT, padx=2)
        
        self.next_error_btn = tk.Button(self.nav_buttons_frame, text="След. ошибка >", 
                                        command=self.goto_next_error, state=tk.NORMAL)
        self.next_error_btn.pack(side=tk.LEFT, padx=2)
        
        self.error_pos_label = tk.Label(self.nav_buttons_frame, text="0/0", width=8)
        self.error_pos_label.pack(side=tk.LEFT, padx=5)
        
        # Панель управления - первая строка
        control_frame_row1 = tk.Frame(self.root)
        control_frame_row1.pack(fill=tk.X, padx=5, pady=2)
        
        # Макс. ширина
        tk.Label(control_frame_row1, text="Макс. ширина:").pack(side=tk.LEFT, padx=5)
        limit_entry = tk.Spinbox(control_frame_row1, from_=1, to=500, textvariable=self.limit_width, 
                                 width=5, command=self.on_limit_change)
        limit_entry.pack(side=tk.LEFT, padx=2)
        limit_entry.bind('<KeyRelease>', self.on_limit_change)
        
        # Ширина по умолчанию
        tk.Label(control_frame_row1, text="Ширина символа по умолч.:").pack(side=tk.LEFT, padx=5)
        default_entry = tk.Spinbox(control_frame_row1, from_=1, to=50, textvariable=self.default_width, 
                                   width=3, command=self.on_default_width_change)
        default_entry.pack(side=tk.LEFT, padx=2)
        default_entry.bind('<KeyRelease>', self.on_default_width_change)
        
        # Кнопка загрузки словаря с отображением имени файла
        dict_frame = tk.Frame(control_frame_row1)
        dict_frame.pack(side=tk.LEFT, padx=5)
        
        tk.Button(dict_frame, text="Загрузить словарь", command=self.load_dict_file).pack(side=tk.LEFT)
        # Отображаем имя файла или "НЕТ СЛОВАРЯ" в зависимости от наличия словаря
        dict_display_text = os.path.basename(self.current_dict_file) if self.dict_exists else "НЕТ СЛОВАРЯ widths.txt"
        dict_display_color = "blue" if self.dict_exists else "red"
        self.dict_name_label = tk.Label(dict_frame, text=dict_display_text, 
                                        fg=dict_display_color, font=("Arial", 9, "italic"))
        self.dict_name_label.pack(side=tk.LEFT, padx=5)
        
        # Создать шаблон словаря
        tk.Button(dict_frame, text="Создать шаблон словаря", command=self.create_dict_template).pack(side=tk.LEFT, padx=2)
        
        # Панель управления - вторая строка (для чекбокса и дополнительных элементов)
        control_frame_row2 = tk.Frame(self.root)
        control_frame_row2.pack(fill=tk.X, padx=5, pady=2)
        
        # Чекбокс подсветки отсутствующих символов
        self.highlight_check = tk.Checkbutton(control_frame_row2, text="Подсветка отсутствующих символов", 
                                              variable=self.highlight_missing,
                                              command=self.on_highlight_missing_change)
        self.highlight_check.pack(side=tk.LEFT, padx=5)
        
        # Кнопки изменения шрифта
        font_frame = tk.Frame(control_frame_row2)
        font_frame.pack(side=tk.LEFT, padx=5)
        tk.Label(font_frame, text="Размер текста:").pack(side=tk.LEFT)
        tk.Button(font_frame, text="A-", command=lambda: self.change_font_size(-1), width=3).pack(side=tk.LEFT, padx=1)
        tk.Button(font_frame, text="A+", command=lambda: self.change_font_size(1), width=3).pack(side=tk.LEFT, padx=1)
        
        tk.Button(control_frame_row2, text="Справка", command=self.show_help).pack(side=tk.RIGHT, padx=5)
        tk.Button(control_frame_row2, text="Очистить текст", command=self.clear_text).pack(side=tk.RIGHT, padx=5)
        
        # Текстовая область с прокруткой
        text_frame = tk.Frame(self.root)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Создаем контейнер для прокрутки
        text_container = tk.Frame(text_frame)
        text_container.pack(fill=tk.BOTH, expand=True)
        
        # Вертикальная прокрутка
        v_scrollbar = tk.Scrollbar(text_container)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Горизонтальная прокрутка
        h_scrollbar = tk.Scrollbar(text_container, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Текстовая область
        self.text_area = tk.Text(text_container, wrap=tk.NONE, 
                                 font=("Courier", self.font_size.get()),
                                 yscrollcommand=v_scrollbar.set,
                                 xscrollcommand=h_scrollbar.set,
                                 undo=True)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        v_scrollbar.config(command=self.text_area.yview)
        h_scrollbar.config(command=self.text_area.xview)
        
        # Привязываем событие правой кнопки мыши к контекстному меню
        self.text_area.bind("<Button-3>", self.show_context_menu)
        
        # Настройка тегов для подсветки
        self.text_area.tag_config("error_part", background="red", foreground="white")
        self.text_area.tag_config("missing_char", background="yellow", foreground="black")
        self.text_area.tag_config("highlight", background="lightgreen", foreground="black")
        
        # Привязка событий
        self.text_area.bind('<KeyRelease>', self.on_text_change)
        self.text_area.bind('<ButtonRelease-1>', lambda e: self.update_colors())
        
        # Начальное обновление
        self.update_colors()


def main():
    root = tk.Tk()
    app = WidthCheckerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()