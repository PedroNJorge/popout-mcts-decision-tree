import math
import random
from .game import PopOut, COLS
from .zobrist import Zobrist
from .tt import TranspositionTable, TTEntry

EXPLORATION_CONSTANT = 1.414  # sqrt(2)


class MCTSNode:
    __slots__ = ['state_hash', 'parent', 'children', 'move', 'depth',
                 'untried_actions', 'game_state', 'tt']

    def __init__(self, state_hash: int, parent: "MCTSNode" | None = None,
                 move: tuple[str, int] | None = None, depth: int = 0,
                 tt: TranspositionTable | None = None):
        self.state_hash = state_hash
        self.parent = parent
        self.children: dict[tuple[str, int], "MCTSNode"] = {}
        self.move = move  # (type, col) where type is 'drop' or 'pop'
        self.depth = depth
        self.untried_actions: list[tuple[str, int]] | None = None
        self.game_state: PopOut | None = None  # Cached for simulation
        self.tt: TranspositionTable = tt

    def get_entry(self) -> TTEntry:
        """Get or create TT entry for this node"""
        entry = self.tt.get(self.state_hash)
        if entry is None:
            self.tt.put(self.state_hash)
            entry = self.tt.get(self.state_hash)
        return entry

    @property
    def visits(self) -> int:
        entry = self.get_entry()
        return entry.visits

    @property
    def value(self) -> float:
        entry = self.get_entry()
        return entry.value

    def get_eval(self) -> float:
        """Get node evalutation U(n) / N(n)"""
        entry = self.get_entry()
        return entry.get_eval()

    def is_fully_expanded(self, game_state: PopOut) -> bool:
        """Check if all legal actions have been expanded"""
        if self.untried_actions is None:
            # Get all valid moves (drop + popout)
            self.untried_actions = self._get_valid_moves(game_state)

        return len(self.untried_actions) == 0

    @staticmethod
    def _get_valid_moves(game_state: PopOut) -> list[tuple[str, int]] | None:
        """Get all legal moves from current state"""
        moves = []

        for col in range(COLS):
            # Drop: column is valid if it has any empty space
            empty_in_col = (~game_state.get_occupied()) & game_state._col_mask(col)
            if empty_in_col != 0:
                moves.append(('drop', col))

            # Pop: valid if bottom bit belongs to current player
            bottom_bit = 1 << (col * 7)
            if game_state.player & bottom_bit:
                moves.append(('pop', col))

        random.shuffle(moves)  # Shuffle for randomness
        return moves

    def expand(self, game_state: PopOut) -> tuple['MCTSNode', PopOut]:
        """Expand one untried action and return new node and state"""
        if self.untried_actions is None:
            self.untried_actions = self._get_valid_moves(game_state)

        if not self.untried_actions:
            raise ValueError("No untried actions available")

        # Pick and remove one action
        move = self.untried_actions.pop()
        move_type, col = move

        # Create new state by applying move
        new_state = game_state.copy()
        if move_type == 'drop':
            valid, _ = new_state.drop_piece(col)
        else:  # pop
            valid, _ = new_state.popout_piece(col)

        if not valid:
            # Should not happen if move was valid
            return self.expand(game_state)

        # Get hash of new state
        new_hash = new_state.get_hash()

        # Ensure TT entry exists
        entry = self.tt.get(new_hash)
        if entry is None:
            self.tt.put(new_hash)

        # Get or create child node
        child_node = MCTSNode(
            state_hash=new_hash,
            parent=self,
            move=move,
            depth=self.depth + 1,
            tt=self.tt
        )
        child_node.game_state = new_state

        # Link child
        self.children[move] = child_node

        return child_node, new_state


class MCTS:
    """Monte Carlo Tree Search with Transposition Table"""

    def __init__(self, exploration_constant: float = EXPLORATION_CONSTANT,
                 max_simulations: int = 1000):
        self.C = exploration_constant
        self.max_simulations = max_simulations
        self.tt = TranspositionTable()
        self.root: MCTSNode | None = None
        self.root_state: PopOut | None = None

    def search(self, root_state: PopOut, simulations: int = None) -> dict[tuple[str, int], float]:
        """
        Run MCTS from root state and return action probabilities.

        Args:
            root_state: Initial game state
            simulations: Number of simulations to run (uses max_simulations if None)

        Returns:
            Dictionary mapping (move_type, col) -> probability
        """
        sim_count = simulations or self.max_simulations

        # Create root node
        root_hash = root_state.get_hash()
        self.tt.put(root_hash)
        self.root = MCTSNode(
            state_hash=root_hash,
            parent=None,
            move=None,
            depth=0,
            tt=self.tt
        )
        self.root.game_state = root_state.copy()
        self.root_state = root_state

        # Run simulations
        for sim in range(sim_count):
            # Selection + Expansion
            node, state = self._select(self.root, root_state.copy())

            # Simulation (rollout)
            result = self._simulate(state)

            # Backpropagation
            self._backpropagate(node, result)

        # Return action probabilities
        return self._get_action_probs(root_state)

    def _select(self, node: MCTSNode, state: PopOut) -> tuple[MCTSNode, PopOut]:
        """
        Selection phase: traverse tree using UCB1 until leaf node.
        Returns (leaf_node, resulting_state).
        """
        while True:
            # Check if node is terminal
            winner = self._get_winner(state)
            if winner is not None:
                # Terminal state
                entry = node.get_entry()
                entry.is_terminal = True
                return node, state

            # Check if node needs expansion
            if not node.is_fully_expanded(state):
                # Expand and return
                return node.expand(state)

            # Select best child using UCB1
            best_child, best_state = self._select_best_child(node, state)
            if best_child is None:
                # No children? Should not happen
                return node, state

            node = best_child
            state = best_state

    def _select_best_child(self, node: MCTSNode, state: PopOut) -> tuple[MCTSNode | None, PopOut | None]:
        """Select best child using UCB1 formula"""
        parent_entry = node.get_entry()
        parent_visits = parent_entry.visits

        if parent_visits == 0:
            parent_visits = 1

        best_value = -float('inf')
        best_child = None
        best_state = None

        # Get all children from parent
        children = node.children

        for move, child_node in children.items():
            child_entry = child_node.get_entry()
            if child_entry is None:
                continue

            # UCB1 formula
            if child_entry.visits == 0:
                ucb = float('inf')
            else:
                exploitation = child_entry.get_eval()
                exploration = self.C * math.sqrt(
                    math.log(parent_visits) / child_entry.visits
                )
                ucb = exploitation + exploration

            if ucb > best_value:
                best_value = ucb

                move_type, col = move
                child_state = state.copy()
                if move_type == 'drop':
                    child_state.drop_piece(col)
                else:
                    child_state.popout_piece(col)

                best_child = child_node
                best_state = child_state

        return best_child, best_state

    def _simulate(self, state: PopOut, max_depth: int = 100) -> float:
        """
        Random rollout until terminal state.
        Returns result from perspective of root player.
        """
        current = state.copy()
        rollout_player = current.cur_player
        depth = 0

        while depth < max_depth:
            # Check for terminal states
            winner = self._get_winner(current)
            if winner is not None:  # Check if rollout player won
                if winner == rollout_player:
                    return 1.0
                else:
                    return 0.0

            # Check for draw
            draw_status = current.get_draw_status()
            if draw_status == "THREE_FOLD":
                return 0.5  # Draw

            # Get all valid moves
            moves = []
            for col in range(COLS):
                empty_in_col = (~current.get_occupied()) & current._col_mask(col)
                if empty_in_col != 0:
                    moves.append(('drop', col))
                bottom_bit = 1 << (col * 7)
                if current.player & bottom_bit:
                    moves.append(('pop', col))

            if not moves:  # Board is full and can't pop
                return 0.5

            # Choose random move
            move = random.choice(moves)
            move_type, col = move

            if move_type == 'drop':
                current.drop_piece(col)
            else:
                current.popout_piece(col)

            depth += 1

        return 0.5  # Default draw

    def _get_winner(self, state: PopOut) -> int | None:
        """Return winner ID (0 or 1) or None if no winner"""
        # Check current player's win after last move
        # We need to check both players
        if state.win(opponent=False):
            return state.cur_player
        if state.win(opponent=True):
            return 1 - state.cur_player
        return None

    def _backpropagate(self, node: MCTSNode, result: float):
        """Backpropagate result up the tree, alternating sign"""
        current = node

        while current is not None:
            entry = current.get_entry()
            entry.update(result)

            # Negate result for parent (opponent's perspective)
            result = 1 - result if result != 0.5 else 0.5
            current = current.parent

    def _get_action_probs(self, state: PopOut, temperature: float = 1.0) -> dict[tuple[str, int], float]:
        """
        Extract action probabilities from visit counts.

        Args:
            state: Current game state
            temperature: Temperature for exploration (1.0 = proportional, 0.0 = greedy)

        Returns:
            Dictionary mapping move -> probability
        """
        if self.root is None:
            return {}

        children = self.root.children

        """
        # Get all valid moves
        valid_moves = []
        for col in range(COLS):
            # Check drop
            temp = state.copy()
            valid, _ = temp.drop_piece(col)
            if valid:
                valid_moves.append(('drop', col))

            # Check popout
            temp = state.copy()
            valid, _ = temp.popout_piece(col)
            if valid:
                valid_moves.append(('pop', col))
        """
        valid_moves = MCTSNode._get_valid_moves(state)
        print(valid_moves)

        # Get visit counts
        visits = {}
        total_visits = 0

        for move in valid_moves:
            if move in children.keys():
                child_node = children[move]
                visits[move] = child_node.visits
                total_visits += visits[move]
            else:
                visits[move] = 0
                print(move)

        # Convert to probabilities
        if total_visits == 0:
            # Uniform if no visits
            for move in valid_moves:
                visits[move] = 1.0 / len(valid_moves)
        elif temperature == 0.0:
            # Greedy: best move gets probability 1
            best_move = max(visits.items(), key=lambda x: x[1])[0]
            visits = {move: 0.0 for move in visits}
            visits[best_move] = 1.0
        else:
            # Temperature scaling
            total = sum(v ** (1.0 / temperature) for v in visits.values())
            for move in visits:
                visits[move] = (visits[move] ** (1.0 / temperature)) / total

        return visits

    def get_best_move(self, state: PopOut, simulations: int = 800) -> tuple[str, int]:
        """
        Run MCTS and return the best move.

        Returns:
            (move_type, col) e.g., ('drop', 3) or ('pop', 1)
        """
        probs = self.search(state, simulations)
        if not probs:
            return ('drop', 0)

        # Return move with highest probability
        best_move = max(probs.items(), key=lambda x: x[1])[0]
        return best_move

    def clear_transposition_table(self):
        """Clear TT for new game"""
        self.tt = TranspositionTable()


# Example usage
if __name__ == "__main__":
    # Test with a game
    game = PopOut(first_player=0)
    mcts = MCTS(exploration_constant=1.414, max_simulations=500)

    # Get best move
    move = mcts.get_best_move(game)
    print(f"Best move: {move}")

    # Get full policy
    policy = mcts.search(game, simulations=500)
    print("\nAction probabilities:")
    for move, prob in sorted(policy.items(), key=lambda x: -x[1])[:5]:
        print(f"  {move}: {prob:.3f}")

    print(f"\nTransposition table size: {len(mcts.tt.table)}")
