from PyQt6.QtWidgets import (
    QScrollArea,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QFileDialog,
    QToolButton,
    QSizePolicy,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QPoint, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap, QImage, QPainter, QIcon, QColor, QPalette
import numpy as np
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ImageViewer(QScrollArea):
    """A modern image viewer with zoom, pan, and download capabilities"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Set modern scrollbar style
        self.setStyleSheet(
            """
            QScrollArea {
                border: none;
                background-color: #f5f5f5;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #c1c1c1;
                min-height: 30px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a8a8a8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                border: none;
                background: #f0f0f0;
                height: 10px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #c1c1c1;
                min-width: 30px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #a8a8a8;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """
        )

        # Create a container widget for the image and controls
        container = QWidget()
        container.setStyleSheet(
            """
            QWidget {
                background-color: #f5f5f5;
            }
        """
        )

        # Main layout
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create the image label with a subtle border
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet(
            """
            QLabel {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                margin: 10px;
            }
        """
        )
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        main_layout.addWidget(self.image_label)

        # Create controls container
        controls_container = QWidget()
        controls_container.setStyleSheet(
            """
            QWidget {
                background-color: white;
            }
        """
        )
        controls_layout = QHBoxLayout(controls_container)
        controls_layout.setContentsMargins(10, 10, 10, 10)
        controls_layout.setSpacing(10)

        # Create zoom controls
        zoom_container = QWidget()
        zoom_layout = QHBoxLayout(zoom_container)
        zoom_layout.setContentsMargins(0, 0, 0, 0)
        zoom_layout.setSpacing(5)

        # Zoom out button
        self.zoom_out_btn = QToolButton()
        self.zoom_out_btn.setIcon(QIcon.fromTheme("zoom-out"))
        self.zoom_out_btn.setToolTip("Zoom Out")
        self.zoom_out_btn.clicked.connect(lambda: self.zoom_image(0.9))
        self.zoom_out_btn.setStyleSheet(
            """
            QToolButton {
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 5px;
                min-width: 30px;
                min-height: 30px;
            }
            QToolButton:hover {
                background-color: #e0e0e0;
            }
            QToolButton:pressed {
                background-color: #d0d0d0;
            }
        """
        )
        zoom_layout.addWidget(self.zoom_out_btn)

        # Zoom reset button
        self.zoom_reset_btn = QToolButton()
        self.zoom_reset_btn.setIcon(QIcon.fromTheme("zoom-fit-best"))
        self.zoom_reset_btn.setToolTip("Reset Zoom")
        self.zoom_reset_btn.clicked.connect(self.fit_to_viewport)
        self.zoom_reset_btn.setStyleSheet(
            """
            QToolButton {
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 5px;
                min-width: 30px;
                min-height: 30px;
            }
            QToolButton:hover {
                background-color: #e0e0e0;
            }
            QToolButton:pressed {
                background-color: #d0d0d0;
            }
        """
        )
        zoom_layout.addWidget(self.zoom_reset_btn)

        # Zoom in button
        self.zoom_in_btn = QToolButton()
        self.zoom_in_btn.setIcon(QIcon.fromTheme("zoom-in"))
        self.zoom_in_btn.setToolTip("Zoom In")
        self.zoom_in_btn.clicked.connect(lambda: self.zoom_image(1.1))
        self.zoom_in_btn.setStyleSheet(
            """
            QToolButton {
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 5px;
                min-width: 30px;
                min-height: 30px;
            }
            QToolButton:hover {
                background-color: #e0e0e0;
            }
            QToolButton:pressed {
                background-color: #d0d0d0;
            }
        """
        )
        zoom_layout.addWidget(self.zoom_in_btn)

        controls_layout.addWidget(zoom_container)
        controls_layout.addStretch()

        # Download button with icon
        self.download_button = QPushButton("Download Image")
        self.download_button.setIcon(QIcon.fromTheme("document-save"))
        self.download_button.setToolTip("Save image to your computer")
        self.download_button.clicked.connect(self.download_image)
        self.download_button.setEnabled(False)
        self.download_button.setStyleSheet(
            """
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: 500;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """
        )
        controls_layout.addWidget(self.download_button)

        main_layout.addWidget(controls_container)
        self.setWidget(container)

        # Initialize variables
        self.zoom_factor = 1.0
        self.original_pixmap = None
        self.last_mouse_pos = None
        self.is_dragging = False

        # Set up mouse tracking
        self.setMouseTracking(True)
        self.image_label.setMouseTracking(True)

        # Connect wheel event
        self.wheelEvent = self.handle_wheel

    def set_image(self, image):
        """Set the image to display"""
        if isinstance(image, QPixmap):
            self.original_pixmap = image
        elif isinstance(image, QImage):
            self.original_pixmap = QPixmap.fromImage(image)
        elif isinstance(image, np.ndarray):
            height, width, channel = image.shape
            bytes_per_line = 3 * width
            q_image = QImage(
                image.data, width, height, bytes_per_line, QImage.Format.Format_RGB888
            )
            self.original_pixmap = QPixmap.fromImage(q_image)

        # Reset zoom and fit image to viewport
        self.zoom_factor = 1.0
        self.fit_to_viewport()
        self.update_image()

        # Enable download button
        self.download_button.setEnabled(True)

        # Show zoom controls
        self.zoom_out_btn.setEnabled(True)
        self.zoom_reset_btn.setEnabled(True)
        self.zoom_in_btn.setEnabled(True)

    def zoom_image(self, factor):
        """Zoom the image by a factor"""
        if self.original_pixmap is None:
            return

        self.zoom_factor *= factor
        self.zoom_factor = max(0.1, min(self.zoom_factor, 5.0))
        self.update_image()

    def download_image(self):
        """Save the current image to a file"""
        if not self.original_pixmap:
            return

        try:
            # Get the user's home directory
            home_dir = os.path.expanduser("~")
            pictures_dir = os.path.join(home_dir, "Pictures")

            # Create Pictures directory if it doesn't exist
            if not os.path.exists(pictures_dir):
                os.makedirs(pictures_dir)

            # Get current timestamp for filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_path = os.path.join(pictures_dir, f"screenshot_{timestamp}.png")

            # Open file dialog with parent widget
            file_path, _ = QFileDialog.getSaveFileName(
                self.parent(),  # Use parent widget instead of self
                "Save Image",
                default_path,
                "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*.*)",
            )

            if file_path:
                # Save the original image
                self.original_pixmap.save(file_path)

                # Show success animation
                self.show_save_animation()
        except Exception as e:
            logger.error(f"Error saving image: {e}")
            QMessageBox.critical(
                self.parent(), "Error", f"Failed to save image: {str(e)}"
            )

    def show_save_animation(self):
        """Show a brief animation when image is saved"""
        # Create a temporary label for the animation
        anim_label = QLabel("✓ Saved!", self)
        anim_label.setStyleSheet(
            """
            QLabel {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
        """
        )
        anim_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Position the label
        anim_label.move((self.width() - anim_label.width()) // 2, self.height() - 100)
        anim_label.show()

        # Create fade out animation
        fade_anim = QPropertyAnimation(anim_label, b"windowOpacity")
        fade_anim.setDuration(1000)  # 1 second duration
        fade_anim.setStartValue(1.0)
        fade_anim.setEndValue(0.0)
        fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Ensure the label is deleted after animation
        def cleanup():
            anim_label.deleteLater()
            fade_anim.deleteLater()

        fade_anim.finished.connect(cleanup)
        fade_anim.start()

    def fit_to_viewport(self):
        """Fit the image to the viewport while maintaining aspect ratio"""
        if self.original_pixmap is None:
            return

        # Get viewport size
        viewport_size = self.viewport().size()

        # Calculate scale factors for both dimensions
        width_scale = viewport_size.width() / self.original_pixmap.width()
        height_scale = viewport_size.height() / self.original_pixmap.height()

        # Use the smaller scale to fit the image
        self.zoom_factor = min(width_scale, height_scale)

        # Update the image
        self.update_image()

    def update_image(self):
        """Update the displayed image with current zoom"""
        if self.original_pixmap is None:
            return

        # Calculate new size
        new_size = self.original_pixmap.size() * self.zoom_factor

        # Scale the image
        scaled_pixmap = self.original_pixmap.scaled(
            new_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # Update the label
        self.image_label.setPixmap(scaled_pixmap)

        # Adjust scroll area to fit the image
        self.image_label.setMinimumSize(1, 1)
        self.image_label.setMaximumSize(16777215, 16777215)

    def handle_wheel(self, event):
        """Handle mouse wheel for zooming"""
        if self.original_pixmap is None:
            return

        # Get the position of the mouse relative to the image
        pos = event.position()

        # Calculate zoom factor
        if event.angleDelta().y() > 0:
            self.zoom_factor *= 1.1
        else:
            self.zoom_factor /= 1.1

        # Limit zoom factor
        self.zoom_factor = max(0.1, min(self.zoom_factor, 5.0))

        # Update the image
        self.update_image()

    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.MouseButton.LeftButton and self.original_pixmap:
            self.is_dragging = True
            self.last_mouse_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if (
            self.is_dragging
            and self.original_pixmap
            and self.last_mouse_pos is not None
        ):
            delta = event.pos() - self.last_mouse_pos
            self.last_mouse_pos = event.pos()

            # Scroll the view
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )

    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.last_mouse_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def clear(self):
        """Clear the current image"""
        self.original_pixmap = None
        self.zoom_factor = 1.0
        self.image_label.clear()
        self.download_button.setEnabled(False)
        self.zoom_out_btn.setEnabled(False)
        self.zoom_reset_btn.setEnabled(False)
        self.zoom_in_btn.setEnabled(False)

    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        if self.original_pixmap is not None:
            self.fit_to_viewport()
