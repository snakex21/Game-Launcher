"""
Moduł narzędzi pomocniczych (utils)
Zawiera funkcje pomocnicze do operacji na plikach, obrazach, systemie i sieci.
"""

from .file_utils import *
from .image_utils import *
from .system_utils import *
from .network_utils import *

__all__ = [
    # File utils
    'ensure_directory',
    'safe_json_load',
    'safe_json_save',
    'get_file_size',
    'get_file_modified_time',
    'copy_file_safe',
    'move_file_safe',
    'delete_file_safe',
    'find_files',
    'get_available_filename',
    
    # Image utils
    'load_image',
    'resize_image',
    'create_thumbnail',
    'save_image',
    'get_image_size',
    'image_to_base64',
    'base64_to_image',
    'create_gradient',
    'add_text_to_image',
    
    # System utils
    'get_system_info',
    'get_cpu_usage',
    'get_memory_usage',
    'get_disk_usage',
    'is_process_running',
    'kill_process',
    'get_process_info',
    'open_file_location',
    'run_as_admin',
    'get_registry_value',
    'set_registry_value',
    
    # Network utils
    'check_internet_connection',
    'download_file',
    'get_public_ip',
    'get_local_ip',
    'ping_host',
    'is_port_open',
    'get_available_port',
    'make_request'
]
