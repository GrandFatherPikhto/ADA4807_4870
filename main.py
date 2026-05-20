"""
Главный исполняемый модуль.

Загружает конфигурацию, выполняет расчёт номиналов, запускает LTspice,
строит графики и генерирует итоговый отчёт.
"""

import os
import json
import sys
from pathlib import Path

from logger_config import logger, setup_logging
from calculation import select_components
from simulation import LTspiceRunner
from plotting import plot_time_domain, plot_spectrum, plot_degradation, plot_input_currents
from report import generate_report
from netlist_generator import generate_netlist


def load_config(config_path: str) -> dict:
    """Загружает конфигурацию из JSON-файла."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"Конфигурация загружена из {config_path}")
        return config
    except Exception as e:
        logger.critical(f"Не удалось загрузить конфиг: {e}")
        sys.exit(1)

def select_best_combination(params: dict) -> dict:
    """Выбирает лучшую комбинацию номиналов из рассчитанных."""
    combinations = select_components(params)
    chosen = combinations[0].copy()
    chosen['R_load'] = params['R_load']
    chosen['R_TIA'] = params['R_TIA']
    logger.info(f"Выбрана комбинация: Ra={chosen['Ra']} Ом, Rf={chosen['Rf_e96']} Ом, "
                f"Rb={chosen['Rb_e96']} Ом, Cf={chosen['Cf']} пФ, R_TIA={chosen['R_TIA']} Ом")
    return chosen


def setup_runner(config: dict) -> LTspiceRunner:
    """Создаёт и возвращает экземпляр LTspiceRunner."""
    return LTspiceRunner(
        schematic_path=config['schematic']['path'],
        ltspice_exe=config['ltspice']['executable'],
        temp_dir=config['simulation']['temp_dir'],
        output_dir=config['simulation']['output_dir']
    )


def run_single_simulation(runner: LTspiceRunner, chosen: dict, freq: float) -> tuple:
    """
    Запускает одиночную симуляцию, возвращает (raw_path, log_path, csv_path, thd, harmonics, amplitudes).
    """
    raw_path, log_path = runner.run(chosen, freq)
    csv_path = runner.export_raw_to_csv(raw_path)
    thd = runner.get_thd(log_path)
    harmonics, amplitudes = runner.get_fourier_data(log_path)
    return raw_path, log_path, csv_path, thd, harmonics, amplitudes


def generate_plots(plots_cfg: dict, csv_path: str, harmonics: list, amplitudes: list,
                   thd: str, frequencies: list, thd_results: list = None, r_tia: float = None):
    """Условно строит графики в соответствии с настройками."""
    if plots_cfg.get('time_domain', False):
        plot_time_domain(csv_path)
    if plots_cfg.get('spectrum', False):
        plot_spectrum(harmonics, amplitudes, thd)
    if plots_cfg.get('input_currents', False) and r_tia is not None:
        plot_input_currents(csv_path, r_tia)
    if plots_cfg.get('degradation', False) and thd_results is not None:
        plot_degradation(frequencies, thd_results)   

def main():
    setup_logging("simulation.log")
    config = load_config("config.json")

    # 1. Генерируем нетлисты (для сверки и вычитывания)
    generate_netlist(config)
    clean_net_path, readable_net_path = generate_netlist(config)
    if clean_net_path:
        logger.info(f"Netlist (чистый) сохранён: {clean_net_path}")
        logger.info(f"Читаемый отчёт: {readable_net_path}")    


    # 2. Подбор номиналов
    chosen = select_best_combination(config['params'])
    chosen.update(config.get('tran_settings', {}))

    # 3. Раннер
    runner = setup_runner(config)

    r_tia=chosen['R_TIA']

    # 4. Одиночная симуляция на первой частоте
    first_freq = config['frequencies'][0]
    raw_path, log_path, csv_path, thd, harmonics, amplitudes = run_single_simulation(
        runner, chosen, first_freq
    )

    # 5. Построение графиков (без деградации пока)
    plots_cfg = config.get('plots', {})
    generate_plots(plots_cfg, csv_path, harmonics, amplitudes, thd, None, None, r_tia)

    # 6. Свип по частотам для деградации (если запрошено)
    thd_results = None
    if plots_cfg.get('degradation', False):
        logger.info("Запуск sweep по частотам для оценки деградации THD...")
        thd_results = runner.degradation_sweep(chosen, config['frequencies'])
        # Перестраиваем график деградации (если нужен отдельно, вызываем снова)
        plot_degradation(config['frequencies'], thd_results)

    # 7. Отчёт
    sim_info = {
        'freq': first_freq,
        'thd': thd,
        'csv_path': csv_path,
        'log_path': log_path,
        'clean_net_path': clean_net_path,
        'readable_net_path': readable_net_path        
    }
    generate_report(config, chosen, sim_info, config['simulation']['output_dir'])

    logger.info("=== Процесс завершён успешно ===")

if __name__ == "__main__":
    main()