"""
Модуль для работы с диагностическим сканером ELM327.
Полная версия с поддержкой Bluetooth, USB, WiFi и расширенными функциями.
"""

import time
import serial
#import bluetooth
import socket
import struct
from enum import Enum
from threading import Thread, Lock, Event
from queue import Queue, Empty
import re
import json
import os
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any, Callable, Union
import logging

# Настройка логгера
logger = logging.getLogger(__name__)

class ConnectionType(Enum):
    """Типы подключения"""
    BLUETOOTH = "bluetooth"
    USB = "usb"
    WIFI = "wifi"

class ELM327Error(Exception):
    """Базовое исключение для ошибок ELM327"""
    pass

class ConnectionError(ELM327Error):
    """Ошибка подключения"""
    pass

class ProtocolError(ELM327Error):
    """Ошибка протокола"""
    pass

class TimeoutError(ELM327Error):
    """Ошибка таймаута"""
    pass

class ELM327Connector:
    """
    Класс для управления подключением к адаптеру ELM327.
    Поддерживает Bluetooth, USB и WiFi подключения.
    """
    
    # Константы ELM327
    DEFAULT_BAUDRATES = [38400, 115200, 9600, 57600, 19200]
    ELM_PROMPT = ">"
    ELM_TIMEOUT = 2  # секунды
    MAX_RETRIES = 3
    
    # AT команды
    AT_COMMANDS = {
        'RESET': 'ATZ',
        'ECHO_OFF': 'ATE0',
        'ECHO_ON': 'ATE1',
        'HEADERS_ON': 'ATH1',
        'HEADERS_OFF': 'ATH0',
        'SPACES_ON': 'ATS1',
        'SPACES_OFF': 'ATS0',
        'LINEFEED_ON': 'ATL1',
        'LINEFEED_OFF': 'ATL0',
        'MEMORY_ON': 'ATM1',
        'MEMORY_OFF': 'ATM0',
        'SET_PROTOCOL': 'ATSP',
        'AUTO_PROTOCOL': 'ATSP0',
        'SET_HEADER': 'ATSH',
        'SET_BAUD': 'ATBRD',
        'DESCRIBE_PROTOCOL': 'ATDP',
        'DESCRIBE_PROTOCOL_N': 'ATDPN',
        'VERSION': 'ATI',
        'DEVICE_DESCRIPTION': 'AT@1',
        'DEVICE_ID': 'AT@2',
        'VOLTAGE': 'ATRV',
        'IGNITION_MONITOR': 'ATIGN',
        'WARM_START': 'ATWS',
        'LOW_POWER': 'ATLP',
        'DEFAULT_SETTINGS': 'ATD',
        'READ_ADAPTIVE': 'ATRA',
        'SET_TIMEOUT': 'ATST',
        'ADAPTIVE_TIMING': 'ATAT',
        'FLOW_CONTROL': 'ATFC',
        'CAN_EXTENDED': 'ATCEA',
        'CAN_DUAL_FILTER': 'ATCRA',
        'CAN_FILTER': 'ATCF',
        'CAN_MASK': 'ATCM'
    }
    
    # Протоколы OBD-II
    PROTOCOLS = {
        0: "AUTO",
        1: "SAE J1850 PWM",
        2: "SAE J1850 VPW",
        3: "ISO 9141-2",
        4: "ISO 14230-4 KWP (5 baud init)",
        5: "ISO 14230-4 KWP (fast init)",
        6: "ISO 15765-4 CAN (11 bit ID, 500 kbaud)",
        7: "ISO 15765-4 CAN (29 bit ID, 500 kbaud)",
        8: "ISO 15765-4 CAN (11 bit ID, 250 kbaud)",
        9: "ISO 15765-4 CAN (29 bit ID, 250 kbaud)",
        10: "SAE J1939 CAN (29 bit ID, 250* kbaud)",
        11: "USER1 CAN (11* bit ID, 125* kbaud)",
        12: "USER2 CAN (11* bit ID, 50* kbaud)"
    }
    
    def __init__(self, config_manager=None):
        """
        Инициализация подключения ELM327.
        
        Args:
            config_manager: Менеджер конфигурации
        """
        self.config = config_manager
        self.connection = None
        self.connection_type = None
        self.port = None
        self.address = None
        self.baudrate = 38400
        self.protocol = "AUTO"
        self.timeout = self.ELM_TIMEOUT
        self.is_connected = False
        self.is_initialized = False
        self.is_monitoring = False
        self.device_info = {}
        
        # Блокировки и очереди
        self.lock = Lock()
        self.command_lock = Lock()
        self.response_ready = Event()
        self.command_queue = Queue()
        self.response_queue = Queue()
        self.monitor_queue = Queue()
        
        # Потоки
        self.monitor_thread = None
        self.command_thread = None
        
        # Статистика
        self.statistics = {
            'bytes_sent': 0,
            'bytes_received': 0,
            'commands_sent': 0,
            'commands_received': 0,
            'errors': 0,
            'timeouts': 0,
            'connection_time': None,
            'last_command': None,
            'last_response': None
        }
        
        # Настройки адаптера
        self.settings = {
            'echo': False,
            'headers': True,
            'spaces': True,
            'linefeed': False,
            'memory': False,
            'adaptive_timing': True,
            'can_extended': False,
            'can_flow_control': False
        }
        
        # Callbacks
        self.callbacks = {
            'on_connect': [],
            'on_disconnect': [],
            'on_error': [],
            'on_data': [],
            'on_timeout': []
        }
        
        # Инициализация логгера
        self.logger = logger
        
    def register_callback(self, event: str, callback: Callable) -> None:
        """
        Регистрация callback функции для событий.
        
        Args:
            event: Событие (on_connect, on_disconnect, on_error, on_data, on_timeout)
            callback: Функция обратного вызова
        """
        if event in self.callbacks:
            self.callbacks[event].append(callback)
        else:
            self.logger.warning(f"Неизвестное событие: {event}")
    
    def _notify(self, event: str, *args, **kwargs) -> None:
        """
        Уведомление всех зарегистрированных callback функций.
        
        Args:
            event: Событие
            *args: Аргументы
            **kwargs: Именованные аргументы
        """
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    self.logger.error(f"Ошибка в callback {event}: {e}")
    
    def scan_devices(self, connection_type: ConnectionType) -> List[Dict[str, str]]:
        """
        Сканирование доступных устройств.
        
        Args:
            connection_type: Тип подключения
            
        Returns:
            Список найденных устройств
        """
        devices = []
        
        try:
            if connection_type == ConnectionType.BLUETOOTH:
                devices = self._scan_bluetooth()
            elif connection_type == ConnectionType.USB:
                devices = self._scan_serial()
            elif connection_type == ConnectionType.WIFI:
                devices = self._scan_wifi()
                
        except Exception as e:
            self.logger.error(f"Ошибка сканирования устройств: {e}")
            self._notify('on_error', f"Ошибка сканирования: {e}")
            
        return devices
    
    def _scan_bluetooth(self) -> List[Dict[str, str]]:
        """
        Сканирование Bluetooth устройств.
        
        Returns:
            Список Bluetooth устройств
        """
        devices = []
        
        try:
            self.logger.info("Начинаю сканирование Bluetooth устройств...")
            
            # Поиск устройств с включенным обнаружением
            nearby_devices = bluetooth.discover_devices(lookup_names=True, duration=8, flush_cache=True)
            
            for addr, name in nearby_devices:
                # Проверка, что это похоже на ELM327
                if self._is_elm327_device(name):
                    device_info = {
                        'address': addr,
                        'name': name,
                        'type': 'bluetooth',
                        'description': f"Bluetooth: {name} ({addr})"
                    }
                    devices.append(device_info)
                    self.logger.info(f"Найдено устройство: {name} ({addr})")
                    
        except Exception as e:
            self.logger.error(f"Ошибка сканирования Bluetooth: {e}")
            
        return devices
    
    def _scan_serial(self) -> List[Dict[str, str]]:
        """
        Сканирование COM портов.
        
        Returns:
            Список COM портов
        """
        devices = []
        
        # Список портов для проверки (зависит от ОС)
        import sys
        if sys.platform.startswith('win'):
            ports = [f'COM{i}' for i in range(1, 257)]
        elif sys.platform.startswith('linux'):
            ports = [f'/dev/ttyUSB{i}' for i in range(10)] + [f'/dev/ttyACM{i}' for i in range(10)]
        elif sys.platform.startswith('darwin'):
            ports = [f'/dev/tty.usbserial-*', f'/dev/tty.usbmodem*']
        else:
            ports = []
            
        for port in ports:
            try:
                # Пробуем подключиться к порту
                test_serial = serial.Serial(
                    port=port,
                    baudrate=38400,
                    timeout=1,
                    write_timeout=1
                )
                
                # Пробуем отправить команду ATZ
                test_serial.write(b'ATZ\r')
                time.sleep(0.5)
                response = test_serial.read_all().decode('utf-8', errors='ignore')
                
                # Проверяем ответ
                if 'ELM327' in response.upper():
                    device_info = {
                        'port': port,
                        'name': 'ELM327 USB',
                        'type': 'usb',
                        'description': f"USB: {port} (ELM327)"
                    }
                    devices.append(device_info)
                    self.logger.info(f"Найден ELM327 на порту: {port}")
                    
                test_serial.close()
                
            except (serial.SerialException, OSError):
                continue
            except Exception as e:
                self.logger.error(f"Ошибка проверки порта {port}: {e}")
                
        return devices
    
    def _scan_wifi(self) -> List[Dict[str, str]]:
        """
        Сканирование WiFi устройств.
        
        Returns:
            Список WiFi устройств
        """
        devices = []
        
        # Предустановленные адреса WiFi адаптеров
        common_ips = [
            ('192.168.0.10', 35000),
            ('192.168.0.11', 35000),
            ('192.168.1.100', 35000),
            ('192.168.1.101', 35000),
            ('10.0.0.10', 35000),
            ('10.0.0.11', 35000),
        ]
        
        for ip, port in common_ips:
            try:
                # Пробуем подключиться
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((ip, port))
                
                if result == 0:
                    # Пробуем отправить команду
                    sock.send(b'ATZ\r')
                    response = sock.recv(1024).decode('utf-8', errors='ignore')
                    
                    if 'ELM327' in response.upper():
                        device_info = {
                            'ip': ip,
                            'port': port,
                            'name': 'ELM327 WiFi',
                            'type': 'wifi',
                            'description': f"WiFi: {ip}:{port} (ELM327)"
                        }
                        devices.append(device_info)
                        self.logger.info(f"Найден ELM327 WiFi: {ip}:{port}")
                        
                sock.close()
                
            except Exception as e:
                continue
                
        return devices
    
    def _is_elm327_device(self, device_name: str) -> bool:
        """
        Проверка, является ли устройство ELM327.
        
        Args:
            device_name: Имя устройства
            
        Returns:
            True если устройство похоже на ELM327
        """
        if not device_name:
            return False
            
        name_upper = device_name.upper()
        elm_keywords = ['ELM327', 'OBDII', 'OBD2', 'V1.5', 'V2.1']
        
        return any(keyword in name_upper for keyword in elm_keywords)
    
    def connect(self, connection_type: ConnectionType, **kwargs) -> bool:
        """
        Подключение к адаптеру ELM327.
        
        Args:
            connection_type: Тип подключения
            **kwargs: Параметры подключения
                Для Bluetooth: address
                Для USB: port, baudrate
                Для WiFi: ip, port
                
        Returns:
            True если подключение успешно
        """
        try:
            self.logger.info(f"Попытка подключения: {connection_type}")
            
            # Сохраняем тип подключения
            self.connection_type = connection_type
            
            # Устанавливаем соединение
            if connection_type == ConnectionType.BLUETOOTH:
                address = kwargs.get('address')
                if not address:
                    raise ValueError("Для Bluetooth подключения требуется адрес")
                self._connect_bluetooth(address)
                
            elif connection_type == ConnectionType.USB:
                port = kwargs.get('port')
                baudrate = kwargs.get('baudrate', self.baudrate)
                if not port:
                    raise ValueError("Для USB подключения требуется порт")
                self._connect_serial(port, baudrate)
                
            elif connection_type == ConnectionType.WIFI:
                ip = kwargs.get('ip')
                port = kwargs.get('port', 35000)
                if not ip:
                    raise ValueError("Для WiFi подключения требуется IP адрес")
                self._connect_wifi(ip, port)
                
            else:
                raise ValueError(f"Неподдерживаемый тип подключения: {connection_type}")
            
            # Инициализация адаптера
            if self._initialize_adapter():
                self.is_connected = True
                self.is_initialized = True
                self.statistics['connection_time'] = datetime.now()
                
                # Запуск потоков
                self._start_threads()
                
                self.logger.info("Подключение успешно установлено")
                self._notify('on_connect', self.device_info)
                return True
            else:
                self.disconnect()
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка подключения: {e}")
            self._notify('on_error', f"Ошибка подключения: {e}")
            self.disconnect()
            return False
    
    def _connect_bluetooth(self, address: str) -> None:
        """
        Подключение по Bluetooth.
        
        Args:
            address: MAC адрес устройства
            
        Raises:
            ConnectionError: Если не удалось подключиться
        """
        try:
            self.logger.info(f"Подключение к Bluetooth устройству {address}")
            
            # Создаем Bluetooth сокет
            self.connection = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            self.connection.settimeout(5)
            
            # Пробуем подключиться на разных каналах
            for channel in range(1, 31):
                try:
                    self.logger.debug(f"Попытка подключения к каналу {channel}")
                    self.connection.connect((address, channel))
                    self.port = f"RFCOMM channel {channel}"
                    self.address = address
                    
                    # Настраиваем таймаут
                    self.connection.settimeout(self.timeout)
                    
                    self.logger.info(f"Подключено к {address} на канале {channel}")
                    break
                    
                except bluetooth.btcommon.BluetoothError as e:
                    if channel == 30:
                        raise ConnectionError(f"Не удалось подключиться к {address}: {e}")
                    continue
                    
        except Exception as e:
            raise ConnectionError(f"Ошибка Bluetooth подключения: {e}")
    
    def _connect_serial(self, port: str, baudrate: int) -> None:
        """
        Подключение по USB/COM порту.
        
        Args:
            port: COM порт
            baudrate: Скорость передачи
            
        Raises:
            ConnectionError: Если не удалось подключиться
        """
        try:
            self.logger.info(f"Подключение к COM порту {port} на скорости {baudrate}")
            
            # Автоподбор скорости если не указана
            if baudrate == 'auto':
                baudrate = self._autodetect_baudrate(port)
                
            self.connection = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
                write_timeout=self.timeout,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
            
            self.port = port
            self.baudrate = baudrate
            
            # Очистка буферов
            self.connection.reset_input_buffer()
            self.connection.reset_output_buffer()
            
            self.logger.info(f"Подключено к {port} на скорости {baudrate}")
            
        except serial.SerialException as e:
            raise ConnectionError(f"Ошибка подключения к порту {port}: {e}")
        except Exception as e:
            raise ConnectionError(f"Неизвестная ошибка при подключении: {e}")
    
    def _autodetect_baudrate(self, port: str) -> int:
        """
        Автодетект скорости для COM порта.
        
        Args:
            port: COM порт
            
        Returns:
            Определенная скорость передачи
        """
        self.logger.info("Автодетект скорости...")
        
        for baudrate in self.DEFAULT_BAUDRATES:
            try:
                test_serial = serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    timeout=0.5
                )
                
                # Отправляем команду ATZ
                test_serial.write(b'ATZ\r')
                time.sleep(0.5)
                response = test_serial.read_all().decode('utf-8', errors='ignore')
                
                test_serial.close()
                
                if 'ELM327' in response.upper():
                    self.logger.info(f"Определена скорость: {baudrate}")
                    return baudrate
                    
            except:
                continue
                
        # Возвращаем скорость по умолчанию если не удалось определить
        self.logger.warning("Не удалось определить скорость, используем 38400")
        return 38400
    
    def _connect_wifi(self, ip: str, port: int) -> None:
        """
        Подключение по WiFi.
        
        Args:
            ip: IP адрес
            port: Порт
            
        Raises:
            ConnectionError: Если не удалось подключиться
        """
        try:
            self.logger.info(f"Подключение к WiFi устройству {ip}:{port}")
            
            # Создаем TCP сокет
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connection.settimeout(5)
            
            # Подключаемся
            self.connection.connect((ip, port))
            
            # Настраиваем таймауты
            self.connection.settimeout(self.timeout)
            
            self.port = f"{ip}:{port}"
            self.address = ip
            
            self.logger.info(f"Подключено к {ip}:{port}")
            
        except socket.error as e:
            raise ConnectionError(f"Ошибка WiFi подключения: {e}")
        except Exception as e:
            raise ConnectionError(f"Неизвестная ошибка при подключении: {e}")
    
    def _initialize_adapter(self) -> bool:
        """
        Инициализация адаптера ELM327.
        
        Returns:
            True если инициализация успешна
        """
        try:
            self.logger.info("Инициализация адаптера ELM327...")
            
            # 1. Сброс адаптера
            response = self._send_raw_command('ATZ', wait_time=2)
            if not response or 'ELM327' not in response.upper():
                self.logger.error("Не удалось сбросить адаптер")
                return False
            
            # Извлекаем информацию об устройстве
            self._parse_device_info(response)
            
            # 2. Настройка параметров адаптера
            init_commands = [
                ('ATE0', 'echo'),      # Выключить эхо
                ('ATH1', 'headers'),   # Включить заголовки
                ('ATL0', 'linefeed'),  # Выключить перевод строки
                ('ATS0', 'spaces'),    # Включить пробелы
                ('ATM0', 'memory'),    # Выключить память
                ('ATAT1', 'adaptive'), # Включить адаптивный тайминг
            ]
            
            for cmd, setting in init_commands:
                response = self._send_raw_command(cmd)
                if 'OK' in response or '?' not in response:
                    self.settings[setting] = cmd.endswith('1')
                else:
                    self.logger.warning(f"Команда {cmd} не поддерживается")
            
            # 3. Определение протокола
            protocol_response = self._send_raw_command('ATDP')
            if protocol_response:
                protocol_code = protocol_response.strip()
                if protocol_code.isdigit():
                    self.protocol = self.PROTOCOLS.get(int(protocol_code), "UNKNOWN")
                    self.logger.info(f"Определен протокол: {self.protocol}")
            
            # 4. Чтение напряжения
            voltage_response = self._send_raw_command('ATRV')
            if voltage_response:
                try:
                    voltage = float(''.join(filter(lambda x: x.isdigit() or x == '.', voltage_response)))
                    self.device_info['voltage'] = voltage
                    self.logger.info(f"Напряжение: {voltage}V")
                except:
                    pass
            
            # 5. Дополнительная информация
            info_commands = {
                'ATI': 'version',
                'AT@1': 'description',
                'AT@2': 'device_id'
            }
            
            for cmd, key in info_commands.items():
                response = self._send_raw_command(cmd)
                if response and '?' not in response:
                    self.device_info[key] = response.strip()
            
            self.logger.info("Инициализация успешно завершена")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации адаптера: {e}")
            return False
    
    def _parse_device_info(self, response: str) -> None:
        """
        Парсинг информации об устройстве из ответа ATZ.
        
        Args:
            response: Ответ от адаптера
        """
        lines = response.split('\n')
        for line in lines:
            line_upper = line.upper()
            
            # Версия
            if 'ELM327' in line_upper:
                version_match = re.search(r'ELM327\s+v?(\d+\.\d+)', line_upper, re.IGNORECASE)
                if version_match:
                    self.device_info['version'] = version_match.group(1)
            
            # Чип
            if 'CHIP' in line_upper:
                chip_match = re.search(r'CHIP:\s*(\S+)', line_upper, re.IGNORECASE)
                if chip_match:
                    self.device_info['chip'] = chip_match.group(1)
            
            # Прошивка
            if 'FIRMWARE' in line_upper:
                fw_match = re.search(r'FIRMWARE:\s*(\S+)', line_upper, re.IGNORECASE)
                if fw_match:
                    self.device_info['firmware'] = fw_match.group(1)
        
        # Базовая информация если не удалось распарсить
        if 'version' not in self.device_info:
            self.device_info['version'] = 'Unknown'
            self.device_info['type'] = 'ELM327'
    
    def _send_raw_command(self, command: str, wait_time: float = 0.1) -> str:
        """
        Отправка RAW команды адаптеру.
        
        Args:
            command: Команда
            wait_time: Время ожидания ответа
            
        Returns:
            Ответ от адаптера
        """
        with self.command_lock:
            if not self.connection:
                return ""
            
            try:
                # Добавляем перенос строки
                if not command.endswith("\r"):
                    command += "\r"
                
                # Отправка команды
                if self.connection_type == ConnectionType.BLUETOOTH:
                    self.connection.send(command.encode())
                elif self.connection_type == ConnectionType.USB:
                    self.connection.write(command.encode())
                elif self.connection_type == ConnectionType.WIFI:
                    self.connection.send(command.encode())
                
                self.statistics['bytes_sent'] += len(command)
                self.statistics['commands_sent'] += 1
                self.statistics['last_command'] = command.strip()
                
                # Ожидание ответа
                time.sleep(wait_time)
                
                # Чтение ответа
                response = self._read_response()
                
                self.statistics['bytes_received'] += len(response)
                self.statistics['commands_received'] += 1
                self.statistics['last_response'] = response
                
                return response
                
            except Exception as e:
                self.statistics['errors'] += 1
                self.logger.error(f"Ошибка отправки команды {command}: {e}")
                return ""
    
    def _read_response(self) -> str:
        """
        Чтение ответа от адаптера.
        
        Returns:
            Ответ адаптера
        """
        if not self.connection:
            return ""
        
        try:
            response = ""
            start_time = time.time()
            
            while True:
                # Проверка таймаута
                if time.time() - start_time > self.timeout:
                    self.statistics['timeouts'] += 1
                    self.logger.warning(f"Таймаут чтения ответа")
                    self._notify('on_timeout', f"Таймаут чтения ответа")
                    break
                
                # Чтение данных
                if self.connection_type == ConnectionType.USB:
                    # Для COM порта
                    if self.connection.in_waiting > 0:
                        data = self.connection.read(self.connection.in_waiting)
                        response += data.decode('utf-8', errors='ignore')
                else:
                    # Для Bluetooth и WiFi
                    self.connection.settimeout(0.1)
                    try:
                        if self.connection_type == ConnectionType.BLUETOOTH:
                            data = self.connection.recv(1024)
                        else:  # WiFi
                            data = self.connection.recv(1024)
                        
                        if data:
                            response += data.decode('utf-8', errors='ignore')
                    except socket.timeout:
                        pass
                
                # Проверка завершения ответа
                if self.ELM_PROMPT in response:
                    break
                
                # Пауза между чтениями
                time.sleep(0.01)
            
            # Очистка ответа
            response = self._clean_response(response)
            return response
            
        except Exception as e:
            self.logger.error(f"Ошибка чтения ответа: {e}")
            return ""
    
    def _clean_response(self, response: str) -> str:
        """
        Очистка ответа от лишних символов и эха.
        
        Args:
            response: Сырой ответ
            
        Returns:
            Очищенный ответ
        """
        if not response:
            return ""
        
        # Удаляем эхо команды если включено
        if not self.settings['echo']:
            # Удаляем строку начинающуюся с '>'
            lines = response.split('\n')
            cleaned_lines = []
            
            for line in lines:
                # Пропускаем строку с эхом команды
                if line.strip().startswith(self.ELM_PROMPT):
                    continue
                
                # Пропускаем пустые строки
                if line.strip() == '':
                    continue
                
                # Удаляем приглашение ELM327
                line = line.replace(self.ELM_PROMPT, '')
                
                cleaned_lines.append(line)
            
            response = '\n'.join(cleaned_lines)
        
        # Удаляем пробелы если отключены
        if not self.settings['spaces']:
            response = response.replace(' ', '')
        
        # Удаляем лишние переносы строк
        response = response.strip()
        response = re.sub(r'\r\n', '\n', response)
        response = re.sub(r'\r', '\n', response)
        response = re.sub(r'\n+', '\n', response)
        
        return response
    
    def _start_threads(self) -> None:
        """Запуск рабочих потоков."""
        # Поток мониторинга
        self.is_monitoring = True
        self.monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        # Поток обработки команд
        self.command_thread = Thread(target=self._command_loop, daemon=True)
        self.command_thread.start()
        
        self.logger.debug("Рабочие потоки запущены")
    
    def _monitor_loop(self) -> None:
        """Цикл мониторинга входящих данных."""
        self.logger.debug("Запущен цикл мониторинга")
        
        while self.is_monitoring and self.is_connected:
            try:
                if self.connection_type == ConnectionType.USB:
                    # Для COM порта
                    if self.connection and self.connection.in_waiting > 0:
                        data = self.connection.read(self.connection.in_waiting)
                        if data:
                            decoded_data = data.decode('utf-8', errors='ignore')
                            self.monitor_queue.put(decoded_data)
                            self._notify('on_data', decoded_data)
                else:
                    # Для Bluetooth и WiFi
                    if self.connection:
                        self.connection.settimeout(0.01)
                        try:
                            if self.connection_type == ConnectionType.BLUETOOTH:
                                data = self.connection.recv(1024)
                            else:  # WiFi
                                data = self.connection.recv(1024)
                            
                            if data:
                                decoded_data = data.decode('utf-8', errors='ignore')
                                self.monitor_queue.put(decoded_data)
                                self._notify('on_data', decoded_data)
                        except socket.timeout:
                            pass
                        except Exception as e:
                            if self.is_monitoring:
                                self.logger.error(f"Ошибка в цикле мониторинга: {e}")
                
                # Пауза для снижения нагрузки на CPU
                time.sleep(0.001)
                
            except Exception as e:
                if self.is_monitoring:
                    self.logger.error(f"Критическая ошибка в цикле мониторинга: {e}")
                    time.sleep(0.1)
        
        self.logger.debug("Цикл мониторинга остановлен")
    
    def _command_loop(self) -> None:
        """Цикл обработки команд из очереди."""
        self.logger.debug("Запущен цикл обработки команд")
        
        while self.is_monitoring and self.is_connected:
            try:
                # Получение команды из очереди с таймаутом
                try:
                    command_data = self.command_queue.get(timeout=0.1)
                except Empty:
                    continue
                
                # Обработка команды
                command = command_data.get('command')
                callback = command_data.get('callback')
                wait_time = command_data.get('wait_time', 0.1)
                
                if command:
                    response = self._send_raw_command(command, wait_time)
                    
                    # Вызов callback если есть
                    if callback:
                        try:
                            callback(response)
                        except Exception as e:
                            self.logger.error(f"Ошибка в callback команды {command}: {e}")
                
                # Отмечаем задачу как выполненную
                self.command_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Ошибка в цикле обработки команд: {e}")
        
        self.logger.debug("Цикл обработки команд остановлен")
    
    def send_command(self, command: str, callback: Callable = None, wait_time: float = 0.1) -> None:
        """
        Асинхронная отправка команды.
        
        Args:
            command: Команда
            callback: Функция обратного вызова
            wait_time: Время ожидания ответа
        """
        if not self.is_connected:
            self.logger.warning("Попытка отправить команду без подключения")
            return
        
        command_data = {
            'command': command,
            'callback': callback,
            'wait_time': wait_time
        }
        
        self.command_queue.put(command_data)
    
    def send_command_sync(self, command: str, wait_time: float = 0.1) -> str:
        """
        Синхронная отправка команды.
        
        Args:
            command: Команда
            wait_time: Время ожидания ответа
            
        Returns:
            Ответ от адаптера
        """
        if not self.is_connected:
            return "NOT CONNECTED"
        
        return self._send_raw_command(command, wait_time)
    
    def send_obd_command(self, mode: str, pid: str, ecu: str = None, **kwargs) -> str:
        """
        Отправка OBD команды.
        
        Args:
            mode: Режим OBD (01, 02, 03 и т.д.)
            pid: PID команды
            ecu: Адрес ECU (опционально)
            
        Returns:
            Ответ от адаптера
        """
        # Построение команды
        if ecu:
            command = f"{ecu}{mode}{pid}"
        else:
            command = f"{mode}{pid}"
        
        # Отправка команды
        return self.send_command_sync(command, **kwargs)
    
    def set_protocol(self, protocol: Union[str, int]) -> bool:
        """
        Установка протокола.
        
        Args:
            protocol: Протокол или код протокола
            
        Returns:
            True если протокол установлен
        """
        try:
            if isinstance(protocol, str):
                # Поиск кода протокола по имени
                protocol_code = None
                for code, name in self.PROTOCOLS.items():
                    if name.upper() == protocol.upper():
                        protocol_code = code
                        break
                
                if protocol_code is None:
                    raise ValueError(f"Неизвестный протокол: {protocol}")
            else:
                protocol_code = protocol
            
            # Установка протокола
            response = self._send_raw_command(f'ATSP{protocol_code}')
            if 'OK' in response:
                self.protocol = self.PROTOCOLS.get(protocol_code, f"UNKNOWN ({protocol_code})")
                self.logger.info(f"Протокол установлен: {self.protocol}")
                return True
            else:
                self.logger.error(f"Не удалось установить протокол {protocol_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка установки протокола: {e}")
            return False
    
    def set_timeout(self, timeout_ms: int) -> bool:
        """
        Установка таймаута.
        
        Args:
            timeout_ms: Таймаут в миллисекундах
            
        Returns:
            True если таймаут установлен
        """
        try:
            # Конвертируем в hex
            timeout_hex = hex(min(max(timeout_ms, 0), 255))[2:].upper().zfill(2)
            
            response = self._send_raw_command(f'ATST{timeout_hex}')
            if 'OK' in response:
                self.timeout = timeout_ms / 1000.0  # Конвертируем в секунды
                self.logger.info(f"Таймаут установлен: {timeout_ms}ms")
                return True
            else:
                self.logger.error(f"Не удалось установить таймаут")
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка установки таймаута: {e}")
            return False
    
    def set_adaptive_timing(self, enabled: bool) -> bool:
        """
        Включение/выключение адаптивного тайминга.
        
        Args:
            enabled: True для включения
            
        Returns:
            True если настройка применена
        """
        try:
            cmd = 'ATAT1' if enabled else 'ATAT0'
            response = self._send_raw_command(cmd)
            
            if 'OK' in response:
                self.settings['adaptive'] = enabled
                self.logger.info(f"Адаптивный тайминг {'включен' if enabled else 'выключен'}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка настройки адаптивного тайминга: {e}")
            return False
    
    def set_can_extended(self, enabled: bool) -> bool:
        """
        Включение/выключение расширенного CAN.
        
        Args:
            enabled: True для включения
            
        Returns:
            True если настройка применена
        """
        try:
            cmd = 'ATCEA1' if enabled else 'ATCEA0'
            response = self._send_raw_command(cmd)
            
            if 'OK' in response:
                self.settings['can_extended'] = enabled
                self.logger.info(f"Расширенный CAN {'включен' if enabled else 'выключен'}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка настройки CAN: {e}")
            return False
    
    def set_can_filter(self, filter_id: str, mask: str = None) -> bool:
        """
        Установка CAN фильтра.
        
        Args:
            filter_id: ID фильтра
            mask: Маска (опционально)
            
        Returns:
            True если фильтр установлен
        """
        try:
            # Установка фильтра
            response = self._send_raw_command(f'ATCF{filter_id}')
            if 'OK' not in response:
                return False
            
            # Установка маски если указана
            if mask:
                response = self._send_raw_command(f'ATCM{mask}')
                if 'OK' not in response:
                    return False
            
            self.logger.info(f"CAN фильтр установлен: {filter_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка установки CAN фильтра: {e}")
            return False
    
    def monitor_live_data(self, pids: List[str], interval: float = 0.1, callback: Callable = None) -> None:
        """
        Мониторинг данных в реальном времени.
        
        Args:
            pids: Список PID для мониторинга
            interval: Интервал опроса
            callback: Функция обратного вызова для данных
        """
        if not self.is_connected:
            self.logger.warning("Попытка мониторинга без подключения")
            return
        
        # Запуск потока мониторинга
        monitor_thread = Thread(
            target=self._live_data_monitor,
            args=(pids, interval, callback),
            daemon=True
        )
        monitor_thread.start()
    
    def _live_data_monitor(self, pids: List[str], interval: float, callback: Callable) -> None:
        """
        Поток мониторинга живых данных.
        
        Args:
            pids: Список PID
            interval: Интервал
            callback: Функция обратного вызова
        """
        self.logger.info(f"Запущен мониторинг {len(pids)} PID с интервалом {interval}с")
        
        try:
            while self.is_connected and self.is_monitoring:
                data = {}
                
                for pid in pids:
                    try:
                        response = self.send_obd_command('01', pid)
                        if response and 'NO DATA' not in response:
                            data[pid] = response
                            
                            # Вызов callback если есть
                            if callback:
                                callback(pid, response)
                    except Exception as e:
                        self.logger.error(f"Ошибка чтения PID {pid}: {e}")
                
                # Пауза между циклами
                time.sleep(interval)
                
        except Exception as e:
            self.logger.error(f"Ошибка в потоке мониторинга: {e}")
        
        self.logger.info("Мониторинг остановлен")
    
    def read_dtcs(self, ecu: str = None) -> List[str]:
        """
        Чтение диагностических кодов неисправностей.
        
        Args:
            ecu: Адрес ECU (опционально)
            
        Returns:
            Список DTC кодов
        """
        try:
            # Режим 03 - чтение сохраненных DTC
            response = self.send_obd_command('03', '', ecu)
            
            if not response or 'NO DATA' in response:
                return []
            
            # Парсинг DTC
            dtc_codes = self._parse_dtc_response(response)
            return dtc_codes
            
        except Exception as e:
            self.logger.error(f"Ошибка чтения DTC: {e}")
            return []
    
    def _parse_dtc_response(self, response: str) -> List[str]:
        """
        Парсинг ответа с DTC кодами.
        
        Args:
            response: Ответ адаптера
            
        Returns:
            Список DTC кодов
        """
        dtc_codes = []
        
        # Удаляем пробелы и лишние символы
        response = re.sub(r'[\s\r\n]', '', response)
        
        # Проверяем минимальную длину
        if len(response) < 8:  # Минимум 4 байта (2 байта заголовок + 2 байта данные)
            return dtc_codes
        
        # Пропускаем заголовок (первые 4 символа)
        data = response[4:]
        
        # Обрабатываем по 4 символа (2 байта на DTC)
        for i in range(0, len(data), 4):
            if i + 4 <= len(data):
                dtc_bytes = data[i:i+4]
                
                # Конвертируем в DTC код
                dtc_code = self._hex_to_dtc(dtc_bytes)
                if dtc_code and dtc_code != 'P0000':
                    dtc_codes.append(dtc_code)
        
        return dtc_codes
    
    def _hex_to_dtc(self, hex_str: str) -> str:
        """
        Конвертация hex строки в DTC код.
        
        Args:
            hex_str: HEX строка (4 символа)
            
        Returns:
            DTC код в формате PXXXX
        """
        if len(hex_str) != 4:
            return ""
        
        try:
            # Преобразуем в целое число
            value = int(hex_str, 16)
            
            if value == 0:
                return "P0000"
            
            # Извлекаем биты
            byte1 = (value >> 8) & 0xFF
            byte2 = value & 0xFF
            
            # Первые два бита определяют тип
            dtc_type = (byte1 >> 6) & 0x03
            
            # Буква типа
            type_letters = ['P', 'C', 'B', 'U']
            dtc_letter = type_letters[dtc_type] if dtc_type < 4 else 'P'
            
            # Оставшиеся биты - код
            dtc_number = ((byte1 & 0x3F) << 8) | byte2
            
            # Форматируем код
            return f"{dtc_letter}{dtc_number:04d}"
            
        except:
            return ""
    
    def clear_dtcs(self, ecu: str = None) -> bool:
        """
        Очистка диагностических кодов неисправностей.
        
        Args:
            ecu: Адрес ECU (опционально)
            
        Returns:
            True если ошибки очищены
        """
        try:
            # Режим 04 - очистка DTC
            response = self.send_obd_command('04', '', ecu)
            
            if response and 'NO DATA' not in response:
                # Даем время на очистку
                time.sleep(1)
                
                # Проверяем, что ошибки очищены
                remaining_dtcs = self.read_dtcs(ecu)
                if not remaining_dtcs:
                    self.logger.info("DTC успешно очищены")
                    return True
                else:
                    self.logger.warning(f"Остались DTC после очистки: {remaining_dtcs}")
                    return False
            else:
                self.logger.error("Не удалось очистить DTC")
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка очистки DTC: {e}")
            return False
    
    def read_freeze_frame(self, frame_number: int = 0, ecu: str = None) -> Dict:
        """
        Чтение замороженных кадров.
        
        Args:
            frame_number: Номер кадра
            ecu: Адрес ECU
            
        Returns:
            Данные замороженного кадра
        """
        try:
            # Режим 02 - чтение замороженных кадров
            response = self.send_obd_command('02', f'{frame_number:02X}', ecu)
            
            if response and 'NO DATA' not in response:
                # Парсинг ответа
                return self._parse_freeze_frame(response)
            else:
                return {}
                
        except Exception as e:
            self.logger.error(f"Ошибка чтения замороженного кадра: {e}")
            return {}
    
    def _parse_freeze_frame(self, response: str) -> Dict:
        """
        Парсинг замороженного кадра.
        
        Args:
            response: Ответ адаптера
            
        Returns:
            Словарь с данными кадра
        """
        frame_data = {}
        
        try:
            # Удаляем пробелы
            response = re.sub(r'[\s\r\n]', '', response)
            
            if len(response) < 8:
                return frame_data
            
            # Пропускаем заголовок
            data = response[4:]
            
            # Первый байт - DTC
            if len(data) >= 4:
                dtc_hex = data[:4]
                frame_data['dtc'] = self._hex_to_dtc(dtc_hex)
                data = data[4:]
            
            # Остальные данные зависят от реализации
            # Здесь можно добавить специфичный парсинг
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга замороженного кадра: {e}")
        
        return frame_data
    
    def read_vehicle_info(self) -> Dict:
        """
        Чтение информации о транспортном средстве.
        
        Returns:
            Информация о транспортном средстве
        """
        vehicle_info = {}
        
        try:
            # VIN (Режим 09 PID 02)
            response = self.send_obd_command('09', '02')
            if response and 'NO DATA' not in response:
                vin = self._parse_vin_response(response)
                if vin:
                    vehicle_info['vin'] = vin
            
            # Calibration ID (Режим 09 PID 04)
            response = self.send_obd_command('09', '04')
            if response and 'NO DATA' not in response:
                calibration_id = self._parse_string_response(response)
                if calibration_id:
                    vehicle_info['calibration_id'] = calibration_id
            
            # ECU Name (Режим 09 PID 0A)
            response = self.send_obd_command('09', '0A')
            if response and 'NO DATA' not in response:
                ecu_name = self._parse_string_response(response)
                if ecu_name:
                    vehicle_info['ecu_name'] = ecu_name
            
        except Exception as e:
            self.logger.error(f"Ошибка чтения информации о ТС: {e}")
        
        return vehicle_info
    
    def _parse_vin_response(self, response: str) -> str:
        """
        Парсинг VIN из ответа.
        
        Args:
            response: Ответ адаптера
            
        Returns:
            VIN номер
        """
        try:
            # Удаляем пробелы и лишние символы
            response = re.sub(r'[\s\r\n]', '', response)
            
            if len(response) < 8:
                return ""
            
            # Пропускаем заголовок
            data = response[4:]
            
            # Конвертируем HEX в ASCII
            vin = ""
            for i in range(0, len(data), 2):
                if i + 2 <= len(data):
                    hex_byte = data[i:i+2]
                    if hex_byte != '00':
                        try:
                            char = chr(int(hex_byte, 16))
                            if char.isprintable():
                                vin += char
                        except:
                            pass
            
            # Проверяем длину VIN (обычно 17 символов)
            if len(vin) >= 17:
                return vin[:17]
            else:
                return vin
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга VIN: {e}")
            return ""
    
    def _parse_string_response(self, response: str) -> str:
        """
        Парсинг строкового ответа.
        
        Args:
            response: Ответ адаптера
            
        Returns:
            Строка
        """
        try:
            # Удаляем пробелы и лишние символы
            response = re.sub(r'[\s\r\n]', '', response)
            
            if len(response) < 8:
                return ""
            
            # Пропускаем заголовок
            data = response[4:]
            
            # Конвертируем HEX в ASCII
            result = ""
            for i in range(0, len(data), 2):
                if i + 2 <= len(data):
                    hex_byte = data[i:i+2]
                    if hex_byte != '00':
                        try:
                            char = chr(int(hex_byte, 16))
                            if char.isprintable():
                                result += char
                        except:
                            pass
            
            return result.strip()
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга строки: {e}")
            return ""
    
    def reset_adaptations(self, adaptation_type: str = None) -> bool:
        """
        Сброс адаптаций.
        
        Args:
            adaptation_type: Тип адаптации
            
        Returns:
            True если сброс выполнен
        """
        try:
            # AT команды для сброса адаптаций
            adaptation_commands = {
                'idle': 'AT IAR',      # Сброс адаптации холостого хода
                'throttle': 'AT TAR',  # Сброс адаптации дроссельной заслонки
                'fuel': 'AT FTR',      # Сброс адаптации топливных коррекций
                'all': 'AT DEFAULTS'   # Сброс всех настроек
            }
            
            if adaptation_type and adaptation_type in adaptation_commands:
                command = adaptation_commands[adaptation_type]
            else:
                # Сброс всех адаптаций по умолчанию
                command = adaptation_commands['all']
            
            response = self._send_raw_command(command, wait_time=2)
            
            if 'OK' in response:
                self.logger.info(f"Адаптации сброшены: {adaptation_type if adaptation_type else 'all'}")
                
                # Даем время на перезагрузку
                time.sleep(2)
                
                # Повторная инициализация
                self._initialize_adapter()
                
                return True
            else:
                self.logger.error("Не удалось сбросить адаптации")
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка сброса адаптаций: {e}")
            return False
    
    def test_communication(self, ecu_list: List[str] = None) -> Dict:
        """
        Тестирование связи с ECU.
        
        Args:
            ecu_list: Список адресов ECU для тестирования
            
        Returns:
            Результаты тестирования
        """
        if ecu_list is None:
            ecu_list = ['10', '28', '15', '29', '25', '08']  # Стандартные адреса
        
        results = {}
        
        for ecu in ecu_list:
            try:
                # Тестовая команда (режим 01 PID 00)
                response = self.send_obd_command('01', '00', ecu)
                
                if response and 'NO DATA' not in response:
                    results[ecu] = {
                        'status': 'CONNECTED',
                        'response': response
                    }
                else:
                    results[ecu] = {
                        'status': 'NO_RESPONSE',
                        'response': response if response else 'NO DATA'
                    }
                    
            except Exception as e:
                results[ecu] = {
                    'status': 'ERROR',
                    'error': str(e)
                }
        
        return results
    
    def get_statistics(self) -> Dict:
        """
        Получение статистики работы.
        
        Returns:
            Словарь со статистикой
        """
        stats = self.statistics.copy()
        
        # Добавляем информацию о подключении
        stats.update({
            'is_connected': self.is_connected,
            'is_initialized': self.is_initialized,
            'is_monitoring': self.is_monitoring,
            'connection_type': self.connection_type.value if self.connection_type else None,
            'port': self.port,
            'address': self.address,
            'baudrate': self.baudrate,
            'protocol': self.protocol,
            'timeout': self.timeout,
            'device_info': self.device_info,
            'settings': self.settings
        })
        
        # Время подключения
        if stats['connection_time']:
            stats['connection_duration'] = str(datetime.now() - stats['connection_time'])
        
        return stats
    
    def save_statistics(self, filepath: str = None) -> bool:
        """
        Сохранение статистики в файл.
        
        Args:
            filepath: Путь к файлу
            
        Returns:
            True если сохранение успешно
        """
        try:
            if filepath is None:
                # Создаем имя файла по умолчанию
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = f"elm327_stats_{timestamp}.json"
            
            stats = self.get_statistics()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, default=str)
            
            self.logger.info(f"Статистика сохранена в {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения статистики: {e}")
            return False
    
    def disconnect(self) -> None:
        """Отключение от адаптера и очистка ресурсов."""
        self.logger.info("Отключение от адаптера...")
        
        # Останавливаем мониторинг
        self.is_monitoring = False
        self.is_connected = False
        self.is_initialized = False
        
        # Ждем завершения потоков
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
            self.monitor_thread = None
        
        if self.command_thread:
            self.command_thread.join(timeout=2)
            self.command_thread = None
        
        # Закрываем соединение
        if self.connection:
            try:
                if self.connection_type == ConnectionType.USB:
                    self.connection.close()
                elif self.connection_type == ConnectionType.BLUETOOTH:
                    self.connection.close()
                elif self.connection_type == ConnectionType.WIFI:
                    self.connection.close()
            except Exception as e:
                self.logger.error(f"Ошибка при закрытии соединения: {e}")
            finally:
                self.connection = None
        
        # Очищаем очереди
        while not self.command_queue.empty():
            try:
                self.command_queue.get_nowait()
                self.command_queue.task_done()
            except:
                pass
        
        while not self.monitor_queue.empty():
            try:
                self.monitor_queue.get_nowait()
            except:
                pass
        
        # Очищаем информацию об устройстве
        self.device_info = {}
        
        # Уведомляем об отключении
        self._notify('on_disconnect')
        
        self.logger.info("Отключение завершено")
    
    def __enter__(self):
        """Контекстный менеджер для использования with."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Завершение работы контекстного менеджера."""
        self.disconnect()
    
    def __del__(self):
        """Деструктор."""
        self.disconnect()