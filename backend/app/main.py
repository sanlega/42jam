from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from openai import OpenAI
import json

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

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()

def check_game_end_conditions(health, current_day):
    if health <= 0:
        return "lose", "Your health has reached 0. You have lost the game."
    elif current_day > MAX_DAYS:
        return "win" if health > 50 else "lose", "You have reached the end of the game." + (" You win!" if health > 50 else " You lose!")
    return None, None

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Check for game end conditions
            status, end_message = check_game_end_conditions(message_data['health'], message_data['currentDay'])
            if status:
                game_state = {
                    "message": end_message,
                    "status": status,
                    "health": message_data['health'],
                    "power": message_data['power'],
                    "currentDay": message_data['currentDay'],
                    "messagesSent": message_data['messagesSent']
                }
                await manager.send_personal_message(json.dumps(game_state), websocket)
                break
            
            # Process the game logic
            completion = openai.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a game master in a fantasy RPG. Guide the player through their adventure, providing challenges, story development, and responses based on their input. Include necessary game logic and calculations. You will always respond only in json format with 3 fields, the message containing the response text telling the story and everything, a health field with a number if the story needs the user to receive damage or something you can modify the health making sure it nevers goes over 100hp and the third field has to be the power field, if the user plays well or finds something while playing that might give him power, you will send the power field increased"
                    },
                    {"role": "user", "content": message_data['message']}
                ]
            )
            reply = completion.choices[0].message.content
            game_state = {
                "message": reply,
                "health": message_data['health'],  # Update based on your logic
                "power": message_data['power'],    # Update based on your logic
                "currentDay": message_data['currentDay'],  # Update based on your logic
                "messagesSent": message_data['messagesSent'] + 1  # Update based on your logic
            }
            await manager.send_personal_message(json.dumps(game_state), websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
