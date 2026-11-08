"""
Interfaz Gráfica Principal — TepuyMatch 🇻🇪
=============================================
Renderiza el juego completo usando Pygame:
  - Pantalla de inicio con menú y selector de estados/dificultad
  - Tablero de cartas con animación de volteo
  - HUD: marcador, cronómetro, turno actual, miniatura de cámara
  - Pantalla de resultado final con leaderboard
  - Ventana de reporte de Programación Lineal para el profesor
"""

import os
import sys
import json
import time
import math

# Agregar la raíz del proyecto al path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

try:
    import pygame
    import pygame.freetype
except ImportError:
    print("ERROR: Pygame no está instalado. Ejecuta: pip install pygame")
    sys.exit(1)

from src.game.memory_game import MemoryGame, GameMode, CardState
from src.game.ai_player import AIPlayer
from src.optimization.board_optimizer import BoardOptimizer
from src.data.db_manager import DatabaseManager


# ─── Constantes de diseño ───────────────────────────────────────

# Ventana
WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 750
FPS = 60

# Colores (paleta Venezuela / naturaleza)
COLOR_BG = (18, 30, 22)            # Fondo verde muy oscuro
COLOR_BG_GRADIENT = (28, 50, 35)
COLOR_PANEL = (25, 45, 35)
COLOR_ACCENT = (46, 164, 79)       # Verde esmeralda
COLOR_ACCENT_HOVER = (60, 190, 100)
COLOR_GOLD = (218, 165, 32)        # Dorado
COLOR_WHITE = (245, 245, 245)
COLOR_TEXT = (220, 220, 210)
COLOR_TEXT_DIM = (140, 140, 130)
COLOR_RED = (200, 60, 60)
COLOR_BLUE = (60, 120, 200)
COLOR_CARD_BG = (40, 70, 50)
COLOR_MATCHED = (30, 100, 50)
COLOR_OVERLAY = (0, 0, 0, 180)
COLOR_BUTTON = (46, 120, 70)
COLOR_BUTTON_HOVER = (60, 150, 90)

# Cartas
CARD_WIDTH = 100
CARD_HEIGHT = 133
CARD_MARGIN = 12
CARD_BORDER_RADIUS = 8

# Layout
BOARD_OFFSET_X = 40
BOARD_OFFSET_Y = 130
HUD_HEIGHT = 110
SIDEBAR_X = 700
SIDEBAR_WIDTH = 380

# Tiempos
CARD_SHOW_DELAY = 800   # ms que permanecen visibles las cartas fallidas
AI_THINK_DELAY = 600    # ms que la IA "piensa" antes de jugar
AI_FLIP_DELAY = 400     # ms entre la primera y segunda carta de la IA


class GameScreen:
    """Pantalla principal del juego."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("⛰️ TepuyMatch — Paisajes de Venezuela 🇻🇪")

        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()

        # Fuentes
        self.font_title = pygame.font.SysFont("Segoe UI", 36, bold=True)
        self.font_subtitle = pygame.font.SysFont("Segoe UI", 22)
        self.font_body = pygame.font.SysFont("Segoe UI", 16)
        self.font_small = pygame.font.SysFont("Segoe UI", 13)
        self.font_hud = pygame.font.SysFont("Segoe UI", 20, bold=True)
        self.font_button = pygame.font.SysFont("Segoe UI", 18, bold=True)
        self.font_card_name = pygame.font.SysFont("Segoe UI", 11)
        self.font_big = pygame.font.SysFont("Segoe UI", 48, bold=True)

        # Base de datos
        self.db = DatabaseManager()
        self.db.sync_from_json()
        self.all_landscapes = self.db.get_all_landscapes()
        self.available_states = self.db.get_available_states()

        # Imágenes de cartas (cargadas bajo demanda)
        self.card_images = {}
        self.card_back_image = None
        self._load_images()

        # Estado del menú
        self.state = "menu"  # "menu", "playing", "result", "lp_report"
        self.selected_mode = GameMode.VS_IA
        self.selected_ai_diff = "Medio"
        self.selected_board = (4, 4)  # (rows, cols)
        self.selected_states = []     # vacío = todos
        self.show_state_selector = False

        # Estado del juego
        self.game = None
        self.ai = None
        self.optimizer_result = None

        # Animación y temporizadores
        self.pending_hide_time = 0     # timestamp para ocultar cartas fallidas
        self.ai_action_time = 0        # timestamp para la próxima acción de la IA
        self.ai_phase = "idle"         # "idle", "thinking", "first_flip", "second_flip", "wait"
        self.ai_move = (None, None)
        self.match_info_text = ""      # Info del paisaje al hacer match
        self.match_info_timer = 0
        self.hover_card = -1           # Carta sobre la que está el cursor

        # Resultado
        self.result_player_name = ""
        self.typing_active = False

        # Control gestual (inicialmente desactivado; se activa si MediaPipe está disponible)
        self.hand_tracker = None
        self.gesture_enabled = False
        self.gesture_cursor = None     # (x, y) del cursor gestual
        self._init_hand_tracker()

    def _load_images(self):
        """Carga las imágenes de las cartas desde assets/images/."""
        img_dir = os.path.join(PROJECT_ROOT, "assets", "images")

        # Reverso
        back_path = os.path.join(img_dir, "card_back.png")
        if os.path.exists(back_path):
            img = pygame.image.load(back_path)
            self.card_back_image = pygame.transform.smoothscale(img, (CARD_WIDTH, CARD_HEIGHT))
        else:
            # Placeholder de color sólido
            self.card_back_image = pygame.Surface((CARD_WIDTH, CARD_HEIGHT))
            self.card_back_image.fill(COLOR_ACCENT)

        # Frentes de cartas
        for landscape in self.all_landscapes:
            lid = landscape["id"]
            for ext in [".png", ".jpg", ".jpeg"]:
                path = os.path.join(img_dir, f"{lid}{ext}")
                if os.path.exists(path):
                    img = pygame.image.load(path)
                    self.card_images[lid] = pygame.transform.smoothscale(img, (CARD_WIDTH, CARD_HEIGHT))
                    break
            else:
                # Placeholder si no hay imagen
                surf = pygame.Surface((CARD_WIDTH, CARD_HEIGHT))
                surf.fill((60, 100, 70))
                name_render = self.font_card_name.render(landscape["name"][:20], True, COLOR_WHITE)
                surf.blit(name_render, (5, CARD_HEIGHT - 20))
                self.card_images[lid] = surf

    def _init_hand_tracker(self):
        """Intenta inicializar el control gestual."""
        try:
            from src.vision.hand_tracker import HandTracker
            self.hand_tracker = HandTracker(
                screen_width=WINDOW_WIDTH,
                screen_height=WINDOW_HEIGHT,
            )
            if self.hand_tracker.start_camera():
                self.gesture_enabled = True
                print("[TepuyMatch] Cámara web activada para control gestual.")
            else:
                print("[TepuyMatch] No se detectó cámara. Usando solo ratón.")
        except Exception as e:
            print(f"[TepuyMatch] Control gestual no disponible: {e}")
            print("[TepuyMatch] Usando solo ratón.")

    def run(self):
        """Bucle principal del juego."""
        running = True
        while running:
            dt = self.clock.tick(FPS)
            now = pygame.time.get_ticks()

            # Actualizar tracker gestual
            if self.gesture_enabled and self.hand_tracker:
                gesture_state = self.hand_tracker.update()
                self.gesture_cursor = (gesture_state["cursor_x"], gesture_state["cursor_y"])
            else:
                self.gesture_cursor = None

            # Eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state == "playing":
                            self.state = "menu"
                        elif self.state in ("result", "lp_report"):
                            self.state = "menu"
                        else:
                            running = False
                    elif self.state == "result" and self.typing_active:
                        self._handle_typing(event)

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_click(event.pos, now)

            # Clic gestual (pellizco)
            if self.gesture_enabled and self.hand_tracker and self.hand_tracker.click_triggered:
                if self.gesture_cursor:
                    self._handle_click(self.gesture_cursor, now)

            # Lógica del juego
            if self.state == "playing":
                self._update_game_logic(now)

            # Renderizar
            self.screen.fill(COLOR_BG)

            if self.state == "menu":
                self._draw_menu()
            elif self.state == "playing":
                self._draw_game(now)
            elif self.state == "result":
                self._draw_result()
            elif self.state == "lp_report":
                self._draw_lp_report()

            # Cursor gestual (dibujado sobre todo)
            if self.gesture_enabled and self.gesture_cursor and self.hand_tracker and self.hand_tracker.hand_detected:
                gx, gy = self.gesture_cursor
                color = COLOR_GOLD if self.hand_tracker.current_gesture.value == "pinch" else COLOR_ACCENT
                pygame.draw.circle(self.screen, color, (gx, gy), 10, 2)
                pygame.draw.circle(self.screen, color, (gx, gy), 3)

            pygame.display.flip()

        # Limpieza
        if self.hand_tracker:
            self.hand_tracker.stop_camera()
        pygame.quit()

    # ─── MENÚ PRINCIPAL ─────────────────────────────────────────

    def _draw_menu(self):
        """Dibuja la pantalla de inicio."""
        # Título
        title = self.font_title.render("⛰️  TepuyMatch", True, COLOR_GOLD)
        subtitle = self.font_subtitle.render("Juego de Memoria — Paisajes de Venezuela", True, COLOR_TEXT)
        self.screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 40))
        self.screen.blit(subtitle, (WINDOW_WIDTH // 2 - subtitle.get_width() // 2, 85))

        # Separador
        pygame.draw.line(self.screen, COLOR_ACCENT, (100, 120), (WINDOW_WIDTH - 100, 120), 1)

        y = 160

        # Selector de modo
        self._draw_label("Modo de Juego:", 80, y)
        y += 30
        self._draw_option_button("Solitario", 80, y, 200, 38,
                                  self.selected_mode == GameMode.SOLITARIO,
                                  lambda: setattr(self, 'selected_mode', GameMode.SOLITARIO))
        self._draw_option_button("Jugador vs IA", 300, y, 200, 38,
                                  self.selected_mode == GameMode.VS_IA,
                                  lambda: setattr(self, 'selected_mode', GameMode.VS_IA))
        y += 55

        # Dificultad de IA (si es VS IA)
        if self.selected_mode == GameMode.VS_IA:
            self._draw_label("Dificultad de la IA:", 80, y)
            y += 30
            for i, diff in enumerate(["Facil", "Medio", "Experto"]):
                display = {"Facil": "🟢 Turista", "Medio": "🟡 Guía", "Experto": "🔴 Experto"}[diff]
                self._draw_option_button(display, 80 + i * 175, y, 160, 38,
                                          self.selected_ai_diff == diff,
                                          lambda d=diff: setattr(self, 'selected_ai_diff', d))
            y += 55

        # Tamaño del tablero
        self._draw_label("Tamaño del Tablero:", 80, y)
        y += 30
        boards = [((3, 4), "3x4 (6 parejas)"), ((4, 4), "4x4 (8 parejas)"), ((4, 6), "4x6 (12 parejas)")]
        for i, (size, label) in enumerate(boards):
            self._draw_option_button(label, 80 + i * 200, y, 185, 38,
                                      self.selected_board == size,
                                      lambda s=size: setattr(self, 'selected_board', s))
        y += 70

        # Botón JUGAR
        self._draw_button("▶  INICIAR PARTIDA", WINDOW_WIDTH // 2 - 140, y, 280, 55,
                           COLOR_ACCENT, COLOR_ACCENT_HOVER, self._start_game)
        y += 80

        # Info del control
        if self.gesture_enabled:
            info = self.font_small.render("🤚 Control gestual ACTIVO — Mueve la mano para interactuar", True, COLOR_ACCENT)
        else:
            info = self.font_small.render("🖱️ Control por ratón — Cámara no detectada", True, COLOR_TEXT_DIM)
        self.screen.blit(info, (WINDOW_WIDTH // 2 - info.get_width() // 2, WINDOW_HEIGHT - 40))

    # ─── PANTALLA DE JUEGO ──────────────────────────────────────

    def _draw_game(self, now):
        """Dibuja el tablero, HUD y sidebar durante la partida."""
        if not self.game:
            return

        state = self.game.get_game_state()

        # ─── HUD Superior ───
        self._draw_hud(state)

        # ─── Tablero de cartas ───
        grid = self.game.get_board_grid()
        for r, row in enumerate(grid):
            for c, card in enumerate(row):
                x = BOARD_OFFSET_X + c * (CARD_WIDTH + CARD_MARGIN)
                y = BOARD_OFFSET_Y + r * (CARD_HEIGHT + CARD_MARGIN)
                self._draw_card(card, x, y, now)

        # ─── Sidebar (Información) ───
        self._draw_sidebar(state, now)

    def _draw_hud(self, state):
        """Dibuja el HUD superior con marcador y turno."""
        # Fondo del HUD
        hud_rect = pygame.Rect(0, 0, WINDOW_WIDTH, HUD_HEIGHT)
        pygame.draw.rect(self.screen, COLOR_PANEL, hud_rect)
        pygame.draw.line(self.screen, COLOR_ACCENT, (0, HUD_HEIGHT), (WINDOW_WIDTH, HUD_HEIGHT), 2)

        # Título
        title = self.font_hud.render("TepuyMatch", True, COLOR_GOLD)
        self.screen.blit(title, (20, 10))

        # Marcador Jugador
        p_label = self.font_body.render("👤 Jugador", True, COLOR_TEXT)
        p_score = self.font_hud.render(str(state["scores"]["Jugador"]), True, COLOR_WHITE)
        self.screen.blit(p_label, (200, 12))
        self.screen.blit(p_score, (215, 38))

        if state["mode"] == "Vs_IA":
            # Separador "vs"
            vs = self.font_body.render("vs", True, COLOR_TEXT_DIM)
            self.screen.blit(vs, (310, 30))

            # Marcador IA
            ai_label = self.font_body.render("🤖 IA", True, COLOR_TEXT)
            ai_score = self.font_hud.render(str(state["scores"]["IA"]), True, COLOR_WHITE)
            self.screen.blit(ai_label, (370, 12))
            self.screen.blit(ai_score, (380, 38))

        # Turno actual
        turn_color = COLOR_ACCENT if state["current_player"] == "Jugador" else COLOR_RED
        turn_text = f"Turno: {state['current_player']}"
        if self.ai_phase == "thinking":
            turn_text = "Turno: IA (Pensando...)"
        turn_render = self.font_body.render(turn_text, True, turn_color)
        self.screen.blit(turn_render, (500, 15))

        # Cronómetro
        elapsed = state["elapsed_time"]
        mins = int(elapsed) // 60
        secs = int(elapsed) % 60
        time_str = f"⏱️ {mins:02d}:{secs:02d}"
        time_render = self.font_hud.render(time_str, True, COLOR_TEXT)
        self.screen.blit(time_render, (500, 45))

        # Parejas restantes
        remaining = f"Parejas: {state['matched_pairs']}/{state['total_pairs']}"
        rem_render = self.font_body.render(remaining, True, COLOR_TEXT_DIM)
        self.screen.blit(rem_render, (500, 75))

    def _draw_card(self, card, x, y, now):
        """Dibuja una carta individual en el tablero."""
        rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)

        # Hover detection
        mouse_pos = pygame.mouse.get_pos()
        is_hovered = rect.collidepoint(mouse_pos)
        if self.gesture_cursor:
            is_hovered = is_hovered or rect.collidepoint(self.gesture_cursor)

        if card.is_matched:
            # Carta emparejada: mostrar imagen con borde verde
            if card.landscape_id in self.card_images:
                self.screen.blit(self.card_images[card.landscape_id], (x, y))
            pygame.draw.rect(self.screen, COLOR_ACCENT, rect, 3, border_radius=CARD_BORDER_RADIUS)
            # Semitransparencia para indicar que ya fue emparejada
            overlay = pygame.Surface((CARD_WIDTH, CARD_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 60))
            self.screen.blit(overlay, (x, y))

        elif card.is_face_up:
            # Carta revelada: mostrar imagen
            if card.landscape_id in self.card_images:
                self.screen.blit(self.card_images[card.landscape_id], (x, y))
            pygame.draw.rect(self.screen, COLOR_GOLD, rect, 3, border_radius=CARD_BORDER_RADIUS)

        else:
            # Carta boca abajo: mostrar reverso
            if self.card_back_image:
                self.screen.blit(self.card_back_image, (x, y))
            else:
                pygame.draw.rect(self.screen, COLOR_CARD_BG, rect, border_radius=CARD_BORDER_RADIUS)

            pygame.draw.rect(self.screen, COLOR_ACCENT if is_hovered else (60, 80, 65),
                             rect, 2, border_radius=CARD_BORDER_RADIUS)

            # Efecto hover
            if is_hovered and self.game.current_player == "Jugador" and not card.is_matched:
                overlay = pygame.Surface((CARD_WIDTH, CARD_HEIGHT), pygame.SRCALPHA)
                overlay.fill((255, 255, 255, 25))
                self.screen.blit(overlay, (x, y))

    def _draw_sidebar(self, state, now):
        """Dibuja la sidebar derecha con info del match y la PL."""
        sx = SIDEBAR_X
        sy = BOARD_OFFSET_Y

        # Fondo sidebar
        sidebar_rect = pygame.Rect(sx - 10, sy - 10, SIDEBAR_WIDTH, WINDOW_HEIGHT - sy)
        pygame.draw.rect(self.screen, COLOR_PANEL, sidebar_rect, border_radius=8)
        pygame.draw.rect(self.screen, (50, 70, 55), sidebar_rect, 1, border_radius=8)

        # Título
        title = self.font_hud.render("📋 Info de la Partida", True, COLOR_GOLD)
        self.screen.blit(title, (sx, sy))
        sy += 35

        # Info de la PL
        if self.optimizer_result and "metadata" in self.optimizer_result:
            meta = self.optimizer_result["metadata"]
            lp_lines = [
                f"Solver: {meta.get('solver', 'N/A')}",
                f"Estado: {meta.get('status', 'N/A')}",
                f"Z* (Valor Óptimo): {meta.get('objective_value', 0):.1f}",
                f"Variables: {meta.get('variables_count', 0)}",
                f"Restricciones: {meta.get('constraints_count', 0)}",
                f"Tiempo solver: {meta.get('solve_time_seconds', 0):.4f}s",
            ]

            pl_title = self.font_body.render("📐 Programación Lineal", True, COLOR_ACCENT)
            self.screen.blit(pl_title, (sx, sy))
            sy += 25

            for line in lp_lines:
                text = self.font_small.render(line, True, COLOR_TEXT_DIM)
                self.screen.blit(text, (sx + 10, sy))
                sy += 18
            sy += 10

        # Botón para ver reporte completo
        self._draw_button("Ver Reporte PL", sx + 10, sy, 180, 32,
                           COLOR_BUTTON, COLOR_BUTTON_HOVER,
                           lambda: setattr(self, 'state', 'lp_report'))
        sy += 50

        # Info del match actual
        if self.match_info_text and pygame.time.get_ticks() - self.match_info_timer < 4000:
            info_title = self.font_body.render("✅ ¡Pareja encontrada!", True, COLOR_ACCENT)
            self.screen.blit(info_title, (sx, sy))
            sy += 22

            # Wrap text
            words = self.match_info_text.split()
            line = ""
            for word in words:
                test = line + " " + word if line else word
                if self.font_small.size(test)[0] < SIDEBAR_WIDTH - 30:
                    line = test
                else:
                    text = self.font_small.render(line, True, COLOR_TEXT)
                    self.screen.blit(text, (sx + 10, sy))
                    sy += 16
                    line = word
            if line:
                text = self.font_small.render(line, True, COLOR_TEXT)
                self.screen.blit(text, (sx + 10, sy))
                sy += 16

        # Info de IA
        if self.ai and state["mode"] == "Vs_IA":
            sy += 20
            ai_stats = self.ai.get_stats()
            ai_title = self.font_body.render(f"🤖 {ai_stats['display_name']}", True, COLOR_TEXT)
            self.screen.blit(ai_title, (sx, sy))
            sy += 22
            mem_text = self.font_small.render(
                f"Cartas memorizadas: {ai_stats['cards_memorized']}", True, COLOR_TEXT_DIM
            )
            self.screen.blit(mem_text, (sx + 10, sy))

    # ─── LÓGICA DEL JUEGO ───────────────────────────────────────

    def _update_game_logic(self, now):
        """Actualiza la lógica de turnos, IA y temporizadores."""
        if not self.game or self.game.game_over:
            if self.game and self.game.game_over and self.state == "playing":
                self._on_game_over()
            return

        # ¿Hay cartas que ocultar después del delay?
        if self.pending_hide_time > 0 and now >= self.pending_hide_time:
            self.game.hide_unmatched()
            self.pending_hide_time = 0

        # Turno de la IA
        if (self.game.mode == GameMode.VS_IA and
                self.game.current_player == "IA" and
                self.pending_hide_time == 0):
            self._process_ai_turn(now)

    def _process_ai_turn(self, now):
        """Maneja las fases del turno de la IA con delays visuales."""
        if self.ai_phase == "idle":
            # Comenzar a "pensar"
            self.ai_phase = "thinking"
            self.ai_action_time = now + AI_THINK_DELAY
            available = self.game.get_flippable_positions()
            if len(available) >= 2:
                self.ai_move = self.ai.choose_move(available)
            else:
                self.ai_phase = "idle"

        elif self.ai_phase == "thinking" and now >= self.ai_action_time:
            # Voltear primera carta
            pos1, pos2 = self.ai_move
            self.game.flip_card(pos1)
            card1 = self.game.get_card(pos1)
            if card1:
                self.ai.observe_card(pos1, card1.landscape_id)
            self.ai_phase = "first_flip"
            self.ai_action_time = now + AI_FLIP_DELAY

        elif self.ai_phase == "first_flip" and now >= self.ai_action_time:
            # Voltear segunda carta
            pos1, pos2 = self.ai_move
            result = self.game.flip_card(pos2)
            card2 = self.game.get_card(pos2)
            if card2:
                self.ai.observe_card(pos2, card2.landscape_id)

            if result:
                if result.is_match:
                    self.ai.forget_matched(pos1, pos2)
                    self.match_info_text = f"{result.landscape_name} — {result.landscape_state}: {result.landscape_description}"
                    self.match_info_timer = now
                    self.ai_phase = "idle"  # Repite turno
                else:
                    self.pending_hide_time = now + CARD_SHOW_DELAY
                    self.ai_phase = "wait"
            else:
                self.ai_phase = "idle"

        elif self.ai_phase == "wait" and self.pending_hide_time == 0:
            self.ai_phase = "idle"

    def _handle_click(self, pos, now):
        """Procesa un clic del jugador (ratón o gesto)."""
        if self.state == "menu":
            self._handle_menu_click(pos)

        elif self.state == "playing" and self.game and not self.game.game_over:
            if self.game.current_player != "Jugador":
                return
            if self.pending_hide_time > 0:
                return

            # ¿Clic en alguna carta?
            grid = self.game.get_board_grid()
            for r, row in enumerate(grid):
                for c, card in enumerate(row):
                    x = BOARD_OFFSET_X + c * (CARD_WIDTH + CARD_MARGIN)
                    y = BOARD_OFFSET_Y + r * (CARD_HEIGHT + CARD_MARGIN)
                    rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)

                    if rect.collidepoint(pos) and card.is_face_down:
                        result = self.game.flip_card(card.position)

                        # Informar a la IA (observa las cartas del jugador también)
                        if self.ai:
                            self.ai.observe_card(card.position, card.landscape_id)

                        if result:
                            if result.is_match:
                                if self.ai:
                                    self.ai.forget_matched(result.card1.position, result.card2.position)
                                self.match_info_text = f"{result.landscape_name} — {result.landscape_state}: {result.landscape_description}"
                                self.match_info_timer = now
                            else:
                                self.pending_hide_time = now + CARD_SHOW_DELAY
                        return

            # ¿Clic en botones de sidebar?
            # (Los botones ya se registran en _draw_button)

        elif self.state == "result":
            self._handle_result_click(pos)

        elif self.state == "lp_report":
            # Botón volver
            pass

    def _handle_menu_click(self, pos):
        """Los clics del menú se manejan dentro de _draw_button callbacks."""
        pass  # Los botones del menú usan callbacks en _draw_button

    def _handle_result_click(self, pos):
        """Clic en la pantalla de resultados."""
        pass

    def _handle_typing(self, event):
        """Maneja la entrada de texto para el nombre del jugador."""
        if event.key == pygame.K_RETURN:
            if self.result_player_name.strip():
                self._save_score()
            self.typing_active = False
        elif event.key == pygame.K_BACKSPACE:
            self.result_player_name = self.result_player_name[:-1]
        elif len(self.result_player_name) < 20 and event.unicode.isprintable():
            self.result_player_name += event.unicode

    # ─── INICIAR PARTIDA ────────────────────────────────────────

    def _start_game(self):
        """Inicia una nueva partida usando el optimizador de PL."""
        rows, cols = self.selected_board
        num_pairs = (rows * cols) // 2

        # Ejecutar Programación Lineal para seleccionar el tablero óptimo
        optimizer = BoardOptimizer(self.all_landscapes)
        self.optimizer_result = optimizer.optimize_board(
            num_pairs=num_pairs,
            selected_states=self.selected_states if self.selected_states else None,
            difficulty_level=self.selected_ai_diff if self.selected_mode == GameMode.VS_IA else "Medio",
            force_regional_diversity=True,
        )

        selected_landscapes = self.optimizer_result["selected_landscapes"]

        # Crear el juego
        self.game = MemoryGame(
            landscapes=selected_landscapes,
            mode=self.selected_mode,
            rows=rows,
            cols=cols,
        )
        self.game.start()

        # Crear IA si aplica
        if self.selected_mode == GameMode.VS_IA:
            self.ai = AIPlayer(difficulty=self.selected_ai_diff)
        else:
            self.ai = None

        # Reset estados
        self.ai_phase = "idle"
        self.pending_hide_time = 0
        self.match_info_text = ""
        self.state = "playing"

        print(f"[TepuyMatch] Partida iniciada: {rows}x{cols}, "
              f"Z*={self.optimizer_result['metadata']['objective_value']}, "
              f"Solver: {self.optimizer_result['metadata']['solve_time_seconds']}s")

    def _on_game_over(self):
        """Transición a la pantalla de resultados."""
        self.state = "result"
        self.typing_active = True
        self.result_player_name = ""

        # Guardar partida en la base de datos
        if self.game:
            game_state = self.game.get_game_state()
            self.db.record_match(
                mode=game_state["mode"],
                board_size=self.game.rows * self.game.cols,
                winner=game_state["winner"],
                player_score=game_state["scores"]["Jugador"],
                turns_count=game_state["turn_number"],
                time_seconds=game_state["elapsed_time"],
                ai_difficulty=self.selected_ai_diff if self.ai else None,
                ai_score=game_state["scores"].get("IA", 0),
                lp_objective_value=self.optimizer_result["metadata"]["objective_value"] if self.optimizer_result else 0,
            )

    def _save_score(self):
        """Guarda el récord del jugador."""
        if self.game and self.result_player_name.strip():
            state = self.game.get_game_state()
            self.db.save_high_score(
                player_name=self.result_player_name.strip(),
                mode=state["mode"],
                score=state["scores"]["Jugador"],
                turns=state["turn_number"],
                time_seconds=state["elapsed_time"],
            )

    # ─── PANTALLA DE RESULTADOS ─────────────────────────────────

    def _draw_result(self):
        """Dibuja la pantalla de fin de partida."""
        if not self.game:
            return

        state = self.game.get_game_state()

        # Fondo oscuro
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        # Panel central
        panel_w, panel_h = 500, 450
        px = (WINDOW_WIDTH - panel_w) // 2
        py = (WINDOW_HEIGHT - panel_h) // 2
        panel_rect = pygame.Rect(px, py, panel_w, panel_h)
        pygame.draw.rect(self.screen, COLOR_PANEL, panel_rect, border_radius=12)
        pygame.draw.rect(self.screen, COLOR_GOLD, panel_rect, 2, border_radius=12)

        y = py + 20

        # Título
        winner = state["winner"]
        if winner == "Jugador":
            title_text = "🏆 ¡GANASTE!"
            title_color = COLOR_GOLD
        elif winner == "IA":
            title_text = "🤖 Ganó la IA"
            title_color = COLOR_RED
        else:
            title_text = "🤝 ¡Empate!"
            title_color = COLOR_ACCENT

        title = self.font_big.render(title_text, True, title_color)
        self.screen.blit(title, (px + (panel_w - title.get_width()) // 2, y))
        y += 70

        # Estadísticas
        stats = [
            f"👤 Jugador: {state['scores']['Jugador']} parejas",
            f"🤖 IA: {state['scores']['IA']} parejas" if state["mode"] == "Vs_IA" else "",
            f"🔄 Turnos totales: {state['turn_number']}",
            f"⏱️ Tiempo: {state['elapsed_time']:.1f} segundos",
        ]
        for s in stats:
            if s:
                text = self.font_body.render(s, True, COLOR_TEXT)
                self.screen.blit(text, (px + 40, y))
                y += 28

        y += 15

        # Input para nombre
        name_label = self.font_body.render("Tu nombre para el récord:", True, COLOR_TEXT_DIM)
        self.screen.blit(name_label, (px + 40, y))
        y += 28

        input_rect = pygame.Rect(px + 40, y, panel_w - 80, 35)
        border_color = COLOR_ACCENT if self.typing_active else COLOR_TEXT_DIM
        pygame.draw.rect(self.screen, (30, 50, 40), input_rect, border_radius=5)
        pygame.draw.rect(self.screen, border_color, input_rect, 2, border_radius=5)

        name_text = self.font_body.render(self.result_player_name + ("_" if self.typing_active else ""), True, COLOR_WHITE)
        self.screen.blit(name_text, (px + 50, y + 7))
        y += 55

        # Botones
        self._draw_button("Guardar y Volver al Menú", px + 40, y, 250, 40,
                           COLOR_ACCENT, COLOR_ACCENT_HOVER,
                           self._result_save_and_menu)
        self._draw_button("Ver Reporte PL", px + 310, y, 150, 40,
                           COLOR_BUTTON, COLOR_BUTTON_HOVER,
                           lambda: setattr(self, 'state', 'lp_report'))

    def _result_save_and_menu(self):
        """Guarda el score y vuelve al menú."""
        if self.result_player_name.strip():
            self._save_score()
        self.state = "menu"

    # ─── REPORTE DE PROGRAMACIÓN LINEAL ─────────────────────────

    def _draw_lp_report(self):
        """Pantalla que muestra al profesor el modelo de PL resuelto."""
        # Fondo
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        panel_w, panel_h = 650, 550
        px = (WINDOW_WIDTH - panel_w) // 2
        py = (WINDOW_HEIGHT - panel_h) // 2
        panel = pygame.Rect(px, py, panel_w, panel_h)
        pygame.draw.rect(self.screen, COLOR_PANEL, panel, border_radius=12)
        pygame.draw.rect(self.screen, COLOR_GOLD, panel, 2, border_radius=12)

        y = py + 20

        title = self.font_hud.render("📐 Reporte de Programación Lineal", True, COLOR_GOLD)
        self.screen.blit(title, (px + 20, y))
        y += 40

        if self.optimizer_result and "metadata" in self.optimizer_result:
            meta = self.optimizer_result["metadata"]

            lines = [
                ("Problema:", "Selección Óptima de Tablero (PLB)"),
                ("Tipo:", "Programación Lineal Entera / Binaria"),
                ("Solver:", str(meta.get("solver", "N/A"))),
                ("Estado de la Solución:", str(meta.get("status", "N/A"))),
                ("", ""),
                ("Valor Óptimo Z*:", f"{meta.get('objective_value', 0):.2f}"),
                ("Num. Variables (paisajes candidatos):", str(meta.get("variables_count", 0))),
                ("Num. Restricciones:", str(meta.get("constraints_count", 0))),
                ("Parejas seleccionadas:", str(meta.get("total_pairs", 0))),
                ("Total de cartas en tablero:", str(meta.get("total_cards", 0))),
                ("Dificultad total acumulada:", str(meta.get("total_difficulty", 0))),
                ("Cotas de dificultad [min, max]:", str(meta.get("difficulty_bounds", "N/A"))),
                ("Tiempo de resolución:", f"{meta.get('solve_time_seconds', 0):.4f} segundos"),
                ("", ""),
                ("Paisajes seleccionados por la PL:", ""),
            ]

            for label, value in lines:
                if label == "" and value == "":
                    y += 8
                    continue
                label_render = self.font_small.render(label, True, COLOR_TEXT_DIM)
                value_render = self.font_small.render(value, True, COLOR_WHITE)
                self.screen.blit(label_render, (px + 30, y))
                self.screen.blit(value_render, (px + 30 + label_render.get_width() + 8, y))
                y += 20

            # Lista de paisajes seleccionados
            for ls in self.optimizer_result.get("selected_landscapes", []):
                text = f"  • {ls['name']} ({ls['state']}) — v={ls['cultural_value']}, d={ls['difficulty']}"
                render = self.font_small.render(text, True, COLOR_ACCENT)
                self.screen.blit(render, (px + 30, y))
                y += 17

        # Botón volver
        self._draw_button("← Volver", px + panel_w - 140, py + panel_h - 50, 120, 35,
                           COLOR_BUTTON, COLOR_BUTTON_HOVER,
                           lambda: setattr(self, 'state', 'playing' if self.game and not self.game.game_over else 'menu'))

    # ─── UTILIDADES DE DIBUJO ───────────────────────────────────

    def _draw_label(self, text, x, y):
        """Dibuja una etiqueta de texto."""
        render = self.font_body.render(text, True, COLOR_TEXT)
        self.screen.blit(render, (x, y))

    def _draw_button(self, text, x, y, w, h, color, hover_color, callback):
        """Dibuja un botón interactivo y ejecuta callback si se hace clic."""
        rect = pygame.Rect(x, y, w, h)
        mouse_pos = pygame.mouse.get_pos()
        is_hovered = rect.collidepoint(mouse_pos)
        if self.gesture_cursor:
            is_hovered = is_hovered or rect.collidepoint(self.gesture_cursor)

        bg_color = hover_color if is_hovered else color
        pygame.draw.rect(self.screen, bg_color, rect, border_radius=6)

        text_render = self.font_button.render(text, True, COLOR_WHITE)
        tx = x + (w - text_render.get_width()) // 2
        ty = y + (h - text_render.get_height()) // 2
        self.screen.blit(text_render, (tx, ty))

        # Detectar clic
        if is_hovered and pygame.mouse.get_pressed()[0]:
            callback()

    def _draw_option_button(self, text, x, y, w, h, selected, callback):
        """Dibuja un botón de opción (toggle)."""
        rect = pygame.Rect(x, y, w, h)
        mouse_pos = pygame.mouse.get_pos()
        is_hovered = rect.collidepoint(mouse_pos)

        if selected:
            pygame.draw.rect(self.screen, COLOR_ACCENT, rect, border_radius=6)
        else:
            pygame.draw.rect(self.screen, (40, 60, 48), rect, border_radius=6)
            pygame.draw.rect(self.screen, (70, 90, 75), rect, 1, border_radius=6)

        text_color = COLOR_WHITE if selected else COLOR_TEXT_DIM
        text_render = self.font_body.render(text, True, text_color)
        tx = x + (w - text_render.get_width()) // 2
        ty = y + (h - text_render.get_height()) // 2
        self.screen.blit(text_render, (tx, ty))

        if is_hovered and pygame.mouse.get_pressed()[0]:
            callback()
