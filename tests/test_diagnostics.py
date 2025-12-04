"""
Полные тесты для модуля диагностики
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

# Добавляем путь к исходным файлам
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from diagnostics_engine import DiagnosticsEngine
from niva_protocols import NivaProtocols
from elm327_connector import ELM327Connector, ConnectionType


class TestDiagnosticsEngine(unittest.TestCase):
    """Тесты для движка диагностики"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        # Создаем мок коннектора
        self.mock_connector = Mock(spec=ELM327Connector)
        self.mock_connector.is_connected = True
        self.mock_connector.send_command = Mock()
        
        # Создаем экземпляр движка
        self.diagnostics = DiagnosticsEngine(self.mock_connector)
        
        # Тестовые данные
        self.test_vehicle_model = '21236'
        
    def tearDown(self):
        """Очистка после каждого теста"""
        self.diagnostics.is_running = False
        if self.diagnostics.diagnostic_thread:
            self.diagnostics.diagnostic_thread.join(timeout=1)
            
    def test_initialization(self):
        """Тест инициализации движка диагностики"""
        self.assertIsNotNone(self.diagnostics)
        self.assertEqual(self.diagnostics.connector, self.mock_connector)
        self.assertIsInstance(self.diagnostics.protocols, NivaProtocols)
        self.assertFalse(self.diagnostics.is_running)
        self.assertEqual(self.diagnostics.results, {})
        self.assertEqual(self.diagnostics.callbacks, {})
        
    def test_perform_full_diagnostic_success(self):
        """Тест успешного выполнения полной диагностики"""
        # Настраиваем мок для успешного выполнения
        self.mock_connector.send_command.side_effect = [
            # Ответ на проверку связи с ECU
            "48 6B 10 41 00 BE 3F B8 11",
            # Ответ на чтение DTC
            "43 01 00 03 00 00 00 00",
            # Ответы на чтение live data
            "41 00 BE 3F B8 11",  # Supported PIDs
            "41 0C 1A F8",        # RPM
            "41 0D 00",           # Speed
            "41 05 7B",           # Coolant temp
            "41 0F 47",           # Intake temp
            "41 11 33",           # Throttle position
            "41 10 03 E8",        # MAF
            "41 0A 23",           # Fuel pressure
            "41 0B 64",           # Intake pressure
            "41 0E 46",           # Timing advance
            "41 04 4D",           # Engine load
            "41 2F 66",           # Fuel level
            "41 42 0D 48",        # Voltage
        ]
        
        # Запускаем диагностику
        result = self.diagnostics.perform_full_diagnostic(self.test_vehicle_model)
        
        # Проверяем результат
        self.assertIn('timestamp', result)
        self.assertEqual(result['vehicle_model'], self.test_vehicle_model)
        self.assertEqual(result['diagnostic_status'], 'IN_PROGRESS')
        
        # Ждем завершения потока
        if self.diagnostics.diagnostic_thread:
            self.diagnostics.diagnostic_thread.join(timeout=2)
            
        # Проверяем, что были вызваны команды
        self.assertTrue(self.mock_connector.send_command.called)
        
    def test_perform_full_diagnostic_no_connection(self):
        """Тест выполнения диагностики без подключения"""
        # Настраиваем мок без подключения
        self.mock_connector.is_connected = False
        
        # Запускаем диагностику
        result = self.diagnostics.perform_full_diagnostic(self.test_vehicle_model)
        
        # Проверяем результат
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'Нет подключения')
        
    @patch('threading.Thread')
    def test_diagnostic_worker_start(self, mock_thread):
        """Тест запуска потока диагностики"""
        # Настраиваем мок потока
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        # Запускаем диагностику
        self.diagnostics.perform_full_diagnostic(self.test_vehicle_model)
        
        # Проверяем создание потока
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
        self.assertTrue(self.diagnostics.is_running)
        
    def test_diagnostic_worker_exception(self):
        """Тест исключения в потоке диагностики"""
        # Настраиваем мок для вызова исключения
        self.mock_connector.send_command.side_effect = Exception("Test error")
        
        # Регистрируем коллбэк для ошибки
        error_callback = Mock()
        self.diagnostics.register_callback('error', error_callback)
        
        # Запускаем диагностику в основном потоке (без Thread для теста)
        self.diagnostics._diagnostic_worker()
        
        # Проверяем, что был вызван коллбэк ошибки
        error_callback.assert_called_once()
        
        # Проверяем результат
        self.assertEqual(self.diagnostics.results['diagnostic_status'], 'FAILED')
        self.assertIn('error', self.diagnostics.results)
        
    def test_check_ecu_communication_success(self):
        """Тест успешной проверки связи с ЭБУ"""
        # Настраиваем мок
        self.mock_connector.send_command.return_value = "48 6B 10 41 00 BE 3F B8 11"
        
        # Выполняем проверку
        result = self.diagnostics._check_ecu_communication()
        
        # Проверяем результат
        self.assertIn('ENGINE', result)
        self.assertEqual(result['ENGINE']['status'], 'CONNECTED')
        self.assertIn('response', result['ENGINE'])
        
        # Проверяем количество вызовов
        expected_calls = len(NivaProtocols.ECUS)
        self.assertEqual(self.mock_connector.send_command.call_count, expected_calls)
        
    def test_check_ecu_communication_no_response(self):
        """Тест проверки связи без ответа от ЭБУ"""
        # Настраиваем мок для отсутствия ответа
        self.mock_connector.send_command.return_value = "NO DATA"
        
        # Выполняем проверку
        result = self.diagnostics._check_ecu_communication()
        
        # Проверяем результат
        self.assertIn('ENGINE', result)
        self.assertEqual(result['ENGINE']['status'], 'NOT_RESPONDING')
        
    def test_check_ecu_communication_exception(self):
        """Тест исключения при проверке связи"""
        # Настраиваем мок для вызова исключения
        self.mock_connector.send_command.side_effect = Exception("Connection failed")
        
        # Выполняем проверку
        result = self.diagnostics._check_ecu_communication()
        
        # Проверяем результат
        self.assertIn('ENGINE', result)
        self.assertEqual(result['ENGINE']['status'], 'ERROR')
        self.assertIn('error', result['ENGINE'])
        
    def test_read_dtcs_success(self):
        """Тест успешного чтения DTC"""
        # Настраиваем мок
        self.mock_connector.send_command.return_value = "43 01 00 03 00 00 00 00"
        
        # Выполняем чтение
        result = self.diagnostics._read_dtcs()
        
        # Проверяем результат
        self.assertIn('ENGINE', result)
        self.assertIsInstance(result['ENGINE'], list)
        
    def test_read_dtcs_no_data(self):
        """Тест чтения DTC без данных"""
        # Настраиваем мок для отсутствия данных
        self.mock_connector.send_command.return_value = "NO DATA"
        
        # Выполняем чтение
        result = self.diagnostics._read_dtcs()
        
        # Проверяем результат
        self.assertIn('ENGINE', result)
        self.assertEqual(result['ENGINE'], [])
        
    def test_parse_dtc_response_valid(self):
        """Тест парсинга валидного ответа с DTC"""
        # Тестовые данные
        test_response = "43 01 00 03 00 00 00 00"
        
        # Выполняем парсинг
        result = self.diagnostics._parse_dtc_response(test_response)
        
        # Проверяем результат
        self.assertIsInstance(result, list)
        
    def test_parse_dtc_response_invalid(self):
        """Тест парсинга невалидного ответа"""
        # Тестовые данные
        test_cases = [
            "",                    # Пустая строка
            "43",                  # Неполные данные
            "ERROR",               # Ошибка
            "43 01 00",            # Недостаточно данных
        ]
        
        for test_response in test_cases:
            result = self.diagnostics._parse_dtc_response(test_response)
            self.assertEqual(result, [])
            
    def test_bytes_to_dtc_valid(self):
        """Тест конвертации валидных байтов в DTC"""
        # Тестовые данные: байты и ожидаемые DTC
        test_cases = [
            ("0003", "P0003"),     # Пример кода
            ("0100", "P0100"),     # MAF circuit malfunction
            ("0123", "P0123"),     # Throttle position sensor
            ("0300", "P0300"),     # Random misfire
            ("1000", "C1000"),     # Chassis code
            ("2000", "B2000"),     # Body code
            ("3000", "U3000"),     # Network code
        ]
        
        for hex_bytes, expected_dtc in test_cases:
            result = self.diagnostics._bytes_to_dtc(hex_bytes)
            self.assertEqual(result, expected_dtc)
            
    def test_bytes_to_dtc_invalid(self):
        """Тест конвертации невалидных байтов"""
        # Тестовые данные
        test_cases = [
            "",        # Пустая строка
            "00",      # Недостаточно байт
            "00030",   # Лишние символы
            "ZZZZ",    # Не hex символы
        ]
        
        for hex_bytes in test_cases:
            result = self.diagnostics._bytes_to_dtc(hex_bytes)
            self.assertEqual(result, "0000")
            
    def test_read_live_data_success(self):
        """Тест успешного чтения текущих данных"""
        # Настраиваем мок для разных PID
        def mock_send_command(command):
            # Определяем PID из команды
            if "010C" in command:  # RPM
                return "41 0C 1A F8"
            elif "010D" in command:  # Speed
                return "41 0D 00"
            elif "0105" in command:  # Coolant temp
                return "41 05 7B"
            elif "010F" in command:  # Intake temp
                return "41 0F 47"
            elif "0111" in command:  # Throttle position
                return "41 11 33"
            elif "0110" in command:  # MAF
                return "41 10 03 E8"
            elif "010A" in command:  # Fuel pressure
                return "41 0A 23"
            elif "010B" in command:  # Intake pressure
                return "41 0B 64"
            elif "010E" in command:  # Timing advance
                return "41 0E 46"
            elif "0104" in command:  # Engine load
                return "41 04 4D"
            elif "012F" in command:  # Fuel level
                return "41 2F 66"
            elif "0142" in command:  # Voltage
                return "41 42 0D 48"
            else:
                return "41 00 BE 3F B8 11"
                
        self.mock_connector.send_command.side_effect = mock_send_command
        
        # Выполняем чтение
        result = self.diagnostics._read_live_data()
        
        # Проверяем результат
        self.assertIsInstance(result, dict)
        
        # Проверяем наличие ключевых параметров
        expected_pids = list(NivaProtocols.ENGINE_PIDS.keys())
        for pid_name in expected_pids:
            self.assertIn(pid_name, result)
            self.assertIsInstance(result[pid_name], dict)
            
        # Проверяем значения
        self.assertIn('value', result['ENGINE_RPM'])
        self.assertIn('unit', result['ENGINE_RPM'])
        self.assertEqual(result['ENGINE_RPM']['unit'], 'rpm')
        
    def test_read_live_data_error(self):
        """Тест чтения текущих данных с ошибкой"""
        # Настраиваем мок для вызова исключения
        self.mock_connector.send_command.side_effect = Exception("Test error")
        
        # Выполняем чтение
        result = self.diagnostics._read_live_data()
        
        # Проверяем результат
        self.assertIsInstance(result, dict)
        for pid_name in NivaProtocols.ENGINE_PIDS.keys():
            self.assertIn(pid_name, result)
            self.assertIn('error', result[pid_name])
            
    def test_get_pid_unit(self):
        """Тест получения единиц измерения для PID"""
        # Тестовые данные
        test_cases = [
            ('010C', 'rpm'),
            ('010D', 'km/h'),
            ('0105', '°C'),
            ('010F', '°C'),
            ('0111', '%'),
            ('0110', 'g/s'),
            ('010A', 'kPa'),
            ('010B', 'kPa'),
            ('010E', '°'),
            ('0104', '%'),
            ('012F', '%'),
            ('0142', 'V'),
            ('9999', ''),  # Неизвестный PID
        ]
        
        for pid_code, expected_unit in test_cases:
            result = self.diagnostics._get_pid_unit(pid_code)
            self.assertEqual(result, expected_unit)
            
    def test_clear_dtcs_success(self):
        """Тест успешной очистки ошибок"""
        # Настраиваем мок
        self.mock_connector.send_command.return_value = "44"
        
        # Выполняем очистку
        result = self.diagnostics.clear_dtcs()
        
        # Проверяем результат
        self.assertTrue(result)
        
        # Проверяем количество вызовов
        expected_calls = len(NivaProtocols.ECUS)
        self.assertEqual(self.mock_connector.send_command.call_count, expected_calls)
        
    def test_clear_dtcs_failure(self):
        """Тест неудачной очистки ошибок"""
        # Настраиваем мок для вызова исключения
        self.mock_connector.send_command.side_effect = Exception("Clear failed")
        
        # Выполняем очистку
        result = self.diagnostics.clear_dtcs()
        
        # Проверяем результат
        self.assertFalse(result)
        
    def test_perform_adaptation(self):
        """Тест выполнения адаптации"""
        # Выполняем адаптацию
        result = self.diagnostics.perform_adaptation('THROTTLE_ADAPTATION')
        
        # Проверяем результат
        self.assertTrue(result)
        
    def test_register_callback(self):
        """Тест регистрации коллбэков"""
        # Создаем мок-коллбэк
        mock_callback = Mock()
        
        # Регистрируем коллбэк
        self.diagnostics.register_callback('status', mock_callback)
        
        # Проверяем регистрацию
        self.assertIn('status', self.diagnostics.callbacks)
        self.assertEqual(len(self.diagnostics.callbacks['status']), 1)
        self.assertEqual(self.diagnostics.callbacks['status'][0], mock_callback)
        
        # Регистрируем второй коллбэк
        mock_callback2 = Mock()
        self.diagnostics.register_callback('status', mock_callback2)
        self.assertEqual(len(self.diagnostics.callbacks['status']), 2)
        
    def test_notify_with_callbacks(self):
        """Тест уведомления с зарегистрированными коллбэками"""
        # Создаем мок-коллбэки
        mock_callback1 = Mock()
        mock_callback2 = Mock()
        
        # Регистрируем коллбэки
        self.diagnostics.register_callback('status', mock_callback1)
        self.diagnostics.register_callback('status', mock_callback2)
        self.diagnostics.register_callback('complete', mock_callback1)
        
        # Отправляем уведомление
        test_data = "Test status update"
        self.diagnostics._notify('status', test_data)
        
        # Проверяем вызовы
        mock_callback1.assert_called_once_with(test_data)
        mock_callback2.assert_called_once_with(test_data)
        
        # Проверяем, что другие события не вызвались
        self.diagnostics._notify('error', "Error message")
        self.assertEqual(mock_callback1.call_count, 1)
        
    def test_notify_without_callbacks(self):
        """Тест уведомления без зарегистрированных коллбэков"""
        # Не должно вызывать исключений
        try:
            self.diagnostics._notify('unknown_event', "data")
            success = True
        except Exception:
            success = False
            
        self.assertTrue(success)
        
    def test_concurrent_diagnostics(self):
        """Тест параллельного выполнения нескольких диагностик"""
        # Настраиваем мок
        self.mock_connector.send_command.return_value = "48 6B 10 41 00 BE 3F B8 11"
        
        # Создаем второй экземпляр движка
        diagnostics2 = DiagnosticsEngine(self.mock_connector)
        
        # Запускаем две диагностики
        result1 = self.diagnostics.perform_full_diagnostic(self.test_vehicle_model)
        result2 = diagnostics2.perform_full_diagnostic('2123')
        
        # Проверяем, что они независимы
        self.assertNotEqual(id(self.diagnostics), id(diagnostics2))
        self.assertNotEqual(result1.get('timestamp'), result2.get('timestamp'))
        
        # Очистка
        diagnostics2.is_running = False
        
    def test_diagnostic_results_structure(self):
        """Тест структуры результатов диагностики"""
        # Запускаем диагностику
        result = self.diagnostics.perform_full_diagnostic(self.test_vehicle_model)
        
        # Проверяем структуру
        required_keys = ['timestamp', 'vehicle_model', 'diagnostic_status', 'modules']
        for key in required_keys:
            self.assertIn(key, result)
            
        # Проверяем типы данных
        self.assertIsInstance(result['timestamp'], str)
        self.assertIsInstance(result['vehicle_model'], str)
        self.assertIsInstance(result['diagnostic_status'], str)
        self.assertIsInstance(result['modules'], dict)
        
    @patch('diagnostics_engine.datetime')
    def test_timestamp_generation(self, mock_datetime):
        """Тест генерации timestamp"""
        # Настраиваем мок datetime
        fixed_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = fixed_time
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        # Запускаем диагностику
        result = self.diagnostics.perform_full_diagnostic(self.test_vehicle_model)
        
        # Проверяем timestamp
        expected_timestamp = "2023-01-01T12:00:00"
        self.assertIn(expected_timestamp, result['timestamp'])
        
    def test_vehicle_model_validation(self):
        """Тест валидации модели автомобиля"""
        # Поддерживаемые модели
        supported_models = list(NivaProtocols.SUPPORTED_MODELS.keys())
        
        for model in supported_models:
            result = self.diagnostics.perform_full_diagnostic(model)
            self.assertEqual(result['vehicle_model'], model)
            
        # Неподдерживаемая модель (должна все равно работать)
        unsupported_model = '9999'
        result = self.diagnostics.perform_full_diagnostic(unsupported_model)
        self.assertEqual(result['vehicle_model'], unsupported_model)
        
    def test_diagnostic_thread_safety(self):
        """Тест безопасности потоков"""
        from threading import Thread, Event
        
        # Событие для синхронизации
        event = Event()
        
        # Коллбэк для проверки вызовов
        callback_calls = []
        
        def test_callback(data):
            callback_calls.append(data)
            
        # Регистрируем коллбэк
        self.diagnostics.register_callback('status', test_callback)
        
        # Запускаем диагностику в отдельном потоке
        def run_diagnostic():
            self.diagnostics.perform_full_diagnostic(self.test_vehicle_model)
            event.set()
            
        thread = Thread(target=run_diagnostic)
        thread.start()
        
        # Ждем завершения
        event.wait(timeout=5)
        
        # Проверяем, что коллбэк вызывался
        self.assertGreater(len(callback_calls), 0)
        
        # Очистка
        thread.join()
        
    def test_diagnostics_with_realistic_responses(self):
        """Тест диагностики с реалистичными ответами от ELM327"""
        # Реалистичные ответы для разных команд
        test_responses = {
            # Проверка связи
            '10': "48 6B 10 41 00 BE 3F B8 11",
            # Чтение ошибок
            '03': "43 01 00 03 00 00 00 00",
            # Поддерживаемые PID
            '0100': "41 00 BE 3F B8 11",
            # RPM (1700 RPM)
            '010C': "41 0C 1A F8",
            # Скорость (0 км/ч)
            '010D': "41 0D 00",
            # Температура охлаждающей жидкости (75°C)
            '0105': "41 05 7B",
            # Температура впускного воздуха (39°C)
            '010F': "41 0F 47",
            # Положение дроссельной заслонки (20%)
            '0111': "41 11 33",
            # Массовый расход воздуха (10.0 g/s)
            '0110': "41 10 03 E8",
            # Давление топлива (105 kPa)
            '010A': "41 0A 23",
            # Давление во впускном коллекторе (100 kPa)
            '010B': "41 0B 64",
            # Угол опережения зажигания (-13°)
            '010E': "41 0E 46",
            # Нагрузка на двигатель (30%)
            '0104': "41 04 4D",
            # Уровень топлива (40%)
            '012F': "41 2F 66",
            # Напряжение бортовой сети (13.6V)
            '0142': "41 42 0D 48",
        }
        
        def mock_send_command(command):
            # Извлекаем PID из команды
            for pid, response in test_responses.items():
                if pid in command:
                    return response
            return "NO DATA"
            
        self.mock_connector.send_command.side_effect = mock_send_command
        
        # Запускаем диагностику
        result = self.diagnostics.perform_full_diagnostic(self.test_vehicle_model)
        
        # Ждем завершения
        if self.diagnostics.diagnostic_thread:
            self.diagnostics.diagnostic_thread.join(timeout=2)
            
        # Проверяем результаты
        self.assertEqual(result['diagnostic_status'], 'COMPLETED')
        self.assertIn('live_data', result)
        
        # Проверяем конкретные значения
        if 'live_data' in result and 'ENGINE_RPM' in result['live_data']:
            rpm_data = result['live_data']['ENGINE_RPM']
            self.assertIn('value', rpm_data)
            # 0x1AF8 = 6904 / 4 = 1726 RPM
            self.assertAlmostEqual(rpm_data['value'], 1726.0, delta=1.0)
            
    def test_error_handling_in_diagnostic_worker(self):
        """Тест обработки ошибок в рабочем потоке"""
        # Настраиваем коллбэки
        status_calls = []
        error_calls = []
        complete_calls = []
        
        def status_callback(data):
            status_calls.append(data)
            
        def error_callback(data):
            error_calls.append(data)
            
        def complete_callback(data):
            complete_calls.append(data)
            
        self.diagnostics.register_callback('status', status_callback)
        self.diagnostics.register_callback('error', error_callback)
        self.diagnostics.register_callback('complete', complete_callback)
        
        # Настраиваем мок для вызова исключения на первом шаге
        self.mock_connector.send_command.side_effect = Exception("Simulated error")
        
        # Запускаем диагностику
        self.diagnostics._diagnostic_worker()
        
        # Проверяем, что коллбэки были вызваны
        self.assertGreater(len(status_calls), 0)
        self.assertEqual(len(error_calls), 1)
        self.assertEqual(len(complete_calls), 0)  # При ошибке complete не вызывается
        
        # Проверяем результат
        self.assertEqual(self.diagnostics.results['diagnostic_status'], 'FAILED')
        self.assertIn('error', self.diagnostics.results)
        
    def test_multiple_ecus_diagnostic(self):
        """Тест диагностики нескольких ECU"""
        # Настраиваем мок для разных ECU
        ecu_responses = {
            '10': "48 6B 10 41 00 BE 3F B8 11",  # ENGINE
            '28': "48 6B 28 41 00 FF FF FF",     # ABS
            '15': "48 6B 15 41 00 00 00 00",     # AIRBAG
            '29': "NO DATA",                      # IMMO (нет ответа)
            '25': "48 6B 25 41 00 12 34 56",     # INSTRUMENT
            '08': "48 6B 08 41 00 AA BB CC",     # AC
        }
        
        def mock_send_command(command):
            for ecu_addr, response in ecu_responses.items():
                if ecu_addr in command:
                    return response
            return "NO DATA"
            
        self.mock_connector.send_command.side_effect = mock_send_command
        
        # Выполняем проверку связи
        result = self.diagnostics._check_ecu_communication()
        
        # Проверяем результаты для каждого ECU
        for ecu_name in NivaProtocols.ECUS.keys():
            self.assertIn(ecu_name, result)
            
        # Проверяем конкретные статусы
        self.assertEqual(result['ENGINE']['status'], 'CONNECTED')
        self.assertEqual(result['IMMO']['status'], 'NOT_RESPONDING')
        
    def test_diagnostic_with_custom_callbacks(self):
        """Тест диагностики с пользовательскими коллбэками"""
        # Создаем пользовательский коллбэк для логирования
        log_entries = []
        
        def custom_logger(data):
            log_entries.append(f"[LOG] {data}")
            
        # Регистрируем коллбэк
        self.diagnostics.register_callback('status', custom_logger)
        
        # Настраиваем мок
        self.mock_connector.send_command.return_value = "48 6B 10 41 00 BE 3F B8 11"
        
        # Запускаем диагностику
        self.diagnostics.perform_full_diagnostic(self.test_vehicle_model)
        
        # Ждем завершения
        if self.diagnostics.diagnostic_thread:
            self.diagnostics.diagnostic_thread.join(timeout=2)
            
        # Проверяем логи
        self.assertGreater(len(log_entries), 0)
        self.assertTrue(any("Проверка связи с ЭБУ" in entry for entry in log_entries))
        
    def test_diagnostics_engine_state_transitions(self):
        """Тест переходов состояний движка диагностики"""
        # Начальное состояние
        self.assertFalse(self.diagnostics.is_running)
        self.assertIsNone(self.diagnostics.diagnostic_thread)
        
        # После запуска
        self.diagnostics.perform_full_diagnostic(self.test_vehicle_model)
        self.assertTrue(self.diagnostics.is_running)
        self.assertIsNotNone(self.diagnostics.diagnostic_thread)
        
        # Ждем завершения
        if self.diagnostics.diagnostic_thread:
            self.diagnostics.diagnostic_thread.join(timeout=2)
            
        # Конечное состояние
        self.assertFalse(self.diagnostics.is_running)
        
    def test_diagnostics_with_partial_responses(self):
        """Тест диагностики с частичными ответами"""
        # Настраиваем мок для возврата частичных данных
        partial_responses = [
            "41 0C",        # Неполный ответ
            "1A F8",        # Продолжение
            "41 05 7B",     # Полный ответ
            "",             # Пустой ответ
            "ERROR",        # Ошибка
        ]
        
        self.mock_connector.send_command.side_effect = partial_responses
        
        # Выполняем чтение live data
        result = self.diagnostics._read_live_data()
        
        # Проверяем, что функция обработала частичные ответы
        self.assertIsInstance(result, dict)
        
        # Должны быть записи для всех PID, даже с ошибками
        for pid_name in NivaProtocols.ENGINE_PIDS.keys():
            self.assertIn(pid_name, result)
            
    def test_diagnostics_with_timeout_handling(self):
        """Тест обработки таймаутов в диагностике"""
        import time
        
        # Мок с задержкой
        def delayed_response(command):
            time.sleep(0.1)  # Имитация задержки
            return "41 0C 1A F8"
            
        self.mock_connector.send_command.side_effect = delayed_response
        
        # Запускаем диагностику с таймаутом
        start_time = time.time()
        result = self.diagnostics.perform_full_diagnostic(self.test_vehicle_model)
        
        # Ждем завершения
        if self.diagnostics.diagnostic_thread:
            self.diagnostics.diagnostic_thread.join(timeout=1)
            
        end_time = time.time()
        
        # Проверяем, что диагностика завершилась
        self.assertGreater(end_time - start_time, 0.1)
        self.assertFalse(self.diagnostics.is_running)
        
    def test_diagnostics_memory_usage(self):
        """Тест использования памяти при диагностике"""
        import gc
        
        # Собираем мусор перед тестом
        gc.collect()
        
        # Запоминаем количество объектов
        initial_objects = len(gc.get_objects())
        
        # Выполняем диагностику несколько раз
        for i in range(3):
            self.diagnostics.perform_full_diagnostic(self.test_vehicle_model)
            if self.diagnostics.diagnostic_thread:
                self.diagnostics.diagnostic_thread.join(timeout=1)
                
        # Снова собираем мусор
        gc.collect()
        
        # Проверяем, что не было утечек памяти
        final_objects = len(gc.get_objects())
        # Допускаем небольшое увеличение из-за кэширования
        self.assertLess(final_objects - initial_objects, 100)


class TestNivaProtocolsIntegration(unittest.TestCase):
    """Тесты интеграции с NivaProtocols"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.protocols = NivaProtocols()
        
    def test_build_command(self):
        """Тест построения команд"""
        # Без ECU
        cmd = self.protocols.build_command('01', '0C')
        self.assertEqual(cmd, '010C')
        
        # С ECU
        cmd = self.protocols.build_command('01', '0C', '10')
        self.assertEqual(cmd, '10010C')
        
    def test_parse_response_rpm(self):
        """Тест парсинга ответа для RPM"""
        # 0x1AF8 = 6904 / 4 = 1726 RPM
        response = "41 0C 1A F8"
        result = self.protocols.parse_response(response, '010C')
        self.assertEqual(result, 1726.0)
        
    def test_parse_response_speed(self):
        """Тест парсинга ответа для скорости"""
        # 0x00 = 0 км/ч
        response = "41 0D 00"
        result = self.protocols.parse_response(response, '010D')
        self.assertEqual(result, 0)
        
    def test_parse_response_coolant_temp(self):
        """Тест парсинга ответа для температуры охлаждающей жидкости"""
        # 0x7B = 123 - 40 = 83°C
        response = "41 05 7B"
        result = self.protocols.parse_response(response, '0105')
        self.assertEqual(result, 83)
        
    def test_parse_response_throttle_position(self):
        """Тест парсинга ответа для положения дроссельной заслонки"""
        # 0x33 = 51 * 100 / 255 ≈ 20%
        response = "41 11 33"
        result = self.protocols.parse_response(response, '0111')
        self.assertAlmostEqual(result, 20.0, delta=0.1)
        
    def test_parse_response_voltage(self):
        """Тест парсинга ответа для напряжения"""
        # 0x0D48 = 3400 / 1000 = 3.4V (но это должно быть 13.6V)
        # Правильный расчет: 0x0D48 = 3400, 3400 / 1000 = 3.4 - это неверно
        # По спецификации OBD-II, PID 0x42 возвращает напряжение в мВ
        # 0x0D48 = 3400 мВ = 3.4V
        response = "41 42 0D 48"
        result = self.protocols.parse_response(response, '0142')
        self.assertEqual(result, 3.4)
        
    def test_parse_response_invalid(self):
        """Тест парсинга невалидного ответа"""
        test_cases = [
            ("", '010C'),           # Пустой ответ
            ("ERROR", '010C'),      # Ошибка
            ("41", '010C'),         # Неполный ответ
            ("ZZ ZZ", '010C'),      # Не hex символы
        ]
        
        for response, pid in test_cases:
            result = self.protocols.parse_response(response, pid)
            self.assertIsNone(result)
            
    def test_supported_models(self):
        """Тест поддерживаемых моделей"""
        models = self.protocols.SUPPORTED_MODELS
        self.assertIsInstance(models, dict)
        self.assertGreater(len(models), 0)
        
        # Проверяем наличие ключевых моделей
        self.assertIn('2123', models)
        self.assertIn('21236', models)
        self.assertIn('2123-250', models)
        self.assertIn('2123M', models)
        
    def test_ecu_addresses(self):
        """Тест адресов ECU"""
        ecus = self.protocols.ECUS
        self.assertIsInstance(ecus, dict)
        
        # Проверяем ключевые ECU
        expected_ecus = ['ENGINE', 'ABS', 'AIRBAG', 'IMMO', 'INSTRUMENT', 'AC']
        for ecu in expected_ecus:
            self.assertIn(ecu, ecus)
            self.assertIsInstance(ecus[ecu], str)
            
    def test_engine_pids(self):
        """Тест PID двигателя"""
        pids = self.protocols.ENGINE_PIDS
        self.assertIsInstance(pids, dict)
        self.assertGreater(len(pids), 0)
        
        # Проверяем ключевые PID
        key_pids = ['ENGINE_RPM', 'VEHICLE_SPEED', 'COOLANT_TEMP', 
                   'THROTTLE_POSITION', 'MAF_SENSOR', 'CONTROL_MODULE_VOLTAGE']
        
        for pid in key_pids:
            self.assertIn(pid, pids)
            self.assertIsInstance(pids[pid], str)
            self.assertEqual(len(pids[pid]), 4)  # 4 hex символа
            
    def test_diagnostic_modes(self):
        """Тест режимов диагностики"""
        modes = self.protocols.MODES
        self.assertIsInstance(modes, dict)
        
        # Проверяем ключевые режимы
        expected_modes = ['CURRENT_DATA', 'FREEZE_FRAME', 'STORED_DTCS',
                         'CLEAR_DTCS', 'O2_SENSOR_TEST', 'TEST_RESULTS',
                         'PENDING_DTCS', 'CONTROL_OPERATIONS', 'VEHICLE_INFO',
                         'PERMANENT_DTCS']
        
        for mode in expected_modes:
            self.assertIn(mode, modes)
            self.assertIsInstance(modes[mode], str)
            self.assertEqual(len(modes[mode]), 2)  # 2 hex символа
            
    def test_adaptation_commands(self):
        """Тест команд адаптации"""
        commands = self.protocols.ADAPTATION_COMMANDS
        self.assertIsInstance(commands, dict)
        
        # Проверяем ключевые команды
        key_commands = ['IDLE_ADAPTATION', 'THROTTLE_ADAPTATION', 'LEARN_VALUES',
                       'FUEL_TRIM_RESET', 'IMMO_LEARN']
        
        for cmd in key_commands:
            self.assertIn(cmd, commands)
            self.assertIsInstance(commands[cmd], str)
            self.assertTrue(commands[cmd].startswith('AT '))


class TestDiagnosticsPerformance(unittest.TestCase):
    """Тесты производительности диагностики"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.mock_connector = Mock(spec=ELM327Connector)
        self.mock_connector.is_connected = True
        self.mock_connector.send_command = Mock(return_value="41 0C 1A F8")
        self.diagnostics = DiagnosticsEngine(self.mock_connector)
        
    def test_diagnostic_speed(self):
        """Тест скорости выполнения диагностики"""
        import time
        
        # Запускаем диагностику
        start_time = time.time()
        result = self.diagnostics.perform_full_diagnostic('21236')
        
        # Ждем завершения
        if self.diagnostics.diagnostic_thread:
            self.diagnostics.diagnostic_thread.join(timeout=5)
            
        end_time = time.time()
        duration = end_time - start_time
        
        # Проверяем, что диагностика завершилась за разумное время
        self.assertLess(duration, 10.0)  # Должно быть меньше 10 секунд
        
    def test_concurrent_diagnostics_performance(self):
        """Тест производительности при параллельной диагностике"""
        import time
        from threading import Thread
        
        # Создаем несколько движков диагностики
        num_diagnostics = 5
        diagnostics_list = []
        threads = []
        
        for i in range(num_diagnostics):
            mock_conn = Mock(spec=ELM327Connector)
            mock_conn.is_connected = True
            mock_conn.send_command = Mock(return_value="41 0C 1A F8")
            
            diag = DiagnosticsEngine(mock_conn)
            diagnostics_list.append(diag)
            
        # Запускаем все диагностики одновременно
        start_time = time.time()
        
        for diag in diagnostics_list:
            thread = Thread(target=diag.perform_full_diagnostic, args=('21236',))
            threads.append(thread)
            thread.start()
            
        # Ждем завершения всех потоков
        for thread in threads:
            thread.join(timeout=10)
            
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Проверяем, что общее время разумное
        # Каждая диагностика ~1 секунда, но они выполняются параллельно
        self.assertLess(total_duration, 15.0)
        
        # Очистка
        for diag in diagnostics_list:
            diag.is_running = False
            
    def test_memory_efficiency(self):
        """Тест эффективности использования памяти"""
        import sys
        import gc
        
        # Измеряем память перед тестом
        gc.collect()
        initial_memory = []
        
        # Собираем данные о памяти нескольких объектов
        for i in range(100):
            mock_conn = Mock(spec=ELM327Connector)
            diag = DiagnosticsEngine(mock_conn)
            initial_memory.append(sys.getsizeof(diag))
            
        # Средний размер объекта
        avg_size = sum(initial_memory) / len(initial_memory)
        
        # Проверяем, что размер объекта разумен
        self.assertLess(avg_size, 10000)  # Меньше 10KB на объект
        
    def test_response_parsing_performance(self):
        """Тест производительности парсинга ответов"""
        import time
        
        # Тестовые данные
        test_responses = [
            ("41 0C 1A F8", '010C'),  # RPM
            ("41 0D 00", '010D'),     # Speed
            ("41 05 7B", '0105'),     # Coolant temp
            ("41 11 33", '0111'),     # Throttle position
            ("41 42 0D 48", '0142'),  # Voltage
        ] * 1000  # 5000 запросов
        
        start_time = time.time()
        
        for response, pid in test_responses:
            result = self.diagnostics.protocols.parse_response(response, pid)
            # Просто чтобы избежать оптимизации
            if result is None:
                pass
                
        end_time = time.time()
        duration = end_time - start_time
        
        # Проверяем скорость парсинга (должно быть быстро)
        self.assertLess(duration, 1.0)  # Меньше 1 секунды на 5000 парсингов
        
    def test_command_building_performance(self):
        """Тест производительности построения команд"""
        import time
        
        # Тестовые данные
        test_cases = [
            ('01', '0C', None),    # Без ECU
            ('01', '0C', '10'),    # С ECU
            ('03', '', '10'),      # Чтение ошибок
            ('04', '', '10'),      # Очистка ошибок
        ] * 1000  # 4000 операций
        
        start_time = time.time()
        
        for mode, pid, ecu in test_cases:
            cmd = self.diagnostics.protocols.build_command(mode, pid, ecu)
            # Просто чтобы избежать оптимизации
            if not cmd:
                pass
                
        end_time = time.time()
        duration = end_time - start_time
        
        # Проверяем скорость построения команд
        self.assertLess(duration, 0.5)  # Меньше 0.5 секунды на 4000 операций


if __name__ == '__main__':
    # Создаем test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDiagnosticsEngine)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestNivaProtocolsIntegration))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDiagnosticsPerformance))
    
    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Выводим статистику
    print(f"\n{'='*60}")
    print(f"Всего тестов: {result.testsRun}")
    print(f"Провалено: {len(result.failures)}")
    print(f"Ошибок: {len(result.errors)}")
    print(f"Пропущено: {len(result.skipped)}")
    
    if result.failures:
        print("\nПроваленные тесты:")
        for test, traceback in result.failures:
            print(f"  {test}:")
            print(f"    {traceback.splitlines()[-1]}")
            
    if result.errors:
        print("\nТесты с ошибками:")
        for test, traceback in result.errors:
            print(f"  {test}:")
            print(f"    {traceback.splitlines()[-1]}")