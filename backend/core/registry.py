import os
import importlib
import inspect
from typing import Dict, Any, List, Optional
from pydantic import ValidationError
from backend.core.base_module import PemaliModuleV2, ModuleOutput

class ModuleRegistry:
    """
    Manajemen siklus hidup modul (Discovery, Validation, & Execution).
    """
    def __init__(self, modules_dir: str = "backend/modules"):
        self.modules_dir = modules_dir
        self.tools: Dict[str, PemaliModuleV2] = {}
        self.load_modules()

    def load_modules(self) -> None:
        if not os.path.exists(self.modules_dir):
            os.makedirs(self.modules_dir)

        for filename in os.listdir(self.modules_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_path = self.modules_dir.replace("/", ".").replace("\\", ".") + "." + filename[:-3]
                try:
                    mod = importlib.import_module(module_path)
                    for _, obj in inspect.getmembers(mod):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, PemaliModuleV2) and 
                            obj is not PemaliModuleV2):
                            
                            instance = obj()
                            self.tools[instance.name] = instance
                            print(f"[Registry] Module V2 Loaded: {instance.name}")
                except Exception as e:
                    print(f"[Registry] Error loading {module_path}: {e}")

    def get_all_manifests(self) -> List[Dict[str, Any]]:
        return [{
            "name": t.name,
            "description": t.description,
            "parameters": t.input_schema.model_json_schema(),
            "depends_on": t.depends_on
        } for t in self.tools.values()]

    async def execute_tool(self, tool_name: str, raw_params: Dict[str, Any], session_id: str = None) -> ModuleOutput:
        if tool_name not in self.tools:
            return ModuleOutput(status=404, error_msg=f"Tool {tool_name} tidak ditemukan.")
        
        tool = self.tools[tool_name]
        try:
            # Validasi input menggunakan schema modul
            validated_params = tool.input_schema(**raw_params)
            context = {"session_id": session_id}
            return await tool.execute(validated_params, context)
            
        except ValidationError as ve:
            return ModuleOutput(status=400, error_msg=f"Validation Error: {ve.model_dump_json()}")
        except Exception as e:
            return ModuleOutput(status=500, error_msg=f"Internal Error: {str(e)}")

registry = ModuleRegistry()