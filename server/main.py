import os, io, base64, json, wave, time, pdfplumber, pyttsx3
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import parse_qs
from dotenv import load_dotenv
from vosk import Model, KaldiRecognizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

# --- Config ---
load_dotenv()
WS_TOKEN = os.getenv("WS_TOKEN", "a07933d5d5a65193b39d8bfbbe46863b827854d3c1fa136d3f840f63618400af")
CARRERAS_DIR = os.getenv("CARRERAS_DIR", "./data/carreras")
VOSK_MODEL_DIR = os.getenv("VOSK_MODEL_DIR", "./data/models/vosk-model-small-es-0.42")
BIND_HOST = os.getenv("BIND_HOST", "0.0.0.0")
BIND_PORT = int(os.getenv("BIND_PORT", "8000"))
SAMPLE_RATE = 16000

# --- FastAPI ---
app = FastAPI(title="Voz Orientador – VPS")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

# --- Vosk STT ---
if not os.path.isdir(VOSK_MODEL_DIR):
    raise RuntimeError(f"Modelo Vosk no encontrado en {VOSK_MODEL_DIR}")
vosk_model = Model(VOSK_MODEL_DIR)

def transcribe_wav_bytes(wav_bytes: bytes) -> str:
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        if wf.getnchannels() != 1: raise ValueError("Se espera audio mono.")
        if wf.getframerate() != SAMPLE_RATE: raise ValueError(f"Se espera {SAMPLE_RATE} Hz.")
        rec = KaldiRecognizer(vosk_model, wf.getframerate())
        rec.SetWords(False)
        while True:
            data = wf.readframes(4000)
            if len(data) == 0: break
            rec.AcceptWaveform(data)
        result = json.loads(rec.FinalResult())
        return result.get("text", "").strip()

# --- pyttsx3 TTS ---
tts_engine = pyttsx3.init()

# Listar todas las voces disponibles (opcional, útil para debug)
# for i, v in enumerate(tts_engine.getProperty('voices')):
#     print(f"{i}: {v.id} - {v.name} - {v.languages}")

# Intentar seleccionar la mejor voz en español
selected = False
for v in tts_engine.getProperty('voices'):
    if any(lang in v.id.lower() or lang in v.name.lower() for lang in ["spanish", "es"]):
        tts_engine.setProperty("voice", v.id)
        selected = True
        break

# Si no se encuentra ninguna, usar la voz por defecto
if not selected:
    print("[TTS] No se encontró voz en español, se usará la voz por defecto.")

# Ajustes opcionales
tts_engine.setProperty("rate", 165)      # velocidad de la voz
tts_engine.setProperty("volume", 0.9)    # volumen 0.0 a 1.0

def tts_to_wav_bytes(text: str) -> bytes:
    tmp = f"/tmp/tts_{int(time.time()*1000)}.wav"
    tts_engine.save_to_file(text, tmp)
    tts_engine.runAndWait()
    with open(tmp, "rb") as f: data = f.read()
    try: os.remove(tmp)
    except Exception: pass
    return data

def pack_audio_b64(wav_bytes: bytes) -> str: return base64.b64encode(wav_bytes).decode("utf-8")
def unpack_audio_b64(b64: str) -> bytes: return base64.b64decode(b64)

# --- PDF Index ---
class PDFIndex:
    def __init__(self, folder: str):
        self.folder = folder
        self.docs: List[Dict[str, Any]] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf = None

    def build(self):
        self.docs.clear()
        texts = []
        idx = 0
        for root, _, files in os.walk(self.folder):
            for fn in files:
                if not fn.lower().endswith(".pdf"): continue
                path = os.path.join(root, fn)
                try:
                    with pdfplumber.open(path) as pdf:
                        for pnum, page in enumerate(pdf.pages):
                            txt = page.extract_text() or ""
                            if not txt.strip(): continue
                            self.docs.append({"id": idx, "file": fn, "page": pnum+1, "path": path, "text": txt.strip()})
                            texts.append(txt)
                            idx += 1
                except Exception as e:
                    print(f"[PDFIndex] Error leyendo {path}: {e}")
        if not texts: 
            self.vectorizer = None
            self.tfidf = None
            print("[PDFIndex] Sin textos indexados.")
            return
        self.vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1,2), max_df=0.9, min_df=1)
        self.tfidf = self.vectorizer.fit_transform(texts)
        print(f"[PDFIndex] Indexadas {len(self.docs)} páginas.")

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.vectorizer or self.tfidf is None or not query.strip(): return []
        q_vec = self.vectorizer.transform([query])
        sims = linear_kernel(q_vec, self.tfidf).flatten()
        top_idx = sims.argsort()[::-1][:top_k]
        out = []
        for i in top_idx:
            score = float(sims[i])
            if score <= 0: continue
            out.append({**self.docs[i], "score": round(score,4)})
        return out

pdfindex = PDFIndex(CARRERAS_DIR)
pdfindex.build()

# --- Categorías y preguntas ---
CATEGORIAS = ["software","infraestructura","ciberseguridad","datos_ai","web_ux","qa_testing"]
PREGUNTAS = [
    ("¿Te gusta programar y construir aplicaciones o APIs?", "software"),
    ("¿Te atrae configurar redes, servidores o servicios en la nube?", "infraestructura"),
    ("¿Te interesan la ciberseguridad, el hacking ético y el análisis de riesgos?", "ciberseguridad"),
    ("¿Te entusiasma analizar datos, hacer dashboards o modelos de IA/ML?", "datos_ai"),
    ("¿Te llama el diseño de interfaces, UX o el desarrollo web front-end?", "web_ux"),
    ("¿Te gusta probar software, automatizar pruebas y asegurar calidad?", "qa_testing")
]
YES_TOKENS = {"si","sí","claro","me gusta","me encanta","mucho","por supuesto","sí, me gusta"}
NO_TOKENS  = {"no","no mucho","poco","no me gusta"}

def score_answer(text: str) -> bool:
    t = text.lower()
    if any(tok in t for tok in YES_TOKENS): return True
    if any(tok in t for tok in NO_TOKENS): return False
    return False

def top_recommendations(scores: Dict[str,int], n:int=2) -> List[str]:
    if not scores: return []
    sorted_items = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top = [k for k,v in sorted_items if v == sorted_items[0][1]]
    return top[:max(n, len(top))]

def query_for_category(cat: str) -> str:
    mapping = {
        "software":"software programación ingeniería",
        "infraestructura":"redes infraestructura cloud servidores tecnologías de información",
        "ciberseguridad":"ciberseguridad seguridad informática ethical hacker",
        "datos_ai":"analítica datos inteligencia artificial machine learning",
        "web_ux":"desarrollo web diseño UX UI front-end",
        "qa_testing":"automatización pruebas QA testing"
    }
    return mapping.get(cat, cat)

class SessionState:
    def __init__(self):
        self.mode: Optional[str] = None
        self.interview_idx: int = 0
        self.scores: Dict[str,int] = {c:0 for c in CATEGORIAS}

def make_msg(reply_text:str, transcript:str="", wav_bytes:Optional[bytes]=None, done:bool=False) -> Dict[str,Any]:
    msg = {"reply_text":reply_text,"transcript":transcript,"done":done}
    if wav_bytes: msg["audio_b64"]=pack_audio_b64(wav_bytes)
    return msg

WELCOME = (
    "Hola, soy tu asistente de orientación tecnológica. "
    "Di 'buscar' para pedir información de una carrera, o di 'entrevista' para que te haga preguntas y recomendarte opciones. "
    "Cuando quieras terminar, di 'salir'."
)

@app.get("/")
def index(): return HTMLResponse("<h3>Voz Orientador – WebSocket en /ws</h3>")

# --- WebSocket ---
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    
    query_params = parse_qs(ws.scope['query_string'].decode())
    token = query_params.get("token", [None])[0]
    if token != WS_TOKEN:
        await ws.send_json(make_msg("Token inválido. Conexión cerrada."))
        await ws.close()
        return

    state = SessionState()
    await ws.send_json(make_msg(WELCOME, "", tts_to_wav_bytes(WELCOME)))

    try:
        while True:
            data = await ws.receive_text()
            payload = json.loads(data)

            if payload.get("type") == "command":
                if payload.get("value")=="reindex":
                    pdfindex.build()
                    text="Índice reconstruido. Puedes continuar."
                    await ws.send_json(make_msg(text,"",tts_to_wav_bytes(text)))
                continue

            if payload.get("type") != "audio": continue
            wav_bytes = unpack_audio_b64(payload.get("audio_b64",""))
            transcript = transcribe_wav_bytes(wav_bytes)
            print(f"[STT] {transcript}")

            if "salir" in transcript.lower():
                bye = "Gracias por usar el sistema. ¡Hasta luego!"
                await ws.send_json(make_msg(bye, transcript, tts_to_wav_bytes(bye), done=True))
                await ws.close()
                return

            # --- Lógica de entrevista y búsqueda ---
            if state.mode is None:
                if "entrevista" in transcript.lower():
                    state.mode="entrevista"
                    q = PREGUNTAS[state.interview_idx][0]
                    audio = tts_to_wav_bytes("Comencemos la entrevista. "+q)
                    await ws.send_json(make_msg(q, transcript, audio))
                    continue
                if "buscar" in transcript.lower():
                    state.mode="buscar"
                    prompt="Dime el nombre o el área de la carrera que te interesa."
                    await ws.send_json(make_msg(prompt, transcript, tts_to_wav_bytes(prompt)))
                    continue
                await ws.send_json(make_msg(WELCOME, transcript, tts_to_wav_bytes("No te entendí. "+WELCOME)))
                continue

            # --- Entrevista ---
            if state.mode=="entrevista":
                cat = PREGUNTAS[state.interview_idx][1]
                if score_answer(transcript): state.scores[cat]+=1
                state.interview_idx+=1
                if state.interview_idx>=len(PREGUNTAS):
                    recs = top_recommendations(state.scores, n=3)
                    if not recs:
                        final_text = "No logré perfilarte bien. Puedes decir 'buscar' y pedirme una carrera específica."
                        await ws.send_json(make_msg(final_text, transcript, tts_to_wav_bytes(final_text)))
                        state=SessionState()
                        continue
                    areas_human = ", ".join({
                        "software":"ingeniería de software",
                        "infraestructura":"infraestructura y redes",
                        "ciberseguridad":"ciberseguridad",
                        "datos_ai":"analítica de datos e inteligencia artificial",
                        "web_ux":"desarrollo y diseño web",
                        "qa_testing":"automatización de pruebas"
                    }[r] for r in recs)
                    final_text=f"Según tus respuestas, te recomiendo explorar: {areas_human}. Te compartiré opciones basadas en tus PDFs."
                    chunks=[final_text]
                    for r in recs:
                        query=query_for_category(r)
                        hits=pdfindex.search(query, top_k=2)
                        if hits:
                            for h in hits: chunks.append(f"- {h['file']} (página {h['page']})")
                        else: chunks.append(f"- No encontré PDFs locales para {r}.")
                    speak = final_text
                    await ws.send_json(make_msg("\n".join(chunks), transcript, tts_to_wav_bytes(speak)))
                    state=SessionState()
                    continue
                else:
                    q = PREGUNTAS[state.interview_idx][0]
                    await ws.send_json(make_msg(q, transcript, tts_to_wav_bytes(q)))
                    continue

            # --- Búsqueda ---
            if state.mode=="buscar":
                query = transcript if transcript else "tecnología"
                hits = pdfindex.search(query, top_k=5)
                if hits:
                    lines = [f"Encontré {len(hits)} resultado(s)."]
                    speak = f"Encontré {len(hits)} resultados relevantes."
                    for h in hits: lines.append(f"- {h['file']} (página {h['page']})")
                    await ws.send_json(make_msg("\n".join(lines), transcript, tts_to_wav_bytes(speak)))
                else:
                    msg = "No encontré coincidencias en los PDFs locales para esa búsqueda."
                    await ws.send_json(make_msg(msg, transcript, tts_to_wav_bytes(msg)))
                continue

    except WebSocketDisconnect:
        print("[WS] Cliente desconectado.")
    except Exception as e:
        err = f"Error en servidor: {e}"
        try:
            await ws.send_json(make_msg(err, "", tts_to_wav_bytes("Ocurrió un error en el servidor."), done=True))
            await ws.close()
        except Exception: pass
        print(err)

if __name__=="__main__":
    import uvicorn
    uvicorn.run("main:app", host=BIND_HOST, port=BIND_PORT, reload=False)
