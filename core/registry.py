import os
import importlib
import inspect
from typing import Dict, Any, List, Optional
from core.base_module import PemaliModuleV2, ModuleOutput

class ModuleRegistry:
    def __init__(self, modules_dir: str = "modules"):
        self.modules_dir = modules_dir
        self.tools: Dict[str, PemaliModuleV2] = {}
        self.load_modules()

    def load_modules(self) -> None:
        """Dynamic discovery untuk PemaliModuleV2 dengan Pydantic support."""
        if not os.path.exists(self.modules_dir):
            os.makedirs(self.modules_dir)
            
        for filename in os.listdir(self.modules_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                module_path = f"{self.modules_dir}.{module_name}"
                
                try:
                    mod = importlib.import_module(module_path)
                    for _, obj in inspect.getmembers(mod):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, PemaliModuleV2) and 
                            obj is not PemaliModuleV2):
                            
                            instance = obj()
                            if instance.name:
                                self.tools[instance.name] = instance
                                print(f"[Registry] V2 Loaded: {instance.name}")
                                
                except Exception as e:
                    print(f"[Registry] Failed to load {module_path}: {e}")

    def get_all_manifests(self) -> List[Dict[str, Any]]:
        """
        Auto-generate JSON Schema untuk LLM Tool Calling.
        Mengonversi Pydantic input_schema ke format standar.
        """
        manifests = []
        for tool in self.tools.values():
            manifests.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema.model_json_schema(),
                "depends_on": tool.depends_on
            })
        return manifests

    async def execute_tool(self, tool_name: str, raw_params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ModuleOutput:
        """
        Dispatcher dengan validasi input otomatis.
        """
        if tool_name not in self.tools:
            return ModuleOutput(status=404, error_msg=f"Tool '{tool_name}' not found.")
        
        tool = self.tools[tool_name]
        ctx = context or {}
        
        try:
            # Validasi input menggunakan schema Pydantic modul
            validated_params = tool.input_schema(**raw_params)
            return await tool.execute(validated_params, ctx)
        except Exception as e:
            return ModuleOutput(status=400, error_msg=f"Validation/Execution Error: {str(e)}")

# Singleton Instance
registry = ModuleRegistry()