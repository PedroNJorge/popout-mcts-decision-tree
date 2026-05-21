from .base import Player
from collections import Counter
import random
import ast
import math
import pickle
import sys

def get_entropy(labels):
    if not labels:
        return 0.0
    entropy = 0.0
    counts = Counter(labels)
    total = len(labels)
    for count in counts.values():
        if count > 0:
            entropy -= (count / total) * math.log2(count / total)
    return entropy


def information_gain(data, labels, attribute_idx):
    """Returns the information gain of a certain attribute."""
    h_c = get_entropy(labels)
    subsets = {}
    for i, row in enumerate(data):
        key = row[attribute_idx]
        subsets.setdefault(key, []).append(labels[i])
    total = len(labels)
    conditional_entropy = 0.0
    for subset_labels in subsets.values():
        probability = len(subset_labels) / total
        conditional_entropy += probability * get_entropy(subset_labels)
    return h_c - conditional_entropy

class DecisionTreeNode:
    def __init__(self, is_leaf=False, label=None, feature_idx=None):
        self.is_leaf = is_leaf
        self.label = label
        self.feature_idx = feature_idx
        self.children = {}


def id3(data, labels, feature_indices, depth=0, max_depth=None):
    if len(set(labels)) == 1:
        return DecisionTreeNode(is_leaf=True, label=labels[0])
    if not feature_indices or (max_depth is not None and depth >= max_depth):
        majority = Counter(labels).most_common(1)[0][0]
        return DecisionTreeNode(is_leaf=True, label=majority)

    best_idx, best_gain = None, 0.0
    for idx in feature_indices:
        gain = information_gain(data, labels, idx)
        if gain > best_gain:
            best_gain, best_idx = gain, idx

    if best_idx is None:
        majority = Counter(labels).most_common(1)[0][0]
        return DecisionTreeNode(is_leaf=True, label=majority)

    node = DecisionTreeNode(feature_idx=best_idx)
    remaining = [idx for idx in feature_indices if idx != best_idx]

    for val in set(row[best_idx] for row in data):
        sub_data   = [data[i]   for i in range(len(data))   if data[i][best_idx] == val]
        sub_labels = [labels[i] for i in range(len(labels)) if data[i][best_idx] == val]
        node.children[val] = id3(sub_data, sub_labels, remaining, depth + 1, max_depth)

    return node

def predict(tree, sample):
    node = tree
    while not node.is_leaf:
        if node.feature_idx is None:
            return None
        val = sample[node.feature_idx]
        if val not in node.children:
            return None
        node = node.children[val]
    return node.label

class ID3Player(Player):
    def __init__(self, name: str, player_id: int, model_path: str = 'id3_model.pkl'):
        super().__init__(name, player_id)
        self.tree = None
        self.state_cols = []
        self.load(model_path)

    def load(self, path: str) -> None:
        sys.setrecursionlimit(10000)
        with open(path, 'rb') as f:
            self.tree, self.state_cols = pickle.load(f)

    def board_to_features(self, game_state) -> list:
        p_bits   = game_state.player
        opp_bits = game_state.opponent

        features = []
        for col in range(7):
            for row in range(6):
                bit = col * 7 + row
                if (p_bits >> bit) & 1:
                    features.append('player')
                elif (opp_bits >> bit) & 1:
                    features.append('opponent')
                else:
                    features.append('empty')
        return features
    
    def get_move(self, game_state) -> tuple[str, int]:
        valid_moves = game_state.get_valid_actions()
        if not valid_moves:
            return random.choice(game_state.get_valid_action())

        features  = self.board_to_features(game_state)
        raw_label = predict(self.tree, features)

        move = None
        if raw_label is not None:
            try:
                move = ast.literal_eval(raw_label)
            except (ValueError, SyntaxError):
                move = None

        if move in valid_moves:
            return move

        return valid_moves[0]