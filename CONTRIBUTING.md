# Contributing to AI Virtual Closet

Welcome to the team! This guide will help you get the project running on your local machine and explain our development workflow.

---

## 🛠️ Prerequisites

- **Node.js** (v18 or higher)
- **Python** (3.9 to 3.12)
- **Git**

---

## 🚀 One-Time Setup

### 1. Clone the Repository
```bash
git clone https://github.com/BassemBG/glam-fincommerce.git
cd virtual-closet
```

### 2. Backend Setup (FastAPI)
```bash
cd backend
# Create virtual environment
python -m venv venv
# Activate it (Windows)
.\venv\Scripts\activate
# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup (Next.js)
```bash
cd ../frontend
npm install
```

---

## 🔑 Environment Variables

### Backend (`backend/.env`)
Create a `.env` file in the `backend/` folder:
```env
GEMINI_API_KEY=your_google_ai_key_here
DATABASE_URL=sqlite:///./virtual_closet.db
```

### Frontend (`frontend/.env.local`)
Create a `.env.local` file in the `frontend/` folder:
```env
# Use localhost for local dev, or your IP for phone access
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 💾 Database & Demo Data

We use **SQLite** (zero-install) and **Qdrant** (local mode) for the MVP.

1. **Initialize Database**:
   ```bash
   cd backend
   python init_db.py
   ```
2. **Seed Demo Clothes & Outfits**:
   ```bash
   python seed_demo_data.py
   ```

---

## 🏃 Running the Application

You need to run both servers simultaneously.

### Start Backend
```bash
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Start Frontend
```bash
cd frontend
npm run dev -- --hostname 0.0.0.0
```

- **Web Access**: [http://localhost:3000](http://localhost:3000)
- **API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Mobile Access**: Check your IP with `ipconfig` and visit `http://YOUR_IP:3000` on your phone.

---

## 🧪 Development Workflow

1. **Branching**: Create a feature branch for your changes: `git checkout -b feat/your-feature-name`.
2. **Code Style**: We use Prettier for frontend and standard PEP8 for backend.
3. **Commit Messages**: Use [Conventional Commits](https://www.conventionalcommits.org/) (e.g., `feat: ...`, `fix: ...`, `chore: ...`).

---

## 🦉 Vector Search (Qdrant)
The project uses Qdrant in **Local Mode**. 
- Vector data is stored in `backend/qdrant_storage/`.
- Do **not** commit this folder (it's in `.gitignore`).
- If you need to reset the vector index, just delete that folder and re-run the seed script.
