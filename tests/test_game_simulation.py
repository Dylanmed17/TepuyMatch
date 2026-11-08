"""
Test de integración: Partida completa Jugador vs IA
====================================================
Simula una partida de memoria con un tablero 4x4 (8 parejas)
para validar turnos, puntuación, memoria del bot y fin de juego.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from src.game.memory_game import MemoryGame, GameMode
from src.game.ai_player import AIPlayer


def load_landscapes():
    """Carga los paisajes del catálogo JSON."""
    json_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "data", "landscapes.json"
    )
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_simulation():
    """Simula una partida Jugador vs IA automática."""
    landscapes = load_landscapes()

    # Crear juego 4x4 (8 parejas, 16 cartas)
    game = MemoryGame(
        landscapes=landscapes,
        mode=GameMode.VS_IA,
        rows=4,
        cols=4,
    )
    game.start()

    # Crear bot IA con dificultad Media
    ai = AIPlayer(difficulty="Medio")

    print("=" * 60)
    print("  ⛰️  TepuyMatch — Simulación Jugador vs IA  🇻🇪")
    print("=" * 60)
    print(f"  Tablero: {game.rows}x{game.cols} ({game.total_pairs} parejas)")
    print(f"  Bot IA: {ai.display_name} (retención {ai.retention_rate*100:.0f}%)")
    print("=" * 60)

    max_turns = 100  # Límite de seguridad
    turn = 0

    while not game.game_over and turn < max_turns:
        turn += 1
        current = game.current_player
        available = game.get_flippable_positions()

        if len(available) < 2:
            break

        if current == "IA":
            # Turno del bot
            pos1, pos2 = ai.choose_move(available)
        else:
            # Turno del jugador (simulado: elige al azar)
            import random
            pos1 = random.choice(available)
            remaining = [p for p in available if p != pos1]
            pos2 = random.choice(remaining)

        # Voltear primera carta
        result1 = game.flip_card(pos1)
        card1 = game.get_card(pos1)

        # El bot observa la primera carta (tanto la suya como la del jugador)
        ai.observe_card(pos1, card1.landscape_id)

        # Voltear segunda carta
        result2 = game.flip_card(pos2)
        card2 = game.get_card(pos2)

        # El bot observa la segunda carta
        ai.observe_card(pos2, card2.landscape_id)

        # result2 contiene el resultado del turno
        if result2:
            icon = "✅" if result2.is_match else "❌"
            print(
                f"  Turno {turn:2d} | {current:8s} | "
                f"Pos {pos1:2d} ↔ Pos {pos2:2d} | "
                f"{icon} {'¡PAREJA! ' + result2.landscape_name if result2.is_match else 'No coinciden'}"
            )

            if result2.is_match:
                ai.forget_matched(pos1, pos2)

            if not result2.is_match:
                game.hide_unmatched()

    # Resultado final
    state = game.get_game_state()
    print("\n" + "=" * 60)
    print("  🏆 RESULTADO FINAL")
    print("=" * 60)
    print(f"  👤 Jugador: {state['scores']['Jugador']} parejas")
    print(f"  🤖 IA:      {state['scores']['IA']} parejas")
    print(f"  🏅 Ganador:  {state['winner']}")
    print(f"  🔄 Turnos:   {state['turn_number']}")
    print(f"  ⏱️  Tiempo:   {state['elapsed_time']} seg")
    print(f"  🧠 Bot memorizó: {ai.get_memory_size()} cartas al finalizar")
    print("=" * 60)

    # Verificaciones automáticas
    assert state["game_over"], "ERROR: El juego debería haber terminado"
    assert state["matched_pairs"] == game.total_pairs, "ERROR: No todas las parejas fueron encontradas"
    total_score = state["scores"]["Jugador"] + state["scores"]["IA"]
    assert total_score == game.total_pairs, f"ERROR: Puntuación total ({total_score}) != parejas ({game.total_pairs})"
    print("\n  ✅ Todas las verificaciones pasaron correctamente.")


if __name__ == "__main__":
    run_simulation()
