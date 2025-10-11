"""
Obsługa gamepadów
Nasłuchuje i przetwarza input z kontrolerów gier.
"""

import logging
import threading
from typing import Optional, Callable, Dict, Any
from queue import Queue, Empty

try:
    from inputs import get_gamepad, UnpluggedError
    GAMEPAD_AVAILABLE = True
except ImportError:
    GAMEPAD_AVAILABLE = False
    logger.warning("Biblioteka 'inputs' nie jest dostępna - obsługa gamepad wyłączona")

from config.constants import (
    GAMEPAD_BTN_A, GAMEPAD_BTN_B, GAMEPAD_BTN_X, GAMEPAD_BTN_Y,
    GAMEPAD_BTN_START, GAMEPAD_BTN_SELECT, GAMEPAD_BTN_LB, GAMEPAD_BTN_RB,
    GAMEPAD_DEADZONE
)

logger = logging.getLogger(__name__)


class GamepadHandler:
    """
    Klasa obsługująca gamepad/kontroler.
    Nasłuchuje eventów z gamepada i wywołuje odpowiednie callbacki.
    """
    
    def __init__(self, launcher_instance=None):
        """
        Inicjalizuje handler gamepada.
        
        Args:
            launcher_instance: Referencja do głównej instancji launchera
        """
        self.launcher = launcher_instance
        self.enabled: bool = False
        self.running: bool = False
        self.thread: Optional[threading.Thread] = None
        self.event_queue: Queue = Queue()
        
        # Deadzone dla analogów
        self.deadzone: float = GAMEPAD_DEADZONE
        
        # Callbacki dla przycisków
        self.button_callbacks: Dict[str, Callable] = {}
        
        # Stan przycisków (pressed/released)
        self.button_states: Dict[str, bool] = {}
        
        # Stan analogów
        self.analog_states: Dict[str, float] = {
            'left_x': 0.0,
            'left_y': 0.0,
            'right_x': 0.0,
            'right_y': 0.0
        }
        
        logger.debug("GamepadHandler zainicjalizowany")
    
    def start(self) -> bool:
        """
        Uruchamia nasłuchiwanie gamepada w osobnym wątku.
        
        Returns:
            True jeśli uruchomiono pomyślnie
        """
        try:
            if not GAMEPAD_AVAILABLE:
                logger.error("Biblioteka 'inputs' nie jest dostępna")
                return False
            
            if self.running:
                logger.warning("Gamepad handler już działa")
                return True
            
            self.running = True
            self.thread = threading.Thread(target=self._gamepad_loop, daemon=True)
            self.thread.start()
            
            logger.info("Gamepad handler uruchomiony")
            return True
            
        except Exception as e:
            logger.error(f"Błąd uruchamiania gamepad handler: {e}")
            self.running = False
            return False
    
    def stop(self):
        """Zatrzymuje nasłuchiwanie gamepada."""
        try:
            self.running = False
            
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=2.0)
            
            logger.info("Gamepad handler zatrzymany")
            
        except Exception as e:
            logger.error(f"Błąd zatrzymywania gamepad handler: {e}")
    
    def _gamepad_loop(self):
        """
        Główna pętla nasłuchująca eventów z gamepada.
        Działa w osobnym wątku.
        """
        logger.info("Pętla gamepada rozpoczęta")
        
        while self.running:
            try:
                events = get_gamepad()
                
                for event in events:
                    if not self.running:
                        break
                    
                    self._process_event(event)
                    
            except UnpluggedError:
                logger.warning("Gamepad odłączony")
                self.running = False
                break
                
            except Exception as e:
                logger.error(f"Błąd w pętli gamepada: {e}")
                # Nie przerywaj pętli przy innych błędach
        
        logger.info("Pętla gamepada zakończona")
    
    def _process_event(self, event):
        """
        Przetwarza pojedynczy event z gamepada.
        
        Args:
            event: Event z biblioteki inputs
        """
        try:
            event_type = event.ev_type
            event_code = event.code
            event_state = event.state
            
            # Przyciski
            if event_type == 'Key':
                self._handle_button_event(event_code, event_state)
            
            # Analogi (joysticki, triggery)
            elif event_type == 'Absolute':
                self._handle_analog_event(event_code, event_state)
            
        except Exception as e:
            logger.error(f"Błąd przetwarzania eventu gamepada: {e}")
    
    def _handle_button_event(self, button_code: str, state: int):
        """
        Obsługuje event przycisku.
        
        Args:
            button_code: Kod przycisku
            state: Stan (0=released, 1=pressed)
        """
        try:
            is_pressed = (state == 1)
            self.button_states[button_code] = is_pressed
            
            # Wywołaj callback jeśli zarejestrowany
            if button_code in self.button_callbacks:
                callback = self.button_callbacks[button_code]
                callback(button_code, is_pressed)
            
            # Dodaj event do kolejki
            self.event_queue.put({
                'type': 'button',
                'code': button_code,
                'pressed': is_pressed
            })
            
            logger.debug(f"Przycisk {button_code}: {'pressed' if is_pressed else 'released'}")
            
        except Exception as e:
            logger.error(f"Błąd obsługi przycisku {button_code}: {e}")
    
    def _handle_analog_event(self, analog_code: str, value: int):
        """
        Obsługuje event analogu.
        
        Args:
            analog_code: Kod analogu
            value: Wartość (zazwyczaj -32768 do 32767)
        """
        try:
            # Normalizuj wartość do -1.0 ... 1.0
            normalized_value = value / 32768.0
            
            # Aplikuj deadzone
            if abs(normalized_value) < self.deadzone:
                normalized_value = 0.0
            
            # Mapuj kody analogów
            analog_map = {
                'ABS_X': 'left_x',
                'ABS_Y': 'left_y',
                'ABS_RX': 'right_x',
                'ABS_RY': 'right_y'
            }
            
            analog_name = analog_map.get(analog_code)
            if analog_name:
                self.analog_states[analog_name] = normalized_value
                
                # Dodaj event do kolejki
                self.event_queue.put({
                    'type': 'analog',
                    'code': analog_name,
                    'value': normalized_value
                })
            
            logger.debug(f"Analog {analog_code}: {normalized_value:.2f}")
            
        except Exception as e:
            logger.error(f"Błąd obsługi analogu {analog_code}: {e}")
    
    def register_button_callback(self, button_code: str, callback: Callable):
        """
        Rejestruje callback dla przycisku.
        
        Args:
            button_code: Kod przycisku
            callback: Funkcja wywoływana przy evencie (button_code, is_pressed)
        """
        self.button_callbacks[button_code] = callback
        logger.debug(f"Zarejestrowano callback dla przycisku: {button_code}")
    
    def unregister_button_callback(self, button_code: str):
        """
        Usuwa callback dla przycisku.
        
        Args:
            button_code: Kod przycisku
        """
        if button_code in self.button_callbacks:
            del self.button_callbacks[button_code]
            logger.debug(f"Usunięto callback dla przycisku: {button_code}")
    
    def get_button_state(self, button_code: str) -> bool:
        """
        Zwraca aktualny stan przycisku.
        
        Args:
            button_code: Kod przycisku
            
        Returns:
            True jeśli przycisk jest wciśnięty
        """
        return self.button_states.get(button_code, False)
    
    def get_analog_state(self, analog_name: str) -> float:
        """
        Zwraca aktualną wartość analogu.
        
        Args:
            analog_name: Nazwa analogu (left_x, left_y, right_x, right_y)
            
        Returns:
            Wartość analogu (-1.0 do 1.0)
        """
        return self.analog_states.get(analog_name, 0.0)
    
    def get_event(self, block: bool = False, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Pobiera event z kolejki.
        
        Args:
            block: Czy blokować czekając na event
            timeout: Timeout w sekundach (None = nieskończony)
            
        Returns:
            Słownik z eventem lub None
        """
        try:
            return self.event_queue.get(block=block, timeout=timeout)
        except Empty:
            return None
    
    def set_deadzone(self, deadzone: float):
        """
        Ustawia deadzone dla analogów.
        
        Args:
            deadzone: Wartość deadzone (0.0 - 1.0)
        """
        self.deadzone = max(0.0, min(1.0, deadzone))
        logger.debug(f"Deadzone ustawione na: {self.deadzone}")
    
    def is_running(self) -> bool:
        """
        Sprawdza czy handler działa.
        
        Returns:
            True jeśli działa
        """
        return self.running
    
    def vibrate(self, duration: float = 0.5):
        """
        Wibracja gamepada (jeśli obsługiwana).
        
        Args:
            duration: Czas wibracji w sekundach
        """
        # TODO: Implementacja wibracji wymaga dodatkowej biblioteki
        # Na razie placeholder
        logger.debug(f"Vibrate: {duration}s (not implemented)")
    
    def cleanup(self):
        """Czyści zasoby gamepad handler."""
        try:
            self.stop()
            self.button_callbacks.clear()
            logger.info("GamepadHandler oczyszczony")
        except Exception as e:
            logger.error(f"Błąd czyszczenia GamepadHandler: {e}")
