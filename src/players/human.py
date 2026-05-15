from .base import Player


class HumanPlayer(Player):
    def get_move(self, game_state) -> None:
        return None  # O CLI trata do input humano
