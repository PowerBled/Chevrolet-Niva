"""
Комплексная система логирования для приложения диагностики Chevrolet Niva.
Поддерживает многоуровневое логирование, ротацию логов и различные обработчики.
"""

import os
import sys
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
import json
import traceback
import inspect

# Константы для настройки логгера
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
DEFAULT_LOG_LEVEL = logging.INFO

# Цвета для консольного вывода (если поддерживается)
COLORS = {
    'DEBUG': '\033[94m',      # Синий
    'INFO': '\033[92m',       # Зеленый
    'WARNING': '\033[93m',    # Желтый
    'ERROR': '\033[91m',      # Красный
    'CRITICAL': '\033[95m',   # Пурпурный
    'RESET': '\033[0m'        # Сброс цвета
}

class ColorFormatter(logging.Formatter):
    """Форматтер с цветным выводом для консоли"""
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        super().__init__(fmt, datefmt)
        self.use_color = sys.platform != 'win32'  # Цвета только для Unix-систем
        
    def format(self, record: logging.LogRecord) -> str:
        """Форматирование записи с цветом"""
        if self.use_color and record.levelname in COLORS:
            color_start = COLORS[record.levelname]
            color_end = COLORS['RESET']
            
            # Сохраняем оригинальное сообщение
            original_msg = record.getMessage()
            
            # Создаем копию записи для форматирования
            record_copy = logging.LogRecord(
                name=record.name,
                level=record.levelno,
                pathname=record.pathname,
                lineno=record.lineno,
                msg=f"{color_start}{original_msg}{color_end}",
                args=record.args,
                exc_info=record.exc_info
            )
            
            # Копируем остальные атрибуты
            for attr in ['created', 'msecs', 'relativeCreated', 'thread', 'threadName', 
                        'process', 'processName', 'funcName', 'stack_info']:
                setattr(record_copy, attr, getattr(record, attr))
                
            return super().format(record_copy)
        
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """Форматтер для вывода логов в формате JSON"""
    
    def __init__(self, include_context: bool = True):
        super().__init__()
        self.include_context = include_context
        
    def format(self, record: logging.LogRecord) -> str:
        """Форматирование записи в JSON"""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.threadName,
            'process': record.processName
        }
        
        # Добавление информации об исключении
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.format_exception(record.exc_info)
            }
            
        # Добавление дополнительных атрибутов
        if hasattr(record, 'custom_data'):
            log_entry['custom_data'] = record.custom_data
            
        # Добавление контекста вызова
        if self.include_context and record.levelno >= logging.WARNING:
            log_entry['call_context'] = self.get_call_context()
            
        return json.dumps(log_entry, ensure_ascii=False, indent=2)
    
    def format_exception(self, exc_info: Any) -> List[str]:
        """Форматирование трассировки стека"""
        return traceback.format_exception(*exc_info)
    
    def get_call_context(self) -> Dict[str, Any]:
        """Получение контекста вызова функции"""
        stack = inspect.stack()
        
        # Пропускаем текущую функцию и format
        call_stack = []
        for frame_info in stack[3:8]:  # Берем 5 кадров
            frame = frame_info.frame
            call_stack.append({
                'file': frame_info.filename,
                'line': frame_info.lineno,
                'function': frame_info.function,
                'code': frame_info.code_context[0].strip() if frame_info.code_context else None
            })
            
        return {'call_stack': call_stack}


class DiagnosticFileHandler(logging.handlers.RotatingFileHandler):
    """Обработчик файлов логов с ротацией и архивированием"""
    
    def __init__(self, 
                 filename: str, 
                 max_bytes: int = 10 * 1024 * 1024,  # 10 MB
                 backup_count: int = 5,
                 encoding: str = 'utf-8'):
        
        # Создаем директорию для логов, если ее нет
        log_dir = os.path.dirname(filename)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            
        super().__init__(
            filename=filename,
            mode='a',
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding=encoding,
            delay=False
        )
        
        # Специальный форматтер для файлов
        self.setFormatter(logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        
    def doRollover(self) -> None:
        """Выполнение ротации логов с добавлением временной метки"""
        if self.stream:
            self.stream.close()
            self.stream = None
            
        # Переименование файлов
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = f"{self.baseFilename}.{i}"
                dfn = f"{self.baseFilename}.{i + 1}"
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
                    
            # Переименование текущего файла с датой
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            dfn = f"{self.baseFilename}.1"
            if os.path.exists(dfn):
                os.remove(dfn)
            if os.path.exists(self.baseFilename):
                os.rename(self.baseFilename, dfn)
                
        # Создание нового файла
        if not self.delay:
            self.stream = self._open()


class DiagnosticFilter(logging.Filter):
    """Фильтр для диагностических логов"""
    
    def __init__(self, name: str = '', min_level: int = logging.DEBUG):
        super().__init__(name)
        self.min_level = min_level
        
    def filter(self, record: logging.LogRecord) -> bool:
        """Фильтрация записей логов"""
        # Проверка минимального уровня
        if record.levelno < self.min_level:
            return False
            
        # Фильтрация по имени логгера
        if self.name and not record.name.startswith(self.name):
            return False
            
        # Дополнительная фильтрация для диагностики
        if hasattr(record, 'diagnostic_source'):
            # Здесь можно добавить специфичную логику фильтрации
            pass
            
        return True


class DatabaseLogHandler(logging.Handler):
    """Обработчик для записи логов в базу данных"""
    
    def __init__(self, db_config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.db_config = db_config or {}
        self.records_buffer = []
        self.buffer_size = 100
        
    def emit(self, record: logging.LogRecord) -> None:
        """Запись лога в буфер"""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'line': record.lineno,
            'exception': self.format_exception(record.exc_info) if record.exc_info else None
        }
        
        self.records_buffer.append(log_entry)
        
        # Сохранение в БД при достижении размера буфера
        if len(self.records_buffer) >= self.buffer_size:
            self.flush()
            
    def flush(self) -> None:
        """Сохранение буфера в базу данных"""
        if not self.records_buffer:
            return
            
        try:
            # Здесь реализуется сохранение в базу данных
            # Например, с использованием SQLAlchemy или других ORM
            self.save_to_database(self.records_buffer)
            self.records_buffer.clear()
            
        except Exception as e:
            print(f"Ошибка сохранения логов в БД: {e}", file=sys.stderr)
            
    def save_to_database(self, records: List[Dict[str, Any]]) -> None:
        """Сохранение записей в базу данных"""
        # Реализация зависит от используемой БД
        # Пример для SQLite:
        # import sqlite3
        # conn = sqlite3.connect(self.db_config.get('database', 'diagnostics.db'))
        # cursor = conn.cursor()
        # ...
        pass
    
    def close(self) -> None:
        """Закрытие обработчика с сохранением оставшихся логов"""
        self.flush()
        super().close()


class DiagnosticLogger:
    """Основной класс для управления логгерами приложения"""
    
    _instance = None
    _loggers: Dict[str, logging.Logger] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.config = self.load_config()
            self.setup_default_logger()
            
    @staticmethod
    def load_config() -> Dict[str, Any]:
        """Загрузка конфигурации логгера из файла"""
        config_path = Path('config') / 'logging.json'
        
        default_config = {
            'log_level': 'INFO',
            'console_enabled': True,
            'file_enabled': True,
            'json_enabled': False,
            'database_enabled': False,
            'log_directory': 'logs',
            'max_file_size_mb': 10,
            'backup_count': 5,
            'enable_colors': sys.platform != 'win32',
            'log_format': DEFAULT_LOG_FORMAT,
            'date_format': DEFAULT_DATE_FORMAT
        }
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"Ошибка загрузки конфигурации логгера: {e}", file=sys.stderr)
                
        return default_config
    
    def setup_default_logger(self) -> None:
        """Настройка корневого логгера по умолчанию"""
        root_logger = logging.getLogger()
        root_logger.setLevel(self.get_log_level())
        
        # Очистка существующих обработчиков
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
        # Добавление обработчиков в зависимости от конфигурации
        if self.config.get('console_enabled', True):
            self.add_console_handler(root_logger)
            
        if self.config.get('file_enabled', True):
            self.add_file_handler(root_logger)
            
        if self.config.get('json_enabled', False):
            self.add_json_handler(root_logger)
            
        if self.config.get('database_enabled', False):
            self.add_database_handler(root_logger)
            
        # Добавление общего фильтра
        diagnostic_filter = DiagnosticFilter(min_level=root_logger.level)
        root_logger.addFilter(diagnostic_filter)
        
    def get_log_level(self) -> int:
        """Получение уровня логирования из конфигурации"""
        level_str = self.config.get('log_level', 'INFO').upper()
        return getattr(logging, level_str, logging.INFO)
    
    def add_console_handler(self, logger: logging.Logger) -> None:
        """Добавление обработчика для консоли"""
        console_handler = logging.StreamHandler(sys.stdout)
        
        if self.config.get('enable_colors', True):
            formatter = ColorFormatter(
                fmt=self.config.get('log_format', DEFAULT_LOG_FORMAT),
                datefmt=self.config.get('date_format', DEFAULT_DATE_FORMAT)
            )
        else:
            formatter = logging.Formatter(
                fmt=self.config.get('log_format', DEFAULT_LOG_FORMAT),
                datefmt=self.config.get('date_format', DEFAULT_DATE_FORMAT)
            )
            
        console_handler.setFormatter(formatter)
        
        # Фильтр для консоли (например, только INFO и выше)
        console_filter = logging.Filter()
        console_filter.filter = lambda record: record.levelno >= logging.INFO
        console_handler.addFilter(console_filter)
        
        logger.addHandler(console_handler)
    
    def add_file_handler(self, logger: logging.Logger) -> None:
        """Добавление обработчика для файлов"""
        log_dir = self.config.get('log_directory', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Файл для основных логов
        main_log_file = os.path.join(log_dir, 'diagnostic.log')
        
        max_bytes = self.config.get('max_file_size_mb', 10) * 1024 * 1024
        backup_count = self.config.get('backup_count', 5)
        
        file_handler = DiagnosticFileHandler(
            filename=main_log_file,
            max_bytes=max_bytes,
            backup_count=backup_count,
            encoding='utf-8'
        )
        
        logger.addHandler(file_handler)
        
        # Дополнительный файл для ошибок
        error_log_file = os.path.join(log_dir, 'errors.log')
        error_handler = DiagnosticFileHandler(
            filename=error_log_file,
            max_bytes=max_bytes,
            backup_count=backup_count
        )
        error_handler.setLevel(logging.WARNING)
        
        # Специальный форматтер для ошибок
        error_formatter = logging.Formatter(
            fmt='%(asctime)s | ERROR | %(name)s | %(message)s\n%(exc_info)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        error_handler.setFormatter(error_formatter)
        
        logger.addHandler(error_handler)
    
    def add_json_handler(self, logger: logging.Logger) -> None:
        """Добавление обработчика для JSON логов"""
        log_dir = self.config.get('log_directory', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        json_log_file = os.path.join(log_dir, 'diagnostic.json')
        json_handler = logging.FileHandler(json_log_file, encoding='utf-8')
        json_handler.setFormatter(JSONFormatter())
        
        logger.addHandler(json_handler)
    
    def add_database_handler(self, logger: logging.Logger) -> None:
        """Добавление обработчика для базы данных"""
        db_config = self.config.get('database_config', {})
        db_handler = DatabaseLogHandler(db_config)
        
        logger.addHandler(db_handler)
    
    def get_logger(self, name: str, level: Optional[int] = None) -> logging.Logger:
        """Получение или создание именованного логгера"""
        if name not in self._loggers:
            logger = logging.getLogger(name)
            
            if level is not None:
                logger.setLevel(level)
            else:
                logger.setLevel(self.get_log_level())
                
            # Наследование обработчиков от корневого логгера
            logger.propagate = True
            
            self._loggers[name] = logger
            
        return self._loggers[name]
    
    def setup_module_logger(self, module_name: str, 
                           level: Optional[int] = None,
                           handlers: Optional[List[logging.Handler]] = None) -> logging.Logger:
        """Настройка логгера для конкретного модуля"""
        logger = self.get_logger(module_name, level)
        
        if handlers:
            for handler in handlers:
                logger.addHandler(handler)
                
        return logger
    
    def log_diagnostic_data(self, 
                           logger_name: str,
                           message: str,
                           data: Dict[str, Any],
                           level: int = logging.INFO) -> None:
        """Логирование диагностических данных с дополнительной информацией"""
        logger = self.get_logger(logger_name)
        
        # Создание записи с дополнительными данными
        extra_data = {'custom_data': data}
        
        if level == logging.DEBUG:
            logger.debug(message, extra=extra_data)
        elif level == logging.INFO:
            logger.info(message, extra=extra_data)
        elif level == logging.WARNING:
            logger.warning(message, extra=extra_data)
        elif level == logging.ERROR:
            logger.error(message, extra=extra_data)
        elif level == logging.CRITICAL:
            logger.critical(message, extra=extra_data)
    
    def log_exception(self, 
                     logger_name: str,
                     message: str,
                     exception: Exception,
                     level: int = logging.ERROR,
                     context: Optional[Dict[str, Any]] = None) -> None:
        """Логирование исключения с контекстом"""
        logger = self.get_logger(logger_name)
        
        extra_data = {}
        if context:
            extra_data['custom_data'] = context
            
        logger.log(level, f"{message}: {exception}", exc_info=True, extra=extra_data)
    
    def log_performance(self, 
                       operation: str,
                       duration: float,
                       details: Optional[Dict[str, Any]] = None) -> None:
        """Логирование производительности операций"""
        logger = self.get_logger('performance')
        
        message = f"Операция '{operation}' заняла {duration:.3f} секунд"
        
        if details:
            details_str = ', '.join(f"{k}={v}" for k, v in details.items())
            message += f" [{details_str}]"
            
        logger.info(message)
    
    def log_connection_event(self, 
                            event_type: str,
                            device: str,
                            status: str,
                            details: Optional[Dict[str, Any]] = None) -> None:
        """Логирование событий подключения"""
        logger = self.get_logger('connection')
        
        message = f"{event_type} - Устройство: {device}, Статус: {status}"
        
        if details:
            logger.info(message, extra={'custom_data': details})
        else:
            logger.info(message)
    
    def log_diagnostic_result(self,
                             vehicle_model: str,
                             test_type: str,
                             result: str,
                             details: Dict[str, Any]) -> None:
        """Логирование результатов диагностики"""
        logger = self.get_logger('diagnostic')
        
        log_data = {
            'vehicle_model': vehicle_model,
            'test_type': test_type,
            'result': result,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Диагностика {vehicle_model} - {test_type}: {result}", 
                   extra={'custom_data': log_data})
    
    def change_log_level(self, level: Union[str, int]) -> None:
        """Изменение уровня логирования для всех логгеров"""
        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.INFO)
            
        # Обновление конфигурации
        self.config['log_level'] = logging.getLevelName(level)
        
        # Обновление всех зарегистрированных логгеров
        for logger in self._loggers.values():
            logger.setLevel(level)
            
        # Обновление корневого логгера
        logging.getLogger().setLevel(level)
        
        # Сохранение конфигурации
        self.save_config()
    
    def save_config(self) -> None:
        """Сохранение конфигурации логгера в файл"""
        config_path = Path('config') / 'logging.json'
        config_path.parent.mkdir(exist_ok=True)
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.get_logger(__name__).error(f"Ошибка сохранения конфигурации: {e}")
    
    def get_log_files(self) -> List[str]:
        """Получение списка файлов логов"""
        log_dir = self.config.get('log_directory', 'logs')
        
        if not os.path.exists(log_dir):
            return []
            
        log_files = []
        for root, _, files in os.walk(log_dir):
            for file in files:
                if file.endswith('.log') or file.endswith('.json'):
                    log_files.append(os.path.join(root, file))
                    
        return sorted(log_files, reverse=True)
    
    def clear_old_logs(self, days: int = 30) -> None:
        """Очистка старых логов"""
        log_dir = self.config.get('log_directory', 'logs')
        
        if not os.path.exists(log_dir):
            return
            
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        for root, _, files in os.walk(log_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_time = os.path.getmtime(file_path)
                
                if file_time < cutoff_time:
                    try:
                        os.remove(file_path)
                        self.get_logger(__name__).info(f"Удален старый лог: {file_path}")
                    except Exception as e:
                        self.get_logger(__name__).error(f"Ошибка удаления лога {file_path}: {e}")
    
    def setup_logging_to_gui(self, callback) -> None:
        """Настройка логирования для вывода в GUI"""
        class GuiLogHandler(logging.Handler):
            def __init__(self, callback_func):
                super().__init__()
                self.callback = callback_func
                self.setFormatter(logging.Formatter(
                    fmt='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%H:%M:%S'
                ))
                
            def emit(self, record):
                try:
                    msg = self.format(record)
                    self.callback(msg, record.levelname)
                except Exception:
                    self.handleError(record)
        
        gui_handler = GuiLogHandler(callback)
        gui_handler.setLevel(logging.INFO)
        
        root_logger = logging.getLogger()
        root_logger.addHandler(gui_handler)


# Функции для удобного использования
def setup_logger(name: str = None, level: Optional[int] = None) -> logging.Logger:
    """Установка и получение логгера"""
    diagnostic_logger = DiagnosticLogger()
    
    if name is None:
        # Получение имени вызывающего модуля
        frame = inspect.currentframe().f_back
        module = inspect.getmodule(frame)
        name = module.__name__ if module else 'unknown'
        
    return diagnostic_logger.get_logger(name, level)


def setup_default_logging() -> None:
    """Настройка логгирования по умолчанию"""
    DiagnosticLogger()


def log_diagnostic_event(source: str, 
                        event_type: str, 
                        message: str, 
                        data: Optional[Dict] = None,
                        level: int = logging.INFO) -> None:
    """Логирование диагностического события"""
    logger = setup_logger('diagnostic_events')
    
    log_entry = {
        'source': source,
        'event_type': event_type,
        'message': message,
        'data': data or {},
        'timestamp': datetime.now().isoformat()
    }
    
    logger.log(level, f"[{source}] {event_type}: {message}", 
              extra={'custom_data': log_entry})


def log_vehicle_data(vehicle_id: str,
                    parameter: str,
                    value: Any,
                    unit: str = '',
                    quality: str = 'good') -> None:
    """Логирование данных от автомобиля"""
    logger = setup_logger('vehicle_data')
    
    log_data = {
        'vehicle_id': vehicle_id,
        'parameter': parameter,
        'value': value,
        'unit': unit,
        'quality': quality,
        'timestamp': datetime.now().timestamp()
    }
    
    logger.info(f"{vehicle_id} - {parameter}: {value} {unit} ({quality})",
               extra={'custom_data': log_data})


def log_error_with_context(error_msg: str,
                          exception: Optional[Exception] = None,
                          context: Optional[Dict] = None,
                          logger_name: str = 'app_error') -> None:
    """Логирование ошибки с контекстом"""
    logger = setup_logger(logger_name)
    
    error_data = {
        'error_message': error_msg,
        'exception': str(exception) if exception else None,
        'exception_type': type(exception).__name__ if exception else None,
        'context': context or {},
        'timestamp': datetime.now().isoformat()
    }
    
    if exception:
        logger.error(f"{error_msg}: {exception}", 
                    exc_info=True,
                    extra={'custom_data': error_data})
    else:
        logger.error(error_msg, extra={'custom_data': error_data})


# Декоратор для логирования выполнения функций
def log_function_call(logger_name: str = None, level: int = logging.DEBUG):
    """Декоратор для логирования вызова функций"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Получение имени логгера
            if logger_name:
                log_name = logger_name
            else:
                log_name = func.__module__
                
            logger = setup_logger(log_name)
            
            # Логирование вызова
            func_name = func.__name__
            args_str = ', '.join([str(arg) for arg in args])
            kwargs_str = ', '.join([f"{k}={v}" for k, v in kwargs.items()])
            
            logger.log(level, f"Вызов функции: {func_name}({args_str}, {kwargs_str})")
            
            try:
                # Выполнение функции
                start_time = datetime.now()
                result = func(*args, **kwargs)
                end_time = datetime.now()
                
                # Логирование успешного выполнения
                duration = (end_time - start_time).total_seconds()
                logger.log(level, f"Функция {func_name} выполнена успешно за {duration:.3f} сек")
                
                return result
                
            except Exception as e:
                # Логирование ошибки
                logger.error(f"Ошибка в функции {func_name}: {e}", exc_info=True)
                raise
                
        return wrapper
    return decorator


# Класс для временного изменения уровня логирования
class TemporaryLogLevel:
    """Контекстный менеджер для временного изменения уровня логирования"""
    
    def __init__(self, level: Union[str, int]):
        self.new_level = level
        self.old_levels = {}
        
    def __enter__(self):
        diagnostic_logger = DiagnosticLogger()
        
        # Сохранение текущих уровней
        for name, logger in diagnostic_logger._loggers.items():
            self.old_levels[name] = logger.level
            
        # Установка нового уровня
        diagnostic_logger.change_log_level(self.new_level)
        
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        diagnostic_logger = DiagnosticLogger()
        
        # Восстановление старых уровней
        for name, level in self.old_levels.items():
            if name in diagnostic_logger._loggers:
                diagnostic_logger._loggers[name].setLevel(level)


# Инициализация логгера при импорте модуля
setup_default_logging()