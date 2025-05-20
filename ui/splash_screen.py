from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont


class LoadingSplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Create logo container
        logo_container = QWidget()
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create logo label with icon
        self.logo_label = QLabel("🎯")
        self.logo_label.setStyleSheet(
            """
            QLabel {
                font-size: 48px;
                color: #2196F3;
            }
        """
        )
        logo_layout.addWidget(self.logo_label)

        # Create app name label
        self.app_name = QLabel("ScreenGPT")
        self.app_name.setStyleSheet(
            """
            QLabel {
                color: #2196F3;
                font-size: 24px;
                font-weight: bold;
                font-family: 'Helvetica Neue', Arial, sans-serif;
            }
        """
        )
        logo_layout.addWidget(self.app_name)

        # Create tagline
        self.tagline = QLabel("Universal Screenshot Analysis")
        self.tagline.setStyleSheet(
            """
            QLabel {
                color: #666666;
                font-size: 14px;
                font-family: 'Helvetica Neue', Arial, sans-serif;
            }
        """
        )
        logo_layout.addWidget(self.tagline)

        main_layout.addWidget(logo_container)

        # Create loading container
        loading_container = QWidget()
        loading_layout = QVBoxLayout(loading_container)
        loading_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create loading bar
        self.loading_bar = QProgressBar()
        self.loading_bar.setFixedSize(200, 6)  # Made slightly taller
        self.loading_bar.setTextVisible(False)
        self.loading_bar.setStyleSheet(
            """
            QProgressBar {
                background-color: #E0E0E0;
                border: none;
                border-radius: 3px;
                min-height: 6px;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 3px;
            }
        """
        )
        loading_layout.addWidget(self.loading_bar)

        # Create loading text
        self.loading_text = QLabel("Initializing...")
        self.loading_text.setStyleSheet(
            """
            QLabel {
                color: #666666;
                font-size: 12px;
                font-family: 'Helvetica Neue', Arial, sans-serif;
            }
        """
        )
        loading_layout.addWidget(self.loading_text)

        main_layout.addWidget(loading_container)

        # Set background
        self.setStyleSheet(
            """
            QWidget {
                background-color: white;
                border-radius: 12px;
            }
        """
        )

        # Set size and position
        self.setFixedSize(300, 250)
        self.center_on_screen()

        # Start loading animation
        self.start_loading_animation()

    def center_on_screen(self):
        """Center the splash screen on the screen"""
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2
        )

    def start_loading_animation(self):
        """Start the loading bar animation"""
        # Set initial progress to 5%
        self.loading_bar.setValue(10)

        # Create initial animation to 85%
        self.initial_animation = QPropertyAnimation(self.loading_bar, b"value")
        self.initial_animation.setDuration(2000)  # 2 seconds
        self.initial_animation.setStartValue(10)  # Start from 10%
        self.initial_animation.setEndValue(85)
        self.initial_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Create final animation to 100%
        self.final_animation = QPropertyAnimation(self.loading_bar, b"value")
        self.final_animation.setDuration(200)  # 0.2 seconds
        self.final_animation.setStartValue(85)
        self.final_animation.setEndValue(100)
        self.final_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # Connect animations
        self.initial_animation.finished.connect(self.final_animation.start)

        # Start initial animation
        self.initial_animation.start()

        # Update loading text
        self.loading_texts = [
            "Initializing...",
            "Loading models...",
            "Preparing interface...",
            "Almost ready...",
        ]
        self.current_text_index = 0
        self.text_timer = QTimer(self)
        self.text_timer.timeout.connect(self.update_loading_text)
        self.text_timer.start(500)  # Update text every 500ms

    def update_loading_text(self):
        """Update the loading text with animation"""
        self.current_text_index = (self.current_text_index + 1) % len(
            self.loading_texts
        )
        self.loading_text.setText(self.loading_texts[self.current_text_index])

        # Fade animation for text
        fade = QPropertyAnimation(self.loading_text, b"windowOpacity")
        fade.setDuration(200)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.start()
