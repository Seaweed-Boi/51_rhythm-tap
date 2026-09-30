import pygame
import random
import math
from array import array
from game.beat import Note, LANES, LANE_KEYS, LANE_LABELS, LANE_COLORS

WIDTH, HEIGHT = 480, 640
FPS = 60
HIT_Y = HEIGHT - 80
HIT_WINDOW = 30
BG = (15, 10, 25)
LANE_W = WIDTH // LANES
BPM = 120
BEAT_INTERVAL = 60 / BPM

class GameEngine:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.hit_sounds = {
            "PERFECT": self.make_tone(880, 0.08),
            "GREAT": self.make_tone(660, 0.08),
            "OK": self.make_tone(440, 0.08),
        }
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Rhythm Tap")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 26, bold=True)
        self.big_font = pygame.font.SysFont("monospace", 44, bold=True)
        self.reset()

    def make_tone(self, frequency, duration):
        sample_rate = 44100
        num_samples = int(sample_rate * duration)

        samples = array("h")

        for i in range(num_samples):
            t = i / sample_rate

            # Basic sine wave
            value = math.sin(2 * math.pi * frequency * t)

            # Fade out at the end to avoid clicking
            envelope = 1 - (i / num_samples)

            samples.append(int(value * envelope * 16000))

        return pygame.mixer.Sound(
            buffer=samples.tobytes()
        )

    def reset(self):
        self.notes = []
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.misses = 0
        self.perfects = 0
        self.greats = 0
        self.oks = 0
        self.beat_timer = 0
        self.speed = 5
        self.frame = 0
        self.feedback = []  # (text, color, ttl, x, y)
        self.game_over = False

    def spawn_note(self):
        lane = random.randint(0, LANES - 1)

        # 25% chance of spawning a hold note
        is_hold = random.random() < 0.25

        self.notes.append(
            Note(
                lane,
                y=-30,
                speed=self.speed,
                hold=is_hold
            )
        )

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.reset()
                elif not self.game_over:
                    for i, key in enumerate(LANE_KEYS):
                        if event.key == key:
                            self.process_tap(i)

            if event.type == pygame.KEYUP:
                if not self.game_over:
                    for i, key in enumerate(LANE_KEYS):
                        if event.key == key:
                            self.release_hold(i)

        return True

    def process_tap(self, lane):
        # Find closest note in this lane near hit zone
        best = None
        best_dist = 9999
        for note in self.notes:
            if note.lane == lane and not note.hit and not note.missed:
                dist = abs(note.y + Note.HEIGHT//2 - HIT_Y)
                if dist < best_dist:
                    best_dist = dist
                    best = note
        lane_x = lane * LANE_W + LANE_W // 2
        if best and best_dist <= HIT_WINDOW:
            if best.hold:
                best.holding = True
                best.hold_start = self.frame
                best.hit = True

                self.feedback.append(
                    ["HOLD", (180, 180, 255), 40, lane_x, HIT_Y - 30]
                )

                return

            best.hit = True

            if best_dist < 8:
                grade, pts = "PERFECT", 300
                col = (255, 220, 0)
            elif best_dist < 18:
                grade, pts = "GREAT", 200
                col = (100, 220, 100)
            else:
                grade, pts = "OK", 100
                col = (180, 180, 255)
            if grade == "PERFECT":
                self.perfects += 1
            elif grade == "GREAT":
                self.greats += 1
            elif grade == "OK":
                self.oks += 1
            self.hit_sounds[grade].play()
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            self.score += pts * max(1, self.combo // 5)
            self.feedback.append([grade, col, 40, lane_x, HIT_Y - 30])
        else:
            self.combo = 0
            self.feedback.append(["MISS", (220,60,60), 40, lane_x, HIT_Y - 30])

    def release_hold(self, lane):
        for note in self.notes:
            if (
                note.lane == lane
                and note.hold
                and note.holding
                and not note.completed
            ):
                note.holding = False

                # Released before completing the required 1 second
                if self.frame - note.hold_start < note.hold_duration:
                    note.hit = False
                    note.missed = True
                    self.combo = 0
                    self.misses += 1

                    lane_x = lane * LANE_W + LANE_W // 2

                    self.feedback.append(
                        ["MISS", (220, 60, 60), 40, lane_x, HIT_Y - 30]
                    )

            return

    def update(self, dt):
        if self.game_over:
            return

        self.frame += 1

        self.beat_timer += dt

        if self.beat_timer >= BEAT_INTERVAL:
            self.spawn_note()
            self.beat_timer -= BEAT_INTERVAL

            if self.frame % (FPS * 10) == 0:
                self.speed = min(10, self.speed + 0.5)

        for note in self.notes:
            note.update()

            # Handle hold notes
            if note.hold and note.holding and not note.completed:
                held_for = self.frame - note.hold_start

                if held_for >= note.hold_duration:
                    note.completed = True
                    note.holding = False

                    self.perfects += 1
                    self.hit_sounds["PERFECT"].play()

                    self.combo += 1
                    self.max_combo = max(self.max_combo, self.combo)
                    self.score += 300 * max(1, self.combo // 5)

                    lane_x = note.lane * LANE_W + LANE_W // 2

                    self.feedback.append(
                        ["PERFECT", (255, 220, 0), 40, lane_x, HIT_Y - 30]
                    )

            # Normal note / failed hold reaches the end
            if (
                not note.missed
                and not note.completed
                and note.y > HIT_Y + HIT_WINDOW + Note.HEIGHT
            ):
                note.missed = True
                self.misses += 1
                self.combo = 0

        self.notes = [
            n for n in self.notes
            if not (
                (n.hit and not n.hold)
                or n.completed
                or (n.missed and n.y > HEIGHT + 10)
            )
        ]
        self.feedback = [[t,c,ttl-1,x,y] for t,c,ttl,x,y in self.feedback if ttl > 1]

        if self.misses >= 15:
            self.game_over = True

    def draw(self):
        self.screen.fill(BG)
        # Lane dividers
        for i in range(LANES + 1):
            pygame.draw.line(self.screen, (40,40,60), (i*LANE_W,0), (i*LANE_W,HEIGHT), 1)

        # Hit line
        pygame.draw.line(self.screen, (80,80,100), (0,HIT_Y), (WIDTH,HIT_Y), 2)
        for i in range(LANES):
            lx = i*LANE_W + LANE_W//2
            pygame.draw.rect(self.screen, LANE_COLORS[i],
                pygame.Rect(lx - Note.WIDTH//2, HIT_Y - 12, Note.WIDTH, 24), border_radius=6)
            lbl = self.font.render(LANE_LABELS[i], True, (20,20,20))
            self.screen.blit(lbl, (lx - lbl.get_width()//2, HIT_Y - 10))

        # Notes
        for note in self.notes:
            if note.hit and not note.hold:
                continue
            lx = note.lane * LANE_W + LANE_W // 2
            rect = note.get_rect(lx)

            if note.hold:
                # Draw a longer body for hold notes
                hold_height = int(self.speed * 60)

                hold_rect = pygame.Rect(
                    lx - Note.WIDTH // 2,
                    int(note.y),
                    Note.WIDTH,
                    hold_height
                )

                pygame.draw.rect(
                    self.screen,
                    LANE_COLORS[note.lane],
                    hold_rect,
                    border_radius=5
                )

                # Draw the head of the note
                pygame.draw.rect(
                    self.screen,
                    (255, 255, 255),
                    rect,
                    border_radius=5
                )
            else:
                pygame.draw.rect(
                    self.screen,
                    LANE_COLORS[note.lane],
                    rect,
                    border_radius=5
                )

        # Feedback
        for text, color, ttl, x, y in self.feedback:
            surf = self.font.render(text, True, color)
            alpha = min(255, ttl * 7)
            surf.set_alpha(alpha)
            self.screen.blit(surf, (x - surf.get_width()//2, y))

        # HUD
        sc = self.font.render(f"Score: {self.score}", True, (220,220,220))
        co = self.font.render(f"Combo: {self.combo}x", True, (255,220,80))
        mi = self.font.render(f"Misses: {self.misses}/15", True, (220,100,100))
        self.screen.blit(sc, (10, 10))
        self.screen.blit(co, (10, 40))
        self.screen.blit(mi, (WIDTH - 170, 10))

        if self.game_over:
            ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 180))
            self.screen.blit(ov, (0, 0))

            # Title
            msg = self.big_font.render(
                "GAME OVER",
                True,
                (220, 60, 60)
            )

            self.screen.blit(
                msg,
                (WIDTH // 2 - msg.get_width() // 2, 80)
            )

            # Score
            score_msg = self.font.render(
                f"Score: {self.score}",
                True,
                (220, 220, 220)
            )

            self.screen.blit(
                score_msg,
                (WIDTH // 2 - score_msg.get_width() // 2, 145)
            )

            # Max combo
            combo_msg = self.font.render(
                f"Max Combo: {self.max_combo}x",
                True,
                (255, 220, 80)
            )

            self.screen.blit(
                combo_msg,
                (WIDTH // 2 - combo_msg.get_width() // 2, 180)
            )

            # Grade statistics
            perfect_msg = self.font.render(
                f"PERFECT: {self.perfects}",
                True,
                (255, 220, 0)
            )

            great_msg = self.font.render(
                f"GREAT: {self.greats}",
                True,
                (100, 220, 100)
            )

            ok_msg = self.font.render(
                f"OK: {self.oks}",
                True,
                (180, 180, 255)
            )

            miss_msg = self.font.render(
                f"MISS: {self.misses}",
                True,
                (220, 60, 60)
            )

            self.screen.blit(
                perfect_msg,
                (WIDTH // 2 - perfect_msg.get_width() // 2, 235)
            )

            self.screen.blit(
                great_msg,
                (WIDTH // 2 - great_msg.get_width() // 2, 275)
            )

            self.screen.blit(
                ok_msg,
                (WIDTH // 2 - ok_msg.get_width() // 2, 315)
            )

            self.screen.blit(
                miss_msg,
                (WIDTH // 2 - miss_msg.get_width() // 2, 355)
            )

            # Accuracy
            accuracy = self.get_accuracy()

            accuracy_msg = self.font.render(
                f"Accuracy: {accuracy:.1f}%",
                True,
                (220, 220, 220)
            )

            self.screen.blit(
                accuracy_msg,
                (WIDTH // 2 - accuracy_msg.get_width() // 2, 415)
            )

            # Restart
            restart = self.font.render(
                "Press R to Restart",
                True,
                (160, 160, 160)
            )

            self.screen.blit(
                restart,
                (WIDTH // 2 - restart.get_width() // 2, 500)
            )

        pygame.display.flip()

    def get_accuracy(self):
        total = self.perfects + self.greats + self.oks + self.misses

        if total == 0:
            return 0.0

        weighted_hits = (
            self.perfects * 1.0
            + self.greats * 0.75
            + self.oks * 0.5
        )

        return (weighted_hits / total) * 100

    def run(self):
        running = True

        while running:
            running = self.handle_events()

            dt = self.clock.tick(FPS) / 1000.0

            self.update(dt)
            self.draw()

        pygame.quit()
