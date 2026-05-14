from collections import defaultdict
import math
from tqdm import tqdm
import random
from .game import PopOut
from .tt import TranspositionTable, NodeEntry, EdgeEntry
from .types import CanonicalAction, PhysicalAction

EXPLORATION_CONSTANT = 1.414  # sqrt(2)
# Note: when working with (node, action), action should be canonical (hash is canonical)
#       when working with (state, action), action should be physical (state is physical)


class MCTSNode:
    """Nodes are shared and can have multiple parents"""
    __slots__ = ['hash']

    def __init__(self, hash: int):
        self.hash = hash


class MCTS:
    """Monte Carlo Tree Search with Transposition Table"""
    __slots__ = ['C', 'max_simulations', 'node_cache', 'node_tt',
                 'edge_tt', 'root', 'root_state']

    def __init__(self, exploration_constant: float = EXPLORATION_CONSTANT,
                 max_simulations: int = 1000):
        self.C = exploration_constant
        self.max_simulations = max_simulations
        self.node_cache: dict[int, MCTSNode] = {}
        self.node_tt = TranspositionTable[int, NodeEntry](
                lambda key: NodeEntry(key)
        )
        self.edge_tt = TranspositionTable[tuple[int, CanonicalAction], EdgeEntry](
                lambda key: EdgeEntry(key[0], key[1])
        )
        self.root: MCTSNode | None = None
        self.root_state: PopOut | None = None

    def search(self, state: PopOut, simulations: int = None,
               show_progress: bool = False) -> dict[PhysicalAction, float]:
        """
        Run MCTS from given state and return action probabilities.

        Args:
            root_state: Initial game state
            simulations: Number of simulations to run (uses max_simulations if None)

        Returns:
            Dictionary mapping PhysicalAction -> probability
        """
        sim_count = simulations or self.max_simulations

        # Create root node
        root_hash = state.get_hash()
        self.root = MCTSNode(root_hash)
        self.node_cache[root_hash] = self.root
        self.node_tt.put(root_hash)
        self.root_state = state.copy()

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

            pbar.update(1)
            if sim % 100 == 0 and sim > 0:
                pbar.set_postfix({
                    'Nodes': len(self.node_cache),
                    'Edges': len(self.edge_tt)
                })
        pbar.close()
        # Return action probabilities
        return self._get_action_probs(self.root, self.root_state)

    def _canonical_action(self, action: PhysicalAction) -> CanonicalAction:
        """Canonical action: always use the smaller of col and its mirror."""
        action_type, col = action
        return action_type, min(col, 6 - col)

    def _physical_actions(self, state: PopOut,
                          canonical: CanonicalAction) -> list[PhysicalAction]:
        """
        A canonical action may map to 1 or 2 physical actions.
        col 3 maps to itself only; all others map to col and 6-col.
        We filter by what's actually valid in the given state.
        """
        action_type, col = canonical
        candidates = [(action_type, col)]
        if col != 6 - col:  # i.e. col != 3
            candidates.append((action_type, 6 - col))
        valid = set(state.get_valid_actions())
        return [a for a in candidates if a in valid]

    def _transition(self, state: PopOut, action: PhysicalAction) -> PopOut | None:
        """
        T(s, a) = s'.

        Returns:
            New State or None if invalid action
        """
        new_state = state.copy()
        action_type, col = action
        if action_type == 'drop':
            valid, _ = new_state.drop_piece(col)
        else:  # 'pop'
            valid, _ = new_state.popout_piece(col)

        if not valid:
            print(f"{action} is not valid for the current state:\n{state}")
        return new_state if valid else None

    def _expand(self, node: MCTSNode, state: PopOut, action: CanonicalAction,
                child_state: PopOut, child_hash: int) -> MCTSNode:
        """Expand a node and return it's child"""
        assert action == self._canonical_action(action)
        child_node = None
        child_entry = self.node_tt.get(child_hash)
        if child_entry:  # child node has been seen
            child_node = self.node_cache[child_hash]
        else:
            # Create entry and set terminal status (forget about draws)
            child_entry = self.node_tt.put(child_hash)
            if not child_entry.is_terminal:
                winner = child_state.get_winner()
                child_entry.is_terminal = winner is not None

        # Update parent node TTs
        node_entry = self.node_tt.get(node.hash)
        node_entry.children[action] = child_hash
        self.edge_tt.put((node.hash, action))

        if child_node is None:
            child_node = MCTSNode(child_hash)
            self.node_cache[child_hash] = child_node
        return child_node

    def _select(self, node: MCTSNode, state: PopOut
                ) -> tuple[MCTSNode, PopOut, list[tuple[int, CanonicalAction]]]:
        """
        Selection phase: traverse tree using UCT until leaf node.
        Returns:
            (leaf_node, leaf_state, path)
        """
        # edge path (parent_hash, action)
        path: list[tuple[int, CanonicalAction]] = []
        i = 1
        visited: set[int] = set()  # make sure we don't get into cycles in the same path
        while True:
            i += 1
            visited.add(node.hash)

            # Can't traverse through terminal nodes
            node_entry = self.node_tt.get(node.hash)
            assert node_entry is not None
            if node_entry.is_terminal:
                return node, state, path

            # Prioritize nodes not expanded
            # Map class equivalences of actions using the canonical
            canonical_map = defaultdict(list)
            for action in state.get_valid_actions():
                canonical_map[self._canonical_action(action)].append(action)

            expanded: set[CanonicalAction] = set(node_entry.children.keys())
            untried: list[CanonicalAction] = [
                    a for a in canonical_map.keys()
                    if a not in expanded]

            while untried:
                canonical: CanonicalAction = random.choice(untried)
                untried.remove(canonical)

                # physical_action: PhysicalAction = self._physical_action(state, action)
                physical_action: PhysicalAction = canonical_map[canonical][0]

                child_state = self._transition(state, physical_action)
                if child_state is None:
                    raise Exception(f"{physical_action} is a not a valid action on the given state")

                child_hash = child_state.get_hash()

                # Don't want to expand nodes that produce cycles
                if child_hash in visited:
                    continue

                child_node = self._expand(
                        node,
                        state,
                        canonical,
                        child_state,
                        child_hash)

                path.append((node.hash, canonical))
                return child_node, child_state, path

            # Fully expanded. Select best child using UCT
            best_child, best_state, action = self._select_best_child(node, state, visited)

            # Safe guard
            if best_child is None:  # all children are terminal or induce in cycles
                return node, state, path

            path.append((node.hash, action))
            node = best_child
            state = best_state
        return node, state, path

    def ucb1(self, edge: EdgeEntry, N_parent_total: int) -> float | None:
        if edge.N == 0:
            return float('inf')
        return edge.Q + self.C * math.sqrt(math.log(N_parent_total) / edge.N)

    def _select_best_child(self, node: MCTSNode, state: PopOut,
                           visited: set[int]) -> tuple[MCTSNode, PopOut, CanonicalAction]:
        """Select best child using UCB1 formula"""
        # total times we considered outgoing edges from node in selection
        node_entry = self.node_tt.get(node.hash)
        assert node_entry is not None

        children: dict[CanonicalAction, int] = node_entry.children
        N_parent_total = sum(
                self.edge_tt.get((node.hash, a)).N
                for a in children.keys()
                if self.edge_tt.get((node.hash, a)) is not None
        )

        best_value = -float('inf')
        best_child = None
        best_state = None
        best_canonical_action = None

        for canonical_action, child_hash in children.items():
            edge = self.edge_tt.get((node.hash, canonical_action))
            child_entry = self.node_tt.get(child_hash)
            if child_entry.is_terminal or child_hash in visited:
                continue

            # UCB1 formula
            ucb = self.ucb1(edge, N_parent_total)

            if ucb > best_value:
                best_value = ucb

                # Generate child state
                candidates = self._physical_actions(state, canonical_action)
                assert candidates
                physical_action = candidates[0]

                child_state = self._transition(state, physical_action)
                if child_state is None:
                    print("Invalid action used in _select_best_child!")

                best_child = self.node_cache[child_hash]
                best_state = child_state
                best_canonical_action = canonical_action
        return best_child, best_state, best_canonical_action

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
            winner = current.get_winner()
            if winner is not None:  # Check if rollout player won
                if winner == rollout_player:
                    return 1.0
                else:
                    return 0.0

            # Check for draw
            draw_status = current.get_draw_status()
            if draw_status == "THREE_FOLD":
                return 0.5  # Draw

            # Get all valid actions & choose one
            valid_actions: list[PhysicalAction] = current.get_valid_actions()

            if not valid_actions:  # Board is full and can't pop
                return 0.5

            # Could substitute with another policy instead of random
            action: PhysicalAction = random.choice(valid_actions)
            current = self._transition(current, action)

            depth += 1
        return 0.5  # Default draw

    def _backpropagate(self, node: MCTSNode, path: list[tuple[int, CanonicalAction]], result: float):
        """Backpropagate result up the tree, alternating sign"""
        leaf_entry = self.node_tt.get(node.hash)
        assert leaf_entry is not None
        leaf_entry.update()

        # BP through edges
        for parent_hash, action in reversed(path):
            result = 1 - result if result != 0.5 else 0.5
            edge = self.edge_tt.get((parent_hash, action))
            assert edge is not None
            edge.update(result)
            node_entry = self.node_tt.get(parent_hash)
            assert node_entry is not None
            node_entry.update()

    def _get_action_probs(self, node: MCTSNode, state: PopOut,
                          temperature: float = 1.0) -> dict[PhysicalAction, float]:
        """
        Extract action probabilities from visit counts.

        Args:
            node: Current node
            state: Current state
            temperature: Temperature for exploration (1.0 = proportional, 0.0 = greedy)

        Returns:
            Dictionary mapping PhysicalAction -> probability,
                i.e., probability distribution of valid physical actions
        """
        valid_actions: list[PhysicalAction] = state.get_valid_actions()

        # Create class equivalences for the actions
        class_equiv = defaultdict(list)
        for action in valid_actions:
            class_equiv[self._canonical_action(action)].append(action)

        # Get visit counts per class equivalence from EdgeTT
        class_visits: dict[CanonicalAction, int] = {}
        total_visits = 0
        for canonical in class_equiv:
            edge = self.edge_tt.get((node.hash, canonical))
            assert edge is not None
            class_visits[canonical] = edge.N
            total_visits += edge.N

        # Convert to ALL actions probability distribution
        if total_visits == 0:  # uniform
            return {action: 1.0 / len(valid_actions) for action in valid_actions}
        elif temperature == 0.0:  # greedy
            # Find best canonical action (highest visits)
            best_canonical = max(class_visits.items(), key=lambda x: x[1])[0]
            best_physical_actions = class_equiv[best_canonical]

            # Distribute probability evenly among equivalent actions
            prob = 1.0 / len(best_physical_actions)
            return {action: prob if action in best_physical_actions else 0.0
                    for action in valid_actions}
        else:
            # Apply temperature scaling to class visits first
            total_weighted = sum(v ** (1.0 / temperature)
                                 for v in class_visits.values())

            probs = {}
            for canonical_action, physical_actions in class_equiv.items():
                # Probability mass for this symmetric class
                class_prob = (class_visits[canonical_action] ** (1.0 / temperature)) / total_weighted

                # Distribute equally among physical actions in this class
                per_action_prob = class_prob / len(physical_actions)
                for action in physical_actions:
                    probs[action] = per_action_prob
            return probs

    def get_best_move(self, state: PopOut, simulations: int = 800,
                      show_progress: bool = False) -> PhysicalAction:
        """
        Run MCTS and return the best move.

        Returns:
            PhysicalAction: (action_type, col)
                e.g., ('drop', 3), ('pop', 1)
        """
        probs: dict[PhysicalAction, float] = self.search(state, simulations, show_progress=show_progress)
        if not probs:
            return ('drop', 0)

        # Return move with highest probability
        best_move = max(probs.items(), key=lambda x: x[1])[0]
        return best_move

    def clear(self):
        """Clear TTs and node_cache for new game"""
        self.node_cache: dict[int, MCTSNode] = {}
        self.node_tt = TranspositionTable[int, NodeEntry](
                lambda key: NodeEntry(key)
        )
        self.edge_tt = TranspositionTable[tuple[int, CanonicalAction], EdgeEntry](
                lambda key: EdgeEntry(key[0], key[1])
        )
