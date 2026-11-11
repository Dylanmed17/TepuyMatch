"""
Módulo de Optimización Matemática (Investigación de Operaciones)
===============================================================
Problema: Selección Óptima de Tablero de Juego (Optimal Board Selection Problem)
Tipo de Modelo: Programación Lineal Entera Mixta / Binaria (MILP / PLB)
Solver: SciPy MILP (Solver HiGHS - Simplex & Branch and Bound de Alto Rendimiento)

FORMULACIÓN MATEMÁTICA FORMAL:
------------------------------
Sea N = {1, 2, ..., n} el conjunto de paisajes candidatos disponibles.
Variables de Decisión:
    x_i in {0, 1} para todo i in N  (1 si el paisaje i es seleccionado para el tablero, 0 en caso contrario)

Parámetros:
    c_i : Valor de representatividad cultural y patrimonial del paisaje i
    d_i : Índice de dificultad visual / mnemotécnica del paisaje i
    k   : Número exacto de parejas requerido por las dimensiones del tablero (k = (filas * columnas) / 2)
    [D_min, D_max] : Rango de dificultad total admisible para el nivel elegido (Fácil, Medio, Experto)
    R_j : Subconjunto de paisajes pertenecientes a la región geográfica j in R

Función Objetivo:
    Maximizar Z = SUM_{i=1}^n (c_i * x_i)   [Maximizar el valor cultural y pedagógico global]

Sujeto a:
    1. Restricción de Cardinalidad Exacta de Parejas:
       SUM_{i=1}^n x_i = k

    2. Restricción de Cota de Dificultad Acumulada:
       D_min <= SUM_{i=1}^n (d_i * x_i) <= D_max

    3. Restricción de Cobertura y Diversidad Regional:
       SUM_{i in R_j} x_i >= 1   para cada región j in R (si |R| <= k)

    4. Naturaleza de las Variables:
       x_i in {0, 1}   para todo i in N

Tiempo de resolución típico con SciPy HiGHS: < 0.005 segundos (< 5 ms).
"""

from typing import List, Dict, Any, Optional
import time
import numpy as np

try:
    from scipy.optimize import milp, LinearConstraint, Bounds
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class BoardOptimizer:
    """
    Formulador y solucionador del modelo de Programación Lineal Entera
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
        n = len(candidates)

        # Parámetros de dificultad acumulada
        difficulty_bounds = {
            "Facil": (k * 1.0, k * 1.4),
            "Fácil": (k * 1.0, k * 1.4),
            "Medio": (k * 1.2, k * 1.8),
            "Dificil": (k * 1.5, k * 2.2),
            "Difícil": (k * 1.5, k * 2.2),
            "Experto": (k * 1.5, k * 2.2),
        }
        min_diff, max_diff = difficulty_bounds.get(difficulty_level, (k * 1.0, k * 2.0))

        if SCIPY_AVAILABLE and n >= k:
            try:
                return self._solve_with_scipy(
                    candidates=candidates,
                    k=k,
                    min_diff=min_diff,
                    max_diff=max_diff,
                    force_regional_diversity=force_regional_diversity,
                    start_time=start_time
                )
            except Exception as e:
                print(f"[BoardOptimizer] Fallback de optimización por excepción: {e}")

        # Fallback voraz si SciPy no pudiera resolver
        return self._heuristic_fallback(candidates, k, start_time, min_diff, max_diff)

    def _solve_with_scipy(
        self,
        candidates: List[Dict[str, Any]],
        k: int,
        min_diff: float,
        max_diff: float,
        force_regional_diversity: bool,
        start_time: float
    ) -> Dict[str, Any]:
        """Resuelve el problema usando SciPy MILP con el solver HiGHS."""
        n = len(candidates)

        # Función objetivo: Maximizar suma(cultural_value_i * x_i)
        # SciPy minimiza c^T x, por lo que usamos c = -valores
        c = -np.array([float(cand["cultural_value"]) for cand in candidates], dtype=np.float64)

        # Variables binarias: x_i in {0, 1}
        integrality = np.ones(n, dtype=np.int32)
        bounds = Bounds(0.0, 1.0)

        # Construir matriz de restricciones A @ x
        A_rows = []
        lhs = []
        rhs = []

        # Restricción 1: Suma(x_i) == k (Exactamente k parejas)
        A_rows.append(np.ones(n, dtype=np.float64))
        lhs.append(float(k))
        rhs.append(float(k))

        # Restricción 2: Cota superior de dificultad sum(d_i * x_i) <= max_diff
        diff_coeffs = np.array([float(cand["difficulty"]) for cand in candidates], dtype=np.float64)
        A_rows.append(diff_coeffs)
        lhs.append(float(min_diff))
        rhs.append(float(max_diff))

        # Restricción 3: Diversidad regional (al menos 1 por región si es factible)
        if force_regional_diversity:
            regions = {}
            for idx, cand in enumerate(candidates):
                regions.setdefault(cand["region"], []).append(idx)

            if len(regions) <= k:
                for reg_name, indices in regions.items():
                    reg_row = np.zeros(n, dtype=np.float64)
                    for idx in indices:
                        reg_row[idx] = 1.0
                    A_rows.append(reg_row)
                    lhs.append(1.0)
                    rhs.append(float(len(indices)))

        A = np.array(A_rows, dtype=np.float64)
        constraints = LinearConstraint(A, lhs, rhs)

        # Ejecutar solver
        res = milp(c=c, integrality=integrality, bounds=bounds, constraints=constraints)

        # Si no fue factible con restricciones estrictas de región/dificultad, relajar
        if not res.success:
            # Solo mantener restricción de tamaño exacto == k
            A_relaxed = np.array([np.ones(n, dtype=np.float64)])
            constraints_relaxed = LinearConstraint(A_relaxed, [float(k)], [float(k)])
            res = milp(c=c, integrality=integrality, bounds=bounds, constraints=constraints_relaxed)

        duration = time.time() - start_time

        # Extraer variables seleccionadas (x_i > 0.5)
        selected = []
        if res.success and res.x is not None:
            for idx, val in enumerate(res.x):
                if val > 0.5:
                    selected.append(candidates[idx])

        # Si aún faltan elementos por alguna razón numérica, completar con los mejores
        if len(selected) < k:
            remaining = [c for c in candidates if c not in selected]
            remaining.sort(key=lambda item: item["cultural_value"], reverse=True)
            selected.extend(remaining[: (k - len(selected))])

        z_val = sum(item["cultural_value"] for item in selected)
        tot_diff = sum(item["difficulty"] for item in selected)

        return {
            "selected_landscapes": selected,
            "metadata": {
                "solver": "SciPy MILP (HiGHS Optimizer)",
                "status": "Optimal" if res.success else "Relaxed_Feasible",
                "objective_value": round(float(z_val), 2),
                "total_pairs": len(selected),
                "total_cards": len(selected) * 2,
                "total_difficulty": tot_diff,
                "difficulty_bounds": (min_diff, max_diff),
                "solve_time_seconds": round(duration, 4),
                "variables_count": n,
                "constraints_count": len(A_rows)
            }
        }

    def _heuristic_fallback(
        self,
        candidates: List[Dict[str, Any]],
        k: int,
        start_time: float,
        min_diff: float,
        max_diff: float
    ) -> Dict[str, Any]:
        """Aproximación por programación voraz."""
        sorted_candidates = sorted(
            candidates, key=lambda c: c.get("cultural_value", 0), reverse=True
        )
        selected = sorted_candidates[:k]
        return {
            "selected_landscapes": selected,
            "metadata": {
                "solver": "Heurística Voraz de Selección",
                "status": "Greedy_Approximation",
                "objective_value": sum(c.get("cultural_value", 0) for c in selected),
                "total_pairs": len(selected),
                "total_cards": len(selected) * 2,
                "total_difficulty": sum(c.get("difficulty", 0) for c in selected),
                "difficulty_bounds": (min_diff, max_diff),
                "solve_time_seconds": round(time.time() - start_time, 4),
                "variables_count": len(candidates),
                "constraints_count": 0
            }
        }
