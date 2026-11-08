"""
Módulo de Optimización Matemática (Investigación de Operaciones)
===============================================================
Problema: Selección Óptima de Tablero de Juego (Optimal Board Generation)
Tipo de Modelo: Programación Lineal Entera / Binaria (PLB)

Este módulo formula y resuelve el modelo de optimización para seleccionar
el conjunto ideal de parejas de cartas para el juego de memoria de paisajes
de Venezuela, garantizando diversidad regional, ajuste de dificultad y
cumplimiento de restricciones de tamaño de tablero.
"""

from typing import List, Dict, Any, Optional
import time

try:
    import pulp
    PULP_AVAILABLE = True
except ImportError:
    PULP_AVAILABLE = False


class BoardOptimizer:
    """
    Formulador y solucionador del modelo de Programación Lineal
    para la generación óptima del tablero.
    """

    def __init__(self, landscapes: List[Dict[str, Any]]):
        self.landscapes = landscapes

    def optimize_board(
        self,
        num_pairs: int = 8,
        selected_states: Optional[List[str]] = None,
        difficulty_level: str = "Medio",
        force_regional_diversity: bool = True
    ) -> Dict[str, Any]:
        """
        Resuelve el modelo de optimización binaria.

        Parámetros:
        -----------
        num_pairs: int
            Número exacto de parejas a seleccionar (ej. 6, 8 o 12).
        selected_states: Optional[List[str]]
            Si se especifica, solo se consideran paisajes de estos estados.
        difficulty_level: str
            "Fácil", "Medio" o "Difícil" (ajusta las cotas de dificultad total).
        force_regional_diversity: bool
            Si es True, fuerza a que al menos cada región disponible esté representada.

        Retorna:
        --------
        Dict con los paisajes seleccionados, métricas del modelo (Z*, estado, tiempo).
        """
        start_time = time.time()

        # Filtrar candidatos si el usuario seleccionó estados específicos
        candidates = self.landscapes
        if selected_states and len(selected_states) > 0:
            filtered = [c for c in self.landscapes if c["state"] in selected_states]
            if len(filtered) >= num_pairs:
                candidates = filtered

        # Si no hay suficientes candidatos para el tamaño del tablero, ajustar num_pairs
        k = min(num_pairs, len(candidates))

        # Parámetros de dificultad acumulada
        difficulty_bounds = {
            "Fácil": (k * 1.0, k * 1.3),
            "Medio": (k * 1.2, k * 1.7),
            "Difícil": (k * 1.5, k * 2.0),
        }
        min_diff, max_diff = difficulty_bounds.get(difficulty_level, (k * 1.0, k * 2.0))

        if not PULP_AVAILABLE:
            # Fallback heurístico en caso de que PuLP aún no esté instalado en el entorno
            return self._heuristic_fallback(candidates, k, start_time)

        # -------------------------------------------------------------
        # FORMULACIÓN MATEMÁTICA EN PuLP (Programación Lineal Binaria)
        # -------------------------------------------------------------
        # 1. Definición del problema: Maximización
        prob = pulp.LpProblem("Seleccion_Optima_Tablero_Venezuela", pulp.LpMaximize)

        # 2. Variables de decisión binarias: x_i in {0, 1}
        # x[i] = 1 si el paisaje i es seleccionado para el tablero, 0 si no.
        x = {
            c["id"]: pulp.LpVariable(f"x_{c['id']}", cat=pulp.LpBinary)
            for c in candidates
        }

        # 3. Función Objetivo: Maximizar el valor cultural/turístico total
        # Max Z = sum(cultural_value_i * x_i)
        prob += pulp.lpSum([c["cultural_value"] * x[c["id"]] for c in candidates]), "Valor_Cultural_Total"

        # 4. Restricción 1: Tamaño exacto del tablero (K parejas)
        # sum(x_i) = K
        prob += (
            pulp.lpSum([x[c["id"]] for c in candidates]) == k,
            f"Tamano_Tablero_Exacto_{k}"
        )

        # 5. Restricción 2: Rango de dificultad cognitiva acumulada
        # sum(difficulty_i * x_i) <= max_diff
        # sum(difficulty_i * x_i) >= min_diff
        prob += (
            pulp.lpSum([c["difficulty"] * x[c["id"]] for c in candidates]) <= max_diff,
            "Cota_Superior_Dificultad"
        )
        prob += (
            pulp.lpSum([c["difficulty"] * x[c["id"]] for c in candidates]) >= min_diff,
            "Cota_Inferior_Dificultad"
        )

        # 6. Restricción 3: Diversidad regional (si aplica)
        # Para cada región geográfica disponible, al menos 1 paisaje si es factible
        if force_regional_diversity:
            regions = {}
            for c in candidates:
                regions.setdefault(c["region"], []).append(c["id"])

            if len(regions) <= k:
                for region_name, ids in regions.items():
                    prob += (
                        pulp.lpSum([x[i] for i in ids]) >= 1,
                        f"Cuota_Minima_Region_{region_name.replace('/', '_').replace(' ', '_')}"
                    )

        # 7. Resolución con el solver integrado (CBC / COIN-OR)
        solver = pulp.PULP_CBC_CMD(msg=False)
        status_code = prob.solve(solver)
        solve_duration = time.time() - start_time

        status_str = pulp.LpStatus[status_code]

        # Si el modelo fue infactible con las restricciones estrictas, resolver relajando cotas
        if status_str != "Optimal":
            # Resolver solo con restricción de tamaño y función objetivo
            prob_relaxed = pulp.LpProblem("Seleccion_Relajada", pulp.LpMaximize)
            prob_relaxed += pulp.lpSum([c["cultural_value"] * x[c["id"]] for c in candidates])
            prob_relaxed += pulp.lpSum([x[c["id"]] for c in candidates]) == k
            prob_relaxed.solve(solver)
            status_str = f"Relaxed_{pulp.LpStatus[prob_relaxed.status]}"

        # Extraer solución óptima
        selected_ids = {
            c_id for c_id, var in x.items() if var.varValue and var.varValue > 0.5
        }
        selected_landscapes = [c for c in candidates if c["id"] in selected_ids]

        # Resumen del reporte académico para el profesor
        objective_val = pulp.value(prob.objective) if status_str == "Optimal" else sum(c["cultural_value"] for c in selected_landscapes)
        total_difficulty = sum(c["difficulty"] for c in selected_landscapes)

        return {
            "selected_landscapes": selected_landscapes,
            "metadata": {
                "solver": "PuLP / CBC",
                "status": status_str,
                "objective_value": objective_val,
                "total_pairs": len(selected_landscapes),
                "total_cards": len(selected_landscapes) * 2,
                "total_difficulty": total_difficulty,
                "difficulty_bounds": (min_diff, max_diff),
                "solve_time_seconds": round(solve_duration, 4),
                "variables_count": len(candidates),
                "constraints_count": len(prob.constraints)
            }
        }

    def _heuristic_fallback(
        self, candidates: List[Dict[str, Any]], k: int, start_time: float
    ) -> Dict[str, Any]:
        """Heurística voraz de respaldo en caso de no tener solver instalado."""
        sorted_candidates = sorted(
            candidates, key=lambda c: c.get("cultural_value", 0), reverse=True
        )
        selected = sorted_candidates[:k]
        return {
            "selected_landscapes": selected,
            "metadata": {
                "solver": "Heurística Voraz (Greedy Fallback)",
                "status": "Heuristic_Approximation",
                "objective_value": sum(c.get("cultural_value", 0) for c in selected),
                "total_pairs": len(selected),
                "total_cards": len(selected) * 2,
                "total_difficulty": sum(c.get("difficulty", 0) for c in selected),
                "solve_time_seconds": round(time.time() - start_time, 4),
                "variables_count": len(candidates),
                "constraints_count": 0
            }
        }
