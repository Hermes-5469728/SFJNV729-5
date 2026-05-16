# 绝对颗粒度评估·抽象层级（克制 vs 过度设计）

过度设计（代码坏味道）:
- 工厂模式滥用: 写ToolFactory支持动态注册，其实只有5个工具
- 配置中心化: 引入Consul/Nacos，其实config.yaml就够了
- 多租户架构: 只有一个人用却设计了租户隔离和权限系统

克制（工业化标志）:
- 硬编码: 原型阶段Prompt/API Key直接写死，跑通再抽离
- 单文件模块: Orchestrator不超过500行就放一个文件
- 特定错误处理: 只捕获预期错误如LLMRateLimitError，不写通用try
