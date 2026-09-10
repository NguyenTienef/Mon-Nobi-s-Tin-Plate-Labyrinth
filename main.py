import pygame
from robot import Robot


# =========================================================
# Configuration
# =========================================================

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700

FPS = 60

BACKGROUND_COLOR = (235, 235, 235)
GRID_COLOR = (210, 210, 210)


# =========================================================
# Grid
# =========================================================

def draw_grid(screen, grid_size=10):
    """Draw the background grid."""

    for x in range(0, SCREEN_WIDTH, grid_size):
        pygame.draw.line(
            screen,
            GRID_COLOR,
            (x, 0),
            (x, SCREEN_HEIGHT),
        )

    for y in range(0, SCREEN_HEIGHT, grid_size):
        pygame.draw.line(
            screen,
            GRID_COLOR,
            (0, y),
            (SCREEN_WIDTH, y),
        )


# =========================================================
# Main
# =========================================================

def main():

    pygame.init()

    screen = pygame.display.set_mode(
        (SCREEN_WIDTH, SCREEN_HEIGHT),
    )

    pygame.display.set_caption(
        "2D Autonomous Robot Simulator - Phase 1",
    )

    clock = pygame.time.Clock()

    # Create robot
    robot = Robot(
        x=SCREEN_WIDTH / 2,
        y=SCREEN_HEIGHT / 2,
        width=20,
        length=30,
    )

    running = True

    while running:

        # Delta time
        dt = clock.tick(FPS) / 1000.0

        # =================================================
        # Events
        # =================================================

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False

        # =================================================
        # Keyboard
        # =================================================

        keys = pygame.key.get_pressed()

        throttle = 0.0
        steering = 0.0

        # Forward / backward
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            throttle = 1.0

        elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
            throttle = -1.0

        # Left / right
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            steering = -1.0

        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            steering = 1.0

        # =================================================
        # Robot update
        # =================================================

        robot.update(
            dt,
            throttle,
            steering,
        )

        robot.keep_inside(
            SCREEN_WIDTH,
            SCREEN_HEIGHT,
        )

        # =================================================
        # Rendering
        # =================================================

        screen.fill(BACKGROUND_COLOR)

        draw_grid(screen)

        robot.draw(screen)

        # =================================================
        # UI
        # =================================================

        font = pygame.font.Font(None, 28)

        controls_text = font.render(
            "W/S or UP/DOWN: Move | "
            "A/D or LEFT/RIGHT: Turn",
            True,
            (30, 30, 30),
        )

        screen.blit(
            controls_text,
            (20, 20),
        )

        state_text = font.render(
            f"x={robot.x:.1f}   "
            f"y={robot.y:.1f}   "
            f"theta={robot.theta:.2f} rad   "
            f"v={robot.v:.1f}",
            True,
            (30, 30, 30),
        )

        screen.blit(
            state_text,
            (20, 50),
        )

        pygame.display.flip()

    pygame.quit()


# =========================================================
# Program entry point
# =========================================================

if __name__ == "__main__":
    main()
