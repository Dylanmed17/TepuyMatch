"""
Agente Inteligente Autónomo: Toma de Decisiones Secuenciales (IA Canaibot) 🇻🇪
=============================================================================
Modelo Teórico: Sistema de Toma de Decisiones Óptimas en Entornos Parcialmente
Observables (POMDP) con Memoria de Trabajo Estocástica (Modelo de Atkinson-Shiffrin).

Fundamentación de Inteligencia Artificial:
------------------------------------------
El agente opera en un espacio de estados parcialmente observable donde el tablero
contiene información oculta. Para cada turno, el agente:
1. Mantiene un 'Belief State' (estado de creencias / memoria interna) que mapea
   posiciones descubiertas a identidades de paisajes.
2. Aplica una tasa de retención probabilística rho in {0.30, 0.70, 1.00} según la dificultad:
   - Fácil   (Novato): rho = 0.30 (memoria humana imperfecta/degradada).
   - Medio   (Guía):   rho = 0.70 (retención moderada con olvido selectivo).
   - Experto (Nacional): rho = 1.00 (oráculo observacional perfecto).
3. Función de Política de Acción (Policy Function pi(s)):
   - Rama Explotación (Greedy Choice): Si la memoria contiene una pareja completa conocida,
     ejecuta de inmediato ambas acciones para garantizar el punto con certeza P = 1.
   - Rama Exploración Inteligente: Si no hay pareja completa, selecciona una carta desconocida
     para maximizar la ganancia de información. Si la carta descubierta coincide con otra en memoria,
     explota el conocimiento inmediatamente; si no, explora una segunda carta desconocida.
"""

import random
from typing import Dict, List, Optional, Tuple


class AIPlayer:
    """
    Bot que juega al juego de memoria usando una estrategia basada en
    memoria observacional y toma de decisiones óptima.

    Algoritmo de decisión por turno:
    ────────────────────────────────
    1. BUSCAR PAREJA CONOCIDA: ¿Conozco la ubicación de dos cartas
       con el mismo paisaje?
         → SÍ: Voltear ambas directamente (punto seguro).
    2. EXPLORACIÓN INTELIGENTE: Si no hay pareja completa conocida:
         a) Voltear una carta desconocida para descubrir su paisaje.
         b) Consultar la memoria: ¿Ya vi antes la otra copia de
            ese paisaje?
              → SÍ: Voltearla (acierto por memoria).
              → NO: Voltear otra carta desconocida (recopilar info).
    """

    # Probabilidad de recordar una carta vista, según dificultad
    MEMORY_RETENTION = {
        "Facil": 0.30,
        "Medio": 0.70,
        "Experto": 1.00,
    }

    DISPLAY_NAMES = {
        "Facil": "🟢 Turista Novato",
        "Medio": "🟡 Guía Turístico",
        "Experto": "🔴 Experto Nacional",
    }

    def __init__(self, difficulty: str = "Medio"):
        if difficulty not in self.MEMORY_RETENTION:
            raise ValueError(
                f"Dificultad inválida '{difficulty}'. "
                f"Opciones: {list(self.MEMORY_RETENTION.keys())}"
            )
        self.difficulty = difficulty
        self.retention_rate = self.MEMORY_RETENTION[difficulty]
        self.display_name = self.DISPLAY_NAMES[difficulty]

        # Memoria interna: mapea posición → landscape_id
        # Solo contiene las cartas que el bot ha "memorizado"
        self._memory: Dict[int, str] = {}

    def observe_card(self, position: int, landscape_id: str) -> None:
        """
        El bot observa una carta que fue volteada (por él o por el jugador).
        Según su nivel de dificultad, puede olvidarla o memorizarla.
        """
        if random.random() <= self.retention_rate:
            self._memory[position] = landscape_id
        # Si no pasa el umbral de retención, no la guarda (la "olvida")

    def forget_matched(self, position1: int, position2: int) -> None:
        """
        Elimina de la memoria las cartas que ya fueron emparejadas
        (ya no están disponibles en el tablero).
        """
        self._memory.pop(position1, None)
        self._memory.pop(position2, None)

    def choose_move(self, available_positions: List[int]) -> Tuple[int, int]:
        """
        Decide qué dos cartas voltear en su turno.

        Parámetros:
        -----------
        available_positions: List[int]
            Posiciones de cartas que están boca abajo y pueden voltearse.

        Retorna:
        --------
        Tuple[int, int]: Las dos posiciones elegidas para voltear.
        """
        if len(available_positions) < 2:
            # Caso borde: quedan menos de 2 cartas (no debería ocurrir)
            return (available_positions[0], available_positions[0])

        # ───────────────────────────────────────────────────
        # PASO 1: ¿Conozco alguna pareja completa en mi memoria?
        # ───────────────────────────────────────────────────
        known_pair = self._find_known_pair(available_positions)
        if known_pair is not None:
            return known_pair

        # ───────────────────────────────────────────────────
        # PASO 2: Exploración inteligente
        # ───────────────────────────────────────────────────
        # Separar posiciones en "conocidas" (ya vistas) y "desconocidas" (nunca vistas)
        known_positions = [p for p in available_positions if p in self._memory]
        unknown_positions = [p for p in available_positions if p not in self._memory]

        # 2a. Primera carta: preferir una desconocida para explorar
        if unknown_positions:
            first = random.choice(unknown_positions)
        else:
            # Todas son conocidas pero no forman pareja → elegir una al azar
            first = random.choice(available_positions)

        # 2b. Segunda carta: ¿La primera carta reveló algo que ya conocemos?
        #     Simularemos que el bot "recuerda" lo que tiene en memoria.
        #     Si tiene en memoria la posición de la pareja de la primera carta,
        #     puede acertar de inmediato.
        first_landscape = self._memory.get(first)
        if first_landscape is not None:
            # Buscar si tenemos memorizada la otra copia de este paisaje
            partner = self._find_partner_in_memory(first, first_landscape, available_positions)
            if partner is not None:
                return (first, partner)

        # 2c. Si no hay información útil, elegir otra carta al azar
        remaining = [p for p in available_positions if p != first]
        if unknown_positions:
            # Preferir otra desconocida para maximizar exploración
            unknown_remaining = [p for p in unknown_positions if p != first]
            if unknown_remaining:
                second = random.choice(unknown_remaining)
            else:
                second = random.choice(remaining)
        else:
            second = random.choice(remaining)

        return (first, second)

    def _find_known_pair(self, available_positions: List[int]) -> Optional[Tuple[int, int]]:
        """
        Busca en la memoria si hay dos posiciones con el mismo landscape_id,
        ambas aún disponibles en el tablero.
        """
        # Invertir la memoria: landscape_id → [lista de posiciones conocidas]
        landscape_positions: Dict[str, List[int]] = {}
        for pos, lid in self._memory.items():
            if pos in available_positions:
                landscape_positions.setdefault(lid, []).append(pos)

        # ¿Algún paisaje tiene exactamente 2 posiciones conocidas?
        for lid, positions in landscape_positions.items():
            if len(positions) >= 2:
                return (positions[0], positions[1])

        return None

    def _find_partner_in_memory(
        self, exclude_pos: int, landscape_id: str, available_positions: List[int]
    ) -> Optional[int]:
        """
        Busca en la memoria si conocemos la posición de la otra copia
        del paisaje, excluyendo la posición actual.
        """
        for pos, lid in self._memory.items():
            if lid == landscape_id and pos != exclude_pos and pos in available_positions:
                return pos
        return None

    def get_memory_size(self) -> int:
        """Devuelve cuántas cartas tiene memorizadas actualmente."""
        return len(self._memory)

    def get_stats(self) -> Dict[str, any]:
        """Devuelve estadísticas del estado interno del bot."""
        return {
            "difficulty": self.difficulty,
            "display_name": self.display_name,
            "retention_rate": f"{self.retention_rate * 100:.0f}%",
            "cards_memorized": self.get_memory_size(),
        }

    def reset(self) -> None:
        """Reinicia la memoria del bot para una nueva partida."""
        self._memory.clear()
