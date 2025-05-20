# utils/image_processing.py

import cv2
import numpy as np
import logging
from PIL import Image, ImageDraw, ImageFont

def convert_to_bgr(image):
    """
    Convert an image to BGR format (used by OpenCV).
    
    Args:
        image: numpy array image in any format
        
    Returns:
        numpy array image in BGR format
    """
    try:
        # Grayscale to BGR
        if len(image.shape) == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        # RGBA to BGR
        elif image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        # RGB to BGR
        elif image.shape[2] == 3 and not is_bgr(image):
            return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        # Already BGR
        else:
            return image
    except Exception as e:
        logging.error(f"Error converting image to BGR: {e}")
        return image

def is_bgr(image):
    """
    Check if an image is already in BGR format (simple heuristic).
    This is a heuristic since numpy arrays don't store color format information.
    """
    # This is just a placeholder - in reality, you cannot reliably detect 
    # if an image is BGR or RGB from the array alone
    return True
        
def resize_image(image, width=None, height=None, scale=None):
    """
    Resize an image while maintaining aspect ratio.
    
    Args:
        image: numpy array image
        width: target width (optional)
        height: target height (optional)
        scale: scale factor (optional)
        
    Returns:
        resized numpy array image
    """
    try:
        if scale:
            return cv2.resize(
                image, 
                None, 
                fx=scale, 
                fy=scale, 
                interpolation=cv2.INTER_AREA
            )
        elif width and height:
            return cv2.resize(
                image, 
                (width, height), 
                interpolation=cv2.INTER_AREA
            )
        elif width:
            h, w = image.shape[:2]
            new_height = int(h * (width / w))
            return cv2.resize(
                image, 
                (width, new_height), 
                interpolation=cv2.INTER_AREA
            )
        elif height:
            h, w = image.shape[:2]
            new_width = int(w * (height / h))
            return cv2.resize(
                image, 
                (new_width, height), 
                interpolation=cv2.INTER_AREA
            )
        else:
            return image
    except Exception as e:
        logging.error(f"Error resizing image: {e}")
        return image
        
def enhance_contrast(image):
    """
    Enhance contrast in an image for better visibility.
    
    Args:
        image: numpy array image
        
    Returns:
        enhanced numpy array image
    """
    try:
        # Convert to grayscale if color image
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Convert back to color if original was color
        if len(image.shape) == 3:
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
            
        return enhanced
    except Exception as e:
        logging.error(f"Error enhancing contrast: {e}")
        return image

def denoise_image(image):
    """
    Apply denoising to an image.
    
    Args:
        image: numpy array image
        
    Returns:
        denoised numpy array image
    """
    try:
        # Convert to grayscale if color image
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            denoised = cv2.fastNlMeansDenoising(gray)
            # Convert back to color
            return cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR)
        else:
            return cv2.fastNlMeansDenoising(image)
    except Exception as e:
        logging.error(f"Error denoising image: {e}")
        return image

def draw_boxes(image, boxes, texts=None, color=(0, 255, 0), thickness=2):
    """
    Draw bounding boxes on an image.
    
    Args:
        image: numpy array image
        boxes: list of bounding boxes (each a list of points)
        texts: optional list of texts to draw (same length as boxes)
        color: box color (default: green)
        thickness: line thickness
        
    Returns:
        image with boxes drawn
    """
    try:
        result = image.copy()
        
        for i, box in enumerate(boxes):
            # Draw bounding box
            pts = np.array(box, np.int32)
            pts = pts.reshape((-1, 1, 2))
            cv2.polylines(result, [pts], True, color, thickness)
            
            # Draw text if provided
            if texts and i < len(texts):
                x, y = box[0]  # Use top-left corner for text
                
                # Use PIL for better text rendering with Unicode support
                pil_img = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
                draw = ImageDraw.Draw(pil_img)
                
                try:
                    # Try to use a font that supports Unicode
                    font = ImageFont.truetype("Arial Unicode.ttf", 20)
                except:
                    # Fallback to default font
                    font = ImageFont.load_default()
                    
                # Draw text with black outline for better visibility
                text = texts[i]
                draw.text((int(x), int(y-25)), text, font=font, fill=(0, 0, 0))
                draw.text((int(x), int(y-25)), text, font=font, fill=color[::-1])  # RGB for PIL
                
                # Convert back to OpenCV format
                result = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        
        return result
    except Exception as e:
        logging.error(f"Error drawing boxes: {e}")
        return image

def sharpen_image(image):
    """
    Sharpen an image using a sharpening kernel.
    
    Args:
        image: numpy array image
        
    Returns:
        sharpened numpy array image
    """
    try:
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        return cv2.filter2D(image, -1, kernel)
    except Exception as e:
        logging.error(f"Error sharpening image: {e}")
        return image

def qimage_to_numpy(qimage):
    """
    Convert a QImage to a numpy array.
    
    Args:
        qimage: QImage object
        
    Returns:
        numpy array image
    """
    try:
        width = qimage.width()
        height = qimage.height()
        
        # Get image data and convert to numpy array
        ptr = qimage.bits()
        ptr.setsize(qimage.byteCount())
        
        if qimage.format() == QImage.Format.Format_RGB32:
            arr = np.array(ptr).reshape(height, width, 4)
            return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
        elif qimage.format() == QImage.Format.Format_RGB888:
            arr = np.array(ptr).reshape(height, width, 3)
            return arr
        else:
            # Convert to RGB888 first
            converted = qimage.convertToFormat(QImage.Format.Format_RGB888)
            ptr = converted.bits()
            ptr.setsize(converted.byteCount())
            arr = np.array(ptr).reshape(height, width, 3)
            return arr
    except Exception as e:
        logging.error(f"Error converting QImage to numpy array: {e}")
        return None

def numpy_to_qimage(array):
    """
    Convert a numpy array to a QImage.
    
    Args:
        array: numpy array image (BGR format assumed)
        
    Returns:
        QImage object
    """
    try:
        from PyQt6.QtGui import QImage
        
        # Convert BGR to RGB for QImage
        if array.shape[2] == 3:  # Color image
            rgb = cv2.cvtColor(array, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            return QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        elif array.shape[2] == 4:  # Alpha channel image
            h, w, ch = array.shape
            bytes_per_line = ch * w
            return QImage(array.data, w, h, bytes_per_line, QImage.Format.Format_RGBA8888)
        elif len(array.shape) == 2:  # Grayscale image
            h, w = array.shape
            bytes_per_line = w
            return QImage(array.data, w, h, bytes_per_line, QImage.Format.Format_Grayscale8)
    except Exception as e:
        logging.error(f"Error converting numpy array to QImage: {e}")
        return None