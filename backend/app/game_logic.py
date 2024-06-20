from .models import Player
import random

def process_game_logic(response: str, player: Player) -> (str, Player):
    if "fight" in response:
        rng = random.randint(0, 10)
        player.power += rng
        player.health -= rng
        response += f" Your power increased by {rng} and health decreased by {rng}."
    
    return response, player

