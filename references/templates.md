# Templates

## Canonical Paper Note

```markdown
---
tags:
  - paper-note
  - <domain-tag>
  - <year>
  - task-<task-slug>
  - category-<core-or-related>
  - method-<method-slug>
title: "<paper title>"
year: <year>
venue: <venue>
tier: <tier>
subtype: <task subtype>
category: <category>
official_url: <url-or-N/A>
doi: <doi-or-N/A>
reading_status: full-read
evidence_level: full-text
one_sentence: "<this paper does X by Y for Z>"
---

# <paper title>

[[<prefix>-索引|返回总索引]]

## 30秒结论

- 一句话：<this paper does X by Y to solve Z>
- 它和最接近方法的关键区别：<one sentence>
- 它最强的证据：<one sentence>
- 它最大的局限：<one sentence>

## 基本信息

- 作者：待补
- 年份：<year>
- 来源：<venue>
- 质量层级：<tier>
- 分类位置：<core / related / mainlist>
- 任务子类：<subtype>
- 方法标签：<method tags>
- 官方页面：<url>
- PDF：[[assets/paper_pdfs/已入库/<paper>.pdf]]
- 关键图片：![[assets/paper_figures/已入库/<paper>_figure_main.png]]
- 图片说明：<why this image matters>
- 主要实验结果图表（可选）：![[assets/paper_figures/已入库/<paper>_table_main_1.png]]

## 论文原文（内嵌 PDF）

![[assets/paper_pdfs/已入库/<paper>.pdf]]

## 这篇论文到底在解决什么问题

- 任务设置：<classification / generation / retrieval / ...>
- 输入与输出：<what goes in and what comes out>
- 监督 / 训练信号：<labels / pairs / pseudo-labels / reward / none>
- 目标约束：<long-tail / missing modality / open-world / compute budget / ...>

## 背景与问题定义

<what broader problem this paper sits in>

## 动机与 prior work 缺口

<what exact gap the authors think prior work misses>

## 方法总览

<用 4-8 句完整描述整条方法链，而不是一句口号。至少说清：输入是什么、先做什么、核心模块是什么、输出是什么、训练时优化什么。>

## 整体流程

### 训练阶段

1. <step 1>
2. <step 2>
3. <step 3>

### 推理阶段

1. <step 1>
2. <step 2>
3. <step 3>

## 方法总图解读

- 图中左边 / 上半部分在做什么：<explain>
- 图中核心模块在做什么：<explain>
- 图中损失 / 约束在做什么：<explain>
- 这张图为什么足以代表整篇方法：<explain>

## 核心思想拆成大白话

- 如果把整篇方法讲给组内同学听，我会怎么说：<plain-language explanation>
- 它为什么可能有效：<mechanism, not slogan>

## 方法家族定位

<which method family or route this belongs to>

## 关键模块拆解

1. <step/module 1>
2. <step/module 2>
3. <step/module 3>

对每个模块尽量补三件事：

- 它吃什么输入
- 它产出什么中间结果
- 它相对 baseline 多做了什么

## 相对最接近 baseline 的真实改动

- baseline 是什么：<closest baseline>
- 它在 baseline 上加了 / 改了什么：<exact change>
- 哪些看起来新，但本质只是实现细节：<separate novelty from packaging>

## 关键增益点与作用机制

- <gain 1>
- <gain 2>
- 每个 gain 对应解决哪个痛点：<map gains to problems>

## 核心公式

<only the formulas worth remembering>

## 公式如何理解

- <reading hint 1>
- <reading hint 2>

## 实验设置

- 数据集：<datasets>
- 指标：<metrics>
- 对比方法：<main baselines>
- 最关键的 setting：<e.g. imbalance factor / missing ratio / shot split / compute budget>

## 实验与结果

<不要只列数据集。明确写出“它比谁强、强在哪、强多少、大致在哪些设置下最明显”。>

### 主要实验结果图表（可选）

![[assets/paper_figures/已入库/<paper>_table_main_1.png]]

## 最强证据是什么，为什么我相信它

- 主结果：<one sentence>
- 最能支撑 claim 的实验：<one sentence>
- 还不够充分的地方：<one sentence>

## 失败点、代价与局限

- 失败场景 / 不稳定点：<failure modes>
- 额外代价：<compute / memory / annotation / tuning>
- 作者没讲清但你需要警惕的点：<your judgment>

## 结论

<what the paper is worth remembering for>

## 我会怎么向别人复述这篇论文

<2-4 句话，把它讲成口头报告版，而不是摘抄版。>

## 与当前项目的相关性

<why this belongs in the current knowledge base>

## 证据边界与后续补强

- 已从全文确认：<what was verified from full text>
- 仍需复核：<what still needs deeper reading>
- 当前笔记属于：<triage / partial / mature>
```

## Triage Paper Note

```markdown
---
tags:
  - paper-note
  - triage-note
  - <prefix>
title: "<paper title>"
year: <year-or-N/A>
venue: <venue-or-N/A>
tier: pending
subtype: <core-or-bridge>
category: pending
official_url: <url-or-N/A>
doi: <doi-or-N/A>
reading_status: pdf-downloaded / metadata-only
evidence_level: pdf-available / metadata-only
one_sentence: "<paper title> | pending triage"
---

# <paper title>

[[<prefix>-待处理清单|返回待处理清单]]
[[<prefix>-索引|返回总索引]]

## 当前状态

- 分类：<core / bridge>
- 分数：<score>
- 检索来源：<arxiv / dblp / crossref>
- 命中查询：<queries>

## 外部入口

- 官方页面：<url>
- 在线 PDF：<pdf-url-or-N/A>
- 本地 PDF：[[assets/paper_pdfs/待处理/<paper>.pdf]]

## 论文原文（内嵌 PDF）

![[assets/paper_pdfs/待处理/<paper>.pdf]]

## 读这篇时优先确认什么

- 它到底解决什么任务设置
- 它相对最近 baseline 的真实改动
- 训练和推理流程是否真的和 claim 对应
- 最强证据是否足够支撑作者结论

## 当前摘录

- 摘要要点：待补
- 方法主线：待补
- 主结果：待补
- 最大疑问：待补
```

## Track Page Template

```markdown
---
tags:
  - index
  - <prefix>
  - <track-slug>
---

# <title> 子任务清单 [[<prefix>-索引|返回总索引]]

> 纯索引页，只保留该子任务的分组、入口和待补清单。

## 快速入口

- 代表论文：待补
- 桥接 / 强相关：待补

## 推荐阅读路径

1. 待补

## 核心主线

- 待补

## 桥接 / 强相关

- 待补

## 待补条目

- 待补
```

## Quality Checklist

写完一篇成熟笔记后，至少检查下面几项：

- 所有占位文字都被替换掉
- 作者、来源、层级、任务子类都已填写
- `30秒结论` 不是空的，且不是换皮摘要
- 看这篇笔记的人不打开 PDF 也能说清：问题、方法、训练 / 推理流程、最强结果、最大局限
- `一篇论文到底做了什么` 用自己的话写清了，不是贴作者原句
- `相对最接近 baseline 的真实改动` 写清了，不把包装当创新
- `实验与结果` 写了结论，不只是罗列数据集和指标
- `论文原文（内嵌 PDF）` 可以直接在笔记里打开，而不是只留外链
- PDF 和关键图至少补齐其一，最好两者都有
- 如果保留了结果表截图，裁剪区域不能接近整页；接近整页时改用手工 bbox 重做
- 章节顺序保持稳定，不要随意改名
- `与当前项目的相关性` 不是空话
- `证据边界与后续补强` 明确说明目前掌握到什么程度
