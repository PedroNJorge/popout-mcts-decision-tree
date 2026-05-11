from src import MCTS, PopOut

if __name__ == "__main__":
    # Test with a game
    game = PopOut(first_player=0)
    mcts = MCTS(exploration_constant=1.414, max_simulations=10000)

    # Get best move
    move = mcts.get_best_move(game)
    print(f"Best move: {move}")

    # Get full policy
    print(game)
    policy = mcts.search(game, simulations=10000)
    print("\nAction probabilities:")
    for move, prob in sorted(policy.items(), key=lambda x: -x[1])[:]:
        print(f"  {move}: {prob:.3f}")

    print(f"\nTransposition table size: {len(mcts.tt.table)}")
