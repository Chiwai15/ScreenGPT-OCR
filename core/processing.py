from PyQt6.QtCore import QThread, pyqtSignal
from transformers import AutoProcessor, AutoModelForVision2Seq
from PIL import Image, ImageDraw, ImageFont
import torch
import cv2
import numpy as np
import easyocr
import openai
import logging
import os
from utils.ocr import preprocess_image_for_ocr

# Configure logging
logger = logging.getLogger(__name__)


class ProcessingThread(QThread):
    """Thread for processing screenshots"""

    finished = pyqtSignal(object)  # Signal to emit when processing is done
    progress = pyqtSignal(str)  # Signal to emit progress updates
    error = pyqtSignal(str)  # Signal to emit errors
    tab_update = pyqtSignal(int, object, str)  # Signal to update tab content

    def __init__(self, parent=None):
        super().__init__(parent)
        self.img = None
        self.model = None
        self.processor = None
        self.reader = None
        self.selected_languages = []  # Will be populated by language checkboxes

    def set_image(self, img):
        self.img = img

    def init_models(self):
        try:
            # Initialize BLIP image captioning model
            model_name = "Salesforce/blip-image-captioning-large"
            self.processor = AutoProcessor.from_pretrained(model_name, use_fast=True)
            self.model = AutoModelForVision2Seq.from_pretrained(
                model_name,
                torch_dtype=torch.float16,
                device_map="auto",
                low_cpu_mem_usage=True,
            )
            self.model.eval()

            # Initialize EasyOCR with default languages (English and Chinese Traditional)
            self.reader = easyocr.Reader(["en", "ch_tra"], gpu=True)
            logger.info(
                "EasyOCR initialized with default languages (English and Chinese Traditional)"
            )
        except Exception as e:
            self.error.emit(f"Error initializing models: {str(e)}")
            raise

    def run(self):
        try:
            if self.img is None:
                self.error.emit("No image to process")
                return

            # Step 1: Run OCR analysis
            self.progress.emit("\n🔍 Running OCR analysis...")
            ocr_text, drawn_img, text_positions = self.extract_text_from_image(self.img)
            self.tab_update.emit(
                0,  # Update processing tab
                drawn_img,
                "✅ OCR Analysis Complete\n\n📝 Extracted Text:\n" + ocr_text,
            )

            # Step 2: Run Vision analysis
            if self.model is None or self.processor is None:
                self.error.emit("❌ Error: Vision model not initialized")
                return

            self.progress.emit("\n👁️ Running Visual Analysis...")
            img_rgb = cv2.cvtColor(drawn_img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)

            with torch.no_grad():
                inputs = self.processor(images=pil_img, return_tensors="pt").to(
                    self.model.device
                )
                generated_ids = self.model.generate(
                    pixel_values=inputs.pixel_values,
                    max_length=100,
                    num_beams=3,
                    length_penalty=1.0,
                    temperature=0.7,
                    do_sample=True,
                )
                vision_text = self.processor.batch_decode(
                    generated_ids, skip_special_tokens=True
                )[0]

            self.tab_update.emit(
                0,  # Update processing tab
                drawn_img,
                "✅ Visual Analysis Complete\n\n🎯 Visual Description:\n" + vision_text,
            )

            # Step 3: Run LLM analysis
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                self.error.emit("❌ Error: OPENAI_API_KEY not set in environment.")
                return

            self.progress.emit("\n🤖 Running AI Analysis...")

            # Format text positions for the prompt
            text_positions_str = "\n".join(
                [
                    f"Text: '{pos['text']}' at position (x: {int(pos['x'])}, y: {int(pos['y'])})"
                    for pos in text_positions
                ]
            )

            # Final analysis with GPT-4
            prompt = f"""You are looking at a screenshot that contains both text and visual elements. Your task is to describe what you see by combining the visible text and visuals to provide an accurate explanation.

Text Content with Positions:
{text_positions_str}
Please group text that appears close together and likely relates to the same topic.

Visual Description:
{vision_text}

Instructions:
1. ONLY describe what is clearly visible in the data provided.
2. Focus on identifying the type of interface or application shown.
3. Group and organize the text based on where it appears (top to bottom, left to right).
4. Use the positions of the text to understand how elements relate to each other.
5. Pull out and structure the most important information in a logical order.
6. If there are different sections or paragraphs, present them clearly and separately.
7. Do NOT guess or add information not supported by what you see.
8. If anything is unclear, feel free to acknowledge the uncertainty.
9. there might be typo or partial character misread by ocr, you should either correct them or ignore them.
Your final response should:
1. Identify the type of interface or application shown.
2. Group related text based on their placement.
3. Present all important content in a well-organized way.
4. Highlight the key details and messages.
5. Keep the original meaning and context intact.

Please make your answer sound like a natural conversation, suitable for anyone aged 10 to 60. Talk as if you're describing the screenshot to a friend—clearly, thoroughly, and without mentioning any technical terms like OCR or analysis. Make it as detailed as possible, but only include what's relevant to the screenshot.
"""


            # Update prompts tab
            prompts_text = f"""🔍 OCR Analysis Results:
{text_positions_str}

👁️ Visual Analysis Results:
{vision_text}

🤖 GPT-4 Analysis Prompt:
{prompt}"""

            self.tab_update.emit(
                1,  # Update prompts tab
                drawn_img,
                "✅ Analysis Prompts\n\n" + prompts_text,
            )

            try:
                client = openai.OpenAI(api_key=openai_api_key)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful assistant that analyzes screenshots.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=300,
                    temperature=0.7,
                )
                final_analysis = response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
                final_analysis = f"Error: {e}"

            self.tab_update.emit(
                2,  # Update final analysis tab
                drawn_img,
                "✅ AI Analysis Complete\n\n📊 Final Analysis:\n" + final_analysis,
            )

            self.progress.emit(
                "\n✨ Check the tabs above for detailed processing steps."
            )

            # Emit the final result
            self.finished.emit(final_analysis)

        except Exception as e:
            self.error.emit(f"Error in processing thread: {str(e)}")

    def extract_text_from_image(self, img):
        """Extract text from image using EasyOCR and draw bounding boxes"""
        try:
            # Create a copy of the image for drawing
            drawn_img = img.copy()

            # Preprocess image for better OCR
            processed_img = preprocess_image_for_ocr(img)

            # Perform OCR on the processed image
            results = self.reader.readtext(processed_img, contrast_ths=0.5, adjust_contrast=0.7)

            # Extract text and draw bounding boxes
            extracted_text = []
            text_positions = []  # Store text with their positions

            for bbox, text, prob in results:
                if prob > 0.5:  # Confidence threshold
                    # Draw bounding box
                    pts = np.array(bbox, np.int32)
                    pts = pts.reshape((-1, 1, 2))
                    cv2.polylines(drawn_img, [pts], True, (0, 255, 0), 2)

                    # Calculate center position of the text
                    x_center = sum(point[0] for point in bbox) / 4
                    y_center = sum(point[1] for point in bbox) / 4

                    # Store text with its position
                    text_positions.append(
                        {"text": text, "x": x_center, "y": y_center, "confidence": prob}
                    )

                    # Add text with proper font support for Chinese
                    x, y = bbox[0]
                    # Convert text to UTF-8 for proper display
                    text_utf8 = text.encode("utf-8").decode("utf-8")

                    # Use PIL to draw text with proper font support
                    pil_img = Image.fromarray(
                        cv2.cvtColor(drawn_img, cv2.COLOR_BGR2RGB)
                    )
                    draw = ImageDraw.Draw(pil_img)
                    try:
                        # Try to use a font that supports Chinese
                        font = ImageFont.truetype("Arial Unicode.ttf", 20)
                    except:
                        # Fallback to default font
                        font = ImageFont.load_default()

                    # Draw text with black outline for better visibility
                    draw.text(
                        (int(x), int(y - 25)), text_utf8, font=font, fill=(0, 0, 0)
                    )
                    draw.text(
                        (int(x), int(y - 25)), text_utf8, font=font, fill=(0, 255, 0)
                    )

                    # Convert back to OpenCV format
                    drawn_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

                    extracted_text.append(text)

            # Sort text positions by y-coordinate (top to bottom) and then x-coordinate (left to right)
            text_positions.sort(key=lambda x: (x["y"], x["x"]))

            # Join all text with spaces
            full_text = " ".join(extracted_text)
            logger.debug(f"Extracted text: {full_text}")
            return full_text, drawn_img, text_positions
        except Exception as e:
            logger.error(f"Error in OCR: {e}")
            return "", img, []

    def update_selected_languages(self):
        """Update the selected languages in the processing thread"""
        try:
            selected_languages = []
            for lang_name, checkbox in self.lang_checkboxes.items():
                if checkbox.isChecked():
                    selected_languages.append(AVAILABLE_LANGUAGES[lang_name])

            if not selected_languages:
                # If no languages selected, default to English
                selected_languages = ["en"]

            # Update the reader with new languages
            self.reader = easyocr.Reader(selected_languages, gpu=True)
            logger.info(f"EasyOCR initialized with languages: {selected_languages}")
        except Exception as e:
            logger.error(f"Error updating languages: {e}")
            # Fallback to default languages
            self.reader = easyocr.Reader(["en", "ch_tra"], gpu=True)
