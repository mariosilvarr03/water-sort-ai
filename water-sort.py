import copy
import random
import pygame
from project import apply_move as logic_apply_move, is_goal, to_state, valid_moves
from search import (
    DEFAULT_HEURISTIC,
    astar,
    available_heuristics,
    bfs,
    dfs,
    greedy,
    iddfs,
    weighted_astar,
)

# initialize pygame
pygame.init()

# initialize game variables
WIDTH = 900
HEIGHT = 550
GAME_WIDTH = 550
screen = pygame.display.set_mode([WIDTH, HEIGHT])
pygame.display.set_caption('Water Sort PyGame')
font = pygame.font.Font('fonts/CashMarket-BoldRounded.ttf', 24)
small_font = pygame.font.Font('fonts/CashMarket-BoldRounded.ttf', 16)
fps = 60
timer = pygame.time.Clock()

color_choices = [
    'red', 'orange', 'light blue', 'dark blue', 'dark green', 'pink',
    'purple', 'dark gray', 'brown', 'light green', 'yellow', 'white'
]

TUBE_CAPACITY = 4
AI_STEP_DELAY_MS = 350
MODE_HUMAN = 'HUMAN'
MODE_AI = 'AI'
ALGORITHMS = ['BFS', 'DFS', 'IDDFS', 'GREEDY', 'A*', 'W-A*']
DFS_DEPTH_LIMIT = 30
IDDFS_MAX_DEPTH = 30

# Difficulty levels: (level_name, tube_count)
DIFFICULTY_LEVELS = [
    ('Level 1 (6 tubes)', 6),
    ('Level 2 (8 tubes)', 8),
    ('Level 3 (12 tubes)', 12),
]
DEFAULT_TUBES = 6
selected_difficulty_idx = 0  # Start with Level 1
AI_HEURISTIC = DEFAULT_HEURISTIC
WEIGHTED_ASTAR_WEIGHT = 1.5
HEURISTIC_OPTIONS = list(available_heuristics())
if not HEURISTIC_OPTIONS:
    HEURISTIC_OPTIONS = [DEFAULT_HEURISTIC]
if AI_HEURISTIC not in HEURISTIC_OPTIONS:
    AI_HEURISTIC = HEURISTIC_OPTIONS[0]
WEIGHT_OPTIONS = [1.2, 1.5, 2.0, 3.0]
if WEIGHTED_ASTAR_WEIGHT not in WEIGHT_OPTIONS:
    WEIGHT_OPTIONS.append(WEIGHTED_ASTAR_WEIGHT)


tube_colors = []
initial_colors = []
tubes = DEFAULT_TUBES
new_game = True
selected = False
tube_rects = []
select_rect = 100
win = False

mode_selected = False
game_mode = None
selected_algorithm_idx = 0
status_message = 'Choose a mode: Human or AI.'
metrics_message = ''

ai_moves = []
ai_animating = False
ai_move_index = 0
ai_next_move_tick = 0
ai_last_result = None
ai_last_algorithm = ''
ai_metrics_printed = False
ai_last_heuristic = ''
ai_last_weight = None

# Human mode helpers
move_history = []  # List of (source, dest, state_before) tuples for reverting moves
hint_message = ''  # Displays the next AI-suggested move


# select a number of tubes and pick random colors upon new game setup
def generate_start(num_tubes=None):
    if num_tubes is None:
        num_tubes = DIFFICULTY_LEVELS[selected_difficulty_idx][1]
    
    tubes_number = num_tubes
    tubes_colors = []
    available_colors = []
    for i in range(tubes_number):
        tubes_colors.append([])
        if i < tubes_number - 2:
            for _ in range(TUBE_CAPACITY):
                available_colors.append(i)
    for i in range(tubes_number - 2):
        for _ in range(TUBE_CAPACITY):
            color = random.choice(available_colors)
            tubes_colors[i].append(color)
            available_colors.remove(color)
    return tubes_number, tubes_colors


# draw all tubes and colors on screen, as well as indicating what tube was selected
def draw_tubes(tubes_num, tube_cols):
    tube_boxes = []
    tube_w = 65
    tube_h = 200
    block_h = 50
    margin_x = 20
    border_radius_bottle = 16
    border_radius_colors = 16

    if tubes_num % 2 == 0:
        top_count = tubes_num // 2
        bottom_count = tubes_num // 2
    else:
        top_count = tubes_num // 2 + 1
        bottom_count = tubes_num - top_count

    def compute_positions(count):
        if count == 0:
            return []
        if count == 1:
            x_start = GAME_WIDTH // 2 - tube_w // 2
            return [x_start]
        total_width = count * tube_w
        available = GAME_WIDTH - 2 * margin_x - total_width
        gap = available / (count - 1) if count > 1 else 0
        x_start = int((GAME_WIDTH - (total_width + gap * (count - 1))) / 2)
        return [int(x_start + i * (tube_w + gap)) for i in range(count)]

    top_num = compute_positions(top_count)
    bottom_num = compute_positions(bottom_count)

    top_y = 50
    bottom_y = 300

    for idx, x in enumerate(top_num):
        cols = tube_cols[idx] if idx < len(tube_cols) else []
        ncols = len(cols)
        for j in range(ncols):
            y = top_y + tube_h - block_h * (j + 1)
            rect = pygame.Rect(x, y, tube_w, block_h)
            col = color_choices[cols[j]]
            if ncols == 1:
                pygame.draw.rect(screen, col, rect, width=0, border_radius=border_radius_colors)
            else:
                if j == 0:
                    pygame.draw.rect(
                        screen,
                        col,
                        rect,
                        width=0,
                        border_top_left_radius=0,
                        border_top_right_radius=0,
                        border_bottom_left_radius=border_radius_colors,
                        border_bottom_right_radius=border_radius_colors,
                    )
                elif j == ncols - 1:
                    pygame.draw.rect(
                        screen,
                        col,
                        rect,
                        width=0,
                        border_top_left_radius=border_radius_colors,
                        border_top_right_radius=border_radius_colors,
                        border_bottom_left_radius=0,
                        border_bottom_right_radius=0,
                    )
                else:
                    pygame.draw.rect(screen, col, rect)

        tube_rect = pygame.Rect(x, top_y, tube_w, tube_h)
        pygame.draw.rect(screen, 'blue', tube_rect, 5, border_radius_bottle)
        if select_rect == idx:
            pygame.draw.rect(screen, 'green', tube_rect, 3, border_radius_bottle)
        tube_boxes.append(tube_rect)

    for k, x in enumerate(bottom_num):
        idx = top_count + k
        cols = tube_cols[idx] if idx < len(tube_cols) else []
        ncols = len(cols)
        for j in range(ncols):
            y = bottom_y + tube_h - block_h * (j + 1)
            rect = pygame.Rect(x, y, tube_w, block_h)
            col = color_choices[cols[j]]
            if ncols == 1:
                pygame.draw.rect(screen, col, rect, width=0, border_radius=border_radius_colors)
            else:
                if j == 0:
                    pygame.draw.rect(
                        screen,
                        col,
                        rect,
                        width=0,
                        border_top_left_radius=0,
                        border_top_right_radius=0,
                        border_bottom_left_radius=border_radius_colors,
                        border_bottom_right_radius=border_radius_colors,
                    )
                elif j == ncols - 1:
                    pygame.draw.rect(
                        screen,
                        col,
                        rect,
                        width=0,
                        border_top_left_radius=border_radius_colors,
                        border_top_right_radius=border_radius_colors,
                        border_bottom_left_radius=0,
                        border_bottom_right_radius=0,
                    )
                else:
                    pygame.draw.rect(screen, col, rect)

        tube_rect = pygame.Rect(x, bottom_y, tube_w, tube_h)
        pygame.draw.rect(screen, 'blue', tube_rect, 5, border_radius_bottle)
        if select_rect == idx:
            pygame.draw.rect(screen, 'green', tube_rect, 3, border_radius_bottle)
        tube_boxes.append(tube_rect)

    return tube_boxes


# apply one move using the shared logic module
def calc_move(colors, selected_rect_idx, destination):
    global move_history
    
    state = to_state(colors)
    move = (selected_rect_idx, destination)

    # Internal validation with valid_moves (not shown to the player).
    if move not in valid_moves(state, capacity=TUBE_CAPACITY):
        return colors

    # Record move in history before applying
    move_history.append((selected_rect_idx, destination, copy.deepcopy(colors)))
    
    next_state = logic_apply_move(state, move, capacity=TUBE_CAPACITY)
    return [list(tube) for tube in next_state]


# check if every non-empty tube is full and monochromatic. That's how we win
def check_victory(colors):
    return is_goal(to_state(colors), capacity=TUBE_CAPACITY)


def reset_ai(clear_metrics=False):
    global ai_moves, ai_animating, ai_move_index, ai_next_move_tick, metrics_message
    global ai_last_result, ai_last_algorithm, ai_metrics_printed
    global ai_last_heuristic, ai_last_weight

    ai_moves = []
    ai_animating = False
    ai_move_index = 0
    ai_next_move_tick = 0
    ai_last_result = None
    ai_last_algorithm = ''
    ai_metrics_printed = False


def go_back_one_step():
    """Revert the last move made by the player."""
    global tube_colors, move_history, hint_message, status_message
    
    if not move_history:
        status_message = 'No moves to undo.'
        return
    
    source, dest, state_before = move_history.pop()
    tube_colors = state_before
    hint_message = ''
    status_message = f'Reverted move: T{source} -> T{dest}'


def get_hint():
    """Get the next move suggested by BFS (optimal solution)."""
    global status_message, hint_message, tube_colors
    
    current_state = to_state(tube_colors)
    
    if is_goal(current_state, TUBE_CAPACITY):
        hint_message = 'The puzzle is already solved!'
        status_message = 'Hint: Already solved.'
        return
    
    # Use BFS to find optimal next move
    result = bfs(current_state, TUBE_CAPACITY)
    
    if not result.solved or not result.moves:
        hint_message = 'No solution found.'
        status_message = 'Hint: No solution found.'
        return
    
    # Get the first move from the solution
    src, dst = result.moves[0]
    hint_message = f'Hint: Tube {src+1} to Tube {dst+1}'
    status_message = f'Hint: T{src} -> T{dst} (from {len(result.moves)}-move solution)'


def reset_ai(clear_metrics=False):
    """Reset AI animation state and optionally clear metrics."""
    global ai_moves, ai_animating, ai_move_index, ai_next_move_tick, metrics_message
    global ai_last_result, ai_last_algorithm, ai_metrics_printed
    global ai_last_heuristic, ai_last_weight

    ai_moves = []
    ai_animating = False
    ai_move_index = 0
    ai_next_move_tick = 0
    ai_last_result = None
    ai_last_algorithm = ''
    ai_metrics_printed = False
    ai_last_heuristic = ''
    ai_last_weight = None

    if clear_metrics:
        metrics_message = ''


def print_ai_metrics(algorithm, result, heuristic_name='', weight=None):
    print()
    print('===== AI Metrics =====')
    print(f'Algorithm: {algorithm}')
    if heuristic_name:
        print(f'Heuristic: {heuristic_name}')
    if weight is not None:
        print(f'Weight: {weight:.2f}')
    print(f'Number of moves: {len(result.moves)}')
    print(f'Expanded states: {result.expanded}')
    print(f'Generated states: {result.generated}')
    print(f'Elapsed time: {result.time_sec:.4f}s')
    print('======================')


def set_mode(mode):
    global mode_selected, game_mode, selected, select_rect, status_message, move_history, hint_message
    mode_selected = True
    game_mode = mode
    selected = False
    select_rect = 100
    move_history = []
    hint_message = ''
    reset_ai(clear_metrics=False)

    if mode == MODE_HUMAN:
        status_message = 'Human mode active.'
    else:
        status_message = 'AI mode active. Choose an algorithm and click Run AI.'


def reset_to_initial():
    global tube_colors, selected, select_rect, status_message

    if not initial_colors:
        return

    tube_colors = copy.deepcopy(initial_colors)
    selected = False
    select_rect = 100
    reset_ai(clear_metrics=False)
    status_message = 'Board reset.'


def start_ai_solver():
    global ai_moves, ai_animating, ai_move_index, ai_next_move_tick
    global status_message, metrics_message, selected, select_rect
    global ai_last_result, ai_last_algorithm, ai_metrics_printed
    global ai_last_heuristic, ai_last_weight

    if game_mode != MODE_AI:
        status_message = 'Select AI mode first.'
        return
    if ai_animating:
        return

    current_state = to_state(tube_colors)
    if is_goal(current_state, TUBE_CAPACITY):
        status_message = 'The puzzle is already solved.'
        return

    algorithm = ALGORITHMS[selected_algorithm_idx]
    selected_heuristic = ''
    selected_weight = None
    if algorithm == 'BFS':
        result = bfs(current_state, TUBE_CAPACITY)
    elif algorithm == 'DFS':
        result = dfs(current_state, TUBE_CAPACITY, depth_limit=DFS_DEPTH_LIMIT)
    elif algorithm == 'IDDFS':
        result = iddfs(current_state, TUBE_CAPACITY, max_depth=IDDFS_MAX_DEPTH)
    elif algorithm == 'GREEDY':
        selected_heuristic = AI_HEURISTIC
        result = greedy(current_state, TUBE_CAPACITY, heuristic=selected_heuristic)
    elif algorithm == 'A*':
        selected_heuristic = AI_HEURISTIC
        result = astar(current_state, TUBE_CAPACITY, heuristic=selected_heuristic)
    elif algorithm == 'W-A*':
        selected_heuristic = AI_HEURISTIC
        selected_weight = WEIGHTED_ASTAR_WEIGHT
        result = weighted_astar(
            current_state,
            TUBE_CAPACITY,
            heuristic=selected_heuristic,
            weight=selected_weight,
        )
    else:
        status_message = f'Algorithm {algorithm} is not implemented.'
        return

    metric_parts = [
        algorithm,
        f'solved={result.solved}',
        f'moves={len(result.moves)}',
        f'execution time={result.time_sec:.4f}s',
    ]
    if selected_heuristic:
        metric_parts.append(f'h={selected_heuristic}')
    if selected_weight is not None:
        metric_parts.append(f'w={selected_weight:.2f}')
    metrics_message = ' | '.join(metric_parts)

    ai_last_result = result
    ai_last_algorithm = algorithm
    ai_last_heuristic = selected_heuristic
    ai_last_weight = selected_weight
    ai_metrics_printed = False

    if not result.solved:
        status_message = f'{algorithm}: no solution found for this board.'
        print_ai_metrics(ai_last_algorithm, ai_last_result, ai_last_heuristic, ai_last_weight)
        ai_metrics_printed = True
        return

    ai_moves = result.moves
    ai_move_index = 0
    selected = False
    select_rect = 100

    if not ai_moves:
        status_message = f'{algorithm}: the board was already solved.'
        print_ai_metrics(ai_last_algorithm, ai_last_result, ai_last_heuristic, ai_last_weight)
        ai_metrics_printed = True
        return

    ai_animating = True
    ai_next_move_tick = pygame.time.get_ticks() + AI_STEP_DELAY_MS
    status_message = f'{algorithm}: solution found ({len(ai_moves)} moves).'


def update_ai_animation():
    global tube_colors, ai_animating, ai_move_index, ai_next_move_tick, status_message
    global ai_last_result, ai_last_algorithm, ai_metrics_printed

    if not ai_animating:
        return

    now = pygame.time.get_ticks()
    if now < ai_next_move_tick:
        return

    if ai_move_index >= len(ai_moves):
        ai_animating = False
        if check_victory(tube_colors):
            status_message = 'AI finished: puzzle solved.'
        else:
            status_message = 'AI finished.'

        if ai_last_result is not None and not ai_metrics_printed:
            print_ai_metrics(ai_last_algorithm, ai_last_result, ai_last_heuristic, ai_last_weight)
            ai_metrics_printed = True
        return

    src, dst = ai_moves[ai_move_index]
    current_state = to_state(tube_colors)

    try:
        next_state = logic_apply_move(current_state, (src, dst), TUBE_CAPACITY)
    except (ValueError, IndexError):
        ai_animating = False
        status_message = f'AI interrupted: invalid move T{src} -> T{dst}.'
        return

    tube_colors = [list(tube) for tube in next_state]
    ai_move_index += 1
    status_message = f'AI move {ai_move_index}/{len(ai_moves)}: T{src} -> T{dst}'
    ai_next_move_tick = now + AI_STEP_DELAY_MS


def build_menu_layout():
    menu_x = GAME_WIDTH + 25
    menu_w = WIDTH - menu_x - 20
    panel = pygame.Rect(menu_x, 15, menu_w, HEIGHT - 30)

    mode_human_btn = pygame.Rect(menu_x + 20, 95, menu_w - 40, 40)
    mode_ai_btn = pygame.Rect(menu_x + 20, 140, menu_w - 40, 40)
    difficulty_btn = pygame.Rect(menu_x + 20, 185, menu_w - 40, 40)
    reset_btn = pygame.Rect(menu_x + 20, 230, menu_w - 40, 40)
    
    # Human mode buttons
    hint_btn = pygame.Rect(menu_x + 20, 275, (menu_w - 50) // 2, 40)
    go_back_btn = pygame.Rect(menu_x + 20 + (menu_w - 50) // 2 + 10, 275, (menu_w - 50) // 2, 40)
    
    # AI mode buttons
    algorithm_btn = pygame.Rect(menu_x + 20, 275, menu_w - 40, 40)
    heuristic_btn = pygame.Rect(menu_x + 20, 315, menu_w - 40, 40)
    weight_btn = pygame.Rect(menu_x + 20, 355, menu_w - 40, 40)
    run_btn = pygame.Rect(menu_x + 20, 395, menu_w - 40, 44)

    return {
        'panel': panel,
        'mode_human_btn': mode_human_btn,
        'mode_ai_btn': mode_ai_btn,
        'reset_btn': reset_btn,
        'difficulty_btn': difficulty_btn,
        'hint_btn': hint_btn,
        'go_back_btn': go_back_btn,
        'algorithm_btn': algorithm_btn,
        'heuristic_btn': heuristic_btn,
        'weight_btn': weight_btn,
        'run_btn': run_btn,
    }


def draw_button(rect, label, selected=False, enabled=True):
    if not enabled:
        bg = (80, 80, 80)
        fg = (170, 170, 170)
    elif selected:
        bg = (46, 160, 67)
        fg = (255, 255, 255)
    else:
        bg = (60, 60, 60)
        fg = (255, 255, 255)

    pygame.draw.rect(screen, bg, rect, border_radius=10)
    pygame.draw.rect(screen, (110, 110, 110), rect, 2, border_radius=10)
    text = small_font.render(label, True, fg)
    text_rect = text.get_rect(center=rect.center)
    screen.blit(text, text_rect)


def draw_wrapped_text(text, x, y, max_width, text_font, color, max_lines=3):
    words = text.split()
    lines = []
    current = ''

    for word in words:
        candidate = word if not current else f'{current} {word}'
        if text_font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    lines = lines[:max_lines]
    for i, line in enumerate(lines):
        rendered = text_font.render(line, True, color)
        screen.blit(rendered, (x, y + i * (text_font.get_height() + 2)))


def draw_menu(layout):
    panel = layout['panel']
    mode_human_btn = layout['mode_human_btn']
    mode_ai_btn = layout['mode_ai_btn']
    reset_btn = layout['reset_btn']
    difficulty_btn = layout['difficulty_btn']
    hint_btn = layout['hint_btn']
    go_back_btn = layout['go_back_btn']
    algorithm_btn = layout['algorithm_btn']
    heuristic_btn = layout['heuristic_btn']
    weight_btn = layout['weight_btn']
    run_btn = layout['run_btn']

    pygame.draw.rect(screen, (25, 25, 25), panel, border_radius=14)

    title = font.render('Choose Mode', True, 'white')
    screen.blit(title, title.get_rect(center=(panel.centerx, panel.y + 28)))

    subtitle = small_font.render('Human or AI', True, (220, 220, 220))
    screen.blit(subtitle, subtitle.get_rect(center=(panel.centerx, panel.y + 54)))

    draw_button(mode_human_btn, 'Human', selected=(game_mode == MODE_HUMAN))
    draw_button(mode_ai_btn, 'AI', selected=(game_mode == MODE_AI))
    
    # Difficulty button always visible
    difficulty_label = DIFFICULTY_LEVELS[selected_difficulty_idx][0]
    draw_button(difficulty_btn, difficulty_label, selected=True)
    
    draw_button(reset_btn, 'Reset')

    if game_mode == MODE_HUMAN:
        # Human mode: show Hint and Go Back buttons
        draw_button(hint_btn, 'Hint', enabled=True)
        draw_button(go_back_btn, 'Undo', enabled=True)
        
        # Show hint message if available
        if hint_message:
            hint_display = small_font.render(hint_message, True, (100, 200, 100))
            screen.blit(hint_display, (panel.x + 20, go_back_btn.bottom + 10))
    elif game_mode == MODE_AI:
        selected_algo = ALGORITHMS[selected_algorithm_idx]
        algo_label = f'Algorithm: {selected_algo}'
        heuristic_label = f'Heuristic: {AI_HEURISTIC}'
        weight_label = f'Weight: {WEIGHTED_ASTAR_WEIGHT:.2f}'

        draw_button(algorithm_btn, algo_label, selected=True, enabled=not ai_animating)
        draw_button(heuristic_btn, heuristic_label, selected=(selected_algo in {'GREEDY', 'A*', 'W-A*'}), enabled=not ai_animating)
        draw_button(weight_btn, weight_label, selected=(selected_algo == 'W-A*'), enabled=not ai_animating)

        run_label = 'Running AI...' if ai_animating else 'Run AI'
        draw_button(run_btn, run_label, enabled=not ai_animating)

    status_title = small_font.render('Status:', True, (235, 235, 235))
    screen.blit(status_title, (panel.x + 20, panel.bottom - 130))
    draw_wrapped_text(status_message, panel.x + 20, panel.bottom - 108, panel.width - 40, small_font, (220, 220, 220), max_lines=3)

    if metrics_message:
        metrics_title = small_font.render('Metrics:', True, (235, 235, 235))
        screen.blit(metrics_title, (panel.x + 20, panel.bottom - 64))
        draw_wrapped_text(metrics_message, panel.x + 20, panel.bottom - 42, panel.width - 40, small_font, (220, 220, 220), max_lines=2)


# main game loop
run = True
while run:
    timer.tick(fps)

    if new_game:
        tubes, tube_colors = generate_start(DIFFICULTY_LEVELS[selected_difficulty_idx][1])
        initial_colors = copy.deepcopy(tube_colors)
        new_game = False
        selected = False
        select_rect = 100
        reset_ai(clear_metrics=True)

    menu_layout = build_menu_layout()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False

        if event.type == pygame.KEYUP:
            if event.key == pygame.K_SPACE:
                reset_to_initial()
            elif event.key == pygame.K_RETURN:
                new_game = True
                status_message = 'Generating a new board...'
                reset_ai(clear_metrics=True)

        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = event.pos

            if menu_layout['mode_human_btn'].collidepoint(pos):
                set_mode(MODE_HUMAN)
                continue

            if menu_layout['mode_ai_btn'].collidepoint(pos):
                set_mode(MODE_AI)
                continue

            if menu_layout['reset_btn'].collidepoint(pos):
                reset_to_initial()
                continue

            # Difficulty button to change level (works in both modes)
            if menu_layout['difficulty_btn'].collidepoint(pos):
                selected_difficulty_idx = (selected_difficulty_idx + 1) % len(DIFFICULTY_LEVELS)
                new_game = True
                status_message = f'Difficulty changed to {DIFFICULTY_LEVELS[selected_difficulty_idx][0]}'
                continue

            if game_mode == MODE_HUMAN:
                # Human mode: Hint and Go Back buttons
                if menu_layout['hint_btn'].collidepoint(pos):
                    get_hint()
                    continue
                
                if menu_layout['go_back_btn'].collidepoint(pos):
                    go_back_one_step()
                    continue

            if game_mode == MODE_AI:
                if menu_layout['algorithm_btn'].collidepoint(pos) and not ai_animating:
                    selected_algorithm_idx = (selected_algorithm_idx + 1) % len(ALGORITHMS)
                    selected_algorithm = ALGORITHMS[selected_algorithm_idx]
                    if selected_algorithm in {'GREEDY', 'A*', 'W-A*'}:
                        status_message = f'Selected algorithm: {selected_algorithm} | h={AI_HEURISTIC}'
                        if selected_algorithm == 'W-A*':
                            status_message += f' | w={WEIGHTED_ASTAR_WEIGHT:.2f}'
                    else:
                        status_message = f'Selected algorithm: {selected_algorithm}'
                    continue

                if menu_layout['heuristic_btn'].collidepoint(pos) and not ai_animating:
                    h_idx = HEURISTIC_OPTIONS.index(AI_HEURISTIC) if AI_HEURISTIC in HEURISTIC_OPTIONS else -1
                    AI_HEURISTIC = HEURISTIC_OPTIONS[(h_idx + 1) % len(HEURISTIC_OPTIONS)]
                    status_message = f'Heuristic selected: {AI_HEURISTIC}'
                    continue

                if menu_layout['weight_btn'].collidepoint(pos) and not ai_animating:
                    w_idx = WEIGHT_OPTIONS.index(WEIGHTED_ASTAR_WEIGHT) if WEIGHTED_ASTAR_WEIGHT in WEIGHT_OPTIONS else -1
                    WEIGHTED_ASTAR_WEIGHT = WEIGHT_OPTIONS[(w_idx + 1) % len(WEIGHT_OPTIONS)]
                    status_message = f'Weight selected: {WEIGHTED_ASTAR_WEIGHT:.2f} (used by W-A*)'
                    continue

                if menu_layout['run_btn'].collidepoint(pos) and not ai_animating:
                    start_ai_solver()
                    continue

            if game_mode == MODE_HUMAN and not ai_animating:
                if not selected:
                    for item in range(len(tube_rects)):
                        if tube_rects[item].collidepoint(pos):
                            selected = True
                            select_rect = item
                            break
                else:
                    for item in range(len(tube_rects)):
                        if tube_rects[item].collidepoint(pos):
                            dest_rect = item
                            tube_colors = calc_move(tube_colors, select_rect, dest_rect)
                            selected = False
                            select_rect = 100
                            break

    update_ai_animation()
    win = check_victory(tube_colors)

    screen.fill('black')
    tube_rects = draw_tubes(tubes, tube_colors)
    draw_menu(menu_layout)

    if win:
        victory_text = font.render('Victory! Press Enter for a new board!', True, 'white')
        v_rect = victory_text.get_rect(center=(GAME_WIDTH // 2, HEIGHT // 2))
        screen.blit(victory_text, v_rect)

    controls_text = small_font.render('Space-Restart | Enter-New Board', True, 'white')
    controls_rect = controls_text.get_rect(center=(GAME_WIDTH // 2, HEIGHT - 20))
    screen.blit(controls_text, controls_rect)

    title_text = font.render('Water Sort', True, 'white')
    title_rect = title_text.get_rect(center=(GAME_WIDTH // 2, 20))
    screen.blit(title_text, title_rect)

    pygame.display.flip()

pygame.quit()




