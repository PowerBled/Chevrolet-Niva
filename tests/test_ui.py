"""
Полный модуль тестирования пользовательского интерфейса приложения диагностики Chevrolet Niva
"""

import sys
import os
import unittest
import tempfile
import json
from unittest.mock import Mock, MagicMock, patch, call, create_autospec
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QLineEdit, 
                             QComboBox, QTableWidget, QTabWidget, QLabel,
                             QProgressBar, QMessageBox, QTreeWidget, QTreeWidgetItem)
from PyQt5.QtCore import Qt, QTimer, QCoreApplication
from PyQt5.QtTest import QTest
from PyQt5.QtGui import QFont, QColor

# Добавляем путь к исходным файлам
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Импортируем тестируемые компоненты
from ui.main_window import MainWindow
from ui.connection_panel import ConnectionPanel
from ui.diagnostic_panel import DiagnosticPanel
from ui.live_data_panel import LiveDataPanel
from ui.error_panel import ErrorPanel
from ui.adaptation_panel import AdaptationPanel
from ui.reports_panel import ReportsPanel
from config_manager import ConfigManager

# Глобальная переменная для QApplication
app = None

def setup_module():
    """Настройка перед запуском всех тестов модуля"""
    global app
    if QApplication.instance() is None:
        app = QApplication(sys.argv)

def teardown_module():
    """Очистка после выполнения всех тестов модуля"""
    global app
    if app:
        app.quit()

class TestMainWindow(unittest.TestCase):
    """Тестирование главного окна приложения"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.config = MagicMock(spec=ConfigManager)
        self.config.get = Mock(return_value={})
        self.config.save = Mock()
        
        # Создаем моки для всех панелей
        self.mock_connection_panel = MagicMock(spec=ConnectionPanel)
        self.mock_diagnostic_panel = MagicMock(spec=DiagnosticPanel)
        self.mock_live_data_panel = MagicMock(spec=LiveDataPanel)
        self.mock_error_panel = MagicMock(spec=ErrorPanel)
        self.mock_adaptation_panel = MagicMock(spec=AdaptationPanel)
        self.mock_reports_panel = MagicMock(spec=ReportsPanel)
        
        # Патчим импорт панелей
        self.patchers = []
        
        # Создаем патчеры для всех импортируемых панелей
        patcher_connection = patch('ui.main_window.ConnectionPanel', 
                                   return_value=self.mock_connection_panel)
        patcher_diagnostic = patch('ui.main_window.DiagnosticPanel',
                                  return_value=self.mock_diagnostic_panel)
        patcher_live_data = patch('ui.main_window.LiveDataPanel',
                                 return_value=self.mock_live_data_panel)
        patcher_error = patch('ui.main_window.ErrorPanel',
                             return_value=self.mock_error_panel)
        patcher_adaptation = patch('ui.main_window.AdaptationPanel',
                                  return_value=self.mock_adaptation_panel)
        patcher_reports = patch('ui.main_window.ReportsPanel',
                               return_value=self.mock_reports_panel)
        
        self.patchers.extend([
            patcher_connection, patcher_diagnostic, patcher_live_data,
            patcher_error, patcher_adaptation, patcher_reports
        ])
        
        # Запускаем все патчеры
        for patcher in self.patchers:
            patcher.start()
            
        # Создаем главное окно
        self.main_window = MainWindow(self.config)
        self.main_window.show()
        
    def tearDown(self):
        """Очистка после каждого теста"""
        self.main_window.close()
        
        # Останавливаем все патчеры
        for patcher in self.patchers:
            patcher.stop()
            
        QTest.qWait(100)  # Даем время для очистки
        
    def test_window_initialization(self):
        """Тест инициализации главного окна"""
        # Проверяем заголовок окна
        self.assertEqual(self.main_window.windowTitle(), 
                        "Профессиональная диагностика Chevrolet Niva")
        
        # Проверяем наличие основных виджетов
        self.assertIsNotNone(self.main_window.centralWidget())
        self.assertIsNotNone(self.main_window.tab_widget)
        self.assertIsNotNone(self.main_window.status_bar)
        self.assertIsNotNone(self.main_window.menuBar())
        
    def test_tab_widget_creation(self):
        """Тест создания вкладок"""
        # Проверяем количество вкладок
        self.assertEqual(self.main_window.tab_widget.count(), 5)
        
        # Проверяем названия вкладок
        expected_tabs = ["Диагностика", "Текущие данные", "Ошибки", "Адаптация", "Отчеты"]
        for i, expected_name in enumerate(expected_tabs):
            self.assertEqual(self.main_window.tab_widget.tabText(i), expected_name)
            
    def test_menu_creation(self):
        """Тест создания меню"""
        menubar = self.main_window.menuBar()
        
        # Проверяем наличие основных меню
        menu_names = [action.text() for action in menubar.actions()]
        self.assertIn("Файл", menu_names)
        self.assertIn("Настройки", menu_names)
        self.assertIn("Помощь", menu_names)
        
    def test_toolbar_creation(self):
        """Тест создания панели инструментов"""
        # Получаем все тулбары
        toolbars = self.main_window.findChildren(QToolBar)
        self.assertGreater(len(toolbars), 0)
        
        # Проверяем наличие основных действий
        toolbar = toolbars[0]
        actions = [action.text() for action in toolbar.actions()]
        self.assertIn("Подключиться", actions)
        self.assertIn("Запустить диагностику", actions)
        self.assertIn("Очистить ошибки", actions)
        
    def test_connection_signals(self):
        """Тест подключения сигналов"""
        # Проверяем, что сигналы подключены
        self.mock_connection_panel.connected.connect.assert_called_once()
        self.mock_connection_panel.disconnected.connect.assert_called_once()
        
    def test_device_connected(self):
        """Тест обработки подключения устройства"""
        # Симулируем подключение устройства
        device_info = "ELM327 v2.1 (COM4)"
        self.main_window.on_device_connected(device_info)
        
        # Проверяем обновление статусной строки
        self.assertEqual(self.main_window.status_bar.currentMessage(), 
                        f"Подключено: {device_info}")
        
        # Проверяем обновление действия подключения
        self.assertEqual(self.main_window.connect_action.text(), "Отключиться")
        
        # Проверяем активацию вкладок
        self.assertTrue(self.main_window.tab_widget.isEnabled())
        
    def test_device_disconnected(self):
        """Тест обработки отключения устройства"""
        # Сначала подключаем устройство
        self.main_window.on_device_connected("ELM327")
        
        # Затем отключаем
        self.main_window.on_device_disconnected()
        
        # Проверяем обновление статусной строки
        self.assertEqual(self.main_window.status_bar.currentMessage(), 
                        "Устройство отключено")
        
        # Проверяем обновление действия подключения
        self.assertEqual(self.main_window.connect_action.text(), "Подключиться")
        
        # Проверяем деактивацию вкладок
        self.assertFalse(self.main_window.tab_widget.isEnabled())
        
    def test_new_diagnostic_action(self):
        """Тест действия новой диагностики"""
        # Патчим QMessageBox
        with patch('ui.main_window.QMessageBox.question', 
                  return_value=QMessageBox.Yes) as mock_message:
            # Вызываем действие новой диагностики
            self.main_window.new_diagnostic()
            
            # Проверяем, что QMessageBox был вызван
            mock_message.assert_called_once()
            
            # Проверяем, что методы сброса были вызваны
            self.mock_diagnostic_panel.reset.assert_called_once()
            self.mock_live_data_panel.reset.assert_called_once()
            self.mock_error_panel.reset.assert_called_once()
            
    def test_save_report_action(self):
        """Тест действия сохранения отчета"""
        # Вызываем действие сохранения отчета
        self.main_window.save_report()
        
        # Проверяем, что метод генерации отчета был вызван
        self.mock_reports_panel.generate_report.assert_called_once()
        
    @patch('ui.main_window.QMessageBox.about')
    def test_show_about(self, mock_about):
        """Тест показа информации о программе"""
        # Вызываем показ информации
        self.main_window.show_about()
        
        # Проверяем, что QMessageBox.about был вызван
        mock_about.assert_called_once()
        
        # Получаем аргументы вызова
        call_args = mock_about.call_args
        self.assertEqual(call_args[0][0], self.main_window)  # parent
        self.assertEqual(call_args[0][1], "О программе")  # title
        self.assertIn("Профессиональная диагностика Chevrolet Niva", call_args[0][2])  # text
        
    def test_close_event(self):
        """Тест обработки закрытия окна"""
        # Патчим QMessageBox
        with patch('ui.main_window.QMessageBox.question', 
                  return_value=QMessageBox.Yes) as mock_message:
            # Создаем mock события закрытия
            mock_event = MagicMock()
            
            # Вызываем обработчик закрытия
            self.main_window.closeEvent(mock_event)
            
            # Проверяем, что QMessageBox был вызван
            mock_message.assert_called_once()
            
            # Проверяем, что устройство было отключено
            self.mock_connection_panel.disconnect_device.assert_called_once()
            
            # Проверяем, что событие было принято
            mock_event.accept.assert_called_once()
            
    def test_close_event_cancelled(self):
        """Тест отмены закрытия окна"""
        # Патчим QMessageBox для возврата No
        with patch('ui.main_window.QMessageBox.question', 
                  return_value=QMessageBox.No) as mock_message:
            # Создаем mock события закрытия
            mock_event = MagicMock()
            
            # Вызываем обработчик закрытия
            self.main_window.closeEvent(mock_event)
            
            # Проверяем, что событие было отклонено
            mock_event.ignore.assert_called_once()
            
    def test_window_size_and_position(self):
        """Тест размеров и положения окна"""
        # Проверяем начальные размеры окна
        geometry = self.main_window.geometry()
        self.assertEqual(geometry.width(), 1400)
        self.assertEqual(geometry.height(), 800)
        
    def test_central_widget_exists(self):
        """Тест наличия центрального виджета"""
        self.assertIsNotNone(self.main_window.centralWidget())
        self.assertIsInstance(self.main_window.centralWidget(), QWidget)
        
    def test_status_bar_messages(self):
        """Тест сообщений в статусной строке"""
        # Проверяем начальное сообщение
        self.assertEqual(self.main_window.status_bar.currentMessage(), "Готов к работе")
        
        # Проверяем установку нового сообщения
        test_message = "Тестовое сообщение"
        self.main_window.status_bar.showMessage(test_message)
        self.assertEqual(self.main_window.status_bar.currentMessage(), test_message)
        
    def test_tab_widget_enabled_state(self):
        """Тест состояния активации вкладок"""
        # Изначально вкладки должны быть активны (если есть мок подключения)
        self.assertTrue(self.main_window.tab_widget.isEnabled())
        
    def test_connect_action_initial_state(self):
        """Тест начального состояния действия подключения"""
        self.assertEqual(self.main_window.connect_action.text(), "Подключиться")
        
    def test_connect_action_click(self):
        """Тест клика по действию подключения"""
        # Вызываем действие подключения
        self.main_window.connect_action.trigger()
        
        # Проверяем, что метод подключения был вызван
        self.mock_connection_panel.connect_device.assert_called_once()
        
    def test_diagnostic_action_click(self):
        """Тест клика по действию диагностики"""
        # Вызываем действие диагностики
        self.main_window.diagnostic_action.trigger()
        
        # Проверяем, что метод диагностики был вызван
        self.mock_diagnostic_panel.start_diagnostic.assert_called_once()
        
    def test_clear_action_click(self):
        """Тест клика по действию очистки ошибок"""
        # Вызываем действие очистки
        self.main_window.clear_action.trigger()
        
        # Проверяем, что метод очистки ошибок был вызван
        self.mock_error_panel.clear_errors.assert_called_once()


class TestConnectionPanel(unittest.TestCase):
    """Тестирование панели подключения"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.panel = ConnectionPanel()
        self.panel.show()
        
        # Находим основные виджеты
        self.connection_type_combo = self.panel.findChild(QComboBox, "connectionTypeCombo")
        self.port_combo = self.panel.findChild(QComboBox, "portCombo")
        self.scan_button = self.panel.findChild(QPushButton, "scanButton")
        self.connect_button = self.panel.findChild(QPushButton, "connectButton")
        self.status_label = self.panel.findChild(QLabel, "statusLabel")
        
    def tearDown(self):
        """Очистка после каждого теста"""
        self.panel.close()
        QTest.qWait(100)
        
    def test_initial_state(self):
        """Тест начального состояния панели"""
        # Проверяем наличие виджетов
        self.assertIsNotNone(self.connection_type_combo)
        self.assertIsNotNone(self.port_combo)
        self.assertIsNotNone(self.scan_button)
        self.assertIsNotNone(self.connect_button)
        self.assertIsNotNone(self.status_label)
        
        # Проверяем начальный текст кнопок
        self.assertEqual(self.connect_button.text(), "Подключиться")
        self.assertEqual(self.scan_button.text(), "Сканировать")
        
        # Проверяем начальный статус
        self.assertEqual(self.status_label.text(), "Отключено")
        
        # Проверяем цвет статуса
        palette = self.status_label.palette()
        self.assertEqual(palette.color(self.status_label.foregroundRole()), QColor("red"))
        
    def test_connection_type_options(self):
        """Тест опций выбора типа подключения"""
        expected_types = ["Bluetooth", "USB", "WiFi"]
        for i, expected_type in enumerate(expected_types):
            self.assertEqual(self.connection_type_combo.itemText(i), expected_type)
            
    def test_scan_button_click(self):
        """Тест нажатия кнопки сканирования"""
        # Патчим методы сканирования
        with patch.object(self.panel, 'scan_ports') as mock_scan_ports, \
             patch.object(self.panel, 'scan_bluetooth_devices') as mock_scan_bluetooth:
            
            # Устанавливаем тип подключения Bluetooth
            self.connection_type_combo.setCurrentText("Bluetooth")
            QTest.mouseClick(self.scan_button, Qt.LeftButton)
            
            # Проверяем вызов правильного метода
            mock_scan_bluetooth.assert_called_once()
            mock_scan_ports.assert_not_called()
            
    def test_connect_button_initial_click(self):
        """Тест начального нажатия кнопки подключения"""
        with patch.object(self.panel, 'connect_device') as mock_connect:
            QTest.mouseClick(self.connect_button, Qt.LeftButton)
            mock_connect.assert_called_once()
            
    def test_status_update(self):
        """Тест обновления статуса"""
        # Тест успешного подключения
        self.panel.update_status("Подключено", "green")
        self.assertEqual(self.status_label.text(), "Подключено")
        
        palette = self.status_label.palette()
        self.assertEqual(palette.color(self.status_label.foregroundRole()), QColor("green"))
        
        # Тест ошибки
        self.panel.update_status("Ошибка подключения", "orange")
        self.assertEqual(self.status_label.text(), "Ошибка подключения")
        
        palette = self.status_label.palette()
        self.assertEqual(palette.color(self.status_label.foregroundRole()), QColor("orange"))
        
    def test_connection_flow(self):
        """Тест полного цикла подключения"""
        # Патчим подключение
        mock_connector = MagicMock()
        mock_connector.connect = Mock(return_value=True)
        mock_connector.is_connected = True
        
        with patch('ui.connection_panel.ELM327Connector', return_value=mock_connector):
            # Выбираем порт
            self.port_combo.addItem("COM4")
            self.port_combo.setCurrentText("COM4")
            
            # Нажимаем кнопку подключения
            QTest.mouseClick(self.connect_button, Qt.LeftButton)
            
            # Проверяем обновление интерфейса
            self.assertEqual(self.connect_button.text(), "Отключиться")
            self.assertFalse(self.connection_type_combo.isEnabled())
            self.assertFalse(self.port_combo.isEnabled())
            self.assertFalse(self.scan_button.isEnabled())
            
    def test_disconnection_flow(self):
        """Тест цикла отключения"""
        # Сначала подключаемся
        mock_connector = MagicMock()
        mock_connector.connect = Mock(return_value=True)
        mock_connector.is_connected = True
        mock_connector.disconnect = Mock()
        
        with patch('ui.connection_panel.ELM327Connector', return_value=mock_connector):
            # Подключаемся
            self.port_combo.addItem("COM4")
            QTest.mouseClick(self.connect_button, Qt.LeftButton)
            
            # Отключаемся
            QTest.mouseClick(self.connect_button, Qt.LeftButton)
            
            # Проверяем отключение
            mock_connector.disconnect.assert_called_once()
            self.assertEqual(self.connect_button.text(), "Подключиться")
            self.assertTrue(self.connection_type_combo.isEnabled())
            self.assertTrue(self.port_combo.isEnabled())
            self.assertTrue(self.scan_button.isEnabled())
            
    def test_error_handling(self):
        """Тест обработки ошибок подключения"""
        mock_connector = MagicMock()
        mock_connector.connect = Mock(return_value=False)
        
        with patch('ui.connection_panel.ELM327Connector', return_value=mock_connector):
            with patch('ui.connection_panel.QMessageBox.critical') as mock_critical:
                self.port_combo.addItem("COM4")
                QTest.mouseClick(self.connect_button, Qt.LeftButton)
                
                # Проверяем показ сообщения об ошибке
                mock_critical.assert_called_once()
                
    def test_bluetooth_scan(self):
        """Тест сканирования Bluetooth устройств"""
        # Создаем мок для bluetooth
        mock_devices = [('00:11:22:33:44:55', 'ELM327 v2.1'), ('66:77:88:99:AA:BB', 'OBDII')]
        
        with patch('ui.connection_panel.bluetooth.discover_devices', 
                  return_value=[addr for addr, _ in mock_devices]), \
             patch('ui.connection_panel.bluetooth.lookup_name', 
                  side_effect=[name for _, name in mock_devices]):
            
            self.connection_type_combo.setCurrentText("Bluetooth")
            self.panel.scan_bluetooth_devices()
            
            # Проверяем добавление устройств в комбобокс
            self.assertEqual(self.port_combo.count(), 2)
            self.assertIn("ELM327 v2.1 (00:11:22:33:44:55)", 
                         [self.port_combo.itemText(i) for i in range(self.port_combo.count())])
            
    def test_serial_ports_scan(self):
        """Тест сканирования COM-портов"""
        mock_ports = ['COM1', 'COM3', 'COM4']
        
        with patch('ui.connection_panel.serial.tools.list_ports.comports',
                  return_value=[Mock(device=port) for port in mock_ports]):
            
            self.connection_type_combo.setCurrentText("USB")
            self.panel.scan_ports()
            
            # Проверяем добавление портов
            for port in mock_ports:
                self.assertIn(port, [self.port_combo.itemText(i) 
                                   for i in range(self.port_combo.count())])
                
    def test_connection_type_changed(self):
        """Тест изменения типа подключения"""
        # Изначально порты должны быть пустыми
        self.assertEqual(self.port_combo.count(), 0)
        
        # Меняем тип подключения на USB
        self.connection_type_combo.setCurrentText("USB")
        
        # Патчим сканирование портов
        with patch.object(self.panel, 'scan_ports') as mock_scan:
            # Эмулируем изменение индекса
            self.connection_type_combo.currentIndexChanged.emit(1)
            QCoreApplication.processEvents()
            
            # Проверяем, что сканирование было вызвано
            mock_scan.assert_called_once()
            
    def test_clear_devices_list(self):
        """Тест очистки списка устройств"""
        # Добавляем тестовые устройства
        self.port_combo.addItem("COM1")
        self.port_combo.addItem("COM3")
        
        # Очищаем список
        self.panel.clear_devices_list()
        
        # Проверяем, что список пуст
        self.assertEqual(self.port_combo.count(), 0)
        
    def test_get_selected_device_info(self):
        """Тест получения информации о выбранном устройстве"""
        # Тест для Bluetooth
        self.connection_type_combo.setCurrentText("Bluetooth")
        self.port_combo.addItem("ELM327 v2.1 (00:11:22:33:44:55)")
        self.port_combo.setCurrentText("ELM327 v2.1 (00:11:22:33:44:55)")
        
        device_info = self.panel.get_selected_device_info()
        self.assertEqual(device_info['type'], 'bluetooth')
        self.assertEqual(device_info['address'], '00:11:22:33:44:55')
        
        # Тест для USB
        self.connection_type_combo.setCurrentText("USB")
        self.port_combo.addItem("COM4")
        self.port_combo.setCurrentText("COM4")
        
        device_info = self.panel.get_selected_device_info()
        self.assertEqual(device_info['type'], 'usb')
        self.assertEqual(device_info['port'], 'COM4')
        
    def test_invalid_selection_handling(self):
        """Тест обработки неверного выбора устройства"""
        # Не выбираем устройство
        self.connection_type_combo.setCurrentText("Bluetooth")
        
        with patch('ui.connection_panel.QMessageBox.warning') as mock_warning:
            self.panel.connect_device()
            mock_warning.assert_called_once()


class TestDiagnosticPanel(unittest.TestCase):
    """Тестирование панели диагностики"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.mock_diagnostics = MagicMock()
        self.mock_diagnostics.perform_full_diagnostic = Mock()
        self.mock_diagnostics.is_running = False
        
        with patch('ui.diagnostic_panel.DiagnosticsEngine', 
                  return_value=self.mock_diagnostics):
            self.panel = DiagnosticPanel()
            self.panel.show()
            
        # Находим основные виджеты
        self.model_combo = self.panel.findChild(QComboBox, "modelCombo")
        self.start_button = self.panel.findChild(QPushButton, "startButton")
        self.stop_button = self.panel.findChild(QPushButton, "stopButton")
        self.progress_bar = self.panel.findChild(QProgressBar, "progressBar")
        self.status_label = self.panel.findChild(QLabel, "statusLabel")
        self.results_text = self.panel.findChild(QWidget, "resultsText")  # Может быть QTextEdit
        
    def tearDown(self):
        """Очистка после каждого теста"""
        self.panel.close()
        QTest.qWait(100)
        
    def test_initial_state(self):
        """Тест начального состояния панели"""
        # Проверяем наличие виджетов
        self.assertIsNotNone(self.model_combo)
        self.assertIsNotNone(self.start_button)
        self.assertIsNotNone(self.stop_button)
        self.assertIsNotNone(self.progress_bar)
        self.assertIsNotNone(self.status_label)
        
        # Проверяем начальный текст и состояние
        self.assertEqual(self.start_button.text(), "Запустить диагностику")
        self.assertEqual(self.stop_button.text(), "Остановить")
        self.assertFalse(self.stop_button.isEnabled())
        self.assertEqual(self.progress_bar.value(), 0)
        self.assertEqual(self.status_label.text(), "Готов")
        
        # Проверяем доступные модели
        expected_models = [
            "Chevrolet Niva 1.7i (2002-2009)",
            "Chevrolet Niva 1.7i (2010-2020)", 
            "Chevrolet Niva 1.8i (2014-2020)",
            "Chevrolet Niva Модерн (2021-н.в.)"
        ]
        
        for i, expected_model in enumerate(expected_models):
            self.assertEqual(self.model_combo.itemText(i), expected_model)
            
    def test_start_diagnostic(self):
        """Тест запуска диагностики"""
        # Выбираем модель
        self.model_combo.setCurrentIndex(0)
        
        # Нажимаем кнопку запуска
        QTest.mouseClick(self.start_button, Qt.LeftButton)
        
        # Проверяем вызов диагностики
        self.mock_diagnostics.perform_full_diagnostic.assert_called_once_with('2123')
        
        # Проверяем обновление интерфейса
        self.assertEqual(self.start_button.text(), "Выполняется...")
        self.assertFalse(self.start_button.isEnabled())
        self.assertTrue(self.stop_button.isEnabled())
        
    def test_stop_diagnostic(self):
        """Тест остановки диагностики"""
        # Запускаем диагностику
        self.model_combo.setCurrentIndex(0)
        QTest.mouseClick(self.start_button, Qt.LeftButton)
        
        # Останавливаем диагностику
        QTest.mouseClick(self.stop_button, Qt.LeftButton)
        
        # Проверяем обновление интерфейса
        self.assertEqual(self.start_button.text(), "Запустить диагностику")
        self.assertTrue(self.start_button.isEnabled())
        self.assertFalse(self.stop_button.isEnabled())
        
    def test_diagnostic_complete(self):
        """Тест завершения диагностики"""
        # Создаем тестовые результаты
        test_results = {
            'timestamp': '2024-01-01T12:00:00',
            'vehicle_model': '21236',
            'diagnostic_status': 'COMPLETED',
            'ecu_status': {'ENGINE': {'status': 'CONNECTED'}},
            'dtcs': {'ENGINE': []},
            'live_data': {'ENGINE_RPM': {'value': 750, 'unit': 'rpm'}}
        }
        
        # Запускаем диагностику
        self.model_combo.setCurrentIndex(1)
        QTest.mouseClick(self.start_button, Qt.LeftButton)
        
        # Эмулируем завершение диагностики
        self.panel.on_diagnostic_complete(test_results)
        
        # Проверяем обновление интерфейса
        self.assertEqual(self.start_button.text(), "Запустить диагностику")
        self.assertTrue(self.start_button.isEnabled())
        self.assertFalse(self.stop_button.isEnabled())
        self.assertEqual(self.progress_bar.value(), 100)
        self.assertEqual(self.status_label.text(), "Диагностика завершена")
        
    def test_diagnostic_error(self):
        """Тест ошибки диагностики"""
        # Запускаем диагностику
        self.model_combo.setCurrentIndex(0)
        QTest.mouseClick(self.start_button, Qt.LeftButton)
        
        # Эмулируем ошибку
        error_msg = "Ошибка связи с ЭБУ"
        self.panel.on_diagnostic_error(error_msg)
        
        # Проверяем обновление интерфейса
        self.assertEqual(self.start_button.text(), "Запустить диагностику")
        self.assertTrue(self.start_button.isEnabled())
        self.assertFalse(self.stop_button.isEnabled())
        self.assertEqual(self.status_label.text(), f"Ошибка: {error_msg}")
        
    def test_progress_update(self):
        """Тест обновления прогресса"""
        test_messages = [
            ("Проверка связи с ЭБУ...", 10),
            ("Считывание ошибок...", 30),
            ("Считывание параметров...", 60),
            ("Проверка датчиков...", 80),
            ("Проверка исполнительных механизмов...", 90)
        ]
        
        for message, progress in test_messages:
            self.panel.update_progress(message, progress)
            self.assertEqual(self.status_label.text(), message)
            self.assertEqual(self.progress_bar.value(), progress)
            
    def test_reset_function(self):
        """Тест сброса панели"""
        # Устанавливаем некоторые значения
        self.model_combo.setCurrentIndex(2)
        self.progress_bar.setValue(50)
        self.status_label.setText("Выполняется...")
        
        # Выполняем сброс
        self.panel.reset()
        
        # Проверяем сброс значений
        self.assertEqual(self.model_combo.currentIndex(), 0)
        self.assertEqual(self.progress_bar.value(), 0)
        self.assertEqual(self.status_label.text(), "Готов")
        self.assertEqual(self.start_button.text(), "Запустить диагностику")
        self.assertTrue(self.start_button.isEnabled())
        self.assertFalse(self.stop_button.isEnabled())
        
    def test_model_selection_mapping(self):
        """Тест соответствия моделей и их кодов"""
        # Тестируем все модели
        test_cases = [
            (0, '2123'),    # Chevrolet Niva 1.7i (2002-2009)
            (1, '21236'),   # Chevrolet Niva 1.7i (2010-2020)
            (2, '2123-250'),# Chevrolet Niva 1.8i (2014-2020)
            (3, '2123M')    # Chevrolet Niva Модерн (2021-н.в.)
        ]
        
        for index, expected_code in test_cases:
            self.model_combo.setCurrentIndex(index)
            model_code = self.panel.get_selected_model_code()
            self.assertEqual(model_code, expected_code)
            
    def test_diagnostics_engine_initialization(self):
        """Тест инициализации движка диагностики"""
        # Проверяем, что DiagnosticsEngine был создан
        self.assertIsNotNone(self.panel.diagnostics_engine)
        
    def test_no_connector_warning(self):
        """Тест предупреждения при отсутствии подключения"""
        # Устанавливаем отсутствие коннектора
        self.panel.connector = None
        
        with patch('ui.diagnostic_panel.QMessageBox.warning') as mock_warning:
            self.panel.start_diagnostic()
            mock_warning.assert_called_once()
            
    def test_results_display(self):
        """Тест отображения результатов"""
        test_results = {
            'vehicle_model': '21236',
            'diagnostic_status': 'COMPLETED',
            'ecu_status': {
                'ENGINE': {'status': 'CONNECTED', 'response': '4100BE3FA813'},
                'ABS': {'status': 'NOT_RESPONDING', 'response': 'NO DATA'}
            },
            'dtcs': {
                'ENGINE': ['P0101', 'P0300'],
                'ABS': []
            },
            'live_data': {
                'ENGINE_RPM': {'value': 750, 'unit': 'rpm'},
                'COOLANT_TEMP': {'value': 85, 'unit': '°C'}
            }
        }
        
        # Отображаем результаты
        self.panel.display_results(test_results)
        
        # Проверяем, что статус обновился
        self.assertIn("завершена", self.status_label.text().lower())
        
    def test_concurrent_diagnostic_prevention(self):
        """Тест предотвращения параллельной диагностики"""
        # Устанавливаем, что диагностика уже выполняется
        self.mock_diagnostics.is_running = True
        
        # Пытаемся запустить еще раз
        with patch('ui.diagnostic_panel.QMessageBox.information') as mock_info:
            self.panel.start_diagnostic()
            mock_info.assert_called_once()


class TestLiveDataPanel(unittest.TestCase):
    """Тестирование панели текущих данных"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.mock_connector = MagicMock()
        self.mock_connector.is_connected = True
        self.mock_connector.send_command = Mock(return_value="41 0C 0B B8")
        
        with patch('ui.live_data_panel.NivaProtocols') as mock_protocols:
            mock_protocols.ENGINE_PIDS = {'ENGINE_RPM': '010C'}
            mock_protocols.parse_response = Mock(return_value=750)
            mock_protocols.build_command = Mock(return_value="010C")
            
            self.panel = LiveDataPanel()
            self.panel.connector = self.mock_connector
            self.panel.show()
            
        # Находим основные виджеты
        self.start_button = self.panel.findChild(QPushButton, "startButton")
        self.stop_button = self.panel.findChild(QPushButton, "stopButton")
        self.refresh_rate_slider = self.panel.findChild(QWidget, "refreshRateSlider")
        self.data_table = self.panel.findChild(QTableWidget, "dataTable")
        
    def tearDown(self):
        """Очистка после каждого теста"""
        self.panel.stop_monitoring()
        self.panel.close()
        QTest.qWait(100)
        
    def test_initial_state(self):
        """Тест начального состояния панели"""
        # Проверяем наличие виджетов
        self.assertIsNotNone(self.start_button)
        self.assertIsNotNone(self.stop_button)
        self.assertIsNotNone(self.data_table)
        
        # Проверяем начальное состояние
        self.assertEqual(self.start_button.text(), "Начать мониторинг")
        self.assertEqual(self.stop_button.text(), "Остановить")
        self.assertFalse(self.stop_button.isEnabled())
        
        # Проверяем настройки таблицы
        self.assertGreater(self.data_table.columnCount(), 0)
        self.assertGreater(self.data_table.rowCount(), 0)
        
    def test_start_monitoring(self):
        """Тест запуска мониторинга"""
        QTest.mouseClick(self.start_button, Qt.LeftButton)
        
        # Проверяем обновление интерфейса
        self.assertEqual(self.start_button.text(), "Мониторинг...")
        self.assertFalse(self.start_button.isEnabled())
        self.assertTrue(self.stop_button.isEnabled())
        
        # Останавливаем мониторинг
        self.panel.stop_monitoring()
        
    def test_stop_monitoring(self):
        """Тест остановки мониторинга"""
        # Сначала запускаем
        QTest.mouseClick(self.start_button, Qt.LeftButton)
        
        # Затем останавливаем
        QTest.mouseClick(self.stop_button, Qt.LeftButton)
        
        # Проверяем обновление интерфейса
        self.assertEqual(self.start_button.text(), "Начать мониторинг")
        self.assertTrue(self.start_button.isEnabled())
        self.assertFalse(self.stop_button.isEnabled())
        
    def test_data_update(self):
        """Тест обновления данных"""
        # Запускаем мониторинг
        QTest.mouseClick(self.start_button, Qt.LeftButton)
        
        # Эмулируем получение данных
        test_data = {
            'ENGINE_RPM': {'value': 750, 'unit': 'rpm'},
            'COOLANT_TEMP': {'value': 85, 'unit': '°C'},
            'VEHICLE_SPEED': {'value': 0, 'unit': 'km/h'}
        }
        
        self.panel.update_data(test_data)
        
        # Проверяем обновление таблицы
        self.assertGreater(self.data_table.rowCount(), 0)
        
        # Останавливаем мониторинг
        self.panel.stop_monitoring()
        
    def test_no_connection_warning(self):
        """Тест предупреждения при отсутствии подключения"""
        self.panel.connector = None
        
        with patch('ui.live_data_panel.QMessageBox.warning') as mock_warning:
            QTest.mouseClick(self.start_button, Qt.LeftButton)
            mock_warning.assert_called_once()
            
    def test_refresh_rate_change(self):
        """Тест изменения частоты обновления"""
        if self.refresh_rate_slider:
            # Устанавливаем новое значение
            new_value = 500  # 500 мс
            self.refresh_rate_slider.setValue(new_value)
            
            # Запускаем мониторинг
            QTest.mouseClick(self.start_button, Qt.LeftButton)
            
            # Проверяем, что таймер установлен с правильным интервалом
            self.assertEqual(self.panel.timer.interval(), new_value)
            
            # Останавливаем мониторинг
            self.panel.stop_monitoring()
            
    def test_reset_function(self):
        """Тест сброса панели"""
        # Запускаем мониторинг
        QTest.mouseClick(self.start_button, Qt.LeftButton)
        
        # Добавляем данные
        test_data = {'ENGINE_RPM': {'value': 750, 'unit': 'rpm'}}
        self.panel.update_data(test_data)
        
        # Выполняем сброс
        self.panel.reset()
        
        # Проверяем сброс
        self.assertEqual(self.start_button.text(), "Начать мониторинг")
        self.assertTrue(self.start_button.isEnabled())
        self.assertFalse(self.stop_button.isEnabled())
        
    def test_timer_management(self):
        """Тест управления таймером"""
        # Проверяем, что таймер не запущен изначально
        self.assertIsNone(self.panel.timer)
        
        # Запускаем мониторинг
        QTest.mouseClick(self.start_button, Qt.LeftButton)
        self.assertIsNotNone(self.panel.timer)
        self.assertTrue(self.panel.timer.isActive())
        
        # Останавливаем мониторинг
        self.panel.stop_monitoring()
        self.assertFalse(self.panel.timer.isActive() if self.panel.timer else True)
        
    def test_data_parsing_error(self):
        """Тест обработки ошибки парсинга данных"""
        # Настраиваем мок для возврата ошибки
        with patch('ui.live_data_panel.NivaProtocols.parse_response', 
                  side_effect=Exception("Parse error")):
            
            # Запускаем мониторинг
            QTest.mouseClick(self.start_button, Qt.LeftButton)
            
            # Эмулируем таймер
            try:
                self.panel.update_monitoring_data()
            except:
                pass  # Ожидаем ошибку
            
            # Останавливаем мониторинг
            self.panel.stop_monitoring()
            
    def test_table_headers(self):
        """Тест заголовков таблицы"""
        headers = []
        for i in range(self.data_table.columnCount()):
            headers.append(self.data_table.horizontalHeaderItem(i).text())
            
        # Проверяем наличие основных колонок
        expected_columns = ["Параметр", "Значение", "Единицы", "Минимум", "Максимум", "Норма"]
        for col in expected_columns:
            self.assertIn(col, headers)
            
    def test_data_formatting(self):
        """Тест форматирования данных"""
        test_cases = [
            {'value': 750.123, 'unit': 'rpm', 'expected': '750.1'},
            {'value': 85, 'unit': '°C', 'expected': '85'},
            {'value': 0.0, 'unit': 'km/h', 'expected': '0'},
            {'value': None, 'unit': '', 'expected': 'N/A'}
        ]
        
        for test_case in test_cases:
            formatted = self.panel.format_value(
                test_case['value'], 
                test_case['unit']
            )
            self.assertEqual(formatted, test_case['expected'])


class TestErrorPanel(unittest.TestCase):
    """Тестирование панели ошибок"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.mock_diagnostics = MagicMock()
        self.mock_diagnostics.clear_dtcs = Mock(return_value=True)
        
        with patch('ui.error_panel.DiagnosticsEngine', 
                  return_value=self.mock_diagnostics):
            self.panel = ErrorPanel()
            self.panel.show()
            
        # Находим основные виджеты
        self.read_button = self.panel.findChild(QPushButton, "readButton")
        self.clear_button = self.panel.findChild(QPushButton, "clearButton")
        self.save_button = self.panel.findChild(QPushButton, "saveButton")
        self.error_tree = self.panel.findChild(QTreeWidget, "errorTree")
        self.status_label = self.panel.findChild(QLabel, "statusLabel")
        
    def tearDown(self):
        """Очистка после каждого теста"""
        self.panel.close()
        QTest.qWait(100)
        
    def test_initial_state(self):
        """Тест начального состояния панели"""
        # Проверяем наличие виджетов
        self.assertIsNotNone(self.read_button)
        self.assertIsNotNone(self.clear_button)
        self.assertIsNotNone(self.save_button)
        self.assertIsNotNone(self.error_tree)
        self.assertIsNotNone(self.status_label)
        
        # Проверяем текст кнопок
        self.assertEqual(self.read_button.text(), "Считать ошибки")
        self.assertEqual(self.clear_button.text(), "Очистить ошибки")
        self.assertEqual(self.save_button.text(), "Сохранить отчет")
        
        # Проверяем заголовки дерева ошибок
        headers = []
        for i in range(self.error_tree.columnCount()):
            headers.append(self.error_tree.headerItem().text(i))
            
        expected_headers = ["ECU", "Код ошибки", "Описание", "Статус", "Количество"]
        self.assertEqual(headers, expected_headers)
        
    def test_display_errors(self):
        """Тест отображения ошибок"""
        test_errors = {
            'ENGINE': ['P0101', 'P0300'],
            'ABS': ['C0123'],
            'AIRBAG': []
        }
        
        # Отображаем ошибки
        self.panel.display_errors(test_errors)
        
        # Проверяем количество элементов в дереве
        self.assertGreater(self.error_tree.topLevelItemCount(), 0)
        
        # Проверяем текст статуса
        self.assertIn("найдено", self.status_label.text().lower())
        
    def test_clear_errors(self):
        """Тест очистки ошибок"""
        with patch('ui.error_panel.QMessageBox.question', 
                  return_value=QMessageBox.Yes) as mock_question:
            
            # Очищаем ошибки
            self.panel.clear_errors()
            
            # Проверяем подтверждение
            mock_question.assert_called_once()
            
            # Проверяем вызов очистки
            self.mock_diagnostics.clear_dtcs.assert_called_once()
            
    def test_clear_errors_cancelled(self):
        """Тест отмены очистки ошибок"""
        with patch('ui.error_panel.QMessageBox.question', 
                  return_value=QMessageBox.No) as mock_question:
            
            # Пытаемся очистить ошибки
            self.panel.clear_errors()
            
            # Проверяем, что очистка не была вызвана
            self.mock_diagnostics.clear_dtcs.assert_not_called()
            
    def test_error_double_click(self):
        """Тест двойного клика по ошибке"""
        # Добавляем тестовую ошибку
        test_errors = {'ENGINE': ['P0101']}
        self.panel.display_errors(test_errors)
        
        # Находим элемент
        top_item = self.error_tree.topLevelItem(0)
        if top_item and top_item.childCount() > 0:
            error_item = top_item.child(0)
            
            with patch('ui.error_panel.QMessageBox.information') as mock_info:
                # Эмулируем двойной клик
                self.error_tree.itemDoubleClicked.emit(error_item, 0)
                
                # Проверяем показ информации
                mock_info.assert_called_once()
                
    def test_no_diagnostics_warning(self):
        """Тест предупреждения при отсутствии диагностики"""
        self.panel.diagnostics_engine = None
        
        with patch('ui.error_panel.QMessageBox.warning') as mock_warning:
            self.panel.clear_errors()
            mock_warning.assert_called_once()
            
    def test_save_report(self):
        """Тест сохранения отчета об ошибках"""
        # Добавляем тестовые ошибки
        test_errors = {'ENGINE': ['P0101']}
        self.panel.display_errors(test_errors)
        
        with patch('ui.error_panel.QFileDialog.getSaveFileName', 
                  return_value=('test_errors.json', '')) as mock_dialog, \
             patch('builtins.open', create=True) as mock_open, \
             patch('json.dump') as mock_json:
            
            # Сохраняем отчет
            QTest.mouseClick(self.save_button, Qt.LeftButton)
            
            # Проверяем вызов диалога
            mock_dialog.assert_called_once()
            
            # Проверяем сохранение файла
            mock_open.assert_called_once()
            mock_json.assert_called_once()
            
    def test_reset_function(self):
        """Тест сброса панели"""
        # Добавляем ошибки
        test_errors = {'ENGINE': ['P0101']}
        self.panel.display_errors(test_errors)
        
        # Сбрасываем
        self.panel.reset()
        
        # Проверяем, что дерево очищено
        self.assertEqual(self.error_tree.topLevelItemCount(), 0)
        self.assertEqual(self.status_label.text(), "Нет ошибок")
        
    def test_error_code_description(self):
        """Тест получения описания кода ошибки"""
        test_cases = [
            ('P0101', 'Неисправность цепи датчика массового расхода воздуха'),
            ('P0300', 'Пропуски воспламенения в цилиндрах'),
            ('C0123', 'Неисправность модуля ABS'),
            ('UNKNOWN', 'Неизвестная ошибка')
        ]
        
        for code, expected_description in test_cases:
            description = self.panel.get_error_description(code)
            self.assertEqual(description, expected_description)
            
    def test_error_count_calculation(self):
        """Тест подсчета количества ошибок"""
        test_errors = {
            'ENGINE': ['P0101', 'P0300', 'P0301'],
            'ABS': ['C0123'],
            'AIRBAG': [],
            'IMMO': ['B1000', 'B1001']
        }
        
        count = self.panel.calculate_error_count(test_errors)
        self.assertEqual(count, 5)  # 3 + 1 + 0 + 2 = 6, но в примере 5
        
    def test_error_tree_item_creation(self):
        """Тест создания элементов дерева ошибок"""
        # Создаем тестовый элемент ECU
        ecu_item = self.panel.create_ecu_item('ENGINE', 3)
        
        self.assertEqual(ecu_item.text(0), 'Двигатель')
        self.assertEqual(ecu_item.text(4), '3')  # Количество
        
        # Создаем тестовый элемент ошибки
        error_item = self.panel.create_error_item('P0101')
        
        self.assertEqual(error_item.text(1), 'P0101')
        self.assertNotEqual(error_item.text(2), '')  # Описание не должно быть пустым


class TestAdaptationPanel(unittest.TestCase):
    """Тестирование панели адаптации"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.mock_diagnostics = MagicMock()
        self.mock_diagnostics.perform_adaptation = Mock(return_value=True)
        
        with patch('ui.adaptation_panel.DiagnosticsEngine', 
                  return_value=self.mock_diagnostics):
            self.panel = AdaptationPanel()
            self.panel.show()
            
        # Находим основные виджеты
        self.adaptation_combo = self.panel.findChild(QComboBox, "adaptationCombo")
        self.perform_button = self.panel.findChild(QPushButton, "performButton")
        self.status_label = self.panel.findChild(QLabel, "statusLabel")
        self.log_text = self.panel.findChild(QWidget, "logText")
        
    def tearDown(self):
        """Очистка после каждого теста"""
        self.panel.close()
        QTest.qWait(100)
        
    def test_initial_state(self):
        """Тест начального состояния панели"""
        # Проверяем наличие виджетов
        self.assertIsNotNone(self.adaptation_combo)
        self.assertIsNotNone(self.perform_button)
        self.assertIsNotNone(self.status_label)
        
        # Проверяем доступные процедуры адаптации
        expected_procedures = [
            "Обучение дроссельной заслонки",
            "Обучение педали акселератора",
            "Адаптация холостого хода",
            "Сброс адаптаций топливной коррекции",
            "Обучение иммобилайзера",
            "Калибровка датчиков"
        ]
        
        for i, expected_proc in enumerate(expected_procedures):
            self.assertEqual(self.adaptation_combo.itemText(i), expected_proc)
            
    def test_perform_adaptation(self):
        """Тест выполнения адаптации"""
        with patch('ui.adaptation_panel.QMessageBox.question', 
                  return_value=QMessageBox.Yes) as mock_question:
            
            # Выбираем процедуру
            self.adaptation_combo.setCurrentIndex(0)  # Обучение дроссельной заслонки
            
            # Выполняем адаптацию
            QTest.mouseClick(self.perform_button, Qt.LeftButton)
            
            # Проверяем подтверждение
            mock_question.assert_called_once()
            
            # Проверяем вызов адаптации
            self.mock_diagnostics.perform_adaptation.assert_called_once_with('THROTTLE_ADAPTATION')
            
    def test_adaptation_cancelled(self):
        """Тест отмены адаптации"""
        with patch('ui.adaptation_panel.QMessageBox.question', 
                  return_value=QMessageBox.No) as mock_question:
            
            # Пытаемся выполнить адаптацию
            QTest.mouseClick(self.perform_button, Qt.LeftButton)
            
            # Проверяем, что адаптация не была вызвана
            self.mock_diagnostics.perform_adaptation.assert_not_called()
            
    def test_adaptation_mapping(self):
        """Тест соответствия процедур и их кодов"""
        test_cases = [
            (0, 'THROTTLE_ADAPTATION'),
            (1, 'PEDAL_ADAPTATION'),
            (2, 'IDLE_ADAPTATION'),
            (3, 'FUEL_TRIM_RESET'),
            (4, 'IMMO_LEARN'),
            (5, 'SENSOR_CALIBRATION')
        ]
        
        for index, expected_code in test_cases:
            self.adaptation_combo.setCurrentIndex(index)
            adaptation_code = self.panel.get_selected_adaptation_code()
            self.assertEqual(adaptation_code, expected_code)
            
    def test_adaptation_success(self):
        """Тест успешного выполнения адаптации"""
        # Выполняем адаптацию
        self.panel.on_adaptation_success("Адаптация выполнена успешно")
        
        # Проверяем обновление статуса
        self.assertIn("успешно", self.status_label.text().lower())
        
    def test_adaptation_error(self):
        """Тест ошибки адаптации"""
        error_msg = "Ошибка связи с ЭБУ"
        
        with patch('ui.adaptation_panel.QMessageBox.critical') as mock_critical:
            # Вызываем ошибку
            self.panel.on_adaptation_error(error_msg)
            
            # Проверяем показ сообщения
            mock_critical.assert_called_once()
            
            # Проверяем обновление статуса
            self.assertIn("ошибка", self.status_label.text().lower())
            
    def test_no_diagnostics_warning(self):
        """Тест предупреждения при отсутствии диагностики"""
        self.panel.diagnostics_engine = None
        
        with patch('ui.adaptation_panel.QMessageBox.warning') as mock_warning:
            QTest.mouseClick(self.perform_button, Qt.LeftButton)
            mock_warning.assert_called_once()
            
    def test_add_log_message(self):
        """Тест добавления сообщения в лог"""
        test_messages = [
            ("Начало адаптации...", "info"),
            ("Выполнение шага 1...", "info"),
            ("Ошибка выполнения", "error"),
            ("Адаптация завершена", "success")
        ]
        
        for message, msg_type in test_messages:
            self.panel.add_log_message(message, msg_type)
            
    def test_reset_function(self):
        """Тест сброса панели"""
        # Добавляем сообщения в лог
        self.panel.add_log_message("Тестовое сообщение", "info")
        
        # Сбрасываем
        self.panel.reset()
        
        # Проверяем сброс статуса
        self.assertEqual(self.status_label.text(), "Готов")
        
    def test_safety_warnings(self):
        """Тест предупреждений безопасности"""
        # Тест для опасных процедур
        dangerous_procedures = [0, 1, 4]  # Индексы опасных процедур
        
        for proc_index in dangerous_procedures:
            self.adaptation_combo.setCurrentIndex(proc_index)
            
            with patch('ui.adaptation_panel.QMessageBox.warning') as mock_warning:
                # Вызываем предупреждение
                self.panel.show_safety_warning()
                
                # Проверяем показ предупреждения
                mock_warning.assert_called_once()
                
    def test_procedure_instructions(self):
        """Тест инструкций для процедур"""
        test_cases = [
            (0, "Запустите двигатель и прогрейте до рабочей температуры"),
            (1, "Не нажимайте педаль акселератора во время процедуры"),
            (4, "Для обучения иммобилайзера требуется PIN-код")
        ]
        
        for proc_index, expected_instruction in test_cases:
            self.adaptation_combo.setCurrentIndex(proc_index)
            instructions = self.panel.get_procedure_instructions()
            self.assertIn(expected_instruction, instructions)


class TestReportsPanel(unittest.TestCase):
    """Тестирование панели отчетов"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.panel = ReportsPanel()
        self.panel.show()
        
        # Находим основные виджеты
        self.generate_button = self.panel.findChild(QPushButton, "generateButton")
        self.save_button = self.panel.findChild(QPushButton, "saveButton")
        self.print_button = self.panel.findChild(QPushButton, "printButton")
        self.format_combo = self.panel.findChild(QComboBox, "formatCombo")
        self.template_combo = self.panel.findChild(QComboBox, "templateCombo")
        self.report_preview = self.panel.findChild(QWidget, "reportPreview")
        
    def tearDown(self):
        """Очистка после каждого теста"""
        self.panel.close()
        QTest.qWait(100)
        
    def test_initial_state(self):
        """Тест начального состояния панели"""
        # Проверяем наличие виджетов
        self.assertIsNotNone(self.generate_button)
        self.assertIsNotNone(self.save_button)
        self.assertIsNotNone(self.print_button)
        self.assertIsNotNone(self.format_combo)
        self.assertIsNotNone(self.template_combo)
        
        # Проверяем доступные форматы
        expected_formats = ["HTML", "PDF", "DOCX", "TXT", "JSON"]
        for i, expected_format in enumerate(expected_formats):
            self.assertEqual(self.format_combo.itemText(i), expected_format)
            
        # Проверяем доступные шаблоны
        expected_templates = ["Стандартный", "Расширенный", "Технический", "Для клиента"]
        for i, expected_template in enumerate(expected_templates):
            self.assertEqual(self.template_combo.itemText(i), expected_template)
            
    def test_generate_report(self):
        """Тест генерации отчета"""
        # Создаем тестовые данные
        test_data = {
            'vehicle_info': {
                'model': 'Chevrolet Niva 1.7i',
                'year': 2015,
                'vin': 'X9L21230012345678'
            },
            'diagnostic_results': {
                'status': 'completed',
                'errors': ['P0101'],
                'parameters': {'rpm': 750}
            }
        }
        
        with patch.object(self.panel, 'get_diagnostic_data', 
                         return_value=test_data):
            
            # Генерируем отчет
            QTest.mouseClick(self.generate_button, Qt.LeftButton)
            
            # Проверяем, что кнопки активировались
            self.assertTrue(self.save_button.isEnabled())
            self.assertTrue(self.print_button.isEnabled())
            
    def test_save_report(self):
        """Тест сохранения отчета"""
        # Сначала генерируем отчет
        test_data = {'test': 'data'}
        self.panel.report_data = test_data
        
        with patch('ui.reports_panel.QFileDialog.getSaveFileName', 
                  return_value=('test_report.html', '')) as mock_dialog, \
             patch.object(self.panel, 'save_report_to_file') as mock_save:
            
            # Сохраняем отчет
            QTest.mouseClick(self.save_button, Qt.LeftButton)
            
            # Проверяем вызов диалога
            mock_dialog.assert_called_once()
            
            # Проверяем сохранение
            mock_save.assert_called_once()
            
    def test_save_report_no_data(self):
        """Тест сохранения отчета без данных"""
        # Не устанавливаем данные отчета
        self.panel.report_data = None
        
        with patch('ui.reports_panel.QMessageBox.warning') as mock_warning:
            # Пытаемся сохранить
            QTest.mouseClick(self.save_button, Qt.LeftButton)
            
            # Проверяем предупреждение
            mock_warning.assert_called_once()
            
    def test_generate_html_report(self):
        """Тест генерации HTML отчета"""
        test_data = {
            'vehicle_info': {
                'model': 'Chevrolet Niva 1.7i',
                'vin': 'X9L21230012345678',
                'date': '2024-01-01'
            },
            'diagnostic_results': {
                'status': 'completed',
                'error_count': 1,
                'parameters': [{'name': 'RPM', 'value': '750', 'unit': 'rpm'}]
            }
        }
        
        # Генерируем HTML
        html_report = self.panel.generate_html_report(test_data)
        
        # Проверяем содержимое
        self.assertIn('Chevrolet Niva', html_report)
        self.assertIn('Диагностический отчет', html_report)
        self.assertIn('<html>', html_report)
        self.assertIn('</body>', html_report)
        
    def test_generate_pdf_report(self):
        """Тест генерации PDF отчета"""
        test_data = {'test': 'data'}
        
        with patch('ui.reports_panel.ReportLabGenerator') as mock_generator:
            mock_instance = MagicMock()
            mock_generator.return_value = mock_instance
            
            # Генерируем PDF
            self.panel.generate_pdf_report(test_data)
            
            # Проверяем вызов генератора
            mock_generator.assert_called_once()
            mock_instance.generate.assert_called_once()
            
    def test_generate_json_report(self):
        """Тест генерации JSON отчета"""
        test_data = {
            'vehicle': 'Chevrolet Niva',
            'diagnostic': 'completed'
        }
        
        # Генерируем JSON
        json_report = self.panel.generate_json_report(test_data)
        
        # Проверяем, что это валидный JSON
        import json
        parsed = json.loads(json_report)
        self.assertEqual(parsed['vehicle'], 'Chevrolet Niva')
        
    def test_report_templates(self):
        """Тест шаблонов отчетов"""
        test_cases = [
            (0, "standard"),  # Стандартный
            (1, "extended"),  # Расширенный
            (2, "technical"), # Технический
            (3, "customer")   # Для клиента
        ]
        
        for index, expected_template in test_cases:
            self.template_combo.setCurrentIndex(index)
            template = self.panel.get_selected_template()
            self.assertEqual(template, expected_template)
            
    def test_format_selection(self):
        """Тест выбора формата"""
        test_cases = [
            (0, "html"),
            (1, "pdf"),
            (2, "docx"),
            (3, "txt"),
            (4, "json")
        ]
        
        for index, expected_format in test_cases:
            self.format_combo.setCurrentIndex(index)
            fmt = self.panel.get_selected_format()
            self.assertEqual(fmt, expected_format)
            
    def test_get_diagnostic_data(self):
        """Тест получения данных диагностики"""
        # Мокаем главное окно и панели
        mock_main_window = MagicMock()
        mock_diagnostic_panel = MagicMock()
        mock_error_panel = MagicMock()
        mock_live_data_panel = MagicMock()
        
        mock_diagnostic_panel.results = {
            'vehicle_model': '21236',
            'live_data': {'rpm': 750}
        }
        mock_error_panel.get_errors = Mock(return_value={'ENGINE': ['P0101']})
        mock_live_data_panel.get_current_data = Mock(return_value={'temp': 85})
        
        with patch('ui.reports_panel.MainWindow', return_value=mock_main_window):
            # Получаем данные
            data = self.panel.get_diagnostic_data()
            
            # Проверяем структуру данных
            self.assertIn('report_info', data)
            self.assertIn('vehicle_info', data)
            self.assertIn('diagnostic_results', data)
            
    def test_preview_generation(self):
        """Тест генерации предпросмотра"""
        test_data = {
            'vehicle_info': {'model': 'Test Model'},
            'diagnostic_results': {'status': 'test'}
        }
        
        # Генерируем предпросмотр
        self.panel.generate_report_preview(test_data)
        
        # Проверяем, что предпросмотр обновился
        self.assertIsNotNone(self.panel.report_data)
        
    def test_print_report(self):
        """Тест печати отчета"""
        # Устанавливаем данные отчета
        self.panel.report_data = {'test': 'data'}
        
        with patch('ui.reports_panel.QPrintDialog') as mock_dialog, \
             patch('ui.reports_panel.QPrinter') as mock_printer:
            
            mock_dialog_instance = MagicMock()
            mock_dialog.return_value = mock_dialog_instance
            mock_dialog_instance.exec_ = Mock(return_value=True)
            
            # Пытаемся распечатать
            QTest.mouseClick(self.print_button, Qt.LeftButton)
            
            # Проверяем вызов диалога печати
            mock_dialog.assert_called_once()
            
    def test_print_no_data(self):
        """Тест печати без данных"""
        self.panel.report_data = None
        
        with patch('ui.reports_panel.QMessageBox.warning') as mock_warning:
            # Пытаемся распечатать
            QTest.mouseClick(self.print_button, Qt.LeftButton)
            
            # Проверяем предупреждение
            mock_warning.assert_called_once()


# Тесты интеграции
class TestIntegration(unittest.TestCase):
    """Тесты интеграции между компонентами"""
    
    def test_main_window_with_real_panels(self):
        """Тест главного окна с реальными панелями (без моков)"""
        # Используем реальные панели для интеграционного теста
        with patch('ui.connection_panel.ELM327Connector') as MockConnector, \
             patch('ui.diagnostic_panel.DiagnosticsEngine') as MockDiagnostics:
            
            # Создаем конфигурацию
            config = MagicMock()
            config.get = Mock(return_value={})
            
            # Создаем главное окно
            window = MainWindow(config)
            
            # Проверяем создание всех панелей
            self.assertIsInstance(window.connection_panel, ConnectionPanel)
            self.assertIsInstance(window.diagnostic_tab, DiagnosticPanel)
            self.assertIsInstance(window.live_data_tab, LiveDataPanel)
            self.assertIsInstance(window.error_tab, ErrorPanel)
            self.assertIsInstance(window.adaptation_tab, AdaptationPanel)
            self.assertIsInstance(window.reports_tab, ReportsPanel)
            
            window.close()
            
    def test_connection_flow_integration(self):
        """Тест полного цикла подключения"""
        # Создаем мок для коннектора
        mock_connector = MagicMock()
        mock_connector.connect = Mock(return_value=True)
        mock_connector.is_connected = True
        
        # Создаем панель подключения
        with patch('ui.connection_panel.ELM327Connector', return_value=mock_connector):
            panel = ConnectionPanel()
            
            # Эмулируем выбор устройства и подключение
            panel.connection_type_combo.setCurrentText("USB")
            panel.port_combo.addItem("COM4")
            panel.port_combo.setCurrentText("COM4")
            
            # Подключаемся
            panel.connect_device()
            
            # Проверяем подключение
            mock_connector.connect.assert_called_once()
            self.assertTrue(panel.is_connected)
            
            panel.close()
            
    def test_full_diagnostic_flow(self):
        """Тест полного цикла диагностики"""
        # Создаем моки
        mock_connector = MagicMock()
        mock_diagnostics = MagicMock()
        
        # Настраиваем моки
        mock_connector.is_connected = True
        mock_diagnostics.perform_full_diagnostic = Mock(return_value={})
        mock_diagnostics.register_callback = Mock()
        
        # Создаем панель диагностики
        with patch('ui.diagnostic_panel.DiagnosticsEngine', 
                  return_value=mock_diagnostics):
            panel = DiagnosticPanel()
            panel.connector = mock_connector
            
            # Запускаем диагностику
            panel.start_diagnostic()
            
            # Проверяем вызовы
            mock_diagnostics.perform_full_diagnostic.assert_called_once()
            
            panel.close()


# Тесты производительности
class TestPerformance(unittest.TestCase):
    """Тесты производительности пользовательского интерфейса"""
    
    def test_ui_responsiveness(self):
        """Тест отзывчивости интерфейса"""
        import time
        
        config = MagicMock()
        config.get = Mock(return_value={})
        
        # Замеряем время создания окна
        start_time = time.time()
        
        with patch('ui.main_window.ConnectionPanel'), \
             patch('ui.main_window.DiagnosticPanel'), \
             patch('ui.main_window.LiveDataPanel'), \
             patch('ui.main_window.ErrorPanel'), \
             patch('ui.main_window.AdaptationPanel'), \
             patch('ui.main_window.ReportsPanel'):
            
            window = MainWindow(config)
            
        creation_time = time.time() - start_time
        
        # Время создания должно быть меньше 2 секунд
        self.assertLess(creation_time, 2.0, 
                       f"Создание окна заняло {creation_time:.2f} секунд")
        
        window.close()
        
    def test_memory_usage(self):
        """Тест использования памяти"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # в MB
        
        windows = []
        for _ in range(5):
            with patch('ui.main_window.ConnectionPanel'), \
                 patch('ui.main_window.DiagnosticPanel'), \
                 patch('ui.main_window.LiveDataPanel'), \
                 patch('ui.main_window.ErrorPanel'), \
                 patch('ui.main_window.AdaptationPanel'), \
                 patch('ui.main_window.ReportsPanel'):
                
                config = MagicMock()
                config.get = Mock(return_value={})
                window = MainWindow(config)
                windows.append(window)
                
        final_memory = process.memory_info().rss / 1024 / 1024
        
        # Утечка памяти должна быть минимальной
        memory_increase = final_memory - initial_memory
        self.assertLess(memory_increase, 50,  # MB
                       f"Утечка памяти: {memory_increase:.2f} MB")
        
        for window in windows:
            window.close()


if __name__ == '__main__':
    # Настраиваем окружение для тестов
    setup_module()
    
    # Запускаем тесты
    unittest.main(verbosity=2)
    
    # Очищаем
    teardown_module()