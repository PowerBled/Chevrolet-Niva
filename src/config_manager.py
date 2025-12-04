"""
Менеджер конфигурации приложения для диагностики Chevrolet Niva
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import shutil
from datetime import datetime
from dataclasses import dataclass, asdict, field
from PyQt5.QtCore import QSettings

class ConfigError(Exception):
    """Исключение для ошибок конфигурации"""
    pass

class VehicleModel(Enum):
    """Модели автомобилей Chevrolet Niva"""
    NIVA_2002_2009 = "2123"
    NIVA_2010_2020 = "21236"
    NIVA_1_8 = "2123-250"
    NIVA_MODERN = "2123M"
    NIVA_CUSTOM = "custom"

class ConnectionType(Enum):
    """Типы подключения"""
    BLUETOOTH = "bluetooth"
    USB = "serial"
    WIFI = "tcp"
    MOCK = "mock"  # Для тестирования без оборудования

class Language(Enum):
    """Поддерживаемые языки"""
    RUSSIAN = "ru"
    ENGLISH = "en"
    GERMAN = "de"

class Theme(Enum):
    """Темы оформления"""
    DARK = "dark"
    LIGHT = "light"
    SYSTEM = "system"

@dataclass
class VehicleProfile:
    """Профиль автомобиля"""
    id: str
    name: str
    model: VehicleModel
    vin: str = ""
    year: int = 0
    engine: str = ""
    engine_code: str = ""
    transmission: str = ""
    mileage: int = 0
    last_service: str = ""
    notes: str = ""
    
    # Диагностические настройки
    supported_ecus: List[str] = field(default_factory=lambda: ["ENGINE", "ABS", "AIRBAG"])
    custom_pids: Dict[str, str] = field(default_factory=dict)
    adaptation_settings: Dict[str, Any] = field(default_factory=dict)
    
    # Калибровочные данные
    calibration_data: Dict[str, Any] = field(default_factory=dict)
    
    # История диагностики
    diagnostic_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'id': self.id,
            'name': self.name,
            'model': self.model.value,
            'vin': self.vin,
            'year': self.year,
            'engine': self.engine,
            'engine_code': self.engine_code,
            'transmission': self.transmission,
            'mileage': self.mileage,
            'last_service': self.last_service,
            'notes': self.notes,
            'supported_ecus': self.supported_ecus,
            'custom_pids': self.custom_pids,
            'adaptation_settings': self.adaptation_settings,
            'calibration_data': self.calibration_data,
            'diagnostic_history': self.diagnostic_history
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VehicleProfile':
        """Создание из словаря"""
        model = VehicleModel(data.get('model', '21236'))
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            model=model,
            vin=data.get('vin', ''),
            year=data.get('year', 0),
            engine=data.get('engine', ''),
            engine_code=data.get('engine_code', ''),
            transmission=data.get('transmission', ''),
            mileage=data.get('mileage', 0),
            last_service=data.get('last_service', ''),
            notes=data.get('notes', ''),
            supported_ecus=data.get('supported_ecus', ["ENGINE", "ABS", "AIRBAG"]),
            custom_pids=data.get('custom_pids', {}),
            adaptation_settings=data.get('adaptation_settings', {}),
            calibration_data=data.get('calibration_data', {}),
            diagnostic_history=data.get('diagnostic_history', [])
        )

@dataclass
class ConnectionSettings:
    """Настройки подключения"""
    connection_type: ConnectionType
    bluetooth_address: str = ""
    com_port: str = "COM3"
    baud_rate: int = 38400
    wifi_ip: str = "192.168.0.10"
    wifi_port: int = 35000
    timeout: float = 2.0
    retry_count: int = 3
    auto_connect: bool = False
    auto_reconnect: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'connection_type': self.connection_type.value,
            'bluetooth_address': self.bluetooth_address,
            'com_port': self.com_port,
            'baud_rate': self.baud_rate,
            'wifi_ip': self.wifi_ip,
            'wifi_port': self.wifi_port,
            'timeout': self.timeout,
            'retry_count': self.retry_count,
            'auto_connect': self.auto_connect,
            'auto_reconnect': self.auto_reconnect
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConnectionSettings':
        """Создание из словаря"""
        conn_type = ConnectionType(data.get('connection_type', 'bluetooth'))
        return cls(
            connection_type=conn_type,
            bluetooth_address=data.get('bluetooth_address', ''),
            com_port=data.get('com_port', 'COM3'),
            baud_rate=data.get('baud_rate', 38400),
            wifi_ip=data.get('wifi_ip', '192.168.0.10'),
            wifi_port=data.get('wifi_port', 35000),
            timeout=data.get('timeout', 2.0),
            retry_count=data.get('retry_count', 3),
            auto_connect=data.get('auto_connect', False),
            auto_reconnect=data.get('auto_reconnect', True)
        )

@dataclass
class DiagnosticSettings:
    """Настройки диагностики"""
    # Общие настройки
    auto_save_logs: bool = True
    log_rotation_days: int = 30
    max_log_size_mb: int = 100
    diagnostic_timeout: int = 30
    
    # Настройки сканирования
    scan_all_modules: bool = True
    deep_scan: bool = False
    skip_optional_modules: bool = False
    module_scan_timeout: Dict[str, int] = field(default_factory=lambda: {
        "ENGINE": 5,
        "ABS": 3,
        "AIRBAG": 3,
        "IMMO": 2,
        "INSTRUMENT": 2,
        "AC": 2
    })
    
    # Настройки живых данных
    live_data_refresh_rate: int = 100  # мс
    chart_history_length: int = 1000
    save_live_data: bool = False
    live_data_sampling_rate: int = 1000  # мс
    
    # Настройки отображения
    show_raw_data: bool = False
    show_hex_data: bool = True
    auto_decode_responses: bool = True
    validate_responses: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'auto_save_logs': self.auto_save_logs,
            'log_rotation_days': self.log_rotation_days,
            'max_log_size_mb': self.max_log_size_mb,
            'diagnostic_timeout': self.diagnostic_timeout,
            'scan_all_modules': self.scan_all_modules,
            'deep_scan': self.deep_scan,
            'skip_optional_modules': self.skip_optional_modules,
            'module_scan_timeout': self.module_scan_timeout,
            'live_data_refresh_rate': self.live_data_refresh_rate,
            'chart_history_length': self.chart_history_length,
            'save_live_data': self.save_live_data,
            'live_data_sampling_rate': self.live_data_sampling_rate,
            'show_raw_data': self.show_raw_data,
            'show_hex_data': self.show_hex_data,
            'auto_decode_responses': self.auto_decode_responses,
            'validate_responses': self.validate_responses
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DiagnosticSettings':
        """Создание из словаря"""
        return cls(
            auto_save_logs=data.get('auto_save_logs', True),
            log_rotation_days=data.get('log_rotation_days', 30),
            max_log_size_mb=data.get('max_log_size_mb', 100),
            diagnostic_timeout=data.get('diagnostic_timeout', 30),
            scan_all_modules=data.get('scan_all_modules', True),
            deep_scan=data.get('deep_scan', False),
            skip_optional_modules=data.get('skip_optional_modules', False),
            module_scan_timeout=data.get('module_scan_timeout', {
                "ENGINE": 5, "ABS": 3, "AIRBAG": 3, "IMMO": 2, "INSTRUMENT": 2, "AC": 2
            }),
            live_data_refresh_rate=data.get('live_data_refresh_rate', 100),
            chart_history_length=data.get('chart_history_length', 1000),
            save_live_data=data.get('save_live_data', False),
            live_data_sampling_rate=data.get('live_data_sampling_rate', 1000),
            show_raw_data=data.get('show_raw_data', False),
            show_hex_data=data.get('show_hex_data', True),
            auto_decode_responses=data.get('auto_decode_responses', True),
            validate_responses=data.get('validate_responses', True)
        )

@dataclass
class UISettings:
    """Настройки пользовательского интерфейса"""
    # Общие настройки
    language: Language = Language.RUSSIAN
    theme: Theme = Theme.DARK
    font_size: int = 9
    font_family: str = "Segoe UI"
    show_tooltips: bool = True
    animation_enabled: bool = True
    confirm_exit: bool = True
    confirm_clear_dtcs: bool = True
    confirm_adaptation: bool = True
    
    # Настройки окон
    main_window_size: tuple = (1400, 800)
    main_window_position: tuple = (100, 100)
    maximize_on_start: bool = False
    restore_last_session: bool = True
    
    # Настройки панелей
    show_connection_panel: bool = True
    show_status_bar: bool = True
    show_toolbar: bool = True
    toolbar_icon_size: int = 32
    tab_position: str = "north"  # north, south, east, west
    
    # Настройки таблиц
    grid_lines: bool = True
    alternating_row_colors: bool = True
    auto_resize_columns: bool = True
    row_height: int = 24
    
    # Настройки графиков
    chart_theme: str = "default"
    chart_line_width: int = 2
    chart_point_size: int = 5
    show_chart_grid: bool = True
    show_chart_legend: bool = True
    chart_animation_duration: int = 200  # мс
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'language': self.language.value,
            'theme': self.theme.value,
            'font_size': self.font_size,
            'font_family': self.font_family,
            'show_tooltips': self.show_tooltips,
            'animation_enabled': self.animation_enabled,
            'confirm_exit': self.confirm_exit,
            'confirm_clear_dtcs': self.confirm_clear_dtcs,
            'confirm_adaptation': self.confirm_adaptation,
            'main_window_size': list(self.main_window_size),
            'main_window_position': list(self.main_window_position),
            'maximize_on_start': self.maximize_on_start,
            'restore_last_session': self.restore_last_session,
            'show_connection_panel': self.show_connection_panel,
            'show_status_bar': self.show_status_bar,
            'show_toolbar': self.show_toolbar,
            'toolbar_icon_size': self.toolbar_icon_size,
            'tab_position': self.tab_position,
            'grid_lines': self.grid_lines,
            'alternating_row_colors': self.alternating_row_colors,
            'auto_resize_columns': self.auto_resize_columns,
            'row_height': self.row_height,
            'chart_theme': self.chart_theme,
            'chart_line_width': self.chart_line_width,
            'chart_point_size': self.chart_point_size,
            'show_chart_grid': self.show_chart_grid,
            'show_chart_legend': self.show_chart_legend,
            'chart_animation_duration': self.chart_animation_duration
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UISettings':
        """Создание из словаря"""
        language = Language(data.get('language', 'ru'))
        theme = Theme(data.get('theme', 'dark'))
        
        return cls(
            language=language,
            theme=theme,
            font_size=data.get('font_size', 9),
            font_family=data.get('font_family', 'Segoe UI'),
            show_tooltips=data.get('show_tooltips', True),
            animation_enabled=data.get('animation_enabled', True),
            confirm_exit=data.get('confirm_exit', True),
            confirm_clear_dtcs=data.get('confirm_clear_dtcs', True),
            confirm_adaptation=data.get('confirm_adaptation', True),
            main_window_size=tuple(data.get('main_window_size', [1400, 800])),
            main_window_position=tuple(data.get('main_window_position', [100, 100])),
            maximize_on_start=data.get('maximize_on_start', False),
            restore_last_session=data.get('restore_last_session', True),
            show_connection_panel=data.get('show_connection_panel', True),
            show_status_bar=data.get('show_status_bar', True),
            show_toolbar=data.get('show_toolbar', True),
            toolbar_icon_size=data.get('toolbar_icon_size', 32),
            tab_position=data.get('tab_position', 'north'),
            grid_lines=data.get('grid_lines', True),
            alternating_row_colors=data.get('alternating_row_colors', True),
            auto_resize_columns=data.get('auto_resize_columns', True),
            row_height=data.get('row_height', 24),
            chart_theme=data.get('chart_theme', 'default'),
            chart_line_width=data.get('chart_line_width', 2),
            chart_point_size=data.get('chart_point_size', 5),
            show_chart_grid=data.get('show_chart_grid', True),
            show_chart_legend=data.get('show_chart_legend', True),
            chart_animation_duration=data.get('chart_animation_duration', 200)
        )

@dataclass
class ReportSettings:
    """Настройки отчетов"""
    # Общие настройки
    auto_generate_report: bool = True
    report_format: str = "pdf"  # pdf, html, docx, excel
    save_location: str = ""
    include_timestamp: bool = True
    compress_reports: bool = False
    
    # Содержимое отчета
    include_vehicle_info: bool = True
    include_dtc_list: bool = True
    include_live_data: bool = True
    include_graphs: bool = True
    include_sensor_data: bool = True
    include_adaptation_data: bool = True
    include_recommendations: bool = True
    include_raw_data: bool = False
    
    # Настройки PDF
    pdf_quality: str = "high"  # low, medium, high
    pdf_author: str = "Niva Diagnostic Pro"
    pdf_title_template: str = "Диагностический отчет {vehicle} {date}"
    
    # Настройки HTML
    html_template: str = "default"
    include_css: bool = True
    include_js: bool = False
    
    # Настройки Excel
    excel_auto_format: bool = True
    excel_include_charts: bool = True
    excel_protect_sheets: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'auto_generate_report': self.auto_generate_report,
            'report_format': self.report_format,
            'save_location': self.save_location,
            'include_timestamp': self.include_timestamp,
            'compress_reports': self.compress_reports,
            'include_vehicle_info': self.include_vehicle_info,
            'include_dtc_list': self.include_dtc_list,
            'include_live_data': self.include_live_data,
            'include_graphs': self.include_graphs,
            'include_sensor_data': self.include_sensor_data,
            'include_adaptation_data': self.include_adaptation_data,
            'include_recommendations': self.include_recommendations,
            'include_raw_data': self.include_raw_data,
            'pdf_quality': self.pdf_quality,
            'pdf_author': self.pdf_author,
            'pdf_title_template': self.pdf_title_template,
            'html_template': self.html_template,
            'include_css': self.include_css,
            'include_js': self.include_js,
            'excel_auto_format': self.excel_auto_format,
            'excel_include_charts': self.excel_include_charts,
            'excel_protect_sheets': self.excel_protect_sheets
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReportSettings':
        """Создание из словаря"""
        return cls(
            auto_generate_report=data.get('auto_generate_report', True),
            report_format=data.get('report_format', 'pdf'),
            save_location=data.get('save_location', ''),
            include_timestamp=data.get('include_timestamp', True),
            compress_reports=data.get('compress_reports', False),
            include_vehicle_info=data.get('include_vehicle_info', True),
            include_dtc_list=data.get('include_dtc_list', True),
            include_live_data=data.get('include_live_data', True),
            include_graphs=data.get('include_graphs', True),
            include_sensor_data=data.get('include_sensor_data', True),
            include_adaptation_data=data.get('include_adaptation_data', True),
            include_recommendations=data.get('include_recommendations', True),
            include_raw_data=data.get('include_raw_data', False),
            pdf_quality=data.get('pdf_quality', 'high'),
            pdf_author=data.get('pdf_author', 'Niva Diagnostic Pro'),
            pdf_title_template=data.get('pdf_title_template', 'Диагностический отчет {vehicle} {date}'),
            html_template=data.get('html_template', 'default'),
            include_css=data.get('include_css', True),
            include_js=data.get('include_js', False),
            excel_auto_format=data.get('excel_auto_format', True),
            excel_include_charts=data.get('excel_include_charts', True),
            excel_protect_sheets=data.get('excel_protect_sheets', False)
        )

@dataclass
class AdaptationSettings:
    """Настройки адаптации"""
    # Безопасность
    backup_before_adaptation: bool = True
    confirm_each_step: bool = True
    max_retry_count: int = 3
    rollback_on_failure: bool = True
    
    # Дроссельная заслонка
    throttle_adaptation_enabled: bool = True
    throttle_min_position: float = 0.0
    throttle_max_position: float = 100.0
    throttle_idle_position: float = 12.0
    throttle_learning_steps: int = 10
    
    # Холостой ход
    idle_speed_adaptation: bool = True
    target_idle_rpm: int = 850
    idle_adaptation_tolerance: int = 50
    idle_learning_time: int = 30  # секунд
    
    # Топливная коррекция
    fuel_trim_reset: bool = True
    long_term_trim_limit: float = 10.0
    short_term_trim_limit: float = 5.0
    fuel_trim_learning_distance: int = 100  # км
    
    # Иммобилайзер
    immo_learning_enabled: bool = True
    immo_key_count: int = 2
    immo_learning_timeout: int = 30
    
    # ABS
    abs_adaptation_enabled: bool = True
    abs_sensor_learning: bool = True
    abs_valve_test: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'backup_before_adaptation': self.backup_before_adaptation,
            'confirm_each_step': self.confirm_each_step,
            'max_retry_count': self.max_retry_count,
            'rollback_on_failure': self.rollback_on_failure,
            'throttle_adaptation_enabled': self.throttle_adaptation_enabled,
            'throttle_min_position': self.throttle_min_position,
            'throttle_max_position': self.throttle_max_position,
            'throttle_idle_position': self.throttle_idle_position,
            'throttle_learning_steps': self.throttle_learning_steps,
            'idle_speed_adaptation': self.idle_speed_adaptation,
            'target_idle_rpm': self.target_idle_rpm,
            'idle_adaptation_tolerance': self.idle_adaptation_tolerance,
            'idle_learning_time': self.idle_learning_time,
            'fuel_trim_reset': self.fuel_trim_reset,
            'long_term_trim_limit': self.long_term_trim_limit,
            'short_term_trim_limit': self.short_term_trim_limit,
            'fuel_trim_learning_distance': self.fuel_trim_learning_distance,
            'immo_learning_enabled': self.immo_learning_enabled,
            'immo_key_count': self.immo_key_count,
            'immo_learning_timeout': self.immo_learning_timeout,
            'abs_adaptation_enabled': self.abs_adaptation_enabled,
            'abs_sensor_learning': self.abs_sensor_learning,
            'abs_valve_test': self.abs_valve_test
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AdaptationSettings':
        """Создание из словаря"""
        return cls(
            backup_before_adaptation=data.get('backup_before_adaptation', True),
            confirm_each_step=data.get('confirm_each_step', True),
            max_retry_count=data.get('max_retry_count', 3),
            rollback_on_failure=data.get('rollback_on_failure', True),
            throttle_adaptation_enabled=data.get('throttle_adaptation_enabled', True),
            throttle_min_position=data.get('throttle_min_position', 0.0),
            throttle_max_position=data.get('throttle_max_position', 100.0),
            throttle_idle_position=data.get('throttle_idle_position', 12.0),
            throttle_learning_steps=data.get('throttle_learning_steps', 10),
            idle_speed_adaptation=data.get('idle_speed_adaptation', True),
            target_idle_rpm=data.get('target_idle_rpm', 850),
            idle_adaptation_tolerance=data.get('idle_adaptation_tolerance', 50),
            idle_learning_time=data.get('idle_learning_time', 30),
            fuel_trim_reset=data.get('fuel_trim_reset', True),
            long_term_trim_limit=data.get('long_term_trim_limit', 10.0),
            short_term_trim_limit=data.get('short_term_trim_limit', 5.0),
            fuel_trim_learning_distance=data.get('fuel_trim_learning_distance', 100),
            immo_learning_enabled=data.get('immo_learning_enabled', True),
            immo_key_count=data.get('immo_key_count', 2),
            immo_learning_timeout=data.get('immo_learning_timeout', 30),
            abs_adaptation_enabled=data.get('abs_adaptation_enabled', True),
            abs_sensor_learning=data.get('abs_sensor_learning', True),
            abs_valve_test=data.get('abs_valve_test', True)
        )

class ConfigManager:
    """Менеджер конфигурации приложения"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Инициализация менеджера конфигурации
        
        Args:
            config_dir: Директория для хранения конфигурации (по умолчанию ~/.niva_diagnostic)
        """
        self.config_dir = config_dir or self._get_default_config_dir()
        self._ensure_config_dir()
        
        # Основные конфигурационные файлы
        self.settings_file = Path(self.config_dir) / "settings.json"
        self.vehicle_profiles_file = Path(self.config_dir) / "vehicle_profiles.json"
        self.adaptation_maps_file = Path(self.config_dir) / "adaptation_maps.json"
        self.error_codes_file = Path(self.config_dir) / "error_codes.json"
        self.pid_database_file = Path(self.config_dir) / "pid_database.json"
        self.calibration_file = Path(self.config_dir) / "calibration_data.json"
        self.logs_dir = Path(self.config_dir) / "logs"
        self.reports_dir = Path(self.config_dir) / "reports"
        self.backup_dir = Path(self.config_dir) / "backups"
        
        # Инициализация структуры каталогов
        self._initialize_directories()
        
        # Загрузка конфигурации
        self.settings = self._load_settings()
        self.vehicle_profiles = self._load_vehicle_profiles()
        self.adaptation_maps = self._load_adaptation_maps()
        
        # Инициализация QSettings для хранения настроек Qt
        self.qsettings = QSettings("NivaDiagnostic", "NivaDiagnosticPro")
        
        # Флаг изменений
        self._modified = False
        
        # Текущий активный профиль
        self.active_vehicle_profile: Optional[VehicleProfile] = None
        
    def _get_default_config_dir(self) -> str:
        """Получение пути к директории конфигурации по умолчанию"""
        home = Path.home()
        
        # Для Windows
        if sys.platform == "win32":
            return str(home / "AppData" / "Local" / "NivaDiagnosticPro")
        # Для Linux
        elif sys.platform == "linux":
            return str(home / ".config" / "niva_diagnostic_pro")
        # Для macOS
        elif sys.platform == "darwin":
            return str(home / "Library" / "Application Support" / "NivaDiagnosticPro")
        else:
            return str(home / ".niva_diagnostic_pro")
    
    def _ensure_config_dir(self) -> None:
        """Создание директории конфигурации если она не существует"""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir, exist_ok=True)
    
    def _initialize_directories(self) -> None:
        """Инициализация всех необходимых директорий"""
        directories = [
            self.logs_dir,
            self.reports_dir,
            self.backup_dir,
            self.reports_dir / "pdf",
            self.reports_dir / "html",
            self.reports_dir / "excel",
            self.reports_dir / "docx",
            self.backup_dir / "profiles",
            self.backup_dir / "settings",
            self.backup_dir / "adaptation"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _load_settings(self) -> Dict[str, Any]:
        """Загрузка настроек из файла"""
        default_settings = self._get_default_settings()
        
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                
                # Объединение с настройками по умолчанию
                settings = self._merge_settings(default_settings, loaded_settings)
                return settings
                
            except (json.JSONDecodeError, IOError) as e:
                print(f"Ошибка загрузки настроек: {e}")
                self._create_backup(self.settings_file)
                return default_settings
        else:
            # Сохранение настроек по умолчанию
            self._save_settings(default_settings)
            return default_settings
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Получение настроек по умолчанию"""
        return {
            'version': '1.0.0',
            'last_modified': datetime.now().isoformat(),
            'application': {
                'name': 'Niva Diagnostic Pro',
                'version': '1.0.0',
                'company': 'Niva Diagnostic Team'
            },
            'connection': ConnectionSettings(ConnectionType.BLUETOOTH).to_dict(),
            'diagnostic': DiagnosticSettings().to_dict(),
            'ui': UISettings().to_dict(),
            'reports': ReportSettings().to_dict(),
            'adaptation': AdaptationSettings().to_dict(),
            'misc': {
                'check_for_updates': True,
                'auto_update': False,
                'send_usage_stats': False,
                'enable_debug_logging': False,
                'log_level': 'INFO'
            }
        }
    
    def _merge_settings(self, default: Dict[str, Any], loaded: Dict[str, Any]) -> Dict[str, Any]:
        """Рекурсивное объединение настроек"""
        result = default.copy()
        
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_settings(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _save_settings(self, settings: Dict[str, Any]) -> None:
        """Сохранение настроек в файл"""
        try:
            # Обновление времени изменения
            settings['last_modified'] = datetime.now().isoformat()
            
            # Создание временного файла
            temp_file = self.settings_file.with_suffix('.tmp')
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
            
            # Замена оригинального файла
            temp_file.replace(self.settings_file)
            
            # Создание резервной копии
            self._create_backup(self.settings_file, 'settings')
            
        except IOError as e:
            raise ConfigError(f"Ошибка сохранения настроек: {e}")
    
    def _load_vehicle_profiles(self) -> List[VehicleProfile]:
        """Загрузка профилей автомобилей"""
        if self.vehicle_profiles_file.exists():
            try:
                with open(self.vehicle_profiles_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                profiles = []
                for profile_data in data.get('profiles', []):
                    try:
                        profile = VehicleProfile.from_dict(profile_data)
                        profiles.append(profile)
                    except Exception as e:
                        print(f"Ошибка загрузки профиля: {e}")
                        continue
                
                return profiles
                
            except (json.JSONDecodeError, IOError) as e:
                print(f"Ошибка загрузки профилей: {e}")
                self._create_backup(self.vehicle_profiles_file)
                return []
        else:
            return []
    
    def _save_vehicle_profiles(self) -> None:
        """Сохранение профилей автомобилей"""
        try:
            data = {
                'last_modified': datetime.now().isoformat(),
                'profiles': [profile.to_dict() for profile in self.vehicle_profiles]
            }
            
            temp_file = self.vehicle_profiles_file.with_suffix('.tmp')
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            temp_file.replace(self.vehicle_profiles_file)
            
            # Создание резервной копии
            self._create_backup(self.vehicle_profiles_file, 'profiles')
            
        except IOError as e:
            raise ConfigError(f"Ошибка сохранения профилей: {e}")
    
    def _load_adaptation_maps(self) -> Dict[str, Any]:
        """Загрузка карт адаптации"""
        if self.adaptation_maps_file.exists():
            try:
                with open(self.adaptation_maps_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Ошибка загрузки карт адаптации: {e}")
                self._create_backup(self.adaptation_maps_file)
                return self._get_default_adaptation_maps()
        else:
            default_maps = self._get_default_adaptation_maps()
            self._save_adaptation_maps(default_maps)
            return default_maps
    
    def _get_default_adaptation_maps(self) -> Dict[str, Any]:
        """Получение карт адаптации по умолчанию"""
        return {
            'throttle_body': {
                '2123': {'min': 0.0, 'max': 95.0, 'idle': 12.0},
                '21236': {'min': 0.0, 'max': 96.0, 'idle': 11.5},
                '2123-250': {'min': 0.0, 'max': 97.0, 'idle': 11.0},
                '2123M': {'min': 0.0, 'max': 98.0, 'idle': 10.5}
            },
            'idle_speed': {
                '2123': {'min': 800, 'max': 900, 'target': 850},
                '21236': {'min': 800, 'max': 900, 'target': 850},
                '2123-250': {'min': 750, 'max': 850, 'target': 800},
                '2123M': {'min': 750, 'max': 850, 'target': 800}
            },
            'fuel_trim': {
                '2123': {'lt_trim_limit': 15.0, 'st_trim_limit': 8.0},
                '21236': {'lt_trim_limit': 12.0, 'st_trim_limit': 6.0},
                '2123-250': {'lt_trim_limit': 10.0, 'st_trim_limit': 5.0},
                '2123M': {'lt_trim_limit': 8.0, 'st_trim_limit': 4.0}
            }
        }
    
    def _save_adaptation_maps(self, maps: Dict[str, Any]) -> None:
        """Сохранение карт адаптации"""
        try:
            temp_file = self.adaptation_maps_file.with_suffix('.tmp')
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(maps, f, ensure_ascii=False, indent=4)
            
            temp_file.replace(self.adaptation_maps_file)
            
        except IOError as e:
            raise ConfigError(f"Ошибка сохранения карт адаптации: {e}")
    
    def _create_backup(self, file_path: Path, category: str = 'general') -> None:
        """Создание резервной копии файла"""
        if not file_path.exists():
            return
        
        try:
            backup_dir = self.backup_dir / category
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
            backup_path = backup_dir / backup_name
            
            shutil.copy2(file_path, backup_path)
            
            # Удаление старых резервных копий (сохраняем только последние 10)
            backups = sorted(backup_dir.glob(f"{file_path.stem}_*{file_path.suffix}"))
            if len(backups) > 10:
                for old_backup in backups[:-10]:
                    old_backup.unlink()
                    
        except Exception as e:
            print(f"Ошибка создания резервной копии: {e}")
    
    # Публичные методы
    
    def save(self) -> None:
        """Сохранение всех изменений"""
        try:
            self._save_settings(self.settings)
            self._save_vehicle_profiles()
            self._save_adaptation_maps(self.adaptation_maps)
            self._modified = False
        except Exception as e:
            raise ConfigError(f"Ошибка сохранения конфигурации: {e}")
    
    def reload(self) -> None:
        """Перезагрузка конфигурации из файлов"""
        self.settings = self._load_settings()
        self.vehicle_profiles = self._load_vehicle_profiles()
        self.adaptation_maps = self._load_adaptation_maps()
        self._modified = False
    
    def reset_to_defaults(self) -> None:
        """Сброс настроек к значениям по умолчанию"""
        self.settings = self._get_default_settings()
        self.vehicle_profiles = []
        self.adaptation_maps = self._get_default_adaptation_maps()
        self.active_vehicle_profile = None
        self._modified = True
        self.save()
    
    def export_config(self, export_path: str) -> None:
        """Экспорт всей конфигурации"""
        export_dir = Path(export_path)
        export_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Копирование всех конфигурационных файлов
            files_to_copy = [
                self.settings_file,
                self.vehicle_profiles_file,
                self.adaptation_maps_file,
                self.error_codes_file,
                self.pid_database_file,
                self.calibration_file
            ]
            
            for file_path in files_to_copy:
                if file_path.exists():
                    shutil.copy2(file_path, export_dir / file_path.name)
            
            # Архивирование
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"niva_diagnostic_config_{timestamp}.zip"
            archive_path = export_dir.parent / archive_name
            
            shutil.make_archive(
                str(archive_path.with_suffix('')),
                'zip',
                str(export_dir)
            )
            
            # Удаление временной директории
            shutil.rmtree(export_dir)
            
        except Exception as e:
            raise ConfigError(f"Ошибка экспорта конфигурации: {e}")
    
    def import_config(self, import_path: str) -> None:
        """Импорт конфигурации"""
        import_file = Path(import_path)
        
        if not import_file.exists():
            raise ConfigError(f"Файл не найден: {import_path}")
        
        try:
            # Создание резервной копии текущей конфигурации
            backup_dir = self.backup_dir / "import_backup" / datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Резервное копирование текущих файлов
            files_to_backup = [
                self.settings_file,
                self.vehicle_profiles_file,
                self.adaptation_maps_file
            ]
            
            for file_path in files_to_backup:
                if file_path.exists():
                    shutil.copy2(file_path, backup_dir / file_path.name)
            
            # Распаковка архива
            temp_dir = Path(self.config_dir) / "temp_import"
            temp_dir.mkdir(exist_ok=True)
            
            shutil.unpack_archive(import_path, str(temp_dir), 'zip')
            
            # Копирование файлов
            for file_name in os.listdir(temp_dir):
                source_file = temp_dir / file_name
                dest_file = Path(self.config_dir) / file_name
                
                if source_file.is_file():
                    shutil.copy2(source_file, dest_file)
            
            # Очистка
            shutil.rmtree(temp_dir)
            
            # Перезагрузка конфигурации
            self.reload()
            
        except Exception as e:
            raise ConfigError(f"Ошибка импорта конфигурации: {e}")
    
    # Методы для работы с настройками
    
    def get_connection_settings(self) -> ConnectionSettings:
        """Получение настроек подключения"""
        return ConnectionSettings.from_dict(self.settings['connection'])
    
    def set_connection_settings(self, settings: ConnectionSettings) -> None:
        """Установка настроек подключения"""
        self.settings['connection'] = settings.to_dict()
        self._modified = True
    
    def get_diagnostic_settings(self) -> DiagnosticSettings:
        """Получение настроек диагностики"""
        return DiagnosticSettings.from_dict(self.settings['diagnostic'])
    
    def set_diagnostic_settings(self, settings: DiagnosticSettings) -> None:
        """Установка настроек диагностики"""
        self.settings['diagnostic'] = settings.to_dict()
        self._modified = True
    
    def get_ui_settings(self) -> UISettings:
        """Получение настроек интерфейса"""
        return UISettings.from_dict(self.settings['ui'])
    
    def set_ui_settings(self, settings: UISettings) -> None:
        """Установка настроек интерфейса"""
        self.settings['ui'] = settings.to_dict()
        self._modified = True
    
    def get_report_settings(self) -> ReportSettings:
        """Получение настроек отчетов"""
        return ReportSettings.from_dict(self.settings['reports'])
    
    def set_report_settings(self, settings: ReportSettings) -> None:
        """Установка настроек отчетов"""
        self.settings['reports'] = settings.to_dict()
        self._modified = True
    
    def get_adaptation_settings(self) -> AdaptationSettings:
        """Получение настроек адаптации"""
        return AdaptationSettings.from_dict(self.settings['adaptation'])
    
    def set_adaptation_settings(self, settings: AdaptationSettings) -> None:
        """Установка настроек адаптации"""
        self.settings['adaptation'] = settings.to_dict()
        self._modified = True
    
    # Методы для работы с профилями автомобилей
    
    def get_vehicle_profiles(self) -> List[VehicleProfile]:
        """Получение списка профилей автомобилей"""
        return self.vehicle_profiles.copy()
    
    def get_vehicle_profile(self, profile_id: str) -> Optional[VehicleProfile]:
        """Получение профиля автомобиля по ID"""
        for profile in self.vehicle_profiles:
            if profile.id == profile_id:
                return profile
        return None
    
    def add_vehicle_profile(self, profile: VehicleProfile) -> None:
        """Добавление нового профиля автомобиля"""
        # Генерация ID если не указан
        if not profile.id:
            profile.id = self._generate_profile_id(profile.name)
        
        # Проверка уникальности ID
        for existing in self.vehicle_profiles:
            if existing.id == profile.id:
                raise ConfigError(f"Профиль с ID {profile.id} уже существует")
        
        self.vehicle_profiles.append(profile)
        self._modified = True
    
    def update_vehicle_profile(self, profile_id: str, updated_profile: VehicleProfile) -> None:
        """Обновление профиля автомобиля"""
        for i, profile in enumerate(self.vehicle_profiles):
            if profile.id == profile_id:
                self.vehicle_profiles[i] = updated_profile
                self._modified = True
                return
        
        raise ConfigError(f"Профиль с ID {profile_id} не найден")
    
    def delete_vehicle_profile(self, profile_id: str) -> None:
        """Удаление профиля автомобиля"""
        for i, profile in enumerate(self.vehicle_profiles):
            if profile.id == profile_id:
                # Создание резервной копии
                backup_file = self.backup_dir / "deleted_profiles" / f"{profile_id}.json"
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(profile.to_dict(), f, ensure_ascii=False, indent=4)
                
                del self.vehicle_profiles[i]
                self._modified = True
                return
        
        raise ConfigError(f"Профиль с ID {profile_id} не найден")
    
    def set_active_vehicle_profile(self, profile_id: str) -> None:
        """Установка активного профиля автомобиля"""
        profile = self.get_vehicle_profile(profile_id)
        if profile:
            self.active_vehicle_profile = profile
            # Сохранение в QSettings для восстановления при следующем запуске
            self.qsettings.setValue("active_vehicle_profile", profile_id)
        else:
            raise ConfigError(f"Профиль с ID {profile_id} не найден")
    
    def get_active_vehicle_profile(self) -> Optional[VehicleProfile]:
        """Получение активного профиля автомобиля"""
        if self.active_vehicle_profile:
            return self.active_vehicle_profile
        
        # Попытка загрузки из QSettings
        profile_id = self.qsettings.value("active_vehicle_profile", "")
        if profile_id:
            return self.get_vehicle_profile(profile_id)
        
        return None
    
    def _generate_profile_id(self, name: str) -> str:
        """Генерация уникального ID для профиля"""
        base_id = name.lower().replace(' ', '_')
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{base_id}_{timestamp}"
    
    # Методы для работы с картами адаптации
    
    def get_adaptation_maps(self) -> Dict[str, Any]:
        """Получение карт адаптации"""
        return self.adaptation_maps.copy()
    
    def get_adaptation_map_for_model(self, model: str, map_type: str) -> Dict[str, Any]:
        """Получение карты адаптации для конкретной модели"""
        if map_type in self.adaptation_maps and model in self.adaptation_maps[map_type]:
            return self.adaptation_maps[map_type][model]
        return {}
    
    def update_adaptation_maps(self, maps: Dict[str, Any]) -> None:
        """Обновление карт адаптации"""
        self.adaptation_maps = maps
        self._save_adaptation_maps(maps)
    
    # Методы для работы с путями
    
    def get_logs_dir(self) -> str:
        """Получение пути к директории логов"""
        return str(self.logs_dir)
    
    def get_reports_dir(self) -> str:
        """Получение пути к директории отчетов"""
        return str(self.reports_dir)
    
    def get_backup_dir(self) -> str:
        """Получение пути к директории резервных копий"""
        return str(self.backup_dir)
    
    def get_config_dir(self) -> str:
        """Получение пути к директории конфигурации"""
        return str(self.config_dir)
    
    # Вспомогательные методы
    
    def is_modified(self) -> bool:
        """Проверка наличия несохраненных изменений"""
        return self._modified
    
    def get_version(self) -> str:
        """Получение версии конфигурации"""
        return self.settings.get('version', '1.0.0')
    
    def get_last_modified(self) -> datetime:
        """Получение времени последнего изменения"""
        try:
            return datetime.fromisoformat(self.settings.get('last_modified', ''))
        except ValueError:
            return datetime.now()
    
    def validate(self) -> List[str]:
        """Валидация конфигурации"""
        errors = []
        
        # Проверка обязательных полей
        required_sections = ['connection', 'diagnostic', 'ui', 'reports', 'adaptation']
        for section in required_sections:
            if section not in self.settings:
                errors.append(f"Отсутствует обязательная секция: {section}")
        
        # Проверка уникальности ID профилей
        profile_ids = set()
        for profile in self.vehicle_profiles:
            if profile.id in profile_ids:
                errors.append(f"Дублирующийся ID профиля: {profile.id}")
            profile_ids.add(profile.id)
        
        return errors
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> None:
        """Очистка старых данных"""
        cutoff_time = datetime.now().timestamp() - (days_to_keep * 86400)
        
        # Очистка старых логов
        for log_file in self.logs_dir.glob("*.log"):
            if log_file.stat().st_mtime < cutoff_time:
                log_file.unlink()
        
        # Очистка старых отчетов
        for report_dir in [self.reports_dir / "pdf", self.reports_dir / "html", 
                          self.reports_dir / "excel", self.reports_dir / "docx"]:
            for report_file in report_dir.glob("*"):
                if report_file.stat().st_mtime < cutoff_time:
                    report_file.unlink()
        
        # Очистка старых резервных копий
        for backup_type in ["settings", "profiles", "adaptation"]:
            backup_dir = self.backup_dir / backup_type
            if backup_dir.exists():
                for backup_file in backup_dir.glob("*"):
                    if backup_file.stat().st_mtime < cutoff_time:
                        backup_file.unlink()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики конфигурации"""
        return {
            'total_vehicle_profiles': len(self.vehicle_profiles),
            'total_log_files': len(list(self.logs_dir.glob("*.log"))),
            'total_report_files': sum(len(list(d.glob("*"))) for d in self.reports_dir.iterdir() if d.is_dir()),
            'total_backup_files': sum(len(list(d.glob("*"))) for d in self.backup_dir.iterdir() if d.is_dir()),
            'config_size_mb': sum(f.stat().st_size for f in Path(self.config_dir).rglob("*") if f.is_file()) / 1024 / 1024,
            'last_modified': self.get_last_modified().isoformat(),
            'version': self.get_version(),
            'active_profile': self.active_vehicle_profile.name if self.active_vehicle_profile else None
        }
    
    def __str__(self) -> str:
        """Строковое представление"""
        stats = self.get_statistics()
        return (f"ConfigManager(profiles={stats['total_vehicle_profiles']}, "
                f"version={stats['version']}, active={stats['active_profile']})")