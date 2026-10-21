import random
from sqlalchemy.orm import Session
import models

CATEGORY_DEFINITIONS = [
    {
        "id": "animals",
        "title": "Animals",
        "keys": ["alligator", "animal", "bee", "bird", "bug", "cat", "cow", "dog", "donkey", "duck", "elephant", "fish", "frog", "giraffe", "goose", "hen", "horse", "kitty", "lion", "mouse", "owl", "pig", "puppy", "tiger", "wolf", "zebra"],
    },
    {
        "id": "actions",
        "title": "Actions & Verbs",
        "keys": ["blow", "can", "clean", "close", "cry", "cut", "dance", "drink", "drop", "dry", "fall", "find", "finish", "give", "go", "hate", "have", "haveto", "hear", "hide", "jump", "kiss", "like", "listen", "look", "make", "nap", "open", "pretend", "read", "ride", "say", "see", "shhh", "sleep", "smile", "stay", "talk", "taste", "think", "touch", "wait", "wake"],
    },
    {
        "id": "food",
        "title": "Food & Drinks",
        "keys": ["apple", "carrot", "cereal", "chocolate", "food", "french-fries", "gum", "icecream", "milk", "nuts", "orange", "pizza", "snack", "water"],
    },
    {
        "id": "home",
        "title": "Home & Rooms",
        "keys": ["backyard", "bath", "bed", "bedroom", "chair", "closet", "drawer", "dryer", "garbage", "glass-window", "home", "lamp", "potty", "refrigerator", "room", "shower", "stairs", "table", "tv", "vacuum"],
    },
    {
        "id": "objects",
        "title": "Objects & Toys",
        "keys": ["balloon", "book", "doll", "flag", "gift", "napkin", "pen", "pencil", "penny", "puzzle", "radio", "scissors", "shoe", "toothbrush", "toy", "zipper"],
    },
    {
        "id": "transport",
        "title": "Transport",
        "keys": ["airplane", "boat", "car", "helicopter"],
    },
    {
        "id": "people_professions",
        "title": "Family, People & Professions",
        "keys": ["aunt", "boy", "brother", "child", "clown", "cowboy", "dad", "fireman", "girl", "grandma", "grandpa", "man", "mom", "person", "police", "uncle", "yourself"],
    },
    {
        "id": "body",
        "title": "Body Parts",
        "keys": ["arm", "cheek", "chin", "ear", "eye", "face", "feet", "hair", "head", "lips", "mouth", "nose", "tongue", "tooth"],
    },
    {
        "id": "colors",
        "title": "Colors",
        "keys": ["black", "blue", "brown", "green", "red", "white", "yellow"],
    },
    {
        "id": "nature",
        "title": "Nature & Places",
        "keys": ["cloud", "farm", "flower", "grass", "moon", "outside", "pool", "rain", "snow", "store", "sun", "there", "tree"],
    },
    {
        "id": "clothing",
        "title": "Clothing",
        "keys": ["hat", "jacket", "jeans", "mitten", "pajamas", "shirt", "underwear"],
    },
    {
        "id": "emotions",
        "title": "Emotions, States & Adjectives",
        "keys": ["awake", "bad", "better", "cute", "dirty", "empty", "fast", "fine", "first", "happy", "high", "hot", "hungry", "loud", "mad", "noisy", "old", "owie", "pretty", "quiet", "sad", "same", "sick", "sleepy", "sticky", "stuck", "thirsty", "wet", "yucky"],
    },
    {
        "id": "greetings",
        "title": "Greetings & Manners",
        "keys": ["bye", "hello", "please", "thank-you"],
    },
    {
        "id": "other",
        "title": "Time, Questions, Adverbs & Other",
        "keys": ["after", "all", "another", "any", "because", "before", "beside", "down", "every", "for", "he", "if", "into", "later", "many", "minemy", "morning", "music", "night", "no", "not", "now", "on", "story", "that", "time", "tomorrow", "up", "we", "where", "who", "why", "will", "yes", "yesterday"],
    },
]


def _parse_categories(categories: str):
    selected = [category.strip().lower() for category in categories.split(",") if category.strip()]
    category_ids = [category["id"] for category in CATEGORY_DEFINITIONS]

    if not selected or "mixed" in selected or "all" in selected:
        return ["alphabet"] + category_ids

    valid_ids = {"alphabet", *category_ids}
    selected = [category for category in selected if category in valid_ids]
    return selected or ["alphabet"] + category_ids


def generate_user_quiz(db: Session, user_id: int, categories: str, nn_dictionary: dict, letters_dictionary: dict):
    """
    Generates a quiz based on the signs learned by the user and filtered by one or more categories.
    Requires a minimum of 3 unlocked signs in the selected categories.
    """
    # 1. Recupera tutti i segni sbloccati dall'utente dal database
    learned_entries = db.query(models.LearnedSign).filter(models.LearnedSign.user_id == user_id).all()
    all_learned_words = list(set([entry.word.lower() for entry in learned_entries])) 
    
    alphabet_set = {w.lower() for w in letters_dictionary.keys()}
    nn_set = {w.lower() for w in nn_dictionary.keys()}
    selected_categories = _parse_categories(categories)

    category_sets = {
        category["id"]: {key.lower() for key in category["keys"] if key.lower() in nn_set}
        for category in CATEGORY_DEFINITIONS
    }
    category_titles = {category["id"]: category["title"] for category in CATEGORY_DEFINITIONS}
    category_titles["alphabet"] = "Alphabet"

    selected_words = set()
    if "alphabet" in selected_categories:
        selected_words.update(alphabet_set)

    for category_id in selected_categories:
        selected_words.update(category_sets.get(category_id, set()))

    category_label = ", ".join(category_titles[category] for category in selected_categories if category in category_titles)
    if len(selected_categories) > 2:
        category_label = "selected categories"

    # 2. Applica il filtro in base alle categorie selezionate dal frontend
    learned_words = [w for w in all_learned_words if w in selected_words]

    min_questions = 3

    # 3. Controllo bloccante del requisito minimo (3 segni) con stringhe in inglese
    if len(learned_words) < min_questions:
        if len(learned_words) == 0:
            msg = f"You cannot start the quiz because you haven't unlocked any signs in the {category_label} category yet. Unlock at least {min_questions} signs in the dictionary!"
        else:
            msg = f"You cannot start the quiz because you have only unlocked {len(learned_words)} signs in the {category_label} category. You need {min_questions - len(learned_words)} more to reach the minimum of {min_questions}!"
            
        return {
            "status": "error",
            "code": "INSUFFICIENT_SIGNS",
            "message": msg
        }

    # 4. Compilazione del set di domande (massimo 10)
    num_questions = min(len(learned_words), 10)
    target_words = random.sample(learned_words, num_questions)
    
    global_words = [w.lower() for w in list(nn_dictionary.keys()) + list(letters_dictionary.keys())]
    selected_words_list = list(selected_words)

    questions = []
    for idx, correct_word in enumerate(target_words):
        if correct_word in alphabet_set:
            distractor_pool = list(alphabet_set)
        else:
            distractor_pool = []
            for category_id in selected_categories:
                if correct_word in category_sets.get(category_id, set()):
                    distractor_pool = list(category_sets[category_id])
                    break
            if not distractor_pool:
                distractor_pool = selected_words_list

        possible_distractors = [w for w in distractor_pool if w != correct_word]
        if len(possible_distractors) < 3:
            possible_distractors = [w for w in selected_words_list if w != correct_word]
        if len(possible_distractors) < 3:
            possible_distractors = [w for w in global_words if w != correct_word]

        distractors = random.sample(possible_distractors, 3)
        
        options = distractors + [correct_word]
        random.shuffle(options)
        
        media_url = f"http://localhost:8000/gif_output/{correct_word.lower()}.gif"
        
        # Bilanciamento tipologie di gioco: 20% fotocamera, 40% sign-word, 40% word-sign
        rand = random.random()
        if rand < 0.25:
            question_type = 'recognition'
        elif rand < 0.625:
            question_type = 'sign-word'
        else:
            question_type = 'word-sign'
        
        questions.append({
            "question_index": idx + 1,
            "type": question_type,
            "target_word": correct_word,
            "target_media": media_url,
            "level": "level_1" if correct_word in alphabet_set else "level_2",
            "options": options
        })

    return {
        "status": "success",
        "questions": questions
    }
