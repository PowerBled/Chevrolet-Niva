"""
Панель отображения текущих данных (Live Data)
Полная версия с графиками, датчиками и логированием
"""

import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                            QGroupBox, QLabel, QPushButton, QComboBox, 
                            QCheckBox, QSpinBox, QDoubleSpinBox, QTabWidget,
                            QTableWidget, QTableWidgetItem, QHeaderView,
                            QSplitter, QFileDialog, QMessageBox, QScrollArea,
                            QFrame, QProgressBar, QToolButton, QMenu, QAction)
from PyQt5.QtCore import (Qt, QTimer, QThread, pyqtSignal, pyqtSlot, 
                         QDateTime, QSettings, QSize)
from PyQt5.QtGui import (QFont, QColor, QPen, QBrush, QLinearGradient,
                        QPainter, QIcon, QPalette)
import pyqtgraph as pg
import numpy as np
from collections import deque
import json
import csv

from ui.widgets.gauges import (CircularGauge, LinearGauge, DigitalGauge,
                              TachometerGauge, SpeedometerGauge, TemperatureGauge,
                              PressureGauge, VoltageGauge)
from ui.widgets.charts import (RealTimeChart, HistoricalChart, 
                              ScatterPlot, BarChart)
from ui.widgets.indicators import (LEDIndicator, StatusIndicator, 
                                  WarningLight, ValueIndicator)
from utils.helpers import format_value, color_gradient
from utils.logger import get_logger

class LiveDataPanel(QWidget):
    """Панель отображения текущих данных в реальном времени"""
    
    data_updated = pyqtSignal(dict)
    recording_changed = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.settings = QSettings("NivaDiagnostic", "LiveData")
        
        # Данные и состояние
        self.current_data = {}
        self.historical_data = {}
        self.max_history_points = 1000
        self.sampling_interval = 100  # мс
        self.is_recording = False
        self.recording_start_time = None
        self.recording_file = None
        self.selected_pids = []
        
        # Компоненты UI
        self.gauges = {}
        self.charts = {}
        self.indicators = {}
        
        # Поток для сбора данных
        self.data_thread = None
        self.data_timer = QTimer()
        
        self.init_ui()
        self.setup_connections()
        self.load_settings()
        
    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Верхняя панель управления
        top_panel = self.create_top_panel()
        main_layout.addWidget(top_panel)
        
        # Разделитель
        splitter = QSplitter(Qt.Vertical)
        
        # Верхняя часть: основные датчики
        gauges_widget = self.create_gauges_widget()
        splitter.addWidget(gauges_widget)
        
        # Нижняя часть: графики и таблица
        charts_tabs = self.create_charts_tabs()
        splitter.addWidget(charts_tabs)
        
        # Настройка пропорций
        splitter.setSizes([400, 400])
        
        main_layout.addWidget(splitter, 1)
        
        # Статус бар
        status_panel = self.create_status_panel()
        main_layout.addWidget(status_panel)
        
        # Таймер для обновления данных
        self.data_timer.timeout.connect(self.update_display)
        
    def create_top_panel(self):
        """Создание верхней панели управления"""
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Кнопка старт/стоп
        self.start_stop_btn = QPushButton()
        self.start_stop_btn.setIcon(QIcon("assets/icons/play.png"))
        self.start_stop_btn.setText("Старт")
        self.start_stop_btn.setMinimumWidth(100)
        self.start_stop_btn.setCheckable(True)
        layout.addWidget(self.start_stop_btn)
        
        # Кнопка записи
        self.record_btn = QPushButton()
        self.record_btn.setIcon(QIcon("assets/icons/record.png"))
        self.record_btn.setText("Запись")
        self.record_btn.setCheckable(True)
        layout.addWidget(self.record_btn)
        
        # Интервал обновления
        layout.addWidget(QLabel("Интервал (мс):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(50, 5000)
        self.interval_spin.setValue(self.sampling_interval)
        self.interval_spin.setSuffix(" мс")
        self.interval_spin.setMaximumWidth(100)
        layout.addWidget(self.interval_spin)
        
        # Выбор PID
        layout.addWidget(QLabel("Датчики:"))
        self.pid_combo = QComboBox()
        self.pid_combo.setEditable(True)
        self.pid_combo.setMinimumWidth(150)
        self.load_pid_list()
        layout.addWidget(self.pid_combo)
        
        # Кнопка добавления PID
        self.add_pid_btn = QPushButton()
        self.add_pid_btn.setIcon(QIcon("assets/icons/add.png"))
        self.add_pid_btn.setText("Добавить")
        self.add_pid_btn.clicked.connect(self.add_selected_pid)
        layout.addWidget(self.add_pid_btn)
        
        # Кнопка очистки
        self.clear_btn = QPushButton()
        self.clear_btn.setIcon(QIcon("assets/icons/clear.png"))
        self.clear_btn.setText("Очистить")
        self.clear_btn.clicked.connect(self.clear_data)
        layout.addWidget(self.clear_btn)
        
        # Кнопка сохранения
        self.save_btn = QPushButton()
        self.save_btn.setIcon(QIcon("assets/icons/save.png"))
        self.save_btn.setText("Сохранить")
        self.save_btn.clicked.connect(self.save_data)
        layout.addWidget(self.save_btn)
        
        # Кнопка настроек
        settings_btn = QToolButton()
        settings_btn.setIcon(QIcon("assets/icons/settings.png"))
        settings_btn.setText("Настройки")
        settings_btn.setPopupMode(QToolButton.InstantPopup)
        settings_menu = self.create_settings_menu()
        settings_btn.setMenu(settings_menu)
        layout.addWidget(settings_btn)
        
        layout.addStretch()
        
        return panel
        
    def create_settings_menu(self):
        """Создание меню настроек"""
        menu = QMenu(self)
        
        # Настройки отображения
        display_action = QAction("Настройки отображения", self)
        display_action.triggered.connect(self.show_display_settings)
        menu.addAction(display_action)
        
        menu.addSeparator()
        
        # Настройки графиков
        charts_action = QAction("Настройки графиков", self)
        charts_action.triggered.connect(self.show_chart_settings)
        menu.addAction(charts_action)
        
        # Настройки датчиков
        gauges_action = QAction("Настройки датчиков", self)
        gauges_action.triggered.connect(self.show_gauge_settings)
        menu.addAction(gauges_action)
        
        menu.addSeparator()
        
        # Сброс настроек
        reset_action = QAction("Сбросить настройки", self)
        reset_action.triggered.connect(self.reset_settings)
        menu.addAction(reset_action)
        
        return menu
        
    def create_gauges_widget(self):
        """Создание виджета с датчиками"""
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        # Основные датчики (всегда отображаются)
        self.create_main_gauges(layout)
        
        # Динамические датчики (добавляются пользователем)
        self.gauges_container = QWidget()
        self.gauges_layout = QGridLayout(self.gauges_container)
        self.gauges_layout.setContentsMargins(0, 0, 0, 0)
        self.gauges_layout.setSpacing(10)
        
        # Прокручиваемая область для датчиков
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.gauges_container)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        layout.addWidget(scroll_area, 2, 0, 1, 4)
        
        return widget
        
    def create_main_gauges(self, layout):
        """Создание основных датчиков"""
        # Тахометр
        self.tachometer = Tachometer()
        self.tachometer.setTitle("Обороты двигателя")
        self.tachometer.setRange(0, 8000)
        self.tachometer.setValue(0)
        self.tachometer.setUnit("об/мин")
        self.tachometer.setWarningLevel(6500)
        self.tachometer.setCriticalLevel(7000)
        layout.addWidget(self.tachometer, 0, 0)
        
        # Спидометр
        self.speedometer = Speedometer()
        self.speedometer.setTitle("Скорость")
        self.speedometer.setRange(0, 200)
        self.speedometer.setValue(0)
        self.speedometer.setUnit("км/ч")
        layout.addWidget(self.speedometer, 0, 1)
        
        # Датчик температуры охлаждающей жидкости
        self.coolant_temp_gauge = TemperatureGauge()
        self.coolant_temp_gauge.setTitle("Температура ОЖ")
        self.coolant_temp_gauge.setRange(-40, 150)
        self.coolant_temp_gauge.setValue(20)
        self.coolant_temp_gauge.setUnit("°C")
        self.coolant_temp_gauge.setWarningLevel(100)
        self.coolant_temp_gauge.setCriticalLevel(110)
        layout.addWidget(self.coolant_temp_gauge, 0, 2)
        
        # Датчик напряжения
        self.voltmeter = Voltmeter()
        self.voltmeter.setTitle("Напряжение")
        self.voltmeter.setRange(10, 16)
        self.voltmeter.setValue(12.5)
        self.voltmeter.setUnit("V")
        self.voltmeter.setWarningLevel(11.5)
        self.voltmeter.setCriticalLevel(11.0)
        layout.addWidget(self.voltmeter, 0, 3)
        
        # Датчик положения дроссельной заслонки
        self.throttle_gauge = CircularGauge()
        self.throttle_gauge.setTitle("Положение дросселя")
        self.throttle_gauge.setRange(0, 100)
        self.throttle_gauge.setValue(0)
        self.throttle_gauge.setUnit("%")
        self.throttle_gauge.setColors(QColor(0, 200, 0), QColor(255, 200, 0), QColor(255, 0, 0))
        layout.addWidget(self.throttle_gauge, 1, 0)
        
        # Датчик нагрузки двигателя
        self.engine_load_gauge = CircularGauge()
        self.engine_load_gauge.setTitle("Нагрузка двигателя")
        self.engine_load_gauge.setRange(0, 100)
        self.engine_load_gauge.setValue(0)
        self.engine_load_gauge.setUnit("%")
        layout.addWidget(self.engine_load_gauge, 1, 1)
        
        # Датчик расхода воздуха
        self.maf_gauge = PressureGauge()
        self.maf_gauge.setTitle("Расход воздуха")
        self.maf_gauge.setRange(0, 300)
        self.maf_gauge.setValue(0)
        self.maf_gauge.setUnit("г/с")
        layout.addWidget(self.maf_gauge, 1, 2)
        
        # Датчик давления во впускном коллекторе
        self.map_gauge = PressureGauge()
        self.map_gauge.setTitle("Давление в коллекторе")
        self.map_gauge.setRange(0, 150)
        self.map_gauge.setValue(100)
        self.map_gauge.setUnit("кПа")
        layout.addWidget(self.map_gauge, 1, 3)
        
        # Индикаторы состояния
        self.create_status_indicators(layout, 2, 0)
        
    def create_status_indicators(self, layout, row, col):
        """Создание индикаторов состояния"""
        group = QGroupBox("Статус систем")
        group_layout = QGridLayout(group)
        
        # Индикатор проверки двигателя
        self.check_engine_light = WarningLight("Check Engine")
        self.check_engine_light.setColor(QColor(255, 0, 0))
        group_layout.addWidget(self.check_engine_light, 0, 0)
        
        # Индикатор ABS
        self.abs_light = WarningLight("ABS")
        self.abs_light.setColor(QColor(255, 165, 0))
        group_layout.addWidget(self.abs_light, 0, 1)
        
        # Индикатор подушек безопасности
        self.airbag_light = WarningLight("Airbag")
        self.airbag_light.setColor(QColor(255, 0, 0))
        group_layout.addWidget(self.airbag_light, 0, 2)
        
        # Индикатор иммобилайзера
        self.immobilizer_light = WarningLight("Immo")
        self.immobilizer_light.setColor(QColor(255, 255, 0))
        group_layout.addWidget(self.immobilizer_light, 1, 0)
        
        # Индикатор давления масла
        self.oil_pressure_light = WarningLight("Масло")
        self.oil_pressure_light.setColor(QColor(255, 0, 0))
        group_layout.addWidget(self.oil_pressure_light, 1, 1)
        
        # Индикатор температуры
        self.oil_temp_light = WarningLight("Температура")
        self.oil_temp_light.setColor(QColor(255, 165, 0))
        group_layout.addWidget(self.oil_temp_light, 1, 2)
        
        layout.addWidget(group, row, col, 1, 2)
        
    def create_charts_tabs(self):
        """Создание вкладок с графиками и таблицей"""
        tabs = QTabWidget()
        
        # График в реальном времени
        self.realtime_chart = RealTimeChart()
        self.realtime_chart.setTitle("Динамика параметров")
        self.realtime_chart.setYLabel("Значение")
        self.realtime_chart.setXLabel("Время")
        tabs.addTab(self.realtime_chart, "График")
        
        # Исторический график
        self.historical_chart = HistoricalChart()
        self.historical_chart.setTitle("Исторические данные")
        tabs.addTab(self.historical_chart, "История")
        
        # Таблица значений
        self.data_table = self.create_data_table()
        tabs.addTab(self.data_table, "Таблица")
        
        # Scatter plot
        self.scatter_plot = ScatterPlot()
        self.scatter_plot.setTitle("Корреляция параметров")
        tabs.addTab(self.scatter_plot, "Корреляция")
        
        # Bar chart
        self.bar_chart = BarChart()
        self.bar_chart.setTitle("Сравнение параметров")
        tabs.addTab(self.bar_chart, "Сравнение")
        
        return tabs
        
    def create_data_table(self):
        """Создание таблицы данных"""
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Параметр", 
            "Текущее значение", 
            "Минимум", 
            "Максимум", 
            "Среднее", 
            "Единицы"
        ])
        
        # Настройка внешнего вида
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        table.setShowGrid(True)
        
        # Контекстное меню
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self.show_table_context_menu)
        
        return table
        
    def show_table_context_menu(self, position):
        """Показ контекстного меню для таблицы"""
        menu = QMenu()
        
        copy_action = QAction("Копировать", self)
        copy_action.triggered.connect(self.copy_table_data)
        menu.addAction(copy_action)
        
        export_action = QAction("Экспорт в CSV", self)
        export_action.triggered.connect(self.export_table_to_csv)
        menu.addAction(export_action)
        
        menu.addSeparator()
        
        clear_action = QAction("Очистить таблицу", self)
        clear_action.triggered.connect(self.clear_table)
        menu.addAction(clear_action)
        
        menu.exec_(self.data_table.viewport().mapToGlobal(position))
        
    def create_status_panel(self):
        """Создание панели статуса"""
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(5, 2, 5, 2)
        
        # Индикатор подключения
        self.connection_indicator = LEDIndicator("Связь")
        self.connection_indicator.setColor(QColor(255, 0, 0))
        layout.addWidget(self.connection_indicator)
        
        # Индикатор записи
        self.recording_indicator = LEDIndicator("Запись")
        self.recording_indicator.setColor(QColor(255, 0, 0))
        layout.addWidget(self.recording_indicator)
        
        # Счетчик кадров
        self.frame_counter = QLabel("Кадры: 0")
        layout.addWidget(self.frame_counter)
        
        # Время записи
        self.recording_time = QLabel("Время: 00:00:00")
        layout.addWidget(self.recording_time)
        
        # Размер файла
        self.file_size_label = QLabel("Файл: 0 KB")
        layout.addWidget(self.file_size_label)
        
        # Прогресс сборки данных
        self.data_progress = QProgressBar()
        self.data_progress.setMaximumWidth(200)
        self.data_progress.setRange(0, 100)
        self.data_progress.setValue(0)
        layout.addWidget(self.data_progress)
        
        layout.addStretch()
        
        # Время последнего обновления
        self.last_update_label = QLabel("Последнее обновление: --:--:--")
        layout.addWidget(self.last_update_label)
        
        return panel
        
    def setup_connections(self):
        """Настройка соединений сигналов и слотов"""
        # Кнопки управления
        self.start_stop_btn.toggled.connect(self.toggle_data_stream)
        self.record_btn.toggled.connect(self.toggle_recording)
        self.interval_spin.valueChanged.connect(self.change_sampling_interval)
        
        # Сигналы от графиков
        self.realtime_chart.parameter_selected.connect(self.on_parameter_selected)
        self.historical_chart.range_changed.connect(self.on_history_range_changed)
        
        # Сигналы от датчиков
        self.data_updated.connect(self.update_all_gauges)
        
    def load_pid_list(self):
        """Загрузка списка PID из конфигурации"""
        try:
            # Загрузка из файла конфигурации
            config_path = os.path.join("config", "pid_list.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    pid_data = json.load(f)
                    
                for category, pids in pid_data.items():
                    self.pid_combo.addItem(f"--- {category} ---")
                    for pid_info in pids:
                        name = pid_info.get('name', '')
                        pid = pid_info.get('pid', '')
                        unit = pid_info.get('unit', '')
                        display_text = f"{name} ({pid}) - {unit}"
                        self.pid_combo.addItem(display_text, pid_info)
            else:
                # Стандартные PID
                default_pids = [
                    {"name": "Обороты двигателя", "pid": "010C", "unit": "об/мин"},
                    {"name": "Скорость", "pid": "010D", "unit": "км/ч"},
                    {"name": "Температура ОЖ", "pid": "0105", "unit": "°C"},
                    {"name": "Положение дросселя", "pid": "0111", "unit": "%"},
                    {"name": "Напряжение", "pid": "0142", "unit": "V"},
                    {"name": "Расход воздуха", "pid": "0110", "unit": "г/с"},
                    {"name": "Давление в коллекторе", "pid": "010B", "unit": "кПа"},
                    {"name": "Температура впускного воздуха", "pid": "010F", "unit": "°C"},
                    {"name": "Угол опережения", "pid": "010E", "unit": "град"},
                    {"name": "Долговременная коррекция топлива", "pid": "0107", "unit": "%"},
                    {"name": "Кратковременная коррекция топлива", "pid": "0106", "unit": "%"},
                    {"name": "Давление топлива", "pid": "010A", "unit": "кПа"},
                    {"name": "Уровень топлива", "pid": "012F", "unit": "%"},
                    {"name": "Пробег", "pid": "0131", "unit": "км"},
                    {"name": "Температура масла", "pid": "015C", "unit": "°C"},
                    {"name": "Абсолютное давление", "pid": "0133", "unit": "кПа"},
                ]
                
                for pid_info in default_pids:
                    display_text = f"{pid_info['name']} ({pid_info['pid']}) - {pid_info['unit']}"
                    self.pid_combo.addItem(display_text, pid_info)
                    
        except Exception as e:
            self.logger.error(f"Ошибка загрузки PID: {e}")
            
    def add_selected_pid(self):
        """Добавление выбранного PID для мониторинга"""
        index = self.pid_combo.currentIndex()
        if index < 0:
            return
            
        pid_data = self.pid_combo.currentData()
        if not pid_data or isinstance(pid_data, str):
            return
            
        pid = pid_data.get('pid')
        name = pid_data.get('name')
        
        if pid not in self.selected_pids:
            self.selected_pids.append(pid)
            
            # Создание нового датчика
            self.create_dynamic_gauge(pid, name, pid_data.get('unit', ''))
            
            # Добавление в график
            self.realtime_chart.add_parameter(pid, name, pid_data.get('unit', ''))
            
            self.logger.info(f"Добавлен PID: {name} ({pid})")
            
    def create_dynamic_gauge(self, pid, name, unit):
        """Создание динамического датчика"""
        # Определение типа датчика на основе имени
        if "температур" in name.lower():
            gauge = TemperatureGauge()
        elif "давлен" in name.lower():
            gauge = PressureGauge()
        elif "напряж" in name.lower():
            gauge = Voltmeter()
        elif "оборот" in name.lower() or "скорост" in name.lower():
            gauge = CircularGauge()
        else:
            gauge = CircularGauge()
            
        gauge.setTitle(name)
        gauge.setUnit(unit)
        
        # Определение диапазона
        if "010C" in pid:  # RPM
            gauge.setRange(0, 8000)
        elif "0105" in pid or "010F" in pid:  # Температура
            gauge.setRange(-40, 150)
        elif "0142" in pid:  # Напряжение
            gauge.setRange(10, 16)
        elif "0111" in pid:  # Дроссель
            gauge.setRange(0, 100)
        else:
            gauge.setRange(0, 100)
            
        # Добавление в layout
        row = len(self.gauges) // 4
        col = len(self.gauges) % 4
        
        self.gauges_layout.addWidget(gauge, row, col)
        self.gauges[pid] = gauge
        
        # Обновление размера контейнера
        self.gauges_container.setMinimumHeight((row + 1) * 200)
        
    def toggle_data_stream(self, enabled):
        """Включение/выключение потока данных"""
        if enabled:
            self.start_data_stream()
            self.start_stop_btn.setIcon(QIcon("assets/icons/pause.png"))
            self.start_stop_btn.setText("Стоп")
        else:
            self.stop_data_stream()
            self.start_stop_btn.setIcon(QIcon("assets/icons/play.png"))
            self.start_stop_btn.setText("Старт")
            
    def start_data_stream(self):
        """Запуск потока данных"""
        if not self.data_timer.isActive():
            self.data_timer.start(self.sampling_interval)
            self.connection_indicator.setColor(QColor(0, 255, 0))
            self.logger.info("Поток данных запущен")
            
    def stop_data_stream(self):
        """Остановка потока данных"""
        if self.data_timer.isActive():
            self.data_timer.stop()
            self.connection_indicator.setColor(QColor(255, 0, 0))
            self.logger.info("Поток данных остановлен")
            
    def toggle_recording(self, enabled):
        """Включение/выключение записи данных"""
        if enabled:
            self.start_recording()
            self.record_btn.setIcon(QIcon("assets/icons/stop_record.png"))
            self.record_btn.setText("Стоп запись")
        else:
            self.stop_recording()
            self.record_btn.setIcon(QIcon("assets/icons/record.png"))
            self.record_btn.setText("Запись")
            
    def start_recording(self):
        """Начало записи данных"""
        try:
            # Создание имени файла
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"niva_data_{timestamp}.csv"
            
            # Выбор папки для сохранения
            folder = self.settings.value("recording_folder", "recordings")
            os.makedirs(folder, exist_ok=True)
            
            self.recording_file = os.path.join(folder, filename)
            
            # Создание CSV файла
            with open(self.recording_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Заголовок
                headers = ['Timestamp'] + [pid for pid in self.selected_pids]
                writer.writerow(headers)
                
            self.is_recording = True
            self.recording_start_time = datetime.now()
            self.recording_indicator.setColor(QColor(255, 0, 0))
            self.recording_indicator.blink(True)
            
            self.recording_changed.emit(True)
            self.logger.info(f"Начата запись в файл: {self.recording_file}")
            
        except Exception as e:
            self.logger.error(f"Ошибка начала записи: {e}")
            self.record_btn.setChecked(False)
            
    def stop_recording(self):
        """Остановка записи данных"""
        self.is_recording = False
        self.recording_indicator.blink(False)
        self.recording_indicator.setColor(QColor(255, 0, 0))
        
        if self.recording_file:
            # Запись статистики
            self.save_recording_stats()
            
        self.recording_changed.emit(False)
        self.logger.info("Запись остановлена")
        
    def save_recording_stats(self):
        """Сохранение статистики записи"""
        try:
            if not self.recording_file:
                return
                
            stats_file = self.recording_file.replace('.csv', '_stats.json')
            stats = {
                'filename': os.path.basename(self.recording_file),
                'start_time': self.recording_start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'duration': (datetime.now() - self.recording_start_time).total_seconds(),
                'parameters': self.selected_pids,
                'sampling_interval': self.sampling_interval
            }
            
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"Ошибка сохранения статистики: {e}")
            
    def change_sampling_interval(self, interval):
        """Изменение интервала опроса"""
        self.sampling_interval = interval
        if self.data_timer.isActive():
            self.data_timer.setInterval(interval)
            
        self.settings.setValue("sampling_interval", interval)
        self.logger.info(f"Интервал опроса изменен на {interval} мс")
        
    def update_display(self):
        """Обновление отображения данных"""
        try:
            # Имитация получения данных (в реальном приложении здесь будет работа с ELM327)
            current_time = datetime.now()
            mock_data = self.generate_mock_data()
            
            # Обновление текущих данных
            self.current_data = mock_data
            
            # Добавление в исторические данные
            self.update_historical_data(mock_data, current_time)
            
            # Обновление датчиков
            self.data_updated.emit(mock_data)
            
            # Обновление графиков
            self.realtime_chart.update_data(mock_data, current_time)
            
            # Обновление таблицы
            self.update_data_table(mock_data)
            
            # Обновление индикаторов
            self.update_status_indicators(mock_data)
            
            # Запись данных, если включена запись
            if self.is_recording and self.recording_file:
                self.write_to_recording_file(mock_data, current_time)
                
            # Обновление статусной панели
            self.update_status_panel(current_time)
            
        except Exception as e:
            self.logger.error(f"Ошибка обновления данных: {e}")
            
    def generate_mock_data(self):
        """Генерация тестовых данных (для демонстрации)"""
        import random
        import math
        
        data = {}
        
        # Основные параметры
        if '010C' in self.selected_pids or not self.selected_pids:
            # RPM с имитацией работы двигателя
            time_factor = datetime.now().timestamp() / 10
            base_rpm = 800 + math.sin(time_factor) * 200
            noise = random.uniform(-50, 50)
            data['010C'] = max(0, base_rpm + noise)
            
        if '010D' in self.selected_pids or not self.selected_pids:
            data['010D'] = random.uniform(0, 120)
            
        if '0105' in self.selected_pids or not self.selected_pids:
            data['0105'] = random.uniform(85, 95)
            
        if '0111' in self.selected_pids or not self.selected_pids:
            data['0111'] = random.uniform(0, 30)
            
        if '0142' in self.selected_pids or not self.selected_pids:
            data['0142'] = random.uniform(13.5, 14.5)
            
        if '0110' in self.selected_pids or not self.selected_pids:
            data['0110'] = random.uniform(5, 20)
            
        if '010B' in self.selected_pids or not self.selected_pids:
            data['010B'] = random.uniform(95, 105)
            
        # Добавление остальных выбранных PID
        for pid in self.selected_pids:
            if pid not in data:
                data[pid] = random.uniform(0, 100)
                
        return data
        
    def update_historical_data(self, data, timestamp):
        """Обновление исторических данных"""
        for pid, value in data.items():
            if pid not in self.historical_data:
                self.historical_data[pid] = {
                    'timestamps': deque(maxlen=self.max_history_points),
                    'values': deque(maxlen=self.max_history_points),
                    'min': float('inf'),
                    'max': float('-inf'),
                    'sum': 0,
                    'count': 0
                }
                
            history = self.historical_data[pid]
            history['timestamps'].append(timestamp)
            history['values'].append(value)
            
            # Обновление статистики
            history['min'] = min(history['min'], value)
            history['max'] = max(history['max'], value)
            history['sum'] += value
            history['count'] += 1
            
    def update_all_gauges(self, data):
        """Обновление всех датчиков"""
        # Основные датчики
        if '010C' in data:
            self.tachometer.setValue(data['010C'])
            
        if '010D' in data:
            self.speedometer.setValue(data['010D'])
            
        if '0105' in data:
            self.coolant_temp_gauge.setValue(data['0105'])
            
        if '0142' in data:
            self.voltmeter.setValue(data['0142'])
            
        if '0111' in data:
            self.throttle_gauge.setValue(data['0111'])
            
        if '0104' in data:
            self.engine_load_gauge.setValue(data.get('0104', 0))
            
        if '0110' in data:
            self.maf_gauge.setValue(data['0110'])
            
        if '010B' in data:
            self.map_gauge.setValue(data['010B'])
            
        # Динамические датчики
        for pid, gauge in self.gauges.items():
            if pid in data:
                gauge.setValue(data[pid])
                
    def update_data_table(self, data):
        """Обновление таблицы данных"""
        self.data_table.setRowCount(len(data))
        
        for row, (pid, value) in enumerate(data.items()):
            # Получение информации о параметре
            param_name = self.get_parameter_name(pid)
            unit = self.get_parameter_unit(pid)
            
            # Текущее значение
            value_item = QTableWidgetItem(format_value(value, unit))
            value_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            # Минимальное значение
            min_value = self.historical_data.get(pid, {}).get('min', value)
            min_item = QTableWidgetItem(format_value(min_value, unit))
            min_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            # Максимальное значение
            max_value = self.historical_data.get(pid, {}).get('max', value)
            max_item = QTableWidgetItem(format_value(max_value, unit))
            max_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            # Среднее значение
            avg_value = self.calculate_average(pid)
            avg_item = QTableWidgetItem(format_value(avg_value, unit))
            avg_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            # Заполнение строки
            self.data_table.setItem(row, 0, QTableWidgetItem(param_name))
            self.data_table.setItem(row, 1, value_item)
            self.data_table.setItem(row, 2, min_item)
            self.data_table.setItem(row, 3, max_item)
            self.data_table.setItem(row, 4, avg_item)
            self.data_table.setItem(row, 5, QTableWidgetItem(unit))
            
    def get_parameter_name(self, pid):
        """Получение имени параметра по PID"""
        for i in range(self.pid_combo.count()):
            data = self.pid_combo.itemData(i)
            if isinstance(data, dict) and data.get('pid') == pid:
                return data.get('name', pid)
        return pid
        
    def get_parameter_unit(self, pid):
        """Получение единиц измерения по PID"""
        for i in range(self.pid_combo.count()):
            data = self.pid_combo.itemData(i)
            if isinstance(data, dict) and data.get('pid') == pid:
                return data.get('unit', '')
        return ''
        
    def calculate_average(self, pid):
        """Расчет среднего значения"""
        history = self.historical_data.get(pid)
        if not history or history['count'] == 0:
            return 0
            
        return history['sum'] / history['count']
        
    def update_status_indicators(self, data):
        """Обновление индикаторов состояния"""
        # Имитация состояния систем
        import random
        
        self.check_engine_light.setState(random.random() > 0.9)
        self.abs_light.setState(random.random() > 0.95)
        self.airbag_light.setState(random.random() > 0.98)
        self.immobilizer_light.setState(random.random() > 0.99)
        
        # Индикатор давления масла (имитация)
        oil_pressure_warning = data.get('010A', 0) < 150 if '010A' in data else random.random() > 0.97
        self.oil_pressure_light.setState(oil_pressure_warning)
        
        # Индикатор температуры масла
        oil_temp_warning = data.get('0105', 0) > 100 if '0105' in data else random.random() > 0.96
        self.oil_temp_light.setState(oil_temp_warning)
        
    def write_to_recording_file(self, data, timestamp):
        """Запись данных в файл"""
        try:
            with open(self.recording_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                row = [timestamp.isoformat()]
                
                for pid in self.selected_pids:
                    row.append(data.get(pid, ''))
                    
                writer.writerow(row)
                
        except Exception as e:
            self.logger.error(f"Ошибка записи в файл: {e}")
            
    def update_status_panel(self, timestamp):
        """Обновление панели статуса"""
        # Счетчик кадров
        total_frames = sum(h['count'] for h in self.historical_data.values())
        self.frame_counter.setText(f"Кадры: {total_frames}")
        
        # Время записи
        if self.is_recording and self.recording_start_time:
            duration = timestamp - self.recording_start_time
            hours, remainder = divmod(duration.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.recording_time.setText(f"Время: {hours:02d}:{minutes:02d}:{seconds:02d}")
            
        # Размер файла
        if self.recording_file and os.path.exists(self.recording_file):
            size_kb = os.path.getsize(self.recording_file) / 1024
            self.file_size_label.setText(f"Файл: {size_kb:.1f} KB")
            
        # Прогресс
        if self.historical_data:
            first_pid = next(iter(self.historical_data))
            count = self.historical_data[first_pid]['count']
            progress = min(100, int(count * 100 / self.max_history_points))
            self.data_progress.setValue(progress)
            
        # Время последнего обновления
        time_str = timestamp.strftime("%H:%M:%S")
        self.last_update_label.setText(f"Последнее обновление: {time_str}")
        
    def clear_data(self):
        """Очистка всех данных"""
        reply = QMessageBox.question(
            self, 
            "Очистка данных",
            "Вы уверены, что хотите очистить все данные?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.historical_data.clear()
            self.realtime_chart.clear()
            self.historical_chart.clear()
            self.data_table.setRowCount(0)
            self.data_progress.setValue(0)
            self.frame_counter.setText("Кадры: 0")
            
            # Сброс датчиков
            for gauge in self.gauges.values():
                gauge.setValue(0)
                
            self.logger.info("Все данные очищены")
            
    def save_data(self):
        """Сохранение данных"""
        if not self.historical_data:
            QMessageBox.warning(self, "Нет данных", "Нет данных для сохранения")
            return
            
        try:
            # Выбор формата
            formats = ["CSV (*.csv)", "JSON (*.json)", "Excel (*.xlsx)"]
            format_filter = ";;".join(formats)
            
            filename, selected_filter = QFileDialog.getSaveFileName(
                self,
                "Сохранить данные",
                f"niva_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                format_filter
            )
            
            if not filename:
                return
                
            # Определение формата
            if "CSV" in selected_filter:
                self.save_to_csv(filename)
            elif "JSON" in selected_filter:
                self.save_to_json(filename)
            elif "Excel" in selected_filter:
                self.save_to_excel(filename)
                
            self.logger.info(f"Данные сохранены в {filename}")
            QMessageBox.information(self, "Сохранено", "Данные успешно сохранены")
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения данных: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить данные: {e}")
            
    def save_to_csv(self, filename):
        """Сохранение в CSV"""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Заголовок
            headers = ['Timestamp']
            for pid in self.historical_data.keys():
                headers.append(self.get_parameter_name(pid))
            writer.writerow(headers)
            
            # Данные
            if self.historical_data:
                first_pid = next(iter(self.historical_data))
                timestamps = list(self.historical_data[first_pid]['timestamps'])
                
                for i, timestamp in enumerate(timestamps):
                    row = [timestamp.isoformat()]
                    for pid in self.historical_data.keys():
                        values = list(self.historical_data[pid]['values'])
                        if i < len(values):
                            row.append(values[i])
                        else:
                            row.append('')
                    writer.writerow(row)
                    
    def save_to_json(self, filename):
        """Сохранение в JSON"""
        data = {
            'metadata': {
                'export_time': datetime.now().isoformat(),
                'parameters_count': len(self.historical_data),
                'data_points': len(next(iter(self.historical_data.values()))['timestamps']) if self.historical_data else 0
            },
            'parameters': {},
            'data': []
        }
        
        # Параметры
        for pid, history in self.historical_data.items():
            data['parameters'][pid] = {
                'name': self.get_parameter_name(pid),
                'unit': self.get_parameter_unit(pid),
                'min': history['min'],
                'max': history['max'],
                'average': history['sum'] / history['count'] if history['count'] > 0 else 0
            }
            
        # Данные
        if self.historical_data:
            first_pid = next(iter(self.historical_data))
            timestamps = list(self.historical_data[first_pid]['timestamps'])
            
            for i, timestamp in enumerate(timestamps):
                entry = {'timestamp': timestamp.isoformat()}
                for pid, history in self.historical_data.items():
                    values = list(history['values'])
                    if i < len(values):
                        entry[pid] = values[i]
                data['data'].append(entry)
                
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
    def save_to_excel(self, filename):
        """Сохранение в Excel"""
        try:
            import pandas as pd
            
            # Подготовка данных
            data_dict = {}
            
            if self.historical_data:
                first_pid = next(iter(self.historical_data))
                timestamps = list(self.historical_data[first_pid]['timestamps'])
                
                data_dict['Timestamp'] = [ts.isoformat() for ts in timestamps]
                
                for pid, history in self.historical_data.items():
                    param_name = self.get_parameter_name(pid)
                    values = list(history['values'])
                    # Дополнение значений если нужно
                    if len(values) < len(timestamps):
                        values.extend([None] * (len(timestamps) - len(values)))
                    data_dict[param_name] = values
                    
            # Создание DataFrame
            df = pd.DataFrame(data_dict)
            
            # Сохранение
            df.to_excel(filename, index=False)
            
        except ImportError:
            QMessageBox.warning(
                self,
                "Библиотека не установлена",
                "Для сохранения в Excel установите библиотеку pandas и openpyxl"
            )
            
    def copy_table_data(self):
        """Копирование данных из таблицы"""
        try:
            import pandas as pd
            
            # Получение данных из таблицы
            data = []
            for row in range(self.data_table.rowCount()):
                row_data = []
                for col in range(self.data_table.columnCount()):
                    item = self.data_table.item(row, col)
                    row_data.append(item.text() if item else '')
                data.append(row_data)
                
            # Создание DataFrame и копирование в буфер
            if data:
                df = pd.DataFrame(data, columns=[
                    self.data_table.horizontalHeaderItem(i).text() 
                    for i in range(self.data_table.columnCount())
                ])
                df.to_clipboard(index=False, sep='\t')
                
                QMessageBox.information(self, "Скопировано", "Данные скопированы в буфер обмена")
                
        except Exception as e:
            self.logger.error(f"Ошибка копирования: {e}")
            
    def export_table_to_csv(self):
        """Экспорт таблицы в CSV"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Экспорт таблицы",
                f"niva_table_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV (*.csv)"
            )
            
            if filename:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    # Заголовок
                    headers = [
                        self.data_table.horizontalHeaderItem(i).text() 
                        for i in range(self.data_table.columnCount())
                    ]
                    writer.writerow(headers)
                    
                    # Данные
                    for row in range(self.data_table.rowCount()):
                        row_data = []
                        for col in range(self.data_table.columnCount()):
                            item = self.data_table.item(row, col)
                            row_data.append(item.text() if item else '')
                        writer.writerow(row_data)
                        
                self.logger.info(f"Таблица экспортирована в {filename}")
                QMessageBox.information(self, "Экспорт", "Таблица успешно экспортирована")
                
        except Exception as e:
            self.logger.error(f"Ошибка экспорта: {e}")
            
    def clear_table(self):
        """Очистка таблицы"""
        self.data_table.setRowCount(0)
        
    def on_parameter_selected(self, pid):
        """Обработка выбора параметра на графике"""
        if pid in self.gauges:
            # Подсветка датчика
            self.gauges[pid].highlight(True)
            
    def on_history_range_changed(self, start_time, end_time):
        """Обработка изменения диапазона истории"""
        # Можно реализовать фильтрацию данных по времени
        pass
        
    def show_display_settings(self):
        """Показ настроек отображения"""
        from ui.settings_dialog import DisplaySettingsDialog
        dialog = DisplaySettingsDialog(self)
        if dialog.exec_() == dialog.Accepted:
            self.apply_display_settings(dialog.get_settings())
            
    def show_chart_settings(self):
        """Показ настроек графиков"""
        from ui.settings_dialog import ChartSettingsDialog
        dialog = ChartSettingsDialog(self)
        if dialog.exec_() == dialog.Accepted:
            self.apply_chart_settings(dialog.get_settings())
            
    def show_gauge_settings(self):
        """Показ настроек датчиков"""
        from ui.settings_dialog import GaugeSettingsDialog
        dialog = GaugeSettingsDialog(self)
        if dialog.exec_() == dialog.Accepted:
            self.apply_gauge_settings(dialog.get_settings())
            
    def apply_display_settings(self, settings):
        """Применение настроек отображения"""
        # Применение настроек
        pass
        
    def apply_chart_settings(self, settings):
        """Применение настроек графиков"""
        # Применение настроек
        pass
        
    def apply_gauge_settings(self, settings):
        """Применение настроек датчиков"""
        # Применение настроек
        pass
        
    def reset_settings(self):
        """Сброс настроек"""
        reply = QMessageBox.question(
            self,
            "Сброс настроек",
            "Вы уверены, что хотите сбросить все настройки к значениям по умолчанию?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.settings.clear()
            self.load_settings()
            QMessageBox.information(self, "Сброс", "Настройки сброшены")
            
    def load_settings(self):
        """Загрузка настроек"""
        self.sampling_interval = self.settings.value("sampling_interval", 100, type=int)
        self.interval_spin.setValue(self.sampling_interval)
        
        # Загрузка сохраненных PID
        saved_pids = self.settings.value("selected_pids", [])
        if saved_pids:
            self.selected_pids = saved_pids
            # Восстановление датчиков
            for pid in saved_pids:
                self.restore_gauge(pid)
                
    def restore_gauge(self, pid):
        """Восстановление датчика по PID"""
        # Поиск информации о PID
        for i in range(self.pid_combo.count()):
            data = self.pid_combo.itemData(i)
            if isinstance(data, dict) and data.get('pid') == pid:
                self.create_dynamic_gauge(
                    pid, 
                    data.get('name', pid), 
                    data.get('unit', '')
                )
                break
                
    def save_settings(self):
        """Сохранение настроек"""
        self.settings.setValue("sampling_interval", self.sampling_interval)
        self.settings.setValue("selected_pids", self.selected_pids)
        
    def closeEvent(self, event):
        """Обработка закрытия"""
        self.save_settings()
        self.stop_data_stream()
        self.stop_recording()
        super().closeEvent(event)
        
    @pyqtSlot(dict)
    def on_diagnostic_data_received(self, data):
        """Обработка полученных диагностических данных"""
        # Этот метод будет вызываться извне при получении реальных данных
        current_time = datetime.now()
        self.current_data = data
        
        # Обновление исторических данных
        self.update_historical_data(data, current_time)
        
        # Обновление UI
        self.data_updated.emit(data)
        self.realtime_chart.update_data(data, current_time)
        self.update_data_table(data)
        self.update_status_panel(current_time)
        
        # Запись, если включена
        if self.is_recording and self.recording_file:
            self.write_to_recording_file(data, current_time)
            
    def set_connection_status(self, connected):
        """Установка статуса подключения"""
        color = QColor(0, 255, 0) if connected else QColor(255, 0, 0)
        self.connection_indicator.setColor(color)
        
        if not connected:
            self.stop_data_stream()
            self.start_stop_btn.setChecked(False)
            
    def get_current_data(self):
        """Получение текущих данных"""
        return self.current_data.copy()
        
    def get_historical_data(self):
        """Получение исторических данных"""
        return self.historical_data.copy()
        
    def reset(self):
        """Сброс панели"""
        self.stop_data_stream()
        self.stop_recording()
        self.clear_data()
        
        # Сброс кнопок
        self.start_stop_btn.setChecked(False)
        self.record_btn.setChecked(False)
        
        # Сброс индикаторов
        self.connection_indicator.setColor(QColor(255, 0, 0))
        self.recording_indicator.setColor(QColor(255, 0, 0))
        
        self.logger.info("Панель текущих данных сброшена")