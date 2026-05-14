import random
from .base import Player
from ..game import PopOut, COLS

class RandomPlayer(Player):
    def get_move(self, game_state: PopOut) -> tuple[str, int]:
        moves = []
        for col in range(COLS):
            # Verifica se pode fazer Drop (coluna não cheia)
            if ((~game_state.get_occupied()) & game_state._col_mask(col)) != 0:
                moves.append(('drop', col))
            # Verifica se pode fazer Pop (se a peça no fundo for sua)
            bottom_bit = 1 << (col * 7)
            if game_state.player & bottom_bit:
                moves.append(('pop', col))
        
        return random.choice(moves) if moves else ('drop', 0)
