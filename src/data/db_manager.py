"""
Módulo de Gestión de Base de Datos (SQLite)
===========================================
Proyecto: TepuyMatch 🇻🇪
Gestiona el catálogo de paisajes venezolanos, el historial de partidas
con métricas de Investigación de Operaciones (PL) y la tabla de récords.
"""

import sqlite3
import json
import os
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "tepuy_match.db"
)
DEFAULT_JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "landscapes.json"
)


class DatabaseManager:
    """Administrador de persistencia relacional SQLite para TepuyMatch."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_database()

    def get_connection(self) -> sqlite3.Connection:
        """Obtiene una conexión con soporte de diccionario en filas."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self) -> None:
        """Crea las tablas relacionales si no existen."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Catálogo de Paisajes Venezolanos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS landscapes (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    state TEXT NOT NULL,
                    region TEXT NOT NULL,
                    difficulty INTEGER NOT NULL CHECK (difficulty BETWEEN 1 AND 3),
                    cultural_value INTEGER NOT NULL CHECK (cultural_value BETWEEN 1 AND 10),
                    description TEXT NOT NULL,
                    image_path TEXT
                );
            """)

            # 2. Historial de Partidas y Métricas de Investigación de Operaciones
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mode TEXT NOT NULL CHECK (mode IN ('Solitario', 'Vs_IA')),
                    ai_difficulty TEXT,
                    board_size INTEGER NOT NULL,
                    winner TEXT NOT NULL,
                    player_score INTEGER NOT NULL,
                    ai_score INTEGER DEFAULT 0,
                    turns_count INTEGER NOT NULL,
                    time_seconds REAL NOT NULL,
                    lp_objective_value REAL DEFAULT 0.0,
                    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 3. Tabla de Mejores Récords (Leaderboard)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS high_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    turns INTEGER NOT NULL,
                    time_seconds REAL NOT NULL,
                    achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            conn.commit()

    def sync_from_json(self, json_path: str = DEFAULT_JSON_PATH) -> int:
        """
        Sincroniza los paisajes desde el archivo JSON hacia SQLite.
        Inserta nuevos o actualiza existentes.
        """
        if not os.path.exists(json_path):
            return 0

        with open(json_path, "r", encoding="utf-8") as f:
            landscapes = json.load(f)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for item in landscapes:
                cursor.execute("""
                    INSERT INTO landscapes (
                        id, name, state, region, difficulty, cultural_value, description, image_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name,
                        state=excluded.state,
                        region=excluded.region,
                        difficulty=excluded.difficulty,
                        cultural_value=excluded.cultural_value,
                        description=excluded.description,
                        image_path=excluded.image_path;
                """, (
                    item["id"],
                    item["name"],
                    item["state"],
                    item["region"],
                    item["difficulty"],
                    item["cultural_value"],
                    item["description"],
                    item.get("image_path", f"assets/images/{item['id']}.jpg")
                ))
            conn.commit()

        return len(landscapes)

    def get_all_landscapes(self) -> List[Dict[str, Any]]:
        """Devuelve todos los paisajes registrados como lista de diccionarios."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM landscapes ORDER BY cultural_value DESC, name ASC;")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_available_states(self) -> List[str]:
        """Devuelve la lista única de estados con paisajes en la base de datos."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT state FROM landscapes ORDER BY state ASC;")
            return [row["state"] for row in cursor.fetchall()]

    def record_match(
        self,
        mode: str,
        board_size: int,
        winner: str,
        player_score: int,
        turns_count: int,
        time_seconds: float,
        ai_difficulty: Optional[str] = None,
        ai_score: int = 0,
        lp_objective_value: float = 0.0
    ) -> int:
        """Guarda una partida jugada en el historial."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO matches (
                    mode, ai_difficulty, board_size, winner, player_score,
                    ai_score, turns_count, time_seconds, lp_objective_value
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                mode, ai_difficulty, board_size, winner, player_score,
                ai_score, turns_count, round(time_seconds, 2), round(lp_objective_value, 2)
            ))
            conn.commit()
            return cursor.lastrowid

    def save_high_score(
        self,
        player_name: str,
        mode: str,
        score: int,
        turns: int,
        time_seconds: float
    ) -> int:
        """Registra un nuevo récord en la tabla de clasificaciones."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO high_scores (player_name, mode, score, turns, time_seconds)
                VALUES (?, ?, ?, ?, ?);
            """, (player_name, mode, score, turns, round(time_seconds, 2)))
            conn.commit()
            return cursor.lastrowid

    def get_leaderboard(self, mode: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtiene las mejores puntuaciones ordenadas por puntaje desc y tiempo asc."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if mode:
                cursor.execute("""
                    SELECT * FROM high_scores
                    WHERE mode = ?
                    ORDER BY score DESC, time_seconds ASC, turns ASC
                    LIMIT ?;
                """, (mode, limit))
            else:
                cursor.execute("""
                    SELECT * FROM high_scores
                    ORDER BY score DESC, time_seconds ASC, turns ASC
                    LIMIT ?;
                """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
