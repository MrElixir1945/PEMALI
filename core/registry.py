import os
import importlib
import inspect
from typing import Dict, Any, List
from core.base_module import PemaliModule, ModuleOutput

class ModuleRegistry:
    def __init__(self, modules_dir: str = "modules"):
        self.modules_dir = modules_dir
        self.tools: Dict[str, PemaliModule] = {}
        self.load_modules()

    def load_modules(self) -> None:
        """Scan & dynamic load class PemaliModule dari modules_dir."""
        if not os.path.exists(self.modules_dir):
            os.makedirs(self.modules_dir)
            
        for filename in os.listdir(self.modules_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                module_path = f"{self.modules_dir}.{module_name}"
                
                try:
                    mod = importlib.import_module(module_path)
                    
                    for name, obj in inspect.getmembers(mod):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, PemaliModule) and 
                            obj is not PemaliModule):
                            
                            instance = obj()
                            tool_name = instance.manifest.get("name")
                            
                            if tool_name:
                                self.tools[tool_name] = instance
                                print(f"[Registry] Loaded: {tool_name}")
                                
                except Exception as e:
                    print(f"[Registry] Error {module_path}: {e}")

    def get_all_manifests(self) -> List[Dict[str, Any]]:
        """Return array of JSON Schema untuk LLM Tool Calling context."""
        return [tool.manifest for tool in self.tools.values()]

    async def execute_tool(self, tool_name: str, params: Dict[str, Any], session_id: str = None) -> ModuleOutput:
        """Dispatcher request ke module yang di-load."""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not registered.")
        
        return await self.tools[tool_name].execute(params, session_id=session_id)

# Export singleton
registry = ModuleRegistry()