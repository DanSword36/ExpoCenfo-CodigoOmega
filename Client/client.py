# ~/voz-orientador-client/client.py
import asyncio
import websockets
import wave
import io
import base64
import os
import json
import sounddevice as sd
import numpy as np
import simpleaudio as sa
from dotenv import load_dotenv

load_dotenv()
WS_URL = os.getenv("WS_URL", "wss://counselor.neomind.co.cr/ws?token=a07933d5d5a65193b39d8bfbbe46863b827854d3c1fa136d3f840f63618400af")
RECORD_SECONDS = int(os.getenv("RECORD_SECONDS", "4"))
SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", "16000"))

print("TEST  " + os.getenv("WS_URL"))

def record_wav_bytes(seconds: int = RECORD_SECONDS, sample_rate: int = SAMPLE_RATE) -> bytes:
    print(f"🎙️ Grabando {seconds}s... (habla ahora)")
    audio = sd.rec(int(seconds * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
    sd.wait()
    # empaquetar WAV (PCM16 mono)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())
    return buf.getvalue()

def b64_audio(wav_bytes: bytes) -> str:
    return base64.b64encode(wav_bytes).decode("utf-8")

def play_wav_bytes(wav_bytes: bytes):
    # simpleaudio puede reproducir desde bytes si extraemos PCM
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16)
        play_obj = sa.play_buffer(audio, num_channels=wf.getnchannels(), bytes_per_sample=2, sample_rate=wf.getframerate())
        play_obj.wait_done()

async def main():
    print(f"Conectando a {WS_URL} ...")
    async with websockets.connect(WS_URL, max_size=20*1024*1024) as ws:
        print("✅ Conectado. Esperando mensaje inicial del servidor...\n")
        # El servidor envía un mensaje inicial (texto + audio)
        init = await ws.recv()
        init_msg = json.loads(init)
        if "reply_text" in init_msg:
            print(f"🧠 Servidor: {init_msg['reply_text']}\n")
        if "audio_b64" in init_msg:
            play_wav_bytes(base64.b64decode(init_msg["audio_b64"]))

        print("Instrucciones:")
        print("- Presiona ENTER para hablar (graba 4s por defecto).")
        print("- Escribe 'reindex' y ENTER para reconstruir índice de PDFs en el servidor.")
        print("- Escribe 'salir' para terminar.\n")

        while True:
            cmd = input("ENTER = hablar | reindex | salir > ").strip().lower()
            if cmd == "salir":
                # envia mensaje de audio diciendo salir (opcional) o corta aquí:
                # Enviaremos un pequeño audio fake que diga 'salir' no es necesario; mejor texto no soportado.
                # En su lugar, mandamos una última grabación y decimos 'salir' con la voz.
                print("Adiós 👋")
                break
            if cmd == "reindex":
                await ws.send(json.dumps({"type":"command","value":"reindex"}))
                msg = json.loads(await ws.recv())
                print(f"🧠 Servidor: {msg.get('reply_text','')}\n")
                if "audio_b64" in msg:
                    play_wav_bytes(base64.b64decode(msg["audio_b64"]))
                continue

            # grabar audio y enviar
            wav_bytes = record_wav_bytes(RECORD_SECONDS, SAMPLE_RATE)
            payload = {"type":"audio","audio_b64": b64_audio(wav_bytes)}
            await ws.send(json.dumps(payload))

            # recibir respuesta
            msg_raw = await ws.recv()
            msg = json.loads(msg_raw)

            transcript = msg.get("transcript","")
            reply = msg.get("reply_text","")
            print(f"🗣️  Tú dijiste: {transcript}")
            print(f"🧠 Servidor: {reply}\n")

            if "audio_b64" in msg:
                play_wav_bytes(base64.b64decode(msg["audio_b64"]))
            if msg.get("done"):
                print("Sesión finalizada por el servidor.")
                break

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.")
