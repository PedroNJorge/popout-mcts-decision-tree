import curses
from game import PopoutCLI

def main(stdscr):
    game = PopoutCLI(stdscr)
    game.run()

if __name__ == "__main__":
    curses.wrapper(main)
