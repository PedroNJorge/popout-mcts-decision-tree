from abc import ABC, abstractmethod
from ..game import PopOut

class Player(ABC):
    def __init__(self, name: str, player_id: int):
        self.name = name
        self.player_id = player_id

    @abstractmethod
    def get_move(self, game_state: PopOut) -> tuple[str, int] | None:
        """Retorna (tipo_movimento, coluna) ou None se for humano."""
        pass