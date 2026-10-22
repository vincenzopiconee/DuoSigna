# DuoSigna
### AI-Powered American Sign Language (ASL) Interactive Learning Platform

[![Live Web Application](https://img.shields.io/badge/Live%20App-Vercel-black?style=for-the-badge&logo=vercel)](https://duo-signa-rose.vercel.app)
[![Cloud Backend](https://img.shields.io/badge/API%20Backend-Google%20Cloud%20Run-4285F4?style=for-the-badge&logo=googlecloud)](https://duosigna-backend-628287759634.europe-west1.run.app)
[![Database](https://img.shields.io/badge/Database-Neon%20PostgreSQL-00E599?style=for-the-badge&logo=postgresql)](https://neon.tech)
[![AI LLM Engine](https://img.shields.io/badge/LLM-Groq%20Cloud%20(Llama%203.3)-F55036?style=for-the-badge&logo=groq)](https://groq.com)
[![Frontend](https://img.shields.io/badge/Frontend-Nuxt%203%20%7C%20Vue%203-00DC82?style=for-the-badge&logo=nuxtdotjs)](https://nuxt.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-24%2F7%20Active%20%26%20Production%20Ready-brightgreen?style=for-the-badge)](#)

---

## Live Product Access

DuoSigna is fully deployed and available 24/7 on the cloud:

* **Web Application (Frontend):** [https://duo-signa-rose.vercel.app](https://duo-signa-rose.vercel.app)
* **API Server (Backend):** [https://duosigna-backend-628287759634.europe-west1.run.app](https://duosigna-backend-628287759634.europe-west1.run.app)
* **Interactive API Docs (Swagger UI):** [https://duosigna-backend-628287759634.europe-west1.run.app/docs](https://duosigna-backend-628287759634.europe-west1.run.app/docs)

> **No installation required:** You can use DuoSigna directly from your modern web browser (desktop or mobile) on any device equipped with a webcam.

---

## Table of Contents
1. [Product Overview](#product-overview)
2. [Key Features](#key-features)
3. [System Architecture](#system-architecture)
4. [Technology Stack](#technology-stack)
5. [User Guide: How to Use DuoSigna](#user-guide-how-to-use-duosigna)
6. [Machine Learning & Computer Vision Engine](#machine-learning--computer-vision-engine)
7. [Cloud Infrastructure & 24/7 Deployment](#cloud-infrastructure--247-deployment)
8. [Local Development Setup (Optional)](#local-development-setup-optional)
9. [API Overview](#api-overview)
10. [Authors & Academic Context](#authors--academic-context)
11. [License](#license)

---

## Product Overview

**DuoSigna** is an educational platform dedicated to teaching **American Sign Language (ASL)** through real-time interactive computer vision and an autonomous AI conversational tutor.

### The Problem
Traditional sign language education relies heavily on static 2D illustrations or passive video demonstrations. Learners lack **immediate feedback** on their 3D hand postures, finger geometry, orientation, and motion dynamics, making self-study frustrating and prone to reinforcing improper habits.

### The DuoSigna Solution
DuoSigna bridges this gap by combining:
1. **Real-time Computer Vision**: Browser-native hand tracking and landmark extraction via MediaPipe running at smooth frame rates with zero client-side lag.
2. **Machine Learning Recognition**: Cloud-powered neural networks and geometry classifiers verifying sign correctness and offering targeted physical corrections.
3. **Autonomous AI Tutor**: A conversational assistant powered by ultra-fast cloud LLMs (Groq / Llama 3.3) capable of translating English words into signs, answering cultural ASL questions, and guiding students through practical exercises.
4. **Gamified Quizzing & Dictionary**: Active vocabulary unlocking, streak tracking, multi-modal quiz challenges, and visual animation libraries.

---

## Key Features

### 1. Intelligent AI Sign Tutor (`/chatbot`)
* **Natural Dialogue**: Ask questions about ASL grammar, deaf culture, or specific signs in plain English.
* **Intent-Aware Routing**: Automatically identifies whether the user wants a sign translation, practice session, conceptual explanation, or casual conversation.
* **Visual Demonstrations**: Automatically pairs responses with synchronized animated sign GIFs or curated YouTube tutorials.
* **Instant Voice Synthesis (TTS)**: Native browser speech engine (`Web Speech API`) vocalizing responses with zero latency.
* **Voice Input**: Speak your questions directly to the tutor using hands-free speech recognition.
* **Persistent Sessions**: Multiple chat conversations saved per user profile.

### 2. Real-Time Vision & Skeleton HUD
* **Client-Side MediaPipe**: Extracts 21 3D hand landmarks and holistic body posture directly in the browser canvas.
* **Live Skeleton Overlay**: Visual HUD with togglable skeleton joints, bounding boxes, and capture states.
* **Optimized Bandwidth**: Captures normalized coordinates and compresses floating points before transmitting frames for inference, ensuring instant evaluation even over mobile connections.

### 3. Categorized ASL Dictionary (`/dictionary`)
* **Over 100+ Signs & Complete Alphabet**: Structured into clear categories (Alphabet, Animals, Food, Actions, Home, Emotions, Colors, Transport, Nature, etc.).
* **Detailed Execution Guides**: Clear textual step-by-step instructions for each sign.
* **Animated Reference Media**: High-framerate looping GIF demonstrations.
* **Progress Tracking**: Unlock signs as you master them to track your growing vocabulary.

### 4. Gamified Quiz & Evaluation System (`/quiz`)
* **Sign-to-Word**: Watch a sign animation and choose the correct meaning from multiple options.
* **Word-to-Sign**: Read an English term and pick the matching animated sign from a visual gallery.
* **Camera Recognition Challenge**: Stand in front of your webcam, perform the required sign, and receive real-time AI validation with targeted correction hints.
* **Dynamic Category Filtering**: Focus your evaluation on specific topic modules or mix unlocked signs.
* **Scoring & Streak Progression**: Earn scores, review mistakes, and track mastery.

### 5. Secure Authentication & User State
* **JWT-Based Authentication**: Secure registration, login, and password hashing (`bcrypt`).
* **Cloud Database Persistence**: Cloud-hosted PostgreSQL managing profiles, unlocked signs, chat history, and evaluation scores.

---

## System Architecture

```mermaid
flowchart TD
    User["User (Browser / Mobile / Desktop)"]
    
    subgraph Frontend ["Frontend (Vercel Edge Network)"]
        UI["Nuxt 3 + Vue 3 + Nuxt UI"]
        MP["MediaPipe Holistic (Client-Side Vision)"]
        TTS["Web Speech API (Browser Voice / TTS)"]
        Auth["Nuxt Auth Client (JWT)"]
    end
    
    subgraph Backend ["Backend (Google Cloud Run - 24/7 Container)"]
        FastAPI["FastAPI App (uvicorn / uv)"]
        Static["Case-Insensitive Static Media Server (/gif_output)"]
        RecEngine["Sign Recognition Engine (Sklearn / TensorFlow)"]
        BotCore["Chatbot Core & Prompt Orchestrator"]
    end
    
    subgraph ExternalServices ["Cloud AI & Database Services"]
        Groq["Groq Cloud API (Llama 3.3-70B / 3.1-8B)"]
        NeonDB[("Neon Serverless PostgreSQL Database")]
    end

    User -->|"Webcam Video Feed"| MP
    User -->|"Interacts via UI & Voice"| UI
    UI -->|"Audio Output"| TTS
    
    MP -->|"Normalized Landmarks JSON"| FastAPI
    UI -->|"HTTPS REST API / JWT"| FastAPI
    
    FastAPI -->|"Query / Update Progress"| NeonDB
    FastAPI -->|"Classification & Feedback"| RecEngine
    FastAPI -->|"Prompt / Dialog Context"| BotCore
    BotCore -->|"High-Speed Inference"| Groq
    FastAPI -->|"Sign GIFs & Media"| Static
    Static -->|"Animated Sign Loops"| UI
```

---

## Technology Stack

| Layer | Technology | Version / Tooling | Purpose |
| :--- | :--- | :--- | :--- |
| **Frontend Framework** | **Nuxt 3 / Vue 3** | `v3.x / Nuxt 4 Ready` | Modern Reactive Single-Page Application (SPA) with Universal Rendering |
| **UI & Styling** | **Tailwind CSS + Nuxt UI** | `Tailwind v4 / @nuxt/ui` | Fully responsive design with Dark/Light theme switching |
| **Icons & Tour** | **Lucide, MDI, Driver.js** | `@iconify-json / driver.js` | Interactive guided walkthroughs and rich UI iconography |
| **Vision (Browser)** | **MediaPipe Holistic** | `@mediapipe/holistic` | Real-time client-side pose and 21-point hand landmark detection |
| **Speech & Audio** | **Web Speech API** | Browser Native | Zero-latency browser text-to-speech (TTS) and voice recognition |
| **Backend API** | **FastAPI** | `v0.136.x / Python 3.11` | High-performance asynchronous REST API backend |
| **Package Manager** | **uv** | Astral `uv` | Ultra-fast Python dependency management and reproducible builds |
| **Language Model** | **Groq Cloud API** | `llama-3.3-70b-versatile` | Real-time AI tutor dialogue, cultural guidance, and intent resolution |
| **Machine Learning** | **Scikit-Learn & TensorFlow** | `scikit-learn 1.6 / TF 2.21` | Static finger-spelling classification and dynamic sequence recognition |
| **Database & ORM** | **PostgreSQL (Neon) + SQLAlchemy** | `SQLAlchemy 2.0 / psycopg2` | Serverless cloud PostgreSQL storing users, chats, signs, and scores |
| **Authentication** | **JWT & Bcrypt** | `PyJWT / passlib / bcrypt` | Secure token authentication and password hashing |
| **Containerization** | **Docker** | Debian Slim Multi-stage | Optimized cloud runtime container image |
| **Cloud Hosting** | **Vercel & Google Cloud Run** | Serverless / Cloud Run | Scalable 24/7 cloud deployment within 100% free-tier limits |

---

## User Guide: How to Use DuoSigna

### 1. Launch & Account Creation
1. Open [https://duo-signa-rose.vercel.app](https://duo-signa-rose.vercel.app) in any modern browser (Chrome, Edge, Safari, Firefox).
2. Sign in or create a new account in seconds.
3. Upon your first login, an interactive guided tour introduces the platform.

### 2. Learn with the AI Tutor (`Tutor` Tab)
* **Ask Questions**: Type queries like *"How do I sign 'apple'?"*, *"What is the difference between signs for 'mother' and 'father'?"*, or *"Can you quiz me on greetings?"*.
* **Listen & Speak**: Toggle the audio speaker icon to listen to the tutor's voice or use the microphone to talk hands-free.
* **Practice Mode**: Click the **Camera Practice** button on any suggested sign:
  1. Allow webcam access when prompted by the browser.
  2. Position your hand inside the camera frame.
  3. Press **[N]** to start buffering your sign motion.
  4. Perform the sign and press **[Spacebar]** (or let the countdown finish) to submit.
  5. The AI verifies your sign and returns detailed feedback on palm orientation, fingertip positions, and accuracy.

### 3. Explore the ASL Dictionary (`Dictionary` Tab)
* Browse categories or search for specific signs (e.g. *Cat, Water, Thank You, Happy*).
* Inspect the sign's animated demonstration GIF and step-by-step physical instructions.
* Unlock signs to add them to your mastered pool and make them eligible for quizzes.

### 4. Test Yourself in the Quiz (`Quiz` Tab)
1. Select one or more categories (ensure you have unlocked at least 3 signs in the selected modules).
2. Start the quiz to experience a balanced mix of questions:
   * **Identify Sign**: Watch a looping GIF and choose the corresponding word.
   * **Select Sign**: Read a prompt and pick the correct gesture among 4 animated options.
   * **Live Sign Performance**: Perform the requested sign in front of your camera. If you get stuck, click **"Don't remember the sign? Watch the hint"** to reveal a reference animation.
3. Review your final score and track your learning progress.

---

## Machine Learning & Computer Vision Engine

DuoSigna combines dual recognition pipelines optimized for accuracy and speed:

```
[Webcam Stream] 
       │
       ▼
[MediaPipe Holistic (Client Canvas)]
  ├── 21 Hand Landmarks (x, y, z) per hand
  └── Pose Landmarks (shoulders, elbows, wrists)
       │
       ▼
[Feature Normalization & Compression]
  ├── Normalized relative to wrist coordinate
  └── Quantized 4-decimal JSON payload
       │
       ▼
[FastAPI Backend Classifier]
  ├── Level 1 (Static Alphabet A-Z): Random Forest / SVM Hand Geometry Classifier
  └── Level 2 (Dynamic Words): Multi-frame Sequential Neural Network
       │
       ▼
[Instant Confidence Score & Targeted Geometric Correction Feedback]
```

---

## Cloud Infrastructure & 24/7 Deployment

DuoSigna is engineered to run **24 hours a day, 7 days a week, 100% free of charge**, leveraging modern serverless cloud tiers:

1. **Frontend on Vercel**:
   * Continuous Deployment triggered directly on every push to the `main` branch.
   * Global CDN edge delivery ensuring fast load times worldwide.
   * Environment variable `NUXT_PUBLIC_API_BASE` points seamlessly to the Cloud Run backend.

2. **Backend on Google Cloud Run**:
   * Packaged as an optimized Docker container using Python 3.11 and Astral `uv`.
   * **Auto-Scaling**: Configured with `min-instances=0` and concurrency handling, staying comfortably within GCP's generous monthly Free Tier (2 million requests/month).
   * **Continuous Delivery**: Integrated with Google Cloud Build to automatically build and roll out revisions on Git push.

3. **Database on Neon PostgreSQL**:
   * Serverless cloud database with automated scaling and connection pooling.
   * Zero server maintenance or manual backup requirements.

4. **Groq Cloud AI**:
   * Hardware-accelerated LPU (Language Processing Unit) inference for Llama 3 models delivering near-instant text generation without expensive dedicated cloud GPUs.

---

## Local Development Setup (Optional)

If you wish to run DuoSigna locally on your development machine:

### Prerequisites
* **Node.js** (v18 or higher) and `npm`
* **Python** (v3.11 or higher)
* **uv** (recommended Python package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
* **Git**

### 1. Clone the Repository
```bash
git clone https://github.com/vincenzopiconee/DuoSigna.git
cd DuoSigna
```

### 2. Backend Setup
```bash
cd backend

# Install dependencies with uv
uv sync

# Configure environment variables
# Create a .env file with your database and Groq credentials:
# DATABASE_URL="postgresql://user:password@host/dbname?sslmode=require"
# GROQ_API_KEY="your-groq-api-key"
# JWT_SECRET="your-secret-key"

# Start the FastAPI server
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
*The backend API will be available at `http://127.0.0.1:8000`.*

### 3. Frontend Setup
```bash
# In a new terminal window:
cd frontend

# Install Node dependencies
npm install

# Start the Nuxt 3 development server
npm run dev
```
*The web app will be accessible at `http://localhost:3000`.*

---

## API Overview

The backend exposes fully documented REST endpoints compliant with OpenAPI / Swagger standards. Visit `/docs` on the backend URL to inspect the live interactive explorer.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Register a new user account |
| `POST` | `/api/auth/login` | Authenticate user and receive JWT bearer token |
| `GET` | `/api/user/me` | Fetch current user profile and stats |
| `GET` | `/api/user/unlocked-signs` | Retrieve user's unlocked dictionary signs |
| `POST` | `/api/user/unlock-sign` | Unlock a newly learned sign |
| `POST` | `/chat` | Send a message to the AI sign language tutor |
| `GET` | `/api/chats` | Retrieve conversation history |
| `POST` | `/recognize-letter` | Classify static finger-spelling landmarks |
| `POST` | `/recognize-sign` | Classify multi-frame dynamic sign gestures |
| `GET` | `/api/dictionary/letters` | Get dictionary entries for alphabet signs |
| `GET` | `/api/dictionary/words` | Get dictionary entries for categorized words |
| `GET` | `/api/quiz/start` | Generate dynamic questions filtered by category |
| `POST` | `/api/quiz/submit` | Record quiz results and update user experience |
| `GET` | `/gif_output/{filename}` | Stream sign demonstration animated GIFs |

---

## Authors & Academic Context

### Production & Cloud Evolution (Current Release)
* [Vincenzo Picone](https://github.com/vincenzopiconee) — *Lead Developer, Cloud Architecture, Groq LLM & Web Speech Integration, CI/CD & Deployment*

### Academic Origins (Politecnico di Milano)
DuoSigna originally started as a collaborative academic project for the **Multimodal Interactive Technologies and Applications (MITA)** course at **Politecnico di Milano (PoliMi)**, developed in collaboration with:

* [Andrea Arzilli](https://github.com/AndreaArzilli)
* [Camilla Bocciolone](https://github.com/camillabocciolone)
* [Davide Fileccia](https://github.com/davidefileccia)
* [Filippo Galletta](https://github.com/filippogalletta)
* [Niccolò Sobrero](https://github.com/NiccoloSobrero)

*Special thanks to the teaching staff and course instructors at Politecnico di Milano for their guidance during the initial conception.*

---

## License

This project is licensed under the terms of the **MIT License**. See the [LICENSE](LICENSE) file for the full license text.

---

<p align="center">
  <b>DuoSigna</b> — Empowering communication through the beauty of sign language.
</p>
