"""
Главное окно приложения - полная версия
"""

import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QStatusBar, QMenuBar, QAction,
                             QMessageBox, QToolBar, QSplitter, QLabel,
                             QProgressBar, QFrame, QGridLayout, QGroupBox,
                             QPushButton, QComboBox, QCheckBox, QSpinBox,
                             QDoubleSpinBox, QTextEdit, QTableWidget,
                             QTableWidgetItem, QHeaderView, QTreeWidget,
                             QTreeWidgetItem, QListWidget, QListWidgetItem,
                             QLineEdit, QFileDialog, QDialog, QDialogButtonBox,
                             QFormLayout, QStackedWidget)
from PyQt5.QtCore import (Qt, QTimer, QSize, QSettings, QPoint, QByteArray,
                         QThread, pyqtSignal, QDateTime, QPropertyAnimation,
                         QEasingCurve)
from PyQt5.QtGui import (QIcon, QFont, QPalette, QColor, QBrush, QLinearGradient,
                        QPixmap, QMovie, QPainter, QPen, QFontDatabase,
                        QKeySequence, QStandardItemModel, QStandardItem)
from PyQt5.QtChart import (QChart, QChartView, QLineSeries, QValueAxis,
                          QDateTimeAxis, QBarSeries, QBarSet, QBarCategoryAxis,
                          QPieSeries, QPieSlice)

from ui.connection_panel import ConnectionPanel
from ui.diagnostic_panel import DiagnosticPanel
from ui.live_data_panel import LiveDataPanel
from ui.error_panel import ErrorPanel
from ui.adaptation_panel import AdaptationPanel
from ui.reports_panel import ReportsPanel
from ui.widgets.gauges import Tachometer, Speedometer, TemperatureGauge
from ui.widgets.indicators import LEDIndicator, StatusIndicator
from utils.logger import DiagnosticLogger

class MainWindow(QMainWindow):
    """Главное окно приложения - полная версия"""
    
    # Сигналы
    connection_status_changed = pyqtSignal(bool)
    diagnostic_started = pyqtSignal()
    diagnostic_completed = pyqtSignal(dict)
    error_cleared = pyqtSignal()
    adaptation_performed = pyqtSignal(str)
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.settings = QSettings("NivaDiagnostics", "ChevroletNivaPro")
        self.logger = DiagnosticLogger()
        self.current_vehicle = None
        self.diagnostic_results = {}
        self.live_data_timer = None
        self.animation_timer = None
        self.connection_status = False
        
        self.setup_ui()
        self.setup_connections()
        self.load_settings()
        self.setup_animation()
        
    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        # Основные настройки окна
        self.setWindowTitle("Chevrolet Niva Pro Diagnostic Suite v2.0")
        self.setMinimumSize(1600, 900)
        
        # Восстановление геометрии окна
        geometry = self.settings.value("window_geometry", QByteArray())
        if not geometry.isEmpty():
            self.restoreGeometry(geometry)
        else:
            self.setGeometry(100, 100, 1600, 900)
        
        # Установка иконки
        self.setWindowIcon(QIcon("assets/icons/app_icon.ico"))
        
        # Загрузка кастомного шрифта
        self.load_fonts()
        
        # Центральный виджет
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Основной layout
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Создание верхней панели
        self.create_top_panel()
        
        # Создание разделителя
        self.create_main_splitter()
        
        # Создание статус бара
        self.create_status_bar()
        
        # Создание меню
        self.create_menu_bar()
        
        # Создание тулбаров
        self.create_toolbars()
        
        # Загрузка стилей
        self.load_styles()
        
        # Инициализация таймеров
        self.setup_timers()
        
    def load_fonts(self):
        """Загрузка кастомных шрифтов"""
        # Добавление шрифтов из assets/fonts
        font_dir = "assets/fonts"
        if os.path.exists(font_dir):
            for font_file in os.listdir(font_dir):
                if font_file.endswith(('.ttf', '.otf')):
                    font_path = os.path.join(font_dir, font_file)
                    QFontDatabase.addApplicationFont(font_path)
        
        # Установка основного шрифта
        app_font = QFont("Segoe UI", 10)
        QApplication.setFont(app_font)
        
    def create_top_panel(self):
        """Создание верхней информационной панели"""
        self.top_panel = QFrame()
        self.top_panel.setObjectName("topPanel")
        self.top_panel.setMaximumHeight(80)
        self.top_panel.setMinimumHeight(60)
        
        top_layout = QHBoxLayout(self.top_panel)
        top_layout.setContentsMargins(20, 5, 20, 5)
        
        # Логотип и название
        logo_label = QLabel()
        logo_pixmap = QPixmap("assets/icons/logo.png")
        if logo_pixmap.isNull():
            logo_label.setText("NIVA PRO")
            logo_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        else:
            logo_label.setPixmap(logo_pixmap.scaled(120, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        # Индикатор состояния
        self.status_indicator = StatusIndicator()
        self.status_indicator.setFixedSize(20, 20)
        
        # Текущее состояние
        self.status_label = QLabel("Готов к работе")
        self.status_label.setObjectName("statusLabel")
        
        # Информация о подключении
        self.connection_info = QLabel("Нет подключения")
        self.connection_info.setObjectName("connectionInfo")
        
        # Информация о автомобиле
        self.vehicle_info = QLabel("Автомобиль: Не выбран")
        self.vehicle_info.setObjectName("vehicleInfo")
        
        # Кнопка быстрого подключения
        self.quick_connect_btn = QPushButton("Быстрое подключение")
        self.quick_connect_btn.setIcon(QIcon("assets/icons/quick_connect.png"))
        self.quick_connect_btn.setObjectName("quickConnectBtn")
        self.quick_connect_btn.clicked.connect(self.quick_connect)
        
        # Добавление виджетов
        top_layout.addWidget(logo_label)
        top_layout.addSpacing(20)
        top_layout.addWidget(self.status_indicator)
        top_layout.addWidget(self.status_label)
        top_layout.addStretch()
        top_layout.addWidget(self.connection_info)
        top_layout.addSpacing(10)
        top_layout.addWidget(self.vehicle_info)
        top_layout.addStretch()
        top_layout.addWidget(self.quick_connect_btn)
        
        self.main_layout.addWidget(self.top_panel)
        
    def create_main_splitter(self):
        """Создание основного разделителя"""
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        
        # Левая панель (навигация и информация)
        self.create_left_panel()
        
        # Центральная область (вкладки)
        self.create_center_area()
        
        # Правая панель (быстрый доступ и виджеты)
        self.create_right_panel()
        
        # Установка размеров
        self.main_splitter.setSizes([250, 1000, 250])
        
        self.main_layout.addWidget(self.main_splitter, 1)
        
    def create_left_panel(self):
        """Создание левой панели навигации"""
        left_widget = QWidget()
        left_widget.setObjectName("leftPanel")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        # Панель выбора автомобиля
        vehicle_group = QGroupBox("Выбор автомобиля")
        vehicle_group.setObjectName("vehicleGroup")
        vehicle_layout = QVBoxLayout()
        
        self.vehicle_combo = QComboBox()
        self.vehicle_combo.addItem("Chevrolet Niva 1.7i (2002-2009)", "2123")
        self.vehicle_combo.addItem("Chevrolet Niva 1.7i (2010-2020)", "21236")
        self.vehicle_combo.addItem("Chevrolet Niva 1.8i (2014-2020)", "2123-250")
        self.vehicle_combo.addItem("Chevrolet Niva Модерн (2021-н.в.)", "2123M")
        self.vehicle_combo.currentIndexChanged.connect(self.on_vehicle_changed)
        
        self.vin_label = QLabel("VIN: Не указан")
        self.vin_label.setWordWrap(True)
        
        self.read_vin_btn = QPushButton("Считать VIN")
        self.read_vin_btn.setIcon(QIcon("assets/icons/vin.png"))
        self.read_vin_btn.clicked.connect(self.read_vin)
        
        vehicle_layout.addWidget(QLabel("Модель:"))
        vehicle_layout.addWidget(self.vehicle_combo)
        vehicle_layout.addWidget(self.vin_label)
        vehicle_layout.addWidget(self.read_vin_btn)
        vehicle_group.setLayout(vehicle_layout)
        
        # Панель быстрой навигации
        nav_group = QGroupBox("Быстрая навигация")
        nav_group.setObjectName("navGroup")
        nav_layout = QVBoxLayout()
        
        nav_buttons = [
            ("Диагностика двигателя", "engine_diag", "assets/icons/engine.png"),
            ("Проверка ABS", "abs_diag", "assets/icons/abs.png"),
            ("Диагностика подушек", "airbag_diag", "assets/icons/airbag.png"),
            ("Иммобилайзер", "immo_diag", "assets/icons/immo.png"),
            ("Приборная панель", "cluster_diag", "assets/icons/cluster.png"),
            ("Климат-контроль", "ac_diag", "assets/icons/ac.png"),
        ]
        
        self.nav_buttons = {}
        for text, id_, icon_path in nav_buttons:
            btn = QPushButton(text)
            btn.setIcon(QIcon(icon_path))
            btn.setObjectName(f"navBtn_{id_}")
            btn.clicked.connect(lambda checked, id=id_: self.quick_navigate(id))
            nav_layout.addWidget(btn)
            self.nav_buttons[id_] = btn
        
        nav_layout.addStretch()
        nav_group.setLayout(nav_layout)
        
        # Панель состояния систем
        systems_group = QGroupBox("Состояние систем")
        systems_group.setObjectName("systemsGroup")
        systems_layout = QVBoxLayout()
        
        self.system_indicators = {}
        systems = [
            ("Двигатель", "engine_status", "#27ae60"),
            ("ABS", "abs_status", "#e74c3c"),
            ("Подушки", "airbag_status", "#f39c12"),
            ("Иммобилайзер", "immo_status", "#3498db"),
        ]
        
        for name, id_, color in systems:
            indicator = LEDIndicator(color)
            indicator.setFixedSize(12, 12)
            
            label = QLabel(name)
            label.setObjectName("systemLabel")
            
            hbox = QHBoxLayout()
            hbox.addWidget(indicator)
            hbox.addWidget(label)
            hbox.addStretch()
            
            systems_layout.addLayout(hbox)
            self.system_indicators[id_] = indicator
        
        systems_group.setLayout(systems_layout)
        
        # Добавление виджетов на левую панель
        left_layout.addWidget(vehicle_group)
        left_layout.addWidget(nav_group)
        left_layout.addWidget(systems_group)
        left_layout.addStretch()
        
        self.main_splitter.addWidget(left_widget)
        
    def create_center_area(self):
        """Создание центральной области с вкладками"""
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        
        # Виджет вкладок
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("mainTabWidget")
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setMovable(True)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        
        # Создание основных вкладок
        self.create_main_tabs()
        
        # Кнопка добавления новой вкладки
        self.add_tab_btn = QPushButton("+")
        self.add_tab_btn.setObjectName("addTabBtn")
        self.add_tab_btn.setFixedSize(30, 30)
        self.add_tab_btn.clicked.connect(self.add_custom_tab)
        
        # Добавление кнопки к табам
        self.tab_widget.setCornerWidget(self.add_tab_btn, Qt.TopRightCorner)
        
        center_layout.addWidget(self.tab_widget)
        
        # Панель прогресса
        self.progress_panel = QFrame()
        self.progress_panel.setObjectName("progressPanel")
        self.progress_panel.setVisible(False)
        progress_layout = QHBoxLayout(self.progress_panel)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        
        self.progress_label = QLabel("Выполнение диагностики...")
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setIcon(QIcon("assets/icons/cancel.png"))
        self.cancel_btn.clicked.connect(self.cancel_operation)
        
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar, 1)
        progress_layout.addWidget(self.cancel_btn)
        
        center_layout.addWidget(self.progress_panel)
        
        self.main_splitter.addWidget(center_widget)
        
    def create_main_tabs(self):
        """Создание основных вкладок"""
        # Вкладка подключения
        self.connection_tab = ConnectionPanel()
        self.tab_widget.addTab(self.connection_tab, QIcon("assets/icons/connection.png"), "Подключение")
        
        # Вкладка диагностики
        self.diagnostic_tab = DiagnosticPanel()
        self.tab_widget.addTab(self.diagnostic_tab, QIcon("assets/icons/diagnostic.png"), "Диагностика")
        
        # Вкладка живых данных
        self.live_data_tab = LiveDataPanel()
        self.tab_widget.addTab(self.live_data_tab, QIcon("assets/icons/live_data.png"), "Живые данные")
        
        # Вкладка ошибок
        self.error_tab = ErrorPanel()
        self.tab_widget.addTab(self.error_tab, QIcon("assets/icons/error.png"), "Ошибки")
        
        # Вкладка адаптации
        self.adaptation_tab = AdaptationPanel()
        self.tab_widget.addTab(self.adaptation_tab, QIcon("assets/icons/adaptation.png"), "Адаптация")
        
        # Вкладка осциллографа
        self.oscilloscope_tab = self.create_oscilloscope_tab()
        self.tab_widget.addTab(self.oscilloscope_tab, QIcon("assets/icons/oscilloscope.png"), "Осциллограф")
        
        # Вкладка отчетов
        self.reports_tab = ReportsPanel()
        self.tab_widget.addTab(self.reports_tab, QIcon("assets/icons/reports.png"), "Отчеты")
        
        # Вкладка карт
        self.maps_tab = self.create_maps_tab()
        self.tab_widget.addTab(self.maps_tab, QIcon("assets/icons/maps.png"), "Карты")
        
        # Вкладка логирования
        self.logging_tab = self.create_logging_tab()
        self.tab_widget.addTab(self.logging_tab, QIcon("assets/icons/logging.png"), "Логи")
        
        # Изначально отключаем все вкладки кроме подключения
        for i in range(1, self.tab_widget.count()):
            self.tab_widget.setTabEnabled(i, False)
        
    def create_oscilloscope_tab(self):
        """Создание вкладки осциллографа"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Панель управления осциллографом
        control_panel = QFrame()
        control_layout = QHBoxLayout(control_panel)
        
        self.osc_channel_combo = QComboBox()
        self.osc_channel_combo.addItems(["Канал 1", "Канал 2", "Канал 3", "Канал 4"])
        
        self.osc_trigger_combo = QComboBox()
        self.osc_trigger_combo.addItems(["Авто", "Восходящий", "Нисходящий"])
        
        self.osc_timebase_spin = QDoubleSpinBox()
        self.osc_timebase_spin.setRange(0.1, 10.0)
        self.osc_timebase_spin.setValue(1.0)
        self.osc_timebase_spin.setSuffix(" мс/дел")
        
        self.osc_voltage_spin = QDoubleSpinBox()
        self.osc_voltage_spin.setRange(0.1, 20.0)
        self.osc_voltage_spin.setValue(1.0)
        self.osc_voltage_spin.setSuffix(" В/дел")
        
        self.osc_start_btn = QPushButton("Старт")
        self.osc_start_btn.setIcon(QIcon("assets/icons/start.png"))
        
        self.osc_stop_btn = QPushButton("Стоп")
        self.osc_stop_btn.setIcon(QIcon("assets/icons/stop.png"))
        
        control_layout.addWidget(QLabel("Канал:"))
        control_layout.addWidget(self.osc_channel_combo)
        control_layout.addWidget(QLabel("Триггер:"))
        control_layout.addWidget(self.osc_trigger_combo)
        control_layout.addWidget(QLabel("Временная база:"))
        control_layout.addWidget(self.osc_timebase_spin)
        control_layout.addWidget(QLabel("Вольт/дел:"))
        control_layout.addWidget(self.osc_voltage_spin)
        control_layout.addWidget(self.osc_start_btn)
        control_layout.addWidget(self.osc_stop_btn)
        
        # Область графика
        self.osc_chart_view = QChartView()
        self.osc_chart_view.setRenderHint(QPainter.Antialiasing)
        
        layout.addWidget(control_panel)
        layout.addWidget(self.osc_chart_view, 1)
        
        return widget
        
    def create_maps_tab(self):
        """Создание вкладки карт"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Панель выбора карты
        map_control = QFrame()
        map_control_layout = QHBoxLayout(map_control)
        
        self.map_type_combo = QComboBox()
        self.map_type_combo.addItems([
            "Топливная карта",
            "Карта зажигания",
            "Карта VVT",
            "Карта турбины",
            "Карта EGR"
        ])
        
        self.map_load_btn = QPushButton("Загрузить карту")
        self.map_load_btn.setIcon(QIcon("assets/icons/load.png"))
        
        self.map_save_btn = QPushButton("Сохранить карту")
        self.map_save_btn.setIcon(QIcon("assets/icons/save.png"))
        
        self.map_edit_btn = QPushButton("Редактировать")
        self.map_edit_btn.setIcon(QIcon("assets/icons/edit.png"))
        
        map_control_layout.addWidget(QLabel("Тип карты:"))
        map_control_layout.addWidget(self.map_type_combo, 1)
        map_control_layout.addWidget(self.map_load_btn)
        map_control_layout.addWidget(self.map_save_btn)
        map_control_layout.addWidget(self.map_edit_btn)
        
        # Область отображения карты
        map_display = QFrame()
        map_display_layout = QVBoxLayout(map_display)
        
        self.map_table = QTableWidget()
        self.map_table.setRowCount(16)
        self.map_table.setColumnCount(16)
        
        map_display_layout.addWidget(self.map_table)
        
        layout.addWidget(map_control)
        layout.addWidget(map_display, 1)
        
        return widget
        
    def create_logging_tab(self):
        """Создание вкладки логирования"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Панель управления логированием
        log_control = QFrame()
        log_control_layout = QHBoxLayout(log_control)
        
        self.log_start_btn = QPushButton("Начать запись")
        self.log_start_btn.setIcon(QIcon("assets/icons/record.png"))
        
        self.log_stop_btn = QPushButton("Остановить")
        self.log_stop_btn.setIcon(QIcon("assets/icons/stop.png"))
        
        self.log_clear_btn = QPushButton("Очистить")
        self.log_clear_btn.setIcon(QIcon("assets/icons/clear.png"))
        
        self.log_save_btn = QPushButton("Сохранить лог")
        self.log_save_btn.setIcon(QIcon("assets/icons/save_log.png"))
        
        log_control_layout.addWidget(self.log_start_btn)
        log_control_layout.addWidget(self.log_stop_btn)
        log_control_layout.addWidget(self.log_clear_btn)
        log_control_layout.addWidget(self.log_save_btn)
        log_control_layout.addStretch()
        
        # Область логов
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 9))
        
        layout.addWidget(log_control)
        layout.addWidget(self.log_text, 1)
        
        return widget
        
    def create_right_panel(self):
        """Создание правой панели"""
        right_widget = QWidget()
        right_widget.setObjectName("rightPanel")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        # Панель быстрых виджетов
        quick_widgets_group = QGroupBox("Быстрые виджеты")
        quick_widgets_group.setObjectName("quickWidgetsGroup")
        quick_layout = QVBoxLayout()
        
        # Тахометр
        self.tachometer = Tachometer()
        self.tachometer.setMinimumHeight(120)
        
        # Спидометр
        self.speedometer = Speedometer()
        self.speedometer.setMinimumHeight(120)
        
        # Датчик температуры
        self.temp_gauge = TemperatureGauge()
        self.temp_gauge.setMinimumHeight(100)
        
        quick_layout.addWidget(QLabel("Обороты:"))
        quick_layout.addWidget(self.tachometer)
        quick_layout.addWidget(QLabel("Скорость:"))
        quick_layout.addWidget(self.speedometer)
        quick_layout.addWidget(QLabel("Температура:"))
        quick_layout.addWidget(self.temp_gauge)
        
        quick_widgets_group.setLayout(quick_layout)
        
        # Панель быстрых действий
        quick_actions_group = QGroupBox("Быстрые действия")
        quick_actions_group.setObjectName("quickActionsGroup")
        actions_layout = QVBoxLayout()
        
        quick_actions = [
            ("Эмуляция неисправностей", "fault_emulation", "assets/icons/fault.png"),
            ("Калибровка датчиков", "sensor_calibration", "assets/icons/calibrate.png"),
            ("Тест форсунок", "injector_test", "assets/icons/injector.png"),
            ("Тест катушек", "coil_test", "assets/icons/coil.png"),
            ("Проверка компрессии", "compression_test", "assets/icons/compression.png"),
            ("Сброс адаптаций", "reset_adaptations", "assets/icons/reset.png"),
        ]
        
        self.quick_action_buttons = {}
        for text, id_, icon_path in quick_actions:
            btn = QPushButton(text)
            btn.setIcon(QIcon(icon_path))
            btn.setObjectName(f"quickAction_{id_}")
            btn.clicked.connect(lambda checked, id=id_: self.perform_quick_action(id))
            actions_layout.addWidget(btn)
            self.quick_action_buttons[id_] = btn
        
        actions_layout.addStretch()
        quick_actions_group.setLayout(actions_layout)
        
        # Панель информации о сеансе
        session_group = QGroupBox("Информация о сеансе")
        session_group.setObjectName("sessionGroup")
        session_layout = QVBoxLayout()
        
        self.session_time_label = QLabel("Время: 00:00:00")
        self.session_data_label = QLabel("Данные: 0 байт")
        self.session_errors_label = QLabel("Ошибок: 0")
        self.session_status_label = QLabel("Статус: Ожидание")
        
        session_layout.addWidget(self.session_time_label)
        session_layout.addWidget(self.session_data_label)
        session_layout.addWidget(self.session_errors_label)
        session_layout.addWidget(self.session_status_label)
        session_layout.addStretch()
        
        # Кнопка завершения сеанса
        self.end_session_btn = QPushButton("Завершить сеанс")
        self.end_session_btn.setIcon(QIcon("assets/icons/end_session.png"))
        self.end_session_btn.clicked.connect(self.end_session)
        
        session_layout.addWidget(self.end_session_btn)
        quick_actions_group.setLayout(session_layout)
        
        # Добавление виджетов на правую панель
        right_layout.addWidget(quick_widgets_group)
        right_layout.addWidget(quick_actions_group)
        right_layout.addWidget(session_group)
        right_layout.addStretch()
        
        self.main_splitter.addWidget(right_widget)
        
    def create_status_bar(self):
        """Создание статус бара"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Основное сообщение
        self.status_bar.showMessage("Готов к работе")
        
        # Виджеты в статус баре
        self.memory_label = QLabel("Память: --")
        self.cpu_label = QLabel("CPU: --")
        self.connection_speed_label = QLabel("Скорость: --")
        self.data_rate_label = QLabel("Данные: --/сек")
        
        self.status_bar.addPermanentWidget(self.memory_label)
        self.status_bar.addPermanentWidget(self.cpu_label)
        self.status_bar.addPermanentWidget(self.connection_speed_label)
        self.status_bar.addPermanentWidget(self.data_rate_label)
        
    def create_menu_bar(self):
        """Создание меню бара"""
        menubar = self.menuBar()
        
        # Меню Файл
        file_menu = menubar.addMenu("&Файл")
        
        new_action = QAction(QIcon("assets/icons/new.png"), "&Новый сеанс", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_session)
        file_menu.addAction(new_action)
        
        open_action = QAction(QIcon("assets/icons/open.png"), "&Открыть...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        save_action = QAction(QIcon("assets/icons/save.png"), "&Сохранить", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction(QIcon("assets/icons/save_as.png"), "Сохранить &как...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        export_menu = file_menu.addMenu(QIcon("assets/icons/export.png"), "&Экспорт")
        
        export_pdf_action = QAction("В PDF", self)
        export_pdf_action.triggered.connect(lambda: self.export_report("pdf"))
        export_menu.addAction(export_pdf_action)
        
        export_excel_action = QAction("В Excel", self)
        export_excel_action.triggered.connect(lambda: self.export_report("excel"))
        export_menu.addAction(export_excel_action)
        
        export_word_action = QAction("В Word", self)
        export_word_action.triggered.connect(lambda: self.export_report("word"))
        export_menu.addAction(export_word_action)
        
        file_menu.addSeparator()
        
        print_action = QAction(QIcon("assets/icons/print.png"), "&Печать...", self)
        print_action.setShortcut("Ctrl+P")
        print_action.triggered.connect(self.print_report)
        file_menu.addAction(print_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction(QIcon("assets/icons/exit.png"), "&Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Меню Правка
        edit_menu = menubar.addMenu("&Правка")
        
        undo_action = QAction(QIcon("assets/icons/undo.png"), "&Отменить", self)
        undo_action.setShortcut("Ctrl+Z")
        edit_menu.addAction(undo_action)
        
        redo_action = QAction(QIcon("assets/icons/redo.png"), "&Повторить", self)
        redo_action.setShortcut("Ctrl+Y")
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        copy_action = QAction(QIcon("assets/icons/copy.png"), "&Копировать", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.copy_data)
        edit_menu.addAction(copy_action)
        
        paste_action = QAction(QIcon("assets/icons/paste.png"), "&Вставить", self)
        paste_action.setShortcut("Ctrl+V")
        edit_menu.addAction(paste_action)
        
        edit_menu.addSeparator()
        
        find_action = QAction(QIcon("assets/icons/find.png"), "&Найти...", self)
        find_action.setShortcut("Ctrl+F")
        edit_menu.addAction(find_action)
        
        # Меню Вид
        view_menu = menubar.addMenu("&Вид")
        
        toolbar_action = QAction("&Панель инструментов", self)
        toolbar_action.setCheckable(True)
        toolbar_action.setChecked(True)
        toolbar_action.triggered.connect(self.toggle_toolbar)
        view_menu.addAction(toolbar_action)
        
        statusbar_action = QAction("&Строка состояния", self)
        statusbar_action.setCheckable(True)
        statusbar_action.setChecked(True)
        statusbar_action.triggered.connect(self.toggle_statusbar)
        view_menu.addAction(statusbar_action)
        
        view_menu.addSeparator()
        
        fullscreen_action = QAction("&Полный экран", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)
        
        # Меню Диагностика
        diag_menu = menubar.addMenu("&Диагностика")
        
        quick_diag_action = QAction(QIcon("assets/icons/quick_diag.png"), "&Быстрая диагностика", self)
        quick_diag_action.setShortcut("F5")
        quick_diag_action.triggered.connect(self.quick_diagnostic)
        diag_menu.addAction(quick_diag_action)
        
        full_diag_action = QAction(QIcon("assets/icons/full_diag.png"), "&Полная диагностика", self)
        full_diag_action.setShortcut("F6")
        full_diag_action.triggered.connect(self.full_diagnostic)
        diag_menu.addAction(full_diag_action)
        
        diag_menu.addSeparator()
        
        engine_diag_action = QAction(QIcon("assets/icons/engine.png"), "Диагностика &двигателя", self)
        engine_diag_action.triggered.connect(lambda: self.system_diagnostic("engine"))
        diag_menu.addAction(engine_diag_action)
        
        abs_diag_action = QAction(QIcon("assets/icons/abs.png"), "Диагностика &ABS", self)
        abs_diag_action.triggered.connect(lambda: self.system_diagnostic("abs"))
        diag_menu.addAction(abs_diag_action)
        
        diag_menu.addSeparator()
        
        clear_errors_action = QAction(QIcon("assets/icons/clear_errors.png"), "&Очистить ошибки", self)
        clear_errors_action.setShortcut("Ctrl+E")
        clear_errors_action.triggered.connect(self.clear_all_errors)
        diag_menu.addAction(clear_errors_action)
        
        # Меню Настройки
        settings_menu = menubar.addMenu("&Настройки")
        
        preferences_action = QAction(QIcon("assets/icons/preferences.png"), "&Настройки программы", self)
        preferences_action.setShortcut("Ctrl+,")
        preferences_action.triggered.connect(self.open_preferences)
        settings_menu.addAction(preferences_action)
        
        vehicle_settings_action = QAction(QIcon("assets/icons/vehicle_settings.png"), "Настройки &автомобиля", self)
        vehicle_settings_action.triggered.connect(self.open_vehicle_settings)
        settings_menu.addAction(vehicle_settings_action)
        
        connection_settings_action = QAction(QIcon("assets/icons/connection_settings.png"), "Настройки &подключения", self)
        connection_settings_action.triggered.connect(self.open_connection_settings)
        settings_menu.addAction(connection_settings_action)
        
        settings_menu.addSeparator()
        
        themes_menu = settings_menu.addMenu(QIcon("assets/icons/themes.png"), "&Темы")
        
        dark_theme_action = QAction("Темная", self)
        dark_theme_action.triggered.connect(lambda: self.change_theme("dark"))
        themes_menu.addAction(dark_theme_action)
        
        light_theme_action = QAction("Светлая", self)
        light_theme_action.triggered.connect(lambda: self.change_theme("light"))
        themes_menu.addAction(light_theme_action)
        
        blue_theme_action = QAction("Синяя", self)
        blue_theme_action.triggered.connect(lambda: self.change_theme("blue"))
        themes_menu.addAction(blue_theme_action)
        
        # Меню Сервис
        service_menu = menubar.addMenu("&Сервис")
        
        calibration_action = QAction(QIcon("assets/icons/calibration.png"), "&Калибровка", self)
        calibration_action.triggered.connect(self.open_calibration)
        service_menu.addAction(calibration_action)
        
        adaptation_action = QAction(QIcon("assets/icons/adaptation.png"), "&Адаптация", self)
        adaptation_action.triggered.connect(self.open_adaptation)
        service_menu.addAction(adaptation_action)
        
        service_menu.addSeparator()
        
        coding_action = QAction(QIcon("assets/icons/coding.png"), "&Кодирование", self)
        coding_action.triggered.connect(self.open_coding)
        service_menu.addAction(coding_action)
        
        flashing_action = QAction(QIcon("assets/icons/flashing.png"), "&Прошивка", self)
        flashing_action.triggered.connect(self.open_flashing)
        service_menu.addAction(flashing_action)
        
        # Меню Помощь
        help_menu = menubar.addMenu("&Помощь")
        
        help_action = QAction(QIcon("assets/icons/help.png"), "&Справка", self)
        help_action.setShortcut("F1")
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        
        tutorial_action = QAction(QIcon("assets/icons/tutorial.png"), "&Обучение", self)
        tutorial_action.triggered.connect(self.show_tutorial)
        help_menu.addAction(tutorial_action)
        
        help_menu.addSeparator()
        
        check_updates_action = QAction(QIcon("assets/icons/update.png"), "Проверить &обновления", self)
        check_updates_action.triggered.connect(self.check_for_updates)
        help_menu.addAction(check_updates_action)
        
        help_menu.addSeparator()
        
        about_action = QAction(QIcon("assets/icons/about.png"), "&О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_toolbars(self):
        """Создание тулбаров"""
        # Главный тулбар
        self.main_toolbar = QToolBar("Главная панель")
        self.main_toolbar.setObjectName("mainToolbar")
        self.main_toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(self.main_toolbar)
        
        # Кнопки главного тулбара
        self.connect_action = QAction(QIcon("assets/icons/connect.png"), "Подключиться", self)
        self.connect_action.triggered.connect(self.connection_tab.connect_device)
        self.main_toolbar.addAction(self.connect_action)
        
        self.disconnect_action = QAction(QIcon("assets/icons/disconnect.png"), "Отключиться", self)
        self.disconnect_action.triggered.connect(self.connection_tab.disconnect_device)
        self.disconnect_action.setEnabled(False)
        self.main_toolbar.addAction(self.disconnect_action)
        
        self.main_toolbar.addSeparator()
        
        self.diagnostic_action = QAction(QIcon("assets/icons/diagnostic.png"), "Диагностика", self)
        self.diagnostic_action.triggered.connect(self.start_diagnostic)
        self.main_toolbar.addAction(self.diagnostic_action)
        
        self.clear_errors_action = QAction(QIcon("assets/icons/clear_errors.png"), "Очистить ошибки", self)
        self.clear_errors_action.triggered.connect(self.clear_errors)
        self.main_toolbar.addAction(self.clear_errors_action)
        
        self.main_toolbar.addSeparator()
        
        self.live_data_action = QAction(QIcon("assets/icons/live_data.png"), "Живые данные", self)
        self.live_data_action.triggered.connect(self.start_live_data)
        self.main_toolbar.addAction(self.live_data_action)
        
        self.graph_action = QAction(QIcon("assets/icons/graph.png"), "Графики", self)
        self.graph_action.triggered.connect(self.show_graphs)
        self.main_toolbar.addAction(self.graph_action)
        
        self.main_toolbar.addSeparator()
        
        self.report_action = QAction(QIcon("assets/icons/report.png"), "Отчет", self)
        self.report_action.triggered.connect(self.generate_report)
        self.main_toolbar.addAction(self.report_action)
        
        self.print_action = QAction(QIcon("assets/icons/print.png"), "Печать", self)
        self.print_action.triggered.connect(self.print_report)
        self.main_toolbar.addAction(self.print_action)
        
        # Тулбар инструментов
        self.tools_toolbar = QToolBar("Инструменты")
        self.tools_toolbar.setObjectName("toolsToolbar")
        self.tools_toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(Qt.RightToolBarArea, self.tools_toolbar)
        
        # Кнопки тулбара инструментов
        self.oscilloscope_action = QAction(QIcon("assets/icons/oscilloscope.png"), "Осциллограф", self)
        self.oscilloscope_action.triggered.connect(self.open_oscilloscope)
        self.tools_toolbar.addAction(self.oscilloscope_action)
        
        self.scope_action = QAction(QIcon("assets/icons/scope.png"), "Сканирование", self)
        self.scope_action.triggered.connect(self.open_scope)
        self.tools_toolbar.addAction(self.scope_action)
        
        self.tools_toolbar.addSeparator()
        
        self.hex_editor_action = QAction(QIcon("assets/icons/hex.png"), "Hex редактор", self)
        self.hex_editor_action.triggered.connect(self.open_hex_editor)
        self.tools_toolbar.addAction(self.hex_editor_action)
        
        self.map_editor_action = QAction(QIcon("assets/icons/map_editor.png"), "Редактор карт", self)
        self.map_editor_action.triggered.connect(self.open_map_editor)
        self.tools_toolbar.addAction(self.map_editor_action)
        
    def load_styles(self):
        """Загрузка стилей"""
        # Загрузка стилей из файла
        style_file = "assets/styles/main.qss"
        if os.path.exists(style_file):
            try:
                with open(style_file, 'r', encoding='utf-8') as f:
                    style = f.read()
                self.setStyleSheet(style)
            except:
                # Запасной стиль
                self.setStyleSheet(self.get_default_style())
        else:
            self.setStyleSheet(self.get_default_style())
            
    def get_default_style(self):
        """Возвращает стиль по умолчанию"""
        return """
        QMainWindow {
            background-color: #2c3e50;
        }
        
        QStatusBar {
            background-color: #34495e;
            color: #ecf0f1;
            font-size: 11px;
        }
        
        QTabWidget::pane {
            border: 1px solid #34495e;
            background-color: #34495e;
            border-radius: 4px;
        }
        
        QTabBar::tab {
            background-color: #2c3e50;
            color: #bdc3c7;
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        
        QTabBar::tab:selected {
            background-color: #34495e;
            color: #ecf0f1;
            border-bottom: 2px solid #3498db;
        }
        
        QTabBar::tab:hover {
            background-color: #3b4f63;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 1px solid #34495e;
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        
        QPushButton {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #2980b9;
        }
        
        QPushButton:pressed {
            background-color: #1c5a7a;
        }
        
        QPushButton:disabled {
            background-color: #34495e;
            color: #7f8c8d;
        }
        
        QComboBox {
            background-color: #34495e;
            color: #ecf0f1;
            border: 1px solid #2c3e50;
            border-radius: 4px;
            padding: 5px;
        }
        
        QComboBox:hover {
            border: 1px solid #3498db;
        }
        
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #34495e;
            color: #ecf0f1;
            border: 1px solid #2c3e50;
            border-radius: 4px;
            padding: 5px;
        }
        
        QTableView, QTableWidget {
            background-color: #34495e;
            alternate-background-color: #2c3e50;
            color: #ecf0f1;
            gridline-color: #2c3e50;
            selection-background-color: #3498db;
        }
        
        QHeaderView::section {
            background-color: #2c3e50;
            color: #ecf0f1;
            padding: 5px;
            border: none;
        }
        
        QProgressBar {
            border: 1px solid #2c3e50;
            border-radius: 3px;
            text-align: center;
            background-color: #34495e;
        }
        
        QProgressBar::chunk {
            background-color: #3498db;
            border-radius: 2px;
        }
        """
        
    def setup_timers(self):
        """Настройка таймеров"""
        # Таймер обновления статуса
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # Обновление каждую секунду
        
        # Таймер обновления живых данных
        self.live_data_timer = QTimer()
        self.live_data_timer.timeout.connect(self.update_live_data)
        
        # Таймер сеанса
        self.session_timer = QTimer()
        self.session_timer.timeout.connect(self.update_session_time)
        self.session_start_time = QDateTime.currentDateTime()
        
    def setup_animation(self):
        """Настройка анимации"""
        # Анимация для индикатора состояния
        self.status_animation = QPropertyAnimation(self.status_indicator, b"opacity")
        self.status_animation.setDuration(1000)
        self.status_animation.setStartValue(0.3)
        self.status_animation.setEndValue(1.0)
        self.status_animation.setLoopCount(-1)
        self.status_animation.setEasingCurve(QEasingCurve.InOutSine)
        
    def setup_connections(self):
        """Настройка соединений между компонентами"""
        # Подключение сигналов от панели подключения
        self.connection_tab.connected.connect(self.on_device_connected)
        self.connection_tab.disconnected.connect(self.on_device_disconnected)
        self.connection_tab.connection_error.connect(self.on_connection_error)
        
        # Подключение сигналов от панели диагностики
        self.diagnostic_tab.diagnostic_started.connect(self.on_diagnostic_started)
        self.diagnostic_tab.diagnostic_completed.connect(self.on_diagnostic_completed)
        self.diagnostic_tab.progress_updated.connect(self.on_progress_updated)
        
        # Подключение сигналов от панели ошибок
        self.error_tab.errors_cleared.connect(self.on_errors_cleared)
        self.error_tab.error_selected.connect(self.on_error_selected)
        
        # Подключение сигналов от панели адаптации
        self.adaptation_tab.adaptation_performed.connect(self.on_adaptation_performed)
        
        # Подключение сигналов от панели отчетов
        self.reports_tab.report_generated.connect(self.on_report_generated)
        
        # Подключение внутренних сигналов
        self.connection_status_changed.connect(self.update_ui_connection_state)
        self.diagnostic_started.connect(self.on_diagnostic_started_internal)
        self.diagnostic_completed.connect(self.on_diagnostic_completed_internal)
        
    def load_settings(self):
        """Загрузка настроек"""
        # Загрузка геометрии сплиттера
        splitter_state = self.settings.value("splitter_state", QByteArray())
        if splitter_state:
            self.main_splitter.restoreState(splitter_state)
            
        # Загрузка последней выбранной модели
        last_model = self.settings.value("last_vehicle_model", "21236")
        index = self.vehicle_combo.findData(last_model)
        if index >= 0:
            self.vehicle_combo.setCurrentIndex(index)
            
        # Загрузка темы
        theme = self.settings.value("theme", "dark")
        self.change_theme(theme, save=False)
        
    def save_settings(self):
        """Сохранение настроек"""
        # Сохранение геометрии окна
        self.settings.setValue("window_geometry", self.saveGeometry())
        
        # Сохранение состояния сплиттера
        self.settings.setValue("splitter_state", self.main_splitter.saveState())
        
        # Сохранение последней модели
        if self.current_vehicle:
            self.settings.setValue("last_vehicle_model", self.current_vehicle)
            
        # Сохранение текущей темы
        self.settings.setValue("theme", self.current_theme)
        
    # ==================== Обработчики событий ====================
    
    def on_device_connected(self, device_info):
        """Обработка подключения устройства"""
        self.connection_status = True
        self.connection_status_changed.emit(True)
        
        # Обновление UI
        self.status_indicator.set_status("connected")
        self.status_label.setText("Подключено")
        self.connection_info.setText(f"Устройство: {device_info}")
        
        # Активация вкладок
        for i in range(1, self.tab_widget.count()):
            self.tab_widget.setTabEnabled(i, True)
            
        # Обновление кнопок
        self.connect_action.setEnabled(False)
        self.disconnect_action.setEnabled(True)
        
        # Запуск таймера сеанса
        self.session_start_time = QDateTime.currentDateTime()
        self.session_timer.start(1000)
        
        # Запись в лог
        self.logger.info(f"Устройство подключено: {device_info}")
        self.log_text.append(f"[{QDateTime.currentDateTime().toString('hh:mm:ss')}] Устройство подключено: {device_info}")
        
        # Старт анимации
        self.status_animation.start()
        
    def on_device_disconnected(self):
        """Обработка отключения устройства"""
        self.connection_status = False
        self.connection_status_changed.emit(False)
        
        # Обновление UI
        self.status_indicator.set_status("disconnected")
        self.status_label.setText("Отключено")
        self.connection_info.setText("Нет подключения")
        
        # Деактивация вкладок
        for i in range(1, self.tab_widget.count()):
            self.tab_widget.setTabEnabled(i, False)
            
        # Обновление кнопок
        self.connect_action.setEnabled(True)
        self.disconnect_action.setEnabled(False)
        
        # Остановка таймеров
        self.live_data_timer.stop()
        self.session_timer.stop()
        
        # Запись в лог
        self.logger.info("Устройство отключено")
        self.log_text.append(f"[{QDateTime.currentDateTime().toString('hh:mm:ss')}] Устройство отключено")
        
        # Остановка анимации
        self.status_animation.stop()
        
    def on_connection_error(self, error_message):
        """Обработка ошибки подключения"""
        QMessageBox.critical(self, "Ошибка подключения", error_message)
        self.logger.error(f"Ошибка подключения: {error_message}")
        self.log_text.append(f"[{QDateTime.currentDateTime().toString('hh:mm:ss')}] ОШИБКА: {error_message}")
        
    def on_diagnostic_started(self):
        """Обработка начала диагностики"""
        self.diagnostic_started.emit()
        
    def on_diagnostic_completed(self, results):
        """Обработка завершения диагностики"""
        self.diagnostic_results = results
        self.diagnostic_completed.emit(results)
        
        # Обновление индикаторов систем
        self.update_system_indicators(results)
        
    def on_progress_updated(self, value, message):
        """Обновление прогресса"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
        
        if value >= 100:
            self.progress_panel.setVisible(False)
            
    def on_errors_cleared(self):
        """Обработка очистки ошибок"""
        self.error_cleared.emit()
        
        # Обновление UI
        self.session_errors_label.setText("Ошибок: 0")
        
    def on_error_selected(self, error_code, description):
        """Обработка выбора ошибки"""
        # Показ подробной информации об ошибке
        self.show_error_details(error_code, description)
        
    def on_adaptation_performed(self, adaptation_type):
        """Обработка выполнения адаптации"""
        self.adaptation_performed.emit(adaptation_type)
        
        # Запись в лог
        self.logger.info(f"Выполнена адаптация: {adaptation_type}")
        self.log_text.append(f"[{QDateTime.currentDateTime().toString('hh:mm:ss')}] Адаптация: {adaptation_type}")
        
    def on_report_generated(self, report_path):
        """Обработка генерации отчета"""
        QMessageBox.information(self, "Отчет сгенерирован", 
                              f"Отчет сохранен в:\n{report_path}")
        
    def on_diagnostic_started_internal(self):
        """Внутренняя обработка начала диагностики"""
        self.progress_panel.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Начало диагностики...")
        
    def on_diagnostic_completed_internal(self, results):
        """Внутренняя обработка завершения диагностики"""
        # Обновление виджетов быстрого доступа
        if 'live_data' in results:
            self.update_quick_widgets(results['live_data'])
            
    # ==================== Методы UI ====================
    
    def update_ui_connection_state(self, connected):
        """Обновление состояния UI в зависимости от подключения"""
        # Обновление кнопок навигации
        for btn in self.nav_buttons.values():
            btn.setEnabled(connected)
            
        # Обновление кнопок быстрых действий
        for btn in self.quick_action_buttons.values():
            btn.setEnabled(connected)
            
    def update_system_indicators(self, results):
        """Обновление индикаторов систем"""
        # Здесь должна быть логика определения состояния систем
        # Временно устанавливаем все в нормальное состояние
        for indicator in self.system_indicators.values():
            indicator.set_state(True)  # Нормальное состояние
            
    def update_quick_widgets(self, live_data):
        """Обновление виджетов быстрого доступа"""
        if 'ENGINE_RPM' in live_data:
            self.tachometer.set_value(live_data['ENGINE_RPM']['value'])
            
        if 'VEHICLE_SPEED' in live_data:
            self.speedometer.set_value(live_data['VEHICLE_SPEED']['value'])
            
        if 'COOLANT_TEMP' in live_data:
            self.temp_gauge.set_value(live_data['COOLANT_TEMP']['value'])
            
    def update_status(self):
        """Обновление статус бара"""
        # Обновление информации о памяти
        import psutil
        memory = psutil.virtual_memory()
        self.memory_label.setText(f"Память: {memory.percent}%")
        
        # Обновление информации о CPU
        cpu_percent = psutil.cpu_percent()
        self.cpu_label.setText(f"CPU: {cpu_percent:.1f}%")
        
    def update_session_time(self):
        """Обновление времени сеанса"""
        elapsed = self.session_start_time.secsTo(QDateTime.currentDateTime())
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        seconds = elapsed % 60
        self.session_time_label.setText(f"Время: {hours:02d}:{minutes:02d}:{seconds:02d}")
        
    def update_live_data(self):
        """Обновление живых данных"""
        # Здесь должна быть логика обновления живых данных
        pass
        
    # ==================== Методы навигации ====================
    
    def quick_navigate(self, tab_id):
        """Быстрая навигация по вкладкам"""
        tab_map = {
            'engine_diag': 1,
            'abs_diag': 1,
            'airbag_diag': 1,
            'immo_diag': 1,
            'cluster_diag': 1,
            'ac_diag': 1,
        }
        
        if tab_id in tab_map:
            self.tab_widget.setCurrentIndex(tab_map[tab_id])
            # Дополнительная настройка вкладки
            if tab_id == 'engine_diag':
                self.diagnostic_tab.select_system('engine')
                
    def quick_connect(self):
        """Быстрое подключение"""
        # Использование последних настроек подключения
        last_port = self.settings.value("last_port", "")
        last_type = self.settings.value("last_connection_type", "bluetooth")
        
        if last_port:
            self.connection_tab.connect_with_params(last_type, last_port)
        else:
            self.tab_widget.setCurrentIndex(0)  # Переход на вкладку подключения
            
    def perform_quick_action(self, action_id):
        """Выполнение быстрого действия"""
        action_map = {
            'fault_emulation': self.open_fault_emulation,
            'sensor_calibration': self.open_sensor_calibration,
            'injector_test': self.open_injector_test,
            'coil_test': self.open_coil_test,
            'compression_test': self.open_compression_test,
            'reset_adaptations': self.reset_adaptations,
        }
        
        if action_id in action_map:
            action_map[action_id]()
            
    # ==================== Методы работы с вкладками ====================
    
    def close_tab(self, index):
        """Закрытие вкладки"""
        if index > 8:  # Пользовательские вкладки
            self.tab_widget.removeTab(index)
            
    def add_custom_tab(self):
        """Добавление пользовательской вкладки"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Новая вкладка")
        layout = QVBoxLayout(dialog)
        
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Название вкладки")
        
        type_combo = QComboBox()
        type_combo.addItems(["График", "Таблица", "Текст", "Настройки"])
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        
        layout.addWidget(QLabel("Название:"))
        layout.addWidget(name_edit)
        layout.addWidget(QLabel("Тип:"))
        layout.addWidget(type_combo)
        layout.addWidget(button_box)
        
        if dialog.exec() == QDialog.Accepted:
            tab_name = name_edit.text()
            if tab_name:
                # Создание новой вкладки
                new_tab = QWidget()
                new_tab.layout = QVBoxLayout(new_tab)
                new_tab.layout.addWidget(QLabel(f"Вкладка: {tab_name}"))
                self.tab_widget.addTab(new_tab, tab_name)
                
    # ==================== Методы меню ====================
    
    def new_session(self):
        """Новый сеанс диагностики"""
        reply = QMessageBox.question(self, "Новый сеанс",
                                   "Начать новый сеанс диагностики?\n"
                                   "Текущие данные будут потеряны.",
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Сброс всех данных
            self.diagnostic_tab.reset()
            self.live_data_tab.reset()
            self.error_tab.reset()
            self.reports_tab.reset()
            
            # Сброс виджетов
            self.tachometer.reset()
            self.speedometer.reset()
            self.temp_gauge.reset()
            
            # Сброс логов
            self.log_text.clear()
            
            # Сброс времени сеанса
            self.session_start_time = QDateTime.currentDateTime()
            
            self.logger.info("Начат новый сеанс диагностики")
            self.log_text.append(f"[{QDateTime.currentDateTime().toString('hh:mm:ss')}] Начат новый сеанс")
            
    def open_file(self):
        """Открытие файла"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть файл диагностики",
            "",
            "Файлы диагностики (*.ndf *.xml *.json);;Все файлы (*.*)"
        )
        
        if file_path:
            # Загрузка файла
            self.load_diagnostic_file(file_path)
            
    def save_file(self):
        """Сохранение файла"""
        # Реализация сохранения
        pass
        
    def save_file_as(self):
        """Сохранение файла как"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить файл диагностики",
            f"diagnostic_{QDateTime.currentDateTime().toString('yyyyMMdd_hhmmss')}.ndf",
            "Файлы диагностики (*.ndf);;XML файлы (*.xml);;JSON файлы (*.json)"
        )
        
        if file_path:
            # Сохранение файла
            self.save_diagnostic_file(file_path)
            
    def export_report(self, format_type):
        """Экспорт отчета"""
        # Реализация экспорта в разные форматы
        pass
        
    def print_report(self):
        """Печать отчета"""
        # Реализация печати
        pass
        
    def copy_data(self):
        """Копирование данных"""
        # Реализация копирования
        pass
        
    def toggle_toolbar(self, visible):
        """Переключение видимости тулбара"""
        self.main_toolbar.setVisible(visible)
        self.tools_toolbar.setVisible(visible)
        
    def toggle_statusbar(self, visible):
        """Переключение видимости статус бара"""
        self.status_bar.setVisible(visible)
        
    def toggle_fullscreen(self):
        """Переключение полноэкранного режима"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
            
    def quick_diagnostic(self):
        """Быстрая диагностика"""
        self.diagnostic_tab.quick_diagnostic()
        
    def full_diagnostic(self):
        """Полная диагностика"""
        self.diagnostic_tab.full_diagnostic()
        
    def system_diagnostic(self, system):
        """Диагностика конкретной системы"""
        self.diagnostic_tab.system_diagnostic(system)
        
    def clear_all_errors(self):
        """Очистка всех ошибок"""
        self.error_tab.clear_all_errors()
        
    def open_preferences(self):
        """Открытие настроек программы"""
        # Реализация диалога настроек
        pass
        
    def open_vehicle_settings(self):
        """Открытие настроек автомобиля"""
        # Реализация диалога настроек автомобиля
        pass
        
    def open_connection_settings(self):
        """Открытие настроек подключения"""
        # Реализация диалога настроек подключения
        pass
        
    def change_theme(self, theme, save=True):
        """Смена темы"""
        self.current_theme = theme
        
        if theme == "dark":
            qdarkstyle.load_stylesheet_pyqt5()
        elif theme == "light":
            # Загрузка светлой темы
            pass
        elif theme == "blue":
            # Загрузка синей темы
            pass
            
        if save:
            self.settings.setValue("theme", theme)
            
    def open_calibration(self):
        """Открытие калибровки"""
        self.tab_widget.setCurrentWidget(self.adaptation_tab)
        self.adaptation_tab.show_calibration()
        
    def open_adaptation(self):
        """Открытие адаптации"""
        self.tab_widget.setCurrentWidget(self.adaptation_tab)
        
    def open_coding(self):
        """Открытие кодирования"""
        # Реализация кодирования
        pass
        
    def open_flashing(self):
        """Открытие прошивки"""
        # Реализация прошивки
        pass
        
    def show_help(self):
        """Показать справку"""
        # Реализация справки
        pass
        
    def show_tutorial(self):
        """Показать обучение"""
        # Реализация обучения
        pass
        
    def check_for_updates(self):
        """Проверка обновлений"""
        # Реализация проверки обновлений
        pass
        
    def show_about(self):
        """Показать информацию о программе"""
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("О программе")
        about_dialog.setFixedSize(400, 300)
        
        layout = QVBoxLayout(about_dialog)
        
        # Заголовок
        title_label = QLabel("Chevrolet Niva Pro Diagnostic Suite")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Segoe UI", 16, QFont.Bold)
        title_label.setFont(title_font)
        
        # Версия
        version_label = QLabel("Версия 2.0 Professional")
        version_label.setAlignment(Qt.AlignCenter)
        
        # Описание
        desc_label = QLabel(
            "Профессиональное программное обеспечение\n"
            "для диагностики автомобилей Chevrolet Niva\n\n"
            "© 2024 Niva Diagnostic Systems\n"
            "Все права защищены"
        )
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        
        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(about_dialog.accept)
        
        layout.addWidget(title_label)
        layout.addWidget(version_label)
        layout.addStretch()
        layout.addWidget(desc_label)
        layout.addStretch()
        layout.addWidget(close_btn)
        
        about_dialog.exec()
        
    # ==================== Методы инструментов ====================
    
    def open_oscilloscope(self):
        """Открытие осциллографа"""
        self.tab_widget.setCurrentWidget(self.oscilloscope_tab)
        
    def open_scope(self):
        """Открытие сканирования"""
        # Реализация сканирования
        pass
        
    def open_hex_editor(self):
        """Открытие hex редактора"""
        # Реализация hex редактора
        pass
        
    def open_map_editor(self):
        """Открытие редактора карт"""
        self.tab_widget.setCurrentWidget(self.maps_tab)
        
    def open_fault_emulation(self):
        """Открытие эмуляции неисправностей"""
        # Реализация эмуляции
        pass
        
    def open_sensor_calibration(self):
        """Открытие калибровки датчиков"""
        self.open_calibration()
        
    def open_injector_test(self):
        """Открытие теста форсунок"""
        # Реализация теста форсунок
        pass
        
    def open_coil_test(self):
        """Открытие теста катушек"""
        # Реализация теста катушек
        pass
        
    def open_compression_test(self):
        """Открытие проверки компрессии"""
        # Реализация проверки компрессии
        pass
        
    def reset_adaptations(self):
        """Сброс адаптаций"""
        reply = QMessageBox.question(self, "Сброс адаптаций",
                                   "Вы уверены, что хотите сбросить все адаптации?\n"
                                   "Это действие может повлиять на работу двигателя.",
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.adaptation_tab.reset_all_adaptations()
            
    # ==================== Вспомогательные методы ====================
    
    def on_vehicle_changed(self, index):
        """Обработка изменения выбранного автомобиля"""
        self.current_vehicle = self.vehicle_combo.itemData(index)
        vehicle_name = self.vehicle_combo.itemText(index)
        self.vehicle_info.setText(f"Автомобиль: {vehicle_name}")
        
    def read_vin(self):
        """Чтение VIN автомобиля"""
        if not self.connection_status:
            QMessageBox.warning(self, "Ошибка", "Нет подключения к автомобилю")
            return
            
        # Реализация чтения VIN
        vin = "X9L21230012345678"  # Пример VIN
        self.vin_label.setText(f"VIN: {vin}")
        
    def start_diagnostic(self):
        """Запуск диагностики"""
        self.diagnostic_tab.start_diagnostic()
        
    def start_live_data(self):
        """Запуск отображения живых данных"""
        self.live_data_tab.start_monitoring()
        self.live_data_timer.start(100)  # Обновление каждые 100 мс
        
    def clear_errors(self):
        """Очистка ошибок"""
        self.error_tab.clear_errors()
        
    def show_graphs(self):
        """Показать графики"""
        self.live_data_tab.show_graphs()
        
    def generate_report(self):
        """Генерация отчета"""
        self.reports_tab.generate_report()
        
    def end_session(self):
        """Завершение сеанса"""
        reply = QMessageBox.question(self, "Завершение сеанса",
                                   "Завершить текущий сеанс диагностики?",
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Остановка всех процессов
            self.live_data_timer.stop()
            self.session_timer.stop()
            
            # Отключение от устройства
            if self.connection_status:
                self.connection_tab.disconnect_device()
                
            # Сброс данных
            self.new_session()
            
    def cancel_operation(self):
        """Отмена текущей операции"""
        # Реализация отмены
        pass
        
    def show_error_details(self, error_code, description):
        """Показать детали ошибки"""
        # Реализация отображения деталей ошибки
        pass
        
    def load_diagnostic_file(self, file_path):
        """Загрузка файла диагностики"""
        # Реализация загрузки файла
        pass
        
    def save_diagnostic_file(self, file_path):
        """Сохранение файла диагностики"""
        # Реализация сохранения файла
        pass
        
    # ==================== События ====================
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        # Сохранение настроек
        self.save_settings()
        
        # Проверка активных процессов
        if self.connection_status or self.live_data_timer.isActive():
            reply = QMessageBox.question(self, "Выход",
                                       "Имеются активные процессы.\n"
                                       "Вы уверены, что хотите выйти?",
                                       QMessageBox.Yes | QMessageBox.No,
                                       QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                # Остановка всех процессов
                self.end_session()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
            
    def resizeEvent(self, event):
        """Обработка изменения размера окна"""
        super().resizeEvent(event)
        # Дополнительная логика при изменении размера
        
    def keyPressEvent(self, event):
        """Обработка нажатия клавиш"""
        # Горячие клавиши
        if event.key() == Qt.Key_F5:
            self.quick_diagnostic()
        elif event.key() == Qt.Key_F6:
            self.full_diagnostic()
        elif event.key() == Qt.Key_F11:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key_F1:
            self.show_help()
        else:
            super().keyPressEvent(event)
            
    def showEvent(self, event):
        """Обработка показа окна"""
        super().showEvent(event)
        # Восстановление состояния
        if self.settings.value("maximized", False, type=bool):
            self.showMaximized()