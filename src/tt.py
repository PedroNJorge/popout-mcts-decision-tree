class TTEntry:
    """Entry in transposition table"""

    def __init__(self, state_hash: int):
        self.hash = state_hash
        self.visits = 0
        self.value = 0.0
        self.is_terminal = False

    def get_eval(self):
        """Returns U(n) / N(n)"""
        if self.visits == 0:
            return 0.0
        return self.value / self.visits

    def update(self, result: float):
        """Update statistics"""
        self.visits += 1
        self.value += result


class TranspositionTable:
    """Hash table for storing unique states"""

    def __init__(self):
        self.table: dict[int, TTEntry] = {}

    def get(self, state_hash: int) -> TTEntry | None:
        """Retrieve entry if exists"""
        return self.table.get(state_hash)

    def put(self, state_hash: int):
        if state_hash not in self.table:
            self.table[state_hash] = TTEntry(state_hash)
