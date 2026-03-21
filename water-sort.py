import copy
import random
import pygame
from project import apply_move as logic_apply_move, is_goal, to_state, valid_moves
from search import bfs, dfs, iddfs, ucs

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
MODE_HUMAN = 'HUMANO'
MODE_AI = 'IA'
ALGORITHMS = ['BFS', 'DFS', 'IDDFS', 'UCS']
DFS_DEPTH_LIMIT = 30
IDDFS_MAX_DEPTH = 30
DEFAULT_TUBES = 6


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
status_message = 'Escolher modo: Humano ou IA.'
metrics_message = ''

ai_moves = []
ai_animating = False
ai_move_index = 0
ai_next_move_tick = 0
ai_last_result = None
ai_last_algorithm = ''
ai_metrics_printed = False


# select a number of tubes and pick random colors upon new game setup
def generate_start():
    tubes_number = DEFAULT_TUBES
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
    state = to_state(colors)
    move = (selected_rect_idx, destination)

    # Internal validation with valid_moves (not shown to the player).
    if move not in valid_moves(state, capacity=TUBE_CAPACITY):
        return colors

    next_state = logic_apply_move(state, move, capacity=TUBE_CAPACITY)
    return [list(tube) for tube in next_state]


# check if every non-empty tube is full and monochromatic. That's how we win
def check_victory(colors):
    return is_goal(to_state(colors), capacity=TUBE_CAPACITY)


def reset_ai(clear_metrics=False):
    global ai_moves, ai_animating, ai_move_index, ai_next_move_tick, metrics_message
    global ai_last_result, ai_last_algorithm, ai_metrics_printed

    ai_moves = []
    ai_animating = False
    ai_move_index = 0
    ai_next_move_tick = 0
    ai_last_result = None
    ai_last_algorithm = ''
    ai_metrics_printed = False

    if clear_metrics:
        metrics_message = ''


def print_ai_metrics(algorithm, result):
    print()
    print('===== IA Metrics =====')
    print(f'Algorithm: {algorithm}')
    print(f'Number of moves: {len(result.moves)}')
    print(f'Numero de states: {result.expanded}')
    print(f'Tempo demorado: {result.time_sec:.4f}s')
    print('======================')


def set_mode(mode):
    global mode_selected, game_mode, selected, select_rect, status_message
    mode_selected = True
    game_mode = mode
    selected = False
    select_rect = 100
    reset_ai(clear_metrics=False)

    if mode == MODE_HUMAN:
        status_message = 'Modo Humano ativo.'
    else:
        status_message = 'Modo IA ativo. Escolhe algoritmo e clica em Correr IA.'


def reset_to_initial():
    global tube_colors, selected, select_rect, status_message

    if not initial_colors:
        return

    tube_colors = copy.deepcopy(initial_colors)
    selected = False
    select_rect = 100
    reset_ai(clear_metrics=False)
    status_message = 'Tabuleiro reiniciado.'


def start_ai_solver():
    global ai_moves, ai_animating, ai_move_index, ai_next_move_tick
    global status_message, metrics_message, selected, select_rect
    global ai_last_result, ai_last_algorithm, ai_metrics_printed

    if game_mode != MODE_AI:
        status_message = 'Seleciona modo IA primeiro.'
        return
    if ai_animating:
        return

    current_state = to_state(tube_colors)
    if is_goal(current_state, TUBE_CAPACITY):
        status_message = 'O puzzle ja esta resolvido.'
        return

    algorithm = ALGORITHMS[selected_algorithm_idx]
    if algorithm == 'BFS':
        result = bfs(current_state, TUBE_CAPACITY)
    elif algorithm == 'DFS':
        result = dfs(current_state, TUBE_CAPACITY, depth_limit=DFS_DEPTH_LIMIT)
    elif algorithm == 'IDDFS':
        result = iddfs(current_state, TUBE_CAPACITY, max_depth=IDDFS_MAX_DEPTH)
    elif algorithm == 'UCS':
        result = ucs(current_state, TUBE_CAPACITY)
    else:
        status_message = f'Algoritmo {algorithm} nao implementado.'
        return

    metrics_message = (
        f'{algorithm} | solved={result.solved} | moves={len(result.moves)} | '
        f'expanded={result.expanded} | generated={result.generated} | '
        f'max_frontier={result.max_frontier} | time={result.time_sec:.4f}s'
    )

    ai_last_result = result
    ai_last_algorithm = algorithm
    ai_metrics_printed = False

    if not result.solved:
        status_message = f'{algorithm}: sem solucao para este tabuleiro.'
        print_ai_metrics(ai_last_algorithm, ai_last_result)
        ai_metrics_printed = True
        return

    ai_moves = result.moves
    ai_move_index = 0
    selected = False
    select_rect = 100

    if not ai_moves:
        status_message = f'{algorithm}: ja estava resolvido.'
        print_ai_metrics(ai_last_algorithm, ai_last_result)
        ai_metrics_printed = True
        return

    ai_animating = True
    ai_next_move_tick = pygame.time.get_ticks() + AI_STEP_DELAY_MS
    status_message = f'{algorithm}: solucao encontrada ({len(ai_moves)} movimentos).'


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
            status_message = 'IA terminou: puzzle resolvido.'
        else:
            status_message = 'IA terminou.'

        if ai_last_result is not None and not ai_metrics_printed:
            print_ai_metrics(ai_last_algorithm, ai_last_result)
            ai_metrics_printed = True
        return

    src, dst = ai_moves[ai_move_index]
    current_state = to_state(tube_colors)

    try:
        next_state = logic_apply_move(current_state, (src, dst), TUBE_CAPACITY)
    except (ValueError, IndexError):
        ai_animating = False
        status_message = f'IA interrompida: movimento invalido T{src} -> T{dst}.'
        return

    tube_colors = [list(tube) for tube in next_state]
    ai_move_index += 1
    status_message = f'IA move {ai_move_index}/{len(ai_moves)}: T{src} -> T{dst}'
    ai_next_move_tick = now + AI_STEP_DELAY_MS


def build_menu_layout():
    menu_x = GAME_WIDTH + 25
    menu_w = WIDTH - menu_x - 20
    panel = pygame.Rect(menu_x, 15, menu_w, HEIGHT - 30)

    mode_human_btn = pygame.Rect(menu_x + 20, 95, menu_w - 40, 40)
    mode_ai_btn = pygame.Rect(menu_x + 20, 145, menu_w - 40, 40)
    reset_btn = pygame.Rect(menu_x + 20, 195, menu_w - 40, 40)
    algorithm_btn = pygame.Rect(menu_x + 20, 245, menu_w - 40, 40)
    run_btn = pygame.Rect(menu_x + 20, 295, menu_w - 40, 44)

    return {
        'panel': panel,
        'mode_human_btn': mode_human_btn,
        'mode_ai_btn': mode_ai_btn,
        'reset_btn': reset_btn,
        'algorithm_btn': algorithm_btn,
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
    algorithm_btn = layout['algorithm_btn']
    run_btn = layout['run_btn']

    pygame.draw.rect(screen, (25, 25, 25), panel, border_radius=14)

    title = font.render('Escolher modo', True, 'white')
    screen.blit(title, title.get_rect(center=(panel.centerx, panel.y + 28)))

    subtitle = small_font.render('Humano ou IA', True, (220, 220, 220))
    screen.blit(subtitle, subtitle.get_rect(center=(panel.centerx, panel.y + 54)))

    draw_button(mode_human_btn, 'Humano', selected=(game_mode == MODE_HUMAN))
    draw_button(mode_ai_btn, 'IA', selected=(game_mode == MODE_AI))
    draw_button(reset_btn, 'Reset')

    if game_mode == MODE_AI:
        algo_label = f'Algoritmo: {ALGORITHMS[selected_algorithm_idx]}'
        draw_button(algorithm_btn, algo_label, selected=True, enabled=not ai_animating)
        run_label = 'A correr IA...' if ai_animating else 'Correr IA'
        draw_button(run_btn, run_label, enabled=not ai_animating)

        tip = small_font.render('Clica no algoritmo para trocar.', True, (190, 190, 190))
        screen.blit(tip, (panel.x + 20, run_btn.y + 54))
    else:
        hint = small_font.render('Seleciona IA para correr algoritmo.', True, (190, 190, 190))
        screen.blit(hint, (panel.x + 20, algorithm_btn.y + 12))

    status_title = small_font.render('Estado:', True, (235, 235, 235))
    screen.blit(status_title, (panel.x + 20, panel.bottom - 130))
    draw_wrapped_text(status_message, panel.x + 20, panel.bottom - 108, panel.width - 40, small_font, (220, 220, 220), max_lines=3)

    if metrics_message:
        metrics_title = small_font.render('Metricas:', True, (235, 235, 235))
        screen.blit(metrics_title, (panel.x + 20, panel.bottom - 64))
        draw_wrapped_text(metrics_message, panel.x + 20, panel.bottom - 42, panel.width - 40, small_font, (220, 220, 220), max_lines=2)


# main game loop
run = True
while run:
    timer.tick(fps)

    if new_game:
        tubes, tube_colors = generate_start()
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
                status_message = 'A gerar novo tabuleiro...'
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

            if game_mode == MODE_AI:
                if menu_layout['algorithm_btn'].collidepoint(pos) and not ai_animating:
                    selected_algorithm_idx = (selected_algorithm_idx + 1) % len(ALGORITHMS)
                    status_message = f'Algoritmo selecionado: {ALGORITHMS[selected_algorithm_idx]}'
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




