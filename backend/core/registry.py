import os
import importlib
import inspect
import logging
from typing import Dict, Any, List, Optional
from pydantic import ValidationError
from backend.core.base_module import PemaliModuleV2, ModuleOutput

logger = logging.getLogger("PEMALI.Registry")

# Path absolute ke folder modules — gak peduli working directory
_MODULES_ABS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "modules"
)

class ModuleRegistry:
    """
    Manajemen siklus hidup modul (Discovery, Validation, & Execution).
    
    Discovery rules:
    - Scan backend/modules/ untuk file *.py
    - Skip file berawalan __ (dunder) atau _ (private/template/example)
    - Instantiate setiap subclass PemaliModuleV2 yang ditemukan
    - Index by instance.name
    """
    def __init__(self, modules_dir: str = ""):
        self.modules_dir = modules_dir if modules_dir else _MODULES_ABS
        self.tools: Dict[str, PemaliModuleV2] = {}
        self._load_failures: Dict[str, str] = {}
        self.load_modules()

    def load_modules(self) -> None:
        if not os.path.exists(self.modules_dir):
            os.makedirs(self.modules_dir)

        # Compute module import prefix dari absolute path
        # /home/.../backend/modules -> backend.modules
        _project_root = os.path.dirname(os.path.dirname(_MODULES_ABS))
        _import_prefix = os.path.relpath(self.modules_dir, _project_root).replace("/", ".")

        for filename in os.listdir(self.modules_dir):
            # Skip: dunder, private/template, non-Python files
            if (not filename.endswith(".py") or 
                filename.startswith("__") or 
                filename.startswith("_")):
                continue

            module_path = f"{_import_prefix}.{filename[:-3]}"
            try:
                mod = importlib.import_module(module_path)
                for _, obj in inspect.getmembers(mod):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, PemaliModuleV2) and 
                        obj is not PemaliModuleV2):
                        
                        instance = obj()
                        
                        # Self-validation
                        validation_errors = instance.validate_self()
                        if validation_errors:
                            logger.warning(
                                f"[Registry] Module {instance.name} failed self-validation: "
                                f"{'; '.join(validation_errors)}"
                            )
                            self._load_failures[instance.name] = "; ".join(validation_errors)
                            continue
                        
                        self.tools[instance.name] = instance
                        tag_info = f" — tags: {', '.join(instance.tags)}" if instance.tags else ""
                        version_info = f" — v{instance.version}"
                        logger.info(
                            f"[Registry] Loaded: {instance.name}{version_info}{tag_info}"
                        )
            except Exception as e:
                logger.warning(f"[Registry] Error loading {module_path}: {e}")
                self._load_failures[module_path] = str(e)

    def get_all_manifests(self) -> List[Dict[str, Any]]:
        return [{
            "name": t.name,
            "description": t.description,
            "parameters": t.input_schema.model_json_schema(),
            "depends_on": t.depends_on,
            "version": t.version,
            "tags": t.tags,
            "output_example": t.output_example,
        } for t in self.tools.values()]

    async def execute_tool(self, tool_name: str, raw_params: Dict[str, Any], session_id: str = None) -> ModuleOutput:
        logger.debug(f"[Registry] execute_tool called: {tool_name}, params={raw_params}")
        if tool_name not in self.tools:
            logger.warning(f"[Registry] Tool not found: {tool_name}")
            return ModuleOutput(
                status=404,
                error_msg=f"Tool '{tool_name}' tidak ditemukan. Tools tersedia: {list(self.tools.keys())}",
                agent_hint=f"Tool '{tool_name}' belum terdaftar. Periksa nama tool dan coba lagi.",
            )
        
        tool = self.tools[tool_name]
        try:
            validated_params = tool.input_schema(**raw_params)
            context = {"session_id": session_id}
            logger.debug(f"[Registry] Executing {tool_name} with validated params")
            return await tool.execute(validated_params, context)
            
        except ValidationError as ve:
            logger.error(f"[Registry] Validation error for {tool_name}: {ve}")
            error_detail = ve.json() if hasattr(ve, 'json') else str(ve.errors())
            return ModuleOutput(
                status=400,
                error_msg=f"Validation Error: {error_detail}",
                agent_hint=f"Parameter tidak valid untuk '{tool_name}'. Periksa kembali format input.",
            )
        except Exception as e:
            logger.error(f"[Registry] Execution error for {tool_name}: {e}", exc_info=True)
            return ModuleOutput(
                status=500,
                error_msg=f"Internal Error: {str(e)}",
                agent_hint=f"'{tool_name}' mengalami error internal. Coba lagi atau laporkan ke tim.",
            )

    def get_load_failures(self) -> Dict[str, str]:
        """Return modules that failed to load with their error messages."""
        return dict(self._load_failures)

registry = ModuleRegistry()