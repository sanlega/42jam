from pydantic import BaseModel

class Player(BaseModel):
    id: int
    health: int
    power: int
    current_day: int
    messages_sent_today: int

class Checkpoint(BaseModel):
    day: int
    boss_health: int
    boss_power: int

