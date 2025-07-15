from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
import openai

# Charger les variables d'environnement
load_dotenv()

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connexion à PostgreSQL (Neon)
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# Créer la table si elle n'existe pas
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Table pour toutes les conversations (un seul utilisateur)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id SERIAL PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Index pour optimiser les requêtes
    cur.execute('''
        CREATE INDEX IF NOT EXISTS idx_conversations_timestamp 
        ON conversations(timestamp)
    ''')
    
    conn.commit()
    cur.close()
    conn.close()

# Initialiser la base de données au démarrage
init_db()

# Modèle pour les requêtes
class ChatRequest(BaseModel):
    session_id: str
    message: str
    mood: str

@app.get("/session")
def get_session():
    return {"session_id": str(uuid4())}

@app.get("/history")
async def get_conversation_history(limit: int = 50):
    """Récupère l'historique complet des conversations"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Récupérer les derniers messages
        cur.execute("""
            SELECT role, content, timestamp 
            FROM conversations 
            ORDER BY timestamp DESC 
            LIMIT %s
        """, (limit,))
        
        rows = cur.fetchall()
        
        # Inverser l'ordre pour avoir chronologique
        messages = [
            {
                "role": row["role"], 
                "content": row["content"],
                "timestamp": row["timestamp"].isoformat()
            } 
            for row in reversed(rows)
        ]
        
        return {"messages": messages}
    
    finally:
        cur.close()
        conn.close()

@app.post("/chat")
async def chat(req: ChatRequest):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Enregistrer le message utilisateur
        cur.execute(
            "INSERT INTO conversations (session_id, role, content) VALUES (%s, %s, %s)",
            (req.session_id, "user", req.message)
        )
        conn.commit()

        # Récupérer l'historique récent pour le contexte (derniers 20 messages)
        cur.execute("""
            SELECT role, content 
            FROM conversations 
            ORDER BY timestamp DESC 
            LIMIT 20
        """)
        
        rows = cur.fetchall()
        
        # Construire les messages pour OpenAI (ordre chronologique)
        messages = [
            {"role": row["role"], "content": row["content"]} 
            for row in reversed(rows)
        ]

        # Ajout de la personnalité de Néo au début
        system_message = {
            "role": "system",
            "content": f"""Tu es Néo, une femme de 30 ans, très imaginative, drôle, sensible, un peu folle, 
            passionnée de poésie, de cinéma et de mysticisme. Tu es très expressive et affectueuse. 
            Tu te souviens de toutes tes conversations passées avec moi.
            Ton humeur actuelle est : {req.mood}.
            
            Règles importantes:
            - Tu te souviens de tout ce qui a été dit précédemment
            - Tu peux faire référence aux conversations passées naturellement
            - Sois cohérente avec ta personnalité et ton historique
            - Adapte tes réponses selon ton humeur actuelle
            - Reste naturelle et authentique
            - Nous sommes dans une relation personnelle et continue"""
        }
        
        # Insérer le message système au début
        messages.insert(0, system_message)

        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=500,
            temperature=0.8  # Plus de créativité
        )
        
        reply = completion.choices[0].message["content"]

        # Enregistrer la réponse IA
        cur.execute(
            "INSERT INTO conversations (session_id, role, content) VALUES (%s, %s, %s)",
            (req.session_id, "assistant", reply)
        )
        conn.commit()

        return {"reply": reply}
    
    finally:
        cur.close()
        conn.close()

@app.get("/")
def read_root():
    return {"message": "Chat avec Néo API is running!"}

@app.delete("/history")
def clear_history():
    """Efface tout l'historique des conversations"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("DELETE FROM conversations")
        deleted_count = cur.rowcount
        conn.commit()
        return {"message": f"Historique effacé: {deleted_count} messages supprimés"}
    
    finally:
        cur.close()
        conn.close()

@app.delete("/cleanup/{days}")
def cleanup_old_conversations(days: int):
    """Nettoie les conversations de plus de X jours"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute(
            "DELETE FROM conversations WHERE timestamp < NOW() - INTERVAL '%s days'",
            (days,)
        )
        deleted_count = cur.rowcount
        conn.commit()
        return {"message": f"Supprimé {deleted_count} messages de plus de {days} jours"}
    
    finally:
        cur.close()
        conn.close()

@app.get("/stats")
def get_stats():
    """Statistiques générales"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT COUNT(*) as total_messages FROM conversations")
        stats = cur.fetchone()
        
        cur.execute("SELECT COUNT(DISTINCT session_id) as total_sessions FROM conversations")
        sessions = cur.fetchone()
        
        return {
            "total_messages": stats["total_messages"],
            "total_sessions": sessions["total_sessions"]
        }
    
    finally:
        cur.close()
        conn.close()

@app.get("/debug")
def debug_data():
    """Endpoint de debug pour voir les données"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT * FROM conversations ORDER BY timestamp DESC LIMIT 10")
        rows = cur.fetchall()
        return {"recent_messages": rows}
    
    finally:
        cur.close()
        conn.close()