"""
Панель диагностики - полная версия
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QGroupBox, QLabel, QPushButton, QComboBox,
                             QProgressBar, QTableWidget, QTableWidgetItem,
                             QTextEdit, QTabWidget, QTreeWidget, QTreeWidgetItem,
                             QHeaderView, QSplitter, QFrame, QCheckBox,
                             QSpinBox, QDoubleSpinBox, QLineEdit, QMessageBox,
                             QFileDialog, QInputDialog, QListWidget, QListWidgetItem,
                             QApplication, QStyleFactory)
from PyQt5.QtCore import (Qt, pyqtSignal, QTimer, QDateTime, QSize, 
                         QPropertyAnimation, QEasingCurve, QThread, pyqtSlot)
from PyQt5.QtGui import (QFont, QIcon, QPalette, QColor, QBrush, QPen,
                        QPainter, QLinearGradient, QFontMetrics)
import time
import json
from datetime import datetime
import os

class DiagnosticPanel(QWidget):
    """Панель для выполнения диагностики"""
    
    # Сигналы
    diagnostic_started = pyqtSignal()
    diagnostic_completed = pyqtSignal(dict)
    diagnostic_error = pyqtSignal(str)
    status_update = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.diagnostics_engine = None
        self.current_results = {}
        self.diagnostic_in_progress = False
        self.setup_ui()
        self.setup_connections()
        self.setup_styles()
        
    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Верхняя панель управления
        self.create_control_panel()
        main_layout.addWidget(self.control_panel)
        
        # Разделитель
        splitter = QSplitter(Qt.Vertical)
        
        # Левая панель - результаты диагностики
        self.create_results_panel()
        splitter.addWidget(self.results_panel)
        
        # Правая панель - детали и логи
        self.create_details_panel()
        splitter.addWidget(self.details_panel)
        
        splitter.setSizes([400, 200])
        main_layout.addWidget(splitter)
        
        # Нижняя панель - прогресс и статистика
        self.create_status_panel()
        main_layout.addWidget(self.status_panel)
        
        self.setMinimumSize(1000, 700)
        
    def create_control_panel(self):
        """Создание панели управления"""
        self.control_panel = QGroupBox("Управление диагностикой")
        control_layout = QGridLayout()
        control_layout.setSpacing(15)
        
        # Выбор модели автомобиля
        model_label = QLabel("Модель автомобиля:")
        model_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(250)
        self.model_combo.setFont(QFont("Segoe UI", 10))
        self.model_combo.addItems([
            "Chevrolet Niva 1.7i (2002-2009)",
            "Chevrolet Niva 1.7i (2010-2020)",
            "Chevrolet Niva 1.8i (2014-2020)",
            "Chevrolet Niva Модерн (2021-н.в.)",
            "Другая модель"
        ])
        self.model_combo.setCurrentIndex(1)
        
        # Поле для ввода VIN
        vin_label = QLabel("VIN код:")
        vin_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        
        self.vin_edit = QLineEdit()
        self.vin_edit.setPlaceholderText("Введите VIN код автомобиля")
        self.vin_edit.setFont(QFont("Segoe UI", 10))
        self.vin_edit.setMaximumWidth(200)
        
        # Кнопка сканирования VIN
        self.scan_vin_btn = QPushButton("Сканировать")
        self.scan_vin_btn.setIcon(QIcon("assets/icons/scan.png"))
        self.scan_vin_btn.setToolTip("Автоматическое сканирование VIN")
        self.scan_vin_btn.setMaximumWidth(120)
        
        # Кнопки управления
        self.full_diagnostic_btn = QPushButton("Полная диагностика")
        self.full_diagnostic_btn.setIcon(QIcon("assets/icons/full_scan.png"))
        self.full_diagnostic_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.full_diagnostic_btn.setMinimumHeight(40)
        self.full_diagnostic_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        
        self.quick_diagnostic_btn = QPushButton("Быстрая проверка")
        self.quick_diagnostic_btn.setIcon(QIcon("assets/icons/quick_scan.png"))
        self.quick_diagnostic_btn.setFont(QFont("Segoe UI", 10))
        self.quick_diagnostic_btn.setMinimumHeight(35)
        
        self.stop_diagnostic_btn = QPushButton("Остановить")
        self.stop_diagnostic_btn.setIcon(QIcon("assets/icons/stop.png"))
        self.stop_diagnostic_btn.setFont(QFont("Segoe UI", 10))
        self.stop_diagnostic_btn.setMinimumHeight(35)
        self.stop_diagnostic_btn.setEnabled(False)
        
        self.save_results_btn = QPushButton("Сохранить результаты")
        self.save_results_btn.setIcon(QIcon("assets/icons/save.png"))
        self.save_results_btn.setFont(QFont("Segoe UI", 10))
        self.save_results_btn.setMinimumHeight(35)
        
        # Чекбоксы выбора систем
        systems_group = QGroupBox("Выбор систем")
        systems_layout = QGridLayout()
        
        self.engine_check = QCheckBox("Двигатель (ECU)")
        self.engine_check.setChecked(True)
        self.abs_check = QCheckBox("АБС")
        self.abs_check.setChecked(True)
        self.airbag_check = QCheckBox("Подушки безопасности")
        self.airbag_check.setChecked(True)
        self.immo_check = QCheckBox("Иммобилайзер")
        self.instrument_check = QCheckBox("Приборная панель")
        self.ac_check = QCheckBox("Климат-контроль")
        
        systems_layout.addWidget(self.engine_check, 0, 0)
        systems_layout.addWidget(self.abs_check, 0, 1)
        systems_layout.addWidget(self.airbag_check, 0, 2)
        systems_layout.addWidget(self.immo_check, 1, 0)
        systems_layout.addWidget(self.instrument_check, 1, 1)
        systems_layout.addWidget(self.ac_check, 1, 2)
        systems_group.setLayout(systems_layout)
        
        # Расположение элементов
        control_layout.addWidget(model_label, 0, 0)
        control_layout.addWidget(self.model_combo, 0, 1, 1, 2)
        control_layout.addWidget(vin_label, 0, 3)
        control_layout.addWidget(self.vin_edit, 0, 4)
        control_layout.addWidget(self.scan_vin_btn, 0, 5)
        
        control_layout.addWidget(self.full_diagnostic_btn, 1, 0, 1, 2)
        control_layout.addWidget(self.quick_diagnostic_btn, 1, 2, 1, 2)
        control_layout.addWidget(self.stop_diagnostic_btn, 1, 4, 1, 2)
        control_layout.addWidget(self.save_results_btn, 2, 0, 1, 3)
        
        control_layout.addWidget(systems_group, 3, 0, 1, 6)
        
        self.control_panel.setLayout(control_layout)
        
    def create_results_panel(self):
        """Создание панели результатов"""
        self.results_panel = QGroupBox("Результаты диагностики")
        results_layout = QVBoxLayout()
        
        # Виджет с вкладками для разных типов результатов
        self.results_tabs = QTabWidget()
        self.results_tabs.setTabPosition(QTabWidget.North)
        self.results_tabs.setFont(QFont("Segoe UI", 10))
        
        # Вкладка: Общий статус
        self.create_summary_tab()
        
        # Вкладка: Системы и модули
        self.create_systems_tab()
        
        # Вкладка: Графики
        self.create_graphs_tab()
        
        # Вкладка: Статистика
        self.create_statistics_tab()
        
        results_layout.addWidget(self.results_tabs)
        self.results_panel.setLayout(results_layout)
        
    def create_summary_tab(self):
        """Создание вкладки с общей информацией"""
        summary_widget = QWidget()
        layout = QVBoxLayout()
        
        # Панель статуса
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        status_layout = QGridLayout()
        
        self.overall_status = QLabel("Статус: Не выполнена")
        self.overall_status.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.overall_status.setStyleSheet("color: #666666;")
        
        self.overall_icon = QLabel()
        self.overall_icon.setPixmap(QIcon("assets/icons/waiting.png").pixmap(32, 32))
        
        self.diagnostic_time = QLabel("Время: --:--")
        self.diagnostic_time.setFont(QFont("Segoe UI", 10))
        
        self.errors_count = QLabel("Ошибок: 0")
        self.errors_count.setFont(QFont("Segoe UI", 10))
        
        self.warnings_count = QLabel("Предупреждений: 0")
        self.warnings_count.setFont(QFont("Segoe UI", 10))
        
        self.systems_checked = QLabel("Проверено систем: 0/6")
        self.systems_checked.setFont(QFont("Segoe UI", 10))
        
        status_layout.addWidget(self.overall_icon, 0, 0, 2, 1, Qt.AlignCenter)
        status_layout.addWidget(self.overall_status, 0, 1, 1, 3)
        status_layout.addWidget(self.diagnostic_time, 1, 1)
        status_layout.addWidget(self.errors_count, 1, 2)
        status_layout.addWidget(self.warnings_count, 1, 3)
        status_layout.addWidget(self.systems_checked, 1, 4)
        
        status_frame.setLayout(status_layout)
        layout.addWidget(status_frame)
        
        # Таблица с основными показателями
        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(4)
        self.summary_table.setHorizontalHeaderLabels([
            "Параметр", "Значение", "Единицы", "Статус"
        ])
        self.summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.summary_table.setFont(QFont("Segoe UI", 9))
        self.summary_table.setAlternatingRowColors(True)
        self.summary_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        layout.addWidget(self.summary_table)
        
        summary_widget.setLayout(layout)
        self.results_tabs.addTab(summary_widget, QIcon("assets/icons/summary.png"), "Общая информация")
        
    def create_systems_tab(self):
        """Создание вкладки с системами"""
        systems_widget = QWidget()
        layout = QVBoxLayout()
        
        # Дерево систем
        self.systems_tree = QTreeWidget()
        self.systems_tree.setHeaderLabels(["Система", "Статус", "Ошибки", "Время проверки"])
        self.systems_tree.setFont(QFont("Segoe UI", 9))
        self.systems_tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.systems_tree.setColumnWidth(0, 250)
        
        # Предварительное заполнение дерева
        systems = [
            ("Двигатель (ECU)", "Ожидание", "0", "--:--"),
            ("Антиблокировочная система (ABS)", "Ожидание", "0", "--:--"),
            ("Подушки безопасности", "Ожидание", "0", "--:--"),
            ("Иммобилайзер", "Ожидание", "0", "--:--"),
            ("Приборная панель", "Ожидание", "0", "--:--"),
            ("Климат-контроль", "Ожидание", "0", "--:--")
        ]
        
        for system in systems:
            item = QTreeWidgetItem(self.systems_tree, system)
            item.setIcon(0, QIcon("assets/icons/system.png"))
            
        layout.addWidget(self.systems_tree)
        
        # Кнопки управления системами
        buttons_layout = QHBoxLayout()
        
        self.refresh_system_btn = QPushButton("Обновить систему")
        self.refresh_system_btn.setIcon(QIcon("assets/icons/refresh.png"))
        self.refresh_system_btn.setEnabled(False)
        
        self.detail_system_btn = QPushButton("Детальная диагностика")
        self.detail_system_btn.setIcon(QIcon("assets/icons/detail.png"))
        self.detail_system_btn.setEnabled(False)
        
        self.test_system_btn = QPushButton("Тест системы")
        self.test_system_btn.setIcon(QIcon("assets/icons/test.png"))
        self.test_system_btn.setEnabled(False)
        
        buttons_layout.addWidget(self.refresh_system_btn)
        buttons_layout.addWidget(self.detail_system_btn)
        buttons_layout.addWidget(self.test_system_btn)
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
        
        systems_widget.setLayout(layout)
        self.results_tabs.addTab(systems_widget, QIcon("assets/icons/systems.png"), "Системы")
        
    def create_graphs_tab(self):
        """Создание вкладки с графиками"""
        graphs_widget = QWidget()
        layout = QVBoxLayout()
        
        # Выбор параметров для графиков
        graph_controls = QFrame()
        graph_controls_layout = QHBoxLayout()
        
        graph_param_label = QLabel("Параметр для графика:")
        graph_param_label.setFont(QFont("Segoe UI", 10))
        
        self.graph_param_combo = QComboBox()
        self.graph_param_combo.addItems([
            "Обороты двигателя (RPM)",
            "Скорость автомобиля",
            "Температура охлаждающей жидкости",
            "Положение дроссельной заслонки",
            "Напряжение бортовой сети",
            "Расход воздуха"
        ])
        self.graph_param_combo.setMinimumWidth(250)
        
        self.graph_type_combo = QComboBox()
        self.graph_type_combo.addItems(["Линейный график", "Столбчатая диаграмма", "Круговая диаграмма"])
        
        self.start_graph_btn = QPushButton("Начать запись")
        self.start_graph_btn.setIcon(QIcon("assets/icons/record.png"))
        
        self.stop_graph_btn = QPushButton("Остановить запись")
        self.stop_graph_btn.setIcon(QIcon("assets/icons/stop_record.png"))
        self.stop_graph_btn.setEnabled(False)
        
        self.clear_graph_btn = QPushButton("Очистить график")
        self.clear_graph_btn.setIcon(QIcon("assets/icons/clear.png"))
        
        graph_controls_layout.addWidget(graph_param_label)
        graph_controls_layout.addWidget(self.graph_param_combo)
        graph_controls_layout.addWidget(self.graph_type_combo)
        graph_controls_layout.addWidget(self.start_graph_btn)
        graph_controls_layout.addWidget(self.stop_graph_btn)
        graph_controls_layout.addWidget(self.clear_graph_btn)
        graph_controls_layout.addStretch()
        
        graph_controls.setLayout(graph_controls_layout)
        layout.addWidget(graph_controls)
        
        # Область для графика (заглушка - в реальном проекте используйте matplotlib или pyqtgraph)
        self.graph_area = QTextEdit()
        self.graph_area.setReadOnly(True)
        self.graph_area.setFont(QFont("Courier New", 10))
        self.graph_area.setPlainText("Графики будут отображаться здесь.\n\n"
                                    "Для отображения реальных графиков необходимо:\n"
                                    "1. Установить matplotlib или pyqtgraph\n"
                                    "2. Реализовать класс GraphWidget\n"
                                    "3. Подключить получение данных в реальном времени")
        
        layout.addWidget(self.graph_area)
        
        # Статистика графика
        graph_stats = QFrame()
        graph_stats_layout = QHBoxLayout()
        
        self.graph_min_label = QLabel("Минимум: --")
        self.graph_max_label = QLabel("Максимум: --")
        self.graph_avg_label = QLabel("Среднее: --")
        self.graph_samples_label = QLabel("Записей: 0")
        
        graph_stats_layout.addWidget(self.graph_min_label)
        graph_stats_layout.addWidget(QLabel("|"))
        graph_stats_layout.addWidget(self.graph_max_label)
        graph_stats_layout.addWidget(QLabel("|"))
        graph_stats_layout.addWidget(self.graph_avg_label)
        graph_stats_layout.addWidget(QLabel("|"))
        graph_stats_layout.addWidget(self.graph_samples_label)
        graph_stats_layout.addStretch()
        
        graph_stats.setLayout(graph_stats_layout)
        layout.addWidget(graph_stats)
        
        graphs_widget.setLayout(layout)
        self.results_tabs.addTab(graphs_widget, QIcon("assets/icons/graph.png"), "Графики")
        
    def create_statistics_tab(self):
        """Создание вкладки со статистикой"""
        stats_widget = QWidget()
        layout = QVBoxLayout()
        
        # Таблица статистики
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(3)
        self.stats_table.setHorizontalHeaderLabels(["Параметр", "Значение", "Описание"])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.setFont(QFont("Segoe UI", 9))
        
        # Предварительное заполнение
        stats_data = [
            ["Общее время диагностики", "--", "Время выполнения полной диагностики"],
            ["Количество запросов", "0", "Общее число отправленных команд"],
            ["Успешные ответы", "0", "Количество корректных ответов"],
            ["Ошибки связи", "0", "Количество ошибок при обмене данными"],
            ["Скорость обмена", "--", "Средняя скорость передачи данных"],
            ["Потребление памяти", "--", "Использование памяти приложением"],
            ["Версия ПО ЭБУ", "--", "Версия программного обеспечения контроллера"],
            ["Дата калибровки", "--", "Дата последней калибровки ЭБУ"]
        ]
        
        self.stats_table.setRowCount(len(stats_data))
        for i, row in enumerate(stats_data):
            for j, cell in enumerate(row):
                item = QTableWidgetItem(cell)
                if j == 1:  # Значение - выделяем жирным
                    item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                self.stats_table.setItem(i, j, item)
        
        layout.addWidget(self.stats_table)
        
        # Кнопки экспорта
        export_layout = QHBoxLayout()
        
        self.export_csv_btn = QPushButton("Экспорт в CSV")
        self.export_csv_btn.setIcon(QIcon("assets/icons/csv.png"))
        
        self.export_excel_btn = QPushButton("Экспорт в Excel")
        self.export_excel_btn.setIcon(QIcon("assets/icons/excel.png"))
        
        self.export_json_btn = QPushButton("Экспорт в JSON")
        self.export_json_btn.setIcon(QIcon("assets/icons/json.png"))
        
        export_layout.addWidget(self.export_csv_btn)
        export_layout.addWidget(self.export_excel_btn)
        export_layout.addWidget(self.export_json_btn)
        export_layout.addStretch()
        
        layout.addLayout(export_layout)
        
        stats_widget.setLayout(layout)
        self.results_tabs.addTab(stats_widget, QIcon("assets/icons/stats.png"), "Статистика")
        
    def create_details_panel(self):
        """Создание панели деталей"""
        self.details_panel = QGroupBox("Детали и логи")
        details_layout = QVBoxLayout()
        
        # Виджет с вкладками
        self.details_tabs = QTabWidget()
        
        # Вкладка: Лог выполнения
        log_widget = QWidget()
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 9))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Courier New', monospace;
            }
        """)
        
        # Кнопки управления логом
        log_buttons = QHBoxLayout()
        
        self.clear_log_btn = QPushButton("Очистить лог")
        self.clear_log_btn.setIcon(QIcon("assets/icons/clear.png"))
        
        self.save_log_btn = QPushButton("Сохранить лог")
        self.save_log_btn.setIcon(QIcon("assets/icons/save.png"))
        
        self.pause_log_btn = QPushButton("Пауза")
        self.pause_log_btn.setIcon(QIcon("assets/icons/pause.png"))
        self.pause_log_btn.setCheckable(True)
        
        log_buttons.addWidget(self.clear_log_btn)
        log_buttons.addWidget(self.save_log_btn)
        log_buttons.addWidget(self.pause_log_btn)
        log_buttons.addStretch()
        
        log_layout.addWidget(self.log_text)
        log_layout.addLayout(log_buttons)
        log_widget.setLayout(log_layout)
        
        # Вкладка: Сырые данные
        raw_widget = QWidget()
        raw_layout = QVBoxLayout()
        
        self.raw_data_text = QTextEdit()
        self.raw_data_text.setReadOnly(True)
        self.raw_data_text.setFont(QFont("Courier New", 8))
        
        raw_buttons = QHBoxLayout()
        
        self.copy_raw_btn = QPushButton("Копировать")
        self.copy_raw_btn.setIcon(QIcon("assets/icons/copy.png"))
        
        self.hex_view_check = QCheckBox("HEX вид")
        self.hex_view_check.setChecked(False)
        
        raw_buttons.addWidget(self.copy_raw_btn)
        raw_buttons.addWidget(self.hex_view_check)
        raw_buttons.addStretch()
        
        raw_layout.addWidget(self.raw_data_text)
        raw_layout.addLayout(raw_buttons)
        raw_widget.setLayout(raw_layout)
        
        # Вкладка: Команды
        commands_widget = QWidget()
        commands_layout = QVBoxLayout()
        
        self.commands_list = QListWidget()
        self.commands_list.setFont(QFont("Courier New", 9))
        
        command_input_layout = QHBoxLayout()
        
        self.command_edit = QLineEdit()
        self.command_edit.setPlaceholderText("Введите команду (например: ATZ, 0100)")
        self.command_edit.setFont(QFont("Courier New", 10))
        
        self.send_command_btn = QPushButton("Отправить")
        self.send_command_btn.setIcon(QIcon("assets/icons/send.png"))
        
        command_input_layout.addWidget(self.command_edit)
        command_input_layout.addWidget(self.send_command_btn)
        
        commands_layout.addWidget(self.commands_list)
        commands_layout.addLayout(command_input_layout)
        commands_widget.setLayout(commands_layout)
        
        # Добавление вкладок
        self.details_tabs.addTab(log_widget, QIcon("assets/icons/log.png"), "Лог")
        self.details_tabs.addTab(raw_widget, QIcon("assets/icons/raw.png"), "Сырые данные")
        self.details_tabs.addTab(commands_widget, QIcon("assets/icons/command.png"), "Команды")
        
        details_layout.addWidget(self.details_tabs)
        self.details_panel.setLayout(details_layout)
        
    def create_status_panel(self):
        """Создание панели статуса"""
        self.status_panel = QFrame()
        self.status_panel.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(10, 5, 10, 5)
        
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFont(QFont("Segoe UI", 9))
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        
        # Текущее действие
        self.current_action = QLabel("Готов к работе")
        self.current_action.setFont(QFont("Segoe UI", 9))
        self.current_action.setMinimumWidth(300)
        
        # Время начала
        self.start_time_label = QLabel("Начало: --:--:--")
        self.start_time_label.setFont(QFont("Segoe UI", 9))
        
        # Прошло времени
        self.elapsed_time_label = QLabel("Прошло: 00:00:00")
        self.elapsed_time_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        
        # Таймер
        self.timer_label = QLabel("Таймер: 00:00:00")
        self.timer_label.setFont(QFont("Segoe UI", 9))
        
        status_layout.addWidget(self.current_action)
        status_layout.addWidget(self.progress_bar)
        status_layout.addWidget(self.start_time_label)
        status_layout.addWidget(self.elapsed_time_label)
        status_layout.addWidget(self.timer_label)
        
        self.status_panel.setLayout(status_layout)
        
    def setup_connections(self):
        """Настройка соединений"""
        # Кнопки управления
        self.full_diagnostic_btn.clicked.connect(self.start_full_diagnostic)
        self.quick_diagnostic_btn.clicked.connect(self.start_quick_diagnostic)
        self.stop_diagnostic_btn.clicked.connect(self.stop_diagnostic)
        self.save_results_btn.clicked.connect(self.save_results)
        self.scan_vin_btn.clicked.connect(self.scan_vin)
        
        # Кнопки лога
        self.clear_log_btn.clicked.connect(self.clear_log)
        self.save_log_btn.clicked.connect(self.save_log)
        
        # Кнопки графика
        self.start_graph_btn.clicked.connect(self.start_graph_recording)
        self.stop_graph_btn.clicked.connect(self.stop_graph_recording)
        self.clear_graph_btn.clicked.connect(self.clear_graph)
        
        # Кнопки экспорта
        self.export_csv_btn.clicked.connect(lambda: self.export_data('csv'))
        self.export_excel_btn.clicked.connect(lambda: self.export_data('excel'))
        self.export_json_btn.clicked.connect(lambda: self.export_data('json'))
        
        # Команды
        self.send_command_btn.clicked.connect(self.send_custom_command)
        self.command_edit.returnPressed.connect(self.send_custom_command)
        
        # Таймер обновления времени
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.elapsed_timer = QTimer()
        self.elapsed_timer.timeout.connect(self.update_elapsed_time)
        
        # Выбор системы в дереве
        self.systems_tree.itemClicked.connect(self.on_system_selected)
        self.refresh_system_btn.clicked.connect(self.refresh_selected_system)
        self.detail_system_btn.clicked.connect(self.detail_selected_system)
        self.test_system_btn.clicked.connect(self.test_selected_system)
        
    def setup_styles(self):
        """Настройка стилей"""
        # Устанавливаем стиль для всего виджета
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTreeWidget {
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
            QTableWidget {
                border: 1px solid #cccccc;
                border-radius: 3px;
                selection-background-color: #e0e0e0;
            }
            QTextEdit {
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
        """)
        
    @pyqtSlot()
    def start_full_diagnostic(self):
        """Запуск полной диагностики"""
        if not self.diagnostics_engine:
            self.log_message("Ошибка: Диагностический движок не инициализирован", "ERROR")
            return
            
        if self.diagnostic_in_progress:
            self.log_message("Диагностика уже выполняется", "WARNING")
            return
            
        # Получаем выбранные системы
        selected_systems = []
        if self.engine_check.isChecked():
            selected_systems.append('ENGINE')
        if self.abs_check.isChecked():
            selected_systems.append('ABS')
        if self.airbag_check.isChecked():
            selected_systems.append('AIRBAG')
        if self.immo_check.isChecked():
            selected_systems.append('IMMO')
        if self.instrument_check.isChecked():
            selected_systems.append('INSTRUMENT')
        if self.ac_check.isChecked():
            selected_systems.append('AC')
            
        if not selected_systems:
            QMessageBox.warning(self, "Внимание", "Не выбраны системы для диагностики!")
            return
            
        # Сбрасываем предыдущие результаты
        self.reset_results()
        
        # Обновляем интерфейс
        self.diagnostic_in_progress = True
        self.update_controls_state()
        
        # Запускаем таймеры
        self.start_time = datetime.now()
        self.start_time_label.setText(f"Начало: {self.start_time.strftime('%H:%M:%S')}")
        self.timer.start(1000)  # Обновление каждую секунду
        self.elapsed_timer.start(1000)
        
        # Запускаем диагностику в отдельном потоке
        self.diagnostic_started.emit()
        self.log_message(f"Запуск полной диагностики для {self.model_combo.currentText()}", "INFO")
        self.log_message(f"Выбраны системы: {', '.join(selected_systems)}", "INFO")
        
        # В реальном приложении здесь будет запуск диагностики через движок
        # self.diagnostics_engine.perform_full_diagnostic(selected_systems)
        
        # Имитация диагностики
        self.simulate_diagnostic()
        
    def simulate_diagnostic(self):
        """Имитация процесса диагностики (для демонстрации)"""
        # В реальном приложении это будет выполняться в отдельном потоке
        
        systems = [
            ("Двигатель (ECU)", 40),
            ("Антиблокировочная система (ABS)", 20),
            ("Подушки безопасности", 15),
            ("Иммобилайзер", 10),
            ("Приборная панель", 10),
            ("Климат-контроль", 5)
        ]
        
        total_progress = 0
        for system_name, system_time in systems:
            if not self.diagnostic_in_progress:
                break
                
            # Обновляем текущее действие
            self.current_action.setText(f"Диагностика {system_name}...")
            self.log_message(f"Начата диагностика {system_name}", "INFO")
            
            # Имитация работы
            for i in range(system_time):
                if not self.diagnostic_in_progress:
                    break
                    
                progress = total_progress + (i + 1) * (100 // sum(s[1] for s in systems))
                self.progress_bar.setValue(min(progress, 100))
                QApplication.processEvents()
                time.sleep(0.05)
                
            total_progress += system_time * (100 // sum(s[1] for s in systems))
            
            # Обновляем статус системы
            self.update_system_status(system_name, "Завершено", "0", f"{system_time}с")
            self.log_message(f"Диагностика {system_name} завершена", "SUCCESS")
            
        if self.diagnostic_in_progress:
            self.finish_diagnostic()
            
    def finish_diagnostic(self):
        """Завершение диагностики"""
        self.diagnostic_in_progress = False
        self.update_controls_state()
        self.timer.stop()
        self.elapsed_timer.stop()
        
        self.progress_bar.setValue(100)
        self.current_action.setText("Диагностика завершена")
        
        # Обновляем общий статус
        self.overall_status.setText("Статус: Завершена успешно")
        self.overall_status.setStyleSheet("color: #4CAF50;")
        self.overall_icon.setPixmap(QIcon("assets/icons/success.png").pixmap(32, 32))
        
        # Обновляем статистику
        self.errors_count.setText("Ошибок: 2")
        self.warnings_count.setText("Предупреждений: 1")
        self.systems_checked.setText("Проверено систем: 6/6")
        
        # Заполняем таблицу результатов
        self.populate_summary_table()
        
        self.log_message("Диагностика успешно завершена", "SUCCESS")
        self.diagnostic_completed.emit(self.current_results)
        
    def stop_diagnostic(self):
        """Остановка диагностики"""
        if self.diagnostic_in_progress:
            self.diagnostic_in_progress = False
            self.timer.stop()
            self.elapsed_timer.stop()
            
            self.overall_status.setText("Статус: Прервана пользователем")
            self.overall_status.setStyleSheet("color: #FF9800;")
            self.overall_icon.setPixmap(QIcon("assets/icons/warning.png").pixmap(32, 32))
            
            self.current_action.setText("Диагностика прервана")
            self.log_message("Диагностика прервана пользователем", "WARNING")
            self.update_controls_state()
            
    def start_quick_diagnostic(self):
        """Запуск быстрой диагностики"""
        self.log_message("Запуск быстрой диагностики...", "INFO")
        # Реализация быстрой диагностики
        
    def save_results(self):
        """Сохранение результатов диагностики"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить результаты диагностики",
            f"diagnostic_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "JSON files (*.json);;Text files (*.txt);;All files (*.*)"
        )
        
        if filename:
            try:
                results = {
                    'timestamp': datetime.now().isoformat(),
                    'vehicle_model': self.model_combo.currentText(),
                    'vin': self.vin_edit.text(),
                    'diagnostic_results': self.current_results
                }
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                    
                self.log_message(f"Результаты сохранены в {filename}", "SUCCESS")
                
            except Exception as e:
                self.log_message(f"Ошибка при сохранении: {str(e)}", "ERROR")
                
    def scan_vin(self):
        """Сканирование VIN кода"""
        self.log_message("Сканирование VIN кода...", "INFO")
        # В реальном приложении: отправка команды для чтения VIN
        # Пока имитируем
        simulated_vin = "X9L212300N1234567"
        self.vin_edit.setText(simulated_vin)
        self.log_message(f"VIN найден: {simulated_vin}", "SUCCESS")
        
    def log_message(self, message, level="INFO"):
        """Добавление сообщения в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        if level == "ERROR":
            color = "#FF5252"
            prefix = "ERROR"
        elif level == "WARNING":
            color = "#FF9800"
            prefix = "WARN"
        elif level == "SUCCESS":
            color = "#4CAF50"
            prefix = "OK"
        else:
            color = "#2196F3"
            prefix = "INFO"
            
        if not self.pause_log_btn.isChecked():
            self.log_text.append(f'<font color="#999999">[{timestamp}]</font> '
                               f'<font color="{color}"><b>[{prefix}]</b></font> '
                               f'<font color="#ffffff">{message}</font>')
            # Автопрокрутка вниз
            self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )
            
    def clear_log(self):
        """Очистка лога"""
        self.log_text.clear()
        self.log_message("Лог очищен", "INFO")
        
    def save_log(self):
        """Сохранение лога в файл"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить лог",
            f"diagnostic_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            "Log files (*.log);;Text files (*.txt);;All files (*.*)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                self.log_message(f"Лог сохранен в {filename}", "SUCCESS")
            except Exception as e:
                self.log_message(f"Ошибка при сохранении лога: {str(e)}", "ERROR")
                
    def update_timer(self):
        """Обновление таймера"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.timer_label.setText(f"Текущее: {current_time}")
        
    def update_elapsed_time(self):
        """Обновление прошедшего времени"""
        if hasattr(self, 'start_time'):
            elapsed = datetime.now() - self.start_time
            hours, remainder = divmod(elapsed.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.elapsed_time_label.setText(f"Прошло: {hours:02d}:{minutes:02d}:{seconds:02d}")
            
    def update_system_status(self, system_name, status, errors, duration):
        """Обновление статуса системы в дереве"""
        for i in range(self.systems_tree.topLevelItemCount()):
            item = self.systems_tree.topLevelItem(i)
            if system_name in item.text(0):
                item.setText(1, status)
                item.setText(2, errors)
                item.setText(3, duration)
                
                # Обновляем иконку в зависимости от статуса
                if status == "Завершено":
                    if errors == "0":
                        item.setIcon(0, QIcon("assets/icons/success.png"))
                        item.setForeground(1, QBrush(QColor("#4CAF50")))
                    else:
                        item.setIcon(0, QIcon("assets/icons/error.png"))
                        item.setForeground(1, QBrush(QColor("#FF5252")))
                elif status == "Выполняется":
                    item.setIcon(0, QIcon("assets/icons/working.png"))
                    item.setForeground(1, QBrush(QColor("#2196F3")))
                    
                break
                
    def populate_summary_table(self):
        """Заполнение таблицы с основными показателями"""
        # Примерные данные
        data = [
            ["Обороты двигателя", "850", "об/мин", "Норма"],
            ["Температура охлаждающей жидкости", "92", "°C", "Норма"],
            ["Напряжение бортовой сети", "13.8", "В", "Норма"],
            ["Положение дроссельной заслонки", "12.5", "%", "Норма"],
            ["Расход воздуха", "4.2", "г/с", "Норма"],
            ["Температура всасываемого воздуха", "32", "°C", "Норма"],
            ["Абсолютное давление", "101", "кПа", "Норма"],
            ["Угол опережения зажигания", "8.5", "град", "Норма"],
            ["Коррекция топливоподачи", "+1.2", "%", "Норма"],
            ["Напряжение датчика кислорода", "0.45", "В", "Норма"],
            ["Скорость автомобиля", "0", "км/ч", "Норма"],
            ["Уровень топлива", "65", "%", "Норма"],
            ["Пробег", "125430", "км", "Норма"],
            ["Остаточный ресурс масла", "8500", "км", "Норма"],
        ]
        
        self.summary_table.setRowCount(len(data))
        
        for row_idx, row_data in enumerate(data):
            for col_idx, cell_data in enumerate(row_data):
                item = QTableWidgetItem(cell_data)
                item.setTextAlignment(Qt.AlignCenter)
                
                # Цветовое кодирование статуса
                if col_idx == 3:  # Столбец статуса
                    if cell_data == "Норма":
                        item.setForeground(QBrush(QColor("#4CAF50")))
                    elif cell_data == "Предупреждение":
                        item.setForeground(QBrush(QColor("#FF9800")))
                    elif cell_data == "Ошибка":
                        item.setForeground(QBrush(QColor("#FF5252")))
                        
                # Выделение значений жирным
                if col_idx == 1:
                    item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                    
                self.summary_table.setItem(row_idx, col_idx, item)
                
    def update_controls_state(self):
        """Обновление состояния элементов управления"""
        is_connected = self.diagnostics_engine is not None
        is_diagnosing = self.diagnostic_in_progress
        
        self.full_diagnostic_btn.setEnabled(is_connected and not is_diagnosing)
        self.quick_diagnostic_btn.setEnabled(is_connected and not is_diagnosing)
        self.stop_diagnostic_btn.setEnabled(is_diagnosing)
        self.save_results_btn.setEnabled(not is_diagnosing and bool(self.current_results))
        
        self.model_combo.setEnabled(not is_diagnosing)
        self.vin_edit.setEnabled(not is_diagnosing)
        self.scan_vin_btn.setEnabled(not is_diagnosing)
        
        # Блокировка чекбоксов во время диагностики
        for check in [self.engine_check, self.abs_check, self.airbag_check,
                     self.immo_check, self.instrument_check, self.ac_check]:
            check.setEnabled(not is_diagnosing)
            
    def reset_results(self):
        """Сброс результатов"""
        self.current_results = {}
        self.progress_bar.setValue(0)
        
        # Сброс статуса
        self.overall_status.setText("Статус: Выполняется")
        self.overall_status.setStyleSheet("color: #2196F3;")
        self.overall_icon.setPixmap(QIcon("assets/icons/working.png").pixmap(32, 32))
        
        self.errors_count.setText("Ошибок: 0")
        self.warnings_count.setText("Предупреждений: 0")
        self.systems_checked.setText("Проверено систем: 0/6")
        
        # Сброс таблицы
        self.summary_table.setRowCount(0)
        
        # Сброс дерева систем
        for i in range(self.systems_tree.topLevelItemCount()):
            item = self.systems_tree.topLevelItem(i)
            item.setText(1, "Ожидание")
            item.setText(2, "0")
            item.setText(3, "--:--")
            item.setIcon(0, QIcon("assets/icons/system.png"))
            item.setForeground(1, QBrush(QColor("#666666")))
            
    def on_system_selected(self, item, column):
        """Обработка выбора системы"""
        system_name = item.text(0)
        self.refresh_system_btn.setEnabled(True)
        self.detail_system_btn.setEnabled(True)
        self.test_system_btn.setEnabled(True)
        
    def refresh_selected_system(self):
        """Обновление выбранной системы"""
        item = self.systems_tree.currentItem()
        if item:
            system_name = item.text(0)
            self.log_message(f"Обновление системы: {system_name}", "INFO")
            
    def detail_selected_system(self):
        """Детальная диагностика выбранной системы"""
        item = self.systems_tree.currentItem()
        if item:
            system_name = item.text(0)
            self.log_message(f"Детальная диагностика системы: {system_name}", "INFO")
            
    def test_selected_system(self):
        """Тестирование выбранной системы"""
        item = self.systems_tree.currentItem()
        if item:
            system_name = item.text(0)
            self.log_message(f"Тестирование системы: {system_name}", "INFO")
            
    def start_graph_recording(self):
        """Начало записи графика"""
        self.start_graph_btn.setEnabled(False)
        self.stop_graph_btn.setEnabled(True)
        self.log_message(f"Начата запись графика: {self.graph_param_combo.currentText()}", "INFO")
        
    def stop_graph_recording(self):
        """Остановка записи графика"""
        self.start_graph_btn.setEnabled(True)
        self.stop_graph_btn.setEnabled(False)
        self.log_message("Запись графика остановлена", "INFO")
        
    def clear_graph(self):
        """Очистка графика"""
        self.graph_area.clear()
        self.log_message("График очищен", "INFO")
        
    def export_data(self, format_type):
        """Экспорт данных"""
        formats = {
            'csv': 'CSV files (*.csv)',
            'excel': 'Excel files (*.xlsx)',
            'json': 'JSON files (*.json)'
        }
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            f"Экспорт данных в {format_type.upper()}",
            f"diagnostic_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            formats.get(format_type, "All files (*.*)")
        )
        
        if filename:
            self.log_message(f"Экспорт данных в {format_type.upper()} начат", "INFO")
            # Здесь будет реализация экспорта
            time.sleep(1)  # Имитация процесса
            self.log_message(f"Данные экспортированы в {filename}", "SUCCESS")
            
    def send_custom_command(self):
        """Отправка пользовательской команды"""
        command = self.command_edit.text().strip()
        if not command:
            return
            
        # Добавляем команду в список
        item = QListWidgetItem(f"> {command}")
        item.setForeground(QBrush(QColor("#2196F3")))
        self.commands_list.addItem(item)
        
        # В реальном приложении: отправка команды через ELM327
        # response = self.diagnostics_engine.send_command(command)
        
        # Имитация ответа
        simulated_responses = [
            "OK",
            "41 00 BE 3F A8 13",
            "NO DATA",
            "SEARCHING...",
            "UNABLE TO CONNECT"
        ]
        
        import random
        response = random.choice(simulated_responses)
        
        # Добавляем ответ
        response_item = QListWidgetItem(f"< {response}")
        response_item.setForeground(QBrush(QColor("#4CAF50")))
        self.commands_list.addItem(response_item)
        
        # Прокрутка к последнему элементу
        self.commands_list.scrollToBottom()
        
        # Очистка поля ввода
        self.command_edit.clear()
        
        # Добавление в лог
        self.log_message(f"Команда отправлена: {command} -> {response}", "INFO")
        
        # Добавление в сырые данные
        self.raw_data_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] > {command}")
        self.raw_data_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] < {response}")
        self.raw_data_text.append("")
        
    def set_diagnostics_engine(self, engine):
        """Установка движка диагностики"""
        self.diagnostics_engine = engine
        self.update_controls_state()
        
    def resizeEvent(self, event):
        """Обработка изменения размера"""
        super().resizeEvent(event)
        # Можно добавить адаптацию интерфейса при изменении размера
        
    def showEvent(self, event):
        """Обработка показа виджета"""
        super().showEvent(event)
        # Инициализация при первом показе
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.log_message("Панель диагностики готова к работе", "INFO")