from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import openai
import json

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize FastAPI app
app = FastAPI()

# Allow all CORS requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Sample player data, usually this would be more dynamic
player_info = {
    "health": 100,
    "power": 50,
    "message": ""
}

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection accepted")

    try:
        while True:
            try:
                # Receive message from the front end
                data = await websocket.receive_text()
                print(f"Received data: {data}")

                if not data:  # Check if data is empty
                    print("Received empty data string.")
                    continue  # Skip processing if data is empty

                try:
                    user_input = json.loads(data)
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")
                    await websocket.send_json({"error": "Invalid JSON format"})
                    continue  # Skip processing if JSON is malformed

                message = user_input.get("message")
                if not message:
                    print("No message provided in the input")
                    await websocket.send_json({"error": "No message provided"})
                    continue  # Skip processing if message is empty

                # Generate a response using OpenAI GPT-4
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are in a dark cave."},
                        {"role": "user", "content": message}
                    ]
                )
                reply = response['choices'][0]['message']['content']

                # Update player's message from GPT-4 response
                player_info["message"] = reply

                # Send updated player info back to the client
                await websocket.send_json(player_info)
            except WebSocketDisconnect:
                print("Client disconnected")
                break
    except Exception as e:
        print(f"Unhandled exception: {e}")

# Run this using Uvicorn command: uvicorn main:app --reload
