"""医疗模块私有配置 · src/modules/medical/config.py"""
from pydantic import BaseModel


class MedicalConfig(BaseModel):
    # 模块名称
    MODULE_NAME: str = "DADS-Medical"
    # DADS 本地数据库路径（离线降级）
    DADS_DB_DIR: str = "dads_db"
    # Gaia 防御管道开关
    GAIA_DEFENSE_ENABLED: bool = True
    # 药物相互作用检测严格度
    INTERACTION_STRICT_MODE: bool = True


medical_config = MedicalConfig()
