from copy import deepcopy
from pprint import pprint
from .levels import Levels, levels


class BitBoard:
    def __init__(self):
        # Board size is 6x7 = 42 bits
        self.player = 0    # Current player's board
        self.opponent = 0  # Current opponent's board

    def __str__(self):
        pprint(self.level.layout)
        return ""

    def __repr__(self):
        self.__str__()
        return ""

    def switch_turn(self):
        self.player, self.opponent = self.opponent, self.player

    def get_occupied(self):
        return self.player | self.opponent

    def get_empty(self):
        return ~self.get_occupied() & 0x3FFFFFFFFFF  # 42 bit mask

    def win(self):
        pass
