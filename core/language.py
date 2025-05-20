from PyQt6.QtCore import QThread, pyqtSignal
import easyocr
import logging

class LanguageDownloadThread(QThread):
    """Thread for downloading language packs in the background"""

    download_complete = pyqtSignal(str)  # Signal emitted when download is complete
    download_error = pyqtSignal(
        str, str
    )  # Signal emitted when download fails (lang_code, error)
    download_progress = pyqtSignal(
        str, str
    )  # Signal emitted for progress updates (lang_code, progress)

    def __init__(self, lang_code):
        super().__init__()
        self.lang_code = lang_code

    def run(self):
        try:
            # Create a temporary reader to trigger download
            reader = easyocr.Reader([self.lang_code], download_enabled=True)
            self.download_complete.emit(self.lang_code)
        except Exception as e:
            self.download_error.emit(self.lang_code, str(e))

