# Modelo de Programación Lineal: Generación Óptima de Tablero de Memoria

**Asignatura:** Investigación de Operaciones  
**Proyecto:** Juego de Memoria de Paisajes de Venezuela con Control Gestual

---

## 1. Definición del Problema

El juego de memoria tradicional requiere un tablero de $K$ parejas de cartas (un total de $2K$ cartas dispuestas en una cuadrícula). Tradicionalmente, las cartas se escogen mediante un muestreo aleatorio uniforme. 

En este proyecto, se reemplaza la selección aleatoria por un **Modelo de Programación Lineal Entera / Binaria (PLB)**, el cual selecciona el subconjunto óptimo de paisajes de Venezuela pertenecientes a un catálogo predefinido $C$, maximizando el valor cultural y de representatividad turística, sujeto a restricciones pedagógicas, de carga cognitiva y de diversidad geográfica.

---

## 2. Formulación Matemática

### 2.1. Conjuntos e Índices
* $I = \{1, 2, \dots, N\}$: Conjunto de paisajes venezolanos disponibles en el catálogo.
* $R$: Conjunto de regiones geográficas de Venezuela (Guayana, Andina, Costera/Insular, Central, Llanos, Zuliana, Occidente).
* $I_r \subseteq I$: Subconjunto de paisajes que pertenecen a la región $r \in R$.

### 2.2. Parámetros
* $K \in \mathbb{Z}^+$: Número exacto de parejas de cartas requeridas por el nivel de juego (ej. $K = 6$ para $3 \times 4$, $K = 8$ para $4 \times 4$, $K = 12$ para $4 \times 6$).
* $v_i \in \mathbb{R}^+$: Valor cultural / turístico asignado al paisaje $i \in I$ (escala 1 a 10).
* $d_i \in \mathbb{Z}^+$: Nivel de dificultad / carga de memorización del paisaje $i$ (escala 1 a 3).
* $D_{\min}, D_{\max} \in \mathbb{R}^+$: Límites inferior y superior para la dificultad cognitiva acumulada del tablero, según el nivel seleccionado (Fácil, Medio, Difícil).

### 2.3. Variables de Decisión
$$x_i \in \{0, 1\} \quad \forall i \in I$$

Donde:
$$x_i = \begin{cases} 
1 & \text{si el paisaje } i \text{ es seleccionado para formar una pareja en el tablero} \\
0 & \text{en caso contrario}
\end{cases}$$

---

## 3. Función Objetivo

Se desea maximizar el valor cultural y turístico total del tablero generado:

$$\max Z = \sum_{i \in I} v_i \cdot x_i$$

---

## 4. Restricciones del Modelo

### 4.1. Restricción de Dimensión del Tablero
El número total de parejas seleccionadas debe ser exactamente igual a $K$:
$$\sum_{i \in I} x_i = K$$

### 4.2. Restricciones de Carga Cognitiva (Dificultad)
La suma de las dificultades de los paisajes seleccionados debe mantenerse dentro del rango pedagógico previsto para la partida:
$$\sum_{i \in I} d_i \cdot x_i \le D_{\max}$$
$$\sum_{i \in I} d_i \cdot x_i \ge D_{\min}$$

### 4.3. Restricción de Diversidad Regional (Cuota Mínima)
Para garantizar representatividad y evitar que un solo estado o región monopolice el tablero, cada región disponible $r \in R$ debe tener al menos un representante (siempre que el número de regiones $|R| \le K$):
$$\sum_{i \in I_r} x_i \ge 1 \quad \forall r \in R$$

### 4.4. Naturaleza de las Variables
$$x_i \in \{0, 1\} \quad \forall i \in I$$

---

## 5. Algoritmo de Solución y Solvers

El problema corresponde formalmente al **Problema de la Mochila con Restricciones Múltiples (Multidimensional Knapsack Problem)** con variables binarias. 

Se resuelve mediante el solver de código abierto **CBC (Coin-or branch and cut)** a través de la interfaz de modelado `PuLP` en Python. El tiempo de resolución típico es menor a $0.05$ segundos, garantizando una experiencia de juego instantánea y matemáticamente rigurosa.
