#!/usr/bin/env python3
"""
Профессиональная диагностика Chevrolet Niva (Нива Шевроле)

Главный файл запуска приложения для комплексной диагностики
автомобилей Chevrolet Niva всех моделей и модификаций.

Функционал:
1. Подключение через ELM327 (Bluetooth, USB, WiFi)
2. Полная диагностика всех систем автомобиля
3. Чтение и сброс ошибок (DTC)
4. Отображение параметров в реальном времени
5. Адаптация и калибровка систем
6. Генерация профессиональных отчетов
"""

import sys
import os
import logging
import traceback
from pathlib import Path

# Настройка путей до того, как будут импортироваться модули
BASE_DIR = Path(__file__).parent.absolute()
SRC_DIR = BASE_DIR / "src"
ASSETS_DIR = BASE_DIR / "assets"
CONFIG_DIR = BASE_DIR / "config"

# Добавляем пути в системный путь Python
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(SRC_DIR / "ui"))
sys.path.insert(0, str(SRC_DIR / "utils"))

# Проверяем и создаем необходимые директории
for directory in [ASSETS_DIR, CONFIG_DIR, ASSETS_DIR / "icons", ASSETS_DIR / "styles", ASSETS_DIR / "images"]:
    directory.mkdir(parents=True, exist_ok=True)

from PyQt5.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt5.QtCore import Qt, QTimer, QLocale, QTranslator, QSize
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QColor
import qdarkstyle

from main import NivaDiagnosticApp
from utils.logger import setup_logger, get_logger
from config_manager import ConfigManager
from version import __version__


class SplashScreen(QSplashScreen):
    """Кастомный splash screen для приложения"""
    
    def __init__(self):
        # Создаем изображение для splash screen
        pixmap = QPixmap(600, 300)
        pixmap.fill(Qt.transparent)
        
        # Рисуем фон
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Градиентный фон
        gradient = QColor(30, 30, 46)
        painter.fillRect(pixmap.rect(), gradient)
        
        # Рамка
        painter.setPen(QColor(0, 150, 255))
        painter.drawRect(5, 5, 590, 290)
        
        # Текст
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 24, QFont.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "Niva Diagnostic Pro")
        
        font = QFont("Arial", 14)
        painter.setFont(font)
        painter.drawText(0, 220, 600, 50, Qt.AlignCenter, "Профессиональная диагностика Chevrolet Niva")
        
        font = QFont("Arial", 10)
        painter.setFont(font)
        painter.drawText(0, 260, 600, 30, Qt.AlignCenter, f"Версия {__version__}")
        
        painter.end()
        
        super().__init__(pixmap)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
    def show_message(self, message):
        """Показ сообщения на splash screen"""
        self.showMessage(
            message,
            Qt.AlignBottom | Qt.AlignHCenter,
            Qt.white
        )
        QApplication.processEvents()


def check_dependencies():
    """Проверка наличия всех необходимых зависимостей"""
    required_modules = [
        'PyQt5',
        'serial',
        'bluetooth',
        'matplotlib',
        'numpy',
        'pandas',
        'pyqtgraph',
        'qdarkstyle',
        'Jinja2',
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module.replace('-', '_'))
        except ImportError as e:
            missing_modules.append((module, str(e)))
    
    return missing_modules


def create_default_config():
    """Создание конфигурационных файлов по умолчанию"""
    config_files = {
        'settings.json': {
            'application': {
                'language': 'ru',
                'theme': 'dark',
                'auto_connect': False,
                'auto_save_reports': True,
                'save_logs': True,
                'log_level': 'INFO'
            },
            'connection': {
                'default_type': 'bluetooth',
                'default_baudrate': 38400,
                'auto_detect': True,
                'timeout': 2,
                'retry_count': 3
            },
            'diagnostics': {
                'default_model': '21236',
                'check_all_ecus': True,
                'deep_scan': False,
                'save_raw_data': False,
                'compare_with_standards': True
            },
            'ui': {
                'show_grid': True,
                'animation_enabled': True,
                'chart_update_interval': 100,
                'gauge_style': 'modern',
                'font_size': 9
            },
            'reports': {
                'default_format': 'pdf',
                'include_charts': True,
                'include_raw_data': False,
                'auto_generate': True,
                'save_path': str(BASE_DIR / "reports")
            }
        },
        
        'vehicle_profiles.json': {
            'profiles': {
                '2123': {
                    'name': 'Chevrolet Niva 1.7i (2002-2009)',
                    'engine': {
                        'type': 'VAZ-2123',
                        'displacement': 1.7,
                        'fuel': 'gasoline',
                        'injection': 'multipoint',
                        'power': 80,
                        'torque': 127,
                        'compression': 9.8
                    },
                    'default_parameters': {
                        'idle_rpm': 850,
                        'coolant_temp_normal': 85,
                        'intake_temp_normal': 40,
                        'fuel_pressure_normal': 300,
                        'battery_voltage_normal': 13.5
                    }
                },
                '21236': {
                    'name': 'Chevrolet Niva 1.7i (2010-2020)',
                    'engine': {
                        'type': 'VAZ-21236',
                        'displacement': 1.7,
                        'fuel': 'gasoline',
                        'injection': 'multipoint',
                        'power': 83,
                        'torque': 129,
                        'compression': 9.8
                    },
                    'default_parameters': {
                        'idle_rpm': 850,
                        'coolant_temp_normal': 85,
                        'intake_temp_normal': 40,
                        'fuel_pressure_normal': 300,
                        'battery_voltage_normal': 13.5
                    }
                },
                '2123-250': {
                    'name': 'Chevrolet Niva 1.8i (2014-2020)',
                    'engine': {
                        'type': 'VAZ-2123-250',
                        'displacement': 1.8,
                        'fuel': 'gasoline',
                        'injection': 'multipoint',
                        'power': 90,
                        'torque': 140,
                        'compression': 9.8
                    },
                    'default_parameters': {
                        'idle_rpm': 850,
                        'coolant_temp_normal': 85,
                        'intake_temp_normal': 40,
                        'fuel_pressure_normal': 300,
                        'battery_voltage_normal': 13.5
                    }
                },
                '2123M': {
                    'name': 'Chevrolet Niva Модерн (2021-н.в.)',
                    'engine': {
                        'type': 'VAZ-2123M',
                        'displacement': 1.7,
                        'fuel': 'gasoline',
                        'injection': 'multipoint',
                        'power': 83,
                        'torque': 129,
                        'compression': 9.8
                    },
                    'default_parameters': {
                        'idle_rpm': 850,
                        'coolant_temp_normal': 85,
                        'intake_temp_normal': 40,
                        'fuel_pressure_normal': 300,
                        'battery_voltage_normal': 13.5
                    }
                }
            }
        },
        
        'adaptation_maps.json': {
            'throttle_adaptation': {
                'procedure': 'AT TAR',
                'description': 'Адаптация дроссельной заслонки',
                'steps': [
                    'Выключить зажигание на 10 секунд',
                    'Включить зажигание (не запускать двигатель)',
                    'Подождать 30 секунд',
                    'Выключить зажигание на 10 секунд'
                ],
                'parameters': {
                    'min_position': 0.0,
                    'max_position': 100.0,
                    'idle_position': 12.5,
                    'tolerance': 2.0
                }
            },
            'idle_adaptation': {
                'procedure': 'AT IAR',
                'description': 'Адаптация холостого хода',
                'preconditions': [
                    'Двигатель прогрет до рабочей температуры',
                    'Все потребители выключены',
                    'Коробка передач в нейтрали'
                ],
                'steps': [
                    'Запустить двигатель',
                    'Дать поработать на холостом ходу 5 минут',
                    'Выключить все потребители',
                    'Подождать стабилизации оборотов'
                ],
                'target_rpm': {
                    'min': 800,
                    'max': 900,
                    'optimal': 850
                }
            },
            'immobilizer_learning': {
                'procedure': 'AT IMMO',
                'description': 'Обучение ключей иммобилайзера',
                'security_code_required': True,
                'max_keys': 5,
                'steps': [
                    'Вставить первый ключ',
                    'Включить зажигание на 5 секунд',
                    'Выключить зажигание',
                    'Вставить следующий ключ',
                    'Повторить для всех ключей'
                ]
            },
            'fuel_trim_reset': {
                'procedure': 'AT FTR',
                'description': 'Сброс корректировок топливоподачи',
                'effect': 'Сброс долгосрочных и краткосрочных корректировок',
                'conditions': 'После ремонта топливной системы'
            }
        }
    }
    
    # Создаем конфигурационные файлы
    import json
    
    for filename, content in config_files.items():
        config_path = CONFIG_DIR / filename
        if not config_path.exists():
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(content, f, ensure_ascii=False, indent=2)
                print(f"Создан конфигурационный файл: {filename}")
            except Exception as e:
                print(f"Ошибка создания файла {filename}: {e}")


def check_assets():
    """Проверка наличия необходимых ресурсов"""
    required_assets = {
        'icons': [
            'app_icon.png',
            'connect.png',
            'disconnect.png',
            'scan.png',
            'clear.png',
            'save.png',
            'exit.png',
            'new.png',
            'settings.png',
            'help.png',
            'diagnostic.png',
            'gauge.png',
            'error.png',
            'adaptation.png',
            'report.png',
            'play.png',
            'stop.png',
            'refresh.png',
            'export.png',
            'print.png'
        ],
        'styles': [
            'main.qss',
            'gauges.qss',
            'buttons.qss'
        ]
    }
    
    missing_assets = []
    
    for asset_type, files in required_assets.items():
        for file in files:
            asset_path = ASSETS_DIR / asset_type / file
            if not asset_path.exists():
                missing_assets.append(str(asset_path))
    
    return missing_assets


def create_default_styles():
    """Создание стилей по умолчанию"""
    styles_dir = ASSETS_DIR / "styles"
    
    # Основной стиль
    main_qss = """
/* Основные цвета */
:root {
    --primary-color: #0078D4;
    --secondary-color: #005A9E;
    --success-color: #107C10;
    --warning-color: #F7630C;
    --danger-color: #D13438;
    --background-color: #1E1E1E;
    --surface-color: #252526;
    --text-color: #FFFFFF;
    --text-secondary: #AAAAAA;
    --border-color: #3E3E42;
}

/* Главное окно */
QMainWindow {
    background-color: var(--background-color);
}

/* Кнопки */
QPushButton {
    background-color: var(--primary-color);
    color: var(--text-color);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: var(--secondary-color);
    border-color: var(--primary-color);
}

QPushButton:pressed {
    background-color: #004578;
}

QPushButton:disabled {
    background-color: #333333;
    color: #666666;
}

/* Кнопки действий */
QPushButton.connect {
    background-color: var(--success-color);
}

QPushButton.disconnect {
    background-color: var(--danger-color);
}

QPushButton.diagnostic {
    background-color: var(--warning-color);
}

/* Вкладки */
QTabWidget::pane {
    border: 1px solid var(--border-color);
    background-color: var(--surface-color);
}

QTabBar::tab {
    background-color: var(--surface-color);
    color: var(--text-secondary);
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: var(--background-color);
    color: var(--text-color);
    border-bottom: 2px solid var(--primary-color);
}

QTabBar::tab:hover:!selected {
    background-color: #2D2D30;
}

/* Таблицы */
QTableView, QTableWidget {
    background-color: var(--surface-color);
    color: var(--text-color);
    gridline-color: var(--border-color);
    selection-background-color: var(--primary-color);
    selection-color: var(--text-color);
    border: 1px solid var(--border-color);
}

QHeaderView::section {
    background-color: #2D2D30;
    color: var(--text-color);
    padding: 4px;
    border: 1px solid var(--border-color);
}

/* Панели и групы */
QGroupBox {
    border: 1px solid var(--border-color);
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
    color: var(--text-color);
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    background-color: var(--background-color);
}

/* Текстовые поля */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: var(--surface-color);
    color: var(--text-color);
    border: 1px solid var(--border-color);
    border-radius: 2px;
    padding: 4px;
    selection-background-color: var(--primary-color);
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: var(--primary-color);
}

/* Комбобоксы */
QComboBox {
    background-color: var(--surface-color);
    color: var(--text-color);
    border: 1px solid var(--border-color);
    border-radius: 2px;
    padding: 4px;
    min-width: 6em;
}

QComboBox:editable {
    background-color: var(--surface-color);
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid var(--border-color);
}

QComboBox::down-arrow {
    image: url(assets/icons/dropdown.png);
}

QComboBox QAbstractItemView {
    background-color: var(--surface-color);
    color: var(--text-color);
    selection-background-color: var(--primary-color);
    selection-color: var(--text-color);
    border: 1px solid var(--border-color);
}

/* Чекбоксы и радиокнопки */
QCheckBox, QRadioButton {
    color: var(--text-color);
    spacing: 5px;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
}

QCheckBox::indicator:unchecked {
    border: 1px solid var(--border-color);
    background-color: var(--surface-color);
}

QCheckBox::indicator:checked {
    border: 1px solid var(--primary-color);
    background-color: var(--primary-color);
    image: url(assets/icons/check.png);
}

/* Прогресс-бар */
QProgressBar {
    border: 1px solid var(--border-color);
    border-radius: 2px;
    background-color: var(--surface-color);
    text-align: center;
    color: var(--text-color);
}

QProgressBar::chunk {
    background-color: var(--primary-color);
    border-radius: 2px;
}

/* Скроллбары */
QScrollBar:vertical {
    background-color: var(--surface-color);
    width: 12px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #3E3E42;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4E4E52;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Статус бар */
QStatusBar {
    background-color: var(--surface-color);
    color: var(--text-secondary);
    border-top: 1px solid var(--border-color);
}

/* Меню */
QMenuBar {
    background-color: var(--background-color);
    color: var(--text-color);
}

QMenuBar::item:selected {
    background-color: var(--surface-color);
}

QMenu {
    background-color: var(--surface-color);
    color: var(--text-color);
    border: 1px solid var(--border-color);
}

QMenu::item:selected {
    background-color: var(--primary-color);
    color: var(--text-color);
}

/* Разделители */
QFrame[frameShape="4"] /* HLine */ {
    color: var(--border-color);
    max-height: 1px;
}

QFrame[frameShape="5"] /* VLine */ {
    color: var(--border-color);
    max-width: 1px;
}

/* Индикаторы */
QLabel.normal {
    color: var(--text-color);
}

QLabel.success {
    color: var(--success-color);
    font-weight: bold;
}

QLabel.warning {
    color: var(--warning-color);
    font-weight: bold;
}

QLabel.error {
    color: var(--danger-color);
    font-weight: bold;
}

/* Списки */
QListWidget {
    background-color: var(--surface-color);
    color: var(--text-color);
    border: 1px solid var(--border-color);
}

QListWidget::item:selected {
    background-color: var(--primary-color);
    color: var(--text-color);
}

/* Деревья */
QTreeWidget {
    background-color: var(--surface-color);
    color: var(--text-color);
    border: 1px solid var(--border-color);
}

QTreeWidget::item:selected {
    background-color: var(--primary-color);
    color: var(--text-color);
}

/* Тулбар */
QToolBar {
    background-color: var(--surface-color);
    border-bottom: 1px solid var(--border-color);
    spacing: 3px;
}

QToolButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 2px;
    padding: 4px;
}

QToolButton:hover {
    background-color: #2D2D30;
    border: 1px solid var(--border-color);
}

QToolButton:pressed {
    background-color: #3E3E42;
}

/* Диалоги */
QDialog {
    background-color: var(--background-color);
}

QMessageBox {
    background-color: var(--background-color);
}

QMessageBox QLabel {
    color: var(--text-color);
}
"""
    
    # Стиль для датчиков
    gauges_qss = """
/* Стили для датчиков и индикаторов */

/* Круговой датчик */
CircularGauge {
    background-color: transparent;
}

CircularGauge::value {
    color: var(--text-color);
    font-size: 16px;
    font-weight: bold;
}

CircularGauge::title {
    color: var(--text-secondary);
    font-size: 12px;
}

/* Линейный датчик */
LinearGauge {
    background-color: var(--surface-color);
    border: 1px solid var(--border-color);
    border-radius: 3px;
}

LinearGauge::value {
    background-color: var(--primary-color);
    border-radius: 2px;
}

/* Индикатор состояния */
StatusIndicator {
    qproperty-diameter: 12px;
}

StatusIndicator[status="normal"] {
    background-color: var(--success-color);
}

StatusIndicator[status="warning"] {
    background-color: var(--warning-color);
}

StatusIndicator[status="error"] {
    background-color: var(--danger-color);
}

StatusIndicator[status="offline"] {
    background-color: var(--text-secondary);
}

/* LED индикатор */
LEDIndicator {
    qproperty-diameter: 10px;
    border-radius: 5px;
    border: 1px solid var(--border-color);
}

LEDIndicator[state="on"] {
    background-color: var(--success-color);
}

LEDIndicator[state="off"] {
    background-color: var(--danger-color);
}

LEDIndicator[state="blink"] {
    background-color: var(--warning-color);
}

/* Графики */
PlotWidget {
    background-color: var(--surface-color);
    border: 1px solid var(--border-color);
    border-radius: 3px;
}
"""
    
    # Стиль для кнопок
    buttons_qss = """
/* Дополнительные стили для кнопок */

/* Большие кнопки */
QPushButton.large {
    padding: 12px 24px;
    font-size: 14px;
    min-height: 40px;
}

/* Иконные кнопки */
QPushButton.icon-button {
    border: none;
    background-color: transparent;
    padding: 8px;
    border-radius: 4px;
}

QPushButton.icon-button:hover {
    background-color: #2D2D30;
}

/* Кнопки в тулбаре */
QToolButton {
    padding: 4px;
    border-radius: 2px;
}

QToolButton:hover {
    background-color: #2D2D30;
    border: 1px solid var(--border-color);
}

/* Кнопки действий */
.action-button {
    background-color: var(--primary-color);
    color: white;
    font-weight: bold;
    padding: 8px 16px;
    border-radius: 4px;
    border: none;
}

.action-button:hover {
    background-color: var(--secondary-color);
}

.action-button:disabled {
    background-color: #333;
    color: #666;
}

/* Текстовые кнопки */
.text-button {
    background-color: transparent;
    color: var(--primary-color);
    border: none;
    padding: 4px 8px;
}

.text-button:hover {
    background-color: rgba(0, 120, 212, 0.1);
    border-radius: 2px;
}
"""
    
    # Сохраняем стили
    try:
        with open(styles_dir / "main.qss", "w", encoding="utf-8") as f:
            f.write(main_qss)
        
        with open(styles_dir / "gauges.qss", "w", encoding="utf-8") as f:
            f.write(gauges_qss)
        
        with open(styles_dir / "buttons.qss", "w", encoding="utf-8") as f:
            f.write(buttons_qss)
            
        print("Созданы файлы стилей")
    except Exception as e:
        print(f"Ошибка создания стилей: {e}")


def create_default_icons():
    """Создание иконок по умолчанию (заглушки)"""
    from PyQt5.QtGui import QPixmap, QPainter, QColor, QBrush, QPen, QLinearGradient
    from PyQt5.QtCore import QRect
    
    icons_dir = ASSETS_DIR / "icons"
    
    # Размеры иконок
    icon_sizes = [16, 24, 32, 48, 64]
    
    # Цветовая схема
    colors = {
        'primary': QColor(0, 120, 212),
        'success': QColor(16, 124, 16),
        'warning': QColor(247, 99, 12),
        'danger': QColor(209, 52, 56),
        'white': QColor(255, 255, 255),
        'gray': QColor(128, 128, 128)
    }
    
    # Простые векторные иконки (в виде функций рисования)
    def draw_connect_icon(painter, rect, color):
        """Иконка подключения"""
        center = rect.center()
        radius = min(rect.width(), rect.height()) * 0.3
        
        # Внешний круг
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, int(radius), int(radius))
        
        # Внутренний круг
        inner_radius = radius * 0.5
        painter.setBrush(QBrush(colors['white']))
        painter.drawEllipse(center, int(inner_radius), int(inner_radius))
        
        # Стрелка
        painter.setBrush(QBrush(color))
        arrow_size = radius * 0.4
        painter.drawPolygon([
            center + QPoint(0, -int(arrow_size)),
            center + QPoint(-int(arrow_size * 0.7), int(arrow_size * 0.5)),
            center + QPoint(int(arrow_size * 0.7), int(arrow_size * 0.5))
        ])
    
    def draw_diagnostic_icon(painter, rect, color):
        """Иконка диагностики"""
        center = rect.center()
        size = min(rect.width(), rect.height()) * 0.4
        
        # Шестеренка
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(colors['white'], 1))
        
        # Рисуем шестеренку (упрощенно - круг с зубьями)
        painter.drawEllipse(center, int(size), int(size))
        
        # Крест
        painter.setPen(QPen(colors['white'], 2))
        painter.drawLine(
            center.x() - int(size * 0.7),
            center.y(),
            center.x() + int(size * 0.7),
            center.y()
        )
        painter.drawLine(
            center.x(),
            center.y() - int(size * 0.7),
            center.x(),
            center.y() + int(size * 0.7)
        )
    
    def draw_error_icon(painter, rect, color):
        """Иконка ошибки"""
        center = rect.center()
        radius = min(rect.width(), rect.height()) * 0.4
        
        # Треугольник с восклицательным знаком
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        
        # Треугольник
        painter.drawPolygon([
            center + QPoint(0, -int(radius)),
            center + QPoint(-int(radius * 0.9), int(radius * 0.6)),
            center + QPoint(int(radius * 0.9), int(radius * 0.6))
        ])
        
        # Восклицательный знак
        painter.setBrush(QBrush(colors['white']))
        bar_width = radius * 0.2
        bar_height = radius * 0.4
        dot_size = bar_width
        
        painter.drawRect(
            center.x() - int(bar_width / 2),
            center.y() - int(radius * 0.4),
            int(bar_width),
            int(bar_height)
        )
        painter.drawEllipse(
            center.x() - int(dot_size / 2),
            center.y() + int(radius * 0.2),
            int(dot_size),
            int(dot_size)
        )
    
    # Создаем иконки разных размеров
    icon_definitions = {
        'connect.png': (draw_connect_icon, colors['success']),
        'disconnect.png': (draw_connect_icon, colors['danger']),
        'diagnostic.png': (draw_diagnostic_icon, colors['warning']),
        'error.png': (draw_error_icon, colors['danger']),
        # Другие иконки...
    }
    
    for filename, (draw_func, color) in icon_definitions.items():
        for size in icon_sizes:
            # Создаем пиксмап
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.transparent)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Рисуем иконку
            draw_func(painter, QRect(0, 0, size, size), color)
            
            painter.end()
            
            # Сохраняем
            icon_path = icons_dir / f"{size}x{size}" / filename
            icon_path.parent.mkdir(exist_ok=True)
            pixmap.save(str(icon_path))
        
        print(f"Создана иконка: {filename}")


def show_error_dialog(title, message, detailed_message=None):
    """Показать диалог ошибки"""
    error_dialog = QMessageBox()
    error_dialog.setIcon(QMessageBox.Critical)
    error_dialog.setWindowTitle(title)
    error_dialog.setText(message)
    
    if detailed_message:
        error_dialog.setDetailedText(detailed_message)
    
    error_dialog.setStandardButtons(QMessageBox.Ok)
    error_dialog.exec_()


def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    """Обработка непойманных исключений"""
    logger = get_logger()
    logger.error("Необработанное исключение:", exc_info=(exc_type, exc_value, exc_traceback))
    
    # Формируем сообщение об ошибке
    error_msg = f"Произошла критическая ошибка:\n{exc_type.__name__}: {exc_value}"
    
    # Пытаемся показать диалог ошибки
    try:
        app = QApplication.instance()
        if app:
            show_error_dialog(
                "Критическая ошибка",
                error_msg,
                ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            )
    except:
        # Если не получилось показать диалог, просто печатаем
        print(error_msg)
        traceback.print_exception(exc_type, exc_value, exc_traceback)
    
    sys.exit(1)


def main():
    """Главная функция приложения"""
    
    # Устанавливаем обработчик непойманных исключений
    sys.excepthook = handle_uncaught_exception
    
    # Проверяем зависимости
    print("Проверка зависимостей...")
    missing_modules = check_dependencies()
    
    if missing_modules:
        error_msg = "Отсутствуют необходимые модули:\n\n"
        for module, error in missing_modules:
            error_msg += f"• {module}: {error}\n"
        
        error_msg += "\nУстановите зависимости командой:\npip install -r requirements.txt"
        
        # Создаем QApplication для показа диалога
        app = QApplication(sys.argv)
        show_error_dialog("Отсутствуют зависимости", error_msg)
        sys.exit(1)
    
    # Создаем конфигурационные файлы по умолчанию
    print("Проверка конфигурации...")
    create_default_config()
    
    # Создаем ресурсы по умолчанию
    print("Проверка ресурсов...")
    missing_assets = check_assets()
    
    if missing_assets:
        print(f"Отсутствуют ресурсы: {len(missing_assets)} файлов")
        print("Создание ресурсов по умолчанию...")
        create_default_styles()
        # create_default_icons()  # Раскомментировать, если нужны сгенерированные иконки
    
    # Настраиваем логирование
    print("Настройка логирования...")
    setup_logger()
    logger = get_logger()
    logger.info(f"Запуск приложения Niva Diagnostic Pro v{__version__}")
    
    # Создаем QApplication
    print("Инициализация приложения...")
    app = QApplication(sys.argv)
    app.setApplicationName("Niva Diagnostic Pro")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("NivaDiagnostics")
    app.setOrganizationDomain("niva-diagnostics.ru")
    
    # Показываем splash screen
    splash = SplashScreen()
    splash.show()
    
    # Инициализация приложения с задержками для имитации загрузки
    splash.show_message("Загрузка конфигурации...")
    QTimer.singleShot(500, lambda: None)
    
    splash.show_message("Инициализация модулей...")
    QTimer.singleShot(1000, lambda: None)
    
    splash.show_message("Подготовка интерфейса...")
    QTimer.singleShot(1500, lambda: None)
    
    try:
        # Загружаем стили
        splash.show_message("Загрузка стилей...")
        style_file = ASSETS_DIR / "styles" / "main.qss"
        if style_file.exists():
            with open(style_file, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
        else:
            # Используем qdarkstyle как запасной вариант
            app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        
        # Настройка шрифта
        splash.show_message("Настройка шрифтов...")
        font = QFont("Segoe UI", 9)
        app.setFont(font)
        
        # Создание главного окна
        splash.show_message("Создание главного окна...")
        
        # Загружаем конфигурацию
        config = ConfigManager()
        
        # Создаем главное окно
        main_app = NivaDiagnosticApp(app, config)
        
        # Закрываем splash screen и показываем главное окно
        splash.show_message("Загрузка завершена!")
        QTimer.singleShot(1000, lambda: finish_startup(splash, main_app))
        
        # Запускаем главный цикл приложения
        return app.exec_()
        
    except Exception as e:
        logger.error(f"Ошибка запуска приложения: {e}", exc_info=True)
        splash.close()
        
        show_error_dialog(
            "Ошибка запуска",
            f"Не удалось запустить приложение:\n{str(e)}",
            traceback.format_exc()
        )
        return 1


def finish_startup(splash, main_app):
    """Завершение запуска приложения"""
    splash.close()
    main_app.main_window.show()
    
    # Показываем приветственное сообщение для первого запуска
    config = main_app.config
    if config.get('application', 'first_run', True):
        welcome_message = """
        <h2>Добро пожаловать в Niva Diagnostic Pro!</h2>
        <p>Вы впервые запустили приложение для диагностики Chevrolet Niva.</p>
        <p><b>Для начала работы:</b></p>
        <ol>
            <li>Подключите ELM327 адаптер к OBD-II разъему автомобиля</li>
            <li>Включите зажигание (двигатель можно не запускать)</li>
            <li>В приложении нажмите "Подключиться" и выберите ваш адаптер</li>
            <li>Выберите модель вашего автомобиля Chevrolet Niva</li>
            <li>Нажмите "Запустить диагностику" для начала сканирования</li>
        </ol>
        <p><b>Поддерживаемые модели:</b></p>
        <ul>
            <li>Chevrolet Niva 1.7i (2002-2009)</li>
            <li>Chevrolet Niva 1.7i (2010-2020)</li>
            <li>Chevrolet Niva 1.8i (2014-2020)</li>
            <li>Chevrolet Niva Модерн (2021-н.в.)</li>
        </ul>
        <p>При возникновении вопросов обратитесь к руководству пользователя.</p>
        """
        
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Добро пожаловать!")
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(welcome_message)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
        
        # Устанавливаем флаг, что первый запуск уже был
        config.set('application', 'first_run', False)
        config.save()


if __name__ == "__main__":
    # Запускаем приложение
    exit_code = main()
    sys.exit(exit_code)


# Дополнительные импорты для завершенности
from PyQt5.QtCore import QPoint