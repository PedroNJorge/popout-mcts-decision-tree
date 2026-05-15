import csv
import random
from src.game import PopOut, ROWS, COLS
from src.mcts import MCTS
 
def encode_state(game: PopOut):
    features = []
    for row in range(ROWS):
        for col in range(COLS):
            bit_index = col * 7 + row
            mask = 1 << bit_index
            if game.player & mask:
                features.append("player")
            elif game.opponent & mask:
                features.append("opponent")
            else:
                features.append("empty")
    return features
 
def action_to_str(action):
    return f"{action[0]}_{action[1]}"
 
def str_to_action(s):
    parts = s.split("_")
    return (parts[0], int(parts[1]))
 
def self_play_game(mcts: MCTS, simulations: int = 800):
    """
    Play one game to completion using MCTS.
    At each step:
      - run search(state, simulations)
      - record the full probability distribution (probs) over all actions
      - sample next move from the returned PMF
      - clear mcts between moves
 
    Returns list of (state_hash, game_copy_at_that_state, probs)
    for every move, where probs is the full MCTS visit distribution.
    """
    game = PopOut()
    ply = []  # (state_hash, state_snapshot, chosen_action)
 
    max_moves = 200
    for _ in range(max_moves):
        if game.get_winner() is not None:
            break
        valid = game.get_valid_actions()
        if not valid:
            break
 
        probs = mcts.search(game, simulations=simulations)
 
        # Sample next move from the full distribution
        actions = list(probs.keys())
        weights = [probs[a] for a in actions]
        chosen = random.choices(actions, weights=weights, k=1)[0]
 
        # Store snapshot + full probs
        ply.append((game.zobrist._compute_hash(game.player, game.opponent, game.cur_player), game.copy(), chosen))
 
        # Apply move
        atype, col = chosen
        if atype == 'drop':
            valid_move, winner = game.drop_piece(col)
        else:
            valid_move, winner = game.popout_piece(col)
        assert valid_move is not None
 
        mcts.clear()
 
        if winner is not None:
            break
 
    return ply

def generate_dataset(n_games: int = 100,
                     simulations: int = 800,
                     output_path: str = 'popout_dataset.csv'):
    mcts = MCTS(exploration_constant=1.414, max_simulations=simulations)
    ply = []
 
    for game_idx in range(n_games):
        print(f"\n=== Game {game_idx + 1}/{n_games} ===")
        game_ply = self_play_game(mcts, simulations=simulations)
        ply.extend(game_ply)
        mcts.clear()

    # Build CSV
    feature_cols = []
    for col in range(COLS):
        for row in range(ROWS):
            feature_cols.append(f"cell_r{row}c{col}")
    header = feature_cols + ["best_action"]
 
    written = 0
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for _, state, action in ply:
            X = encode_state(state)
            Y = action_to_str(action)
            #for features, action in zip(X, Y):
            #    writer.writerow([*features, action])
            writer.writerow([*X, action])
            written += 1
 
    print(f"\nDataset written to '{output_path}' — {written} rows.")
    return output_path
 
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate PopOut MCTS dataset")
    parser.add_argument("--games",   type=int, default=50,
                        help="Number of self-play games (default: 50)")
    parser.add_argument("--sims",    type=int, default=800,
                        help="MCTS simulations per move (default: 800)")
    parser.add_argument("--output",  type=str, default="popout_dataset.csv",
                        help="Output CSV path")
    parser.add_argument("--seed",    type=int, default=42)
    args = parser.parse_args()
    random.seed(args.seed)
    out = generate_dataset(n_games=args.games,
                           simulations=args.sims,
                           output_path=args.output)