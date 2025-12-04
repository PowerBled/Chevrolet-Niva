"""
Полный модуль протоколов и команд для диагностики Chevrolet Niva
Автор: Профессиональная диагностика Chevrolet Niva
Версия: 1.0.0
"""

import struct
import binascii
from enum import Enum, IntEnum
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
import json

class ProtocolType(Enum):
    """Типы протоколов OBD-II"""
    ISO_9141_2 = "ISO 9141-2"
    ISO_14230_4_KWP = "ISO 14230-4 KWP"
    ISO_14230_4_KWP_FAST = "ISO 14230-4 KWP (Fast)"
    ISO_15765_4_CAN = "ISO 15765-4 CAN"
    SAE_J1850_PWM = "SAE J1850 PWM"
    SAE_J1850_VPW = "SAE J1850 VPW"
    AUTO = "AUTO"

class ECUAddress(IntEnum):
    """Адреса ЭБУ в автомобиле"""
    # Основные ЭБУ
    ENGINE_ECU = 0x10           # ЭБУ двигателя (главный)
    TRANSMISSION_ECU = 0x18     # ЭБУ АКПП (если есть)
    ABS_ECU = 0x28              # АБС
    AIRBAG_ECU = 0x15           # Подушки безопасности
    IMMOBILIZER_ECU = 0x29      # Иммобилайзер
    INSTRUMENT_CLUSTER = 0x25   # Приборная панель
    CLIMATE_CONTROL = 0x08      # Климат-контроль
    BODY_CONTROL = 0x40         # Блок кузовной электроники
    CENTRAL_LOCKING = 0x30      # Центральный замок
    
    # Дополнительные ЭБУ
    ELECTRONIC_STABILITY = 0x2A # ESP
    STEERING_ANGLE = 0x2B       # Датчик угла поворота руля
    PARKING_ASSIST = 0x36       # Парктроник
    RADIO = 0x50                # Магнитола
    
    # Шины
    DIAGNOSIS_INTERFACE = 0xF1  # Диагностический интерфейс
    GATEWAY = 0x7F              # Шлюз

class DiagnosticMode(IntEnum):
    """Режимы диагностики OBD-II"""
    SHOW_CURRENT_DATA = 0x01
    SHOW_FREEZE_FRAME_DATA = 0x02
    SHOW_STORED_DIAGNOSTIC_TROUBLE_CODES = 0x03
    CLEAR_DIAGNOSTIC_TROUBLE_CODES = 0x04
    TEST_RESULTS_OXYGEN_SENSORS = 0x05
    TEST_RESULTS_OTHER_MONITORS = 0x06
    SHOW_PENDING_DIAGNOSTIC_TROUBLE_CODES = 0x07
    CONTROL_OPERATIONS = 0x08
    REQUEST_VEHICLE_INFORMATION = 0x09
    SHOW_PERMANENT_DIAGNOSTIC_TROUBLE_CODES = 0x0A
    
    # Расширенные режимы
    ECU_IDENTIFICATION = 0x1A
    READ_ECU_MEMORY = 0x23
    WRITE_ECU_MEMORY = 0x3D
    ROUTINE_CONTROL = 0x31
    REQUEST_DOWNLOAD = 0x34
    TRANSFER_DATA = 0x36
    REQUEST_TRANSFER_EXIT = 0x37

@dataclass
class VehicleModel:
    """Модель автомобиля"""
    code: str
    name: str
    production_years: str
    engine_type: str
    engine_codes: List[str]
    protocol: ProtocolType
    ecus: List[ECUAddress]
    notes: str = ""

@dataclass
class PIDDefinition:
    """Определение PID"""
    pid_code: str
    name: str
    description: str
    formula: str
    unit: str
    min_value: float
    max_value: float
    byte_length: int
    scaling: float = 1.0
    offset: float = 0.0
    data_type: str = "uint8"  # uint8, uint16, int8, int16, bits, bool

@dataclass
class SensorDefinition:
    """Определение датчика"""
    sensor_id: str
    name: str
    ecu: ECUAddress
    pid: str
    normal_range: Tuple[float, float]
    critical_range: Tuple[float, float]
    location: str
    replacement_part_number: str = ""

@dataclass
class AdaptationParameter:
    """Параметр адаптации"""
    param_id: str
    name: str
    description: str
    address: Tuple[int, int]  # (address, length)
    min_value: int
    max_value: int
    default_value: int
    step: int = 1
    requires_ignition: bool = True
    requires_engine_off: bool = False

class NivaProtocols:
    """
    Полная реализация протоколов для Chevrolet Niva
    """
    
    # =========================================================================
    # МОДЕЛИ АВТОМОБИЛЕЙ
    # =========================================================================
    
    VEHICLE_MODELS: Dict[str, VehicleModel] = {
        '2123': VehicleModel(
            code='2123',
            name='Chevrolet Niva 1.7i 8V',
            production_years='2002-2009',
            engine_type='ВАЗ-2123, 1.7L, 8V, инжектор',
            engine_codes=['2111', '21114'],
            protocol=ProtocolType.ISO_9141_2,
            ecus=[
                ECUAddress.ENGINE_ECU,
                ECUAddress.ABS_ECU,
                ECUAddress.AIRBAG_ECU,
                ECUAddress.IMMOBILIZER_ECU,
                ECUAddress.INSTRUMENT_CLUSTER,
            ],
            notes='Первое поколение, Январь 7.2 / M7.3.7'
        ),
        
        '21236': VehicleModel(
            code='21236',
            name='Chevrolet Niva 1.7i 16V',
            production_years='2010-2020',
            engine_type='ВАЗ-21236, 1.7L, 16V, инжектор',
            engine_codes=['21236'],
            protocol=ProtocolType.ISO_14230_4_KWP,
            ecus=[
                ECUAddress.ENGINE_ECU,
                ECUAddress.ABS_ECU,
                ECUAddress.AIRBAG_ECU,
                ECUAddress.IMMOBILIZER_ECU,
                ECUAddress.INSTRUMENT_CLUSTER,
                ECUAddress.CLIMATE_CONTROL,
                ECUAddress.BODY_CONTROL,
            ],
            notes='Второе поколение, Bosch ME7.9.7 / Январь 7.3'
        ),
        
        '2123-250': VehicleModel(
            code='2123-250',
            name='Chevrolet Niva 1.8i',
            production_years='2014-2020',
            engine_type='ВАЗ-11194, 1.8L, 16V, инжектор',
            engine_codes=['11194'],
            protocol=ProtocolType.ISO_15765_4_CAN,
            ecus=[
                ECUAddress.ENGINE_ECU,
                ECUAddress.ABS_ECU,
                ECUAddress.AIRBAG_ECU,
                ECUAddress.IMMOBILIZER_ECU,
                ECUAddress.INSTRUMENT_CLUSTER,
                ECUAddress.CLIMATE_CONTROL,
                ECUAddress.BODY_CONTROL,
                ECUAddress.ELECTRONIC_STABILITY,
            ],
            notes='Третье поколение, Bosch ME17.9.7'
        ),
        
        '2123M': VehicleModel(
            code='2123M',
            name='Chevrolet Niva Модерн',
            production_years='2021-н.в.',
            engine_type='ВАЗ-21231, 1.7L, 16V, инжектор',
            engine_codes=['21231'],
            protocol=ProtocolType.ISO_15765_4_CAN,
            ecus=[
                ECUAddress.ENGINE_ECU,
                ECUAddress.ABS_ECU,
                ECUAddress.AIRBAG_ECU,
                ECUAddress.IMMOBILIZER_ECU,
                ECUAddress.INSTRUMENT_CLUSTER,
                ECUAddress.CLIMATE_CONTROL,
                ECUAddress.BODY_CONTROL,
                ECUAddress.ELECTRONIC_STABILITY,
                ECUAddress.PARKING_ASSIST,
            ],
            notes='Обновленная версия, Bosch ME17.9.7+, CAN-шина'
        ),
        
        '2123-60': VehicleModel(
            code='2123-60',
            name='LADA Niva Travel',
            production_years='2020-н.в.',
            engine_type='ВАЗ-21230, 1.7L, 16V, инжектор',
            engine_codes=['21230'],
            protocol=ProtocolType.ISO_15765_4_CAN,
            ecus=[
                ECUAddress.ENGINE_ECU,
                ECUAddress.ABS_ECU,
                ECUAddress.AIRBAG_ECU,
                ECUAddress.IMMOBILIZER_ECU,
                ECUAddress.INSTRUMENT_CLUSTER,
                ECUAddress.CLIMATE_CONTROL,
                ECUAddress.BODY_CONTROL,
                ECUAddress.ELECTRONIC_STABILITY,
                ECUAddress.PARKING_ASSIST,
            ],
            notes='Экспортная версия, полная CAN-шина'
        ),
    }
    
    # =========================================================================
    # PID ОПРЕДЕЛЕНИЯ
    # =========================================================================
    
    # Базовые PID (режим 01)
    BASE_PIDS: Dict[str, PIDDefinition] = {
        # Показатели двигателя
        '0100': PIDDefinition(
            pid_code='0100',
            name='Supported PIDs [01-20]',
            description='Поддерживаемые PID с 01 по 20',
            formula='Битовая маска',
            unit='bits',
            min_value=0,
            max_value=0xFFFFFFFF,
            byte_length=4,
            data_type='bits'
        ),
        
        '0101': PIDDefinition(
            pid_code='0101',
            name='Monitor status since DTCs cleared',
            description='Статус мониторов с момента очистки DTC',
            formula='4 байта данных',
            unit='',
            min_value=0,
            max_value=0xFFFFFFFF,
            byte_length=4,
            data_type='bits'
        ),
        
        '0103': PIDDefinition(
            pid_code='0103',
            name='Fuel system status',
            description='Состояние топливной системы',
            formula='A*256 + B',
            unit='',
            min_value=0,
            max_value=65535,
            byte_length=2,
            data_type='uint16'
        ),
        
        '0104': PIDDefinition(
            pid_code='0104',
            name='Calculated engine load',
            description='Расчетная нагрузка на двигатель',
            formula='A * 100 / 255',
            unit='%',
            min_value=0,
            max_value=100,
            byte_length=1,
            scaling=100/255,
            data_type='uint8'
        ),
        
        '0105': PIDDefinition(
            pid_code='0105',
            name='Engine coolant temperature',
            description='Температура охлаждающей жидкости',
            formula='A - 40',
            unit='°C',
            min_value=-40,
            max_value=215,
            byte_length=1,
            offset=-40,
            data_type='int8'
        ),
        
        '0106': PIDDefinition(
            pid_code='0106',
            name='Short term fuel trim—Bank 1',
            description='Краткосрочная коррекция топлива, банк 1',
            formula='(A - 128) * 100 / 128',
            unit='%',
            min_value=-100,
            max_value=99.22,
            byte_length=1,
            scaling=100/128,
            offset=-100,
            data_type='int8'
        ),
        
        '0107': PIDDefinition(
            pid_code='0107',
            name='Long term fuel trim—Bank 1',
            description='Долгосрочная коррекция топлива, банк 1',
            formula='(A - 128) * 100 / 128',
            unit='%',
            min_value=-100,
            max_value=99.22,
            byte_length=1,
            scaling=100/128,
            offset=-100,
            data_type='int8'
        ),
        
        '010C': PIDDefinition(
            pid_code='010C',
            name='Engine RPM',
            description='Обороты двигателя',
            formula='(A*256 + B) / 4',
            unit='rpm',
            min_value=0,
            max_value=16383.75,
            byte_length=2,
            scaling=0.25,
            data_type='uint16'
        ),
        
        '010D': PIDDefinition(
            pid_code='010D',
            name='Vehicle speed',
            description='Скорость автомобиля',
            formula='A',
            unit='km/h',
            min_value=0,
            max_value=255,
            byte_length=1,
            data_type='uint8'
        ),
        
        '010F': PIDDefinition(
            pid_code='010F',
            name='Intake air temperature',
            description='Температура всасываемого воздуха',
            formula='A - 40',
            unit='°C',
            min_value=-40,
            max_value=215,
            byte_length=1,
            offset=-40,
            data_type='int8'
        ),
        
        '0110': PIDDefinition(
            pid_code='0110',
            name='MAF air flow rate',
            description='Массовый расход воздуха',
            formula='(A*256 + B) / 100',
            unit='g/s',
            min_value=0,
            max_value=655.35,
            byte_length=2,
            scaling=0.01,
            data_type='uint16'
        ),
        
        '0111': PIDDefinition(
            pid_code='0111',
            name='Throttle position',
            description='Положение дроссельной заслонки',
            formula='A * 100 / 255',
            unit='%',
            min_value=0,
            max_value=100,
            byte_length=1,
            scaling=100/255,
            data_type='uint8'
        ),
        
        '0113': PIDDefinition(
            pid_code='0113',
            name='Oxygen sensors present',
            description='Присутствующие датчики кислорода',
            formula='Битовая маска',
            unit='bits',
            min_value=0,
            max_value=255,
            byte_length=1,
            data_type='bits'
        ),
        
        '0114': PIDDefinition(
            pid_code='0114',
            name='Oxygen Sensor 1',
            description='Датчик кислорода 1, банк 1',
            formula='A * 0.005',
            unit='V',
            min_value=0,
            max_value=1.275,
            byte_length=1,
            scaling=0.005,
            data_type='uint8'
        ),
        
        '0115': PIDDefinition(
            pid_code='0115',
            name='Oxygen Sensor 2',
            description='Датчик кислорода 2, банк 1',
            formula='A * 0.005',
            unit='V',
            min_value=0,
            max_value=1.275,
            byte_length=1,
            scaling=0.005,
            data_type='uint8'
        ),
        
        '011C': PIDDefinition(
            pid_code='011C',
            name='OBD standards this vehicle conforms to',
            description='Стандарт OBD',
            formula='A',
            unit='',
            min_value=1,
            max_value=7,
            byte_length=1,
            data_type='uint8'
        ),
        
        '011F': PIDDefinition(
            pid_code='011F',
            name='Run time since engine start',
            description='Время работы с момента запуска двигателя',
            formula='A*256 + B',
            unit='seconds',
            min_value=0,
            max_value=65535,
            byte_length=2,
            data_type='uint16'
        ),
        
        '0121': PIDDefinition(
            pid_code='0121',
            name='Distance traveled with MIL on',
            description='Расстояние, пройденное с горящей лампой Check Engine',
            formula='A*256 + B',
            unit='km',
            min_value=0,
            max_value=65535,
            byte_length=2,
            data_type='uint16'
        ),
        
        '012F': PIDDefinition(
            pid_code='012F',
            name='Fuel level input',
            description='Уровень топлива',
            formula='A * 100 / 255',
            unit='%',
            min_value=0,
            max_value=100,
            byte_length=1,
            scaling=100/255,
            data_type='uint8'
        ),
        
        '0131': PIDDefinition(
            pid_code='0131',
            name='Distance traveled since codes cleared',
            description='Расстояние с момента очистки кодов',
            formula='A*256 + B',
            unit='km',
            min_value=0,
            max_value=65535,
            byte_length=2,
            data_type='uint16'
        ),
        
        '0133': PIDDefinition(
            pid_code='0133',
            name='Barometric pressure',
            description='Атмосферное давление',
            formula='A',
            unit='kPa',
            min_value=0,
            max_value=255,
            byte_length=1,
            data_type='uint8'
        ),
        
        '0142': PIDDefinition(
            pid_code='0142',
            name='Control module voltage',
            description='Напряжение питания ЭБУ',
            formula='(A*256 + B) / 1000',
            unit='V',
            min_value=0,
            max_value=65.535,
            byte_length=2,
            scaling=0.001,
            data_type='uint16'
        ),
        
        '0143': PIDDefinition(
            pid_code='0143',
            name='Absolute load value',
            description='Абсолютная нагрузка',
            formula='(A*256 + B) * 100 / 255',
            unit='%',
            min_value=0,
            max_value=25700,
            byte_length=2,
            scaling=100/255,
            data_type='uint16'
        ),
        
        '0145': PIDDefinition(
            pid_code='0145',
            name='Relative throttle position',
            description='Относительное положение дроссельной заслонки',
            formula='A * 100 / 255',
            unit='%',
            min_value=0,
            max_value=100,
            byte_length=1,
            scaling=100/255,
            data_type='uint8'
        ),
        
        '0146': PIDDefinition(
            pid_code='0146',
            name='Ambient air temperature',
            description='Температура окружающего воздуха',
            formula='A - 40',
            unit='°C',
            min_value=-40,
            max_value=215,
            byte_length=1,
            offset=-40,
            data_type='int8'
        ),
        
        '0149': PIDDefinition(
            pid_code='0149',
            name='Accelerator pedal position D',
            description='Положение педали акселератора D',
            formula='A * 100 / 255',
            unit='%',
            min_value=0,
            max_value=100,
            byte_length=1,
            scaling=100/255,
            data_type='uint8'
        ),
        
        '014A': PIDDefinition(
            pid_code='014A',
            name='Accelerator pedal position E',
            description='Положение педали акселератора E',
            formula='A * 100 / 255',
            unit='%',
            min_value=0,
            max_value=100,
            byte_length=1,
            scaling=100/255,
            data_type='uint8'
        ),
        
        '014C': PIDDefinition(
            pid_code='014C',
            name='Commanded throttle actuator',
            description='Заданное положение дроссельной заслонки',
            formula='A * 100 / 255',
            unit='%',
            min_value=0,
            max_value=100,
            byte_length=1,
            scaling=100/255,
            data_type='uint8'
        ),
    }
    
    # Расширенные PID для двигателя (специфичные для Нивы)
    ENGINE_EXTENDED_PIDS: Dict[str, PIDDefinition] = {
        '2001': PIDDefinition(
            pid_code='2001',
            name='Ignition timing advance',
            description='Угол опережения зажигания',
            formula='(A - 128) / 2',
            unit='°',
            min_value=-64,
            max_value=63.5,
            byte_length=1,
            scaling=0.5,
            offset=-64,
            data_type='int8'
        ),
        
        '2002': PIDDefinition(
            pid_code='2002',
            name='Injection time',
            description='Время впрыска',
            formula='(A*256 + B) / 1000',
            unit='ms',
            min_value=0,
            max_value=65.535,
            byte_length=2,
            scaling=0.001,
            data_type='uint16'
        ),
        
        '2003': PIDDefinition(
            pid_code='2003',
            name='Fuel pressure',
            description='Давление топлива',
            formula='A * 3',
            unit='kPa',
            min_value=0,
            max_value=765,
            byte_length=1,
            scaling=3,
            data_type='uint8'
        ),
        
        '2004': PIDDefinition(
            pid_code='2004',
            name='Intake manifold pressure',
            description='Давление во впускном коллекторе',
            formula='A',
            unit='kPa',
            min_value=0,
            max_value=255,
            byte_length=1,
            data_type='uint8'
        ),
        
        '2005': PIDDefinition(
            pid_code='2005',
            name='Camshaft position',
            description='Положение распредвала',
            formula='A',
            unit='°',
            min_value=0,
            max_value=255,
            byte_length=1,
            data_type='uint8'
        ),
        
        '2006': PIDDefinition(
            pid_code='2006',
            name='Crankshaft position',
            description='Положение коленвала',
            formula='A',
            unit='°',
            min_value=0,
            max_value=255,
            byte_length=1,
            data_type='uint8'
        ),
        
        '2007': PIDDefinition(
            pid_code='2007',
            name='Knock sensor signal',
            description='Сигнал датчика детонации',
            formula='A / 2',
            unit='V',
            min_value=0,
            max_value=12.75,
            byte_length=1,
            scaling=0.5,
            data_type='uint8'
        ),
        
        '2008': PIDDefinition(
            pid_code='2008',
            name='Lambda correction',
            description='Коррекция лямбда-зонда',
            formula='(A - 128) * 100 / 128',
            unit='%',
            min_value=-100,
            max_value=99.22,
            byte_length=1,
            scaling=100/128,
            offset=-100,
            data_type='int8'
        ),
        
        '2009': PIDDefinition(
            pid_code='2009',
            name='Idle air control position',
            description='Положение регулятора холостого хода',
            formula='A',
            unit='steps',
            min_value=0,
            max_value=255,
            byte_length=1,
            data_type='uint8'
        ),
        
        '2010': PIDDefinition(
            pid_code='2010',
            name='Fuel pump duty cycle',
            description='Рабочий цикл топливного насоса',
            formula='A * 100 / 255',
            unit='%',
            min_value=0,
            max_value=100,
            byte_length=1,
            scaling=100/255,
            data_type='uint8'
        ),
        
        '2011': PIDDefinition(
            pid_code='2011',
            name='Battery voltage',
            description='Напряжение аккумулятора',
            formula='A / 10',
            unit='V',
            min_value=0,
            max_value=25.5,
            byte_length=1,
            scaling=0.1,
            data_type='uint8'
        ),
        
        '2012': PIDDefinition(
            pid_code='2012',
            name='Coolant fan status',
            description='Состояние вентилятора охлаждения',
            formula='A',
            unit='',
            min_value=0,
            max_value=3,
            byte_length=1,
            data_type='uint8'
        ),
        
        '2013': PIDDefinition(
            pid_code='2013',
            name='A/C compressor status',
            description='Состояние компрессора кондиционера',
            formula='A',
            unit='',
            min_value=0,
            max_value=1,
            byte_length=1,
            data_type='bool'
        ),
        
        '2014': PIDDefinition(
            pid_code='2014',
            name='Purge valve duty cycle',
            description='Рабочий цикл клапана продувки',
            formula='A * 100 / 255',
            unit='%',
            min_value=0,
            max_value=100,
            byte_length=1,
            scaling=100/255,
            data_type='uint8'
        ),
        
        '2015': PIDDefinition(
            pid_code='2015',
            name='EGR valve position',
            description='Положение клапана EGR',
            formula='A * 100 / 255',
            unit='%',
            min_value=0,
            max_value=100,
            byte_length=1,
            scaling=100/255,
            data_type='uint8'
        ),
    }
    
    # PID для ABS
    ABS_PIDS: Dict[str, PIDDefinition] = {
        '3001': PIDDefinition(
            pid_code='3001',
            name='ABS system status',
            description='Статус системы ABS',
            formula='A',
            unit='',
            min_value=0,
            max_value=255,
            byte_length=1,
            data_type='bits'
        ),
        
        '3002': PIDDefinition(
            pid_code='3002',
            name='Wheel speed FL',
            description='Скорость вращения колеса перед левое',
            formula='A',
            unit='km/h',
            min_value=0,
            max_value=255,
            byte_length=1,
            data_type='uint8'
        ),
        
        '3003': PIDDefinition(
            pid_code='3003',
            name='Wheel speed FR',
            description='Скорость вращения колеса перед правое',
            formula='A',
            unit='km/h',
            min_value=0,
            max_value=255,
            byte_length=1,
            data_type='uint8'
        ),
        
        '3004': PIDDefinition(
            pid_code='3004',
            name='Wheel speed RL',
            description='Скорость вращения колеса заднее левое',
            formula='A',
            unit='km/h',
            min_value=0,
            max_value=255,
            byte_length=1,
            data_type='uint8'
        ),
        
        '3005': PIDDefinition(
            pid_code='3005',
            name='Wheel speed RR',
            description='Скорость вращения колеса заднее правое',
            formula='A',
            unit='km/h',
            min_value=0,
            max_value=255,
            byte_length=1,
            data_type='uint8'
        ),
        
        '3006': PIDDefinition(
            pid_code='3006',
            name='ABS pump status',
            description='Состояние насоса ABS',
            formula='A',
            unit='',
            min_value=0,
            max_value=1,
            byte_length=1,
            data_type='bool'
        ),
        
        '3007': PIDDefinition(
            pid_code='3007',
            name='ABS solenoid status',
            description='Состояние соленоидов ABS',
            formula='A',
            unit='',
            min_value=0,
            max_value=15,
            byte_length=1,
            data_type='bits'
        ),
    }
    
    # PID для приборной панели
    INSTRUMENT_PIDS: Dict[str, PIDDefinition] = {
        '4001': PIDDefinition(
            pid_code='4001',
            name='Total vehicle distance',
            description='Общий пробег автомобиля',
            formula='A*16777216 + B*65536 + C*256 + D',
            unit='km',
            min_value=0,
            max_value=4294967295,
            byte_length=4,
            data_type='uint32'
        ),
        
        '4002': PIDDefinition(
            pid_code='4002',
            name='Fuel consumption',
            description='Расход топлива',
            formula='(A*256 + B) / 10',
            unit='L/100km',
            min_value=0,
            max_value=6553.5,
            byte_length=2,
            scaling=0.1,
            data_type='uint16'
        ),
        
        '4003': PIDDefinition(
            pid_code='4003',
            name='Average speed',
            description='Средняя скорость',
            formula='A',
            unit='km/h',
            min_value=0,
            max_value=255,
            byte_length=1,
            data_type='uint8'
        ),
        
        '4004': PIDDefinition(
            pid_code='4004',
            name='Trip distance',
            description='Пробег поездки',
            formula='(A*256 + B) / 10',
            unit='km',
            min_value=0,
            max_value=6553.5,
            byte_length=2,
            scaling=0.1,
            data_type='uint16'
        ),
        
        '4005': PIDDefinition(
            pid_code='4005',
            name='External temperature',
            description='Наружная температура',
            formula='A - 40',
            unit='°C',
            min_value=-40,
            max_value=215,
            byte_length=1,
            offset=-40,
            data_type='int8'
        ),
    }
    
    # =========================================================================
    # ОПРЕДЕЛЕНИЯ ДАТЧИКОВ
    # =========================================================================
    
    SENSORS: Dict[str, SensorDefinition] = {
        # Датчики двигателя
        'ENG_COOLANT_TEMP': SensorDefinition(
            sensor_id='ENG_COOLANT_TEMP',
            name='Датчик температуры охлаждающей жидкости',
            ecu=ECUAddress.ENGINE_ECU,
            pid='0105',
            normal_range=(-40, 110),
            critical_range=(115, 130),
            location='Головка блока цилиндров',
            replacement_part_number='2112-3851010'
        ),
        
        'ENG_INTAKE_TEMP': SensorDefinition(
            sensor_id='ENG_INTAKE_TEMP',
            name='Датчик температуры впускного воздуха',
            ecu=ECUAddress.ENGINE_ECU,
            pid='010F',
            normal_range=(-40, 80),
            critical_range=(90, 120),
            location='Впускной коллектор',
            replacement_part_number='2112-3851010-01'
        ),
        
        'ENG_THROTTLE_POS': SensorDefinition(
            sensor_id='ENG_THROTTLE_POS',
            name='Датчик положения дроссельной заслонки',
            ecu=ECUAddress.ENGINE_ECU,
            pid='0111',
            normal_range=(0, 100),
            critical_range=(0, 0),  # нет критического диапазона
            location='Дроссельный узел',
            replacement_part_number='2123-1148020'
        ),
        
        'ENG_MAP_SENSOR': SensorDefinition(
            sensor_id='ENG_MAP_SENSOR',
            name='Датчик абсолютного давления',
            ecu=ECUAddress.ENGINE_ECU,
            pid='010B',
            normal_range=(20, 110),
            critical_range=(0, 5),  # вакуум или перегрузка
            location='Впускной коллектор',
            replacement_part_number='2112-1138610'
        ),
        
        'ENG_O2_SENSOR_B1S1': SensorDefinition(
            sensor_id='ENG_O2_SENSOR_B1S1',
            name='Лямбда-зонд 1',
            ecu=ECUAddress.ENGINE_ECU,
            pid='0114',
            normal_range=(0.1, 0.9),
            critical_range=(0, 0.05),  # обрыв или короткое замыкание
            location='Выпускной коллектор',
            replacement_part_number='2112-3850010'
        ),
        
        'ENG_O2_SENSOR_B1S2': SensorDefinition(
            sensor_id='ENG_O2_SENSOR_B1S2',
            name='Лямбда-зонд 2',
            ecu=ECUAddress.ENGINE_ECU,
            pid='0115',
            normal_range=(0.1, 0.9),
            critical_range=(0, 0.05),
            location='За катализатором',
            replacement_part_number='2112-3850010-01'
        ),
        
        'ENG_CRANKSHAFT_SENSOR': SensorDefinition(
            sensor_id='ENG_CRANKSHAFT_SENSOR',
            name='Датчик положения коленвала',
            ecu=ECUAddress.ENGINE_ECU,
            pid='2006',
            normal_range=(0, 255),
            critical_range=(0, 0),  # проверяется по наличию сигнала
            location='Крышка ГРМ',
            replacement_part_number='2112-3847010'
        ),
        
        'ENG_CAMSHAFT_SENSOR': SensorDefinition(
            sensor_id='ENG_CAMSHAFT_SENSOR',
            name='Датчик положения распредвала',
            ecu=ECUAddress.ENGINE_ECU,
            pid='2005',
            normal_range=(0, 255),
            critical_range=(0, 0),
            location='Головка блока цилиндров',
            replacement_part_number='2112-3706030'
        ),
        
        'ENG_KNOCK_SENSOR': SensorDefinition(
            sensor_id='ENG_KNOCK_SENSOR',
            name='Датчик детонации',
            ecu=ECUAddress.ENGINE_ECU,
            pid='2007',
            normal_range=(0, 5),
            critical_range=(8, 12),
            location='Блок цилиндров',
            replacement_part_number='2112-3855020'
        ),
        
        # Датчики ABS
        'ABS_WHEEL_SPEED_FL': SensorDefinition(
            sensor_id='ABS_WHEEL_SPEED_FL',
            name='Датчик скорости колеса перед левое',
            ecu=ECUAddress.ABS_ECU,
            pid='3002',
            normal_range=(0, 200),
            critical_range=(0, 0),  # проверяется согласованность
            location='Ступица переднего колеса',
            replacement_part_number='2123-3837010'
        ),
        
        'ABS_WHEEL_SPEED_FR': SensorDefinition(
            sensor_id='ABS_WHEEL_SPEED_FR',
            name='Датчик скорости колеса перед правое',
            ecu=ECUAddress.ABS_ECU,
            pid='3003',
            normal_range=(0, 200),
            critical_range=(0, 0),
            location='Ступица переднего колеса',
            replacement_part_number='2123-3837010'
        ),
        
        'ABS_WHEEL_SPEED_RL': SensorDefinition(
            sensor_id='ABS_WHEEL_SPEED_RL',
            name='Датчик скорости колеса заднее левое',
            ecu=ECUAddress.ABS_ECU,
            pid='3004',
            normal_range=(0, 200),
            critical_range=(0, 0),
            location='Ступица заднего колеса',
            replacement_part_number='2123-3838010'
        ),
        
        'ABS_WHEEL_SPEED_RR': SensorDefinition(
            sensor_id='ABS_WHEEL_SPEED_RR',
            name='Датчик скорости колеса заднее правое',
            ecu=ECUAddress.ABS_ECU,
            pid='3005',
            normal_range=(0, 200),
            critical_range=(0, 0),
            location='Ступица заднего колеса',
            replacement_part_number='2123-3838010'
        ),
    }
    
    # =========================================================================
    # ПАРАМЕТРЫ АДАПТАЦИИ
    # =========================================================================
    
    ADAPTATION_PARAMETERS: Dict[str, AdaptationParameter] = {
        # Адаптация двигателя
        'ADAPT_IDLE_SPEED': AdaptationParameter(
            param_id='ADAPT_IDLE_SPEED',
            name='Обороты холостого хода',
            description='Настройка оборотов холостого хода',
            address=(0x1234, 1),
            min_value=700,
            max_value=900,
            default_value=800,
            step=10,
            requires_ignition=True,
            requires_engine_off=False
        ),
        
        'ADAPT_THROTTLE_VALVE': AdaptationParameter(
            param_id='ADAPT_THROTTLE_VALVE',
            name='Адаптация дроссельной заслонки',
            description='Обучение крайних положений дроссельной заслонки',
            address=(0x1235, 2),
            min_value=0,
            max_value=100,
            default_value=50,
            step=1,
            requires_ignition=True,
            requires_engine_off=True
        ),
        
        'ADAPT_FUEL_TRIM': AdaptationParameter(
            param_id='ADAPT_FUEL_TRIM',
            name='Коррекция топливоподачи',
            description='Сброс долгосрочной коррекции топливоподачи',
            address=(0x1236, 1),
            min_value=-25,
            max_value=25,
            default_value=0,
            step=1,
            requires_ignition=True,
            requires_engine_off=False
        ),
        
        'ADAPT_O2_SENSOR': AdaptationParameter(
            param_id='ADAPT_O2_SENSOR',
            name='Адаптация лямбда-зонда',
            description='Обучение лямбда-зонда',
            address=(0x1237, 2),
            min_value=0,
            max_value=255,
            default_value=128,
            step=1,
            requires_ignition=True,
            requires_engine_off=False
        ),
        
        'ADAPT_IDLE_AIR': AdaptationParameter(
            param_id='ADAPT_IDLE_AIR',
            name='Регулятор холостого хода',
            description='Обучение регулятора холостого хода',
            address=(0x1238, 1),
            min_value=0,
            max_value=255,
            default_value=120,
            step=1,
            requires_ignition=True,
            requires_engine_off=True
        ),
        
        'ADAPT_KNOCK_SENSOR': AdaptationParameter(
            param_id='ADAPT_KNOCK_SENSOR',
            name='Адаптация датчика детонации',
            description='Калибровка датчика детонации',
            address=(0x1239, 1),
            min_value=0,
            max_value=100,
            default_value=50,
            step=1,
            requires_ignition=True,
            requires_engine_off=False
        ),
        
        # Адаптация иммобилайзера
        'ADAPT_IMMO_LEARN': AdaptationParameter(
            param_id='ADAPT_IMMO_LEARN',
            name='Обучение иммобилайзера',
            description='Обучение новых ключей',
            address=(0x2001, 4),
            min_value=0,
            max_value=255,
            default_value=0,
            step=1,
            requires_ignition=True,
            requires_engine_off=True
        ),
        
        'ADAPT_IMMO_PIN': AdaptationParameter(
            param_id='ADAPT_IMMO_PIN',
            name='ПИН-код иммобилайзера',
            description='Изменение ПИН-кода иммобилайзера',
            address=(0x2002, 4),
            min_value=0,
            max_value=9999,
            default_value=0,
            step=1,
            requires_ignition=True,
            requires_engine_off=True
        ),
        
        # Адаптация АКПП (если есть)
        'ADAPT_TRANS_SHIFT': AdaptationParameter(
            param_id='ADAPT_TRANS_SHIFT',
            name='Адаптация переключений АКПП',
            description='Обучение точек переключения передач',
            address=(0x3001, 2),
            min_value=0,
            max_value=255,
            default_value=128,
            step=1,
            requires_ignition=True,
            requires_engine_off=False
        ),
    }
    
    # =========================================================================
    # КОМАНДЫ ДИАГНОСТИКИ
    # =========================================================================
    
    # Базовые AT-команды ELM327
    AT_COMMANDS = {
        'RESET': 'ATZ',
        'ECHO_OFF': 'ATE0',
        'ECHO_ON': 'ATE1',
        'LINE_FEEDS_OFF': 'ATL0',
        'LINE_FEEDS_ON': 'ATL1',
        'SPACES_OFF': 'ATS0',
        'SPACES_ON': 'ATS1',
        'HEADERS_OFF': 'ATH0',
        'HEADERS_ON': 'ATH1',
        'MEMORY_OFF': 'AT@1',
        'MEMORY_ON': 'AT@2',
        'PROTOCOL_AUTO': 'ATSP0',
        'PROTOCOL_ISO_9141': 'ATSP3',
        'PROTOCOL_ISO_14230': 'ATSP4',
        'PROTOCOL_ISO_15765': 'ATSP6',
        'VOLTAGE': 'ATRV',
        'DESCRIBE_PROTOCOL': 'ATDP',
        'DEVICE_DESCRIPTION': 'AT@1',
        'READ_VERSION': 'ATI',
        'WARM_START': 'ATWS',
        'LOW_POWER_MODE': 'ATLP',
        'SET_TIMEOUT': 'ATST',
        'SET_BAUDRATE': 'ATBRD',
        'SET_CAN_BAUDRATE': 'ATCRA',
        'SET_CAN_ID': 'ATCF',
        'SET_FILTER': 'ATCF',
        'SET_MASK': 'ATCM',
        'MONITOR_ALL': 'ATMA',
        'MONITOR_OFF': 'ATPC',
    }
    
    # Команды адаптации (специфичные для Нивы)
    ADAPTATION_COMMANDS = {
        'IDLE_ADAPTATION': {
            'command': '28 10 10',
            'description': 'Адаптация холостого хода',
            'procedure': [
                'Двигатель прогрет до рабочей температуры',
                'Электрические потребители выключены',
                'Запустить процедуру',
                'Дождаться стабилизации оборотов',
                'Сохранить параметры'
            ]
        },
        
        'THROTTLE_ADAPTATION': {
            'command': '28 10 11',
            'description': 'Адаптация дроссельной заслонки',
            'procedure': [
                'Зажигание ВКЛ, двигатель ВЫКЛ',
                'Выполнить процедуру',
                'Дождаться звуковых сигналов ЭБУ',
                'Выключить зажигание на 10 секунд'
            ]
        },
        
        'IMMO_LEARN': {
            'command': '29 10 01',
            'description': 'Обучение ключей иммобилайзера',
            'procedure': [
                'Иметь мастер-ключ',
                'Вставить мастер-ключ, включить зажигание',
                'Выключить зажигание, вынуть ключ',
                'Вставить новый ключ в течение 10 секунд',
                'Включить зажигание, подождать 5 секунд'
            ]
        },
        
        'ABS_ADAPTATION': {
            'command': '28 10 20',
            'description': 'Адаптация датчиков ABS',
            'procedure': [
                'Двигатель запущен',
                'Автомобиль на ровной поверхности',
                'Выполнить процедуру калибровки',
                'Проехать 20-30 метров для завершения'
            ]
        },
        
        'FUEL_TRIM_RESET': {
            'command': '01 04',
            'description': 'Сброс коррекций топливоподачи',
            'procedure': [
                'Двигатель прогрет',
                'Обороты холостого хода',
                'Выполнить сброс',
                'Дать двигателю поработать 5 минут'
            ]
        },
    }
    
    # =========================================================================
    # МЕТОДЫ РАБОТЫ С ПРОТОКОЛАМИ
    # =========================================================================
    
    @staticmethod
    def build_command(
        mode: DiagnosticMode,
        pid: str = "",
        ecu: ECUAddress = None,
        data: bytes = b"",
        is_can: bool = False
    ) -> str:
        """
        Построение команды диагностики
        
        Args:
            mode: Режим диагностики
            pid: Идентификатор параметра
            ecu: Адрес ЭБУ (опционально)
            data: Дополнительные данные
            is_can: Флаг CAN-шины
        
        Returns:
            Строка команды
        """
        if ecu is not None:
            # Команда с указанием адреса ЭБУ
            ecu_hex = f"{ecu.value:02X}"
            mode_hex = f"{mode.value:02X}"
            
            if is_can:
                # CAN формат
                return f"{ecu_hex}{mode_hex}{pid}" + (data.hex().upper() if data else "")
            else:
                # K-line формат
                return f"{ecu_hex}{mode_hex}{pid}" + (data.hex().upper() if data else "")
        else:
            # Стандартная OBD команда
            return f"{mode.value:02X}{pid}" + (data.hex().upper() if data else "")
    
    @staticmethod
    def parse_response(
        response: str,
        pid: str,
        pid_def: PIDDefinition = None
    ) -> Union[float, int, str, Dict[str, Any], None]:
        """
        Парсинг ответа от ЭБУ
        
        Args:
            response: Сырой ответ от ЭБУ
            pid: PID для парсинга
            pid_def: Определение PID (опционально)
        
        Returns:
            Распарсенное значение или None при ошибке
        """
        if not response or "NO DATA" in response or "ERROR" in response:
            return None
        
        # Очистка ответа
        clean_response = response.strip().replace(" ", "").replace("\r", "").replace("\n", "")
        
        if len(clean_response) < 4:
            return None
        
        # Определяем PID definition
        if pid_def is None:
            pid_def = NivaProtocols._get_pid_definition(pid)
            if pid_def is None:
                # Если не нашли определение, возвращаем сырые данные
                return {"raw": clean_response, "hex": clean_response}
        
        # Извлекаем данные (пропускаем заголовок и длину)
        data_start = 4
        if len(clean_response) > 4:
            # Пытаемся определить длину данных
            try:
                data_length = int(clean_response[2:4], 16)
                data_part = clean_response[4:4+data_length*2]
            except:
                data_part = clean_response[4:]
        else:
            data_part = clean_response[4:]
        
        if not data_part:
            return None
        
        # Парсинг в соответствии с типом данных
        try:
            if pid_def.data_type == "uint8":
                value = int(data_part[:2], 16)
                result = value * pid_def.scaling + pid_def.offset
                
            elif pid_def.data_type == "uint16":
                value = int(data_part[:4], 16)
                result = value * pid_def.scaling + pid_def.offset
                
            elif pid_def.data_type == "uint32":
                value = int(data_part[:8], 16)
                result = value * pid_def.scaling + pid_def.offset
                
            elif pid_def.data_type == "int8":
                value = int(data_part[:2], 16)
                if value > 127:
                    value = value - 256
                result = value * pid_def.scaling + pid_def.offset
                
            elif pid_def.data_type == "int16":
                value = int(data_part[:4], 16)
                if value > 32767:
                    value = value - 65536
                result = value * pid_def.scaling + pid_def.offset
                
            elif pid_def.data_type == "bits":
                # Битовая маска
                value = int(data_part[:2], 16)
                result = {
                    "value": value,
                    "binary": bin(value)[2:].zfill(8),
                    "bits": []
                }
                
            elif pid_def.data_type == "bool":
                value = int(data_part[:2], 16)
                result = bool(value)
                
            else:
                # Неизвестный тип - возвращаем raw
                result = {
                    "raw": data_part,
                    "hex": data_part,
                    "dec": int(data_part, 16) if data_part else 0
                }
            
            return {
                "value": result,
                "unit": pid_def.unit,
                "min": pid_def.min_value,
                "max": pid_def.max_value,
                "normal_range": pid_def.min_value <= result <= pid_def.max_value,
                "raw": clean_response,
                "pid_def": pid_def.name
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "raw": clean_response,
                "pid": pid
            }
    
    @staticmethod
    def decode_dtc(dtc_bytes: str) -> Dict[str, Any]:
        """
        Декодирование DTC из байтов
        
        Args:
            dtc_bytes: 2 байта DTC в hex (например, "0123")
        
        Returns:
            Словарь с расшифровкой DTC
        """
        if len(dtc_bytes) != 4:
            return {"error": "Неверная длина DTC"}
        
        try:
            first_byte = int(dtc_bytes[0:2], 16)
            second_byte = int(dtc_bytes[2:4], 16)
            
            # Определение типа системы
            system_type = (first_byte >> 6) & 0x03
            
            system_types = {
                0: {"code": "P", "name": "Powertrain", "description": "Трансмиссия"},
                1: {"code": "C", "name": "Chassis", "description": "Шасси"},
                2: {"code": "B", "name": "Body", "description": "Кузов"},
                3: {"code": "U", "name": "Network", "description": "Сеть"}
            }
            
            system_info = system_types.get(system_type, {"code": "U", "name": "Unknown", "description": "Неизвестно"})
            
            # Определение кода неисправности
            digit1 = str((first_byte >> 4) & 0x03)
            digit2 = str(first_byte & 0x0F)
            digit3 = str((second_byte >> 4) & 0x0F)
            digit4 = str(second_byte & 0x0F)
            
            dtc_code = f"{system_info['code']}{digit1}{digit2}{digit3}{digit4}"
            
            return {
                "dtc_code": dtc_code,
                "system_code": system_info["code"],
                "system_name": system_info["name"],
                "system_description": system_info["description"],
                "bytes": dtc_bytes,
                "first_byte": first_byte,
                "second_byte": second_byte
            }
            
        except Exception as e:
            return {"error": f"Ошибка декодирования DTC: {str(e)}", "bytes": dtc_bytes}
    
    @staticmethod
    def get_pids_for_ecu(ecu: ECUAddress) -> Dict[str, PIDDefinition]:
        """
        Получение PID для конкретного ЭБУ
        
        Args:
            ecu: Адрес ЭБУ
        
        Returns:
            Словарь PID для ЭБУ
        """
        if ecu == ECUAddress.ENGINE_ECU:
            return {**NivaProtocols.BASE_PIDS, **NivaProtocols.ENGINE_EXTENDED_PIDS}
        elif ecu == ECUAddress.ABS_ECU:
            return NivaProtocols.ABS_PIDS
        elif ecu == ECUAddress.INSTRUMENT_CLUSTER:
            return NivaProtocols.INSTRUMENT_PIDS
        else:
            return NivaProtocols.BASE_PIDS
    
    @staticmethod
    def get_sensor_info(sensor_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение информации о датчике
        
        Args:
            sensor_id: Идентификатор датчика
        
        Returns:
            Информация о датчике или None
        """
        if sensor_id in NivaProtocols.SENSORS:
            sensor = NivaProtocols.SENSORS[sensor_id]
            pid_def = NivaProtocols._get_pid_definition(sensor.pid)
            
            return {
                "id": sensor.sensor_id,
                "name": sensor.name,
                "ecu": sensor.ecu.name,
                "pid": sensor.pid,
                "normal_range": sensor.normal_range,
                "critical_range": sensor.critical_range,
                "location": sensor.location,
                "part_number": sensor.replacement_part_number,
                "pid_info": pid_def.name if pid_def else "Unknown"
            }
        
        return None
    
    @staticmethod
    def perform_adaptation_procedure(
        adaptation_id: str,
        vehicle_model: str,
        current_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Выполнение процедуры адаптации
        
        Args:
            adaptation_id: Идентификатор адаптации
            vehicle_model: Модель автомобиля
            current_params: Текущие параметры
        
        Returns:
            Результат адаптации
        """
        if adaptation_id not in NivaProtocols.ADAPTATION_COMMANDS:
            return {"error": f"Неизвестная процедура адаптации: {adaptation_id}"}
        
        adaptation = NivaProtocols.ADAPTATION_COMMANDS[adaptation_id]
        
        # Проверка предварительных условий
        if adaptation_id == "THROTTLE_ADAPTATION":
            if current_params.get("engine_running", False):
                return {"error": "Двигатель должен быть выключен для адаптации дросселя"}
            
            if current_params.get("coolant_temp", 0) < 20:
                return {"warning": "Рекомендуется выполнять при температуре двигателя >20°C"}
        
        # Формирование команды
        command = adaptation["command"]
        
        return {
            "adaptation_id": adaptation_id,
            "name": adaptation["description"],
            "command": command,
            "procedure": adaptation["procedure"],
            "estimated_time": "1-2 минуты",
            "requirements": {
                "ignition_on": True,
                "engine_off": adaptation_id in ["THROTTLE_ADAPTATION", "IMMO_LEARN"],
                "parking_brake": True
            }
        }
    
    # =========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================================
    
    @staticmethod
    def _get_pid_definition(pid: str) -> Optional[PIDDefinition]:
        """
        Получение определения PID по коду
        
        Args:
            pid: Код PID
        
        Returns:
            Определение PID или None
        """
        # Ищем во всех словарях PID
        all_pids = {
            **NivaProtocols.BASE_PIDS,
            **NivaProtocols.ENGINE_EXTENDED_PIDS,
            **NivaProtocols.ABS_PIDS,
            **NivaProtocols.INSTRUMENT_PIDS
        }
        
        return all_pids.get(pid)
    
    @staticmethod
    def get_vehicle_info_by_vin(vin: str) -> Optional[Dict[str, Any]]:
        """
        Получение информации об автомобиле по VIN
        
        Args:
            vin: VIN номер
        
        Returns:
            Информация об автомобиле или None
        """
        # Примеры VIN для разных моделей
        vin_patterns = {
            "XTA212300": "2123",      # Chevrolet Niva 1.7i 8V
            "XTA212360": "21236",     # Chevrolet Niva 1.7i 16V
            "XTA212350": "2123-250",  # Chevrolet Niva 1.8i
            "XTA2123M0": "2123M",     # Chevrolet Niva Модерн
            "XTA212360": "2123-60",   # LADA Niva Travel
        }
        
        for pattern, model_code in vin_patterns.items():
            if vin.startswith(pattern):
                model = NivaProtocols.VEHICLE_MODELS[model_code]
                return {
                    "vin": vin,
                    "model_code": model.code,
                    "model_name": model.name,
                    "production_years": model.production_years,
                    "engine_type": model.engine_type,
                    "protocol": model.protocol.value
                }
        
        return None
    
    @staticmethod
    def calculate_checksum(data: bytes) -> int:
        """
        Расчет контрольной суммы для команды
        
        Args:
            data: Данные для расчета
        
        Returns:
            Контрольная сумма
        """
        checksum = 0
        for byte in data:
            checksum += byte
        return checksum & 0xFF
    
    @staticmethod
    def create_can_message(
        ecu_id: int,
        data: bytes,
        can_format: str = "standard"
    ) -> bytes:
        """
        Создание CAN сообщения
        
        Args:
            ecu_id: Идентификатор ECU
            data: Данные
            can_format: Формат CAN (standard/extended)
        
        Returns:
            CAN сообщение
        """
        if can_format == "extended":
            # 29-битный идентификатор
            id_bytes = ecu_id.to_bytes(4, byteorder='big')
        else:
            # 11-битный идентификатор
            id_bytes = ecu_id.to_bytes(2, byteorder='big')
        
        length = len(data)
        return id_bytes + bytes([length]) + data
    
    @staticmethod
    def get_supported_pids(ecu_response: str, mode: int = 1) -> List[str]:
        """
        Получение списка поддерживаемых PID из ответа ЭБУ
        
        Args:
            ecu_response: Ответ от ЭБУ
            mode: Режим диагностики
        
        Returns:
            Список поддерживаемых PID
        """
        if not ecu_response or len(ecu_response) < 8:
            return []
        
        try:
            # Извлекаем битовую маску
            data_part = ecu_response[4:]  # Пропускаем заголовок
            if len(data_part) < 8:
                return []
            
            # Первые 4 байта - битовая маска поддерживаемых PID
            mask_bytes = data_part[:8]
            mask = int(mask_bytes, 16)
            
            supported_pids = []
            
            # Проверяем биты (PID от 01 до 20 для mode 01)
            for i in range(32):
                if mask & (1 << (31 - i)):
                    pid_num = i + 1
                    pid_hex = f"{pid_num:02X}"
                    
                    # Формируем полный PID код
                    if mode == 1:
                        full_pid = f"01{pid_hex}"
                    elif mode == 3:
                        full_pid = f"03{pid_hex}"
                    else:
                        full_pid = f"{mode:02X}{pid_hex}"
                    
                    supported_pids.append(full_pid)
            
            return supported_pids
            
        except Exception as e:
            print(f"Ошибка при парсинге поддерживаемых PID: {e}")
            return []
    
    # =========================================================================
    # МЕТОДЫ ДЛЯ КОНКРЕТНЫХ ПРОЦЕДУР ДИАГНОСТИКИ
    # =========================================================================
    
    @staticmethod
    def create_engine_test_sequence() -> List[Dict[str, Any]]:
        """
        Создание последовательности тестов двигателя
        """
        return [
            {
                "name": "Проверка связи с ЭБУ",
                "command": "0100",
                "expected": "Поддерживаемые PID",
                "timeout": 2
            },
            {
                "name": "Проверка датчика температуры ОЖ",
                "command": "0105",
                "expected": "20-110 °C",
                "timeout": 1
            },
            {
                "name": "Проверка датчика положения дросселя",
                "command": "0111",
                "expected": "0-100%",
                "timeout": 1
            },
            {
                "name": "Проверка ДПКВ",
                "command": "010C",
                "expected": "0-7000 об/мин",
                "timeout": 1
            },
            {
                "name": "Проверка ДПРВ",
                "command": "2005",
                "expected": "Сигнал присутствует",
                "timeout": 1
            },
            {
                "name": "Проверка лямбда-зонда",
                "command": "0114",
                "expected": "0.1-0.9 В",
                "timeout": 2
            },
            {
                "name": "Проверка датчика детонации",
                "command": "2007",
                "expected": "0-5 В",
                "timeout": 1
            },
            {
                "name": "Проверка регулятора ХХ",
                "command": "2009",
                "expected": "0-255 шагов",
                "timeout": 1
            },
            {
                "name": "Проверка напряжения",
                "command": "0142",
                "expected": "12-14.5 В",
                "timeout": 1
            }
        ]
    
    @staticmethod
    def create_abs_test_sequence() -> List[Dict[str, Any]]:
        """
        Создание последовательности тестов ABS
        """
        return [
            {
                "name": "Проверка связи с ABS",
                "command": "280100",
                "expected": "Ответ от ABS",
                "timeout": 2
            },
            {
                "name": "Проверка датчиков скорости",
                "command": "280302",
                "expected": "Скорость всех колес",
                "timeout": 2
            },
            {
                "name": "Проверка насоса ABS",
                "command": "280306",
                "expected": "Состояние насоса",
                "timeout": 1
            },
            {
                "name": "Проверка соленоидов",
                "command": "280307",
                "expected": "Состояние соленоидов",
                "timeout": 1
            },
            {
                "name": "Считывание ошибок ABS",
                "command": "2803",
                "expected": "Список DTC",
                "timeout": 2
            }
        ]
    
    @staticmethod
    def create_airbag_test_sequence() -> List[Dict[str, Any]]:
        """
        Создание последовательности тестов подушек безопасности
        """
        return [
            {
                "name": "Проверка связи с Airbag",
                "command": "150100",
                "expected": "Ответ от Airbag",
                "timeout": 2
            },
            {
                "name": "Проверка датчика удара",
                "command": "150201",
                "expected": "Состояние датчика",
                "timeout": 1
            },
            {
                "name": "Проверка подушек",
                "command": "150202",
                "expected": "Сопротивление подушек",
                "timeout": 1
            },
            {
                "name": "Считывание ошибок Airbag",
                "command": "1503",
                "expected": "Список DTC",
                "timeout": 2
            }
        ]
    
    @staticmethod
    def get_diagnostic_procedures() -> Dict[str, List[Dict[str, Any]]]:
        """
        Получение всех процедур диагностики
        """
        return {
            "engine": NivaProtocols.create_engine_test_sequence(),
            "abs": NivaProtocols.create_abs_test_sequence(),
            "airbag": NivaProtocols.create_airbag_test_sequence(),
            "immobilizer": [
                {
                    "name": "Проверка связи с иммобилайзером",
                    "command": "290100",
                    "expected": "Ответ от иммобилайзера",
                    "timeout": 2
                },
                {
                    "name": "Проверка ключей",
                    "command": "290201",
                    "expected": "Количество обученных ключей",
                    "timeout": 1
                }
            ],
            "instrument_cluster": [
                {
                    "name": "Проверка связи с приборной панелью",
                    "command": "250100",
                    "expected": "Ответ от приборной панели",
                    "timeout": 2
                },
                {
                    "name": "Проверка пробега",
                    "command": "250401",
                    "expected": "Значение пробега",
                    "timeout": 1
                }
            ]
        }
    
    # =========================================================================
    # КОНСТАНТЫ И СПРАВОЧНИКИ
    # =========================================================================
    
    # Коды состояний топливной системы
    FUEL_SYSTEM_STATUS = {
        0: "Неизвестно",
        1: "Открытый контур - недостаточно температуры",
        2: "Закрытый контур с использованием кислородного датчика",
        4: "Открытый контур из-за отказа двигателя",
        8: "Закрытый контур с неисправностью кислородного датчика"
    }
    
    # Коды стандартов OBD
    OBD_STANDARDS = {
        1: "OBD-II (CARB)",
        2: "OBD (EPA)",
        3: "OBD и OBD-II",
        4: "OBD-I",
        5: "EOBD",
        6: "EOBD и OBD-II",
        7: "EOBD и OBD"
    }
    
    # Расшифровка битового поля статуса мониторов
    MONITOR_STATUS_BITS = {
        "MIL": {"bit": 7, "description": "Лампа Check Engine"},
        "DTC_COUNT": {"bit": 6, "description": "Количество DTC"},
        "COMPREHENSIVE": {"bits": [4, 5], "description": "Комплексный монитор"},
        "FUEL_SYSTEM": {"bits": [2, 3], "description": "Топливная система"},
        "MISFIRE": {"bits": [0, 1], "description": "Пропуски зажигания"}
    }
    
    # Нормальные диапазоны параметров для Нивы
    NORMAL_RANGES = {
        "engine_rpm_idle": (750, 850),           # Обороты ХХ
        "engine_rpm_max": (6500, 7000),          # Максимальные обороты
        "coolant_temp_normal": (85, 105),        # Нормальная температура ОЖ
        "coolant_temp_warning": (110, 120),      # Предупреждение
        "coolant_temp_critical": (121, 130),     # Критическая
        "intake_temp_normal": (-20, 50),         # Температура впуска
        "throttle_idle": (0, 2),                 # Дроссель на ХХ
        "throttle_full": (85, 100),              # Дроссель полностью
        "maf_normal": (2, 10),                   # MAF на ХХ
        "fuel_pressure_normal": (300, 350),      # Давление топлива
        "battery_voltage_normal": (13.5, 14.5),  # Напряжение при работе
        "battery_voltage_off": (12.0, 12.8),     # Напряжение при выкл. двигателе
        "lambda_normal": (0.1, 0.9),             # Напряжение лямбда-зонда
        "fuel_level_empty": (0, 5),              # Пустой бак
        "fuel_level_full": (95, 100),            # Полный бак
    }
    
    # Время выполнения процедур (в секундах)
    PROCEDURE_TIMES = {
        "full_diagnostic": 180,
        "engine_diagnostic": 60,
        "abs_diagnostic": 30,
        "airbag_diagnostic": 30,
        "immobilizer_diagnostic": 20,
        "instrument_diagnostic": 15,
        "throttle_adaptation": 120,
        "idle_adaptation": 180,
        "immo_learn": 300,
        "abs_adaptation": 60
    }
    
    # Требования к условиям выполнения
    PROCEDURE_REQUIREMENTS = {
        "engine_running": ["engine_diagnostic", "idle_adaptation"],
        "engine_off": ["throttle_adaptation", "immo_learn", "airbag_diagnostic"],
        "parking_brake": ["abs_diagnostic", "abs_adaptation"],
        "coolant_temp_ok": ["idle_adaptation", "engine_diagnostic"],
        "battery_voltage_ok": ["all"],
        "no_dtc": ["adaptation_procedures"]
    }