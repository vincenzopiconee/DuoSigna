""" This file contains all the configuration settings, updated for PostgreSQL """

import os
import json

def read_settings(base_dir, file_path="settings.json"):
    """
    Legge il file JSON delle impostazioni e restituisce un dizionario.
    Rimosse le dipendenze dal vecchio database SQLite.
    """
    # Costruisce il percorso assoluto combinando la cartella base e il nome file
    full_path = os.path.join(base_dir, file_path)

    if not os.path.exists(full_path):
        print(f"Warning: Il file {full_path} non è stato trovato!")
        return {}

    with open(full_path, "r", encoding="utf-8") as file:
        try:
            settings = json.load(file)
        except json.JSONDecodeError:
            print(f"Error: Il file {full_path} è malformato.")
            return {}     

    # Restituisce le impostazioni (la gestione dell'ID sessione ora avviene in main.py)
    return settings