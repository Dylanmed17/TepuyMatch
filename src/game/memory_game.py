"""
Motor del Juego de Memoria Tradicional
=======================================
Proyecto: TepuyMatch 🇻🇪

Gestiona el tablero de cartas, los turnos (Solitario o Vs IA),
la verificación de parejas y el sistema de puntuación.
"""

import random
import time
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class GameMode(Enum):
    SOLITARIO = "Solitario"
    VS_IA = "Vs_IA"


class CardState(Enum):
    FACE_DOWN = "face_down"      # Carta boca abajo (oculta)
    FACE_UP = "face_up"          # Carta revelada temporalmente
    MATCHED = "matched"          # Carta emparejada (permanece visible)


class Card:
    """Representa una carta individual del tablero."""

    def __init__(self, landscape_id: str, name: str, state_name: str,
                 description: str, position: int):
        self.landscape_id = landscape_id
        self.name = name
        self.state_name = state_name
        self.description = description
        self.position = position
        self.status = CardState.FACE_DOWN

    def flip_up(self) -> None:
        """Voltea la carta boca arriba."""
        if self.status == CardState.FACE_DOWN:
            self.status = CardState.FACE_UP

    def flip_down(self) -> None:
        """Voltea la carta boca abajo."""
        if self.status == CardState.FACE_UP:
            self.status = CardState.FACE_DOWN

    def mark_matched(self) -> None:
        """Marca la carta como emparejada permanentemente."""
        self.status = CardState.MATCHED

    @property
    def is_face_down(self) -> bool:
        return self.status == CardState.FACE_DOWN

    @property
    def is_face_up(self) -> bool:
        return self.status == CardState.FACE_UP

    @property
    def is_matched(self) -> bool:
        return self.status == CardState.MATCHED

    def __repr__(self) -> str:
        return f"Card(pos={self.position}, id='{self.landscape_id}', status={self.status.value})"


class TurnResult:
    """Resultado de un turno completo (dos cartas volteadas)."""

    def __init__(self, card1: Card, card2: Card, is_match: bool,
                 player: str, turn_number: int):
        self.card1 = card1
        self.card2 = card2
        self.is_match = is_match
        self.player = player          # "Jugador" o "IA"
        self.turn_number = turn_number
        self.landscape_name = card1.name if is_match else ""
        self.landscape_state = card1.state_name if is_match else ""
        self.landscape_description = card1.description if is_match else ""


class MemoryGame:
    """
    Motor principal del juego de memoria de paisajes venezolanos.

    Reglas tradicionales:
    - El tablero contiene K parejas de cartas (2K cartas en total).
    - En cada turno el jugador voltea exactamente 2 cartas.
    - Si las cartas son iguales (mismo paisaje): quedan descubiertas,
      el jugador suma 1 punto y REPITE turno.
    - Si son distintas: se voltean boca abajo tras un breve instante
      y el turno pasa al siguiente jugador (o continúa en solitario).
    - La partida termina cuando todas las parejas han sido encontradas.
    """

    def __init__(
        self,
        landscapes: List[Dict[str, Any]],
        mode: GameMode = GameMode.SOLITARIO,
        rows: int = 4,
        cols: int = 4,
    ):
        self.mode = mode
        self.rows = rows
        self.cols = cols
        self.total_pairs = (rows * cols) // 2
        self.landscapes = landscapes

        # Estado del juego
        self.board: List[Card] = []
        self.turn_number: int = 0
        self.current_player: str = "Jugador"  # "Jugador" o "IA"
        self.scores: Dict[str, int] = {"Jugador": 0, "IA": 0}
        self.first_card_flipped: Optional[Card] = None
        self.history: List[TurnResult] = []
        self.game_started: bool = False
        self.game_over: bool = False
        self.start_time: float = 0.0
        self.end_time: float = 0.0

        # Construir el tablero
        self._build_board()

    def _build_board(self) -> None:
        """Construye el tablero con parejas de cartas barajadas."""
        total_cards = self.rows * self.cols

        # Seleccionar los paisajes necesarios (ya vienen del optimizador de PL)
        selected = self.landscapes[:self.total_pairs]

        # Crear dos cartas por paisaje (la pareja)
        cards_data = []
        for landscape in selected:
            for _ in range(2):
                cards_data.append(landscape)

        # Barajar aleatoriamente las posiciones
        random.shuffle(cards_data)

        # Crear los objetos Card con su posición en el tablero
        self.board = []
        for pos, data in enumerate(cards_data):
            card = Card(
                landscape_id=data["id"],
                name=data["name"],
                state_name=data["state"],
                description=data.get("description", ""),
                position=pos,
            )
            self.board.append(card)

    def start(self) -> None:
        """Inicia la partida y el cronómetro."""
        self.game_started = True
        self.game_over = False
        self.start_time = time.time()
        self.turn_number = 0
        self.scores = {"Jugador": 0, "IA": 0}
        self.current_player = "Jugador"
        self.first_card_flipped = None
        self.history = []

    def get_card(self, position: int) -> Optional[Card]:
        """Devuelve la carta en la posición indicada del tablero."""
        if 0 <= position < len(self.board):
            return self.board[position]
        return None

    def get_flippable_positions(self) -> List[int]:
        """Devuelve las posiciones de cartas que aún pueden voltearse."""
        return [
            card.position for card in self.board
            if card.is_face_down
        ]

    def flip_card(self, position: int) -> Optional[TurnResult]:
        """
        Voltea una carta en la posición dada.

        - Si es la primera carta del turno: solo la revela y espera la segunda.
        - Si es la segunda carta del turno: evalúa si hay pareja y retorna
          el resultado del turno completo.

        Retorna TurnResult si se completó un turno, None si fue la primera carta.
        """
        if self.game_over or not self.game_started:
            return None

        card = self.get_card(position)
        if card is None or not card.is_face_down:
            return None

        card.flip_up()

        # ¿Es la primera carta del turno?
        if self.first_card_flipped is None:
            self.first_card_flipped = card
            return None

        # Es la segunda carta: evaluar si hay match
        first = self.first_card_flipped
        second = card
        self.first_card_flipped = None
        self.turn_number += 1

        is_match = first.landscape_id == second.landscape_id

        if is_match:
            # ¡Pareja encontrada!
            first.mark_matched()
            second.mark_matched()
            self.scores[self.current_player] += 1
            # Regla tradicional: si acierta, REPITE turno (no cambia current_player)
        else:
            # No es pareja: las cartas deben voltearse boca abajo.
            # La UI se encargará del delay visual antes de llamar a hide_unmatched().
            pass

        result = TurnResult(
            card1=first,
            card2=second,
            is_match=is_match,
            player=self.current_player,
            turn_number=self.turn_number,
        )
        self.history.append(result)

        # Verificar si el juego terminó
        if self._check_game_over():
            self.game_over = True
            self.end_time = time.time()

        # Si falló y estamos en modo Vs IA, cambiar turno
        if not is_match and not self.game_over:
            self._switch_turn()

        return result

    def hide_unmatched(self) -> None:
        """
        Voltea boca abajo todas las cartas que están face_up pero no matched.
        Debe llamarse desde la UI después de mostrar brevemente las cartas fallidas.
        """
        for card in self.board:
            if card.is_face_up:
                card.flip_down()

    def _switch_turn(self) -> None:
        """Alterna el turno entre Jugador e IA (solo en modo Vs IA)."""
        if self.mode == GameMode.VS_IA:
            self.current_player = "IA" if self.current_player == "Jugador" else "Jugador"

    def _check_game_over(self) -> bool:
        """El juego termina cuando todas las cartas han sido emparejadas."""
        return all(card.is_matched for card in self.board)

    def get_winner(self) -> str:
        """Devuelve el ganador de la partida."""
        if not self.game_over:
            return ""
        if self.mode == GameMode.SOLITARIO:
            return "Jugador"
        if self.scores["Jugador"] > self.scores["IA"]:
            return "Jugador"
        elif self.scores["IA"] > self.scores["Jugador"]:
            return "IA"
        else:
            return "Empate"

    def get_elapsed_time(self) -> float:
        """Devuelve el tiempo transcurrido en segundos."""
        if not self.game_started:
            return 0.0
        end = self.end_time if self.game_over else time.time()
        return round(end - self.start_time, 2)

    def get_board_grid(self) -> List[List[Card]]:
        """Devuelve el tablero organizado como matriz 2D (filas x columnas)."""
        grid = []
        for r in range(self.rows):
            row = []
            for c in range(self.cols):
                idx = r * self.cols + c
                row.append(self.board[idx])
            grid.append(row)
        return grid

    def get_game_state(self) -> Dict[str, Any]:
        """Devuelve un resumen completo del estado actual del juego."""
        matched_pairs = sum(1 for c in self.board if c.is_matched) // 2
        return {
            "mode": self.mode.value,
            "board_size": f"{self.rows}x{self.cols}",
            "total_pairs": self.total_pairs,
            "matched_pairs": matched_pairs,
            "remaining_pairs": self.total_pairs - matched_pairs,
            "current_player": self.current_player,
            "scores": dict(self.scores),
            "turn_number": self.turn_number,
            "elapsed_time": self.get_elapsed_time(),
            "game_over": self.game_over,
            "winner": self.get_winner(),
        }
