"""
Модуль для создания специализированных графиков и диаграмм
для отображения диагностических данных
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QComboBox, QCheckBox, QPushButton,
                             QSpinBox, QDoubleSpinBox, QGroupBox, QFrame,
                             QColorDialog, QInputDialog)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QDateTime, QPointF
from PyQt5.QtGui import QColor, QPen, QBrush, QPainter, QFont, QPainterPath
import pyqtgraph as pg
import numpy as np
from collections import deque
import time
import json
import os

pg.setConfigOptions(antialias=True, foreground='w', background='#1e1e1e')


class RealTimeChart(QWidget):
    """График реального времени"""
    
    data_updated = pyqtSignal(str, float)
    
    def __init__(self, title="", y_label="", unit="", parent=None):
        super().__init__(parent)
        self.title = title
        self.y_label = y_label
        self.unit = unit
        self.buffer_size = 1000
        self.sample_rate = 100  # мс
        self.is_paused = False
        self.is_recording = False
        self.recording_data = []
        self.setup_ui()
        self.setup_data()
        
    def setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Панель управления
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(0, 0, 0, 0)
        
        # Заголовок
        self.title_label = QLabel(f"<h3>{self.title}</h3>")
        control_layout.addWidget(self.title_label)
        
        control_layout.addStretch()
        
        # Кнопки управления
        self.pause_btn = QPushButton("⏸")
        self.pause_btn.setFixedSize(30, 30)
        self.pause_btn.setToolTip("Пауза")
        self.pause_btn.clicked.connect(self.toggle_pause)
        control_layout.addWidget(self.pause_btn)
        
        self.clear_btn = QPushButton("🗑")
        self.clear_btn.setFixedSize(30, 30)
        self.clear_btn.setToolTip("Очистить")
        self.clear_btn.clicked.connect(self.clear_chart)
        control_layout.addWidget(self.clear_btn)
        
        self.record_btn = QPushButton("●")
        self.record_btn.setFixedSize(30, 30)
        self.record_btn.setToolTip("Запись")
        self.record_btn.setStyleSheet("color: red;")
        self.record_btn.clicked.connect(self.toggle_recording)
        control_layout.addWidget(self.record_btn)
        
        self.export_btn = QPushButton("📤")
        self.export_btn.setFixedSize(30, 30)
        self.export_btn.setToolTip("Экспорт")
        self.export_btn.clicked.connect(self.export_data)
        control_layout.addWidget(self.export_btn)
        
        layout.addWidget(control_panel)
        
        # График
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1e1e1e')
        self.plot_widget.setLabel('left', f'{self.y_label}', units=self.unit)
        self.plot_widget.setLabel('bottom', 'Время', units='с')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setMouseEnabled(x=True, y=True)
        self.plot_widget.enableAutoRange(axis=pg.ViewBox.XAxis)
        
        # Легенда
        self.plot_widget.addLegend(offset=(10, 10))
        
        # Кривая данных
        self.curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#00ff00', width=2),
            name='Значение'
        )
        
        # Кривая среднего
        self.mean_curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#ffaa00', width=1, style=Qt.DashLine),
            name='Среднее'
        )
        
        # Текст статистики
        self.stats_text = pg.TextItem("", color='#ffffff', anchor=(1, 1))
        self.plot_widget.addItem(self.stats_text)
        self.stats_text.setPos(1, 1)
        
        layout.addWidget(self.plot_widget)
        
        # Панель статистики
        stats_panel = QWidget()
        stats_layout = QHBoxLayout(stats_panel)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        
        self.current_label = QLabel("Текущее: --")
        self.min_label = QLabel("Мин: --")
        self.max_label = QLabel("Макс: --")
        self.mean_label = QLabel("Среднее: --")
        
        for label in [self.current_label, self.min_label, 
                      self.max_label, self.mean_label]:
            label.setStyleSheet("color: #888; font-size: 10pt;")
            stats_layout.addWidget(label)
            
        stats_layout.addStretch()
        
        # Настройки отображения
        self.show_mean_cb = QCheckBox("Показать среднее")
        self.show_mean_cb.setChecked(True)
        self.show_mean_cb.stateChanged.connect(self.toggle_mean)
        stats_layout.addWidget(self.show_mean_cb)
        
        layout.addWidget(stats_panel)
        
    def setup_data(self):
        """Инициализация данных"""
        self.time_data = deque(maxlen=self.buffer_size)
        self.value_data = deque(maxlen=self.buffer_size)
        self.mean_data = deque(maxlen=self.buffer_size)
        
        self.start_time = time.time()
        self.last_update = self.start_time
        
        # Таймер обновления
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(self.sample_rate)
        
    def add_data_point(self, value):
        """Добавление точки данных"""
        if self.is_paused:
            return
            
        current_time = time.time() - self.start_time
        self.time_data.append(current_time)
        self.value_data.append(value)
        
        # Расчет скользящего среднего
        window_size = min(10, len(self.value_data))
        if window_size > 0:
            mean_value = sum(list(self.value_data)[-window_size:]) / window_size
            self.mean_data.append(mean_value)
            
        # Запись данных
        if self.is_recording:
            self.recording_data.append({
                'timestamp': current_time,
                'value': value,
                'datetime': QDateTime.currentDateTime().toString('hh:mm:ss.zzz')
            })
            
        self.update_statistics()
        
    def update_display(self):
        """Обновление отображения графика"""
        if not self.value_data:
            return
            
        # Обновление кривой
        self.curve.setData(list(self.time_data), list(self.value_data))
        
        if self.show_mean_cb.isChecked() and self.mean_data:
            self.mean_curve.setData(list(self.time_data), list(self.mean_data))
            
        # Автомасштабирование
        if len(self.value_data) > 1:
            self.plot_widget.enableAutoRange()
            
    def update_statistics(self):
        """Обновление статистики"""
        if not self.value_data:
            return
            
        values = list(self.value_data)
        current_value = values[-1]
        
        # Обновление меток
        self.current_label.setText(f"Текущее: {current_value:.2f} {self.unit}")
        self.min_label.setText(f"Мин: {min(values):.2f} {self.unit}")
        self.max_label.setText(f"Макс: {max(values):.2f} {self.unit}")
        self.mean_label.setText(f"Среднее: {np.mean(values):.2f} {self.unit}")
        
        # Обновление текста на графике
        stats_text = (
            f"Текущее: {current_value:.2f}{self.unit}\n"
            f"Мин: {min(values):.2f}{self.unit}\n"
            f"Макс: {max(values):.2f}{self.unit}\n"
            f"Среднее: {np.mean(values):.2f}{self.unit}"
        )
        self.stats_text.setText(stats_text)
        
    @pyqtSlot()
    def toggle_pause(self):
        """Переключение паузы"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.setText("▶")
            self.pause_btn.setToolTip("Продолжить")
        else:
            self.pause_btn.setText("⏸")
            self.pause_btn.setToolTip("Пауза")
            
    @pyqtSlot()
    def toggle_recording(self):
        """Переключение записи"""
        self.is_recording = not self.is_recording
        if self.is_recording:
            self.record_btn.setStyleSheet("color: #ff0000; font-weight: bold;")
            self.recording_data = []
        else:
            self.record_btn.setStyleSheet("color: red;")
            
    @pyqtSlot()
    def clear_chart(self):
        """Очистка графика"""
        self.time_data.clear()
        self.value_data.clear()
        self.mean_data.clear()
        self.curve.clear()
        self.mean_curve.clear()
        self.start_time = time.time()
        self.update_statistics()
        
    @pyqtSlot()
    def export_data(self):
        """Экспорт данных"""
        if not self.value_data:
            return
            
        # Здесь должна быть реализация диалога сохранения
        # Пока просто сохраняем в файл
        data = {
            'title': self.title,
            'y_label': self.y_label,
            'unit': self.unit,
            'data': list(zip(list(self.time_data), list(self.value_data))),
            'statistics': {
                'min': min(self.value_data),
                'max': max(self.value_data),
                'mean': np.mean(list(self.value_data)),
                'std': np.std(list(self.value_data))
            }
        }
        
        # В реальном приложении здесь будет QFileDialog
        print(f"Экспорт данных: {self.title}")
        
    @pyqtSlot(int)
    def toggle_mean(self, state):
        """Показать/скрыть среднее"""
        if state == Qt.Checked:
            self.mean_curve.show()
        else:
            self.mean_curve.hide()


class MultiParameterChart(QWidget):
    """График с несколькими параметрами"""
    
    def __init__(self, title="Мультипараметрический график", parent=None):
        super().__init__(parent)
        self.title = title
        self.parameters = {}
        self.curves = {}
        self.data_buffers = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Панель заголовка
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.title_label = QLabel(f"<h3>{self.title}</h3>")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Кнопка настроек
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(30, 30)
        self.settings_btn.setToolTip("Настройки")
        self.settings_btn.clicked.connect(self.show_settings)
        header_layout.addWidget(self.settings_btn)
        
        layout.addWidget(header)
        
        # График
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1e1e1e')
        self.plot_widget.setLabel('left', 'Значения')
        self.plot_widget.setLabel('bottom', 'Время', units='с')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend(offset=(10, 10))
        
        # ViewBox для правой оси
        self.right_vb = pg.ViewBox()
        self.plot_widget.scene().addItem(self.right_vb)
        self.plot_widget.getAxis('right').linkToView(self.right_vb)
        self.right_vb.setXLink(self.plot_widget)
        
        # Обновление ViewBox при изменении размеров
        self.plot_widget.vb.sigResized.connect(self.update_views)
        
        layout.addWidget(self.plot_widget)
        
        # Панель параметров
        self.params_panel = QGroupBox("Параметры")
        params_layout = QGridLayout(self.params_panel)
        
        # Заголовки столбцов
        params_layout.addWidget(QLabel("Параметр"), 0, 0)
        params_layout.addWidget(QLabel("Цвет"), 0, 1)
        params_layout.addWidget(QLabel("Включен"), 0, 2)
        params_layout.addWidget(QLabel("Ось"), 0, 3)
        params_layout.addWidget(QLabel("Ширина"), 0, 4)
        
        layout.addWidget(self.params_panel)
        
        # Таймер обновления
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_chart)
        self.update_timer.start(100)
        
    def update_views(self):
        """Обновление ViewBox"""
        self.right_vb.setGeometry(self.plot_widget.vb.sceneBoundingRect())
        self.right_vb.linkedViewChanged(self.plot_widget.vb, 
                                       self.right_vb.XAxis)
        
    def add_parameter(self, name, color=None, enabled=True, axis='left', 
                     line_width=2, buffer_size=500):
        """Добавление параметра для отображения"""
        if not color:
            color = self.get_next_color()
            
        # Создание кривой
        if axis == 'left':
            curve = self.plot_widget.plot(pen=pg.mkPen(color=color, width=line_width), name=name)
        else:
            curve = pg.PlotCurveItem(pen=pg.mkPen(color=color, width=line_width), name=name)
            self.right_vb.addItem(curve)
            
        # Буфер данных
        self.data_buffers[name] = {
            'time': deque(maxlen=buffer_size),
            'values': deque(maxlen=buffer_size),
            'axis': axis,
            'color': color,
            'enabled': enabled,
            'line_width': line_width
        }
        
        self.curves[name] = curve
        
        # Добавление в панель параметров
        self.add_parameter_to_panel(name, color, enabled, axis, line_width)
        
    def add_parameter_to_panel(self, name, color, enabled, axis, line_width):
        """Добавление параметра в панель управления"""
        params_layout = self.params_panel.layout()
        row = params_layout.rowCount()
        
        # Название параметра
        name_label = QLabel(name)
        params_layout.addWidget(name_label, row, 0)
        
        # Цвет
        color_btn = QPushButton()
        color_btn.setFixedSize(20, 20)
        color_btn.setStyleSheet(f"background-color: {color.name()};")
        color_btn.clicked.connect(lambda: self.change_color(name))
        params_layout.addWidget(color_btn, row, 1)
        
        # Checkbox включения
        enabled_cb = QCheckBox()
        enabled_cb.setChecked(enabled)
        enabled_cb.stateChanged.connect(lambda s, n=name: self.toggle_parameter(n, s))
        params_layout.addWidget(enabled_cb, row, 2)
        
        # Выбор оси
        axis_combo = QComboBox()
        axis_combo.addItems(['Левая', 'Правая'])
        axis_combo.setCurrentText('Левая' if axis == 'left' else 'Правая')
        axis_combo.currentTextChanged.connect(lambda a, n=name: self.change_axis(n, a))
        params_layout.addWidget(axis_combo, row, 3)
        
        # Ширина линии
        width_spin = QSpinBox()
        width_spin.setRange(1, 5)
        width_spin.setValue(line_width)
        width_spin.valueChanged.connect(lambda w, n=name: self.change_line_width(n, w))
        params_layout.addWidget(width_spin, row, 4)
        
    def add_data_point(self, param_name, value):
        """Добавление точки данных для параметра"""
        if param_name not in self.data_buffers:
            return
            
        buffer = self.data_buffers[param_name]
        if not buffer['enabled']:
            return
            
        current_time = time.time()
        if not buffer['time']:
            buffer['start_time'] = current_time
            
        elapsed_time = current_time - buffer['start_time']
        buffer['time'].append(elapsed_time)
        buffer['values'].append(value)
        
    def update_chart(self):
        """Обновление графика"""
        for name, buffer in self.data_buffers.items():
            if not buffer['enabled'] or not buffer['time']:
                continue
                
            curve = self.curves[name]
            curve.setData(list(buffer['time']), list(buffer['values']))
            
    def get_next_color(self):
        """Получение следующего цвета из палитры"""
        colors = [
            QColor('#00ff00'),  # зеленый
            QColor('#ff0000'),  # красный
            QColor('#0000ff'),  # синий
            QColor('#ffff00'),  # желтый
            QColor('#ff00ff'),  # пурпурный
            QColor('#00ffff'),  # голубой
            QColor('#ff8800'),  # оранжевый
            QColor('#8800ff'),  # фиолетовый
        ]
        
        used_colors = [buf['color'] for buf in self.data_buffers.values()]
        for color in colors:
            if color not in used_colors:
                return color
                
        return QColor('#ffffff')
        
    def change_color(self, param_name):
        """Изменение цвета параметра"""
        color = QColorDialog.getColor()
        if color.isValid():
            buffer = self.data_buffers[param_name]
            buffer['color'] = color
            
            # Обновление кривой
            curve = self.curves[param_name]
            curve.setPen(pg.mkPen(color=color, width=buffer['line_width']))
            
            # Обновление кнопки
            # (нужно найти соответствующую кнопку и обновить её стиль)
            
    def toggle_parameter(self, param_name, state):
        """Включение/выключение параметра"""
        self.data_buffers[param_name]['enabled'] = (state == Qt.Checked)
        
    def change_axis(self, param_name, axis_text):
        """Изменение оси параметра"""
        new_axis = 'left' if axis_text == 'Левая' else 'right'
        buffer = self.data_buffers[param_name]
        
        if buffer['axis'] == new_axis:
            return
            
        # Удаляем со старой оси
        curve = self.curves[param_name]
        if buffer['axis'] == 'left':
            self.plot_widget.removeItem(curve)
        else:
            self.right_vb.removeItem(curve)
            
        # Добавляем на новую ось
        buffer['axis'] = new_axis
        if new_axis == 'left':
            self.plot_widget.addItem(curve)
        else:
            self.right_vb.addItem(curve)
            
    def change_line_width(self, param_name, width):
        """Изменение ширины линии"""
        buffer = self.data_buffers[param_name]
        buffer['line_width'] = width
        curve = self.curves[param_name]
        curve.setPen(pg.mkPen(color=buffer['color'], width=width))
        
    def show_settings(self):
        """Показать настройки графика"""
        # Здесь можно реализовать диалог настроек
        pass


class HistogramChart(QWidget):
    """Гистограмма распределения значений"""
    
    def __init__(self, title="Гистограмма", parent=None):
        super().__init__(parent)
        self.title = title
        self.data = []
        self.bins = 20
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Панель управления
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(0, 0, 0, 0)
        
        self.title_label = QLabel(f"<h3>{self.title}</h3>")
        control_layout.addWidget(self.title_label)
        
        control_layout.addStretch()
        
        # Количество бинов
        control_layout.addWidget(QLabel("Бины:"))
        self.bins_spin = QSpinBox()
        self.bins_spin.setRange(5, 100)
        self.bins_spin.setValue(self.bins)
        self.bins_spin.valueChanged.connect(self.update_histogram)
        control_layout.addWidget(self.bins_spin)
        
        # Кнопка обновления
        self.update_btn = QPushButton("Обновить")
        self.update_btn.clicked.connect(self.update_histogram)
        control_layout.addWidget(self.update_btn)
        
        # Кнопка очистки
        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.clicked.connect(self.clear_data)
        control_layout.addWidget(self.clear_btn)
        
        layout.addWidget(control_panel)
        
        # График
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1e1e1e')
        self.plot_widget.setLabel('left', 'Частота')
        self.plot_widget.setLabel('bottom', 'Значения')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # Гистограмма
        self.bar_graph = pg.BarGraphItem(x=[], height=[], width=0)
        self.plot_widget.addItem(self.bar_graph)
        
        layout.addWidget(self.plot_widget)
        
        # Статистика
        self.stats_label = QLabel("Нет данных")
        self.stats_label.setStyleSheet("color: #888; font-size: 10pt;")
        layout.addWidget(self.stats_label)
        
    def set_data(self, data):
        """Установка данных для гистограммы"""
        self.data = data
        self.update_histogram()
        
    def add_data(self, value):
        """Добавление значения"""
        self.data.append(value)
        self.update_histogram()
        
    def update_histogram(self):
        """Обновление гистограммы"""
        if not self.data:
            self.bar_graph.setOpts(x=[], height=[])
            self.stats_label.setText("Нет данных")
            return
            
        # Расчет гистограммы
        self.bins = self.bins_spin.value()
        hist, bin_edges = np.histogram(self.data, bins=self.bins)
        
        # Центры бинов
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        bin_width = bin_edges[1] - bin_edges[0]
        
        # Обновление графика
        self.bar_graph.setOpts(x=bin_centers, height=hist, width=bin_width*0.8)
        
        # Обновление статистики
        stats = self.calculate_statistics()
        stats_text = (
            f"Кол-во: {len(self.data)} | "
            f"Среднее: {stats['mean']:.2f} | "
            f"Медиана: {stats['median']:.2f} | "
            f"Стд: {stats['std']:.2f} | "
            f"Мин: {stats['min']:.2f} | "
            f"Макс: {stats['max']:.2f}"
        )
        self.stats_label.setText(stats_text)
        
    def calculate_statistics(self):
        """Расчет статистики"""
        if not self.data:
            return {}
            
        data_array = np.array(self.data)
        return {
            'count': len(self.data),
            'mean': np.mean(data_array),
            'median': np.median(data_array),
            'std': np.std(data_array),
            'min': np.min(data_array),
            'max': np.max(data_array),
            'q25': np.percentile(data_array, 25),
            'q75': np.percentile(data_array, 75)
        }
        
    def clear_data(self):
        """Очистка данных"""
        self.data = []
        self.update_histogram()


class ScatterPlot(QWidget):
    """Точечная диаграмма для анализа корреляции"""
    
    def __init__(self, title="Диаграмма рассеяния", parent=None):
        super().__init__(parent)
        self.title = title
        self.x_data = []
        self.y_data = []
        self.labels = []
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Панель управления
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(0, 0, 0, 0)
        
        self.title_label = QLabel(f"<h3>{self.title}</h3>")
        control_layout.addWidget(self.title_label)
        
        control_layout.addStretch()
        
        # Выбор параметров
        control_layout.addWidget(QLabel("X:"))
        self.x_combo = QComboBox()
        control_layout.addWidget(self.x_combo)
        
        control_layout.addWidget(QLabel("Y:"))
        self.y_combo = QComboBox()
        control_layout.addWidget(self.y_combo)
        
        self.update_plot_btn = QPushButton("Обновить")
        self.update_plot_btn.clicked.connect(self.update_plot)
        control_layout.addWidget(self.update_plot_btn)
        
        layout.addWidget(control_panel)
        
        # График
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1e1e1e')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setMouseEnabled(x=True, y=True)
        
        # Точечная диаграмма
        self.scatter_plot = pg.ScatterPlotItem(size=10, pen=pg.mkPen(None), 
                                              brush=pg.mkBrush(255, 255, 255, 120))
        self.plot_widget.addItem(self.scatter_plot)
        
        # Линия регрессии
        self.regression_line = pg.PlotCurveItem(pen=pg.mkPen('#ff0000', width=2))
        self.plot_widget.addItem(self.regression_line)
        
        layout.addWidget(self.plot_widget)
        
        # Статистика корреляции
        self.correlation_label = QLabel("Коэффициент корреляции: --")
        self.correlation_label.setStyleSheet("color: #888; font-size: 10pt;")
        layout.addWidget(self.correlation_label)
        
    def set_data(self, x_data, y_data, x_label="", y_label="", labels=None):
        """Установка данных"""
        self.x_data = x_data
        self.y_data = y_data
        self.labels = labels or []
        
        # Обновление меток осей
        self.plot_widget.setLabel('bottom', x_label)
        self.plot_widget.setLabel('left', y_label)
        
        # Обновление выпадающих списков
        self.update_combos()
        
        # Обновление графика
        self.update_plot()
        
    def update_combos(self):
        """Обновление выпадающих списков"""
        # В реальном приложении здесь будет обновление из доступных параметров
        pass
        
    def update_plot(self):
        """Обновление графика"""
        if not self.x_data or not self.y_data:
            return
            
        # Обновление точечной диаграммы
        points = []
        for i, (x, y) in enumerate(zip(self.x_data, self.y_data)):
            point = {'pos': (x, y), 'data': i}
            if i < len(self.labels):
                point['tip'] = self.labels[i]
            points.append(point)
            
        self.scatter_plot.setData(points)
        
        # Расчет линии регрессии
        self.calculate_regression()
        
        # Расчет корреляции
        correlation = np.corrcoef(self.x_data, self.y_data)[0, 1]
        self.correlation_label.setText(
            f"Коэффициент корреляции: {correlation:.4f} | "
            f"Коэффициент детерминации (R²): {correlation**2:.4f}"
        )
        
    def calculate_regression(self):
        """Расчет линейной регрессии"""
        if len(self.x_data) < 2:
            return
            
        x_array = np.array(self.x_data)
        y_array = np.array(self.y_data)
        
        # Линейная регрессия
        A = np.vstack([x_array, np.ones(len(x_array))]).T
        m, c = np.linalg.lstsq(A, y_array, rcond=None)[0]
        
        # Точки для линии
        x_min, x_max = min(x_array), max(x_array)
        x_line = np.array([x_min, x_max])
        y_line = m * x_line + c
        
        # Обновление линии
        self.regression_line.setData(x_line, y_line)


class DigitalGauge(QWidget):
    """Цифровой индикатор с графиком истории"""
    
    value_changed = pyqtSignal(float)
    
    def __init__(self, title="", unit="", min_val=0, max_val=100, 
                 warn_threshold=80, danger_threshold=90, parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.min_val = min_val
        self.max_val = max_val
        self.warn_threshold = warn_threshold
        self.danger_threshold = danger_threshold
        self.current_value = 0
        self.history = deque(maxlen=50)
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Заголовок
        self.title_label = QLabel(f"<b>{self.title}</b>")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)
        
        # Основной индикатор
        self.value_display = QLabel("--")
        self.value_display.setAlignment(Qt.AlignCenter)
        self.value_display.setStyleSheet("""
            QLabel {
                font-size: 24pt;
                font-weight: bold;
                padding: 10px;
                border: 2px solid #333;
                border-radius: 10px;
                background-color: #222;
            }
        """)
        layout.addWidget(self.value_display)
        
        # Единица измерения
        self.unit_label = QLabel(self.unit)
        self.unit_label.setAlignment(Qt.AlignCenter)
        self.unit_label.setStyleSheet("color: #888; font-size: 10pt;")
        layout.addWidget(self.unit_label)
        
        # Мини-график истории
        self.history_plot = pg.PlotWidget()
        self.history_plot.setMaximumHeight(80)
        self.history_plot.setBackground('#1e1e1e')
        self.history_plot.hideAxis('bottom')
        self.history_plot.hideAxis('left')
        
        # Линия истории
        self.history_curve = self.history_plot.plot(pen=pg.mkPen('#00ff00', width=2))
        
        # Линии порогов
        if self.warn_threshold:
            warn_line = pg.InfiniteLine(
                pos=self.warn_threshold, 
                angle=0,
                pen=pg.mkPen('#ffff00', width=1, style=Qt.DashLine)
            )
            self.history_plot.addItem(warn_line)
            
        if self.danger_threshold:
            danger_line = pg.InfiniteLine(
                pos=self.danger_threshold, 
                angle=0,
                pen=pg.mkPen('#ff0000', width=1, style=Qt.DashLine)
            )
            self.history_plot.addItem(danger_line)
            
        layout.addWidget(self.history_plot)
        
        # Шкала
        scale_widget = QWidget()
        scale_layout = QHBoxLayout(scale_widget)
        scale_layout.setContentsMargins(0, 0, 0, 0)
        
        self.min_label = QLabel(f"{self.min_val}")
        self.min_label.setStyleSheet("color: #888; font-size: 8pt;")
        scale_layout.addWidget(self.min_label)
        
        scale_layout.addStretch()
        
        self.max_label = QLabel(f"{self.max_val}")
        self.max_label.setStyleSheet("color: #888; font-size: 8pt;")
        scale_layout.addWidget(self.max_label)
        
        layout.addWidget(scale_widget)
        
    def set_value(self, value):
        """Установка значения"""
        self.current_value = value
        self.history.append(value)
        
        # Обновление отображения
        self.value_display.setText(f"{value:.2f}")
        
        # Изменение цвета в зависимости от значения
        if value >= self.danger_threshold:
            color = "#ff0000"
        elif value >= self.warn_threshold:
            color = "#ffff00"
        else:
            color = "#00ff00"
            
        self.value_display.setStyleSheet(f"""
            QLabel {{
                font-size: 24pt;
                font-weight: bold;
                padding: 10px;
                border: 2px solid {color};
                border-radius: 10px;
                background-color: #222;
                color: {color};
            }}
        """)
        
        # Обновление графика истории
        if self.history:
            self.history_curve.setData(list(self.history))
            
        # Сигнал об изменении
        self.value_changed.emit(value)
        
    def get_value(self):
        """Получение текущего значения"""
        return self.current_value


class CompareChart(QWidget):
    """График для сравнения нескольких наборов данных"""
    
    def __init__(self, title="Сравнение данных", parent=None):
        super().__init__(parent)
        self.title = title
        self.datasets = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Панель управления
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(0, 0, 0, 0)
        
        self.title_label = QLabel(f"<h3>{self.title}</h3>")
        control_layout.addWidget(self.title_label)
        
        control_layout.addStretch()
        
        # Тип графика
        control_layout.addWidget(QLabel("Тип:"))
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["Линейный", "Столбчатый", "Точечный"])
        self.chart_type_combo.currentTextChanged.connect(self.update_chart_type)
        control_layout.addWidget(self.chart_type_combo)
        
        layout.addWidget(control_panel)
        
        # График
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1e1e1e')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend(offset=(10, 10))
        
        layout.addWidget(self.plot_widget)
        
        # Легенда
        self.legend_widget = QWidget()
        self.legend_layout = QVBoxLayout(self.legend_widget)
        self.legend_layout.setContentsMargins(10, 10, 10, 10)
        
        legend_group = QGroupBox("Наборы данных")
        legend_group.setLayout(self.legend_layout)
        layout.addWidget(legend_group)
        
    def add_dataset(self, name, data, color=None):
        """Добавление набора данных"""
        if not color:
            color = self.get_next_color()
            
        self.datasets[name] = {
            'data': data,
            'color': color,
            'visible': True,
            'curve': None
        }
        
        self.add_to_legend(name, color)
        self.update_chart()
        
    def add_to_legend(self, name, color):
        """Добавление в легенду"""
        legend_item = QWidget()
        legend_layout = QHBoxLayout(legend_item)
        legend_layout.setContentsMargins(0, 0, 0, 0)
        
        # Цветной квадрат
        color_label = QLabel()
        color_label.setFixedSize(15, 15)
        color_label.setStyleSheet(f"background-color: {color.name()};")
        legend_layout.addWidget(color_label)
        
        # Название
        name_label = QLabel(name)
        legend_layout.addWidget(name_label)
        
        legend_layout.addStretch()
        
        # Checkbox видимости
        visible_cb = QCheckBox()
        visible_cb.setChecked(True)
        visible_cb.stateChanged.connect(
            lambda s, n=name: self.toggle_dataset_visibility(n, s)
        )
        legend_layout.addWidget(visible_cb)
        
        self.legend_layout.addWidget(legend_item)
        
    def update_chart(self):
        """Обновление графика"""
        self.plot_widget.clear()
        
        chart_type = self.chart_type_combo.currentText()
        
        for name, dataset in self.datasets.items():
            if not dataset['visible']:
                continue
                
            data = dataset['data']
            color = dataset['color']
            
            if chart_type == "Линейный":
                curve = self.plot_widget.plot(
                    data, 
                    pen=pg.mkPen(color=color, width=2),
                    name=name
                )
            elif chart_type == "Столбчатый":
                x = np.arange(len(data))
                curve = pg.BarGraphItem(
                    x=x, height=data, width=0.8,
                    brush=pg.mkBrush(color)
                )
                self.plot_widget.addItem(curve)
            elif chart_type == "Точечный":
                x = np.arange(len(data))
                curve = pg.ScatterPlotItem(
                    x=x, y=data, size=10,
                    pen=pg.mkPen(None),
                    brush=pg.mkBrush(color)
                )
                self.plot_widget.addItem(curve)
                
            dataset['curve'] = curve
            
    def update_chart_type(self, chart_type):
        """Изменение типа графика"""
        self.update_chart()
        
    def toggle_dataset_visibility(self, name, state):
        """Переключение видимости набора данных"""
        if name in self.datasets:
            self.datasets[name]['visible'] = (state == Qt.Checked)
            self.update_chart()
            
    def get_next_color(self):
        """Получение следующего цвета"""
        colors = [
            QColor('#ff6b6b'),  # красный
            QColor('#4ecdc4'),  # бирюзовый
            QColor('#45b7d1'),  # голубой
            QColor('#96ceb4'),  # зеленый
            QColor('#feca57'),  # желтый
            QColor('#ff9ff3'),  # розовый
            QColor('#54a0ff'),  # синий
            QColor('#5f27cd'),  # фиолетовый
        ]
        
        used_colors = [ds['color'] for ds in self.datasets.values()]
        for color in colors:
            if color not in used_colors:
                return color
                
        return QColor('#ffffff')


class PerformanceChart(QWidget):
    """График производительности системы"""
    
    def __init__(self, title="Производительность", parent=None):
        super().__init__(parent)
        self.title = title
        self.metrics = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # График
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1e1e1e')
        self.plot_widget.setLabel('left', 'Время', units='мс')
        self.plot_widget.setLabel('bottom', 'Измерение')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # Столбчатая диаграмма
        self.bar_graph = pg.BarGraphItem(x=[], height=[], width=0.5)
        self.plot_widget.addItem(self.bar_graph)
        
        layout.addWidget(self.plot_widget)
        
        # Таблица метрик
        self.metrics_table = QGroupBox("Метрики")
        table_layout = QVBoxLayout(self.metrics_table)
        
        # Заголовки
        headers = QWidget()
        headers_layout = QHBoxLayout(headers)
        headers_layout.setContentsMargins(0, 0, 0, 0)
        
        headers_layout.addWidget(QLabel("<b>Метрика</b>"), 1)
        headers_layout.addWidget(QLabel("<b>Значение</b>"), 1)
        headers_layout.addWidget(QLabel("<b>Единицы</b>"), 1)
        headers_layout.addWidget(QLabel("<b>Статус</b>"), 1)
        
        table_layout.addWidget(headers)
        
        self.metrics_layout = QVBoxLayout()
        table_layout.addLayout(self.metrics_layout)
        
        layout.addWidget(self.metrics_table)
        
    def add_metric(self, name, value, unit="", status="ok"):
        """Добавление метрики"""
        self.metrics[name] = {
            'value': value,
            'unit': unit,
            'status': status
        }
        
        self.add_metric_to_table(name, value, unit, status)
        self.update_chart()
        
    def add_metric_to_table(self, name, value, unit, status):
        """Добавление метрики в таблицу"""
        metric_widget = QWidget()
        metric_layout = QHBoxLayout(metric_widget)
        metric_layout.setContentsMargins(0, 0, 0, 0)
        
        # Название
        name_label = QLabel(name)
        metric_layout.addWidget(name_label, 1)
        
        # Значение
        value_label = QLabel(f"{value:.2f}")
        metric_layout.addWidget(value_label, 1)
        
        # Единицы
        unit_label = QLabel(unit)
        metric_layout.addWidget(unit_label, 1)
        
        # Статус
        status_label = QLabel()
        if status == "ok":
            status_label.setText("✓")
            status_label.setStyleSheet("color: #00ff00;")
        elif status == "warning":
            status_label.setText("⚠")
            status_label.setStyleSheet("color: #ffff00;")
        else:
            status_label.setText("✗")
            status_label.setStyleSheet("color: #ff0000;")
            
        metric_layout.addWidget(status_label, 1)
        
        self.metrics_layout.addWidget(metric_widget)
        
    def update_chart(self):
        """Обновление графика"""
        if not self.metrics:
            return
            
        names = list(self.metrics.keys())
        values = [m['value'] for m in self.metrics.values()]
        x = np.arange(len(names))
        
        # Цвета в зависимости от статуса
        brushes = []
        for metric in self.metrics.values():
            if metric['status'] == "ok":
                brushes.append(pg.mkBrush('#00ff00'))
            elif metric['status'] == "warning":
                brushes.append(pg.mkBrush('#ffff00'))
            else:
                brushes.append(pg.mkBrush('#ff0000'))
                
        self.bar_graph.setOpts(x=x, height=values, brushes=brushes)
        
        # Обновление осей
        self.plot_widget.getAxis('bottom').setTicks([list(zip(x, names))])


# Фабрика графиков
class ChartFactory:
    """Фабрика для создания графиков"""
    
    @staticmethod
    def create_chart(chart_type, **kwargs):
        """Создание графика указанного типа"""
        if chart_type == "realtime":
            return RealTimeChart(**kwargs)
        elif chart_type == "multiparameter":
            return MultiParameterChart(**kwargs)
        elif chart_type == "histogram":
            return HistogramChart(**kwargs)
        elif chart_type == "scatter":
            return ScatterPlot(**kwargs)
        elif chart_type == "gauge":
            return DigitalGauge(**kwargs)
        elif chart_type == "compare":
            return CompareChart(**kwargs)
        elif chart_type == "performance":
            return PerformanceChart(**kwargs)
        else:
            raise ValueError(f"Неизвестный тип графика: {chart_type}")


# Пример использования
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    # Создание примера реального времени
    rt_chart = RealTimeChart(title="Обороты двигателя", 
                           y_label="RPM", 
                           unit="об/мин")
    rt_chart.show()
    
    # Генерация тестовых данных
    import random
    
    def generate_test_data():
        value = 800 + random.random() * 2000
        rt_chart.add_data_point(value)
        
    timer = QTimer()
    timer.timeout.connect(generate_test_data)
    timer.start(100)
    
    sys.exit(app.exec_())