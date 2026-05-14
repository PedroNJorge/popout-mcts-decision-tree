from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Callable
from .types import CanonicalAction

K = TypeVar('K')


class BaseEntry(ABC, Generic[K]):
    """TT entry ABC"""
    @property
    @abstractmethod
    def key(self) -> K:
        pass


E = TypeVar('E', bound=BaseEntry)


class EdgeEntry(BaseEntry[tuple[int, CanonicalAction]]):
    """
    Entry in edge transposition table.
    Notation:
        N(s, a) -> visit count for edge
        W(s, a) -> cumulative total reward
        Q(s, a) -> mean action value: W(s, a) / N(s, a)
    """

    def __init__(self, parent_hash: int, action: CanonicalAction):
        self._key = (parent_hash, action)
        self.N = 0
        self.W = 0.0

    @property
    def key(self) -> tuple[int, CanonicalAction]:
        return self._key

    @property
    def Q(self):
        if self.N == 0:
            return 0.0
        return self.W / self.N

    def update(self, result: float) -> None:
        """Update statistics"""
        self.N += 1
        self.W += result


class NodeEntry(BaseEntry[int]):
    """
    Entry in node transposition table
    Notation:
        N(s) -> visit count for node
        V(s) -> estimate evaluation of node (heuristic / NN)
        π(s) -> policy at node
        P(s, a) = π(s)[a] -> prior probability of action
    """

    def __init__(self, state_hash: int,
                 children: dict[CanonicalAction, int] = None,
                 priors: dict[CanonicalAction, float] = None):
        self._key = state_hash
        self.N: int = 0
        self.V: float = 0.0
        self.P: dict[CanonicalAction, float] = priors or {}
        self.children: dict[CanonicalAction, int] = children or {}
        self.is_terminal: bool = False

    @property
    def key(self):
        return self._key

    def update(self) -> None:
        self.N += 1


class TranspositionTable(Generic[K, E]):
    """Hash table for storing unique states"""

    def __init__(self, factory: Callable[[K], E]):
        self.table: dict[K, E] = {}
        self._factory = factory

    def __len__(self):
        return len(self.table)

    def get(self, key) -> E | None:
        return self.table.get(key)

    def put(self, key) -> E:
        if key not in self.table:
            self.table[key] = self._factory(key)
        return self.table[key]
