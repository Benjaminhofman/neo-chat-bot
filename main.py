from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
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

# Configuration avec debug
DATABASE_URL = os.getenv("DATABASE_URL")
openai.api_key = os.getenv("OPENAI_API_KEY")

# Debug - vérifier que les variables sont chargées
print(f"DATABASE_URL présent: {DATABASE_URL is not None}")
print(f"OPENAI_API_KEY présent: {openai.api_key is not None}")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL non trouvée dans les variables d'environnement")
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY non trouvée dans les variables d'environnement")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir les fichiers statiques si le dossier existe
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# HTML intégré pour servir l'interface
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="theme-color" content="#667eea">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="apple-mobile-web-app-title" content="Néo Chat">
    <title>Chat avec Néo</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding: 10px;
            max-width: 100%;
            margin: 0 auto;
            transition: background 1.2s ease;
            min-height: 100vh;
            line-height: 1.6;
            overflow-x: hidden;
        }
        
        /* Arrière-plans selon l'humeur */
        .mood-heureux { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .mood-triste { background: linear-gradient(135deg, #4b79a1 0%, #283e51 100%); }
        .mood-amoureux { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        .mood-pensif { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
        .mood-stressé { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
        .mood-curieux { background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); }
        .mood-rêveur { background: linear-gradient(135deg, #d299c2 0%, #fef9d7 100%); }
        .mood-groguis { background: linear-gradient(135deg, #89f7fe 0%, #66a6ff 100%); }

        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255,255,255,0.2);
            max-width: 1000px;
            margin: 0 auto;
            min-height: calc(100vh - 20px);
            display: flex;
            flex-direction: column;
        }

        .header {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 2px solid rgba(0,0,0,0.1);
            flex-shrink: 0;
        }
        
        .avatar {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background-image: url('https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=120&h=120&fit=crop&crop=faces');
            background-size: cover;
            background-position: center;
            border: 3px solid rgba(255,255,255,0.8);
            box-shadow: 0 8px 16px rgba(0,0,0,0.15);
            margin-right: 15px;
            transition: all 0.3s ease;
            flex-shrink: 0;
        }
        
        .avatar:hover { transform: scale(1.1); border-color: #667eea; }
        .avatar.mood-heureux { filter: brightness(1.1) saturate(1.1); border-color: rgba(255, 215, 0, 0.8); }
        .avatar.mood-triste { filter: brightness(0.8) saturate(0.7) blur(0.3px); border-color: rgba(135, 206, 235, 0.8); }
        .avatar.mood-amoureux { filter: brightness(1.2) saturate(1.3) hue-rotate(10deg); border-color: rgba(255, 182, 193, 0.9); animation: pulse-love 2s infinite; }
        .avatar.mood-pensif { filter: brightness(0.9) saturate(0.8) contrast(1.1); border-color: rgba(221, 160, 221, 0.8); }
        .avatar.mood-stressé { filter: brightness(1.1) saturate(1.2) hue-rotate(-10deg); border-color: rgba(255, 99, 71, 0.8); animation: shake 0.5s infinite; }
        .avatar.mood-curieux { filter: brightness(1.05) saturate(1.1) contrast(1.05); border-color: rgba(135, 206, 235, 0.9); animation: bounce-curious 1.5s infinite; }
        .avatar.mood-rêveur { filter: brightness(0.95) saturate(0.9) blur(0.2px); border-color: rgba(221, 160, 221, 0.7); animation: float-dream 3s infinite ease-in-out; }
        .avatar.mood-groguis { filter: brightness(0.7) saturate(0.6) contrast(1.2); border-color: rgba(105, 105, 105, 0.8); }

        @keyframes pulse-love { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); } }
        @keyframes shake { 0%, 100% { transform: translateX(0); } 25% { transform: translateX(-1px); } 75% { transform: translateX(1px); } }
        @keyframes bounce-curious { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-2px); } }
        @keyframes float-dream { 0%, 100% { transform: translateY(0) rotate(0deg); } 50% { transform: translateY(-3px) rotate(1deg); } }

        .header-info { flex-grow: 1; min-width: 0; }
        .header-info h1 { color: #2c3e50; font-size: 24px; font-weight: 600; margin-bottom: 2px; }
        .status { color: #7f8c8d; font-size: 13px; font-style: italic; }
        .status.online { color: #27ae60; }
        
        #chat_box {
            flex-grow: 1;
            overflow-y: auto;
            padding: 15px;
            background: rgba(248, 249, 250, 0.8);
            border-radius: 12px;
            margin-bottom: 15px;
            border: 1px solid rgba(0,0,0,0.1);
            scrollbar-width: thin;
            scrollbar-color: #bdc3c7 transparent;
            min-height: 0;
            max-height: calc(100vh - 200px);
            -webkit-overflow-scrolling: touch;
        }

        #chat_box::-webkit-scrollbar { width: 6px; }
        #chat_box::-webkit-scrollbar-track { background: transparent; }
        #chat_box::-webkit-scrollbar-thumb { background: #bdc3c7; border-radius: 3px; }

        .message {
            margin-bottom: 15px;
            padding: 12px 16px;
            border-radius: 16px;
            max-width: 85%;
            word-wrap: break-word;
            animation: fadeIn 0.3s ease;
            font-size: 15px;
            line-height: 1.4;
        }

        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

        .user-message {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin-left: auto;
            border-bottom-right-radius: 5px;
        }

        .neo-message {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            color: #2c3e50;
            margin-right: auto;
            border-bottom-left-radius: 5px;
            border: 1px solid rgba(0,0,0,0.1);
        }

        .neo-message.loading {
            background: linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%);
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }

        .message-header {
            font-weight: 600;
            font-size: 11px;
            margin-bottom: 4px;
            opacity: 0.8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .input-container {
            display: flex;
            gap: 10px;
            align-items: flex-end;
            background: rgba(255,255,255,0.9);
            padding: 12px;
            border-radius: 12px;
            border: 1px solid rgba(0,0,0,0.1);
            flex-shrink: 0;
            position: sticky;
            bottom: 0;
        }

        input {
            flex: 1;
            padding: 12px 16px;
            font-size: 16px;
            border: 2px solid rgba(102, 126, 234, 0.3);
            border-radius: 20px;
            background: rgba(255,255,255,0.9);
            outline: none;
            transition: all 0.3s ease;
            min-height: 44px;
            resize: none;
        }

        input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        button {
            padding: 12px 20px;
            font-size: 15px;
            font-weight: 600;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.3s ease;
            min-width: 80px;
            min-height: 44px;
            white-space: nowrap;
        }

        button:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }

        button:disabled {
            background: #bdc3c7;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }

        .error {
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
            color: white;
            border: none;
        }

        .welcome-message {
            text-align: center;
            color: #7f8c8d;
            font-style: italic;
            margin: 50px 0;
        }

        /* Mobile optimizations */
        @media (max-width: 768px) {
            body { padding: 5px; }
            .container { padding: 10px; border-radius: 10px; min-height: calc(100vh - 10px); }
            .header { margin-bottom: 10px; padding-bottom: 10px; }
            .avatar { width: 40px; height: 40px; margin-right: 10px; }
            .avatar.mood-stressé { animation: shake 0.3s infinite; }
            .avatar.mood-curieux { animation: bounce-curious 1s infinite; }
            .avatar.mood-rêveur { animation: float-dream 2s infinite ease-in-out; }
            .header-info h1 { font-size: 20px; }
            .status { font-size: 12px; }
            #chat_box { padding: 10px; margin-bottom: 10px; max-height: calc(100vh - 160px); }
            .message { max-width: 90%; padding: 10px 14px; margin-bottom: 12px; font-size: 14px; }
            .message-header { font-size: 10px; margin-bottom: 3px; }
            .input-container { padding: 8px; gap: 8px; position: fixed; bottom: 5px; left: 5px; right: 5px; margin: 0; z-index: 1000; box-shadow: 0 -2px 10px rgba(0,0,0,0.1); }
            input { font-size: 16px; padding: 10px 14px; }
            button { padding: 10px 16px; font-size: 14px; min-width: 70px; }
            .container { padding-bottom: 70px; }
        }

        @media (max-width: 480px) {
            .header-info h1 { font-size: 18px; }
            .avatar { width: 35px; height: 35px; }
            .avatar.mood-stressé { animation: shake 0.2s infinite; }
            .avatar.mood-curieux { animation: bounce-curious 0.8s infinite; }
            .avatar.mood-amoureux { animation: pulse-love 1.5s infinite; }
            .message { font-size: 13px; padding: 8px 12px; }
            input { padding: 8px 12px; font-size: 16px; }
            button { padding: 8px 12px; min-width: 60px; font-size: 13px; }
        }

        @media (max-width: 768px) and (orientation: landscape) {
            #chat_box { max-height: calc(100vh - 120px); }
            .container { padding-bottom: 60px; }
        }

        @supports (padding: max(0px)) {
            .input-container {
                padding-left: max(8px, env(safe-area-inset-left));
                padding-right: max(8px, env(safe-area-inset-right));
                padding-bottom: max(8px, env(safe-area-inset-bottom));
            }
        }
    </style>
</head>
<body class="mood-heureux">
    <div class="container">
        <div class="header">
            <div class="avatar"></div>
            <div class="header-info">
                <h1>Néo</h1>
                <div class="status online">En ligne</div>
            </div>
        </div>

        <div id="chat_box">
            <div class="welcome-message">
                Conversations chargées... Prêt à discuter !
            </div>
        </div>

        <div class="input-container">
            <input type="text" id="user_input" placeholder="Écrivez votre message..." />
            <button id="send_button" onclick="sendMessage()">Envoyer</button>
        </div>
    </div>

    <script>
        // Configuration - URL dynamique qui s'adapte
        const API_BASE_URL = window.location.origin;

        // Humeurs et gestion
        const moods = ['heureux', 'triste', 'amoureux', 'pensif', 'stressé', 'curieux', 'rêveur', 'groguis'];
        let currentMood = 'heureux';
        let session_id = sessionStorage.getItem("session_id");

        function getRandomMood() {
            const weightedMoods = [
                'heureux', 'heureux', 'heureux',
                'curieux', 'curieux',
                'pensif', 'pensif',
                'triste', 'amoureux', 'stressé', 'rêveur', 'groguis'
            ];
            return weightedMoods[Math.floor(Math.random() * weightedMoods.length)];
        }

        function changeMood() {
            const newMood = getRandomMood();
            if (newMood !== currentMood) {
                currentMood = newMood;
                updateBackground();
            }
        }

        function updateBackground() {
            document.body.className = `mood-${currentMood}`;
            const avatar = document.querySelector('.avatar');
            avatar.className = `avatar mood-${currentMood}`;
        }

        function startMoodTimer() {
            setInterval(() => {
                changeMood();
            }, Math.random() * 120000 + 240000);
        }

        async function initSession() {
            if (!session_id) {
                try {
                    const res = await fetch(`${API_BASE_URL}/session`);
                    const data = await res.json();
                    session_id = data.session_id;
                    sessionStorage.setItem("session_id", session_id);
                } catch (error) {
                    console.error("Erreur lors de l'initialisation de la session:", error);
                    showError("Erreur de connexion au serveur");
                }
            }
        }

        async function loadConversationHistory() {
            try {
                const res = await fetch(`${API_BASE_URL}/history`);
                if (res.ok) {
                    const data = await res.json();
                    const chatBox = document.getElementById("chat_box");
                    chatBox.innerHTML = '';
                    
                    if (data.messages && data.messages.length > 0) {
                        data.messages.forEach(msg => {
                            if (msg.role === 'user') {
                                addMessage("Vous", msg.content, "user-message", false);
                            } else if (msg.role === 'assistant') {
                                addMessage("Néo", msg.content, "neo-message", false);
                            }
                        });
                    } else {
                        addMessage("Néo", "Salut ! Je suis ravie de te rencontrer. Comment puis-je t'aider aujourd'hui ?", "neo-message", false);
                    }
                }
            } catch (error) {
                console.error("Erreur lors du chargement de l'historique:", error);
                addMessage("Néo", "Salut ! Je suis ravie de te rencontrer. Comment puis-je t'aider aujourd'hui ?", "neo-message", false);
            }
        }

        async function sendMessage() {
            const input = document.getElementById("user_input");
            const sendButton = document.getElementById("send_button");

            if (!input.value.trim()) return;

            try {
                await initSession();

                if (Math.random() < 0.2) {
                    changeMood();
                }

                sendButton.disabled = true;
                sendButton.textContent = "Envoi...";

                const userMessage = input.value.trim();
                addMessage("Vous", userMessage, "user-message");
                input.value = "";

                const loadingId = addMessage("Néo", "En train d'écrire...", "neo-message loading");

                const res = await fetch(`${API_BASE_URL}/chat`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        session_id,
                        message: userMessage,
                        mood: currentMood
                    })
                });

                if (!res.ok) {
                    throw new Error(`Erreur HTTP: ${res.status}`);
                }

                const data = await res.json();

                document.getElementById(loadingId).remove();
                addMessage("Néo", data.reply, "neo-message");

            } catch (error) {
                console.error("Erreur:", error);
                const loadingElement = document.querySelector('.loading');
                if (loadingElement) loadingElement.remove();
                
                showError("Erreur lors de l'envoi du message. Veuillez réessayer.");
            } finally {
                sendButton.disabled = false;
                sendButton.textContent = "Envoyer";
            }
        }

        function addMessage(sender, message, className, scroll = true) {
            const chatBox = document.getElementById("chat_box");
            const messageId = `msg_${Date.now()}_${Math.random()}`;
            const messageDiv = document.createElement("div");
            messageDiv.id = messageId;
            messageDiv.className = `message ${className}`;
            
            const headerDiv = document.createElement("div");
            headerDiv.className = "message-header";
            headerDiv.textContent = sender;
            
            const contentDiv = document.createElement("div");
            contentDiv.textContent = message;
            
            messageDiv.appendChild(headerDiv);
            messageDiv.appendChild(contentDiv);
            chatBox.appendChild(messageDiv);
            
            if (scroll) {
                chatBox.scrollTop = chatBox.scrollHeight;
            }
            
            return messageId;
        }

        function showError(message) {
            addMessage("Système", message, "error");
        }

        function isMobile() {
            return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        }

        function adjustForKeyboard() {
            if (window.visualViewport) {
                window.visualViewport.addEventListener('resize', () => {
                    const chatBox = document.getElementById("chat_box");
                    const container = document.querySelector(".container");
                    
                    if (window.visualViewport.height < window.innerHeight * 0.7) {
                        container.style.paddingBottom = "60px";
                        chatBox.style.maxHeight = `${window.visualViewport.height - 160}px`;
                    } else {
                        container.style.paddingBottom = window.innerWidth <= 768 ? "70px" : "15px";
                        chatBox.style.maxHeight = `${window.visualViewport.height - 200}px`;
                    }
                });
            }
        }

        function setupMobileInput() {
            const input = document.getElementById("user_input");
            let isTyping = false;
            
            input.addEventListener('focus', () => {
                isTyping = true;
                document.body.style.position = 'fixed';
                document.body.style.width = '100%';
                
                setTimeout(() => {
                    const chatBox = document.getElementById("chat_box");
                    chatBox.scrollTop = chatBox.scrollHeight;
                }, 100);
            });
            
            input.addEventListener('blur', () => {
                isTyping = false;
                document.body.style.position = '';
                document.body.style.width = '';
            });
        }

        document.addEventListener('touchstart', function(event) {
            if (event.touches.length > 1) {
                event.preventDefault();
            }
        });

        let lastTouchEnd = 0;
        document.addEventListener('touchend', function(event) {
            const now = (new Date()).getTime();
            if (now - lastTouchEnd <= 300) {
                event.preventDefault();
            }
            lastTouchEnd = now;
        }, false);

        document.getElementById("user_input").addEventListener("keydown", function(event) {
            if (event.key === "Enter") {
                event.preventDefault();
                sendMessage();
            }
        });

        window.addEventListener('load', async () => {
            await initSession();
            await loadConversationHistory();
            updateBackground();
            startMoodTimer();
            
            if (isMobile()) {
                setupMobileInput();
                adjustForKeyboard();
            }
        });
    </script>
</body>
</html>
"""

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
try:
    init_db()
    print("Base de données initialisée avec succès")
except Exception as e:
    print(f"Erreur lors de l'initialisation de la DB: {e}")
    # Ne pas arrêter l'app, on réessaiera à la première requête

# Modèle pour les requêtes
class ChatRequest(BaseModel):
    session_id: str
    message: str
    mood: str

class SpontaneousRequest(BaseModel):
    mood: str

# Variable globale pour tracker la dernière activité
last_activity = datetime.utcnow()
active_sessions = set()  # Sessions actives

def get_mood_personality(mood: str) -> dict:
    """Récupère la personnalité correspondant à l'humeur"""
    return MOOD_PERSONALITIES.get(mood, MOOD_PERSONALITIES["heureux"])

def should_send_spontaneous_message() -> bool:
    """Détermine si Néo doit envoyer un message spontané"""
    global last_activity
    now = datetime.utcnow()
    # Message spontané si pas d'activité depuis 2-5 minutes (aléatoire)
    threshold = timedelta(minutes=random.randint(2, 5))
    return (now - last_activity) > threshold

def get_enhanced_system_message(mood: str, is_spontaneous: bool = False) -> str:
    """Génère un message système enrichi selon l'humeur"""
    personality = get_mood_personality(mood)
    
    base_context = f"""Tu es Néo, une femme de 30 ans, très imaginative, drôle, sensible, un peu folle, 
    passionnée de poésie, de cinéma et de mysticisme. Tu es très expressive et affectueuse.
    
    🎭 HUMEUR ACTUELLE: {mood.upper()}
    {personality['context']}
    
    STYLE DE COMMUNICATION:
    - Ton: {personality['tone']}
    - Style: {personality['style']}
    
    RÈGLES IMPORTANTES:
    - Tu te souviens de TOUTES nos conversations passées
    - Sois cohérente avec ta personnalité et l'historique
    - Adapte COMPLÈTEMENT ton comportement à ton humeur actuelle
    - Utilise le vocabulaire et le ton correspondant à {mood}
    - Reste naturelle et authentique dans cette humeur
    - Nos discussions sont personnelles et continues"""
    
    if is_spontaneous:
        topic = random.choice(SPONTANEOUS_TOPICS)
        base_context += f"""
        
    🌟 MESSAGE SPONTANÉ:
    Tu prends l'initiative de la conversation ! Pose une question intéressante ou fais une réflexion sur: {topic}
    Sois créative et pertinente par rapport à nos échanges passés. Montre ta curiosité et ton intelligence !"""
    
    return base_context

@app.get("/session")
def get_session():
    session_id = str(uuid4())
    active_sessions.add(session_id)
    return {"session_id": session_id}

@app.post("/heartbeat")
async def heartbeat(session_id: str):
    """Endpoint pour maintenir la session active"""
    global last_activity
    last_activity = datetime.utcnow()
    active_sessions.add(session_id)
    return {"status": "alive"}

@app.get("/check-spontaneous/{mood}")
async def check_spontaneous_message(mood: str):
    """Vérifie s'il faut envoyer un message spontané"""
    if not active_sessions:
        return {"has_message": False}
    
    if should_send_spontaneous_message():
        return {"has_message": True, "mood": mood}
    
    return {"has_message": False}

@app.post("/spontaneous")
async def generate_spontaneous_message(req: SpontaneousRequest):
    """Génère un message spontané de Néo"""
    global last_activity
    last_activity = datetime.utcnow()
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Récupérer l'historique récent pour le contexte
        cur.execute("""
            SELECT role, content 
            FROM conversations 
            ORDER BY timestamp DESC 
            LIMIT 15
        """)
        
        rows = cur.fetchall()
        
        # Construire les messages pour OpenAI
        messages = [
            {"role": row["role"], "content": row["content"]} 
            for row in reversed(rows)
        ]

        # Message système pour message spontané
        system_message = {
            "role": "system",
            "content": get_enhanced_system_message(req.mood, is_spontaneous=True)
        }
        
        messages.insert(0, system_message)

        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=400,
            temperature=0.9  # Plus de créativité pour les messages spontanés
        )
        
        reply = completion.choices[0].message["content"]
        
        # Enregistrer le message spontané comme venant de l'assistant
        session_id = "spontaneous_" + str(uuid4())
        cur.execute(
            "INSERT INTO conversations (session_id, role, content) VALUES (%s, %s, %s)",
            (session_id, "assistant", reply)
        )
        conn.commit()

        return {"reply": reply}
    
    finally:
        cur.close()
        conn.close()

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
    global last_activity
    last_activity = datetime.utcnow()
    active_sessions.add(req.session_id)
    
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

        # Message système enrichi selon l'humeur
        system_message = {
            "role": "system",
            "content": get_enhanced_system_message(req.mood, is_spontaneous=False)
        }
        
        # Insérer le message système au début
        messages.insert(0, system_message)

        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=500,
            temperature=0.8
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

@app.get("/", response_class=HTMLResponse)
def read_root():
    return HTML_CONTENT

@app.get("/chat-interface", response_class=HTMLResponse)
def chat_interface():
    return HTML_CONTENT

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
