import pandas as pd

def calculate_emission_scenario(scope1, scope2, growth_rate, reduction_rate, years):
    """
    scope1, scope2 : 基準年の排出量
    growth_rate    : 事業成長率（%）
    reduction_rate : ターゲット年の削減率（%）
    years          : ターゲットまでの年数
    """

    base = scope1 + scope2
    growth = growth_rate / 100
    final_reduction = reduction_rate / 100  # 例：40% → 0.40

    rows = []

    for t in range(years + 1):
        # ---- BAU排出量（事業成長のみ反映） ----
        bau = base * ((1 + growth) ** t)

        # ---- 削減率の計算（線形に増加） ----
        # 基準年(0年目)=0%削減、ターゲット年(years)=final_reduction
        reduction_t = final_reduction * (t / years)

        # ---- 削減シナリオ排出量 ----
        plan = bau * (1 - reduction_t)

        rows.append({
            "年": t,
            "BAU排出量(t-CO2e)": bau,
            "計画排出量(t-CO2e)": plan,
            "削減率(%)": reduction_t * 100
        })

    df = pd.DataFrame(rows)
    return df
