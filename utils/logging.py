import logging
import os
import sys

def setup_logging(log_level=logging.DEBUG, log_file=None):
    """
    Configure logging for the ScreenGPT application.
    
    Args:
        log_level: The logging level (default: DEBUG)
        log_file: Optional file path to write logs to
    """
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers (in case this function is called multiple times)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Create file handler if a log file is specified
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Log the startup message
    logging.info(f"Logging initialized at level {logging.getLevelName(log_level)}")
    if log_file:
        logging.info(f"Logs will be saved to {log_file}")
    
    return root_logger