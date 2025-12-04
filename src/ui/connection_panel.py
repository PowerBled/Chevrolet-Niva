"""
Панель подключения к диагностическому сканеру ELM327
"""

import os
import sys
import time
from typing import Dict, List, Optional, Tuple

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QComboBox, QPushButton, QTextEdit,
                             QProgressBar, QListWidget, QListWidgetItem,
                             QSplitter, QFrame, QMessageBox, QTabWidget,
                             QFormLayout, QSpinBox, QCheckBox, QLineEdit)
from PyQt5.QtCore import (Qt, QThread, pyqtSignal, pyqtSlot, QTimer, 
                          QSize, QPoint, QRect)
from PyQt5.QtGui import (QFont, QColor, QPalette, QIcon, QPixmap, 
                         QPainter, QPen, QBrush)

from src.elm327_connector import ELM327Connector, ConnectionType
from src.utils.logger import setup_logger


class DeviceScannerThread(QThread):
    """Поток для сканирования устройств"""
    
    devices_found = pyqtSignal(list)
    scan_complete = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, scan_type: str = "bluetooth"):
        super().__init__()
        self.scan_type = scan_type
        self.found_devices = []
        
    def run(self):
        """Основной метод потока"""
        try:
            if self.scan_type == "bluetooth":
                self.scan_bluetooth()
            elif self.scan_type == "serial":
                self.scan_serial_ports()
            elif self.scan_type == "wifi":
                self.scan_wifi_devices()
                
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.scan_complete.emit()
            
    def scan_bluetooth(self):
        """Сканирование Bluetooth устройств"""
        try:
            import bluetooth
            
            self.found_devices = []
            
            # Показываем статус сканирования
            self.devices_found.emit([{"name": "Сканирование...", "address": "", "type": "status"}])
            
            # Поиск устройств (таймаут 10 секунд)
            devices = bluetooth.discover_devices(lookup_names=True, duration=10, flush_cache=True)
            
            # Фильтруем устройства ELM327 по имени
            elm_devices = []
            for addr, name in devices:
                device_info = {
                    "address": addr,
                    "name": name,
                    "type": "bluetooth"
                }
                
                # Проверяем, является ли устройство ELM327
                if self.is_elm327_device(name):
                    device_info["is_elm327"] = True
                    elm_devices.insert(0, device_info)  # Добавляем в начало
                else:
                    device_info["is_elm327"] = False
                    elm_devices.append(device_info)
                    
            self.found_devices = elm_devices
            self.devices_found.emit(elm_devices)
            
        except ImportError:
            self.error_occurred.emit("Модуль bluetooth не установлен. Установите: pip install pybluez")
        except Exception as e:
            self.error_occurred.emit(f"Ошибка сканирования Bluetooth: {e}")
            
    def scan_serial_ports(self):
        """Сканирование COM-портов"""
        try:
            import serial.tools.list_ports
            
            ports = list(serial.tools.list_ports.comports())
            devices = []
            
            for port in ports:
                device_info = {
                    "name": port.description,
                    "address": port.device,
                    "type": "serial",
                    "hwid": port.hwid,
                    "manufacturer": port.manufacturer,
                    "product": port.product,
                    "is_elm327": self.is_elm327_port(port.description)
                }
                devices.append(device_info)
                
            self.found_devices = devices
            self.devices_found.emit(devices)
            
        except Exception as e:
            self.error_occurred.emit(f"Ошибка сканирования COM-портов: {e}")
            
    def scan_wifi_devices(self):
        """Сканирование WiFi устройств"""
        # Заглушка для WiFi сканирования
        devices = [
            {
                "name": "ELM327 WiFi (192.168.0.10:35000)",
                "address": "192.168.0.10:35000",
                "type": "wifi",
                "is_elm327": True
            },
            {
                "name": "ELM327 WiFi (192.168.0.11:35000)",
                "address": "192.168.0.11:35000",
                "type": "wifi",
                "is_elm327": True
            }
        ]
        
        self.found_devices = devices
        self.devices_found.emit(devices)
        
    def is_elm327_device(self, device_name: str) -> bool:
        """Проверка, является ли устройство ELM327"""
        if not device_name:
            return False
            
        elm_indicators = [
            "elm327", "elm 327", "obd", "obdii", "obd2", 
            "vgate", "icar", "bluetooth", "bt", "wifi"
        ]
        
        device_lower = device_name.lower()
        for indicator in elm_indicators:
            if indicator in device_lower:
                return True
        return False
        
    def is_elm327_port(self, port_description: str) -> bool:
        """Проверка COM-порта на ELM327"""
        if not port_description:
            return False
            
        elm_indicators = [
            "arduino", "ftdi", "pl2303", "ch340", "cp210",
            "usb serial", "usb-serial", "elm327"
        ]
        
        desc_lower = port_description.lower()
        for indicator in elm_indicators:
            if indicator in desc_lower:
                return True
        return False


class ConnectionWorker(QThread):
    """Поток для установки соединения"""
    
    connected = pyqtSignal(dict)
    connection_failed = pyqtSignal(str)
    connection_progress = pyqtSignal(str, int)
    
    def __init__(self, connector: ELM327Connector, 
                 connection_type: ConnectionType,
                 address: str, port: str = None):
        super().__init__()
        self.connector = connector
        self.connection_type = connection_type
        self.address = address
        self.port = port
        
    def run(self):
        """Установка соединения"""
        try:
            self.connection_progress.emit("Инициализация подключения...", 10)
            
            if self.connection_type == ConnectionType.BLUETOOTH:
                self.connection_progress.emit(f"Подключение к Bluetooth устройству {self.address}...", 30)
                success = self.connector.connect(
                    self.connection_type, 
                    address=self.address
                )
            elif self.connection_type == ConnectionType.USB:
                self.connection_progress.emit(f"Подключение к COM-порту {self.port}...", 30)
                success = self.connector.connect(
                    self.connection_type,
                    port=self.port
                )
            elif self.connection_type == ConnectionType.WIFI:
                self.connection_progress.emit(f"Подключение к WiFi устройству {self.address}...", 30)
                success = self.connector.connect(
                    self.connection_type,
                    port=self.address
                )
            else:
                raise ValueError(f"Неизвестный тип подключения: {self.connection_type}")
                
            if success:
                self.connection_progress.emit("Проверка связи с ELM327...", 60)
                
                # Тестирование адаптера
                test_result = self.test_adapter()
                
                self.connection_progress.emit("Получение информации об адаптере...", 80)
                
                # Получение информации об адаптере
                adapter_info = self.get_adapter_info()
                
                self.connection_progress.emit("Подключение установлено!", 100)
                
                # Формирование информации о подключении
                connection_info = {
                    "type": self.connection_type.value,
                    "address": self.address if self.address else self.port,
                    "adapter_info": adapter_info,
                    "test_result": test_result,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                self.connected.emit(connection_info)
            else:
                self.connection_failed.emit("Не удалось установить соединение")
                
        except Exception as e:
            self.connection_failed.emit(f"Ошибка подключения: {str(e)}")
            
    def test_adapter(self) -> Dict:
        """Тестирование адаптера"""
        test_results = {}
        
        try:
            # Тестовая команда ATZ (сброс)
            response = self.connector.send_command("ATZ")
            test_results["reset"] = {
                "command": "ATZ",
                "response": response,
                "success": "ELM327" in response or "OK" in response
            }
            
            # Получение версии прошивки
            response = self.connector.send_command("ATI")
            test_results["version"] = {
                "command": "ATI",
                "response": response,
                "success": "ELM327" in response
            }
            
            # Проверка протоколов
            response = self.connector.send_command("ATSP0")
            test_results["protocol"] = {
                "command": "ATSP0",
                "response": response,
                "success": "OK" in response
            }
            
        except Exception as e:
            test_results["error"] = str(e)
            
        return test_results
        
    def get_adapter_info(self) -> Dict:
        """Получение информации об адаптере"""
        info = {
            "firmware_version": "Неизвестно",
            "protocol_version": "Неизвестно",
            "elm327_version": "Неизвестно",
            "supported_commands": []
        }
        
        try:
            # Получение версии прошивки
            response = self.connector.send_command("ATI")
            if response:
                info["firmware_version"] = response.strip()
                
            # Получение версии ELM327
            response = self.connector.send_command("AT@1")
            if response and "ERROR" not in response:
                info["elm327_version"] = response.strip()
                
            # Проверка поддержки команд
            test_commands = [
                ("ATH1", "Заголовки"),
                ("ATE0", "Эхо"),
                ("ATL0", "Перевод строки"),
                ("ATS0", "Пробелы"),
                ("ATSP0", "Протоколы"),
                ("ATDPN", "Номер протокола"),
            ]
            
            supported = []
            for cmd, desc in test_commands:
                response = self.connector.send_command(cmd)
                if response and "ERROR" not in response:
                    supported.append(desc)
                    
            info["supported_commands"] = supported
            
        except Exception as e:
            info["error"] = str(e)
            
        return info


class DeviceListWidget(QListWidget):
    """Кастомный виджет списка устройств"""
    
    device_selected = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка внешнего вида"""
        self.setMinimumHeight(150)
        self.setAlternatingRowColors(True)
        
        # Настройка шрифта
        font = QFont("Segoe UI", 9)
        self.setFont(font)
        
    def add_device(self, device_info: Dict):
        """Добавление устройства в список"""
        item = QListWidgetItem()
        
        # Создание кастомного виджета для элемента
        widget = self.create_device_widget(device_info)
        item.setSizeHint(widget.sizeHint())
        
        self.addItem(item)
        self.setItemWidget(item, widget)
        
        # Сохраняем информацию об устройстве
        item.setData(Qt.UserRole, device_info)
        
    def create_device_widget(self, device_info: Dict) -> QWidget:
        """Создание виджета для отображения устройства"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Основная информация
        info_layout = QHBoxLayout()
        
        # Иконка устройства
        icon_label = QLabel()
        icon_type = device_info.get("type", "unknown")
        
        if icon_type == "bluetooth":
            icon_path = "assets/icons/bluetooth.png"
        elif icon_type == "serial":
            icon_path = "assets/icons/usb.png"
        elif icon_type == "wifi":
            icon_path = "assets/icons/wifi.png"
        else:
            icon_path = "assets/icons/device.png"
            
        # Проверка существования иконки
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(pixmap)
        else:
            # Альтернативный текст
            icon_label.setText("●")
            icon_label.setFont(QFont("Arial", 16))
            
        info_layout.addWidget(icon_label)
        
        # Текстовая информация
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(5, 0, 0, 0)
        
        # Название устройства
        name_label = QLabel(device_info.get("name", "Неизвестное устройство"))
        name_font = QFont("Segoe UI", 10, QFont.Bold)
        name_label.setFont(name_font)
        
        # Адрес/порт
        address = device_info.get("address", "")
        address_label = QLabel(f"Адрес: {address}")
        address_label.setFont(QFont("Segoe UI", 8))
        address_label.setStyleSheet("color: #666;")
        
        # Индикатор ELM327
        if device_info.get("is_elm327", False):
            elm_label = QLabel("ELM327 Совместимый")
            elm_label.setFont(QFont("Segoe UI", 8, QFont.Bold))
            elm_label.setStyleSheet("color: #2E7D32; background-color: #E8F5E9; padding: 2px 5px; border-radius: 3px;")
            
            text_layout.addWidget(elm_label)
            
        text_layout.addWidget(name_label)
        text_layout.addWidget(address_label)
        
        info_layout.addWidget(text_widget, 1)
        
        layout.addLayout(info_layout)
        
        # Разделитель
        if self.count() > 0:
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setFrameShadow(QFrame.Sunken)
            separator.setStyleSheet("color: #E0E0E0;")
            layout.addWidget(separator)
            
        return widget
        
    def mouseDoubleClickEvent(self, event):
        """Обработка двойного клика по устройству"""
        item = self.itemAt(event.pos())
        if item:
            device_info = item.data(Qt.UserRole)
            if device_info:
                self.device_selected.emit(device_info)
                
        super().mouseDoubleClickEvent(event)


class ConnectionStatusWidget(QWidget):
    """Виджет статуса подключения"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.set_connection_status(False)
        
    def setup_ui(self):
        """Настройка интерфейса"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Индикатор статуса
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(16, 16)
        self.status_indicator.setStyleSheet("""
            QLabel {
                border-radius: 8px;
                background-color: #f44336;
                border: 2px solid #c62828;
            }
        """)
        
        # Текст статуса
        self.status_label = QLabel("Не подключено")
        self.status_label.setFont(QFont("Segoe UI", 10))
        
        # Информация о подключении
        self.connection_info = QLabel("")
        self.connection_info.setFont(QFont("Segoe UI", 9))
        self.connection_info.setStyleSheet("color: #666;")
        
        layout.addWidget(self.status_indicator)
        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(self.connection_info)
        
    def set_connection_status(self, connected: bool, info: Dict = None):
        """Установка статуса подключения"""
        if connected:
            self.status_indicator.setStyleSheet("""
                QLabel {
                    border-radius: 8px;
                    background-color: #4CAF50;
                    border: 2px solid #2E7D32;
                }
            """)
            self.status_label.setText("Подключено")
            self.status_label.setStyleSheet("color: #2E7D32; font-weight: bold;")
            
            if info:
                conn_type = info.get("type", "unknown").upper()
                address = info.get("address", "N/A")
                self.connection_info.setText(f"{conn_type}: {address}")
        else:
            self.status_indicator.setStyleSheet("""
                QLabel {
                    border-radius: 8px;
                    background-color: #f44336;
                    border: 2px solid #c62828;
                }
            """)
            self.status_label.setText("Не подключено")
            self.status_label.setStyleSheet("color: #f44336;")
            self.connection_info.setText("")


class ConnectionPanel(QWidget):
    """Панель подключения к ELM327"""
    
    connected = pyqtSignal(dict)
    disconnected = pyqtSignal()
    connection_error = pyqtSignal(str)
    devices_updated = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.connector = ELM327Connector()
        self.scanner_thread = None
        self.connection_worker = None
        self.current_connection_info = None
        self.logger = setup_logger()
        
        self.setup_ui()
        self.setup_connections()
        self.load_settings()
        
    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Виджет статуса подключения
        self.status_widget = ConnectionStatusWidget()
        main_layout.addWidget(self.status_widget)
        
        # Группа подключения
        connection_group = QGroupBox("Подключение к диагностическому сканеру")
        connection_group.setFont(QFont("Segoe UI", 10, QFont.Bold))
        connection_layout = QVBoxLayout(connection_group)
        
        # Вкладки типов подключения
        self.connection_tabs = QTabWidget()
        
        # Вкладка Bluetooth
        self.bluetooth_tab = self.create_bluetooth_tab()
        self.connection_tabs.addTab(self.bluetooth_tab, QIcon("assets/icons/bluetooth.png"), "Bluetooth")
        
        # Вкладка USB (COM-порт)
        self.serial_tab = self.create_serial_tab()
        self.connection_tabs.addTab(self.serial_tab, QIcon("assets/icons/usb.png"), "USB (COM)")
        
        # Вкладка WiFi
        self.wifi_tab = self.create_wifi_tab()
        self.connection_tabs.addTab(self.wifi_tab, QIcon("assets/icons/wifi.png"), "WiFi")
        
        connection_layout.addWidget(self.connection_tabs)
        
        # Кнопки управления
        button_layout = QHBoxLayout()
        
        self.scan_button = QPushButton(QIcon("assets/icons/scan.png"), "Сканировать устройства")
        self.scan_button.setFont(QFont("Segoe UI", 10))
        self.scan_button.setMinimumHeight(35)
        self.scan_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 5px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        
        self.connect_button = QPushButton(QIcon("assets/icons/connect.png"), "Подключиться")
        self.connect_button.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.connect_button.setMinimumHeight(35)
        self.connect_button.setEnabled(False)
        self.connect_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        
        self.disconnect_button = QPushButton(QIcon("assets/icons/disconnect.png"), "Отключиться")
        self.disconnect_button.setFont(QFont("Segoe UI", 10))
        self.disconnect_button.setMinimumHeight(35)
        self.disconnect_button.setEnabled(False)
        self.disconnect_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border-radius: 5px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        
        self.settings_button = QPushButton(QIcon("assets/icons/settings.png"), "Настройки")
        self.settings_button.setFont(QFont("Segoe UI", 10))
        self.settings_button.setMinimumHeight(35)
        self.settings_button.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                border-radius: 5px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #455A64;
            }
        """)
        
        button_layout.addWidget(self.scan_button)
        button_layout.addWidget(self.connect_button)
        button_layout.addWidget(self.disconnect_button)
        button_layout.addStretch()
        button_layout.addWidget(self.settings_button)
        
        connection_layout.addLayout(button_layout)
        
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        connection_layout.addWidget(self.progress_bar)
        
        # Панель логов
        log_group = QGroupBox("Лог подключения")
        log_group.setFont(QFont("Segoe UI", 10, QFont.Bold))
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 3px;
            }
        """)
        
        log_buttons_layout = QHBoxLayout()
        self.clear_log_button = QPushButton("Очистить лог")
        self.save_log_button = QPushButton("Сохранить лог")
        
        log_buttons_layout.addWidget(self.clear_log_button)
        log_buttons_layout.addWidget(self.save_log_button)
        log_buttons_layout.addStretch()
        
        log_layout.addWidget(self.log_text)
        log_layout.addLayout(log_buttons_layout)
        
        main_layout.addWidget(connection_group)
        main_layout.addWidget(log_group)
        
        # Таймер для периодических проверок
        self.connection_check_timer = QTimer()
        self.connection_check_timer.setInterval(5000)  # 5 секунд
        
    def create_bluetooth_tab(self) -> QWidget:
        """Создание вкладки Bluetooth"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Список устройств
        self.bluetooth_list = DeviceListWidget()
        layout.addWidget(QLabel("Найденные Bluetooth устройства:"))
        layout.addWidget(self.bluetooth_list)
        
        # Панель ручного ввода
        manual_group = QGroupBox("Ручное подключение")
        manual_layout = QFormLayout(manual_group)
        
        self.bt_address_input = QLineEdit()
        self.bt_address_input.setPlaceholderText("Введите MAC-адрес устройства (например: 00:11:22:33:44:55)")
        manual_layout.addRow("MAC-адрес:", self.bt_address_input)
        
        self.bt_pin_input = QLineEdit()
        self.bt_pin_input.setPlaceholderText("PIN-код (обычно 1234 или 0000)")
        self.bt_pin_input.setEchoMode(QLineEdit.Password)
        manual_layout.addRow("PIN-код:", self.bt_pin_input)
        
        layout.addWidget(manual_group)
        
        # Информация
        info_label = QLabel(
            "Для подключения:\n"
            "1. Включите Bluetooth на компьютере\n"
            "2. Включите зажигание в автомобиле\n"
            "3. Нажмите 'Сканировать устройства'\n"
            "4. Выберите устройство ELM327 из списка"
        )
        info_label.setFont(QFont("Segoe UI", 9))
        info_label.setStyleSheet("color: #666; padding: 10px; background-color: #FFF3E0; border-radius: 5px;")
        layout.addWidget(info_label)
        
        return tab
        
    def create_serial_tab(self) -> QWidget:
        """Создание вкладки Serial (COM-порт)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Выбор COM-порта
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("COM-порт:"))
        
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(150)
        port_layout.addWidget(self.port_combo)
        
        self.refresh_ports_button = QPushButton("Обновить список")
        port_layout.addWidget(self.refresh_ports_button)
        port_layout.addStretch()
        
        layout.addLayout(port_layout)
        
        # Настройки порта
        settings_group = QGroupBox("Настройки порта")
        settings_layout = QFormLayout(settings_group)
        
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems(["38400", "9600", "115200", "57600", "19200"])
        self.baudrate_combo.setCurrentText("38400")
        settings_layout.addRow("Скорость (baud):", self.baudrate_combo)
        
        self.data_bits_combo = QComboBox()
        self.data_bits_combo.addItems(["8", "7"])
        self.data_bits_combo.setCurrentText("8")
        settings_layout.addRow("Биты данных:", self.data_bits_combo)
        
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["NONE", "EVEN", "ODD"])
        settings_layout.addRow("Четность:", self.parity_combo)
        
        self.stop_bits_combo = QComboBox()
        self.stop_bits_combo.addItems(["1", "1.5", "2"])
        settings_layout.addRow("Стоп-биты:", self.stop_bits_combo)
        
        layout.addWidget(settings_group)
        
        # Тест подключения
        test_button = QPushButton("Тестировать подключение")
        test_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border-radius: 5px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        layout.addWidget(test_button)
        
        # Информация
        info_label = QLabel(
            "Для подключения:\n"
            "1. Подключите ELM327 к USB-порту\n"
            "2. Включите зажигание в автомобиле\n"
            "3. Нажмите 'Обновить список'\n"
            "4. Выберите COM-порт из списка"
        )
        info_label.setFont(QFont("Segoe UI", 9))
        info_label.setStyleSheet("color: #666; padding: 10px; background-color: #E3F2FD; border-radius: 5px;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        return tab
        
    def create_wifi_tab(self) -> QWidget:
        """Создание вкладки WiFi"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Список WiFi устройств
        self.wifi_list = DeviceListWidget()
        layout.addWidget(QLabel("Найденные WiFi устройства:"))
        layout.addWidget(self.wifi_list)
        
        # Ручной ввод
        manual_group = QGroupBox("Ручное подключение")
        manual_layout = QFormLayout(manual_group)
        
        self.wifi_ip_input = QLineEdit()
        self.wifi_ip_input.setPlaceholderText("Введите IP-адрес (например: 192.168.0.10)")
        manual_layout.addRow("IP-адрес:", self.wifi_ip_input)
        
        self.wifi_port_input = QLineEdit()
        self.wifi_port_input.setPlaceholderText("Порт (обычно 35000)")
        self.wifi_port_input.setText("35000")
        manual_layout.addRow("Порт:", self.wifi_port_input)
        
        layout.addWidget(manual_group)
        
        # Настройки сети
        network_group = QGroupBox("Настройки сети")
        network_layout = QFormLayout(network_group)
        
        self.network_timeout = QSpinBox()
        self.network_timeout.setRange(1, 30)
        self.network_timeout.setValue(5)
        self.network_timeout.setSuffix(" сек")
        network_layout.addRow("Таймаут:", self.network_timeout)
        
        self.auto_discovery = QCheckBox("Автоматическое обнаружение")
        self.auto_discovery.setChecked(True)
        network_layout.addRow(self.auto_discovery)
        
        layout.addWidget(network_group)
        
        # Информация
        info_label = QLabel(
            "Для подключения:\n"
            "1. Подключитесь к сети WiFi ELM327\n"
            "2. Включите зажигание в автомобиле\n"
            "3. Нажмите 'Сканировать устройства'\n"
            "4. Выберите устройство из списка"
        )
        info_label.setFont(QFont("Segoe UI", 9))
        info_label.setStyleSheet("color: #666; padding: 10px; background-color: #E8F5E9; border-radius: 5px;")
        layout.addWidget(info_label)
        
        return tab
        
    def setup_connections(self):
        """Настройка соединений между сигналами и слотами"""
        # Кнопки
        self.scan_button.clicked.connect(self.scan_devices)
        self.connect_button.clicked.connect(self.connect_device)
        self.disconnect_button.clicked.connect(self.disconnect_device)
        self.settings_button.clicked.connect(self.show_settings)
        self.refresh_ports_button.clicked.connect(self.refresh_serial_ports)
        self.clear_log_button.clicked.connect(self.clear_log)
        self.save_log_button.clicked.connect(self.save_log)
        
        # Списки устройств
        self.bluetooth_list.device_selected.connect(self.on_device_selected)
        self.wifi_list.device_selected.connect(self.on_device_selected)
        
        # Таймеры
        self.connection_check_timer.timeout.connect(self.check_connection_status)
        
        # Обновление списка портов при первом запуске
        QTimer.singleShot(100, self.refresh_serial_ports)
        
    def load_settings(self):
        """Загрузка сохраненных настроек"""
        try:
            # Здесь будет загрузка из файла конфигурации
            self.saved_devices = []
            self.preferred_connection = "bluetooth"
        except:
            self.saved_devices = []
            self.preferred_connection = "bluetooth"
            
    def log_message(self, message: str, message_type: str = "info"):
        """Добавление сообщения в лог"""
        timestamp = time.strftime("%H:%M:%S")
        
        # Цвета для разных типов сообщений
        colors = {
            "info": "#2196F3",
            "success": "#4CAF50",
            "error": "#f44336",
            "warning": "#FF9800",
            "debug": "#9C27B0"
        }
        
        color = colors.get(message_type, "#000000")
        
        html_message = f'<span style="color: #666;">[{timestamp}]</span> '
        html_message += f'<span style="color: {color};">{message}</span><br>'
        
        # Сохраняем текущую позицию прокрутки
        scrollbar = self.log_text.verticalScrollBar()
        at_bottom = scrollbar.value() == scrollbar.maximum()
        
        # Добавляем сообщение
        self.log_text.insertHtml(html_message)
        
        # Прокручиваем вниз если были внизу
        if at_bottom:
            scrollbar.setValue(scrollbar.maximum())
            
        # Логируем в файл
        log_message = f"[{timestamp}] {message}"
        if message_type == "error":
            self.logger.error(log_message)
        elif message_type == "warning":
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
            
    @pyqtSlot()
    def scan_devices(self):
        """Сканирование устройств"""
        current_tab = self.connection_tabs.currentIndex()
        
        if current_tab == 0:  # Bluetooth
            self.scan_bluetooth_devices()
        elif current_tab == 1:  # Serial
            self.refresh_serial_ports()
        elif current_tab == 2:  # WiFi
            self.scan_wifi_devices()
            
    def scan_bluetooth_devices(self):
        """Сканирование Bluetooth устройств"""
        self.log_message("Начато сканирование Bluetooth устройств...", "info")
        
        # Очистка списка
        self.bluetooth_list.clear()
        
        # Блокировка кнопок
        self.scan_button.setEnabled(False)
        self.scan_button.setText("Сканирование...")
        
        # Создание и запуск потока сканирования
        self.scanner_thread = DeviceScannerThread("bluetooth")
        self.scanner_thread.devices_found.connect(self.on_bluetooth_devices_found)
        self.scanner_thread.scan_complete.connect(self.on_scan_complete)
        self.scanner_thread.error_occurred.connect(self.on_scan_error)
        self.scanner_thread.start()
        
    def refresh_serial_ports(self):
        """Обновление списка COM-портов"""
        self.log_message("Обновление списка COM-портов...", "info")
        
        # Очистка списка
        self.port_combo.clear()
        
        try:
            import serial.tools.list_ports
            
            ports = list(serial.tools.list_ports.comports())
            
            if not ports:
                self.log_message("COM-порты не найдены", "warning")
                return
                
            for port in ports:
                description = port.description if port.description else port.device
                display_text = f"{port.device} - {description}"
                self.port_combo.addItem(display_text, port.device)
                
            self.log_message(f"Найдено {len(ports)} COM-порт(ов)", "success")
            
        except Exception as e:
            self.log_message(f"Ошибка при сканировании COM-портов: {e}", "error")
            
    def scan_wifi_devices(self):
        """Сканирование WiFi устройств"""
        self.log_message("Начато сканирование WiFi устройств...", "info")
        
        # Очистка списка
        self.wifi_list.clear()
        
        # Блокировка кнопок
        self.scan_button.setEnabled(False)
        self.scan_button.setText("Сканирование...")
        
        # Создание и запуск потока сканирования
        self.scanner_thread = DeviceScannerThread("wifi")
        self.scanner_thread.devices_found.connect(self.on_wifi_devices_found)
        self.scanner_thread.scan_complete.connect(self.on_scan_complete)
        self.scanner_thread.error_occurred.connect(self.on_scan_error)
        self.scanner_thread.start()
        
    @pyqtSlot(list)
    def on_bluetooth_devices_found(self, devices):
        """Обработка найденных Bluetooth устройств"""
        for device in devices:
            if device.get("type") == "status":
                # Это статусное сообщение
                self.log_message(device.get("name", ""), "info")
                continue
                
            self.bluetooth_list.add_device(device)
            
            if device.get("is_elm327", False):
                self.log_message(f"Найден ELM327: {device.get('name')} ({device.get('address')})", "success")
            else:
                self.log_message(f"Найдено устройство: {device.get('name')}", "info")
                
    @pyqtSlot(list)
    def on_wifi_devices_found(self, devices):
        """Обработка найденных WiFi устройств"""
        for device in devices:
            self.wifi_list.add_device(device)
            if device.get("is_elm327", False):
                self.log_message(f"Найден ELM327 WiFi: {device.get('name')}", "success")
                
    @pyqtSlot()
    def on_scan_complete(self):
        """Завершение сканирования"""
        self.scan_button.setEnabled(True)
        self.scan_button.setText("Сканировать устройства")
        self.log_message("Сканирование завершено", "info")
        
    @pyqtSlot(str)
    def on_scan_error(self, error_message):
        """Ошибка при сканировании"""
        self.log_message(f"Ошибка сканирования: {error_message}", "error")
        self.scan_button.setEnabled(True)
        self.scan_button.setText("Сканировать устройства")
        
    @pyqtSlot(dict)
    def on_device_selected(self, device_info):
        """Выбор устройства из списка"""
        current_tab = self.connection_tabs.currentIndex()
        
        if current_tab == 0:  # Bluetooth
            self.bt_address_input.setText(device_info.get("address", ""))
            self.log_message(f"Выбрано устройство: {device_info.get('name')}", "info")
        elif current_tab == 2:  # WiFi
            address = device_info.get("address", "")
            if ":" in address:
                ip, port = address.split(":")
                self.wifi_ip_input.setText(ip)
                self.wifi_port_input.setText(port)
            self.log_message(f"Выбрано устройство: {device_info.get('name')}", "info")
            
        self.connect_button.setEnabled(True)
        
    @pyqtSlot()
    def connect_device(self):
        """Подключение к выбранному устройству"""
        current_tab = self.connection_tabs.currentIndex()
        
        try:
            if current_tab == 0:  # Bluetooth
                self.connect_bluetooth()
            elif current_tab == 1:  # Serial
                self.connect_serial()
            elif current_tab == 2:  # WiFi
                self.connect_wifi()
                
        except Exception as e:
            self.log_message(f"Ошибка при подключении: {str(e)}", "error")
            self.connection_error.emit(str(e))
            
    def connect_bluetooth(self):
        """Подключение по Bluetooth"""
        address = self.bt_address_input.text().strip()
        
        if not address:
            QMessageBox.warning(self, "Ошибка", "Введите MAC-адрес устройства")
            return
            
        self.log_message(f"Подключение к Bluetooth устройству {address}...", "info")
        
        # Блокировка элементов UI
        self.set_ui_connecting_state(True)
        
        # Создание и запуск потока подключения
        self.connection_worker = ConnectionWorker(
            self.connector,
            ConnectionType.BLUETOOTH,
            address=address
        )
        
        self.setup_connection_worker_signals()
        self.connection_worker.start()
        
    def connect_serial(self):
        """Подключение по COM-порту"""
        port_index = self.port_combo.currentIndex()
        if port_index < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите COM-порт")
            return
            
        port = self.port_combo.currentData()
        if not port:
            # Пробуем извлечь из текста
            text = self.port_combo.currentText()
            port = text.split(" - ")[0] if " - " in text else text
            
        self.log_message(f"Подключение к COM-порту {port}...", "info")
        
        # Установка параметров порта
        try:
            baudrate = int(self.baudrate_combo.currentText())
            self.connector.baudrate = baudrate
        except:
            pass
            
        # Блокировка элементов UI
        self.set_ui_connecting_state(True)
        
        # Создание и запуск потока подключения
        self.connection_worker = ConnectionWorker(
            self.connector,
            ConnectionType.USB,
            port=port,
            address=port
        )
        
        self.setup_connection_worker_signals()
        self.connection_worker.start()
        
    def connect_wifi(self):
        """Подключение по WiFi"""
        ip = self.wifi_ip_input.text().strip()
        port = self.wifi_port_input.text().strip()
        
        if not ip:
            QMessageBox.warning(self, "Ошибка", "Введите IP-адрес устройства")
            return
            
        if not port:
            port = "35000"
            
        address = f"{ip}:{port}"
        
        self.log_message(f"Подключение к WiFi устройству {address}...", "info")
        
        # Блокировка элементов UI
        self.set_ui_connecting_state(True)
        
        # Создание и запуск потока подключения
        self.connection_worker = ConnectionWorker(
            self.connector,
            ConnectionType.WIFI,
            address=address
        )
        
        self.setup_connection_worker_signals()
        self.connection_worker.start()
        
    def setup_connection_worker_signals(self):
        """Настройка сигналов для потока подключения"""
        if self.connection_worker:
            self.connection_worker.connected.connect(self.on_connected)
            self.connection_worker.connection_failed.connect(self.on_connection_failed)
            self.connection_worker.connection_progress.connect(self.on_connection_progress)
            
    @pyqtSlot(dict)
    def on_connected(self, connection_info):
        """Обработка успешного подключения"""
        self.current_connection_info = connection_info
        
        # Обновление UI
        self.set_ui_connected_state(True)
        self.status_widget.set_connection_status(True, connection_info)
        
        # Логирование
        adapter_info = connection_info.get("adapter_info", {})
        firmware = adapter_info.get("firmware_version", "Неизвестно")
        self.log_message(f"Подключение установлено!", "success")
        self.log_message(f"Версия прошивки: {firmware}", "info")
        
        # Отправка сигнала о подключении
        self.connected.emit(connection_info)
        
        # Запуск таймера проверки соединения
        self.connection_check_timer.start()
        
    @pyqtSlot(str)
    def on_connection_failed(self, error_message):
        """Обработка неудачного подключения"""
        self.log_message(f"Ошибка подключения: {error_message}", "error")
        
        # Восстановление UI
        self.set_ui_connected_state(False)
        
        # Показать сообщение об ошибке
        QMessageBox.critical(self, "Ошибка подключения", error_message)
        
        # Отправка сигнала об ошибке
        self.connection_error.emit(error_message)
        
    @pyqtSlot(str, int)
    def on_connection_progress(self, message, progress):
        """Обновление прогресса подключения"""
        self.progress_bar.setValue(progress)
        self.progress_bar.setFormat(f"{message} - {progress}%")
        
        if not self.progress_bar.isVisible():
            self.progress_bar.setVisible(True)
            
        self.log_message(message, "info")
        
    def set_ui_connecting_state(self, connecting: bool):
        """Установка состояния UI при подключении"""
        self.scan_button.setEnabled(not connecting)
        self.connect_button.setEnabled(not connecting)
        self.disconnect_button.setEnabled(False)
        self.settings_button.setEnabled(not connecting)
        
        if connecting:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
    def set_ui_connected_state(self, connected: bool):
        """Установка состояния UI при подключении/отключении"""
        self.scan_button.setEnabled(not connected)
        self.connect_button.setEnabled(not connected)
        self.disconnect_button.setEnabled(connected)
        self.settings_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # Блокировка вкладок
        self.connection_tabs.setEnabled(not connected)
        
    @pyqtSlot()
    def disconnect_device(self):
        """Отключение от устройства"""
        reply = QMessageBox.question(
            self, "Отключение",
            "Вы уверены, что хотите отключиться от устройства?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.perform_disconnect()
            
    def perform_disconnect(self):
        """Выполнение отключения"""
        try:
            # Остановка таймера проверки
            self.connection_check_timer.stop()
            
            # Отключение от адаптера
            self.connector.disconnect()
            
            # Логирование
            self.log_message("Отключено от устройства", "info")
            
            # Обновление UI
            self.set_ui_connected_state(False)
            self.status_widget.set_connection_status(False)
            
            # Очистка информации о подключении
            self.current_connection_info = None
            
            # Отправка сигнала об отключении
            self.disconnected.emit()
            
        except Exception as e:
            self.log_message(f"Ошибка при отключении: {str(e)}", "error")
            
    @pyqtSlot()
    def check_connection_status(self):
        """Проверка статуса соединения"""
        if not self.connector.is_connected:
            self.log_message("Соединение разорвано", "error")
            self.perform_disconnect()
            return
            
        try:
            # Отправка тестовой команды
            response = self.connector.send_command("ATI", wait_time=0.1)
            
            if "ERROR" in response or "NO DATA" in response:
                self.log_message("Потеря связи с адаптером", "warning")
                
        except:
            self.log_message("Ошибка проверки связи", "warning")
            
    @pyqtSlot()
    def show_settings(self):
        """Показ окна настроек"""
        from ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(self)
        if dialog.exec_():
            # Сохранение настроек
            self.save_settings()
            self.log_message("Настройки сохранены", "success")
            
    @pyqtSlot()
    def clear_log(self):
        """Очистка лога"""
        self.log_text.clear()
        self.log_message("Лог очищен", "info")
        
    @pyqtSlot()
    def save_log(self):
        """Сохранение лога в файл"""
        try:
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"connection_log_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.log_text.toPlainText())
                
            self.log_message(f"Лог сохранен в файл: {filename}", "success")
            
        except Exception as e:
            self.log_message(f"Ошибка сохранения лога: {str(e)}", "error")
            
    def save_settings(self):
        """Сохранение настроек"""
        # Реализация сохранения настроек в файл
        pass
        
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        if self.connector.is_connected:
            self.perform_disconnect()
            
        if self.scanner_thread and self.scanner_thread.isRunning():
            self.scanner_thread.terminate()
            self.scanner_thread.wait()
            
        if self.connection_worker and self.connection_worker.isRunning():
            self.connection_worker.terminate()
            self.connection_worker.wait()
            
        super().closeEvent(event)
        
    def get_connection_info(self) -> Optional[Dict]:
        """Получение информации о текущем подключении"""
        return self.current_connection_info
        
    def is_connected(self) -> bool:
        """Проверка состояния подключения"""
        return self.connector.is_connected if hasattr(self, 'connector') else False