"""
Основной класс приложения для профессиональной диагностики Chevrolet Niva
"""

import sys
import os
import platform
import ctypes
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PyQt5.QtCore import (Qt, QTimer, QTranslator, QLocale, QSettings, 
                         QCoreApplication, QThread, pyqtSignal)
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor, QPalette
import qdarkstyle
import traceback
import logging
from datetime import datetime

# Добавляем путь к модулям
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from ui.main_window import MainWindow
from utils.logger import setup_logger, get_logger
from config_manager import ConfigManager
from elm327_connector import ELM327Connector
from diagnostics_engine import DiagnosticsEngine
from error_codes import ErrorCodeDatabase
from adapters import VehicleAdapterFactory
from report_generator import ReportGenerator

class ApplicationInitializer(QThread):
    """Поток инициализации приложения"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self):
        super().__init__()
        self.config = None
        self.logger = None
        self.error = None
        
    def run(self):
        """Запуск инициализации"""
        try:
            self.progress.emit(10, "Настройка системы...")
            
            # Инициализация конфигурации
            self.progress.emit(20, "Загрузка конфигурации...")
            self.config = ConfigManager()
            
            # Настройка логгера
            self.progress.emit(30, "Настройка логгера...")
            self.logger = setup_logger()
            self.logger.info("=" * 80)
            self.logger.info(f"Запуск приложения диагностики Chevrolet Niva")
            self.logger.info(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info(f"Операционная система: {platform.system()} {platform.release()}")
            self.logger.info(f"Версия Python: {platform.python_version()}")
            self.logger.info("=" * 80)
            
            # Проверка необходимых директорий
            self.progress.emit(40, "Проверка файловой системы...")
            self._check_directories()
            
            # Инициализация базы данных ошибок
            self.progress.emit(60, "Загрузка базы ошибок...")
            error_db = ErrorCodeDatabase()
            error_db.load_from_file()
            
            # Инициализация фабрики адаптеров
            self.progress.emit(80, "Инициализация адаптеров...")
            VehicleAdapterFactory.initialize()
            
            self.progress.emit(100, "Инициализация завершена!")
            self.finished.emit(True, "Успешно")
            
        except Exception as e:
            error_msg = f"Ошибка инициализации: {str(e)}\n{traceback.format_exc()}"
            self.error = error_msg
            if self.logger:
                self.logger.error(error_msg)
            else:
                print(error_msg)
            self.finished.emit(False, error_msg)
            
    def _check_directories(self):
        """Проверка и создание необходимых директорий"""
        directories = [
            "logs",
            "reports",
            "backups",
            "exports",
            os.path.join("assets", "icons"),
            os.path.join("assets", "styles"),
            os.path.join("assets", "images"),
            os.path.join("config", "profiles"),
            os.path.join("config", "templates"),
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

class NivaDiagnosticApp:
    """Основной класс приложения"""
    
    def __init__(self, argv):
        self.argv = argv
        self.app = None
        self.splash = None
        self.main_window = None
        self.config = None
        self.connector = None
        self.diagnostics_engine = None
        self.report_generator = None
        self.initializer = None
        self.logger = None
        
        # Настройки приложения
        self.APP_NAME = "Профессиональная диагностика Chevrolet Niva"
        self.APP_VERSION = "1.0.0"
        self.APP_ORGANIZATION = "NivaDiagnosticPro"
        self.APP_DOMAIN = "nivadiagnostic.ru"
        
    def run(self):
        """Запуск приложения"""
        try:
            # Создание QApplication
            self.app = QApplication(self.argv)
            
            # Настройка информации о приложении
            self.app.setApplicationName(self.APP_NAME)
            self.app.setApplicationVersion(self.APP_VERSION)
            self.app.setOrganizationName(self.APP_ORGANIZATION)
            self.app.setOrganizationDomain(self.APP_DOMAIN)
            
            # Настройка для Windows (иконка в панели задач)
            if platform.system() == "Windows":
                self._setup_windows_app_id()
            
            # Показ заставки
            self.show_splash_screen()
            
            # Запуск инициализации
            self.start_initialization()
            
            # Запуск главного цикла
            return self.app.exec_()
            
        except Exception as e:
            self.show_critical_error(str(e))
            return 1
    
    def show_splash_screen(self):
        """Показать заставку приложения"""
        splash_pixmap = QPixmap()
        
        # Попытка загрузить кастомную заставку
        splash_paths = [
            os.path.join("assets", "images", "splash.png"),
            os.path.join("assets", "images", "splash.jpg"),
            "splash.png",
        ]
        
        for path in splash_paths:
            if os.path.exists(path):
                splash_pixmap = QPixmap(path)
                break
        
        # Если заставка не найдена, создаем простую
        if splash_pixmap.isNull():
            splash_pixmap = self.create_default_splash()
        
        self.splash = QSplashScreen(splash_pixmap, Qt.WindowStaysOnTopHint)
        self.splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.splash.setEnabled(False)
        
        # Стиль текста на заставке
        self.splash.setStyleSheet("""
            QSplashScreen {
                background-color: #1e1e1e;
                color: #ffffff;
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
        self.splash.show()
        self.app.processEvents()
        
    def create_default_splash(self):
        """Создание заставки по умолчанию"""
        from PyQt5.QtGui import QPainter, QLinearGradient, QFont
        from PyQt5.QtCore import QRect
        
        pixmap = QPixmap(600, 400)
        pixmap.fill(QColor("#1e1e1e"))
        
        painter = QPainter(pixmap)
        
        # Градиентный фон
        gradient = QLinearGradient(0, 0, 600, 400)
        gradient.setColorAt(0, QColor("#2c3e50"))
        gradient.setColorAt(1, QColor("#1a1a2e"))
        painter.fillRect(0, 0, 600, 400, gradient)
        
        # Логотип
        painter.setPen(QColor("#3498db"))
        painter.setFont(QFont("Arial", 48, QFont.Bold))
        painter.drawText(QRect(0, 100, 600, 100), Qt.AlignCenter, "NIVA")
        
        painter.setPen(QColor("#ecf0f1"))
        painter.setFont(QFont("Arial", 24))
        painter.drawText(QRect(0, 180, 600, 50), Qt.AlignCenter, "Professional Diagnostic")
        
        painter.setPen(QColor("#95a5a6"))
        painter.setFont(QFont("Arial", 14))
        painter.drawText(QRect(0, 250, 600, 50), Qt.AlignCenter, "Chevrolet Niva")
        
        painter.setPen(QColor("#7f8c8d"))
        painter.setFont(QFont("Arial", 10))
        painter.drawText(QRect(0, 350, 600, 30), Qt.AlignCenter, f"Версия {self.APP_VERSION}")
        
        painter.end()
        
        return pixmap
    
    def start_initialization(self):
        """Запуск процесса инициализации"""
        self.initializer = ApplicationInitializer()
        self.initializer.progress.connect(self.update_splash_progress)
        self.initializer.finished.connect(self.initialization_finished)
        self.initializer.start()
    
    def update_splash_progress(self, progress, message):
        """Обновление прогресса на заставке"""
        if self.splash:
            self.splash.showMessage(
                f"{message}... {progress}%",
                Qt.AlignBottom | Qt.AlignHCenter,
                Qt.white
            )
            self.splash.repaint()
            self.app.processEvents()
    
    def initialization_finished(self, success, message):
        """Завершение инициализации"""
        if success:
            # Получение результатов инициализации
            self.config = self.initializer.config
            self.logger = get_logger()
            
            # Инициализация основных компонентов
            self.initialize_components()
            
            # Скрытие заставки и показ главного окна
            if self.splash:
                self.splash.finish(self.main_window)
            
            # Показ главного окна
            self.main_window.show()
            
            # Загрузка настроек окна
            self.load_window_settings()
            
            # Логирование успешного запуска
            self.logger.info("Приложение успешно запущено")
            
        else:
            # Ошибка инициализации
            if self.splash:
                self.splash.hide()
            
            self.show_critical_error(
                f"Ошибка при инициализации приложения:\n\n{message}\n\n"
                "Пожалуйста, проверьте:\n"
                "1. Наличие всех файлов приложения\n"
                "2. Права доступа к файлам\n"
                "3. Установленные зависимости Python\n\n"
                "Подробности в файле logs/application.log"
            )
            
            # Сохранение ошибки в лог
            if self.logger:
                self.logger.error(f"Ошибка инициализации: {message}")
            else:
                print(f"Ошибка инициализации: {message}")
            
            self.app.quit()
    
    def initialize_components(self):
        """Инициализация основных компонентов приложения"""
        try:
            # Создание основных компонентов
            self.connector = ELM327Connector()
            self.diagnostics_engine = DiagnosticsEngine(self.connector)
            self.report_generator = ReportGenerator()
            
            # Создание главного окна
            self.main_window = MainWindow(
                config=self.config,
                connector=self.connector,
                diagnostics_engine=self.diagnostics_engine,
                report_generator=self.report_generator
            )
            
            # Настройка стилей
            self.setup_styles()
            
            # Настройка обработки исключений
            self.setup_exception_handling()
            
            # Проверка обновлений (в фоновом режиме)
            self.check_for_updates()
            
            self.logger.info("Компоненты приложения успешно инициализированы")
            
        except Exception as e:
            error_msg = f"Ошибка инициализации компонентов: {str(e)}\n{traceback.format_exc()}"
            self.logger.error(error_msg)
            raise
    
    def setup_styles(self):
        """Настройка стилей приложения"""
        try:
            # Загрузка темной темы
            dark_stylesheet = qdarkstyle.load_stylesheet_pyqt5()
            
            # Загрузка кастомного стиля
            custom_style_path = os.path.join("assets", "styles", "custom.css")
            custom_style = ""
            
            if os.path.exists(custom_style_path):
                with open(custom_style_path, 'r', encoding='utf-8') as f:
                    custom_style = f.read()
            
            # Объединение стилей
            combined_style = dark_stylesheet + "\n" + custom_style
            
            # Применение стиля
            self.app.setStyleSheet(combined_style)
            
            # Настройка шрифта
            font = QFont("Segoe UI", 10)
            self.app.setFont(font)
            
            # Палитра
            palette = self.app.palette()
            palette.setColor(QPalette.Link, QColor("#3498db"))
            palette.setColor(QPalette.LinkVisited, QColor("#9b59b6"))
            self.app.setPalette(palette)
            
            self.logger.info("Стили приложения успешно загружены")
            
        except Exception as e:
            self.logger.warning(f"Не удалось загрузить кастомные стили: {e}")
    
    def setup_exception_handling(self):
        """Настройка обработки необработанных исключений"""
        sys.excepthook = self.handle_exception
        
        # Установка обработчика для PyQt
        def qt_exception_hook(exc_type, exc_value, exc_traceback):
            self.handle_exception(exc_type, exc_value, exc_traceback)
        
        # Сохраняем оригинальный обработчик
        self.original_excepthook = sys.excepthook
        sys.excepthook = qt_exception_hook
    
    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """Обработка необработанных исключений"""
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        
        # Логирование ошибки
        if self.logger:
            self.logger.error(f"Необработанное исключение:\n{error_msg}")
        else:
            print(f"Необработанное исключение:\n{error_msg}")
        
        # Показ сообщения об ошибке (только в основном потоке)
        if QApplication.instance() and QThread.currentThread() == QApplication.instance().thread():
            error_dialog = QMessageBox()
            error_dialog.setIcon(QMessageBox.Critical)
            error_dialog.setWindowTitle("Критическая ошибка")
            error_dialog.setText("В приложении произошла критическая ошибка")
            error_dialog.setInformativeText(f"{exc_type.__name__}: {exc_value}")
            error_dialog.setDetailedText(error_msg)
            error_dialog.setStandardButtons(QMessageBox.Ok)
            error_dialog.exec_()
        
        # Вызов оригинального обработчика
        if hasattr(self, 'original_excepthook'):
            self.original_excepthook(exc_type, exc_value, exc_traceback)
    
    def load_window_settings(self):
        """Загрузка настроек окна"""
        try:
            settings = QSettings(self.APP_ORGANIZATION, self.APP_NAME)
            
            # Восстановление геометрии окна
            geometry = settings.value("main_window/geometry")
            if geometry:
                self.main_window.restoreGeometry(geometry)
            
            # Восстановление состояния окна
            window_state = settings.value("main_window/state")
            if window_state:
                self.main_window.restoreState(window_state)
            
            # Восстановление позиции
            pos = settings.value("main_window/position")
            if pos:
                self.main_window.move(pos)
            
            # Восстановление размера
            size = settings.value("main_window/size")
            if size:
                self.main_window.resize(size)
            
            self.logger.info("Настройки окна восстановлены")
            
        except Exception as e:
            self.logger.warning(f"Не удалось загрузить настройки окна: {e}")
    
    def save_window_settings(self):
        """Сохранение настроек окна"""
        try:
            if self.main_window:
                settings = QSettings(self.APP_ORGANIZATION, self.APP_NAME)
                
                settings.setValue("main_window/geometry", self.main_window.saveGeometry())
                settings.setValue("main_window/state", self.main_window.saveState())
                settings.setValue("main_window/position", self.main_window.pos())
                settings.setValue("main_window/size", self.main_window.size())
                
                self.logger.info("Настройки окна сохранены")
                
        except Exception as e:
            self.logger.warning(f"Не удалось сохранить настройки окна: {e}")
    
    def check_for_updates(self):
        """Проверка обновлений (в фоновом режиме)"""
        # Эта функция запускается в фоновом потоке
        # Реализация проверки обновлений
        pass
    
    def show_critical_error(self, message):
        """Показать критическую ошибку"""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Критическая ошибка")
        msg_box.setText("Не удалось запустить приложение")
        msg_box.setInformativeText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
    
    def _setup_windows_app_id(self):
        """Настройка AppUserModelID для Windows (для панели задач)"""
        if platform.system() == "Windows":
            try:
                myappid = f"{self.APP_ORGANIZATION}.{self.APP_NAME}.{self.APP_VERSION}"
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception as e:
                # Игнорируем ошибки, так как это не критично
                pass
    
    def cleanup(self):
        """Очистка ресурсов при выходе"""
        try:
            # Сохранение настроек окна
            self.save_window_settings()
            
            # Остановка диагностического движка
            if self.diagnostics_engine:
                self.diagnostics_engine.stop()
            
            # Отключение от ELM327
            if self.connector:
                self.connector.disconnect()
            
            # Сохранение конфигурации
            if self.config:
                self.config.save()
            
            # Логирование завершения работы
            if self.logger:
                self.logger.info("=" * 80)
                self.logger.info(f"Завершение работы приложения")
                self.logger.info(f"Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                self.logger.info("=" * 80)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Ошибка при очистке ресурсов: {e}")
            else:
                print(f"Ошибка при очистке ресурсов: {e}")

def main():
    """Точка входа в приложение"""
    try:
        app = NivaDiagnosticApp(sys.argv)
        
        # Установка обработчика завершения
        def handle_exit():
            app.cleanup()
        
        # Привязка обработчика к сигналу aboutToQuit
        app.app.aboutToQuit.connect(handle_exit)
        
        return app.run()
        
    except Exception as e:
        print(f"Критическая ошибка при запуске приложения: {e}")
        print(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())