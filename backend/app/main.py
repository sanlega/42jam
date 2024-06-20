from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Dict
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.llms import OpenAI
from dotenv import load_dotenv
import os
import openai
import random

from .models import Player, Checkpoint
from .game_logic import process_game_logic

app = FastAPI()

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize LangChain Conversation with Buffer Memory and OpenAI LLM
memory = ConversationBufferMemory()
llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
conversation = ConversationChain(memory=memory, llm=llm)

# In-memory store for players
players: Dict[int, Player] = {}

# Define initial game state and checkpoints
initial_health = 100
initial_power = 10
total_days = 7
messages_per_day = 5

checkpoints = [
    Checkpoint(day=1, boss_health=50, boss_power=10),
    Checkpoint(day=3, boss_health=100, boss_power=20),
    Checkpoint(day=7, boss_health=200, boss_power=30)
]

# Helper function to get or create a player
def get_or_create_player(player_id: int) -> Player:
    if player_id not in players:
        players[player_id] = Player(id=player_id, health=initial_health, power=initial_power, current_day=1, messages_sent_today=0)
    return players[player_id]

@app.websocket("/ws/{player_id}")
async def websocket_endpoint(websocket: WebSocket, player_id: int):
    await websocket.accept()
    player = get_or_create_player(player_id)

    try:
        while True:
            data = await websocket.receive_text()
            
            if player.messages_sent_today >= messages_per_day:
                await websocket.send_text("You have reached the message limit for today. Proceed to the next day.")
                continue
            
            response = conversation.predict(input=data, context=player.dict())
            player.messages_sent_today += 1

            response, player = process_game_logic(response, player)

            if player.health <= 0:
                response = "You have died. Game over."
                await websocket.send_text(response)
                break

            await websocket.send_text(response)
            
            if player.messages_sent_today >= messages_per_day:
                for checkpoint in checkpoints:
                    if checkpoint.day == player.current_day:
                        rng = random.randint(0, 10)
                        if player.power >= checkpoint.boss_power and player.health >= checkpoint.boss_health - rng:
                            response = f"Checkpoint {checkpoint.day} completed. Proceed to the next day."
                        else:
                            response = f"You failed to complete checkpoint {checkpoint.day}. Game over."
                            await websocket.send_text(response)
                            break

                player.current_day += 1
                player.messages_sent_today = 0

    except WebSocketDisconnect:
        await websocket.close()

@app.get("/player/{player_id}", response_model=Player)
async def get_player(player_id: int):
    player = get_or_create_player(player_id)
    return player

@app.post("/player/{player_id}/reset")
async def reset_player(player_id: int):
    players[player_id] = Player(id=player_id, health=initial_health, power=initial_power, current_day=1, messages_sent_today=0)
    return {"message": "Player reset successfully"}

