"""
Панель для работы с ошибками (DTC) - полная версия
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QGroupBox, QTreeWidget, QTreeWidgetItem,
                             QTextEdit, QComboBox, QCheckBox, QSpinBox,
                             QSplitter, QMessageBox, QProgressBar,
                             QTabWidget, QFrame, QToolBar, QAction, 
                             QFileDialog, QMenu, QApplication, QStyle)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QDateTime
from PyQt5.QtGui import QFont, QIcon, QColor, QBrush
import json
import csv
import os

class ErrorPanel(QWidget):
    """Панель для работы с диагностическими кодами неисправностей"""
    
    # Сигналы
    clear_errors_requested = pyqtSignal()
    read_errors_requested = pyqtSignal()
    error_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.error_database = {}
        self.loaded_errors = {}
        self.current_ecu = None
        self.init_ui()
        self.load_error_database()
        self.setup_connections()
        
    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Верхняя панель инструментов
        self.create_toolbar()
        main_layout.addWidget(self.toolbar)
        
        # Разделитель для основной области
        splitter = QSplitter(Qt.Vertical)
        
        # Верхняя панель - таблица ошибок
        self.create_error_table_panel()
        splitter.addWidget(self.error_table_panel)
        
        # Нижняя панель - детали ошибки и действия
        self.create_error_details_panel()
        splitter.addWidget(self.error_details_panel)
        
        splitter.setSizes([400, 200])
        main_layout.addWidget(splitter)
        
        # Статус бар внизу
        self.create_status_bar()
        main_layout.addWidget(self.status_frame)
        
    def create_toolbar(self):
        """Создание панели инструментов"""
        self.toolbar = QToolBar("Панель ошибок")
        self.toolbar.setIconSize(QSize(24, 24))
        
        # Кнопка чтения ошибок
        self.read_errors_action = QAction(
            QIcon.fromTheme("view-refresh", QIcon("assets/icons/refresh.png")),
            "Считать ошибки",
            self
        )
        self.read_errors_action.setShortcut("F5")
        self.read_errors_action.setStatusTip("Считать ошибки со всех модулей")
        self.toolbar.addAction(self.read_errors_action)
        
        # Кнопка очистки ошибок
        self.clear_errors_action = QAction(
            QIcon.fromTheme("edit-clear", QIcon("assets/icons/clear.png")),
            "Очистить ошибки",
            self
        )
        self.clear_errors_action.setStatusTip("Очистить все ошибки во всех модулях")
        self.toolbar.addAction(self.clear_errors_action)
        
        self.toolbar.addSeparator()
        
        # Кнопка сохранения ошибок
        self.save_errors_action = QAction(
            QIcon.fromTheme("document-save", QIcon("assets/icons/save.png")),
            "Сохранить",
            self
        )
        self.save_errors_action.setShortcut("Ctrl+S")
        self.save_errors_action.setStatusTip("Сохранить отчет об ошибках")
        self.toolbar.addAction(self.save_errors_action)
        
        # Кнопка загрузки ошибок
        self.load_errors_action = QAction(
            QIcon.fromTheme("document-open", QIcon("assets/icons/open.png")),
            "Загрузить",
            self
        )
        self.load_errors_action.setStatusTip("Загрузить ранее сохраненные ошибки")
        self.toolbar.addAction(self.load_errors_action)
        
        self.toolbar.addSeparator()
        
        # Кнопка печати
        self.print_action = QAction(
            QIcon.fromTheme("document-print", QIcon("assets/icons/print.png")),
            "Печать",
            self
        )
        self.print_action.setShortcut("Ctrl+P")
        self.print_action.setStatusTip("Распечатать отчет об ошибках")
        self.toolbar.addAction(self.print_action)
        
        # Выбор ECU
        self.toolbar.addWidget(QLabel(" Модуль: "))
        self.ecu_combo = QComboBox()
        self.ecu_combo.addItem("Все модули", "ALL")
        self.ecu_combo.addItem("Двигатель (ECU)", "ENGINE")
        self.ecu_combo.addItem("ABS", "ABS")
        self.ecu_combo.addItem("Подушки безопасности", "AIRBAG")
        self.ecu_combo.addItem("Иммобилайзер", "IMMO")
        self.ecu_combo.addItem("Приборная панель", "INSTRUMENT")
        self.ecu_combo.addItem("Климат-контроль", "AC")
        self.ecu_combo.setMaximumWidth(150)
        self.toolbar.addWidget(self.ecu_combo)
        
    def create_error_table_panel(self):
        """Создание панели с таблицей ошибок"""
        self.error_table_panel = QWidget()
        layout = QVBoxLayout(self.error_table_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Заголовок
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.StyledPanel)
        header_layout = QHBoxLayout(header_frame)
        
        self.error_count_label = QLabel("Ошибок не обнаружено")
        self.error_count_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        
        self.last_update_label = QLabel("")
        self.last_update_label.setAlignment(Qt.AlignRight)
        
        header_layout.addWidget(self.error_count_label)
        header_layout.addWidget(self.last_update_label)
        
        layout.addWidget(header_frame)
        
        # Таблица ошибок
        self.error_table = QTableWidget()
        self.error_table.setColumnCount(8)
        self.error_table.setHorizontalHeaderLabels([
            "Модуль", "Код", "Статус", "Описание", 
            "Приоритет", "Первое появление", "Последнее появление", "Количество"
        ])
        
        # Настройка таблицы
        self.error_table.setAlternatingRowColors(True)
        self.error_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.error_table.setSelectionMode(QTableWidget.SingleSelection)
        self.error_table.setSortingEnabled(True)
        self.error_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Настройка заголовков
        header = self.error_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Модуль
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Код
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Статус
        header.setSectionResizeMode(3, QHeaderView.Stretch)           # Описание
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Приоритет
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Первое появление
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Последнее появление
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Количество
        
        # Контекстное меню для таблицы
        self.error_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.error_table.customContextMenuRequested.connect(self.show_table_context_menu)
        
        layout.addWidget(self.error_table)
        
    def create_error_details_panel(self):
        """Создание панели деталей ошибки"""
        self.error_details_panel = QTabWidget()
        
        # Вкладка 1: Детальная информация об ошибке
        self.details_tab = QWidget()
        details_layout = QVBoxLayout(self.details_tab)
        
        # Группа основной информации
        info_group = QGroupBox("Информация об ошибке")
        info_layout = QVBoxLayout()
        
        self.error_code_label = QLabel("Код ошибки: -")
        self.error_code_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        
        self.error_module_label = QLabel("Модуль: -")
        self.error_description_label = QLabel("Описание: -")
        self.error_meaning_label = QLabel("Значение: -")
        self.error_conditions_label = QLabel("Условия возникновения: -")
        
        info_layout.addWidget(self.error_code_label)
        info_layout.addWidget(self.error_module_label)
        info_layout.addWidget(self.error_description_label)
        info_layout.addWidget(self.error_meaning_label)
        info_layout.addWidget(self.error_conditions_label)
        
        info_group.setLayout(info_layout)
        details_layout.addWidget(info_group)
        
        # Группа рекомендуемых действий
        action_group = QGroupBox("Рекомендуемые действия")
        action_layout = QVBoxLayout()
        
        self.error_causes_text = QTextEdit()
        self.error_causes_text.setReadOnly(True)
        self.error_causes_text.setMaximumHeight(80)
        
        self.error_solutions_text = QTextEdit()
        self.error_solutions_text.setReadOnly(True)
        self.error_solutions_text.setMaximumHeight(80)
        
        action_layout.addWidget(QLabel("Возможные причины:"))
        action_layout.addWidget(self.error_causes_text)
        action_layout.addWidget(QLabel("Рекомендуемые решения:"))
        action_layout.addWidget(self.error_solutions_text)
        
        action_group.setLayout(action_layout)
        details_layout.addWidget(action_group)
        
        # Группа технической информации
        tech_group = QGroupBox("Техническая информация")
        tech_layout = QVBoxLayout()
        
        self.tech_info_table = QTableWidget()
        self.tech_info_table.setColumnCount(2)
        self.tech_info_table.setHorizontalHeaderLabels(["Параметр", "Значение"])
        self.tech_info_table.horizontalHeader().setStretchLastSection(True)
        self.tech_info_table.setMaximumHeight(120)
        
        tech_layout.addWidget(self.tech_info_table)
        tech_group.setLayout(tech_layout)
        details_layout.addWidget(tech_group)
        
        self.error_details_panel.addTab(self.details_tab, QIcon("assets/icons/info.png"), "Информация")
        
        # Вкладка 2: График возникновения ошибки
        self.history_tab = QWidget()
        history_layout = QVBoxLayout(self.history_tab)
        
        history_label = QLabel("История возникновения ошибки")
        history_label.setAlignment(Qt.AlignCenter)
        history_label.setStyleSheet("font-weight: bold; padding: 10px;")
        
        # Здесь будет график (пока заглушка)
        self.history_placeholder = QLabel("График истории возникновения ошибки\n(требуется интеграция с matplotlib)")
        self.history_placeholder.setAlignment(Qt.AlignCenter)
        self.history_placeholder.setStyleSheet("color: gray; font-style: italic;")
        
        history_layout.addWidget(history_label)
        history_layout.addWidget(self.history_placeholder)
        
        self.error_details_panel.addTab(self.history_tab, QIcon("assets/icons/chart.png"), "История")
        
        # Вкладка 3: Действия
        self.actions_tab = QWidget()
        actions_layout = QVBoxLayout(self.actions_tab)
        
        # Группа немедленных действий
        immediate_group = QGroupBox("Немедленные действия")
        immediate_layout = QVBoxLayout()
        
        self.test_sensor_btn = QPushButton("Протестировать датчик")
        self.test_sensor_btn.setIcon(QIcon("assets/icons/sensor.png"))
        self.test_sensor_btn.setEnabled(False)
        
        self.check_wiring_btn = QPushButton("Проверить проводку")
        self.check_wiring_btn.setIcon(QIcon("assets/icons/wiring.png"))
        self.check_wiring_btn.setEnabled(False)
        
        self.reset_adaptation_btn = QPushButton("Сбросить адаптацию")
        self.reset_adaptation_btn.setIcon(QIcon("assets/icons/reset.png"))
        self.reset_adaptation_btn.setEnabled(False)
        
        immediate_layout.addWidget(self.test_sensor_btn)
        immediate_layout.addWidget(self.check_wiring_btn)
        immediate_layout.addWidget(self.reset_adaptation_btn)
        immediate_group.setLayout(immediate_layout)
        
        # Группа настроек
        settings_group = QGroupBox("Настройки мониторинга")
        settings_layout = QVBoxLayout()
        
        self.monitor_checkbox = QCheckBox("Мониторить эту ошибку")
        self.monitor_checkbox.setEnabled(False)
        
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Пороговое значение:"))
        self.threshold_spinbox = QSpinBox()
        self.threshold_spinbox.setRange(0, 1000)
        self.threshold_spinbox.setSuffix(" раз")
        self.threshold_spinbox.setEnabled(False)
        threshold_layout.addWidget(self.threshold_spinbox)
        threshold_layout.addStretch()
        
        settings_layout.addWidget(self.monitor_checkbox)
        settings_layout.addLayout(threshold_layout)
        settings_group.setLayout(settings_layout)
        
        actions_layout.addWidget(immediate_group)
        actions_layout.addWidget(settings_group)
        actions_layout.addStretch()
        
        self.error_details_panel.addTab(self.actions_tab, QIcon("assets/icons/tools.png"), "Действия")
        
    def create_status_bar(self):
        """Создание статус бара"""
        self.status_frame = QFrame()
        self.status_frame.setFrameShape(QFrame.StyledPanel)
        status_layout = QHBoxLayout(self.status_frame)
        
        self.status_label = QLabel("Готов к чтению ошибок")
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        
        self.ecu_status_label = QLabel("ECU: Не подключен")
        self.ecu_status_label.setAlignment(Qt.AlignRight)
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        status_layout.addWidget(self.ecu_status_label)
        
    def setup_connections(self):
        """Настройка соединений между элементами UI"""
        # Панель инструментов
        self.read_errors_action.triggered.connect(self.on_read_errors)
        self.clear_errors_action.triggered.connect(self.on_clear_errors)
        self.save_errors_action.triggered.connect(self.on_save_errors)
        self.load_errors_action.triggered.connect(self.on_load_errors)
        self.print_action.triggered.connect(self.on_print_report)
        self.ecu_combo.currentIndexChanged.connect(self.on_ecu_changed)
        
        # Таблица ошибок
        self.error_table.itemSelectionChanged.connect(self.on_error_selected)
        self.error_table.itemDoubleClicked.connect(self.on_error_double_clicked)
        
        # Вкладка действий
        self.test_sensor_btn.clicked.connect(self.on_test_sensor)
        self.check_wiring_btn.clicked.connect(self.on_check_wiring)
        self.reset_adaptation_btn.clicked.connect(self.on_reset_adaptation)
        self.monitor_checkbox.stateChanged.connect(self.on_monitor_changed)
        self.threshold_spinbox.valueChanged.connect(self.on_threshold_changed)
        
    def load_error_database(self):
        """Загрузка базы данных ошибок"""
        try:
            # Загрузка из файла или ресурсов
            db_path = "config/error_codes.json"
            if os.path.exists(db_path):
                with open(db_path, 'r', encoding='utf-8') as f:
                    self.error_database = json.load(f)
            else:
                # Загрузка встроенной базы данных
                self.load_default_error_database()
                
            self.status_label.setText(f"База данных ошибок загружена: {len(self.error_database)} записей")
            
        except Exception as e:
            self.status_label.setText(f"Ошибка загрузки базы данных: {str(e)}")
            self.load_default_error_database()
            
    def load_default_error_database(self):
        """Загрузка стандартной базы данных ошибок для Chevrolet Niva"""
        self.error_database = {
            "P0100": {
                "description": "Неисправность цепи датчика массового расхода воздуха",
                "meaning": "Слишком высокое или низкое напряжение в цепи ДМРВ",
                "causes": [
                    "Обрыв или короткое замыкание в проводке ДМРВ",
                    "Неисправность датчика ДМРВ",
                    "Проблемы с разъемом ДМРВ",
                    "Неисправность ЭБУ"
                ],
                "solutions": [
                    "Проверить проводку и разъем ДМРВ",
                    "Проверить напряжение питания датчика (5В)",
                    "Проверить сигнал ДМРВ на холостом ходу (1.0-1.2В)",
                    "Заменить датчик ДМРВ при необходимости"
                ],
                "severity": "HIGH",
                "module": "ENGINE",
                "conditions": "Зажигание включено, двигатель работает"
            },
            "P0110": {
                "description": "Неисправность цепи датчика температуры воздуха на впуске",
                "meaning": "Неверные показания датчика температуры впускного воздуха",
                "causes": [
                    "Обрыв или короткое замыкание в проводке датчика",
                    "Неисправность датчика температуры воздуха",
                    "Проблемы с разъемом датчика"
                ],
                "solutions": [
                    "Проверить сопротивление датчика при разных температурах",
                    "Проверить напряжение в цепи датчика",
                    "Заменить датчик при необходимости"
                ],
                "severity": "MEDIUM",
                "module": "ENGINE",
                "conditions": "Двигатель работает"
            },
            "P0300": {
                "description": "Пропуски зажигания в цилиндрах",
                "meaning": "Обнаружены множественные пропуски зажигания",
                "causes": [
                    "Неисправность свечей зажигания",
                    "Проблемы с катушками зажигания",
                    "Неисправность форсунок",
                    "Низкая компрессия",
                    "Проблемы с топливной системой"
                ],
                "solutions": [
                    "Проверить свечи зажигания",
                    "Проверить катушки зажигания",
                    "Проверить компрессию в цилиндрах",
                    "Проверить работу форсунок"
                ],
                "severity": "HIGH",
                "module": "ENGINE",
                "conditions": "Двигатель работает под нагрузкой"
            },
            "C0128": {
                "description": "Неисправность модуля ABS",
                "meaning": "Обнаружена неисправность в модуле АБС",
                "causes": [
                    "Неисправность датчика ABS",
                    "Проблемы с проводкой к датчикам ABS",
                    "Неисправность модуля управления ABS"
                ],
                "solutions": [
                    "Проверить датчики ABS на всех колесах",
                    "Проверить проводку датчиков",
                    "Проверить модуль управления ABS"
                ],
                "severity": "HIGH",
                "module": "ABS",
                "conditions": "Двигатель работает, скорость > 5 км/ч"
            }
        }
        
    def on_read_errors(self):
        """Обработка чтения ошибок"""
        self.status_label.setText("Чтение ошибок...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Эмуляция процесса чтения
        QTimer.singleShot(100, lambda: self.progress_bar.setValue(25))
        QTimer.singleShot(300, lambda: self.progress_bar.setValue(50))
        QTimer.singleShot(500, lambda: self.progress_bar.setValue(75))
        QTimer.singleShot(700, self.process_loaded_errors)
        
        self.read_errors_requested.emit()
        
    def process_loaded_errors(self):
        """Обработка загруженных ошибок"""
        # Пример загруженных ошибок (для демонстрации)
        self.loaded_errors = {
            "ENGINE": [
                {
                    "code": "P0100",
                    "status": "ACTIVE",
                    "first_occurrence": "2024-01-15 14:30:22",
                    "last_occurrence": "2024-01-20 09:15:45",
                    "count": 5,
                    "freeze_frame": {
                        "rpm": 2450,
                        "speed": 80,
                        "coolant_temp": 92,
                        "load": 65
                    }
                },
                {
                    "code": "P0110",
                    "status": "PENDING",
                    "first_occurrence": "2024-01-18 16:45:12",
                    "last_occurrence": "2024-01-20 09:15:45",
                    "count": 2,
                    "freeze_frame": {
                        "rpm": 1200,
                        "speed": 0,
                        "coolant_temp": 85,
                        "load": 25
                    }
                }
            ],
            "ABS": [
                {
                    "code": "C0128",
                    "status": "ACTIVE",
                    "first_occurrence": "2024-01-10 08:20:33",
                    "last_occurrence": "2024-01-20 09:15:45",
                    "count": 12,
                    "freeze_frame": {
                        "speed": 60,
                        "brake_pressure": 0,
                        "wheel_speed_fl": 60,
                        "wheel_speed_fr": 59
                    }
                }
            ]
        }
        
        self.update_error_table()
        self.progress_bar.setValue(100)
        QTimer.singleShot(1000, lambda: self.progress_bar.setVisible(False))
        self.status_label.setText(f"Ошибки загружены: {self.count_total_errors()} обнаружено")
        self.last_update_label.setText(f"Обновлено: {QDateTime.currentDateTime().toString('dd.MM.yyyy HH:mm:ss')}")
        
    def update_error_table(self):
        """Обновление таблицы ошибок"""
        self.error_table.setRowCount(0)
        
        total_errors = 0
        for module, errors in self.loaded_errors.items():
            for error in errors:
                total_errors += 1
                row = self.error_table.rowCount()
                self.error_table.insertRow(row)
                
                # Цвет строки в зависимости от статуса
                color = self.get_error_color(error["status"])
                
                # Модуль
                module_item = QTableWidgetItem(self.get_module_name(module))
                module_item.setBackground(color)
                self.error_table.setItem(row, 0, module_item)
                
                # Код ошибки
                code_item = QTableWidgetItem(error["code"])
                code_item.setBackground(color)
                code_item.setForeground(QBrush(Qt.blue))
                self.error_table.setItem(row, 1, code_item)
                
                # Статус
                status_item = QTableWidgetItem(self.get_status_text(error["status"]))
                status_item.setBackground(color)
                self.error_table.setItem(row, 2, status_item)
                
                # Описание
                description = self.error_database.get(error["code"], {}).get("description", "Неизвестная ошибка")
                desc_item = QTableWidgetItem(description)
                desc_item.setBackground(color)
                self.error_table.setItem(row, 3, desc_item)
                
                # Приоритет
                severity = self.error_database.get(error["code"], {}).get("severity", "UNKNOWN")
                severity_item = QTableWidgetItem(self.get_severity_text(severity))
                severity_item.setBackground(color)
                self.error_table.setItem(row, 4, severity_item)
                
                # Первое появление
                first_item = QTableWidgetItem(error["first_occurrence"])
                first_item.setBackground(color)
                self.error_table.setItem(row, 5, first_item)
                
                # Последнее появление
                last_item = QTableWidgetItem(error["last_occurrence"])
                last_item.setBackground(color)
                self.error_table.setItem(row, 6, last_item)
                
                # Количество
                count_item = QTableWidgetItem(str(error["count"]))
                count_item.setBackground(color)
                count_item.setTextAlignment(Qt.AlignCenter)
                self.error_table.setItem(row, 7, count_item)
        
        # Обновление заголовка
        if total_errors == 0:
            self.error_count_label.setText("Ошибок не обнаружено")
            self.error_count_label.setStyleSheet("font-weight: bold; color: green; font-size: 12pt;")
        else:
            self.error_count_label.setText(f"Обнаружено ошибок: {total_errors}")
            self.error_count_label.setStyleSheet("font-weight: bold; color: red; font-size: 12pt;")
            
    def get_error_color(self, status):
        """Получение цвета для строки в зависимости от статуса ошибки"""
        if status == "ACTIVE":
            return QColor(255, 200, 200)  # Светло-красный
        elif status == "PENDING":
            return QColor(255, 255, 200)  # Светло-желтый
        elif status == "PERMANENT":
            return QColor(200, 200, 255)  # Светло-синий
        else:
            return QColor(240, 240, 240)  # Светло-серый
            
    def get_module_name(self, module_code):
        """Получение читаемого имени модуля"""
        module_names = {
            "ENGINE": "Двигатель (ECU)",
            "ABS": "ABS",
            "AIRBAG": "Подушки безопасности",
            "IMMO": "Иммобилайзер",
            "INSTRUMENT": "Приборная панель",
            "AC": "Климат-контроль"
        }
        return module_names.get(module_code, module_code)
        
    def get_status_text(self, status):
        """Получение читаемого текста статуса"""
        status_texts = {
            "ACTIVE": "Активная",
            "PENDING": "Ожидающая",
            "PERMANENT": "Постоянная",
            "STORED": "Сохраненная"
        }
        return status_texts.get(status, status)
        
    def get_severity_text(self, severity):
        """Получение читаемого текста приоритета"""
        severity_texts = {
            "HIGH": "Высокий",
            "MEDIUM": "Средний",
            "LOW": "Низкий",
            "INFO": "Информация"
        }
        return severity_texts.get(severity, "Неизвестно")
        
    def count_total_errors(self):
        """Подсчет общего количества ошибок"""
        total = 0
        for errors in self.loaded_errors.values():
            total += len(errors)
        return total
        
    def on_error_selected(self):
        """Обработка выбора ошибки в таблице"""
        selected_items = self.error_table.selectedItems()
        if not selected_items:
            return
            
        row = selected_items[0].row()
        error_code = self.error_table.item(row, 1).text()
        module_code = ""
        
        # Определяем модуль по строке таблицы
        for module, errors in self.loaded_errors.items():
            for error in errors:
                if error["code"] == error_code:
                    module_code = module
                    break
        
        self.display_error_details(error_code, module_code, row)
        self.error_selected.emit(error_code)
        
    def display_error_details(self, error_code, module_code, row):
        """Отображение деталей выбранной ошибки"""
        error_data = self.error_database.get(error_code, {})
        loaded_error = None
        
        # Находим загруженную ошибку
        for module, errors in self.loaded_errors.items():
            for error in errors:
                if error["code"] == error_code:
                    loaded_error = error
                    module_code = module
                    break
        
        # Обновление основной информации
        self.error_code_label.setText(f"Код ошибки: {error_code}")
        self.error_module_label.setText(f"Модуль: {self.get_module_name(module_code)}")
        self.error_description_label.setText(f"Описание: {error_data.get('description', 'Неизвестная ошибка')}")
        self.error_meaning_label.setText(f"Значение: {error_data.get('meaning', 'Нет информации')}")
        self.error_conditions_label.setText(f"Условия возникновения: {error_data.get('conditions', 'Нет информации')}")
        
        # Обновление причин и решений
        causes = error_data.get('causes', ['Нет информации'])
        solutions = error_data.get('solutions', ['Нет информации'])
        
        self.error_causes_text.setText('\n'.join([f"• {cause}" for cause in causes]))
        self.error_solutions_text.setText('\n'.join([f"• {solution}" for solution in solutions]))
        
        # Обновление технической информации
        self.tech_info_table.setRowCount(0)
        
        if loaded_error:
            # Добавляем техническую информацию из загруженной ошибки
            tech_info = [
                ("Статус", self.get_status_text(loaded_error["status"])),
                ("Количество появлений", str(loaded_error["count"])),
                ("Первое появление", loaded_error["first_occurrence"]),
                ("Последнее появление", loaded_error["last_occurrence"])
            ]
            
            # Добавляем данные из freeze frame
            if "freeze_frame" in loaded_error:
                for key, value in loaded_error["freeze_frame"].items():
                    tech_info.append((f"Freeze Frame: {key}", str(value)))
            
            self.tech_info_table.setRowCount(len(tech_info))
            for i, (param, value) in enumerate(tech_info):
                param_item = QTableWidgetItem(param)
                value_item = QTableWidgetItem(value)
                self.tech_info_table.setItem(i, 0, param_item)
                self.tech_info_table.setItem(i, 1, value_item)
        
        # Активация кнопок действий
        self.test_sensor_btn.setEnabled(True)
        self.check_wiring_btn.setEnabled(True)
        self.reset_adaptation_btn.setEnabled(True)
        self.monitor_checkbox.setEnabled(True)
        self.threshold_spinbox.setEnabled(True)
        
    def on_error_double_clicked(self, item):
        """Обработка двойного клика по ошибке"""
        # Открытие дополнительной информации
        error_code = self.error_table.item(item.row(), 1).text()
        self.show_error_details_dialog(error_code)
        
    def show_error_details_dialog(self, error_code):
        """Показать диалог с детальной информацией об ошибке"""
        dialog = QMessageBox(self)
        dialog.setWindowTitle(f"Детальная информация: {error_code}")
        dialog.setIcon(QMessageBox.Information)
        
        error_data = self.error_database.get(error_code, {})
        message = f"""
        <b>Код ошибки:</b> {error_code}<br><br>
        <b>Описание:</b> {error_data.get('description', 'Неизвестная ошибка')}<br><br>
        <b>Значение:</b> {error_data.get('meaning', 'Нет информации')}<br><br>
        <b>Возможные причины:</b><br>
        {chr(10).join([f'• {cause}' for cause in error_data.get('causes', ['Нет информации'])])}<br><br>
        <b>Рекомендуемые решения:</b><br>
        {chr(10).join([f'• {solution}' for solution in error_data.get('solutions', ['Нет информации'])])}
        """
        
        dialog.setTextFormat(Qt.RichText)
        dialog.setText(message)
        dialog.setStandardButtons(QMessageBox.Ok)
        dialog.exec_()
        
    def on_clear_errors(self):
        """Обработка очистки ошибок"""
        reply = QMessageBox.question(
            self,
            "Очистка ошибок",
            "Вы уверены, что хотите очистить все ошибки?\nЭто действие удалит все сохраненные коды неисправностей.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.status_label.setText("Очистка ошибок...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # Эмуляция процесса очистки
            QTimer.singleShot(100, lambda: self.progress_bar.setValue(25))
            QTimer.singleShot(300, lambda: self.progress_bar.setValue(50))
            QTimer.singleShot(500, lambda: self.progress_bar.setValue(75))
            QTimer.singleShot(700, self.complete_clear_errors)
            
            self.clear_errors_requested.emit()
            
    def complete_clear_errors(self):
        """Завершение очистки ошибок"""
        self.loaded_errors = {}
        self.update_error_table()
        self.progress_bar.setValue(100)
        
        QTimer.singleShot(1000, lambda: self.progress_bar.setVisible(False))
        self.status_label.setText("Ошибки очищены успешно")
        
        # Сброс детальной панели
        self.reset_error_details()
        
    def reset_error_details(self):
        """Сброс детальной панели ошибок"""
        self.error_code_label.setText("Код ошибки: -")
        self.error_module_label.setText("Модуль: -")
        self.error_description_label.setText("Описание: -")
        self.error_meaning_label.setText("Значение: -")
        self.error_conditions_label.setText("Условия возникновения: -")
        self.error_causes_text.clear()
        self.error_solutions_text.clear()
        self.tech_info_table.setRowCount(0)
        
        # Деактивация кнопок действий
        self.test_sensor_btn.setEnabled(False)
        self.check_wiring_btn.setEnabled(False)
        self.reset_adaptation_btn.setEnabled(False)
        self.monitor_checkbox.setEnabled(False)
        self.threshold_spinbox.setEnabled(False)
        
    def on_save_errors(self):
        """Сохранение ошибок в файл"""
        if not self.loaded_errors:
            QMessageBox.warning(self, "Сохранение", "Нет ошибок для сохранения")
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить отчет об ошибках",
            f"niva_errors_{QDateTime.currentDateTime().toString('yyyy-MM-dd_HH-mm-ss')}",
            "JSON файлы (*.json);;CSV файлы (*.csv);;Текстовые файлы (*.txt)"
        )
        
        if filename:
            try:
                if filename.endswith('.json'):
                    self.save_errors_json(filename)
                elif filename.endswith('.csv'):
                    self.save_errors_csv(filename)
                else:
                    self.save_errors_txt(filename)
                    
                self.status_label.setText(f"Ошибки сохранены в {filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл: {str(e)}")
                
    def save_errors_json(self, filename):
        """Сохранение ошибок в JSON формате"""
        report = {
            "timestamp": QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss'),
            "vehicle": "Chevrolet Niva",
            "total_errors": self.count_total_errors(),
            "errors": self.loaded_errors
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
    def save_errors_csv(self, filename):
        """Сохранение ошибок в CSV формате"""
        with open(filename, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(['Модуль', 'Код ошибки', 'Статус', 'Описание', 'Приоритет', 
                           'Первое появление', 'Последнее появление', 'Количество'])
            
            for module, errors in self.loaded_errors.items():
                for error in errors:
                    error_data = self.error_database.get(error["code"], {})
                    writer.writerow([
                        self.get_module_name(module),
                        error["code"],
                        self.get_status_text(error["status"]),
                        error_data.get('description', 'Неизвестная ошибка'),
                        self.get_severity_text(error_data.get('severity', 'UNKNOWN')),
                        error["first_occurrence"],
                        error["last_occurrence"],
                        error["count"]
                    ])
                    
    def save_errors_txt(self, filename):
        """Сохранение ошибок в текстовом формате"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("ОТЧЕТ О ДИАГНОСТИЧЕСКИХ ОШИБКАХ\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Автомобиль: Chevrolet Niva\n")
            f.write(f"Дата и время: {QDateTime.currentDateTime().toString('dd.MM.yyyy HH:mm:ss')}\n")
            f.write(f"Всего ошибок: {self.count_total_errors()}\n\n")
            
            for module, errors in self.loaded_errors.items():
                if errors:
                    f.write(f"\n{'-' * 60}\n")
                    f.write(f"Модуль: {self.get_module_name(module)}\n")
                    f.write(f"{'-' * 60}\n\n")
                    
                    for error in errors:
                        error_data = self.error_database.get(error["code"], {})
                        f.write(f"Код: {error['code']}\n")
                        f.write(f"Статус: {self.get_status_text(error['status'])}\n")
                        f.write(f"Описание: {error_data.get('description', 'Неизвестная ошибка')}\n")
                        f.write(f"Приоритет: {self.get_severity_text(error_data.get('severity', 'UNKNOWN'))}\n")
                        f.write(f"Первое появление: {error['first_occurrence']}\n")
                        f.write(f"Последнее появление: {error['last_occurrence']}\n")
                        f.write(f"Количество: {error['count']}\n\n")
                        
    def on_load_errors(self):
        """Загрузка ошибок из файла"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Загрузить отчет об ошибках",
            "",
            "Все поддерживаемые файлы (*.json *.csv *.txt);;JSON файлы (*.json);;CSV файлы (*.csv);;Текстовые файлы (*.txt)"
        )
        
        if filename:
            try:
                if filename.endswith('.json'):
                    self.load_errors_json(filename)
                elif filename.endswith('.csv'):
                    self.load_errors_csv(filename)
                elif filename.endswith('.txt'):
                    self.load_errors_txt(filename)
                    
                self.update_error_table()
                self.status_label.setText(f"Ошибки загружены из {filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить файл: {str(e)}")
                
    def load_errors_json(self, filename):
        """Загрузка ошибок из JSON файла"""
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if "errors" in data:
            self.loaded_errors = data["errors"]
            
    def load_errors_csv(self, filename):
        """Загрузка ошибок из CSV файла"""
        # Упрощенная реализация
        pass
        
    def load_errors_txt(self, filename):
        """Загрузка ошибок из текстового файла"""
        # Упрощенная реализация
        pass
        
    def on_print_report(self):
        """Печать отчета об ошибках"""
        if not self.loaded_errors:
            QMessageBox.warning(self, "Печать", "Нет ошибок для печати")
            return
            
        # Здесь должна быть реализация печати
        # Показываем сообщение о подготовке
        QMessageBox.information(
            self,
            "Печать",
            "Отчет подготовлен для печати.\n\n"
            "В полной версии будет реализована печать с предварительным просмотром."
        )
        
    def on_ecu_changed(self, index):
        """Обработка изменения выбранного ECU"""
        ecu = self.ecu_combo.itemData(index)
        self.current_ecu = ecu
        self.filter_errors_by_ecu(ecu)
        
    def filter_errors_by_ecu(self, ecu):
        """Фильтрация ошибок по выбранному ECU"""
        if ecu == "ALL" or not self.loaded_errors:
            self.update_error_table()
        else:
            # Фильтруем и показываем только ошибки выбранного модуля
            self.error_table.setRowCount(0)
            
            if ecu in self.loaded_errors:
                errors = self.loaded_errors[ecu]
                for error in errors:
                    self.add_error_to_table(error, ecu)
                    
            # Обновление заголовка
            error_count = len(self.loaded_errors.get(ecu, []))
            module_name = self.get_module_name(ecu)
            self.error_count_label.setText(f"{module_name}: {error_count} ошибок")
            
    def add_error_to_table(self, error, module):
        """Добавление ошибки в таблицу"""
        row = self.error_table.rowCount()
        self.error_table.insertRow(row)
        
        color = self.get_error_color(error["status"])
        
        # Модуль
        module_item = QTableWidgetItem(self.get_module_name(module))
        module_item.setBackground(color)
        self.error_table.setItem(row, 0, module_item)
        
        # Код ошибки
        code_item = QTableWidgetItem(error["code"])
        code_item.setBackground(color)
        self.error_table.setItem(row, 1, code_item)
        
        # Остальные столбцы аналогично update_error_table()
        # ... (полная реализация)
        
    def show_table_context_menu(self, position):
        """Показать контекстное меню таблицы"""
        menu = QMenu()
        
        selected_rows = self.error_table.selectionModel().selectedRows()
        has_selection = len(selected_rows) > 0
        
        # Действия меню
        copy_action = QAction("Копировать код ошибки", self)
        copy_action.setEnabled(has_selection)
        copy_action.triggered.connect(self.copy_error_code)
        
        search_action = QAction("Найти в базе данных", self)
        search_action.setEnabled(has_selection)
        search_action.triggered.connect(self.search_error_in_database)
        
        mark_action = QAction("Пометить как проверенную", self)
        mark_action.setEnabled(has_selection)
        mark_action.triggered.connect(self.mark_error_as_checked)
        
        menu.addAction(copy_action)
        menu.addAction(search_action)
        menu.addAction(mark_action)
        menu.addSeparator()
        
        export_action = QAction("Экспортировать выбранные", self)
        export_action.setEnabled(has_selection)
        export_action.triggered.connect(self.export_selected_errors)
        
        menu.addAction(export_action)
        
        menu.exec_(self.error_table.viewport().mapToGlobal(position))
        
    def copy_error_code(self):
        """Копирование кода ошибки в буфер обмена"""
        selected_items = self.error_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            error_code = self.error_table.item(row, 1).text()
            clipboard = QApplication.clipboard()
            clipboard.setText(error_code)
            self.status_label.setText(f"Код ошибки {error_code} скопирован в буфер")
            
    def search_error_in_database(self):
        """Поиск ошибки в базе данных (внешний поиск)"""
        selected_items = self.error_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            error_code = self.error_table.item(row, 1).text()
            self.status_label.setText(f"Поиск информации по ошибке {error_code}...")
            # Здесь можно реализовать поиск в интернете или расширенной базе
            
    def mark_error_as_checked(self):
        """Пометка ошибки как проверенной"""
        selected_items = self.error_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            error_code = self.error_table.item(row, 1).text()
            
            # Изменяем цвет строки
            for col in range(self.error_table.columnCount()):
                item = self.error_table.item(row, col)
                if item:
                    item.setBackground(QColor(200, 255, 200))  # Светло-зеленый
            
            self.status_label.setText(f"Ошибка {error_code} помечена как проверенная")
            
    def export_selected_errors(self):
        """Экспорт выбранных ошибок"""
        selected_rows = self.error_table.selectionModel().selectedRows()
        if not selected_rows:
            return
            
        errors_to_export = []
        for row in selected_rows:
            error_code = self.error_table.item(row.row(), 1).text()
            module = self.error_table.item(row.row(), 0).text()
            errors_to_export.append((module, error_code))
        
        # Экспорт выбранных ошибок
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт выбранных ошибок",
            "",
            "Текстовые файлы (*.txt)"
        )
        
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("Экспортированные ошибки:\n")
                f.write("=" * 40 + "\n\n")
                for module, error_code in errors_to_export:
                    error_data = self.error_database.get(error_code, {})
                    f.write(f"Модуль: {module}\n")
                    f.write(f"Код ошибки: {error_code}\n")
                    f.write(f"Описание: {error_data.get('description', 'Неизвестная ошибка')}\n\n")
                
    def on_test_sensor(self):
        """Тестирование датчика связанного с ошибкой"""
        selected_items = self.error_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            error_code = self.error_table.item(row, 1).text()
            self.status_label.setText(f"Тестирование датчика для ошибки {error_code}...")
            
            # Здесь будет реализация тестирования датчика
            
    def on_check_wiring(self):
        """Проверка проводки"""
        selected_items = self.error_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            error_code = self.error_table.item(row, 1).text()
            self.status_label.setText(f"Проверка проводки для ошибки {error_code}...")
            
            # Здесь будет реализация проверки проводки
            
    def on_reset_adaptation(self):
        """Сброс адаптации"""
        selected_items = self.error_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            error_code = self.error_table.item(row, 1).text()
            
            reply = QMessageBox.question(
                self,
                "Сброс адаптации",
                f"Вы уверены, что хотите сбросить адаптацию для ошибки {error_code}?\n"
                "Это может повлиять на работу двигателя.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.status_label.setText(f"Сброс адаптации для ошибки {error_code}...")
                # Здесь будет реализация сброса адаптации
                
    def on_monitor_changed(self, state):
        """Изменение состояния мониторинга ошибки"""
        if state == Qt.Checked:
            self.status_label.setText("Мониторинг ошибки активирован")
        else:
            self.status_label.setText("Мониторинг ошибки деактивирован")
            
    def on_threshold_changed(self, value):
        """Изменение порогового значения"""
        self.status_label.setText(f"Пороговое значение установлено: {value}")
        
    def update_ecu_status(self, status):
        """Обновление статуса подключения к ECU"""
        self.ecu_status_label.setText(f"ECU: {status}")
        
    def add_error(self, module, error_code, status="ACTIVE", count=1):
        """Добавление ошибки вручную (для тестирования)"""
        if module not in self.loaded_errors:
            self.loaded_errors[module] = []
            
        # Проверяем, нет ли уже такой ошибки
        for error in self.loaded_errors[module]:
            if error["code"] == error_code:
                error["count"] += count
                error["last_occurrence"] = QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss')
                if status == "ACTIVE" and error["status"] != "ACTIVE":
                    error["status"] = status
                self.update_error_table()
                return
                
        # Добавляем новую ошибку
        new_error = {
            "code": error_code,
            "status": status,
            "first_occurrence": QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss'),
            "last_occurrence": QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss'),
            "count": count,
            "freeze_frame": {}
        }
        
        self.loaded_errors[module].append(new_error)
        self.update_error_table()
        
    def clear_all(self):
        """Полная очистка всех ошибок"""
        self.loaded_errors = {}
        self.update_error_table()
        self.reset_error_details()
        self.status_label.setText("Все ошибки очищены")
        
    def get_error_summary(self):
        """Получение сводки по ошибкам"""
        summary = {
            "total": self.count_total_errors(),
            "by_module": {},
            "by_severity": {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0},
            "by_status": {"ACTIVE": 0, "PENDING": 0, "PERMANENT": 0}
        }
        
        for module, errors in self.loaded_errors.items():
            summary["by_module"][module] = len(errors)
            
            for error in errors:
                error_data = self.error_database.get(error["code"], {})
                severity = error_data.get("severity", "UNKNOWN")
                if severity in summary["by_severity"]:
                    summary["by_severity"][severity] += 1
                    
                if error["status"] in summary["by_status"]:
                    summary["by_status"][error["status"]] += 1
                    
        return summary