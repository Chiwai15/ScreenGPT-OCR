# ScreenGPT

> Universal Screenshot Analysis with Advanced Computer Vision and AI

ScreenGPT is a powerful desktop application that combines OCR (Optical Character Recognition), computer vision, and AI to analyze screenshots and provide detailed information about their content. With just a shortcut key, you can capture and analyze any screen content, making it a versatile accessibility and productivity tool.

![ScreenGPT Interface](https://github.com/Chiwai15/ScreenGPT-OCR/assets/screen-gpt-home.jpg)

## Features

- **Advanced Multi-Language OCR**: Powered by EasyOCR with support for English, Chinese (Traditional), Japanese, Korean, French, German and more
- **Visual Analysis**: Uses Salesforce BLIP image captioning model to understand visual content beyond text
- **AI-Powered Analysis**: Combines OCR and visual data using GPT-4o for comprehensive understanding of screenshots
- **Text-to-Speech**: Built-in TTS capabilities to read analysis results aloud
- **Universal Capture**: Capture any screen area with simple keyboard shortcuts
- **Interactive UI**: Zoom, pan, and explore analyzed content with an intuitive interface
- **Multi-language Support**: Process content in multiple languages simultaneously

## Technology Stack

ScreenGPT integrates several cutting-edge technologies:

- **PyQt6**: Modern Qt-based UI framework for Python
- **EasyOCR**: Multi-language Optical Character Recognition engine
- **Salesforce BLIP**: State-of-the-art image captioning model for visual analysis
- **Transformers**: Hugging Face's Transformers library for deep learning models
- **OpenAI GPT-4o**: Advanced large language model for final analysis and synthesis
- **OpenCV**: Computer vision library for image preprocessing and visualization
- **pyttsx3**: Text-to-speech engine for audio output
- **MSS**: Fast cross-platform screenshot utility

## Installation

### Prerequisites

- Python 3.8+
- PyQt6
- CUDA-capable GPU (recommended for optimal performance)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/chiwai15/ScreenGPT-OCR.git
   cd screen-gpt
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env.example` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

4. Run the application:
   ```bash
   python screen_gpt.py
   ```

## Usage

### Keyboard Shortcuts

- **Ctrl+Alt+A**: Start screenshot analysis
- **Ctrl+Shift+A**: Alternative shortcut for screenshot analysis
- **Alt+A**: Another alternative shortcut

### Workflow

1. Press any of the shortcut keys or click "Select Area" to start the screenshot tool
2. Drag to select the area you want to analyze
3. Wait for the analysis to complete
4. View results in the different tabs:
   - Processing tab shows OCR extraction and raw visual analysis
   - Analysis Prompts tab shows the data sent to GPT-4o
   - Final Analysis tab shows the complete AI interpretation
5. Use the "Read Analysis" button to have the results read aloud

### Language Selection

Select your desired OCR languages from the checkboxes. Note that:
- English can be combined with one other language
- Some language combinations have restrictions due to script incompatibility

## Technical Details

### OCR Processing

ScreenGPT uses EasyOCR with custom preprocessing to enhance text recognition:
- Adaptive thresholding
- Denoising
- Sharpening
- Contrast enhancement

### Visual Analysis Pipeline

1. **Capture**: High-resolution screenshot capture with MSS
2. **OCR Analysis**: Text extraction with spatial position data
3. **Visual Analysis**: Image captioning using Salesforce's BLIP model
4. **AI Synthesis**: Combined analysis using GPT-4o with structured prompts
5. **Result Presentation**: Multi-tabbed interface showing all processing stages

### Model Architecture

- **OCR**: EasyOCR with language-specific recognition models
- **Vision**: Salesforce/blip-image-captioning-large model
- **Language Processing**: OpenAI GPT-4o with specialized prompting

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [EasyOCR](https://github.com/JaidedAI/EasyOCR)
- [Salesforce BLIP](https://github.com/salesforce/BLIP)
- [Hugging Face Transformers](https://github.com/huggingface/transformers)
- [OpenAI](https://openai.com/)
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/)
