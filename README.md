# DuoSigna-FinalVersion

Welcome to DuoSigna! This document contains all the step-by-step instructions to install the dependencies and properly start the local development environment (Python Backend and Nuxt 3 Frontend).

## 🛠 Prerequisites
Before starting, ensure you have the following installed on your local machine:
* **Node.js** (which includes `npm`) to run the frontend.
* **Python** and **uv** (an ultra-fast Python package manager) to run the backend.
* **llama3.2** to run the model on your computer.

---

## 🖥 1. Backend Setup & Startup (FastAPI)

The backend manages the AI models (Kokoro TTS, Scikit-Learn for Sign Recognition) and the API calls.

1. Open a terminal and navigate to the backend folder:

```
cd backend
```

2. Install the project dependencies. This command reads the project configuration file and installs all the required packages locally:
   
```
uv sync
```


3. Start the FastAPI server in development mode:

```
uv run uvicorn main:app --reload
```


*The backend is now active and listening at: `http://127.0.0.1:8000`*

---

## 🎨 2. Frontend Setup & Startup (Nuxt 3)

The frontend manages the user interface, the chatbot, and the webcam access for sign recognition.

1. Open a **new** terminal (leaving the backend running in the background) and navigate to the frontend folder:

```
cd frontend
```

2. Install all the Node.js dependencies declared in the `package.json` file:

```
npm install
```


3. Start the frontend development server:
   
```
npm run dev
```


*The site is now ready! Open your browser and navigate to the address indicated in the terminal (usually `http://localhost:3000`).*
