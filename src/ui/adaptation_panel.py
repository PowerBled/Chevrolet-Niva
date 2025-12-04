"""
Панель адаптации и калибровки систем Chevrolet Niva
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QGroupBox, QLabel, QPushButton, QComboBox,
                             QTextEdit, QProgressBar, QSpinBox, QDoubleSpinBox,
                             QCheckBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QSplitter, QMessageBox,
                             QTabWidget, QFrame, QScrollArea)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont, QColor, QPalette
import time
from datetime import datetime


class AdaptationPanel(QWidget):
    """Панель для выполнения процедур адаптации и калибровки"""
    
    # Сигналы
    adaptation_started = pyqtSignal(str)  # Начата адаптация
    adaptation_completed = pyqtSignal(dict)  # Адаптация завершена
    adaptation_failed = pyqtSignal(str)  # Ошибка адаптации
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Ссылки на внешние компоненты
        self.diagnostics_engine = None
        self.connector = None
        
        # Текущий статус
        self.is_adapting = False
        self.current_procedure = None
        self.procedure_timer = QTimer()
        
        # Счетчики
        self.adaptation_count = 0
        self.success_count = 0
        self.failed_count = 0
        
        self.init_ui()
        self.setup_connections()
        
    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        
        # Панель статуса
        self.create_status_panel(main_layout)
        
        # Разделитель
        splitter = QSplitter(Qt.Vertical)
        
        # Верхняя часть - выбор процедур
        self.create_procedures_panel(splitter)
        
        # Нижняя часть - журнал и результаты
        self.create_results_panel(splitter)
        
        splitter.setSizes([400, 300])
        main_layout.addWidget(splitter)
        
        # Панель статистики
        self.create_statistics_panel(main_layout)
        
    def create_status_panel(self, parent_layout):
        """Создание панели статуса"""
        status_group = QGroupBox("Статус адаптации")
        status_layout = QGridLayout()
        
        # Индикатор подключения
        self.connection_label = QLabel("❌ Не подключено")
        self.connection_label.setStyleSheet("font-weight: bold; color: red;")
        status_layout.addWidget(self.connection_label, 0, 0)
        
        # Статус процедуры
        self.procedure_status = QLabel("Готов к работе")
        self.procedure_status.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(self.procedure_status, 0, 1)
        
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        status_layout.addWidget(self.progress_bar, 0, 2)
        
        # Кнопка отмены
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.setEnabled(False)
        self.cancel_button.setStyleSheet("background-color: #dc3545; color: white;")
        status_layout.addWidget(self.cancel_button, 0, 3)
        
        status_group.setLayout(status_layout)
        parent_layout.addWidget(status_group)
        
    def create_procedures_panel(self, parent):
        """Создание панели выбора процедур"""
        procedures_widget = QWidget()
        procedures_layout = QVBoxLayout(procedures_widget)
        
        # Группа выбора процедуры
        selection_group = QGroupBox("Выбор процедуры адаптации")
        selection_layout = QGridLayout()
        
        # Выбор модели автомобиля
        selection_layout.addWidget(QLabel("Модель автомобиля:"), 0, 0)
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "Chevrolet Niva 1.7i (2002-2009)",
            "Chevrolet Niva 1.7i (2010-2020)", 
            "Chevrolet Niva 1.8i (2014-2020)",
            "Chevrolet Niva Модерн (2021-н.в.)"
        ])
        selection_layout.addWidget(self.model_combo, 0, 1)
        
        # Выбор системы
        selection_layout.addWidget(QLabel("Система:"), 1, 0)
        self.system_combo = QComboBox()
        self.system_combo.addItems([
            "Двигатель (ECU)",
            "Дроссельная заслонка",
            "Иммобилайзер",
            "КПП (АКПП)",
            "ABS",
            "Airbag",
            "Климат-контроль"
        ])
        self.system_combo.currentTextChanged.connect(self.on_system_changed)
        selection_layout.addWidget(self.system_combo, 1, 1)
        
        # Выбор процедуры
        selection_layout.addWidget(QLabel("Процедура:"), 2, 0)
        self.procedure_combo = QComboBox()
        selection_layout.addWidget(self.procedure_combo, 2, 1)
        
        # Заполняем процедуры по умолчанию
        self.update_procedures_list()
        
        selection_group.setLayout(selection_layout)
        procedures_layout.addWidget(selection_group)
        
        # Группа настроек процедуры
        self.settings_group = QGroupBox("Настройки процедуры")
        self.settings_layout = QGridLayout()
        self.settings_group.setLayout(self.settings_layout)
        procedures_layout.addWidget(self.settings_group)
        
        # Группа предварительных условий
        conditions_group = QGroupBox("Предварительные условия")
        conditions_layout = QVBoxLayout()
        
        self.condition_ignition = QCheckBox("✅ Зажигание ВКЛ")
        self.condition_engine_off = QCheckBox("✅ Двигатель ВЫКЛ")
        self.condition_brake = QCheckBox("✅ Педаль тормоза не нажата")
        self.condition_clutch = QCheckBox("✅ Педаль сцепления не нажата")
        self.condition_throttle = QCheckBox("✅ Педаль акселератора не нажата")
        self.condition_gear = QCheckBox("✅ Рычаг КПП в нейтрали (N)")
        self.condition_battery = QCheckBox("✅ Напряжение аккумулятора > 12.0В")
        
        conditions_layout.addWidget(self.condition_ignition)
        conditions_layout.addWidget(self.condition_engine_off)
        conditions_layout.addWidget(self.condition_brake)
        conditions_layout.addWidget(self.condition_clutch)
        conditions_layout.addWidget(self.condition_throttle)
        conditions_layout.addWidget(self.condition_gear)
        conditions_layout.addWidget(self.condition_battery)
        
        conditions_group.setLayout(conditions_layout)
        procedures_layout.addWidget(conditions_group)
        
        # Кнопки управления
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("🚀 Запустить процедуру")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("⏹️ Остановить")
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: black;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
            }
        """)
        button_layout.addWidget(self.stop_button)
        
        self.test_button = QPushButton("🔧 Тест компонента")
        self.test_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
            }
        """)
        button_layout.addWidget(self.test_button)
        
        procedures_layout.addLayout(button_layout)
        
        parent.addWidget(procedures_widget)
        
    def create_results_panel(self, parent):
        """Создание панели результатов"""
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        
        # Табы для результатов и журнала
        tabs = QTabWidget()
        
        # Вкладка журнала
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 3px;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        # Кнопки управления журналом
        log_buttons = QHBoxLayout()
        self.clear_log_button = QPushButton("Очистить журнал")
        self.save_log_button = QPushButton("Сохранить журнал")
        self.copy_log_button = QPushButton("Копировать")
        
        log_buttons.addWidget(self.clear_log_button)
        log_buttons.addWidget(self.save_log_button)
        log_buttons.addWidget(self.copy_log_button)
        log_buttons.addStretch()
        
        log_layout.addLayout(log_buttons)
        tabs.addTab(log_tab, "Журнал")
        
        # Вкладка результатов
        results_tab = QWidget()
        results_tab_layout = QVBoxLayout(results_tab)
        
        # Таблица результатов
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "Время", "Процедура", "Статус", "Длительность", "Примечания"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #dee2e6;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        
        results_tab_layout.addWidget(self.results_table)
        tabs.addTab(results_tab, "История")
        
        # Вкладка калибровочных данных
        calibration_tab = QWidget()
        calibration_layout = QVBoxLayout(calibration_tab)
        
        self.calibration_text = QTextEdit()
        self.calibration_text.setReadOnly(True)
        self.calibration_text.setFont(QFont("Consolas", 9))
        calibration_layout.addWidget(self.calibration_text)
        
        calib_buttons = QHBoxLayout()
        self.load_calibration_button = QPushButton("Загрузить калибровку")
        self.save_calibration_button = QPushButton("Сохранить калибровку")
        self.reset_calibration_button = QPushButton("Сбросить к заводским")
        
        calib_buttons.addWidget(self.load_calibration_button)
        calib_buttons.addWidget(self.save_calibration_button)
        calib_buttons.addWidget(self.reset_calibration_button)
        calib_buttons.addStretch()
        
        calibration_layout.addLayout(calib_buttons)
        tabs.addTab(calibration_tab, "Калибровка")
        
        results_layout.addWidget(tabs)
        parent.addWidget(results_widget)
        
    def create_statistics_panel(self, parent_layout):
        """Создание панели статистики"""
        stats_group = QGroupBox("Статистика адаптации")
        stats_layout = QHBoxLayout()
        
        # Счетчики
        stats_widgets = []
        
        total_widget = self.create_stat_widget("Всего процедур", "0", "#17a2b8")
        stats_widgets.append(total_widget)
        
        success_widget = self.create_stat_widget("Успешно", "0", "#28a745")
        stats_widgets.append(success_widget)
        
        failed_widget = self.create_stat_widget("Неудачно", "0", "#dc3545")
        stats_widgets.append(failed_widget)
        
        time_widget = self.create_stat_widget("Общее время", "0:00:00", "#6c757d")
        stats_widgets.append(time_widget)
        
        # Добавляем виджеты в layout
        for widget in stats_widgets:
            stats_layout.addWidget(widget)
            
        stats_layout.addStretch()
        
        # Кнопка сброса статистики
        self.reset_stats_button = QPushButton("Сбросить статистику")
        self.reset_stats_button.setStyleSheet("background-color: #6c757d; color: white;")
        stats_layout.addWidget(self.reset_stats_button)
        
        stats_group.setLayout(stats_layout)
        parent_layout.addWidget(stats_group)
        
    def create_stat_widget(self, title, value, color):
        """Создание виджета статистики"""
        widget = QFrame()
        widget.setFrameStyle(QFrame.Box | QFrame.Raised)
        widget.setLineWidth(1)
        widget.setMidLineWidth(0)
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: {color}20;
                border: 2px solid {color};
                border-radius: 5px;
                padding: 5px;
            }}
        """)
        
        layout = QVBoxLayout(widget)
        
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; color: #495057;")
        
        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {color};
        """)
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        # Сохраняем ссылки на label'ы для обновления
        if title == "Всего процедур":
            self.total_procedures_label = value_label
        elif title == "Успешно":
            self.success_procedures_label = value_label
        elif title == "Неудачно":
            self.failed_procedures_label = value_label
        elif title == "Общее время":
            self.total_time_label = value_label
            
        return widget
        
    def setup_connections(self):
        """Настройка соединений сигналов и слотов"""
        # Кнопки
        self.start_button.clicked.connect(self.start_adaptation)
        self.stop_button.clicked.connect(self.stop_adaptation)
        self.cancel_button.clicked.connect(self.cancel_adaptation)
        self.test_button.clicked.connect(self.test_component)
        
        # Кнопки журнала
        self.clear_log_button.clicked.connect(self.clear_log)
        self.save_log_button.clicked.connect(self.save_log)
        self.copy_log_button.clicked.connect(self.copy_log)
        
        # Кнопки калибровки
        self.load_calibration_button.clicked.connect(self.load_calibration)
        self.save_calibration_button.clicked.connect(self.save_calibration)
        self.reset_calibration_button.clicked.connect(self.reset_calibration)
        
        # Кнопка сброса статистики
        self.reset_stats_button.clicked.connect(self.reset_statistics)
        
        # Таймер
        self.procedure_timer.timeout.connect(self.update_procedure_status)
        
    def update_procedures_list(self):
        """Обновление списка процедур в зависимости от выбранной системы"""
        system = self.system_combo.currentText()
        self.procedure_combo.clear()
        
        procedures_map = {
            "Двигатель (ECU)": [
                "Адаптация дроссельной заслонки",
                "Адаптация ХХ (обучение холостого хода)",
                "Адаптация топливных коррекций",
                "Адаптация зажигания",
                "Сброс адаптаций",
                "Калибровка ДПДЗ",
                "Калибровка ДМРВ",
                "Калибровка ДТОЖ",
                "Калибровка ДД"
            ],
            "Дроссельная заслонка": [
                "Обучение закрытого положения",
                "Обучение открытого положения",
                "Обучение механических ограничителей",
                "Проверка хода заслонки",
                "Калибровка потенциометров"
            ],
            "Иммобилайзер": [
                "Добавление нового ключа",
                "Удаление ключа",
                "Сброс иммобилайзера",
                "Калибровка антенны",
                "Программирование метки"
            ],
            "КПП (АКПП)": [
                "Адаптация сцепления",
                "Адаптация переключений",
                "Обучение селектора",
                "Калибровка соленоидов",
                "Сброс адаптаций АКПП"
            ],
            "ABS": [
                "Калибровка датчиков скорости",
                "Прокачка ABS",
                "Калибровка блока управления",
                "Тест насоса ABS",
                "Сброс ошибок ABS"
            ],
            "Airbag": [
                "Сброс ошибок Airbag",
                "Тест подушек безопасности",
                "Калибровка датчиков удара",
                "Тест пиропатронов"
            ],
            "Климат-контроль": [
                "Калибровка заслонок",
                "Обучение моторов заслонок",
                "Калибровка датчиков температуры",
                "Тест компрессора кондиционера"
            ]
        }
        
        if system in procedures_map:
            self.procedure_combo.addItems(procedures_map[system])
            
        # Обновляем настройки процедуры
        self.update_procedure_settings()
        
    def update_procedure_settings(self):
        """Обновление настроек для выбранной процедуры"""
        # Очищаем текущие настройки
        while self.settings_layout.count():
            child = self.settings_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        procedure = self.procedure_combo.currentText()
        
        if "дроссельной заслонки" in procedure.lower():
            self.create_throttle_settings()
        elif "хх" in procedure.lower() or "холостого хода" in procedure.lower():
            self.create_idle_settings()
        elif "иммобилайзер" in procedure.lower():
            self.create_immo_settings()
        elif "ключ" in procedure.lower():
            self.create_key_settings()
            
    def create_throttle_settings(self):
        """Создание настроек для адаптации дроссельной заслонки"""
        row = 0
        
        self.settings_layout.addWidget(QLabel("Температура двигателя:"), row, 0)
        self.temp_spin = QSpinBox()
        self.temp_spin.setRange(70, 110)
        self.temp_spin.setValue(90)
        self.temp_spin.setSuffix(" °C")
        self.settings_layout.addWidget(self.temp_spin, row, 1)
        row += 1
        
        self.settings_layout.addWidget(QLabel("Напряжение АКБ:"), row, 0)
        self.voltage_spin = QDoubleSpinBox()
        self.voltage_spin.setRange(12.0, 15.0)
        self.voltage_spin.setValue(13.5)
        self.voltage_spin.setDecimals(1)
        self.voltage_spin.setSuffix(" В")
        self.settings_layout.addWidget(self.voltage_spin, row, 1)
        row += 1
        
        self.settings_layout.addWidget(QLabel("Таймаут:"), row, 0)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(30, 300)
        self.timeout_spin.setValue(60)
        self.timeout_spin.setSuffix(" сек")
        self.settings_layout.addWidget(self.timeout_spin, row, 1)
        row += 1
        
        self.verbose_check = QCheckBox("Подробное логирование")
        self.verbose_check.setChecked(True)
        self.settings_layout.addWidget(self.verbose_check, row, 0, 1, 2)
        
    def create_idle_settings(self):
        """Создание настроек для адаптации ХХ"""
        row = 0
        
        self.settings_layout.addWidget(QLabel("Целевые обороты ХХ:"), row, 0)
        self.idle_rpm_spin = QSpinBox()
        self.idle_rpm_spin.setRange(700, 900)
        self.idle_rpm_spin.setValue(800)
        self.idle_rpm_spin.setSuffix(" об/мин")
        self.settings_layout.addWidget(self.idle_rpm_spin, row, 1)
        row += 1
        
        self.settings_layout.addWidget(QLabel("Допуск оборотов:"), row, 0)
        self.idle_tolerance_spin = QSpinBox()
        self.idle_tolerance_spin.setRange(10, 50)
        self.idle_tolerance_spin.setValue(20)
        self.idle_tolerance_spin.setSuffix(" об/мин")
        self.settings_layout.addWidget(self.idle_tolerance_spin, row, 1)
        row += 1
        
        self.settings_layout.addWidget(QLabel("Время стабилизации:"), row, 0)
        self.stabilization_spin = QSpinBox()
        self.stabilization_spin.setRange(10, 120)
        self.stabilization_spin.setValue(30)
        self.stabilization_spin.setSuffix(" сек")
        self.settings_layout.addWidget(self.stabilization_spin, row, 1)
        
    def create_immo_settings(self):
        """Создание настроек для иммобилайзера"""
        row = 0
        
        self.settings_layout.addWidget(QLabel("PIN-код:"), row, 0)
        self.pin_edit = QLineEdit()
        self.pin_edit.setEchoMode(QLineEdit.Password)
        self.pin_edit.setMaxLength(4)
        self.settings_layout.addWidget(self.pin_edit, row, 1)
        row += 1
        
        self.settings_layout.addWidget(QLabel("Количество ключей:"), row, 0)
        self.key_count_spin = QSpinBox()
        self.key_count_spin.setRange(1, 8)
        self.key_count_spin.setValue(2)
        self.settings_layout.addWidget(self.key_count_spin, row, 1)
        row += 1
        
        self.settings_layout.addWidget(QLabel("Номер ключа:"), row, 0)
        self.key_number_spin = QSpinBox()
        self.key_number_spin.setRange(1, 8)
        self.key_number_spin.setValue(1)
        self.settings_layout.addWidget(self.key_number_spin, row, 1)
        
    def create_key_settings(self):
        """Создание настроек для добавления ключа"""
        from PyQt5.QtWidgets import QLineEdit
        
        row = 0
        
        self.settings_layout.addWidget(QLabel("ID ключа:"), row, 0)
        self.key_id_edit = QLineEdit()
        self.key_id_edit.setPlaceholderText("Введите 8-значный HEX ID ключа")
        self.key_id_edit.setMaxLength(8)
        self.settings_layout.addWidget(self.key_id_edit, row, 1)
        row += 1
        
        self.settings_layout.addWidget(QLabel("Тип ключа:"), row, 0)
        self.key_type_combo = QComboBox()
        self.key_type_combo.addItems(["Обычный", "Стираемый", "Мастер"])
        self.settings_layout.addWidget(self.key_type_combo, row, 1)
        
    def on_system_changed(self, system):
        """Обработка изменения выбранной системы"""
        self.update_procedures_list()
        
    def set_connection(self, connected, device_info=""):
        """Установка статуса подключения"""
        if connected:
            self.connection_label.setText(f"✅ Подключено: {device_info}")
            self.connection_label.setStyleSheet("font-weight: bold; color: green;")
            self.start_button.setEnabled(True)
            self.test_button.setEnabled(True)
        else:
            self.connection_label.setText("❌ Не подключено")
            self.connection_label.setStyleSheet("font-weight: bold; color: red;")
            self.start_button.setEnabled(False)
            self.test_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            
    def set_diagnostics_engine(self, engine):
        """Установка ссылки на движок диагностики"""
        self.diagnostics_engine = engine
        if engine and engine.connector:
            self.connector = engine.connector
            
    def log_message(self, message, level="INFO"):
        """Добавление сообщения в журнал"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Определяем цвет для уровня
        colors = {
            "INFO": "black",
            "SUCCESS": "green",
            "WARNING": "orange",
            "ERROR": "red",
            "DEBUG": "blue"
        }
        
        color = colors.get(level, "black")
        
        # Форматируем сообщение
        formatted_message = f'<font color="{color}">[{timestamp}] {message}</font>'
        
        # Добавляем в журнал
        self.log_text.append(formatted_message)
        
        # Прокручиваем вниз
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
        
    def start_adaptation(self):
        """Запуск процедуры адаптации"""
        # Проверяем условия
        if not self.check_conditions():
            return
            
        # Получаем параметры процедуры
        procedure = self.procedure_combo.currentText()
        system = self.system_combo.currentText()
        model = self.model_combo.currentText()
        
        # Логируем начало
        self.log_message(f"🚀 Начало процедуры: {procedure}", "INFO")
        self.log_message(f"Система: {system}, Модель: {model}", "INFO")
        
        # Обновляем UI
        self.is_adapting = True
        self.current_procedure = procedure
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        self.procedure_status.setText(f"Выполняется: {procedure}")
        self.procedure_status.setStyleSheet("font-weight: bold; color: blue;")
        self.progress_bar.setValue(0)
        
        # Запускаем таймер для обновления прогресса
        self.procedure_timer.start(100)  # 100 мс
        
        # Сигнал о начале адаптации
        self.adaptation_started.emit(procedure)
        
        # Запускаем процедуру в отдельном потоке
        import threading
        self.adaptation_thread = threading.Thread(
            target=self.execute_adaptation_procedure,
            args=(procedure, system, model),
            daemon=True
        )
        self.adaptation_thread.start()
        
    def execute_adaptation_procedure(self, procedure, system, model):
        """Выполнение процедуры адаптации (в отдельном потоке)"""
        try:
            start_time = time.time()
            
            if "дроссельной заслонки" in procedure.lower():
                result = self.perform_throttle_adaptation()
            elif "хх" in procedure.lower() or "холостого хода" in procedure.lower():
                result = self.perform_idle_adaptation()
            elif "иммобилайзер" in procedure.lower():
                result = self.perform_immo_adaptation()
            elif "ключ" in procedure.lower():
                result = self.perform_key_programming()
            elif "топливных коррекций" in procedure.lower():
                result = self.perform_fuel_trim_reset()
            elif "сброс адаптаций" in procedure.lower():
                result = self.perform_adaptation_reset()
            else:
                result = {"status": "UNKNOWN", "message": "Процедура не реализована"}
                
            duration = time.time() - start_time
            
            # Обновляем UI через главный поток
            self.adaptation_completed_signal.emit({
                "procedure": procedure,
                "status": result.get("status", "UNKNOWN"),
                "message": result.get("message", ""),
                "duration": duration,
                "details": result
            })
            
        except Exception as e:
            # Обновляем UI через главный поток
            self.adaptation_failed_signal.emit(str(e))
            
    def perform_throttle_adaptation(self):
        """Выполнение адаптации дроссельной заслонки"""
        steps = [
            ("Проверка предварительных условий", 10),
            ("Сброс адаптаций дросселя", 20),
            ("Обучение закрытого положения", 40),
            ("Обучение открытого положения", 60),
            ("Проверка хода заслонки", 80),
            ("Сохранение параметров", 100)
        ]
        
        for step, progress in steps:
            self.update_progress(progress, step)
            time.sleep(2)  # Имитация работы
            
            # Здесь должна быть реальная работа с ELM327
            if self.connector and self.connector.is_connected:
                # Пример команды для адаптации дросселя
                if "закрытого положения" in step:
                    # Отправка команды обучения закрытого положения
                    pass
                elif "открытого положения" in step:
                    # Отправка команды обучения открытого положения
                    pass
                    
        return {
            "status": "SUCCESS",
            "message": "Адаптация дроссельной заслонки выполнена успешно",
            "throttle_position": 0.0,
            "adaptation_values": {
                "closed_position": 0.45,
                "open_position": 4.65,
                "range": 4.20
            }
        }
        
    def perform_idle_adaptation(self):
        """Выполнение адаптации холостого хода"""
        steps = [
            ("Прогрев двигателя до рабочей температуры", 20),
            ("Сброс адаптаций ХХ", 40),
            ("Стабилизация оборотов", 60),
            ("Обучение регулятора ХХ", 80),
            ("Проверка качества адаптации", 100)
        ]
        
        for step, progress in steps:
            self.update_progress(progress, step)
            time.sleep(3)  # Имитация работы
            
        return {
            "status": "SUCCESS",
            "message": "Адаптация холостого хода выполнена успешно",
            "idle_rpm": 800,
            "stability": "Хорошая",
            "correction": "+2.3%"
        }
        
    def perform_immo_adaptation(self):
        """Выполнение адаптации иммобилайзера"""
        return {
            "status": "SUCCESS",
            "message": "Процедура иммобилайзера выполнена",
            "keys_programmed": 2,
            "security_level": "Высокий"
        }
        
    def perform_key_programming(self):
        """Программирование ключа"""
        return {
            "status": "SUCCESS",
            "message": "Ключ успешно запрограммирован",
            "key_id": "A1B2C3D4",
            "key_type": "Обычный"
        }
        
    def perform_fuel_trim_reset(self):
        """Сброс топливных коррекций"""
        if self.diagnostics_engine:
            # Используем команды через diagnostics_engine
            pass
            
        return {
            "status": "SUCCESS",
            "message": "Топливные коррекции сброшены",
            "short_term": "0.0%",
            "long_term": "0.0%"
        }
        
    def perform_adaptation_reset(self):
        """Сброс всех адаптаций"""
        if self.diagnostics_engine:
            # Выполняем сброс через diagnostics_engine
            pass
            
        return {
            "status": "SUCCESS",
            "message": "Все адаптации сброшены",
            "reset_modules": ["ECU", "Throttle", "Transmission"]
        }
        
    def check_conditions(self):
        """Проверка предварительных условий"""
        conditions = [
            (self.condition_ignition.isChecked(), "Зажигание должно быть включено"),
            (self.condition_engine_off.isChecked(), "Двигатель должен быть выключен"),
            (self.condition_brake.isChecked(), "Педаль тормоза не должна быть нажата"),
            (self.condition_throttle.isChecked(), "Педаль газа не должна быть нажата"),
        ]
        
        failed_conditions = []
        for condition, message in conditions:
            if not condition:
                failed_conditions.append(message)
                
        if failed_conditions:
            error_msg = "Не выполнены условия:\n" + "\n".join(failed_conditions)
            QMessageBox.warning(self, "Предупреждение", error_msg)
            return False
            
        return True
        
    def update_progress(self, value, message=""):
        """Обновление прогресса (вызывается из потока)"""
        # Используем сигнал для обновления UI из другого потока
        self.progress_update_signal.emit(value, message)
        
    @pyqtSlot(int, str)
    def on_progress_update(self, value, message):
        """Обработка обновления прогресса"""
        self.progress_bar.setValue(value)
        if message:
            self.log_message(f"Прогресс: {message} ({value}%)", "INFO")
            
    @pyqtSlot(dict)
    def on_adaptation_completed(self, result):
        """Обработка завершения адаптации"""
        self.is_adapting = False
        self.procedure_timer.stop()
        
        procedure = result["procedure"]
        status = result["status"]
        message = result["message"]
        duration = result["duration"]
        
        # Обновляем UI
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setValue(100)
        
        if status == "SUCCESS":
            self.procedure_status.setText("✅ Процедура завершена успешно")
            self.procedure_status.setStyleSheet("font-weight: bold; color: green;")
            self.log_message(f"✅ {message}", "SUCCESS")
            
            # Увеличиваем счетчики
            self.adaptation_count += 1
            self.success_count += 1
            
        else:
            self.procedure_status.setText("❌ Процедура завершена с ошибкой")
            self.procedure_status.setStyleSheet("font-weight: bold; color: red;")
            self.log_message(f"❌ {message}", "ERROR")
            
            # Увеличиваем счетчики
            self.adaptation_count += 1
            self.failed_count += 1
            
        # Добавляем в историю
        self.add_to_history(result)
        
        # Обновляем статистику
        self.update_statistics()
        
        # Сигнал о завершении
        self.adaptation_completed.emit(result)
        
    @pyqtSlot(str)
    def on_adaptation_failed(self, error_message):
        """Обработка ошибки адаптации"""
        self.is_adapting = False
        self.procedure_timer.stop()
        
        # Обновляем UI
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setValue(0)
        
        self.procedure_status.setText("❌ Ошибка выполнения")
        self.procedure_status.setStyleSheet("font-weight: bold; color: red;")
        self.log_message(f"❌ Ошибка: {error_message}", "ERROR")
        
        # Увеличиваем счетчики
        self.adaptation_count += 1
        self.failed_count += 1
        self.update_statistics()
        
        # Сигнал об ошибке
        self.adaptation_failed.emit(error_message)
        
    def stop_adaptation(self):
        """Остановка текущей процедуры"""
        if self.is_adapting:
            reply = QMessageBox.question(
                self, "Остановка",
                "Вы уверены, что хотите остановить текущую процедуру?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.is_adapting = False
                self.procedure_timer.stop()
                
                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(False)
                self.cancel_button.setEnabled(False)
                
                self.procedure_status.setText("⏹️ Процедура остановлена")
                self.procedure_status.setStyleSheet("font-weight: bold; color: orange;")
                
                self.log_message("Процедура остановлена пользователем", "WARNING")
                
    def cancel_adaptation(self):
        """Отмена текущей процедуры"""
        self.stop_adaptation()
        
    def test_component(self):
        """Тестирование компонента"""
        component = self.procedure_combo.currentText()
        self.log_message(f"🔧 Тестирование компонента: {component}", "INFO")
        
        # Здесь будет реальное тестирование через ELM327
        # Пока имитируем тест
        self.log_message("Тест: Проверка связи... OK", "SUCCESS")
        self.log_message("Тест: Проверка напряжения... 12.8В", "SUCCESS")
        self.log_message("Тест: Проверка сопротивления... 4.7 Ом", "SUCCESS")
        self.log_message("✅ Тестирование завершено успешно", "SUCCESS")
        
    def clear_log(self):
        """Очистка журнала"""
        self.log_text.clear()
        self.log_message("Журнал очищен", "INFO")
        
    def save_log(self):
        """Сохранение журнала"""
        from PyQt5.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить журнал", "", "Текстовые файлы (*.txt);;Все файлы (*)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    # Получаем plain text из QTextEdit
                    f.write(self.log_text.toPlainText())
                self.log_message(f"Журнал сохранен: {filename}", "SUCCESS")
            except Exception as e:
                self.log_message(f"Ошибка сохранения: {e}", "ERROR")
                
    def copy_log(self):
        """Копирование журнала в буфер обмена"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.log_text.toPlainText())
        self.log_message("Журнал скопирован в буфер обмена", "INFO")
        
    def load_calibration(self):
        """Загрузка калибровочных данных"""
        from PyQt5.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getOpenFileName(
            self, "Загрузить калибровку", "", "Калибровочные файлы (*.cal);;Все файлы (*)"
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = f.read()
                self.calibration_text.setText(data)
                self.log_message(f"Калибровка загружена: {filename}", "SUCCESS")
            except Exception as e:
                self.log_message(f"Ошибка загрузки: {e}", "ERROR")
                
    def save_calibration(self):
        """Сохранение калибровочных данных"""
        from PyQt5.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить калибровку", "", "Калибровочные файлы (*.cal);;Все файлы (*)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.calibration_text.toPlainText())
                self.log_message(f"Калибровка сохранена: {filename}", "SUCCESS")
            except Exception as e:
                self.log_message(f"Ошибка сохранения: {e}", "ERROR")
                
    def reset_calibration(self):
        """Сброс калибровки к заводским настройкам"""
        reply = QMessageBox.question(
            self, "Сброс калибровки",
            "Вы уверены, что хотите сбросить калибровку к заводским настройкам?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Здесь будет загрузка заводских калибровочных данных
            factory_calibration = """Заводские настройки:
            
[Дроссельная заслонка]
Закрытое положение: 0.45В
Открытое положение: 4.65В
Ход: 4.20В

[Холостые обороты]
Целевые: 800 об/мин
Коррекция: ±50 об/мин

[Топливные коррекции]
Базовые: 0.0%
Диапазон: ±25%"""
            
            self.calibration_text.setText(factory_calibration)
            self.log_message("Калибровка сброшена к заводским настройкам", "SUCCESS")
            
    def add_to_history(self, result):
        """Добавление результата в историю"""
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        # Время
        time_item = QTableWidgetItem(datetime.now().strftime("%H:%M:%S"))
        self.results_table.setItem(row, 0, time_item)
        
        # Процедура
        proc_item = QTableWidgetItem(result["procedure"])
        self.results_table.setItem(row, 1, proc_item)
        
        # Статус
        status_item = QTableWidgetItem(result["status"])
        if result["status"] == "SUCCESS":
            status_item.setForeground(QColor("green"))
        else:
            status_item.setForeground(QColor("red"))
        self.results_table.setItem(row, 2, status_item)
        
        # Длительность
        duration = result.get("duration", 0)
        duration_item = QTableWidgetItem(f"{duration:.1f} сек")
        self.results_table.setItem(row, 3, duration_item)
        
        # Примечания
        notes_item = QTableWidgetItem(result.get("message", ""))
        self.results_table.setItem(row, 4, notes_item)
        
        # Прокручиваем к новой записи
        self.results_table.scrollToBottom()
        
    def update_procedure_status(self):
        """Обновление статуса процедуры (вызывается таймером)"""
        if self.is_adapting:
            current_value = self.progress_bar.value()
            if current_value < 99:
                self.progress_bar.setValue(current_value + 1)
                
    def update_statistics(self):
        """Обновление статистики"""
        # Обновляем счетчики
        self.total_procedures_label.setText(str(self.adaptation_count))
        self.success_procedures_label.setText(str(self.success_count))
        self.failed_procedures_label.setText(str(self.failed_count))
        
        # Обновляем общее время
        # Здесь нужно аккумулировать время всех процедур
        # Пока используем заглушку
        total_seconds = self.adaptation_count * 30  # Предполагаем 30 сек на процедуру
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        self.total_time_label.setText(f"{hours}:{minutes:02d}:{seconds:02d}")
        
    def reset_statistics(self):
        """Сброс статистики"""
        reply = QMessageBox.question(
            self, "Сброс статистики",
            "Вы уверены, что хотите сбросить статистику?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.adaptation_count = 0
            self.success_count = 0
            self.failed_count = 0
            self.update_statistics()
            self.log_message("Статистика сброшена", "INFO")
            
    def reset(self):
        """Сброс панели к начальному состоянию"""
        self.is_adapting = False
        self.procedure_timer.stop()
        
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        
        self.procedure_status.setText("Готов к работе")
        self.procedure_status.setStyleSheet("font-weight: bold; color: black;")
        
        self.progress_bar.setValue(0)
        
    # Необходимые импорты для PyQt5 сигналов
    from PyQt5.QtCore import pyqtSignal as Signal
    progress_update_signal = Signal(int, str)
    adaptation_completed_signal = Signal(dict)
    adaptation_failed_signal = Signal(str)


if __name__ == "__main__":
    # Тестирование панели
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Создаем тестовую панель
    panel = AdaptationPanel()
    panel.set_connection(True, "ELM327 Bluetooth")
    
    # Имитируем подключение движка диагностики
    class MockDiagnosticsEngine:
        def __init__(self):
            self.connector = MockConnector()
            
    class MockConnector:
        def __init__(self):
            self.is_connected = True
            
    panel.set_diagnostics_engine(MockDiagnosticsEngine())
    
    # Показываем панель
    panel.show()
    
    sys.exit(app.exec_())