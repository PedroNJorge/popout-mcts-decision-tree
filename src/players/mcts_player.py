from .base import Player
from ..mcts import MCTS


class MCTSPlayer(Player):
    def __init__(self, name: str, player_id: int, simulations: int = 1500):
        super().__init__(name, player_id)
        self.ai = MCTS(max_simulations=simulations)

    def get_move(self, game_state) -> tuple[str, int]:
        # Utiliza o método get_best_move que já tens no mcts.py
        self.ai.clear()
        policy = self.ai.search(game_state)
        if not policy:
            return ('drop', 0)
        msg = "Action probabilities:\n"
        for move, prob in sorted(policy.items(), key=lambda x: -x[1])[:]:
            msg += f"  {move}: {prob:.3f}\n"

        # Return move with highest probability
        best_move = max(policy.items(), key=lambda x: x[1])[0]
        return msg, best_move
