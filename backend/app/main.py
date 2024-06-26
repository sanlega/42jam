from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from openai import OpenAI
import json
import logging
import asyncio

# Initialize FastAPI app
app = FastAPI()

# Load environment variables
load_dotenv()
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_DAYS = 5
INITIAL_HEALTH = 100
INITIAL_POWER = 10
MAX_HEALTH = 100
MAX_POWER = 100

# Setup logging
logging.basicConfig(filename="game_log.log", level=logging.INFO, 
                    format="%(asctime)s - %(levelname)s - %(message)s")

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.message_history = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.message_history[websocket] = []
        logging.info(f"New connection: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        if websocket in self.message_history:
            del self.message_history[websocket]
        logging.info(f"Connection closed: {websocket.client}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    def add_message_to_history(self, websocket: WebSocket, role: str, content: str):
        if websocket in self.message_history:
            self.message_history[websocket].append({"role": role, "content": content})
            logging.info(f"Message added to history: {role} - {content}")

manager = ConnectionManager()

def check_game_end_conditions(health, current_day):
    if health is None or current_day is None:
        return None, None
    if health <= 0:
        return "lose", "Tu salud ha llegado a 0. Has perdido el juego."
    elif current_day > MAX_DAYS:
        return "win" if health > 50 else "lose", "Has llegado al final del juego." + (" ¡Ganas!" if health > 50 else " Pierdes.")
    return None, None

def ensure_valid_values(health, power):
    if health is not None:
        health = max(0, min(health, MAX_HEALTH))
    if power is not None:
        power = max(0, min(power, MAX_POWER))
    return health, power

def extract_json(response_text):
    try:
        json_start = response_text.index('{')
        json_end = response_text.rindex('}') + 1
        json_str = response_text[json_start:json_end]
        return json.loads(json_str)
    except (ValueError, json.JSONDecodeError) as e:
        logging.error(f"Error extracting JSON: {e}")
        return None

async def handle_gpt_response(system_prompt, user_message, message_history, websocket, retries=3):
    default_response = {
        "message": "No se pudo procesar tu solicitud en este momento. Intenta nuevamente.",
        "health": INITIAL_HEALTH,
        "power": INITIAL_POWER
    }

    while retries > 0:
        try:
            completion = openai.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    *message_history,
                    {"role": "user", "content": user_message}
                ]
            )
            
            gpt_response = completion.choices[0].message.content
            logging.info(f"GPT Response: {gpt_response}")
            print("GPT Response:", gpt_response)
            
            try:
                return json.loads(gpt_response)
            except json.JSONDecodeError:
                json_str = extract_json(gpt_response)
                if json_str:
                    return json_str
                else:
                    system_prompt += (
                        f" Recuerda, debes responder solo en formato JSON: {{\"message\": \"...\", \"health\": {message_history[-1].get('health', INITIAL_HEALTH)}, \"power\": {message_history[-1].get('power', INITIAL_POWER)}}}. POR FAVOR, usa este formato de JSON"
                    )
                    message_history.append({"role": "system", "content": system_prompt})
                    retries -= 1
        except Exception as e:
            logging.error(f"Error during GPT response handling: {e}")
            retries -= 1

    logging.warning("Maximum retries exceeded. Returning default response.")
    return default_response

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Initial prompt to start the game
        initial_prompt = (
            "¡Saludos, aventurero! Bienvenido al 42º reino. Tu viaje comienza en el borde del Bosque Trepidante cerca de un Poblado. ¿Qué deseas hacer primero?"
        )
        manager.add_message_to_history(websocket, "assistant", initial_prompt)
        await manager.send_personal_message(json.dumps({"message": initial_prompt}), websocket)

        # Keep-alive task
        async def keep_alive():
            while True:
                await asyncio.sleep(30)  # Send a ping every 30 seconds
                try:
                    await websocket.send_text(json.dumps({"ping": "keep-alive"}))
                except WebSocketDisconnect:
                    break

        keep_alive_task = asyncio.create_task(keep_alive())

        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Ensure health and power are initialized if not present
            health = message_data.get('health', INITIAL_HEALTH)
            power = message_data.get('power', INITIAL_POWER)
            current_day = message_data.get('currentDay', 1)
            messages_sent = message_data.get('messagesSent', 0)
            
            # Check for game end conditions
            status, end_message = check_game_end_conditions(health, current_day)
            if status:
                game_state = {
                    "message": end_message,
                    "status": status,
                    "health": health,
                    "power": power,
                    "currentDay": current_day,
                    "messagesSent": messages_sent
                }
                await manager.send_personal_message(json.dumps(game_state), websocket)
                logging.info(f"Game end condition met: {end_message}")
                break
            
            # Add user message to history
            manager.add_message_to_history(websocket, "user", message_data['message'])

            # System prompt
            system_prompt = (
                f"Eres un maestro del juego en un RPG de fantasía que responderá en formato JSON. Guía al jugador a través de su aventura, "
                f"proporcionando desafíos, desarrollo de la historia y respuestas basadas en su entrada. Incluye la lógica "
                f"del juego y los cálculos necesarios. El estado actual del juego es: Día {current_day}, Salud {health}, Poder {power}, "
                f"Mensajes enviados hoy {messages_sent}. Debes responder solo en el siguiente formato JSON: "
                f"{{\"message\": \"...\", \"health\": {health}, \"power\": {power}}}. No restablezcas la salud o el poder a menos que se especifique."
                f"Si se pregunta sobre la salud o el poder actual, responde con el valor actual sin modificarlo."
                f"Si el jugador toma decisiones muy malas, puede morir."
                f"Es muy importante que uses los valores actuales de salud {health} y poder {power} para cualquier actualización. "
                f"Si no puedes proporcionar una respuesta clara, indica 'error' en el campo de mensaje. Y recuerda el formato JSON mencionado"
            )

            try:
                reply = await handle_gpt_response(system_prompt, message_data['message'], manager.message_history[websocket], websocket)
            except ValueError:
                reply = {
                    "message": "Hubo un error procesando la respuesta del maestro del juego.",
                    "status": "error",
                    "health": health,
                    "power": power,
                    "currentDay": current_day,
                    "messagesSent": messages_sent
                }
            
            if reply.get("health") is not None and reply.get("power") is not None:
                health = reply["health"]
                power = reply["power"]
                health, power = ensure_valid_values(health, power)
            else:
                # If response is not JSON or lacks health/power, treat it as a plain message
                reply = {"message": reply.get("message", gpt_response), "health": health, "power": power}

            game_state = {
                "message": reply["message"],
                "health": health,
                "power": power,
                "currentDay": current_day,
                "messagesSent": messages_sent + 1
            }
            # Add GPT response to history
            manager.add_message_to_history(websocket, "assistant", reply["message"])

            await manager.send_personal_message(json.dumps(game_state), websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        keep_alive_task.cancel()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
