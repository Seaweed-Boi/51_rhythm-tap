import pygame
import random

LANES = 4
LANE_KEYS = [pygame.K_d, pygame.K_f, pygame.K_j, pygame.K_k]
LANE_LABELS = ['D', 'F', 'J', 'K']
LANE_COLORS = [(220,80,80),(80,180,220),(100,220,100),(220,180,60)]

class Note:
    WIDTH = 70
    HEIGHT = 20
    def __init__(self, lane, y=-30, speed=4, hold=False):
        self.lane = lane
        self.y = y
        self.speed = speed

        self.hold = hold
        self.hold_duration = 60
        self.holding = False
        self.hold_start = None
        self.completed = False

        self.hit = False
        self.missed = False

    def update(self):
        self.y += self.speed

    def get_rect(self, lane_x):
        return pygame.Rect(lane_x - self.WIDTH//2, int(self.y), self.WIDTH, self.HEIGHT)
