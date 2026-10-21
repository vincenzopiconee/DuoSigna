""" This file contains all the necessary tools to manage language """

# NATURAL LANGUAGE TOOL KIT
import nltk
nltk.download('punkt_tab', quiet=True)
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.stem import PorterStemmer

import string
import difflib

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


from . import config as conf

# MUST BE THE SAME of build_embeddings.py
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
LLM_MODEL = 'llama3.2'


#_____________________________________________________________

# --- Function to process a sentence ---
# - Removing punctuation
# - Forcing lowercase
# - Stemming 
# - NOTE: Removing stopwords is risky in our case since easy words requested
#         by user can be part of the stopwords

def process(sentence):
  """Performs punctuation removal and stemming"""
  stemmer = PorterStemmer()
  
  # Add to stop_words what I want to remove
  stop_words = set(string.punctuation)
  stop_words = stop_words.union(set(["'s"]))
  # stop_words = stop_words.union(set(stopwords.words("english")))
  
  words = word_tokenize(sentence)
  new_sentence = ""
  for word in words:
    if word.lower() not in stop_words:
      # Stemming and Lowercasing 
      new_sentence += stemmer.stem(word.lower())
      new_sentence += " "

  # Return procesed sentence    
  return new_sentence

#_____________________________________________________________

# --- Function to extract a short title/summary from a chat ---
def summarize(client, long_text):
    # Process text
    clean_text = long_text.strip()
    
    # If chat is empty give a prefixed title
    if not clean_text:
        return "New Chat"

    # Create messages array with a strong System Prompt
    messages = [
        {
            'role': 'system',
            'content': 'You are an assistant specialized in summarizing conversations. Your only task is to generate a very short title (maximum 3-5 words) that describes the main topic of the provided chat. Return EXCLUSIVELY the title, without using quotes, trailing periods, or introductory phrases.'
        },
        {
            'role': 'user',
            'content': f"Chat text:\n\n{clean_text}"
        }
    ]

    try:
        # Call Ollama API
        response = client.chat(
            model=LLM_MODEL, 
            messages=messages
        )
        
        # Extract and clean the generated title
        title = response['message']['content'].strip()
        title = title.replace('"', '').replace("'", "")
        
        return title

    except Exception as e:
        print(f"Error during title generation: {e}")
        return "Chat Saved" # Fallback
    
#_____________________________________________________________

# --- Function to take just the instructions from the message using LLaMA 3.2 ---
def process_instructions(client, long_instructions):
  """
  Extract only the instructions using LLaMA 3.2 via Ollama.
  """
  # Process the long instructions text
  clean_text = long_instructions.strip()

  # Create messages array with a strong System Prompt
  messages = [
      {
          'role': 'system',
          'content': 'You are a precise text extractor. Your only task is to EXCLUSIVELY return the practical and physical instructions required to perform the American Sign Language (ASL) sign. Remove any introductions, conclusions, or conversational text. Do not add your own comments or explanations.'
      },
      {
          'role': 'user',
          'content': f"Text:\n\n{clean_text}"
      }
  ]

  try:
      # Call Ollama API
      response = client.chat(
          model=LLM_MODEL, 
          messages=messages
      )
      
      # Extract the content from the response
      instructions = response['message']['content'].strip()
      
      return instructions

  except Exception as e:
      print(f"Error during instructions extraction: {e}")
      return clean_text          
#_____________________________________________________________

# --- Function to find the closest word (in terms of wryiting form) to a target in a dictionary ---
def find_closest_word_typo(dictionary, target):
  # Extract all the keys (words) in my dictionary
  all_words = dictionary.keys()

  # Find closest word
  closest_word = difflib.get_close_matches(
    word=target,
    possibilities=all_words,
    n=1,  # Just one result
    cutoff=0.8 # Threshold for the similarity
  )

  # Return closest word if there is one that survives the cutoff
  return closest_word[0] if closest_word else None  

#_____________________________________________________________

# --- Function to find the closest word (in terms of meaning) to a target in ASL dictionary ---
def find_closest_word_meaning(model, dictionary_embeddings, target):
  # Get the embedding of the target word
  target_embedding = model.encode([target])

  # Compute cosine similarity (Returns a matrix of scores from -1 to 1)
  similarities = cosine_similarity(target_embedding, dictionary_embeddings)[0]

  # Find the highest
  best_index = np.argmax(similarities)
  best_score = similarities[best_index]

  # Impose a cutoff for similarity
  return [best_index] if best_score > 0.8 else None

#_____________________________________________________________

# --- Function to find the closest chunks (in terms of meaning) to a question target ---
def find_closest_chunks(model, chunks_embeddings, target, chunks, top_k=3, cutoff=0.4):
    # Get the embedding of the target text
    target_embedding = model.encode([target])

    # Compute cosine similarity
    similarities = cosine_similarity(target_embedding, chunks_embeddings)[0]

    # Get the top_k indices sorted by similarity (descending)
    top_indices = np.argsort(similarities)[::-1][:top_k]
    top_scores = similarities[top_indices]

    # Filter by cutoff and merge the best chunks into a single string
    selected_chunks = [
        chunks[i] for i, score in zip(top_indices, top_scores)
        if score > cutoff
    ]

    if not selected_chunks:
        return None

    # Return them as a single text string
    merged_context = "\n\n".join(selected_chunks)
    return merged_context

#_____________________________________________________________





