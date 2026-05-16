# Skill库架构与生命周期白皮书

> 版本：v1.0  
> 更新日期：2026-05-12  
> 适用范围：OpenCode Skill管理系统

---

## 目录

1. [目录结构透视](#目录结构透视)
2. [技能生命周期详解](#技能生命周期详解)
3. [权限与控制](#权限与控制)
4. [数据流转机制](#数据流转机制)
5. [创世特权集成](#创世特权集成)

---

## 目录结构透视

### 整体架构树

```
{USER_VAULT}\
├── .trae/                           # Trae配置目录
│   ├── skills/                      # 【活跃技能库】当前可用的技能
│   │   ├── awesome-agent-skills/     # 第三方技能仓库（克隆）
│   │   ├── career-ops/              # 职业运营技能
│   │   ├── chinese-prompts/          # 中文提示词库
│   │   ├── skills.db                # 技能元数据库（SQLite）
│   │   ├── skill_loader.py          # 增强版技能加载器
│   │   └── skill_manager.py         # 技能管理脚本
│   │
│   └── skills_dormant/              # 【休眠技能库】暂时禁用的技能
│       └── [休眠技能目录结构...]
│
├── PersonalDataCenter/              # 个人数据处理中心
│   ├── sdk/                         # 【SDK核心层】受保护的核心数据
│   │   ├── core_data/               # 核心数据（仅创世管理员可写）
│   │   ├── core_backup/             # 核心数据备份（自动生成）
│   │   ├── genesis_manager.py       # 创世特权管理器
│   │   ├── auth_manager.py          # 权限管理器
│   │   └── plugin_manager.py        # 插件管理器
│   │
│   └── data/                        # 【镜像层】开放读取的数据
│       ├── dads_db/                 # DADS数据库镜像（TXT格式）
│       │   ├── drugs.txt            # 药物数据库
│       │   ├── interactions.txt     # 药物相互作用
│       │   ├── guidelines.txt       # 临床指南
│       │   └── safety.txt          # 安全信息
│       └── memory/                  # 记忆存储
│
└── 00-hermes/                       # 架构文档
    ├── ARCHITECTURE-HUMAN.md        # 人话版架构
    └── ARCHITECTURE-MATH.md         # 数学版架构
```

### 目录功能说明

| 目录 | 类型 | 权限 | 说明 |
|------|------|------|------|
| `.trae/skills/` | **活跃技能** | 读取：所有进程<br>写入：需创世管理员 | 当前可用的技能库，包含技能定义、元数据库和加载器 |
| `.trae/skills_dormant/` | **休眠技能** | 读取：所有进程<br>写入：需创世管理员 | 暂时禁用的技能，保留备份可随时唤醒 |
| `PersonalDataCenter/sdk/core_data/` | **SDK核心层** | 读取：所有进程<br>写入：仅创世管理员 | 核心数据存储，落锁后仅创世管理员可修改 |
| `PersonalDataCenter/sdk/core_backup/` | **备份/版本历史** | 读取：所有进程<br>写入：仅创世管理员 | 自动生成的核心数据备份，支持回滚 |
| `PersonalDataCenter/data/` | **镜像层** | 读取：所有进程<br>写入：需创世管理员 | 基于SDK核心层生成的镜像，损坏可一键复原 |

---

## 技能生命周期详解

### 1. 激活态（Active State）

**定义**：技能被加载到镜像层，可供用户直接使用。

**触发条件**：
- 技能文件位于 `.trae/skills/` 目录下
- 数据库中 `enabled = 1` 且 `dormant = 0`
- 技能加载器成功解析并注册

**加载流程**：

```
1. 扫描阶段
   └─> skill_loader.py 扫描 .trae/skills/ 目录
       ├─> 查找 SKILL.md 或 *.md 文件
       └─> 提取 YAML Frontmatter 元数据

2. 解析阶段
   └─> 解析技能定义
       ├─> 提取触发词（triggers）
       ├─> 提取指令（commands）
       └─> 提取真值（truths）

3. 入库阶段
   └─> 存储到 skills.db
       ├─> skills 表：元数据
       ├─> skill_truths 表：真值数据
       └─> skill_execution 表：执行记录

4. 激活阶段
   └─> 技能加载到内存
       ├─> 注册触发词映射
       └─> 准备响应 /skill-name 调用
```

**示例**：

```python
# 用户输入：/grill-me
# 系统响应流程：
1. 检测触发词：/grill-me
2. 查询数据库：SELECT * FROM skills WHERE triggers LIKE '%grill-me%'
3. 加载技能：读取 skill_loader.py 中的 grill-me 技能定义
4. 执行指令：按技能定义的步骤执行
5. 记录日志：INSERT INTO skill_execution ...
```

---

### 2. 休眠态（Dormant State）

**定义**：技能暂时禁用，保留文件但不可调用。

**触发条件**：
- 管理员手动休眠
- 长期未使用（自动休眠策略）
- 功能重复或过时

**休眠机制**：

```
方式一：移动到休眠目录（推荐）
└─> 移动技能文件到 .trae/skills_dormant/
    ├─> 保留原始目录结构
    └─> 数据库标记 dormant = 1

方式二：数据库标记（轻量级）
└─> 仅修改数据库状态
    ├─> UPDATE skills SET dormant = 1 WHERE name = 'xxx'
    └─> 文件仍在原位置，但加载器会跳过
```

**休眠操作示例**：

```python
# 方式一：移动到休眠目录
def move_to_dormant(skill_path):
    rel_path = os.path.relpath(skill_path, '.trae/skills')
    dest_path = os.path.join('.trae/skills_dormant', rel_path)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    shutil.move(skill_path, dest_path)
    
    # 更新数据库
    conn = sqlite3.connect('.trae/skills/skills.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE skills SET dormant = 1 WHERE file_path = ?', (skill_path,))
    conn.commit()
    conn.close()

# 方式二：仅数据库标记
def mark_dormant(skill_name):
    conn = sqlite3.connect('.trae/skills/skills.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE skills SET dormant = 1 WHERE name = ?', (skill_name,))
    conn.commit()
    conn.close()
```

**休眠后状态**：

| 状态 | 文件位置 | 数据库状态 | 可调用性 |
|------|---------|-----------|---------|
| 移动休眠 | `.trae/skills_dormant/` | `dormant = 1` | ❌ 不可调用 |
| 标记休眠 | `.trae/skills/` | `dormant = 1` | ❌ 不可调用 |

---

### 3. 回滚态（Rollback State）

**定义**：当SDK核心层被破坏时，系统利用备份进行复原。

**触发条件**：
- 核心数据损坏或丢失
- 创世管理员手动触发回滚
- 系统检测到数据不一致

**回滚机制**：

```
1. 检测损坏
   └─> 核心层完整性检查
       ├─> 文件存在性检查
       ├─> 数据格式验证
       └─> 签名校验

2. 选择备份
   └─> 从 core_backup/ 选择备份
       ├─> 查找最新备份（backup_YYYYMMDD_HHMMSS）
       ├─> 或指定特定时间戳的备份
       └─> 验证备份完整性

3. 执行回滚
   └─> 恢复核心数据
       ├─> 清空当前 core_data/
       ├─> 从备份复制文件
       └─> 验证恢复结果

4. 重新生成镜像
   └─> 基于恢复的核心数据
       ├─> 清空 data/ 镜像层
       └─> 重新生成镜像文件
```

**回滚操作示例**：

```python
# 创世管理员执行回滚
genesis_manager.restore_sdk_data(
    credential='4039c7f5...',  # 创世管理员凭证
    backup_timestamp='20260512_160134'  # 可选，默认最新备份
)

# 回滚成功后，自动重新生成镜像
genesis_manager.regenerate_mirror(credential='4039c7f5...')
```

**回滚保证**：

- ✅ **原子性**：回滚操作要么全部成功，要么全部失败
- ✅ **可逆性**：回滚前会自动备份当前状态
- ✅ **完整性**：回滚后自动验证数据完整性
- ✅ **镜像同步**：回滚后自动重新生成镜像层

---

## 权限与控制

### 创世管理员特权

作为创世管理员，你拥有以下管理指令：

#### 1. 查看系统状态

```bash
/sdk genesis-status
```

**输出示例**：

```json
{
  "is_vacuum_period": false,
  "is_locked": true,
  "genesis_admin_exists": true,
  "backup_timestamp": "20260512_160134",
  "core_data_count": 12,
  "mirror_data_count": 8
}
```

#### 2. 申请创世管理员身份

```bash
/sdk claim-genesis
```

**说明**：仅在真空期（系统未锁定且无核心数据）时可用。

#### 3. 手动锁定系统

```bash
/sdk lock-system
```

**说明**：锁定后，SDK核心层仅创世管理员可写入。

#### 4. 备份SDK核心数据

```bash
/sdk backup-sdk
```

**说明**：需要创世管理员凭证。

#### 5. 恢复SDK初始数据

```bash
/sdk restore-sdk [timestamp]
```

**说明**：
- 需要创世管理员凭证
- `timestamp` 可选，默认恢复最新备份
- 恢复前会自动备份当前状态

#### 6. 一键复原镜像文件

```bash
/sdk regenerate-mirror
```

**说明**：
- 基于SDK核心数据重新生成镜像层
- 创世管理员可强制执行
- 其他用户需系统未锁定

---

### 技能管理指令

#### 1. 查看所有技能

```bash
/skills list
```

**输出示例**：

```
活跃技能（29个）：
  • diagnose - 诊断技能
  • tdd - 测试驱动开发
  • prototype - 原型设计
  • grill-me - 需求追问
  ...

休眠技能（0个）：
  （无）
```

#### 2. 查看休眠技能列表

```python
# 查询数据库
SELECT name, description, file_path 
FROM skills 
WHERE dormant = 1;
```

#### 3. 强制唤醒休眠技能

```python
# 方式一：从休眠目录移回
def wake_from_dormant(skill_path):
    rel_path = os.path.relpath(skill_path, '.trae/skills_dormant')
    dest_path = os.path.join('.trae/skills', rel_path)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    shutil.move(skill_path, dest_path)
    
    # 更新数据库
    conn = sqlite3.connect('.trae/skills/skills.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE skills SET dormant = 0 WHERE file_path = ?', (skill_path,))
    conn.commit()
    conn.close()

# 方式二：仅数据库标记
def wake_skill(skill_name):
    conn = sqlite3.connect('.trae/skills/skills.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE skills SET dormant = 0 WHERE name = ?', (skill_name,))
    conn.commit()
    conn.close()
```

#### 4. 清理技能缓存

```python
def clear_skill_cache():
    conn = sqlite3.connect('.trae/skills/skills.db')
    cursor = conn.cursor()
    
    # 清理执行记录（保留最近100条）
    cursor.execute('''
        DELETE FROM skill_execution 
        WHERE id NOT IN (
            SELECT id FROM skill_execution 
            ORDER BY timestamp DESC 
            LIMIT 100
        )
    ''')
    
    conn.commit()
    conn.close()
```

---

### 权限检查流程

```
用户请求操作
    ↓
检查资源类型
    ↓
┌─────────────────┬─────────────────┐
│  SDK核心层      │  镜像层          │
│  (sdk:*)        │  (mirror:*)      │
├─────────────────┼─────────────────┤
│ 读取：允许      │ 读取：允许       │
│ 写入：需创世    │ 写入：需创世     │
└─────────────────┴─────────────────┘
    ↓
检查创世管理员凭证
    ↓
┌─────────────────┬─────────────────┐
│  凭证有效       │  凭证无效        │
├─────────────────┼─────────────────┤
│ 允许操作        │ 拒绝操作         │
│ 记录日志        │ 返回错误         │
└─────────────────┴─────────────────┘
```

**权限检查代码示例**：

```python
from sdk.auth_manager import AuthManager
from sdk.genesis_manager import get_genesis_manager

auth_manager = AuthManager()
genesis_manager = get_genesis_manager()

# 检查SDK核心层写入权限
allowed, reason = auth_manager.check_full_permission(
    subject='user1',
    object='sdk:core_data',
    action='write',
    credential=genesis_manager.genesis_admin  # 创世管理员凭证
)

if allowed:
    print("允许写入SDK核心层")
else:
    print(f"拒绝写入：{reason}")
```

---

## 数据流转机制

### 1. 技能数据流

```
┌─────────────────────────────────────────────────────────────┐
│                    技能数据流转                             │
└─────────────────────────────────────────────────────────────┘

[技能定义文件]
    ↓
[skill_loader.py 扫描]
    ↓
[解析 YAML Frontmatter]
    ↓
[提取元数据]
    ├─> name（技能名称）
    ├─> description（描述）
    ├─> triggers（触发词）
    ├─> commands（指令）
    └─> truths（真值）
    ↓
[存储到 skills.db]
    ├─> skills 表（元数据）
    ├─> skill_truths 表（真值）
    └─> skill_execution 表（执行记录）
    ↓
[加载到内存]
    ├─> 注册触发词映射
    └─> 准备响应调用
    ↓
[用户调用 /skill-name]
    ↓
[执行技能指令]
    ↓
[记录执行日志]
```

### 2. SDK核心数据流

```
┌─────────────────────────────────────────────────────────────┐
│                  SDK核心数据流转                             │
└─────────────────────────────────────────────────────────────┘

[创世管理员写入]
    ↓
[权限检查]
    ├─> 创世凭证验证
    └─> 系统锁定状态检查
    ↓
[写入 core_data/]
    ├─> 核心配置文件
    ├─> 技能定义
    └─> 数据模型
    ↓
[自动备份]
    ├─> 创建时间戳备份
    ├─> 保存到 core_backup/
    └─> 更新备份元数据
    ↓
[生成镜像层]
    ├─> 清空 data/
    ├─> 基于核心数据生成镜像
    └─> 创建 TXT/MD 文件
    ↓
[开放读取]
    ├─> 所有进程可读取镜像
    └─> 镜像损坏可一键复原
```

### 3. 数据一致性保证

| 层级 | 数据来源 | 一致性机制 | 恢复方式 |
|------|---------|-----------|---------|
| SDK核心层 | 创世管理员写入 | 写入前自动备份 | 从备份回滚 |
| 备份层 | 自动生成 | 时间戳管理 | 选择历史版本 |
| 镜像层 | 从核心层生成 | 自动同步 | 重新生成镜像 |

**一致性检查**：

```python
def check_data_integrity():
    """检查数据一致性"""
    genesis_manager = get_genesis_manager()
    
    # 1. 检查核心层数据
    core_files = os.listdir(genesis_manager.SDK_CORE_DIR)
    
    # 2. 检查备份层数据
    backup_files = os.listdir(genesis_manager.SDK_BACKUP_DIR)
    
    # 3. 检查镜像层数据
    mirror_files = os.listdir(genesis_manager.MIRROR_DIR)
    
    # 4. 验证一致性
    if len(core_files) == 0 and genesis_manager.is_locked:
        logger.warning("核心层数据为空，可能需要回滚")
        return False
    
    if len(mirror_files) == 0:
        logger.warning("镜像层数据为空，可能需要重新生成")
        return False
    
    return True
```

---

## 创世特权集成

### 初始化流程

```
1. 系统启动
    ↓
2. 检查是否真空期
    ├─> 是：进入创世特权模式
    └─> 否：进入正常运行模式
    ↓
3. 创世特权模式
    ├─> 等待首个安装请求
    ├─> 自动授予创世管理员身份
    └─> 生成唯一凭证
    ↓
4. 初始数据写入
    ├─> 创世管理员写入核心数据
    ├─> 系统自动备份
    └─> 生成镜像层
    ↓
5. 落锁
    ├─> 创世管理员手动或自动落锁
    ├─> 系统锁定
    └─> 后续操作需创世凭证
```

### 权限层次

```
权限层次（从高到低）：

1. 创世管理员（Genesis Admin）
   ├─> SDK核心层：读写
   ├─> 备份层：读写
   ├─> 镜像层：读写
   └─> 系统配置：完全控制

2. 授权用户（Authorized User）
   ├─> SDK核心层：只读
   ├─> 备份层：只读
   ├─> 镜像层：读写（需授权）
   └─> 系统配置：受限

3. 默认用户（Default User）
   ├─> SDK核心层：只读
   ├─> 备份层：只读
   ├─> 镜像层：只读
   └─> 系统配置：无权
```

### 安全机制

| 机制 | 说明 | 实现方式 |
|------|------|---------|
| **凭证验证** | 创世管理员操作需验证凭证 | SHA256哈希 + 时间戳 |
| **系统锁定** | 落锁后核心层仅创世可写 | `.genesis_lock` 文件标记 |
| **自动备份** | 写入前自动备份当前状态 | 时间戳备份目录 |
| **审计日志** | 记录所有关键操作 | `skill_execution` 表 |
| **回滚保护** | 回滚前自动备份当前状态 | 原子性操作 |

---

## 总结

### 核心原则

1. **SDK核心层**：保险箱，创世管理员专属，落锁后仅创世可写
2. **镜像层**：展示台，开放读取，损坏可一键复原
3. **技能生命周期**：激活→休眠→回滚，状态可逆
4. **权限控制**：创世特权优先，分层授权，最小权限原则

### 快速参考

| 操作 | 指令 | 权限要求 |
|------|------|---------|
| 查看系统状态 | `/sdk genesis-status` | 无 |
| 申请创世身份 | `/sdk claim-genesis` | 真空期 |
| 锁定系统 | `/sdk lock-system` | 创世管理员 |
| 备份数据 | `/sdk backup-sdk` | 创世管理员 |
| 恢复数据 | `/sdk restore-sdk` | 创世管理员 |
| 复原镜像 | `/sdk regenerate-mirror` | 创世管理员/未锁定 |
| 查看技能列表 | `/skills list` | 无 |
| 唤醒休眠技能 | 数据库操作 | 创世管理员 |

---

**文档版本**：v1.0  
**最后更新**：2026-05-12  
**维护者**：OpenCode Team