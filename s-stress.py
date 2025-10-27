#!/usr/bin/env python3

import subprocess
import time
import sys
import psutil
import platform

class RaplPowerSource:
    """Класс для извлечения информации о потреблении энергии через RAPL."""
    def __init__(self):
        self.package_power_file_0 = "/sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj"
        self.package_power_file_1 = "/sys/class/powercap/intel-rapl/intel-rapl:1/energy_uj"
        self.previous_energy_0 = self.read_energy(self.package_power_file_0)  # Учитываем первое значение при инициализации
        self.previous_energy_1 = self.read_energy(self.package_power_file_1)  # Учитываем второе значение при инициализации
        self.previous_time = time.time()  # Записываем текущее время

    def read_energy(self, power_file):
        """Читает текущее значение энергии из указанного файла и проверяет на наличие файла"""
        try:
            with open(power_file, 'r') as file:
                energy = int(file.read().strip())
            return energy
        except Exception as e:
           # print(f"Ошибка при чтении энергии из {power_file}: {e}")
            return None

    def get_power_consumption(self):
        current_time = time.time()  # Получаем текущее время
        time_interval = current_time - self.previous_time  # Вычисляем промежуток времени
        self.previous_time = current_time  # Обновляем время для следующего вызова

        """Возвращает текущее энергопотребление из обоих источников в Джоулях."""
        current_energy_0 = self.read_energy(self.package_power_file_0)
        current_energy_1 = self.read_energy(self.package_power_file_1)

        power_consumed = []
        if current_energy_0 is not None:
            energy_0 = (current_energy_0 - self.previous_energy_0) / 1_000_000  # переводим в Джоули
            power_0 = energy_0 / time_interval if time_interval > 0 else 0  # Рассчитываем мощность в Вт
            self.previous_energy_0 = current_energy_0
            power_consumed.append(f"Потребление энергии (intel-rapl:0): {energy_0:.4f} J, Мощность: {power_0:.4f} W")

        if current_energy_1 is not None:
            energy_1 = (current_energy_1 - self.previous_energy_1) / 1_000_000  # переводим в Джоули
            power_1 = energy_1 / time_interval if time_interval > 0 else 0  # Рассчитываем мощность в Вт
            self.previous_energy_1 = current_energy_1
            power_consumed.append(f"Потребление энергии (intel-rapl:1): {energy_1:.4f} J, Мощность: {power_1:.4f} W")

        return "\n".join(power_consumed) if power_consumed else None

#---------------------------------------------------------------------------------------------------------------
print("\n")

def install_package(package_name):
    """Устанавливает пакет, если он не установлен."""
    try:
        if subprocess.run(['dpkg', '-l'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout.find(package_name) == -1:
            print(f"{package_name} не установлен. Устанавливаем...")
            subprocess.run(['sudo', 'DEBIAN_FRONTEND=noninteractive', 'apt', 'install', '-y', package_name], check=True)
        else:
            print(f"{package_name} уже установлен.")
    except Exception as e:
        print(f"Ошибка при установке {package_name}: {e}")

def install_packages(package_list):
    """Устанавливает список пакетов."""
    for package in package_list:
        install_package(package)
#----------------------------------------------------------------------------------------------------------------

def get_cpu_temperature():
    """Получает текущую температуру всех ядер CPU в градусах Цельсия."""
    temperatures = {}
    try:
        output = subprocess.check_output(['sensors']).decode()
        for line in output.split('\n'):
            if 'Package id 0' in line:  # Изменяем на соответствующий id, если требуется
                core_label = "CPU0"  # Статичный метка для CPU1
                temp_string = line.split(':')[1].strip().split(' ')[0]
                temperature = float(temp_string.replace('+', '').replace('°C', ''))
                temperatures[core_label] = temperature
            elif 'Package id 1' in line:  # Если есть 'Package id 1'
                core_label = "CPU1"  # Статичный метка для CPU2, если требуется
                temp_string = line.split(':')[1].strip().split(' ')[0]
                temperature = float(temp_string.replace('+', '').replace('°C', ''))
                temperatures[core_label] = temperature
    except Exception as e:
        print(f"Ошибка при получении температуры: {e}")
        return None
    return temperatures

def get_cpu_model():
    try:
        # Выполняем команду lscpu и извлекаем модель CPU
        result = subprocess.run(['lscpu'], stdout=subprocess.PIPE, text=True)
        for line in result.stdout.splitlines():
            if "Model name" in line:
                return line.split(":")[1].strip()
    except Exception:
        return "N/A"

def run_process(command):
    """Запускает процесс и возвращает его объект."""
    try:
        return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        print(f"Ошибка при запуске {' '.join(command)}: {e}")
        return None

def main():
    print("\n")

    logical_processors = psutil.cpu_count(logical=True)
    print(f"Кол-во логических процессоров (потоков): {logical_processors}")

    physicals_cores = psutil.cpu_count(logical=False)
    print(f"Кол-во физических ядер: {physicals_cores}")

    print("\n")

    # Переменные для хранения значений
    cores = None
    duration = None

    # Запрос количества ядер
    while cores is None:
        try:
            cores = int(input("Введите количество ядер для stress-ng: "))
        except ValueError:
            print("Пожалуйста, введите целое число для ядер.")

    # Запрос времени работы
    while duration is None:
        try:
            duration = int(input("Введите время работы stress-ng в секундах: "))
        except ValueError:
            print("Пожалуйста, введите целое число для времени работы.")

    print("\n")
    # Создаём объект для RAPL
    power_source = RaplPowerSource()

    # Запуск stress-ng
    stress_ng_process = run_process([
        "stress-ng",
        "-c",
        str(cores),
        "-t",
        str(duration)
    ])

    if not stress_ng_process:
        print("Не удалось запустить stress-ng.")
        return

#-------------------------------------------------------------------------------------------------


    max_temperatures_cpu0 = float('-inf') # Тмпература CPU1
    max_temperatures_cpu1 = float('-inf') # Температура CPU2
    max_power_consumption_cpu0 = float('-inf') #
    max_power_consumption_cpu1 = float('-inf') #
    last_power_consumption_cpu0 = None  # Для хранения последнего значения мощности CPU0
    last_power_consumption_cpu1 = None  # Для хранения последнего значения мощности CPU1
    max_cpu_frequency = float('-inf') # частота
    max_cpu_usage = float('-inf') # Загруженность

    rapl_power_source = RaplPowerSource()

    try:
        print(f"{'Температура CPU0 (°C)':<25}{'Температура CPU1 (°C)':<25}{'Потребляемая мощность CPU0 (W)':<35}{'Потребляемая мощность CPU1 (W)':<35}{'Частота (MHz)':<20}{'Загруженность (%)':<25}")
        start_time = time.time()
        while time.time() - start_time < duration:
            temperatures = get_cpu_temperature()

            # Получаем потребляемую мощность для CPU0 и CPU1
            power_consumption = rapl_power_source.get_power_consumption().split("\n")
            power_consumption_cpu0 = float(power_consumption[0].split(":")[-1].strip().split()[0]) if power_consumption[0] else None
#            power_consumption_cpu1 = float(power_consumption[1].split(":")[-1].strip().split()[0]) if power_consumption[1] else None
            try:
              power_consumption_cpu1 = float(power_consumption[1].split(":")[-1].strip().split()[0]) if power_consumption[1] else None
            except (IndexError, ValueError, AttributeError):
              power_consumption_cpu1 = None


            # Обновление max значений

            if temperatures is not None:
                cpu0_temp = temperatures.get("CPU0", float('-inf'))
                cpu1_temp = temperatures.get("CPU1", float('-inf'))
                max_temperatures_cpu0 = max(max_temperatures_cpu0, cpu0_temp)
                max_temperatures_cpu1 = max(max_temperatures_cpu1, cpu1_temp)

            # Сохраняем последние значения потребляемой мощности
            if power_consumption_cpu0 is not None:
                last_power_consumption_cpu0 = power_consumption_cpu0

            if power_consumption_cpu1 is not None:
                last_power_consumption_cpu1 = power_consumption_cpu1

            # Сохраняем max значения потребляемой мощности
            if power_consumption_cpu0 is not None:
                max_power_consumption_cpu0 = max(max_power_consumption_cpu0, power_consumption_cpu0)

            if power_consumption_cpu1 is not None:
                max_power_consumption_cpu1 = max(max_power_consumption_cpu1, power_consumption_cpu1)

            # Получаем загруженность CPU и частоту
            cpu_freq = psutil.cpu_freq(percpu=False)  # Частота для всей системы
            cpu_usage = psutil.cpu_percent(interval=None)  # Загруженность CPU

            if cpu_freq is not None:
                max_cpu_frequency = max(max_cpu_frequency, cpu_freq.current)

            max_cpu_usage = max(max_cpu_usage, cpu_usage)

            # Форматированный вывод текущих значений
            cpu0_temp = temperatures.get("CPU0", "N/A")
            cpu1_temp = temperatures.get("CPU1", "N/A")

            # Форматированный вывод
            output = (f"{cpu0_temp:<25}{cpu1_temp:<25}"
                      f"{(int(power_consumption_cpu0) if power_consumption_cpu0 is not None else 'N/A'):<35}"
                      f"{(int(power_consumption_cpu1) if power_consumption_cpu1 is not None else 'N/A'):<35}"
                      f"{(float(cpu_freq.current) if cpu_freq else 'N/A'):<20.3f}"
                      f"{cpu_usage:<25}")

            # Обновление строки
            print(f"\r{output}", end='')
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nПрерывание мониторинга.")
    finally:
        print('\n')
        print("############################################")
        print('\n')

        # Вывод модели CPU
        cpu_model = get_cpu_model()
        print(f"Модель CPU: {cpu_model}")
        print('\n')

        # Вывод максимальных значений
        print("Максимальные показатели во время теста:")
        print("\n")
        print(f"Згруженность CPU: {max_cpu_usage:.2f} %" if max_cpu_usage != float('-inf') else "Макс. загруженность CPU: N/A")
        print(f"Частота CPU: {max_cpu_frequency:.3f} MHz" if max_cpu_frequency != float('-inf') else "Макс. частота CPU: N/A")
        print(f"Температура CPU0: {max_temperatures_cpu0:.1f} °C" if max_temperatures_cpu0 != float('-inf') else "Температура CPU0: N/A")
        print(f"Температура CPU1: {max_temperatures_cpu1:.1f} °C" if max_temperatures_cpu1 != float('-inf') else "Температура CPU1: N/A")
        print(f"Мощность CPU0: {int(last_power_consumption_cpu0)} W" if last_power_consumption_cpu0 is not None and last_power_consumption_cpu0 != float('-inf') else "Мощность CPU0: N/A")
        print(f"Мощность CPU1: {int(last_power_consumption_cpu1)} W" if last_power_consumption_cpu1 is not None and last_power_consumption_cpu1 != float('-inf') else "Мощность CPU1: N/A")        
        print(f"Cтарт stress макс. мощность CPU0: {int(max_power_consumption_cpu0)} W" if max_power_consumption_cpu0 != float('-inf') else "Cтарт stress макс. мощность CPU0: N/A")
        print(f"Cтарт stress макс. мощность CPU1: {int(max_power_consumption_cpu1)} W" if max_power_consumption_cpu1 != float('-inf') else "Cтарт stress макс. мощность CPU1: N/A")

        print('\n')
        print("#############################################")
        print('\n')
if __name__ == "__main__":

    # Устанавливаем необходимые пакеты
    packages = [
        "stress",
        "stress-ng",
        "lm-sensors",
        "psutil",
        "python3"

    ]
    install_packages(packages)

    main()
