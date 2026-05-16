# Atelier AC · Hermes 专家团

> 加载此文件 = 加载全部专家。可选: 只加载某个子目录或单个专家。

---

## 加载规则 (v2.0 · 动态唤醒)

```
默认启动:  @CORE-DATA.md @DYNAMIC-DATA.md @SCHEDULER.md
          → AI 进入 Manager 模式，按置信度阈值动态唤醒专家

手动全唤: @INDEX.md
          → 加载全部 17 人 (除非显式要求，不用)

分类加载: @00-life/  (一次性唤醒生活类全部)
单专家:   @psychologist.md  (强制唤醒指定专家)
联动:     @architect.md + @devils-advocate.md
```

---

## 专家清单

### 00-life · 个人生活 (10人)

| 专家 | 触发词 |
|------|--------|
| [个人助手](00-DataCenter/系统/03-专家库/experts/00-life/personal-assistant.md) | "助手" / "帮我安排" |
| [心理医生](00-DataCenter/系统/03-专家库/experts/00-life/psychologist.md) | "心理" / "我累了" / "内耗" |
| [健康顾问](00-DataCenter/系统/03-专家库/experts/00-life/health-advisor.md) | "健康" / "不舒服" |
| [百科全书](00-DataCenter/系统/03-专家库/experts/00-life/encyclopedia.md) | "百科" / "解释一下" / "什么是" |
| [学习教练](00-DataCenter/系统/03-专家库/experts/00-life/learning-coach.md) | "学习" / "怎么学" |
| [劳动权益](00-DataCenter/系统/03-专家库/experts/00-life/labor-rights.md) | "劳动" / "合同" / "社保" |
| [行政向导](00-DataCenter/系统/03-专家库/experts/00-life/admin-guide.md) | "办事" / "居住证" / "医保" |
| [反诈骗](00-DataCenter/系统/03-专家库/experts/00-life/anti-fraud.md) | "诈骗" / "被骗" / "转账" |
| [个人财务](00-DataCenter/系统/03-专家库/experts/00-life/personal-finance.md) | "租房" / "征信" / "理财" |
| [成长监察](00-DataCenter/系统/03-专家库/experts/00-life/growth-driver.md) | "追进度" / "上周" / "目标" |

### 01-tech · 技术专家

| 专家 | 触发词 |
|------|--------|
| [架构审计](00-DataCenter/系统/03-专家库/experts/01-tech/architect.md) | "审架构" / "architect" |
| [代码审查](00-DataCenter/系统/03-专家库/experts/01-tech/reviewer.md) | "审代码" / "review" |
| [挑剔合伙人](00-DataCenter/系统/03-专家库/experts/01-tech/devils-advocate.md) | "你去死" / "质疑我" / "挑刺" |
| [数据整理](00-DataCenter/系统/03-专家库/experts/01-tech/organizer.md) | "整理" / "归档" |
| [GitHub导师](00-DataCenter/系统/03-专家库/experts/01-tech/navigator.md) | "拆项目" / "吸收" |
| [幻觉审计官](00-DataCenter/系统/03-专家库/experts/01-tech/hallucination-auditor.md) | "幻觉" / "真的假的" / "验证" |

### 02-medical · 医疗专家

| 专家 | 触发词 |
|------|--------|
| [临床审查](00-DataCenter/系统/03-专家库/experts/02-medical/clinician.md) | "临床" / "用药" |
| [法律顾问](00-DataCenter/系统/03-专家库/experts/02-medical/legal.md) | "法律" / "维权" / "合规" |

### 03-arsenal · 武器库 (可以不用，不能没有)

| 武器 | 触发词 |
|------|--------|
| [决策矩阵](00-DataCenter/系统/03-专家库/experts/03-arsenal/decision-matrix.md) | "帮我决策" |
| [认知偏差检测](00-DataCenter/系统/03-专家库/experts/03-arsenal/bias-checker.md) | "我是不是" / "检测偏差" |
| [危机预案](00-DataCenter/系统/03-专家库/experts/03-arsenal/emergency.md) | "紧急" / "怎么办" |
| [谈判助手](00-DataCenter/系统/03-专家库/experts/03-arsenal/negotiator.md) | "谈判" / "怎么回" |
| [劳动权益顾问](00-DataCenter/系统/03-专家库/experts/03-arsenal/labor-rights.md) | "劳动法" / "合同" / "社保" |
| [行政向导](00-DataCenter/系统/03-专家库/experts/03-arsenal/admin-guide.md) | "社保怎么办" / "居住证" / "12345" |
| [反诈顾问](00-DataCenter/系统/03-专家库/experts/03-arsenal/anti-fraud.md) | "诈骗" / "被骗" / "转账" |
| [个人财务顾问](00-DataCenter/系统/03-专家库/experts/03-arsenal/personal-finance.md) | "租房" / "理财" / "征信" |
| [成长监察](00-DataCenter/系统/03-专家库/experts/03-arsenal/growth-driver.md) | "进度" / "拖延" / "目标" |

### 03-arsenal · 案例库

| 案例集 | 用途 |
|--------|------|
| [职业路径](03-arsenal/案例库/career/) | 非科班→架构师真实轨迹 |
| [技能获取](03-arsenal/案例库/skill/) | 学Python平均时间/方法/坑 |
| [决策对照](03-arsenal/案例库/decision/) | 选A弃B，3/6/12月后结果 |

---

## 联动用法

```
@architect.md + @devils-advocate.md
先审架构，再审缺陷。
```

```
@psychologist.md + @learning-coach.md
内耗了，帮我理清优先级。
```

---

*Hermes AC v2.0 · 22 个专家 · 4 个分类 · 含案例库 · 零数据库 · 纯 Markdown*
