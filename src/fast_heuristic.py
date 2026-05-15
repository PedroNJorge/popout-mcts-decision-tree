from .game import PopOut
from .types import Action


class FastHeuristic:
    def __init__(self):
        # Precompute win patterns for each possible position
        self.win_masks = self._precompute_win_masks()

    def _precompute_win_masks(self):
        """Precompute all possible 4-in-a-row masks for faster win detection"""
        masks = []

        # Horizontal: 4 consecutive bits in same row
        for row in range(6):
            for col in range(4):
                mask = 0
                for i in range(4):
                    bit_pos = row + (col + i) * 7
                    mask |= 1 << bit_pos
                masks.append(mask)

        # Vertical: 4 consecutive bits in same column
        for col in range(7):
            for row in range(3):
                mask = 0
                for i in range(4):
                    bit_pos = (row + i) + col * 7
                    mask |= 1 << bit_pos
                masks.append(mask)

        # Diagonal down-right
        for col in range(4):
            for row in range(3):
                mask = 0
                for i in range(4):
                    bit_pos = (row + i) + (col + i) * 7
                    mask |= 1 << bit_pos
                masks.append(mask)

        # Diagonal up-right
        for col in range(4):
            for row in range(3, 6):
                mask = 0
                for i in range(4):
                    bit_pos = (row - i) + (col + i) * 7
                    mask |= 1 << bit_pos
                masks.append(mask)

        return masks

    def _check_win_fast(self, bitboard: int) -> bool:
        """Check win using precomputed masks - very fast"""
        for mask in self.win_masks:
            if (bitboard & mask) == mask:
                return True
        return False

    def is_winning_move(self, state: PopOut, action: Action) -> bool:
        """
        Check if making this move results in a win for the current player.
        Uses bitboard operations without modifying the original state.
        """
        action_type, col = action
        player = state.player
        opponent = state.opponent
        occupied = (player | opponent) | state.filler_mask
        
        if action_type == 'drop':
            col_mask = state._col_mask(col)
            empty_in_col = (~occupied) & col_mask
            
            if empty_in_col == 0:
                return False
            
            # Get lowest empty bit (two's complement trick)
            move_bit = empty_in_col & -empty_in_col
            new_player = player | move_bit
            
            return self._check_win_fast(new_player)
        
        elif action_type == 'pop':
            bottom_bit = 1 << (col * 7)
            
            # Check if bottom piece belongs to current player
            if not (player & bottom_bit):
                return False
            
            # Simulate popout by removing bottom piece and shifting
            new_player, _ = self._simulate_popout(player, opponent, col)
            
            return self._check_win_fast(new_player)
        
        return False

    def _simulate_popout(
        self,
        player: int,
        opponent: int,
        col: int) -> tuple[int, int]:
        """
        Simulate a popout move.

        Returns:
            (new_player, new_opponent)
        """

        bottom_bit = 1 << (col * 7)

        # Remove bottom piece from player
        new_player = player & ~bottom_bit
        new_opponent = opponent

        for row in range(1, 6):
            current_bit = 1 << (col * 7 + row)
            below_bit = 1 << (col * 7 + (row - 1))

            if player & current_bit:
                new_player &= ~current_bit
                new_player |= below_bit

            elif opponent & current_bit:
                new_opponent &= ~current_bit
                new_opponent |= below_bit

        return new_player, new_opponent

    def is_blocking_move(self, state: PopOut, action: Action) -> bool:
        """
        A move is blocking if:
        1. Opponent currently has at least one winning move
        2. After our move, opponent has none
        """

        # Does opponent currently threaten a win?
        opponent_has_threat = False

        # Create perspective where opponent becomes current player
        opp_state = state.copy()
        opp_state.switch_turn()

        for opp_action in opp_state.get_valid_actions():
            if self.is_winning_move(opp_state, opp_action):
                opponent_has_threat = True
                break

        if not opponent_has_threat:
            return False

        # Apply our move
        temp_state = state.copy()

        action_type, col = action

        if action_type == 'drop':
            valid, _ = temp_state.drop_piece(col)
        else:
            valid, _ = temp_state.popout_piece(col)

        if not valid:
            return False

        # After our move, opponent should NOT have winning move
        for opp_action in temp_state.get_valid_actions():
            if self.is_winning_move(temp_state, opp_action):
                return False

        return True
