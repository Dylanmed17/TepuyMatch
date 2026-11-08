"""
TepuyMatch 🇻🇪 — Punto de Entrada Principal
=============================================
Juego de Memoria de Paisajes de Venezuela
con Control Gestual y Programación Lineal.

Proyecto de Investigación de Operaciones.
"""

from src.ui.game_screen import GameScreen


def main():
    print("=" * 50)
    print("  ⛰️  TepuyMatch — Paisajes de Venezuela 🇻🇪")
    print("  Investigación de Operaciones")
    print("=" * 50)

    game = GameScreen()
    game.run()


if __name__ == "__main__":
    main()
