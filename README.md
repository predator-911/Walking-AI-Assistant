# 🚶‍♂️ Walking AI Assistant – Your Location-Aware Travel AI

> Your personal AI that walks with you — wherever you go.

The Walking AI Assistant is an intelligent, location-aware assistant that combines **geospatial awareness**, **LLM capabilities**, and **real-time context** to help you explore the world like never before.

🧭 Whether you're walking through Paris or planning a trip to Tokyo, it generates:
- Nearby points of interest
- Smart travel timelines
- Personalized suggestions
- Day-by-day check-ins and travel memories

---

## ✨ Features

- 🌍 **Geolocation-based Intelligence**  
  Understands where you are and tailors responses accordingly.

- 🗓️ **AI Travel Timeline Generator**  
  Automatically creates your itinerary based on time, interests, and location.

- 💬 **LLM-Powered Assistant**  
  Uses OpenAI or any compatible LLM to give intelligent responses, suggestions, and summaries.

- 📍 **Check-in + Memory System**  
  Stores and remembers where you’ve been and what you liked.

- 🌐 **FastAPI Backend**  
  Clean, modular, and production-ready backend built using FastAPI.

- ⚙️ **Plug-and-Play Design**  
  Modular services for location, language model, and user session — easy to scale or swap.

---

## 🏗️ Tech Stack

- **Python**  
- **FastAPI**  
- **OpenAI API (or other LLM)**  
- **Google Maps API (planned)**  
- **SQLite / Firebase (planned for memory)**  
- **Timeline.js / Streamlit (for visualization)**

---

## 🚀 How to Run (Local Setup)

```bash
git clone https://github.com/your-username/Walking-AI-Assistant.git
cd Walking-AI-Assistant
pip install -r requirements.txt
uvicorn main:app --reload
