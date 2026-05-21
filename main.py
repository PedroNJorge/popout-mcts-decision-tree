import curses
from src.cli import PopOutCLI


def main(stdscr):
    game = PopOutCLI(stdscr)
    game.run()


if __name__ == "__main__":
    curses.wrapper(main)
