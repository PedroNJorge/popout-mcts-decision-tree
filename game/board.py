ROWS = 6
COLS = 7


class BitBoard:
    def __init__(self):
        """
        Each bitboard is of the format [col0], [col1], ..., [col6],
        where col_i = 6 bits, i = 0(1)6.

        Note: Row0 is the bottom of the board.
        Each col_i is of the format [row0, row1, ..., row5]
        """
        # Board size is 6x7 = 42 bits
        self.player = 0    # Current player's board
        self.opponent = 0  # Current opponent's board

    def __str__(self):
        return f"Player bits: {self.player:042b}"


    def switch_turn(self):
        self.player, self.opponent = self.opponent, self.player

    def get_occupied(self) -> int:
        return self.player | self.opponent

    def get_empty(self) -> int:
        return ~self.get_occupied() & 0x3FFFFFFFFFF  # 42 bit mask

    def win(self) -> bool:
        """Check if player wins"""
        # All directions: horizontal (1), vertical (7),
        # diagonal down-right (6), diagonal up-right (8)
        for shift in [1, 7, 6, 8]:
            m = self.player & (self.player >> shift)
            if m & (m >> (2 * shift)):
                return True
        return False

    def _col_mask(self, col: int) -> int:
        """Create mask for a column"""
        # (1 << 6) - 1 = 111111 (6 bits)
        return ((1 << 6) - 1) << (col * 7)

    def drop_piece(self, col: int) -> bool:
        """Drop piece like in Connect 4"""
        # Find lowest empty row in column
        col_mask = self._col_mask(col)
        occupied = self.get_occupied()
        empty_in_col = (~occupied) & col_mask

        if empty_in_col == 0:
            return False  # Column full

        # Get lowest empty bit (closest to bottom)
        # -x = ~x + 1
        # x = [bits] 1 [0's]
        # -x = [~bits] 1 [0's]
        move_bit = empty_in_col & -empty_in_col
        self.player |= move_bit
        return True
