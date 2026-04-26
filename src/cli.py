import curses
import time
from .game import PopOut, ROWS, COLS

EMPTY = '-'
PLAYER1 = 'X'
PLAYER2 = 'O'


class PopOutCLI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.game = PopOut()
        self.cursor_col = COLS // 2  # Start in middle
        self.player = PLAYER1
        self.opponent = PLAYER2
        self.curPlayerId = 0
        self.playerId = {0: PLAYER1, 1: PLAYER2}

        self.log_file = open('debug.log', 'w')

        # Initialize colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)

    def log(self, msg):
        """Write debug message to log file"""
        self.log_file.write(f"{msg}\n")
        self.log_file.flush()

    def show_title_screen(self):
        """Display title screen with ASCII art"""
        self.stdscr.clear()

        # Get terminal dimensions
        height, width = self.stdscr.getmaxyx()

        stylized_title = [
            "██████╗  ██████╗ ██████╗  ██████╗ ██╗   ██╗████████╗",
            "██╔══██╗██╔═══██╗██╔══██╗██╔═══██╗██║   ██║╚══██╔══╝",
            "██████╔╝██║   ██║██████╔╝██║   ██║██║   ██║   ██║   ",
            "██╔═══╝ ██║   ██║██╔═══╝ ██║   ██║██║   ██║   ██║   ",
            "██║     ╚██████╔╝██║     ╚██████╔╝╚██████╔╝   ██║   ",
            "╚═╝      ╚═════╝ ╚═╝      ╚═════╝  ╚═════╝    ╚═╝   "
        ]

        # Calculate starting Y position (center vertically)
        title_height = len(stylized_title)
        start_y = (height - title_height - 8) // 2  # 8 lines for spacing and authors

        # Draw title in a fancy color (use color pair 1 for red)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)  # Cyan for title
        curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Yellow for authors

        for i, line in enumerate(stylized_title):
            x = (width - len(line)) // 2
            try:
                self.stdscr.addstr(start_y + i, x, line, curses.color_pair(4) | curses.A_BOLD)
            except curses.error:
                pass  # Ignore if line doesn't fit

        # Draw subtitle or authors
        authors_y = start_y + title_height + 2
        authors_text = "Authors: Ana Francisca, Pedro N. Jorge, Sofia Ribeiro"
        authors_x = (width - len(authors_text)) // 2
        self.stdscr.addstr(authors_y, authors_x, authors_text, curses.color_pair(5) | curses.A_BOLD)

        # Add a fancy border or separator
        separator = "=" * min(60, width - 4)
        sep_x = (width - len(separator)) // 2
        self.stdscr.addstr(authors_y + 2, sep_x, separator, curses.color_pair(5))

        # Instructions to start
        start_text = "Press any key to start the game..."
        start_x = (width - len(start_text)) // 2
        self.stdscr.addstr(authors_y + 4, start_x, start_text, curses.A_DIM)

        self.stdscr.refresh()

        # Wait for any key press
        self.stdscr.getch()

    def get_display_board(self):
        """Convert bitboard to display grid"""
        display = [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]

        # Convert bit positions to row/col
        for bit in range(48):
            col = bit // 7
            row = bit % 7
            if row >= ROWS or col >= COLS:
                continue

            if (self.game.player >> bit) & 1:
                # Convert bottom-oriented row to display-oriented row
                display_row = ROWS - 1 - row
                display[display_row][col] = self.player
            elif (self.game.opponent >> bit) & 1:
                display_row = ROWS - 1 - row
                display[display_row][col] = self.opponent

        return display

    def draw_board(self, info=True):
        """Draw the game board"""
        self.stdscr.clear()

        # Get terminal dimensions
        height, width = self.stdscr.getmaxyx()

        # Calculate center position
        start_y = (height - ROWS) // 2
        start_x = (width - COLS * 2) // 2  # *2 for spacing

        # Get current board state
        display_board = self.get_display_board()

        # Draw the board
        for row in range(ROWS):
            for col in range(COLS):
                y = start_y + row
                x = start_x + col * 2

                piece = display_board[row][col]
                if piece == EMPTY:
                    self.stdscr.addch(y, x, piece, curses.color_pair(3))
                elif piece == PLAYER1:
                    self.stdscr.addch(y, x, piece, curses.color_pair(1))
                elif piece == PLAYER2:
                    self.stdscr.addch(y, x, piece, curses.color_pair(2))

        if info:
            # Draw column numbers
            nums_y = start_y - 1
            for col in range(COLS):
                x = start_x + col * 2
                if col == self.cursor_col:
                    self.stdscr.addch(nums_y, x, '*', curses.color_pair(self.curPlayerId + 1))
                else:
                    pass
                    # self.stdscr.addch(nums_y, x, chr(ord('1') + col))

            # Draw status line
            status_y = start_y + ROWS + 2
            status = f"Player {self.player}'s turn"
            self.stdscr.addstr(status_y, start_x, status)

            # Draw instructions
            help_y = status_y + 1
            help_text = "←/→ move | d drop | p popout | t draw | q quit"
            self.stdscr.addstr(help_y, start_x, help_text)

            # If can draw show
            draw_status = self.game.get_draw_status()
            if draw_status == "BOARD_FULL":
                tie_x = start_x + 2*COLS + 3
                tie_y = nums_y + ROWS // 2
                tie = f"Board is full! {self.player} can declare a draw!"
                self.stdscr.addstr(tie_y, tie_x, tie)
            elif draw_status == "THREE_FOLD":
                self.show_message(
                        "THREE FOLD REPETITION DETECTED - Press 't' to declare draw",
                        bold=True,
                        wait=False
                )
        self.stdscr.refresh()

    def show_message(self, msg, bold=False, wait=True):
        """Show a temporary message"""
        # Clear any pending input
        self.stdscr.nodelay(True)
        while self.stdscr.getch() != -1:
            pass  # Flush input buffer
        self.stdscr.nodelay(False)

        height, width = self.stdscr.getmaxyx()
        msg_y = height // 2 + ROWS + 4
        msg_x = (width - len(msg)) // 2
        if bold:
            self.stdscr.addstr(msg_y, msg_x, msg, curses.A_BOLD)
        else:
            self.stdscr.addstr(msg_y, msg_x, msg)
        self.stdscr.refresh()

        # Wait without processing input
        if wait:
            time.sleep(1)

    def show_game_over(self, playerId=None, draw=False):
        """Show game over screen"""
        self.draw_board(info=False)
        if playerId is None and not draw:
            raise ValueError("Must provide a player ID when game is not a draw")

        height, width = self.stdscr.getmaxyx()
        if draw:
            msg = "GAME ENDS WITH A TIE!"
        else:
            msg = f"GAME OVER! Player {self.playerId[playerId]} wins!"
        msg_y = height // 2 + ROWS + 2
        msg_x = (width - len(msg)) // 2

        self.stdscr.addstr(msg_y, msg_x, msg, curses.A_BOLD)
        self.stdscr.addstr(msg_y + 1, msg_x, "Press any key to exit")
        self.stdscr.refresh()
        self.stdscr.getch()

    def switch_turn(self):
        self.player, self.opponent = self.opponent, self.player
        self.curPlayerId = 1 - self.curPlayerId

    def drop_piece(self):
        """Drop piece in current column"""
        return self.game.drop_piece(self.cursor_col)

    def popout_piece(self):
        """Popout piece from current column"""
        return self.game.popout_piece(self.cursor_col)

    def run(self):
        """Main game loop"""
        # Hide cursor
        curses.curs_set(0)

        self.show_title_screen()

        while True:
            self.draw_board()

            # Get user input
            key = self.stdscr.getch()

            if key == ord('q'):
                break

            elif key == curses.KEY_LEFT and self.cursor_col > 0:
                self.cursor_col -= 1

            elif key == curses.KEY_RIGHT and self.cursor_col < COLS - 1:
                self.cursor_col += 1

            elif key == ord('d'):
                valid, winner = self.drop_piece()
                if not valid:
                    self.show_message("Column full!")
                elif winner is None:
                    self.switch_turn()
                else:
                    self.show_game_over(winner)
                    break

            elif key == ord('p'):
                valid, winner = self.popout_piece()
                if not valid:
                    self.show_message("Column empty or not your piece at bottom!")
                elif winner is None:
                    self.switch_turn()
                else:
                    self.show_game_over(winner)
                    break

            elif key == ord('t'):
                status = self.game.get_draw_status()
                if status is not None:
                    self.show_game_over(draw=True)
                    break
