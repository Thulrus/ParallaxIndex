"""
Plugin registry and loader for Parallax Index.

Manages discovery, registration, and retrieval of plugins.
"""

import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Optional

from plugins.base import PluginBase
from core.schemas import PluginDefinition


class PluginRegistry:
    """
    Central registry for all available plugins.
    
    Plugins are discovered at startup by scanning the plugins directory.
    The registry provides lookup and instantiation services.
    """
    
    def __init__(self):
        self._plugins: dict[str, type[PluginBase]] = {}
        self._definitions: dict[str, PluginDefinition] = {}
    
    def register(self, plugin_class: type[PluginBase]) -> None:
        """
        Register a plugin class.
        
        Args:
            plugin_class: A class that inherits from PluginBase
            
        Raises:
            ValueError: If plugin_id is already registered
        """
        # Instantiate to get definition
        instance = plugin_class()
        definition = instance.get_definition()
        
        if definition.plugin_id in self._plugins:
            raise ValueError(
                f"Plugin '{definition.plugin_id}' is already registered"
            )
        
        self._plugins[definition.plugin_id] = plugin_class
        self._definitions[definition.plugin_id] = definition
        
        print(f"Registered plugin: {definition.display_name} ({definition.plugin_id})")
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginBase]:
        """
        Get an instance of a plugin by ID.
        
        Args:
            plugin_id: The unique plugin identifier
            
        Returns:
            New instance of the plugin, or None if not found
        """
        plugin_class = self._plugins.get(plugin_id)
        if plugin_class:
            return plugin_class()
        return None
    
    def get_definition(self, plugin_id: str) -> Optional[PluginDefinition]:
        """
        Get the definition for a plugin without instantiating it.
        
        Args:
            plugin_id: The unique plugin identifier
            
        Returns:
            PluginDefinition or None if not found
        """
        return self._definitions.get(plugin_id)
    
    def list_plugins(self) -> list[PluginDefinition]:
        """
        List all registered plugins.
        
        Returns:
            List of PluginDefinition objects
        """
        return list(self._definitions.values())
    
    def discover_plugins(self) -> None:
        """
        Automatically discover and register plugins from the plugins directory.
        
        Scans for Python modules containing PluginBase subclasses and
        registers them automatically.
        """
        # Get the plugins directory
        plugins_dir = Path(__file__).parent
        
        # Import all Python modules in the plugins directory
        for importer, modname, ispkg in pkgutil.iter_modules([str(plugins_dir)]):
            # Skip base module and private modules
            if modname in ['base', 'registry'] or modname.startswith('_'):
                continue
            
            try:
                # Import the module
                module = importlib.import_module(f'plugins.{modname}')
                
                # Find all PluginBase subclasses
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # Check if it's a PluginBase subclass (but not PluginBase itself)
                    if (issubclass(obj, PluginBase) and 
                        obj is not PluginBase and
                        obj.__module__ == module.__name__):
                        try:
                            self.register(obj)
                        except Exception as e:
                            print(f"Failed to register {name} from {modname}: {e}")
            
            except Exception as e:
                print(f"Failed to load plugin module {modname}: {e}")


# Global registry instance
registry = PluginRegistry()


def get_registry() -> PluginRegistry:
    """
    Get the global plugin registry.
    
    Returns:
        The singleton PluginRegistry instance
    """
    return registry
