class DataCenterInterface:
    def __init__(self, dc_adapter):
        self._adapter = dc_adapter
        self.io = DataCenterIO(dc_adapter)
        self.schema = DataCenterSchema(dc_adapter)
        self.kb = DataCenterKB(dc_adapter)


class DataCenterIO:
    def __init__(self, adapter):
        self._a = adapter

    def read_data(self, path: str) -> dict:
        return self._a.call("read_data", {"path": path})

    def write_data(self, path: str, payload: dict) -> dict:
        return self._a.call("write_data", {"path": path, "payload": payload})


class DataCenterSchema:
    def __init__(self, adapter):
        self._a = adapter

    @property
    def UserProfile(self):
        return self._a.get_schema_types()[0]

    @property
    def MedicalRecord(self):
        return self._a.get_schema_types()[1]


class DataCenterKB:
    def __init__(self, adapter):
        self._a = adapter

    def query_medical(self, symptoms: str) -> list:
        fn, kb = self._a.get_medical_kb()
        matches = fn(symptoms)
        return matches if matches else []

    def query_protection(self, scenario: str) -> list:
        fn, kb = self._a.get_protection_kb()
        matches = fn(scenario)
        return matches if matches else []

    def medical_size(self) -> int:
        _, kb = self._a.get_medical_kb()
        return len(kb)

    def protection_size(self) -> int:
        _, kb = self._a.get_protection_kb()
        return len(kb)
