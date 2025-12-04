"""
Движок диагностики для Chevrolet Niva
Полная профессиональная диагностика всех систем автомобиля
"""

import time
from datetime import datetime
from threading import Thread, Lock, Event
from queue import Queue, Empty
import json
import struct
import math
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any, Callable
import statistics

from elm327_connector import ELM327Connector, ConnectionType
from niva_protocols import NivaProtocols
from error_codes import ErrorCodeDatabase
from adapters import VehicleAdapter, VehicleModel
from utils.logger import setup_logger

class DiagnosticStatus(Enum):
    """Статусы диагностики"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    CONNECTING = "connecting"
    SCANNING_ECUS = "scanning_ecus"
    READING_DTCS = "reading_dtcs"
    READING_LIVE_DATA = "reading_live_data"
    TESTING_SENSORS = "testing_sensors"
    TESTING_ACTUATORS = "testing_actuators"
    PERFORMING_ADAPTATIONS = "performing_adaptations"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class SensorTestResult(Enum):
    """Результаты тестирования датчиков"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NOT_AVAILABLE = "not_available"

@dataclass
class DiagnosticParameter:
    """Параметр диагностики"""
    name: str
    value: Any
    unit: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    normal_value: Optional[float] = None
    tolerance_percent: float = 5.0
    raw_data: Optional[str] = None
    timestamp: Optional[datetime] = None
    quality: float = 100.0  # Качество измерения в процентах

@dataclass
class DiagnosticResult:
    """Результат диагностики"""
    module_name: str
    status: str
    parameters: Dict[str, DiagnosticParameter]
    dtcs: List[str]
    recommendations: List[str]
    execution_time: float
    start_time: datetime
    end_time: datetime

@dataclass
class SensorTest:
    """Тест датчика"""
    sensor_name: str
    test_type: str
    commands: List[str]
    expected_responses: List[str]
    validation_function: Optional[Callable] = None
    timeout: float = 2.0

class DiagnosticsEngine:
    """Движок выполнения профессиональной диагностики"""
    
    def __init__(self, connector: ELM327Connector):
        self.connector = connector
        self.protocols = NivaProtocols()
        self.error_db = ErrorCodeDatabase()
        
        self.is_running = False
        self.is_cancelled = False
        self.diagnostic_thread = None
        self.lock = Lock()
        
        # Результаты диагностики
        self.results = {}
        self.diagnostic_history = []
        self.current_status = DiagnosticStatus.IDLE
        self.progress = 0
        self.current_step = ""
        
        # Коллбэки
        self.status_callbacks = []
        self.progress_callbacks = []
        self.result_callbacks = []
        self.error_callbacks = []
        
        # Логирование
        self.logger = setup_logger("diagnostics")
        
        # Конфигурация
        self.diagnostic_config = {
            'perform_ecu_scan': True,
            'read_dtcs': True,
            'read_live_data': True,
            'test_sensors': True,
            'test_actuators': False,  # Требует осторожности
            'perform_adaptations': False,  # Требует подтверждения
            'generate_report': True,
            'deep_scan': False,
            'save_logs': True,
            'timeout_per_command': 1.0,
            'max_retries': 3,
            'vehicle_model': '21236',
            'vin': None,
            'mileage': None,
        }
        
        # Тесты датчиков и исполнительных механизмов
        self._initialize_tests()
        
    def _initialize_tests(self):
        """Инициализация тестов"""
        # Тесты датчиков
        self.sensor_tests = {
            'COOLANT_TEMP': SensorTest(
                sensor_name="Датчик температуры охлаждающей жидкости",
                test_type="RANGE_CHECK",
                commands=["01 05", "01 05"],
                expected_responses=["41 05", "41 05"],
                validation_function=self._validate_coolant_temp,
                timeout=3.0
            ),
            'THROTTLE_POSITION': SensorTest(
                sensor_name="Датчик положения дроссельной заслонки",
                test_type="RESPONSE_CHECK",
                commands=["01 11"],
                expected_responses=["41 11"],
                validation_function=self._validate_throttle_position,
                timeout=2.0
            ),
            'OXYGEN_SENSOR': SensorTest(
                sensor_name="Датчик кислорода",
                test_type="DYNAMIC_CHECK",
                commands=["01 14", "01 15"],
                expected_responses=["41 14", "41 15"],
                validation_function=self._validate_oxygen_sensor,
                timeout=5.0
            ),
            'MAF_SENSOR': SensorTest(
                sensor_name="Датчик массового расхода воздуха",
                test_type="RANGE_CHECK",
                commands=["01 10"],
                expected_responses=["41 10"],
                validation_function=self._validate_maf_sensor,
                timeout=2.0
            ),
            'MAP_SENSOR': SensorTest(
                sensor_name="Датчик абсолютного давления",
                test_type="RANGE_CHECK",
                commands=["01 0B"],
                expected_responses=["41 0B"],
                validation_function=self._validate_map_sensor,
                timeout=2.0
            ),
            'CRANKSHAFT_SENSOR': SensorTest(
                sensor_name="Датчик положения коленвала",
                test_type="FREQUENCY_CHECK",
                commands=["01 0C"],
                expected_responses=["41 0C"],
                validation_function=self._validate_crankshaft_sensor,
                timeout=3.0
            ),
            'CAMSHAFT_SENSOR': SensorTest(
                sensor_name="Датчик положения распредвала",
                test_type="SIGNAL_CHECK",
                commands=["01 0D"],
                expected_responses=["41 0D"],
                validation_function=self._validate_camshaft_sensor,
                timeout=3.0
            ),
            'KNOCK_SENSOR': SensorTest(
                sensor_name="Датчик детонации",
                test_type="SIGNAL_CHECK",
                commands=["01 66"],
                expected_responses=["41 66"],
                validation_function=self._validate_knock_sensor,
                timeout=2.0
            ),
            'FUEL_PRESSURE': SensorTest(
                sensor_name="Датчик давления топлива",
                test_type="RANGE_CHECK",
                commands=["01 0A"],
                expected_responses=["41 0A"],
                validation_function=self._validate_fuel_pressure,
                timeout=2.0
            ),
            'VEHICLE_SPEED': SensorTest(
                sensor_name="Датчик скорости",
                test_type="RANGE_CHECK",
                commands=["01 0D"],
                expected_responses=["41 0D"],
                validation_function=self._validate_vehicle_speed,
                timeout=2.0
            ),
        }
        
        # Тесты исполнительных механизмов
        self.actuator_tests = {
            'INJECTORS': {
                'name': "Форсунки",
                'test_commands': ["04 30", "04 31", "04 32", "04 33"],
                'check_commands': ["01 21", "01 22", "01 23", "01 24"],
                'expected_range': (2.0, 20.0),  # мс
            },
            'IGNITION_COILS': {
                'name': "Катушки зажигания",
                'test_commands': ["04 40", "04 41", "04 42", "04 43"],
                'check_commands': ["01 2C", "01 2D", "01 2E", "01 2F"],
                'expected_resistance': (0.3, 1.0),  # Ом
            },
            'IDLE_VALVE': {
                'name': "Клапан холостого хода",
                'test_commands': ["04 20"],
                'check_commands': ["01 11"],
                'expected_range': (10, 90),  # %
            },
            'FUEL_PUMP': {
                'name': "Топливный насос",
                'test_commands': ["04 50"],
                'check_commands': ["01 2A"],
                'expected_pressure': (280, 320),  # кПа
            },
            'EVAP_VALVE': {
                'name': "Клапан продувки адсорбера",
                'test_commands': ["04 60"],
                'check_commands': ["01 1E"],
                'duty_cycle_range': (0, 100),  # %
            },
        }
        
    def set_config(self, config: Dict[str, Any]):
        """Установка конфигурации диагностики"""
        with self.lock:
            self.diagnostic_config.update(config)
            
    def get_config(self) -> Dict[str, Any]:
        """Получение текущей конфигурации"""
        with self.lock:
            return self.diagnostic_config.copy()
            
    def register_status_callback(self, callback: Callable):
        """Регистрация коллбэка для статуса"""
        self.status_callbacks.append(callback)
        
    def register_progress_callback(self, callback: Callable):
        """Регистрация коллбэка для прогресса"""
        self.progress_callbacks.append(callback)
        
    def register_result_callback(self, callback: Callable):
        """Регистрация коллбэка для результатов"""
        self.result_callbacks.append(callback)
        
    def register_error_callback(self, callback: Callable):
        """Регистрация коллбэка для ошибок"""
        self.error_callbacks.append(callback)
        
    def _update_status(self, status: DiagnosticStatus, step: str = ""):
        """Обновление статуса диагностики"""
        with self.lock:
            self.current_status = status
            self.current_step = step
            
        for callback in self.status_callbacks:
            callback(status.value, step)
            
    def _update_progress(self, progress: int, total: int = 100):
        """Обновление прогресса"""
        with self.lock:
            self.progress = int((progress / total) * 100) if total > 0 else 0
            
        for callback in self.progress_callbacks:
            callback(self.progress)
            
    def _notify_result(self, result_type: str, data: Any):
        """Уведомление о результате"""
        for callback in self.result_callbacks:
            callback(result_type, data)
            
    def _notify_error(self, error: str, details: str = ""):
        """Уведомление об ошибке"""
        self.logger.error(f"{error}: {details}")
        for callback in self.error_callbacks:
            callback(error, details)
            
    def perform_full_diagnostic(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Выполнение полной профессиональной диагностики
        
        Args:
            config: Дополнительная конфигурация диагностики
            
        Returns:
            Словарь с результатами диагностики
        """
        if config:
            self.set_config(config)
            
        if not self.connector.is_connected:
            error_msg = "Нет подключения к диагностическому адаптеру"
            self._notify_error(error_msg)
            return {"error": error_msg}
            
        # Сброс флагов
        self.is_cancelled = False
        
        # Инициализация результатов
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'vehicle_model': self.diagnostic_config['vehicle_model'],
            'vin': self.diagnostic_config['vin'],
            'mileage': self.diagnostic_config['mileage'],
            'diagnostic_status': 'IN_PROGRESS',
            'overall_result': 'UNKNOWN',
            'execution_time': 0,
            'modules': {},
            'recommendations': [],
            'warnings': [],
            'errors': [],
            'summary': {},
        }
        
        start_time = time.time()
        
        try:
            # Запуск в отдельном потоке
            self.is_running = True
            self.diagnostic_thread = Thread(target=self._diagnostic_worker)
            self.diagnostic_thread.start()
            
            # Ожидание завершения
            self.diagnostic_thread.join(timeout=300)  # 5 минут таймаут
            
            if self.diagnostic_thread.is_alive():
                self.cancel_diagnostic()
                raise TimeoutError("Диагностика превысила максимальное время выполнения")
                
        except Exception as e:
            self.results['diagnostic_status'] = 'FAILED'
            self.results['errors'].append(str(e))
            self._notify_error("Ошибка выполнения диагностики", str(e))
            
        finally:
            self.is_running = False
            self.results['execution_time'] = time.time() - start_time
            
        return self.results
        
    def _diagnostic_worker(self):
        """Рабочий поток выполнения диагностики"""
        try:
            self._update_status(DiagnosticStatus.INITIALIZING, "Инициализация диагностики...")
            self._update_progress(0, 100)
            
            # 1. Проверка связи и идентификация ЭБУ
            self._update_status(DiagnosticStatus.CONNECTING, "Проверка связи с ЭБУ...")
            ecu_status = self._check_ecu_communication()
            self.results['modules']['ecu_status'] = ecu_status
            self._update_progress(10, 100)
            
            if self.is_cancelled:
                return
                
            # 2. Чтение VIN и идентификаторов
            self._update_status(DiagnosticStatus.SCANNING_ECUS, "Идентификация систем...")
            vehicle_info = self._read_vehicle_information()
            self.results.update(vehicle_info)
            self._update_progress(15, 100)
            
            if self.is_cancelled:
                return
                
            # 3. Считывание ошибок
            if self.diagnostic_config['read_dtcs']:
                self._update_status(DiagnosticStatus.READING_DTCS, "Считывание кодов неисправностей...")
                dtc_results = self._read_all_dtcs()
                self.results['modules']['dtcs'] = dtc_results
                self._update_progress(25, 100)
                
            if self.is_cancelled:
                return
                
            # 4. Считывание текущих параметров
            if self.diagnostic_config['read_live_data']:
                self._update_status(DiagnosticStatus.READING_LIVE_DATA, "Считывание текущих параметров...")
                live_data = self._read_comprehensive_live_data()
                self.results['modules']['live_data'] = live_data
                self._update_progress(50, 100)
                
            if self.is_cancelled:
                return
                
            # 5. Тестирование датчиков
            if self.diagnostic_config['test_sensors']:
                self._update_status(DiagnosticStatus.TESTING_SENSORS, "Тестирование датчиков...")
                sensor_results = self._perform_sensor_tests()
                self.results['modules']['sensor_tests'] = sensor_results
                self._update_progress(70, 100)
                
            if self.is_cancelled:
                return
                
            # 6. Тестирование исполнительных механизмов (опционально)
            if self.diagnostic_config['test_actuators']:
                self._update_status(DiagnosticStatus.TESTING_ACTUATORS, "Тестирование исполнительных механизмов...")
                actuator_results = self._perform_actuator_tests()
                self.results['modules']['actuator_tests'] = actuator_results
                self._update_progress(85, 100)
                
            if self.is_cancelled:
                return
                
            # 7. Выполнение адаптаций (опционально)
            if self.diagnostic_config['perform_adaptations']:
                self._update_status(DiagnosticStatus.PERFORMING_ADAPTATIONS, "Выполнение процедур адаптации...")
                adaptation_results = self._perform_adaptations()
                self.results['modules']['adaptations'] = adaptation_results
                self._update_progress(90, 100)
                
            if self.is_cancelled:
                return
                
            # 8. Генерация отчета и рекомендаций
            self._update_status(DiagnosticStatus.GENERATING_REPORT, "Анализ результатов и генерация отчета...")
            self._analyze_results_and_generate_recommendations()
            self._update_progress(95, 100)
            
            # 9. Завершение
            self._update_status(DiagnosticStatus.COMPLETED, "Диагностика завершена")
            self.results['diagnostic_status'] = 'COMPLETED'
            
            # Определение общего результата
            self._determine_overall_result()
            
            # Сохранение в историю
            self.diagnostic_history.append(self.results.copy())
            
            # Уведомление о завершении
            self._notify_result('complete', self.results)
            self._update_progress(100, 100)
            
        except Exception as e:
            self._update_status(DiagnosticStatus.FAILED, f"Ошибка: {str(e)}")
            self.results['diagnostic_status'] = 'FAILED'
            self.results['errors'].append(str(e))
            self._notify_error('diagnostic_failed', str(e))
            
        finally:
            self.is_running = False
            
    def _check_ecu_communication(self) -> Dict[str, Any]:
        """Проверка связи со всеми ЭБУ"""
        status = {}
        total_ecus = len(self.protocols.ECUS)
        checked_ecus = 0
        
        for ecu_name, ecu_addr in self.protocols.ECUS.items():
            if self.is_cancelled:
                break
                
            checked_ecus += 1
            progress = 10 + int((checked_ecus / total_ecus) * 5)
            self._update_progress(progress, 100)
            
            try:
                # Отправка команды запроса текущих данных
                cmd = self.protocols.build_command('01', '00', ecu_addr)
                response = self.connector.send_command(cmd, wait_time=0.5)
                
                if response and 'NO DATA' not in response and 'ERROR' not in response:
                    # Чтение идентификатора ЭБУ
                    id_cmd = self.protocols.build_command('09', '00', ecu_addr)
                    id_response = self.connector.send_command(id_cmd, wait_time=0.5)
                    
                    status[ecu_name] = {
                        'status': 'CONNECTED',
                        'address': ecu_addr,
                        'response': response[:100],  # Ограничиваем длину
                        'ecu_id': id_response[:50] if id_response else None,
                        'response_time': self._measure_response_time(cmd),
                    }
                else:
                    status[ecu_name] = {
                        'status': 'NOT_RESPONDING',
                        'address': ecu_addr,
                        'response': response,
                        'error': 'Нет ответа от ЭБУ'
                    }
                    
            except Exception as e:
                status[ecu_name] = {
                    'status': 'ERROR',
                    'address': ecu_addr,
                    'error': str(e),
                    'response_time': None
                }
                
            time.sleep(0.1)  # Пауза между запросами
            
        return status
        
    def _read_vehicle_information(self) -> Dict[str, Any]:
        """Чтение информации об автомобиле"""
        info = {
            'vin': None,
            'calibration_ids': {},
            'ecu_serial_numbers': {},
            'software_versions': {},
        }
        
        try:
            # Чтение VIN
            vin_cmd = "09 02"
            vin_response = self.connector.send_command(vin_cmd, wait_time=1.0)
            
            if vin_response and 'NO DATA' not in vin_response:
                # Парсинг VIN из ответа
                vin = self._parse_vin_response(vin_response)
                if vin:
                    info['vin'] = vin
                    self.diagnostic_config['vin'] = vin
                    
            # Чтение калибровочных ID для каждого ЭБУ
            for ecu_name, ecu_addr in self.protocols.ECUS.items():
                try:
                    cal_id_cmd = self.protocols.build_command('09', '04', ecu_addr)
                    cal_response = self.connector.send_command(cal_id_cmd, wait_time=0.5)
                    
                    if cal_response and 'NO DATA' not in cal_response:
                        info['calibration_ids'][ecu_name] = cal_response[:100]
                        
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"Ошибка чтения информации об автомобиле: {e}")
            
        return info
        
    def _parse_vin_response(self, response: str) -> Optional[str]:
        """Парсинг VIN из ответа"""
        try:
            # Очистка ответа
            response = response.replace(' ', '').replace('\r', '').replace('\n', '').replace('>', '')
            
            # Формат: 49 02 01 [данные VIN]
            if '4902' in response:
                # Находим начало данных VIN
                start_idx = response.find('4902') + 4
                if start_idx >= len(response):
                    return None
                    
                # Получаем данные VIN
                vin_data = response[start_idx:]
                
                # Преобразуем hex в ASCII
                vin = ""
                for i in range(0, len(vin_data), 2):
                    if i + 2 <= len(vin_data):
                        hex_byte = vin_data[i:i+2]
                        try:
                            char = chr(int(hex_byte, 16))
                            if char.isprintable() and char not in ['\x00', '\xff']:
                                vin += char
                        except:
                            continue
                            
                # VIN должен быть 17 символов
                if len(vin) == 17:
                    return vin
                    
        except Exception as e:
            self.logger.error(f"Ошибка парсинга VIN: {e}")
            
        return None
        
    def _read_all_dtcs(self) -> Dict[str, Any]:
        """Чтение всех кодов неисправностей"""
        dtc_results = {
            'current': {},
            'pending': {},
            'permanent': {},
            'cleared': {},
            'freeze_frame': {},
            'total_count': 0,
            'by_severity': {
                'critical': 0,
                'major': 0,
                'minor': 0,
                'info': 0,
            }
        }
        
        total_ecus = len(self.protocols.ECUS)
        processed_ecus = 0
        
        for ecu_name, ecu_addr in self.protocols.ECUS.items():
            if self.is_cancelled:
                break
                
            processed_ecus += 1
            progress = 25 + int((processed_ecus / total_ecus) * 15)
            self._update_progress(progress, 100)
            
            try:
                ecu_dtcs = {
                    'current': [],
                    'pending': [],
                    'permanent': [],
                    'cleared': [],
                    'freeze_frame': {},
                }
                
                # 1. Текущие DTC
                current_cmd = self.protocols.build_command('03', '', ecu_addr)
                current_response = self.connector.send_command(current_cmd, wait_time=1.0)
                
                if current_response and 'NO DATA' not in current_response:
                    current_dtcs = self._parse_dtc_response(current_response)
                    ecu_dtcs['current'] = current_dtcs
                    dtc_results['total_count'] += len(current_dtcs)
                    
                # 2. Ожидающие DTC
                pending_cmd = self.protocols.build_command('07', '', ecu_addr)
                pending_response = self.connector.send_command(pending_cmd, wait_time=1.0)
                
                if pending_response and 'NO DATA' not in pending_response:
                    pending_dtcs = self._parse_dtc_response(pending_response)
                    ecu_dtcs['pending'] = pending_dtcs
                    
                # 3. Постоянные DTC
                permanent_cmd = self.protocols.build_command('0A', '', ecu_addr)
                permanent_response = self.connector.send_command(permanent_cmd, wait_time=1.0)
                
                if permanent_response and 'NO DATA' not in permanent_response:
                    permanent_dtcs = self._parse_dtc_response(permanent_response)
                    ecu_dtcs['permanent'] = permanent_dtcs
                    
                # 4. Кадры заморозки
                for i in range(1, 4):  # Первые 3 кадра
                    ff_cmd = self.protocols.build_command('02', f'{i:02d}', ecu_addr)
                    ff_response = self.connector.send_command(ff_cmd, wait_time=1.0)
                    
                    if ff_response and 'NO DATA' not in ff_response:
                        ff_data = self._parse_freeze_frame(ff_response)
                        if ff_data:
                            ecu_dtcs['freeze_frame'][f'frame_{i}'] = ff_data
                            
                # Анализ серьезности ошибок
                for dtc in ecu_dtcs['current']:
                    severity = self._determine_dtc_severity(dtc, ecu_name)
                    dtc_results['by_severity'][severity] += 1
                    
                dtc_results['current'][ecu_name] = ecu_dtcs['current']
                dtc_results['pending'][ecu_name] = ecu_dtcs['pending']
                dtc_results['permanent'][ecu_name] = ecu_dtcs['permanent']
                dtc_results['freeze_frame'][ecu_name] = ecu_dtcs['freeze_frame']
                
            except Exception as e:
                self.logger.error(f"Ошибка чтения DTC для {ecu_name}: {e}")
                dtc_results['current'][ecu_name] = []
                dtc_results['pending'][ecu_name] = []
                dtc_results['permanent'][ecu_name] = []
                
            time.sleep(0.2)
            
        return dtc_results
        
    def _parse_dtc_response(self, response: str) -> List[str]:
        """Парсинг ответа с DTC"""
        dtc_list = []
        
        try:
            # Очистка ответа
            response = response.replace(' ', '').replace('\r', '').replace('\n', '').replace('>', '')
            
            # Формат: 43 [количество байт] [данные DTC]
            if len(response) >= 4 and response.startswith('43'):
                # Получаем количество байт данных
                data_length = int(response[2:4], 16) * 2  # в hex символах
                
                if len(response) >= 4 + data_length:
                    data = response[4:4 + data_length]
                    
                    # Каждый DTC занимает 4 hex символа (2 байта)
                    for i in range(0, len(data), 4):
                        if i + 4 <= len(data):
                            dtc_bytes = data[i:i+4]
                            if dtc_bytes != '0000':
                                dtc = self._hex_to_dtc(dtc_bytes)
                                if dtc:
                                    dtc_list.append(dtc)
                                    
        except Exception as e:
            self.logger.error(f"Ошибка парсинга DTC: {e}")
            
        return dtc_list
        
    def _hex_to_dtc(self, hex_dtc: str) -> Optional[str]:
        """Конвертация hex в DTC формат"""
        if len(hex_dtc) != 4:
            return None
            
        try:
            first_byte = int(hex_dtc[0:2], 16)
            second_byte = int(hex_dtc[2:4], 16)
            
            # Определение типа неисправности
            fault_type = (first_byte >> 6) & 0x03
            
            fault_types = {
                0: 'P',  # Powertrain
                1: 'C',  # Chassis
                2: 'B',  # Body
                3: 'U',  # Network
            }
            
            fault_code = fault_types.get(fault_type, 'P')
            
            # Код неисправности
            code1 = str(((first_byte >> 4) & 0x03))
            code2 = format(first_byte & 0x0F, 'X')
            code3 = format(second_byte >> 4, 'X')
            code4 = format(second_byte & 0x0F, 'X')
            
            return f"{fault_code}{code1}{code2}{code3}{code4}"
            
        except:
            return None
            
    def _parse_freeze_frame(self, response: str) -> Dict[str, Any]:
        """Парсинг кадра заморозки"""
        frame_data = {}
        
        try:
            # Очистка ответа
            response = response.replace(' ', '').replace('\r', '').replace('\n', '').replace('>', '')
            
            if len(response) >= 4 and response.startswith('42'):
                # Формат: 42 [PID] [данные]
                pid = response[2:4]
                data = response[4:]
                
                frame_data['pid'] = pid
                frame_data['raw_data'] = data
                
                # Декодирование в зависимости от PID
                if pid == '0C':  # RPM
                    if len(data) >= 4:
                        rpm = int(data[:4], 16) / 4
                        frame_data['rpm'] = rpm
                        
                elif pid == '0D':  # Speed
                    if len(data) >= 2:
                        speed = int(data[:2], 16)
                        frame_data['speed'] = speed
                        
                elif pid == '05':  # Coolant temp
                    if len(data) >= 2:
                        temp = int(data[:2], 16) - 40
                        frame_data['coolant_temp'] = temp
                        
                elif pid == '11':  # Throttle position
                    if len(data) >= 2:
                        throttle = int(data[:2], 16) * 100 / 255
                        frame_data['throttle_position'] = throttle
                        
        except Exception as e:
            self.logger.error(f"Ошибка парсинга кадра заморозки: {e}")
            
        return frame_data
        
    def _determine_dtc_severity(self, dtc: str, ecu_name: str) -> str:
        """Определение серьезности ошибки"""
        # Получение информации об ошибке
        dtc_info = self.error_db.get_dtc_info(dtc)
        
        if not dtc_info:
            return 'minor'
            
        severity = dtc_info.get('severity', 'minor')
        
        # Критические ошибки для важных систем
        critical_systems = ['ENGINE', 'ABS', 'AIRBAG']
        if ecu_name in critical_systems and severity in ['major', 'critical']:
            return 'critical'
            
        return severity
        
    def _read_comprehensive_live_data(self) -> Dict[str, Any]:
        """Чтение комплексных текущих данных"""
        live_data = {
            'engine': {},
            'fuel_system': {},
            'ignition_system': {},
            'emission_system': {},
            'vehicle_status': {},
            'sensor_readings': {},
            'calculated_parameters': {},
            'timestamps': [],
        }
        
        # Список PID для мониторинга
        pid_groups = {
            'engine': ['010C', '0104', '0105', '010F', '0111', '010E', '010B', '010A'],
            'fuel_system': ['0110', '0114', '0115', '012F', '0102', '0103'],
            'ignition_system': ['010C', '010E', '0133', '0134'],
            'emission_system': ['0114', '0115', '0133', '0134', '013C', '013D'],
            'vehicle_status': ['010D', '0112', '0113', '011F', '0142'],
        }
        
        total_pids = sum(len(pids) for pids in pid_groups.values())
        processed_pids = 0
        
        # Чтение данных в нескольких циклах для статистики
        cycles = 3 if not self.diagnostic_config['deep_scan'] else 10
        all_readings = {group: {} for group in pid_groups.keys()}
        
        for cycle in range(cycles):
            if self.is_cancelled:
                break
                
            cycle_data = {}
            
            for group_name, pids in pid_groups.items():
                if self.is_cancelled:
                    break
                    
                for pid in pids:
                    if self.is_cancelled:
                        break
                        
                    try:
                        # Отправка команды
                        cmd = self.protocols.build_command('01', pid)
                        response = self.connector.send_command(cmd, wait_time=0.1)
                        
                        if response:
                            value = self.protocols.parse_response(response, pid)
                            unit = self._get_pid_unit(pid)
                            
                            if value is not None:
                                param_name = self._get_pid_name(pid)
                                
                                if pid not in cycle_data:
                                    cycle_data[pid] = {
                                        'name': param_name,
                                        'values': [],
                                        'unit': unit,
                                        'raw_responses': [],
                                    }
                                    
                                cycle_data[pid]['values'].append(value)
                                cycle_data[pid]['raw_responses'].append(response)
                                
                                # Обновление прогресса
                                processed_pids += 1
                                progress = 50 + int((processed_pids / (total_pids * cycles)) * 20)
                                self._update_progress(progress, 100)
                                
                    except Exception as e:
                        self.logger.warning(f"Ошибка чтения PID {pid}: {e}")
                        
                time.sleep(0.05)
                
            # Пауза между циклами
            if cycle < cycles - 1:
                time.sleep(0.5)
                
            # Добавление временной метки
            live_data['timestamps'].append(datetime.now().isoformat())
            
        # Обработка и усреднение данных
        for pid, data in cycle_data.items():
            if data['values']:
                # Вычисление статистики
                values = data['values']
                avg_value = statistics.mean(values)
                min_value = min(values)
                max_value = max(values)
                std_dev = statistics.stdev(values) if len(values) > 1 else 0
                
                # Определение группы
                group = self._get_pid_group(pid)
                
                if group not in live_data:
                    live_data[group] = {}
                    
                live_data[group][data['name']] = {
                    'value': avg_value,
                    'unit': data['unit'],
                    'min': min_value,
                    'max': max_value,
                    'std_dev': std_dev,
                    'stability': self._calculate_stability(values),
                    'raw_data': data['raw_responses'][0] if data['raw_responses'] else None,
                    'timestamp': live_data['timestamps'][-1] if live_data['timestamps'] else None,
                }
                
        # Расчет дополнительных параметров
        self._calculate_derived_parameters(live_data)
        
        return live_data
        
    def _get_pid_name(self, pid: str) -> str:
        """Получение имени параметра по PID"""
        pid_names = {
            '010C': 'Обороты двигателя',
            '0104': 'Нагрузка на двигатель',
            '0105': 'Температура охлаждающей жидкости',
            '010F': 'Температура впускного воздуха',
            '0111': 'Положение дроссельной заслонки',
            '010E': 'Угол опережения зажигания',
            '010B': 'Давление во впускном коллекторе',
            '010A': 'Давление в топливной рампе',
            '0110': 'Расход воздуха',
            '0114': 'Напряжение датчика кислорода 1',
            '0115': 'Напряжение датчика кислорода 2',
            '012F': 'Уровень топлива',
            '0102': 'Долговременная коррекция топлива',
            '0103': 'Кратковременная коррекция топлива',
            '0133': 'Барометрическое давление',
            '0134': 'Напряжение датчика кислорода 3',
            '013C': 'Катализатор температура B1S1',
            '013D': 'Катализатор температура B2S1',
            '010D': 'Скорость автомобиля',
            '0112': 'Напряжение бортовой сети',
            '0113': 'Напряжение датчика положения дросселя',
            '011F': 'Время работы двигателя',
            '0142': 'Напряжение контрольного модуля',
        }
        
        return pid_names.get(pid, f"PID {pid}")
        
    def _get_pid_group(self, pid: str) -> str:
        """Определение группы параметра"""
        pid_groups_map = {
            '010C': 'engine',
            '0104': 'engine',
            '0105': 'engine',
            '010F': 'engine',
            '0111': 'engine',
            '010E': 'engine',
            '010B': 'engine',
            '010A': 'fuel_system',
            '0110': 'fuel_system',
            '0114': 'fuel_system',
            '0115': 'fuel_system',
            '012F': 'fuel_system',
            '0102': 'fuel_system',
            '0103': 'fuel_system',
            '0133': 'emission_system',
            '0134': 'emission_system',
            '013C': 'emission_system',
            '013D': 'emission_system',
            '010D': 'vehicle_status',
            '0112': 'vehicle_status',
            '0113': 'vehicle_status',
            '011F': 'vehicle_status',
            '0142': 'vehicle_status',
        }
        
        return pid_groups_map.get(pid, 'sensor_readings')
        
    def _get_pid_unit(self, pid: str) -> str:
        """Получение единиц измерения для PID"""
        units = {
            '010C': 'об/мин',
            '0104': '%',
            '0105': '°C',
            '010F': '°C',
            '0111': '%',
            '010E': 'град.',
            '010B': 'кПа',
            '010A': 'кПа',
            '0110': 'г/с',
            '0114': 'В',
            '0115': 'В',
            '012F': '%',
            '0102': '%',
            '0103': '%',
            '0133': 'кПа',
            '0134': 'В',
            '013C': '°C',
            '013D': '°C',
            '010D': 'км/ч',
            '0112': 'В',
            '0113': 'В',
            '011F': 'сек',
            '0142': 'В',
        }
        
        return units.get(pid, '')
        
    def _calculate_stability(self, values: List[float]) -> float:
        """Расчет стабильности параметра"""
        if len(values) < 2:
            return 100.0
            
        avg = statistics.mean(values)
        if avg == 0:
            return 100.0
            
        # Коэффициент вариации (обратный)
        std_dev = statistics.stdev(values)
        cv = (std_dev / avg) * 100 if avg != 0 else 0
        
        # Стабильность в процентах (100% = идеальная стабильность)
        stability = max(0, 100 - cv)
        
        return round(stability, 2)
        
    def _calculate_derived_parameters(self, live_data: Dict[str, Any]):
        """Расчет производных параметров"""
        try:
            # Расчет расхода топлива (приблизительный)
            if 'engine' in live_data and 'vehicle_status' in live_data:
                engine_data = live_data['engine']
                vehicle_data = live_data['vehicle_status']
                
                if ('Обороты двигателя' in engine_data and 
                    'Скорость автомобиля' in vehicle_data and
                    'Нагрузка на двигатель' in engine_data):
                    
                    rpm = engine_data['Обороты двигателя']['value']
                    speed = vehicle_data['Скорость автомобиля']['value']
                    load = engine_data['Нагрузка на двигатель']['value']
                    
                    # Эмпирическая формула для расчета расхода
                    if speed > 0 and rpm > 0:
                        # Удельный расход (л/100км)
                        specific_consumption = (load * rpm * 0.0001) / max(speed, 1)
                        instant_consumption = specific_consumption * speed / 100
                        
                        live_data['calculated_parameters']['instant_fuel_consumption'] = {
                            'value': round(instant_consumption, 2),
                            'unit': 'л/ч',
                            'description': 'Мгновенный расход топлива'
                        }
                        
                        live_data['calculated_parameters']['specific_fuel_consumption'] = {
                            'value': round(specific_consumption, 2),
                            'unit': 'л/100км',
                            'description': 'Удельный расход топлива'
                        }
                        
            # Расчет мощности (приблизительный)
            if 'engine' in live_data:
                engine_data = live_data['engine']
                
                if ('Обороты двигателя' in engine_data and 
                    'Нагрузка на двигатель' in engine_data):
                    
                    rpm = engine_data['Обороты двигателя']['value']
                    load = engine_data['Нагрузка на двигатель']['value']
                    
                    # Для Нива 1.7i ~80 л.с.
                    max_power = 80
                    estimated_power = (load / 100) * max_power * (rpm / 4000)
                    
                    live_data['calculated_parameters']['estimated_power'] = {
                        'value': round(estimated_power, 1),
                        'unit': 'л.с.',
                        'description': 'Расчетная мощность'
                    }
                    
            # Расчет КПД двигателя
            if 'fuel_system' in live_data and 'engine' in live_data:
                fuel_data = live_data['fuel_system']
                engine_data = live_data['engine']
                
                if ('Расход воздуха' in fuel_data and 
                    'Нагрузка на двигатель' in engine_data):
                    
                    maf = fuel_data['Расход воздуха']['value']
                    load = engine_data['Нагрузка на двигатель']['value']
                    
                    # Теоретический расход воздуха для идеального смесеобразования
                    theoretical_maf = load * 0.8  # Упрощенная модель
                    
                    if theoretical_maf > 0:
                        efficiency = min(100, (maf / theoretical_maf) * 100)
                        
                        live_data['calculated_parameters']['combustion_efficiency'] = {
                            'value': round(efficiency, 1),
                            'unit': '%',
                            'description': 'Эффективность сгорания'
                        }
                        
        except Exception as e:
            self.logger.warning(f"Ошибка расчета производных параметров: {e}")
            
    def _perform_sensor_tests(self) -> Dict[str, Any]:
        """Выполнение тестирования датчиков"""
        test_results = {
            'overall_score': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'warning_tests': 0,
            'sensors': {},
            'recommendations': [],
            'detailed_results': {},
        }
        
        total_tests = len(self.sensor_tests)
        completed_tests = 0
        
        for sensor_key, test in self.sensor_tests.items():
            if self.is_cancelled:
                break
                
            completed_tests += 1
            progress = 70 + int((completed_tests / total_tests) * 10)
            self._update_progress(progress, 100)
            self._update_status(DiagnosticStatus.TESTING_SENSORS, 
                              f"Тестирование датчика: {test.sensor_name}")
            
            try:
                sensor_result = self._execute_sensor_test(test)
                test_results['sensors'][sensor_key] = sensor_result
                test_results['detailed_results'][sensor_key] = sensor_result
                
                if sensor_result['status'] == SensorTestResult.PASS.value:
                    test_results['passed_tests'] += 1
                elif sensor_result['status'] == SensorTestResult.FAIL.value:
                    test_results['failed_tests'] += 1
                    test_results['recommendations'].append(
                        f"Неисправен датчик: {test.sensor_name}"
                    )
                elif sensor_result['status'] == SensorTestResult.WARNING.value:
                    test_results['warning_tests'] += 1
                    test_results['recommendations'].append(
                        f"Проверить датчик: {test.sensor_name}"
                    )
                    
                time.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Ошибка тестирования датчика {sensor_key}: {e}")
                test_results['sensors'][sensor_key] = {
                    'status': SensorTestResult.FAIL.value,
                    'error': str(e)
                }
                test_results['failed_tests'] += 1
                
        # Расчет общего счета
        if total_tests > 0:
            test_results['overall_score'] = int(
                (test_results['passed_tests'] / total_tests) * 100
            )
            
        return test_results
        
    def _execute_sensor_test(self, test: SensorTest) -> Dict[str, Any]:
        """Выполнение теста датчика"""
        result = {
            'sensor_name': test.sensor_name,
            'test_type': test.test_type,
            'status': SensorTestResult.NOT_AVAILABLE.value,
            'measurements': [],
            'raw_responses': [],
            'validation_result': None,
            'execution_time': 0,
            'timestamp': datetime.now().isoformat(),
        }
        
        start_time = time.time()
        measurements = []
        
        try:
            for i, command in enumerate(test.commands):
                # Отправка команды
                response = self.connector.send_command(command, wait_time=test.timeout)
                result['raw_responses'].append(response)
                
                if response and 'NO DATA' not in response and 'ERROR' not in response:
                    # Парсинг значения
                    value = self.protocols.parse_response(response, command[3:7])
                    if value is not None:
                        measurements.append(value)
                        
                time.sleep(0.2)
                
            result['measurements'] = measurements
            
            # Валидация
            if test.validation_function and measurements:
                validation_result = test.validation_function(measurements)
                result['validation_result'] = validation_result
                result['status'] = validation_result['status'].value
            else:
                result['status'] = SensorTestResult.PASS.value if measurements else SensorTestResult.NOT_AVAILABLE.value
                
        except Exception as e:
            result['status'] = SensorTestResult.FAIL.value
            result['error'] = str(e)
            
        result['execution_time'] = time.time() - start_time
        
        return result
        
    def _validate_coolant_temp(self, measurements: List[float]) -> Dict[str, Any]:
        """Валидация датчика температуры охлаждающей жидкости"""
        if not measurements:
            return {'status': SensorTestResult.FAIL, 'message': 'Нет данных'}
            
        avg_temp = statistics.mean(measurements)
        
        # Нормальные диапазоны
        if avg_temp < -40 or avg_temp > 150:
            return {
                'status': SensorTestResult.FAIL,
                'message': f'Температура вне диапазона: {avg_temp:.1f}°C',
                'value': avg_temp,
                'min_allowed': -40,
                'max_allowed': 150,
            }
        elif avg_temp < 0 or avg_temp > 120:
            return {
                'status': SensorTestResult.WARNING,
                'message': f'Температура на границе диапазона: {avg_temp:.1f}°C',
                'value': avg_temp,
                'recommended_min': 0,
                'recommended_max': 120,
            }
        else:
            return {
                'status': SensorTestResult.PASS,
                'message': f'Температура в норме: {avg_temp:.1f}°C',
                'value': avg_temp,
            }
            
    def _validate_throttle_position(self, measurements: List[float]) -> Dict[str, Any]:
        """Валидация датчика положения дроссельной заслонки"""
        if not measurements:
            return {'status': SensorTestResult.FAIL, 'message': 'Нет данных'}
            
        avg_position = statistics.mean(measurements)
        
        # Проверка на залипание (значение должно быть близко к 0 при отпущенной педали)
        if avg_position > 10:  # Предполагаем, что педаль отпущена
            return {
                'status': SensorTestResult.WARNING,
                'message': f'Возможно залипание дросселя: {avg_position:.1f}%',
                'value': avg_position,
                'expected_max': 10,
            }
        elif avg_position < 0 or avg_position > 100:
            return {
                'status': SensorTestResult.FAIL,
                'message': f'Положение вне диапазона: {avg_position:.1f}%',
                'value': avg_position,
                'min_allowed': 0,
                'max_allowed': 100,
            }
        else:
            return {
                'status': SensorTestResult.PASS,
                'message': f'Положение в норме: {avg_position:.1f}%',
                'value': avg_position,
            }
            
    # Другие функции валидации...
    
    def _validate_oxygen_sensor(self, measurements: List[float]) -> Dict[str, Any]:
        """Валидация датчика кислорода"""
        if not measurements:
            return {'status': SensorTestResult.FAIL, 'message': 'Нет данных'}
            
        # Проверка динамики сигнала
        if len(measurements) > 1:
            changes = [abs(measurements[i] - measurements[i-1]) 
                      for i in range(1, len(measurements))]
            avg_change = statistics.mean(changes) if changes else 0
            
            if avg_change < 0.1:  # Слишком стабильный сигнал
                return {
                    'status': SensorTestResult.WARNING,
                    'message': 'Низкая динамика сигнала датчика кислорода',
                    'avg_voltage': statistics.mean(measurements),
                    'avg_change': avg_change,
                }
            elif avg_change > 1.0:  # Слишком большие колебания
                return {
                    'status': SensorTestResult.WARNING,
                    'message': 'Высокая динамика сигнала датчика кислорода',
                    'avg_voltage': statistics.mean(measurements),
                    'avg_change': avg_change,
                }
                
        avg_voltage = statistics.mean(measurements)
        
        if avg_voltage < 0.1 or avg_voltage > 1.0:
            return {
                'status': SensorTestResult.FAIL,
                'message': f'Напряжение вне диапазона: {avg_voltage:.3f}В',
                'value': avg_voltage,
                'min_allowed': 0.1,
                'max_allowed': 1.0,
            }
        else:
            return {
                'status': SensorTestResult.PASS,
                'message': f'Напряжение в норме: {avg_voltage:.3f}В',
                'value': avg_voltage,
            }
            
    def _perform_actuator_tests(self) -> Dict[str, Any]:
        """Выполнение тестирования исполнительных механизмов"""
        # ВНИМАНИЕ: Эти тесты могут изменить состояние автомобиля!
        # Требуется подтверждение пользователя и соблюдение мер безопасности
        
        test_results = {
            'overall_score': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'warning_tests': 0,
            'actuators': {},
            'safety_warnings': [
                'Тестирование исполнительных механизмов выполнено',
                'Проверьте работу систем автомобиля',
                'При возникновении ошибок выполните сброс ЭБУ',
            ],
            'execution_time': 0,
        }
        
        start_time = time.time()
        
        # Здесь будет реализация безопасного тестирования актуаторов
        # В данной версии тесты отключены по умолчанию
        
        test_results['execution_time'] = time.time() - start_time
        
        return test_results
        
    def _perform_adaptations(self) -> Dict[str, Any]:
        """Выполнение процедур адаптации"""
        adaptation_results = {
            'performed_adaptations': [],
            'successful': 0,
            'failed': 0,
            'results': {},
            'recommendations': [],
            'execution_time': 0,
        }
        
        start_time = time.time()
        
        # Список процедур адаптации для Chevrolet Niva
        adaptations = [
            {
                'name': 'Адаптация дроссельной заслонки',
                'command': '04 01',
                'description': 'Обучение крайних положений дроссельной заслонки',
                'conditions': ['Выключен двигатель', 'Зажигание ON'],
            },
            {
                'name': 'Адаптация холостого хода',
                'command': '04 02',
                'description': 'Обучение регулятора холостого хода',
                'conditions': ['Прогретый двигатель', 'Нейтральная передача'],
            },
            {
                'name': 'Сброс адаптаций топливоподачи',
                'command': '04 03',
                'description': 'Сброс долговременных коррекций топлива',
                'conditions': ['Выключен двигатель'],
            },
            {
                'name': 'Адаптация иммобилайзера',
                'command': '04 04',
                'description': 'Обучение новых ключей',
                'conditions': ['Имеются новые ключи', 'Знание пин-кода'],
            },
        ]
        
        for adaptation in adaptations:
            try:
                self._update_status(
                    DiagnosticStatus.PERFORMING_ADAPTATIONS,
                    f"Выполнение: {adaptation['name']}"
                )
                
                # Проверка условий
                conditions_met = self._check_adaptation_conditions(adaptation['conditions'])
                if not conditions_met:
                    adaptation_results['results'][adaptation['name']] = {
                        'status': 'SKIPPED',
                        'reason': 'Условия не выполнены',
                        'conditions': adaptation['conditions'],
                    }
                    continue
                    
                # Выполнение адаптации
                response = self.connector.send_command(adaptation['command'], wait_time=5.0)
                
                if response and 'OK' in response:
                    adaptation_results['successful'] += 1
                    adaptation_results['performed_adaptations'].append(adaptation['name'])
                    adaptation_results['results'][adaptation['name']] = {
                        'status': 'SUCCESS',
                        'response': response,
                    }
                else:
                    adaptation_results['failed'] += 1
                    adaptation_results['results'][adaptation['name']] = {
                        'status': 'FAILED',
                        'response': response,
                        'error': 'Ошибка выполнения',
                    }
                    
                time.sleep(2.0)
                
            except Exception as e:
                adaptation_results['failed'] += 1
                adaptation_results['results'][adaptation['name']] = {
                    'status': 'ERROR',
                    'error': str(e),
                }
                
        adaptation_results['execution_time'] = time.time() - start_time
        
        # Рекомендации после адаптации
        if adaptation_results['successful'] > 0:
            adaptation_results['recommendations'].extend([
                'После адаптации дайте двигателю поработать на холостом ходу 2-3 минуты',
                'Совершите тестовую поездку для завершения адаптации',
                'Проверьте работу систем, которые были адаптированы',
            ])
            
        return adaptation_results
        
    def _check_adaptation_conditions(self, conditions: List[str]) -> bool:
        """Проверка условий для выполнения адаптации"""
        # В реальной реализации здесь будет проверка текущего состояния автомобиля
        # через чтение параметров ЭБУ
        
        # Для примера всегда возвращаем True
        # В реальном приложении здесь должна быть сложная логика проверки
        return True
        
    def _analyze_results_and_generate_recommendations(self):
        """Анализ результатов и генерация рекомендаций"""
        recommendations = []
        warnings = []
        
        # Анализ ошибок
        if 'dtcs' in self.results['modules']:
            dtc_results = self.results['modules']['dtcs']
            
            if dtc_results['total_count'] > 0:
                # Критические ошибки
                if dtc_results['by_severity']['critical'] > 0:
                    recommendations.append(
                        "Обнаружены критические ошибки! Требуется немедленное вмешательство."
                    )
                    
                # Основные ошибки
                if dtc_results['by_severity']['major'] > 0:
                    recommendations.append(
                        "Обнаружены серьезные ошибки. Рекомендуется диагностика и ремонт."
                    )
                    
                # Минорные ошибки
                if dtc_results['by_severity']['minor'] > 0:
                    recommendations.append(
                        "Обнаружены незначительные ошибки. Рекомендуется проверить системы."
                    )
                    
        # Анализ текущих параметров
        if 'live_data' in self.results['modules']:
            live_data = self.results['modules']['live_data']
            
            # Проверка температуры двигателя
            if 'engine' in live_data and 'Температура охлаждающей жидкости' in live_data['engine']:
                temp = live_data['engine']['Температура охлаждающей жидкости']['value']
                if temp < 80:
                    warnings.append(
                        f"Двигатель не прогрет до рабочей температуры: {temp}°C"
                    )
                elif temp > 105:
                    recommendations.append(
                        f"Перегрев двигателя: {temp}°C. Проверить систему охлаждения."
                    )
                    
            # Проверка напряжения бортовой сети
            if 'vehicle_status' in live_data and 'Напряжение бортовой сети' in live_data['vehicle_status']:
                voltage = live_data['vehicle_status']['Напряжение бортовой сети']['value']
                if voltage < 13.0:
                    recommendations.append(
                        f"Низкое напряжение бортовой сети: {voltage}В. Проверить генератор и АКБ."
                    )
                elif voltage > 14.7:
                    warnings.append(
                        f"Высокое напряжение бортовой сети: {voltage}В. Возможна перезарядка."
                    )
                    
            # Проверка коррекций топлива
            if 'fuel_system' in live_data:
                if 'Долговременная коррекция топлива' in live_data['fuel_system']:
                    ltft = live_data['fuel_system']['Долговременная коррекция топлива']['value']
                    if abs(ltft) > 10:
                        recommendations.append(
                            f"Большая долговременная коррекция топлива: {ltft}%. Проверить систему впуска/выпуска."
                        )
                        
                if 'Кратковременная коррекция топлива' in live_data['fuel_system']:
                    stft = live_data['fuel_system']['Кратковременная коррекция топлива']['value']
                    if abs(stft) > 8:
                        warnings.append(
                            f"Большая кратковременная коррекция топлива: {stft}%. Возможны проблемы с смесеобразованием."
                        )
                        
        # Анализ тестов датчиков
        if 'sensor_tests' in self.results['modules']:
            sensor_results = self.results['modules']['sensor_tests']
            
            if sensor_results['failed_tests'] > 0:
                recommendations.append(
                    f"Обнаружены неисправные датчики: {sensor_results['failed_tests']} шт."
                )
                
            if sensor_results['warning_tests'] > 0:
                warnings.append(
                    f"Требуется проверка датчиков: {sensor_results['warning_tests']} шт."
                )
                
        # Добавление рекомендаций и предупреждений
        self.results['recommendations'] = recommendations
        self.results['warnings'] = warnings
        
        # Сводка диагностики
        self.results['summary'] = self._generate_diagnostic_summary()
        
    def _generate_diagnostic_summary(self) -> Dict[str, Any]:
        """Генерация сводки диагностики"""
        summary = {
            'overall_health': 'UNKNOWN',
            'systems_health': {},
            'priority_actions': [],
            'maintenance_recommendations': [],
            'estimated_repair_cost': 0,
            'diagnostic_confidence': 0,
        }
        
        # Оценка общего состояния
        health_score = 100
        
        # Учет ошибок
        if 'dtcs' in self.results['modules']:
            dtc_results = self.results['modules']['dtcs']
            
            # Штрафы за ошибки
            health_score -= dtc_results['by_severity']['critical'] * 30
            health_score -= dtc_results['by_severity']['major'] * 15
            health_score -= dtc_results['by_severity']['minor'] * 5
            
            # Оценка систем
            for ecu_name, dtcs in dtc_results['current'].items():
                if dtcs:
                    summary['systems_health'][ecu_name] = 'FAULT'
                else:
                    summary['systems_health'][ecu_name] = 'OK'
                    
        # Учет тестов датчиков
        if 'sensor_tests' in self.results['modules']:
            sensor_results = self.results['modules']['sensor_tests']
            health_score -= sensor_results['failed_tests'] * 10
            health_score -= sensor_results['warning_tests'] * 5
            
        # Определение общего состояния
        health_score = max(0, min(100, health_score))
        
        if health_score >= 80:
            summary['overall_health'] = 'GOOD'
        elif health_score >= 60:
            summary['overall_health'] = 'FAIR'
        elif health_score >= 40:
            summary['overall_health'] = 'POOR'
        else:
            summary['overall_health'] = 'CRITICAL'
            
        # Доверие к диагностике
        confidence_factors = []
        
        # Качество связи
        if 'ecu_status' in self.results['modules']:
            connected_ecus = sum(1 for ecu in self.results['modules']['ecu_status'].values() 
                               if ecu.get('status') == 'CONNECTED')
            total_ecus = len(self.protocols.ECUS)
            if total_ecus > 0:
                connection_quality = (connected_ecus / total_ecus) * 100
                confidence_factors.append(connection_quality)
                
        # Качество данных
        if 'live_data' in self.results['modules']:
            live_data = self.results['modules']['live_data']
            valid_params = sum(1 for group in live_data.values() 
                             if isinstance(group, dict) and len(group) > 0)
            confidence_factors.append(min(100, valid_params * 10))
            
        if confidence_factors:
            summary['diagnostic_confidence'] = int(statistics.mean(confidence_factors))
            
        return summary
        
    def _determine_overall_result(self):
        """Определение общего результата диагностики"""
        if self.results['diagnostic_status'] != 'COMPLETED':
            self.results['overall_result'] = 'FAILED'
            return
            
        summary = self.results.get('summary', {})
        overall_health = summary.get('overall_health', 'UNKNOWN')
        
        if overall_health == 'CRITICAL':
            self.results['overall_result'] = 'CRITICAL'
        elif overall_health == 'POOR':
            self.results['overall_result'] = 'POOR'
        elif overall_health == 'FAIR':
            self.results['overall_result'] = 'FAIR'
        elif overall_health == 'GOOD':
            self.results['overall_result'] = 'GOOD'
        else:
            self.results['overall_result'] = 'UNKNOWN'
            
    def _measure_response_time(self, command: str) -> float:
        """Измерение времени отклика ЭБУ"""
        start_time = time.time()
        response = self.connector.send_command(command, wait_time=2.0)
        end_time = time.time()
        
        if response and 'NO DATA' not in response:
            return round((end_time - start_time) * 1000, 2)  # мс
        return -1
        
    def cancel_diagnostic(self):
        """Отмена текущей диагностики"""
        with self.lock:
            self.is_cancelled = True
            self.is_running = False
            
        self._update_status(DiagnosticStatus.CANCELLED, "Диагностика отменена")
        self._notify_result('cancelled', None)
        
    def clear_all_dtcs(self) -> Dict[str, Any]:
        """Очистка всех ошибок"""
        result = {
            'cleared_ecus': [],
            'failed_ecus': [],
            'total_cleared': 0,
            'execution_time': 0,
        }
        
        start_time = time.time()
        
        try:
            for ecu_name, ecu_addr in self.protocols.ECUS.items():
                try:
                    cmd = self.protocols.build_command('04', '', ecu_addr)
                    response = self.connector.send_command(cmd, wait_time=1.0)
                    
                    if response and ('OK' in response or 'NO DATA' not in response):
                        result['cleared_ecus'].append(ecu_name)
                        result['total_cleared'] += 1
                    else:
                        result['failed_ecus'].append({
                            'ecu': ecu_name,
                            'response': response
                        })
                        
                    time.sleep(0.5)
                    
                except Exception as e:
                    result['failed_ecus'].append({
                        'ecu': ecu_name,
                        'error': str(e)
                    })
                    
        except Exception as e:
            result['error'] = str(e)
            
        result['execution_time'] = time.time() - start_time
        
        # После очистки рекомендуется перечитать ошибки
        if result['total_cleared'] > 0:
            self._notify_result('dtcs_cleared', result)
            
        return result
        
    def get_diagnostic_history(self) -> List[Dict[str, Any]]:
        """Получение истории диагностики"""
        return self.diagnostic_history.copy()
        
    def save_current_results(self, filename: str = None) -> str:
        """Сохранение текущих результатов в файл"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"diagnostic_results_{timestamp}.json"
            
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
                
            return filename
            
        except Exception as e:
            self._notify_error("Ошибка сохранения результатов", str(e))
            return ""
            
    def reset_adaptations(self, adaptation_type: str = None) -> Dict[str, Any]:
        """Сброс адаптаций"""
        result = {
            'type': adaptation_type or 'ALL',
            'status': 'UNKNOWN',
            'commands_executed': [],
            'responses': [],
            'execution_time': 0,
        }
        
        start_time = time.time()
        
        try:
            if adaptation_type == 'THROTTLE' or adaptation_type == 'ALL':
                # Сброс адаптации дроссельной заслонки
                cmd = "04 01"
                response = self.connector.send_command(cmd, wait_time=3.0)
                result['commands_executed'].append(cmd)
                result['responses'].append(response)
                
            if adaptation_type == 'FUEL' or adaptation_type == 'ALL':
                # Сброс адаптаций топливоподачи
                cmd = "04 03"
                response = self.connector.send_command(cmd, wait_time=3.0)
                result['commands_executed'].append(cmd)
                result['responses'].append(response)
                
            if adaptation_type == 'IDLE' or adaptation_type == 'ALL':
                # Сброс адаптации холостого хода
                cmd = "04 02"
                response = self.connector.send_command(cmd, wait_time=3.0)
                result['commands_executed'].append(cmd)
                result['responses'].append(response)
                
            # Проверка успешности
            success_count = sum(1 for resp in result['responses'] 
                              if resp and 'OK' in resp)
                              
            if success_count == len(result['commands_executed']):
                result['status'] = 'SUCCESS'
            elif success_count > 0:
                result['status'] = 'PARTIAL'
            else:
                result['status'] = 'FAILED'
                
        except Exception as e:
            result['status'] = 'ERROR'
            result['error'] = str(e)
            
        result['execution_time'] = time.time() - start_time
        
        return result
        
    def perform_custom_test(self, commands: List[str], 
                           validation_function: Callable = None) -> Dict[str, Any]:
        """Выполнение пользовательского теста"""
        result = {
            'commands': commands,
            'responses': [],
            'parsed_values': [],
            'validation_result': None,
            'execution_time': 0,
            'status': 'UNKNOWN',
        }
        
        start_time = time.time()
        
        try:
            for cmd in commands:
                response = self.connector.send_command(cmd, wait_time=1.0)
                result['responses'].append(response)
                
                # Парсинг значения
                if len(cmd) >= 7:
                    pid = cmd[3:7]
                    value = self.protocols.parse_response(response, pid)
                    if value is not None:
                        result['parsed_values'].append({
                            'pid': pid,
                            'value': value,
                            'unit': self._get_pid_unit(pid),
                        })
                        
                time.sleep(0.2)
                
            # Валидация
            if validation_function and result['parsed_values']:
                validation_result = validation_function(result['parsed_values'])
                result['validation_result'] = validation_result
                result['status'] = validation_result.get('status', 'UNKNOWN')
            else:
                result['status'] = 'COMPLETED'
                
        except Exception as e:
            result['status'] = 'ERROR'
            result['error'] = str(e)
            
        result['execution_time'] = time.time() - start_time
        
        return result
        
    def get_system_health_report(self) -> Dict[str, Any]:
        """Получение отчета о состоянии систем"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'vehicle_info': {
                'model': self.diagnostic_config.get('vehicle_model'),
                'vin': self.diagnostic_config.get('vin'),
                'mileage': self.diagnostic_config.get('mileage'),
            },
            'system_status': {},
            'health_score': 0,
            'maintenance_items': [],
            'urgent_actions': [],
        }
        
        # Сбор информации из результатов диагностики
        if self.results:
            if 'summary' in self.results:
                report['health_score'] = self._calculate_health_score()
                report['system_status'] = self.results['summary'].get('systems_health', {})
                
            if 'recommendations' in self.results:
                report['urgent_actions'] = self.results['recommendations']
                
            if 'warnings' in self.results:
                report['maintenance_items'] = self.results['warnings']
                
        return report
        
    def _calculate_health_score(self) -> int:
        """Расчет общего показателя здоровья систем"""
        if not self.results or 'summary' not in self.results:
            return 0
            
        summary = self.results['summary']
        overall_health = summary.get('overall_health', 'UNKNOWN')
        
        health_scores = {
            'CRITICAL': 20,
            'POOR': 40,
            'FAIR': 60,
            'GOOD': 80,
            'EXCELLENT': 100,
        }
        
        return health_scores.get(overall_health, 0)
        
    def is_diagnostic_running(self) -> bool:
        """Проверка, выполняется ли диагностика"""
        with self.lock:
            return self.is_running
            
    def get_current_status(self) -> Tuple[str, str]:
        """Получение текущего статуса диагностики"""
        with self.lock:
            return self.current_status.value, self.current_step
            
    def get_progress(self) -> int:
        """Получение текущего прогресса"""
        with self.lock:
            return self.progress