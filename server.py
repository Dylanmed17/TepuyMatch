"""
TepuyMatch 🇻🇪 — Servidor Web de Alta Disponibilidad
===================================================
Servidor Flask que expone la API del juego y sirve la interfaz web responsive.
Usa SciPy MILP (Solver HiGHS) para optimización matemática instantánea (<0.01s).
"""

import os
import sys
import json
import webbrowser
import threading
from flask import Flask, jsonify, request, send_from_directory

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from src.optimization.board_optimizer import BoardOptimizer
from src.game.memory_game import MemoryGame, GameMode
from src.game.ai_player import AIPlayer
from src.data.db_manager import DatabaseManager

app = Flask(__name__, static_folder="web", static_url_path="")

# Persistencia
db = DatabaseManager()
db.sync_from_json()

# Estado global de la sesión
game_state = {
    "game": None,
    "ai": None,
    "optimizer_result": None,
}
game_lock = threading.Lock()


@app.route("/")
def index():
    return send_from_directory("web", "index.html")


@app.route("/assets/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(os.path.join(PROJECT_ROOT, "assets", "images"), filename)


@app.route("/api/states", methods=["GET"])
def get_states():
    """Devuelve los estados venezolanos disponibles para el filtro."""
    try:
        states = db.get_available_states()
        return jsonify(states)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/new-game", methods=["POST"])
def new_game():
    """Crea una nueva partida usando Programación Lineal Entera (SciPy HiGHS)."""
    try:
        data = request.json or {}
        mode = data.get("mode", "Vs_IA")
        ai_difficulty = data.get("ai_difficulty", "Medio")
        rows = int(data.get("rows", 4))
        cols = int(data.get("cols", 4))
        selected_states = data.get("selected_states", [])

        num_pairs = (rows * cols) // 2
        all_landscapes = db.get_all_landscapes()

        # Ejecutar optimización lineal con SciPy MILP
        optimizer = BoardOptimizer(all_landscapes)
        result = optimizer.optimize_board(
            num_pairs=num_pairs,
            selected_states=selected_states if selected_states else None,
            difficulty_level=ai_difficulty,
            force_regional_diversity=True,
        )

        game_mode = GameMode.VS_IA if mode == "Vs_IA" else GameMode.SOLITARIO
        game = MemoryGame(
            landscapes=result["selected_landscapes"],
            mode=game_mode,
            rows=rows,
            cols=cols,
        )
        game.start()

        ai = None
        if game_mode == GameMode.VS_IA:
            ai = AIPlayer(difficulty=ai_difficulty)

        with game_lock:
            game_state["game"] = game
            game_state["ai"] = ai
            game_state["optimizer_result"] = result

        # Serializar tablero
        board = [
            {
                "position": card.position,
                "landscape_id": card.landscape_id,
                "name": card.name,
                "state_name": card.state_name,
                "description": card.description,
                "status": card.status.value,
            }
            for card in game.board
        ]

        return jsonify({
            "board": board,
            "rows": rows,
            "cols": cols,
            "total_pairs": game.total_pairs,
            "mode": mode,
            "ai_difficulty": ai_difficulty,
            "lp_report": result["metadata"],
            "current_player": game.current_player,
        })
    except Exception as e:
        print(f"[Error en /api/new-game]: {e}")
        return jsonify({"error": f"Error al generar partida: {str(e)}"}), 500


@app.route("/api/flip", methods=["POST"])
def flip_card():
    """Voltea una carta seleccionada por el jugador."""
    try:
        with game_lock:
            game = game_state["game"]
            ai = game_state["ai"]
            if not game or game.game_over:
                return jsonify({"error": "No hay partida activa"}), 400

            data = request.json or {}
            position = data.get("position")
            if position is None:
                return jsonify({"error": "Posición requerida"}), 400

            if game.current_player != "Jugador":
                return jsonify({"error": "No es tu turno"}), 400

            card = game.get_card(position)
            if not card or not card.is_face_down:
                return jsonify({"error": "Carta no disponible"}), 400

            result = game.flip_card(position)
            if result is None and game.first_card_flipped is None:
                return jsonify({"error": "Movimiento inválido"}), 400

            # La IA observa la carta volteada por el jugador
            if ai:
                ai.observe_card(position, card.landscape_id)

            response = _build_board_state()

            if result:
                response["turn_result"] = {
                    "is_match": result.is_match,
                    "card1": result.card1.position,
                    "card2": result.card2.position,
                    "landscape_name": result.landscape_name,
                    "landscape_state": result.landscape_state,
                    "landscape_description": result.landscape_description,
                    "player": result.player,
                }
                if result.is_match and ai:
                    ai.forget_matched(result.card1.position, result.card2.position)

            return jsonify(response)
    except Exception as e:
        print(f"[Error en /api/flip]: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/hide-unmatched", methods=["POST"])
def hide_unmatched():
    """Oculta las cartas que no coincidieron."""
    try:
        with game_lock:
            game = game_state["game"]
            if game:
                game.hide_unmatched()
            return jsonify(_build_board_state())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ai-turn", methods=["POST"])
def ai_turn():
    """Ejecuta el turno del agente de Inteligencia Artificial."""
    try:
        with game_lock:
            game = game_state["game"]
            ai = game_state["ai"]
            if not game or not ai or game.game_over:
                return jsonify({"error": "No disponible"}), 400

            if game.current_player != "IA":
                return jsonify({"error": "No es turno de la IA"}), 400

            available = game.get_flippable_positions()
            if len(available) < 2:
                return jsonify(_build_board_state())

            pos1, pos2 = ai.choose_move(available)

            # Voltear primera carta
            game.flip_card(pos1)
            card1 = game.get_card(pos1)
            if card1:
                ai.observe_card(pos1, card1.landscape_id)

            # Voltear segunda carta
            result = game.flip_card(pos2)
            card2 = game.get_card(pos2)
            if card2:
                ai.observe_card(pos2, card2.landscape_id)

            response = _build_board_state()
            response["ai_move"] = {"pos1": pos1, "pos2": pos2}

            if result:
                response["turn_result"] = {
                    "is_match": result.is_match,
                    "card1": result.card1.position,
                    "card2": result.card2.position,
                    "landscape_name": result.landscape_name,
                    "landscape_state": result.landscape_state,
                    "landscape_description": result.landscape_description,
                    "player": result.player,
                }
                if result.is_match:
                    ai.forget_matched(result.card1.position, result.card2.position)

            return jsonify(response)
    except Exception as e:
        print(f"[Error en /api/ai-turn]: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/set-difficulty", methods=["POST"])
def set_difficulty():
    """Permite cambiar la dificultad de la IA en tiempo real durante la partida."""
    try:
        data = request.json or {}
        diff = data.get("ai_difficulty", "Medio")
        ai = game_state.get("ai")
        if ai:
            # Preservar memoria actual si existe, pero cambiar la tasa de retención
            old_memory = ai._memory.copy() if hasattr(ai, '_memory') else {}
            new_ai = AIPlayer(difficulty=diff)
            new_ai._memory = old_memory
            game_state["ai"] = new_ai
            return jsonify({
                "ok": True,
                "ai_difficulty": diff,
                "ai_stats": new_ai.get_stats()
            })
        return jsonify({"ok": True, "ai_difficulty": diff})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/save-score", methods=["POST"])
def save_score():
    """Guarda el récord y métricas en SQLite."""
    try:
        game = game_state["game"]
        data = request.json or {}
        name = data.get("player_name", "Anónimo").strip() or "Anónimo"

        if game:
            state = game.get_game_state()
            db.record_match(
                mode=state["mode"],
                board_size=game.rows * game.cols,
                winner=state["winner"],
                player_score=state["scores"]["Jugador"],
                turns_count=state["turn_number"],
                time_seconds=state["elapsed_time"],
                ai_score=state["scores"].get("IA", 0),
                lp_objective_value=game_state["optimizer_result"]["metadata"]["objective_value"] if game_state["optimizer_result"] else 0,
            )
            db.save_high_score(
                player_name=name,
                mode=state["mode"],
                score=state["scores"]["Jugador"],
                turns=state["turn_number"],
                time_seconds=state["elapsed_time"],
            )

        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/leaderboard", methods=["GET"])
def leaderboard():
    """Devuelve el salón de la fama."""
    try:
        scores = db.get_leaderboard(limit=10)
        return jsonify(scores)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _build_board_state():
    """Construye el estado consolidado de la partida."""
    game = game_state["game"]
    ai = game_state["ai"]
    if not game:
        return {}

    board = [
        {
            "position": card.position,
            "landscape_id": card.landscape_id,
            "name": card.name,
            "state_name": card.state_name,
            "description": card.description,
            "status": card.status.value,
        }
        for card in game.board
    ]

    state = game.get_game_state()

    resp = {
        "board": board,
        "current_player": state["current_player"],
        "scores": state["scores"],
        "turn_number": state["turn_number"],
        "elapsed_time": state["elapsed_time"],
        "game_over": state["game_over"],
        "winner": state["winner"],
        "matched_pairs": state["matched_pairs"],
        "total_pairs": state["total_pairs"],
    }

    if ai:
        resp["ai_stats"] = ai.get_stats()

    return resp


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    url = f"http://localhost:{port}"
    print("=" * 60)
    print(f"  ⛰️  TepuyMatch — Paisajes de Venezuela 🇻🇪")
    print(f"  Servidor activo en: {url}")
    print("=" * 60)
    
    # Abrir navegador solo si se ejecuta localmente
    if "PORT" not in os.environ:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
        
    app.run(host="0.0.0.0", port=port, debug=False)
