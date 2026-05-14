from .base import Player
from ..mcts import MCTS


class MCTSPlayer(Player):
    def __init__(self, name: str, player_id: int, simulations: int = 800):
        super().__init__(name, player_id)
        self.ai = MCTS(max_simulations=simulations)

    def get_move(self, game_state) -> tuple[str, int]:
        # Utiliza o método get_best_move que já tens no mcts.py
        return self.ai.get_best_move(game_state)
