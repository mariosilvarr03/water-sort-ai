import copy
import random
import pygame

# initialize pygame
pygame.init()

# initialize game variables
WIDTH = 900
HEIGHT = 550
GAME_WIDTH = 550
screen = pygame.display.set_mode([WIDTH, HEIGHT])
pygame.display.set_caption('Water Sort PyGame')
font = pygame.font.Font('fonts/CashMarket-BoldRounded.ttf', 24)
# smaller font for helper text (fallback to system font if TTF missing)
small_font = pygame.font.Font('fonts/CashMarket-BoldRounded.ttf', 16)
fps = 60
timer = pygame.time.Clock()
color_choices = ['red', 'orange', 'light blue', 'dark blue', 'dark green', 'pink', 'purple', 'dark gray',
                 'brown', 'light green', 'yellow', 'white']
tube_colors = []
initial_colors = []
tubes = 10
new_game = True
selected = False
tube_rects = []
select_rect = 100
win = False



# select a number of tubes and pick random colors upon new game setup
def generate_start():
    tubes_number = 10
    tubes_colors = []
    available_colors = []
    for i in range(tubes_number):
        tubes_colors.append([])
        if i < tubes_number - 2:
            for j in range(4):
                available_colors.append(i)
    for i in range(tubes_number - 2):
        for j in range(4):
            color = random.choice(available_colors)
            tubes_colors[i].append(color)
            available_colors.remove(color)
    print(tubes_colors)
    print(tubes_number)
    return tubes_number, tubes_colors


# draw all tubes and colors on screen, as well as indicating what tube was selected
def draw_tubes(tubes_num, tube_cols):
    tube_boxes = []
    # layout parameters
    tube_w = 65
    tube_h = 200
    block_h = 50
    margin_x = 20
    border_radius_bottle = 16
    border_radius_colors = 16

    # split into top and bottom rows
    if tubes_num % 2 == 0:
        top_count = tubes_num // 2
        bottom_count = tubes_num // 2
    else:
        top_count = tubes_num // 2 + 1
        bottom_count = tubes_num - top_count

    # compute horizontal spacing so rows are centered
    def compute_positions(count):
        if count == 0:
            return []
        if count == 1:
            x_start = GAME_WIDTH // 2 - tube_w // 2
            return [x_start]
        total_width = count * tube_w
        available = GAME_WIDTH - 2 * margin_x - total_width
        gap = available / (count - 1) if count > 1 else 0
        # center the block of tubes inside the game area
        x_start = int((GAME_WIDTH - (total_width + gap * (count - 1))) / 2)
        return [int(x_start + i * (tube_w + gap)) for i in range(count)]

    top_num = compute_positions(top_count)
    bottom_num = compute_positions(bottom_count)

    # Y positions of each row (for later drawing purporses)
    top_y = 50
    bottom_y = 300

    # Draw the top row
    for idx, x in enumerate(top_num):
        # Get the colors for each tube
        if idx < len(tube_cols):
            cols = tube_cols[idx]
        else:
            cols = []
        # draw color blocks (from bottom up)
        ncols = len(cols)
        for j in range(ncols):
            y = top_y + tube_h - block_h * (j + 1)
            rect = pygame.Rect(x, y, tube_w, block_h)
            col = color_choices[cols[j]]
            if ncols == 1:
                # single block: round all corners (use width=0 for filled rect)
                pygame.draw.rect(screen, col, rect, width=0, border_radius=border_radius_colors)
            else:
                # For colors in the bottom of the bottle we only round the bottom corners
                if j == 0:
                    pygame.draw.rect(screen, col, rect, width=0,
                                     border_top_left_radius=0,
                                     border_top_right_radius=0,
                                     border_bottom_left_radius=border_radius_colors,
                                     border_bottom_right_radius=border_radius_colors)
                elif j == ncols - 1:
                # For colors in the top of the bottle we only round the top corners
                    pygame.draw.rect(screen, col, rect, width=0,
                                     border_top_left_radius=border_radius_colors,
                                     border_top_right_radius=border_radius_colors,
                                     border_bottom_left_radius=0, 
                                     border_bottom_right_radius=0)
                # For colors in the middle we simply draw a square
                else:
                    pygame.draw.rect(screen, col, rect)
        # Draw the tubes
        tube_rect = pygame.Rect(x, top_y, tube_w, tube_h)
        pygame.draw.rect(screen, 'blue', tube_rect, 5, border_radius_bottle)
        # Green highlight whenever we a tube is marked as 'selected'
        if select_rect == idx:
            pygame.draw.rect(screen, 'green', tube_rect, 3, border_radius_bottle)
        tube_boxes.append(tube_rect)

    # Draw the bottom row
    for k, x in enumerate(bottom_num):
        idx = top_count + k
        if idx < len(tube_cols):
            cols = tube_cols[idx]
        else:
            cols = []
        ncols = len(cols)
        for j in range(ncols):
            y = bottom_y + tube_h - block_h * (j + 1)
            rect = pygame.Rect(x, y, tube_w, block_h)
            col = color_choices[cols[j]]
            if ncols == 1:
                pygame.draw.rect(screen, col, rect, width=0, border_radius=border_radius_colors)
            else:
                if j == 0:
                    pygame.draw.rect(screen, col, rect, width=0,
                                     border_top_left_radius=0, 
                                     border_top_right_radius=0,
                                     border_bottom_left_radius=border_radius_colors, 
                                     border_bottom_right_radius=border_radius_colors)
                elif j == ncols - 1:
                    pygame.draw.rect(screen, col, rect, width=0,
                                     border_top_left_radius=border_radius_colors, 
                                     border_top_right_radius=border_radius_colors,
                                     border_bottom_left_radius=0, 
                                     border_bottom_right_radius=0)
                else:
                    pygame.draw.rect(screen, col, rect)
        tube_rect = pygame.Rect(x, bottom_y, tube_w, tube_h)
        pygame.draw.rect(screen, 'blue', tube_rect, 5, border_radius_bottle)
        if select_rect == idx:
            pygame.draw.rect(screen, 'green', tube_rect, 3, border_radius_bottle)
        tube_boxes.append(tube_rect)

    return tube_boxes


# determine the top color of the selected tube and destination tube,
# as well as how long a chain of that color to move
def calc_move(colors, selected_rect, destination):
    chain = True
    color_on_top = 100
    length = 1
    color_to_move = 100
    if len(colors[selected_rect]) > 0:
        color_to_move = colors[selected_rect][-1]
        for i in range(1, len(colors[selected_rect])):
            if chain:
                if colors[selected_rect][-1 - i] == color_to_move:
                    length += 1
                else:
                    chain = False
    if 4 > len(colors[destination]):
        if len(colors[destination]) == 0:
            color_on_top = color_to_move
        else:
            color_on_top = colors[destination][-1]
    if color_on_top == color_to_move:
        for i in range(length):
            if len(colors[destination]) < 4:
                if len(colors[selected_rect]) > 0:
                    colors[destination].append(color_on_top)
                    colors[selected_rect].pop(-1)
    print(colors, length)
    return colors


# check if every tube with colors is 4 long and all the same color. That's how we win
def check_victory(colors):
    won = True
    for i in range(len(colors)):
        if len(colors[i]) > 0:
            if len(colors[i]) != 4:
                won = False
            else:
                main_color = colors[i][-1]
                for j in range(len(colors[i])):
                    if colors[i][j] != main_color:
                        won = False
    return won


# main game loop
run = True
while run:
    screen.fill('black')
    # draw menu panel on the right
    menu_x = GAME_WIDTH + 50
    menu_w = WIDTH - GAME_WIDTH - 50
    if menu_w > 0:
        pygame.draw.rect(screen, (25, 25, 25), (menu_x, 0, menu_w, HEIGHT))
        # menu title and placeholder items
        menu_title = font.render('Menu', True, 'white')
        mt_rect = menu_title.get_rect(center=(menu_x + menu_w // 2, 30))
        screen.blit(menu_title, mt_rect)
        alg_text = font.render('Algorithm: Human', True, 'white')
        a_rect = alg_text.get_rect(center=(menu_x + menu_w // 2, 70))
        screen.blit(alg_text, a_rect)
    timer.tick(fps)
    # generate game board on new game, make a copy of the colors in case of restart
    if new_game:
        tubes, tube_colors = generate_start()
        initial_colors = copy.deepcopy(tube_colors)
        new_game = False
    # draw tubes every cycle
    else:
        tube_rects = draw_tubes(tubes, tube_colors)
    # check for victory every cycle
    win = check_victory(tube_colors)
    # event handling - Quit button exits, clicks select tubes, enter and space for restart and new board
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_SPACE:
                tube_colors = copy.deepcopy(initial_colors)
            elif event.key == pygame.K_RETURN:
                new_game = True
        if event.type == pygame.MOUSEBUTTONDOWN:
            if not selected:
                for item in range(len(tube_rects)):
                    if tube_rects[item].collidepoint(event.pos):
                        selected = True
                        select_rect = item
            else:
                for item in range(len(tube_rects)):
                    if tube_rects[item].collidepoint(event.pos):
                        dest_rect = item
                        tube_colors = calc_move(tube_colors, select_rect, dest_rect)
                        selected = False
                        select_rect = 100
                        
    # Text draw
    
    # 1. - In case of a win, draw the text in the center
    if win:
        victory_text = font.render('Victory! Press Enter for a new board!', True, 'white')
        v_rect = victory_text.get_rect(center=(GAME_WIDTH // 2, HEIGHT // 2))
        screen.blit(victory_text, v_rect)
    # 2. - Helper text at the bottom left corner of the GAME_WIDTH screen
    restart_text = small_font.render('Space-Restart | Enter-New Board', True, 'white')
    r_rect = restart_text.get_rect(center=(WIDTH - GAME_WIDTH +110, HEIGHT-20))
    screen.blit(restart_text, r_rect)
    # 3. - Game title 'Water Sort'
    restart_text = font.render('Water Sort', True, 'white')
    r_rect = restart_text.get_rect(center=(GAME_WIDTH // 2, 20))
    screen.blit(restart_text, r_rect)

    # display all drawn items on screen, exit pygame if run == False
    pygame.display.flip()
pygame.quit()