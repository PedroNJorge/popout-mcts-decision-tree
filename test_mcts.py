from src import MCTS, PopOut

if __name__ == "__main__":
    game = PopOut()
    game.player   = 0b0000000000000000000000000110000000000000000000000
    game.opponent = 0b0000000000000000000000000001000000000000010000001
    print(game)
    mcts = MCTS(exploration_constant=1.2, max_simulations=100000)
    policy = mcts.search(game, show_progress=True)
    print("Action probabilities:")
    for move, prob in sorted(policy.items(), key=lambda x: -x[1])[:]:
        print(f"  {move}: {prob:.3f}")

    """
    for c in [1.0, 1.1, 1.2, 1.3]:
        print(f"C = {c}")
        for s in [1000, 10000, 50000]:
            mcts = MCTS(exploration_constant=c, max_simulations=s)
            policy = mcts.search(game, show_progress=True)
            print("Action probabilities:")
            for move, prob in sorted(policy.items(), key=lambda x: -x[1])[:]:
                print(f"  {move}: {prob:.3f}")
    """
