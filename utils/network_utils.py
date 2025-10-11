"""
Narzędzia sieciowe
Zawiera funkcje do operacji sieciowych (HTTP, ping, porty, etc.).
"""

import socket
import logging
import requests
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Timeout dla requestów HTTP
DEFAULT_TIMEOUT = 10


def check_internet_connection(host: str = "8.8.8.8", port: int = 53, timeout: int = 3) -> bool:
    """
    Sprawdza czy jest połączenie z internetem.
    
    Args:
        host: Host do sprawdzenia (domyślnie DNS Google)
        port: Port do sprawdzenia
        timeout: Timeout w sekundach
        
    Returns:
        True jeśli jest połączenie
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False


def download_file(url: str, 
                 output_path: str,
                 chunk_size: int = 8192,
                 timeout: int = DEFAULT_TIMEOUT,
                 headers: Optional[Dict[str, str]] = None) -> bool:
    """
    Pobiera plik z URL.
    
    Args:
        url: URL pliku do pobrania
        output_path: Ścieżka wyjściowa
        chunk_size: Rozmiar chunka do pobierania
        timeout: Timeout w sekundach
        headers: Opcjonalne nagłówki HTTP
        
    Returns:
        True jeśli pobrano pomyślnie
    """
    try:
        response = requests.get(url, stream=True, timeout=timeout, headers=headers)
        response.raise_for_status()
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"Pobrano plik: {url} -> {output_path}")
        return True
        
    except requests.RequestException as e:
        logger.error(f"Błąd pobierania pliku {url}: {e}")
        return False
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd podczas pobierania {url}: {e}")
        return False


def get_public_ip() -> Optional[str]:
    """
    Zwraca publiczny adres IP.
    
    Returns:
        String z adresem IP lub None
    """
    try:
        response = requests.get('https://api.ipify.org', timeout=5)
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        logger.error(f"Błąd pobierania publicznego IP: {e}")
        return None


def get_local_ip() -> Optional[str]:
    """
    Zwraca lokalny adres IP.
    
    Returns:
        String z adresem IP lub None
    """
    try:
        # Trik: łączymy się z Google DNS, żeby uzyskać lokalny IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        logger.error(f"Błąd pobierania lokalnego IP: {e}")
        return None


def ping_host(host: str, timeout: int = 3) -> Tuple[bool, Optional[float]]:
    """
    Pinguje hosta i zwraca czas odpowiedzi.
    
    Args:
        host: Host do sprawdzenia
        timeout: Timeout w sekundach
        
    Returns:
        Tuple (success, response_time_ms)
    """
    import subprocess
    import platform
    import re
    
    try:
        # Parametry zależne od systemu
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        timeout_param = '-w' if platform.system().lower() == 'windows' else '-W'
        
        # Wykonaj ping
        command = ['ping', param, '1', timeout_param, str(timeout * 1000), host]
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout + 1
        )
        
        if result.returncode == 0:
            # Wyciągnij czas odpowiedzi z outputu
            output = result.stdout.decode()
            
            # Windows: "time=XXms" lub "czas=XXms"
            # Linux: "time=XX.X ms"
            match = re.search(r'time[=<](\d+\.?\d*)', output.lower())
            
            if match:
                response_time = float(match.group(1))
                return True, response_time
            
            return True, None
        
        return False, None
        
    except subprocess.TimeoutExpired:
        logger.warning(f"Timeout podczas pingowania {host}")
        return False, None
    except Exception as e:
        logger.error(f"Błąd pingowania {host}: {e}")
        return False, None


def is_port_open(host: str, port: int, timeout: int = 3) -> bool:
    """
    Sprawdza czy port jest otwarty na hoście.
    
    Args:
        host: Host do sprawdzenia
        port: Numer portu
        timeout: Timeout w sekundach
        
    Returns:
        True jeśli port jest otwarty
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.error(f"Błąd sprawdzania portu {host}:{port}: {e}")
        return False


def get_available_port(start_port: int = 5000, max_attempts: int = 100) -> Optional[int]:
    """
    Znajduje dostępny port.
    
    Args:
        start_port: Port początkowy
        max_attempts: Maksymalna liczba prób
        
    Returns:
        Numer dostępnego portu lub None
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', port))
            sock.close()
            logger.debug(f"Znaleziono dostępny port: {port}")
            return port
        except OSError:
            continue
    
    logger.error(f"Nie znaleziono dostępnego portu po {max_attempts} próbach")
    return None


def make_request(url: str,
                method: str = 'GET',
                params: Optional[Dict[str, Any]] = None,
                data: Optional[Dict[str, Any]] = None,
                json: Optional[Dict[str, Any]] = None,
                headers: Optional[Dict[str, str]] = None,
                timeout: int = DEFAULT_TIMEOUT) -> Optional[requests.Response]:
    """
    Wykonuje żądanie HTTP z obsługą błędów.
    
    Args:
        url: URL żądania
        method: Metoda HTTP (GET, POST, etc.)
        params: Parametry query string
        data: Dane formularza
        json: Dane JSON
        headers: Nagłówki HTTP
        timeout: Timeout w sekundach
        
    Returns:
        Obiekt Response lub None w przypadku błędu
    """
    try:
        response = requests.request(
            method=method.upper(),
            url=url,
            params=params,
            data=data,
            json=json,
            headers=headers,
            timeout=timeout
        )
        response.raise_for_status()
        
        logger.debug(f"{method} {url} - Status: {response.status_code}")
        return response
        
    except requests.Timeout:
        logger.error(f"Timeout podczas żądania {method} {url}")
        return None
    except requests.ConnectionError:
        logger.error(f"Błąd połączenia: {method} {url}")
        return None
    except requests.HTTPError as e:
        logger.error(f"Błąd HTTP {e.response.status_code}: {method} {url}")
        return None
    except Exception as e:
        logger.error(f"Błąd żądania {method} {url}: {e}")
        return None


def get_json(url: str,
            params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None,
            timeout: int = DEFAULT_TIMEOUT) -> Optional[Dict[str, Any]]:
    """
    Pobiera dane JSON z URL.
    
    Args:
        url: URL do pobrania
        params: Parametry query string
        headers: Nagłówki HTTP
        timeout: Timeout w sekundach
        
    Returns:
        Słownik z danymi JSON lub None
    """
    try:
        response = make_request(
            url=url,
            method='GET',
            params=params,
            headers=headers,
            timeout=timeout
        )
        
        if response:
            return response.json()
        
        return None
        
    except requests.JSONDecodeError:
        logger.error(f"Błąd parsowania JSON z {url}")
        return None
    except Exception as e:
        logger.error(f"Błąd pobierania JSON z {url}: {e}")
        return None


def post_json(url: str,
             data: Dict[str, Any],
             headers: Optional[Dict[str, str]] = None,
             timeout: int = DEFAULT_TIMEOUT) -> Optional[Dict[str, Any]]:
    """
    Wysyła dane JSON metodą POST.
    
    Args:
        url: URL do wysłania
        data: Dane JSON do wysłania
        headers: Nagłówki HTTP
        timeout: Timeout w sekundach
        
    Returns:
        Słownik z odpowiedzią JSON lub None
    """
    try:
        response = make_request(
            url=url,
            method='POST',
            json=data,
            headers=headers,
            timeout=timeout
        )
        
        if response:
            return response.json()
        
        return None
        
    except requests.JSONDecodeError:
        logger.error(f"Błąd parsowania odpowiedzi JSON z {url}")
        return None
    except Exception as e:
        logger.error(f"Błąd wysyłania JSON do {url}: {e}")
        return None


def validate_url(url: str) -> bool:
    """
    Sprawdza czy URL jest prawidłowy.
    
    Args:
        url: URL do sprawdzenia
        
    Returns:
        True jeśli URL jest prawidłowy
    """
    import re
    
    # Prosty regex dla URL
    url_pattern = re.compile(
        r'^https?://'  # http:// lub https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domena
        r'localhost|'  # lub localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # lub IP
        r'(?::\d+)?'  # opcjonalny port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None


def get_hostname() -> Optional[str]:
    """
    Zwraca nazwę hosta komputera.
    
    Returns:
        Nazwa hosta lub None
    """
    try:
        return socket.gethostname()
    except Exception as e:
        logger.error(f"Błąd pobierania nazwy hosta: {e}")
        return None


def resolve_hostname(hostname: str) -> Optional[str]:
    """
    Rozwiązuje hostname do adresu IP.
    
    Args:
        hostname: Nazwa hosta do rozwiązania
        
    Returns:
        Adres IP lub None
    """
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        logger.error(f"Nie można rozwiązać hostname: {hostname}")
        return None
    except Exception as e:
        logger.error(f"Błąd rozwiązywania hostname {hostname}: {e}")
        return None
