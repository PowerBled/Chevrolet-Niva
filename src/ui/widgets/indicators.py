"""
Кастомные индикаторы и виджеты для отображения данных диагностики
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QProgressBar, QGroupBox, QGridLayout,
                             QSizePolicy, QGraphicsDropShadowEffect)
from PyQt5.QtCore import (Qt, QPropertyAnimation, QEasingCurve, QTimer, 
                          pyqtProperty, pyqtSignal, QRectF)
from PyQt5.QtGui import (QPainter, QColor, QPen, QBrush, QLinearGradient,
                         QFont, QFontMetrics, QPainterPath, QIcon)
from PyQt5.QtSvg import QSvgWidget
import math
from enum import Enum

class IndicatorStyle(Enum):
    """Стили индикаторов"""
    MODERN = "modern"
    CLASSIC = "classic"
    MINIMAL = "minimal"
    GAUGE = "gauge"

class IndicatorState(Enum):
    """Состояния индикаторов"""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    INACTIVE = "inactive"
    SUCCESS = "success"

class LEDIndicator(QWidget):
    """Светодиодный индикатор"""
    
    colorChanged = pyqtSignal(QColor)
    
    def __init__(self, parent=None, size=20, color=QColor(0, 255, 0), 
                 blink_interval=500):
        super().__init__(parent)
        
        self._size = size
        self._color = color
        self._blink_interval = blink_interval
        self._is_blinking = False
        self._is_on = True
        self._state = IndicatorState.NORMAL
        
        # Таймер для мигания
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.toggle_blink)
        
        # Эффект свечения
        self.glow_effect = QGraphicsDropShadowEffect(self)
        self.glow_effect.setBlurRadius(10)
        self.glow_effect.setColor(self._color)
        self.glow_effect.setOffset(0, 0)
        self.setGraphicsEffect(self.glow_effect)
        
        # Настройки виджета
        self.setFixedSize(self._size + 10, self._size + 10)
        
    def set_state(self, state):
        """Установка состояния индикатора"""
        self._state = state
        
        colors = {
            IndicatorState.NORMAL: QColor(0, 255, 0),    # Зеленый
            IndicatorState.WARNING: QColor(255, 255, 0), # Желтый
            IndicatorState.CRITICAL: QColor(255, 0, 0),  # Красный
            IndicatorState.INACTIVE: QColor(128, 128, 128), # Серый
            IndicatorState.SUCCESS: QColor(0, 200, 0),   # Темно-зеленый
        }
        
        self.set_color(colors.get(state, QColor(0, 255, 0)))
        
    def set_color(self, color):
        """Установка цвета индикатора"""
        self._color = color
        self.glow_effect.setColor(color)
        self.colorChanged.emit(color)
        self.update()
        
    def get_color(self):
        """Получение цвета индикатора"""
        return self._color
        
    color = pyqtProperty(QColor, get_color, set_color)
    
    def start_blinking(self, interval=None):
        """Начало мигания"""
        if interval:
            self._blink_interval = interval
            
        if not self._is_blinking:
            self._is_blinking = True
            self.blink_timer.start(self._blink_interval)
            
    def stop_blinking(self):
        """Остановка мигания"""
        if self._is_blinking:
            self._is_blinking = False
            self.blink_timer.stop()
            self._is_on = True
            self.update()
            
    def toggle_blink(self):
        """Переключение состояния мигания"""
        self._is_on = not self._is_on
        self.update()
        
    def paintEvent(self, event):
        """Отрисовка индикатора"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Фон
        painter.fillRect(self.rect(), QColor(40, 40, 40))
        
        if not self._is_on:
            return
            
        # Рисуем светодиод
        center = self.rect().center()
        radius = self._size // 2
        
        # Градиент для объемного эффекта
        gradient = QLinearGradient(
            center.x() - radius, center.y() - radius,
            center.x() + radius, center.y() + radius
        )
        
        gradient.setColorAt(0, self._color.lighter(150))
        gradient.setColorAt(0.5, self._color)
        gradient.setColorAt(1, self._color.darker(150))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
        
        # Рисуем круг
        painter.drawEllipse(center, radius, radius)
        
        # Блики для реалистичности
        painter.setBrush(QBrush(QColor(255, 255, 255, 100)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            center.x() - radius // 3,
            center.y() - radius // 3,
            radius // 2,
            radius // 2
        )
        
    def mousePressEvent(self, event):
        """Обработка нажатия мыши"""
        if event.button() == Qt.LeftButton:
            self._is_on = not self._is_on
            self.update()
            
        super().mousePressEvent(event)

class CircularGauge(QWidget):
    """Круговой индикатор-датчик"""
    
    valueChanged = pyqtSignal(float)
    
    def __init__(self, parent=None, title="", unit="", min_value=0, 
                 max_value=100, value=0, style=IndicatorStyle.MODERN):
        super().__init__(parent)
        
        self._title = title
        self._unit = unit
        self._min_value = min_value
        self._max_value = max_value
        self._value = value
        self._style = style
        self._animation = None
        
        # Цветовые настройки
        self._normal_color = QColor(0, 255, 0)
        self._warning_color = QColor(255, 255, 0)
        self._critical_color = QColor(255, 0, 0)
        
        # Пороги
        self._warning_threshold = max_value * 0.7
        self._critical_threshold = max_value * 0.9
        
        # Настройки отображения
        self._start_angle = 45
        self._end_angle = 270
        self._scale_divisions = 10
        self._minor_divisions = 5
        
        # Шрифты
        self._title_font = QFont("Arial", 10, QFont.Bold)
        self._value_font = QFont("Arial", 16, QFont.Bold)
        self._unit_font = QFont("Arial", 8)
        
        # Анимация
        self.setup_animation()
        
        # Настройки виджета
        self.setMinimumSize(150, 150)
        
    def setup_animation(self):
        """Настройка анимации"""
        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setDuration(1000)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        
    def set_value(self, value, animated=True):
        """Установка значения с анимацией"""
        if value < self._min_value:
            value = self._min_value
        elif value > self._max_value:
            value = self._max_value
            
        if animated and self._animation:
            self._animation.stop()
            self._animation.setStartValue(self._value)
            self._animation.setEndValue(value)
            self._animation.start()
        else:
            self._value = value
            self.valueChanged.emit(value)
            self.update()
            
    def get_value(self):
        """Получение текущего значения"""
        return self._value
        
    value = pyqtProperty(float, get_value, set_value)
    
    def set_title(self, title):
        """Установка заголовка"""
        self._title = title
        self.update()
        
    def set_unit(self, unit):
        """Установка единиц измерения"""
        self._unit = unit
        self.update()
        
    def set_range(self, min_value, max_value):
        """Установка диапазона значений"""
        self._min_value = min_value
        self._max_value = max_value
        self.update()
        
    def set_thresholds(self, warning, critical):
        """Установка пороговых значений"""
        self._warning_threshold = warning
        self._critical_threshold = critical
        self.update()
        
    def get_color_for_value(self, value):
        """Получение цвета в зависимости от значения"""
        if value >= self._critical_threshold:
            return self._critical_color
        elif value >= self._warning_threshold:
            return self._warning_color
        else:
            return self._normal_color
            
    def paintEvent(self, event):
        """Отрисовка датчика"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Размеры
        width = self.width()
        height = self.height()
        size = min(width, height) - 20
        x = (width - size) // 2
        y = (height - size) // 2 + 10
        
        # Рисуем фон
        self.draw_background(painter, x, y, size)
        
        # Рисуем шкалу
        self.draw_scale(painter, x, y, size)
        
        # Рисуем стрелку
        self.draw_needle(painter, x, y, size)
        
        # Рисуем центр
        self.draw_center(painter, x, y, size)
        
        # Рисуем текст
        self.draw_text(painter, x, y, size)
        
    def draw_background(self, painter, x, y, size):
        """Отрисовка фона датчика"""
        # Фон
        if self._style == IndicatorStyle.MODERN:
            gradient = QLinearGradient(x, y, x + size, y + size)
            gradient.setColorAt(0, QColor(50, 50, 50))
            gradient.setColorAt(1, QColor(30, 30, 30))
            painter.setBrush(QBrush(gradient))
        else:
            painter.setBrush(QBrush(QColor(40, 40, 40)))
            
        painter.setPen(QPen(QColor(80, 80, 80), 2))
        painter.drawEllipse(x, y, size, size)
        
    def draw_scale(self, painter, x, y, size):
        """Отрисовка шкалы"""
        radius = size // 2
        center_x = x + radius
        center_y = y + radius
        scale_radius = radius - 15
        
        # Основные деления
        painter.save()
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        
        for i in range(self._scale_divisions + 1):
            angle = self._start_angle + (i / self._scale_divisions) * self._end_angle
            rad = math.radians(angle)
            
            x1 = center_x + (scale_radius - 10) * math.cos(rad)
            y1 = center_y - (scale_radius - 10) * math.sin(rad)
            x2 = center_x + scale_radius * math.cos(rad)
            y2 = center_y - scale_radius * math.sin(rad)
            
            painter.drawLine(x1, y1, x2, y2)
            
            # Подписи значений
            value = self._min_value + (i / self._scale_divisions) * (self._max_value - self._min_value)
            text = f"{value:.0f}"
            
            font_metrics = QFontMetrics(self._unit_font)
            text_width = font_metrics.width(text)
            text_height = font_metrics.height()
            
            label_radius = scale_radius - 25
            label_x = center_x + label_radius * math.cos(rad) - text_width / 2
            label_y = center_y - label_radius * math.sin(rad) + text_height / 4
            
            painter.setFont(self._unit_font)
            painter.drawText(label_x, label_y, text)
            
        painter.restore()
        
        # Внутренняя дуга
        arc_rect = QRectF(x + 10, y + 10, size - 20, size - 20)
        
        # Критическая зона
        if self._critical_threshold < self._max_value:
            critical_start = self.value_to_angle(self._critical_threshold)
            critical_span = self.value_to_angle(self._max_value) - critical_start
            
            painter.setPen(QPen(self._critical_color, 8))
            painter.drawArc(arc_rect, int(critical_start * 16), int(critical_span * 16))
            
        # Предупреждающая зона
        if self._warning_threshold < self._critical_threshold:
            warning_start = self.value_to_angle(self._warning_threshold)
            warning_span = self.value_to_angle(self._critical_threshold) - warning_start
            
            painter.setPen(QPen(self._warning_color, 8))
            painter.drawArc(arc_rect, int(warning_start * 16), int(warning_span * 16))
            
        # Нормальная зона
        normal_start = self.value_to_angle(self._min_value)
        normal_span = self.value_to_angle(self._warning_threshold) - normal_start
        
        painter.setPen(QPen(self._normal_color, 8))
        painter.drawArc(arc_rect, int(normal_start * 16), int(normal_span * 16))
        
    def draw_needle(self, painter, x, y, size):
        """Отрисовка стрелки"""
        radius = size // 2
        center_x = x + radius
        center_y = y + radius
        
        angle = self.value_to_angle(self._value)
        rad = math.radians(angle)
        
        # Длина стрелки
        needle_length = radius - 25
        
        # Конец стрелки
        end_x = center_x + needle_length * math.cos(rad)
        end_y = center_y - needle_length * math.sin(rad)
        
        # Основание стрелки (треугольник)
        painter.save()
        
        # Поворачиваем систему координат
        painter.translate(center_x, center_y)
        painter.rotate(-angle)
        
        # Рисуем стрелку
        needle_color = self.get_color_for_value(self._value)
        painter.setBrush(QBrush(needle_color))
        painter.setPen(QPen(needle_color.darker(), 1))
        
        # Треугольник для стрелки
        path = QPainterPath()
        path.moveTo(0, -5)
        path.lineTo(needle_length, 0)
        path.lineTo(0, 5)
        path.closeSubpath()
        
        painter.drawPath(path)
        
        painter.restore()
        
    def draw_center(self, painter, x, y, size):
        """Отрисовка центра датчика"""
        radius = size // 2
        center_x = x + radius
        center_y = y + radius
        
        # Центральный круг
        painter.setBrush(QBrush(QColor(50, 50, 50)))
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawEllipse(center_x - 10, center_y - 10, 20, 20)
        
        # Внутренний круг
        painter.setBrush(QBrush(QColor(30, 30, 30)))
        painter.drawEllipse(center_x - 5, center_y - 5, 10, 10)
        
    def draw_text(self, painter, x, y, size):
        """Отрисовка текста"""
        radius = size // 2
        center_x = x + radius
        center_y = y + radius
        
        # Заголовок
        painter.setFont(self._title_font)
        painter.setPen(QPen(QColor(200, 200, 200)))
        
        font_metrics = QFontMetrics(self._title_font)
        title_width = font_metrics.width(self._title)
        painter.drawText(center_x - title_width // 2, y + size + 20, self._title)
        
        # Значение
        painter.setFont(self._value_font)
        value_text = f"{self._value:.1f}"
        font_metrics = QFontMetrics(self._value_font)
        value_width = font_metrics.width(value_text)
        
        value_color = self.get_color_for_value(self._value)
        painter.setPen(QPen(value_color))
        painter.drawText(center_x - value_width // 2, center_y + 5, value_text)
        
        # Единицы измерения
        if self._unit:
            painter.setFont(self._unit_font)
            painter.setPen(QPen(QColor(150, 150, 150)))
            
            unit_width = QFontMetrics(self._unit_font).width(self._unit)
            painter.drawText(center_x - unit_width // 2, center_y + 25, self._unit)
            
    def value_to_angle(self, value):
        """Конвертация значения в угол"""
        normalized = (value - self._min_value) / (self._max_value - self._min_value)
        return self._start_angle + normalized * self._end_angle

class DigitalDisplay(QWidget):
    """Цифровой дисплей"""
    
    def __init__(self, parent=None, value=0.0, unit="", precision=1,
                 background_color=QColor(20, 30, 20),
                 text_color=QColor(0, 255, 0)):
        super().__init__(parent)
        
        self._value = value
        self._unit = unit
        self._precision = precision
        self._background_color = background_color
        self._text_color = text_color
        self._blink = False
        self._blink_state = True
        
        # Шрифт для цифр (цифровой стиль)
        self._digit_font = QFont("Courier New", 24, QFont.Bold)
        self._unit_font = QFont("Arial", 10)
        
        # Таймер для мигания
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self.toggle_blink)
        
        # Настройки виджета
        self.setMinimumSize(150, 60)
        
    def set_value(self, value):
        """Установка значения"""
        self._value = value
        self.update()
        
    def set_unit(self, unit):
        """Установка единиц измерения"""
        self._unit = unit
        self.update()
        
    def set_precision(self, precision):
        """Установка точности"""
        self._precision = precision
        self.update()
        
    def set_colors(self, background, text):
        """Установка цветов"""
        self._background_color = background
        self._text_color = text
        self.update()
        
    def start_blinking(self, interval=500):
        """Начало мигания"""
        self._blink = True
        self._blink_state = True
        self._blink_timer.start(interval)
        
    def stop_blinking(self):
        """Остановка мигания"""
        self._blink = False
        self._blink_timer.stop()
        self._blink_state = True
        self.update()
        
    def toggle_blink(self):
        """Переключение состояния мигания"""
        self._blink_state = not self._blink_state
        self.update()
        
    def paintEvent(self, event):
        """Отрисовка дисплея"""
        if self._blink and not self._blink_state:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Фон с градиентом
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, self._background_color.lighter(120))
        gradient.setColorAt(1, self._background_color.darker(120))
        
        painter.fillRect(self.rect(), QBrush(gradient))
        
        # Рамка
        painter.setPen(QPen(self._text_color.darker(150), 2))
        painter.drawRect(1, 1, self.width() - 2, self.height() - 2)
        
        # Текст значения
        value_text = f"{self._value:.{self._precision}f}"
        
        painter.setFont(self._digit_font)
        painter.setPen(QPen(self._text_color))
        
        font_metrics = QFontMetrics(self._digit_font)
        text_width = font_metrics.width(value_text)
        text_height = font_metrics.height()
        
        # Позиционирование
        x = (self.width() - text_width) // 2
        y = (self.height() - text_height) // 2 + font_metrics.ascent()
        
        painter.drawText(x, y, value_text)
        
        # Единицы измерения
        if self._unit:
            painter.setFont(self._unit_font)
            painter.setPen(QPen(self._text_color.darker(200)))
            
            unit_metrics = QFontMetrics(self._unit_font)
            unit_width = unit_metrics.width(self._unit)
            
            unit_x = self.width() - unit_width - 10
            unit_y = self.height() - 5
            
            painter.drawText(unit_x, unit_y, self._unit)

class StatusIndicator(QWidget):
    """Индикатор состояния системы"""
    
    def __init__(self, parent=None, system_name="", status="normal", 
                 description=""):
        super().__init__(parent)
        
        self._system_name = system_name
        self._status = status
        self._description = description
        
        # Цвета состояний
        self._status_colors = {
            "normal": QColor(0, 255, 0),
            "warning": QColor(255, 255, 0),
            "error": QColor(255, 0, 0),
            "inactive": QColor(128, 128, 128),
            "unknown": QColor(255, 165, 0),
        }
        
        # Иконки состояний
        self._status_icons = {
            "normal": "✓",
            "warning": "⚠",
            "error": "✗",
            "inactive": "—",
            "unknown": "?",
        }
        
        # Шрифты
        self._name_font = QFont("Arial", 10, QFont.Bold)
        self._status_font = QFont("Arial", 9)
        self._desc_font = QFont("Arial", 8)
        
        # Layout
        self._layout = QHBoxLayout()
        self._layout.setContentsMargins(10, 5, 10, 5)
        self._layout.setSpacing(10)
        self.setLayout(self._layout)
        
        # Создание виджетов
        self._create_widgets()
        
    def _create_widgets(self):
        """Создание виджетов индикатора"""
        # Индикатор состояния
        self._led = LEDIndicator(self, size=12)
        self._led.set_state(self._get_indicator_state())
        self._layout.addWidget(self._led)
        
        # Название системы
        self._name_label = QLabel(self._system_name)
        self._name_label.setFont(self._name_font)
        self._name_label.setStyleSheet("color: white;")
        self._name_label.setFixedWidth(120)
        self._layout.addWidget(self._name_label)
        
        # Статус
        self._status_label = QLabel(self._status.upper())
        self._status_label.setFont(self._status_font)
        self._status_label.setStyleSheet(f"color: {self._get_status_color().name()};")
        self._layout.addWidget(self._status_label)
        
        # Иконка статуса
        self._icon_label = QLabel(self._status_icons.get(self._status, "?"))
        self._icon_label.setFont(QFont("Arial", 12))
        self._icon_label.setStyleSheet(f"color: {self._get_status_color().name()};")
        self._icon_label.setFixedWidth(20)
        self._layout.addWidget(self._icon_label)
        
        # Описание
        self._desc_label = QLabel(self._description)
        self._desc_label.setFont(self._desc_font)
        self._desc_label.setStyleSheet("color: #AAAAAA;")
        self._desc_label.setWordWrap(True)
        self._layout.addWidget(self._desc_label, 1)
        
    def _get_status_color(self):
        """Получение цвета статуса"""
        return self._status_colors.get(self._status, QColor(255, 165, 0))
        
    def _get_indicator_state(self):
        """Получение состояния индикатора"""
        state_map = {
            "normal": IndicatorState.NORMAL,
            "warning": IndicatorState.WARNING,
            "error": IndicatorState.CRITICAL,
            "inactive": IndicatorState.INACTIVE,
            "unknown": IndicatorState.WARNING,
        }
        return state_map.get(self._status, IndicatorState.WARNING)
        
    def set_status(self, status, description=""):
        """Установка статуса системы"""
        self._status = status
        if description:
            self._description = description
            
        # Обновление виджетов
        self._led.set_state(self._get_indicator_state())
        self._status_label.setText(status.upper())
        self._status_label.setStyleSheet(f"color: {self._get_status_color().name()};")
        self._icon_label.setText(self._status_icons.get(status, "?"))
        self._icon_label.setStyleSheet(f"color: {self._get_status_color().name()};")
        self._desc_label.setText(self._description)
        
        # Мигание при ошибке
        if status == "error":
            self._led.start_blinking()
        else:
            self._led.stop_blinking()

class BarIndicator(QWidget):
    """Столбчатый индикатор"""
    
    def __init__(self, parent=None, title="", value=0, max_value=100,
                 orientation=Qt.Horizontal, show_value=True):
        super().__init__(parent)
        
        self._title = title
        self._value = value
        self._max_value = max_value
        self._orientation = orientation
        self._show_value = show_value
        self._thresholds = [70, 90]  # Пороги для смены цвета
        
        # Цвета
        self._colors = [
            QColor(0, 255, 0),    # Зеленый
            QColor(255, 255, 0),  # Желтый
            QColor(255, 0, 0),    # Красный
        ]
        
        # Шрифты
        self._title_font = QFont("Arial", 9)
        self._value_font = QFont("Arial", 8, QFont.Bold)
        
        # Layout
        if orientation == Qt.Horizontal:
            self._layout = QVBoxLayout()
        else:
            self._layout = QHBoxLayout()
            
        self._layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(self._layout)
        
        # Создание виджетов
        self._create_widgets()
        
    def _create_widgets(self):
        """Создание виджетов индикатора"""
        # Заголовок
        self._title_label = QLabel(self._title)
        self._title_label.setFont(self._title_font)
        self._title_label.setStyleSheet("color: white;")
        self._layout.addWidget(self._title_label)
        
        # Контейнер для бара
        self._bar_container = QWidget()
        self._bar_container.setMinimumHeight(20)
        
        bar_layout = QHBoxLayout(self._bar_container)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        
        # Бар
        self._bar_widget = QWidget()
        self._bar_widget.setMinimumHeight(15)
        bar_layout.addWidget(self._bar_widget)
        
        # Значение
        if self._show_value:
            self._value_label = QLabel(f"{self._value:.1f}")
            self._value_label.setFont(self._value_font)
            self._value_label.setStyleSheet("color: white;")
            self._value_label.setFixedWidth(40)
            bar_layout.addWidget(self._value_label)
            
        self._layout.addWidget(self._bar_container)
        
    def set_value(self, value):
        """Установка значения"""
        self._value = min(max(0, value), self._max_value)
        
        if self._show_value:
            self._value_label.setText(f"{self._value:.1f}")
            
        self.update()
        
    def set_max_value(self, max_value):
        """Установка максимального значения"""
        self._max_value = max_value
        self.update()
        
    def set_thresholds(self, thresholds):
        """Установка пороговых значений"""
        self._thresholds = thresholds
        self.update()
        
    def get_color_for_value(self, value):
        """Получение цвета в зависимости от значения"""
        percentage = (value / self._max_value) * 100
        
        if percentage >= self._thresholds[1]:
            return self._colors[2]  # Красный
        elif percentage >= self._thresholds[0]:
            return self._colors[1]  # Желтый
        else:
            return self._colors[0]  # Зеленый
            
    def paintEvent(self, event):
        """Отрисовка бара"""
        if not hasattr(self, '_bar_widget'):
            return
            
        painter = QPainter(self._bar_widget)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Размеры
        width = self._bar_widget.width()
        height = self._bar_widget.height()
        
        # Фон
        painter.fillRect(0, 0, width, height, QColor(50, 50, 50))
        
        # Расчет заполненной части
        fill_width = (self._value / self._max_value) * width
        
        if fill_width > 0:
            # Градиент для заполнения
            fill_color = self.get_color_for_value(self._value)
            gradient = QLinearGradient(0, 0, fill_width, 0)
            gradient.setColorAt(0, fill_color.lighter(150))
            gradient.setColorAt(0.5, fill_color)
            gradient.setColorAt(1, fill_color.darker(150))
            
            # Рисуем заполнение
            painter.fillRect(0, 0, fill_width, height, QBrush(gradient))
            
            # Рисуем полоски для эффекта
            painter.setPen(QPen(fill_color.lighter(200), 1))
            for i in range(0, int(fill_width), 4):
                painter.drawLine(i, 0, i, height)
                
        # Рамка
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawRect(0, 0, width - 1, height - 1)

class IconIndicator(QWidget):
    """Индикатор с иконкой"""
    
    clicked = pyqtSignal()
    
    def __init__(self, parent=None, icon_path="", text="", 
                 status="normal", tooltip=""):
        super().__init__(parent)
        
        self._icon_path = icon_path
        self._text = text
        self._status = status
        self._tooltip = tooltip
        self._is_clickable = True
        
        # Цвета статусов
        self._status_colors = {
            "normal": QColor(0, 255, 0, 100),
            "warning": QColor(255, 255, 0, 100),
            "error": QColor(255, 0, 0, 100),
            "inactive": QColor(128, 128, 128, 100),
        }
        
        # Layout
        self._layout = QVBoxLayout()
        self._layout.setContentsMargins(5, 5, 5, 5)
        self._layout.setSpacing(5)
        self.setLayout(self._layout)
        
        # Настройки
        self.setToolTip(self._tooltip)
        self.setCursor(Qt.PointingHandCursor)
        
        # Создание виджетов
        self._create_widgets()
        
    def _create_widgets(self):
        """Создание виджетов индикатора"""
        # Контейнер для иконки
        self._icon_container = QWidget()
        self._icon_container.setFixedSize(50, 50)
        self._layout.addWidget(self._icon_container, 0, Qt.AlignCenter)
        
        # Текст
        self._text_label = QLabel(self._text)
        self._text_label.setAlignment(Qt.AlignCenter)
        self._text_label.setStyleSheet("color: white; font-size: 9px;")
        self._text_label.setWordWrap(True)
        self._layout.addWidget(self._text_label)
        
    def paintEvent(self, event):
        """Отрисовка индикатора"""
        painter = QPainter(self._icon_container)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Размеры
        size = min(self._icon_container.width(), self._icon_container.height())
        rect = QRectF(0, 0, size, size)
        
        # Фон
        if self._status in self._status_colors:
            color = self._status_colors[self._status]
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(rect)
            
        # Иконка
        if self._icon_path:
            try:
                # Загрузка SVG иконки
                svg_widget = QSvgWidget(self._icon_path)
                if svg_widget.isValid():
                    svg_widget.render(painter, rect)
            except:
                # Альтернатива: простой текст
                painter.setFont(QFont("Arial", 16))
                painter.setPen(QPen(QColor(255, 255, 255)))
                painter.drawText(rect, Qt.AlignCenter, "?")
                
        # Рамка
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawEllipse(rect.adjusted(0.5, 0.5, -0.5, -0.5))
        
    def mousePressEvent(self, event):
        """Обработка нажатия мыши"""
        if event.button() == Qt.LeftButton and self._is_clickable:
            self.clicked.emit()
            
        super().mousePressEvent(event)
        
    def set_status(self, status):
        """Установка статуса"""
        self._status = status
        self.update()
        
    def set_clickable(self, clickable):
        """Установка возможности нажатия"""
        self._is_clickable = clickable
        if clickable:
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

class MultiStateIndicator(QWidget):
    """Многосостоятельный индикатор"""
    
    stateChanged = pyqtSignal(str)
    
    def __init__(self, parent=None, states=None, current_state="", 
                 title="", style="buttons"):
        super().__init__(parent)
        
        self._states = states or {
            "off": ("Выкл", QColor(128, 128, 128)),
            "on": ("Вкл", QColor(0, 255, 0)),
            "error": ("Ошибка", QColor(255, 0, 0)),
        }
        
        self._current_state = current_state or list(self._states.keys())[0]
        self._title = title
        self._style = style  # "buttons" или "selector"
        
        # Шрифты
        self._title_font = QFont("Arial", 9, QFont.Bold)
        self._state_font = QFont("Arial", 8)
        
        # Layout
        self._layout = QVBoxLayout()
        self._layout.setContentsMargins(5, 5, 5, 5)
        self._layout.setSpacing(5)
        self.setLayout(self._layout)
        
        # Создание виджетов
        self._create_widgets()
        
    def _create_widgets(self):
        """Создание виджетов индикатора"""
        # Заголовок
        if self._title:
            self._title_label = QLabel(self._title)
            self._title_label.setFont(self._title_font)
            self._title_label.setStyleSheet("color: white;")
            self._title_label.setAlignment(Qt.AlignCenter)
            self._layout.addWidget(self._title_label)
            
        # Контейнер для состояний
        self._states_container = QWidget()
        
        if self._style == "buttons":
            self._states_layout = QHBoxLayout(self._states_container)
        else:
            self._states_layout = QVBoxLayout(self._states_container)
            
        self._states_layout.setContentsMargins(0, 0, 0, 0)
        self._states_layout.setSpacing(2)
        
        # Создание кнопок состояний
        self._state_buttons = {}
        for state_id, (state_text, color) in self._states.items():
            button = self._create_state_button(state_id, state_text, color)
            self._state_buttons[state_id] = button
            self._states_layout.addWidget(button)
            
        self._layout.addWidget(self._states_container)
        
        # Установка текущего состояния
        self._update_current_state()
        
    def _create_state_button(self, state_id, text, color):
        """Создание кнопки состояния"""
        button = QWidget()
        button.setProperty("state", state_id)
        button.setCursor(Qt.PointingHandCursor)
        button.setFixedHeight(25)
        
        # Сохраняем данные
        button.state_id = state_id
        button.state_text = text
        button.state_color = color
        
        return button
        
    def _update_current_state(self):
        """Обновление отображения текущего состояния"""
        for state_id, button in self._state_buttons.items():
            if state_id == self._current_state:
                button.setProperty("active", True)
            else:
                button.setProperty("active", False)
            button.update()
            
    def paintEvent(self, event):
        """Отрисовка (для кнопок состояний)"""
        # Отрисовка виджета не требуется, т.к. рисуем кнопки отдельно
        super().paintEvent(event)
        
        # Отрисовка кнопок состояний
        for button in self.findChildren(QWidget):
            if hasattr(button, 'state_id'):
                self._draw_state_button(button)
                
    def _draw_state_button(self, button):
        """Отрисовка кнопки состояния"""
        painter = QPainter(button)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Размеры
        width = button.width()
        height = button.height()
        
        # Активное или неактивное состояние
        is_active = button.property("active")
        
        if is_active:
            # Активное состояние
            color = button.state_color
            bg_color = color
            text_color = QColor(255, 255, 255)
            border_color = color.lighter(150)
        else:
            # Неактивное состояние
            color = button.state_color
            bg_color = color.darker(300)
            text_color = color.lighter(150)
            border_color = color.darker(200)
            
        # Фон
        painter.fillRect(0, 0, width, height, bg_color)
        
        # Текст
        painter.setFont(self._state_font)
        painter.setPen(QPen(text_color))
        
        font_metrics = QFontMetrics(self._state_font)
        text_width = font_metrics.width(button.state_text)
        text_height = font_metrics.height()
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2 + font_metrics.ascent()
        
        painter.drawText(x, y, button.state_text)
        
        # Рамка
        painter.setPen(QPen(border_color, 1))
        painter.drawRect(0, 0, width - 1, height - 1)
        
    def mousePressEvent(self, event):
        """Обработка нажатия мыши на кнопки состояний"""
        pos = event.pos()
        child = self.childAt(pos)
        
        if child and hasattr(child, 'state_id'):
            new_state = child.state_id
            if new_state != self._current_state:
                self._current_state = new_state
                self._update_current_state()
                self.stateChanged.emit(new_state)
                
        super().mousePressEvent(event)
        
    def set_state(self, state):
        """Установка состояния"""
        if state in self._states and state != self._current_state:
            self._current_state = state
            self._update_current_state()
            self.stateChanged.emit(state)
            
    def get_state(self):
        """Получение текущего состояния"""
        return self._current_state
        
    def add_state(self, state_id, text, color):
        """Добавление нового состояния"""
        self._states[state_id] = (text, color)
        
        # Пересоздание виджетов
        self._recreate_widgets()
        
    def _recreate_widgets(self):
        """Пересоздание виджетов"""
        # Удаляем старые виджеты
        for button in self._state_buttons.values():
            button.deleteLater()
            
        self._state_buttons.clear()
        
        # Создаем новые кнопки
        for state_id, (state_text, color) in self._states.items():
            button = self._create_state_button(state_id, state_text, color)
            self._state_buttons[state_id] = button
            self._states_layout.addWidget(button)
            
        self._update_current_state()

class CompositeIndicator(QFrame):
    """Составной индикатор с несколькими элементами"""
    
    def __init__(self, parent=None, title="", columns=2):
        super().__init__(parent)
        
        self._title = title
        self._columns = columns
        self._indicators = []
        
        # Стиль рамки
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        self.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border: 1px solid #555;
                border-radius: 5px;
            }
        """)
        
        # Основной layout
        self._main_layout = QVBoxLayout()
        self._main_layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(self._main_layout)
        
        # Заголовок
        if self._title:
            title_label = QLabel(self._title)
            title_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-weight: bold;
                    font-size: 11px;
                    border-bottom: 1px solid #555;
                    padding-bottom: 5px;
                }
            """)
            self._main_layout.addWidget(title_label)
            
        # Grid для индикаторов
        self._grid_layout = QGridLayout()
        self._grid_layout.setHorizontalSpacing(10)
        self._grid_layout.setVerticalSpacing(5)
        self._main_layout.addLayout(self._grid_layout)
        
    def add_indicator(self, widget, label_text="", row=None, col=None):
        """Добавление индикатора"""
        if row is None or col is None:
            # Автоматическое размещение
            count = len(self._indicators)
            row = count // self._columns
            col = count % self._columns
        else:
            # Ручное размещение
            row = max(0, row)
            col = max(0, col)
            
        # Добавляем метку, если указана
        if label_text:
            label = QLabel(label_text)
            label.setStyleSheet("color: #AAAAAA; font-size: 9px;")
            label.setAlignment(Qt.AlignCenter)
            self._grid_layout.addWidget(label, row * 2, col)
            self._grid_layout.addWidget(widget, row * 2 + 1, col)
        else:
            self._grid_layout.addWidget(widget, row, col)
            
        self._indicators.append(widget)
        
    def clear_indicators(self):
        """Очистка всех индикаторов"""
        for indicator in self._indicators:
            indicator.deleteLater()
        self._indicators.clear()
        
    def get_indicator(self, index):
        """Получение индикатора по индексу"""
        if 0 <= index < len(self._indicators):
            return self._indicators[index]
        return None

# Фабрика для создания индикаторов
class IndicatorFactory:
    """Фабрика для создания индикаторов"""
    
    @staticmethod
    def create_gauge(title, unit, min_val, max_val, value=0):
        """Создание кругового датчика"""
        return CircularGauge(
            title=title,
            unit=unit,
            min_value=min_val,
            max_value=max_val,
            value=value
        )
        
    @staticmethod
    def create_led(size=20, color=None, state=IndicatorState.NORMAL):
        """Создание светодиодного индикатора"""
        led = LEDIndicator(size=size)
        if color:
            led.set_color(color)
        led.set_state(state)
        return led
        
    @staticmethod
    def create_digital_display(value=0, unit="", precision=1):
        """Создание цифрового дисплея"""
        return DigitalDisplay(
            value=value,
            unit=unit,
            precision=precision
        )
        
    @staticmethod
    def create_status_indicator(system_name, status, description=""):
        """Создание индикатора состояния системы"""
        return StatusIndicator(
            system_name=system_name,
            status=status,
            description=description
        )
        
    @staticmethod
    def create_bar_indicator(title, value, max_value, orientation=Qt.Horizontal):
        """Создание столбчатого индикатора"""
        return BarIndicator(
            title=title,
            value=value,
            max_value=max_value,
            orientation=orientation
        )
        
    @staticmethod
    def create_icon_indicator(icon_path, text, status="normal", tooltip=""):
        """Создание индикатора с иконкой"""
        return IconIndicator(
            icon_path=icon_path,
            text=text,
            status=status,
            tooltip=tooltip
        )
        
    @staticmethod
    def create_multi_state_indicator(states, current_state, title="", style="buttons"):
        """Создание многосостоятельного индикатора"""
        return MultiStateIndicator(
            states=states,
            current_state=current_state,
            title=title,
            style=style
        )
        
    @staticmethod
    def create_composite_indicator(title="", columns=2):
        """Создание составного индикатора"""
        return CompositeIndicator(
            title=title,
            columns=columns
        )

# Экспорт классов
__all__ = [
    'IndicatorStyle',
    'IndicatorState',
    'LEDIndicator',
    'CircularGauge',
    'DigitalDisplay',
    'StatusIndicator',
    'BarIndicator',
    'IconIndicator',
    'MultiStateIndicator',
    'CompositeIndicator',
    'IndicatorFactory'
]