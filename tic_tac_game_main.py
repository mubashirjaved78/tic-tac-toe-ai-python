import pygame
import sys
import math
import random
import threading
import time

from engine import (
    empty_board, apply_move, legal_moves, game_status, winner,
    opponent, best_move, WIN_LINES
)
import tictactoe_sounds as sfx

pygame.init()
pygame.font.init()
sfx.init()

WIDTH, HEIGHT = 980, 700

C_BG_TOP      = (20, 22, 30)
C_BG_BOT      = (13, 14, 19)
C_BOARD_BG    = (30, 33, 43)
C_GRID_LINE   = (60, 65, 80)
C_CELL_HOVER  = (42, 46, 58)
C_CELL_WIN    = (52, 58, 46)

C_X_COLOR     = (255, 122, 95)     
C_X_GLOW      = (255, 150, 125)
C_O_COLOR     = (84, 209, 200)     
C_O_GLOW      = (120, 230, 220)

C_TEXT_MAIN   = (228, 230, 238)
C_TEXT_DIM    = (130, 136, 156)
C_TEXT_ACCENT = (255, 159, 99)
C_PANEL_BG    = (24, 26, 35)
C_PANEL_BG2   = (18, 20, 27)
C_PANEL_LINE  = (48, 52, 66)
C_BTN         = (40, 44, 56)
C_BTN_HOVER   = (54, 59, 75)
C_BTN_ACTIVE_X = (255, 122, 95)
C_BTN_ACTIVE_O = (84, 209, 200)

BOARD_SIZE = 480
BOARD_X = 70
BOARD_Y = (HEIGHT - BOARD_SIZE) // 2
CELL = BOARD_SIZE // 3


def load_font(size, bold=False):
    try:
        return pygame.font.SysFont("segoeui,arial,helvetica", size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size)


def ease_out_back(t):
    t = max(0.0, min(1.0, t))
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def vertical_gradient(surf, rect, top_color, bottom_color):
    x, y, w, h = rect
    for i in range(h):
        t = i / max(1, h - 1)
        col = [int(top_color[c] + (bottom_color[c] - top_color[c]) * t) for c in range(3)]
        pygame.draw.line(surf, col, (x, y + i), (x + w, y + i))


class Button:
    def __init__(self, rect, text, font, style='default'):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.style = style
        self.hover_t = 0.0

    def update(self, mouse_pos, dt):
        target = 1.0 if self.rect.collidepoint(mouse_pos) else 0.0
        self.hover_t += (target - self.hover_t) * min(1.0, dt * 10)

    def draw(self, screen, active=False, active_color=None):
        r = self.rect
        if active:
            base = active_color or C_TEXT_ACCENT
            col = base
        else:
            col = tuple(int(C_BTN[i] + (C_BTN_HOVER[i] - C_BTN[i]) * self.hover_t) for i in range(3))
        pygame.draw.rect(screen, col, r, border_radius=10)
        if active:
            pygame.draw.rect(screen, (255, 255, 255), r, 2, border_radius=10)
        else:
            pygame.draw.rect(screen, C_PANEL_LINE, r, 1, border_radius=10)
        text_col = (20, 20, 24) if active else C_TEXT_MAIN
        label = self.font.render(self.text, True, text_col)
        screen.blit(label, (r.centerx - label.get_width() // 2, r.centery - label.get_height() // 2))


class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max_life', 'color', 'size')

    def __init__(self, x, y, color):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(120, 320)
        self.x, self.y = x, y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 80
        self.life = self.max_life = random.uniform(0.6, 1.2)
        self.color = color
        self.size = random.uniform(2.5, 5.5)

    def update(self, dt):
        self.vy += 420 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    @property
    def alive(self):
        return self.life > 0


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def burst(self, x, y, color, count=36):
        for _ in range(count):
            self.particles.append(Particle(x, y, color))

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]

    def draw(self, screen):
        for p in self.particles:
            t = p.life / p.max_life
            alpha = max(0, min(255, int(255 * t)))
            s = pygame.Surface((p.size * 2, p.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*p.color, alpha), (p.size, p.size), p.size)
            screen.blit(s, (p.x - p.size, p.y - p.size))


class MarkAnim:
    def __init__(self, index, mark):
        self.index = index
        self.mark = mark
        self.t = 0.0
        self.duration = 0.32

    def update(self, dt):
        self.t = min(1.0, self.t + dt / self.duration)

    @property
    def done(self):
        return self.t >= 1.0

    @property
    def progress(self):
        return ease_out_back(self.t)


class TicTacToeGame:
    STATE_MENU = 'menu'
    STATE_PLAYING = 'playing'

    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Tic-Tac-Toe — Premium Edition")
        self.clock = pygame.time.Clock()

        self.font_xs = load_font(14)
        self.font_sm = load_font(17)
        self.font_md = load_font(20, bold=True)
        self.font_lg = load_font(26, bold=True)
        self.font_xl = load_font(38, bold=True)
        self.font_title = load_font(52, bold=True)

        self.particles = ParticleSystem()
        self.state = self.STATE_MENU
        self.bg_t = 0.0

        self.menu_mode = 'ai'        
        self.menu_difficulty = 'hard'
        self.menu_mark = 'X'         

        self._build_menu_buttons()
        self.new_game()

    def _build_menu_buttons(self):
        cx = WIDTH // 2
        self.btn_mode_ai  = Button((cx - 220, 248, 200, 56), "vs AI", self.font_md)
        self.btn_mode_pvp = Button((cx + 20,  248, 200, 56), "vs Player", self.font_md)

        self.btn_diff_easy   = Button((cx - 330, 388, 200, 56), "Easy", self.font_md)
        self.btn_diff_medium = Button((cx - 100, 388, 200, 56), "Medium", self.font_md)
        self.btn_diff_hard   = Button((cx + 130, 388, 200, 56), "Hard", self.font_md)

        self.btn_mark_x = Button((cx - 220, 498, 200, 56), "Play as X", self.font_md)
        self.btn_mark_o = Button((cx + 20,  498, 200, 56), "Play as O", self.font_md)

        self.btn_start = Button((cx - 140, 598, 280, 64), "Start Game", self.font_lg, style='accent')

    def _build_game_buttons(self):
        px = BOARD_X + BOARD_SIZE + 50
        pw = WIDTH - px - 40
        self.btn_new_game = Button((px + 10, HEIGHT - 150, pw - 20, 44), "New Game", self.font_sm)
        self.btn_menu = Button((px + 10, HEIGHT - 96, pw - 20, 44), "Main Menu", self.font_sm)

    def new_game(self):
        self.game_mode = self.menu_mode
        self.human_mark = self.menu_mark if self.game_mode == 'ai' else 'X'
        self.ai_mark = opponent(self.human_mark) if self.game_mode == 'ai' else None
        self.ai_difficulty = self.menu_difficulty

        self.board = empty_board()
        self.current_turn = 'X'
        self.game_over = False
        self.winner_mark = None
        self.win_line = None
        self.status_text = "X to move"
        self.scores = getattr(self, 'scores', {'X': 0, 'O': 0, 'Draw': 0})

        self.mark_anims = []
        self.ai_thinking = False
        self.ai_thread = None
        self.ai_result = None
        self.ai_lock = threading.Lock()
        self.ai_think_start = 0.0

        self.hover_cell = None
        self.win_line_progress = 0.0
        self.win_burst_done = False

        self._build_game_buttons()

        if self.game_mode == 'ai' and self.ai_mark == 'X':
            self._trigger_ai_move()

    def cell_rect(self, index):
        r, c = divmod(index, 3)
        x = BOARD_X + c * CELL
        y = BOARD_Y + r * CELL
        return pygame.Rect(x, y, CELL, CELL)

    def cell_center(self, index):
        rect = self.cell_rect(index)
        return rect.centerx, rect.centery

    def px_to_cell(self, pos):
        x, y = pos
        if not (BOARD_X <= x < BOARD_X + BOARD_SIZE and BOARD_Y <= y < BOARD_Y + BOARD_SIZE):
            return None
        c = (x - BOARD_X) // CELL
        r = (y - BOARD_Y) // CELL
        return r * 3 + c

    def make_move(self, index):
        if self.board[index] is not None or self.game_over:
            return
        mark = self.current_turn
        self.board = apply_move(self.board, index, mark)
        self.mark_anims.append(MarkAnim(index, mark))
        sfx.play('place_x' if mark == 'X' else 'place_o')

        status = game_status(self.board)
        if status == 'win':
            self.game_over = True
            w, line = winner(self.board)
            self.winner_mark = w
            self.win_line = line
            self.scores[w] = self.scores.get(w, 0) + 1
            human_won = (self.game_mode == 'ai' and w == self.human_mark) or self.game_mode == 'pvp'
            self.status_text = f"{w} wins!"
            sfx.play('win' if (self.game_mode != 'ai' or w == self.human_mark) else 'lose')
        elif status == 'draw':
            self.game_over = True
            self.winner_mark = None
            self.scores['Draw'] = self.scores.get('Draw', 0) + 1
            self.status_text = "It's a draw!"
            sfx.play('draw')
        else:
            self.current_turn = opponent(mark)
            self.status_text = f"{self.current_turn} to move"
            if self.game_mode == 'ai' and self.current_turn == self.ai_mark:
                self._trigger_ai_move()

    def handle_board_click(self, pos):
        if self.game_over or self.ai_thinking:
            return
        if self.game_mode == 'ai' and self.current_turn != self.human_mark:
            return
        index = self.px_to_cell(pos)
        if index is None or self.board[index] is not None:
            if index is not None and self.board[index] is not None:
                sfx.play('illegal')
            return
        self.make_move(index)

    def _trigger_ai_move(self):
        self.ai_thinking = True
        self.ai_think_start = time.time()

        def worker():
            time.sleep(random.uniform(0.35, 0.7))
            move = best_move(self.board, self.ai_mark, self.ai_difficulty)
            with self.ai_lock:
                self.ai_result = move

        self.ai_thread = threading.Thread(target=worker, daemon=True)
        self.ai_thread.start()

    def _check_ai_result(self):
        if not self.ai_thinking:
            return
        with self.ai_lock:
            result = self.ai_result
            self.ai_result = None
        if result is not None:
            self.ai_thinking = False
            self.make_move(result)

    def draw_background(self, dt):
        self.bg_t += dt
        vertical_gradient(self.screen, (0, 0, WIDTH, HEIGHT), C_BG_TOP, C_BG_BOT)

    def draw_board_frame(self):
        shadow = pygame.Surface((BOARD_SIZE + 24, BOARD_SIZE + 24), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 90), shadow.get_rect(), border_radius=20)
        self.screen.blit(shadow, (BOARD_X - 12, BOARD_Y - 8))

        panel_rect = (BOARD_X - 16, BOARD_Y - 16, BOARD_SIZE + 32, BOARD_SIZE + 32)
        pygame.draw.rect(self.screen, C_BOARD_BG, panel_rect, border_radius=18)
        pygame.draw.rect(self.screen, C_PANEL_LINE, panel_rect, 1, border_radius=18)

    def draw_grid(self):
        if self.win_line:
            for idx in self.win_line:
                rect = self.cell_rect(idx)
                s = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
                glow = C_X_GLOW if self.winner_mark == 'X' else C_O_GLOW
                s.fill((*glow, 26))
                self.screen.blit(s, rect.topleft)

        if self.hover_cell is not None and not self.game_over and self.board[self.hover_cell] is None:
            allowed = True
            if self.game_mode == 'ai' and self.current_turn != self.human_mark:
                allowed = False
            if allowed:
                rect = self.cell_rect(self.hover_cell)
                pygame.draw.rect(self.screen, C_CELL_HOVER, rect)

        lw = 4
        for i in (1, 2):
            x = BOARD_X + i * CELL
            pygame.draw.line(self.screen, C_GRID_LINE, (x, BOARD_Y + 14), (x, BOARD_Y + BOARD_SIZE - 14), lw)
            y = BOARD_Y + i * CELL
            pygame.draw.line(self.screen, C_GRID_LINE, (BOARD_X + 14, y), (BOARD_X + BOARD_SIZE - 14, y), lw)

    def _draw_x(self, cx, cy, size, progress, color, glow):
        half = size * 0.32 * progress
        lw = max(3, int(size * 0.085))
        glow_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        gc = (cx - (cx - size // 2), cy - (cy - size // 2))  # unused, kept simple below
        for (dx1, dy1, dx2, dy2) in [(-half, -half, half, half), (-half, half, half, -half)]:
            pygame.draw.line(self.screen, glow, (cx + dx1, cy + dy1), (cx + dx2, cy + dy2), lw + 6)
        s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        for (dx1, dy1, dx2, dy2) in [(-half, -half, half, half), (-half, half, half, -half)]:
            pygame.draw.line(self.screen, color, (cx + dx1, cy + dy1), (cx + dx2, cy + dy2), lw)
            pygame.draw.circle(self.screen, color, (int(cx + dx1), int(cy + dy1)), lw // 2)
            pygame.draw.circle(self.screen, color, (int(cx + dx2), int(cy + dy2)), lw // 2)

    def _draw_o(self, cx, cy, size, progress, color, glow):
        radius = size * 0.32
        lw = max(3, int(size * 0.085))
        sweep = progress * 360
        # Glow ring
        pygame.draw.circle(self.screen, glow, (cx, cy), radius, lw + 6)
        if progress >= 0.999:
            pygame.draw.circle(self.screen, color, (cx, cy), radius, lw)
        else:
            steps = max(2, int(sweep))
            pts = []
            for i in range(steps + 1):
                ang = -math.pi / 2 + math.radians(i * (sweep / steps if steps else 0))
                pts.append((cx + math.cos(ang) * radius, cy + math.sin(ang) * radius))
            if len(pts) >= 2:
                pygame.draw.lines(self.screen, color, False, pts, lw)
                pygame.draw.circle(self.screen, color, (int(pts[0][0]), int(pts[0][1])), lw // 2)
                pygame.draw.circle(self.screen, color, (int(pts[-1][0]), int(pts[-1][1])), lw // 2)

    def draw_marks(self, dt):
        finished_anim_indices = set()
        for anim in self.mark_anims:
            anim.update(dt)
            finished_anim_indices.add(anim.index)

        animating_indices = {a.index for a in self.mark_anims if not a.done}

        for i, mark in enumerate(self.board):
            if mark is None or i in animating_indices:
                continue
            cx, cy = self.cell_center(i)
            color = C_X_COLOR if mark == 'X' else C_O_COLOR
            glow = C_X_GLOW if mark == 'X' else C_O_GLOW
            if mark == 'X':
                self._draw_x(cx, cy, CELL, 1.0, color, glow)
            else:
                self._draw_o(cx, cy, CELL, 1.0, color, glow)

        for anim in self.mark_anims:
            if anim.done:
                continue
            cx, cy = self.cell_center(anim.index)
            color = C_X_COLOR if anim.mark == 'X' else C_O_COLOR
            glow = C_X_GLOW if anim.mark == 'X' else C_O_GLOW
            if anim.mark == 'X':
                self._draw_x(cx, cy, CELL, anim.progress, color, glow)
            else:
                self._draw_o(cx, cy, CELL, anim.progress, color, glow)

        self.mark_anims = [a for a in self.mark_anims if not a.done]

    def draw_win_line(self, dt):
        if not self.win_line:
            return
        self.win_line_progress = min(1.0, self.win_line_progress + dt / 0.35)
        a, _, c = self.win_line
        start = self.cell_center(a)
        end = self.cell_center(c)
        t = ease_out_cubic(self.win_line_progress)
        cur_end = (start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t)
        color = C_X_COLOR if self.winner_mark == 'X' else C_O_COLOR
        pygame.draw.line(self.screen, color, start, cur_end, 7)
        pygame.draw.circle(self.screen, color, (int(start[0]), int(start[1])), 6)

        if self.win_line_progress >= 1.0 and not self.win_burst_done:
            self.win_burst_done = True
            mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
            self.particles.burst(mid[0], mid[1], color, count=44)

    def draw_panel(self, dt):
        px = BOARD_X + BOARD_SIZE + 50
        pw = WIDTH - px - 40
        panel_rect = (px, 24, pw, HEIGHT - 48)
        panel = pygame.Surface((pw, HEIGHT - 48), pygame.SRCALPHA)
        vertical_gradient(panel, (0, 0, pw, HEIGHT - 48), C_PANEL_BG, C_PANEL_BG2)
        self.screen.blit(panel, (px, 24))
        pygame.draw.rect(self.screen, C_PANEL_LINE, panel_rect, 1, border_radius=12)

        y = 42
        title = self.font_lg.render("Tic-Tac-Toe", True, C_TEXT_ACCENT)
        self.screen.blit(title, (px + (pw - title.get_width()) // 2, y))
        y += 38
        pygame.draw.line(self.screen, C_PANEL_LINE, (px + 14, y), (px + pw - 14, y))
        y += 16

        # Status
        if self.ai_thinking:
            dots = '.' * (1 + int(self.bg_t * 2) % 3)
            status_render = self.font_sm.render(f"AI thinking{dots}", True, C_TEXT_DIM)
        else:
            status_color = C_TEXT_ACCENT if self.game_over else C_TEXT_MAIN
            status_render = self.font_sm.render(self.status_text, True, status_color)
        self.screen.blit(status_render, (px + (pw - status_render.get_width()) // 2, y))
        y += 34

        pygame.draw.line(self.screen, C_PANEL_LINE, (px + 14, y), (px + pw - 14, y))
        y += 20

        # Scoreboard
        score_lbl = self.font_xs.render("SCOREBOARD", True, C_TEXT_DIM)
        self.screen.blit(score_lbl, (px + 14, y))
        y += 26

        x_name = (f"You (X)" if (self.game_mode == 'ai' and self.human_mark == 'X') else
                  ("AI (X)" if self.game_mode == 'ai' else "Player 1 (X)"))
        o_name = (f"You (O)" if (self.game_mode == 'ai' and self.human_mark == 'O') else
                  ("AI (O)" if self.game_mode == 'ai' else "Player 2 (O)"))

        for label, count, color in [
            (x_name, self.scores.get('X', 0), C_X_COLOR),
            (o_name, self.scores.get('O', 0), C_O_COLOR),
            ("Draws", self.scores.get('Draw', 0), C_TEXT_DIM),
        ]:
            dot_rect = pygame.Rect(px + 14, y + 4, 10, 10)
            pygame.draw.circle(self.screen, color, dot_rect.center, 5)
            lbl = self.font_sm.render(label, True, C_TEXT_MAIN)
            self.screen.blit(lbl, (px + 32, y))
            val = self.font_sm.render(str(count), True, color)
            self.screen.blit(val, (px + pw - 30 - val.get_width(), y))
            y += 28

        y += 10
        pygame.draw.line(self.screen, C_PANEL_LINE, (px + 14, y), (px + pw - 14, y))
        y += 16

        mode_lbl = self.font_xs.render("MODE", True, C_TEXT_DIM)
        self.screen.blit(mode_lbl, (px + 14, y))
        y += 22
        mode_txt = "vs AI" if self.game_mode == 'ai' else "vs Player"
        if self.game_mode == 'ai':
            mode_txt += f" · {self.ai_difficulty.capitalize()}"
        mode_render = self.font_sm.render(mode_txt, True, C_TEXT_MAIN)
        self.screen.blit(mode_render, (px + 14, y))

        mx, my = pygame.mouse.get_pos()
        self.btn_new_game.update((mx, my), dt)
        self.btn_new_game.draw(self.screen)
        self.btn_menu.update((mx, my), dt)
        self.btn_menu.draw(self.screen)

    def draw_game_over_banner(self):
        if not self.game_over:
            return
        if self.winner_mark:
            text = f"{self.winner_mark} Wins!"
            color = C_X_COLOR if self.winner_mark == 'X' else C_O_COLOR
        else:
            text = "It's a Draw"
            color = C_TEXT_DIM

        banner_h = 64
        banner_y = BOARD_Y - 16 - banner_h - 14
        s = pygame.Surface((BOARD_SIZE + 32, banner_h), pygame.SRCALPHA)
        pygame.draw.rect(s, (*C_PANEL_BG, 235), s.get_rect(), border_radius=14)
        pygame.draw.rect(s, color, s.get_rect(), 2, border_radius=14)
        self.screen.blit(s, (BOARD_X - 16, banner_y))

        label = self.font_xl.render(text, True, color)
        self.screen.blit(label, (BOARD_X - 16 + (BOARD_SIZE + 32 - label.get_width()) // 2,
                                  banner_y + (banner_h - label.get_height()) // 2))

    def draw_menu(self, dt):
        self.bg_t += dt
        vertical_gradient(self.screen, (0, 0, WIDTH, HEIGHT), C_BG_TOP, C_BG_BOT)

        for i in range(5):
            fx = (WIDTH / 5.5) * i + 90
            fy = 95 + math.sin(self.bg_t * 0.3 + i * 1.4) * 16
            mark = 'X' if i % 2 == 0 else 'O'
            color = C_X_COLOR if mark == 'X' else C_O_COLOR
            ghost = pygame.Surface((100, 100), pygame.SRCALPHA)
            if mark == 'X':
                lw = 7
                pygame.draw.line(ghost, color, (20, 20), (80, 80), lw)
                pygame.draw.line(ghost, color, (80, 20), (20, 80), lw)
            else:
                pygame.draw.circle(ghost, color, (50, 50), 32, 7)
            ghost.set_alpha(22)
            self.screen.blit(ghost, (fx - 50, fy - 50))

        title = self.font_title.render("TIC-TAC-TOE", True, C_TEXT_MAIN)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 96))
        subtitle = self.font_sm.render("Premium Edition", True, C_TEXT_ACCENT)
        self.screen.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 156))

        pygame.draw.line(self.screen, C_PANEL_LINE, (WIDTH // 2 - 160, 196), (WIDTH // 2 + 160, 196))
        dot = pygame.Rect(0, 0, 6, 6)
        dot.center = (WIDTH // 2, 196)
        pygame.draw.circle(self.screen, C_TEXT_ACCENT, dot.center, 3)

        mx, my = pygame.mouse.get_pos()

        sec0 = self.font_md.render("SELECT MODE", True, C_TEXT_DIM)
        self.screen.blit(sec0, (WIDTH // 2 - sec0.get_width() // 2, 218))
        for btn, key in [(self.btn_mode_ai, 'ai'), (self.btn_mode_pvp, 'pvp')]:
            btn.update((mx, my), dt)
            btn.draw(self.screen, active=(self.menu_mode == key), active_color=C_TEXT_ACCENT)

        if self.menu_mode == 'ai':
            sec1 = self.font_md.render("SELECT DIFFICULTY", True, C_TEXT_DIM)
            self.screen.blit(sec1, (WIDTH // 2 - sec1.get_width() // 2, 358))
            for btn, key in [(self.btn_diff_easy, 'easy'), (self.btn_diff_medium, 'medium'), (self.btn_diff_hard, 'hard')]:
                btn.update((mx, my), dt)
                btn.draw(self.screen, active=(self.menu_difficulty == key), active_color=C_TEXT_ACCENT)

            sec2 = self.font_md.render("SELECT YOUR MARK", True, C_TEXT_DIM)
            self.screen.blit(sec2, (WIDTH // 2 - sec2.get_width() // 2, 468))
            self.btn_mark_x.update((mx, my), dt)
            self.btn_mark_x.draw(self.screen, active=(self.menu_mark == 'X'), active_color=C_X_COLOR)
            self.btn_mark_o.update((mx, my), dt)
            self.btn_mark_o.draw(self.screen, active=(self.menu_mark == 'O'), active_color=C_O_COLOR)
        else:
            icon_y = 408
            ghost = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.line(ghost, C_X_COLOR, (6, 6), (34, 34), 5)
            pygame.draw.line(ghost, C_X_COLOR, (34, 6), (6, 34), 5)
            self.screen.blit(ghost, (WIDTH // 2 - 46, icon_y))
            ghost2 = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(ghost2, C_O_COLOR, (20, 20), 14, 5)
            self.screen.blit(ghost2, (WIDTH // 2 + 6, icon_y))
            note = self.font_sm.render("Two players, one board — take turns clicking cells", True, C_TEXT_DIM)
            self.screen.blit(note, (WIDTH // 2 - note.get_width() // 2, 460))
            note2 = self.font_xs.render("X always moves first", True, C_TEXT_DIM)
            self.screen.blit(note2, (WIDTH // 2 - note2.get_width() // 2, 486))

        self.btn_start.update((mx, my), dt)
        self.btn_start.draw(self.screen, active=True, active_color=C_TEXT_ACCENT)

        hint = self.font_xs.render("Unbeatable AI on Hard — powered by Minimax with alpha-beta pruning", True, C_TEXT_DIM)
        self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 678))

    def handle_menu_click(self, pos):
        if self.btn_mode_ai.rect.collidepoint(pos):
            self.menu_mode = 'ai'
            sfx.play('ui_click')
        elif self.btn_mode_pvp.rect.collidepoint(pos):
            self.menu_mode = 'pvp'
            sfx.play('ui_click')
        elif self.menu_mode == 'ai' and self.btn_diff_easy.rect.collidepoint(pos):
            self.menu_difficulty = 'easy'
            sfx.play('ui_click')
        elif self.menu_mode == 'ai' and self.btn_diff_medium.rect.collidepoint(pos):
            self.menu_difficulty = 'medium'
            sfx.play('ui_click')
        elif self.menu_mode == 'ai' and self.btn_diff_hard.rect.collidepoint(pos):
            self.menu_difficulty = 'hard'
            sfx.play('ui_click')
        elif self.menu_mode == 'ai' and self.btn_mark_x.rect.collidepoint(pos):
            self.menu_mark = 'X'
            sfx.play('ui_click')
        elif self.menu_mode == 'ai' and self.btn_mark_o.rect.collidepoint(pos):
            self.menu_mark = 'O'
            sfx.play('ui_click')
        elif self.btn_start.rect.collidepoint(pos):
            sfx.play('start')
            self.scores = {'X': 0, 'O': 0, 'Draw': 0}
            self.state = self.STATE_PLAYING
            self.new_game()

    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.state == self.STATE_MENU:
                        self.handle_menu_click(event.pos)
                    else:
                        if self.btn_new_game.rect.collidepoint(event.pos):
                            sfx.play('ui_click')
                            self.new_game()
                        elif self.btn_menu.rect.collidepoint(event.pos):
                            sfx.play('ui_click')
                            self.state = self.STATE_MENU
                        else:
                            self.handle_board_click(event.pos)

            if self.state == self.STATE_PLAYING:
                self.hover_cell = self.px_to_cell(pygame.mouse.get_pos())
                self._check_ai_result()

            if self.state == self.STATE_MENU:
                self.draw_menu(dt)
            else:
                self.draw_background(dt)
                self.draw_board_frame()
                self.draw_grid()
                self.draw_marks(dt)
                self.draw_win_line(dt)
                self.particles.update(dt)
                self.particles.draw(self.screen)
                self.draw_panel(dt)
                self.draw_game_over_banner()

            pygame.display.flip()


if __name__ == '__main__':
    TicTacToeGame().run()
