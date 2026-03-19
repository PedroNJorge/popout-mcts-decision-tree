class GameLogic:
    def __init__(self, block, board):
        self.block = block
        self.board = board
        self.game_over = False
        self.level_completed = False

    def check_win(self):
        if self.block.orientation == "upright":
            return self.board.is_goal((self.block.x1, self.block.y1))

    def check_lose(self):
        return self.board.is_fatal(self.block)

    def update(self):
        if self.check_win():
            print("win")
            self.level_completed = True
        elif self.check_lose():
            print("lose")
            self.game_over = True
