"""
TepuyMatch 🇻🇪 — Servidor Web
==============================
Servidor Flask que expone la API del juego y sirve la interfaz web.
Ejecuta: python server.py → se abre http://localhost:5000 en el navegador.
"""

import os
import sys
import json
import webbrowser
import threading
from flask import Flask, jsonify, request, send_from_directory, send_file

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from src.optimization.board_optimizer import BoardOptimizer
from src.game.memory_game import MemoryGame, GameMode
from src.game.ai_player import AIPlayer
from src.data.db_manager import DatabaseManager

app = Flask(__name__, static_folder="web", static_url_path="")

# Estado global del juego (una partida a la vez)
db = DatabaseManager()
db.sync_from_json()

game_state = {
    "game": None,
    "ai": None,
    "optimizer_result": None,
}


@app.route("/")
def index():
    return send_from_directory("web", "index.html")


@app.route("/assets/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(os.path.join(PROJECT_ROOT, "assets", "images"), filename)


@app.route("/api/landscapes", methods=["GET"])
def get_landscapes():
    """Devuelve todos los paisajes del catálogo."""
    landscapes = db.get_all_landscapes()
    return jsonify(landscapes)


@app.route("/api/states", methods=["GET"])
def get_states():
    """Devuelve los estados disponibles."""
    states = db.get_available_states()
    return jsonify(states)


@app.route("/api/new-game", methods=["POST"])
def new_game():
    """Crea una nueva partida usando Programación Lineal."""
    data = request.json or {}
    mode = data.get("mode", "Vs_IA")
    ai_difficulty = data.get("ai_difficulty", "Medio")
    rows = data.get("rows", 4)
    cols = data.get("cols", 4)
    selected_states = data.get("selected_states", [])

    num_pairs = (rows * cols) // 2
    all_landscapes = db.get_all_landscapes()

    # Ejecutar Programación Lineal
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

    game_state["game"] = game
    game_state["ai"] = ai
    game_state["optimizer_result"] = result

    # Construir el tablero para el frontend
    board = []
    for card in game.board:
        board.append({
            "position": card.position,
            "landscape_id": card.landscape_id,
            "name": card.name,
            "state_name": card.state_name,
            "description": card.description,
            "status": card.status.value,
        })

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


@app.route("/api/flip", methods=["POST"])
def flip_card():
    """Voltea una carta del jugador."""
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

    # La IA observa
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


@app.route("/api/hide-unmatched", methods=["POST"])
def hide_unmatched():
    """Voltea boca abajo las cartas no emparejadas."""
    game = game_state["game"]
    if game:
        game.hide_unmatched()
    return jsonify(_build_board_state())


@app.route("/api/ai-turn", methods=["POST"])
def ai_turn():
    """Ejecuta el turno completo de la IA."""
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

    # Primera carta
    game.flip_card(pos1)
    card1 = game.get_card(pos1)
    if card1:
        ai.observe_card(pos1, card1.landscape_id)

    # Segunda carta
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


@app.route("/api/save-score", methods=["POST"])
def save_score():
    """Guarda el récord del jugador."""
    game = game_state["game"]
    data = request.json or {}
    name = data.get("player_name", "Anónimo")

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


@app.route("/api/leaderboard", methods=["GET"])
def leaderboard():
    """Devuelve la tabla de récords."""
    scores = db.get_leaderboard(limit=10)
    return jsonify(scores)


def _build_board_state():
    """Construye el estado completo del tablero para el frontend."""
    game = game_state["game"]
    ai = game_state["ai"]
    if not game:
        return {}

    board = []
    for card in game.board:
        board.append({
            "position": card.position,
            "landscape_id": card.landscape_id,
            "name": card.name,
            "state_name": card.state_name,
            "description": card.description,
            "status": card.status.value,
        })

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
    port = 5000
    url = f"http://localhost:{port}"
    print("=" * 50)
    print(f"  ⛰️  TepuyMatch — Paisajes de Venezuela 🇻🇪")
    print(f"  Abriendo en: {url}")
    print("=" * 50)
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host="0.0.0.0", port=port, debug=False)
