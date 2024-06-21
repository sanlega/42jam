from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from openai import OpenAI
import json
import logging

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
        return "win" if health > 50 else "lose", "Has llegado al final del juego." + (" ¡Has ganado!" if health > 50 else " Has perdido.")
    return None, None

def ensure_valid_values(health, power):
    if health is not None:
        health = max(0, min(health, MAX_HEALTH))
    if power is not None:
        power = max(0, min(power, MAX_POWER))
    return health, power

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Ensure health and power are initialized if not present
            health = message_data.get('health', INITIAL_HEALTH)
            power = message_data.get('power', INITIAL_POWER)
            current_day = message_data.get('currentDay', 1)
            messages_sent = message_data.get('messagesSent', 0)
            
            # Add user message to history if it's not the initial start
            if message_data['message'] != 'start':
                manager.add_message_to_history(websocket, "user", message_data['message'])
            else:
                # Send initial prompt
                initial_prompt = {
                    "message": "¡Saludos, aventurero! Bienvenido al reino de Eldoria. Tu viaje comienza en el borde del Bosque Susurrante. ¿Qué deseas hacer primero?",
                    "health": health,
                    "power": power,
                    "currentDay": current_day,
                    "messagesSent": messages_sent
                }
                await manager.send_personal_message(json.dumps(initial_prompt), websocket)
                continue

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
            
            def generate_system_prompt():
                return (
                    f"Eres un maestro del juego en un RPG de fantasía. Guía al jugador a través de su aventura, "
                    f"proporcionando desafíos, desarrollo de la historia y respuestas basadas en su entrada. Incluye la lógica "
                    f"del juego y los cálculos necesarios. El estado actual del juego es: Día {current_day}, Salud {health}, Poder {power}, "
                    f"Mensajes enviados hoy {messages_sent}. Siempre responderás solo en formato JSON con 3 campos: "
                    f"'message' que contiene el texto de la respuesta contando la historia, 'health' con un número, si el numero no varía en cuanto al número de {health}, mantelo como está si la historia "
                    f"necesita que el usuario reciba daño o curación (asegúrate de que la salud nunca supere 100), y 'power' con "
                    f"un número que tienes que tener en cuenta el número actual {power}, que indique cualquier cambio en el poder del jugador. No restablezcas la salud o el poder a menos que se especifique."
                    f"Si se pregunta sobre la salud o el poder actual, responde con el valor actual sin modificarlo. "
                    f"Si el jugador toma decisiones muy malas, puede morir. "
                    f"Es muy importante que uses los valores actuales (health: {health} y power: {power}) de salud y poder para cualquier actualización y no los restablezcas. Si los modificas, en la respuesta formato JSON que devuelvas actualizalos, solo pueden ser 0 si el usuario ha muerto por alguna razón de la trama del juego o por una muy mala decisión. "
                    f"Solo responde en formato JSON. No incluyas ninguna explicación adicional, solo el JSON."
                )

            retries = 3
            while retries > 0:
                retries -= 1
                system_prompt = generate_system_prompt()
                completion = openai.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        *manager.message_history[websocket],
                        {"role": "user", "content": message_data['message']}
                    ]
                )

                # Log GPT response to console and file
                gpt_response = completion.choices[0].message.content
                logging.info(f"GPT Response: {gpt_response}")
                print("GPT Response:", gpt_response)
                
                # Parse the GPT response
                try:
                    reply = json.loads(gpt_response)
                    health = reply.get("health", health)
                    power = reply.get("power", power)
                    health, power = ensure_valid_values(health, power)
                    game_state = {
                        "message": reply["message"],
                        "health": health,
                        "power": power,
                        "currentDay": current_day,
                        "messagesSent": messages_sent + 1
                    }
                    # Add GPT response to history
                    manager.add_message_to_history(websocket, "assistant", reply["message"])
                    break  # Exit retry loop if successful
                except (json.JSONDecodeError, KeyError) as e:
                    logging.error(f"Error processing GPT response: {e}")
                    logging.error(f"GPT Raw Response: {gpt_response}")
                    if retries == 0:
                        game_state = {
                            "message": "Hubo un error procesando la respuesta del maestro del juego.",
                            "health": health,
                            "power": power,
                            "currentDay": current_day,
                            "messagesSent": messages_sent
                        }

            await manager.send_personal_message(json.dumps(game_state), websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
