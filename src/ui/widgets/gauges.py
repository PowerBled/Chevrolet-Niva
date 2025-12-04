"""
Модуль с кастомными графическими виджетами-приборами для отображения данных диагностики
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QFontMetrics, QLinearGradient, QRadialGradient
import math


class GaugeWidget(QWidget):
    """Базовый класс для виджетов-приборов"""
    
    valueChanged = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self._min_value = 0.0
        self._max_value = 100.0
        self._target_value = 0.0
        self._unit = ""
        self._title = ""
        self._precision = 1
        self._animation_duration = 500
        self._animation = None
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка UI"""
        self.setMinimumSize(150, 150)
        
    def set_range(self, min_val, max_val):
        """Установка диапазона значений"""
        self._min_value = min_val
        self._max_value = max_val
        self.update()
        
    def set_value(self, value, animated=True):
        """Установка значения с возможностью анимации"""
        value = max(self._min_value, min(self._max_value, value))
        self._target_value = value
        
        if animated:
            if self._animation:
                self._animation.stop()
                
            self._animation = QPropertyAnimation(self, b"animated_value")
            self._animation.setDuration(self._animation_duration)
            self._animation.setStartValue(self._value)
            self._animation.setEndValue(value)
            self._animation.setEasingCurve(QEasingCurve.OutCubic)
            self._animation.valueChanged.connect(lambda val: self.valueChanged.emit(val))
            self._animation.start()
        else:
            self._value = value
            self.update()
            self.valueChanged.emit(value)
            
    def get_value(self):
        """Получение текущего значения"""
        return self._value
        
    def set_unit(self, unit):
        """Установка единиц измерения"""
        self._unit = unit
        self.update()
        
    def set_title(self, title):
        """Установка заголовка"""
        self._title = title
        self.update()
        
    def set_precision(self, precision):
        """Установка точности отображения"""
        self._precision = precision
        self.update()
        
    @property
    def animated_value(self):
        return self._value
        
    @animated_value.setter
    def animated_value(self, value):
        self._value = value
        self.update()


class CircularGauge(GaugeWidget):
    """Круговой прибор (тахометр, спидометр и т.д.)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._start_angle = 135  # Начальный угол в градусах
        self._end_angle = 405    # Конечный угол в градусах
        self._major_ticks = 10   # Количество основных делений
        self._minor_ticks = 5    # Количество промежуточных делений между основными
        self._zones = []         # Зоны цветовой индикации
        self._current_zone_color = QColor(0, 150, 0)
        
    def add_zone(self, start, end, color):
        """Добавление цветовой зоны"""
        self._zones.append({
            'start': start,
            'end': end,
            'color': color
        })
        
    def clear_zones(self):
        """Очистка цветовых зон"""
        self._zones.clear()
        
    def paintEvent(self, event):
        """Отрисовка виджета"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Размеры
        width = self.width()
        height = self.height()
        size = min(width, height) - 20
        center_x = width // 2
        center_y = height // 2
        radius = size // 2
        
        # Отрисовка фона
        self.draw_background(painter, center_x, center_y, radius)
        
        # Отрисовка зон
        self.draw_zones(painter, center_x, center_y, radius)
        
        # Отрисовка шкалы
        self.draw_scale(painter, center_x, center_y, radius)
        
        # Отрисовка стрелки
        self.draw_needle(painter, center_x, center_y, radius)
        
        # Отрисовка центра
        self.draw_center(painter, center_x, center_y)
        
        # Отрисовка текста
        self.draw_text(painter, center_x, center_y, radius)
        
    def draw_background(self, painter, center_x, center_y, radius):
        """Отрисовка фона прибора"""
        # Градиент для фона
        gradient = QRadialGradient(center_x, center_y, radius)
        gradient.setColorAt(0, QColor(50, 50, 50))
        gradient.setColorAt(1, QColor(30, 30, 30))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
        
    def draw_zones(self, painter, center_x, center_y, radius):
        """Отрисовка цветовых зон"""
        if not self._zones:
            return
            
        pen_width = radius // 8
        inner_radius = radius - pen_width // 2
        
        painter.save()
        painter.translate(center_x, center_y)
        
        for zone in self._zones:
            # Вычисляем углы для зоны
            start_percent = (zone['start'] - self._min_value) / (self._max_value - self._min_value)
            end_percent = (zone['end'] - self._min_value) / (self._max_value - self._min_value)
            
            start_angle = self._start_angle + start_percent * (self._end_angle - self._start_angle)
            end_angle = self._start_angle + end_percent * (self._end_angle - self._start_angle)
            
            # Определяем цвет текущей зоны
            if self._value >= zone['start'] and self._value <= zone['end']:
                self._current_zone_color = zone['color']
            
            # Отрисовываем дугу зоны
            pen = QPen(zone['color'], pen_width)
            pen.setCapStyle(Qt.FlatCap)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            
            # Конвертируем углы для Qt (Qt использует 1/16 градуса)
            start_angle_qt = int(start_angle * 16)
            span_angle_qt = int((end_angle - start_angle) * 16)
            
            painter.drawArc(-inner_radius, -inner_radius, inner_radius * 2, inner_radius * 2,
                           start_angle_qt, span_angle_qt)
                           
        painter.restore()
        
    def draw_scale(self, painter, center_x, center_y, radius):
        """Отрисовка шкалы с делениями"""
        painter.save()
        painter.translate(center_x, center_y)
        
        # Основные параметры
        major_tick_length = radius // 10
        minor_tick_length = major_tick_length // 2
        tick_pen_width = max(2, radius // 50)
        
        # Отрисовка делений
        for i in range(self._major_ticks * self._minor_ticks + 1):
            # Вычисляем угол
            angle = self._start_angle + (i / (self._major_ticks * self._minor_ticks)) * \
                   (self._end_angle - self._start_angle)
            angle_rad = math.radians(angle)
            
            # Определяем длину деления
            is_major = i % self._minor_ticks == 0
            tick_length = major_tick_length if is_major else minor_tick_length
            
            # Координаты начала и конца деления
            cos_val = math.cos(angle_rad)
            sin_val = math.sin(angle_rad)
            x1 = (radius - tick_length) * cos_val
            y1 = -(radius - tick_length) * sin_val  # Отрицательный т.к. Qt координаты инвертированы
            x2 = radius * cos_val
            y2 = -radius * sin_val
            
            # Настройка пера
            pen = QPen(QColor(200, 200, 200), tick_pen_width if is_major else tick_pen_width // 2)
            painter.setPen(pen)
            
            # Отрисовка линии
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
            
            # Отрисовка числовых значений для основных делений
            if is_major:
                value = self._min_value + (i / (self._major_ticks * self._minor_ticks)) * \
                       (self._max_value - self._min_value)
                
                # Позиция для текста
                text_radius = radius - tick_length - 20
                text_x = text_radius * cos_val
                text_y = -text_radius * sin_val
                
                # Настройка текста
                painter.save()
                font = QFont("Arial", max(8, radius // 15))
                painter.setFont(font)
                painter.setPen(QColor(220, 220, 220))
                
                # Выравнивание текста
                text = f"{value:.0f}"
                text_rect = QFontMetrics(font).boundingRect(text)
                painter.translate(text_x, text_y)
                painter.drawText(-text_rect.width() // 2, text_rect.height() // 2, text)
                painter.restore()
                
        painter.restore()
        
    def draw_needle(self, painter, center_x, center_y, radius):
        """Отрисовка стрелки"""
        painter.save()
        painter.translate(center_x, center_y)
        
        # Вычисляем угол стрелки
        value_percent = (self._value - self._min_value) / (self._max_value - self._min_value)
        angle = self._start_angle + value_percent * (self._end_angle - self._start_angle)
        angle_rad = math.radians(angle)
        
        # Параметры стрелки
        needle_length = radius * 0.85
        needle_width = max(3, radius // 20)
        tail_length = radius * 0.15
        
        # Градиент для стрелки
        gradient = QLinearGradient(0, 0, needle_length * math.cos(angle_rad), 
                                  -needle_length * math.sin(angle_rad))
        gradient.setColorAt(0, QColor(255, 50, 50))
        gradient.setColorAt(1, QColor(180, 30, 30))
        
        # Рисуем стрелку
        painter.rotate(angle)
        
        # Основная часть стрелки
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(100, 0, 0), 1))
        
        needle_points = [
            QPointF(0, -needle_width // 2),
            QPointF(needle_length, -needle_width // 4),
            QPointF(needle_length, needle_width // 4),
            QPointF(0, needle_width // 2)
        ]
        painter.drawPolygon(needle_points)
        
        # Хвост стрелки
        tail_points = [
            QPointF(0, -needle_width // 2),
            QPointF(-tail_length, -needle_width // 2),
            QPointF(-tail_length, needle_width // 2),
            QPointF(0, needle_width // 2)
        ]
        painter.drawPolygon(tail_points)
        
        painter.restore()
        
    def draw_center(self, painter, center_x, center_y):
        """Отрисовка центральной части"""
        center_radius = max(5, self.width() // 30)
        
        # Градиент для центра
        gradient = QRadialGradient(center_x, center_y, center_radius)
        gradient.setColorAt(0, QColor(200, 200, 200))
        gradient.setColorAt(1, QColor(100, 100, 100))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(50, 50, 50), 2))
        painter.drawEllipse(center_x - center_radius, center_y - center_radius,
                           center_radius * 2, center_radius * 2)
                           
    def draw_text(self, painter, center_x, center_y, radius):
        """Отрисовка текстовой информации"""
        # Заголовок
        if self._title:
            font = QFont("Arial", max(10, radius // 12), QFont.Bold)
            painter.setFont(font)
            painter.setPen(QColor(220, 220, 220))
            
            title_rect = QFontMetrics(font).boundingRect(self._title)
            painter.drawText(center_x - title_rect.width() // 2,
                           center_y - radius // 2, self._title)
                           
        # Текущее значение
        value_font = QFont("Arial", max(12, radius // 8), QFont.Bold)
        painter.setFont(value_font)
        
        # Цвет значения в зависимости от зоны
        painter.setPen(QPen(self._current_zone_color))
        
        value_text = f"{self._value:.{self._precision}f}"
        value_rect = QFontMetrics(value_font).boundingRect(value_text)
        painter.drawText(center_x - value_rect.width() // 2,
                       center_y + value_rect.height() // 2, value_text)
                       
        # Единицы измерения
        if self._unit:
            unit_font = QFont("Arial", max(8, radius // 15))
            painter.setFont(unit_font)
            painter.setPen(QColor(180, 180, 180))
            
            unit_rect = QFontMetrics(unit_font).boundingRect(self._unit)
            painter.drawText(center_x - unit_rect.width() // 2,
                           center_y + radius // 3, self._unit)


class LinearGauge(GaugeWidget):
    """Линейный прибор (уровень топлива, температура и т.д.)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._orientation = Qt.Horizontal
        self._zones = []
        self._show_scale = True
        self._show_value = True
        self._bar_height = 20
        self._current_zone_color = QColor(0, 150, 0)
        
    def set_orientation(self, orientation):
        """Установка ориентации (Horizontal или Vertical)"""
        self._orientation = orientation
        self.update()
        
    def set_bar_height(self, height):
        """Установка высоты полосы"""
        self._bar_height = height
        self.update()
        
    def add_zone(self, start, end, color):
        """Добавление цветовой зоны"""
        self._zones.append({
            'start': start,
            'end': end,
            'color': color
        })
        
    def clear_zones(self):
        """Очистка цветовых зон"""
        self._zones.clear()
        
    def paintEvent(self, event):
        """Отрисовка виджета"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Размеры
        width = self.width()
        height = self.height()
        
        if self._orientation == Qt.Horizontal:
            self.draw_horizontal_gauge(painter, width, height)
        else:
            self.draw_vertical_gauge(painter, width, height)
            
    def draw_horizontal_gauge(self, painter, width, height):
        """Отрисовка горизонтального прибора"""
        # Параметры
        margin = 10
        bar_width = width - 2 * margin
        bar_y = (height - self._bar_height) // 2
        
        # Фон прибора
        painter.setBrush(QColor(40, 40, 40))
        painter.setPen(QPen(QColor(80, 80, 80), 2))
        rounded_rect = QRectF(margin, bar_y, bar_width, self._bar_height)
        painter.drawRoundedRect(rounded_rect, 5, 5)
        
        # Цветовые зоны
        self.draw_horizontal_zones(painter, margin, bar_y, bar_width)
        
        # Текущее значение
        self.draw_horizontal_value(painter, margin, bar_y, bar_width)
        
        # Шкала
        if self._show_scale:
            self.draw_horizontal_scale(painter, margin, bar_y, bar_width, height)
            
        # Текст
        self.draw_horizontal_text(painter, width, height, margin, bar_y)
        
    def draw_horizontal_zones(self, painter, margin, bar_y, bar_width):
        """Отрисовка цветовых зон для горизонтального прибора"""
        if not self._zones:
            return
            
        for zone in self._zones:
            # Вычисляем позиции зоны
            start_percent = (zone['start'] - self._min_value) / (self._max_value - self._min_value)
            end_percent = (zone['end'] - self._min_value) / (self._max_value - self._min_value)
            
            x1 = margin + start_percent * bar_width
            x2 = margin + end_percent * bar_width
            
            # Определяем цвет текущей зоны
            if self._value >= zone['start'] and self._value <= zone['end']:
                self._current_zone_color = zone['color']
            
            # Отрисовываем зону
            painter.setBrush(QBrush(zone['color']))
            painter.setPen(Qt.NoPen)
            zone_rect = QRectF(x1, bar_y, x2 - x1, self._bar_height)
            painter.drawRoundedRect(zone_rect, 5, 5)
            
    def draw_horizontal_value(self, painter, margin, bar_y, bar_width):
        """Отрисовка текущего значения для горизонтального прибора"""
        # Вычисляем позицию указателя
        value_percent = (self._value - self._min_value) / (self._max_value - self._min_value)
        pointer_x = margin + value_percent * bar_width
        
        # Отрисовываем указатель
        pointer_height = self._bar_height + 10
        pointer_y = bar_y - 5
        
        painter.setBrush(QBrush(QColor(220, 220, 220)))
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        
        pointer_points = [
            QPointF(pointer_x - 5, pointer_y),
            QPointF(pointer_x + 5, pointer_y),
            QPointF(pointer_x, pointer_y + pointer_height)
        ]
        painter.drawPolygon(pointer_points)
        
    def draw_horizontal_scale(self, painter, margin, bar_y, bar_width, height):
        """Отрисовка шкалы для горизонтального прибора"""
        painter.save()
        
        # Параметры шкалы
        scale_y = bar_y + self._bar_height + 15
        major_tick_length = 10
        minor_tick_length = 5
        num_ticks = 11  # Количество основных делений
        
        font = QFont("Arial", 8)
        painter.setFont(font)
        painter.setPen(QColor(180, 180, 180))
        
        for i in range(num_ticks):
            # Позиция деления
            x = margin + (i / (num_ticks - 1)) * bar_width
            
            # Значение
            value = self._min_value + (i / (num_ticks - 1)) * (self._max_value - self._min_value)
            
            # Основное деление
            painter.drawLine(x, scale_y, x, scale_y + major_tick_length)
            
            # Текст
            text = f"{value:.0f}"
            text_rect = QFontMetrics(font).boundingRect(text)
            painter.drawText(x - text_rect.width() // 2, scale_y + major_tick_length + text_rect.height(), text)
            
            # Промежуточные деления
            if i < num_ticks - 1:
                for j in range(1, 4):
                    sub_x = x + (j * bar_width) / (4 * (num_ticks - 1))
                    painter.drawLine(sub_x, scale_y, sub_x, scale_y + minor_tick_length)
                    
        painter.restore()
        
    def draw_horizontal_text(self, painter, width, height, margin, bar_y):
        """Отрисовка текста для горизонтального прибора"""
        # Заголовок
        if self._title:
            font = QFont("Arial", 10, QFont.Bold)
            painter.setFont(font)
            painter.setPen(QColor(220, 220, 220))
            
            title_rect = QFontMetrics(font).boundingRect(self._title)
            painter.drawText(width // 2 - title_rect.width() // 2,
                           bar_y - 10, self._title)
                           
        # Текущее значение
        if self._show_value:
            value_font = QFont("Arial", 12, QFont.Bold)
            painter.setFont(value_font)
            painter.setPen(QPen(self._current_zone_color))
            
            value_text = f"{self._value:.{self._precision}f} {self._unit}"
            value_rect = QFontMetrics(value_font).boundingRect(value_text)
            painter.drawText(width // 2 - value_rect.width() // 2,
                           height - 5, value_text)
                           
    def draw_vertical_gauge(self, painter, width, height):
        """Отрисовка вертикального прибора"""
        # Параметры
        margin = 10
        bar_height = height - 2 * margin
        bar_x = (width - self._bar_height) // 2
        
        # Фон прибора
        painter.setBrush(QColor(40, 40, 40))
        painter.setPen(QPen(QColor(80, 80, 80), 2))
        rounded_rect = QRectF(bar_x, margin, self._bar_height, bar_height)
        painter.drawRoundedRect(rounded_rect, 5, 5)
        
        # Цветовые зоны
        self.draw_vertical_zones(painter, bar_x, margin, bar_height)
        
        # Текущее значение
        self.draw_vertical_value(painter, bar_x, margin, bar_height)
        
        # Шкала
        if self._show_scale:
            self.draw_vertical_scale(painter, bar_x, margin, bar_height, width)
            
        # Текст
        self.draw_vertical_text(painter, width, height, bar_x, margin)
        
    def draw_vertical_zones(self, painter, bar_x, margin, bar_height):
        """Отрисовка цветовых зон для вертикального прибора"""
        if not self._zones:
            return
            
        for zone in self._zones:
            # Вычисляем позиции зоны (инвертируем т.к. ось Y направлена вниз)
            start_percent = 1 - (zone['start'] - self._min_value) / (self._max_value - self._min_value)
            end_percent = 1 - (zone['end'] - self._min_value) / (self._max_value - self._min_value)
            
            y1 = margin + start_percent * bar_height
            y2 = margin + end_percent * bar_height
            
            # Определяем цвет текущей зоны
            if self._value >= zone['start'] and self._value <= zone['end']:
                self._current_zone_color = zone['color']
            
            # Отрисовываем зону
            painter.setBrush(QBrush(zone['color']))
            painter.setPen(Qt.NoPen)
            zone_rect = QRectF(bar_x, y1, self._bar_height, y2 - y1)
            painter.drawRoundedRect(zone_rect, 5, 5)
            
    def draw_vertical_value(self, painter, bar_x, margin, bar_height):
        """Отрисовка текущего значения для вертикального прибора"""
        # Вычисляем позицию указателя (инвертируем т.к. ось Y направлена вниз)
        value_percent = 1 - (self._value - self._min_value) / (self._max_value - self._min_value)
        pointer_y = margin + value_percent * bar_height
        
        # Отрисовываем указатель
        pointer_width = self._bar_height + 10
        pointer_x = bar_x - 5
        
        painter.setBrush(QBrush(QColor(220, 220, 220)))
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        
        pointer_points = [
            QPointF(pointer_x, pointer_y - 5),
            QPointF(pointer_x, pointer_y + 5),
            QPointF(pointer_x + pointer_width, pointer_y)
        ]
        painter.drawPolygon(pointer_points)
        
    def draw_vertical_scale(self, painter, bar_x, margin, bar_height, width):
        """Отрисовка шкалы для вертикального прибора"""
        painter.save()
        
        # Параметры шкалы
        scale_x = bar_x + self._bar_height + 15
        major_tick_length = 10
        minor_tick_length = 5
        num_ticks = 11  # Количество основных делений
        
        font = QFont("Arial", 8)
        painter.setFont(font)
        painter.setPen(QColor(180, 180, 180))
        
        for i in range(num_ticks):
            # Позиция деления (инвертируем т.к. ось Y направлена вниз)
            y = margin + (i / (num_ticks - 1)) * bar_height
            
            # Значение
            value = self._min_value + (i / (num_ticks - 1)) * (self._max_value - self._min_value)
            
            # Основное деление
            painter.drawLine(scale_x, y, scale_x + major_tick_length, y)
            
            # Текст
            text = f"{value:.0f}"
            text_rect = QFontMetrics(font).boundingRect(text)
            painter.drawText(scale_x + major_tick_length + 5, y + text_rect.height() // 3, text)
            
            # Промежуточные деления
            if i < num_ticks - 1:
                for j in range(1, 4):
                    sub_y = y + (j * bar_height) / (4 * (num_ticks - 1))
                    painter.drawLine(scale_x, sub_y, scale_x + minor_tick_length, sub_y)
                    
        painter.restore()
        
    def draw_vertical_text(self, painter, width, height, bar_x, margin):
        """Отрисовка текста для вертикального прибора"""
        # Заголовок
        if self._title:
            font = QFont("Arial", 10, QFont.Bold)
            painter.setFont(font)
            painter.setPen(QColor(220, 220, 220))
            
            # Поворачиваем текст на 90 градусов
            painter.save()
            painter.translate(bar_x - 30, height // 2)
            painter.rotate(-90)
            
            title_rect = QFontMetrics(font).boundingRect(self._title)
            painter.drawText(-title_rect.width() // 2, 0, self._title)
            painter.restore()
            
        # Текущее значение
        if self._show_value:
            value_font = QFont("Arial", 12, QFont.Bold)
            painter.setFont(value_font)
            painter.setPen(QPen(self._current_zone_color))
            
            value_text = f"{self._value:.{self._precision}f} {self._unit}"
            value_rect = QFontMetrics(value_font).boundingRect(value_text)
            painter.drawText(width // 2 - value_rect.width() // 2,
                           height - 5, value_text)


class DigitalGauge(QFrame):
    """Цифровой прибор для точного отображения значений"""
    
    valueChanged = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self._unit = ""
        self._title = ""
        self._precision = 2
        self._alarm_min = None
        self._alarm_max = None
        self._normal_color = QColor(0, 200, 0)
        self._alarm_color = QColor(255, 50, 50)
        self._background_color = QColor(30, 30, 30)
        self._text_color = QColor(220, 220, 220)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка UI"""
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setLineWidth(2)
        
        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Заголовок
        self.title_label = QLabel()
        self.title_label.setAlignment(Qt.AlignCenter)
        font = QFont("Arial", 9)
        self.title_label.setFont(font)
        layout.addWidget(self.title_label)
        
        # Значение
        self.value_label = QLabel()
        self.value_label.setAlignment(Qt.AlignCenter)
        value_font = QFont("Consolas", 14, QFont.Bold)
        self.value_label.setFont(value_font)
        layout.addWidget(self.value_label)
        
        # Единицы измерения
        self.unit_label = QLabel()
        self.unit_label.setAlignment(Qt.AlignCenter)
        unit_font = QFont("Arial", 8)
        self.unit_label.setFont(unit_font)
        layout.addWidget(self.unit_label)
        
        self.update_display()
        
    def set_value(self, value):
        """Установка значения"""
        self._value = value
        self.update_display()
        self.valueChanged.emit(value)
        
    def get_value(self):
        """Получение значения"""
        return self._value
        
    def set_unit(self, unit):
        """Установка единиц измерения"""
        self._unit = unit
        self.update_display()
        
    def set_title(self, title):
        """Установка заголовка"""
        self._title = title
        self.update_display()
        
    def set_precision(self, precision):
        """Установка точности"""
        self._precision = precision
        self.update_display()
        
    def set_alarm_limits(self, min_val, max_val):
        """Установка границ тревоги"""
        self._alarm_min = min_val
        self._alarm_max = max_val
        self.update_display()
        
    def set_colors(self, normal_color, alarm_color):
        """Установка цветов"""
        self._normal_color = normal_color
        self._alarm_color = alarm_color
        self.update_display()
        
    def update_display(self):
        """Обновление отображения"""
        # Заголовок
        self.title_label.setText(self._title)
        self.title_label.setStyleSheet(f"color: {self._text_color.name()};")
        
        # Значение
        value_text = f"{self._value:.{self._precision}f}"
        self.value_label.setText(value_text)
        
        # Проверка на тревогу
        is_alarm = False
        if self._alarm_min is not None and self._value < self._alarm_min:
            is_alarm = True
        if self._alarm_max is not None and self._value > self._alarm_max:
            is_alarm = True
            
        # Установка цвета значения
        color = self._alarm_color if is_alarm else self._normal_color
        self.value_label.setStyleSheet(f"color: {color.name()};")
        
        # Единицы измерения
        self.unit_label.setText(self._unit)
        self.unit_label.setStyleSheet(f"color: {self._text_color.name()};")
        
        # Фон
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self._background_color.name()};
                border: 2px solid #555;
                border-radius: 5px;
            }}
        """)


class GroupGaugeWidget(QWidget):
    """Виджет-группа приборов"""
    
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self._title = title
        self.gauges = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка UI"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Заголовок группы
        if self._title:
            self.title_label = QLabel(self._title)
            self.title_label.setAlignment(Qt.AlignCenter)
            font = QFont("Arial", 10, QFont.Bold)
            self.title_label.setFont(font)
            self.title_label.setStyleSheet("color: #4CAF50; padding: 5px;")
            self.main_layout.addWidget(self.title_label)
            
        # Контейнер для приборов
        self.gauges_layout = QHBoxLayout()
        self.gauges_layout.setSpacing(10)
        self.main_layout.addLayout(self.gauges_layout)
        
    def add_gauge(self, name, gauge_widget):
        """Добавление прибора в группу"""
        self.gauges[name] = gauge_widget
        self.gauges_layout.addWidget(gauge_widget)
        
    def remove_gauge(self, name):
        """Удаление прибора из группы"""
        if name in self.gauges:
            self.gauges[name].setParent(None)
            del self.gauges[name]
            
    def get_gauge(self, name):
        """Получение прибора по имени"""
        return self.gauges.get(name)
        
    def set_gauge_value(self, name, value, animated=True):
        """Установка значения прибора"""
        gauge = self.get_gauge(name)
        if gauge:
            gauge.set_value(value, animated)
            
    def clear_gauges(self):
        """Очистка всех приборов"""
        for gauge in self.gauges.values():
            gauge.setParent(None)
        self.gauges.clear()


class TachometerGauge(CircularGauge):
    """Специализированный тахометр"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_title("ОБОРОТЫ ДВИГАТЕЛЯ")
        self.set_unit("об/мин")
        self.set_range(0, 8000)
        self.set_precision(0)
        
        # Добавление цветовых зон для тахометра
        self.add_zone(0, 3000, QColor(0, 200, 0))      # Зеленая зона
        self.add_zone(3000, 5000, QColor(255, 200, 0)) # Желтая зона
        self.add_zone(5000, 8000, QColor(255, 50, 50)) # Красная зона


class SpeedometerGauge(CircularGauge):
    """Специализированный спидометр"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_title("СКОРОСТЬ")
        self.set_unit("км/ч")
        self.set_range(0, 200)
        self.set_precision(0)
        
        # Добавление цветовых зон для спидометра
        self.add_zone(0, 60, QColor(0, 200, 0))       # Зеленая зона
        self.add_zone(60, 120, QColor(255, 200, 0))   # Желтая зона
        self.add_zone(120, 200, QColor(255, 50, 50))  # Красная зона


class TemperatureGauge(CircularGauge):
    """Специализированный датчик температуры"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_title("ТЕМПЕРАТУРА")
        self.set_unit("°C")
        self.set_range(-40, 120)
        self.set_precision(1)
        
        # Добавление цветовых зон для температуры
        self.add_zone(-40, 0, QColor(0, 150, 255))    # Синяя зона (холодно)
        self.add_zone(0, 90, QColor(0, 200, 0))       # Зеленая зона (норма)
        self.add_zone(90, 105, QColor(255, 200, 0))   # Желтая зона (нагревание)
        self.add_zone(105, 120, QColor(255, 50, 50))  # Красная зона (перегрев)


class PressureGauge(CircularGauge):
    """Специализированный датчик давления"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_title("ДАВЛЕНИЕ")
        self.set_unit("кПа")
        self.set_range(0, 500)
        self.set_precision(0)
        
        # Добавление цветовых зон для давления
        self.add_zone(0, 200, QColor(0, 200, 0))      # Зеленая зона
        self.add_zone(200, 350, QColor(255, 200, 0))  # Желтая зона
        self.add_zone(350, 500, QColor(255, 50, 50))  # Красная зона


class FuelLevelGauge(LinearGauge):
    """Специализированный датчик уровня топлива"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_title("УРОВЕНЬ ТОПЛИВА")
        self.set_unit("%")
        self.set_range(0, 100)
        self.set_precision(0)
        self.set_orientation(Qt.Vertical)
        self.set_bar_height(30)
        
        # Добавление цветовых зон для уровня топлива
        self.add_zone(0, 15, QColor(255, 50, 50))     # Красная зона (мало)
        self.add_zone(15, 30, QColor(255, 200, 0))    # Желтая зона (мало)
        self.add_zone(30, 100, QColor(0, 200, 0))     # Зеленая зона (норма)


class VoltageGauge(DigitalGauge):
    """Специализированный вольтметр"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_title("НАПРЯЖЕНИЕ")
        self.set_unit("В")
        self.set_precision(2)
        self.set_alarm_limits(11.5, 15.5)
        
        # Настройка цветов для напряжения
        self.set_colors(QColor(0, 200, 0), QColor(255, 50, 50))


class EngineLoadGauge(LinearGauge):
    """Специализированный датчик нагрузки двигателя"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_title("НАГРУЗКА ДВИГАТЕЛА")
        self.set_unit("%")
        self.set_range(0, 100)
        self.set_precision(1)
        self.set_orientation(Qt.Horizontal)
        
        # Добавление цветовых зон для нагрузки
        self.add_zone(0, 50, QColor(0, 200, 0))       # Зеленая зона
        self.add_zone(50, 80, QColor(255, 200, 0))    # Желтая зона
        self.add_zone(80, 100, QColor(255, 50, 50))   # Красная зона


class OilPressureGauge(CircularGauge):
    """Специализированный датчик давления масла"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_title("ДАВЛЕНИЕ МАСЛА")
        self.set_unit("кПа")
        self.set_range(0, 10)
        self.set_precision(1)
        
        # Добавление цветовых зон для давления масла
        self.add_zone(0, 2, QColor(255, 50, 50))      # Красная зона (опасно)
        self.add_zone(2, 4, QColor(255, 200, 0))      # Желтая зона (низкое)
        self.add_zone(4, 7, QColor(0, 200, 0))        # Зеленая зона (норма)
        self.add_zone(7, 10, QColor(255, 200, 0))     # Желтая зона (высокое)


class BoostGauge(CircularGauge):
    """Специализированный датчик наддува (для турбированных модификаций)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_title("ДАВЛЕНИЕ НАДДУВА")
        self.set_unit("бар")
        self.set_range(-1, 2)
        self.set_precision(2)
        
        # Добавление цветовых зон для наддува
        self.add_zone(-1, 0, QColor(0, 150, 255))     # Синяя зона (разрежение)
        self.add_zone(0, 1, QColor(0, 200, 0))        # Зеленая зона (норма)
        self.add_zone(1, 2, QColor(255, 50, 50))      # Красная зона (опасно)


# Пример использования
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    # Создание тестового окна
    from PyQt5.QtWidgets import QMainWindow, QGridLayout, QWidget
    
    window = QMainWindow()
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    
    layout = QGridLayout(central_widget)
    
    # Создание и добавление приборов
    tachometer = TachometerGauge()
    tachometer.set_value(2500)
    layout.addWidget(tachometer, 0, 0)
    
    speedometer = SpeedometerGauge()
    speedometer.set_value(80)
    layout.addWidget(speedometer, 0, 1)
    
    temperature = TemperatureGauge()
    temperature.set_value(85)
    layout.addWidget(temperature, 1, 0)
    
    fuel_level = FuelLevelGauge()
    fuel_level.set_value(45)
    layout.addWidget(fuel_level, 1, 1)
    
    voltage = VoltageGauge()
    voltage.set_value(13.8)
    layout.addWidget(voltage, 2, 0)
    
    engine_load = EngineLoadGauge()
    engine_load.set_value(65)
    layout.addWidget(engine_load, 2, 1)
    
    window.setGeometry(100, 100, 1000, 800)
    window.show()
    
    sys.exit(app.exec_())