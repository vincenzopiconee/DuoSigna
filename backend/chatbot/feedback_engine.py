"""
feedback_engine.py
------------------
Modulo riutilizzabile per generare hint didattici dato un vettore di feature
e la lettera target.

Uso tipico:
    from feedback_engine import FeedbackEngine

    engine = FeedbackEngine("summaries.csv")
    hints = engine.get_feedback(features_dict, target_letter="a")
    for h in hints:
        print(h)
"""

import pandas as pd

# --------------------------------------------------
# Soglia minima di severity per mostrare un hint.
# Severity = (distanza dal range) / (q90 - q10)
# 0.15 significa che la feature deve essere fuori
# dal range di almeno il 15% dell'ampiezza del range
# stesso  -  filtra i casi "appena fuori" che sono rumore.
# --------------------------------------------------
MIN_SEVERITY = 0.15

# --------------------------------------------------
# Profilo delle lettere  -  per riferimento rapido
# (valori q50 da landmark_features_v5.csv)
#
# A  -  Pugno chiuso, pollice laterale all'indice
#     pip_angoli ? 0.17 - 0.28 (dita serrate)
#     thumb_index_tip_distance ? 0.69 (pollice a lato)
#     thumb_middle/ring/pinky distanze ? 0.85 - 1.23
#
# B  -  Mano piatta, dita distese, pollice ripiegato sul palmo
#     pip_angoli ? 0.96 - 0.97 (dita completamente distese)
#     thumb_mcp_angle ? 0.68 (pollice piegato)
#     thumb_pinky_tip_distance ? 0.74 (pollice vicino al mignolo)
#
# C  -  Mano a C, dita incurvate
#     pip_angoli ? 0.74 - 0.82 (curvatura media)
#     thumb_cmc_angle ? 0.86 (pollice aperto)
#     distanze pollice-dita ? 0.62 - 0.66 (spazio a C)
#
# D  -  Indice dritto verso l'alto, altre dita piegate,
#     pollice a contatto con medio/anulare
#     index_pip_angle ? 0.95 (indice esteso)
#     middle/ring_pip ? 0.57 - 0.61 (piegate)
#     index_middle_tip_distance ? 1.38 (indice separato)
#     thumb_middle/ring_tip_distance ? 0.30 - 0.38 (pollice tocca)
#
# E  -  Dita piegate a uncino, pollice stretto sotto le punte
#     pip_angoli ? 0.15 - 0.31 (simile ad A ma pollice pi? basso)
#     thumb_mcp_angle ? 0.63 (pollice ripiegato)
#     thumb_index_tip_distance ? 0.50 (pollice sotto l'indice)
#     thumb_middle/ring/pinky distanze ? 0.25 - 0.33
# --------------------------------------------------

# --------------------------------------------------
# Hint lettera-specifici.
#
# Struttura: LETTER_FEATURE_HINTS[lettera][feature] = (msg_low, msg_high)
#
# msg_low  ? valore < q10 (feature troppo bassa rispetto alla lettera target)
# msg_high ? valore > q90 (feature troppo alta rispetto alla lettera target)
#
# Ogni messaggio spiega *cosa correggere* nel contesto della lettera specifica,
# non solo in modo generico.
# --------------------------------------------------
LETTER_FEATURE_HINTS = {

    # ------------------------------------------------------------------ A
    # Pugno chiuso, pollice disteso lateralmente all'indice
    # ------------------------------------------------------------------ A
    "a": {
        "index_pip_angle":  (None, "For A the fingers must be curled into a fist - your index finger is too straight"),
        "index_dip_angle":  (None, None),   # punta piegata = corretta per A, non segnalare
        "middle_pip_angle": (None, "For A the fingers must be curled into a fist - your middle finger is too straight"),
        "middle_dip_angle": (None, None),
        "ring_pip_angle":   (None, "For A the fingers must be curled into a fist - your ring finger is too straight"),
        "ring_dip_angle":   (None, None),
        "pinky_pip_angle":  (None, "For A the fingers must be curled into a fist - your pinky finger is too straight"),
        "pinky_dip_angle":  (None, None),
        "thumb_cmc_angle":  (
            "Open the base of your thumb slightly outward - for A the thumb rests laterally, not pressed flat against the palm",
            "The base of your thumb is too open - fold it back in toward the fist, not out to the side",
        ),
        "thumb_mcp_angle":  (
            "Extend your thumb slightly - for A it rests laterally beside the fist, not bent forward",
            None,
        ),
        "thumb_index_tip_distance": (
            "Your thumb is too close to the index finger - for A it sits laterally beside the fist, not on top of it",
            "Your thumb is too far from the index finger - bring it laterally alongside the fist",
        ),
        "thumb_middle_tip_distance":  (None, None),
        "thumb_ring_tip_distance":    (None, None),
        "thumb_pinky_tip_distance":   (None, None),
        "index_middle_tip_distance":  (None, None),
        "middle_ring_tip_distance":   (None, None),
        "ring_pinky_tip_distance":    (None, None),
    },

    # ------------------------------------------------------------------ B
    # Mano piatta, tutte le dita distese e unite, pollice ripiegato sul palmo
    # ------------------------------------------------------------------ B
    "b": {
        "index_pip_angle":  (
            "For B the index finger must be completely straight - you are holding it too bent",
            None,
        ),
        "index_dip_angle":  (
            "Straighten the tip of your index finger - it must be fully extended for B",
            None,
        ),
        "middle_pip_angle": (
            "For B the middle finger must be completely straight - you are holding it too bent",
            None,
        ),
        "middle_dip_angle": (
            "Straighten the tip of your middle finger - it must be fully extended for B",
            None,
        ),
        "ring_pip_angle":   (
            "For B the ring finger must be completely straight - you are holding it too bent",
            None,
        ),
        "ring_dip_angle":   (
            "Straighten the tip of your ring finger for B",
            None,
        ),
        # pinky_pip_angle altissimo (>q90): mignolo iperesteso e fisiologico per la B
        "pinky_pip_angle":  (
            "For B the pinky must also be completely straight - you are holding it too bent",
            None,   # troppo disteso = ok per la B, non segnalare
        ),
        "pinky_dip_angle":  (
            "Straighten the tip of your pinky for B",
            None,
        ),
        "thumb_mcp_angle":  (
            None,
            "For B the thumb is folded onto the palm - bend it downward, do not keep it extended",
        ),
        "thumb_ip_angle":   (
            None,
            "Fold your thumb onto the palm - for B it is not extended outward",
        ),
        "ring_pinky_tip_distance": (
            None,   # dita molto vicine: normale per la B, non segnalare (coerente con le altre coppie)
            "Your fingers are too spread apart - for B they are held close together",
        ),
        "thumb_pinky_tip_distance": (
            None,
            "Your thumb is too far from the pinky - fold it onto the palm toward the inner edge of the hand",
        ),
        # Distanze tra punte adiacenti: nella B le dita sono unite, quindi
        # un valore troppo basso (dita vicinissime) non e un errore rilevante.
        # Un valore troppo alto invece s?  -  le dita si stanno allargando.
        "index_middle_tip_distance": (
            None,   # dita molto vicine: normale per la B, non segnalare
            "Keep your index and middle finger together - for B the fingers are held close",
        ),
        "middle_ring_tip_distance": (
            None,   # dita molto vicine: normale per la B, non segnalare
            "Keep your middle and ring finger together - for B the fingers are held close",
        ),
        # Distanze pollice-dita non rilevanti per la B
        "thumb_cmc_angle":           (None, None),
        "thumb_index_tip_distance":  (None, None),
        "thumb_middle_tip_distance": (None, None),
        "thumb_ring_tip_distance":   (None, None),
    },

    # ------------------------------------------------------------------ C
    # Mano a forma di C: dita incurvate allo stesso modo, pollice aperto di fronte
    # ------------------------------------------------------------------ C
    "c": {
        "index_pip_angle":  (
            "For C the index finger must be curved, not fully closed - open it slightly",
            "Your index finger is too straight - curve it to form the C shape",
        ),
        "index_dip_angle":  (
            "Open the tip of your index finger slightly - for C it is not fully curled",
            "Curve the tip of your index finger slightly toward the thumb",
        ),
        "middle_pip_angle": (
            "For C the middle finger must be curved, not fully closed - open it slightly",
            "Your middle finger is too straight - curve it like the other fingers to form the C",
        ),
        "middle_dip_angle": (
            "Open the tip of your middle finger slightly - for C it is not fully closed",
            "Curve the tip of your middle finger slightly",
        ),
        "ring_pip_angle":   (
            "For C the ring finger must be curved - open it slightly from the fist",
            "Your ring finger is too straight - curve it like the other fingers for C",
        ),
        "pinky_pip_angle":  (
            "For C the pinky must also be curved - open it slightly",
            "Your pinky is too straight - curve it to complete the C shape",
        ),
        "thumb_cmc_angle":  (
            "Open the base of your thumb outward - for C the thumb is well open, facing the fingers",
            None,
        ),
        "thumb_mcp_angle":  (
            None,
            None,
        ),
        "thumb_index_tip_distance": (
            "Your thumb is too close to the index finger - for C there is an open gap between thumb and fingers",
            "Your thumb is too far from the index finger - bring it closer to close the C shape",
        ),
        "thumb_middle_tip_distance": (
            "Your thumb is too close to the middle finger - move it away to maintain the C shape",
            "Your thumb is too far from the middle finger - bring it closer toward the fingers",
        ),
        "thumb_ring_tip_distance": (
            "Your thumb is too close to the ring finger - keep the C shape open",
            "Your thumb is too far from the ring finger - bring it closer toward the fingers",
        ),
        "index_middle_tip_distance": (
            None,
            "Keep your index and middle finger close - for C the fingers are not spread apart",
        ),
        # Nella C le dita sono incurvate e vicine tra loro:
        # distanze basse tra dita adiacenti sono CORRETTE, non vanno segnalate
        "middle_ring_tip_distance": (
            None,
            "Keep your middle and ring finger close - for C the fingers are not spread apart",
        ),
        "ring_pinky_tip_distance": (
            None,
            "Keep your ring finger and pinky close - for C the fingers are not spread apart",
        ),
        # dip angles: stessa biomeccanica per tutte le dita nella C, quindi
        # gestiti in modo simmetrico (sia LOW che HIGH) come index/middle_dip_angle
        "ring_dip_angle": (
            "Open the tip of your ring finger slightly - for C it is not fully closed",
            "Curve the tip of your ring finger slightly toward the thumb",
        ),
        "pinky_dip_angle": (
            "Open the tip of your pinky slightly - for C it is not fully closed",
            "Curve the tip of your pinky slightly toward the thumb",
        ),
        "thumb_ip_angle":        (None, None),  # non rilevante per la C
        "thumb_pinky_tip_distance": (None, None),  # non rilevante per la C
    },

    # ------------------------------------------------------------------ D
    # Indice dritto verso l'alto, medio/anulare/mignolo piegati,
    # pollice che tocca le punte di medio e anulare
    # ------------------------------------------------------------------ D
    "d": {
        "index_pip_angle":  (
            "For D the index finger must point fully upward - you are holding it too bent",
            None,
        ),
        "index_dip_angle":  (
            "Fully straighten the tip of your index finger too - it must be straight for D",
            None,
        ),
        "middle_pip_angle": (
            None,
            "For D the middle finger must be curled toward the palm - it is too straight",
        ),
        "middle_dip_angle": (
            None,
            "Curl the tip of your middle finger - for D the curled fingers are not straight",
        ),
        "ring_pip_angle":   (
            None,
            "For D the ring finger must be curled toward the palm - it is too straight",
        ),
        "ring_dip_angle":   (
            None,
            "Curl the tip of your ring finger - for D the curled fingers are not straight",
        ),
        "pinky_pip_angle":  (
            None,
            "For D the pinky must also be curled - it is too straight",
        ),
        "pinky_dip_angle":  (
            None,
            "Curl the tip of your pinky - for D the curled fingers are not straight",
        ),
        "thumb_index_tip_distance": (
            "Your thumb is too close to the index finger - for D the thumb touches the middle and ring fingers, not the index",
            None,
        ),
        "index_middle_tip_distance": (
            "The index finger must be separated and pointing straight up - you are holding it too close to the middle finger",
            None,
        ),
        "thumb_middle_tip_distance": (
            None,
            "Bring your thumb to the tip of the middle finger - for D the thumb touches it forming a circle",
        ),
        "thumb_ring_tip_distance": (
            None,
            "Bring your thumb to the ring finger - for D the thumb also touches the ring finger",
        ),
        "thumb_pinky_tip_distance": (
            None,
            None,
        ),
        "thumb_cmc_angle":  (None, None),
        # Nella D medio/anulare/mignolo sono piegate insieme:
        # distanze basse tra queste dita sono CORRETTE
        "middle_ring_tip_distance": (
            None,
            "Keep your middle and ring finger close - for D they are curled together",
        ),
        "ring_pinky_tip_distance": (
            None,
            "Keep your ring finger and pinky close - for D they are curled together",
        ),
        # pollice quasi completamente disteso nella D: HIGH non e un errore
        "thumb_mcp_angle": (
            "Extend your thumb - for D it is almost fully extended",
            None,
        ),
        "thumb_ip_angle": (
            "Extend the tip of your thumb - for D it is almost fully extended",
            None,
        ),
    },

    # ------------------------------------------------------------------ E
    # Tutte le dita piegate a uncino verso il palmo,
    # pollice ripiegato stretto sotto le punte delle dita
    # ------------------------------------------------------------------ E
    
    "e": {
        # pip angles: dita piegate = corretto; troppo dritte = errore
        "index_pip_angle":  (None, "For E all fingers must be bent toward the palm - your index finger is too straight"),
        "middle_pip_angle": (None, "For E the middle finger must be bent toward the palm - it is too straight"),
        "ring_pip_angle":   (None, "For E the ring finger must be bent toward the palm - it is too straight"),
        "pinky_pip_angle":  (None, "For E the pinky must be bent - it is too straight"),
        # dip angles: per natura biomeccanica il dip resta quasi dritto anche
        # quando il pip e chiuso - non segnalare in nessuna direzione
        "index_dip_angle":  (None, None),
        "middle_dip_angle": (None, None),
        "ring_dip_angle":   (None, None),
        "pinky_dip_angle":  (None, None),
        # pollice
        "thumb_cmc_angle":           (None, None),
        "thumb_mcp_angle":           (None, "For E the thumb must be tucked tightly under the fingertips - bend it toward the palm"),
        "thumb_ip_angle":            (None, "Bend the tip of your thumb downward - for E it is hidden under the fingers"),
        # distanze pollice-dita: troppo lontano = errore
        "thumb_index_tip_distance":  (None, "Your thumb is too far from the index finger - for E it is tucked under the fingertips"),
        "thumb_middle_tip_distance": (None, "Your thumb is too far from the middle finger - tuck it under the fingertips for E"),
        "thumb_ring_tip_distance":   (None, "Your thumb is too far from the ring finger - for E it is tucked under all the fingertips"),
        "thumb_pinky_tip_distance":  (None, "Your thumb is too far from the pinky - for E it is brought under all the fingers"),
        # distanze tra dita adiacenti: troppo separate = errore
        "index_middle_tip_distance": (None, "Keep your index and middle finger close - for E the fingers are held together"),
        "middle_ring_tip_distance":  (None, "Keep your middle and ring finger close - for E the fingers are held together"),
        "ring_pinky_tip_distance":   (None, "Keep your ring finger and pinky close - for E the fingers are held together"),
    },
}




def _get_hint_message(letter: str, feature: str, direction: str):
    """
    Cerca prima un hint lettera-specifico.

    Logica:
      - feature PRESENTE in LETTER_FEATURE_HINTS[letter]:
          specific[idx] is a string - returns that string
          specific[idx] is None       - returns None (hint suppressed,
                                        NON cade sul generico)
      - feature ASSENTE dal dizionario lettera-specifico:
          usa il messaggio generico da FEATURE_HINTS_GENERIC

    direction: "low" | "high"
    """
    idx = 0 if direction == "low" else 1

    letter_hints = LETTER_FEATURE_HINTS.get(letter, {})
    if feature in letter_hints:
        # Feature esplicitamente definita per questa lettera:
        # None significa "sopprimi", non "usa il generico"
        return letter_hints[feature][idx]

    # Feature non definita per questa lettera: warning
    raise KeyError(
        f"Feature '{feature}' non definita per la lettera '{letter}'"
    )


class FeedbackEngine:

    def __init__(self, summaries_path: str):
        self._db = self._load(summaries_path)

    def _load(self, path: str) -> dict:
        df = pd.read_csv(path)
        db = {}
        for _, row in df.iterrows():
            label   = row["label"]
            feature = row["feature"]
            if label not in db:
                db[label] = {}
            db[label][feature] = {
                "mean": row["mean"],
                "std":  row["std"],
                "q10":  row["q10"],
                "q25":  row["q25"],
                "q50":  row["q50"],
                "q75":  row["q75"],
                "q90":  row["q90"],
            }
        return db

    def get_feedback(
        self,
        features: dict,
        target_letter: str,
        max_hints: int = 5,
        min_severity: float = MIN_SEVERITY,
    ) -> list[dict]:
        """
        Confronta le feature della mano con i percentili della lettera target.
        Restituisce hint ordinati per gravita, ignorando quelli appena fuori range.

        Parameters
        ----------
        features      : { nome_feature: valore_float }
        target_letter : es. "a"
        max_hints     : massimo hint restituiti
        min_severity  : soglia minima  -  hint con severity < min_severity ignorati.
                        Severity = (distanza dal range) / (q90 - q10).
                        Default 0.15: la feature deve essere fuori di almeno
                        il 15% dell'ampiezza del range per generare un hint.
        """
        letter = target_letter.lower()
        if letter not in self._db:
            return [{"message": f"Lettera '{target_letter}' non presente nelle summaries."}]

        stats = self._db[letter]
        hints = []

        for feat, value in features.items():
            if feat not in stats:
                continue

            q10 = stats[feat]["q10"]
            q90 = stats[feat]["q90"]
            iqr = q90 - q10 if q90 > q10 else 1e-8

            if value < q10:
                severity  = (q10 - value) / iqr
                direction = "low"
            elif value > q90:
                severity  = (value - q90) / iqr
                direction = "high"
            else:
                continue

            if severity < min_severity:
                continue

            message = _get_hint_message(letter, feat, direction)
            if message is None:
                # Nessun hint rilevante per questa combinazione lettera/feature/direzione
                continue

            hints.append({
                "feature":   feat,
                "value":     round(value, 4),
                "q10":       round(q10, 4),
                "q90":       round(q90, 4),
                "direction": direction,
                "severity":  round(severity, 4),
                "message":   message,
            })

        hints.sort(key=lambda h: h["severity"], reverse=True)
        return hints[:max_hints]

    def available_letters(self) -> list[str]:
        return sorted(self._db.keys())

    def available_features(self, letter: str) -> list[str]:
        return sorted(self._db.get(letter.lower(), {}).keys())


if __name__ == "__main__":
    import os
    BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
    SUMMARIES_PATH = os.path.join(BASE_DIR, "summaries.csv")

    engine = FeedbackEngine(SUMMARIES_PATH)
    print("Lettere disponibili:", engine.available_letters())

    # Test: qualcuno che prova a fare la B ma con dita piegate e pollice disteso
    test_b = {
        "index_pip_angle":   0.40,   # troppo basso ? "stendi l'indice per la B"
        "middle_pip_angle":  0.85,   # ok
        "ring_pip_angle":    0.35,   # troppo basso
        "pinky_pip_angle":   0.90,   # ok
        "thumb_mcp_angle":   0.95,   # troppo alto ? "ripiega il pollice per la B"
        "thumb_pinky_tip_distance": 1.50,  # troppo alto
        "index_middle_tip_distance": 0.23, # ok
    }
    print("\nFeedback test for letter B (bent fingers, extended thumb):")
    for i, h in enumerate(engine.get_feedback(test_b, "b"), 1):
        print(f"  {i}. [{h['severity']:.2f}] {h['message']}")

    # Test: qualcuno che prova a fare la D ma con indice piegato e pollice lontano
    test_d = {
        "index_pip_angle":           0.30,  # troppo basso ? "distendi l'indice per la D"
        "middle_pip_angle":          0.55,  # ok
        "ring_pip_angle":            0.52,  # ok
        "index_middle_tip_distance": 0.25,  # troppo basso ? "separa l'indice"
        "thumb_middle_tip_distance": 1.20,  # troppo alto ? "avvicina pollice al medio"
        "thumb_ring_tip_distance":   1.10,  # troppo alto ? "avvicina pollice all'anulare"
    }
    print("\nFeedback test for letter D (bent index, thumb too far):")
    for i, h in enumerate(engine.get_feedback(test_d, "d"), 1):
        print(f"  {i}. [{h['severity']:.2f}] {h['message']}")

    # Test: qualcuno che prova a fare la E ma con le dita distese
    test_e = {
        "index_pip_angle":           0.80,  # troppo alto ? "piega l'indice per la E"
        "middle_pip_angle":          0.75,  # troppo alto
        "ring_pip_angle":            0.70,  # troppo alto
        "pinky_pip_angle":           0.60,  # troppo alto
        "thumb_index_tip_distance":  1.20,  # troppo alto ? "avvicina il pollice sotto"
        "thumb_middle_tip_distance": 0.90,  # troppo alto
    }
    print("\nFeedback test for letter E (fingers too straight):")
    for i, h in enumerate(engine.get_feedback(test_e, "e"), 1):
        print(f"  {i}. [{h['severity']:.2f}] {h['message']}")
