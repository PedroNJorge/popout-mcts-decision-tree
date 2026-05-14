import curses
import time
from .game import PopOut, ROWS, COLS
from .players.human import HumanPlayer
from .players.random_player import RandomPlayer
from .players.mcts_player import MCTSPlayer

class PopOutCLI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.game = None
        self.players = []
        self.cursor_col = COLS // 2
        
        # Inicializar cores
        curses.start_color()
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)    # Player 1
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Player 2
        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)   # Seleção/Menu

    def show_menu(self) -> int:
        """Menu de seleção de modo de jogo"""
        options = [
            "1. Player vs Player",
            "2. Player vs AI (MCTS)",
            "3. AI (MCTS) vs AI (Random)",
            "4. Sair"
        ]
        current = 0
        while True:
            self.stdscr.clear()
            h, w = self.stdscr.getmaxyx()
            self.stdscr.addstr(h//2-5, w//2-10, "MODO DE JOGO:", curses.A_BOLD)
            
            for i, opt in enumerate(options):
                attr = curses.color_pair(3) | curses.A_REVERSE if i == current else 0
                self.stdscr.addstr(h//2-1+i, w//2-len(opt)//2, opt, attr)
            
            key = self.stdscr.getch()
            if key == curses.KEY_UP and current > 0: current -= 1
            elif key == curses.KEY_DOWN and current < len(options)-1: current += 1
            elif key in [10, 13]: return current

    def setup_game(self, mode):
        self.game = PopOut()
        if mode == 0:
            self.players = [HumanPlayer("Humano 1", 0), HumanPlayer("Humano 2", 1)]
        elif mode == 1:
            self.players = [HumanPlayer("Tu", 0), MCTSPlayer("Bot MCTS", 1)]
        elif mode == 2:
            self.players = [MCTSPlayer("MCTS Alpha", 0), RandomPlayer("Random Bot", 1)]

    def run(self):
        curses.curs_set(0)
        # self.show_title_screen() # Podes manter a tua função aqui
        
        mode = self.show_menu()
        if mode == 3: return
        self.setup_game(mode)

        while True:
            self.draw_board() # Usa a tua função draw_board
            curr_p = self.players[self.game.cur_player]
            
            move = curr_p.get_move(self.game)

            if move is None: # Vez do Humano (Input Teclado)
                key = self.stdscr.getch()
                if key == ord('q'): break
                elif key == curses.KEY_LEFT and self.cursor_col > 0: self.cursor_col -= 1
                elif key == curses.KEY_RIGHT and self.cursor_col < COLS-1: self.cursor_col += 1
                elif key == ord('d'): move = ('drop', self.cursor_col)
                elif key == ord('p'): move = ('pop', self.cursor_col)
                elif key == ord('t') and self.game.get_draw_status():
                    # Lógica de empate
                    break
            else:
                # Vez da AI
                # Se for AI vs AI, colocamos um pequeno delay para ser visível
                if mode == 2: time.sleep(0.5)

            if move:
                m_type, col = move
                valid, winner = False, None
                if m_type == 'drop':
                    valid, winner = self.game.drop_piece(col)
                else:
                    valid, winner = self.game.popout_piece(col)
                
                if winner is not None:
                    self.draw_board()
                    # self.show_game_over(winner)
                    break