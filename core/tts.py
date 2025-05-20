from PyQt6.QtCore import QThread, pyqtSignal
import pyttsx3
import time
import logging

logger = logging.getLogger(__name__)


class TTSThread(QThread):
    """Thread for handling text-to-speech without blocking the UI"""

    finished = pyqtSignal()  # Signal emitted when TTS is finished
    started = pyqtSignal()  # Signal emitted when TTS starts

    def __init__(self, parent=None):
        super().__init__(parent)
        self.text = ""
        self.tts_engine = None
        self._stop_requested = False
        self._is_running = False

    def set_text(self, text):
        """Set the text to be read"""
        self.text = text

    def set_engine(self, engine):
        """Set the TTS engine to use"""
        self.tts_engine = engine

    def stop(self):
        """Request the thread to stop"""
        try:
            self._stop_requested = True
            self._is_running = False
            # Try to stop any active TTS
            if self.tts_engine:
                try:
                    self.tts_engine.stop()
                except Exception as e:
                    logger.error(f"Error stopping TTS engine: {e}")
                finally:
                    # Create a new engine instance to ensure clean state
                    try:
                        self.tts_engine = pyttsx3.init()
                        self.tts_engine.setProperty("rate", 150)
                        self.tts_engine.setProperty("volume", 0.9)
                    except Exception as e:
                        logger.error(f"Error reinitializing TTS engine: {e}")
        except Exception as e:
            logger.error(f"Error in TTS stop: {e}")

    def run(self):
        """Run the TTS processing"""
        if self._is_running:
            return

        self._stop_requested = False
        self._is_running = True

        try:
            if self.tts_engine and self.text:
                # Emit started signal before starting TTS
                self.started.emit()
                # Small delay to ensure UI updates
                time.sleep(0.1)

                if not self._stop_requested:
                    self.tts_engine.say(self.text)
                    self.tts_engine.runAndWait()

        except Exception as e:
            logger.error(f"Error in TTS thread: {e}")
            # Stop the TTS engine
            try:
                if self.tts_engine:
                    self.tts_engine.stop()
            except:
                pass
            # Create a new engine instance to ensure clean state
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty("rate", 150)
                self.tts_engine.setProperty("volume", 0.9)
            except Exception as e:
                logger.error(f"Error reinitializing TTS engine: {e}")

        finally:
            self._is_running = False
            # Ensure we emit finished signal even if there's an error
            self.finished.emit()
            # Clean up the engine
            try:
                if self.tts_engine:
                    self.tts_engine.stop()
            except:
                pass
