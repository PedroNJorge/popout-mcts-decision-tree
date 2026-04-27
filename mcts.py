import math
import random
import copy
from .game import PopOut, ROWS, COLS

class MCTSNode:
    def __init__(self, game_state, move=None, parent=None):
        self.game = game_state
        self.move = move
        self.parent = parent
        self.children = []
        self.wins = 0
        self.visits = 0
        # Quem fez a jogada para chegar a este estado
        self.player_who_moved = 1 - game_state.cur_player 
        self.untried_moves = self.get_legal_moves()

    def get_legal_moves(self):
        moves = []
        occupied = self.game.player | self.game.opponent
        
        # Drops
        for c in range(COLS):
            col_mask = self.game.filler_mask & (0b111111 << (c * 7))
            if not ((occupied & col_mask) == col_mask):
                moves.append(('drop', c))
        
        # Pops
        for c in range(COLS):
            bottom_bit = 1 << (c * 7)
            if self.game.player & bottom_bit: # Regra: só retira se for do player atual
                moves.append(('pop', c))
        return moves

    def uct_select_child(self, exploration_constant=1.414):
        return max(self.children, key=lambda c: (c.wins / c.visits) + 
                   exploration_constant * math.sqrt(math.log(self.visits) / c.visits))

    def add_child(self, move, state):
        child = MCTSNode(state, move=move, parent=self)
        self.untried_moves.remove(move)
        self.children.append(child)
        return child

class MCTS:
    def __init__(self, iterations=1000):
        self.iterations = iterations

    def search(self, initial_state):
        root = MCTSNode(copy.deepcopy(initial_state))

        for _ in range(self.iterations):
            node = root
            state = copy.deepcopy(initial_state)

            # 1. SELEÇÃO
            while not node.untried_moves and node.children:
                node = node.uct_select_child()
                self._apply_move(state, node.move)

            # 2. EXPANSÃO
            if node.untried_moves:
                move = random.choice(node.untried_moves)
                self._apply_move(state, move)
                node = node.add_child(move, copy.deepcopy(state))

            # 3. SIMULAÇÃO
            winner_id = self._simulate(state)

            # 4. RETROPROPAGAÇÃO (Diferenciando Jogadores)
            while node is not None:
                node.visits += 1
                if winner_id == 0.5:
                    node.wins += 0.5
                # O nó ganha ponto se o vencedor for quem fez a jogada do nó
                elif winner_id == node.player_who_moved:
                    node.wins += 1.0
                node = node.parent

        # Escolhe a melhor jogada (exploração = 0)
        return root.uct_select_child(exploration_constant=0).move

    def _apply_move(self, state, move):
        m_type, col = move
        if m_type == 'drop':
            state.drop_piece(col)
        else:
            state.popout_piece(col)

    def _simulate(self, state):
        temp_state = copy.deepcopy(state)
        max_moves = 60
        
        while max_moves > 0:
            # Verifica vitória do último a jogar
            if temp_state.win(): 
                return 1 - temp_state.cur_player
            # Verifica se o anterior ganhou (no caso de popout dar vitória a ambos)
            if temp_state.win(opponent=True):
                return temp_state.cur_player
            if temp_state.get_empty() == 0:
                return 0.5
            
            moves = MCTSNode(temp_state).get_legal_moves()
            if not moves: return 0.5
            
            self._apply_move(temp_state, random.choice(moves))
            max_moves -= 1
        return 0.5