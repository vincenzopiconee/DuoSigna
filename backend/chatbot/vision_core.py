"""
Questo modulo gestisce il preprocessing matematico e l'inferenza del modello TensorFlow
per il riconoscimento dei segni. Adattato per ricevere dati direttamente dal Frontend Web.
"""

import os
import zipfile
import numpy as np
import tensorflow as tf
import json

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

# ==============================================================================
#  CONFIGURAZIONI E LANDMARK
# ==============================================================================
SEQUENCE_LENGTH = 384
ROWS_PER_FRAME = 543
NUM_NODES = 118

LIP = [
    0, 61, 185, 40, 39, 37, 267, 269, 270, 409,
    291, 146, 91, 181, 84, 17, 314, 405, 321, 375,
    78, 191, 80, 81, 82, 13, 312, 311, 310, 415,
    95, 88, 178, 87, 14, 317, 402, 318, 324, 308,
]
LHAND = list(range(468, 489))
RHAND = list(range(522, 543))
NOSE = [1, 2, 98, 327]
REYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 246, 161, 160, 159, 158, 157, 173]
LEYE = [263, 249, 390, 373, 374, 380, 381, 382, 362, 466, 388, 387, 386, 385, 384, 398]

POINT_LANDMARKS = LIP + LHAND + RHAND + NOSE + REYE + LEYE

# ==============================================================================
#  FUNZIONI DI CARICAMENTO
# ==============================================================================
def load_labels(json_path):
    if os.path.isfile(json_path):
        with open(json_path) as f:
            m = json.load(f)
        return [k for k, v in sorted(m.items(), key=lambda x: x[1])]
    return []

def load_savedmodel(zip_path, extract_dir):
    pb_path = None
    if os.path.isdir(extract_dir):
        for root, _, files in os.walk(extract_dir):
            if "saved_model.pb" in files:
                pb_path = root
                break

    if pb_path is None:
        print(f"[Model] Estrazione di {zip_path} in {extract_dir}...")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)
        for root, _, files in os.walk(extract_dir):
            if "saved_model.pb" in files:
                pb_path = root
                break

    print(f"[Model] Caricamento del modello neurale da: {pb_path}")
    model = tf.saved_model.load(pb_path)
    sig = model.signatures["serving_default"]
    in_key = list(sig.structured_input_signature[1].keys())[0]
    out_key = list(sig.structured_outputs.keys())[0]

    def infer(arr: np.ndarray) -> np.ndarray:
        tensor = tf.constant(arr[np.newaxis], dtype=tf.float32)
        return sig(**{in_key: tensor})[out_key].numpy()[0]

    return infer

# ==============================================================================
#  PREPROCESSING MATEMATICO
# ==============================================================================
def _nan_mean(x, axis, keepdims=True):
    with np.errstate(all='ignore'):
        return np.nanmean(x, axis=axis, keepdims=keepdims)

def _nan_std_centered(x, center, axis, keepdims=True):
    d = x - center
    with np.errstate(all='ignore'):
        var = np.nanmean(d * d, axis=axis, keepdims=keepdims)
    return np.sqrt(var)

def preprocess_sequence(frames: list) -> np.ndarray:
    """Trasforma la lista di frame inviata da Nuxt in un tensore pronto per TensorFlow"""
    # Ripeti i frame se sono meno di 384, oppure tronca
    while len(frames) < SEQUENCE_LENGTH:
        frames.extend(frames)
    frames = frames[:SEQUENCE_LENGTH]

    # --- AGGIUNGI QUESTE DUE RIGHE PER GESTIRE I NULL DI JAVASCRIPT ---
    # Convertiamo i null (None in Python) in np.nan come vuole il modello
    clean_frames = [[[np.nan, np.nan, np.nan] if pt == [None, None, None] else pt for pt in frame] for frame in frames]
    x = np.array(clean_frames, dtype=np.float32)[np.newaxis]
    # -----------------------------------------------------------------

    T = x.shape[1]

    lm17 = x[:, :, 17:18, :]
    mean = _nan_mean(lm17, axis=(1, 2), keepdims=True)
    mean = np.where(np.isnan(mean), np.float32(0.5), mean)

    x = x[:, :, POINT_LANDMARKS, :]

    std = _nan_std_centered(x, mean, axis=(1, 2), keepdims=True)
    std = np.where((std == 0) | np.isnan(std), np.float32(1.0), std)

    x = (x - mean) / std
    x = x[..., :2]

    dx = np.zeros_like(x)
    dx2 = np.zeros_like(x)
    if T > 1: dx[:, :-1] = x[:, 1:] - x[:, :-1]
    if T > 2: dx2[:, :-2] = x[:, 2:] - x[:, :-2]

    N = NUM_NODES * 2
    x_r, dx_r, dx2_r = x.reshape(1, T, N), dx.reshape(1, T, N), dx2.reshape(1, T, N)
    result = np.concatenate([x_r, dx_r, dx2_r], axis=-1)
    result = np.where(np.isnan(result), np.float32(0.0), result)

    return result[0].astype(np.float32)