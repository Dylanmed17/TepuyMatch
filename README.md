# TepuyMatch: Sistema Interactivo de Memoria Geográfica con Optimización Lineal (HiGHS) y Visión Artificial (MediaPipe IA)

> **Proyecto Integrador de Cátedra**  
> **Área:** Investigación de Operaciones & Inteligencia Artificial  
> **Plataforma:** Aplicación Web de Alta Disponibilidad & Edge Computing  
> **Despliegue Continuo (Producción):** [https://tepuymatch.onrender.com](https://tepuymatch.onrender.com)

---

## 1. Resumen Ejecutivo y Arquitectura del Sistema

**TepuyMatch** es un sistema lúdico-educativo centrado en la geografía y el patrimonio natural de Venezuela (Salto Ángel, Monte Roraima, Los Roques, Médanos de Coro, Relámpago del Catatumbo, entre otros). A diferencia de los juegos de memoria convencionales basados en barajado estocástico (`random.shuffle`), TepuyMatch integra **modelos formales de optimización matemática e inteligencia artificial**:

```
                                    ARQUITECTURA DEL SISTEMA
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              CLIENTE (Navegador / Móvil)                               │
│                                                                                        │
│  ┌────────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────────┐  │
│  │   Motor de Gestos      │  │   Motor de Geometría    │  │   Iconografía Vectorial │  │
│  │   MediaPipe Hands IA   │  │   resizeBoardGrid()     │  │   Lucide SVG (0 deps)   │  │
│  │   (Wasm/WebGL @ 30fps) │  │   (Aspect Ratio 3:4)    │  │   (Temas Claro/Oscuro)  │  │
│  └───────────┬────────────┘  └────────────┬────────────┘  └─────────────────────────┘  │
└──────────────┼────────────────────────────┼────────────────────────────────────────────┘
               │ HTTP / JSON                │ Auto-fit 100dvh
               ▼                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                             BACKEND (Python / Flask API)                               │
│                                                                                        │
│  ┌─────────────────────────────────────┐  ┌─────────────────────────────────────────┐  │
│  │   Investigación de Operaciones      │  │   Inteligencia Artificial (Canaibot)    │  │
│  │   Programación Lineal Binaria (PLB) │  │   POMDP + Memoria Atkinson-Shiffrin     │  │
│  │   Solver SciPy HiGHS (< 5 ms)       │  │   Retención: 30% / 70% / 100%           │  │
│  └──────────────────┬──────────────────┘  └─────────────────────────────────────────┘  │
│                     │                                                                  │
│                     ▼                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │   Capa de Persistencia: SQLite3 / WAL Mode (Récords y Catálogo Geográfico)       │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Investigación de Operaciones: Modelo de Programación Lineal Binaria (PLB)

### 2.1 Justificación Teórica
En un juego pedagógico, una selección meramente aleatoria puede generar tableros pedagógicamente deficientes: sobre-representación de una única región, acumulación de cartas visualmente triviales o imposibles, y desbalance cognitivo. 

Para garantizar rigor académico, la configuración de cada tablero se formula como un **Problema de Selección Óptima de Tablero (Optimal Board Selection Problem)** resuelto mediante Programación Lineal Entera Mixta / Binaria (MILP/PLB).

### 2.2 Formulación Matemática Formal

#### Conjuntos e Índices:
* $N = \{1, 2, \dots, n\}$: Conjunto de $n$ paisajes patrimoniales venezolanos disponibles en la base de datos ($n = 15$).
* $R = \{\text{Guayana}, \text{Andes}, \text{Costa e Insular}, \text{Llanos}, \text{Centro-Occidental}\}$: Conjunto de regiones geográficas.
* $R_j \subset N$: Subconjunto de paisajes pertenecientes a la región geográfica $j \in R$.

#### Parámetros:
* $c_i \in \mathbb{R}^+$: Coeficiente de representatividad cultural y valor patrimonial del paisaje $i$.
* $d_i \in \{1, 2, 3\}$: Nivel de dificultad mnemotécnica del paisaje $i$ (1: Fácil, 2: Medio, 3: Difícil).
* $k \in \mathbb{Z}^+$: Número exacto de parejas de cartas requeridas según la dimensión del tablero:
  $$k = \frac{\text{filas} \times \text{columnas}}{2} \quad (k \in \{6, 8, 10, 12\})$$
* $[D_{\min}, D_{\max}]$: Rango admisible de carga cognitiva acumulada según la dificultad seleccionada.
* $S \subseteq N$: Subconjunto de paisajes permitidos cuando el usuario filtra por estados específicos.

#### Variables de Decisión:
$$x_i \in \{0, 1\} \quad \forall i \in N$$
Donde $x_i = 1$ si el par de cartas del paisaje $i$ es incluido en el tablero, y $x_i = 0$ en caso contrario.

#### Función Objetivo:
$$\max Z = \sum_{i \in N} c_i \cdot x_i$$
*Maximizar el valor de representatividad cultural y pedagógica acumulada en el tablero.*

#### Restricciones del Sistema:
1. **Restricción de Cardinalidad Exacta:**
   $$\sum_{i \in N} x_i = k$$
   *Garantiza que el tablero contenga exactamente la cantidad de parejas necesarias para llenar la cuadrícula.*

2. **Restricción de Cota de Dificultad (Balance Cognitivo):**
   $$D_{\min} \le \sum_{i \in N} d_i \cdot x_i \le D_{\max}$$
   *Asegura que el tablero no sea ni trivialmente fácil ni frustrantemente complejo para el nivel seleccionado.*

3. **Restricción de Cobertura y Diversidad Regional:**
   $$\sum_{i \in R_j} x_i \ge 1 \quad \forall j \in R \quad (\text{si } |R| \le k)$$
   *Garantiza que ninguna región venezolana quede excluida de la partida.*

4. **Restricción de Filtro Geográfico Estricto:**
   $$x_i = 0 \quad \forall i \notin S \quad (\text{cuando } S \neq \emptyset)$$
   *Excluye cualquier paisaje que no pertenezca a los estados seleccionados por el usuario.*

5. **Naturaleza Binaria de las Variables:**
   $$x_i \in \{0, 1\} \quad \forall i \in N$$

### 2.3 Solver Utilizado y Tiempo de Resolución
* **Solver:** `SciPy MILP` (`scipy.optimize.milp`), el cual utiliza internamente el motor **HiGHS** (desarrollado en C++, empleando algoritmos Simplex Dual, Puntos Interiores y Branch-and-Cut).
* **Tiempo de Solución Típico:** **$\le 0.004$ segundos ($< 4$ ms)**.
* **Ubicación en el Código:** `src/optimization/board_optimizer.py` (Líneas 1–250) y llamada en `server.py` (Líneas 70–85).

---

## 3. Inteligencia Artificial: Agente Autónomo Canaibot

### 3.1 Fundamentación Teórica
El rival virtual **Canaibot** no realiza elecciones al azar ni "hace trampa" leyendo el estado interno del juego. Modela la cognición humana mediante un **Proceso de Decisión de Markov Parcialmente Observable (POMDP)** combinado con el **Modelo de Memoria Multialmacén de Atkinson-Shiffrin**:

1. **Estado de Creencias (Belief State $b_t$):**  
   Canaibot mantiene un diccionario de memoria que asocia cada posición del tablero con el identificador del paisaje observado durante turnos propios o del jugador humano.
2. **Tasa de Retención Estocástica ($\rho$):**  
   Al observar una carta en la posición $p$, el agente la retiene en su memoria de trabajo con probabilidad $\rho \in (0, 1]$:
   * **Novato (Fácil):** $\rho = 0.30$ (Olvido frecuente del 70%, simula memoria de corto plazo débil).
   * **Guía (Medio):** $\rho = 0.70$ (Retención moderada y realista).
   * **Experto (Difícil):** $\rho = 1.00$ (Memoria fotográfica perfecta; si una carta fue revelada, nunca la olvida).
3. **Función de Política de Decisión ($\pi(b_t)$):**
   * **Explotación Inmediata (Greedy):** Si el agente recuerda la ubicación de 2 cartas del mismo paisaje, las voltea consecutivamente garantizando el punto con certeza $P = 1$.
   * **Exploración Informativa:** Si no hay pareja conocida, selecciona una carta no volteada $p_1$. Al revelarse, consulta si conoce la pareja de dicho paisaje. Si la recuerda, ejecuta la explotación en el segundo clic; de lo contrario, explora una segunda carta no descubierta.
* **Ubicación en el Código:** `src/game/ai_player.py` (Líneas 1–199).

---

## 4. Visión por Computador e Interacción Gestual (MediaPipe Hands IA)

### 4.1 Arquitectura de Visión Artificial (Edge AI)
El sistema implementa control gestual mediante **Google MediaPipe Hands**:
* **Detección de Palma:** Modelo convolucional en una sola etapa (*BlazePalm Single-Shot Detector*) optimizado para visión móvil.
* **Malla de 21 Puntos Tridimensionales (3D Hand Landmarks):** Red neuronal de regresión directa que predice coordenadas relativas $(x, y, z)$ de cada articulación de la mano.
* **Ejecución Local (Edge Computing):** Corre directamente en el cliente en WebAssembly y WebGL a **30 FPS estables**, eliminando consumo de ancho de banda y latencia de red (latencia de inferencia $< 25$ ms).

### 4.2 Lógica Matemática de los Gestos Implementados

| Gesto | Formulación Matemática / Criterio de Activación | Acción en el Juego |
|---|---|---|
| **Apunta (Puntero Neón)** | Coordenadas normalizadas del extremo del dedo índice: Landmark #8 $(x_8, y_8)$, filtradas con suavizado exponencial Lerp: $C_t = C_{t-1} + \alpha (T_t - C_{t-1})$ con $\alpha = 0.32$. | Desplaza el cursor virtual con anclaje magnético a la carta más cercana. |
| **Pellizco (Pinch Click)** | Distancia euclidiana normalizada entre pulgar (#4) e índice (#8): $d = \sqrt{(x_4 - x_8)^2 + (y_4 - y_8)^2} < 0.08$. Al detectarse, activa un candado espacial que **congela el cursor** en la carta objetivo para evitar saltos. | Voltea la carta seleccionada. |
| **Swipe Lateral (Deslizamiento)** | Velocidad horizontal instantánea: $v_x = \frac{x_t - x_{t-\Delta t}}{\Delta t} > 0.38 \text{ s}^{-1}$ con desplazamiento total $|\Delta x| > 0.08$. Incluye **bloqueo de desaceleración de 850 ms** (`swipeLockoutUntil`). | Navega espacialmente entre cartas contiguas (izquierda/derecha). |
| **Swipe Vertical** | Velocidad vertical $v_y > 0.40 \text{ s}^{-1}$ con $|\Delta y| > 0.10$. | Swipe hacia abajo: Pausa y abre menú. Swipe hacia arriba: Reanuda la partida. |
| **Palma Abierta** | Extensión de los 4 dedos respecto a sus nudillos: $y_{\text{tip}} < y_{\text{pip}}$ sostenida por $> 0.35$ s. | Alterna pausa / reanudación del juego. |

* **Ubicación en el Código:** `web/index.html` (Líneas 2100–2650: clase `MediaPipeGestureController`).

---

## 5. Diseño de Interfaz y Geometría Adaptativa (`resizeBoardGrid`)

### 5.1 Eliminación de Emojis y Pack Vectorial SVG Profesional
Para evitar la estética genérica ("look IA") y garantizar alta fidelidad gráfica:
* Se eliminaron **todos los emojis** del HTML y JavaScript dinámico.
* Se implementó un repositorio integrado de **38 símbolos vectoriales SVG** basados en la especificación **Lucide Icons** embebidos directamente en `<svg><defs><symbol>...`.
* **Ventajas:** Cero dependencias externas (sin fuentes de terceros ni CDNs lentos), rendering a 0 ms, soporte de color heredado (`currentColor`) y alto contraste en modo claro y oscuro.

### 5.2 Motor de Auto-Ajuste de Cuadrícula (Cero Scroll y Cero Desborde)
En dispositivos móviles con safe-area insets y barra de navegación dinámica:
* La función `resizeBoardGrid()` calcula analíticamente las dimensiones exactas $(W, H)$ de cada carta respetando el aspect ratio áureo de $3:4$:
  $$W_{\text{carta}} = \min\left(\frac{W_{\text{disponible}}}{C}, \frac{H_{\text{disponible}}}{R} \times \frac{3}{4}\right)$$
* Se incorporaron márgenes de guarda simétricos ($26$ px en vertical) y respeto de `env(safe-area-inset-bottom)`, garantizando que la fila superior nunca colisione con el HUD y la fila 6 inferior nunca sufra cortes en Safari o Chrome.
* **Ubicación en el Código:** `web/index.html` (Líneas 3460–3515).

---

## 6. Banco de Preguntas y Respuestas para Defensa Oral (Cheat Sheet)

Guía rápida de respuestas preparadas para las preguntas habituales del profesor:

### P1: "¿Dónde está la Inteligencia Artificial en el código?"
* **Respuesta:**
  1. **En el Rival (Canaibot):** En `src/game/ai_player.py`. Es un agente basado en POMDP y el modelo de memoria de Atkinson-Shiffrin (Líneas 48–110), con retención probabilística de 30%, 70% y 100% y una función de política greedy/exploratoria.
  2. **En la Visión Artificial:** En `web/index.html` (Líneas 2100–2650). Utiliza los modelos de aprendizaje profundo **BlazePalm** y **Hand Landmark 3D** de Google MediaPipe ejecutados en WebAssembly/WebGL en el cliente.

### P2: "¿Dónde está la Investigación de Operaciones y qué modelo matemático formularon?"
* **Respuesta:**
  * En `src/optimization/board_optimizer.py` (Líneas 1–250) y expuesto vía API en `server.py` (Líneas 58–80).
  * Es un modelo de **Programación Lineal Binaria (PLB / 0-1)** que maximiza el valor cultural del tablero ($\max Z = \sum c_i x_i$) sujeto a restricción de cardinalidad ($\sum x_i = k$), límites de dificultad por entropía ($D_{\min} \le \sum d_i x_i \le D_{\max}$), cobertura regional obligatoria ($\sum_{i \in R_j} x_i \ge 1$) y filtros de exclusión.

### P3: "¿Por qué no barajaron las cartas con un simple `random.shuffle`?"
* **Respuesta:**
  * Porque el azar no garantiza balance pedagógico ni diversidad geográfica. Puede generar partidas con 5 cartas del mismo estado o todas de dificultad extrema. El modelo de PLB garantiza matemáticamente la representatividad óptima de Venezuela y la dificultad justa en menos de 5 milisegundos.

### P4: "¿Qué framework usaron y por qué?"
* **Respuesta:**
  * **Backend:** Python con **Flask** por su ligereza y facilidad para exponer la API REST conectada directamente al solver SciPy HiGHS y SQLite.
  * **Frontend:** **HTML5 / CSS3 / JavaScript ES6+ nativo** con **Iconos Vectoriales SVG embebidos**. Se evitó React o Vue para garantizar carga instantánea, 0 ms de compilación, 0 dependencias pesadas en el cliente y compatibilidad directa con WebGL/MediaPipe.
  * **Solver:** **SciPy MILP** con el motor **HiGHS** en C++ (el solver de código abierto más rápido del mundo para MILP).

### P5: "¿Cuánto tarda en compilar y ejecutarse?"
* **Respuesta:**
  * **Compilación:** 0 segundos en el cliente (código interpretado nativo).
  * **Optimización de Investigación de Operaciones (PLB):** Menos de **0.005 segundos (< 5 ms)** por partida calculada con HiGHS.
  * **Inferencia de Visión Artificial:** **20 a 30 ms por cuadro (30 FPS continuos)** procesados localmente en la GPU del usuario.

### P6: "¿Cómo se calculan el pellizco y los gestos laterales?"
* **Respuesta:**
  * El **pellizco** calcula la distancia euclidiana entre el Landmark #4 (punta del pulgar) y el Landmark #8 (punta del índice). Si la distancia es menor a 0.08 en espacio normalizado, se activa el clic y se congela el cursor en la carta actual.
  * El **deslizamiento (swipe)** mide la velocidad diferencial $\Delta x / \Delta t$. Si supera 0.38 s⁻¹, navega a la carta vecina y activa un tiempo de enfriamiento (`swipeLockoutUntil`) de 850 ms para que el frenado de la mano no desplace accidentalmente el cursor.

---

## 7. Estructura del Repositorio

```text
memoria-venezuela-io/
├── assets/
│   └── images/              # Fotografías de paisajes y reverso oficial (7 estrellas)
├── data/
│   ├── landscapes.json      # Catálogo patrimonial (dificultad, región, estado, valor)
│   └── tepuy_match.db       # Base de datos SQLite3 (WAL mode) para el Salón de la Fama
├── docs/
│   └── MODELO_MATEMATICO.md # Demostración y formulación matemática extendida
├── src/
│   ├── data/
│   │   └── db_manager.py    # Persistencia y ranking
│   ├── game/
│   │   ├── ai_player.py     # Agente Canaibot (POMDP + Atkinson-Shiffrin)
│   │   └── memory_game.py   # Reglas formales del juego y transiciones de estado
│   ├── optimization/
│   │   └── board_optimizer.py # Modelo PLB con SciPy MILP (Solver HiGHS)
│   └── vision/
│       └── hand_tracker.py  # Módulo OpenCV/MediaPipe para entorno de escritorio local
├── tests/
│   └── test_game_simulation.py # Pruebas unitarias de concurrencia y turnos
├── web/
│   └── index.html           # SPA responsiva, MediaPipe WebAssembly y Lucide SVG
├── Procfile                 # Despliegue en Render (Gunicorn)
├── server.py                # Servidor Flask de producción y endpoints REST
└── requirements.txt         # Dependencias Python (Flask, scipy, numpy, gunicorn)
```

---

## 8. Instrucciones de Instalación y Ejecución Local

### Prerrequisitos:
* Python 3.10 o superior instalado.
* Cámara web (opcional para control gestual, el juego cuenta con control táctil/ratón 100% funcional).

### Paso a paso:
1. Clonar el repositorio:
   ```bash
   git clone https://github.com/Dylanmed17/TepuyMatch.git
   cd TepuyMatch
   ```
2. Crear y activar entorno virtual:
   ```bash
   python -m venv venv
   # En Windows:
   venv\Scripts\activate
   # En Linux/macOS:
   source venv/bin/activate
   ```
3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Ejecutar el servidor:
   ```bash
   python server.py
   ```
5. Abrir en el navegador:
   ```
   http://localhost:5000
   ```
