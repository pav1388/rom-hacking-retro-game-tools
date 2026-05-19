#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Vanguard Bandits PSX Text Tools - Improved Version by pav13 + deepseek

import os
import sys
import struct
import argparse
import re
import traceback
import shutil
from pathlib import Path

CHAR_TO_BYTE = {}
BYTE_TO_CHAR = {}

def load_encoding_table(filename='tools/encoding_table.txt'):
    """
    Загружает таблицу кодировки из файла с поддержкой раздельных таблиц для извлечения и обновления.
    """
    global CHAR_TO_BYTE, BYTE_TO_CHAR
    
    CHAR_TO_BYTE = {}
    BYTE_TO_CHAR = {}
    
    # Раздельные таблицы
    extract_table = {}  # для извлечения (байт -> символ)
    update_table = {}   # для обновления (символ -> байт)
    
    current_section = None
    
    try:
        with open(str(filename), 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    # Определяем секцию по комментариям
                    if 'Латиница' in line or 'для извлечения' in line:
                        current_section = 'extract'
                    elif 'Кириллица' in line or 'для обновления' in line:
                        current_section = 'update'
                    elif 'Спецсимволы' in line or 'общие' in line:
                        current_section = 'both'
                    continue
                
                if '=' in line:
                    hex_byte, char = line.split('=', 1)
                    if char:
                        byte_val = int(hex_byte, 16)
                        
                        if current_section in ['extract', 'both']:
                            extract_table[byte_val] = char
                        
                        if current_section in ['update', 'both']:
                            update_table[char] = byte_val
        
        BYTE_TO_CHAR = extract_table
        
        for byte_val, char in extract_table.items():
            if char not in update_table:
                update_table[char] = byte_val
        
        CHAR_TO_BYTE = update_table
        
        print(" Загружено символов для извлечения: " + str(len(BYTE_TO_CHAR)))
        print(" Загружено символов для обновления: " + str(len(CHAR_TO_BYTE)))
        
        conflicts = []
        for byte_val in BYTE_TO_CHAR:
            extract_char = BYTE_TO_CHAR[byte_val]
            if extract_char in CHAR_TO_BYTE and CHAR_TO_BYTE[extract_char] != byte_val:
                conflicts.append("0x{0:02X}: '{1}' -> 0x{2:02X}".format(byte_val, extract_char, CHAR_TO_BYTE[extract_char]))
        
        if conflicts:
            print("[!] Обнаружены конфликты в таблице кодировки:")
            for conflict in conflicts:
                print("   " + conflict)
        
        return True
        
    except FileNotFoundError:
        print("[!] Ошибка: файл кодировки " + filename + " не найден")
        return False
    except Exception as e:
        print("[!] Ошибка загрузки таблицы кодировки: " + str(e))
        return False

def debug_encoding_table(filename='tools/encoding_table.txt'):
    """
    Диагностика таблицы кодировки с четким разделением на ошибки и нормальное поведение.
    """
    print("\n" + "=" * 30)
    print(" ПОЛНАЯ ДИАГНОСТИКА ТАБЛИЦЫ КОДИРОВКИ")
    print("=" * 30)
    
    extract_table = {}
    update_table = {}
    current_section = None
    
    section_info = []
    duplicate_definitions = []
    multi_char_bytes = []
    line_info = []
    
    try:
        with open(str(filename), 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    if 'Латиница' in line or 'для извлечения' in line:
                        current_section = 'extract'
                        section_info.append(" Строка {0}: Начало секции ИЗВЛЕЧЕНИЯ".format(line_num))
                    elif 'Кириллица' in line or 'для обновления' in line:
                        current_section = 'update' 
                        section_info.append(" Строка {0}: Начало секции ОБНОВЛЕНИЯ".format(line_num))
                    elif 'Спецсимволы' in line or 'общие' in line:
                        current_section = 'both'
                        section_info.append(" Строка {0}: Начало секции ОБЩИХ СИМВОЛОВ".format(line_num))
                    continue
                
                if '=' in line:
                    hex_byte, char = line.split('=', 1)
                    if char:
                        try:
                            byte_val = int(hex_byte, 16)
                            line_info.append((line_num, byte_val, char, current_section))
                            
                            if current_section in ['extract', 'both']:
                                if byte_val in extract_table:
                                    duplicate_definitions.append(
                                        "[ERR] Строка {0}: Байт 0x{1:02X} уже определен как '{2}', переопределяется на '{3}'".format(
                                        line_num, byte_val, extract_table[byte_val], char)
                                    )
                                extract_table[byte_val] = char
                            
                            if current_section in ['update', 'both']:
                                if char in update_table:
                                    duplicate_definitions.append(
                                        "[ERR] Строка {0}: Символ '{1}' уже определен как 0x{2:02X}, переопределяется на 0x{3:02X}".format(
                                        line_num, char, update_table[char], byte_val)
                                    )
                                update_table[char] = byte_val
                                
                        except ValueError:
                            duplicate_definitions.append(
                                "[ERR] Строка {0}: Неверный hex-формат '{1}'".format(line_num, hex_byte)
                            )
        
        added_from_extract = 0
        for byte_val, char in extract_table.items():
            if char not in update_table:
                update_table[char] = byte_val
                added_from_extract += 1
        
        byte_to_chars = {}
        for byte_val, char in extract_table.items():
            if byte_val not in byte_to_chars:
                byte_to_chars[byte_val] = []
            byte_to_chars[byte_val].append(char)
        
        for byte_val, chars in byte_to_chars.items():
            if len(chars) > 1:
                multi_char_bytes.append((byte_val, chars))
        
        print("\n[STATS] ОБЩАЯ СТАТИСТИКА:")
        print("   [OK] Записей для извлечения (байт -> символ): " + str(len(extract_table)))
        print("   [OK] Записей для обновления (символ -> байт): " + str(len(update_table)))
        print("   [OK] Символов добавлено из извлечения: " + str(added_from_extract))
        
        print("\n[STRUCT] СТРУКТУРА ФАЙЛА:")
        for info in section_info:
            print("   " + info)
        
        if duplicate_definitions:
            print("\n[CRIT] КРИТИЧЕСКИЕ ОШИБКИ (нужно исправить):")
            for error in duplicate_definitions:
                print("   " + error)
            print("\n   [TIP] Рекомендация: Удалите дублирующиеся строки из таблицы!")
        else:
            print("\n[OK] Критических ошибок не обнаружено")
        
        if multi_char_bytes:
            print("\n[NORM] НОРМАЛЬНОЕ ПОВЕДЕНИЕ (один байт -> несколько символов):")
            print("   [TIP] Это ожидаемо для кастомной кодировки игр!")
            for byte_val, chars in multi_char_bytes:
                print("   [MAP] 0x{0:02X} -> {1}".format(byte_val, ', '.join(repr(c) for c in chars)))
        
        print("\n[CHECK] ПРОВЕРКА СОГЛАСОВАННОСТИ ТАБЛИЦ:")
        mapping_issues = []
        for char, byte_val in update_table.items():
            if byte_val in extract_table and extract_table[byte_val] != char:
                mapping_issues.append((byte_val, extract_table[byte_val], char))
        
        if mapping_issues:
            print("   [INFO] Ожидаемые различия (извлечение vs обновление):")
            for byte_val, extract_char, update_char in mapping_issues:
                print("     0x{0:02X}: '{1}' (извлек.) != '{2}' (обновл.)".format(byte_val, extract_char, update_char))
        else:
            print("   [OK] Таблицы полностью согласованы")
        
        print("\n[TEST] ТЕСТ КЛЮЧЕВЫХ ПРЕОБРАЗОВАНИЙ:")
        test_cases = [
            (0x41, 'A', 'А'), (0x42, 'B', 'В'),
            (0x61, 'a', 'а'), (0x62, 'b', 'в'),
            (0x45, 'E', 'Е'), (0x4F, 'O', 'Э'),
            (0x30, '0', 'О'), (0x33, '3', 'З')
        ]
        
        all_tests_passed = True
        for byte_val, latin_char, cyrillic_char in test_cases:
            extracted = extract_table.get(byte_val, '?')
            latin_byte = update_table.get(latin_char, None)
            cyrillic_byte = update_table.get(cyrillic_char, None)
            
            status_extract = "[OK]" if extracted != '?' else "[NO]"
            status_latin = "[OK]" if latin_byte is not None else "[NO]" 
            status_cyrillic = "[OK]" if cyrillic_byte is not None else "[NO]"
            
            print("   {0} Извлечение: 0x{1:02X} -> '{2}'".format(status_extract, byte_val, extracted))
            if latin_byte is not None:
                print("   {0} Обновление: '{1}' -> 0x{2:02X}".format(status_latin, latin_char, latin_byte))
            if cyrillic_byte is not None:
                print("   {0} Обновление: '{1}' -> 0x{2:02X}".format(status_cyrillic, cyrillic_char, cyrillic_byte))
            
            if extracted == '?' or latin_byte is None or cyrillic_byte is None:
                all_tests_passed = False
        
        print("\n" + "=" * 30)
        if not duplicate_definitions and all_tests_passed:
            print("[PASS] ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Таблица кодировки работает корректно.")
            print("[TIP] Небольшие различия между извлечением и обновлением - это нормально!")
        elif duplicate_definitions:
            print("[WARN] Обнаружены критические ошибки! Исправьте дубликаты в таблице.")
        else:
            print("[WARN] Есть проблемы с тестовыми преобразованиями. Проверьте таблицу.")
        print("=" * 30)
        
        return len(duplicate_definitions) == 0
        
    except FileNotFoundError:
        print("[ERR] Файл кодировки не найден: " + filename)
        return False
    except Exception as e:
        print("[ERR] Ошибка диагностики: " + str(e))
        traceback.print_exc()
        return False

def encode_text_to_custom(text):
    """
    Кодирует текст в байты по кастомной таблице.
    """
    result = bytearray()
    
    i = 0
    while i < len(text):
        # Проверяем escape-последовательности
        if i + 1 < len(text) and text[i] == '\\':
            seq = text[i:i+2]
            if seq in ['\\0', '\\t', '\\n', '\\r']:
                if seq == '\\0':
                    result.append(0x00)  # нулевой байт
                elif seq == '\\t':
                    result.append(0x09)
                elif seq == '\\n':
                    result.append(0x0A)
                elif seq == '\\r':
                    result.append(0x0D)
                i += 2
                continue
        
        # Обрабатываем все основные символы
        char = text[i]
        if char == '\x00':  # нулевой байт
            result.append(0x00)
        elif char == '\t':
            result.append(0x09)
        elif char == '\n':
            result.append(0x0A)
        elif char == '\r':
            result.append(0x0D)
        elif char == ' ':  # ПРОБЕЛ
            result.append(0x20)
        elif char in CHAR_TO_BYTE:
            result.append(CHAR_TO_BYTE[char])
        else:
            result.append(0x3F)
            print("Предупреждение: символ '{0}' (0x{1:04X}) не найден в таблице кодировки".format(char, ord(char)))
        i += 1
    
    return bytes(result)

def is_valid_sentence_start(text_bytes, position, data):
    """
    Проверяет, является ли позиция началом нового предложения.
    """
    if position == 0:
        return True
    
    # Если предыдущий байт - нулевой (конец предыдущей строки)
    if position > 0 and data[position - 1] == 0x00:
        return True
    
    # Если предыдущий байт - конец предыдущего блока
    if position >= 3 and data[position - 3:position] == b'\x00\x00\x00':
        return True
    
    # Проверяем, начинается ли текст с заглавной буквы или цифры
    if len(text_bytes) > 0:
        first_char_byte = text_bytes[0]
        # Заглавные буквы ASCII
        if 0x41 <= first_char_byte <= 0x5A:
            return True
        # Цифры
        if 0x30 <= first_char_byte <= 0x39:
            return True
        # Специальные символы, которые могут начинать предложение
        if first_char_byte in [0x22, 0x27, 0x28, 0x5B]:  # ", ', (, [
            return True
    
    return False

def is_valid_text_continuation(data, position, length):
    """
    Проверяет, является ли последовательность байтов валидным текстом.
    """
    if length < 2:
        return False
    
    consecutive_printable = 0
    max_consecutive = 0
    
    for i in range(position, min(position + length, len(data))):
        byte = data[i]
        # Проверяем печатные символы ASCII и основные управляющие
        if (0x20 <= byte <= 0x7E) or byte in [0x09, 0x0A, 0x0D]:
            consecutive_printable += 1
            max_consecutive = max(max_consecutive, consecutive_printable)
        else:
            consecutive_printable = 0
        
        # Если нашли достаточное количество подряд идущих печатных символов
        if max_consecutive >= 4:  # Уменьшил порог для коротких слов
            return True
    
    return False

def find_text_blocks_improved(filename, max_blocks=1000, min_string_length=3):
    """
    Улучшенный поиск текстовых блоков с валидацией заголовков и поинтеров.
    """
    try:
        with open(str(filename), 'rb') as f:
            data = f.read()
    except FileNotFoundError:
        print("Ошибка: файл " + filename + " не найден")
        return []
    except Exception as e:
        print("Ошибка чтения файла " + filename + ": " + str(e))
        return []
    
    text_blocks = []
    position = 0
    data_len = len(data)
    
    # ANSI символы (печатные символы ASCII + некоторые специальные)
    printable_bytes = bytes(range(0x20, 0x7F)) + b'\x09\x0A\x0D'
    
    while position < data_len - 6 and len(text_blocks) < max_blocks:
        # Ищем потенциальное начало текста
        if data[position] in printable_bytes:
            potential_start = position
            
            # Проверяем, не находимся ли мы уже внутри другого блока
            in_existing_block = False
            for block in text_blocks:
                if block['text_start'] <= potential_start < block['block_end']:
                    in_existing_block = True
                    break
            if in_existing_block:
                position += 1
                continue
            
            # Пытаемся найти структуру блока с заголовком
            block_result = analyze_potential_block(data, potential_start, data_len, 
                                                 printable_bytes, min_string_length)
            
            if block_result:
                text_blocks.append(block_result)
                position = block_result['block_end'] + 3
            else:
                # Пытаемся найти простой текстовый блок без заголовка
                simple_block = analyze_simple_text_block(data, potential_start, data_len,
                                                       printable_bytes, min_string_length)
                if simple_block:
                    text_blocks.append(simple_block)
                    position = simple_block['block_end'] + 1
                else:
                    position += 1
        else:
            position += 1
    
    # Фильтруем дубликаты и вложенные блоки
    text_blocks = filter_duplicate_blocks(text_blocks)
    
    return text_blocks

def analyze_potential_block(data, start_pos, data_len, printable_bytes, min_length):
    """
    Анализирует потенциальный текстовый блок с заголовком.
    """
    # Ищем возможный заголовок перед текстом
    header_info = find_possible_header(data, start_pos, data_len)
    
    if not header_info:
        return None
    
    header_start, pointers = header_info
    
    # Анализируем текстовый блок
    text_block_info = analyze_text_block_content(data, start_pos, data_len, 
                                               printable_bytes, min_length, pointers, header_start)
    
    if not text_block_info or text_block_info['string_count'] == 0:
        return None
    
    # Валидируем соответствие поинтеров и строк
    if not validate_pointers_and_strings(text_block_info, pointers, header_start):
        return None
    
    # Собираем полную информацию о блоке
    block_info = {
        'header_start': header_start,
        'text_start': start_pos,
        'block_end': text_block_info['block_end'],
        'pointers': pointers,
        'string_pointers': text_block_info['string_pointers'],
        'strings': text_block_info['strings'],
        'header_size': start_pos - header_start,
        'text_size': text_block_info['block_end'] - start_pos,
        'total_size': text_block_info['block_end'] - header_start,
        'string_count': text_block_info['string_count'],
        'has_header': True,
        'validated': True
    }
    
    return block_info

def find_possible_header(data, text_start, data_len):
    """
    Ищет возможный заголовок с поинтерами перед текстовым блоком.
    """
    # Ищем разделитель 0x000000 перед текстом
    separator_pos = find_block_separator(data, text_start)
    if separator_pos is None:
        return None
    
    header_start = separator_pos + 3
    header_size = text_start - header_start
    
    # Заголовок должен быть выровнен и иметь разумный размер
    if header_size < 2 or header_size > 1024 or header_size % 2 != 0:
        return None
    
    # Анализируем поинтеры в заголовке
    pointers = analyze_header_pointers(data, header_start, text_start, header_size)
    
    if not pointers:
        return None
    
    return header_start, pointers

def find_block_separator(data, text_start, search_range = 512):
    """
    Ищет разделитель блоков (0x000000) перед указанной позицией.
    """
    start_search = max(0, text_start - search_range)
    
    for pos in range(text_start - 3, start_search - 1, -1):
        if pos >= 2 and data[pos:pos+3] == b'\x00\x00\x00':
            return pos
    
    return None

def analyze_header_pointers(data, header_start, text_start, header_size):
    """
    Анализирует поинтеры в заголовке и возвращает валидные.
    """
    pointers = []
    printable_bytes = bytes(range(0x20, 0x7F)) + b'\x09\x0A\x0D'
    
    for offset in range(0, header_size - 1, 2):
        pointer_pos = header_start + offset
        if pointer_pos + 1 >= len(data):
            break
            
        pointer_val = struct.unpack('<H', data[pointer_pos:pointer_pos+2])[0]
        target_addr = header_start + pointer_val
        
        # Проверяем, указывает ли поинтер на валидную позицию в текстовом блоке
        if (target_addr >= text_start and 
            target_addr < len(data) and 
            data[target_addr] in printable_bytes and
            is_valid_sentence_start(data[target_addr:target_addr+1], target_addr, data)):
            
            pointers.append((pointer_pos, pointer_val))
    
    return pointers

def analyze_text_block_content(data, start_pos, data_len, printable_bytes, min_length,
                                pointers, header_start):
    """
    Анализирует содержимое текстового блока.
    """
    strings = []
    current_string_start = start_pos
    block_end = None
    string_pointers = {}
    
    position = start_pos
    
    # Создаем множество целевых адресов из поинтеров для быстрой проверки
    pointer_targets = {header_start + ptr_val for _, ptr_val in pointers}
    
    while position < data_len - 2:
        # Проверяем конец блока
        if data[position:position+3] == b'\x00\x00\x00':
            block_end = position
            # Добавляем последнюю строку если она валидна
            if (current_string_start < block_end and 
                block_end - current_string_start >= min_length):
                strings.append(current_string_start)
            break
        
        # Конец строки
        elif data[position] == 0x00:
            string_length = position - current_string_start
            
            # Проверяем валидность строки
            if (string_length >= min_length and
                is_valid_text_continuation(data, current_string_start, string_length)):
                
                strings.append(current_string_start)
                
                # Проверяем, есть ли поинтер на эту строку
                if current_string_start in pointer_targets:
                    # Находим соответствующий поинтер
                    for ptr_pos, ptr_val in pointers:
                        if header_start + ptr_val == current_string_start:
                            string_pointers[current_string_start] = (ptr_pos, ptr_val)
                            break
            
            current_string_start = position + 1
            position += 1
        
        # Валидный текстовый символ
        elif data[position] in printable_bytes:
            position += 1
        
        # Невалидный символ - возможно конец блока
        else:
            # Если накопили достаточно строк, считаем это концом блока
            if len(strings) >= 1 and position - start_pos > 16:
                block_end = position
                break
            else:
                return None
    
    # Если дошли до конца файла
    if block_end is None and position >= data_len - 2:
        block_end = data_len
        if (current_string_start < block_end and 
            block_end - current_string_start >= min_length):
            strings.append(current_string_start)
    
    if not strings or block_end is None:
        return None
    
    return {
        'strings': strings,
        'string_pointers': string_pointers,
        'block_end': block_end,
        'string_count': len(strings)
    }

def analyze_simple_text_block(data, start_pos, data_len, printable_bytes, min_length):
    """
    Анализирует простой текстовый блок без заголовка.
    """
    strings = []
    current_string_start = start_pos
    block_end = None
    
    position = start_pos
    
    while position < data_len:
        # Конец строки
        if data[position] == 0x00:
            string_length = position - current_string_start
            
            if (string_length >= min_length and
                is_valid_text_continuation(data, current_string_start, string_length)):
                
                strings.append(current_string_start)
            
            current_string_start = position + 1
        
        # Непечатный символ (кроме разрешенных)
        elif data[position] not in printable_bytes:
            # Если набрали несколько строк, считаем это текстовым блоком
            if len(strings) >= 2:
                block_end = position
                break
            else:
                return None
        
        position += 1
        
        # Защита от бесконечного цикла
        if position - start_pos > 4096:  # Максимальный размер блока
            if len(strings) >= 1:
                block_end = position
                break
            else:
                return None
    
    if block_end is None and position >= data_len:
        block_end = data_len
    
    if len(strings) < 1:
        return None
    
    # Добавляем последнюю строку если нужно
    if (current_string_start < block_end and 
        block_end - current_string_start >= min_length and
        is_valid_text_continuation(data, current_string_start, block_end - current_string_start)):
        strings.append(current_string_start)
    
    return {
        'header_start': start_pos,
        'text_start': start_pos,
        'block_end': block_end,
        'pointers': [],
        'string_pointers': {},
        'strings': strings,
        'header_size': 0,
        'text_size': block_end - start_pos,
        'total_size': block_end - start_pos,
        'string_count': len(strings),
        'has_header': False,
        'validated': True
    }

def filter_duplicate_blocks(blocks):
    """
    Фильтрует дублирующиеся и вложенные блоки.
    """
    if not blocks:
        return []
    
    # Сортируем блоки по начальной позиции
    blocks.sort(key=lambda x: x['text_start'])
    
    filtered_blocks = []
    covered_ranges = []
    
    for block in blocks:
        block_range = (block['text_start'], block['block_end'])
        
        # Проверяем, не перекрывается ли блок с уже добавленными
        is_duplicate = False
        for start, end in covered_ranges:
            if (block_range[0] >= start and block_range[1] <= end) or \
               (block_range[0] <= end and block_range[1] >= start):
                is_duplicate = True
                break
        
        if not is_duplicate:
            filtered_blocks.append(block)
            covered_ranges.append(block_range)
    
    return filtered_blocks

def validate_pointers_and_strings(block_info, pointers, header_start):
    """
    Проверяет соответствие поинтеров и строк в блоке.
    """
    if not pointers:
        return True
    
    # Проверяем, что поинтеры указывают на начала строк
    valid_pointer_count = 0
    string_starts = set(block_info['strings'])
    
    for ptr_pos, ptr_val in pointers:
        target_addr = header_start + ptr_val
        if target_addr in string_starts:
            valid_pointer_count += 1
    
    # Считаем блок валидным если хотя бы некоторые поинтеры совпадают
    return valid_pointer_count >= max(1, len(pointers) * 0.3)  # 30% поинтеров должны быть валидны

def extract_text_from_file(filename, block_info):
    """Извлекает текст из блока файла (оригинальный английский)."""
    try:
        with open(str(filename), 'rb') as f:
            data = f.read()
    except Exception as e:
        print("Ошибка чтения файла: " + str(e))
        return []
    
    extracted_strings = []
    strings_addrs = block_info['strings']
    
    for i in range(len(strings_addrs)):
        start_addr = strings_addrs[i]
        
        # Определяем конец строки
        if i < len(strings_addrs) - 1:
            end_addr = strings_addrs[i + 1] - 1  # -1 чтобы исключить 0x00 разделитель
        else:
            end_addr = block_info['block_end']
        
        # Извлекаем байты строки
        string_bytes = data[start_addr:end_addr]
        
        # Декодируем в текст
        try:
            cleaned_bytes = bytearray()
            for byte in string_bytes:
                if byte in [0x09, 0x0A, 0x0D, 0x00]:  # таб, LF, CR, нулевой байт - сохраняем как есть
                    cleaned_bytes.append(byte)
                elif 0x20 <= byte <= 0x7E:  # печатные символы ASCII
                    cleaned_bytes.append(byte)
                else:
                    # Для кастомной кодировки проверяем таблицу
                    if byte in BYTE_TO_CHAR:
                        cleaned_bytes.append(byte)
                    else:
                        cleaned_bytes.append(0x3F)  # заменяем на '?' только неизвестные байты
            
            # Конвертируем в строку, сохраняя специальные символы
            text = ""
            for byte in cleaned_bytes:
                if byte == 0x09:    # таб
                    text += '\\t'
                elif byte == 0x0A:  # новая строка
                    text += '\\n'
                elif byte == 0x0D:  # возврат каретки
                    text += '\\r'
                elif byte == 0x00:  # нулевой байт
                    text += '\\0'
                elif 0x20 <= byte <= 0x7E:  # печатные символы
                    text += chr(byte)
                else:  # символы из кастомной кодировки
                    if byte in BYTE_TO_CHAR:
                        text += BYTE_TO_CHAR[byte]
                    else:
                        text += '?'  # fallback
            
            extracted_strings.append(text)
            
        except Exception as e:
            extracted_strings.append("[Ошибка декодирования: " + str(e) + "]")
    
    return extracted_strings

def save_text_blocks_to_file(input_filename, blocks, output_filename):
    """
    Сохраняет найденные текстовые блоки в файл с улучшенным форматом.
    """
    with open(str(output_filename), 'w', encoding='utf-8') as f:
        f.write("# Файл: " + input_filename + "\n")
        f.write("# Блоки: " + str(len(blocks)) + "\n")
        f.write("# Формат: BLOCK_NUM|HEADER_START|TEXT_START|BLOCK_END|STRING_COUNT|HAS_HEADER|VALIDATED\n")
        f.write("# Формат строки: STRING|TRANSLATE|ADDRESS|POINTER_VALUE|HAS_POINTER\n")
        f.write("# Escape-последовательности: \\0 (нулевой байт), \\t (таб), \\n (новая строка), \\r (возврат каретки)\n\n")
        
        for i, block in enumerate(blocks):
            f.write("### BLOCK {0:04d} ###\n".format(i))
            f.write("BLOCK_HEADER: {0:04d}|0x{1:08X}|0x{2:08X}|0x{3:08X}|{4}|{5}|{6}\n".format(
                i, block['header_start'], block['text_start'], block['block_end'],
                block['string_count'], int(block['has_header']), int(block.get('validated', False))))
            f.write("# SIZES: HEADER={0} TEXT={1} TOTAL={2}\n".format(
                block['header_size'], block['text_size'], block['total_size']))
            f.write("# POINTERS: " + str(len(block['pointers'])) + "\n")
            
            # Извлекаем текст для этого блока
            strings_text = extract_text_from_file(input_filename, block)
            
            for j, (string_addr, text) in enumerate(zip(block['strings'], strings_text)):
                # Получаем поинтер для этой строки если есть
                has_pointer = string_addr in block['string_pointers']
                pointer_val = block['string_pointers'].get(string_addr, (0, 0xFFFF))[1]
                
                # УБИРАЕМ лишнее экранирование - оставляем как есть
                # text уже содержит правильные escape-последовательности: \n, \t, \r, \0
                f.write("STRING: " + text + "\n")
                f.write("TRANSLATE: \n")
                f.write("METADATA: 0x{0:08X}|0x{1:04X}|{2}\n".format(string_addr, pointer_val, int(has_pointer)))
                f.write("END_STRING\n\n")
            
            f.write("END_BLOCK\n\n")

def parse_text_blocks_file(filename):
    """
    Парсит улучшенный файл с текстовыми блоками.
    """
    blocks = {}
    
    try:
        with open(str(filename), 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print("Ошибка чтения файла " + filename + ": " + str(e))
        return blocks
    
    current_block = None
    current_string = None
    
    for line in content.split('\n'):
        line = line.strip()
        
        if line.startswith('### BLOCK '):
            block_num = int(line.split()[2])
            current_block = {
                'block_num': block_num,
                'addresses': {},
                'pointers': [],
                'string_pointers': {},
                'strings': []
            }
            blocks[block_num] = current_block
        
        elif line.startswith('BLOCK_HEADER: '):
            if current_block:
                addr_info = line.replace('BLOCK_HEADER: ', '').split('|')
                current_block['addresses'] = {
                    'header_start': int(addr_info[1], 16),
                    'text_start': int(addr_info[2], 16),
                    'block_end': int(addr_info[3], 16),
                    'string_count': int(addr_info[4]),
                    'has_header': bool(int(addr_info[5])),
                    'validated': bool(int(addr_info[6]))
                }
        
        elif line.startswith('STRING: '):
            if current_block and current_string is None:
                text = line.replace('STRING: ', '')
                # Текст уже содержит правильные escape-последовательности: \n, \t, \r, \0
                # НИКАКОГО дополнительного преобразования не нужно!
                
                current_string = {
                    'original': text,
                    'translate': '',
                    'address': 0,
                    'pointer': 0xFFFF,
                    'has_pointer': False
                }
        
        elif line.startswith('TRANSLATE: '):
            if current_string:
                text = line.replace('TRANSLATE: ', '')
                # Перевод тоже содержит готовые escape-последовательности
                current_string['translate'] = text
        
        elif line.startswith('METADATA: '):
            if current_string:
                meta_info = line.replace('METADATA: ', '').split('|')
                current_string['address'] = int(meta_info[0], 16)
                current_string['pointer'] = int(meta_info[1], 16)
                current_string['has_pointer'] = bool(int(meta_info[2]))
                
                if current_string['pointer'] != 0xFFFF:
                    current_block['pointers'].append(current_string['pointer'])
                    current_block['string_pointers'][current_string['address']] = (0, current_string['pointer'])
        
        elif line == 'END_STRING':
            if current_block and current_string:
                current_block['strings'].append(current_string)
                current_string = None
        
        elif line == 'END_BLOCK':
            current_block = None
    
    return blocks

def update_file_with_translation(original_filename, blocks_data, output_filename, block_num, use_translate=True):
    """
    Обновляет файл переведенным текстом, корректируя поинтеры.
    """
    if block_num not in blocks_data:
        print("Ошибка: блок " + str(block_num) + " не найден")
        return False

    # Загружаем таблицу кодировки
    if not load_encoding_table():
        return False

    block = blocks_data[block_num]
    header_start = block['addresses']['header_start']
    text_start = block['addresses']['text_start']
    original_block_end = block['addresses']['block_end']
    has_header = block['addresses']['has_header']

    try:
        # Читаем исходный файл
        with open(str(original_filename), 'rb') as f:
            original_data = bytearray(f.read())
    except Exception as e:
        print("Ошибка чтения исходного файла: " + str(e))
        return False

    # Создаем новую версию данных
    new_data = original_data.copy()

    # Подготавливаем новые строки и вычисляем новые позиции
    new_strings_data = []
    string_new_positions = {}  # маппинг старый_адрес -> новый_адрес
    current_text_pos = text_start

    print("Кодирование строк...")
    total_strings = len(block['strings'])
    
    for string_index, string_info in enumerate(block['strings']):
        if use_translate:
            text_to_use = string_info['translate']
            # Проверка на пустой перевод
            if not text_to_use.strip():
                text_to_use = string_info['original']
                print("  Предупреждение: для строки по адресу 0x{0:08X} перевод пустой, используется оригинал".format(string_info['address']))
        else:
            text_to_use = string_info['original']

        old_string_addr = string_info['address']

        # Сохраняем новую позицию для этой строки
        string_new_positions[old_string_addr] = current_text_pos

        # Конвертируем текст в байты по кастомной таблице
        try:
            # Восстанавливаем специальные символы
            text_to_use = text_to_use.replace('\\t', '\t').replace('\\n', '\n').replace('\\r', '\r')

            # Кодируем по кастомной таблице
            string_bytes = encode_text_to_custom(text_to_use)

            # Добавляем нулевой байт в конце строки, НО НЕ ДЛЯ ПОСЛЕДНЕЙ СТРОКИ В БЛОКЕ
            # Последняя строка заканчивается маркером конца блока, а не нулевым байтом
            is_last_string = (string_index == total_strings - 1)
            
            if not is_last_string:
                string_bytes += b'\x00'
                print("  Строка {0:2d}/{1:2d}: 0x{2:08X} -> 0x{3:08X} ({4} байт) +0x00".format(
                    string_index, total_strings-1, old_string_addr, current_text_pos, len(string_bytes)))
            else:
                print("  Строка {0:2d}/{1:2d}: 0x{2:08X} -> 0x{3:08X} ({4} байт) [последняя]".format(
                    string_index, total_strings-1, old_string_addr, current_text_pos, len(string_bytes)))

            new_strings_data.append((old_string_addr, string_bytes, is_last_string))
            current_text_pos += len(string_bytes)

        except Exception as e:
            print("Ошибка обработки строки по адресу 0x{0:08X}: {1}".format(old_string_addr, str(e)))
            return False

    # Вычисляем новый размер текстового блока
    total_new_text_size = current_text_pos - text_start
    original_text_size = original_block_end - text_start

    print("Размер текстового блока: {0}/{1} байт".format(total_new_text_size, original_text_size))

    # Проверяем размер нового текстового блока
    if total_new_text_size > original_text_size:
        print("ОШИБКА: Новый текстовый блок больше оригинального!")
        print("Превышение на: {0} байт".format(total_new_text_size - original_text_size))
        
        print("\nДИАГНОСТИКА:")
        print("Начало текста: 0x{0:08X}".format(text_start))
        print("Конец текста (оригинал): 0x{0:08X}".format(original_block_end))
        print("Конец текста (новый): 0x{0:08X}".format(current_text_pos))
        
        # Покажем размеры каждой строки
        current_pos = text_start
        for i, (old_addr, string_bytes, is_last) in enumerate(new_strings_data):
            print("Строка {0:2d}: 0x{1:08X}-0x{2:08X} ({3} байт) {4}".format(
                i, current_pos, current_pos + len(string_bytes), len(string_bytes), '[последняя]' if is_last else ''))
            current_pos += len(string_bytes)
        
        print("Обновление отменено.")
        return False

    # Записываем новые строки в текстовую часть
    print("Запись новых строк...")
    current_text_pos = text_start
    for old_string_addr, string_bytes, is_last_string in new_strings_data:
        for i, byte in enumerate(string_bytes):
            if current_text_pos + i < len(new_data):
                new_data[current_text_pos + i] = byte
        current_text_pos += len(string_bytes)

    # Дополняем оставшееся пространство нулями если новый блок меньше
    if current_text_pos < original_block_end:
        fill_bytes = original_block_end - current_text_pos
        print("Дополнение нулями: {0} байт (0x{1:08X}-0x{2:08X})".format(fill_bytes, current_text_pos, original_block_end))
        for i in range(current_text_pos, original_block_end):
            new_data[i] = 0x00
    elif current_text_pos == original_block_end:
        print("Размер блока совпадает с оригиналом")
    else:
        # Этого не должно случиться, т.к. мы проверили размер выше
        print("КРИТИЧЕСКАЯ ОШИБКА: current_text_pos ({0}) > original_block_end ({1})".format(current_text_pos, original_block_end))
        return False

    # Обновляем поинтеры в заголовке если есть заголовок
    if has_header and block['pointers']:
        print("Обновление поинтеров в заголовке...")

        # Восстанавливаем оригинальные позиции поинтеров из файла
        try:
            with open(str(original_filename), 'rb') as f:
                original_file_data = f.read()
        except Exception as e:
            print("Ошибка чтения оригинального файла для восстановления поинтеров: " + str(e))
            return False

        # Находим позиции поинтеров в оригинальном файле
        for string_info in block['strings']:
            old_pointer = string_info.get('pointer', 0xFFFF)
            if old_pointer != 0xFFFF:
                old_string_addr = string_info['address']

                # Ищем позицию этого поинтера в заголовке
                for pos in range(header_start, text_start - 1, 2):
                    if pos + 1 < len(original_file_data):
                        current_pointer = struct.unpack('<H', original_file_data[pos:pos+2])[0]
                        if current_pointer == old_pointer:
                            # Нашли позицию поинтера, обновляем его
                            new_string_addr = string_new_positions.get(old_string_addr)
                            if new_string_addr is not None:
                                new_pointer = new_string_addr - header_start
                                # Записываем новый поинтер
                                new_data[pos] = new_pointer & 0xFF
                                new_data[pos + 1] = (new_pointer >> 8) & 0xFF
                                print("  Поинтер 0x{0:08X}: 0x{1:04X} -> 0x{2:04X}".format(pos, old_pointer, new_pointer))
                            break

    # Записываем обновленный файл
    try:
        with open(str(output_filename), 'wb') as f:
            f.write(new_data)
        print("[+] Файл успешно обновлен: " + output_filename)
        print("[+] Обновлено строк: " + str(len(new_strings_data)))
        if has_header:
            updated_pointers = len([p for p in block['pointers'] if p != 0xFFFF])
            print("[+] Обновлено поинтеров: " + str(updated_pointers))
        return True
    except Exception as e:
        print("Ошибка записи файла: " + str(e))
        return False

def update_all_blocks_in_file(original_filename, translation_filename, output_filename=None, use_translate=True):
    """
    Обновляет все блоки в файле на основе файла перевода.
    """
    if output_filename is None:
        output_filename = original_filename

    # Парсим файл перевода
    blocks_data = parse_text_blocks_file(translation_filename)
    if not blocks_data:
        print("[!] Не удалось загрузить данные блоков из файла перевода")
        return False

    print("[+] Загружено блоков: " + str(len(blocks_data)))

    # Создаем резервную копию
    backup_file = original_filename + '.bak'
    if not os.path.exists(backup_file):
        shutil.copy2(original_filename, backup_file)
        print("[+] Создана резервная копия: " + backup_file)

    # Обновляем все блоки
    success_count = 0
    total_blocks = len(blocks_data)

    for block_num in range(total_blocks):
        print("[+] Обновление блока " + str(block_num) + "...")

        success = update_file_with_translation(
            original_filename=original_filename,
            blocks_data=blocks_data,
            output_filename=output_filename,
            block_num=block_num,
            use_translate=use_translate
        )

        if success:
            success_count += 1
            print("[+] Блок " + str(block_num) + " успешно обновлен")
        else:
            print("[!] Ошибка при обновлении блока " + str(block_num))

    print("[+] Итог: успешно обновлено {0}/{1} блоков".format(success_count, total_blocks))
    return success_count > 0


def find_text_in_folder(folder_path, max_blocks=1000, min_length=3):
    """
    Ищет текстовые блоки во всех файлах в папке.
    """
    bin_files = list(Path(folder_path).glob("*.bin"))
    total_files = len(bin_files)
    processed_files = 0
    total_blocks = 0
    total_strings = 0

    print("[+] Поиск текстовых блоков в " + str(total_files) + " файлах...")

    for file_path in bin_files:
        processed_files += 1

        # Определяем приоритетный файл (распакованный LZSS или оригинальный BIN)
        unpack_file = file_path.with_suffix('.lzss-dec')
        if unpack_file.exists():
            input_file = str(unpack_file)
            file_type = "LZSS-dec"
        else:
            input_file = str(file_path)
            file_type = "BIN"

        output_file = str(file_path.with_name(file_path.stem + "-text.txt"))

        print("[{0}/{1}] Обработка {2}: {3}".format(processed_files, total_files, file_type, file_path.name))

        try:
            blocks = find_text_blocks_improved(input_file, max_blocks, min_length)
            if blocks:
                save_text_blocks_to_file(input_file, blocks, output_file)
                file_blocks = len(blocks)
                file_strings = sum(block['string_count'] for block in blocks)
                total_blocks += file_blocks
                total_strings += file_strings

                print("    Найдено: {0} блоков, {1} строк -> {2}".format(file_blocks, file_strings, Path(output_file).name))
            else:
                print("    Текстовые блоки не найдены")

        except Exception as e:
            print("   [!] Ошибка при обработке: " + str(e))

    print("\n[+] ПОИСК ЗАВЕРШЕН:")
    print("   Обработано файлов: {0}/{1}".format(processed_files, total_files))
    print("   Найдено блоков: " + str(total_blocks))
    print("   Найдено строк: " + str(total_strings))

    return {
        'processed_files': processed_files,
        'total_files': total_files,
        'total_blocks': total_blocks,
        'total_strings': total_strings
    }

def main():
    parser = argparse.ArgumentParser(
        description='Улучшенный поиск и работа с текстовыми блоками',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Примеры использования:
  # Улучшенный поиск текстовых блоков
  python text_tool_improved.py find -i file.bin -o text_blocks.txt
  
  # Поиск с кастомными параметрами
  python text_tool_improved.py find -i file.bin -o text_blocks.txt -m 100 -l 2
  
  # Обновление файла с переводом
  python text_tool_improved.py update -i original.bin -t text_blocks.txt -o updated.bin -b 0 --use-translate
        '''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Команда')
    
    # Парсер для команды find
    find_parser = subparsers.add_parser('find', help='Улучшенный поиск текстовых блоков')
    find_parser.add_argument('-i', '--input', required=True, help='Входной файл для поиска')
    find_parser.add_argument('-o', '--output', required=True, help='Файл для сохранения блоков')
    find_parser.add_argument('-m', '--max-blocks', type=int, default=1000, 
                           help='Максимальное количество блоков (по умолчанию: 1000)')
    find_parser.add_argument('-l', '--min-length', type=int, default=3,
                           help='Минимальная длина строки (по умолчанию: 3)')
    
    # Парсер для команды update
    update_parser = subparsers.add_parser('update', help='Обновление файла с переводом')
    update_parser.add_argument('-i', '--input', required=True, help='Исходный файл')
    update_parser.add_argument('-t', '--translation', required=True, help='Файл с переводами')
    update_parser.add_argument('-o', '--output', required=True, help='Выходной файл')
    update_parser.add_argument('-b', '--block', type=int, required=True, help='Номер блока для обновления')
    update_group = update_parser.add_mutually_exclusive_group(required=True)
    update_group.add_argument('--use-translate', action='store_true', help='Использовать перевод')
    update_group.add_argument('--use-original', action='store_true', help='Использовать оригинал')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'find':
            print("Улучшенный поиск текстовых блоков в файле: " + args.input)
            blocks = find_text_blocks_improved(args.input, args.max_blocks, args.min_length)
            print("Найдено блоков: " + str(len(blocks)))
            
            if blocks:
                save_text_blocks_to_file(args.input, blocks, args.output)
                print("Блоки сохранены в: " + args.output)
                
                # Детальная статистика
                blocks_with_headers = sum(1 for b in blocks if b['has_header'])
                validated_blocks = sum(1 for b in blocks if b.get('validated', False))
                total_strings = sum(block['string_count'] for block in blocks)
                total_pointers = sum(len(block['pointers']) for block in blocks)
                
                print("Блоков с заголовками: {0}/{1}".format(blocks_with_headers, len(blocks)))
                print("Валидированных блоков: {0}/{1}".format(validated_blocks, len(blocks)))
                print("Всего строк: " + str(total_strings))
                print("Всего поинтеров: " + str(total_pointers))
            else:
                print("Текстовые блоки не найдены")
        
        elif args.command == 'update':
            print("Обновление файла " + args.input + " блоком " + str(args.block))
            blocks_data = parse_text_blocks_file(args.translation)
            
            if not blocks_data:
                print("Не удалось загрузить данные блоков")
                return
            
            use_translate = args.use_translate
            success = update_file_with_translation(
                args.input, blocks_data, args.output, args.block, use_translate
            )
            
            if success:
                print("Файл успешно обновлен")
        
    except Exception as e:
        print("Ошибка: " + str(e))
        traceback.print_exc()

if __name__ == "__main__":
    main()