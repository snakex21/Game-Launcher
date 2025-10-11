"""
Narzędzia systemowe
Zawiera funkcje do monitorowania systemu, procesów i rejestru Windows.
"""

import os
import sys
import psutil
import logging
import subprocess
import winreg
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


def get_system_info() -> Dict[str, Any]:
    """
    Zwraca informacje o systemie.
    
    Returns:
        Słownik z informacjami systemowymi
    """
    try:
        return {
            'platform': sys.platform,
            'python_version': sys.version,
            'cpu_count': psutil.cpu_count(),
            'cpu_freq': psutil.cpu_freq().current if psutil.cpu_freq() else None,
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'disk_usage': {
                partition.mountpoint: {
                    'total': psutil.disk_usage(partition.mountpoint).total,
                    'used': psutil.disk_usage(partition.mountpoint).used,
                    'free': psutil.disk_usage(partition.mountpoint).free,
                    'percent': psutil.disk_usage(partition.mountpoint).percent
                }
                for partition in psutil.disk_partitions()
            }
        }
    except Exception as e:
        logger.error(f"Błąd pobierania informacji systemowych: {e}")
        return {}


def get_cpu_usage(interval: float = 1.0) -> float:
    """
    Zwraca aktualne użycie CPU (%).
    
    Args:
        interval: Interwał pomiaru w sekundach
        
    Returns:
        Procentowe użycie CPU
    """
    try:
        return psutil.cpu_percent(interval=interval)
    except Exception as e:
        logger.error(f"Błąd pobierania użycia CPU: {e}")
        return 0.0


def get_memory_usage() -> Dict[str, Any]:
    """
    Zwraca informacje o użyciu pamięci RAM.
    
    Returns:
        Słownik z danymi o pamięci
    """
    try:
        mem = psutil.virtual_memory()
        return {
            'total': mem.total,
            'available': mem.available,
            'used': mem.used,
            'percent': mem.percent,
            'free': mem.free
        }
    except Exception as e:
        logger.error(f"Błąd pobierania użycia pamięci: {e}")
        return {}


def get_disk_usage(path: str = "/") -> Dict[str, Any]:
    """
    Zwraca informacje o użyciu dysku.
    
    Args:
        path: Ścieżka do sprawdzenia (domyślnie root)
        
    Returns:
        Słownik z danymi o dysku
    """
    try:
        usage = psutil.disk_usage(path)
        return {
            'total': usage.total,
            'used': usage.used,
            'free': usage.free,
            'percent': usage.percent
        }
    except Exception as e:
        logger.error(f"Błąd pobierania użycia dysku {path}: {e}")
        return {}


def is_process_running(process_name: str) -> bool:
    """
    Sprawdza czy proces o danej nazwie jest uruchomiony.
    
    Args:
        process_name: Nazwa procesu (np. "notepad.exe")
        
    Returns:
        True jeśli proces działa
    """
    try:
        for proc in psutil.process_iter(['name']):
            if proc.info['name'].lower() == process_name.lower():
                return True
        return False
    except Exception as e:
        logger.error(f"Błąd sprawdzania procesu {process_name}: {e}")
        return False


def get_process_info(process_name: str) -> List[Dict[str, Any]]:
    """
    Zwraca informacje o wszystkich procesach o danej nazwie.
    
    Args:
        process_name: Nazwa procesu
        
    Returns:
        Lista słowników z informacjami o procesach
    """
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'create_time']):
            if proc.info['name'].lower() == process_name.lower():
                processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'cpu_percent': proc.info['cpu_percent'],
                    'memory_mb': proc.info['memory_info'].rss / (1024 * 1024) if proc.info['memory_info'] else 0,
                    'create_time': proc.info['create_time']
                })
        return processes
    except Exception as e:
        logger.error(f"Błąd pobierania informacji o procesie {process_name}: {e}")
        return []


def kill_process(process_name: Optional[str] = None, 
                pid: Optional[int] = None,
                force: bool = False) -> bool:
    """
    Zabija proces po nazwie lub PID.
    
    Args:
        process_name: Nazwa procesu do zabicia
        pid: PID procesu do zabicia
        force: Czy użyć SIGKILL (force)
        
    Returns:
        True jeśli zabito proces
    """
    try:
        if pid:
            proc = psutil.Process(pid)
            if force:
                proc.kill()
            else:
                proc.terminate()
            logger.info(f"Zabito proces PID: {pid}")
            return True
            
        elif process_name:
            killed = False
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() == process_name.lower():
                    if force:
                        proc.kill()
                    else:
                        proc.terminate()
                    killed = True
                    logger.info(f"Zabito proces: {process_name} (PID: {proc.info['pid']})")
            return killed
            
        else:
            logger.warning("Nie podano ani nazwy procesu ani PID")
            return False
            
    except psutil.NoSuchProcess:
        logger.warning(f"Proces nie istnieje")
        return False
    except Exception as e:
        logger.error(f"Błąd zabijania procesu: {e}")
        return False


def open_file_location(filepath: str) -> bool:
    """
    Otwiera lokalizację pliku w eksploratorze plików.
    
    Args:
        filepath: Ścieżka do pliku
        
    Returns:
        True jeśli otwarto pomyślnie
    """
    try:
        filepath = Path(filepath).resolve()
        
        if sys.platform == 'win32':
            subprocess.run(['explorer', '/select,', str(filepath)])
        elif sys.platform == 'darwin':  # macOS
            subprocess.run(['open', '-R', str(filepath)])
        else:  # Linux
            subprocess.run(['xdg-open', str(filepath.parent)])
        
        logger.debug(f"Otwarto lokalizację: {filepath}")
        return True
        
    except Exception as e:
        logger.error(f"Błąd otwierania lokalizacji {filepath}: {e}")
        return False


def run_as_admin(filepath: str, parameters: str = "") -> bool:
    """
    Uruchamia program z uprawnieniami administratora (Windows).
    
    Args:
        filepath: Ścieżka do programu
        parameters: Parametry wiersza poleceń
        
    Returns:
        True jeśli uruchomiono pomyślnie
    """
    try:
        if sys.platform != 'win32':
            logger.warning("run_as_admin działa tylko na Windows")
            return False
        
        import ctypes
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", filepath, parameters, None, 1
        )
        
        # Wartość > 32 oznacza sukces
        success = result > 32
        
        if success:
            logger.info(f"Uruchomiono jako admin: {filepath}")
        else:
            logger.warning(f"Nie udało się uruchomić jako admin: {filepath}")
        
        return success
        
    except Exception as e:
        logger.error(f"Błąd uruchamiania jako admin {filepath}: {e}")
        return False


def get_registry_value(key_path: str, value_name: str, 
                      root: int = winreg.HKEY_CURRENT_USER) -> Optional[Any]:
    """
    Pobiera wartość z rejestru Windows.
    
    Args:
        key_path: Ścieżka do klucza (np. "Software\\MyApp")
        value_name: Nazwa wartości
        root: Korzeń rejestru (domyślnie HKEY_CURRENT_USER)
        
    Returns:
        Wartość z rejestru lub None
    """
    try:
        if sys.platform != 'win32':
            logger.warning("Rejestr Windows dostępny tylko na Windows")
            return None
        
        key = winreg.OpenKey(root, key_path, 0, winreg.KEY_READ)
        value, value_type = winreg.QueryValueEx(key, value_name)
        winreg.CloseKey(key)
        
        logger.debug(f"Pobrano z rejestru: {key_path}\\{value_name} = {value}")
        return value
        
    except FileNotFoundError:
        logger.debug(f"Klucz rejestru nie istnieje: {key_path}\\{value_name}")
        return None
    except Exception as e:
        logger.error(f"Błąd odczytu rejestru: {e}")
        return None


def set_registry_value(key_path: str, value_name: str, value: Any,
                      value_type: int = winreg.REG_SZ,
                      root: int = winreg.HKEY_CURRENT_USER) -> bool:
    """
    Ustawia wartość w rejestrze Windows.
    
    Args:
        key_path: Ścieżka do klucza
        value_name: Nazwa wartości
        value: Wartość do ustawienia
        value_type: Typ wartości (REG_SZ, REG_DWORD, etc.)
        root: Korzeń rejestru
        
    Returns:
        True jeśli ustawiono pomyślnie
    """
    try:
        if sys.platform != 'win32':
            logger.warning("Rejestr Windows dostępny tylko na Windows")
            return False
        
        key = winreg.CreateKey(root, key_path)
        winreg.SetValueEx(key, value_name, 0, value_type, value)
        winreg.CloseKey(key)
        
        logger.debug(f"Ustawiono w rejestrze: {key_path}\\{value_name} = {value}")
        return True
        
    except Exception as e:
        logger.error(f"Błąd zapisu do rejestru: {e}")
        return False


def get_installed_programs() -> List[Dict[str, str]]:
    """
    Zwraca listę zainstalowanych programów (Windows).
    
    Returns:
        Lista słowników z informacjami o programach
    """
    try:
        if sys.platform != 'win32':
            logger.warning("get_installed_programs działa tylko na Windows")
            return []
        
        programs = []
        
        # Sprawdź oba rejestry (32-bit i 64-bit)
        paths = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
        ]
        
        for path in paths:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ)
                
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey = winreg.OpenKey(key, subkey_name)
                        
                        try:
                            name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            version = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                            publisher = winreg.QueryValueEx(subkey, "Publisher")[0]
                            
                            programs.append({
                                'name': name,
                                'version': version,
                                'publisher': publisher
                            })
                        except:
                            pass
                        
                        winreg.CloseKey(subkey)
                    except:
                        continue
                
                winreg.CloseKey(key)
            except:
                continue
        
        return programs
        
    except Exception as e:
        logger.error(f"Błąd pobierania listy programów: {e}")
        return []


def format_bytes(bytes_value: int) -> str:
    """
    Formatuje bajty do czytelnej postaci.
    
    Args:
        bytes_value: Wartość w bajtach
        
    Returns:
        Sformatowany string (np. "1.5 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"
