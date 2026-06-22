import os
from PIL import Image, ImageStat
import cv2
import numpy as np

def extract_features(filepath):
    """
    Extracts features from an image using Pillow and OpenCV.
    Returns a dictionary of features.
    """
    features = {
        "file_size_kb": 0,
        "width": 0,
        "height": 0,
        "avg_color_hex": "#000000",
        "contrast_level": 0.0
    }
    
    if not os.path.exists(filepath):
        return features

    # 1. File Size
    features["file_size_kb"] = int(os.path.getsize(filepath) / 1024)
    
    # 2. Dimensions & Basic Color (Pillow)
    try:
        with Image.open(filepath) as img:
            features["width"], features["height"] = img.size
            
            # Average Color
            img_rgb = img.convert('RGB')
            stat = ImageStat.Stat(img_rgb)
            r, g, b = [int(v) for v in stat.mean]
            features["avg_color_hex"] = f"#{r:02x}{g:02x}{b:02x}"
            
    except Exception as e:
        print(f"Error extracting Pillow features: {e}")

    # 3. Advanced Features (OpenCV - Headless)
    try:
        # Read image using OpenCV
        cv_img = cv2.imread(filepath)
        if cv_img is not None:
            # Convert to grayscale for contrast
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            features["contrast_level"] = float(gray.std())
    except Exception as e:
        print(f"Error extracting OpenCV features: {e}")

    return features
