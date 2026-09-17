# Target Profile 1.0

`核心系统/目标规格/` 提供独立规格契约、严格校验、不可变编辑与 JSON 持久化。它不导入插件、workflow、候选库、实验数据、Benchmark 或模型设置；不触发自动注册、启动调度、读取数据库或联网。

当前尚未接 UI、候选过滤/生成、模型调度或 Pareto。以下 role/mode/策略是规格语义和当前校验契约，不表示执行层已实现。

## 中性 JSON 示例

```json
{
  "name": "formulation_screen_v1",
  "target_profile_version": "1.0",
  "criteria": {
    "refractive_index": {
      "role": "objective",
      "scope": "formulation",
      "mode": "target",
      "target": 1.50,
      "tolerance": 0.02,
      "missing_policy": "keep_unknown",
      "evidence_requirement": "measured_or_predicted"
    },
    "viscosity": {
      "role": "objective",
      "scope": "formulation",
      "mode": "minimize",
      "missing_policy": "keep_unknown"
    },
    "water_solubility": {
      "role": "hard_constraint",
      "scope": "molecule",
      "lower": 10,
      "unit": "g/L",
      "missing_policy": "exclude"
    },
    "toxicity": {"role": "report_only", "missing_policy": "keep_unknown"},
    "density": {"role": "disabled", "scope": "formulation"}
  }
}
```

数值仅演示格式，不是经过验证的用途规格或默认搜索需求。名称不参与候选生成、评价或打分，规格不含候选清单、CAS/SMILES、成功标签或 Benchmark。

## 字段与实际校验

- 顶层只接受且必填 name、target_profile_version、criteria；仅支持版本字符串 `1.0`，不自动迁移。
- criteria 是小写 snake_case 指标 ID 到 Criterion 的映射，允许空映射作草稿和扩展 ID；当前不判断该指标是否已有模型，也不允许重名指标。
- scope 允许 molecule/formulation/delivery/experiment；可省略，保持未指定。delivery 是代码允许的通用作用域，不代表当前已有递送模块或递送指标实现。
- 可选字段应省略，不接受 JSON 显式 null。拒绝未知字段、重复键、非法枚举、布尔数值、数值字符串、NaN、Infinity 和溢出数值。
- 启用指标省略 missing_policy 时规范化为 keep_unknown，省略 evidence_requirement 时为 any；这些是配置默认语义，不是填充候选实验数据。
- unit 必须是非空字符串，校验层不推断量纲、不检查单位兼容或换算。没有 weight 或加权总分字段。

| role | 当前配置要求 | 语义与执行边界 |
| --- | --- | --- |
| hard_constraint | 至少 lower/upper 或布尔 equals，二者互斥 | 规格表达硬条件；实际淘汰尚未接入 |
| objective | 必填 mode | 表达比较目标；当前不计算比较向量 |
| report_only | 不接受目标/阈值，只允许 keep_unknown | 表达仅报告，不应改变排名；当前无执行报告适配 |
| disabled | 只接受 role 和可选 scope | 表达禁用；当前不调度模型 |

上下限包含边界且 lower≤upper。equals 只接受布尔值，不能嵌入候选名称或标签。report_only+exclude 是矛盾配置，校验报错。

| objective mode | 字段契约与规格语义 |
| --- | --- |
| minimize/maximize | 不接受 target/tolerance/lower/upper；表达越小/越大越优 |
| target | 必须 target 和非负 tolerance，不接受 lower/upper；表达容差带目标 |
| range | 必须 lower/upper 且有序，不接受 target/tolerance；表达可接受区间 |

目标容差/区间本身不等于硬约束。执行适配未实现，不能另建一套排序系统来假装它已接入。

## 缺失与证据要求

keep_unknown 表达保留未知；exclude 表达缺合格值时排除。当前只保存和校验策略。缺失不得填零、均值或最优值，证据不符合要求不能视为条件通过；缺目标的候选不能伪装完整比较向量混入 Pareto 前沿。

| evidence_requirement | 规格含义 |
| --- | --- |
| measured_only | 只接受实测 |
| measured_or_predicted | 可接受二者，可比条件下优先实测 |
| predicted_allowed | 可接受二者，不额外强制实测优先，不是仅预测 |
| any | 不以类别作门槛，但仍需保留值、单位、来源、条件和未知状态 |

本模块不选择证据，不把数据库 summary 当 measured。将来明确授权执行适配时仍需检验作用域、模型可用性、条件与单位，并沿用现有证据/模型接口；具体接入不属于当前模块实现。

## Python 接口与持久化

```python
from 核心系统.目标规格 import (
    Criterion, TargetProfile, import_profile_json, export_profile_json,
    save_profile, load_profile,
)

profile = TargetProfile("formulation_screen_v1", {})
profile = profile.with_criterion("refractive_index", Criterion(
    role="objective", scope="formulation", mode="target",
    target=1.50, tolerance=0.02,
    evidence_requirement="measured_or_predicted",
))
edited = profile.renamed("formulation_screen_v2")
text = export_profile_json(edited)
assert import_profile_json(text) == edited

# 路径由调用方明确选择，父目录已经存在：
# save_profile(edited, user_selected_path)
# restored = load_profile(user_selected_path)
# save_profile(edited, user_selected_path, overwrite=True)
```

Criterion/TargetProfile 不可变，编辑返回新对象，构造/导入/编辑均校验，to_dict 返回独立副本。JSON 稳定排序、UTF-8，导入兼容 BOM；规范化可加入显式策略，但往返语义一致。

没有默认路径，不把 name 拼成目录，也不创建父目录。只保存 `.json`，默认拒覆盖；显式 overwrite 时在目标目录临时写入并原子替换，失败清理临时文件。内部 JSON 解析辅助函数和临时路径不是其他模块的接口。

## 扩展与验证边界

新增通用指标 ID 可通过现有 Criterion/TargetProfile 表达，不创建平行规格模型。仅有 ID 不代表对应模型存在；不得用研究概念或规格名称自动生成软件需求。

现有测试验证严格契约、JSON 往返、不可变编辑、失败保存、独立导入无写入/联网、旧发现流程前后一致。实际禁用调度、硬约束淘汰、目标进入 Pareto 和 report_only 隔离尚未实现或验收。既有发现流程的比例细化问题不由本模块修复，见 [07](../07_技术债与遗留预留.md)。
