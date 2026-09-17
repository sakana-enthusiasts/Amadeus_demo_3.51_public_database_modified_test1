"""只读取已组装配方的预测物性；不接受论文参照或论文候选分数。"""

from math import isfinite
from 插件.插件接口 import 基础插件接口
from 插件.配方物性.配方物性接口 import 有限数


class 配方候选排序插件(基础插件接口):
    插件标识 = "配方候选排序"

    def 执行(self, 数据上下文):
        目标 = 有限数(数据上下文["目标折射率"], "目标折射率", 最小=1)
        n = 数据上下文.get("返回数量", 8)
        if isinstance(n, bool) or not isinstance(n, int) or not 5 <= n <= 10:
            raise ValueError("返回数量须为5–10的整数")
        目标们 = 数据上下文.get("优化目标") or {"RI目标差": "最小", "混合黏度": "最小"}
        可选 = {"RI目标差", "混合黏度", "渗透压", "水活度", "溶液自由扩散系数", "成本_元_kg", "局部细胞存活率_pct"}
        if set(目标们) - 可选 or any(v not in {"最小", "最大"} for v in 目标们.values()):
            raise ValueError("优化目标或方向无效")
        可用, 排除 = [], []
        for 配方 in 数据上下文["预测配方"]:
            物性 = 配方["配方物性"]
            ri, eta = (物性[x]["值"] for x in ("混合折射率", "混合黏度"))
            if not 配方.get("可参与排序", True):
                排除.append({"配方编号": 配方["配方编号"], "原因": "违反约束或严格模式缺证据", "配方": 配方})
                continue
            if ri is None or eta is None or not all(isfinite(x) for x in (ri, eta)):
                排除.append({"配方编号": 配方["配方编号"], "原因": "缺少可比较的RI或黏度", "配方": 配方})
                continue
            指标值 = {k: v["值"] for k, v in 物性.items()} | {"RI目标差": abs(ri-目标),
                "成本_元_kg": 配方.get("成本_元_kg"), "局部细胞存活率_pct": 配方.get("局部细胞存活率_pct")}
            if any(指标值[k] is None or not isfinite(指标值[k]) for k in 目标们):
                排除.append({"配方编号": 配方["配方编号"], "原因": "优化目标缺少数值，未用有利数填空", "配方": 配方})
                continue
            向量 = tuple(指标值[k] * (1 if v == "最小" else -1) for k, v in 目标们.items())
            可用.append({"配方": 配方, "RI差": abs(ri - 目标), "黏度": eta, "向量": 向量})
        # 字典序保证支配者在前，逐项计算非支配层，避免逐层三次方枚举。
        可用.sort(key=lambda a: (a["向量"], a["配方"]["配方编号"]))
        for i, a in enumerate(可用):
            a["层"] = 1 + max((b["层"] for b in 可用[:i] if b["向量"] != a["向量"] and
                                  all(x <= y for x, y in zip(b["向量"], a["向量"]))), default=0)
        可用.sort(key=lambda a: (a["层"], a["RI差"], a["黏度"], a["配方"]["配方编号"]))
        全排序 = [a["配方"] | {"非支配层": a["层"], "目标RI差": a["RI差"],
                  "推荐原因": f"已选目标非支配层{a['层']}；距目标RI {a['RI差']:.4f}，预测黏度 {a['黏度']:.4g} mPa·s；{a['配方'].get('约束状态', '证据待补')}",
                  "适用结论": "探索候选；不得将物性排序等同于局部递送或安全性排名"} for a in 可用]
        return {"候选": 全排序[:n], "Pareto前沿": [x for x in 全排序 if x["非支配层"] == 1],
                "排序总数": len(全排序), "排除": 排除,
                "排序规则": {"优化目标": 目标们, "层内次序": "RI目标差、黏度、稳定编号；不使用参考体系"}}
