# main.py

import sys
import logging
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread  # Added missing import
from app import ScreenGPT
from utils.logging import setup_logging
import os


def main():
    try:
        # Set up logging first thing
        log_file = os.path.join(os.path.dirname(__file__), "logs", "screengpt.log")
        setup_logging(log_file=log_file)

        # Initialize the application
        app = QApplication(sys.argv)

        # Show splash screen
        from ui.splash_screen import LoadingSplashScreen

        splash = LoadingSplashScreen()
        splash.show()
        app.processEvents()

        # Create and initialize main application window
        window = ScreenGPT()

        # Wait for splash screen to finish animation
        while splash.loading_bar.value() < 100:
            app.processEvents()
            time.sleep(0.01)  # Using time.sleep() instead of QThread.msleep()

        # Hide splash and show main window
        splash.hide()
        window.show()

        # Start event loop
        sys.exit(app.exec())

    except Exception as e:
        logging.critical(f"Fatal error in main: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
