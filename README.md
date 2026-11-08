# 🇻🇪 Memoria Venezuela: Juego de Memoria con Control Gestual y Programación Lineal

Proyecto integrador para la asignatura de **Investigación de Operaciones**, combinando visión artificial, diseño de interfaces interactivas y modelos matemáticos de optimización lineal.

---

## 📌 1. Visión General del Proyecto

El proyecto consiste en un juego de memoria centrado en los paisajes más emblemáticos de Venezuela (Roraima, Salto Ángel, Los Roques, Médanos de Coro, Pico Bolívar, Relámpago del Catatumbo, entre otros).

El proyecto integra tres componentes clave:
1. **Investigación de Operaciones (Programación Lineal)**: Generación óptima de tableros y partidas balanceando diversidad geográfica, dificultad y restricciones de tiempo mediante programación lineal entera/binaria.
2. **Control por Gesticulación (Visión por Computador)**: Interacción libre de periféricos tradicionales usando la cámara web (MediaPipe + OpenCV) para mover el cursor y voltear cartas con gestos naturales de la mano.
3. **Interfaz Gráfica (GUI Temática)**: Selector de paisajes por estados/regiones, visualización del tablero, cronómetro, puntuación y tabla de récords persistente.

---

## 📐 2. Modelo de Programación Lineal (Investigación de Operaciones)

A diferencia de un juego convencional donde las cartas se barajan al azar, este proyecto resuelve el **Problema de Selección Óptima de Tablero (Optimal Board Generation Problem)**:

* **Variables de Decisión**:
  $$x_i \in \{0, 1\} \quad \forall i \in \{1, \dots, N\}$$
  Indica si el par de cartas del paisaje $i$ es seleccionado para la partida.

* **Función Objetivo**:
  Maximizar el valor de representatividad cultural, diversidad regional y ajuste al nivel de desafío del jugador.

* **Restricciones Principales**:
  * Tamaño exacto del tablero ($K$ pares de cartas).
  * Cuotas mínimas y máximas por región geográfica (Andes, Guayana, Costa/Insular, Llanos, Centro-Occidente).
  * Límite de carga cognitiva / Dificultad acumulada.
  * Restricciones lógicas de exclusión mutua o complementariedad entre paisajes.

---

## 📁 3. Estructura del Proyecto

```text
memoria-venezuela-io/
│
├── assets/                  # Recursos gráficos y multimedia
│   └── images/              # Fotografías de paisajes organizadas por estado
│
├── data/                    # Datos estructurados
│   └── landscapes.json      # Catálogo de paisajes, estados, dificultad y regiones
│
├── docs/                    # Documentación académica y justificación del modelo de PL
│
├── src/                     # Código fuente modular
│   ├── game/                # Lógica del juego de memoria y reglas
│   ├── optimization/        # Modelo matemático y solver de Programación Lineal
│   ├── ui/                  # Interfaz gráfica de usuario y menús
│   └── vision/              # Detección de manos y gestos (OpenCV + MediaPipe)
│
├── .gitignore
├── README.md
└── requirements.txt
```

---

## 🚀 4. Requisitos y Configuración

* Python 3.10+
* Git
* Dependencias principales:
  * `opencv-python`
  * `mediapipe`
  * `pulp`
  * `numpy`
