# Vanguard Bandits PSX Tools by pav13 + deepseek + https://www.romhacking.net/forum/index.php?topic=40701.0

import argparse
import os
import sys
import struct
import shutil
import time
import warnings
from pathlib import Path
from itertools import repeat
"""
A fairly straight port of Haruhiko Okumura's LZSS codec from C.
Nothing really clever, and not very pythonic.  (I'm not that good at this honestly.)
"""

# Like its C equiv., has problems when idx isn't what it would like.  Tied to node init, and instead of attempting to fix this came up with an equally problematic ringless-ring encoder.
def encode(data, ring, limit, threshold, idx, fill, byteorder, condition=True):
    """
    Compresses [data], returning a bytes object.

    [ring] may be any size between 0x4000 and 0x100.
    [limit] set the longest length for a copy; proper values depend on ring and threshold.
    [threshold] is the shortest acceptable copy, minus one.
    [idx] is typically ring - limit but may differ on application.
    [fill] is used to initialize the ring.
        *) For text applications use a space (b' ', or ASCII code 0x20)
        *) Binary applications use a zero (b'\\0' or 0)
    [byteorder] sets the byteorder copy commands are written in.
        Usually this is 'little', but 'big' is also acceptable.
    [condition] sets the flag state used for literals and dictionary hits.
    """
    output = bytearray()
    if not data: return output

    # Initialize the ring buffer with a common fill value.
    if isinstance(fill, (bytes, bytearray)):
        fill = fill[0]
    rng = bytearray(repeat(fill, ring + limit))
    matchlen, matchpos, nil = 0, 0, ring
    # Initialize the trees.
    lson= list(bytes(ring + 1))
    rson= list(bytes(ring + 1))
    rson.extend(repeat(nil, 256))
    dad = list(repeat(nil, ring + 1))

    # Create the masks for encoding values.
    # This assumes minimum ring of 0x100, maximum length of 0x100 + threashold + 1.
    r_mask = ring - 1
    b_shft = r_mask.bit_length() - 8
    b_mask = (0xFF00 >> b_shft) & 0xFF
    condition = 0x80 if condition else 0
    noncondition = condition ^ 0x80

    def InsertNode(v):
        """Inserts string into trees and returns
        longest match position and length as a tuple.
        If match length equals the limit, it replaces the old node.
        By embedding this function it can use the trees and ring globally."""
        cmp, ml, mp = 1, 0, matchpos
        key = rng[v:]
        pos = ring + 1 + key[0]
        rson[v] = nil
        lson[v] = nil
        while True:
            if cmp>=0:
                if rson[pos] != nil:
                    pos = rson[pos]
                else:
                    rson[pos] = v
                    dad[v] = pos
                    return (ml, mp)
            else:
                if lson[pos] != nil:
                    pos = lson[pos]
                else:
                    lson[pos] = v
                    dad[v] = pos
                    return (ml, mp)
            for i in range(1, limit+1):
                cmp = key[i] - rng[pos + i]
                if cmp:
                    break
            if i > ml:
                mp, ml = pos, i
                if ml >= limit: break
        dad[v] = dad[pos]
        lson[v]=lson[pos]
        rson[v]=rson[pos]
        dad[lson[pos]] = v
        dad[rson[pos]] = v
        if rson[dad[pos]] == pos:
            rson[dad[pos]] = v
        else:
            lson[dad[pos]] = v
        dad[pos] = nil
        return (ml, mp)

    def DeleteNode(pos):
        if dad[pos] == nil: return
        # If it's in the tree, delete it.
        q = lson[pos]
        if lson[pos] == nil:
            q = rson[pos]
        elif rson[pos] != nil:
            if rson[q] != nil:
                while True:
                    q = rson[q]
                    if rson[q] == nil: break
                rson[dad[q]] = lson[q]
                dad[lson[q]] = dad[q]
                lson[q] = lson[pos]
                dad[lson[pos]] = q
            rson[q] = rson[pos]
            dad[rson[pos]] = q
        dad[q] = dad[pos]
        if rson[dad[pos]] == pos:
            rson[dad[pos]] = q
        else:
            lson[dad[pos]] = q
        dad[pos] = nil

    # Unset flags on copies; send when less than 256.
    mask = 0xFF00
    codebuf = bytearray()
    s = 0
    # Read limit bytes into the ring at idx.
    p = min(limit, len(data)-1)
    rng[idx:idx+p] = data[0:p]
    cur = p
    for i in range(1, limit+1):
        matchlen, matchpos = InsertNode(idx - i)
    matchlen, matchpos = InsertNode(idx)
    # Now you're initialized, so do the rest of the file.
    while True:
        mask>>=1
        matchlen = min(matchlen, p)
        if matchlen <= threshold:
            matchlen = 1
            codebuf.append(rng[idx])
            mask ^= noncondition
        else:
            mask ^= condition
            a = (matchpos>>b_shft) & b_mask
            a |= (matchlen - threshold - 1)
            b = matchpos&0xFF
            if byteorder == 'little':
                codebuf.extend((b,a))
            else:
                codebuf.extend((a,b))
        # Flush when the mask is full.
        if mask < 256:
            output.append(mask)
            output.extend(codebuf)
            codebuf = bytearray()
            mask = 0xFF00
        prevmatchlen = matchlen
        j = min(prevmatchlen, len(data)-cur)
        for i in range(j):
            DeleteNode(s)
            rng[s] = data[cur]
            if s < (limit - 1):
                rng[s + ring] = data[cur]
            cur+=1
            # Correct the ring position via modulo ring
            s+=1
            s&= r_mask
            idx+=1
            idx&= r_mask
            matchlen, matchpos = InsertNode(idx)
        # Flush the rest of the buffer if necessary.
        for i in range(j, prevmatchlen):
            DeleteNode(s)
            s+=1
            s&= r_mask
            idx+=1
            idx&= r_mask
            p-=1
            if p:
                matchlen, matchpos = InsertNode(idx)
        # Loop until source empty.
        if not p:
            break
    # Flush remaining output; mask the lead bit off the mask.
    if codebuf:
        ## mask &= ~(1<<mask.bit_length()-1)   # bottom to top bitorder.
        l = mask.bit_length() - 8
        # mask &= 0xFF   # ??? DDDel ???
        # mask_byte = mask >> 8     # ??? DDDel ???
        output.append(mask>>l)
        output.extend(codebuf)
    return output

def decode(data, out_sz, ring, threshold, idx, fill, byteorder, bitorder='bottom', condition=True, count=-1, relative=False):
    """
    Decompresses [data] originally compressed with encode(),
        returning a bytes object.
    if [out_sz] is None, will decompress to the end of file.
    [ring], [threshold], [idx], [fill], and [byteorder]
        should match the original compression settings.

    [ring] may be any size between 0x4000 and 0x100.
    [threshold] is the shortest acceptable copy, minus one.
    [idx] is typically ring - limit but may differ on application.
    [fill] is used to initialize the ring.
        *) For text applications use a space (b' ', or ASCII code 0x20)
        *) Binary applications use a zero (b'\\0' or 0)
    [byteorder] sets the byteorder copy commands are written in.
        Usually this is 'little', but 'big' is also acceptable.
    [bitorder] indicates if command bits are read from the 'bottom' or 'top'.
    [condition] sets if a literal is written when a flag is True or False.
    [count], when set, terminates decompression after the given number of commands.
    [relative], if True, effectively is ringless.
    """
    output, buffer = bytearray(), bytearray(ring)
    # set up ring buffer
    if fill:
        if isinstance(fill, str):
            fill = fill.encode()
        if isinstance(fill, (bytes, bytearray)):
            fill = fill[0]
        buffer[0:idx] = repeat(fill, idx)
    bits = 0
    c_mask = 0
    c_refill = 1 if bitorder=='bottom' else 0x80
    d = iter(data)

    r_mask = ring-1
    threshold += 1
    b_shift = r_mask.bit_length() - 8
    s_mask = (0xFF >> b_shift) & 0xFF
    b_mask = s_mask ^ 0xFF

    try:
     while count:
        #if bits<2:
        #    bits = next(d) | 0x100
        #if(bits&1):
        if not c_mask:
            bits = next(d)
            c_mask = c_refill
        count -= 1
        if bool(bits&c_mask) == condition:
            v = next(d)
            buffer[idx]=v
            idx=(idx+1)&r_mask
            output.append(v)
        else:
            if byteorder == 'little':
                val = next(d)
                size = next(d)
            else:
                size = next(d)
                val = next(d)
            back = (size & b_mask) << b_shift
            back &= 0xFF00
            back |= val
            # back &= r_mask
            size = (size & s_mask) + threshold
            if relative:
                for x in range(size):
                    buffer[idx] = output[-back]
                    output.append(output[-back])
                    idx=(idx+1)&r_mask
            else:
                for x in range(size):
                    buffer[idx] = buffer[back]
                    output.append(buffer[back])
                    idx=(idx+1)&r_mask
                    back = (back+1)&r_mask
        #bits>>=1
        if bitorder == 'bottom':
            c_mask <<= 1
        else:
            c_mask >>= 1
        c_mask &= 0xFF
        if out_sz:
            if out_sz<=len(output):
                break
    except IndexError:
        warnings.warn("\tError!  Insufficient data.\n  Probably not an LZSS file.\n")
        return bytes()
    except StopIteration as E:
        if out_sz:
            raise E
    return bytes(output)

def length(data, out_sz, ring, threshold, byteorder, bitorder='bottom', condition=True, count=-1):
    """
    Returns (compressed size, decompressed size).
    if [out_sz] is None, will decompress to the end of file.
    [ring], [threshold], and [byteorder]
        should match the original compression settings.

    [ring] may be any size between 0x4000 and 0x100.
    [threshold] is the shortest acceptable copy, minus one.
    [byteorder] sets the byteorder copy commands are written in.
        Usually this is 'little', but 'big' is also acceptable.
    [bitorder] indicates if command bits are read from the 'bottom' or 'top'.
    [condition] sets if a literal is written when a flag is True or False.
    [count], when set, terminates decompression after the given number of commands.
    """
    sz, out = 0, 0
    bits = 0
    c_mask = 0
    c_refill = 1 if bitorder=='bottom' else 0x80

    r_mask = ring-1
    threshold += 1
    b_shift = r_mask.bit_length() - 8
    s_mask = (0xFF >> b_shift) & 0xFF

    try:
     while count:
        if not c_mask:
            bits = data[sz]
            sz += 1
            c_mask = c_refill
        count -= 1
        if bool(bits&c_mask) == condition:
            v = data[sz]
            sz += 1
            out += 1
        else:
            if byteorder == 'little':
                val = data[sz]
                size = data[sz+1]
            else:
                size = data[sz]
                val = data[sz+1]
            sz += 2
            out += (size & s_mask) + threshold
        if bitorder == 'bottom':
            c_mask <<= 1
        else:
            c_mask >>= 1
        c_mask &= 0xFF
        if out_sz:
            if out_sz<=out:
                break
    except Exception as E:
        print(E)
        # Still return progress to this point.
    return (sz, out)

__modes = {'txt':0x20, 'bin':0}

def encode1KB(data, mode='bin', **kwargs):
    """Compresses [data] using 1KB ring and given fill mode,
        returning a bytes object.
    [mode] may be:
        'txt': fills buffer with spaces (b' ', or ASCII code 0x20)
        'bin': fills buffer with zeroes
    same as:
        encode(data, 1024, 66, 2, 958, mode, 'little', False)
    """
    f = __modes.get(mode)
    return encode(data, ring=1024, limit=66, threshold=2, idx=kwargs.pop('idx', 958), fill=f, byteorder=kwargs.pop('byteorder', 'little'), condition=kwargs.pop('condition', False), **kwargs)

def decode1KB(data, out_sz=None, mode='bin', **kwargs):
    """Decompresses [data] using 1KB ring and given fill [mode],
        returning a bytes object.
    If [out_sz] is not given, decompresses to the end of data.
    [mode] may be:
        'txt': fills buffer with spaces (b' ', or ASCII code 0x20)
        'bin': fills buffer with zeroes
    same as:
        decode(data, out_sz, 1024, 2, 958, mode, 'little', 'bottom', False)
    """
    f = __modes.get(mode)
    return decode(data, out_sz, ring=1024, threshold=2, idx=kwargs.pop('idx', 958), fill=f, byteorder=kwargs.pop('byteorder', 'little'), condition=kwargs.pop('condition', False), **kwargs)

def length1KB(data, out_sz=None, **kwargs):
    """Returns (compressed size, decompressed size) of [data] using 1KB ring,
        basically by faking decompression.
    If [out_sz] is not given, "decompresses" to the end of data.
    same as:
        length(data, out_sz, 1024, 2, 'little', 'bottom', False)
    """
    return length(data, out_sz, ring=1024, threshold=2, byteorder=kwargs.pop('byteorder', 'little'), condition=kwargs.pop('condition', False), **kwargs)

def split(file_name=None, output_dir="extracted", folder_path=None):
    """
    Извлекает файлы из архива(ов)
    
    Args:
        file_name: Имя файла архива для извлечения (режим одного файла)
        output_dir: Папка для извлеченных файлов
        folder_path: Путь к папке для обработки всех архивов (режим папки)
    """
    print("\nНачало извлечения ... ")
    start_time = time.time()
    
    # Проверяем, что указан либо файл, либо папка
    if not file_name and not folder_path:
        raise ValueError("Должен быть указан либо file_name, либо folder_path")
    
    try:
        if folder_path:
            # РЕЖИМ ПАПКИ: обработка всех файлов в указанной папке
            folder = Path(folder_path)
            if not folder.exists() or not folder.is_dir():
                raise FileNotFoundError("Папка '" + folder_path + "' не существует")
            
            print("Обработка всех файлов в папке: " + folder_path)
            print("=" * 30)
            
            total_archives_processed = 0
            total_files_extracted = 0
            
            # Проходим по всем файлам в папке
            for file_path in sorted(folder.iterdir()):
                if file_path.is_file():
                    try:
                        # Создаем подпапку для каждого файла архива
                        base_name = file_path.stem
                        file_output_dir = Path(output_dir) / (base_name + "-extracted")
                        if not file_output_dir.exists():
                            file_output_dir.mkdir(parents=True)
                        
                        print("\nОбработка архива: " + file_path.name)
                        files_extracted = split_single_file(str(file_path), str(file_output_dir))
                        
                        total_archives_processed += 1
                        total_files_extracted += files_extracted
                        
                        print("[+] Извлечено " + str(files_extracted) + " файлов из " + file_path.name)
                        
                    except Exception as e:
                        print("[!] Ошибка при обработке файла " + file_path.name + ": " + str(e))
                        continue
            
            # Выводим итоговую статистику
            print("\n" + "=" * 30)
            print("ИТОГИ ИЗВЛЕЧЕНИЯ:")
            print("=" * 30)
            print("Обработано архивов: " + str(total_archives_processed))
            print("Всего извлечено файлов: " + str(total_files_extracted))
            
            end_time = time.time()
            total_time = end_time - start_time
            print("Общее время выполнения: {0:.2f} секунд".format(total_time))
            
            return total_files_extracted
            
        else:
            # РЕЖИМ ОДНОГО ФАЙЛА: извлечение из одного архива
            file_path = Path(file_name)
            if not file_path.exists() or not file_path.is_file():
                raise FileNotFoundError("Файл '" + file_name + "' не существует")
            
            print("Обработка архива: " + file_name)
            output_path = Path(output_dir)
            if not output_path.exists():
                output_path.mkdir(parents=True)
            
            files_extracted = split_single_file(file_name, output_dir)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            print("\n" + "=" * 30)
            print("ИТОГИ ИЗВЛЕЧЕНИЯ:")
            print("=" * 30)
            print("Извлечено файлов: " + str(files_extracted))
            print("Время выполнения: {0:.2f} секунд".format(total_time))
            
            return files_extracted
            
    except Exception as e:
        print("Критическая ошибка: " + str(e))
        return 0


def split_single_file(file_name, output_dir):
    """Вспомогательная функция для обработки одного файла архива"""
    start_time = time.time()
    
    # Создаем папку для извлеченных файлов
    output_path = Path(output_dir)
    if not output_path.exists():
        output_path.mkdir(parents=True)
    
    with open(str(file_name), 'rb') as f:  
        src = f.read()
    
    file_size = len(src)
    print("Размер файла: " + str(file_size) + " байт")
    
    # Предварительный подсчет количества файлов
    total_files = 0
    temp_index = 0
    
    while True:
        offset = temp_index << 3
        if offset + 8 > file_size:
            break
        data_offset, data_size = struct.unpack("<LL", src[offset:offset+8])
        if data_offset == 0:
            break
        if data_offset + data_size <= file_size:
            total_files += 1
        temp_index += 1
    
    print("Найдено файлов для извлечения: " + str(total_files))
    
    if total_files == 0:
        print("Файлы для извлечения не найдены!")
        return 0
    
    # Основной цикл извлечения
    index = 0
    files_extracted = 0
    last_percent = -1
    
    while True:
        offset = index << 3
        
        # Проверяем, не вышли ли за пределы файла
        if offset + 8 > file_size:
            break
            
        # Читаем запись из таблицы содержания
        data_offset, data_size = struct.unpack("<LL", src[offset:offset+8])
        
        # Если data_offset равен 0, прекращаем извлечение
        if data_offset == 0:
            break
            
        # Проверяем валидность данных
        if data_offset + data_size > file_size:
            # Пропускаем некорректные записи, но продолжаем
            index += 1
            continue
        
        # Извлекаем данные
        extracted_data = src[data_offset:data_offset+data_size]
        
        # Сохраняем с правильным именем
        output_filename = output_path / ("file_{0:04d}.bin".format(index))
        with open(str(output_filename), 'wb') as f: 
            f.write(extracted_data)
        
        files_extracted += 1
        
        # Вывод прогресса
        percent = (files_extracted * 100) // total_files
        if percent != last_percent:
            print("Прогресс: {0}% ({1}/{2}) - файл {3:04d}, размер: {4} байт".format(percent, files_extracted, total_files, index, data_size))
            last_percent = percent
        
        index += 1
    
    return files_extracted

def build(input_dir, output_file="EPICA.bin", alignment=0x800, verify=False, detailed=False):
    """
    Собирает файлы из папки обратно в архив с таблицей содержания в начале
    Первый файл начинается с смещения 0x1800
    
    Args:
        input_dir: Папка с извлеченными файлами (формат file_XXXX.bin)
        output_file: Имя выходного файла архива
        alignment: Выравнивание между файлами (0x800 = 2048 байт)
    """
    print("Сборка файла " + output_file + " ...")
    start_time = time.time()
    
    # Получаем список файлов в папке
    input_path = Path(input_dir)
    if not input_path.exists():
        raise FileNotFoundError("Папка '" + input_dir + "' не найдена")

    # Шаг 2: Ищем файлы в формате file_XXXX.bin для сборки архива
    file_pattern = "file_*.bin"
    files = sorted(input_path.glob(file_pattern))
    
    # if not files:
        # Пробуем альтернативный паттерн
        # file_pattern = "*.bin"
        # files = sorted(input_path.glob(file_pattern))
        
    if not files:
        raise FileNotFoundError("В папке '" + input_dir + "' не найдены файлы .bin для сборки архива")
    
    print("Найдено частей для сборки: " + str(len(files)))
    
    # Собираем данные файлов
    file_data = []
    file_sizes = []
    
    # Читаем все файлы
    for file_path in files:
        with open(str(file_path), 'rb') as f:
            data = f.read()
        file_data.append(data)
        file_sizes.append(len(data))
        if detailed:
            print("Прочитан файл " + file_path.name + ", размер: " + str(len(data)) + " байт")
    
    # Вычисляем размер таблицы содержания (8 байт на файл + 8 байт нулевая запись в конце)
    toc_size = (len(files) + 1) * 8
    print("Размер таблицы содержания: " + str(toc_size) + " байт")
    
    # Первый файл начинается с 0x1800
    first_file_offset = 0x1800
    
    # Проверяем, что таблица содержания помещается до 0x1800
    if toc_size > first_file_offset:
        raise ValueError("Таблица содержания слишком большая (" + str(toc_size) + " байт) для смещения 0x{0:X}".format(first_file_offset))
    
    # Вычисляем смещения для данных файлов
    current_offset = first_file_offset
    aligned_offsets = []
    
    # Вычисляем выровненные смещения для каждого файла
    for i, size in enumerate(file_sizes):
        aligned_offsets.append(current_offset)
        # Выравниваем следующий offset
        current_offset += size
        # Добавляем выравнивание (блок нулей)
        padding = (alignment - (current_offset % alignment)) % alignment
        current_offset += padding
    
    # print(f"Первый файл начинается с: 0x{first_file_offset:08X}")
    # print(f"Общий размер данных с выравниванием: {current_offset - first_file_offset} байт")
    print("Общий размер файла: " + str(current_offset) + " байт")
    
    # Собираем архив
    archive_data = bytearray()
    
    # 1. Записываем таблицу содержания в НАЧАЛО (с 0x0000)
    for i, data in enumerate(file_data):
        data_offset = aligned_offsets[i]
        data_size = len(data)
        toc_entry = struct.pack("<LL", data_offset, data_size)
        archive_data.extend(toc_entry)
        if detailed:
            print("Таблица: файл {0:04d} -> смещение=0x{1:08X}, размер={2} байт".format(i, data_offset, data_size))
    
    # Добавляем нулевую запись в конец таблицы
    archive_data.extend(struct.pack("<LL", 0, 0))
    
    # 2. Заполняем пространство между таблицей и первым файлом нулями
    current_pos = len(archive_data)
    if current_pos < first_file_offset:
        padding_size = first_file_offset - current_pos
        archive_data.extend(b'\x00' * padding_size)
        if detailed:
            print("Заполнение до 0x{0:08X}: {1} байт нулей".format(first_file_offset, padding_size))
    
    # 3. Записываем данные файлов с выравниванием
    for i, data in enumerate(file_data):
        current_pos = len(archive_data)
        expected_pos = aligned_offsets[i]
        
        # Проверяем текущую позицию
        if current_pos != expected_pos:
            print("Ошибка: текущая позиция 0x{0:08X}, ожидалась 0x{1:08X}".format(current_pos, expected_pos))
            # Добавляем выравнивание если нужно
            if current_pos < expected_pos:
                padding_size = expected_pos - current_pos
                archive_data.extend(b'\x00' * padding_size)
                if detailed:
                    print("Выравнивание перед файлом {0:04d}: {1} байт".format(i, padding_size))
            else:
                raise ValueError("Переполнение: текущая позиция 0x{0:08X} > ожидаемой 0x{1:08X}".format(current_pos, expected_pos))
        
        # Записываем данные файла
        archive_data.extend(data)
        if detailed:
            print("Файл {0:04d}: записан по смещению 0x{1:08X}, размер={2} байт".format(i, aligned_offsets[i], len(data)))
        
        # Добавляем выравнивание после файла (кроме последнего)
        if i < len(file_data) - 1:
            current_pos = len(archive_data)
            next_offset = aligned_offsets[i + 1]
            padding_size = next_offset - current_pos
            if padding_size > 0:
                archive_data.extend(b'\x00' * padding_size)
                if detailed:
                    print("Выравнивание после файла {0:04d}: {1} байт".format(i, padding_size))
    
    # Записываем архив в файл
    with open(str(output_file), 'wb') as f:
        f.write(archive_data)
    
    print('=' * 50)
    print("\nФайл успешно собран: " + output_file)
    if detailed:
        print("Размер таблицы содержания: " + str(toc_size) + " байт")
        print("Первый файл начинается с: 0x{0:08X}".format(first_file_offset))
        print("Количество файлов: " + str(len(files)))
        print("Общий размер данных: " + str(sum(file_sizes)) + " байт")
        print("Общий размер архива: " + str(len(archive_data)) + " байт")
        print("Размер выравнивания: " + str(len(archive_data) - sum(file_sizes) - first_file_offset) + " байт")
    
    end_time = time.time()
    print("Время выполнения: {0:.2f} секунд".format(end_time - start_time))
        
    # Проверяем целостность
    if verify:
        verify_pack(output_file, len(files))
    
    return len(archive_data)

def verify_pack(file_name, expected_files):
    """
    Проверяет целостность созданного файла
    """
    print('=' * 50)
    print("\nПроверка целостности сборки файла: " + file_name)
    
    with open(str(file_name), 'rb') as f:
        src = f.read()
    
    # Проверяем таблицу содержания
    index = 0
    files_found = 0
    
    while True:
        offset = index << 3  # index * 8
        
        if offset + 8 > len(src):
            break
            
        data_offset, data_size = struct.unpack("<LL", src[offset:offset+8])
        
        if data_offset == 0:
            break
            
        # Проверяем, что данные существуют
        if data_offset + data_size <= len(src):
            files_found += 1
            # print(f" Запись {index:04d}: смещение=0x{data_offset:08X}, размер={data_size} байт - OK")
        else:
            print(" Запись {0:04d}: смещение=0x{1:08X}, размер={2} байт - ERROR".format(index, data_offset, data_size))
        
        index += 1
    
    print("Проверено записей: {0} (ожидалось: {1})".format(files_found, expected_files))
    
    if files_found == expected_files:
        print(" Целостность архива подтверждена")
    else:
        print(" Ошибка целостности архива")

# Общий блок сигнатур для использования в разных функциях
LZSS_SIGNATURES = {
    b'\x82\x18\xBB\xC1': "LZSS-archive",    # 8218BBC1 
    b'\x0A\x10\xBB\xC0': "LZSS-archive",    # 0A10BBC0 
    b'\x4A\x10\xBB\xC0': "LZSS-archive",    # 4A10BBC0 
    b'\x82\x06\xBB\xC0': "LZSS-archive",    # 8206BBC0 
    b'\x0A\x41\xB7\xC4': "LZSS-archive",    # 0A41B7C4 
    b'\x2A\x06\xBB\xC0': "LZSS-archive",    # 2A06BBC0 
    b'\x00\x03\x00\x88': "LZSS-archive",    # 00030088 
    b'\x00\x58\x00\x58': "LZSS-archive",    # 00580058 
    b'\x02\x03\xBB\xC0': "LZSS-archive",    # 0203BBC0 
    b'\x82\x03\xBB\xC0': "LZSS-archive",    # 8203BBC0 
    b'\x02\x28\xBB\xC0': "LZSS-archive",    # 0228BBC0 
    b'\x02\x2C\xBB\xC0': "LZSS-archive",    # 022CBBC0 
    b'\x02\x20\xBB\xC0': "LZSS-archive",    # 0220BBC0 
    b'\x02\x30\xBB\xC0': "LZSS-archive",    # 0230BBC0 
    b'\x02\x40\xBB\xC0': "LZSS-archive",    # 0240BBC0 
    b'\x12\x24\xBB\xC0': "LZSS-archive",    # 1224BBC0 
    b'\x02\x34\xBB\xC0': "LZSS-archive",    # 0234BBC0 
    b'\x02\x38\xBB\xC0': "LZSS-archive",    # 0238BBC0 
    b'\x02\x3C\xBB\xC0': "LZSS-archive",    # 023CBBC0 
    b'\x02\x1C\xBB\xC0': "LZSS-archive",    # 021CBBC0 
    b'\x02\x24\xBB\xC0': "LZSS-archive",    # 0224BBC0 
    b'\x02\x28\xBB\xC1': "LZSS-archive",    # 0228BBC1 
    b'\x02\x28\xBA\xC1': "LZSS-archive",    # 0228BAC1 
    b'\x02\x44\xBB\xC0': "LZSS-archive",    # 0244BBC0 
    b'\x02\x40\xBA\xC1': "LZSS-archive",    # 0240BAC1 
    b'\x02\x30\xBA\xC1': "LZSS-archive",    # 0230BAC1 
    b'\x12\x2C\xBB\xC0': "LZSS-archive",    # 122CBBC0 
    b'\x02\x14\xBB\xC0': "LZSS-archive",    # 0214BBC0 
    b'\x0A\x14\xBB\xC0': "LZSS-archive",    # 0A14BBC0 
    b'\x02\x14\xBB\xC1': "LZSS-archive",    # 0214BBC1 
    b'\x02\x14\xBA\xC1': "LZSS-archive",    # 0214BAC1 
    b'\x2A\x14\xBB\xC0': "LZSS-archive",    # 2A14BBC0 
    b'\x4A\x14\xBB\xC0': "LZSS-archive",    # 4A14BBC0 
    b'\x12\x14\xBB\xC0': "LZSS-archive",    # 1214BBC0 
    b'\x0A\x24\xBB\xC0': "LZSS-archive",    # 0A24BBC0 
    b'\x4A\x24\xBB\xC0': "LZSS-archive",    # 4A24BBC0 
    b'\x2A\x24\xBB\xC0': "LZSS-archive",    # 2A24BBC0
}

IMAGE_SIGNATURES = {
    b'\x10\x00\x00\x00\x08\x00\x00\x00': "TIM-4bpp",  # 1000000008000000
    b'\x10\x00\x00\x00\x09\x00\x00\x00': "TIM-8bpp",  # 1000000009000000
    b'\x10\x00\x50\x00': "TIM_10005000",  # 10005000
    b'\x10\x00': "TIM_1000",  # 1000
}

OTHER_SIGNATURES = {
    b'\x41\x00\x00\x00\x00\x00\x00\x00': "model_3d",  # 4100000000000000
    b'\x00\x80\x08\x00': "uncompressed_data_text",  # 00800800
    b'\x00\x04': "unkn_0004",  # 0004
    b'\x04\x00\x00\x00': "unkn_04000000",  # 04000000
    b'\x06\x00\x00\x00': "unkn_06000000",  # 04000000
    b'\x00\x88\x00': "unkn_008800",  # 008800
}

def analyze(file_name="EPICA.bin", output_file=None, folder_path=None):
    """
    Анализирует структуру оригинального архива с проверкой сигнатур файлов
    
    Args:
        file_name: Имя файла архива для анализа (режим одного файла)
        output_file: Файл для сохранения отчета
        folder_path: Путь к папке для анализа (если указан - режим папки)
    """
    
    
    # Cигнатуры файлов
    signatures = {}
    signatures.update(LZSS_SIGNATURES)
    signatures.update(IMAGE_SIGNATURES)
    signatures.update(OTHER_SIGNATURES)
    
    print("\nНачало анализа ... ")
    start_time = time.time()
    
    # Если указан файл для вывода, меняем stdout
    original_stdout = sys.stdout
    if output_file:
        sys.stdout = open(output_file, 'w', encoding='utf-8')
    
    try:
        if folder_path:
            # РЕЖИМ ПАПКИ: анализ всех файлов в указанной папке
            folder = Path(folder_path)
            if not folder.exists() or not folder.is_dir():
                print("Ошибка: Папка '" + folder_path + "' не существует")
                return
            
            print("Анализ всех файлов в папке: " + folder_path)
            print("=" * 87)
            print("|Имя файла               |Сигнатура                |Первые 16 байт                    |")
            print("-" * 87)
            
            # Собираем статистику по типам файлов
            file_types_count = {}
            total_files = 0
            
            # Проходим по всем файлам в папке
            for file_path in sorted(folder.iterdir()):
                if file_path.is_file():
                    total_files += 1
                    file_type = "unknown"
                    
                    try:
                        with open(str(file_path), 'rb') as f:
                            file_header = f.read(16)  # Читаем первые 16 байт для проверки сигнатур
                        
                        # Проверяем все сигнатуры
                        for sig_bytes, sig_name in signatures.items():
                            if file_header.startswith(sig_bytes):
                                file_type = sig_name
                                break
                        
                        # Если не нашли полное совпадение, проверяем частичные совпадения
                        if file_type == "unknown":
                            # Проверяем первые 4 байта
                            first_4_bytes = file_header[:4]
                            for sig_bytes, sig_name in signatures.items():
                                if len(sig_bytes) >= 4 and first_4_bytes == sig_bytes[:4]:
                                    file_type = "partial_" + sig_name
                                    break
                    
                    except Exception as e:
                        file_type = "error_reading"
                    
                    # Обновляем статистику
                    if file_type not in file_types_count:
                        file_types_count[file_type] = 0
                    file_types_count[file_type] += 1
                    
                    # Форматируем первые 16 байт для вывода
                    try:
                        with open(str(file_path), 'rb') as f:
                            first_16_data = f.read(16)
                        
                        hex_groups = []
                        for i in range(0, len(first_16_data), 4):
                            group = first_16_data[i:i+4]
                            hex_group = ''.join('{0:02X}'.format(b) for b in group)
                            hex_groups.append(hex_group)
                        first_16_bytes = ' '.join(hex_groups)
                        
                    except Exception:
                        first_16_bytes = "Ошибка чтения"
                    
                    # Выводим информацию о файле
                    print("{0:<25} {1:<25} {2}".format(file_path.name, file_type, first_16_bytes))
            
            # Выводим статистику
            print("\n" + "=" * 30)
            print("СТАТИСТИКА ПО ТИПАМ ФАЙЛОВ:")
            print("=" * 30)
            print("Всего файлов в папке: " + str(total_files))
            print("-" * 30)
            
            # Сортируем по количеству файлов
            for file_type, count in sorted(file_types_count.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_files) * 100 if total_files > 0 else 0
                print("{0:<30} {1:4d} файлов ({2:5.1f}%)".format(file_type, count, percentage))
            
            return file_types_count
            
        else:
            # РЕЖИМ ОДНОГО ФАЙЛА: оригинальная логика анализа архива
            print("Анализ структуры: " + file_name)
            
            with open(str(file_name), 'rb') as f:
                src = f.read()
            
            file_size = len(src)
            print("Размер файла: {0} байт (0x{1:08X})".format(file_size, file_size))
            
            # Анализируем записи таблицы содержания
            index = 0
            files_info = []
            
            while True:
                offset = index << 3  # index * 8
                
                if offset + 8 > file_size:
                    break
                    
                data_offset, data_size = struct.unpack("<LL", src[offset:offset+8])
                
                if data_offset == 0:
                    break
                    
                files_info.append((index, data_offset, data_size))
                index += 1
            
            print("Найдено записей в таблицы содержания: " + str(len(files_info)))
            
            # Анализируем структуру данных с проверкой сигнатур
            if files_info:
                print("\nСтруктура данных:")
                print("|Файл |Смещение              |Размер     |Выравнивание|Сигнатура              |Первые 16 байт (LE)               |")
                print("-" * 114)
                
                for i, (idx, offset, size) in enumerate(files_info):
                    end_pos = offset + size
                    next_offset = files_info[i + 1][1] if i + 1 < len(files_info) else file_size
                    
                    gap = next_offset - end_pos if i + 1 < len(files_info) else 0
                    alignment = gap if gap < 0x100000 else ">1MB"
                    
                    # Проверяем сигнатуры файла
                    file_type = "unknown"
                    first_16_bytes = "N/A"
                    
                    if offset + 16 <= file_size:  # Проверяем, что можем прочитать 16 байт
                        file_header = src[offset:offset + 16]  # Читаем 16 для сигнатур
                        first_16_data = src[offset:offset + 16]  # Читаем 16 для отображения
                        
                        # Форматируем первые 16 байт в HEX с пробелом между каждыми 4 байтами
                        hex_groups = []
                        for i in range(0, len(first_16_data), 4):
                            group = first_16_data[i:i+4]
                            hex_group = ''.join('{0:02X}'.format(b) for b in group)
                            hex_groups.append(hex_group)
                        first_16_bytes = ' '.join(hex_groups)
                        
                        # Проверяем все сигнатуры
                        for sig_bytes, sig_name in signatures.items():
                            if file_header.startswith(sig_bytes):
                                file_type = sig_name
                                break
                        
                        # Если не нашли полное совпадение, проверяем частичные совпадения
                        if file_type == "unknown":
                            # Проверяем первые 4 байта
                            first_4_bytes = file_header[:4]
                            for sig_bytes, sig_name in signatures.items():
                                if len(sig_bytes) >= 4 and first_4_bytes == sig_bytes[:4]:
                                    file_type = "partial_" + sig_name
                                    break
                    else:
                        # Если файл слишком маленький для чтения 16 байт
                        available_bytes = file_size - offset
                        if available_bytes > 0:
                            first_12_data = src[offset:offset + min(16, available_bytes)]
                            # Форматируем доступные байты с пробелом между каждыми 4 байтами
                            hex_groups = []
                            for i in range(0, len(first_16_data), 4):
                                group = first_16_data[i:i+4]
                                hex_group = ''.join('{0:02X}'.format(b) for b in group)
                                hex_groups.append(hex_group)
                            first_16_bytes = ' '.join(hex_groups)
                            first_16_bytes += ' ' * (23 - len(first_16_bytes))  # Выравнивание
                        file_type = "too_small"
                    
                    print("{0:04d}:  0x{1:08X}-0x{2:08X}  {3:6d} байт   {4:>8}   {5:<23} {6}".format(idx, offset, end_pos, size, alignment, file_type, first_16_bytes))
                
                # Статистика по типам файлов
                print("\n" + "=" * 110)
                print("СТАТИСТИКА ПО ТИПАМ ФАЙЛОВ:")
                print("=" * 110)
                
                file_types_count = {}
                for idx, offset, size in files_info:
                    file_type = "unknown"
                    if offset + 16 <= file_size:
                        file_header = src[offset:offset + 16]
                        for sig_bytes, sig_name in signatures.items():
                            if file_header.startswith(sig_bytes):
                                file_type = sig_name
                                break
                    
                    if file_type not in file_types_count:
                        file_types_count[file_type] = 0
                    file_types_count[file_type] += 1
                
                # Сортируем по количеству файлов
                for file_type, count in sorted(file_types_count.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / len(files_info)) * 100
                    print("{0:<25} {1:4d} файлов ({2:5.1f}%)".format(file_type, count, percentage))
                        
            return files_info
            
    finally:
        # Восстанавливаем stdout
        if output_file:
            sys.stdout.close()
            sys.stdout = original_stdout
        
        print("\nАнализ завершен. Отчет: " + output_file)
        end_time = time.time()
        print("Время выполнения: {0:.2f} секунд".format(end_time - start_time))

def read_first_n_bytes(folder_path, n_bytes, output_file):
    """Обрабатывает все файлы в указанной папке"""
    try:
        with open(str(output_file), 'w', encoding='utf-8') as out_file:
            # Получаем список файлов в папке
            out_file.write("Анализ папки: " + folder_path + "\n")
            out_file.write("Предпросмотр первых " + str(n_bytes) + " байт каждого файла\n\n\n")
            
            file_count = 0
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                
                # Пропускаем папки, обрабатываем только файлы
                if os.path.isfile(file_path):
                    """Читает первые n_bytes байт файла и возвращает в требуемом формате"""
                    try:
                        with open(str(file_path), 'rb') as file:
                            first_n_bytes = file.read(n_bytes)
                            
                            # Если файл меньше n_bytes байт, дополняем нулями
                            if len(first_n_bytes) < n_bytes:
                                first_n_bytes += b'\x00' * (n_bytes - len(first_n_bytes))
                            
                            # Разбиваем на группы по 4 байта
                            bytes_groups = [
                                first_n_bytes[i:i+4] for i in range(0, n_bytes, 4)
                            ]
                            
                            # Форматируем байты в hex строку
                            formatted_bytes = ' '.join(
                                ''.join('{0:02X}'.format(b) for b in group) for group in bytes_groups
                            )
                            
                    except Exception as e:
                        return "Ошибка чтения: " + str(e)
                    
                    out_file.write(filename + ": " + formatted_bytes + "\n")
                    print("Обработан: " + filename)
                    file_count += 1
            
            if file_count == 0:
                print("В указанной папке нет файлов для обработки!")
                out_file.write("В указанной папке нет файлов для обработки!\n")
            else:
                print("\nОбработано файлов: " + str(file_count))
                    
        print("Результаты сохранены в файл: " + output_file)
        
    except Exception as e:
        print("Ошибка при обработке папки: " + str(e))

def unpack_lzss(input_file=None, output_file=None, unpack_all=False, search_folder=None):
    """
    Распаковывает файл(ы) используя decode1KB
    
    Args:
        input_file: Входной файл для распаковки (используется при unpack_all=False)
        output_file: Выходной файл (используется при unpack_all=False)
        unpack_all: Если True - распаковывает все файлы по сигнатурам, если False - один указанный файл
        search_folder: Папка для поиска файлов по сигнатурам (используется только при unpack_all=True)
    """
    start_time = time.time()
    
    if unpack_all:
        # Режим распаковки всех файлов по сигнатурам
        if search_folder is None:
            # Если папка не указана, используем текущую директорию
            input_path = Path.cwd()
        else:
            input_path = Path(search_folder)
        
        # Проверяем существование папки
        if not input_path.exists():
            print("Ошибка: Папка " + str(input_path) + " не существует")
            return
        
        processed_files = 0
        
        print("Поиск файлов с известными сигнатурами в папке: " + str(input_path))
        print("Всего LZSS сигнатур в базе: " + str(len(LZSS_SIGNATURES)))
        print("-" * 50)
        
        # Проходим по всем файлам в папке
        for file_path in input_path.iterdir():
            if file_path.is_file():
                try:
                    with open(str(file_path), 'rb') as f:
                        first_bytes = f.read(4)  # Читаем первые 4 байта
                    
                    # Проверяем совпадение с любым из шаблонов
                    if first_bytes in LZSS_SIGNATURES:
                        signature_hex = ''.join('{0:02X}'.format(b) for b in first_bytes)
                        # print(f"Найдена сигнатура {signature_hex} в файле: {file_path.name}")
                        
                        # Читаем весь файл
                        with open(str(file_path), 'rb') as f:
                            file_data = f.read()
                        
                        # Декодируем файл
                        try:
                            decoded_data = decode1KB(file_data)
                            original_size = len(file_data)
                            
                            # Сохраняем распакованный файл
                            output_path = file_path.with_suffix('.lzss-dec')
                            with open(str(output_path), 'wb') as f:
                                f.write(decoded_data)

                            print("[+] Файл " + file_path.name + " распакован в " + output_path.name)
                            # print(f"    Исходный: {original_size} байт, распакованный: {len(decoded_data)} байт")
                            processed_files += 1
                                
                        except Exception as e:
                            print("   Ошибка декодирования " + file_path.name + ": " + str(e))
                            
                except Exception as e:
                    print("Ошибка обработки файла " + file_path.name + ": " + str(e))
        
        print("-" * 50)
        print("Распаковано файлов: " + str(processed_files))
        end_time = time.time()
        print("Время выполнения: {0:.2f} секунд".format(end_time - start_time))
        return processed_files
        
    else:
        # Режим распаковки одного файла (без проверки сигнатур)
        try:
            input_path = Path(input_file)
            if not input_path.exists():
                print("Ошибка: Файл " + input_file + " не существует")
                return
                
            with open(str(input_file), 'rb') as f:
                data = f.read()
            
            # Пропускаем проверку сигнатур для одного файла и сразу декодируем
            decompressed_data = decode1KB(data)
            
            with open(str(output_file), 'wb') as f:
                f.write(decompressed_data)
            
            print("Файл успешно распакован: " + input_file + " -> " + output_file)
            print("Исходный размер: " + str(len(data)) + " байт")
            print("Распакованный размер: " + str(len(decompressed_data)) + " байт")
            end_time = time.time()
            print("Время выполнения: {0:.2f} секунд".format(end_time - start_time))
            
        except Exception as e:
            print("Ошибка распаковки: " + str(e))

def repack_lzss(input_file, output_file, compress_all=False, search_folder=None):
    """
    Упаковывает файл(ы) используя encode1KB
    
    Args:
        input_file: Входной файл для сжатия (используется при compress_all=False)
        output_file: Выходной файл (используется при compress_all=False)
        compress_all: Если True - сжимает все файлы *.lzss-dec, если False - один указанный файл
        search_folder: Папка для поиска файлов *.lzss-dec (используется только при compress_all=True)
    """
    start_time = time.time()
    
    if compress_all:
        # Режим сжатия всех файлов *.lzss-dec
        if search_folder is None:
            # Если папка не указана, используем текущую директорию
            input_path = Path.cwd()
        else:
            input_path = Path(search_folder)
        
        # Проверяем существование папки
        if not input_path.exists():
            print("Ошибка: Папка " + str(input_path) + " не существует")
            return
        
        # Ищем файлы *.lzss-dec и кодируем их в *.bin
        unpack_files = sorted(input_path.glob("*.lzss-dec"))
        if not unpack_files:
            print("Файлы .lzss-dec не найдены в папке " + str(input_path))
            return
        
        total_files = len(unpack_files)
        print("Найдено " + str(total_files) + " файлов .lzss-dec для кодирования")
        

        for i, unpack_file in enumerate(unpack_files):
            try:
                # Читаем распакованные данные
                with open(str(unpack_file), 'rb') as f:
                    unpacked_data = f.read()
                
                # Кодируем обратно в сжатый формат
                encoded_data = encode1KB(unpacked_data)
                
                # Создаем имя для закодированного файла
                bin_file = unpack_file.with_suffix('.bin')
                
                # Сохраняем закодированные данные
                with open(str(bin_file), 'wb') as f:
                    f.write(encoded_data)
                
                # Расчет прогресса в процентах
                progress = (i + 1) / total_files * 100
                
                print("Сжат: {0} -> {1} [{2}/{3} - {4:.1f}%]".format(unpack_file.name, bin_file.name, i + 1, total_files, progress))
                      
            except Exception as e:
                # Расчет прогресса в процентах при ошибке
                progress = (i + 1) / total_files * 100
                print("Ошибка кодирования {0}: {1} [{2}/{3} - {4:.1f}%]".format(unpack_file.name, str(e), i + 1, total_files, progress))
        
        end_time = time.time()
        print("Время выполнения: {0:.2f} секунд".format(end_time - start_time))
        
    else:
        # Режим сжатия одного файла
        try:
            input_path = Path(input_file)
            if not input_path.exists():
                print("Ошибка: Файл " + input_file + " не существует")
                return
                
            with open(str(input_file), 'rb') as f:
                data = f.read()
            
            compressed_data = encode1KB(data)
            
            with open(str(output_file), 'wb') as f:
                f.write(compressed_data)
            
            print("Файл успешно упакован: " + input_file + " -> " + output_file)
            print("Исходный размер: " + str(len(data)) + " байт")
            print("Сжатый размер: " + str(len(compressed_data)) + " байт")
            print("Коэффициент сжатия: {0:.1f}%".format(len(compressed_data)/len(data)*100))
            end_time = time.time()
            print("Время выполнения: {0:.2f} секунд".format(end_time - start_time))
            
        except Exception as e:
            print("Ошибка упаковки: " + str(e))

def main():
    parser = argparse.ArgumentParser(
        description="Работа с Vanguard Bandits (PS1) - извлечение и упаковка файлов",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  Извлечение:
    %(prog)s split -f file.bin                  # Извлечь все файлы из указанного контейнера в папку extracted
    %(prog)s split -f file.bin -o folder        # Извлечь все файлы из указанного контейнера в папку folder
    %(prog)s split -d folder                    # Папка для извлечённых файлов в папки 'имя_файла-extracted'
        
  Упаковка:     
    %(prog)s build -d folder                    # Упаковать файлы из папки folder в контейнер EPICA.bin
    %(prog)s build -d extracted -o new.bin      # Упаковать файлы из папки extracted в контейнера new.bin
    %(prog)s build -d folder -v                 # Упаковать файлы с верификацией контейнера
    %(prog)s build -d folder -i                 # Подробный вывод о ходе выполнения
        
  Анализ:       
    %(prog)s analyze -f file.bin -o report.txt  # Проанализировать структуру архива с сохранением отчета
    %(prog)s analyze -d folder -o report.txt # Проанализировать структуру файлов в папке с сохранением отчета
    %(prog)s read_bytes -d folder -b 32 -o report.txt  # Читать первые 32 байта каждого файла из папки folder
    
  Распаковка LZSS:
    %(prog)s unpack -d folder                   # Автоматически распаковать файлы по сигнатурам
    %(prog)s unpack -i file.bin -o file.dec     # Распаковать один файл без проверки сигнатур
    %(prog)s unpack -a -d folder                # Распаковать все файлы в папке по сигнатурам
        
  Упаковка LZSS:
    %(prog)s repack -d folder                   # Автоматически упаковать все файлы .lzss-dec
    %(prog)s repack -i file.dec -o file.bin     # Упаковать один файл
        """
    )
    
    # Добавляем подкоманды
    subparsers = parser.add_subparsers(dest='command', help='Команда')
    
    # Парсер для команды split
    split_parser = subparsers.add_parser('split', help='Извлечение файлов из архива')
    split_mode_group = split_parser.add_mutually_exclusive_group(required=True)
    split_mode_group.add_argument('-f', '--file', 
                                help='Имя файла архива для извлечения (режим одного файла)')
    split_mode_group.add_argument('-d', '--folder', 
                                help='Путь к папке для обработки всех архивов (режим папки)')
    split_parser.add_argument('-o', '--output', default='extracted',
                            help='Папка для извлеченных файлов (по умолчанию: extracted)')
    
    # Парсер для команды build
    build_parser = subparsers.add_parser('build', help='Упаковка файлов в архив')
    build_parser.add_argument('-d', '--dir', required=True,
                           help='Папка с извлеченными файлами для упаковки')
    build_parser.add_argument('-o', '--output', default='EPICA.bin',
                           help='Имя выходного файла архива (по умолчанию: EPICA.bin)')
    build_parser.add_argument('-a', '--alignment', type=lambda x: int(x, 0), default=0x800,
                           help='Выравнивание между файлами (по умолчанию: 0x800)')
    build_parser.add_argument('-v', '--verify', action='store_true',
                           help='Проверка архива на целостность')
    build_parser.add_argument('-i', '--info', action='store_true',
                           help='Подробный вывод информации в консоль')
    
    # Парсер для команды analyze
    analyze_parser = subparsers.add_parser('analyze', help='Анализ структуры архива или всех файлов в папке')
    analyze_group = analyze_parser.add_mutually_exclusive_group(required=True)
    analyze_group.add_argument('-f', '--file', 
                              help='Имя файла архива для анализа (режим одного файла)')
    analyze_group.add_argument('-d', '--dir', 
                              help='Путь к папке для анализа всех файлов (режим папки)')
    analyze_parser.add_argument('-o', '--output', required=True,
                              help='Файл для сохранения отчета (обязательный параметр)')
    
    # Парсер для команды read_first_n_bytes
    read_first_n_bytes_parser = subparsers.add_parser('read_bytes', 
                            help='Читает первые байты всех файлов в указанной папке')
    read_first_n_bytes_parser.add_argument('-d', '--dir', default='EPICA.BIN-extracted',
                              help='Имя файла архива для анализа (по умолчанию: EPICA.bin)')
    read_first_n_bytes_parser.add_argument('-b', '--bytes', type=int, default=16,
                              help='Количество байт для чтения (по умолчанию: 16)')
    read_first_n_bytes_parser.add_argument('-o', '--output', default='read_first_16_bytes.txt',
                          help='Файл для сохранения отчета (по умолчанию: EPICA.BIN-extracted-first_16_bytes.txt)')
    
    # Парсер для команды unpack
    unpack_parser = subparsers.add_parser('unpack', help='Распаковка LZSS файлов')
    unpack_parser.add_argument('-d', '--dir', help='Папка с файлами для автоматической распаковки')
    unpack_parser.add_argument('-i', '--input', help='Входной файл для распаковки (если не используется --all)')
    unpack_parser.add_argument('-o', '--output', help='Выходной файл (если не используется --all)')
    unpack_parser.add_argument('-a', '--all', action='store_true',
                      help='Распаковать все файлы в указанной папке по сигнатурам')
    
    # Парсер для команды repack
    repack_parser = subparsers.add_parser('repack', help='Упаковка LZSS файлов')
    repack_parser.add_argument('-d', '--dir', help='Папка с файлами для автоматической упаковки')
    repack_parser.add_argument('-i', '--input', help='Входной файл для упаковки (если не используется --all)')
    repack_parser.add_argument('-o', '--output', help='Выходной файл (если не используется --all)')
    repack_parser.add_argument('-a', '--all', action='store_true',
                      help='Упаковать все файлы в указанной папке')
    
    args = parser.parse_args()
    
    if not args.command:
        print("\n *** Команды: ***")
        print("=" * 50)
        parser.print_help()
        print("\n *** Команда split: ***")
        print("=" * 50)
        split_parser.print_help()
        print("\n *** Команда build: ***")
        print("=" * 50)
        build_parser.print_help()
        print("\n *** Команда analyze: ***")
        print("=" * 50)
        analyze_parser.print_help()
        print("=" * 50)
        print("\n *** Команда read_bytes: ***")
        print("=" * 50)
        read_first_n_bytes_parser.print_help()
        print("=" * 50)
        print("\n *** Команда unpack: ***")
        print("=" * 50)
        unpack_parser.print_help()
        print("\n *** Команда repack: ***")
        print("=" * 50)
        repack_parser.print_help()
        print("=" * 50)
        input("Нажмите Enter для выхода")
        return
    
    try:
        if args.command == 'split':
            if args.folder:
                # Режим работы с папкой
                split(folder_path=args.folder, output_dir=args.output)
            else:
                # Режим работы с одним файлом
                split(file_name=args.file, output_dir=args.output)
                
        elif args.command == 'build':
            build(input_dir=args.dir, output_file=args.output, alignment=args.alignment,
                    verify=args.verify, detailed=args.info)
            
        elif args.command == 'analyze':
            analyze(file_name=args.file, output_file=args.output, folder_path=args.dir)
        
        elif args.command == 'read_bytes':
            read_first_n_bytes(folder_path=args.dir, n_bytes=args.bytes, output_file=args.output)
            
        elif args.command == 'unpack':
            if args.all:
                # Режим распаковки всех файлов по сигнатурам
                unpack_lzss(unpack_all=True, search_folder=args.dir)
            else:
                # Режим распаковки одного файла - проверяем что input и output указаны
                if not args.input or not args.output:
                    print("Ошибка: для распаковки одного файла, надо указать --input и --output")
                    exit(1)
                unpack_lzss(input_file=args.input, output_file=args.output, unpack_all=False)
                
        elif args.command == 'repack':
            if args.all:
                # Режим упаковки всех файлов
                repack_lzss("", "", compress_all=True, search_folder=args.dir)
            else:
                # Режим упаковки одного файла - проверяем что input и output указаны
                if not args.input or not args.output:
                    print("Ошибка: для упаковки одного файла, надо указать --input и --output")
                    exit(1)
                repack_lzss(args.input, args.output, compress_all=False)
                
    except FileNotFoundError as e:
        print("Ошибка: " + str(e))
        sys.exit(1)
    except Exception as e:
        print("Ошибка: " + str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()