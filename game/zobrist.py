from random import getrandbits


class Zobrist:
    def __init__(self):
        # 42 cells on board x 2 player (player id 0, player id 1)
        self.zArray = [[getrandbits(64) for _ in range(2)] for _ in range(42)]
        self.zTurn = [getrandbits(64), getrandbits(64)]  # [player id i]

    def get_hash(self, player, opponent, cur_player):
        """
        Args:
            player: current player bitboard
            opponent: opponent bitboard
            cur_player: ID of player
        """
        h = 0
        other_player = 1 - cur_player

        for col in range(7):
            for row in range(6):
                bit_index = col * 7 + row  # skip filler bit at col*7 + 6
                cell = col * 6 + row       # flat 42-cell index for Zobrist table
                mask = 1 << bit_index

                if player & mask:
                    h ^= self.zArray[cell][cur_player]
                elif opponent & mask:
                    h ^= self.zArray[cell][other_player]

        h ^= self.zTurn[cur_player]
        return h
