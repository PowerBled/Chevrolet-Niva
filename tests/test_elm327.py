"""
Полные тесты для модуля ELM327 Connector
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import time

# Добавляем путь к исходным файлам
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from elm327_connector import ELM327Connector, ConnectionType

class TestELM327Connector(unittest.TestCase):
    """Тесты для класса ELM327Connector"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.connector = ELM327Connector()
        
        # Моки для последовательного порта и Bluetooth
        self.mock_serial = Mock()
        self.mock_bluetooth = Mock()
        
    def tearDown(self):
        """Очистка после каждого теста"""
        if self.connector.is_connected:
            self.connector.disconnect()
    
    def test_initial_state(self):
        """Тест начального состояния соединения"""
        self.assertFalse(self.connector.is_connected)
        self.assertFalse(self.connector.is_monitoring)
        self.assertIsNone(self.connector.connection)
        self.assertIsNone(self.connector.connection_type)
        self.assertEqual(self.connector.baudrate, 38400)
        self.assertEqual(self.connector.bytes_sent, 0)
        self.assertEqual(self.connector.bytes_received, 0)
        self.assertEqual(self.connector.errors, 0)
    
    @patch('serial.Serial')
    def test_usb_connection_success(self, mock_serial_class):
        """Тест успешного USB подключения"""
        # Настройка мока
        mock_serial = Mock()
        mock_serial.read_all.return_value = b'ATZ\r\rELM327 v1.5\r>'
        mock_serial.in_waiting = 0
        mock_serial_class.return_value = mock_serial
        
        # Выполнение подключения
        result = self.connector.connect(ConnectionType.USB, port='COM3')
        
        # Проверки
        self.assertTrue(result)
        self.assertTrue(self.connector.is_connected)
        self.assertEqual(self.connector.connection_type, ConnectionType.USB)
        self.assertEqual(self.connector.port, 'COM3')
        
        # Проверка вызовов инициализации
        mock_serial_class.assert_called_once_with(
            port='COM3',
            baudrate=38400,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=1
        )
    
    @patch('serial.Serial')
    def test_usb_connection_failure(self, mock_serial_class):
        """Тест неудачного USB подключения"""
        # Настройка мока для вызова исключения
        mock_serial_class.side_effect = serial.SerialException("Port not found")
        
        # Выполнение подключения
        result = self.connector.connect(ConnectionType.USB, port='COM99')
        
        # Проверки
        self.assertFalse(result)
        self.assertFalse(self.connector.is_connected)
        self.assertIsNone(self.connector.connection_type)
    
    @patch('bluetooth.discover_devices')
    @patch('bluetooth.BluetoothSocket')
    def test_bluetooth_connection_success(self, mock_socket_class, mock_discover):
        """Тест успешного Bluetooth подключения"""
        # Настройка моков
        mock_discover.return_value = ['00:0D:18:00:00:00', 'AA:BB:CC:DD:EE:FF']
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        
        # Имитация успешной инициализации адаптера
        mock_socket.recv.side_effect = [
            b'ATZ\r\rELM327 v1.5\r>',
            b'ATE0\rOK\r>',
            b'ATL0\rOK\r>',
            b'ATS0\rOK\r>',
            b'ATH1\rOK\r>',
            b'ATSP0\rOK\r>'
        ]
        
        # Выполнение подключения
        result = self.connector.connect(
            ConnectionType.BLUETOOTH,
            address='00:0D:18:00:00:00'
        )
        
        # Проверки
        self.assertTrue(result)
        self.assertTrue(self.connector.is_connected)
        self.assertEqual(self.connector.connection_type, ConnectionType.BLUETOOTH)
        
        # Проверка вызовов
        mock_discover.assert_called_once()
        mock_socket_class.assert_called_once_with(bluetooth.RFCOMM)
        mock_socket.connect.assert_called_once_with(('00:0D:18:00:00:00', 1))
    
    @patch('bluetooth.discover_devices')
    def test_bluetooth_connection_device_not_found(self, mock_discover):
        """Тест Bluetooth подключения при отсутствии устройства"""
        # Настройка мока
        mock_discover.return_value = ['AA:BB:CC:DD:EE:FF']  # Только другое устройство
        
        # Выполнение подключения
        with self.assertRaises(ConnectionError) as context:
            self.connector.connect(
                ConnectionType.BLUETOOTH,
                address='00:0D:18:00:00:00'
            )
        
        # Проверка сообщения об ошибке
        self.assertEqual(str(context.exception), "Устройство не найдено")
        self.assertFalse(self.connector.is_connected)
    
    @patch('serial.Serial')
    def test_adapter_initialization_failure(self, mock_serial_class):
        """Тест неудачной инициализации адаптера"""
        # Настройка мока
        mock_serial = Mock()
        mock_serial.read_all.return_value = b'ATZ\rERROR\r>'
        mock_serial.in_waiting = 0
        mock_serial_class.return_value = mock_serial
        
        # Выполнение подключения
        result = self.connector.connect(ConnectionType.USB, port='COM3')
        
        # Проверки
        self.assertFalse(result)
        self.assertFalse(self.connector.is_connected)
    
    @patch('serial.Serial')
    def test_send_command_success(self, mock_serial_class):
        """Тест успешной отправки команды"""
        # Настройка мока
        mock_serial = Mock()
        mock_serial.read_all.side_effect = [
            b'',  # Первый вызов - нет данных
            b'010C\r41 0C 0F A0 \r>'  # Ответ на команду RPM
        ]
        mock_serial.in_waiting = 0
        mock_serial_class.return_value = mock_serial
        
        # Подключение
        self.connector.connect(ConnectionType.USB, port='COM3')
        
        # Отправка команды
        response = self.connector.send_command("010C", wait_time=0.01)
        
        # Проверки
        self.assertIsNotNone(response)
        self.assertNotIn("ERROR", response)
        self.assertEqual(self.connector.bytes_sent, len("010C\r"))
        self.assertGreater(self.connector.bytes_received, 0)
        
        # Проверка вызовов
        mock_serial.write.assert_called_once_with(b'010C\r')
    
    @patch('serial.Serial')
    def test_send_command_not_connected(self, mock_serial_class):
        """Тест отправки команды без подключения"""
        # Отправка команды без подключения
        response = self.connector.send_command("010C")
        
        # Проверки
        self.assertEqual(response, "NOT CONNECTED")
        self.assertEqual(self.connector.bytes_sent, 0)
        self.assertEqual(self.connector.bytes_received, 0)
    
    @patch('serial.Serial')
    def test_send_command_with_error(self, mock_serial_class):
        """Тест отправки команды с ошибкой"""
        # Настройка мока
        mock_serial = Mock()
        mock_serial.write.side_effect = serial.SerialException("Write failed")
        mock_serial_class.return_value = mock_serial
        
        # Подключение
        self.connector.connect(ConnectionType.USB, port='COM3')
        
        # Отправка команды
        response = self.connector.send_command("010C")
        
        # Проверки
        self.assertIn("ERROR", response)
        self.assertEqual(self.connector.errors, 1)
    
    def test_clean_response(self):
        """Тест очистки ответа"""
        test_cases = [
            {
                'input': '>010C\r\r41 0C 0F A0 \r\r>',
                'expected': '41 0C 0F A0'
            },
            {
                'input': '  41 0C 0F A0  \r\n  ',
                'expected': '41 0C 0F A0'
            },
            {
                'input': '41  0C   0F   A0',
                'expected': '41 0C 0F A0'
            },
            {
                'input': '',
                'expected': ''
            },
            {
                'input': 'NO DATA',
                'expected': 'NO DATA'
            }
        ]
        
        for test_case in test_cases:
            with self.subTest(input=test_case['input']):
                result = self.connector._clean_response(test_case['input'])
                self.assertEqual(result, test_case['expected'])
    
    @patch('serial.Serial')
    def test_monitoring_thread(self, mock_serial_class):
        """Тест потока мониторинга"""
        # Настройка мока
        mock_serial = Mock()
        mock_serial.in_waiting = 10
        mock_serial.read_all.side_effect = [
            b'41 0C 0F A0\r',
            b'41 0D 00\r',
            b''  # Пустой ответ для выхода из цикла
        ]
        mock_serial_class.return_value = mock_serial
        
        # Подключение и запуск мониторинга
        self.connector.connect(ConnectionType.USB, port='COM3')
        
        # Даем время потоку мониторинга собрать данные
        time.sleep(0.1)
        
        # Проверки
        self.assertTrue(self.connector.is_monitoring)
        self.assertIsNotNone(self.connector.monitor_thread)
        self.assertTrue(self.connector.monitor_thread.is_alive())
        
        # Проверка очереди ответов
        self.assertFalse(self.connector.response_queue.empty())
        
        # Останавливаем мониторинг
        self.connector.disconnect()
        
        # Проверка отключения
        self.assertFalse(self.connector.is_monitoring)
        self.assertFalse(self.connector.is_connected)
    
    @patch('serial.Serial')
    def test_disconnect(self, mock_serial_class):
        """Тест отключения от адаптера"""
        # Настройка мока
        mock_serial = Mock()
        mock_serial_class.return_value = mock_serial
        
        # Подключение
        self.connector.connect(ConnectionType.USB, port='COM3')
        
        # Отключение
        self.connector.disconnect()
        
        # Проверки
        self.assertFalse(self.connector.is_connected)
        self.assertFalse(self.connector.is_monitoring)
        mock_serial.close.assert_called_once()
    
    @patch('serial.Serial')
    def test_disconnect_without_connection(self, mock_serial_class):
        """Тест отключения без установленного соединения"""
        # Отключение без подключения
        self.connector.disconnect()
        
        # Проверки - не должно быть исключений
        self.assertFalse(self.connector.is_connected)
        self.assertFalse(self.connector.is_monitoring)
    
    @patch('serial.Serial')
    def test_get_statistics(self, mock_serial_class):
        """Тест получения статистики"""
        # Настройка мока
        mock_serial = Mock()
        mock_serial.read_all.return_value = b'41 0C 0F A0\r'
        mock_serial.in_waiting = 0
        mock_serial_class.return_value = mock_serial
        
        # Подключение и отправка команд
        self.connector.connect(ConnectionType.USB, port='COM4')
        
        # Отправляем несколько команд
        self.connector.send_command("010C")
        self.connector.send_command("010D")
        
        # Получаем статистику
        stats = self.connector.get_statistics()
        
        # Проверки
        self.assertEqual(stats['connection_type'], ConnectionType.USB)
        self.assertEqual(stats['port'], 'COM4')
        self.assertGreater(stats['bytes_sent'], 0)
        self.assertGreater(stats['bytes_received'], 0)
        self.assertEqual(stats['errors'], 0)
    
    @patch('serial.Serial')
    def test_connection_resilience(self, mock_serial_class):
        """Тест устойчивости соединения при ошибках"""
        # Настройка мока с периодическими ошибками
        mock_serial = Mock()
        call_count = 0
        
        def mock_read_all():
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:  # Каждая третья команда вызывает ошибку
                raise serial.SerialException("Temporary error")
            return b'41 0C 0F A0\r'
        
        mock_serial.read_all = mock_read_all
        mock_serial.in_waiting = 0
        mock_serial_class.return_value = mock_serial
        
        # Подключение
        self.connector.connect(ConnectionType.USB, port='COM3')
        
        # Отправляем несколько команд
        for i in range(10):
            response = self.connector.send_command(f"01{i:02X}")
            
            if i % 3 == 2:
                self.assertIn("ERROR", response)
            else:
                self.assertNotIn("ERROR", response)
        
        # Проверяем количество ошибок
        self.assertEqual(self.connector.errors, 3)
    
    @patch('serial.Serial')
    def test_thread_safety(self, mock_serial_class):
        """Тест потокобезопасности"""
        import threading
        
        # Настройка мока
        mock_serial = Mock()
        mock_serial.read_all.return_value = b'41 0C 0F A0\r'
        mock_serial.in_waiting = 0
        mock_serial_class.return_value = mock_serial
        
        # Подключение
        self.connector.connect(ConnectionType.USB, port='COM3')
        
        # Функция для отправки команд из потока
        def send_commands(thread_id, num_commands):
            for i in range(num_commands):
                cmd = f"01{thread_id:02X}"
                response = self.connector.send_command(cmd, wait_time=0.001)
                self.assertIsNotNone(response)
        
        # Создаем и запускаем несколько потоков
        threads = []
        num_threads = 5
        commands_per_thread = 20
        
        for i in range(num_threads):
            thread = threading.Thread(
                target=send_commands,
                args=(i, commands_per_thread)
            )
            threads.append(thread)
            thread.start()
        
        # Ожидаем завершения всех потоков
        for thread in threads:
            thread.join()
        
        # Проверяем, что нет race conditions и все команды обработаны
        expected_total_commands = num_threads * commands_per_thread
        expected_bytes_sent = expected_total_commands * 5  # 4 символа + \r
        
        self.assertGreaterEqual(self.connector.bytes_sent, expected_bytes_sent)
        self.assertEqual(self.connector.errors, 0)
    
    @patch('serial.Serial')
    def test_command_timeout(self, mock_serial_class):
        """Тест таймаута при отправке команды"""
        # Настройка мока с задержкой
        mock_serial = Mock()
        
        def delayed_read_all():
            time.sleep(0.2)  # Задержка больше чем wait_time
            return b'41 0C 0F A0\r'
        
        mock_serial.read_all = delayed_read_all
        mock_serial.in_waiting = 0
        mock_serial_class.return_value = mock_serial
        
        # Подключение
        self.connector.connect(ConnectionType.USB, port='COM3')
        
        # Отправка команды с маленьким таймаутом
        response = self.connector.send_command("010C", wait_time=0.01)
        
        # Проверка - ответ может быть пустым из-за таймаута
        self.assertIsNotNone(response)
    
    def test_connection_type_enum(self):
        """Тест перечисления типов подключения"""
        # Проверка значений enum
        self.assertEqual(ConnectionType.BLUETOOTH.value, "bluetooth")
        self.assertEqual(ConnectionType.USB.value, "usb")
        self.assertEqual(ConnectionType.WIFI.value, "wifi")
        
        # Проверка строкового представления
        self.assertEqual(str(ConnectionType.BLUETOOTH), "ConnectionType.BLUETOOTH")
        self.assertEqual(str(ConnectionType.USB), "ConnectionType.USB")
        
        # Проверка сравнения
        self.assertEqual(ConnectionType.BLUETOOTH, ConnectionType.BLUETOOTH)
        self.assertNotEqual(ConnectionType.BLUETOOTH, ConnectionType.USB)
    
    @patch('serial.Serial')
    def test_reconnect_after_disconnect(self, mock_serial_class):
        """Тест повторного подключения после отключения"""
        # Первое подключение
        mock_serial1 = Mock()
        mock_serial1.read_all.return_value = b'ATZ\r\rELM327 v1.5\r>'
        mock_serial1.in_waiting = 0
        
        mock_serial_class.return_value = mock_serial1
        result1 = self.connector.connect(ConnectionType.USB, port='COM3')
        
        self.assertTrue(result1)
        self.assertTrue(self.connector.is_connected)
        
        # Отключение
        self.connector.disconnect()
        
        # Проверка сброса статистики
        self.assertEqual(self.connector.bytes_sent, 0)
        self.assertEqual(self.connector.bytes_received, 0)
        self.assertEqual(self.connector.errors, 0)
        
        # Второе подключение
        mock_serial2 = Mock()
        mock_serial2.read_all.return_value = b'ATZ\r\rELM327 v2.1\r>'
        mock_serial2.in_waiting = 0
        
        mock_serial_class.return_value = mock_serial2
        result2 = self.connector.connect(ConnectionType.USB, port='COM4')
        
        self.assertTrue(result2)
        self.assertTrue(self.connector.is_connected)
        self.assertEqual(self.connector.port, 'COM4')
    
    @patch('serial.Serial')
    def test_multiple_commands_rapid_fire(self, mock_serial_class):
        """Тест быстрой отправки нескольких команд подряд"""
        # Настройка мока
        responses = [
            b'41 0C 0F A0\r',  # RPM
            b'41 0D 00\r',     # Speed
            b'41 05 7B\r',     # Coolant temp
            b'41 0F 45\r',     # Intake temp
            b'41 11 33\r',     # Throttle position
        ]
        
        mock_serial = Mock()
        mock_serial.read_all.side_effect = responses
        mock_serial.in_waiting = 0
        mock_serial_class.return_value = mock_serial
        
        # Подключение
        self.connector.connect(ConnectionType.USB, port='COM3')
        
        # Быстрая отправка команд
        commands = ["010C", "010D", "0105", "010F", "0111"]
        results = []
        
        for cmd in commands:
            response = self.connector.send_command(cmd, wait_time=0.01)
            results.append(response)
        
        # Проверки
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertIsNotNone(result)
            self.assertNotIn("ERROR", result)
        
        # Проверка статистики
        self.assertGreater(self.connector.bytes_sent, 0)
        self.assertGreater(self.connector.bytes_received, 0)
    
    @patch('serial.Serial')
    def test_invalid_utf8_response(self, mock_serial_class):
        """Тест обработки ответа с невалидными UTF-8 символами"""
        # Настройка мока с бинарными данными
        mock_serial = Mock()
        mock_serial.read_all.return_value = b'\xff\xfe\x00\x00' + b'41 0C 0F A0\r'
        mock_serial.in_waiting = 0
        mock_serial_class.return_value = mock_serial
        
        # Подключение
        self.connector.connect(ConnectionType.USB, port='COM3')
        
        # Отправка команды
        response = self.connector.send_command("010C")
        
        # Проверка - не должно быть исключения UnicodeDecodeError
        self.assertIsNotNone(response)
        self.assertNotIn("ERROR", response)
    
    @patch('serial.Serial')
    def test_partial_response_handling(self, mock_serial_class):
        """Тест обработки частичного ответа"""
        # Настройка мока с неполным ответом
        mock_serial = Mock()
        mock_serial.read_all.return_value = b'41 0C'  # Неполный ответ
        mock_serial.in_waiting = 0
        mock_serial_class.return_value = mock_serial
        
        # Подключение
        self.connector.connect(ConnectionType.USB, port='COM3')
        
        # Отправка команды
        response = self.connector.send_command("010C")
        
        # Проверка
        self.assertIsNotNone(response)
        self.assertEqual(response, "41 0C")
    
    def test_connection_type_validation(self):
        """Тест валидации типа подключения"""
        # Попытка подключения с неверным типом
        with self.assertRaises(AttributeError):
            self.connector.connect("INVALID_TYPE", port='COM3')
        
        # Попытка подключения без порта для USB
        with self.assertRaises(TypeError):
            self.connector.connect(ConnectionType.USB)
        
        # Попытка подключения без адреса для Bluetooth
        with self.assertRaises(TypeError):
            self.connector.connect(ConnectionType.BLUETOOTH)


class TestELM327ConnectorEdgeCases(unittest.TestCase):
    """Тесты для граничных случаев ELM327Connector"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.connector = ELM327Connector()
    
    def test_empty_command(self):
        """Тест отправки пустой команды"""
        with patch('serial.Serial') as mock_serial_class:
            mock_serial = Mock()
            mock_serial.read_all.return_value = b'\r>'
            mock_serial.in_waiting = 0
            mock_serial_class.return_value = mock_serial
            
            self.connector.connect(ConnectionType.USB, port='COM3')
            
            # Отправка пустой команды
            response = self.connector.send_command("")
            
            # Проверка
            self.assertIsNotNone(response)
            self.assertEqual(self.connector.bytes_sent, len("\r"))
    
    def test_very_long_command(self):
        """Тест отправки очень длинной команды"""
        with patch('serial.Serial') as mock_serial_class:
            mock_serial = Mock()
            mock_serial.read_all.return_value = b'OK\r>'
            mock_serial.in_waiting = 0
            mock_serial_class.return_value = mock_serial
            
            self.connector.connect(ConnectionType.USB, port='COM3')
            
            # Отправка очень длинной команды
            long_command = "AT" + "A" * 1000
            response = self.connector.send_command(long_command)
            
            # Проверка
            self.assertIsNotNone(response)
            self.assertEqual(self.connector.bytes_sent, len(long_command) + 1)
    
    @patch('serial.Serial')
    def test_rapid_disconnect_reconnect(self, mock_serial_class):
        """Тест быстрого отключения и повторного подключения"""
        mock_serial = Mock()
        mock_serial.read_all.return_value = b'ATZ\r\rELM327 v1.5\r>'
        mock_serial.in_waiting = 0
        mock_serial_class.return_value = mock_serial
        
        # Быстрые циклы подключения/отключения
        for i in range(5):
            result = self.connector.connect(ConnectionType.USB, port=f'COM{i+1}')
            self.assertTrue(result)
            self.assertTrue(self.connector.is_connected)
            
            self.connector.disconnect()
            self.assertFalse(self.connector.is_connected)
    
    @patch('serial.Serial')
    def test_monitoring_thread_exception_handling(self, mock_serial_class):
        """Тест обработки исключений в потоке мониторинга"""
        mock_serial = Mock()
        
        # Симуляция исключения при чтении
        def read_with_exception():
            raise serial.SerialException("Read error")
        
        mock_serial.in_waiting = 10
        mock_serial.read_all = read_with_exception
        mock_serial_class.return_value = mock_serial
        
        # Подключение
        result = self.connector.connect(ConnectionType.USB, port='COM3')
        self.assertTrue(result)
        
        # Даем время потоку упасть и восстановиться
        time.sleep(0.1)
        
        # Проверка - поток должен продолжать работать
        self.assertTrue(self.connector.is_monitoring)
        self.assertTrue(self.connector.monitor_thread.is_alive())
    
    def test_thread_safe_disconnect(self):
        """Тест потокобезопасного отключения"""
        with patch('serial.Serial') as mock_serial_class:
            mock_serial = Mock()
            mock_serial.read_all.return_value = b'41 0C 0F A0\r'
            mock_serial.in_waiting = 10  # Имитация данных для мониторинга
            mock_serial_class.return_value = mock_serial
            
            self.connector.connect(ConnectionType.USB, port='COM3')
            
            # Запускаем отключение из нескольких потоков одновременно
            import threading
            
            def disconnect_thread():
                self.connector.disconnect()
            
            threads = []
            for i in range(3):
                thread = threading.Thread(target=disconnect_thread)
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
            
            # Проверка - не должно быть исключений
            self.assertFalse(self.connector.is_connected)
            self.assertFalse(self.connector.is_monitoring)


class TestELM327ConnectorIntegration(unittest.TestCase):
    """Интеграционные тесты для ELM327Connector"""
    
    @classmethod
    def setUpClass(cls):
        """Настройка перед всеми тестами класса"""
        cls.test_port = None
        
        # Попытка найти реальный COM-порт для тестирования
        if sys.platform.startswith('win'):
            # Для Windows проверяем COM3-COM10
            for port_num in range(3, 11):
                port_name = f'COM{port_num}'
                try:
                    with serial.Serial(port_name, timeout=0.1):
                        cls.test_port = port_name
                        break
                except:
                    continue
    
    @unittest.skipUnless(sys.platform.startswith('win'), "Требуется Windows и реальный COM-порт")
    def test_real_serial_connection(self):
        """Тест реального подключения к последовательному порту (требуется реальное устройство)"""
        if not self.test_port:
            self.skipTest("Не найден доступный COM-порт для тестирования")
        
        # Создаем подключение к реальному порту
        connector = ELM327Connector()
        
        try:
            # Пробуем подключиться
            result = connector.connect(ConnectionType.USB, port=self.test_port)
            
            # Если подключение успешно, тестируем команды
            if result:
                # Тестовая команда
                response = connector.send_command("ATZ", wait_time=0.5)
                self.assertIsNotNone(response)
                
                # Проверка статистики
                stats = connector.get_statistics()
                self.assertGreater(stats['bytes_sent'], 0)
                
            # Если не удалось подключиться, это тоже нормально для тестов
            # без реального устройства
            
        finally:
            connector.disconnect()
    
    def test_mock_full_communication_cycle(self):
        """Тест полного цикла коммуникации с моком"""
        with patch('serial.Serial') as mock_serial_class:
            # Настройка сложного мока для полного цикла
            mock_serial = Mock()
            
            # Имитация ответов на команды инициализации
            init_responses = [
                b'ATZ\r\rELM327 v2.1\r>',
                b'ATE0\rOK\r>',
                b'ATL0\rOK\r>',
                b'ATS0\rOK\r>',
                b'ATH1\rOK\r>',
                b'ATSP0\rOK\r>',
            ]
            
            # Имитация ответов на диагностические команды
            diag_responses = [
                b'41 00 BE 1F B8 10\r>',  # Supported PIDs
                b'41 0C 0F A0\r>',         # RPM
                b'41 0D 00\r>',            # Speed
                b'41 05 7B\r>',            # Coolant temp
                b'7F 01 12\r>',            # Ошибка для несуществующего PID
            ]
            
            all_responses = init_responses + diag_responses
            response_index = 0
            
            def get_response():
                nonlocal response_index
                if response_index < len(all_responses):
                    response = all_responses[response_index]
                    response_index += 1
                    return response
                return b'NO DATA\r>'
            
            mock_serial.read_all = get_response
            mock_serial.in_waiting = 0
            mock_serial_class.return_value = mock_serial
            
            # Подключение
            connector = ELM327Connector()
            result = connector.connect(ConnectionType.USB, port='COM3')
            self.assertTrue(result)
            
            # Серия диагностических команд
            commands = ["0100", "010C", "010D", "0105", "0199"]  # Последний - несуществующий PID
            responses = []
            
            for cmd in commands:
                response = connector.send_command(cmd, wait_time=0.05)
                responses.append(response)
            
            # Проверки
            self.assertEqual(len(responses), 5)
            
            # Проверка конкретных ответов
            self.assertIn("BE 1F B8 10", responses[0])  # Supported PIDs
            self.assertIn("0F A0", responses[1])         # RPM
            self.assertIn("7F 01 12", responses[4])      # Ошибка
            
            # Проверка статистики
            stats = connector.get_statistics()
            self.assertGreater(stats['bytes_sent'], 0)
            self.assertGreater(stats['bytes_received'], 0)
            
            connector.disconnect()


class TestELM327ConnectorPerformance(unittest.TestCase):
    """Тесты производительности ELM327Connector"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.connector = ELM327Connector()
    
    @patch('serial.Serial')
    def test_command_throughput(self, mock_serial_class):
        """Тест пропускной способности команд"""
        import time
        
        mock_serial = Mock()
        mock_serial.read_all.return_value = b'41 0C 0F A0\r'
        mock_serial.in_waiting = 0
        mock_serial_class.return_value = mock_serial
        
        # Подключение
        self.connector.connect(ConnectionType.USB, port='COM3')
        
        # Измеряем время отправки множества команд
        num_commands = 100
        start_time = time.time()
        
        for i in range(num_commands):
            cmd = f"01{i % 256:02X}"
            self.connector.send_command(cmd, wait_time=0.001)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Проверка производительности
        commands_per_second = num_commands / total_time
        print(f"\nПропускная способность: {commands_per_second:.2f} команд/сек")
        
        # Минимальные требования к производительности
        self.assertGreater(commands_per_second, 10)  # Минимум 10 команд/сек
    
    @patch('serial.Serial')
    def test_memory_usage(self, mock_serial_class):
        """Тест использования памяти"""
        import gc
        import psutil
        import os
        
        mock_serial = Mock()
        mock_serial.read_all.return_value = b'41 0C 0F A0\r'
        mock_serial.in_waiting = 0
        mock_serial_class.return_value = mock_serial
        
        # Измеряем начальное использование памяти
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # в MB
        
        # Создаем много соединений и команд
        connectors = []
        for i in range(100):
            connector = ELM327Connector()
            connector.connect(ConnectionType.USB, port=f'COM{i % 10 + 1}')
            
            # Отправляем несколько команд
            for j in range(10):
                connector.send_command(f"01{j:02X}")
            
            connectors.append(connector)
        
        # Измеряем использование памяти после создания объектов
        gc.collect()  # Принудительный сбор мусора
        final_memory = process.memory_info().rss / 1024 / 1024
        
        memory_increase = final_memory - initial_memory
        print(f"\nИспользование памяти: {memory_increase:.2f} MB на 100 соединений")
        
        # Очистка
        for connector in connectors:
            connector.disconnect()
        
        # Проверка - утечек памяти быть не должно
        self.assertLess(memory_increase, 50)  # Не более 50 MB на 100 соединений


def run_all_tests():
    """Запуск всех тестов"""
    # Создаем test suite
    loader = unittest.TestLoader()
    
    # Загружаем все тестовые классы
    test_classes = [
        TestELM327Connector,
        TestELM327ConnectorEdgeCases,
        TestELM327ConnectorIntegration,
        TestELM327ConnectorPerformance,
    ]
    
    suites = []
    for test_class in test_classes:
        suite = loader.loadTestsFromTestCase(test_class)
        suites.append(suite)
    
    # Объединяем все suites
    full_suite = unittest.TestSuite(suites)
    
    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(full_suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    # Импортируем serial здесь, чтобы не мешать мокам
    import serial
    
    success = run_all_tests()
    
    if not success:
        sys.exit(1)
    else:
        print("\n" + "="*70)
        print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("="*70)