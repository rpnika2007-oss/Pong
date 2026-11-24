
import math
import random
import time
import tkinter as tk
from tkinter import ttk


FIELD_WIDTH = 840
FIELD_HEIGHT = 360
FIELD_TOP = 68
PADDLE_WIDTH = 12
PADDLE_HEIGHT = 76
PADDLE_MARGIN = 22
PADDLE_SPEED = 7
PADDLE_LEFTS = (PADDLE_MARGIN, FIELD_WIDTH - PADDLE_MARGIN - PADDLE_WIDTH)
BALL_RADIUS = 8
WINNING_SCORE = 5
FRAME_MS = 16
FRAME_NS = FRAME_MS * 1_000_000
MAX_CATCH_UP_STEPS = 8
SERVE_DELAY_STEPS = math.ceil(1000 / FRAME_MS)
PADDLE_START_Y = (FIELD_HEIGHT - PADDLE_HEIGHT) / 2

START_SPEEDS = {"Лёгкая": 5.0, "Средняя": 6.3, "Сложная": 7.6}
MAX_BALL_SPEED = 11.0
SPEED_GAIN = 0.5
MAX_BOUNCE_ANGLE = math.radians(60)
RUSSIAN_KEYS = {
    "cyrillic_tse": "w", "cyrillic_yeru": "s", "cyrillic_ka": "r",
    "ц": "w", "ы": "s", "к": "r",
}
WINDOWS_LETTER_KEYS = {0x57: "w", 0x53: "s", 0x52: "r"}

BACKGROUND = "#ffffff"
FIELD_COLOR = "#fce4ee"
BALL_COLOR = "#a81756"
BALL_OUTLINE = "#8f194c"
TEXT = "#29222a"
MUTED = "#63535e"
LEFT_COLOR = "#b34569"
RIGHT_COLOR = "#773575"
PINK_BORDER = "#d8aebf"
PINK_SURFACE = "#fff6fa"
PINK_BUTTON = "#fbe2ec"
PINK_START = "#f8cfe0"
PINK_HOVER = "#f6c8dc"
PINK_PRESSED = "#efb5ce"
PINK_DISABLED = "#f9f1f5"
FONT_FAMILY = "Century Gothic"


class GameModel:
    """Храните состояние матча и рассчитывайте движение объектов."""

    def __init__(self):
        """Подготовьте матч со средней сложностью."""
        self.reset(START_SPEEDS["Средняя"])

    def reset(self, start_speed):
        """Обнулите счёт и верните объекты в исходное положение."""
        self.start_speed = start_speed
        self.scores = [0, 0]
        self.winner = None
        self.paddle_y = [PADDLE_START_Y] * 2
        self.serve_steps_remaining = 0
        self._serve(random.choice((-1, 1)))

    def _serve(self, direction):
        self.ball_x = FIELD_WIDTH / 2
        self.ball_y = FIELD_HEIGHT / 2
        self.ball_speed = self.start_speed
        angle = math.radians(random.choice((-18, 18)))
        self.ball_dx = direction * self.ball_speed * math.cos(angle)
        self.ball_dy = self.ball_speed * math.sin(angle)

    def step(self, left_direction, right_direction):
        """Продвиньте матч на один кадр с учётом движения обеих ракеток."""
        if self.winner is not None:
            return

        paddle_starts = self.paddle_y.copy()
        for player, direction in enumerate((left_direction, right_direction)):
            new_y = self.paddle_y[player] + direction * PADDLE_SPEED
            self.paddle_y[player] = min(
                FIELD_HEIGHT - PADDLE_HEIGHT, max(0, new_y)
            )

        if self.serve_steps_remaining:
            self.serve_steps_remaining -= 1
            return

        elapsed = 0.0
        while elapsed < 1:
            target = 0 if self.ball_dx < 0 else 1
            paddle_dy = self.paddle_y[target] - paddle_starts[target]
            paddle_top = paddle_starts[target] + elapsed * paddle_dy
            wall_y = BALL_RADIUS if self.ball_dy < 0 else FIELD_HEIGHT - BALL_RADIUS
            wall_time = (
                (wall_y - self.ball_y) / self.ball_dy if self.ball_dy else math.inf
            )
            remaining = 1 - elapsed
            paddle_time = self._paddle_contact_time(
                target, paddle_top, paddle_dy, min(remaining, wall_time)
            )
            travel_time = min(remaining, wall_time, paddle_time)
            self.ball_x += self.ball_dx * travel_time
            self.ball_y += self.ball_dy * travel_time
            elapsed += travel_time

            if travel_time == wall_time:
                self.ball_y = wall_y
            if travel_time == paddle_time:
                contact_top = paddle_top + paddle_dy * travel_time
                self._bounce(target, self.ball_y - contact_top - PADDLE_HEIGHT / 2)
            elif travel_time == wall_time:
                self.ball_dy = -self.ball_dy

        if self.ball_x + BALL_RADIUS <= 0:
            self._score(1, -1)
        elif self.ball_x - BALL_RADIUS >= FIELD_WIDTH:
            self._score(0, 1)

    def _paddle_contact_time(self, player, top, paddle_dy, limit):
        """Найдите первый контакт круга с ракеткой в её системе отсчёта."""
        left = PADDLE_LEFTS[player]
        right = left + PADDLE_WIDTH
        x, y = self.ball_x, self.ball_y - top
        dx, dy = self.ball_dx, self.ball_dy - paddle_dy
        if not dx:
            return math.inf
        front = right + BALL_RADIUS if player == 0 else left - BALL_RADIUS
        front_time = (front - x) / dx
        if front_time > limit:
            return math.inf

        contact = math.inf
        if 0 <= front_time and 0 <= y + dy * front_time <= PADDLE_HEIGHT:
            contact = front_time

        if dy:
            edge_y = -BALL_RADIUS if dy > 0 else PADDLE_HEIGHT + BALL_RADIUS
            edge_time = (edge_y - y) / dy
            if 0 <= edge_time <= limit and left <= x + dx * edge_time <= right:
                contact = min(contact, edge_time)

        speed_squared = dx * dx + dy * dy
        for corner_x, x_side in ((left, -1), (right, 1)):
            for corner_y, y_side in ((0, -1), (PADDLE_HEIGHT, 1)):
                offset_x, offset_y = x - corner_x, y - corner_y
                projection = offset_x * dx + offset_y * dy
                distance_squared = offset_x * offset_x + offset_y * offset_y
                discriminant = projection**2 - speed_squared * (
                    distance_squared - BALL_RADIUS**2
                )
                if projection >= 0 or discriminant < 0:
                    continue
                hit = (-projection - math.sqrt(discriminant)) / speed_squared
                if (
                    0 <= hit <= limit
                    and (offset_x + dx * hit) * x_side >= 0
                    and (offset_y + dy * hit) * y_side >= 0
                ):
                    contact = min(contact, hit)
        return contact

    def _bounce(self, player, offset):
        # Попадание в центр даёт прямой отскок, попадание в край — до 60°.
        relative_offset = max(-1, min(1, offset / (PADDLE_HEIGHT / 2)))
        angle = relative_offset * MAX_BOUNCE_ANGLE
        self.ball_speed = min(MAX_BALL_SPEED, self.ball_speed + SPEED_GAIN)
        direction = 1 if player == 0 else -1
        self.ball_dx = direction * self.ball_speed * math.cos(angle)
        self.ball_dy = self.ball_speed * math.sin(angle)

    def _score(self, player, serve_direction):
        self.scores[player] += 1
        self._serve(serve_direction)
        if self.scores[player] == WINNING_SCORE:
            self.winner = player + 1
            return
        self.paddle_y = [PADDLE_START_Y] * 2
        self.serve_steps_remaining = SERVE_DELAY_STEPS


class GameRenderer:
    """Рисуйте поле, счёт и состояние матча на Canvas."""

    def __init__(self, canvas):
        """Создайте постоянные элементы поля и подвижные объекты."""
        self.canvas = canvas
        center_x = FIELD_WIDTH / 2
        bottom = FIELD_TOP + FIELD_HEIGHT

        canvas.create_rectangle(
            0, FIELD_TOP, FIELD_WIDTH, bottom, fill=FIELD_COLOR, outline=""
        )
        canvas.create_line(
            center_x, FIELD_TOP + 1, center_x, bottom - 1,
            fill=PINK_BORDER, width=2, dash=(5, 8),
        )
        canvas.create_rectangle(
            1, FIELD_TOP, FIELD_WIDTH - 1, bottom - 1, outline=BALL_OUTLINE
        )

        canvas.create_rectangle(
            center_x - 151, 2, center_x + 151, FIELD_TOP - 7,
            fill=PINK_SURFACE, outline=PINK_BORDER,
        )
        canvas.create_line(center_x, 12, center_x, FIELD_TOP - 17, fill=PINK_BORDER)
        self.score_items = []
        for x, number, color in (
            (center_x - 75, 1, LEFT_COLOR),
            (center_x + 75, 2, RIGHT_COLOR),
        ):
            canvas.create_text(
                x, 13, text=f"ИГРОК {number}", fill=color,
                font=(FONT_FAMILY, -12, "bold"),
            )
            item = canvas.create_text(
                x, 41, fill=color, font=(FONT_FAMILY, -27, "bold")
            )
            self.score_items.append(item)

        self.paddles = [
            canvas.create_rectangle(0, 0, 0, 0, fill=color, outline="")
            for color in (LEFT_COLOR, RIGHT_COLOR)
        ]
        self.ball = canvas.create_oval(0, 0, 0, 0, fill=BALL_COLOR, outline=BALL_OUTLINE)
        center_y = FIELD_TOP + FIELD_HEIGHT / 2
        canvas.create_rectangle(
            center_x - 190, center_y - 48, center_x + 190, center_y + 48,
            fill=BACKGROUND, outline=PINK_BORDER, tags="overlay",
        )
        self.message = canvas.create_text(
            center_x, center_y - 13, fill=TEXT, tags="overlay",
            font=(FONT_FAMILY, 21, "bold"),
        )
        self.hint = canvas.create_text(
            center_x, center_y + 20, fill=MUTED, tags="overlay",
            font=(FONT_FAMILY, 10),
        )

    def draw(self, model, state):
        """Обновите координаты, счёт и сообщение на игровом поле."""
        for player, x in enumerate(PADDLE_LEFTS):
            y = FIELD_TOP + model.paddle_y[player]
            self.canvas.coords(
                self.paddles[player], x, y, x + PADDLE_WIDTH, y + PADDLE_HEIGHT
            )
            self.canvas.itemconfigure(
                self.score_items[player], text=str(model.scores[player])
            )

        x, y = model.ball_x, FIELD_TOP + model.ball_y
        self.canvas.coords(
            self.ball, x - BALL_RADIUS, y - BALL_RADIUS,
            x + BALL_RADIUS, y + BALL_RADIUS,
        )
        if state == "playing" and not model.serve_steps_remaining:
            self.canvas.itemconfigure("overlay", state="hidden")
            return

        titles = {
            "ready": ("До пяти очков", "Выберите сложность и начните игру"),
            "playing": ("Следующая подача", "Можно переместить ракетки"),
            "paused": ("Пауза", "Нажмите пробел, чтобы продолжить"),
            "finished": (
                f"Победил игрок {model.winner}",
                "Нажмите «Начать игру» для нового матча",
            ),
        }
        title, hint = titles[state]
        self.canvas.itemconfigure(self.message, text=title)
        self.canvas.itemconfigure(self.hint, text=hint)
        self.canvas.itemconfigure("overlay", state="normal")


class App:
    """Создайте окно и свяжите управление с игровым циклом."""

    def __init__(self, root):
        """Настройте интерфейс, привязки клавиш и обновление кадров."""
        self.root = root
        self.root.title("Пинг-понг • Игра для двоих")
        self.root.geometry("900x600")
        self.root.resizable(False, False)
        self.root.configure(bg=BACKGROUND)

        self.model = GameModel()
        self.pressed_keys = set()
        self.window_system = self.root.tk.call("tk", "windowingsystem")
        self.difficulty = tk.StringVar(value="Средняя")
        self._build_interface()
        self.root.bind("<KeyPress>", self._key_pressed)
        self.root.bind("<KeyRelease>", self._key_released)
        self.root.bind("<FocusOut>", self._focus_lost)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self._set_state("ready")
        self._tick()

    def _build_interface(self):
        self.root.option_add("*TCombobox*Listbox.font", (FONT_FAMILY, 10))
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "TButton", font=(FONT_FAMILY, 10, "bold"), padding=(13, 7),
            background=PINK_BUTTON, foreground=TEXT, bordercolor=PINK_BORDER,
            lightcolor=PINK_BORDER, darkcolor=PINK_BORDER, focuscolor="#87566b",
        )
        button_colors = [
            ("disabled", PINK_DISABLED), ("pressed", PINK_PRESSED),
            ("active", PINK_HOVER),
        ]
        style.map(
            "TButton", background=button_colors,
            foreground=[("disabled", MUTED)],
        )
        style.configure("Start.TButton", background=PINK_START)
        style.configure(
            "TCombobox", foreground=TEXT, fieldbackground=PINK_SURFACE,
            background=PINK_BUTTON, arrowcolor=TEXT, bordercolor=PINK_BORDER,
            lightcolor=PINK_BORDER, darkcolor=PINK_BORDER, padding=4,
        )
        style.map(
            "TCombobox",
            background=button_colors,
            fieldbackground=[("disabled", PINK_DISABLED), ("readonly", PINK_SURFACE)],
            foreground=[("disabled", MUTED)],
            selectbackground=[("readonly", PINK_SURFACE)],
            selectforeground=[("readonly", TEXT)],
        )

        header = tk.Frame(self.root, bg=BACKGROUND)
        header.pack(fill="x", padx=30, pady=(14, 6))
        tk.Label(
            header, text="Пинг-понг", bg=BACKGROUND, fg=TEXT,
            font=(FONT_FAMILY, 24, "bold"),
        ).pack(side="left")
        tk.Label(
            header, text="Двое игроков · до 5 очков", bg=BACKGROUND,
            fg=MUTED, font=(FONT_FAMILY, 10),
        ).pack(side="right")

        toolbar = tk.Frame(self.root, bg=BACKGROUND)
        toolbar.pack(fill="x", padx=30, pady=(0, 5))
        self.start_button = ttk.Button(
            toolbar, text="Начать игру", command=self._start,
            style="Start.TButton",
        )
        self.start_button.pack(side="left")
        self.pause_button = ttk.Button(
            toolbar, text="Пауза", command=self._toggle_pause
        )
        self.pause_button.pack(side="left", padx=8)
        ttk.Button(
            toolbar, text="Заново", command=self._reset
        ).pack(side="left")
        self.difficulty_box = ttk.Combobox(
            toolbar, textvariable=self.difficulty, values=tuple(START_SPEEDS),
            state="readonly", width=10, font=(FONT_FAMILY, 10),
        )
        self.difficulty_box.pack(side="right")
        tk.Label(
            toolbar, text="Сложность", bg=BACKGROUND, fg=MUTED,
            font=(FONT_FAMILY, 10),
        ).pack(side="right", padx=10)

        self.canvas = tk.Canvas(
            self.root, width=FIELD_WIDTH, height=FIELD_TOP + FIELD_HEIGHT,
            bg=BACKGROUND, highlightthickness=0,
        )
        self.canvas.pack()
        self.renderer = GameRenderer(self.canvas)

        footer = tk.Frame(self.root, bg=BACKGROUND)
        footer.pack(fill="x", padx=30, pady=(13, 0))
        for label, color, side in (
            ("Игрок 1   W / S", LEFT_COLOR, "left"),
            ("Игрок 2   ↑ / ↓", RIGHT_COLOR, "left"),
            ("Пробел — пауза    R — заново", MUTED, "right"),
        ):
            tk.Label(
                footer, text=label, bg=BACKGROUND, fg=color,
                font=(FONT_FAMILY, 10),
            ).pack(side=side, padx=(0, 24) if side == "left" else 0)

    def _start(self):
        self.model.reset(START_SPEEDS[self.difficulty.get()])
        self.pressed_keys.clear()
        self.canvas.focus_set()
        self._set_state("playing")

    def _reset(self):
        self.model.reset(START_SPEEDS[self.difficulty.get()])
        self.pressed_keys.clear()
        self.canvas.focus_set()
        self._set_state("ready")

    def _toggle_pause(self):
        if self.state == "playing":
            next_state = "paused"
        elif self.state == "paused":
            next_state = "playing"
        else:
            return
        self.canvas.focus_set()
        self._set_state(next_state)

    def _set_state(self, state):
        self.state = state
        self._last_tick_ns = time.monotonic_ns()
        self._pending_ns = 0
        self._refresh()

    def _refresh(self):
        match_active = self.state in ("playing", "paused")
        self.start_button.configure(
            state="disabled" if match_active else "normal"
        )
        self.difficulty_box.configure(
            state="disabled" if match_active else "readonly"
        )
        self.pause_button.configure(
            text="Продолжить" if self.state == "paused" else "Пауза",
            state="normal" if match_active else "disabled",
        )
        self.renderer.draw(self.model, self.state)

    def _game_key(self, event):
        key = event.keysym.lower()
        if self.window_system == "win32":
            key = WINDOWS_LETTER_KEYS.get(event.keycode, key)
        return RUSSIAN_KEYS.get(key, key)

    def _key_pressed(self, event):
        key = self._game_key(event)
        if key in self.pressed_keys:
            return
        if key == "r":
            self._reset()
        self.pressed_keys.add(key)
        if key == "space":
            self._toggle_pause()

    def _key_released(self, event):
        self.pressed_keys.discard(self._game_key(event))

    def _focus_lost(self, event):
        # Дождитесь завершения смены фокуса, в том числе между виджетами.
        self.root.after_idle(self._pause_if_unfocused)

    def _pause_if_unfocused(self):
        if self.root.focus_get() is not None:
            return
        self.pressed_keys.clear()
        if self.state == "playing":
            self._set_state("paused")

    def _tick(self):
        now = time.monotonic_ns()
        elapsed = now - self._last_tick_ns
        self._last_tick_ns = now

        if self.state == "playing":
            left = (
                int("s" in self.pressed_keys) - int("w" in self.pressed_keys)
            )
            right = (
                int("down" in self.pressed_keys)
                - int("up" in self.pressed_keys)
            )
            self._pending_ns = min(
                self._pending_ns + elapsed, MAX_CATCH_UP_STEPS * FRAME_NS
            )
            while self._pending_ns >= FRAME_NS:
                self._pending_ns -= FRAME_NS
                self.model.step(left, right)
                if self.model.winner is not None:
                    self._set_state("finished")
                    break
            if self.state == "playing":
                self.renderer.draw(self.model, self.state)

        self.frame_id = self.root.after(FRAME_MS, self._tick)

    def _close(self):
        self.root.after_cancel(self.frame_id)
        self.root.destroy()


if __name__ == "__main__":
    window = tk.Tk()
    app = App(window)
    window.mainloop()
