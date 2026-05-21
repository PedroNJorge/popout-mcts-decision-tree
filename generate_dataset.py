import csv
import os
import random
from tqdm import tqdm
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


def self_play_game(mcts: MCTS, simulations: int = 800, pbar=None):
    """
    Play one game to completion using MCTS.
    At each step:
      - run search(state, simulations)
      - record the full probability distribution (probs) over all actions
      - sample next move from the returned PMF
      - clear mcts between moves

    Returns list of (state_hash, game_copy_at_that_state, action) and num_ply
    for every move, where action is a random sample from MCTS PMF
    """
    game = PopOut()
    ply = []  # list of tuples (state_hash, state_snapshot, chosen_action)

    max_ply = 200
    for i in range(1, max_ply + 1):
        if pbar:
            pbar.set_postfix({
                'Ply': i,
                'Move': (i + 1) >> 1
            })
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

        # Store snapshot + move
        ply.append((game.copy(), chosen))

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

    return ply, i


def generate_dataset(n_games: int = 100,
                     simulations: int = 800,
                     output_path: str = 'popout_dataset.csv'):
    mcts = MCTS(exploration_constant=1.414, max_simulations=simulations)

    pbar = tqdm(total=n_games, desc="MCTS Self-Play Games",
                unit="game")

    # Build CSV
    feature_cols = []
    for col in range(COLS):
        for row in range(ROWS):
            feature_cols.append(f"cell_r{row}c{col}")

    action_cols = []
    for atype in ['drop', 'pop']:
        for col in range(COLS):
            action_cols.append(f"('{atype}', {col})")
    header = feature_cols + action_cols + ["best_action"]

    # Check if file exists and decide mode
    file_exists = os.path.isfile(output_path)
    mode = 'a' if file_exists else 'w'  # 'a' for append, 'w' for write

    written = 0
    with open(output_path, mode, newline='') as f:
        writer = csv.writer(f)

        if mode == 'w':
            writer.writerow(header)

        move_avg = 0
        first_player_wins = 0
        # MCTS Self-play
        for game_idx in range(1, n_games + 1):
            game = PopOut()
            first_player_id = game.cur_player

            max_ply = 200
            for i in range(1, max_ply + 1):
                current_move = (i + 1) >> 1

                win_pct = (first_player_wins / (game_idx - 1)) * 100 if game_idx > 1 else 0
                pbar.set_postfix({
                    'Ply': i,
                    'Move': current_move,
                    'MoveAvg': f"{(move_avg * (game_idx - 1) + current_move) / game_idx:.2f}",
                    'P1 Win': f"{win_pct:.1f}%"
                })
                winner = game.get_winner()
                if not game.get_valid_actions() or winner is not None:
                    first_player_wins += (winner == first_player_id)
                    break

                # Apply MCTS and sample next move from its PMF
                probs = mcts.search(game, simulations=simulations)

                # Build probability vector of ALL actions from MCTS
                probs_vector = []
                for atype in ['drop', 'pop']:
                    for col in range(COLS):
                        p = probs.get((atype, col), 0.0)
                        probs_vector.append(p)

                actions = list(probs.keys())
                weights = [probs[a] for a in actions]
                chosen = random.choices(actions, weights=weights, k=1)[0]

                # Write move in csv
                X = encode_state(game)
                writer.writerow([*X, *probs_vector, chosen])
                written += 1

                if written % 10000 == 0:
                    f.flush()

                # Apply move
                atype, col = chosen
                if atype == 'drop':
                    valid_move, winner = game.drop_piece(col)
                else:
                    valid_move, winner = game.popout_piece(col)
                assert valid_move is not None

                mcts.clear()  # Clear for next turn

                if winner is not None:
                    first_player_wins += (winner == first_player_id)
                    break

            mcts.clear()
            move_avg = (move_avg * (game_idx - 1) + current_move) / game_idx
            pbar.update(1)
        pbar.close()

    print(f"\nWrote {written} rows into '{output_path}'.")
    print(f"First player win rate: {(first_player_wins / n_games) * 100:.1f}% ({first_player_wins}/{n_games})")
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
