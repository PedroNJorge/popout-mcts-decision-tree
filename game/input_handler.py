import pygame


# Game states
MAIN_MENU = 0
RULES = 1
LEVEL_SELECT = 2
PLAYING = 3
GAME_OVER = 4
LEVEL_COMPLETE = 5
AI_OR_HUMAN = 6
ALGORITHMS_LEVEL_SELECT = 7
ALGORITHMS = 8
AI_PLAYING = 9
AI_LEVEL_COMPLETE = 10


class InputHandler:
    def __init__(self, block, board, game_logic, renderer):
        self.block = block
        self.board = board
        self.game_logic = game_logic
        self.renderer = renderer

    def handle_events(self):
        for event in pygame.event.get():
            match event.type:
                case pygame.QUIT:
                    return False    # used to update run in main.py
                case pygame.KEYDOWN:
                    if self.renderer.game_state == PLAYING:
                        self.handle_keyboard(event)
                case pygame.MOUSEMOTION | pygame.MOUSEBUTTONDOWN:
                    self.handle_mouse(event)

        return True

    def handle_keyboard(self, event):
        if self.renderer.game_state != AI_PLAYING:
            match event.key:
                case pygame.K_w | pygame.K_UP:
                    self.block.move("up")
                case pygame.K_s | pygame.K_DOWN:
                    self.block.move("down")
                case pygame.K_a | pygame.K_LEFT:
                    self.block.move("left")
                case pygame.K_d | pygame.K_RIGHT:
                    self.block.move("right")

        self.board.refresh_layout(self.block)
        self.game_logic.update()

    def handle_mouse(self, event):
        mouse_pos = pygame.mouse.get_pos()

        if event.type == pygame.MOUSEBUTTONDOWN:
            match self.renderer.game_state:
                case 0:
                    self.renderer.handle_main_menu(mouse_pos)
                case 1:
                    self.renderer.handle_rules_screen(mouse_pos)
                case 2 | 7:
                    self.renderer.handle_level_select(mouse_pos)
                case 3 | 9:
                    self.renderer.handle_playing(mouse_pos)
                case 4:
                    self.renderer.handle_game_over(mouse_pos)
                case 5 | 10:
                    self.renderer.handle_level_complete(mouse_pos)
                case 6:
                    self.renderer.handle_ai_or_human(mouse_pos)
                case 8:
                    self.renderer.handle_algorithms(mouse_pos)
