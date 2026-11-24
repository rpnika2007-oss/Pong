import math
import unittest
from tkinter import ttk
from unittest.mock import Mock, patch

from main import (
    BALL_RADIUS,
    FIELD_HEIGHT,
    FIELD_WIDTH,
    FRAME_NS,
    MAX_CATCH_UP_STEPS,
    PADDLE_HEIGHT,
    PADDLE_LEFTS,
    PADDLE_START_Y,
    PADDLE_WIDTH,
    SERVE_DELAY_STEPS,
    WINNING_SCORE,
    App,
    GameModel,
)


class GameModelTests(unittest.TestCase):
    def setUp(self):
        self.model = GameModel()
        self.model.reset(7.6)

    def set_ball(self, x, y, dx, dy):
        self.model.ball_x = x
        self.model.ball_y = y
        self.model.ball_dx = dx
        self.model.ball_dy = dy

    def test_ball_misses_corner_outside_circle_radius(self):
        self.set_ball(43, 224, -5, 5)
        self.model.step(0, 0)
        self.assertEqual(self.model.ball_dx, -5)
        self.assertEqual((self.model.ball_x, self.model.ball_y), (38, 229))

    def test_ball_hits_corner_after_crossing_front_contact_line(self):
        self.set_ball(43, 227, -8, -2)
        self.model.step(0, 0)
        self.assertGreater(self.model.ball_dx, 0)

    def test_ball_hits_right_paddle_corner_symmetrically(self):
        self.set_ball(797, 227, 8, -2)
        self.model.step(0, 0)
        self.assertLess(self.model.ball_dx, 0)

    def test_ball_uses_remaining_time_after_center_hit(self):
        center = self.model.paddle_y[0] + PADDLE_HEIGHT / 2
        self.set_ball(43, center, -7.6, 0)
        self.model.step(0, 0)
        self.assertAlmostEqual(self.model.ball_x, 42 + 8.1 * (1 - 1 / 7.6))
        self.assertEqual(self.model.ball_y, center)

    def test_bounce_uses_paddle_position_at_time_of_contact(self):
        center_at_contact = self.model.paddle_y[0] + PADDLE_HEIGHT / 2 + 7 / 8
        self.set_ball(43, center_at_contact, -8, 0)
        self.model.step(1, 0)
        self.assertEqual(self.model.ball_y, center_at_contact)
        self.assertAlmostEqual(self.model.ball_dy, 0)

    def test_moving_paddle_does_not_overlap_ball_after_bounce(self):
        self.model.reset(5)
        self.set_ball(35, 227, -5, 0)
        self.model.step(1, 0)
        corner_x = PADDLE_LEFTS[0] + PADDLE_WIDTH
        corner_y = self.model.paddle_y[0] + PADDLE_HEIGHT
        distance = math.hypot(
            self.model.ball_x - corner_x, self.model.ball_y - corner_y
        )
        self.assertGreater(self.model.ball_dx, 0)
        self.assertGreaterEqual(distance, BALL_RADIUS - 1e-9)
        self.assertAlmostEqual(
            math.hypot(self.model.ball_dx, self.model.ball_dy), 5.5
        )

    def test_ball_can_hit_wall_and_paddle_in_same_step(self):
        self.model.paddle_y[0] = 0
        self.set_ball(44, 9, -8, -8)
        self.model.step(0, 0)
        self.assertGreater(self.model.ball_dx, 0)
        self.assertGreater(self.model.ball_dy, 0)
        self.assertGreaterEqual(self.model.ball_y, BALL_RADIUS)
        self.assertAlmostEqual(math.hypot(self.model.ball_dx, self.model.ball_dy), 8.1)

    def test_point_resets_paddles_and_delays_serve(self):
        self.model.paddle_y = [0, FIELD_HEIGHT - PADDLE_HEIGHT]
        self.set_ball(FIELD_WIDTH + BALL_RADIUS - 1, 180, 5, 0)
        self.model.step(0, 0)
        self.assertEqual(self.model.scores, [1, 0])
        self.assertEqual(self.model.paddle_y, [PADDLE_START_Y] * 2)
        center_x = FIELD_WIDTH / 2
        for _ in range(SERVE_DELAY_STEPS):
            self.model.step(1, 0)
            self.assertEqual(self.model.ball_x, center_x)
        self.assertGreater(self.model.paddle_y[0], PADDLE_START_Y)
        self.model.step(0, 0)
        self.assertGreater(self.model.ball_x, center_x)

    def test_winning_point_ends_match_immediately(self):
        self.model.scores[1] = WINNING_SCORE - 1
        self.set_ball(-BALL_RADIUS + 1, 180, -5, 0)
        self.model.step(0, 0)
        self.assertEqual(self.model.winner, 2)
        self.assertEqual(self.model.serve_steps_remaining, 0)
        self.model.reset(5)
        self.assertEqual(self.model.scores, [0, 0])
        self.assertIsNone(self.model.winner)


class AppTests(unittest.TestCase):
    def setUp(self):
        self.app = App.__new__(App)
        self.app.root = Mock()
        self.app.model = Mock(winner=None)
        self.app.renderer = Mock()
        self.app.pressed_keys = {"w", "down"}
        self.app._refresh = Mock()
        with patch("main.time.monotonic_ns", return_value=0):
            self.app._set_state("playing")

    def test_tick_accounts_for_elapsed_time(self):
        with patch("main.time.monotonic_ns", side_effect=[3 * FRAME_NS // 2, 4 * FRAME_NS]):
            self.app._tick()
            self.assertEqual(self.app.model.step.call_count, 1)
            self.app._tick()
        self.assertEqual(self.app.model.step.call_count, 4)
        self.app.model.step.assert_called_with(-1, 1)

    def test_long_delay_limits_catch_up(self):
        with patch("main.time.monotonic_ns", return_value=100 * FRAME_NS):
            self.app._tick()
        self.assertEqual(self.app.model.step.call_count, MAX_CATCH_UP_STEPS)

    def test_pause_does_not_accumulate_time(self):
        with patch("main.time.monotonic_ns", side_effect=[
            FRAME_NS // 2, 99 * FRAME_NS, 100 * FRAME_NS, 101 * FRAME_NS
        ]):
            self.app._set_state("paused")
            self.app._tick()
            self.app.model.step.assert_not_called()
            self.app._set_state("playing")
            self.app._tick()
        self.app.model.step.assert_called_once_with(-1, 1)

    def test_space_on_button_does_not_repeat_tkinter_action(self):
        self.app.window_system = "win32"
        self.app._toggle_pause = Mock()
        event = Mock(keysym="space", keycode=32, widget=Mock(spec=ttk.Button))
        self.app._key_pressed(event)
        self.app._toggle_pause.assert_not_called()

        self.app._key_released(event)
        event.widget = Mock()
        self.app._key_pressed(event)
        self.app._toggle_pause.assert_called_once_with()

    def test_focus_change_within_window_does_not_pause(self):
        self.app.root.focus_get.return_value = Mock()
        self.app._pause_if_unfocused()
        self.assertEqual(self.app.state, "playing")
        self.assertEqual(self.app.pressed_keys, {"w", "down"})

    def test_leaving_window_pauses_and_clears_keys(self):
        self.app.root.focus_get.return_value = None
        self.app._focus_lost(Mock())
        self.app.root.after_idle.assert_called_once_with(self.app._pause_if_unfocused)
        self.app._pause_if_unfocused()
        self.assertEqual(self.app.state, "paused")
        self.assertEqual(self.app.pressed_keys, set())


if __name__ == "__main__":
    unittest.main()
