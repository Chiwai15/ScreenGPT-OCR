from PyQt6.QtWidgets import QWidget, QApplication, QScrollArea, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QScreen, QWheelEvent
import mss
import numpy as np
import cv2
import time
import logging

# Configure logging
logger = logging.getLogger(__name__)


class ScreenPicker(QWidget):
    # Add signal for captured image
    image_captured = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        # Set window flags for proper overlay behavior
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        # Get screen size and set window geometry
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        # Set transparency attributes
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # Set more visible background style
        self.setStyleSheet(
            """
            QWidget {
                background-color: rgba(0, 0, 0, 100);
            }
        """
        )
        self.setCursor(Qt.CursorShape.CrossCursor)

        self.begin = QPoint()
        self.end = QPoint()
        self.is_drawing = False
        self.is_dragging = False
        self.drag_start = QPoint()
        self.selection_rect = QRect()

        # Add scroll offsets
        self.scroll_x = 0
        self.scroll_y = 0
        self.scroll_speed = 20  # Pixels per scroll step

        # Ensure the widget is visible and interactive
        self.setVisible(True)
        self.raise_()
        self.activateWindow()

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel events for scrolling"""
        try:
            # Get the scroll delta
            delta = event.angleDelta()

            # Check if Ctrl is pressed for horizontal scrolling
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                # Horizontal scroll
                self.scroll_x += delta.x() // 120 * self.scroll_speed
            else:
                # Vertical scroll
                self.scroll_y += delta.y() // 120 * self.scroll_speed

            # Update the view
            self.update()
            event.accept()
        except Exception as e:
            logger.error(f"Error in wheelEvent: {e}")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw semi-transparent overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self.is_drawing or self.is_dragging:
            # Calculate selection rectangle with scroll offset
            rect = QRect(
                self.begin.x() - self.scroll_x,
                self.begin.y() - self.scroll_y,
                self.end.x() - self.begin.x(),
                self.end.y() - self.begin.y(),
            )

            # Clear the selection area
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, Qt.GlobalColor.transparent)

            # Draw selection border
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver
            )
            painter.setPen(QPen(Qt.GlobalColor.white, 2))
            painter.drawRect(rect)

            # Draw size indicators
            width = abs(self.end.x() - self.begin.x())
            height = abs(self.end.y() - self.begin.y())
            size_text = f"{width} x {height}"

            # Draw size text
            painter.setPen(QPen(Qt.GlobalColor.white, 1))
            painter.setFont(QFont("Arial", 12))
            text_rect = painter.fontMetrics().boundingRect(size_text)

            # Position text at the top-left of selection
            text_x = min(self.begin.x(), self.end.x()) - self.scroll_x
            text_y = min(self.begin.y(), self.end.y()) - self.scroll_y - 5

            # Draw text background
            painter.fillRect(
                text_x,
                text_y - text_rect.height(),
                text_rect.width(),
                text_rect.height(),
                QColor(0, 0, 0, 180),
            )

            # Draw text
            painter.drawText(text_x, text_y, size_text)

            # Draw scroll indicators
            self.draw_scroll_indicators(painter)

        painter.end()

    def draw_scroll_indicators(self, painter):
        """Draw scroll indicators when near screen edges"""
        width = self.width()
        height = self.height()

        # Draw horizontal scroll indicator
        if self.scroll_x != 0:
            painter.setPen(QPen(Qt.GlobalColor.white, 2))
            painter.drawLine(0, height - 20, width, height - 20)
            # Draw arrow
            if self.scroll_x > 0:
                painter.drawLine(width - 30, height - 20, width - 20, height - 15)
                painter.drawLine(width - 30, height - 20, width - 20, height - 25)
            else:
                painter.drawLine(20, height - 20, 30, height - 15)
                painter.drawLine(20, height - 20, 30, height - 25)

        # Draw vertical scroll indicator
        if self.scroll_y != 0:
            painter.setPen(QPen(Qt.GlobalColor.white, 2))
            painter.drawLine(width - 20, 0, width - 20, height)
            # Draw arrow
            if self.scroll_y > 0:
                painter.drawLine(width - 20, height - 30, width - 15, height - 20)
                painter.drawLine(width - 20, height - 30, width - 25, height - 20)
            else:
                painter.drawLine(width - 20, 20, width - 15, 30)
                painter.drawLine(width - 20, 20, width - 25, 30)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_drawing:
                # Check if click is inside the selection
                if self.selection_rect.contains(event.pos()):
                    self.is_dragging = True
                    self.drag_start = event.pos()
                else:
                    # Start new selection
                    self.begin = event.pos()
                    self.end = self.begin
                    self.is_drawing = True
            else:
                # Start new selection
                self.begin = event.pos()
                self.end = self.begin
                self.is_drawing = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            # Calculate the movement delta
            delta = event.pos() - self.drag_start
            self.drag_start = event.pos()

            # Move the selection rectangle
            self.begin += delta
            self.end += delta
            self.selection_rect = QRect(self.begin, self.end)
            self.update()
        elif self.is_drawing:
            self.end = event.pos()
            self.selection_rect = QRect(self.begin, self.end)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_dragging:
                self.is_dragging = False
            elif self.is_drawing:
                self.is_drawing = False
                self.capture_selection()

    def capture_selection(self):
        try:
            # Get the selected area with scroll offset
            x1 = min(self.begin.x(), self.end.x()) - self.scroll_x
            y1 = min(self.begin.y(), self.end.y()) - self.scroll_y
            x2 = max(self.begin.x(), self.end.x()) - self.scroll_x
            y2 = max(self.begin.y(), self.end.y()) - self.scroll_y

            # Ensure minimum size
            if x2 - x1 < 10 or y2 - y1 < 10:
                self.close()
                return

            # Get the screen geometry
            screen = QApplication.primaryScreen().geometry()

            # IMPORTANT: Hide this widget temporarily to capture what's underneath
            self.hide()
            QApplication.processEvents()

            # Add a small delay to ensure the widget is hidden
            time.sleep(0.05)

            # Capture the screen
            with mss.mss() as sct:
                # Get the primary monitor
                monitor = sct.monitors[1]  # Primary monitor

                # Calculate the absolute screen coordinates
                left = monitor["left"] + x1
                top = monitor["top"] + y1
                width = x2 - x1
                height = y2 - y1

                logger.debug(
                    f"Capturing area: left={left}, top={top}, width={width}, height={height}"
                )

                # Capture the specific area
                screenshot = sct.grab(
                    {"left": left, "top": top, "width": width, "height": height}
                )

                # Convert to numpy array
                img = np.array(screenshot)

                # Convert to BGR
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                # Log the captured image size for debugging
                logger.debug(f"Captured image size: {img.shape}")

                # Emit the captured image
                self.image_captured.emit(img)

        except Exception as e:
            logger.error(f"Error capturing screen: {e}")
            logger.error(f"Error details: {str(e)}")
        finally:
            self.close()

    def closeEvent(self, event):
        """Handle window close event"""
        try:
            # Ensure the window is properly cleaned up
            self.hide()
            event.accept()
        except Exception as e:
            logger.error(f"Error in closeEvent: {e}")
            event.accept()
