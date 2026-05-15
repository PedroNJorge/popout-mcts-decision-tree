from collections import defaultdict
import math
from tqdm import tqdm
import random
from .fast_heuristic import FastHeuristic
from .game import PopOut
from .tt import TranspositionTable, NodeEntry, EdgeEntry
from .types import Action

EXPLORATION_CONSTANT = 1.414  # sqrt(2)


class MCTSNode:
    """Nodes are shared and can have multiple parents"""
    __slots__ = ['hash']

    def __init__(self, hash: int):
        self.hash = hash


class MCTS:
    """Monte Carlo Tree Search with Transposition Table"""
    __slots__ = ['C', 'max_simulations', 'node_cache', 'node_tt',
                 'edge_tt', 'root', 'root_state', 'root_player', 'heuristic']

    def __init__(self, exploration_constant: float = EXPLORATION_CONSTANT,
                 max_simulations: int = 1000):
        self.C = exploration_constant
        self.max_simulations = max_simulations
        self.node_cache: dict[int, MCTSNode] = {}
        self.node_tt = TranspositionTable[int, NodeEntry](
                lambda key: NodeEntry(key)
        )
        self.edge_tt = TranspositionTable[tuple[int, Action], EdgeEntry](
                lambda key: EdgeEntry(key[0], key[1])
        )
        self.root: MCTSNode | None = None
        self.root_state: PopOut | None = None
        self.root_player: int = None
        self.heuristic = FastHeuristic()

    def search(self, state: PopOut, simulations: int = None,
               show_progress: bool = False) -> dict[Action, float]:
        """
        Run MCTS from given state and return action probabilities.

        Args:
            state: Initial game state
            simulations: Number of simulations to run (uses max_simulations if None)

        Returns:
            Dictionary mapping Action -> probability
        """
        valid = state.get_valid_actions()
        valid_set = set(valid)

        # Immediate win
        for action in valid:
            if self.heuristic.is_winning_move(state, action):
                return {a: (1.0 if a == action else 0.0) for a in valid}

        # Find opponent's winning moves using swapped bitboards (no copy)
        # is_winning_move reads state.player — swap so opponent is "player"
        class SwappedState:
            def __init__(self, s):
                self.player = s.opponent
                self.opponent = s.player
                self.filler_mask = s.filler_mask
                self._col_mask = s._col_mask

        swapped = SwappedState(state)
        for action in valid:  # opponent can only threaten via valid actions too
            if action in valid_set and self.heuristic.is_winning_move(swapped, action):
                return {a: (1.0 if a == action else 0.0) for a in valid}

        # Proceed with regular MCTS
        sim_count = simulations or self.max_simulations

        # Create root node
        root_hash = state.get_hash()
        self.root = MCTSNode(root_hash)
        self.node_cache[root_hash] = self.root
        self.node_tt.put(root_hash)
        self.root_state = state.copy()
        self.root_player = state.cur_player

        # Progress bar
        pbar = tqdm(total=sim_count, desc="MCTS Simulations",
                    unit="sim", disable=not show_progress)

        # Run simulations
        for sim in range(sim_count):
            # Selection + Expansion
            leaf_node, leaf_state, path = self._select(self.root, self.root_state.copy())

            # Simulation (rollout)
            result: float = self._simulate(leaf_state)

            # Backpropagation
            self._backpropagate(leaf_node, path, result)

            if sim == 10:
                print(self.node_tt.get(root_hash).children)

            pbar.update(1)
            if sim % 100 == 0 and sim > 0:
                pbar.set_postfix({
                    'Nodes': len(self.node_cache),
                    'Edges': len(self.edge_tt)
                })
        pbar.close()
        # Return action probabilities
        return self._get_action_probs(self.root, self.root_state)

    def _transition(self, state: PopOut, action: Action, verbose=False) -> PopOut | None:
        """
        T(s, a) = s'.

        Returns:
            New state or None if invalid action
        """
        new_state = state.copy()
        action_type, col = action
        if action_type == 'drop':
            valid, _ = new_state.drop_piece(col)
        else:  # 'pop'
            valid, _ = new_state.popout_piece(col)

        if not valid and verbose:
            print(f"{action} is not valid for the current state:\n{state}")
        return new_state if valid else None

    def _expand(self, node: MCTSNode, action: Action,
                child_state: PopOut, child_hash: int) -> tuple[MCTSNode, bool]:
        """Expand a node and return its child and whether a new edge was registered."""
        child_node = None
        child_entry = self.node_tt.get(child_hash)
        if child_entry:  # child node has been seen before
            child_node = self.node_cache[child_hash]
        else:
            # Create entry and set terminal status
            child_entry = self.node_tt.put(child_hash)
            if not child_entry.is_terminal:
                winner = child_state.get_winner()
                if winner is not None:
                    child_entry.is_terminal = True
                    child_entry.winner = winner

        if child_node is None:
            child_node = MCTSNode(child_hash)
            self.node_cache[child_hash] = child_node

        node_entry = self.node_tt.get(node.hash)

        """
        # Re-use child node if previously expanded
        if action in node_entry.children:
            return child_node, False

        # If mirror action was already expanded it points to the same child hash
        # due to symmetry. Therefore, reuse the edge as to not create ghost entries
        action_type, col = action
        mirror = (action_type, 6 - col)
        if mirror in node_entry.children:
            assert node_entry.children[mirror] == child_hash, \
                    "Mirror action points to different child, i.e., board is not symmetric"
            return child_node, False
        """
        # Check if representative of this equivalence class is already registered.
        # Reuse it as to not create ghost entries
        if child_hash in node_entry.children.values():
            return child_node, False

        # Register edge
        node_entry.children[action] = child_hash
        self.edge_tt.put((node.hash, action))
        return child_node, True

    def _select(self, node: MCTSNode, state: PopOut
                ) -> tuple[MCTSNode, PopOut, list[tuple[int, Action]]]:
        """
        Selection phase: traverse tree using UCT until leaf node.

        Returns:
            (leaf_node, leaf_state, path)
        """
        path: list[tuple[int, Action]] = []
        visited: set[int] = set()  # prevent cycles within one path
        while True:
            visited.add(node.hash)

            node_entry = self.node_tt.get(node.hash)
            assert node_entry is not None
            if node_entry.is_terminal:  # Therefore it is a leaf node
                return node, state, path

            valid_actions: list[Action] = state.get_valid_actions()
            expanded: set[Action] = set(node_entry.children.keys())

            # Find untried actions using class equivalences
            expanded_hashes: set[int] = {
                    child_hash for child_hash in node_entry.children.values()
                    }
            untried: list[Action] = []
            for action in valid_actions:
                if action in expanded:
                    continue
                child_state = self._transition(state, action)
                if child_state.get_hash() not in expanded_hashes:
                    untried.append(action)

            # Prioritize unseen nodes = leaf nodes
            while untried:
                action: Action = random.choice(untried)
                untried.remove(action)

                child_state = self._transition(state, action)
                if child_state is None:
                    raise Exception(f"{action} is not a valid action on the given state")

                child_hash = child_state.get_hash()

                # Don't expand nodes that produce cycles
                if child_hash in visited:
                    continue

                child_node, edge_registered = self._expand(node, action, child_state, child_hash)
                if edge_registered:
                    path.append((node.hash, action))
                return child_node, child_state, path

            # Fully expanded — select best child using UCT
            best_child, best_state, action = self._select_best_child(node, state, visited)

            # Safeguard: all children are terminal or lead to cycles
            if best_child is None:
                return node, state, path

            path.append((node.hash, action))
            node = best_child
            state = best_state

    def ucb1(self, edge: EdgeEntry, N_parent_total: int) -> float:
        if edge.N == 0:
            return float('inf')
        return edge.Q + self.C * math.sqrt(math.log(N_parent_total) / edge.N)

    def _select_best_child(self, node: MCTSNode, state: PopOut,
                           visited: set[int]) -> tuple[MCTSNode, PopOut, Action]:
        """Select best child using UCB1 formula"""
        node_entry = self.node_tt.get(node.hash)
        assert node_entry is not None

        children: dict[Action, int] = node_entry.children
        N_parent_total = sum(
                self.edge_tt.get((node.hash, a)).N
                for a in children.keys()
                if self.edge_tt.get((node.hash, a)) is not None
        )

        best_value = -float('inf')
        best_child = None
        best_state = None
        best_action = None

        for action, child_hash in children.items():
            if child_hash in visited:  # No cycles
                continue

            child_state = self._transition(state, action)
            if child_state is None:
                continue  # edge valid on a different path

            child_entry = self.node_tt.get(child_hash)
            if child_entry and child_entry.is_terminal:
                if child_entry.winner == self.root_player:  # root player just won — take it immediately
                    return self.node_cache[child_hash], child_state, action
                else:  # opponent just won — skip this losing move
                    continue

            edge = self.edge_tt.get((node.hash, action))
            ucb = self.ucb1(edge, N_parent_total)

            if ucb > best_value:
                best_value = ucb
                best_child = self.node_cache[child_hash]
                best_state = child_state
                best_action = action

        return best_child, best_state, best_action

    def _simulate(self, state: PopOut, max_depth: int = 100) -> float:
        """
        Random rollout until terminal state.
        Returns result from perspective of the player to move at the leaf.
        """
        current = state.copy()
        rollout_player = current.cur_player
        depth = 0

        while depth < max_depth:
            winner = current.get_winner()
            if winner is not None:
                return 1.0 if winner == rollout_player else -1.0

            draw_status = current.get_draw_status()
            if draw_status == "THREE_FOLD":
                return 0.0

            valid_actions: list[Action] = current.get_valid_actions()
            if not valid_actions:  # board full, can't pop
                return 0.0

            action = random.choice(valid_actions)
            current = self._transition(current, action)
            depth += 1

        return 0.0  # depth limit reached

    def _backpropagate(self, node: MCTSNode, path: list[tuple[int, Action]], result: float):
        """Backpropagate result up the tree, alternating perspective each edge"""
        leaf_entry = self.node_tt.get(node.hash)
        assert leaf_entry is not None
        leaf_entry.update()

        for parent_hash, action in reversed(path):
            result = -result
            edge = self.edge_tt.get((parent_hash, action))
            assert edge is not None
            edge.update(result)
            node_entry = self.node_tt.get(parent_hash)
            assert node_entry is not None
            node_entry.update()

    def _get_action_probs(self, node: MCTSNode, state: PopOut,
                          temperature: float = 1.0) -> dict[Action, float]:
        """
        Extract action probabilities from visit counts.

        Args:
            node: Current node
            state: Current state
            temperature: Temperature for exploration (1.0 = proportional, 0.0 = greedy)

        Returns:
            Dictionary mapping Action -> probability
        """
        node_entry = self.node_tt.get(node.hash)
        children: dict[Action, int] = node_entry.children
        valid_set: set[Action] = set(state.get_valid_actions())

        visits = {action: self.edge_tt.get((node.hash, action)).N
                  for action in children}
        total_visits = sum(visits.values())

        if total_visits == 0:  # uniform fallback
            return {action: 1.0 / len(valid_set) for action in valid_set}
        elif temperature == 0.0:  # greedy
            best_action = max(visits.items(), key=lambda x: x[1])[0]
            probs = {action: 1.0 if action == best_action else 0.0 for action in children}
        else:
            total_weighted = sum(v ** (1.0 / temperature) for v in visits.values())
            probs = {
                action: (visits[action] ** (1.0 / temperature)) / total_weighted
                for action in children
            }

        print(f"valid_actions = {valid_set}")
        print(f"canonical probs = {probs}")

        # Build G(s) = A(s) / ~ using canonical hashes
        groups: dict[int, list[Action]] = defaultdict(list)
        for action in valid_set:
            child_state = self._transition(state, action)
            groups[child_state.get_hash()].append(action)

        # For each equivalence class, find the registered edge and distribute
        final_probs = {}
        for canonical, actions in groups.items():
            registered = [a for a in actions if a in probs]
            if not registered:
                continue
            assert len(registered) == 1, "There should only be one representative of the class equivalence"
            prob = probs[registered[0]]
            per_action = prob / len(actions)
            for action in actions:
                final_probs[action] = per_action
        return final_probs

    def get_best_move(self, state: PopOut, simulations: int = 800,
                      show_progress: bool = False) -> Action:
        """
        Run MCTS and return the best move.

        Returns:
            Action: (action_type, col)
                e.g., ('drop', 3), ('pop', 1)
        """
        probs: dict[Action, float] = self.search(state, simulations, show_progress=show_progress)
        if not probs:
            return ('drop', 0)
        return max(probs.items(), key=lambda x: x[1])[0]

    def clear(self):
        """Clear TTs and node cache for a new game"""
        self.node_cache: dict[int, MCTSNode] = {}
        self.node_tt = TranspositionTable[int, NodeEntry](
                lambda key: NodeEntry(key)
        )
        self.edge_tt = TranspositionTable[tuple[int, Action], EdgeEntry](
                lambda key: EdgeEntry(key[0], key[1])
        )