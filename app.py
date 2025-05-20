import os
import logging
import time
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QPushButton,
    QCheckBox,
    QGridLayout,
    QMessageBox,
    QTabWidget,
    QTextEdit,
    QApplication,
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import QPixmap, QImage, QKeySequence, QShortcut
import cv2
import numpy as np
import pyttsx3

from ui.image_viewer import ImageViewer
from ui.splash_screen import LoadingSplashScreen
from ui.screen_picker import ScreenPicker
from core.processing import ProcessingThread
from core.language import LanguageDownloadThread
from core.tts import TTSThread
from config import AVAILABLE_LANGUAGES

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ScreenGPT(QMainWindow):
    def __init__(self):
        super().__init__()
        logger.debug("Initializing ScreenGPT")
        self.setWindowTitle("ScreenGPT - Universal Screenshot Analysis")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize text-to-speech engine
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty("rate", 150)
        self.tts_engine.setProperty("volume", 0.9)

        # Initialize TTS thread
        self.tts_thread = TTSThread(self)
        self.tts_thread.set_engine(self.tts_engine)
        self.tts_thread.finished.connect(self.on_tts_finished)
        self.tts_thread.started.connect(self.on_tts_started)

        # Initialize language download tracking
        self.downloading_languages = set()
        self.download_threads = {}

        # Initialize components
        self.init_ui()
        self.setup_shortcuts()

        # Initialize processing thread
        self.processing_thread = ProcessingThread(self)
        self.processing_thread.finished.connect(self.handle_processing_finished)
        self.processing_thread.progress.connect(self.update_progress)
        self.processing_thread.error.connect(self.handle_error)
        self.processing_thread.tab_update.connect(self.update_processing_tab)

        # Initialize processing thread's models
        self.processing_thread.init_models()

        logger.debug("ScreenGPT initialization complete")

    def init_ui(self):
        """Initialize the user interface"""
        try:
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            main_layout = QHBoxLayout(central_widget)  # Main horizontal layout
            main_layout.setSpacing(20)  # Add spacing between columns

            # Left column for image display (2/3 width)
            left_column = QWidget()
            left_layout = QVBoxLayout(left_column)
            left_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins

            # Create image viewer
            self.image_viewer = ImageViewer()
            self.image_viewer.setMinimumSize(600, 400)  # Larger minimum size
            left_layout.addWidget(self.image_viewer)

            # Right column for controls and data (1/3 width)
            right_column = QWidget()
            right_layout = QVBoxLayout(right_column)
            right_layout.setContentsMargins(20, 0, 0, 0)  # Add margin on the left
            right_layout.setSpacing(15)  # Add spacing between elements

            # Create language selection group
            lang_group = QGroupBox("OCR Languages")
            lang_layout = QGridLayout()  # Use grid layout for 2x3 arrangement
            lang_layout.setSpacing(10)  # Add spacing between checkboxes

            # Create language checkboxes in a 2x3 grid
            self.lang_checkboxes = {}
            row = 0
            col = 0
            for lang_name in AVAILABLE_LANGUAGES.keys():
                checkbox = QCheckBox(lang_name)
                # Set default checked state
                if lang_name == "English" or lang_name == "Chinese (Traditional)":
                    checkbox.setChecked(True)
                else:
                    checkbox.setChecked(False)
                checkbox.setStyleSheet(
                    """
                    QCheckBox {
                        font-size: 12px;
                        padding: 5px;
                    }
                    QCheckBox::indicator {
                        width: 18px;
                        height: 18px;
                    }
                """
                )
                self.lang_checkboxes[lang_name] = checkbox
                lang_layout.addWidget(checkbox, row, col)

                # Connect checkbox to language update function
                checkbox.stateChanged.connect(self.on_language_changed)

                # Update row and column for next checkbox
                col += 1
                if col > 2:  # After 3 columns
                    col = 0
                    row += 1

            lang_group.setLayout(lang_layout)
            right_layout.addWidget(lang_group)

            # Create tab widget for different processing stages
            self.tab_widget = QTabWidget()
            self.tab_widget.setTabsClosable(False)
            right_layout.addWidget(self.tab_widget)

            # Create zoom controls
            zoom_layout = QHBoxLayout()
            zoom_layout.setSpacing(10)  # Add spacing between buttons

            # Style for zoom buttons
            zoom_button_style = """
                QPushButton {
                    padding: 8px 15px;
                    background-color: #f0f0f0;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
            """

            self.zoom_in_button = QPushButton("🔍 Zoom In")
            self.zoom_in_button.setStyleSheet(zoom_button_style)
            self.zoom_in_button.clicked.connect(self.zoom_in)
            zoom_layout.addWidget(self.zoom_in_button)

            self.zoom_out_button = QPushButton("🔍 Zoom Out")
            self.zoom_out_button.setStyleSheet(zoom_button_style)
            self.zoom_out_button.clicked.connect(self.zoom_out)
            zoom_layout.addWidget(self.zoom_out_button)

            self.reset_zoom_button = QPushButton("↺ Reset Zoom")
            self.reset_zoom_button.setStyleSheet(zoom_button_style)
            self.reset_zoom_button.clicked.connect(self.reset_zoom)
            zoom_layout.addWidget(self.reset_zoom_button)

            right_layout.addLayout(zoom_layout)

            # Create bottom button group
            button_layout = QHBoxLayout()
            button_layout.setSpacing(10)  # Add spacing between buttons

            # Style for action buttons
            action_button_style = """
                QPushButton {
                    padding: 10px 20px;
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 4px;
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

            # Add screenshot picker button
            self.picker_button = QPushButton("🎯 Select Area")
            self.picker_button.setStyleSheet(action_button_style)
            self.picker_button.clicked.connect(self.start_screen_picker)
            button_layout.addWidget(self.picker_button)

            self.analyze_button = QPushButton("Full Screen")
            self.analyze_button.setStyleSheet(action_button_style)
            self.analyze_button.clicked.connect(self.analyze_screenshot)
            button_layout.addWidget(self.analyze_button)

            # Create separate play and stop buttons
            self.play_button = QPushButton("🔊 Read Analysis")
            self.play_button.setStyleSheet(action_button_style)
            self.play_button.clicked.connect(self.start_reading)
            self.play_button.setEnabled(False)  # Initially disabled
            button_layout.addWidget(self.play_button)

            self.stop_button = QPushButton("🛑 Stop Reading")
            self.stop_button.setStyleSheet(action_button_style)
            self.stop_button.clicked.connect(self.stop_reading)
            self.stop_button.setVisible(False)  # Initially hidden
            button_layout.addWidget(self.stop_button)

            self.close_button = QPushButton("Close Program")
            self.close_button.setStyleSheet(action_button_style)
            self.close_button.clicked.connect(self.quit_application)
            button_layout.addWidget(self.close_button)

            right_layout.addLayout(button_layout)

            # Add columns to main layout with 2:1 ratio
            main_layout.addWidget(left_column, 2)  # 2/3 width
            main_layout.addWidget(right_column, 1)  # 1/3 width

            # Set window flags to show standard window controls
            self.setWindowFlags(Qt.WindowType.Window)

            # Initialize processing state
            self.current_tab_index = 0
            self.processing_tabs = {}

            # Create initial tabs
            self.create_initial_tabs()

        except Exception as e:
            logger.error(f"Error in init_ui: {e}")
            raise

    def create_initial_tabs(self):
        """Create the initial set of tabs"""
        try:
            # Create processing tab (combines original, OCR, and visual analysis)
            self.create_processing_tab("1. Processing")
            # Create prompts tab
            self.create_processing_tab("2. Analysis Prompts", is_prompts=True)
            # Create final analysis tab
            self.create_processing_tab("3. Final Analysis", is_final=True)
        except Exception as e:
            logger.error(f"Error creating initial tabs: {e}")

    def create_processing_tab(self, title, is_final=False, is_prompts=False):
        """Create a new tab for processing stage"""
        try:
            # Create tab content
            tab = QWidget()
            layout = QVBoxLayout(tab)

            # Create progress text
            progress_text = QTextEdit()
            progress_text.setReadOnly(True)
            layout.addWidget(progress_text)

            # Add tab to widget
            index = self.tab_widget.addTab(tab, title)
            self.tab_widget.setCurrentIndex(index)

            # Store tab info
            self.processing_tabs[index] = {
                "widget": tab,
                "image_label": self.image_viewer,  # Use the main image label
                "progress_text": progress_text,
                "is_final": is_final,
                "is_prompts": is_prompts,
                "zoom_level": 1.0,
                "pan_offset": QPoint(0, 0),
                "original_pixmap": None,
                "last_mouse_pos": None,
            }

            return index
        except Exception as e:
            logger.error(f"Error creating processing tab: {e}")
            return None

    def update_processing_tab(self, tab_index, image=None, text=None):
        """Update content of a processing tab"""
        try:
            if tab_index in self.processing_tabs:
                tab_info = self.processing_tabs[tab_index]

                if image is not None:
                    # Convert image to QPixmap and display
                    img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    h, w, ch = img_rgb.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(
                        img_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
                    )
                    pixmap = QPixmap.fromImage(qt_image)
                    self.image_viewer.set_image(pixmap)

                if text is not None:
                    # For the processing tab, append with clear section headers
                    if tab_index == 0:  # Processing tab
                        if "OCR Analysis" in text:
                            tab_info["progress_text"].append("\n=== OCR Analysis ===")
                        elif "Visual Analysis" in text:
                            tab_info["progress_text"].append(
                                "\n=== Visual Analysis ==="
                            )
                        elif "AI Analysis" in text:
                            tab_info["progress_text"].append("\n=== AI Analysis ===")
                    tab_info["progress_text"].append(text)
                    # Ensure the text is visible
                    tab_info["progress_text"].verticalScrollBar().setValue(
                        tab_info["progress_text"].verticalScrollBar().maximum()
                    )

                # Switch to this tab
                self.tab_widget.setCurrentIndex(tab_index)
                QApplication.processEvents()
        except Exception as e:
            logger.error(f"Error updating processing tab: {e}")

    def show_full_image(self, tab_index):
        """Display the image at full size in the tab"""
        try:
            if tab_index in self.processing_tabs:
                tab_info = self.processing_tabs[tab_index]
                if tab_info["original_pixmap"]:
                    # Scale the image to fit the label while maintaining aspect ratio
                    scaled_pixmap = tab_info["original_pixmap"].scaled(
                        tab_info["image_label"].size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )

                    # Create a new pixmap with the label size
                    final_pixmap = QPixmap(tab_info["image_label"].size())
                    final_pixmap.fill(Qt.GlobalColor.transparent)

                    # Calculate center position
                    center_x = (
                        tab_info["image_label"].width() - scaled_pixmap.width()
                    ) // 2
                    center_y = (
                        tab_info["image_label"].height() - scaled_pixmap.height()
                    ) // 2

                    # Draw the scaled pixmap centered
                    painter = QPainter(final_pixmap)
                    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.drawPixmap(center_x, center_y, scaled_pixmap)
                    painter.end()

                    tab_info["image_label"].setPixmap(final_pixmap)
        except Exception as e:
            logger.error(f"Error in show_full_image: {e}")

    def mouse_press_event(self, event):
        """Handle mouse press event for dragging"""
        current_tab = self.tab_widget.currentIndex()
        if current_tab in self.processing_tabs:
            tab_info = self.processing_tabs[current_tab]
            if event.button() == Qt.MouseButton.LeftButton:
                tab_info["last_mouse_pos"] = event.pos()

    def mouse_move_event(self, event):
        """Handle mouse move event for dragging"""
        current_tab = self.tab_widget.currentIndex()
        if current_tab in self.processing_tabs:
            tab_info = self.processing_tabs[current_tab]
            if tab_info["last_mouse_pos"] is not None and tab_info["original_pixmap"]:
                delta = event.pos() - tab_info["last_mouse_pos"]
                tab_info["pan_offset"] += delta
                tab_info["last_mouse_pos"] = event.pos()
                self.update_zoom_for_tab(current_tab)

    def mouse_release_event(self, event):
        """Handle mouse release event for dragging"""
        current_tab = self.tab_widget.currentIndex()
        if current_tab in self.processing_tabs:
            tab_info = self.processing_tabs[current_tab]
            if event.button() == Qt.MouseButton.LeftButton:
                tab_info["last_mouse_pos"] = None

    def mouse_double_click_event(self, event):
        """Handle double click event for zooming to cursor position"""
        try:
            current_tab = self.tab_widget.currentIndex()
            if current_tab in self.processing_tabs:
                tab_info = self.processing_tabs[current_tab]
                if tab_info["original_pixmap"]:
                    # Get cursor position relative to the image label
                    cursor_pos = event.pos()

                    # Calculate the center position of the current view
                    center_x = (
                        tab_info["image_label"].width()
                        - tab_info["original_pixmap"].width()
                    ) // 2
                    center_y = (
                        tab_info["image_label"].height()
                        - tab_info["original_pixmap"].height()
                    ) // 2

                    # Calculate the cursor position relative to the original image
                    rel_x = cursor_pos.x() - center_x - tab_info["pan_offset"].x()
                    rel_y = cursor_pos.y() - center_y - tab_info["pan_offset"].y()

                    # Zoom in
                    old_zoom = tab_info["zoom_level"]
                    tab_info["zoom_level"] *= 2.0

                    # Calculate new pan offset to keep cursor position fixed
                    zoom_factor = tab_info["zoom_level"] / old_zoom
                    tab_info["pan_offset"] = QPoint(
                        int(cursor_pos.x() - (rel_x * zoom_factor)),
                        int(cursor_pos.y() - (rel_y * zoom_factor)),
                    )

                    self.update_zoom_for_tab(current_tab)
        except Exception as e:
            logger.error(f"Error in mouse_double_click_event: {e}")

    def update_zoom_for_tab(self, tab_index):
        """Update the image display with current zoom level and pan offset for a specific tab"""
        try:
            if tab_index in self.processing_tabs:
                tab_info = self.processing_tabs[tab_index]
                if tab_info["original_pixmap"]:
                    # Only apply zoom if zoom level is not 1.0
                    if tab_info["zoom_level"] != 1.0:
                        # Calculate scaled size
                        scaled_size = (
                            tab_info["original_pixmap"].size() * tab_info["zoom_level"]
                        )
                        scaled_pixmap = tab_info["original_pixmap"].scaled(
                            scaled_size,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )

                        # Create a new pixmap with the label size
                        final_pixmap = QPixmap(tab_info["image_label"].size())
                        final_pixmap.fill(Qt.GlobalColor.transparent)

                        # Calculate center position
                        center_x = (
                            tab_info["image_label"].width() - scaled_pixmap.width()
                        ) // 2
                        center_y = (
                            tab_info["image_label"].height() - scaled_pixmap.height()
                        ) // 2

                        # Draw the scaled pixmap with pan offset
                        painter = QPainter(final_pixmap)
                        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                        painter.drawPixmap(
                            center_x + tab_info["pan_offset"].x(),
                            center_y + tab_info["pan_offset"].y(),
                            scaled_pixmap,
                        )
                        painter.end()

                        tab_info["image_label"].setPixmap(final_pixmap)
                    else:
                        # If zoom level is 1.0, show full image
                        self.show_full_image(tab_index)
        except Exception as e:
            logger.error(f"Error in update_zoom_for_tab: {e}")

    def analyze_screenshot(self):
        """Capture and analyze screenshot"""
        try:
            # Clear existing tab contents
            for tab_info in self.processing_tabs.values():
                if "progress_text" in tab_info:
                    tab_info["progress_text"].clear()
                if "image_label" in tab_info:
                    tab_info["image_label"].clear()

            # Disable analyze button and read button during processing
            self.analyze_button.setEnabled(False)
            self.play_button.setEnabled(False)
            self.play_button.setVisible(True)
            self.stop_button.setVisible(False)

            # Update processing tab with initial message
            self.update_processing_tab(0, text="✅ Starting screenshot analysis...")
            QApplication.processEvents()

            # Capture screenshot
            self.update_processing_tab(0, text="✅ Capturing screenshot...")
            QApplication.processEvents()

            img = self.capture_screen()
            if img is None:
                self.processing_tabs[0]["progress_text"].append(
                    "❌ Failed to capture screenshot"
                )
                self.analyze_button.setEnabled(True)
                self.play_button.setEnabled(False)
                self.stop_button.setEnabled(False)
                return

            # Update screenshot tab with success message
            self.update_processing_tab(
                0, image=img, text="✅ Screenshot captured successfully"
            )
            QApplication.processEvents()

            # Set the image in the processing thread
            self.processing_thread.set_image(img)

            # Start processing in background
            self.processing_thread.start()

        except Exception as e:
            logger.error(f"Error in analyze_screenshot: {e}")
            self.processing_tabs[0]["progress_text"].append(f"❌ Error: {str(e)}")
            self.analyze_button.setEnabled(True)
            self.play_button.setEnabled(False)
            self.stop_button.setEnabled(False)

    def handle_processing_finished(self, result):
        """Handle the completion of background processing"""
        try:
            if result:
                # Find the final analysis tab
                final_tab = None
                for index, tab_info in self.processing_tabs.items():
                    if tab_info["is_final"]:
                        final_tab = index
                        break

                if final_tab is not None:
                    # Only append the completion message, not the analysis again
                    self.processing_tabs[final_tab]["progress_text"].append(
                        "\n✨ Analysis complete!"
                    )
                    # Enable the read button only if analysis was successful
                    self.play_button.setEnabled(True)
                    self.play_button.setVisible(True)
                    self.stop_button.setVisible(False)
            # Re-enable analyze button
            self.analyze_button.setEnabled(True)
        except Exception as e:
            logger.error(f"Error handling processing finished: {e}")
            self.processing_tabs[final_tab]["progress_text"].append(
                f"❌ Error: {str(e)}"
            )
            self.analyze_button.setEnabled(True)
            self.play_button.setEnabled(False)
            self.play_button.setVisible(True)
            self.stop_button.setVisible(False)

    def update_progress(self, message):
        """Update progress message in the UI"""
        try:
            # Find the current processing tab
            current_tab = self.tab_widget.currentIndex()
            if current_tab in self.processing_tabs:
                self.processing_tabs[current_tab]["progress_text"].append(message)
            QApplication.processEvents()
        except Exception as e:
            logger.error(f"Error updating progress: {e}")

    def handle_error(self, error_message):
        """Handle errors from the processing thread"""
        try:
            # Find the current processing tab
            current_tab = self.tab_widget.currentIndex()
            if current_tab in self.processing_tabs:
                self.processing_tabs[current_tab]["progress_text"].append(
                    f"❌ Error: {error_message}"
                )
            self.analyze_button.setEnabled(True)
            self.play_button.setEnabled(False)
            self.play_button.setVisible(True)
            self.stop_button.setVisible(False)
        except Exception as e:
            logger.error(f"Error handling error message: {e}")

    def setup_shortcuts(self):
        """Set up keyboard shortcuts"""
        try:
            # Create a global shortcut for Analyze Screenshot (Ctrl+Alt+A)
            self.shortcut = QShortcut(QKeySequence("Ctrl+Alt+A"), self)
            self.shortcut.setContext(
                Qt.ShortcutContext.ApplicationShortcut
            )  # Make it work globally
            self.shortcut.activated.connect(self.analyze_screenshot)

            # Add alternative shortcuts
            self.shortcut2 = QShortcut(QKeySequence("Ctrl+Shift+A"), self)
            self.shortcut2.setContext(Qt.ShortcutContext.ApplicationShortcut)
            self.shortcut2.activated.connect(self.analyze_screenshot)

            # Add a third alternative shortcut
            self.shortcut3 = QShortcut(QKeySequence("Alt+A"), self)
            self.shortcut3.setContext(Qt.ShortcutContext.ApplicationShortcut)
            self.shortcut3.activated.connect(self.analyze_screenshot)

            # Add Ctrl+Alt+A+S shortcut
            self.shortcut4 = QShortcut(QKeySequence("Ctrl+Alt+A+S"), self)
            self.shortcut4.setContext(Qt.ShortcutContext.ApplicationShortcut)
            self.shortcut4.activated.connect(self.analyze_screenshot)

            logger.debug("Shortcuts set up successfully")
        except Exception as e:
            logger.error(f"Failed to set up shortcuts: {e}")

    def keyPressEvent(self, event):
        """Override key press event to handle global shortcuts"""
        try:
            # Check for Ctrl+Alt+A
            if event.key() == Qt.Key.Key_A and event.modifiers() == (
                Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier
            ):
                self.analyze_screenshot()
                event.accept()
                return

            # Check for Ctrl+Shift+A
            if event.key() == Qt.Key.Key_A and event.modifiers() == (
                Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
            ):
                self.analyze_screenshot()
                event.accept()
                return

            # Check for Alt+A
            if (
                event.key() == Qt.Key.Key_A
                and event.modifiers() == Qt.KeyboardModifier.AltModifier
            ):
                self.analyze_screenshot()
                event.accept()
                return

            # Check for Ctrl+Alt+A+S
            if event.key() == Qt.Key.Key_S and event.modifiers() == (
                Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier
            ):
                self.analyze_screenshot()
                event.accept()
                return

            super().keyPressEvent(event)
        except Exception as e:
            logger.error(f"Error in keyPressEvent: {e}")
            super().keyPressEvent(event)

    def capture_screen(self):
        """Capture the screen and return the image"""
        try:
            # Hide the window
            self.hide()
            QApplication.processEvents()
            time.sleep(0.1)  # Give time for the window to hide

            with mss.mss() as sct:
                monitor = sct.monitors[1]
                logger.debug(f"Capturing screen from monitor: {monitor}")

                # Capture at full resolution
                screenshot = sct.grab(monitor)
                img = np.array(screenshot)
                # Convert BGRA to BGR without quality loss
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                logger.debug(f"Screen captured successfully. Image shape: {img.shape}")

                # Show the window again
                self.show()
                self.raise_()  # Bring window to front
                self.activateWindow()  # Activate the window

                return img
        except Exception as e:
            logger.error(f"Failed to capture screen: {e}")
            # Make sure window is shown again even if there's an error
            self.show()
            self.raise_()
            self.activateWindow()
            self.result_text.append("Error: Failed to capture screen")
            return None

    def reset_program(self):
        """Reset the entire program state"""
        try:
            # Clear the image display
            self.image_viewer.clear()

            # Clear all tab contents
            for tab_info in self.processing_tabs.values():
                if "progress_text" in tab_info:
                    tab_info["progress_text"].clear()

            # Enable analyze button, disable read button
            self.analyze_button.setEnabled(True)
            self.play_button.setEnabled(False)
            self.play_button.setVisible(True)
            self.stop_button.setVisible(False)

            # Switch to first tab
            self.tab_widget.setCurrentIndex(0)

            logger.debug("Program reset complete")
        except Exception as e:
            logger.error(f"Error resetting program: {e}")

    def zoom_in(self):
        """Zoom in the image"""
        if self.image_viewer.original_pixmap:
            self.image_viewer.zoom_factor *= 1.2
            self.image_viewer.update_image()

    def zoom_out(self):
        """Zoom out the image"""
        if self.image_viewer.original_pixmap:
            self.image_viewer.zoom_factor /= 1.2
            self.image_viewer.update_image()

    def reset_zoom(self):
        """Reset zoom level to original"""
        if self.image_viewer.original_pixmap:
            self.image_viewer.zoom_factor = 1.0
            self.image_viewer.update_image()

    def close_tab(self, index):
        """Close a processing tab - disabled"""
        pass  # Tabs cannot be closed

    def on_tts_started(self):
        """Handle TTS start"""
        self.play_button.setVisible(False)
        self.stop_button.setVisible(True)
        self.stop_button.setEnabled(True)  # Enable stop button

    def quit_application(self):
        """Properly quit the application"""
        try:
            # Stop TTS if running
            if self.tts_thread.isRunning():
                try:
                    self.tts_thread.stop()
                    # Wait for the thread to finish with a timeout
                    if not self.tts_thread.wait(1000):  # Wait up to 1 second
                        logger.warning("TTS thread did not stop gracefully")
                except Exception as e:
                    logger.error(f"Error stopping TTS thread: {e}")

            # Stop processing thread if running
            if self.processing_thread.isRunning():
                try:
                    self.processing_thread.terminate()
                    self.processing_thread.wait()
                except Exception as e:
                    logger.error(f"Error stopping processing thread: {e}")

            # Quit the application
            QApplication.quit()
        except Exception as e:
            logger.error(f"Error quitting application: {e}")
            # Force quit if normal quit fails
            QApplication.exit(0)

    def start_reading(self):
        """Start or stop reading the analysis"""
        try:
            # If TTS is already running, stop it
            if self.tts_thread.isRunning():
                self.stop_reading()
                return

            # Find the final analysis tab
            final_tab = None
            for index, tab_info in self.processing_tabs.items():
                if tab_info["is_final"]:
                    final_tab = index
                    break

            if final_tab is not None:
                # Get the text from the progress text widget
                text = self.processing_tabs[final_tab]["progress_text"].toPlainText()

                # Extract only the analysis part (after "Final Analysis:")
                if "Final Analysis:" in text:
                    analysis_text = text.split("Final Analysis:")[1].strip()
                    # Remove the completion message if present
                    if "✨ Analysis complete!" in analysis_text:
                        analysis_text = analysis_text.split("✨ Analysis complete!")[
                            0
                        ].strip()

                    # Set the text to be read
                    self.tts_thread.set_text(analysis_text)

                    # Start the TTS thread
                    self.tts_thread.start()
        except Exception as e:
            logger.error(f"Error in start_reading: {e}")
            self.stop_reading()

    def stop_reading(self):
        """Stop the current reading"""
        try:
            if self.tts_thread.isRunning():
                # First update UI to prevent user confusion
                self.play_button.setVisible(True)
                self.play_button.setEnabled(True)
                self.stop_button.setVisible(False)
                self.stop_button.setEnabled(False)

                # Then stop the TTS thread
                self.tts_thread.stop()
                # Wait for the thread to finish with a timeout
                if not self.tts_thread.wait(1000):  # Wait up to 1 second
                    logger.warning("TTS thread did not stop gracefully")

            # Ensure buttons are in correct state
            self.play_button.setVisible(True)
            self.play_button.setEnabled(True)
            self.stop_button.setVisible(False)
            self.stop_button.setEnabled(False)
        except Exception as e:
            logger.error(f"Error in stop_reading: {e}")
            # Ensure buttons are in correct state even if error occurs
            self.play_button.setVisible(True)
            self.play_button.setEnabled(True)
            self.stop_button.setVisible(False)
            self.stop_button.setEnabled(False)

    def on_tts_finished(self):
        """Handle TTS completion"""
        self.play_button.setVisible(True)
        self.play_button.setEnabled(True)  # Re-enable play button
        self.stop_button.setVisible(False)
        self.stop_button.setEnabled(False)  # Disable stop button

    def start_screen_picker(self):
        """Start the custom screen picker"""
        try:
            # Hide the main window temporarily
            self.hide()
            QApplication.processEvents()
            time.sleep(0.1)  # Small delay to ensure window is hidden

            # Create and show the screen picker
            self.screen_picker = ScreenPicker()
            self.screen_picker.image_captured.connect(self.handle_picked_image)
            self.screen_picker.show()

            # Use a timer to ensure the picker is properly activated
            QTimer.singleShot(200, lambda: self.activate_picker())

        except Exception as e:
            logger.error(f"Error in screen picker: {e}")
            self.show()  # Ensure main window is shown again
            QMessageBox.warning(
                self, "Error", f"Failed to start screen picker: {str(e)}"
            )

    def activate_picker(self):
        """Activate the screen picker with a slight delay"""
        try:
            if hasattr(self, "screen_picker"):
                self.screen_picker.raise_()
                self.screen_picker.activateWindow()
                self.screen_picker.setWindowState(Qt.WindowState.WindowActive)
                self.screen_picker.update()  # Force redraw
                QApplication.processEvents()
        except Exception as e:
            logger.error(f"Error activating picker: {e}")
            self.show()  # Show main window if activation fails

    def handle_picked_image(self, image):
        """Handle the image selected by the user"""
        try:
            # Show the main window
            self.show()
            self.raise_()
            self.activateWindow()

            # IMPORTANT: Verify the image shape and type
            if image is None:
                logger.error("Received None image in handle_picked_image")
                QMessageBox.warning(self, "Error", "No image data received.")
                return

            # Log image details
            height, width = image.shape[:2]
            logger.debug(f"Processing image in handle_picked_image: {width}x{height}")

            # Ensure image is in BGR format for OpenCV
            if len(image.shape) == 2:  # Grayscale
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            elif image.shape[2] == 4:  # RGBA
                image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

            # Create a copy to ensure we're not working with a reference
            processed_image = image.copy()

            # Update the image viewer DIRECTLY - this is key
            img_rgb = cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB)
            h, w, ch = img_rgb.shape
            bytes_per_line = ch * w
            qt_image = QImage(
                img_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
            )
            pixmap = QPixmap.fromImage(qt_image)
            self.image_viewer.set_image(pixmap)

            # Force UI update
            QApplication.processEvents()

            # Verify the image is displayed correctly
            logger.debug("Image displayed in viewer")

            # Set the image in the processing thread
            self.processing_thread.set_image(processed_image)

            # Start processing
            self.analyze_image()

        except Exception as e:
            logger.error(f"Error handling picked image: {e}")
            logger.error(f"Error details: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to process image: {str(e)}")

    def analyze_image(self):
        """Analyze the current image without capturing a new screenshot"""
        try:
            # Clear existing tab contents
            for tab_info in self.processing_tabs.values():
                if "progress_text" in tab_info:
                    tab_info["progress_text"].clear()

            # Disable analyze button and read button during processing
            self.analyze_button.setEnabled(False)
            self.play_button.setEnabled(False)
            self.play_button.setVisible(True)
            self.stop_button.setVisible(False)

            # Update processing tab
            self.update_processing_tab(0, text="✅ Starting image analysis...")
            QApplication.processEvents()

            # Start processing in background
            self.processing_thread.start()

        except Exception as e:
            logger.error(f"Error in analyze_image: {e}")
            if 0 in self.processing_tabs:
                self.processing_tabs[0]["progress_text"].append(f"❌ Error: {str(e)}")
            self.analyze_button.setEnabled(True)
            self.play_button.setEnabled(False)
            self.stop_button.setEnabled(False)

    def on_language_changed(self):
        """Handle language checkbox state changes"""
        try:
            selected_languages = []
            selected_scripts = set()

            # First, check if English is selected
            english_selected = self.lang_checkboxes["English"].isChecked()

            # Collect selected languages and their scripts
            for lang_name, checkbox in self.lang_checkboxes.items():
                if checkbox.isChecked():
                    lang_info = AVAILABLE_LANGUAGES[lang_name]
                    selected_languages.append(lang_info["code"])
                    selected_scripts.add(lang_info["script"])

            # If no languages selected, default to English
            if not selected_languages:
                selected_languages = ["en"]
                self.lang_checkboxes["English"].setChecked(True)
            else:
                # Handle mutual exclusivity for Asian languages
                asian_langs = ["Chinese (Traditional)", "Japanese", "Korean"]
                selected_asian = [
                    lang
                    for lang in asian_langs
                    if self.lang_checkboxes[lang].isChecked()
                ]

                if len(selected_asian) > 1:
                    # Keep only the last selected Asian language
                    last_selected = selected_asian[-1]
                    for lang in asian_langs:
                        if lang != last_selected:
                            self.lang_checkboxes[lang].setChecked(False)

                    # Update selected languages
                    selected_languages = ["en"] if english_selected else []
                    selected_languages.append(
                        AVAILABLE_LANGUAGES[last_selected]["code"]
                    )

                # If English is selected, we can combine it with one other language
                if english_selected and len(selected_languages) > 2:
                    # Keep English and the first other selected language
                    other_langs = [lang for lang in selected_languages if lang != "en"]
                    selected_languages = ["en", other_langs[0]]
                    # Update checkboxes to reflect this
                    for lang_name, checkbox in self.lang_checkboxes.items():
                        if lang_name != "English":
                            checkbox.setChecked(False)
                    if other_langs[0] in AVAILABLE_LANGUAGES.values():
                        for lang_name, lang_info in AVAILABLE_LANGUAGES.items():
                            if lang_info["code"] == other_langs[0]:
                                self.lang_checkboxes[lang_name].setChecked(True)
                                break
                # If no English, only allow one language
                elif not english_selected and len(selected_languages) > 1:
                    # Keep only the first selected language
                    selected_languages = [selected_languages[0]]
                    # Update checkboxes to reflect this
                    first_lang = selected_languages[0]
                    for lang_name, checkbox in self.lang_checkboxes.items():
                        checkbox.setChecked(
                            AVAILABLE_LANGUAGES[lang_name]["code"] == first_lang
                        )

            try:
                # Check if any selected language needs to be downloaded
                for lang_code in selected_languages:
                    if lang_code != "en":
                        self.start_language_download(lang_code)

                # Create a new reader with selected languages
                self.processing_thread.reader = easyocr.Reader(
                    selected_languages, gpu=True
                )
                logger.info(f"EasyOCR updated with languages: {selected_languages}")

                # Show a message if languages were automatically adjusted
                if len(selected_languages) > 1:
                    QMessageBox.information(
                        self,
                        "Language Selection",
                        "EasyOCR supports combining English with one other language, or using a single non-English language.\n"
                        "Your selection has been adjusted accordingly.",
                    )
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error updating languages: {error_msg}")

                # Handle specific error messages
                if "is only compatible with English" in error_msg:
                    # Extract the language code from the error message
                    lang_code = (
                        error_msg.split('"')[1]
                        if '"' in error_msg
                        else "selected language"
                    )

                    # Find the language name from the code
                    lang_name = next(
                        (
                            name
                            for name, info in AVAILABLE_LANGUAGES.items()
                            if info["code"] == lang_code
                        ),
                        lang_code,
                    )

                    # Show user-friendly error message
                    QMessageBox.warning(
                        self,
                        "Language Compatibility",
                        f"{lang_name} can only be used with English.\n\n"
                        "Please select either:\n"
                        f"• {lang_name} + English\n"
                        "• {lang_name} alone\n"
                        "• English alone",
                    )

                    # Reset to English only
                    for name, checkbox in self.lang_checkboxes.items():
                        checkbox.setChecked(name == "English")
                    self.processing_thread.reader = easyocr.Reader(["en"], gpu=True)
                else:
                    # Generic error handling
                    QMessageBox.warning(
                        self,
                        "Language Selection Error",
                        "There was an error setting up the language selection.\n"
                        "Falling back to English only.",
                    )
                    # Fallback to English only
                    self.processing_thread.reader = easyocr.Reader(["en"], gpu=True)
                    logger.info("Falling back to English only due to error")

        except Exception as e:
            logger.error(f"Error in language selection: {e}")
            # Fallback to English only
            self.processing_thread.reader = easyocr.Reader(["en"], gpu=True)
            logger.info("Falling back to English only due to error")

    def start_language_download(self, lang_code):
        """Start downloading a language pack in the background"""
        try:
            # Skip if already downloading or if it's English
            if lang_code in self.downloading_languages or lang_code == "en":
                return

            # Check if language pack already exists
            try:
                # Try to create a reader with the language to check if it exists
                test_reader = easyocr.Reader([lang_code], download_enabled=False)
                # If we get here, the language pack exists
                logger.info(f"Language pack for {lang_code} already exists")
                return
            except Exception as e:
                # If we get an error about missing language pack, proceed with download
                if "language pack" not in str(e).lower():
                    logger.error(f"Error checking language pack: {e}")
                    return

            # Start download process
            self.downloading_languages.add(lang_code)

            # Create and start download thread
            download_thread = LanguageDownloadThread(lang_code)
            download_thread.download_complete.connect(
                self.on_language_download_complete
            )
            download_thread.download_error.connect(self.on_language_download_error)
            download_thread.download_progress.connect(
                self.on_language_download_progress
            )

            # Store thread reference
            self.download_threads[lang_code] = download_thread

            # Start download
            download_thread.start()

            # Show download started message
            lang_name = next(
                (
                    name
                    for name, info in AVAILABLE_LANGUAGES.items()
                    if info["code"] == lang_code
                ),
                lang_code,
            )
            QMessageBox.information(
                self,
                "Language Pack Download",
                f"Downloading {lang_name} language pack in the background.\n"
                "You can continue using the application while it downloads.",
            )
        except Exception as e:
            logger.error(f"Error starting language download: {e}")
            self.downloading_languages.discard(lang_code)

    def on_language_download_complete(self, lang_code):
        """Handle completion of language pack download"""
        try:
            self.downloading_languages.discard(lang_code)
            if lang_code in self.download_threads:
                del self.download_threads[lang_code]

            # Show completion message
            lang_name = next(
                (
                    name
                    for name, info in AVAILABLE_LANGUAGES.items()
                    if info["code"] == lang_code
                ),
                lang_code,
            )
            QMessageBox.information(
                self,
                "Download Complete",
                f"{lang_name} language pack has been downloaded successfully.",
            )
        except Exception as e:
            logger.error(f"Error handling download completion: {e}")

    def on_language_download_error(self, lang_code, error):
        """Handle language pack download error"""
        try:
            self.downloading_languages.discard(lang_code)
            if lang_code in self.download_threads:
                del self.download_threads[lang_code]

            # Show error message
            lang_name = next(
                (
                    name
                    for name, info in AVAILABLE_LANGUAGES.items()
                    if info["code"] == lang_code
                ),
                lang_code,
            )
            QMessageBox.warning(
                self,
                "Download Error",
                f"Failed to download {lang_name} language pack:\n{error}",
            )
        except Exception as e:
            logger.error(f"Error handling download error: {e}")

    def on_language_download_progress(self, lang_code, progress):
        """Handle language pack download progress updates"""
        try:
            # Update progress in UI if needed
            logger.debug(f"Download progress for {lang_code}: {progress}")
        except Exception as e:
            logger.error(f"Error handling download progress: {e}")

    def _clamp_pan_offset(self):
        """Ensure the image cannot be dragged out of view."""
        if not self.image_viewer.original_pixmap:
            return
        scaled_size = (
            self.image_viewer.original_pixmap.size() * self.image_viewer.zoom_factor
        )
        min_x = min(0, self.width() - scaled_size.width())
        min_y = min(0, self.height() - scaled_size.height())
        max_x = max(0, self.width() - scaled_size.width())
        max_y = max(0, self.height() - scaled_size.height())
        self.image_viewer.pan_offset.setX(
            max(min_x, min(self.image_viewer.pan_offset.x(), max_x))
        )
        self.image_viewer.pan_offset.setY(
            max(min_y, min(self.image_viewer.pan_offset.y(), max_y))
        )
