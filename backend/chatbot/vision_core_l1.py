"""
Modulo per il preprocessing geometrico e l'inferenza del Livello 1 (Lettere).
Include il motore di feedback didattico.
"""

import os
import pickle
import numpy as np
from chatbot.feedback_engine import FeedbackEngine

# ==============================================================================
# CARICAMENTO RISORSE
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'sign_model.pkl')
SUMMARIES_PATH = os.path.join(BASE_DIR, 'summaries.csv')

l1_bundle = None
feedback_engine = None

if os.path.exists(MODEL_PATH):
    with open(MODEL_PATH, 'rb') as f:
        l1_bundle = pickle.load(f)

if os.path.exists(SUMMARIES_PATH):
    feedback_engine = FeedbackEngine(SUMMARIES_PATH)

FEATURE_NAMES = [
    "thumb_cmc_angle", "thumb_mcp_angle", "thumb_ip_angle",
    "index_pip_angle", "index_dip_angle",
    "middle_pip_angle", "middle_dip_angle",
    "ring_pip_angle", "ring_dip_angle",
    "pinky_pip_angle", "pinky_dip_angle",
    "thumb_index_tip_distance", "index_middle_tip_distance",
    "middle_ring_tip_distance", "ring_pinky_tip_distance",
    "thumb_middle_tip_distance", "thumb_ring_tip_distance",
    "thumb_pinky_tip_distance"
]


# ==============================================================================
# FUNZIONI MATEMATICHE
# ==============================================================================
def compute_angle(p1, p2, p3):
    v1 = p1 - p2
    v2 = p3 - p2
    dot = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 1.0
    cos_angle = dot / (norm1 * norm2)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    return float(np.arccos(cos_angle) / np.pi)

def process_l1_sequence(frames):
    sequence_features = []
    
    for frame in frames:
        if len(frame) < 543: continue
            
        hand_pts = frame[522:543] # Mano destra
        if any(pt == [None, None, None] or pt is None for pt in hand_pts):
            hand_pts = frame[468:489] # Fallback mano sinistra
            
        if any(pt == [None, None, None] or pt is None for pt in hand_pts):
            continue
            
        pts = np.array(hand_pts, dtype=np.float32)
        
        # Normalizzazione: Traslazione e Scala
        pts = pts - pts[0]
        dist_0_9 = np.linalg.norm(pts[9] - pts[0])
        if dist_0_9 > 0:
            pts = pts / dist_0_9
            
        # Rotazione 2D sul piano XY e azzeramento Z
        x9, y9 = pts[9][0], pts[9][1]
        angle = np.arctan2(x9, y9)
        c, s = np.cos(-angle), np.sin(-angle)
        
        rotated_pts = pts.copy()
        for i in range(21):
            x, y = pts[i][0], pts[i][1]
            rotated_pts[i][0] = x * c - y * s
            rotated_pts[i][1] = x * s + y * c
            rotated_pts[i][2] = 0.0 
            
        # Estrazione delle 18 feature
        feats = []
        feats.append(compute_angle(rotated_pts[0], rotated_pts[1], rotated_pts[2])) 
        feats.append(compute_angle(rotated_pts[1], rotated_pts[2], rotated_pts[3])) 
        feats.append(compute_angle(rotated_pts[2], rotated_pts[3], rotated_pts[4])) 
        feats.append(compute_angle(rotated_pts[5], rotated_pts[6], rotated_pts[7])) 
        feats.append(compute_angle(rotated_pts[6], rotated_pts[7], rotated_pts[8])) 
        feats.append(compute_angle(rotated_pts[9], rotated_pts[10], rotated_pts[11])) 
        feats.append(compute_angle(rotated_pts[10], rotated_pts[11], rotated_pts[12])) 
        feats.append(compute_angle(rotated_pts[13], rotated_pts[14], rotated_pts[15])) 
        feats.append(compute_angle(rotated_pts[14], rotated_pts[15], rotated_pts[16])) 
        feats.append(compute_angle(rotated_pts[17], rotated_pts[18], rotated_pts[19])) 
        feats.append(compute_angle(rotated_pts[18], rotated_pts[19], rotated_pts[20])) 
        
        feats.append(float(np.linalg.norm(rotated_pts[4] - rotated_pts[8])))   
        feats.append(float(np.linalg.norm(rotated_pts[8] - rotated_pts[12])))  
        feats.append(float(np.linalg.norm(rotated_pts[12] - rotated_pts[16]))) 
        feats.append(float(np.linalg.norm(rotated_pts[16] - rotated_pts[20]))) 
        feats.append(float(np.linalg.norm(rotated_pts[4] - rotated_pts[12])))  
        feats.append(float(np.linalg.norm(rotated_pts[4] - rotated_pts[16])))  
        feats.append(float(np.linalg.norm(rotated_pts[4] - rotated_pts[20])))  
        
        sequence_features.append(feats)
        
    if not sequence_features:
        return None
        
    # Mediana temporale per stabilizzare il segno
    return np.median(np.array(sequence_features), axis=0).tolist()

# ==============================================================================
# CORE INFERENZA
# ==============================================================================
def evaluate_letter(frames: list, target_word: str) -> dict:
    if l1_bundle is None:
        raise Exception("Modello sign_model.pkl non trovato.")
        
    features_median = process_l1_sequence(frames)
    if features_median is None:
        return {
            "predicted_word": "Hand not detected",
            "confidence": 0.0,
            "is_correct": False,
            "feedback": [{"severity": 1.0, "message": "Show your hand clearly to get feedback."}]
        }
        
    clf_model = l1_bundle["model"]
    prediction = clf_model.predict([features_median])[0]
    probabilities = clf_model.predict_proba([features_median])[0]
    
    classes = list(clf_model.classes_)
    predicted_word = str(prediction).lower()
    top_p = float(probabilities[classes.index(prediction)])
    
    # Soglia didattica al 65% per il Livello 1
    is_correct = (predicted_word == target_word.lower() and top_p >= 0.65)

    # Feedback sempre dato, confrontando le feature con i percentili
    # della lettera target (indipendentemente da cosa ha predetto il modello)
    feedback_list = []
    if feedback_engine:
        features_dict = dict(zip(FEATURE_NAMES, features_median))
        feedback_list = feedback_engine.get_feedback(features_dict, target_letter=target_word.lower())
        
    return {
        "predicted_word": predicted_word.upper(),
        "confidence": top_p,
        "is_correct": is_correct,
        "feedback": feedback_list
    }
