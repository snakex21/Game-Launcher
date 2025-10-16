# core/plugin_manager.py
import os
import importlib.util
import inspect
from .plugin_interface import BasePlugin

def load_plugins(app_context):
    plugins = []
    plugins_dir = 'plugins'
    if not os.path.exists(plugins_dir):
        return []

    for dir_name in os.listdir(plugins_dir):
        plugin_path = os.path.join(plugins_dir, dir_name) # <-- POPRAWKA: Używamy `dir_name`
        if os.path.isdir(plugin_path):
            try:
                module_path = os.path.join(plugin_path, 'plugin.py')
                if not os.path.exists(module_path):
                    continue

                spec = importlib.util.spec_from_file_location(f"plugins.{dir_name}.plugin", module_path) # <-- POPRAWKA: Używamy `dir_name`
                plugin_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(plugin_module)

                for name, obj in inspect.getmembers(plugin_module):
                    if inspect.isclass(obj) and issubclass(obj, BasePlugin) and obj is not BasePlugin:
                        instance = obj(app_context)
                        plugins.append(instance)
                        
                        app_context.data_manager.register_plugin_storage(
                            instance.plugin_name, 
                            instance.get_default_storage()
                        )
                        print(f"Załadowano i zarejestrowano plugin: {instance.plugin_name}")
            
            # --- BRAKUJĄCA I KLUCZOWA CZĘŚĆ ---
            except Exception as e:
                print(f"Błąd podczas ładowania pluginu {dir_name}: {e}")
                # Kontynuujemy, aby błąd w jednym pluginie nie zatrzymał całej aplikacji
                continue
    return plugins