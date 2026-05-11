from random import getrandbits


class Zobrist:
    def __init__(self):
        # 42 cells on board x 2 player (player id 0, player id 1)
        self.zArray = [[getrandbits(64) for _ in range(2)] for _ in range(42)]
        self.zTurn = [getrandbits(64), getrandbits(64)]  # [player id i]

    def _compute_hash(self, player, opponent, cur_player):
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

    def _mirror(self, bitboard: int):
        """Reflect columns: col 0 <-> col 6, col 1 <-> col 5, col 2 <-> col 4, col 3 stays"""
        result = 0
        for col in range(7):
            mirrored_col = 6 - col
            # Extract col's 6 bits and place them at mirrored_col's position
            col_bits = (bitboard >> (col * 7)) & 0x3F  # 0x3F = 0b111111 (6 bits)
            result |= col_bits << (mirrored_col * 7)
        return result

    def get_hash(self, player, opponent, cur_player):
        """
        Returns canonical hash
        """
        h_normal = self._compute_hash(player, opponent, cur_player)
        h_mirror = self._compute_hash(self._mirror(player), self._mirror(opponent), cur_player)
        return min(h_normal, h_mirror)
