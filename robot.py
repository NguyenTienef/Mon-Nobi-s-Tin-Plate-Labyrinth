import math
import pygame


class Robot:
    """2D four-wheel robot model."""

    def __init__(
        self,
        x=100.0,
        y=50.0,
        width=15.0,
        length=30.0,
    ):
        # Pose
        self.x = x
        self.y = y
        self.theta = 0.0

        # Robot dimensions
        self.width = width
        self.length = length

        # Motion state
        self.v = 0.0
        self.omega = 0.0

        # Motion limits
        self.max_speed = 200.0
        self.max_omega = 2.5

        # Acceleration
        self.acceleration = 200.0
        self.angular_acceleration = 5.0

    def update(self, dt, throttle=0.0, steering=0.0):
        """
        Update robot state.

        throttle:
            -1.0 = backward
             0.0 = stop
             1.0 = forward

        steering:
            -1.0 = left
             0.0 = straight
             1.0 = right
        """

        target_v = throttle * self.max_speed
        target_omega = steering * self.max_omega

        self.v = self._move_towards(
            self.v,
            target_v,
            self.acceleration * dt,
        )

        self.omega = self._move_towards(
            self.omega,
            target_omega,
            self.angular_acceleration * dt,
        )

        # Kinematic motion model
        self.x += self.v * math.cos(self.theta) * dt
        self.y += self.v * math.sin(self.theta) * dt

        self.theta += self.omega * dt

        # Normalize angle to [-pi, pi]
        self.theta = math.atan2(
            math.sin(self.theta),
            math.cos(self.theta),
        )

    @staticmethod
    def _move_towards(current, target, max_delta):
        if current < target:
            return min(current + max_delta, target)

        if current > target:
            return max(current - max_delta, target)

        return target

    def get_corners(self):
        """Return the four corners of the robot body."""

        half_length = self.length / 2
        half_width = self.width / 2

        local_corners = [
            (half_length, -half_width),
            (half_length, half_width),
            (-half_length, half_width),
            (-half_length, -half_width),
        ]

        corners = []

        cos_theta = math.cos(self.theta)
        sin_theta = math.sin(self.theta)

        for lx, ly in local_corners:
            wx = (
                self.x
                + lx * cos_theta
                - ly * sin_theta
            )

            wy = (
                self.y
                + lx * sin_theta
                + ly * cos_theta
            )

            corners.append((wx, wy))

        return corners

    def get_wheel_positions(self):
        """Return the world coordinates of the four wheels."""
        wheel_offset = self.width * 0.08
        half_length = self.length * 0.35
        half_width = self.width / 2 + wheel_offset

        local_wheels = [
            (half_length, -half_width),   # Front right
            (half_length, half_width),    # Front left
            (-half_length, half_width),   # Rear left
            (-half_length, -half_width),  # Rear right
        ]

        wheels = []

        cos_theta = math.cos(self.theta)
        sin_theta = math.sin(self.theta)

        for lx, ly in local_wheels:
            wx = (
                self.x
                + lx * cos_theta
                - ly * sin_theta
            )

            wy = (
                self.y
                + lx * sin_theta
                + ly * cos_theta
            )

            wheels.append((wx, wy))

        return wheels

    def draw(self, screen):
        """Draw the robot."""

        # -----------------------------
        # Robot body
        # -----------------------------

        corners = self.get_corners()

        pygame.draw.polygon(
            screen,
            (70, 130, 200),
            corners,
        )

        pygame.draw.polygon(
            screen,
            (20, 20, 20),
            corners,
            3,
        )

        # -----------------------------
        # Wheels
        # -----------------------------

        wheel_positions = self.get_wheel_positions()

        wheel_width = max(3, self.width * 0.35)
        wheel_length = max(6, self.length * 0.20)

        for wx, wy in wheel_positions:

            wheel_surface = pygame.Surface(
                (wheel_length, wheel_width),
                pygame.SRCALPHA,
            )

            wheel_surface.fill((30, 30, 30))

            rotated_wheel = pygame.transform.rotate(
                wheel_surface,
                -math.degrees(self.theta),
            )

            wheel_rect = rotated_wheel.get_rect(
                center=(int(wx), int(wy)),
            )

            screen.blit(
                rotated_wheel,
                wheel_rect,
            )
        # -----------------------------
        # Heading arrow
        # -----------------------------
        arrow_length = self.length * 0.45

        end_x = (
            self.x
            + arrow_length * math.cos(self.theta)
        )

        end_y = (
            self.y
            + arrow_length * math.sin(self.theta)
        )

        pygame.draw.line(
            screen,
            (220, 40, 40),
            (int(self.x), int(self.y)),
            (int(end_x), int(end_y)),
            5,
        )

        # Robot center
        pygame.draw.circle(
            screen,
            (255, 255, 255),
            (int(self.x), int(self.y)),
            5,
        )

    def keep_inside(self, width, height):
        """Keep the robot inside the simulation window."""

        margin_x = self.length / 2
        margin_y = self.length / 2

        self.x = max(
            margin_x,
            min(width - margin_x, self.x),
        )

        self.y = max(
            margin_y,
            min(height - margin_y, self.y),
        )
