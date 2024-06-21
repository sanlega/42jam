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
        return "lose", "Your health has reached 0. You have lost the game."
    elif current_day > MAX_DAYS:
        return "win" if health > 50 else "lose", "You have reached the end of the game." + (" You win!" if health > 50 else " You lose!")
    return None, None

def ensure_valid_values(health, power):
    if health is not None:
        health = max(0, min(health, MAX_HEALTH))
    if power is not None:
        power = max(0, min(power, MAX_POWER))
    return health, power

# ... existing imports and setup ...

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
                    "message": "Greetings, adventurer! Welcome to the realm of Eldoria. Your journey begins at the edge of the Whispering Woods. What do you wish to do first?",
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
            
            # Process the game logic
            system_prompt = (
                f"You are a game master in a fantasy RPG. Guide the player through their adventure, "
                f"providing challenges, story development, and responses based on their input. Include necessary "
                f"game logic and calculations. The current game state is: Day {current_day}, Health {health}, Power {power}, "
                f"Messages sent today {messages_sent}. You will always respond only in JSON format with 3 fields: "
                f"'message' containing the response text telling the story, 'health' with a number if the story "
                f"needs the user to receive damage or healing (ensure health never goes over 100), and 'power' with "
                f"a number indicating any change in the player's power. Do not reset health or power unless specified."
                f"If asked about the current health or power, respond with the current value without modifying it."
            )

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
            except (json.JSONDecodeError, KeyError) as e:
                logging.error(f"Error processing GPT response: {e}")
                game_state = {
                    "message": "Oh oh... El maestro ha perdido la conexión espiritual",
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
