from pathlib import Path
import sys
import importlib.util

from .base import BaseAdapter
from ..common.logger import SdkLogger


class DataCenterAdapter(BaseAdapter):
    def __init__(self, endpoint: str):
        self.logger = SdkLogger("dc-adapter")
        self._load_modules()

    def _load_modules(self):
        root = Path(__file__).resolve().parent.parent.parent
        for name, path in [
            ("hermes_client_mod", root / "shared" / "hermes" / "client.py"),
            ("hermes_schema_mod", root / "shared" / "hermes" / "schema.py"),
            ("med_kb_mod", root / "dads-medical" / "knowledge_base.py"),
            ("personal_kb_mod", root / "dads-personal" / "protection_rules.py"),
        ]:
            if path.exists():
                spec = importlib.util.spec_from_file_location(name, str(path))
                mod = importlib.util.module_from_spec(spec)
                sys.modules[name] = mod
                spec.loader.exec_module(mod)

    def get_client(self):
        from hermes_client_mod import HermesClient
        return HermesClient()

    def get_schema_types(self):
        from hermes_schema_mod import UserProfile, MedicalRecord
        return UserProfile, MedicalRecord

    def get_medical_kb(self):
        from med_kb_mod import query_medical_knowledge, MEDICAL_KB
        return query_medical_knowledge, MEDICAL_KB

    def get_protection_kb(self):
        from personal_kb_mod import query_protection_rules, PROTECTION_KB
        return query_protection_rules, PROTECTION_KB

    def call(self, method: str, params: dict) -> dict:
        import time
        t0 = time.time()
        try:
            client = self.get_client()
            if method == "read_data":
                client.read_data(params["path"])
                self.logger.log_call("dc", method, int((time.time()-t0)*1000))
                return {"path": params["path"], "status": "ok"}
            if method == "write_data":
                client.write_data(params["path"], params.get("payload", {}))
                self.logger.log_call("dc", method, int((time.time()-t0)*1000))
                return {"path": params["path"], "status": "ok"}
            return {"error": f"unknown method: {method}"}
        except Exception as e:
            self.logger.log_call("dc", method, 0, error=str(e))
            raise
