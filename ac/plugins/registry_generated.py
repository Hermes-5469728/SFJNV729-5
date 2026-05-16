# 由 plugins/generate_registry.py 自动生成，勿手动编辑
"""AC Plugin Registry — 所有 55+ 项目的注册入口"""
from plugins.base import ACPlugin, PluginStatus

REGISTRY = {

    "LiteLLM": ACPlugin(name="LiteLLM", port=7500, url="https://github.com/BerriAI/litellm", category="gateway", status=PluginStatus.ACTIVE, layer="①模型层"),
    "Open WebUI": ACPlugin(name="Open WebUI", port=8100, url="https://github.com/open-webui/open-webui", category="frontend", status=PluginStatus.ACTIVE, layer="①模型层"),
    "LocalAI": ACPlugin(name="LocalAI", port=7501, url="https://github.com/localai/localai", category="model", status=PluginStatus.STANDBY, layer="①模型层"),
    "Mem0": ACPlugin(name="Mem0", port=7601, url="https://github.com/mem0ai/mem0", category="memory", status=PluginStatus.ACTIVE, layer="②记忆层"),
    "RAGFlow": ACPlugin(name="RAGFlow", port=7602, url="https://github.com/infiniflow/ragflow", category="knowledge", status=PluginStatus.ACTIVE, layer="②记忆层"),
    "LanceDB": ACPlugin(name="LanceDB", url="https://github.com/lancedb/lancedb", category="vector", status=PluginStatus.ACTIVE, layer="②记忆层"),
    "FastGPT": ACPlugin(name="FastGPT", port=7603, url="https://github.com/labring/FastGPT", category="knowledge", status=PluginStatus.STANDBY, layer="②记忆层"),
    "MaxKB": ACPlugin(name="MaxKB", port=7604, url="https://github.com/1Panel-dev/MaxKB", category="knowledge", status=PluginStatus.STANDBY, layer="②记忆层"),
    "Ruflo": ACPlugin(name="Ruflo", port=7605, url="https://github.com/ruflo-ai/ruflo", category="knowledge", status=PluginStatus.STANDBY, layer="②记忆层"),
    "Dify": ACPlugin(name="Dify", port=8101, url="https://github.com/langgenius/dify", category="llmops", status=PluginStatus.ACTIVE, layer="②记忆层"),
    "MemOS": ACPlugin(name="MemOS", port=8601, category="memory", status=PluginStatus.STANDBY, layer="②记忆层"),
    "open-zk-kb": ACPlugin(name="open-zk-kb", port=8602, category="memory", status=PluginStatus.STANDBY, layer="②记忆层"),
    "kgraph": ACPlugin(name="kgraph", port=8603, category="knowledge", status=PluginStatus.STANDBY, layer="②记忆层"),
    "CrewAI": ACPlugin(name="CrewAI", port=7701, url="https://github.com/crewAIInc/crewAI", category="agent", status=PluginStatus.ACTIVE, layer="③Agent层"),
    "AutoGen": ACPlugin(name="AutoGen", port=7702, url="https://github.com/microsoft/autogen", category="agent", status=PluginStatus.STANDBY, layer="③Agent层"),
    "MetaGPT": ACPlugin(name="MetaGPT", port=7703, url="https://github.com/geekan/MetaGPT", category="agent", status=PluginStatus.STANDBY, layer="③Agent层"),
    "AgentScope": ACPlugin(name="AgentScope", port=7704, url="https://github.com/agentscope-ai/agentscope", category="agent", status=PluginStatus.STANDBY, layer="③Agent层"),
    "OpenCode": ACPlugin(name="OpenCode", port=7801, url="https://github.com/opencode-ai/opencode", category="execution", status=PluginStatus.ACTIVE, layer="④执行层"),
    "Hermes Agent": ACPlugin(name="Hermes Agent", port=7801, url="https://github.com/nousresearch/ac-agent", category="execution", status=PluginStatus.ACTIVE, layer="④执行层"),
    "OpenHands": ACPlugin(name="OpenHands", port=7802, url="https://github.com/All-Hands-AI/OpenHands", category="execution", status=PluginStatus.STANDBY, layer="④执行层"),
    "Continue": ACPlugin(name="Continue", url="https://github.com/continuedev/continue", category="ide", status=PluginStatus.STANDBY, layer="④执行层"),
    "Void IDE": ACPlugin(name="Void IDE", category="ide", status=PluginStatus.STANDBY, layer="④执行层"),
    "Aider": ACPlugin(name="Aider", port=7803, url="https://github.com/paul-gauthier/aider", category="execution", status=PluginStatus.STANDBY, layer="④执行层"),
    "Cline": ACPlugin(name="Cline", category="ide", status=PluginStatus.STANDBY, layer="④执行层"),
    "Roo Cline": ACPlugin(name="Roo Cline", category="ide", status=PluginStatus.STANDBY, layer="④执行层"),
    "DeepSeek-TUI": ACPlugin(name="DeepSeek-TUI", port=7804, category="execution", status=PluginStatus.STANDBY, layer="④执行层"),
    "AutoGenesis": ACPlugin(name="AutoGenesis", port=7805, url="https://github.com/autogenesis-ai/autogenesis", category="execution", status=PluginStatus.STANDBY, layer="④执行层"),
    "LobsterAI": ACPlugin(name="LobsterAI", port=7806, url="https://github.com/netease/lobster-ai", category="execution", status=PluginStatus.STANDBY, layer="④执行层"),
    "DeepAudit": ACPlugin(name="DeepAudit", port=7901, url="https://github.com/lintsinghua/deepaudit", category="audit", status=PluginStatus.ACTIVE, layer="⑤审计层"),
    "TRUST": ACPlugin(name="TRUST", port=7902, category="audit", status=PluginStatus.STANDBY, layer="⑤审计层"),
    "ClawVault": ACPlugin(name="ClawVault", port=8701, category="security", status=PluginStatus.STANDBY, layer="⑤审计层"),
    "PrefixGuard": ACPlugin(name="PrefixGuard", port=8702, category="security", status=PluginStatus.STANDBY, layer="⑤审计层"),
    "KCode": ACPlugin(name="KCode", port=8703, category="security", status=PluginStatus.STANDBY, layer="⑤审计层"),
    "Schemathesis": ACPlugin(name="Schemathesis", category="test", status=PluginStatus.STANDBY, layer="⑤审计层"),
    "TestMaker": ACPlugin(name="TestMaker", port=8802, category="test", status=PluginStatus.STANDBY, layer="⑤审计层"),
    "Autotestplat": ACPlugin(name="Autotestplat", port=8801, url="https://github.com/Autotestplat/Autotestplat", category="test", status=PluginStatus.STANDBY, layer="⑤审计层"),
    "夜莺": ACPlugin(name="夜莺", port=8201, url="https://github.com/ccfos/nightingale", category="monitor", status=PluginStatus.STANDBY, layer="运维"),
    "SigNoz": ACPlugin(name="SigNoz", port=8202, category="monitor", status=PluginStatus.STANDBY, layer="运维"),
    "Prometheus+Grafana": ACPlugin(name="Prometheus+Grafana", port=8203, category="monitor", status=PluginStatus.STANDBY, layer="运维"),
    "Zabbix": ACPlugin(name="Zabbix", port=8205, category="monitor", status=PluginStatus.STANDBY, layer="运维"),
    "Coroot": ACPlugin(name="Coroot", port=8206, category="monitor", status=PluginStatus.STANDBY, layer="运维"),
    "Jenkins": ACPlugin(name="Jenkins", port=8301, url="https://github.com/jenkinsci/jenkins", category="cicd", status=PluginStatus.ACTIVE, layer="运维"),
    "Woodpecker CI": ACPlugin(name="Woodpecker CI", port=8302, category="cicd", status=PluginStatus.ACTIVE, layer="运维"),
    "Forge CI": ACPlugin(name="Forge CI", port=8303, category="cicd", status=PluginStatus.STANDBY, layer="运维"),
    "Coolify": ACPlugin(name="Coolify", port=8304, category="cicd", status=PluginStatus.STANDBY, layer="运维"),
    "Ansible": ACPlugin(name="Ansible", category="cicd", status=PluginStatus.STANDBY, layer="运维"),
    "BuildBot": ACPlugin(name="BuildBot", port=8305, category="cicd", status=PluginStatus.STANDBY, layer="运维"),
    "禅道": ACPlugin(name="禅道", port=8401, url="https://github.com/easysoft/zentaopms", category="pm", status=PluginStatus.STANDBY, layer="运维"),
    "Plane": ACPlugin(name="Plane", port=8402, category="pm", status=PluginStatus.STANDBY, layer="运维"),
    "Taiga": ACPlugin(name="Taiga", port=8403, category="pm", status=PluginStatus.STANDBY, layer="运维"),
    "Huly": ACPlugin(name="Huly", port=8404, category="pm", status=PluginStatus.STANDBY, layer="运维"),
    "Outline": ACPlugin(name="Outline", port=8604, category="pm", status=PluginStatus.STANDBY, layer="运维"),
    "京医千询": ACPlugin(name="京医千询", port=8501, url="https://github.com/BeijingMedicalAI/JingYiQianXun", category="medical", status=PluginStatus.STANDBY, layer="医学"),
    "Janus-Pro-CXR": ACPlugin(name="Janus-Pro-CXR", port=8502, url="https://github.com/wu-lab/Janus-Pro-CXR", category="medical", status=PluginStatus.STANDBY, layer="医学"),
    "iNeuOS_Doctor": ACPlugin(name="iNeuOS_Doctor", port=8503, url="https://github.com/iNeuOS/iNeuOS_Doctor", category="medical", status=PluginStatus.STANDBY, layer="医学"),
    "MedPilot/Mira": ACPlugin(name="MedPilot/Mira", port=8504, category="medical", status=PluginStatus.STANDBY, layer="医学"),
    "PixelDeck": ACPlugin(name="PixelDeck", category="medical", status=PluginStatus.STANDBY, layer="医学"),
    "SegMed": ACPlugin(name="SegMed", category="medical", status=PluginStatus.STANDBY, layer="医学"),

}

def list_active():
    return {k:v for k,v in REGISTRY.items() if v.status == PluginStatus.ACTIVE}

def list_by_layer(layer):
    return {k:v for k,v in REGISTRY.items() if v.layer == layer}

def mount(name):
    p = REGISTRY.get(name)
    if not p: return f"插件 {name} 未注册"
    if p.status == PluginStatus.ACTIVE: return f"{name} 已活跃"
    return p.mount_cmd()

def unmount(name):
    p = REGISTRY.get(name)
    if not p: return f"插件 {name} 未注册"
    if p.status != PluginStatus.ACTIVE: return f"{name} 未在运行"
    return p.unmount_cmd()

def stats():
    active = sum(1 for v in REGISTRY.values() if v.status == PluginStatus.ACTIVE)
    standby = sum(1 for v in REGISTRY.values() if v.status == PluginStatus.STANDBY)
    return f"活跃 {active} | 待命 {standby} | 总计 {len(REGISTRY)}"