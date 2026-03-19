import pygame
import sys
from game import Board
from game import Block
from game import GameLogic
from game import InputHandler
from game import Renderer


def main():
    pygame.init()

    board = Board("LEVEL1")
    block = Block(board.level.start[0], board.level.start[1])
    game_logic = GameLogic(block, board)
    input_handler = InputHandler(block, board, game_logic, None)
    renderer = Renderer(block, board, game_logic, input_handler)
    input_handler.renderer = renderer

    board.refresh_layout(block)

    renderer.run()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
