"""
Модуль валидаторов для приложения диагностики Chevrolet Niva
Включает все возможные проверки для входных данных, параметров и команд
"""

import re
import struct
import binascii
from datetime import datetime, date
from typing import Union, List, Dict, Any, Optional, Tuple
import ipaddress
from enum import Enum

class ValidationError(Exception):
    """Исключение для ошибок валидации"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(self.message)

class ValidationLevel(Enum):
    """Уровни строгости валидации"""
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class VehicleParameterValidator:
    """Валидатор параметров автомобиля"""
    
    # Допустимые диапазоны значений для Chevrolet Niva
    PARAMETER_RANGES = {
        'engine_rpm': (0, 8000),  # RPM
        'vehicle_speed': (0, 200),  # км/ч
        'coolant_temp': (-40, 150),  # °C
        'intake_temp': (-40, 150),  # °C
        'throttle_position': (0, 100),  # %
        'maf_flow': (0, 1000),  # г/с
        'fuel_pressure': (0, 1000),  # кПа
        'intake_pressure': (0, 255),  # кПа
        'timing_advance': (-64, 63.5),  # градусы
        'engine_load': (0, 100),  # %
        'fuel_level': (0, 100),  # %
        'battery_voltage': (0, 20),  # В
        'lambda_voltage': (0, 5),  # В
        'lambda_current': (-128, 128),  # мА
        'injector_pulse_width': (0, 100),  # мс
        'ignition_advance': (-64, 63.5),  # градусы
        'fuel_trim_short': (-100, 100),  # %
        'fuel_trim_long': (-100, 100),  # %
        'oxygen_sensor_voltage': (0, 1.275),  # В
        'oxygen_sensor_current': (-128, 128),  # мА
        'egr_position': (0, 100),  # %
        'evap_pressure': (-32767, 32767),  # Па
        'catalyst_temp': (-40, 1500),  # °C
        'turbo_pressure': (0, 255),  # кПа
        'boost_pressure': (0, 255),  # кПа
        'ambient_temp': (-40, 150),  # °C
        'barometric_pressure': (0, 255),  # кПа
        'fuel_rail_pressure': (0, 655350),  # кПа
        'ethanol_fuel_percent': (0, 100),  # %
        'oil_temp': (-40, 210),  # °C
        'oil_pressure': (0, 1000),  # кПа
        'transmission_temp': (-40, 210),  # °C
        'torque_percent': (-125, 125),  # %
        'aux_input_status': (0, 1),  # Вкл/Выкл
    }
    
    # Критические пороги для предупреждений
    CRITICAL_THRESHOLDS = {
        'engine_rpm': {'min': 0, 'max': 7000, 'level': ValidationLevel.CRITICAL},
        'coolant_temp': {'min': 0, 'max': 110, 'level': ValidationLevel.CRITICAL},
        'oil_temp': {'min': 0, 'max': 130, 'level': ValidationLevel.CRITICAL},
        'battery_voltage': {'min': 11.5, 'max': 15.5, 'level': ValidationLevel.CRITICAL},
        'fuel_pressure': {'min': 200, 'max': 600, 'level': ValidationLevel.CRITICAL},
        'oil_pressure': {'min': 100, 'max': 600, 'level': ValidationLevel.CRITICAL},
    }
    
    # Допустимые модели Chevrolet Niva
    VALID_MODELS = {
        '2123': {
            'years': range(2002, 2010),
            'engines': ['1.7i'],
            'ecus': ['Bosch M1.5.4', 'Bosch M7.9.7']
        },
        '21236': {
            'years': range(2010, 2021),
            'engines': ['1.7i'],
            'ecus': ['Bosch M7.9.7', 'Bosch ME7.9.7']
        },
        '2123-250': {
            'years': range(2014, 2021),
            'engines': ['1.8i'],
            'ecus': ['Bosch ME17.9.7']
        },
        '2123M': {
            'years': range(2021, 2026),
            'engines': ['1.7i', '1.8i'],
            'ecus': ['Bosch ME17.9.7', 'Delphi']
        }
    }
    
    @classmethod
    def validate_parameter(cls, param_name: str, value: float, 
                          model: str = None) -> Dict[str, Any]:
        """
        Валидация параметра автомобиля
        
        Args:
            param_name: Название параметра
            value: Значение параметра
            model: Модель автомобиля (для специфичных проверок)
            
        Returns:
            Dict с результатами валидации
            
        Raises:
            ValidationError: При ошибке валидации
        """
        if param_name not in cls.PARAMETER_RANGES:
            raise ValidationError(
                f"Неизвестный параметр: {param_name}",
                field=param_name,
                value=value
            )
        
        min_val, max_val = cls.PARAMETER_RANGES[param_name]
        result = {
            'valid': True,
            'parameter': param_name,
            'value': value,
            'range': (min_val, max_val),
            'warnings': [],
            'errors': [],
            'critical': False
        }
        
        # Проверка диапазона
        if not (min_val <= value <= max_val):
            error_msg = f"Значение {value} вне допустимого диапазона [{min_val}, {max_val}]"
            result['valid'] = False
            result['errors'].append(error_msg)
            
            if param_name in cls.CRITICAL_THRESHOLDS:
                result['critical'] = True
        
        # Проверка критических порогов
        if param_name in cls.CRITICAL_THRESHOLDS:
            threshold = cls.CRITICAL_THRESHOLDS[param_name]
            if value < threshold['min'] or value > threshold['max']:
                warning_msg = (f"Критическое значение: {value}. "
                             f"Допустимый диапазон: [{threshold['min']}, {threshold['max']}]")
                result['warnings'].append({
                    'message': warning_msg,
                    'level': threshold['level'].value
                })
                if threshold['level'] == ValidationLevel.CRITICAL:
                    result['critical'] = True
        
        # Специфичные проверки для модели
        if model and model in cls.VALID_MODELS:
            result.update(cls._validate_for_model(param_name, value, model))
        
        return result
    
    @classmethod
    def _validate_for_model(cls, param_name: str, value: float, 
                           model: str) -> Dict[str, Any]:
        """Специфичные проверки для модели"""
        result = {}
        warnings = []
        
        model_info = cls.VALID_MODELS[model]
        
        # Проверки для 1.7i
        if '1.7i' in model_info['engines']:
            if param_name == 'fuel_pressure':
                if value < 280:
                    warnings.append("Низкое давление топлива для 1.7i")
                elif value > 320:
                    warnings.append("Высокое давление топлива для 1.7i")
        
        # Проверки для 1.8i
        elif '1.8i' in model_info['engines']:
            if param_name == 'fuel_pressure':
                if value < 350:
                    warnings.append("Низкое давление топлива для 1.8i")
                elif value > 380:
                    warnings.append("Высокое давление топлива для 1.8i")
        
        if warnings:
            result['warnings'] = warnings
        
        return result
    
    @classmethod
    def validate_vehicle_model(cls, model: str, year: int, 
                              engine: str = None) -> Dict[str, Any]:
        """
        Валидация данных автомобиля
        
        Args:
            model: Код модели (2123, 21236 и т.д.)
            year: Год выпуска
            engine: Тип двигателя
            
        Returns:
            Dict с результатами валидации
        """
        result = {
            'valid': True,
            'model': model,
            'year': year,
            'engine': engine,
            'errors': [],
            'warnings': []
        }
        
        # Проверка модели
        if model not in cls.VALID_MODELS:
            result['valid'] = False
            result['errors'].append(f"Неизвестная модель: {model}")
            return result
        
        model_info = cls.VALID_MODELS[model]
        
        # Проверка года выпуска
        if year not in model_info['years']:
            result['valid'] = False
            result['errors'].append(
                f"Год выпуска {year} не поддерживается для модели {model}. "
                f"Поддерживаемые годы: {list(model_info['years'])[0]}-{list(model_info['years'])[-1]}"
            )
        
        # Проверка двигателя
        if engine and engine not in model_info['engines']:
            result['warnings'].append(
                f"Двигатель {engine} не является стандартным для модели {model}. "
                f"Стандартные двигатели: {', '.join(model_info['engines'])}"
            )
        
        return result
    
    @classmethod
    def validate_parameter_list(cls, parameters: Dict[str, float], 
                               model: str = None) -> Dict[str, Any]:
        """
        Валидация списка параметров
        
        Args:
            parameters: Словарь параметров
            model: Модель автомобиля
            
        Returns:
            Результаты валидации
        """
        results = {
            'valid': True,
            'parameters': {},
            'summary': {
                'total': 0,
                'valid': 0,
                'errors': 0,
                'warnings': 0,
                'critical': 0
            }
        }
        
        for param_name, value in parameters.items():
            try:
                param_result = cls.validate_parameter(param_name, value, model)
                results['parameters'][param_name] = param_result
                
                results['summary']['total'] += 1
                if param_result['valid']:
                    results['summary']['valid'] += 1
                else:
                    results['summary']['errors'] += 1
                    results['valid'] = False
                
                results['summary']['warnings'] += len(param_result.get('warnings', []))
                if param_result.get('critical', False):
                    results['summary']['critical'] += 1
                    
            except ValidationError as e:
                results['parameters'][param_name] = {
                    'valid': False,
                    'error': str(e),
                    'value': value
                }
                results['summary']['errors'] += 1
                results['valid'] = False
        
        return results


class ELMCommandValidator:
    """Валидатор команд для ELM327"""
    
    # Регулярные выражения для проверки команд
    AT_COMMAND_REGEX = re.compile(r'^AT[ \t]*[A-Z0-9][A-Z0-9]?[0-9]?[A-Z]?$', re.IGNORECASE)
    OBD_COMMAND_REGEX = re.compile(r'^[0-9A-F]{2}[0-9A-F]{2,}$', re.IGNORECASE)
    CAN_COMMAND_REGEX = re.compile(r'^[0-9A-F]{3}[0-9A-F]{2,}$', re.IGNORECASE)
    
    # Поддерживаемые AT команды
    SUPPORTED_AT_COMMANDS = {
        'ATZ': 'Сброс адаптера',
        'ATI': 'Идентификация адаптера',
        'ATE': 'Включение/выключение эхо',
        'ATL': 'Включение/выключение перевода строки',
        'ATS': 'Включение/выключение пробелов',
        'ATH': 'Включение/выключение заголовков',
        'ATSP': 'Установка протокола',
        'ATDP': 'Описание протокола',
        'ATRV': 'Напряжение питания',
        'AT@1': 'Описание устройства',
        'AT@2': 'Идентификация устройства',
        'ATH0': 'Отключение заголовков',
        'ATH1': 'Включение заголовков',
        'ATE0': 'Отключение эхо',
        'ATE1': 'Включение эхо',
        'ATL0': 'Отключение перевода строки',
        'ATL1': 'Включение перевода строки',
        'ATS0': 'Отключение пробелов',
        'ATS1': 'Включение пробелов',
        'ATSP0': 'Автовыбор протокола',
        'ATSP1': 'Протокол SAE J1850 PWM',
        'ATSP2': 'Протокол SAE J1850 VPW',
        'ATSP3': 'Протокол ISO 9141-2',
        'ATSP4': 'Протокол ISO 14230-4 KWP (5 baud init)',
        'ATSP5': 'Протокол ISO 14230-4 KWP (fast init)',
        'ATSP6': 'Протокол ISO 15765-4 CAN (11 bit ID, 500 kbps)',
        'ATSP7': 'Протокол ISO 15765-4 CAN (29 bit ID, 500 kbps)',
        'ATSP8': 'Протокол ISO 15765-4 CAN (11 bit ID, 250 kbps)',
        'ATSP9': 'Протокол ISO 15765-4 CAN (29 bit ID, 250 kbps)',
        'ATSPA': 'Протокол SAE J1939 CAN (29 bit ID, 250 kbps)',
    }
    
    # Поддерживаемые OBD команды (режимы)
    SUPPORTED_OBD_MODES = {
        '01': 'Текущие данные',
        '02': 'Данные freeze frame',
        '03': 'Диагностические коды неисправностей',
        '04': 'Очистка кодов неисправностей',
        '05': 'Результаты теста кислородного датчика',
        '06': 'Результаты теста непрерывного мониторинга',
        '07': 'Ожидающие коды неисправностей',
        '08': 'Управление бортовыми системами',
        '09': 'Информация об автомобиле',
        '0A': 'Постоянные коды неисправностей',
    }
    
    @classmethod
    def validate_command(cls, command: str, protocol: str = None) -> Dict[str, Any]:
        """
        Валидация команды для ELM327
        
        Args:
            command: Команда для отправки
            protocol: Текущий протокол (для контекстной проверки)
            
        Returns:
            Результаты валидации
        """
        command = command.strip().upper()
        result = {
            'valid': True,
            'command': command,
            'type': None,
            'description': None,
            'errors': [],
            'warnings': []
        }
        
        # Проверка пустой команды
        if not command:
            result['valid'] = False
            result['errors'].append("Пустая команда")
            return result
        
        # Проверка на наличие недопустимых символов
        if not re.match(r'^[A-Z0-9 \t\r\n]*$', command):
            result['valid'] = False
            result['errors'].append("Команда содержит недопустимые символы")
            return result
        
        # Определение типа команды
        if command.startswith('AT'):
            result['type'] = 'AT_COMMAND'
            cls._validate_at_command(command, result, protocol)
        elif re.match(r'^[0-9A-F]{2}', command):
            result['type'] = 'OBD_COMMAND'
            cls._validate_obd_command(command, result, protocol)
        elif re.match(r'^[0-9A-F]{3}', command):
            result['type'] = 'CAN_COMMAND'
            cls._validate_can_command(command, result, protocol)
        else:
            result['valid'] = False
            result['errors'].append(f"Неизвестный формат команды: {command}")
        
        return result
    
    @classmethod
    def _validate_at_command(cls, command: str, result: Dict[str, Any], 
                            protocol: str = None):
        """Валидация AT команды"""
        # Проверка формата
        if not cls.AT_COMMAND_REGEX.match(command):
            result['valid'] = False
            result['errors'].append("Неверный формат AT команды")
            return
        
        # Извлечение чистой команды (без пробелов)
        clean_cmd = re.sub(r'[ \t]', '', command)
        
        # Проверка поддержки команды
        if clean_cmd not in cls.SUPPORTED_AT_COMMANDS:
            result['warnings'].append(f"Команда {clean_cmd} может не поддерживаться адаптером")
        else:
            result['description'] = cls.SUPPORTED_AT_COMMANDS[clean_cmd]
        
        # Специфичные проверки
        if clean_cmd.startswith('ATSP'):
            if len(clean_cmd) > 4:
                proto_code = clean_cmd[4:]
                if not proto_code.isalnum():
                    result['valid'] = False
                    result['errors'].append(f"Недопустимый код протокола: {proto_code}")
    
    @classmethod
    def _validate_obd_command(cls, command: str, result: Dict[str, Any], 
                             protocol: str = None):
        """Валидация OBD команды"""
        # Проверка минимальной длины
        if len(command) < 4:
            result['valid'] = False
            result['errors'].append("Слишком короткая OBD команда")
            return
        
        # Проверка режима
        mode = command[0:2]
        if mode not in cls.SUPPORTED_OBD_MODES:
            result['warnings'].append(f"Неизвестный режим: {mode}")
        else:
            result['description'] = f"{cls.SUPPORTED_OBD_MODES[mode]} (PID: {command[2:]})"
        
        # Проверка PID (для режима 01)
        if mode == '01' and len(command) >= 4:
            pid = command[2:4]
            if not cls._is_valid_pid(pid):
                result['warnings'].append(f"PID {pid} может не поддерживаться")
        
        # Проверка длины команды
        if len(command) % 2 != 0:
            result['valid'] = False
            result['errors'].append("Длина команды должна быть четной")
        
        # Проверка hex формата
        try:
            int(command, 16)
        except ValueError:
            result['valid'] = False
            result['errors'].append("Команда должна содержать только hex символы")
    
    @classmethod
    def _validate_can_command(cls, command: str, result: Dict[str, Any], 
                             protocol: str = None):
        """Валидация CAN команды"""
        # Проверка минимальной длины
        if len(command) < 5:
            result['valid'] = False
            result['errors'].append("Слишком короткая CAN команда")
            return
        
        # Проверка идентификатора
        can_id = command[0:3]
        try:
            int(can_id, 16)
        except ValueError:
            result['valid'] = False
            result['errors'].append(f"Недопустимый CAN ID: {can_id}")
        
        # Проверка данных
        if len(command) > 3:
            data = command[3:]
            if len(data) % 2 != 0:
                result['valid'] = False
                result['errors'].append("Длина данных должна быть четной")
            
            try:
                int(data, 16)
            except ValueError:
                result['valid'] = False
                result['errors'].append("Данные должны содержать только hex символы")
        
        result['description'] = f"CAN команда (ID: {can_id})"
    
    @classmethod
    def _is_valid_pid(cls, pid: str) -> bool:
        """Проверка валидности PID"""
        try:
            pid_int = int(pid, 16)
            return 0x00 <= pid_int <= 0xFF
        except ValueError:
            return False
    
    @classmethod
    def validate_response(cls, command: str, response: str, 
                         protocol: str = None) -> Dict[str, Any]:
        """
        Валидация ответа от ELM327
        
        Args:
            command: Отправленная команда
            response: Полученный ответ
            protocol: Текущий протокол
            
        Returns:
            Результаты валидации
        """
        result = {
            'valid': True,
            'command': command,
            'response': response,
            'type': None,
            'errors': [],
            'warnings': []
        }
        
        # Проверка пустого ответа
        if not response:
            result['valid'] = False
            result['errors'].append("Пустой ответ от адаптера")
            return result
        
        # Нормализация ответа
        response = response.strip()
        
        # Определение типа ответа
        if response.startswith('AT'):
            result['type'] = 'AT_RESPONSE'
        elif 'NO DATA' in response:
            result['type'] = 'NO_DATA'
            result['warnings'].append("Адаптер не получил данные от ECU")
        elif 'ERROR' in response:
            result['type'] = 'ERROR'
            result['valid'] = False
            result['errors'].append(f"Ошибка адаптера: {response}")
        elif 'UNABLE TO CONNECT' in response:
            result['type'] = 'CONNECTION_ERROR'
            result['valid'] = False
            result['errors'].append("Невозможно подключиться к ECU")
        elif 'STOPPED' in response:
            result['type'] = 'STOPPED'
            result['warnings'].append("Адаптер остановлен")
        elif re.match(r'^[0-9A-F ]+$', response):
            result['type'] = 'DATA_RESPONSE'
            cls._validate_data_response(command, response, result, protocol)
        else:
            result['type'] = 'UNKNOWN'
            result['warnings'].append(f"Неизвестный формат ответа: {response}")
        
        return result
    
    @classmethod
    def _validate_data_response(cls, command: str, response: str, 
                               result: Dict[str, Any], protocol: str = None):
        """Валидация ответа с данными"""
        # Очистка пробелов
        clean_response = re.sub(r'\s+', '', response)
        
        # Проверка минимальной длины
        if len(clean_response) < 4:
            result['valid'] = False
            result['errors'].append("Слишком короткий ответ")
            return
        
        # Проверка hex формата
        try:
            int(clean_response, 16)
        except ValueError:
            result['valid'] = False
            result['errors'].append("Ответ содержит не hex символы")
            return
        
        # Проверка заголовка (если включены заголовки)
        if protocol and protocol.startswith('CAN'):
            # Для CAN протоколов ответ должен содержать заголовок
            if len(clean_response) < 8:
                result['warnings'].append("Ответ может не содержать полный заголовок")
        
        # Проверка длины данных
        if len(clean_response) % 2 != 0:
            result['warnings'].append("Нечетная длина ответа")
        
        # Проверка на наличие мусора
        if '?' in response or '<' in response or '>' in response:
            result['warnings'].append("Ответ может содержать мусорные символы")


class DTCValidator:
    """Валидатор диагностических кодов неисправностей"""
    
    # Форматы DTC
    DTC_FORMATS = {
        'SAE_J2012': re.compile(r'^[PBCU][0-9]{4}$'),
        'ISO_15031': re.compile(r'^[0-9A-F]{5}$'),
        'MANUFACTURER': re.compile(r'^[0-9A-F]{6}$'),
    }
    
    # Категории DTC
    DTC_CATEGORIES = {
        'P': {
            'code': 'Powertrain',
            'subcategories': {
                '0': 'SAE - общие',
                '1': 'Производитель - специфичные',
                '2': 'SAE - общие',
                '3': 'Производитель - специфичные'
            }
        },
        'C': {
            'code': 'Chassis',
            'subcategories': {
                '0': 'SAE - общие',
                '1': 'Производитель - специфичные',
                '2': 'SAE - общие',
                '3': 'Производитель - специфичные'
            }
        },
        'B': {
            'code': 'Body',
            'subcategories': {
                '0': 'SAE - общие',
                '1': 'Производитель - специфичные',
                '2': 'SAE - общие',
                '3': 'Производитель - специфичные'
            }
        },
        'U': {
            'code': 'Network',
            'subcategories': {
                '0': 'SAE - общие',
                '1': 'Производитель - специфичные',
                '2': 'SAE - общие',
                '3': 'Производитель - специфичные'
            }
        }
    }
    
    # Специфичные коды для Chevrolet Niva
    NIVA_SPECIFIC_DTCS = {
        'P0016': 'Несоответствие фаз газораспределения (ряд 1)',
        'P0030': 'Цепь управления подогревателем датчика кислорода (ряд 1, датчик 1)',
        'P0036': 'Цепь управления подогревателем датчика кислорода (ряд 1, датчик 2)',
        'P0102': 'Низкий уровень сигнала датчика массового расхода воздуха',
        'P0103': 'Высокий уровень сигнала датчика массового расхода воздуха',
        'P0112': 'Низкая температура впускного воздуха',
        '0113': 'Высокая температура впускного воздуха',
        'P0116': 'Диапазон/рабочие характеристики датчика температуры охлаждающей жидкости',
        'P0117': 'Низкий сигнал датчика температуры охлаждающей жидкости',
        'P0118': 'Высокий сигнал датчика температуры охлаждающей жидкости',
        'P0122': 'Низкий сигнал датчика положения дроссельной заслонки',
        'P0123': 'Высокий сигнал датчика положения дроссельной заслонки',
        'P0130': 'Неисправность цепи датчика кислорода (ряд 1, датчик 1)',
        'P0131': 'Низкое напряжение датчика кислорода (ряд 1, датчик 1)',
        'P0132': 'Высокое напряжение датчика кислорода (ряд 1, датчик 1)',
        'P0133': 'Медленный отклик датчика кислорода (ряд 1, датчик 1)',
        'P0134': 'Отсутствие активности датчика кислорода (ряд 1, датчик 1)',
        'P0135': 'Неисправность цепи подогревателя датчика кислорода (ряд 1, датчик 1)',
        'P0136': 'Неисправность цепи датчика кислорода (ряд 1, датчик 2)',
        'P0137': 'Низкое напряжение датчика кислорода (ряд 1, датчик 2)',
        'P0138': 'Высокое напряжение датчика кислорода (ряд 1, датчик 2)',
        'P0140': 'Отсутствие активности датчика кислорода (ряд 1, датчик 2)',
        'P0141': 'Неисправность цепи подогревателя датчика кислорода (ряд 1, датчик 2)',
        'P0171': 'Слишком бедная смесь (ряд 1)',
        'P0172': 'Слишком богатая смесь (ряд 1)',
        'P0201': 'Неисправность цепи управления форсункой 1',
        'P0202': 'Неисправность цепи управления форсункой 2',
        'P0203': 'Неисправность цепи управления форсункой 3',
        'P0204': 'Неисправность цепи управления форсункой 4',
        'P0300': 'Пропуски воспламенения в нескольких цилиндрах',
        'P0301': 'Пропуски воспламенения в цилиндре 1',
        'P0302': 'Пропуски воспламенения в цилиндре 2',
        'P0303': 'Пропуски воспламенения в цилиндре 3',
        'P0304': 'Пропуски воспламенения в цилиндре 4',
        'P0325': 'Неисправность цепи датчика детонации (ряд 1)',
        'P0327': 'Низкий сигнал датчика детонации (ряд 1)',
        'P0328': 'Высокий сигнал датчика детонации (ряд 1)',
        'P0335': 'Неисправность цепи датчика положения коленчатого вала',
        'P0336': 'Диапазон/рабочие характеристики датчика положения коленчатого вала',
        'P0340': 'Неисправность цепи датчика положения распределительного вала',
        'P0341': 'Диапазон/рабочие характеристики датчика положения распределительного вала',
        'P0351': 'Неисправность цепи катушки зажигания A',
        'P0352': 'Неисправность цепи катушки зажигания B',
        'P0353': 'Неисправность цепи катушки зажигания C',
        'P0354': 'Неисправность цепи катушки зажигания D',
        'P0420': 'Низкая эффективность системы нейтрализации отработавших газов (ряд 1)',
        'P0443': 'Неисправность цепи клапана продувки адсорбера',
        'P0458': 'Низкий сигнал цепи клапана продувки адсорбера',
        'P0459': 'Высокий сигнал цепи клавана продувки адсорбера',
        'P0500': 'Неисправность датчика скорости автомобиля',
        'P0506': 'Низкие обороты холостого хода',
        'P0507': 'Высокие обороты холостого хода',
        'P0562': 'Низкое напряжение системы',
        'P0563': 'Высокое напряжение системы',
        'P0601': 'Неисправность контрольной суммы памяти ЭБУ',
        'P0602': 'Незапрограммированный ЭБУ',
        'P0604': 'Неисправность оперативного запоминающего устройства ЭБУ',
        'P0605': 'Неисправность постоянного запоминающего устройства ЭБУ',
        'P0606': 'Неисправность процессора ЭБУ',
        'P0607': 'Неисправность модуля контроля ЭБУ',
        'P0608': 'Неисправность датчика скорости передачи данных VSS "A"',
        'P0615': 'Неисправность цепи реле стартера',
        'P0616': 'Низкий сигнал цепи реле стартера',
        'P0617': 'Высокий сигнал цепи реле стартера',
        'P062F': 'Неисправность энергонезависимой памяти ЭБУ',
        'P0630': 'Неверный VIN код',
        'P0638': 'Диапазон/рабочие характеристики дроссельной заслонки (ряд 1)',
        'P0685': 'Неисправность цепи реле главного ЭБУ',
        'P1102': 'Низкое сопротивление подогревателя датчика кислорода (ряд 1, датчик 1)',
        'P1103': 'Высокое сопротивление подогревателя датчика кислорода (ряд 1, датчик 1)',
        'P1115': 'Низкое сопротивление подогревателя датчика кислорода (ряд 1, датчик 2)',
        'P1116': 'Высокое сопротивление подогревателя датчика кислорода (ряд 1, датчик 2)',
        'P1123': 'Низкий сигнал датчика положения дроссельной заслонки 1',
        'P1124': 'Высокий сигнал датчика положения дроссельной заслонки 1',
        'P1125': 'Неисправность привода дроссельной заслонки',
        'P1127': 'Неисправность цепи подогрева датчика температуры впускного воздуха',
        'P1128': 'Неисправность цепи вентилятора системы охлаждения',
        'P1130': 'Неисправность цепи датчика кислорода (ряд 1, датчик 1) - Chevrolet Niva',
        'P1131': 'Обрыв цепи датчика кислорода (ряд 1, датчик 1) - Chevrolet Niva',
        'P1132': 'Короткое замыкание на массу датчика кислорода (ряд 1, датчик 1) - Chevrolet Niva',
        'P1133': 'Короткое замыкание на питание датчика кислорода (ряд 1, датчик 1) - Chevrolet Niva',
        'P1135': 'Неисправность цепи подогревателя датчика кислорода (ряд 1, датчик 1) - Chevrolet Niva',
        'P1136': 'Обрыв цепи подогревателя датчика кислорода (ряд 1, датчик 1) - Chevrolet Niva',
        'P1137': 'Короткое замыкание на массу подогревателя (ряд 1, датчик 1) - Chevrolet Niva',
        'P1138': 'Короткое замыкание на питание подогревателя (ряд 1, датчик 1) - Chevrolet Niva',
        'P1500': 'Неисправность цепи датчика скорости автомобиля - Chevrolet Niva',
        'P1501': 'Нет сигнала датчика скорости автомобиля - Chevrolet Niva',
        'P1502': 'Низкий сигнал датчика скорости автомобиля - Chevrolet Niva',
        'P1503': 'Высокий сигнал датчика скорости автомобиля - Chevrolet Niva',
        'P1545': 'Неисправность цепи клапана поддержания холостого хода - Chevrolet Niva',
        'P1546': 'Обрыв цепи клапана поддержания холостого хода - Chevrolet Niva',
        'P1547': 'Короткое замыкание на массу клапана ХХ - Chevrolet Niva',
        'P1548': 'Короткое замыкание на питание клапана ХХ - Chevrolet Niva',
        'P1560': 'Неисправность системы кондиционирования - Chevrolet Niva',
        'P1561': 'Обрыв цепи компрессора кондиционера - Chevrolet Niva',
        'P1562': 'Короткое замыкание компрессора кондиционера - Chevrolet Niva',
        'P1602': 'Потеря связи с АБС - Chevrolet Niva',
        'P1603': 'Потеря связи с иммобилайзером - Chevrolet Niva',
        'P1604': 'Потеря связи с приборной панелью - Chevrolet Niva',
        'U0001': 'Неисправность высокоскоростной CAN шины',
        'U0002': 'Неисправность низкоскоростной CAN шины',
        'U0100': 'Потеря связи с ECM',
        'U0101': 'Потеря связи с TCM',
        'U0121': 'Потеря связи с ABS',
        'U0140': 'Потеря связи с BCM',
        'U0155': 'Потеря связи с приборной панелью',
        'U0164': 'Потеря связи с модулем HVAC',
        'U0300': 'Несовместимость программного обеспечения ECM',
        'U0301': 'Несовместимость программного обеспечения TCM',
    }
    
    @classmethod
    def validate_dtc(cls, dtc_code: str, format_type: str = 'SAE_J2012') -> Dict[str, Any]:
        """
        Валидация диагностического кода неисправности
        
        Args:
            dtc_code: Код неисправности
            format_type: Формат кода
            
        Returns:
            Результаты валидации
        """
        dtc_code = dtc_code.strip().upper()
        result = {
            'valid': True,
            'dtc': dtc_code,
            'format': format_type,
            'category': None,
            'description': None,
            'severity': 'UNKNOWN',
            'errors': [],
            'warnings': []
        }
        
        # Проверка длины
        if len(dtc_code) < 4:
            result['valid'] = False
            result['errors'].append(f"Слишком короткий DTC код: {dtc_code}")
            return result
        
        # Валидация по формату
        if format_type in cls.DTC_FORMATS:
            if not cls.DTC_FORMATS[format_type].match(dtc_code):
                result['valid'] = False
                result['errors'].append(f"DTC код не соответствует формату {format_type}")
                return result
        
        # Определение категории
        if dtc_code[0] in cls.DTC_CATEGORIES:
            category = cls.DTC_CATEGORIES[dtc_code[0]]
            result['category'] = category['code']
            
            # Определение подкатегории
            if len(dtc_code) > 1 and dtc_code[1] in category['subcategories']:
                subcategory = category['subcategories'][dtc_code[1]]
                result['subcategory'] = subcategory
        
        # Поиск описания
        if dtc_code in cls.NIVA_SPECIFIC_DTCS:
            result['description'] = cls.NIVA_SPECIFIC_DTCS[dtc_code]
            result['manufacturer_specific'] = True
            result['severity'] = cls._determine_severity(dtc_code)
        else:
            result['warnings'].append(f"Неизвестный DTC код: {dtc_code}")
            result['description'] = "Код не найден в базе Chevrolet Niva"
            result['manufacturer_specific'] = False
        
        # Проверка на валидный hex
        try:
            int(dtc_code[1:], 16)
        except ValueError:
            result['valid'] = False
            result['errors'].append("DTC код содержит недопустимые символы")
        
        return result
    
    @classmethod
    def _determine_severity(cls, dtc_code: str) -> str:
        """Определение серьезности ошибки"""
        # Критические коды
        critical_codes = ['P0016', 'P0300', 'P0301', 'P0302', 'P0303', 'P0304',
                         'P0325', 'P0335', 'P0340', 'P0351', 'P0352', 'P0353',
                         'P0354', 'P0562', 'P0563', 'P0601', 'P0602', 'P0604',
                         'P0605', 'P0606', 'P0607', 'P0608', 'U0001', 'U0002']
        
        # Важные коды
        important_codes = ['P0102', 'P0103', 'P0116', 'P0117', 'P0118',
                          'P0122', 'P0123', 'P0130', 'P0135', 'P0136',
                          'P0141', 'P0171', 'P0172', 'P0201', 'P0202',
                          'P0203', 'P0204', 'P0420', 'P0443', 'P0500',
                          'P0506', 'P0507', 'U0100', 'U0101', 'U0121']
        
        if dtc_code in critical_codes:
            return 'CRITICAL'
        elif dtc_code in important_codes:
            return 'IMPORTANT'
        else:
            return 'NORMAL'
    
    @classmethod
    def validate_dtc_list(cls, dtc_list: List[str], 
                         format_type: str = 'SAE_J2012') -> Dict[str, Any]:
        """
        Валидация списка DTC кодов
        
        Args:
            dtc_list: Список кодов неисправностей
            format_type: Формат кодов
            
        Returns:
            Результаты валидации
        """
        results = {
            'valid': True,
            'dtcs': [],
            'summary': {
                'total': len(dtc_list),
                'valid': 0,
                'errors': 0,
                'warnings': 0,
                'critical': 0,
                'important': 0,
                'normal': 0
            }
        }
        
        for dtc in dtc_list:
            try:
                dtc_result = cls.validate_dtc(dtc, format_type)
                results['dtcs'].append(dtc_result)
                
                if dtc_result['valid']:
                    results['summary']['valid'] += 1
                    
                    # Подсчет по серьезности
                    severity = dtc_result.get('severity', 'NORMAL')
                    if severity == 'CRITICAL':
                        results['summary']['critical'] += 1
                    elif severity == 'IMPORTANT':
                        results['summary']['important'] += 1
                    else:
                        results['summary']['normal'] += 1
                else:
                    results['summary']['errors'] += 1
                    results['valid'] = False
                
                results['summary']['warnings'] += len(dtc_result.get('warnings', []))
                
            except Exception as e:
                results['dtcs'].append({
                    'valid': False,
                    'dtc': dtc,
                    'error': str(e)
                })
                results['summary']['errors'] += 1
                results['valid'] = False
        
        return results
    
    @classmethod
    def decode_dtc_from_bytes(cls, bytes_hex: str) -> str:
        """
        Декодирование DTC из hex байтов
        
        Args:
            bytes_hex: Hex строка с байтами DTC
            
        Returns:
            DTC код
        """
        if not bytes_hex or len(bytes_hex) < 4:
            return ""
        
        # Очистка от пробелов
        bytes_hex = re.sub(r'\s+', '', bytes_hex)
        
        if len(bytes_hex) != 4:
            raise ValidationError(f"Неверная длина байтов DTC: {len(bytes_hex)}")
        
        try:
            # Конвертация hex в байты
            byte1 = int(bytes_hex[0:2], 16)
            byte2 = int(bytes_hex[2:4], 16)
            
            # Декодирование согласно SAE J2012
            dtc_byte1 = byte1
            dtc_byte2 = byte2
            
            # Определение типа неисправности
            fault_type = (dtc_byte1 >> 6) & 0x03
            fault_chars = ['P', 'C', 'B', 'U']
            
            if fault_type >= len(fault_chars):
                raise ValidationError(f"Неизвестный тип неисправности: {fault_type}")
            
            fault_char = fault_chars[fault_type]
            
            # Формирование кода
            dtc_num = ((dtc_byte1 & 0x3F) << 8) | dtc_byte2
            
            return f"{fault_char}{dtc_num:04d}"
            
        except ValueError as e:
            raise ValidationError(f"Ошибка декодирования DTC: {e}")


class ConnectionValidator:
    """Валидатор параметров подключения"""
    
    # Допустимые параметры Bluetooth
    BLUETOOTH_PARAMS = {
        'address': re.compile(r'^([0-9A-F]{2}:){5}[0-9A-F]{2}$', re.IGNORECASE),
        'name': re.compile(r'^[A-Z0-9_\- ]{1,30}$', re.IGNORECASE),
        'port': (1, 30),
        'timeout': (1, 60),
    }
    
    # Допустимые параметры Serial
    SERIAL_PARAMS = {
        'port': re.compile(r'^(COM[0-9]{1,3}|/dev/tty(USB|ACM|S)[0-9]{1,3})$', re.IGNORECASE),
        'baudrate': [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600],
        'bytesize': [5, 6, 7, 8],
        'parity': ['N', 'E', 'O', 'M', 'S'],
        'stopbits': [1, 1.5, 2],
        'timeout': (0.1, 60.0),
    }
    
    # Допустимые параметры WiFi
    WIFI_PARAMS = {
        'host': re.compile(r'^(\d{1,3}\.){3}\d{1,3}$'),
        'port': (1, 65535),
        'timeout': (1, 60),
    }
    
    @classmethod
    def validate_bluetooth_connection(cls, address: str, port: int = 1, 
                                     timeout: int = 10) -> Dict[str, Any]:
        """
        Валидация параметров Bluetooth подключения
        
        Args:
            address: MAC адрес устройства
            port: Номер порта (канала)
            timeout: Таймаут подключения
            
        Returns:
            Результаты валидации
        """
        result = {
            'valid': True,
            'type': 'bluetooth',
            'parameters': {
                'address': address,
                'port': port,
                'timeout': timeout
            },
            'errors': [],
            'warnings': []
        }
        
        # Валидация MAC адреса
        if not cls.BLUETOOTH_PARAMS['address'].match(address):
            result['valid'] = False
            result['errors'].append(f"Неверный формат MAC адреса: {address}")
        
        # Валидация порта
        min_port, max_port = cls.BLUETOOTH_PARAMS['port']
        if not (min_port <= port <= max_port):
            result['valid'] = False
            result['errors'].append(f"Номер порта должен быть в диапазоне [{min_port}, {max_port}]")
        
        # Валидация таймаута
        min_timeout, max_timeout = cls.BLUETOOTH_PARAMS['timeout']
        if not (min_timeout <= timeout <= max_timeout):
            result['warnings'].append(f"Таймаут рекомендуется в диапазоне [{min_timeout}, {max_timeout}] секунд")
        
        # Проверка на локальный адрес
        if address.startswith('00:00:00'):
            result['warnings'].append("MAC адрес может быть невалидным (нулевой)")
        
        return result
    
    @classmethod
    def validate_serial_connection(cls, port: str, baudrate: int = 38400,
                                  bytesize: int = 8, parity: str = 'N',
                                  stopbits: float = 1, timeout: float = 1.0) -> Dict[str, Any]:
        """
        Валидация параметров Serial подключения
        
        Args:
            port: Имя порта (COMx или /dev/ttyXXX)
            baudrate: Скорость передачи
            bytesize: Размер байта
            parity: Четность
            stopbits: Стоповые биты
            timeout: Таймаут
            
        Returns:
            Результаты валидации
        """
        result = {
            'valid': True,
            'type': 'serial',
            'parameters': {
                'port': port,
                'baudrate': baudrate,
                'bytesize': bytesize,
                'parity': parity,
                'stopbits': stopbits,
                'timeout': timeout
            },
            'errors': [],
            'warnings': []
        }
        
        # Валидация порта
        if not cls.SERIAL_PARAMS['port'].match(port):
            result['valid'] = False
            result['errors'].append(f"Неверный формат порта: {port}")
        
        # Валидация скорости
        if baudrate not in cls.SERIAL_PARAMS['baudrate']:
            result['warnings'].append(f"Скорость {baudrate} может не поддерживаться. "
                                    f"Рекомендуется: {cls.SERIAL_PARAMS['baudrate']}")
        
        # Валидация размера байта
        if bytesize not in cls.SERIAL_PARAMS['bytesize']:
            result['valid'] = False
            result['errors'].append(f"Неверный размер байта: {bytesize}. "
                                  f"Допустимо: {cls.SERIAL_PARAMS['bytesize']}")
        
        # Валидация четности
        if parity.upper() not in cls.SERIAL_PARAMS['parity']:
            result['valid'] = False
            result['errors'].append(f"Неверный параметр четности: {parity}. "
                                  f"Допустимо: {cls.SERIAL_PARAMS['parity']}")
        
        # Валидация стоповых битов
        if stopbits not in cls.SERIAL_PARAMS['stopbits']:
            result['valid'] = False
            result['errors'].append(f"Неверное количество стоповых битов: {stopbits}. "
                                  f"Допустимо: {cls.SERIAL_PARAMS['stopbits']}")
        
        # Валидация таймаута
        min_timeout, max_timeout = cls.SERIAL_PARAMS['timeout']
        if not (min_timeout <= timeout <= max_timeout):
            result['warnings'].append(f"Таймаут рекомендуется в диапазоне [{min_timeout}, {max_timeout}] секунд")
        
        # Проверка скорости для ELM327
        if baudrate not in [38400, 115200]:
            result['warnings'].append("Для ELM327 рекомендуется скорость 38400 или 115200")
        
        return result
    
    @classmethod
    def validate_wifi_connection(cls, host: str, port: int = 35000,
                                timeout: int = 10) -> Dict[str, Any]:
        """
        Валидация параметров WiFi подключения
        
        Args:
            host: IP адрес
            port: Номер порта
            timeout: Таймаут подключения
            
        Returns:
            Результаты валидации
        """
        result = {
            'valid': True,
            'type': 'wifi',
            'parameters': {
                'host': host,
                'port': port,
                'timeout': timeout
            },
            'errors': [],
            'warnings': []
        }
        
        # Валидация IP адреса
        try:
            ipaddress.ip_address(host)
        except ValueError:
            result['valid'] = False
            result['errors'].append(f"Неверный IP адрес: {host}")
        
        # Проверка на локальный адрес
        try:
            ip = ipaddress.ip_address(host)
            if not ip.is_private:
                result['warnings'].append("IP адрес не является приватным (локальным)")
        except:
            pass
        
        # Валидация порта
        min_port, max_port = cls.WIFI_PARAMS['port']
        if not (min_port <= port <= max_port):
            result['valid'] = False
            result['errors'].append(f"Номер порта должен быть в диапазоне [{min_port}, {max_port}]")
        
        # Проверка стандартного порта ELM327 WiFi
        if port != 35000:
            result['warnings'].append(f"Стандартный порт для ELM327 WiFi: 35000")
        
        # Валидация таймаута
        min_timeout, max_timeout = cls.WIFI_PARAMS['timeout']
        if not (min_timeout <= timeout <= max_timeout):
            result['warnings'].append(f"Таймаут рекомендуется в диапазоне [{min_timeout}, {max_timeout}] секунд")
        
        return result
    
    @classmethod
    def validate_connection_type(cls, connection_type: str) -> bool:
        """
        Валидация типа подключения
        
        Args:
            connection_type: Тип подключения
            
        Returns:
            True если тип валиден
        """
        valid_types = ['bluetooth', 'serial', 'usb', 'wifi']
        return connection_type.lower() in valid_types


class AdaptationValidator:
    """Валидатор параметров адаптации"""
    
    # Допустимые диапазоны для адаптации
    ADAPTATION_RANGES = {
        'idle_speed': (700, 900),  # RPM
        'idle_co2': (0.5, 2.5),    # %
        'fuel_trim_short': (-25, 25),  # %
        'fuel_trim_long': (-25, 25),   # %
        'throttle_position': (0, 100),  # %
        'throttle_learning_value': (0, 255),  # raw
        'injector_correction': (-10, 10),  # %
        'ignition_timing': (-10, 10),  # градусы
        'lambda_control': (0.8, 1.2),  # λ
        'evap_purge': (0, 100),  # %
        'egr_position': (0, 100),  # %
        'vvt_position': (0, 100),  # %
        'turbo_wastegate': (0, 100),  # %
        'coolant_fan_temp': (85, 105),  # °C
        'ac_pressure_limit': (100, 300),  # kPa
        'fuel_pressure': (250, 400),  # kPa
        'oil_pressure_warning': (50, 150),  # kPa
    }
    
    # Заводские настройки для разных моделей
    FACTORY_SETTINGS = {
        '2123': {  # 1.7i 2002-2009
            'idle_speed': 800,
            'idle_co2': 1.5,
            'throttle_learning_value': 128,
            'coolant_fan_temp': 92,
            'fuel_pressure': 300,
        },
        '21236': {  # 1.7i 2010-2020
            'idle_speed': 800,
            'idle_co2': 1.5,
            'throttle_learning_value': 128,
            'coolant_fan_temp': 94,
            'fuel_pressure': 300,
        },
        '2123-250': {  # 1.8i 2014-2020
            'idle_speed': 750,
            'idle_co2': 1.2,
            'throttle_learning_value': 128,
            'coolant_fan_temp': 96,
            'fuel_pressure': 350,
        },
        '2123M': {  # Модерн 2021+
            'idle_speed': 750,
            'idle_co2': 1.0,
            'throttle_learning_value': 128,
            'coolant_fan_temp': 98,
            'fuel_pressure': 380,
        }
    }
    
    @classmethod
    def validate_adaptation_value(cls, param_name: str, value: float, 
                                 model: str = None) -> Dict[str, Any]:
        """
        Валидация значения для адаптации
        
        Args:
            param_name: Название параметра
            value: Значение
            model: Модель автомобиля
            
        Returns:
            Результаты валидации
        """
        if param_name not in cls.ADAPTATION_RANGES:
            raise ValidationError(
                f"Неизвестный параметр адаптации: {param_name}",
                field=param_name,
                value=value
            )
        
        min_val, max_val = cls.ADAPTATION_RANGES[param_name]
        result = {
            'valid': True,
            'parameter': param_name,
            'value': value,
            'range': (min_val, max_val),
            'factory_value': None,
            'difference': None,
            'errors': [],
            'warnings': []
        }
        
        # Проверка диапазона
        if not (min_val <= value <= max_val):
            result['valid'] = False
            result['errors'].append(
                f"Значение {value} вне допустимого диапазона [{min_val}, {max_val}]"
            )
        
        # Сравнение с заводскими настройками
        if model and model in cls.FACTORY_SETTINGS:
            factory_settings = cls.FACTORY_SETTINGS[model]
            if param_name in factory_settings:
                factory_value = factory_settings[param_name]
                result['factory_value'] = factory_value
                result['difference'] = value - factory_value
                
                # Предупреждение при большом отклонении
                diff_percent = abs(result['difference'] / factory_value * 100) if factory_value != 0 else 0
                if diff_percent > 20:
                    result['warnings'].append(
                        f"Большое отклонение от заводской настройки: {diff_percent:.1f}%"
                    )
        
        # Дополнительные проверки для специфичных параметров
        cls._validate_specific_parameter(param_name, value, result, model)
        
        return result
    
    @classmethod
    def _validate_specific_parameter(cls, param_name: str, value: float,
                                    result: Dict[str, Any], model: str = None):
        """Специфичные проверки для параметров"""
        if param_name == 'idle_speed':
            if value < 700:
                result['warnings'].append("Слишком низкие обороты холостого хода")
            elif value > 900:
                result['warnings'].append("Слишком высокие обороты холостого хода")
        
        elif param_name == 'fuel_pressure':
            if model in ['2123', '21236'] and value > 320:
                result['warnings'].append("Высокое давление топлива для 1.7i")
            elif model == '2123-250' and value > 380:
                result['warnings'].append("Высокое давление топлива для 1.8i")
            elif model == '2123M' and value > 400:
                result['warnings'].append("Высокое давление топлива для модерна")
        
        elif param_name == 'coolant_fan_temp':
            if value > 100:
                result['warnings'].append("Высокая температура включения вентилятора")
    
    @classmethod
    def validate_adaptation_procedure(cls, procedure: str, 
                                     vehicle_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Валидация процедуры адаптации
        
        Args:
            procedure: Название процедуры
            vehicle_state: Текущее состояние автомобиля
            
        Returns:
            Результаты валидации
        """
        result = {
            'valid': True,
            'procedure': procedure,
            'requirements_met': True,
            'missing_requirements': [],
            'errors': [],
            'warnings': []
        }
        
        # Требования для разных процедур
        requirements = {
            'idle_adaptation': {
                'engine_running': True,
                'engine_warm': True,
                'parking_brake': True,
                'neutral_gear': True,
                'ac_off': True,
                'lights_off': True,
                'coolant_temp': (80, 105),
                'battery_voltage': (12.5, 15.0),
            },
            'throttle_adaptation': {
                'ignition_on': True,
                'engine_off': True,
                'throttle_clean': True,
                'battery_voltage': (12.0, 15.0),
            },
            'lambda_adaptation': {
                'engine_running': True,
                'engine_warm': True,
                'catalyst_warm': True,
                'coolant_temp': (80, 105),
                'lambda_active': True,
            },
            'immobilizer_learning': {
                'ignition_on': True,
                'engine_off': True,
                'key_present': True,
                'security_code': True,
            },
            'transmission_adaptation': {
                'engine_running': True,
                'parking_brake': True,
                'brake_pressed': True,
                'coolant_temp': (60, 105),
            },
        }
        
        if procedure not in requirements:
            result['valid'] = False
            result['errors'].append(f"Неизвестная процедура адаптации: {procedure}")
            return result
        
        # Проверка требований
        proc_requirements = requirements[procedure]
        for req_name, req_value in proc_requirements.items():
            actual_value = vehicle_state.get(req_name)
            
            if isinstance(req_value, bool):
                if actual_value != req_value:
                    result['requirements_met'] = False
                    result['missing_requirements'].append(req_name)
            
            elif isinstance(req_value, tuple) and len(req_value) == 2:
                min_val, max_val = req_value
                if actual_value is None or not (min_val <= actual_value <= max_val):
                    result['requirements_met'] = False
                    result['missing_requirements'].append(
                        f"{req_name} (текущее: {actual_value}, требуется: {min_val}-{max_val})"
                    )
        
        if not result['requirements_met']:
            result['valid'] = False
            result['errors'].append("Не выполнены требования для процедуры адаптации")
        
        return result


class VehicleIdentificationValidator:
    """Валидатор идентификационных данных автомобиля"""
    
    # Форматы VIN для Chevrolet Niva
    VIN_REGEX = {
        'STANDARD': re.compile(r'^[A-HJ-NPR-Z0-9]{17}$'),
        'CHEVROLET': re.compile(r'^X9[FLT]2123[0-9A-Z]{10}$'),
    }
    
    # Коды моделей в VIN
    MODEL_CODES = {
        'X9F2123': 'Chevrolet Niva 1.7i Lada',
        'X9L2123': 'Chevrolet Niva 1.7i GM',
        'X9T2123': 'Chevrolet Niva 1.8i',
    }
    
    # Коды двигателей
    ENGINE_CODES = {
        'L67': '1.7i 8V (80 л.с.)',
        'L69': '1.7i 8V (83 л.с.)',
        'L70': '1.7i 8V (80 л.с.) Евро-3',
        'H16M': '1.8i 16V (122 л.с.)',
        'H16N': '1.8i 16V (125 л.с.)',
    }
    
    @classmethod
    def validate_vin(cls, vin: str) -> Dict[str, Any]:
        """
        Валидация VIN номера
        
        Args:
            vin: VIN номер
            
        Returns:
            Результаты валидации
        """
        vin = vin.strip().upper()
        result = {
            'valid': True,
            'vin': vin,
            'format': None,
            'model': None,
            'year': None,
            'plant': None,
            'errors': [],
            'warnings': []
        }
        
        # Проверка длины
        if len(vin) != 17:
            result['valid'] = False
            result['errors'].append(f"Неверная длина VIN: {len(vin)} (должно быть 17)")
            return result
        
        # Проверка стандартного формата
        if cls.VIN_REGEX['STANDARD'].match(vin):
            result['format'] = 'STANDARD'
        elif cls.VIN_REGEX['CHEVROLET'].match(vin):
            result['format'] = 'CHEVROLET'
        else:
            result['valid'] = False
            result['errors'].append("Неверный формат VIN")
            return result
        
        # Проверка контрольной суммы
        if not cls._validate_vin_checksum(vin):
            result['warnings'].append("Неверная контрольная сумма VIN")
        
        # Декодирование VIN
        try:
            decoded = cls._decode_vin(vin)
            result.update(decoded)
        except Exception as e:
            result['warnings'].append(f"Ошибка декодирования VIN: {e}")
        
        # Проверка на Chevrolet Niva
        if result['format'] == 'CHEVROLET':
            model_code = vin[0:7]
            if model_code in cls.MODEL_CODES:
                result['model'] = cls.MODEL_CODES[model_code]
            else:
                result['warnings'].append(f"Неизвестный код модели в VIN: {model_code}")
        
        return result
    
    @classmethod
    def _validate_vin_checksum(cls, vin: str) -> bool:
        """
        Проверка контрольной суммы VIN (9-й символ)
        
        Args:
            vin: VIN номер
            
        Returns:
            True если контрольная сумма верна
        """
        # Таблица замены символов
        transliteration = {
            'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8,
            'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5, 'P': 7, 'R': 9,
            'S': 2, 'T': 3, 'U': 4, 'V': 5, 'W': 6, 'X': 7, 'Y': 8, 'Z': 9,
            '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9
        }
        
        # Весовые коэффициенты
        weights = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]
        
        try:
            total = 0
            for i, char in enumerate(vin):
                if char not in transliteration:
                    return False
                total += transliteration[char] * weights[i]
            
            checksum = total % 11
            if checksum == 10:
                checksum_char = 'X'
            else:
                checksum_char = str(checksum)
            
            return vin[8] == checksum_char
            
        except:
            return False
    
    @classmethod
    def _decode_vin(cls, vin: str) -> Dict[str, Any]:
        """
        Декодирование VIN номера
        
        Args:
            vin: VIN номер
            
        Returns:
            Словарь с декодированными данными
        """
        result = {}
        
        # WMI (World Manufacturer Identifier) - позиции 1-3
        wmi = vin[0:3]
        result['wmi'] = wmi
        
        # VDS (Vehicle Descriptor Section) - позиции 4-9
        vds = vin[3:9]
        result['vds'] = vds
        
        # VIS (Vehicle Identifier Section) - позиции 10-17
        vis = vin[9:17]
        result['vis'] = vis
        
        # Год выпуска (10-й символ)
        year_char = vin[9]
        year = cls._decode_year_char(year_char)
        if year:
            result['year'] = year
        
        # Завод (11-й символ)
        plant_char = vin[10]
        result['plant_code'] = plant_char
        
        # Серийный номер (позиции 12-17)
        serial = vin[11:17]
        result['serial_number'] = serial
        
        return result
    
    @classmethod
    def _decode_year_char(cls, year_char: str) -> Optional[int]:
        """Декодирование символа года"""
        year_codes = {
            'A': 2010, 'B': 2011, 'C': 2012, 'D': 2013, 'E': 2014,
            'F': 2015, 'G': 2016, 'H': 2017, 'J': 2018, 'K': 2019,
            'L': 2020, 'M': 2021, 'N': 2022, 'P': 2023, 'R': 2024,
            'S': 2025, 'T': 2026, 'V': 2027, 'W': 2028, 'X': 2029,
            'Y': 2030,
            '1': 2001, '2': 2002, '3': 2003, '4': 2004, '5': 2005,
            '6': 2006, '7': 2007, '8': 2008, '9': 2009,
        }
        
        return year_codes.get(year_char.upper())
    
    @classmethod
    def validate_engine_code(cls, engine_code: str) -> Dict[str, Any]:
        """
        Валидация кода двигателя
        
        Args:
            engine_code: Код двигателя
            
        Returns:
            Результаты валидации
        """
        engine_code = engine_code.strip().upper()
        result = {
            'valid': True,
            'engine_code': engine_code,
            'description': None,
            'displacement': None,
            'power': None,
            'years': None,
            'errors': [],
            'warnings': []
        }
        
        if engine_code in cls.ENGINE_CODES:
            result['description'] = cls.ENGINE_CODES[engine_code]
            
            # Добавление дополнительной информации
            if engine_code.startswith('L'):
                result['displacement'] = 1.7
                result['power'] = '80-83 л.с.'
                result['years'] = '2002-2020'
            elif engine_code.startswith('H'):
                result['displacement'] = 1.8
                result['power'] = '122-125 л.с.'
                result['years'] = '2014-н.в.'
        else:
            result['valid'] = False
            result['errors'].append(f"Неизвестный код двигателя: {engine_code}")
        
        return result


class InputValidator:
    """Общий валидатор ввода"""
    
    @staticmethod
    def validate_integer(value: Any, min_val: int = None, max_val: int = None,
                        field_name: str = None) -> Dict[str, Any]:
        """
        Валидация целого числа
        
        Args:
            value: Значение для проверки
            min_val: Минимальное значение
            max_val: Максимальное значение
            field_name: Название поля
            
        Returns:
            Результаты валидации
        """
        result = {
            'valid': True,
            'value': None,
            'errors': []
        }
        
        try:
            # Попытка преобразования
            if isinstance(value, str):
                value = value.strip()
                # Удаление посторонних символов
                value = re.sub(r'[^\d\-]', '', value)
            
            int_value = int(value)
            result['value'] = int_value
            
            # Проверка минимального значения
            if min_val is not None and int_value < min_val:
                result['valid'] = False
                result['errors'].append(
                    f"{field_name or 'Значение'} должно быть не меньше {min_val}"
                )
            
            # Проверка максимального значения
            if max_val is not None and int_value > max_val:
                result['valid'] = False
                result['errors'].append(
                    f"{field_name or 'Значение'} должно быть не больше {max_val}"
                )
                
        except (ValueError, TypeError):
            result['valid'] = False
            result['errors'].append(
                f"{field_name or 'Значение'} должно быть целым числом"
            )
        
        return result
    
    @staticmethod
    def validate_float(value: Any, min_val: float = None, max_val: float = None,
                      decimal_places: int = None, field_name: str = None) -> Dict[str, Any]:
        """
        Валидация вещественного числа
        
        Args:
            value: Значение для проверки
            min_val: Минимальное значение
            max_val: Максимальное значение
            decimal_places: Количество знаков после запятой
            field_name: Название поля
            
        Returns:
            Результаты валидации
        """
        result = {
            'valid': True,
            'value': None,
            'errors': []
        }
        
        try:
            # Попытка преобразования
            if isinstance(value, str):
                value = value.strip()
                # Замена запятой на точку
                value = value.replace(',', '.')
                # Удаление посторонних символов
                value = re.sub(r'[^\d\.\-]', '', value)
            
            float_value = float(value)
            result['value'] = float_value
            
            # Проверка минимального значения
            if min_val is not None and float_value < min_val:
                result['valid'] = False
                result['errors'].append(
                    f"{field_name or 'Значение'} должно быть не меньше {min_val}"
                )
            
            # Проверка максимального значения
            if max_val is not None and float_value > max_val:
                result['valid'] = False
                result['errors'].append(
                    f"{field_name or 'Значение'} должно быть не больше {max_val}"
                )
            
            # Проверка количества знаков после запятой
            if decimal_places is not None:
                # Преобразование к строке для проверки
                str_value = str(float_value)
                if '.' in str_value:
                    decimals = len(str_value.split('.')[1])
                    if decimals > decimal_places:
                        result['warnings'] = result.get('warnings', [])
                        result['warnings'].append(
                            f"Рекомендуется не более {decimal_places} знаков после запятой"
                        )
                        
        except (ValueError, TypeError):
            result['valid'] = False
            result['errors'].append(
                f"{field_name or 'Значение'} должно быть числом"
            )
        
        return result
    
    @staticmethod
    def validate_string(value: Any, min_length: int = None, max_length: int = None,
                       pattern: str = None, allowed_chars: str = None,
                       field_name: str = None) -> Dict[str, Any]:
        """
        Валидация строки
        
        Args:
            value: Значение для проверки
            min_length: Минимальная длина
            max_length: Максимальная длина
            pattern: Регулярное выражение
            allowed_chars: Разрешенные символы
            field_name: Название поля
            
        Returns:
            Результаты валидации
        """
        result = {
            'valid': True,
            'value': None,
            'errors': []
        }
        
        try:
            # Преобразование к строке
            str_value = str(value).strip()
            result['value'] = str_value
            
            # Проверка минимальной длины
            if min_length is not None and len(str_value) < min_length:
                result['valid'] = False
                result['errors'].append(
                    f"{field_name or 'Строка'} должна содержать не менее {min_length} символов"
                )
            
            # Проверка максимальной длины
            if max_length is not None and len(str_value) > max_length:
                result['valid'] = False
                result['errors'].append(
                    f"{field_name or 'Строка'} должна содержать не более {max_length} символов"
                )
            
            # Проверка по регулярному выражению
            if pattern:
                if not re.match(pattern, str_value):
                    result['valid'] = False
                    result['errors'].append(
                        f"{field_name or 'Строка'} не соответствует требуемому формату"
                    )
            
            # Проверка разрешенных символов
            if allowed_chars:
                for char in str_value:
                    if char not in allowed_chars:
                        result['valid'] = False
                        result['errors'].append(
                            f"{field_name or 'Строка'} содержит недопустимые символы"
                        )
                        break
                        
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Ошибка валидации строки: {e}")
        
        return result
    
    @staticmethod
    def validate_hex_string(value: Any, min_length: int = None,
                           max_length: int = None, field_name: str = None) -> Dict[str, Any]:
        """
        Валидация hex строки
        
        Args:
            value: Значение для проверки
            min_length: Минимальная длина
            max_length: Максимальная длина
            field_name: Название поля
            
        Returns:
            Результаты валидации
        """
        # Проверка что строка содержит только hex символы
        hex_pattern = r'^[0-9A-Fa-f]+$'
        
        result = InputValidator.validate_string(
            value, min_length, max_length, hex_pattern, field_name
        )
        
        if result['valid']:
            # Дополнительная проверка на четность длины
            hex_value = result['value']
            if len(hex_value) % 2 != 0:
                result['warnings'] = result.get('warnings', [])
                result['warnings'].append("Hex строка должна иметь четную длину")
        
        return result
    
    @staticmethod
    def validate_datetime(value: Any, min_date: datetime = None,
                         max_date: datetime = None, field_name: str = None) -> Dict[str, Any]:
        """
        Валидация даты и времени
        
        Args:
            value: Значение для проверки
            min_date: Минимальная дата
            max_date: Максимальная дата
            field_name: Название поля
            
        Returns:
            Результаты валидации
        """
        result = {
            'valid': True,
            'value': None,
            'errors': []
        }
        
        try:
            # Преобразование к datetime
            if isinstance(value, str):
                # Попробуем разные форматы
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d',
                    '%d.%m.%Y %H:%M:%S',
                    '%d.%m.%Y',
                    '%H:%M:%S'
                ]
                
                dt_value = None
                for fmt in formats:
                    try:
                        dt_value = datetime.strptime(value, fmt)
                        break
                    except ValueError:
                        continue
                
                if dt_value is None:
                    raise ValueError("Неверный формат даты")
                    
            elif isinstance(value, datetime):
                dt_value = value
            elif isinstance(value, date):
                dt_value = datetime.combine(value, datetime.min.time())
            else:
                raise TypeError("Неподдерживаемый тип данных")
            
            result['value'] = dt_value
            
            # Проверка минимальной даты
            if min_date and dt_value < min_date:
                result['valid'] = False
                result['errors'].append(
                    f"{field_name or 'Дата'} не может быть раньше {min_date}"
                )
            
            # Проверка максимальной даты
            if max_date and dt_value > max_date:
                result['valid'] = False
                result['errors'].append(
                    f"{field_name or 'Дата'} не может быть позже {max_date}"
                )
                
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Ошибка валидации даты: {e}")
        
        return result
    
    @staticmethod
    def validate_email(value: Any, field_name: str = None) -> Dict[str, Any]:
        """
        Валидация email адреса
        
        Args:
            value: Значение для проверки
            field_name: Название поля
            
        Returns:
            Результаты валидации
        """
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        result = InputValidator.validate_string(value, pattern=email_pattern, field_name=field_name)
        
        if result['valid']:
            email = result['value']
            # Дополнительные проверки
            if len(email) > 254:
                result['valid'] = False
                result['errors'].append("Email слишком длинный")
            elif email.count('@') != 1:
                result['valid'] = False
                result['errors'].append("Неверный формат email")
        
        return result
    
    @staticmethod
    def validate_phone(value: Any, field_name: str = None) -> Dict[str, Any]:
        """
        Валидация номера телефона
        
        Args:
            value: Значение для проверки
            field_name: Название поля
            
        Returns:
            Результаты валидации
        """
        # Удаление всех нецифровых символов
        if isinstance(value, str):
            digits = re.sub(r'\D', '', value)
        else:
            digits = str(value)
        
        result = {
            'valid': True,
            'value': digits,
            'errors': []
        }
        
        # Проверка длины
        if len(digits) < 10:
            result['valid'] = False
            result['errors'].append(
                f"{field_name or 'Телефон'} должен содержать не менее 10 цифр"
            )
        elif len(digits) > 15:
            result['valid'] = False
            result['errors'].append(
                f"{field_name or 'Телефон'} слишком длинный"
            )
        
        # Проверка формата
        if digits.startswith('0'):
            result['warnings'] = result.get('warnings', [])
            result['warnings'].append("Номер телефона не должен начинаться с 0")
        
        return result


class FileValidator:
    """Валидатор файлов"""
    
    # Разрешенные расширения файлов
    ALLOWED_EXTENSIONS = {
        'config': ['.json', '.ini', '.cfg', '.xml'],
        'report': ['.pdf', '.docx', '.xlsx', '.html', '.txt'],
        'log': ['.log', '.txt', '.csv'],
        'backup': ['.bak', '.backup', '.bin'],
        'image': ['.png', '.jpg', '.jpeg', '.bmp', '.gif'],
    }
    
    # Максимальные размеры файлов (в байтах)
    MAX_FILE_SIZES = {
        'config': 10 * 1024 * 1024,  # 10 MB
        'report': 50 * 1024 * 1024,  # 50 MB
        'log': 100 * 1024 * 1024,    # 100 MB
        'backup': 500 * 1024 * 1024, # 500 MB
        'image': 5 * 1024 * 1024,    # 5 MB
    }
    
    @staticmethod
    def validate_file_path(file_path: str, file_type: str = None,
                          check_exists: bool = True) -> Dict[str, Any]:
        """
        Валидация пути к файлу
        
        Args:
            file_path: Путь к файлу
            file_type: Тип файла
            check_exists: Проверять существование файла
            
        Returns:
            Результаты валидации
        """
        result = {
            'valid': True,
            'file_path': file_path,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Проверка на пустой путь
            if not file_path or not file_path.strip():
                result['valid'] = False
                result['errors'].append("Путь к файлу не может быть пустым")
                return result
            
            # Нормализация пути
            file_path = os.path.normpath(file_path.strip())
            result['file_path'] = file_path
            
            # Проверка на абсолютный путь
            if not os.path.isabs(file_path):
                result['warnings'].append("Используется относительный путь")
            
            # Проверка существования файла
            if check_exists and not os.path.exists(file_path):
                result['valid'] = False
                result['errors'].append(f"Файл не существует: {file_path}")
            
            # Проверка что это файл, а не директория
            if os.path.exists(file_path) and os.path.isdir(file_path):
                result['valid'] = False
                result['errors'].append(f"Указанный путь является директорией: {file_path}")
            
            # Проверка расширения файла
            if file_type and file_type in FileValidator.ALLOWED_EXTENSIONS:
                ext = os.path.splitext(file_path)[1].lower()
                allowed_exts = FileValidator.ALLOWED_EXTENSIONS[file_type]
                
                if ext not in allowed_exts:
                    result['valid'] = False
                    result['errors'].append(
                        f"Неверное расширение файла: {ext}. "
                        f"Допустимые расширения: {', '.join(allowed_exts)}"
                    )
            
            # Проверка размера файла
            if (file_type and file_type in FileValidator.MAX_FILE_SIZES and 
                os.path.exists(file_path) and os.path.isfile(file_path)):
                file_size = os.path.getsize(file_path)
                max_size = FileValidator.MAX_FILE_SIZES[file_type]
                
                if file_size > max_size:
                    result['valid'] = False
                    result['errors'].append(
                        f"Файл слишком большой: {file_size / 1024 / 1024:.2f} MB. "
                        f"Максимальный размер: {max_size / 1024 / 1024:.2f} MB"
                    )
            
            # Проверка прав доступа
            if os.path.exists(file_path):
                if not os.access(file_path, os.R_OK):
                    result['valid'] = False
                    result['errors'].append("Нет прав на чтение файла")
                
                # Для записи проверяем права на директорию
                dir_path = os.path.dirname(file_path)
                if dir_path and not os.access(dir_path, os.W_OK):
                    result['warnings'].append("Нет прав на запись в директорию")
                    
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Ошибка при валидации пути: {e}")
        
        return result
    
    @staticmethod
    def validate_directory_path(dir_path: str, check_exists: bool = True,
                               check_writable: bool = False) -> Dict[str, Any]:
        """
        Валидация пути к директории
        
        Args:
            dir_path: Путь к директории
            check_exists: Проверять существование директории
            check_writable: Проверять права на запись
            
        Returns:
            Результаты валидации
        """
        result = {
            'valid': True,
            'dir_path': dir_path,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Проверка на пустой путь
            if not dir_path or not dir_path.strip():
                result['valid'] = False
                result['errors'].append("Путь к директории не может быть пустым")
                return result
            
            # Нормализация пути
            dir_path = os.path.normpath(dir_path.strip())
            result['dir_path'] = dir_path
            
            # Проверка существования директории
            if check_exists and not os.path.exists(dir_path):
                result['valid'] = False
                result['errors'].append(f"Директория не существует: {dir_path}")
            
            # Проверка что это директория, а не файл
            if os.path.exists(dir_path) and os.path.isfile(dir_path):
                result['valid'] = False
                result['errors'].append(f"Указанный путь является файлом: {dir_path}")
            
            # Проверка прав доступа
            if os.path.exists(dir_path):
                if not os.access(dir_path, os.R_OK):
                    result['valid'] = False
                    result['errors'].append("Нет прав на чтение директории")
                
                if check_writable and not os.access(dir_path, os.W_OK):
                    result['valid'] = False
                    result['errors'].append("Нет прав на запись в директорию")
                    
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Ошибка при валидации директории: {e}")
        
        return result
    
    @staticmethod
    def validate_json_file(file_path: str, schema: Dict = None) -> Dict[str, Any]:
        """
        Валидация JSON файла
        
        Args:
            file_path: Путь к JSON файлу
            schema: JSON схема для валидации
            
        Returns:
            Результаты валидации
        """
        import json
        
        result = {
            'valid': True,
            'file_path': file_path,
            'data': None,
            'errors': [],
            'warnings': []
        }
        
        # Сначала проверяем путь
        path_result = FileValidator.validate_file_path(file_path, 'config')
        if not path_result['valid']:
            result['valid'] = False
            result['errors'].extend(path_result['errors'])
            return result
        
        try:
            # Чтение файла
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Парсинг JSON
            data = json.loads(content)
            result['data'] = data
            
            # Проверка схемы
            if schema:
                # Простая проверка структуры
                errors = FileValidator._validate_json_structure(data, schema)
                if errors:
                    result['valid'] = False
                    result['errors'].extend(errors)
            
            # Проверка на пустой JSON
            if not data:
                result['warnings'].append("JSON файл пуст")
                
        except json.JSONDecodeError as e:
            result['valid'] = False
            result['errors'].append(f"Ошибка парсинга JSON: {e}")
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Ошибка при чтении файла: {e}")
        
        return result
    
    @staticmethod
    def _validate_json_structure(data: Any, schema: Dict) -> List[str]:
        """Простая валидация структуры JSON"""
        errors = []
        
        if 'type' in schema:
            expected_type = schema['type']
            actual_type = type(data).__name__
            
            if expected_type == 'object' and not isinstance(data, dict):
                errors.append(f"Ожидался объект, получен {actual_type}")
            elif expected_type == 'array' and not isinstance(data, list):
                errors.append(f"Ожидался массив, получен {actual_type}")
            elif expected_type == 'string' and not isinstance(data, str):
                errors.append(f"Ожидалась строка, получен {actual_type}")
            elif expected_type == 'number' and not isinstance(data, (int, float)):
                errors.append(f"Ожидалось число, получен {actual_type}")
            elif expected_type == 'boolean' and not isinstance(data, bool):
                errors.append(f"Ожидалось булево значение, получен {actual_type}")
            elif expected_type == 'null' and data is not None:
                errors.append(f"Ожидалось null, получен {actual_type}")
        
        # Рекурсивная проверка полей объекта
        if isinstance(data, dict) and 'properties' in schema:
            for field_name, field_schema in schema['properties'].items():
                if field_name in data:
                    field_errors = FileValidator._validate_json_structure(
                        data[field_name], field_schema
                    )
                    for error in field_errors:
                        errors.append(f"{field_name}: {error}")
                elif 'required' in schema.get(field_name, {}) and schema[field_name]['required']:
                    errors.append(f"Обязательное поле отсутствует: {field_name}")
        
        # Проверка элементов массива
        elif isinstance(data, list) and 'items' in schema:
            for i, item in enumerate(data):
                item_errors = FileValidator._validate_json_structure(item, schema['items'])
                for error in item_errors:
                    errors.append(f"[{i}]: {error}")
        
        return errors


# Импорт os для работы с путями
import os

# Фабрика валидаторов для удобного использования
class ValidatorFactory:
    """Фабрика для создания валидаторов"""
    
    @staticmethod
    def get_vehicle_validator() -> VehicleParameterValidator:
        """Получить валидатор параметров автомобиля"""
        return VehicleParameterValidator()
    
    @staticmethod
    def get_elm_validator() -> ELMCommandValidator:
        """Получить валидатор команд ELM327"""
        return ELMCommandValidator()
    
    @staticmethod
    def get_dtc_validator() -> DTCValidator:
        """Получить валидатор DTC кодов"""
        return DTCValidator()
    
    @staticmethod
    def get_connection_validator() -> ConnectionValidator:
        """Получить валидатор подключения"""
        return ConnectionValidator()
    
    @staticmethod
    def get_adaptation_validator() -> AdaptationValidator:
        """Получить валидатор адаптации"""
        return AdaptationValidator()
    
    @staticmethod
    def get_vin_validator() -> VehicleIdentificationValidator:
        """Получить валидатор идентификации автомобиля"""
        return VehicleIdentificationValidator()
    
    @staticmethod
    def get_input_validator() -> InputValidator:
        """Получить общий валидатор ввода"""
        return InputValidator()
    
    @staticmethod
    def get_file_validator() -> FileValidator:
        """Получить валидатор файлов"""
        return FileValidator()


# Экспорт основных классов для удобного импорта
__all__ = [
    'ValidationError',
    'ValidationLevel',
    'VehicleParameterValidator',
    'ELMCommandValidator',
    'DTCValidator',
    'ConnectionValidator',
    'AdaptationValidator',
    'VehicleIdentificationValidator',
    'InputValidator',
    'FileValidator',
    'ValidatorFactory'
]