# 🎯 DuoSigna - Quiz System Implementation Report

---

## 🧠 1. Architettura dei Quiz (Backend)

Logica isolata nel nuovo file `quiz.py`, alleggerendo il main.

- **Integrazione Database:** Il sistema interroga Postgres (Neon) per recuperare la lista dei segni salvati dall'utente corrente nella tabella `learned_signs`.
- **Requisito Minimo:** L'utente deve aver sbloccato almeno **3 segni** per poter generare un quiz. In caso contrario, l'endpoint blocca l'esecuzione e restituisce un errore `400 Bad Request`. Viene anche restituito un messaggio lato frontend.
- **Limite Massimo:** Il quiz seleziona un massimo di **10 domande** casuali basate esclusivamente sui progressi reali dell'utente.
- **Generazione Distrattori:** Per ogni domanda vengono estratti 3 distrattori (risposte errate) unici attingendo dai dizionari globali `NN_DICTIONARY` e `LETTERS_DICTIONARY`.
- **Modalità Dinamica delle Domande:** Introdotta l'alternanza casuale delle tipologie di quesito (`sign-word` per la scelta multipla testuale e `recognition` per la verifica in tempo reale tramite fotocamera), rendendo il quiz interattivo e misto.

---

## 🎨 2. Integrazione Frontend (`quiz.vue`)

I dati statici di prova (mock data) sono stati sostituiti con le chiamate asincrone alle API reali del server.

- **Avvio Quiz (`/api/quiz/start`):** Al click su *Start Quiz* (nella categoria *Mixed*), il frontend invia il token JWT nell'header per autenticare l'utente e scaricare le domande dinamiche.
- **Gestione Errori e Alert:** Implementato un blocco `try/catch` per intercettare il `400 Bad Request` del backend. Se i requisiti minimi non sono soddisfatti, viene mostrato un alert bloccante nel template esattamente sopra il pulsante di avvio.
- **Salvataggio Punteggio (`/api/quiz/submit`):** Al termine dell'ultima domanda, il frontend invia automaticamente il counter delle risposte corrette al backend, incrementando lo `score` dell'utente su Postgres.
- **Stile del Pulsante Skip:** Corretto il feedback visivo del pulsante "Skip Question" per entrambe le modalità di gioco (`sign-word` e `recognition`). Sono state integrate classi Tailwind dedicate (`transition-all hover:scale-105 hover:bg-gray-200 dark:hover:bg-gray-800`) per sanare il comportamento grafico della variante `soft` di Nuxt UI.
- **Ottimizzazione Tempi di Acquisizione:** Ridotto drasticamente il tempo di buffering automatico per il modulo di *Sign Recognition*. La proprietà computata `maxFrames` è stata riproporzionata a **60 frame** per le lettere (~2s) e **120 frame** per i segni completi (~4s), evitando attese inutili e migliorando la reattività del quiz e del chatbot.

---

## 📌 3. Next Steps

1. SOLVED **Mappatura Media/Icone:** Attualmente le opzioni usano l'icona generica `i-lucide-hand`. Bisogna collegare il campo `targetMedia` del quiz con i file video/GIF reali esposti dal backend sulla rotta `/gif_output`.
2. SOLVED **Filtri Categorie:** Estendere la logica di `quiz.py` per filtrare i dizionari se l'utente seleziona categorie specifiche anziché il quiz *Mixed* (es. solo lettere se sceglie *Alphabet*). Al momento solo la categoria "Mixed" è collegata ai dati dinamici; le altre (*Alphabet*, *Static Signs*, *Dynamic Signs*) avviano lo stato di gioco ma interrogano l'endpoint generico senza filtri specifici.
3. SOLVED tasto skip delle domande
4. SOLVED (vincenzo) alcune gif non funzionano: forse c'è un db da qualche parte con gif che non esistono?
5. SOLVED recording time del sign recognition troppo lungo
6. SUGGESTION usare i punti e le linee di mediapipe invece di quelle frontend che si vedono male
7. SOLVED 4 gif e una parola da indovinare
8. SOLVED riquadro rettangolare più grande
9. DEBUGGING usa sign reco in chatbot (chatbot.vue, vision_core, vision)
10. quando si fa partire il quiz scarica di nuovo i weight da HF
11. le gif sono ancora piccole
12. SOLVED (appunti vincenzo) il sign recognition anche se faccio il segno giusto non lo riconosce e me lo da sbagliato.
13. SOLVED (appunti vincenzo) mettere almeno 3 tentativi per il sign recognition
13. (appunti vincenzo) il pop-up della domanda corretta o sbagliata sarebe meglio e centrarlo con la sezione del quiz piuttosto che con tutta la pagina del sito (risulta decentrato per colpa della barra laterale a sinistra)
14. nelle opzioni dei quiz alcune parole non hanno gli spazi in mezzo