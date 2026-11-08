"""
Módulo de Control Gestual (Visión Artificial)
=============================================
Proyecto: TepuyMatch 🇻🇪

Detecta la mano del jugador mediante la cámara web usando MediaPipe,
traduce la posición del dedo índice a coordenadas de cursor y detecta
el gesto de "pellizco" (pulgar + índice juntos) como acción de clic.

También permite el uso del ratón como respaldo.
"""

import math
from typing import Optional, Tuple, Dict, Any
from enum import Enum

try:
    import cv2
    import mediapipe as mp
    import numpy as np
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False


class GestureType(Enum):
    """Tipos de gestos reconocidos."""
    NONE = "none"             # Sin gesto / mano abierta
    POINTING = "pointing"     # Dedo índice extendido (mover cursor)
    PINCH = "pinch"           # Pellizco pulgar-índice (clic / voltear carta)
    FIST = "fist"             # Puño cerrado (pausa)


class HandTracker:
    """
    Rastreador de mano y detector de gestos mediante webcam.

    Usa MediaPipe Hands para detectar 21 puntos clave (landmarks) de
    la mano y traducirlos en acciones de juego:
      - Posición del índice → Coordenadas del cursor
      - Distancia pulgar-índice < umbral → Gesto de clic (pellizco)
    """

    # Landmarks clave de MediaPipe Hands
    THUMB_TIP = 4
    INDEX_TIP = 8
    MIDDLE_TIP = 12
    RING_TIP = 16
    PINKY_TIP = 20
    INDEX_MCP = 5    # Nudillo del índice (metacarpiano)
    WRIST = 0

    # Umbral de distancia normalizada para detectar pellizco
    PINCH_THRESHOLD = 0.05
    # Número de frames consecutivos para confirmar un clic (anti-rebote)
    CLICK_CONFIRM_FRAMES = 3

    def __init__(
        self,
        camera_index: int = 0,
        screen_width: int = 1024,
        screen_height: int = 768,
        detection_confidence: float = 0.7,
        tracking_confidence: float = 0.6,
    ):
        self.camera_index = camera_index
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Estado del rastreador
        self.cursor_x: int = screen_width // 2
        self.cursor_y: int = screen_height // 2
        self.current_gesture: GestureType = GestureType.NONE
        self.pinch_counter: int = 0
        self.click_triggered: bool = False
        self.hand_detected: bool = False
        self.is_active: bool = False

        # Suavizado del cursor (filtro de media móvil)
        self._smooth_x: float = float(screen_width // 2)
        self._smooth_y: float = float(screen_height // 2)
        self._smoothing_factor: float = 0.35  # 0 = sin suavizado, 1 = máximo

        # Frame actual de la cámara (para la miniatura en la UI)
        self.current_frame: Optional[Any] = None
        self.debug_frame: Optional[Any] = None

        # MediaPipe y cámara
        self._cap = None
        self._hands = None
        self._mp_hands = None
        self._mp_drawing = None

        if VISION_AVAILABLE:
            self._mp_hands = mp.solutions.hands
            self._mp_drawing = mp.solutions.drawing_utils
            self._hands = self._mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=detection_confidence,
                min_tracking_confidence=tracking_confidence,
            )

    def start_camera(self) -> bool:
        """Inicia la captura de la cámara web. Retorna True si tuvo éxito."""
        if not VISION_AVAILABLE:
            print("[HandTracker] OpenCV/MediaPipe no disponible. Usando solo ratón.")
            return False

        try:
            self._cap = cv2.VideoCapture(self.camera_index)
            if not self._cap.isOpened():
                print(f"[HandTracker] No se pudo abrir la cámara {self.camera_index}.")
                return False
            self.is_active = True
            return True
        except Exception as e:
            print(f"[HandTracker] Error al iniciar cámara: {e}")
            return False

    def stop_camera(self) -> None:
        """Libera la cámara web."""
        self.is_active = False
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def update(self) -> Dict[str, Any]:
        """
        Lee un frame de la cámara, detecta la mano y actualiza:
        - cursor_x, cursor_y (posición del cursor virtual)
        - current_gesture (tipo de gesto)
        - click_triggered (True en el frame exacto donde se confirma un clic)

        Retorna un diccionario con todo el estado actual.
        """
        self.click_triggered = False

        if not self.is_active or self._cap is None:
            return self._get_state()

        ret, frame = self._cap.read()
        if not ret or frame is None:
            return self._get_state()

        # Espejo horizontal para que sea intuitivo
        frame = cv2.flip(frame, 1)
        frame_h, frame_w, _ = frame.shape

        # Convertir BGR → RGB para MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb_frame)

        self.hand_detected = False

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            self.hand_detected = True

            # Extraer posición del dedo índice (punta)
            index_tip = hand_landmarks.landmark[self.INDEX_TIP]
            thumb_tip = hand_landmarks.landmark[self.THUMB_TIP]

            # Mapear posición normalizada [0,1] → coordenadas de pantalla
            raw_x = index_tip.x * self.screen_width
            raw_y = index_tip.y * self.screen_height

            # Suavizar el movimiento del cursor
            self._smooth_x += (raw_x - self._smooth_x) * (1 - self._smoothing_factor)
            self._smooth_y += (raw_y - self._smooth_y) * (1 - self._smoothing_factor)
            self.cursor_x = int(max(0, min(self.screen_width - 1, self._smooth_x)))
            self.cursor_y = int(max(0, min(self.screen_height - 1, self._smooth_y)))

            # Calcular distancia pulgar-índice para detectar pellizco
            pinch_dist = math.sqrt(
                (thumb_tip.x - index_tip.x) ** 2 +
                (thumb_tip.y - index_tip.y) ** 2
            )

            if pinch_dist < self.PINCH_THRESHOLD:
                self.current_gesture = GestureType.PINCH
                self.pinch_counter += 1
                if self.pinch_counter == self.CLICK_CONFIRM_FRAMES:
                    self.click_triggered = True
            else:
                self.current_gesture = GestureType.POINTING
                self.pinch_counter = 0

            # Dibujar landmarks en el frame para debug/miniatura
            self._mp_drawing.draw_landmarks(
                frame, hand_landmarks, self._mp_hands.HAND_CONNECTIONS
            )

            # Dibujar indicador de pellizco
            cx_px = int(index_tip.x * frame_w)
            cy_px = int(index_tip.y * frame_h)
            color = (0, 255, 0) if self.current_gesture == GestureType.PINCH else (255, 255, 0)
            cv2.circle(frame, (cx_px, cy_px), 12, color, -1)

        else:
            self.current_gesture = GestureType.NONE
            self.pinch_counter = 0

        self.current_frame = frame
        self.debug_frame = frame.copy()

        return self._get_state()

    def get_camera_thumbnail(self, width: int = 200, height: int = 150) -> Optional[Any]:
        """
        Devuelve el frame actual de la cámara redimensionado para la miniatura
        en la esquina de la interfaz del juego.
        """
        if self.current_frame is None or not VISION_AVAILABLE:
            return None
        return cv2.resize(self.current_frame, (width, height))

    def _get_state(self) -> Dict[str, Any]:
        """Retorna el estado completo del rastreador."""
        return {
            "cursor_x": self.cursor_x,
            "cursor_y": self.cursor_y,
            "gesture": self.current_gesture.value,
            "click": self.click_triggered,
            "hand_detected": self.hand_detected,
            "is_active": self.is_active,
        }

    def __del__(self):
        """Limpieza al destruir el objeto."""
        self.stop_camera()
