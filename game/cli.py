import curses
import time
from .board import BitBoard, ROWS, COLS

EMPTY = '-'


class PopoutCLI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.bitboard = BitBoard()
        self.cursor_col = COLS // 2  # Start in middle
        self.player = 'X'
        self.opponent = 'O'

        self.log_file = open('debug.log', 'w')

    def log(self, msg):
        """Write debug message to log file"""
        self.log_file.write(f"{msg}\n")
        self.log_file.flush()

    def switch_turn(self):
        self.player, self.opponent = self.opponent, self.player
        self.bitboard.switch_turn()

    def get_display_board(self):
        """Convert bitboard to display grid"""
        display = [[EMPTY for _ in range(COLS)] for _ in range(ROWS)]

        # Convert bit positions to row/col
        for bit in range(48):
            col = bit // 7
            row = bit % 7
            if row >= ROWS or col >= COLS:
                continue

            if (self.bitboard.player >> bit) & 1:
                # Convert bottom-oriented row to display-oriented row
                display_row = ROWS - 1 - row
                display[display_row][col] = self.player
            elif (self.bitboard.opponent >> bit) & 1:
                display_row = ROWS - 1 - row
                display[display_row][col] = self.opponent

        return display

    def draw_board(self):
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
                self.stdscr.addch(y, x, piece)

        # Draw column numbers
        nums_y = start_y - 1
        for col in range(COLS):
            x = start_x + col * 2
            if col == self.cursor_col:
                self.stdscr.addch(nums_y, x, '*')
            else:
                self.stdscr.addch(nums_y, x, chr(ord('1') + col))

        # Draw status line
        status_y = start_y + ROWS + 2
        status = f"Player {self.player}'s turn  |  Column: {self.cursor_col + 1}"
        self.stdscr.addstr(status_y, start_x, status)

        # Draw instructions
        help_y = status_y + 1
        help_text = "←/→ move | d drop | p popout | t tie | q quit"
        self.stdscr.addstr(help_y, start_x, help_text)

        self.stdscr.refresh()

    def drop_piece(self):
        """Drop piece in current column"""
        if self.bitboard.drop_piece(self.cursor_col):
            # Check win after drop
            if self.bitboard.win():
                return "WIN"
            return True
        return False

    def can_draw(self):
        """Check if player can draw"""
        return self.bitboard.can_draw()

    def popout_piece(self):
        """Popout piece from current column"""
        if self.bitboard.popout_piece(self.cursor_col):
            # Check win after popout
            if self.bitboard.win():
                return "WIN"

            # Need to temporarily switch to opponent's perspective to check their win
            self.bitboard.switch_turn()
            opponent_wins = self.bitboard.win()
            self.bitboard.switch_turn()  # Switch back to current player

            if opponent_wins:
                return "OPPONENT_WIN"

            return True
        return False

    def run(self):
        """Main game loop"""
        # Hide cursor
        curses.curs_set(0)

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
                result = self.drop_piece()
                if result == "WIN":
                    self.show_game_over()
                    break
                elif not result:
                    self.show_message("Column full!")
                else:
                    self.switch_turn()

            elif key == ord('p'):
                result = self.popout_piece()
                if result == "WIN":
                    self.show_game_over()
                    break
                elif result == "OPPONENT_WIN":
                    self.switch_turn()
                    self.show_game_over()
                    break
                elif not result:
                    self.show_message("Not your piece at bottom!")
                else:
                    self.switch_turn()

            elif key == ord('t'):
                result = self.can_draw()
                self.log(f"CAN DRAW: {result}")
                self.log(f"Player: {self.bitboard.player:X}")
                self.log(f"Opponent: {self.bitboard.opponent:X}")
                self.log(f"Empty: {self.bitboard.get_empty():X}")
                self.log(f"Occupied: {self.bitboard.get_occupied():X}")

                if result:
                    self.show_game_over(draw=True)
                    break

    def show_message(self, msg):
        """Show a temporary message"""
        # Clear any pending input
        self.stdscr.nodelay(True)
        while self.stdscr.getch() != -1:
            pass  # Flush input buffer
        self.stdscr.nodelay(False)

        height, width = self.stdscr.getmaxyx()
        msg_y = height // 2 + ROWS + 4
        msg_x = (width - len(msg)) // 2
        self.stdscr.addstr(msg_y, msg_x, msg)
        self.stdscr.refresh()

        # Wait without processing input
        time.sleep(1)

    def show_game_over(self, draw=False):
        """Show game over screen"""
        self.draw_board()

        height, width = self.stdscr.getmaxyx()
        if draw:
            msg = "GAME ENDS WITH A TIE!"
        else:
            msg = f"GAME OVER! Player {self.player} wins!"
        msg_y = height // 2 + ROWS + 2
        msg_x = (width - len(msg)) // 2

        self.stdscr.addstr(msg_y, msg_x, msg, curses.A_BOLD)
        self.stdscr.addstr(msg_y + 1, msg_x, "Press any key to exit")
        self.stdscr.refresh()
        self.stdscr.getch()


def main(stdscr):
    game = PopoutCLI(stdscr)
    game.run()


if __name__ == "__main__":
    curses.wrapper(main)
