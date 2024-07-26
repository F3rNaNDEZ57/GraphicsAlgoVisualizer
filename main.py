import pygame
import threading
import queue

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
GRID_WIDTH, GRID_HEIGHT = 40, 30  # Grid of 40x30 cells
PIXEL_SIZE = 20

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)

# Create screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Pixel Grid Display")

# Queue for sending click events to Tkinter
click_queue = queue.Queue()

def draw_grid():
    for x in range(GRID_WIDTH):
        for y in range(GRID_HEIGHT):
            screen_x = x * PIXEL_SIZE
            screen_y = y * PIXEL_SIZE
            rect = pygame.Rect(screen_x, screen_y, PIXEL_SIZE, PIXEL_SIZE)
            pygame.draw.rect(screen, WHITE, rect, 1)

def set_pixel(x, y, color=RED):
    if 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT:
        screen_x = x * PIXEL_SIZE
        screen_y = y * PIXEL_SIZE
        rect = pygame.Rect(screen_x, screen_y, PIXEL_SIZE, PIXEL_SIZE)
        pygame.draw.rect(screen, color, rect)

def clear_grid():
    screen.fill(BLACK)
    draw_grid()
    pygame.display.flip()

def main():
    running = True
    clear_grid()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = event.pos
                grid_x = mouse_x // PIXEL_SIZE
                grid_y = mouse_y // PIXEL_SIZE
                click_queue.put((grid_x, grid_y))

        pygame.display.flip()

    pygame.quit()

def start_pygame():
    main()

# Run Pygame in a separate thread
pygame_thread = threading.Thread(target=start_pygame)
pygame_thread.start()
