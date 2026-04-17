ROWS = 6
COLS = 7


class BitBoard:
    def __init__(self):
        """
        Each bitboard is of the format [col0], [col1], ..., [col6],
        where col_i = 6 bits, i = 0(1)6.

        Note: Row0 is the bottom of the board.
        Each col_i is of the format [row0, row1, ..., row5]

        Between each col_i there is a filler bit
        """
        # Create filler mask (bit 6 of each column)
        self.filler_mask = 0
        for col in range(7):
            self.filler_mask |= (1 << (col * 7 + 6))  # bit 6 of each column

        # Board size is 6x7 = 42 bits
        self.player = 0    # Current player's board
        self.opponent = 0  # Current opponent's board

    def __str__(self):
        return f"Player bits: {self.player:042b}"

    def switch_turn(self):
        self.player, self.opponent = self.opponent, self.player

    def get_occupied(self) -> int:
        return (self.player | self.opponent) | self.filler_mask

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

    def popout_piece(self, col: int) -> bool:
        """
        Pop out the player's own piece from the bottom of a column.
        The piece is removed and all pieces above it fall down.

        Args:
            col: Column index (0-6) to pop from

        Returns:
            bool: True if successful, False if invalid move
        """
        # Check if column is empty
        col_mask = self._col_mask(col)
        occupied = self.get_occupied()

        # Check if there's any piece in this column
        if (occupied & col_mask) == 0:
            return False  # Column is empty

        # Get the bottom-most piece in the column
        bottom_bit = 1 << (col * 7)  # Row 0 is bottom

        # Check if the bottom piece belongs to the current player
        if not (self.player & bottom_bit):
            return False  # Bottom piece is not owned by current player

        # Remove the bottom piece
        self.player &= ~bottom_bit

        # Shift all pieces above down by one position
        # For each row from row 1 to row 5, move the piece down one row
        for row in range(1, 6):  # Start from row 1 (second from bottom)
            current_bit = 1 << (col * 7 + row)
            below_bit = 1 << (col * 7 + (row - 1))

            # Check if there's a piece in current position
            if self.player & current_bit:
                # Move player's piece down
                self.player &= ~current_bit
                self.player |= below_bit
            elif self.opponent & current_bit:
                # Move opponent's piece down
                self.opponent &= ~current_bit
                self.opponent |= below_bit

        return True

    def can_draw(self) -> bool:
        """
        Checks if board is full and if so the player can draw the game.
        """
        if self.get_empty() == 0:
            return True
        return False
