import cv2
import numpy as np
import logging


def preprocess_image_for_ocr(img):
    """Preprocess image for better OCR results"""
    try:
        # Create a copy of the image for processing
        processed = img.copy()
        # Convert to grayscale
        if len(processed.shape) == 3:
            gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
        else:
            gray = processed
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        # Denoise
        denoised = cv2.fastNlMeansDenoising(thresh)
        # Sharpen
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        sharpened = cv2.filter2D(denoised, -1, kernel)
        # Increase contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(sharpened)
        # Convert back to BGR if original was color
        if len(img.shape) == 3:
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        return enhanced
    except Exception as e:
        logging.error(f"Error in image preprocessing: {e}")
        return img  # Return original image if preprocessing fails
