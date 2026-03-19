from collections import deque
from memory_profiler import memory_usage
import pygame
import time
from game.block import Block
from game.board import Board
from game.game_logic import GameLogic
from game.input_handler import InputHandler
from search_algorithms import Problem
from search_algorithms import a_star
from search_algorithms import breadth_first_search
from search_algorithms import depth_first_search
from search_algorithms import greedy_search
from search_algorithms import iterative_deepening_search
from search_algorithms import uniform_cost_search

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TILE_SIZE = 50
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
BLUE = (51, 51, 255)  # grid
GREEN = (0, 255, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)  # new path discovered by button
PURPLE = (128, 0, 128)  # button
TRANSPARENT_BLUE = (0, 0, 255, 128)  # glass floor
DARK_GRAY = (50, 50, 50)
LIGHT_BLUE = (173, 216, 230)  # sky
HOT_PINK = (255, 0, 127)  # block
WHITE_CLOUD = (204, 255, 204)  # clouds

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


# All buttons shape and color
class Button:
    def __init__(self, x, y, width, height, text, color, hover_color, text_color=BLACK):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.is_hovered = False

    def draw(self, screen):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, BLACK, self.rect, 2, border_radius=10)

        font = pygame.font.Font(None, 32)
        text_surface = font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def update(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)


# Running the game itself
class Renderer:
    def __init__(self, block, board, game_logic, input_handler):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Roll the Block!")
        self.clock = pygame.time.Clock()
        self.game_state = MAIN_MENU
        self.block = block
        self.board = board
        self.game_logic = game_logic
        self.input_handler = input_handler
        self.init_buttons()
        self.running = True
        self.algorithm = None
        self.solution = None
        self.algorithm_completed = False
        self.level_name = None

        self.animation_active = False
        self.animation_direction = None
        self.animation_progress = 0
        self.animation_speed = 0.1
        self.old_block_position = None
        self.target_block_position = None

    def init_buttons(self):
        center_x = SCREEN_WIDTH // 2
        # Main menu
        self.play_button = Button(center_x - 100, 200, 200, 50, "Play", WHITE_CLOUD, (204, 255, 204))
        self.rules_button = Button(center_x - 100, 270, 200, 50, "Rules", WHITE_CLOUD, (204, 255, 204))
        # AI or Human
        self.human_button = Button(center_x - 250, 200, 200, 50, "Human", WHITE_CLOUD, (204, 255, 204))
        self.ai_button = Button(center_x + 70, 200, 200, 50, "AI", WHITE_CLOUD, (204, 255, 204))

        # Back from rules
        self.back_button = Button(center_x - 100, 500, 200, 50, "Back", WHITE_CLOUD, (204, 255, 204))

        # Search algorithms
        self.solve_button = Button(20, 100, 100, 40, "Solve", WHITE_CLOUD, (204, 255, 204))
        self.algorithm_buttons = []
        algorithms = ["A*", "BFS", "DFS", "Greedy", "UCS", "IDS"]
        for i, algo in enumerate(algorithms):
            self.algorithm_buttons.append(Button(SCREEN_WIDTH // 2 - 70, 100 + i*50, 100, 40, algo, CYAN, (100, 255, 255)))

        # Level select buttons
        self.level_buttons = []
        for i in range(3):
            for j in range(3):
                level_num = i * 3 + j + 1
                x = 150 + j * 175
                y = 150 + i * 120
                self.level_buttons.append(Button(x, y, 125, 80, f"Level {level_num}", CYAN, (100, 255, 255)))

        # Game buttons
        self.menu_button = Button(SCREEN_WIDTH - 120, 20, 100, 40, "Menu", WHITE_CLOUD, (204, 255, 204))
        self.restart_button = Button(SCREEN_WIDTH - 120, 70, 100, 40, "Restart", WHITE_CLOUD, (204, 255, 204))
        self.next_level_button = Button(SCREEN_WIDTH // 2 - 100, 400, 200, 50, "Next Level", BLUE, (51, 51, 255))
        self.retry_button = Button(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 50, 200, 50, "Try Again", YELLOW, (225, 255, 100))

    def initialize_level(self, level_name, AI=False):
        self.current_level = level_name
        self.board = Board(level_name)
        x, y = self.board.level.start
        self.block = Block(x, y)
        self.game_logic = GameLogic(self.block, self.board)
        self.input_handler = InputHandler(self.block, self.board, self.game_logic, self)

        # Update the layout with the initial block position
        self.board.refresh_layout(self.block)

        self.calculate_camera_offset()

        if AI and not self.algorithm_completed:
            if self.board.level.button:
                layout_only = False
            else:
                layout_only = True
            problem = Problem(self.block, self.board, layout_only=layout_only)

            match self.algorithm:
                case "a*":
                    start = time.perf_counter()
                    solution_node = a_star(problem)
                    # mem_usage, solution_node = memory_usage((a_star, (problem,)), retval=True)
                    end = time.perf_counter()
                case "bfs":
                    start = time.perf_counter()
                    solution_node = breadth_first_search(problem)
                    # mem_usage, solution_node = memory_usage((breadth_first_search, (problem,)), retval=True)
                    end = time.perf_counter()
                case "dfs":
                    start = time.perf_counter()
                    solution_node = depth_first_search(problem)
                    # mem_usage, solution_node = memory_usage((depth_first_search, (problem,)), retval=True)
                    end = time.perf_counter()
                case "greedy":
                    start = time.perf_counter()
                    solution_node = greedy_search(problem)
                    # mem_usage, solution_node = memory_usage((greedy_search, (problem,)), retval=True)
                    end = time.perf_counter()
                case "ucs":
                    start = time.perf_counter()
                    solution_node = uniform_cost_search(problem)
                    # mem_usage, solution_node = memory_usage((uniform_cost_search, (problem,)), retval=True)
                    end = time.perf_counter()
                case "ids":
                    start = time.perf_counter()
                    solution_node = iterative_deepening_search(problem)
                    # mem_usage, solution_node = memory_usage((iterative_deepening_search, (problem,)), retval=True)
                    end = time.perf_counter()

            print(f"Algorithm {self.algorithm} took {(end - start)*1000:.6f} ms")
            # print(f"Peak Memory usage: {max(mem_usage):.2f} MiB")

            if solution_node is not None:
                self.solution = deque()
                prev_node = solution_node.parent
                self.solution.appendleft(solution_node.action)

                while prev_node is not None:
                    self.solution.appendleft(prev_node.action)
                    prev_node = prev_node.parent

                self.solution.popleft()
                self.algorithm_completed = True

    def calculate_camera_offset(self):
        level_pixel_width = len(self.board.level.layout[0]) * TILE_SIZE
        level_pixel_height = len(self.board.level.layout) * TILE_SIZE
        self.camera_offset_x = (SCREEN_WIDTH - level_pixel_width) // 2
        self.camera_offset_y = (SCREEN_HEIGHT - level_pixel_height) // 2

    def draw(self):
        self.screen.fill(LIGHT_BLUE)

        if self.game_state == MAIN_MENU:
            self.draw_main_menu()
        elif self.game_state == AI_OR_HUMAN:
            self.draw_ai_or_human()
        elif self.game_state == ALGORITHMS:
            self.draw_algorithms()
        elif self.game_state == RULES:
            self.draw_rules_screen()
        elif self.game_state == LEVEL_SELECT or self.game_state == ALGORITHMS_LEVEL_SELECT:
            self.draw_level_select()
        elif self.game_state == PLAYING or self.game_state == AI_PLAYING:
            self.draw_level()
        elif self.game_state == GAME_OVER:
            self.draw_level()
            self.draw_game_over()
        elif self.game_state == LEVEL_COMPLETE or self.game_state == AI_LEVEL_COMPLETE:
            self.draw_level()
            self.draw_level_complete()

        pygame.display.flip()

    # GAME STATE 0 - MAIN_MENU
    def handle_main_menu(self, mouse_pos):
        self.play_button.update(mouse_pos)
        self.rules_button.update(mouse_pos)

        if self.play_button.is_clicked(mouse_pos):
            self.game_state = AI_OR_HUMAN
        elif self.rules_button.is_clicked(mouse_pos):
            self.game_state = RULES

    def draw_main_menu(self):
        # Draw title
        font = pygame.font.Font(None, 72)
        title = font.render("Roll the Block", True, BLUE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(title, title_rect)
        # Draw buttons
        self.play_button.draw(self.screen)
        self.rules_button.draw(self.screen)

    # GAME_STATE 1 - RULES
    def handle_rules_screen(self, mouse_pos):
        self.back_button.update(mouse_pos)

        if self.back_button.is_clicked(mouse_pos):
            self.game_state = MAIN_MENU

    def draw_rules_screen(self):
        # Draw title
        font = pygame.font.Font(None, 40)
        title = font.render("Game Rules", True, BLUE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 50))
        self.screen.blit(title, title_rect)

        rules = [
            "MOVEMENT KEYS:"
            "   WASD or ARROWS",
            "",
            "BLOCK STATES:",
            "   -Upright: Can be on regular floor,",
            "                     but not on glass floor",
            "   -Horizontal/Vertical: Can be on any type of floor",
            "",
            "GAME ELEMENTS:",
            "   -Blue tile: Regular Floor",
            "   -Green tile: Goal",
            "   -Yellow tile: Button that activates hiddent paths",
            "   -Black tile: Void",
            "   -Glass Floor: The block can only traverse it on the",
            "                             horizontal/vertical states",
        ]

        font = pygame.font.Font(None, 24)
        for i, line in enumerate(rules):
            text = font.render(line, True, BLACK)
            self.screen.blit(text, (100, 120 + i * 25))

        # Draw back button
        self.back_button.draw(self.screen)

    # GAME_STATE 2 - LEVEL_SELECT
    def handle_level_select(self, mouse_pos):
        self.back_button.update(mouse_pos)

        if self.back_button.is_clicked(mouse_pos):
            self.game_state = MAIN_MENU

        for i, button in enumerate(self.level_buttons):
            button.update(mouse_pos)
            if button.is_clicked(mouse_pos):
                self.level_name = f"LEVEL{i+1}"
                if self.game_state == ALGORITHMS_LEVEL_SELECT:
                    self.game_state = ALGORITHMS
                else:
                    self.initialize_level(self.level_name)
                    self.game_state = PLAYING

    def draw_level_select(self):
        # Draw title
        font = pygame.font.Font(None, 48)
        title = font.render("Select Level", True, BLUE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 60))
        self.screen.blit(title, title_rect)

        # Draw level buttons
        for button in self.level_buttons:
            button.draw(self.screen)

        # Draw back button
        self.back_button.draw(self.screen)

    # GAME_STATE 3 - PLAYING
    def handle_playing(self, mouse_pos):
        self.menu_button.update(mouse_pos)
        self.restart_button.update(mouse_pos)

        if self.menu_button.is_clicked(mouse_pos):
            self.game_state = MAIN_MENU
        elif self.restart_button.is_clicked(mouse_pos):
            self.initialize_level(self.current_level)

        if self.game_logic.game_over:
            self.game_state = GAME_OVER

    # GAME_STATE 4 - GAME_OVER
    def handle_game_over(self, mouse_pos):
        self.restart_button.update(mouse_pos)
        self.menu_button.update(mouse_pos)
        self.retry_button.update(mouse_pos)

        if self.retry_button.is_clicked(mouse_pos):
            self.initialize_level(self.current_level)
            self.game_state = PLAYING
        elif self.menu_button.is_clicked(mouse_pos):
            self.game_state = MAIN_MENU

    def draw_game_over(self):
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        # Game over text
        font = pygame.font.Font(None, 72)
        text = font.render("Game Over", True, RED)
        text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 -50))
        self.screen.blit(text, text_rect)

        # Buttons
        self.retry_button.draw(self.screen)

    # GAME_STATE 5 - LEVEL_COMPLETE
    def handle_level_complete(self, mouse_pos):
        self.menu_button.update(mouse_pos)
        self.next_level_button.update(mouse_pos)

        if self.next_level_button.is_clicked(mouse_pos):
            if self.game_state == AI_LEVEL_COMPLETE:
                self.game_state = ALGORITHMS_LEVEL_SELECT
            else:
                self.board.switch_level()
                next_level = self.board.level.level_name
                self.initialize_level(next_level)
                self.game_state = PLAYING
        elif self.menu_button.is_clicked(mouse_pos):
            self.game_state = MAIN_MENU

    def draw_level_complete(self):
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        # Level complete text
        font = pygame.font.Font(None, 72)
        text = font.render("Level Complete!", True, RED)
        text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 -50))
        self.screen.blit(text, text_rect)

        # Display move count
        font = pygame.font.Font(None, 36)
        moves_text = font.render(f"Moves: {self.block.move_counter}", True, WHITE)
        moves_rect = moves_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(moves_text, moves_rect)

        # Buttons
        self.next_level_button.draw(self.screen)

        self.menu_button.update(pygame.mouse.get_pos())
        self.menu_button.draw(self.screen)

    # GAME_STATE 6 - AI_OR_HUMAN
    def handle_ai_or_human(self, mouse_pos):
        self.back_button.update(mouse_pos)
        self.human_button.update(mouse_pos)
        self.ai_button.update(mouse_pos)

        if self.back_button.is_clicked(mouse_pos):
            self.game_state = MAIN_MENU
        elif self.human_button.is_clicked(mouse_pos):
            self.game_state = LEVEL_SELECT
        elif self.ai_button.is_clicked(mouse_pos):
            self.game_state = ALGORITHMS_LEVEL_SELECT

    def draw_ai_or_human(self):
        # Draw title
        font = pygame.font.Font(None, 48)
        title = font.render("Play as Human or AI?", True, BLUE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 60))
        self.screen.blit(title, title_rect)

        # Draw buttons
        self.human_button.draw(self.screen)
        self.ai_button.draw(self.screen)
        self.back_button.draw(self.screen)

    # GAME_STATE 8 - ALGORITHMS
    def handle_algorithms(self, mouse_pos):
        self.back_button.update(mouse_pos)
        for button in self.algorithm_buttons:
            button.update(mouse_pos)

        if self.back_button.is_clicked(mouse_pos):
            self.game_state = AI_OR_HUMAN
        for button in self.algorithm_buttons:
            for i, button in enumerate(self.algorithm_buttons):
                button.update(mouse_pos)
                if button.is_clicked(mouse_pos):
                    self.algorithm = button.text.lower()
                    self.initialize_level(self.level_name, AI=True)
                    self.game_state = AI_PLAYING

    def draw_algorithms(self):
        # Draw title
        font = pygame.font.Font(None, 48)
        title = font.render("Choose the search algorithm", True, BLUE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 60))
        self.screen.blit(title, title_rect)

        # Draw buttons
        for button in self.algorithm_buttons:
            button.draw(self.screen)

    def start_animation(self, direction):
        self.animation_active = True
        self.animation_direction = direction
        self.animation_progress = 0
        self.old_block_position = (self.block.x1, self.block.y1, self.block.x2, self.block.y2)

        # Temporary block used to calculate following moves
        temp_block = Block(self.block.x1, self.block.y1)
        temp_block.x2 = self.block.x2
        temp_block.y2 = self.block.y2
        temp_block.orientation = self.block.orientation
        temp_block.move(direction)

        self.target_block_position = (temp_block.x1, temp_block.y1, temp_block.x2, temp_block.y2)

    def draw_solve_options(self):
        if hasattr(self, 'show_solution') and self.show_solution:
            font = pygame.font.Font(None, 24)
            text = font.render(f"Solving... Step {self.solution_index}/{len(self.solution_actions)}", True, BLACK)
            self.screen.blit(text, (20, 150))

        self.solve_button.draw(self.screen)

    def draw_level(self):
        # Draw the game grid
        layout = self.board.level.layout

        for i in range(self.board.level.height):
            for j in range(self.board.level.width):
                x = j * TILE_SIZE + self.camera_offset_x
                y = i * TILE_SIZE + self.camera_offset_y

                match layout[i][j]:
                    case -1:  # Void
                        pygame.draw.rect(self.screen, BLACK, (x,y, TILE_SIZE, TILE_SIZE))
                    case 0:  # Regular floor
                        pygame.draw.rect(self.screen, BLUE, (x, y, TILE_SIZE, TILE_SIZE))
                        pygame.draw.rect(self.screen, BLACK, (x, y, TILE_SIZE, TILE_SIZE), 1)
                    case 3:  # Glass floor
                        pygame.draw.rect(self.screen, CYAN, (x, y, TILE_SIZE, TILE_SIZE))
                        pygame.draw.rect(self.screen, BLACK, (x, y, TILE_SIZE, TILE_SIZE), 1)
                    case 4:  # Button
                        pygame.draw.rect(self.screen, YELLOW, (x, y, TILE_SIZE, TILE_SIZE))
                        pygame.draw.rect(self.screen, BLACK, (x, y, TILE_SIZE, TILE_SIZE), 1)
                    case 7:  # Goal
                        pygame.draw.rect(self.screen, GREEN, (x, y, TILE_SIZE, TILE_SIZE))
                        pygame.draw.rect(self.screen, BLACK, (x, y, TILE_SIZE, TILE_SIZE), 1)
                    case 2 | 1:  # Block
                        pygame.draw.rect(self.screen, HOT_PINK, (x, y, TILE_SIZE, TILE_SIZE))
                        pygame.draw.rect(self.screen, BLACK, (x, y, TILE_SIZE, TILE_SIZE), 1)

        # Draw UI elements
        if self.game_state != AI_PLAYING:
            self.menu_button.draw(self.screen)
            self.restart_button.draw(self.screen)

        # Draw level information
        font = pygame.font.Font(None, 32)
        level_text = font.render(f"Level: {self.current_level.replace('LEVEL', '')}", True, WHITE_CLOUD)
        self.screen.blit(level_text, (20, 20))

        moves_text = font.render(f"Moves: {self.block.move_counter}", True, WHITE_CLOUD)
        self.screen.blit(moves_text, (20, 60))

        if self.game_state == AI_PLAYING and self.solution:
            self.block.move(self.solution.popleft())
            self.board.refresh_layout(self.block)
            pygame.time.delay(1000)
        elif self.solution is not None and not self.solution:
            pygame.time.delay(1000)
            self.solution = None
            self.algorithm = None
            self.algorithm_completed = False
            self.game_state = AI_LEVEL_COMPLETE

    def update_animation(self):
        pygame.display.flip()

    def run(self):
        while self.running:
            self.clock.tick(60)
            self.running = self.input_handler.handle_events()
            if self.game_logic.game_over:
                self.game_state = GAME_OVER

            if self.game_logic.level_completed:
                self.game_logic.level_completed = False
                if self.game_state == PLAYING:
                    self.game_state = LEVEL_COMPLETE
                elif self.game_state == AI_PLAYING:
                    self.game_state = AI_LEVEL_COMPLETE

            self.draw()
            self.update_animation()
