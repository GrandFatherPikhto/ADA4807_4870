"""
Генерация чистого netlist из схемы LTspice (.asc) через вызов LTspice -netlist.
Затем создаётся читаемый отчёт о компонентах и их соединениях.
Все результаты сохраняются в папку 'net' в виде .txt файлов.
"""

import os
import subprocess
import re
from pathlib import Path

# ========== НАСТРОЙКИ ==========
SCHEMATIC_FILE = "ada4807_4870.asc"        # имя файла схемы (должен лежать в той же папке)
LTSPICE_EXE = r"C:\Users\grand\AppData\Local\Programs\ADI\LTspice\LTspice.exe"
# Если у вас другая версия или путь, измените строку выше.
# Альтернативные пути (раскомментируйте нужный):
# LTSPICE_EXE = r"C:\Program Files\ADI\LTspice\LTspice.exe"
# LTSPICE_EXE = r"C:\Program Files (x86)\LTC\LTspiceXVII\XVIIx64.exe"
# ================================


def run_ltspice_netlist(asc_path: Path, ltspice_exe: str = LTSPICE_EXE) -> Path:
    """
    Запускает LTspice с ключом -netlist, генерирует .net файл рядом с исходной схемой.
    Возвращает путь к сгенерированному .net файлу.
    """
    net_path = asc_path.with_suffix(".net")
    # Если старый .net существует, удалим, чтобы не было путаницы
    if net_path.exists():
        net_path.unlink()
    
    cmd = [ltspice_exe, "-netlist", str(asc_path.absolute())]
    print(f"Выполняется: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=asc_path.parent)
    if result.returncode != 0:
        raise RuntimeError(f"Ошибка при генерации netlist:\n{result.stderr}")
    if not net_path.exists():
        raise RuntimeError(f"Файл {net_path} не был создан.")
    print(f"Netlist сгенерирован: {net_path}")
    return net_path


def clean_netlist(raw_net_path: Path, output_txt_path: Path) -> list[str]:
    with open(raw_net_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    cleaned = []
    for line in lines:
        # Удаляем комментарии после ;
        line = line.split(';')[0].strip()
        if not line:
            continue
        if line.startswith('*') or line.startswith('.lib') or line.startswith('.backanno'):
            continue
        cleaned.append(line)
    with open(output_txt_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(cleaned))
    return cleaned


def parse_netlist(cleaned_lines: list[str]) -> dict:
    """
    Парсит очищенный netlist, корректно обрабатывая behavioural источники (B*).
    Возвращает словарь: {имя_компонента: {'type': тип, 'value': номинал, 'pins': [список цепей]}}
    """
    components = {}
    for line in cleaned_lines:
        line = line.strip()
        if not line:
            continue
        # Не разбиваем сразу по пробелам, а будем искать паттерн для B-источников
        parts = line.split()
        name = parts[0]
        if name.startswith('.'):
            continue

        # Определяем тип
        if name.startswith('X'):
            comp_type = "subcircuit"
        elif name.startswith('R'):
            comp_type = "resistor"
        elif name.startswith('C'):
            comp_type = "capacitor"
        elif name.startswith('V'):
            comp_type = "voltage_source"
        elif name.startswith('I'):
            comp_type = "current_source"
        elif name.startswith('B'):
            comp_type = "behavioral_source"
        else:
            comp_type = "unknown"

        # Для B-источников используем регулярное выражение для выделения полного значения
        if comp_type == "behavioral_source":
            # Ищем I={...} или V={...} (с учётом возможных вложенных скобок)
            match = re.search(r'[IV]=\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', line)
            if match:
                value = match.group(0)
                # Всё до этого match — имя и пины
                before = line[:match.start()].strip()
                # Первый токен — имя, остальные — пины
                pin_tokens = before.split()[1:]  # пропускаем имя
                pins = pin_tokens
            else:
                # Запасной вариант: берём последний токен как значение
                value = parts[-1]
                pins = parts[1:-1]
        else:
            # Для остальных — последний токен значение, остальное пины
            value = parts[-1]
            pins = parts[1:-1]

        components[name] = {
            'type': comp_type,
            'value': value,
            'pins': pins
        }
    return components


def generate_readable_report(components: dict, output_txt_path: Path):
    """
    Создаёт читаемый отчёт о компонентах и их подключениях.
    """
    lines = []
    lines.append(f"=== ЧИТАЕМЫЙ ОТЧЁТ ПО СХЕМЕ: {SCHEMATIC_FILE} ===\n")
    lines.append(f"Всего компонентов: {len(components)}\n")
    lines.append("-" * 80)
    lines.append(f"{'Имя':<12} | {'Тип':<15} | {'Номинал':<20} | Цепи (пины)")
    lines.append("-" * 80)
    
    for name, comp in sorted(components.items()):
        clean_name = name.replace('§', '_')   # убираем символ параграфа
        pins_str = " ".join(comp['pins'])
        lines.append(f"{clean_name:<12} | {comp['type']:<15} | {comp['value']:<20} | {pins_str}")
    
    lines.append("\n" + "=" * 80)
    lines.append("--- АНАЛИЗ ЭЛЕКТРИЧЕСКИХ СВЯЗЕЙ (NETS) ---")
    
    # Собираем все цепи (уникальные имена)
    all_nets = set()
    for comp in components.values():
        all_nets.update(comp['pins'])
    # Исключаем '0' (земля) и переименовываем в GND
    nets_dict = {}
    for net in sorted(all_nets):
        net_name = "GND" if net == '0' else net
        display_name = net_name.replace('§', '_')
        nets_dict[net] = display_name
    
    # Для каждой цепи перечисляем подключённые компоненты
    for net, display in sorted(nets_dict.items()):
        connected = []
        for name, comp in components.items():
            if net in comp['pins']:
                # connected.append(name)
                connected.append(name.replace('§', '_'))
        comps_str = ", ".join(connected) if connected else "—"
        lines.append(f"Шина [{display:<10}] -> объединяет: {comps_str}")
    
    with open(output_txt_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print(f"Читаемый отчёт сохранён: {output_txt_path}")


def run_generate(ltspice_exe, schematic_path, output_dir):
    # 1. Проверяем наличие файла схемы
    asc_path = Path(schematic_path)
    if not asc_path.exists():
        raise FileNotFoundError(f"Файл схемы '{schematic_path}' не найден в текущей папке.")
    
    # 2. Создаём папку net
    net_dir = Path(output_dir)
    net_dir.mkdir(exist_ok=True)
    
    # 3. Генерируем .net через LTspice
    raw_net_path = run_ltspice_netlist(asc_path, ltspice_exe)
    
    # 4. Очищаем netlist и сохраняем как .txt в папку net
    clean_txt_path = net_dir / f"{asc_path.stem}_clean.net.txt"
    cleaned_lines = clean_netlist(raw_net_path, clean_txt_path)
    
    # 5. Парсим очищенный netlist для читаемого отчёта
    components = parse_netlist(cleaned_lines)
    
    # 6. Сохраняем читаемый отчёт
    readable_path = net_dir / f"{asc_path.stem}_readable.txt"
    generate_readable_report(components, readable_path)
    
    print("\n✅ Готово! Все файлы находятся в папке 'net'.")

    return [Path(clean_txt_path), Path(readable_path)]


def generate_netlist(config) -> tuple[Path, Path]:
    """Возвращает пути к clean.txt и readable.txt"""

    is_generate_netlist = config.get('netlist_generator', {}).get('generate_netlist', False)
    if is_generate_netlist == None or is_generate_netlist == False:
        return [None, None]

    output_dir = config.get('netlist_generator', {}).get('output_dir', False)
    schematic_path = config.get('schematic', {}).get('path', False)
    ltspice_exe = config.get('ltspice', {}).get('executable', False)

    return run_generate(ltspice_exe, schematic_path, output_dir)

if __name__ == "__main__":
    res = run_generate(LTSPICE_EXE, SCHEMATIC_FILE, "net")
    # print(res)