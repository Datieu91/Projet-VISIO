def classify_image(features):
    """
    Simple conditional rule engine to simulate Machine Learning classification.
    Takes features dictionary, returns (prediction, confidence).
    """
    # Default
    prediction = "Vide"
    confidence = 50
    
    # Simple heuristics based on the Cahier des Charges requirements
    
    # Heuristic 1: Full bins tend to have higher contrast (messy garbage sticking out)
    contrast = features.get("contrast_level", 0)
    
    # Heuristic 2: Average color. 
    # Let's assume messy garbage often has varying colors, making the average grayish/darker compared to an empty bright green/blue bin.
    # We'll just convert hex to simple luminosity approximation
    hex_color = features.get("avg_color_hex", "#000000").lstrip('#')
    luminosity = 255
    if len(hex_color) == 6:
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        luminosity = (0.299*r + 0.587*g + 0.114*b)
        
    score = 0
    
    if contrast > 50:
        score += 40
    if luminosity < 100: # darker
        score += 30
    if features.get("file_size_kb", 0) > 200: # Busy images are harder to compress
        score += 20
        
    if score >= 60:
        prediction = "Pleine"
        confidence = min(score + 15, 99) # Add some bias to make it look like an AI score
    else:
        prediction = "Vide"
        confidence = min(100 - score + 10, 99)
        
    return prediction, int(confidence)
