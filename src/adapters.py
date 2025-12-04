"""
Адаптеры для различных моделей Chevrolet Niva.
Обеспечивает поддержку всех модификаций и годов выпуска.
"""

import json
import os
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import hashlib

class VehicleModel(Enum):
    """Поддерживаемые модели Chevrolet Niva"""
    NIVA_2002_2009 = "2123"          # 2002-2009 1.7i 8V
    NIVA_2010_2014 = "21236"         # 2010-2014 1.7i 8V
    NIVA_2014_2020_17 = "21236_17"   # 2014-2020 1.7i 8V
    NIVA_2014_2020_18 = "2123-250"   # 2014-2020 1.8i 16V
    NIVA_MODERN_2021 = "2123M_17"    # 2021-н.в. 1.7i
    NIVA_MODERN_2021_18 = "2123M_18" # 2021-н.в. 1.8i
    NIVA_TAXI = "2123T"              # Такси версия
    NIVA_LUXE = "2123L"              # Люкс комплектация
    NIVA_OFFROAD = "2123O"           # Внедорожная версия

class EngineType(Enum):
    """Типы двигателей"""
    OPEL_17_8V = "OPEL_C16NE"        # 1.7i 8V Opel
    OPEL_18_16V = "OPEL_Z18XE"       # 1.8i 16V Opel
    VAZ_21214 = "VAZ_21214"          # ВАЗовский 1.7i
    VAZ_2123 = "VAZ_2123"            # ВАЗовский 1.8i

class ECUType(Enum):
    """Типы ЭБУ"""
    BOSCH_MP7_0 = "BOSCH_MP7.0"      # Бош МР7.0
    BOSCH_ME7_9_7 = "BOSCH_ME7.9.7"  # Бош МЕ7.9.7
    BOSCH_ME7_9_7_1 = "BOSCH_ME7.9.7.1" # Бош МЕ7.9.7.1
    ITELMA_7_2 = "ITELMA_7.2"        # Ительма 7.2
    JANUARY_7_2 = "JANUARY_7.2"      # Январь 7.2
    VS_5_1 = "VS_5.1"                # VS5.1

class TransmissionType(Enum):
    """Типы трансмиссии"""
    MANUAL_5 = "MANUAL_5"            # Механика 5-ступ
    MANUAL_6 = "MANUAL_6"            # Механика 6-ступ (редуктор)
    AUTOMATIC_4 = "AUTOMATIC_4"      # АКПП 4-ступ

@dataclass
class VehicleInfo:
    """Информация об автомобиле"""
    model: VehicleModel
    year: int
    vin: str
    engine_type: EngineType
    ecu_type: ECUType
    transmission: TransmissionType
    mileage: int = 0
    last_service_date: Optional[datetime] = None
    options: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def vehicle_id(self) -> str:
        """Уникальный идентификатор автомобиля"""
        return hashlib.md5(f"{self.vin}{self.model.value}".encode()).hexdigest()
    
    @property
    def is_euro_2(self) -> bool:
        """Соответствие нормам Евро-2"""
        return self.year <= 2005
    
    @property
    def is_euro_4(self) -> bool:
        """Соответствие нормам Евро-4"""
        return 2006 <= self.year <= 2013
    
    @property
    def is_euro_5(self) -> bool:
        """Соответствие нормам Евро-5"""
        return self.year >= 2014
    
    @property
    def has_abs(self) -> bool:
        """Наличие ABS"""
        return self.year >= 2008 or "abs" in self.options.get("features", [])
    
    @property
    def has_airbag(self) -> bool:
        """Наличие подушек безопасности"""
        return self.year >= 2010 or "airbag" in self.options.get("features", [])
    
    @property
    def has_immobilizer(self) -> bool:
        """Наличие иммобилайзера"""
        return self.year >= 2004
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            "model": self.model.value,
            "year": self.year,
            "vin": self.vin,
            "engine_type": self.engine_type.value,
            "ecu_type": self.ecu_type.value,
            "transmission": self.transmission.value,
            "mileage": self.mileage,
            "last_service_date": self.last_service_date.isoformat() if self.last_service_date else None,
            "options": self.options
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VehicleInfo':
        """Создание из словаря"""
        return cls(
            model=VehicleModel(data["model"]),
            year=data["year"],
            vin=data["vin"],
            engine_type=EngineType(data["engine_type"]),
            ecu_type=ECUType(data["ecu_type"]),
            transmission=TransmissionType(data["transmission"]),
            mileage=data.get("mileage", 0),
            last_service_date=datetime.fromisoformat(data["last_service_date"]) if data.get("last_service_date") else None,
            options=data.get("options", {})
        )

@dataclass
class ECUSettings:
    """Настройки конкретного ЭБУ"""
    ecu_type: ECUType
    protocol: str
    baudrate: int
    init_sequence: List[str]
    supported_pids: Dict[str, str]
    adaptation_procedures: List[str]
    reset_procedures: List[str]
    calibration_data: Dict[str, Any]
    
    # Диагностические параметры
    min_voltage: float = 11.0
    max_voltage: float = 15.0
    normal_rpm_range: tuple = (650, 850)
    normal_coolant_temp_range: tuple = (85, 105)
    
    # Маски для опросов
    query_masks: Dict[str, List[str]] = field(default_factory=dict)

class BaseAdapter:
    """Базовый класс адаптера"""
    
    def __init__(self, vehicle_info: VehicleInfo):
        self.vehicle_info = vehicle_info
        self.settings = self._load_settings()
        self.adaptation_history = []
        self.diagnostic_cache = {}
        
    def _load_settings(self) -> ECUSettings:
        """Загрузка настроек для конкретной модели"""
        raise NotImplementedError
        
    def get_ecu_address(self, system: str) -> str:
        """Получение адреса ЭБУ для системы"""
        addresses = {
            "engine": self._get_engine_address(),
            "abs": "28",
            "airbag": "15",
            "instrument": "25",
            "immobilizer": "29",
            "ac": "08",
            "transmission": "18" if self.vehicle_info.transmission == TransmissionType.AUTOMATIC_4 else None
        }
        return addresses.get(system, "10")
    
    def _get_engine_address(self) -> str:
        """Получение адреса ЭБУ двигателя"""
        if self.vehicle_info.ecu_type == ECUType.BOSCH_MP7_0:
            return "12"
        elif self.vehicle_info.ecu_type in [ECUType.BOSCH_ME7_9_7, ECUType.BOSCH_ME7_9_7_1]:
            return "11"
        elif self.vehicle_info.ecu_type == ECUType.ITELMA_7_2:
            return "13"
        elif self.vehicle_info.ecu_type == ECUType.JANUARY_7_2:
            return "14"
        else:
            return "10"
    
    def get_init_sequence(self) -> List[str]:
        """Получение последовательности инициализации"""
        return self.settings.init_sequence
    
    def get_supported_pids(self, system: str = "engine") -> Dict[str, str]:
        """Получение поддерживаемых PID для системы"""
        if system == "engine":
            return self.settings.supported_pids
        
        # PID для других систем
        system_pids = {
            "abs": self._get_abs_pids(),
            "airbag": self._get_airbag_pids(),
            "instrument": self._get_instrument_pids()
        }
        return system_pids.get(system, {})
    
    def _get_abs_pids(self) -> Dict[str, str]:
        """PID для ABS"""
        return {
            "ABS_STATUS": "01",
            "WHEEL_SPEED_FL": "02",
            "WHEEL_SPEED_FR": "03",
            "WHEEL_SPEED_RL": "04",
            "WHEEL_SPEED_RR": "05",
            "BRAKE_PRESSURE": "06",
            "ABS_WARNING": "07"
        }
    
    def _get_airbag_pids(self) -> Dict[str, str]:
        """PID для подушек безопасности"""
        return {
            "AIRBAG_STATUS": "01",
            "CRASH_SENSOR": "02",
            "SEATBELT_SENSOR": "03",
            "AIRBAG_WARNING": "04"
        }
    
    def _get_instrument_pids(self) -> Dict[str, str]:
        """PID для приборной панели"""
        return {
            "ODOMETER": "01",
            "FUEL_LEVEL": "02",
            "TEMPERATURE": "03",
            "WARNING_LIGHTS": "04",
            "GEAR_POSITION": "05"
        }
    
    def decode_pid_value(self, pid_code: str, raw_value: str, system: str = "engine") -> Any:
        """Декодирование значения PID"""
        decoder = self._get_decoder_for_system(system)
        return decoder(pid_code, raw_value)
    
    def _get_decoder_for_system(self, system: str) -> Callable:
        """Получение декодера для системы"""
        decoders = {
            "engine": self._decode_engine_pid,
            "abs": self._decode_abs_pid,
            "airbag": self._decode_airbag_pid,
            "instrument": self._decode_instrument_pid
        }
        return decoders.get(system, self._decode_generic_pid)
    
    def _decode_engine_pid(self, pid_code: str, raw_value: str) -> Any:
        """Декодирование PID двигателя"""
        try:
            value = int(raw_value, 16)
            
            # Декодирование в зависимости от PID
            if pid_code == "010C":  # RPM
                return value / 4.0 if value > 0 else 0
            
            elif pid_code == "0105":  # Coolant temp
                return value - 40
            
            elif pid_code == "010D":  # Speed
                return value
            
            elif pid_code == "0111":  # Throttle position
                return round((value * 100) / 255, 1)
            
            elif pid_code == "010F":  # Intake air temp
                return value - 40
            
            elif pid_code == "0110":  # MAF
                return value / 100.0
            
            elif pid_code == "010B":  # Intake pressure
                return value
            
            elif pid_code == "0142":  # Control module voltage
                return value / 1000.0
            
            elif pid_code == "0104":  # Engine load
                return round((value * 100) / 255, 1)
            
            elif pid_code == "010E":  # Timing advance
                return (value - 128) / 2.0
            
            elif pid_code == "0133":  # Barometric pressure
                return value
            
            elif pid_code == "010A":  # Fuel pressure
                return value * 3
            
            elif pid_code == "012F":  # Fuel level
                return round((value * 100) / 255, 1)
            
            elif pid_code == "0146":  # Ambient air temp
                return value - 40
            
            elif pid_code == "015C":  # Oil temperature
                return value - 40
            
            elif pid_code == "015E":  # Fuel rate
                return value * 0.05
            
            elif pid_code == "0131":  # Distance since codes cleared
                return value
            
            elif pid_code == "0100":  # Supported PIDs 01-20
                return format(value, '032b')
            
            elif pid_code == "0120":  # Supported PIDs 21-40
                return format(value, '032b')
            
            else:
                return value
                
        except (ValueError, TypeError):
            return None
    
    def _decode_abs_pid(self, pid_code: str, raw_value: str) -> Any:
        """Декодирование PID ABS"""
        value = int(raw_value, 16)
        
        if pid_code == "01":  # ABS статус
            status_bits = bin(value)[2:].zfill(8)
            return {
                "abs_active": status_bits[0] == "1",
                "tcs_active": status_bits[1] == "1",
                "esp_active": status_bits[2] == "1",
                "failure": status_bits[7] == "1"
            }
        
        elif pid_code in ["02", "03", "04", "05"]:  # Скорость колес
            return value * 0.05625  # км/ч
        
        elif pid_code == "06":  # Давление в тормозах
            return value * 0.1  # Бар
        
        else:
            return value
    
    def _decode_airbag_pid(self, pid_code: str, raw_value: str) -> Any:
        """Декодирование PID подушек безопасности"""
        value = int(raw_value, 16)
        
        if pid_code == "01":  # Статус
            status_map = {
                0: "Normal",
                1: "Crash detected",
                2: "Fault detected",
                3: "System disabled"
            }
            return status_map.get(value, "Unknown")
        
        else:
            return value
    
    def _decode_instrument_pid(self, pid_code: str, raw_value: str) -> Any:
        """Декодирование PID приборной панели"""
        value = int(raw_value, 16)
        
        if pid_code == "01":  # Одометр
            return value * 10  # Метры -> километры
        
        elif pid_code == "02":  # Уровень топлива
            return round((value * 100) / 255, 1)
        
        elif pid_code == "03":  # Температура
            return value - 40
        
        elif pid_code == "04":  # Предупреждающие лампы
            warnings = []
            bits = bin(value)[2:].zfill(8)
            warning_map = {
                0: "Check Engine",
                1: "ABS",
                2: "Airbag",
                3: "Battery",
                4: "Oil Pressure",
                5: "Brake Fluid",
                6: "Coolant Temp",
                7: "Seatbelt"
            }
            for i, bit in enumerate(bits):
                if bit == "1" and i in warning_map:
                    warnings.append(warning_map[i])
            return warnings
        
        else:
            return value
    
    def _decode_generic_pid(self, pid_code: str, raw_value: str) -> Any:
        """Общий декодер PID"""
        try:
            return int(raw_value, 16)
        except (ValueError, TypeError):
            return raw_value
    
    def get_normal_ranges(self, parameter: str) -> tuple:
        """Получение нормальных диапазонов для параметра"""
        ranges = {
            "rpm": self.settings.normal_rpm_range,
            "coolant_temp": self.settings.normal_coolant_temp_range,
            "voltage": (self.settings.min_voltage, self.settings.max_voltage),
            "throttle_position": (0.0, 2.0),
            "maf": (2.0, 6.0) if self.vehicle_info.engine_type == EngineType.OPEL_17_8V else (3.0, 8.0),
            "intake_pressure": (30, 40) if self.vehicle_info.is_euro_2 else (35, 45),
            "fuel_pressure": (3.0, 4.0),
            "timing_advance": (-5.0, 15.0),
            "engine_load": (10.0, 30.0) if self.vehicle_info.year <= 2010 else (8.0, 25.0),
            "lambda_voltage": (0.1, 0.9),
            "lambda_correction": (-10.0, 10.0),
            "intake_temp": (10, 50),
            "ambient_temp": (-30, 50)
        }
        return ranges.get(parameter, (None, None))
    
    def is_parameter_normal(self, parameter: str, value: float) -> bool:
        """Проверка, находится ли параметр в нормальном диапазоне"""
        min_val, max_val = self.get_normal_ranges(parameter)
        if min_val is None or max_val is None:
            return True
        return min_val <= value <= max_val
    
    def get_adaptation_procedures(self) -> List[Dict[str, Any]]:
        """Получение процедур адаптации"""
        procedures = []
        
        # Базовые процедуры
        base_procedures = [
            {
                "id": "throttle_adaptation",
                "name": "Адаптация дроссельной заслонки",
                "description": "Обучение нулевого положения дроссельной заслонки",
                "requirements": ["ignition_on", "engine_off", "coolant_temp_5_90"],
                "steps": self._get_throttle_adaptation_steps()
            },
            {
                "id": "idle_adaptation",
                "name": "Адаптация холостого хода",
                "description": "Обучение системы поддержания холостого хода",
                "requirements": ["engine_on", "coolant_temp_70_105", "electrics_off"],
                "steps": self._get_idle_adaptation_steps()
            },
            {
                "id": "lambda_adaptation",
                "name": "Адаптация лямбда-регулирования",
                "description": "Обучение системы топливоподачи",
                "requirements": ["engine_on", "coolant_temp_70_105", "driving_cycle"],
                "steps": self._get_lambda_adaptation_steps()
            }
        ]
        
        procedures.extend(base_procedures)
        
        # Процедуры для конкретных систем
        if self.vehicle_info.has_abs:
            procedures.append({
                "id": "abs_adaptation",
                "name": "Адаптация ABS",
                "description": "Обучение датчиков ABS",
                "requirements": ["ignition_on", "engine_off", "wheel_speed_0"],
                "steps": self._get_abs_adaptation_steps()
            })
        
        if self.vehicle_info.has_immobilizer:
            procedures.append({
                "id": "immobilizer_learning",
                "name": "Обучение иммобилайзера",
                "description": "Добавление новых ключей",
                "requirements": ["ignition_on", "security_code"],
                "steps": self._get_immobilizer_learning_steps()
            })
        
        # Процедуры для АКПП
        if self.vehicle_info.transmission == TransmissionType.AUTOMATIC_4:
            procedures.append({
                "id": "transmission_adaptation",
                "name": "Адаптация АКПП",
                "description": "Обучение переключения передач",
                "requirements": ["engine_on", "coolant_temp_70_105", "transmission_cycle"],
                "steps": self._get_transmission_adaptation_steps()
            })
        
        return procedures
    
    def _get_throttle_adaptation_steps(self) -> List[Dict[str, Any]]:
        """Шаги адаптации дроссельной заслонки"""
        steps = []
        
        if self.vehicle_info.ecu_type == ECUType.BOSCH_MP7_0:
            steps = [
                {"command": "AT IAC", "description": "Инициализация адаптации", "timeout": 2},
                {"command": "010C", "description": "Проверка RPM", "wait_for": "rpm_0"},
                {"command": "0111", "description": "Чтение положения ДЗ", "expect": "0-2%"},
                {"command": "AT TAR", "description": "Запуск адаптации", "timeout": 10},
                {"command": "0111", "description": "Проверка положения ДЗ", "expect": "0%"},
                {"command": "AT DTR", "description": "Сохранить адаптацию", "timeout": 2}
            ]
        elif self.vehicle_info.ecu_type == ECUType.BOSCH_ME7_9_7:
            steps = [
                {"command": "AT IAC", "description": "Инициализация", "timeout": 2},
                {"command": "010C", "description": "Проверка RPM", "wait_for": "rpm_0"},
                {"command": "AT TPSLRN", "description": "Обучение ДЗ", "timeout": 15},
                {"command": "AT TPSRST", "description": "Сброс адаптации ДЗ", "timeout": 5},
                {"command": "AT TPSSAV", "description": "Сохранение параметров", "timeout": 3}
            ]
        
        return steps
    
    def _get_idle_adaptation_steps(self) -> List[Dict[str, Any]]:
        """Шаги адаптации холостого хода"""
        return [
            {"command": "010C", "description": "Проверка RPM", "expect": "700-900"},
            {"command": "0105", "description": "Температура охлаждающей жидкости", "expect": "70-105"},
            {"command": "AT IAR", "description": "Запуск адаптации ХХ", "timeout": 60},
            {"command": "010C", "description": "Контроль RPM", "monitor": True, "duration": 30}
        ]
    
    def _get_lambda_adaptation_steps(self) -> List[Dict[str, Any]]:
        """Шаги адаптации лямбда-регулирования"""
        return [
            {"command": "010C", "description": "RPM > 1500", "wait_for": "rpm_1500"},
            {"command": "AT FTR", "description": "Сброс топливных коррекций", "timeout": 2},
            {"command": "AT LRN", "description": "Обучение лямбда", "timeout": 180},
            {"command": "010C", "description": "Поддержание RPM", "monitor": True, "duration": 180}
        ]
    
    def _get_abs_adaptation_steps(self) -> List[Dict[str, Any]]:
        """Шаги адаптации ABS"""
        return [
            {"command": "28 01", "description": "Проверка связи ABS", "timeout": 2},
            {"command": "28 02", "description": "Сброс адаптации", "timeout": 5},
            {"command": "28 03", "description": "Обучение датчиков", "timeout": 30},
            {"command": "28 04", "description": "Проверка адаптации", "timeout": 2}
        ]
    
    def _get_immobilizer_learning_steps(self) -> List[Dict[str, Any]]:
        """Шаги обучения иммобилайзера"""
        return [
            {"command": "29 01", "description": "Вход в режим обучения", "timeout": 2},
            {"command": "29 02", "description": "Ввод PIN-кода", "input_required": True},
            {"command": "29 03", "description": "Добавление ключа", "timeout": 10},
            {"command": "29 04", "description": "Завершение обучения", "timeout": 2}
        ]
    
    def _get_transmission_adaptation_steps(self) -> List[Dict[str, Any]]:
        """Шаги адаптации АКПП"""
        return [
            {"command": "18 01", "description": "Проверка связи АКПП", "timeout": 2},
            {"command": "18 02", "description": "Сброс адаптации", "timeout": 5},
            {"command": "18 03", "description": "Обучение муфт", "timeout": 120},
            {"command": "18 04", "description": "Проверка адаптации", "timeout": 2}
        ]
    
    def get_reset_procedures(self) -> List[Dict[str, Any]]:
        """Получение процедур сброса"""
        procedures = []
        
        # Сброс адаптаций
        procedures.append({
            "id": "reset_all_adaptations",
            "name": "Сброс всех адаптаций",
            "description": "Сброс всех обучаемых параметров",
            "command": "AT ADPRST",
            "confirmation_required": True
        })
        
        # Сброс топливных коррекций
        procedures.append({
            "id": "reset_fuel_trims",
            "name": "Сброс топливных коррекций",
            "description": "Сброс краткосрочных и долгосрочных коррекций",
            "command": "AT FTR",
            "confirmation_required": False
        })
        
        # Сброс ошибок с сохранением адаптации
        procedures.append({
            "id": "reset_dtc_keep_adaptation",
            "name": "Сброс ошибок (сохранить адаптацию)",
            "description": "Очистка ошибок без сброса адаптаций",
            "command": "AT DCLR",
            "confirmation_required": True
        })
        
        # Полный сброс ECU
        procedures.append({
            "id": "reset_ecu",
            "name": "Полный сброс ЭБУ",
            "description": "Сброс к заводским настройкам",
            "command": "AT Z",
            "confirmation_required": True,
            "warning": "Требуется последующая адаптация!"
        })
        
        return procedures
    
    def get_optimization_parameters(self) -> Dict[str, Any]:
        """Получение оптимальных параметров для настройки"""
        params = {
            "idle_rpm": self._get_optimal_idle_rpm(),
            "fuel_maps": self._get_optimal_fuel_maps(),
            "ignition_maps": self._get_optimal_ignition_maps(),
            "lambda_targets": self._get_optimal_lambda_targets(),
            "vvt_settings": self._get_optimal_vvt_settings(),
            "transmission_settings": self._get_optimal_transmission_settings()
        }
        
        return params
    
    def _get_optimal_idle_rpm(self) -> Dict[str, float]:
        """Оптимальные обороты ХХ"""
        if self.vehicle_info.engine_type == EngineType.OPEL_17_8V:
            return {"warm": 750, "cold": 1100, "ac_on": 850}
        elif self.vehicle_info.engine_type == EngineType.OPEL_18_16V:
            return {"warm": 700, "cold": 1000, "ac_on": 800}
        elif self.vehicle_info.engine_type == EngineType.VAZ_21214:
            return {"warm": 800, "cold": 1200, "ac_on": 900}
        else:
            return {"warm": 750, "cold": 1100, "ac_on": 850}
    
    def _get_optimal_fuel_maps(self) -> Dict[str, List[float]]:
        """Оптимальные топливные карты"""
        # Базовые карты для разных режимов
        if self.vehicle_info.is_euro_2:
            return {
                "idle": [0.8, 0.9, 1.0, 1.1, 1.2],
                "cruise": [0.95, 1.0, 1.05, 1.1, 1.15],
                "acceleration": [1.1, 1.2, 1.3, 1.4, 1.5],
                "wot": [1.2, 1.3, 1.4, 1.5, 1.6]
            }
        elif self.vehicle_info.is_euro_4:
            return {
                "idle": [0.9, 1.0, 1.1, 1.2, 1.3],
                "cruise": [1.0, 1.05, 1.1, 1.15, 1.2],
                "acceleration": [1.15, 1.25, 1.35, 1.45, 1.55],
                "wot": [1.25, 1.35, 1.45, 1.55, 1.65]
            }
        else:  # Евро-5
            return {
                "idle": [1.0, 1.1, 1.2, 1.3, 1.4],
                "cruise": [1.05, 1.1, 1.15, 1.2, 1.25],
                "acceleration": [1.2, 1.3, 1.4, 1.5, 1.6],
                "wot": [1.3, 1.4, 1.5, 1.6, 1.7]
            }
    
    def _get_optimal_ignition_maps(self) -> Dict[str, List[float]]:
        """Оптимальные углы опережения зажигания"""
        base_map = [5, 8, 12, 15, 18, 20, 22, 24, 26, 28]
        
        if self.vehicle_info.engine_type == EngineType.OPEL_18_16V:
            # Более агрессивные углы для 16V
            base_map = [6, 10, 14, 18, 22, 25, 27, 29, 31, 33]
        
        return {
            "low_load": base_map,
            "medium_load": [x + 2 for x in base_map],
            "high_load": [x - 5 for x in base_map],
            "wot": [x - 8 for x in base_map]
        }
    
    def _get_optimal_lambda_targets(self) -> Dict[str, float]:
        """Оптимальные целевые значения лямбда"""
        return {
            "idle": 1.0,
            "cruise": 1.01,
            "acceleration": 0.98,
            "deceleration": 1.05,
            "wot": 0.95,
            "cold_start": 0.9,
            "warm_up": 0.95
        }
    
    def _get_optimal_vvt_settings(self) -> Dict[str, Any]:
        """Оптимальные настройки VVT (для 16V)"""
        if self.vehicle_info.engine_type != EngineType.OPEL_18_16V:
            return {"available": False}
        
        return {
            "available": True,
            "advance_rpm_start": 1500,
            "advance_rpm_end": 4000,
            "max_advance": 25,  # градусов
            "advance_map": [0, 5, 10, 15, 20, 25, 25, 20, 15, 10],
            "retard_map": [0, -5, -10, -15, -10, -5, 0, 0, 0, 0]
        }
    
    def _get_optimal_transmission_settings(self) -> Dict[str, Any]:
        """Оптимальные настройки трансмиссии"""
        if self.vehicle_info.transmission != TransmissionType.AUTOMATIC_4:
            return {"available": False}
        
        return {
            "available": True,
            "shift_points": {
                "1-2": [15, 25, 35],
                "2-3": [30, 40, 50],
                "3-4": [45, 55, 65],
                "kickdown_points": [75, 85, 95]
            },
            "pressure_settings": {
                "normal": 3.5,
                "sport": 4.0,
                "winter": 3.0
            }
        }
    
    def log_adaptation(self, procedure_id: str, result: str, details: Dict[str, Any]):
        """Логирование процедуры адаптации"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "procedure_id": procedure_id,
            "vehicle_id": self.vehicle_info.vehicle_id,
            "result": result,
            "details": details,
            "mileage": self.vehicle_info.mileage
        }
        self.adaptation_history.append(log_entry)
        
        # Сохранение в файл
        self._save_adaptation_log(log_entry)
    
    def _save_adaptation_log(self, log_entry: Dict[str, Any]):
        """Сохранение лога адаптации"""
        log_file = f"adaptation_log_{self.vehicle_info.vehicle_id}.json"
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            logs.append(log_entry)
            
            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Ошибка сохранения лога: {e}")
    
    def get_adaptation_history(self) -> List[Dict[str, Any]]:
        """Получение истории адаптаций"""
        return self.adaptation_history

class Niva2002_2009Adapter(BaseAdapter):
    """Адаптер для Niva 2002-2009 (1.7i 8V)"""
    
    def _load_settings(self) -> ECUSettings:
        return ECUSettings(
            ecu_type=ECUType.BOSCH_MP7_0,
            protocol="ISO9141-2",
            baudrate=10400,
            init_sequence=[
                "ATZ",
                "ATE0",
                "ATL0",
                "ATH1",
                "ATSP3",
                "0100"
            ],
            supported_pids={
                "ENGINE_RPM": "010C",
                "VEHICLE_SPEED": "010D",
                "COOLANT_TEMP": "0105",
                "INTAKE_TEMP": "010F",
                "THROTTLE_POSITION": "0111",
                "MAF_SENSOR": "0110",
                "O2_SENSOR_B1S1": "0114",
                "FUEL_PRESSURE": "010A",
                "INTAKE_PRESSURE": "010B",
                "TIMING_ADVANCE": "010E",
                "ENGINE_LOAD": "0104",
                "FUEL_LEVEL": "012F",
                "CONTROL_MODULE_VOLTAGE": "0142"
            },
            adaptation_procedures=[
                "throttle_adaptation",
                "idle_adaptation",
                "lambda_adaptation"
            ],
            reset_procedures=[
                "reset_dtc",
                "reset_adaptation"
            ],
            calibration_data={
                "idle_rpm": 750,
                "max_rpm": 6200,
                "fuel_cutoff_rpm": 6400,
                "lambda_target": 1.0,
                "injection_time_base": 2.5,
                "ignition_advance_base": 10
            },
            min_voltage=11.5,
            max_voltage=14.5,
            normal_rpm_range=(700, 800),
            normal_coolant_temp_range=(85, 100)
        )

class Niva2010_2014Adapter(BaseAdapter):
    """Адаптер для Niva 2010-2014 (1.7i 8V)"""
    
    def _load_settings(self) -> ECUSettings:
        return ECUSettings(
            ecu_type=ECUType.BOSCH_ME7_9_7,
            protocol="ISO14230-4 (KWP2000)",
            baudrate=10400,
            init_sequence=[
                "ATZ",
                "ATE0",
                "ATL0",
                "ATH1",
                "ATSP4",
                "ATBI",
                "0100"
            ],
            supported_pids={
                "ENGINE_RPM": "010C",
                "VEHICLE_SPEED": "010D",
                "COOLANT_TEMP": "0105",
                "INTAKE_TEMP": "010F",
                "THROTTLE_POSITION": "0111",
                "MAF_SENSOR": "0110",
                "O2_SENSOR_B1S1": "0114",
                "O2_SENSOR_B1S2": "0115",
                "INTAKE_PRESSURE": "010B",
                "TIMING_ADVANCE": "010E",
                "ENGINE_LOAD": "0104",
                "FUEL_LEVEL": "012F",
                "CONTROL_MODULE_VOLTAGE": "0142",
                "BAROMETRIC_PRESSURE": "0133",
                "AMBIENT_TEMP": "0146",
                "FUEL_RATE": "015E",
                "DISTANCE_TRAVELED": "0131"
            },
            adaptation_procedures=[
                "throttle_adaptation",
                "idle_adaptation",
                "lambda_adaptation",
                "abs_adaptation"
            ],
            reset_procedures=[
                "reset_dtc",
                "reset_adaptation",
                "reset_fuel_trims"
            ],
            calibration_data={
                "idle_rpm": 700,
                "max_rpm": 6500,
                "fuel_cutoff_rpm": 6700,
                "lambda_target": 1.01,
                "injection_time_base": 2.2,
                "ignition_advance_base": 12,
                "vvt_enabled": False
            },
            min_voltage=11.8,
            max_voltage=14.7,
            normal_rpm_range=(680, 750),
            normal_coolant_temp_range=(87, 102)
        )

class Niva2014_2020_18Adapter(BaseAdapter):
    """Адаптер для Niva 2014-2020 (1.8i 16V)"""
    
    def _load_settings(self) -> ECUSettings:
        return ECUSettings(
            ecu_type=ECUType.BOSCH_ME7_9_7_1,
            protocol="ISO14230-4 (KWP2000)",
            baudrate=10400,
            init_sequence=[
                "ATZ",
                "ATE0",
                "ATL0",
                "ATH1",
                "ATSP4",
                "ATBI",
                "ATSH8111F1",
                "0100"
            ],
            supported_pids={
                "ENGINE_RPM": "010C",
                "VEHICLE_SPEED": "010D",
                "COOLANT_TEMP": "0105",
                "INTAKE_TEMP": "010F",
                "THROTTLE_POSITION": "0111",
                "MAF_SENSOR": "0110",
                "O2_SENSOR_B1S1": "0114",
                "O2_SENSOR_B1S2": "0115",
                "O2_SENSOR_B2S1": "0124",
                "O2_SENSOR_B2S2": "0125",
                "INTAKE_PRESSURE": "010B",
                "TIMING_ADVANCE": "010E",
                "ENGINE_LOAD": "0104",
                "FUEL_LEVEL": "012F",
                "CONTROL_MODULE_VOLTAGE": "0142",
                "BAROMETRIC_PRESSURE": "0133",
                "AMBIENT_TEMP": "0146",
                "FUEL_RATE": "015E",
                "DISTANCE_TRAVELED": "0131",
                "OIL_TEMP": "015C",
                "VVT_POSITION": "0134",
                "CATALYST_TEMP": "013C"
            },
            adaptation_procedures=[
                "throttle_adaptation",
                "idle_adaptation",
                "lambda_adaptation",
                "vvt_adaptation",
                "abs_adaptation",
                "immobilizer_learning"
            ],
            reset_procedures=[
                "reset_dtc",
                "reset_adaptation",
                "reset_fuel_trims",
                "reset_vvt_learning"
            ],
            calibration_data={
                "idle_rpm": 680,
                "max_rpm": 6800,
                "fuel_cutoff_rpm": 7000,
                "lambda_target": 1.0,
                "injection_time_base": 2.0,
                "ignition_advance_base": 15,
                "vvt_enabled": True,
                "vvt_advance_max": 25,
                "vvt_retard_max": 15
            },
            min_voltage=12.0,
            max_voltage=14.8,
            normal_rpm_range=(670, 730),
            normal_coolant_temp_range=(88, 103),
            query_masks={
                "quick_scan": ["010C", "0105", "010D", "0111", "0142"],
                "full_scan": ["0100", "0120", "0140", "0160", "0180"],
                "emissions": ["0114", "0115", "0124", "0125", "013C"]
            }
        )

class NivaModernAdapter(BaseAdapter):
    """Адаптер для Niva Модерн (2021-н.в.)"""
    
    def _load_settings(self) -> ECUSettings:
        return ECUSettings(
            ecu_type=ECUType.ITELMA_7_2,
            protocol="ISO15765-4 (CAN)",
            baudrate=500000,
            init_sequence=[
                "ATZ",
                "ATE0",
                "ATL0",
                "ATH1",
                "ATSP6",
                "ATC1",
                "ATCAF0",
                "ATFCSH7E0",
                "ATFCSD300000",
                "ATFCSM1",
                "022004"
            ],
            supported_pids={
                "ENGINE_RPM": "010C",
                "VEHICLE_SPEED": "010D",
                "COOLANT_TEMP": "0105",
                "INTAKE_TEMP": "010F",
                "THROTTLE_POSITION": "0111",
                "MAF_SENSOR": "0110",
                "O2_SENSOR_B1S1": "0114",
                "O2_SENSOR_B1S2": "0115",
                "INTAKE_PRESSURE": "010B",
                "TIMING_ADVANCE": "010E",
                "ENGINE_LOAD": "0104",
                "FUEL_LEVEL": "012F",
                "CONTROL_MODULE_VOLTAGE": "0142",
                "BAROMETRIC_PRESSURE": "0133",
                "AMBIENT_TEMP": "0146",
                "FUEL_RATE": "015E",
                "DISTANCE_TRAVELED": "0131",
                "OIL_TEMP": "015C",
                "PARTICULATE_FILTER": "015D",
                "NOX_SENSOR": "015F"
            },
            adaptation_procedures=[
                "throttle_adaptation",
                "idle_adaptation",
                "lambda_adaptation",
                "dpf_regeneration",
                "nox_sensor_adaptation",
                "abs_adaptation",
                "immobilizer_learning",
                "transmission_adaptation"
            ],
            reset_procedures=[
                "reset_dtc",
                "reset_adaptation",
                "reset_fuel_trims",
                "reset_dpf",
                "reset_nox"
            ],
            calibration_data={
                "idle_rpm": 650,
                "max_rpm": 6500,
                "fuel_cutoff_rpm": 6700,
                "lambda_target": 1.0,
                "injection_time_base": 1.8,
                "ignition_advance_base": 18,
                "vvt_enabled": True,
                "dpf_enabled": True,
                "nox_enabled": True,
                "start_stop_enabled": True
            },
            min_voltage=12.2,
            max_voltage=15.0,
            normal_rpm_range=(640, 700),
            normal_coolant_temp_range=(90, 105),
            query_masks={
                "quick_scan": ["010C", "0105", "010D", "0111", "0142", "015C"],
                "full_scan": ["0100", "0120", "0140", "0160", "0180", "01A0"],
                "emissions": ["0114", "0115", "015D", "015F", "013C"],
                "systems": ["022004", "0220C1", "0220C2", "0220C3"]
            }
        )

class AdapterFactory:
    """Фабрика для создания адаптеров"""
    
    @staticmethod
    def create_adapter(vehicle_info: VehicleInfo) -> BaseAdapter:
        """Создание адаптера для конкретного автомобиля"""
        model = vehicle_info.model
        
        adapter_map = {
            VehicleModel.NIVA_2002_2009: Niva2002_2009Adapter,
            VehicleModel.NIVA_2010_2014: Niva2010_2014Adapter,
            VehicleModel.NIVA_2014_2020_17: Niva2010_2014Adapter,  # Используем тот же адаптер
            VehicleModel.NIVA_2014_2020_18: Niva2014_2020_18Adapter,
            VehicleModel.NIVA_MODERN_2021: NivaModernAdapter,
            VehicleModel.NIVA_MODERN_2021_18: NivaModernAdapter,
            VehicleModel.NIVA_TAXI: NivaModernAdapter,  # Такси на базе Модерн
            VehicleModel.NIVA_LUXE: NivaModernAdapter,  # Люкс на базе Модерн
            VehicleModel.NIVA_OFFROAD: NivaModernAdapter  # Внедорожная на базе Модерн
        }
        
        adapter_class = adapter_map.get(model)
        if not adapter_class:
            # По умолчанию используем адаптер для современной модели
            adapter_class = NivaModernAdapter
        
        return adapter_class(vehicle_info)
    
    @staticmethod
    def detect_model_from_vin(vin: str) -> Optional[VehicleModel]:
        """Определение модели по VIN"""
        if not vin or len(vin) < 17:
            return None
        
        # Анализ VIN для определения модели
        # XTT - Chevrolet
        # 2123 - модель
        # Позиции в VIN для Chevrolet Niva
        
        try:
            model_code = vin[3:7]  # Позиции 4-7 для модели
            
            if model_code == "2123":
                year_code = vin[9]  # Позиция 10 - год
                year = AdapterFactory._decode_year_code(year_code)
                
                if year >= 2021:
                    return VehicleModel.NIVA_MODERN_2021
                elif year >= 2014:
                    engine_code = vin[7]  # Позиция 8 - двигатель
                    if engine_code == "H":  # 1.8i
                        return VehicleModel.NIVA_2014_2020_18
                    else:  # 1.7i
                        return VehicleModel.NIVA_2014_2020_17
                elif year >= 2010:
                    return VehicleModel.NIVA_2010_2014
                else:
                    return VehicleModel.NIVA_2002_2009
                    
        except (IndexError, ValueError):
            pass
        
        return None
    
    @staticmethod
    def _decode_year_code(code: str) -> int:
        """Декодирование кода года"""
        year_map = {
            'A': 2010, 'B': 2011, 'C': 2012, 'D': 2013, 'E': 2014,
            'F': 2015, 'G': 2016, 'H': 2017, 'J': 2018, 'K': 2019,
            'L': 2020, 'M': 2021, 'N': 2022, 'P': 2023, 'R': 2024,
            'S': 2025
        }
        return year_map.get(code.upper(), 2000)
    
    @staticmethod
    def detect_ecu_type(connector: Any) -> Optional[ECUType]:
        """Определение типа ЭБУ через диагностику"""
        # Отправляем тестовые команды для определения ЭБУ
        test_commands = [
            ("ATZ", ECUType.BOSCH_MP7_0),
            ("ATI", ECUType.BOSCH_ME7_9_7),
            ("AT@1", ECUType.ITELMA_7_2),
            ("ATRV", ECUType.JANUARY_7_2)
        ]
        
        for cmd, ecu_type in test_commands:
            try:
                response = connector.send_command(cmd)
                if response and "ELM327" not in response:
                    # Анализируем ответ для определения ЭБУ
                    if "BOSCH MP7.0" in response:
                        return ECUType.BOSCH_MP7_0
                    elif "BOSCH ME7.9.7" in response:
                        return ECUType.BOSCH_ME7_9_7
                    elif "ITELMA" in response:
                        return ECUType.ITELMA_7_2
                    elif "JANUARY" in response:
                        return ECUType.JANUARY_7_2
            except:
                continue
        
        return None

# Утилиты для работы с адаптерами

class VehicleDatabase:
    """База данных автомобилей"""
    
    def __init__(self, db_file: str = "vehicles.db.json"):
        self.db_file = db_file
        self.vehicles = self._load_database()
    
    def _load_database(self) -> Dict[str, VehicleInfo]:
        """Загрузка базы данных"""
        try:
            if os.path.exists(self.db_file):
                with open(self.db_file, 'r') as f:
                    data = json.load(f)
                return {vid: VehicleInfo.from_dict(vdata) for vid, vdata in data.items()}
        except Exception as e:
            print(f"Ошибка загрузки БД: {e}")
        return {}
    
    def save_database(self):
        """Сохранение базы данных"""
        try:
            data = {vid: vehicle.to_dict() for vid, vehicle in self.vehicles.items()}
            with open(self.db_file, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Ошибка сохранения БД: {e}")
            return False
    
    def add_vehicle(self, vehicle_info: VehicleInfo) -> bool:
        """Добавление автомобиля в БД"""
        self.vehicles[vehicle_info.vehicle_id] = vehicle_info
        return self.save_database()
    
    def get_vehicle(self, vehicle_id: str) -> Optional[VehicleInfo]:
        """Получение информации об автомобиле"""
        return self.vehicles.get(vehicle_id)
    
    def update_vehicle_mileage(self, vehicle_id: str, mileage: int) -> bool:
        """Обновление пробега автомобиля"""
        if vehicle_id in self.vehicles:
            self.vehicles[vehicle_id].mileage = mileage
            return self.save_database()
        return False
    
    def find_vehicle_by_vin(self, vin: str) -> Optional[VehicleInfo]:
        """Поиск автомобиля по VIN"""
        for vehicle in self.vehicles.values():
            if vehicle.vin == vin:
                return vehicle
        return None
    
    def get_all_vehicles(self) -> List[VehicleInfo]:
        """Получение всех автомобилей"""
        return list(self.vehicles.values())

class AdapterManager:
    """Менеджер адаптеров"""
    
    def __init__(self):
        self.active_adapter: Optional[BaseAdapter] = None
        self.vehicle_database = VehicleDatabase()
        self.adaptation_logs = {}
    
    def initialize_adapter(self, vehicle_info: VehicleInfo) -> BaseAdapter:
        """Инициализация адаптера для автомобиля"""
        self.active_adapter = AdapterFactory.create_adapter(vehicle_info)
        
        # Добавляем автомобиль в БД если его нет
        if not self.vehicle_database.get_vehicle(vehicle_info.vehicle_id):
            self.vehicle_database.add_vehicle(vehicle_info)
        
        return self.active_adapter
    
    def detect_and_initialize(self, vin: str, connector: Any = None) -> Optional[BaseAdapter]:
        """Автоматическое определение и инициализация адаптера"""
        # Поиск в БД
        vehicle_info = self.vehicle_database.find_vehicle_by_vin(vin)
        
        if not vehicle_info:
            # Автоматическое определение модели
            model = AdapterFactory.detect_model_from_vin(vin)
            if not model:
                return None
            
            # Определение типа ЭБУ если есть подключение
            ecu_type = None
            if connector:
                ecu_type = AdapterFactory.detect_ecu_type(connector)
            
            # Создаем базовую информацию
            vehicle_info = VehicleInfo(
                model=model,
                year=AdapterFactory._decode_year_code(vin[9]) if len(vin) > 9 else 2020,
                vin=vin,
                engine_type=EngineType.OPEL_17_8V if model.value.endswith("17") else EngineType.OPEL_18_16V,
                ecu_type=ecu_type or ECUType.BOSCH_ME7_9_7,
                transmission=TransmissionType.MANUAL_5
            )
        
        return self.initialize_adapter(vehicle_info)
    
    def get_active_adapter(self) -> Optional[BaseAdapter]:
        """Получение активного адаптера"""
        return self.active_adapter
    
    def save_adaptation_log(self, procedure_id: str, result: str, details: Dict[str, Any]):
        """Сохранение лога адаптации"""
        if not self.active_adapter:
            return
        
        vehicle_id = self.active_adapter.vehicle_info.vehicle_id
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "procedure_id": procedure_id,
            "result": result,
            "details": details
        }
        
        if vehicle_id not in self.adaptation_logs:
            self.adaptation_logs[vehicle_id] = []
        
        self.adaptation_logs[vehicle_id].append(log_entry)
        
        # Также сохраняем через адаптер
        self.active_adapter.log_adaptation(procedure_id, result, details)
    
    def get_vehicle_statistics(self, vehicle_id: str) -> Dict[str, Any]:
        """Получение статистики по автомобилю"""
        vehicle = self.vehicle_database.get_vehicle(vehicle_id)
        if not vehicle:
            return {}
        
        adaptations = self.adaptation_logs.get(vehicle_id, [])
        
        return {
            "vehicle_info": vehicle.to_dict(),
            "total_adaptations": len(adaptations),
            "last_adaptation": adaptations[-1] if adaptations else None,
            "successful_adaptations": len([a for a in adaptations if a.get("result") == "success"]),
            "adaptation_history": adaptations[-10:]  # Последние 10 записей
        }

# Экспортируемые функции для удобства

def create_adapter_for_vehicle(
    model: str,
    year: int,
    vin: str,
    engine_type: str = None,
    ecu_type: str = None
) -> BaseAdapter:
    """Создание адаптера по параметрам"""
    # Преобразование строк в Enum
    try:
        vehicle_model = VehicleModel(model)
    except ValueError:
        # Поиск по частичному совпадению
        for vm in VehicleModel:
            if model in vm.value:
                vehicle_model = vm
                break
        else:
            vehicle_model = VehicleModel.NIVA_MODERN_2021
    
    engine_enum = EngineType.OPEL_17_8V
    if engine_type:
        try:
            engine_enum = EngineType(engine_type)
        except ValueError:
            if "1.8" in engine_type or "16V" in engine_type:
                engine_enum = EngineType.OPEL_18_16V
    
    ecu_enum = ECUType.BOSCH_ME7_9_7
    if ecu_type:
        try:
            ecu_enum = ECUType(ecu_type)
        except ValueError:
            if "MP7" in ecu_type:
                ecu_enum = ECUType.BOSCH_MP7_0
            elif "ITELMA" in ecu_type:
                ecu_enum = ECUType.ITELMA_7_2
    
    # Определение трансмиссии
    transmission = TransmissionType.MANUAL_5
    if year >= 2021 and "AUTO" in vin.upper():
        transmission = TransmissionType.AUTOMATIC_4
    
    vehicle_info = VehicleInfo(
        model=vehicle_model,
        year=year,
        vin=vin,
        engine_type=engine_enum,
        ecu_type=ecu_enum,
        transmission=transmission
    )
    
    return AdapterFactory.create_adapter(vehicle_info)

def get_all_supported_models() -> List[Dict[str, Any]]:
    """Получение списка всех поддерживаемых моделей"""
    models = []
    
    for model in VehicleModel:
        adapter_class = AdapterFactory.create_adapter.__func__.__defaults__[0]
        try:
            # Создаем тестовый VehicleInfo для получения информации
            test_info = VehicleInfo(
                model=model,
                year=2020,
                vin="TEST" + model.value,
                engine_type=EngineType.OPEL_17_8V,
                ecu_type=ECUType.BOSCH_ME7_9_7,
                transmission=TransmissionType.MANUAL_5
            )
            
            adapter = AdapterFactory.create_adapter(test_info)
            settings = adapter.settings
            
            models.append({
                "model": model.value,
                "name": model.name,
                "years": _get_model_years(model),
                "engine": _get_model_engine(model),
                "ecu_type": settings.ecu_type.value,
                "protocol": settings.protocol,
                "supported_systems": list(adapter.get_adaptation_procedures())
            })
        except:
            continue
    
    return models

def _get_model_years(model: VehicleModel) -> str:
    """Получение годов выпуска модели"""
    year_map = {
        VehicleModel.NIVA_2002_2009: "2002-2009",
        VehicleModel.NIVA_2010_2014: "2010-2014",
        VehicleModel.NIVA_2014_2020_17: "2014-2020",
        VehicleModel.NIVA_2014_2020_18: "2014-2020",
        VehicleModel.NIVA_MODERN_2021: "2021-н.в.",
        VehicleModel.NIVA_MODERN_2021_18: "2021-н.в.",
        VehicleModel.NIVA_TAXI: "2021-н.в.",
        VehicleModel.NIVA_LUXE: "2021-н.в.",
        VehicleModel.NIVA_OFFROAD: "2021-н.в."
    }
    return year_map.get(model, "Unknown")

def _get_model_engine(model: VehicleModel) -> str:
    """Получение двигателя модели"""
    engine_map = {
        VehicleModel.NIVA_2002_2009: "1.7i 8V",
        VehicleModel.NIVA_2010_2014: "1.7i 8V",
        VehicleModel.NIVA_2014_2020_17: "1.7i 8V",
        VehicleModel.NIVA_2014_2020_18: "1.8i 16V",
        VehicleModel.NIVA_MODERN_2021: "1.7i 8V",
        VehicleModel.NIVA_MODERN_2021_18: "1.8i 16V",
        VehicleModel.NIVA_TAXI: "1.7i 8V (Такси)",
        VehicleModel.NIVA_LUXE: "1.8i 16V (Люкс)",
        VehicleModel.NIVA_OFFROAD: "1.7i 8V (Offroad)"
    }
    return engine_map.get(model, "Unknown")

# Пример использования
if __name__ == "__main__":
    # Пример создания адаптера для конкретного автомобиля
    vehicle_info = VehicleInfo(
        model=VehicleModel.NIVA_2014_2020_18,
        year=2018,
        vin="XTT2123H8J1234567",
        engine_type=EngineType.OPEL_18_16V,
        ecu_type=ECUType.BOSCH_ME7_9_7_1,
        transmission=TransmissionType.MANUAL_5,
        mileage=75000
    )
    
    adapter = AdapterFactory.create_adapter(vehicle_info)
    print(f"Адаптер создан для: {vehicle_info.model.name}")
    print(f"Протокол: {adapter.settings.protocol}")
    print(f"Поддерживаемых PID: {len(adapter.get_supported_pids())}")
    print(f"Процедур адаптации: {len(adapter.get_adaptation_procedures())}")
    
    # Пример получения оптимальных параметров
    optimal_params = adapter.get_optimization_parameters()
    print(f"Оптимальные обороты ХХ: {optimal_params['idle_rpm']}")