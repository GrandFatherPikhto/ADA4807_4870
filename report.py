"""
Модуль создания подробного текстового отчёта о подборе и симуляции.
Сохраняется в файл report.txt в папке output_dir.
"""

from pathlib import Path
from logger_config import logger


def generate_report(config: dict, combo: dict, sim_info: dict, output_dir: str = "./out"):
    """
    Создаёт текстовый отчёт и сохраняет в output_dir/report.txt.

    config   – полный словарь конфига (из config.json),
    combo    – выбранная комбинация номиналов (из results),
    sim_info – словарь с результатами симуляции:
               {'freq': частота, 'thd': строка THD, 'csv_path': путь к CSV, 'log_path': путь к .log}
    """
    out_path = Path(output_dir) / "report.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    p = config['params']
    lines = [
        "=" * 60,
        "ОТЧЁТ О ПОДБОРЕ НОМИНАЛОВ ДЛЯ ADA4870 / ADA4807-2",
        "=" * 60,
        "",
        "Исходные параметры:",
        f"  I_FS            = {p['I_FS']*1e3:.3f} мА",
        f"  R_TIA           = {p['R_TIA']} Ом",
        f"  V_out_amp       = {p['V_out_amp']} В",
        f"  R_load          = {p['R_load']} Ом",
        f"  Питание         = ±{abs(p['V_sup'])} В",
        f"  Запас до шины   = {p['V_headroom']} В",
        f"  Макс. ток вых.  = {p['I_out_max']} А",
        "",
        "Результаты расчёта:",
        f"  V_diff_amp          = {p['I_FS'] * p['R_TIA']:.3f} В",
        f"  Требуемое усиление  = {p['V_out_amp'] / (p['I_FS'] * p['R_TIA']):.3f}",
        "",
        "Подобранные номиналы (ближайшие E96):",
        f"  Ra          = {combo['Ra']} Ом",
        f"  Rf (расчёт) = {combo['Rf']} Ом  -> E96 = {combo['Rf_e96']} Ом",
        f"  Rb (расчёт) = {combo['Rb']} Ом  -> E96 = {combo['Rb_e96']} Ом",
        f"  Cf          = {combo['Cf']} пФ",
        "",
        "Проверка:",
        f"  A_v реальное             = {combo['A_v_real']:.2f}",
        f"  Ожидаемая амплитуда      = {combo['A_v_real'] * p['I_FS'] * p['R_TIA']:.2f} В",
        f"  Пиковый ток нагрузки     = {p['V_out_amp'] / p['R_load']:.3f} А",
        "",
        "Результаты симуляции:",
        f"  Частота: {sim_info.get('freq', 0)/1e6:.2f} МГц",
        f"  THD: {sim_info['thd']}",
        f"  Постоянная составляющая: не измерялась (добавить при необходимости)",
        "",
        "Файлы:",
        f"  CSV с сигналами: {sim_info.get('csv_path', 'N/A')}",
        f"  Лог LTSpice:     {sim_info.get('log_path', 'N/A')}",
        f"  CSV с сигналами: {sim_info.get('csv_path', 'N/A')}",
        f"  Лог LTSpice:     {sim_info.get('log_path', 'N/A')}",
        f"  Netlist (очищенный):    {sim_info.get('clean_net_path', 'N/A')}",
        f"  Netlist (читаемый):    {sim_info.get('readable_net_path', 'N/A')}",
        "=" * 60
    ]

    report_text = "\n".join(lines)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(report_text)

    logger.info(f"Текстовый отчёт сохранён: {out_path}")
    print(report_text)  # также выводим в консоль, если нужно