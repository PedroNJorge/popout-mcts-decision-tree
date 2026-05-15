from .types import Action
from .zobrist import Zobrist
from collections import defaultdict

ROWS = 6
COLS = 7


class PopOut:
    def __init__(self, first_player: int = 0):
        """
        Each bitboard is of the format:
            [col6]0[col5]0[col4]0[col3]0[col2]0[col1]0[col0]

        Note: between each [col_i] and [col_j] there is a filler bit;
              the right-most bit in [col_i] represents row0, and the
              left-most bit represents row5
        """
        # Create filler mask (bit 6 of each column)
        self.filler_mask = 0
        for col in range(7):
            self.filler_mask |= (1 << (col * 7 + 6))  # bit 6 of each column

        # Board size is 6x7 = 42 bits + 6 filler bits
        self.player = 0    # Current player's board
        self.opponent = 0  # Current opponent's board

        self.cur_player = 0  # ID: 0 or 1
        self.zobrist = Zobrist()
        self.state_counts = defaultdict(int)

        self._record_state()  # Record initial state

    def __str__(self):
        display = [['-' for _ in range(COLS)] for _ in range(ROWS)]
        for bit in range(48):
            col = bit // 7
            row = bit % 7
            if row >= ROWS or col >= COLS:
                continue
            if (self.player >> bit) & 1:
                display_row = ROWS - 1 - row
                display[display_row][col] = 'O'
            elif (self.opponent >> bit) & 1:
                display_row = ROWS - 1 - row
                display[display_row][col] = 'X'
        return '\n'.join(' '.join(row) for row in display)

    def copy(self):
        """Create a lightweight copy with only essential attributes."""
        new = PopOut.__new__(PopOut)
        new.filler_mask = self.filler_mask
        new.player = self.player
        new.opponent = self.opponent
        new.cur_player = self.cur_player
        new.zobrist = self.zobrist
        new.state_counts = self.state_counts.copy()
        # new.state_counts = defaultdict(int)
        return new

    def get_hash(self) -> int:
        """Returns Canonical Hash"""
        _, h = self.zobrist.get_hash(self.player, self.opponent, self.cur_player)
        return h

    def get_raw_hash(self) -> int:
        return self.zobrist._compute_hash(self.player, self.opponent, self.cur_player)

    def get_hash_with_mirror(self) -> tuple[bool, int]:
        """Returns (isMirrored, Canonical Hash)"""
        return self.zobrist.get_hash(self.player, self.opponent, self.cur_player)

    def _record_state(self) -> None:
        self.state_counts[self.get_raw_hash()] += 1

    def is_threefold_repetition(self) -> bool:
        return self.state_counts[self.get_raw_hash()] >= 3

    def switch_turn(self) -> None:
        self.player, self.opponent = self.opponent, self.player
        self.cur_player = 1 - self.cur_player

    def get_occupied(self) -> int:
        return (self.player | self.opponent) | self.filler_mask

    def get_empty(self) -> int:
        return ~self.get_occupied() & 0x3FFFFFFFFFF  # 42 bit mask

    def win(self, opponent=False) -> bool:
        """
        Check if player wins.

        Args:
            opponent: Enable win check of opponent instead
        """
        bitboard = self.player
        if opponent:
            bitboard = self.opponent

        # All directions: horizontal (1), vertical (7),
        # diagonal down-right (6), diagonal up-right (8)
        for shift in [1, 7, 6, 8]:
            m = bitboard & (bitboard >> shift)
            if m & (m >> (2 * shift)):
                return True
        return False

    def get_winner(self) -> int | None:
        """Return winner ID (0 or 1) or None if no winner"""
        if self.win(opponent=False):
            return self.cur_player
        if self.win(opponent=True):
            return 1 - self.cur_player
        return None

    def get_valid_actions(self) -> list[Action]:
        """Get all legal actions from current state"""
        actions = []

        for col in range(COLS):
            # Drop: column is valid if it has any empty space
            empty_in_col = (~self.get_occupied()) & self._col_mask(col)
            if empty_in_col != 0:
                actions.append(('drop', col))

            # Pop: valid if bottom bit belongs to current player
            bottom_bit = 1 << (col * 7)
            if self.player & bottom_bit:
                actions.append(('pop', col))
        return actions

    def _col_mask(self, col: int) -> int:
        """Create mask for a column"""
        # (1 << 6) - 1 = 111111 (6 bits)
        return ((1 << 6) - 1) << (col * 7)

    def drop_piece(self, col: int) -> tuple[bool, int | None]:
        """
        Drop piece like in Connect 4

        Args:
            col: column to drop piece

        Returns:
            (ValidMove, WinnerAfterMove)
        """
        # Find lowest empty row in column
        col_mask = self._col_mask(col)
        occupied = self.get_occupied()
        empty_in_col = (~occupied) & col_mask

        if empty_in_col == 0:
            return (False, None)  # Column full

        # Get lowest empty bit (closest to bottom)
        # -x = ~x + 1
        # x = [bits] 1 [0's]
        # -x = [~bits] 1 [0's]
        move_bit = empty_in_col & -empty_in_col
        self.player |= move_bit

        if self.win():
            return (True, self.cur_player)

        self.switch_turn()
        self._record_state()
        return (True, None)

    def popout_piece(self, col: int) -> tuple[bool, int | None]:
        """
        Pop out the player's own piece from the bottom of a column.
        The piece is removed and all pieces above it fall down.

        Args:
            col: Column index (0-6) to pop from

        Returns:
            (ValidMove, WinnerAfterMove)
        """
        # Check if column is empty
        col_mask = self._col_mask(col)
        occupied = self.get_occupied()

        # Check if there's any piece in this column
        if (occupied & col_mask) == 0:
            return (False, None)  # Column is empty

        # Get the bottom-most piece in the column
        bottom_bit = 1 << (col * 7)  # Row 0 is bottom

        # Check if the bottom piece belongs to the current player
        if not (self.player & bottom_bit):
            return (False, None)  # Bottom piece is not owned by current player

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

        if self.win():
            return (True, self.cur_player)
        elif self.win(opponent=True):
            return (True, 1 - self.cur_player)

        self.switch_turn()
        self._record_state()
        return (True, None)

    def get_draw_status(self) -> str | None:
        """
        Return the current draw status

        Returns:
            "BOARD_FULL": Board is full --- player decides
            "THREE_FOLD": Three-fold repetition occured --- either player can claim
            None: No draw available
        """
        if self.get_empty() == 0:
            return "BOARD_FULL"
        elif self.is_threefold_repetition():
            return "THREE_FOLD"
        return None
    
    def get_raw_hash(self) -> int:
        """Returns raw (non-canonical) hash without mirror normalization"""
        return self.zobrist._compute_hash(self.player, self.opponent, self.cur_player)
