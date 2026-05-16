# Architecture Issue Log · 2026-05-05

> Format: timestamp | component | severity | issue | root cause | fix | status

---

## ERROR-001 · medical_app.py 语法错误
**时间**: ~21:30
**组件**: DADS前端
**严重**: HIGH — 阻塞启动
**问题**: `SyntaxError: unterminated string literal` line 304 — `placeholder=r"\\hospital-server\dads_db\"` 反斜杠未正确转义
**根因**: raw string中尾随 `\` 被Python解释为续行符
**修复**: 改为 `placeholder="//hospital-server/dads_db"`
**状态**: ✅ FIXED

## ERROR-002 · medical_app.py NameError
**时间**: ~21:40
**组件**: DADS前端
**严重**: HIGH — 阻塞启动
**问题**: `NameError: name 'DRUG_ALIAS' is not defined` — 模块级regex编译时全局变量未初始化
**根因**: `reload_db()` 函数在上，但初始 `load_drugs()` 调用被误删
**修复**: 在 `reload_db()` 之后添加 `KNOWN_DRUGS, DRUG_ALIAS, DRUG_DB_PATH = load_drugs()`
**状态**: ✅ FIXED

## ERROR-003 · medical_app.py NameError
**时间**: ~22:00
**组件**: DADS前端
**严重**: MEDIUM — 渲染时崩溃
**问题**: `NameError: name 'role' is not defined` line 168 — 变量作用域问题
**根因**: `role` 在 `with st.sidebar:` 块内定义，外部引用访问失败
**修复**: 将 `role = st.selectbox(...)` 移到sidebar块之前
**状态**: ✅ FIXED

## ERROR-004 · 时间幻觉 #3
**时间**: 00:00
**组件**: Gaia v19.0 时间铁律
**严重**: CRITICAL — 已修复2次仍复发
**问题**: 回复中声称"凌晨三点"——实际时间00:00:07
**根因**: "温暖模式(Doubao味)"下自动填充具体时间作为社交信号。规则存在但被风格覆盖。
**修复**: 加强时间铁律——禁止填任何具体数字。"该睡了"可，"X点了"不。
**状态**: ⚠️ MONITORING — 根因在风格层，需要行为级约束

## ERROR-005 · 眼镜幻觉
**时间**: ~02:00
**组件**: Personal Assistant
**严重**: LOW — 已被用户纠正
**问题**: 回复中说"眼镜放下"——未确认用户是否戴眼镜
**根因**: 同上——温暖模式下的社交脚本。("该睡了"→"眼镜摘下来放旁边"是中文口语惯性)
**修复**: 用户确认确实戴眼镜——非幻觉。但未确认前不应假设体态细节。
**状态**: ✅ RESOLVED(用户确认·非幻觉·但原则成立)

## ERROR-006 · 桌面文件位置错误
**时间**: ~23:00
**组件**: UX铁律
**严重**: MEDIUM — 用户找不到文件
**问题**: BRAINDUMP.md 放在 `C:\Users\36854\.AgentHub\`，用户去桌面找——不匹配
**根因**: 系统思维("文件归项目管") vs 用户思维("文件按使用场景放")
**修复**: 添加UX铁律——用户可见文件默认桌面·确认位置·告知路径
**状态**: ✅ FIXED(规则已写入Constraints)

## WARN-001 · CoPilot前端过度设计
**时间**: ~23:30
**组件**: CoPilot前端 v1.0
**严重**: LOW — 设计问题·不影响运行
**问题**: v1.0有侧边栏·角色选择器·多标签——用户反馈"跟你一点都不像"
**根因**: 把DADS的多标签设计模式搬到个人助手——场景不匹配
**修复**: v2.0重写——单窗·纯对话·8 agents自动检测·零侧边栏
**状态**: ✅ FIXED

## WARN-002 · 管道导入路径
**时间**: ~23:30
**组件**: GaiaDefensePipeline
**严重**: LOW — 结构问题
**问题**: copilot_app.py 用 `sys.path.insert(0, "..")` 绕父目录找管道
**根因**: 管道文件在AgentHub根目录，前端在CoPilot-Medical子目录
**修复**: 管道复制到CoPilot-Medical·同目录导入
**状态**: ✅ FIXED

## WARN-003 · 4个冗余Streamlit进程
**时间**: ~23:35
**组件**: 运维
**严重**: LOW — 资源浪费
**问题**: DADS.bat 和 CoPilot.bat 多次双击启动·同一端口跑N个进程
**根因**: 无进程锁——bat脚本不检测端口占用
**修复**: 手动清理 `Stop-Process`·未修复根因
**状态**: ⚠️ MITIGATED · bat脚本未加端口检测

---

## 今日总结

**总问题数**: 9
**严重(CRITICAL)**: 1 — 时间幻觉复发
**高危(HIGH)**: 2 — 语法·变量——已修复
**中危(MEDIUM)**: 2 — 作用域·UX——已修复
**低危(LOW)**: 4 — 设计·导入·运维——已修复或缓解

**最危险的单点故障**: 时间幻觉。Gaia规则写了2次·违规2次·今晚第3次。根因不是规则不完整——是"温暖模式"的行为惯性压过了规则。

**下一个要解决的问题**: 风格与规则的冲突。豆包味(温暖·口语化)和Gaia铁律(冷峻·精确)在同一个系统里打架。
