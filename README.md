# Glam FinCommerce: AI-Powered Virtual Closet & Shopping Advisor

Glam FinCommerce is a state-of-the-art digital wardrobe management system. It uses **CLIP embeddings** and **Llama 3.2 Vision** (via Groq) to help users organize their clothes, visualize outfits, and get intelligent shopping advice.

## 🚀 Key Features

*   **Digital Closet**: Upload your clothes and let AI automatically categorize them, detect colors, and suggest styling tips.
*   **AI Shopping Advisor**: Upload a photo of a potential purchase and see how well it fits with your current wardrobe. The AI checks for visual similarity and metadata matches (category/color).
*   **Body Profile Analysis**: Analyze your physical traits (morphology, skin tone, height, weight) from a full-body photo to get personalized fashion advice.
*   **Visual Search**: Find items in your closet using natural language ("white summer dress") or image similarity.
*   **Virtual Try-On**: Visualize how different pieces look together on your virtual twin.

## 🛠️ Technology Stack

*   **Backend**: FastAPI, SQLAlchemy (SQLite), Qdrant (Vector Database).
*   **AI/ML**: Groq Llama 3.2 Vision, CLIP Embeddings (transformers/torch).
*   **Frontend**: Next.js 15+, TypeScript, CSS Modules.
*   **Storage**: Local & Cloud (Qdrant Cloud integration).

## 🏃 Getting Started

### Backend Setup
1. `cd backend`
2. `python -m venv venv`
3. `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
4. `pip install -r requirements.txt`
5. Create a `.env` file based on `.env.example` with your `GROQ_API_KEY` and `QDRANT_API_KEY`.
6. `uvicorn app.main:app --reload`

### Frontend Setup
1. `cd frontend`
2. `npm install`
3. `npm run dev`

## 📁 Project Structure
*   `backend/`: FastAPI server and AI services.
*   `frontend/`: Next.js web application.
*   `profile_data/`: (Local) AI-generated user physical profiles.
*   `uploads/`: (Local) temporary storage for high-res images.

## 📄 License
MIT
