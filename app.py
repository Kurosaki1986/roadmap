import streamlit as st
import pandas as pd
import altair as alt
import json
import openai

from emission_calc import calculate_emission_scenario
from prompt_roadmap import ROADMAP_SYSTEM_PROMPT

# --------------------------------------------------
# OpenAI 設定
# --------------------------------------------------
openai.api_key = st.secrets["OPENAI_API_KEY"]
client = openai.OpenAI()

# --------------------------------------------------
# ページ設定
# --------------------------------------------------
st.set_page_config(page_title="簡易 脱炭素ロードマップ生成", layout="wide")
st.title("簡易脱炭素ロードマップ生成")

# --------------------------------------------------
# 企業情報入力
# --------------------------------------------------
st.header("企業情報の入力")

col1, col2 = st.columns(2)

with col1:
    industry = st.selectbox(
        "業種（単一選択）",
        [
            "製造",
            "金属加工",
            "化学",
            "食品",
            "建設",
            "物流",
            "小売",
            "飲食",
            "情報通信",
            "金融",
            "その他",
        ],
    )

    employees = st.selectbox(
        "従業員規模（単一選択）",
        [
            "1〜50名",
            "51〜100名",
            "101〜150名",
            "151〜200名",
            "201〜300名",
            "301〜400名",
            "401〜500名",
        ],
    )

    baseline_year = st.selectbox(
        "基準年",
        [2020, 2021, 2022, 2023, 2024, 2025]
    )

    scope1 = st.number_input("Scope1排出量（t-CO₂e）", min_value=0.0, step=10.0)
    scope2 = st.number_input("Scope2排出量（t-CO₂e）", min_value=0.0, step=10.0)

with col2:
    emission_sources = st.multiselect(
        "排出源（複数選択可）",
        ["ガス", "ガソリン", "軽油", "灯油", "電気"],
    )

    equipment_options = [
        "給湯",
        "ガソリン車",
        "ディーゼル車",
        "フォークリフト",
        "ガスボイラー",
        "灯油ボイラー",
        "ディーゼル発電機",
        "コンプレッサー",
        "プレス機",
        "照明設備",
        "空調設備",
        "製造・加工設備",
        "冷凍・冷蔵設備",
    ]
    emission_equipments = st.multiselect("排出源となる設備（複数選択可）", equipment_options)

    is_saving_law = st.selectbox(
        "省エネ法の特定事業者に該当しますか？",
        ["いいえ", "はい", "不明"],
    )

    emission_profile = st.selectbox(
        "排出構造の特徴（最も近いものを選択）",
        [
            "燃料依存型（Scope1が中心）",
            "電力依存型（Scope2が中心）",
            "混合型（両方同程度）",
            "事業量変動が大きい",
        ],
    )

add_info = st.text_area("追加情報（任意）")

# --------------------------------------------------
# 排出量シナリオ
# --------------------------------------------------
st.header("排出量シナリオ（現状 vs 削減）")

col3, col4, col5 = st.columns(3)
with col3:
    growth_rate = st.number_input("事業成長率（年率 %）", -10.0, 20.0, 0.0)
with col4:
    reduction_rate = st.number_input("目標削減率（%）", 0.0, 100.0, 50.0)
with col5:
    years = st.number_input("目標までの年数（年）", 1, 30, 5)

if st.button("排出量シナリオ計算"):
    df = calculate_emission_scenario(scope1, scope2, growth_rate, reduction_rate, years)
    df["年"] = df["年"].apply(lambda x: baseline_year + x)
    st.session_state["scenario_df"] = df

# --------------------------------------------------
# シナリオ表示
# --------------------------------------------------
if "scenario_df" in st.session_state:
    df = st.session_state["scenario_df"]

    display_df = df.rename(
        columns={
            "BAU排出量(t-CO2e)": "現状シナリオ(t-CO₂e)",
            "計画排出量(t-CO2e)": "削減シナリオ(t-CO₂e)",
        }
    )

    # 数値フォーマット
    formatted_df = display_df.copy()
    formatted_df["年"] = formatted_df["年"].astype(int)
    for col in formatted_df.columns:
        if col != "年":
            formatted_df[col] = formatted_df[col].map(lambda x: f"{x:.2f}")

    st.markdown("### 排出量シナリオ一覧")

    # HTML生成（行頭スペースなし）
    html_table = formatted_df.to_html(index=False, escape=False)

    html_output = f"""
<style>
table {{
    font-size: 16px;
    width: 100%;
    border-collapse: collapse;
}}
th {{
    text-align: center;
    padding: 6px 10px;
}}
td {{
    text-align: right;
    padding: 6px 10px;
}}
</style>
{html_table}
"""

    st.markdown(html_output, unsafe_allow_html=True)

    # グラフ
    chart_df = pd.DataFrame(
        {
            "年": list(df["年"]) * 2,
            "シナリオ": ["現状シナリオ"] * len(df) + ["削減シナリオ"] * len(df),
            "排出量(t-CO₂e)": list(df["BAU排出量(t-CO2e)"]) + list(df["計画排出量(t-CO2e)"]),
        }
    )

    y_max = chart_df["排出量(t-CO₂e)"].max() * 1.1

    chart = (
        alt.Chart(chart_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("年:O", title="年", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("排出量(t-CO₂e):Q", title="排出量（t-CO₂e）", scale=alt.Scale(domain=[0, y_max])),
            color=alt.Color("シナリオ:N", title="シナリオ"),
            tooltip=["年", "シナリオ", "排出量(t-CO₂e)"],
        )
        .properties(title="現状シナリオ vs 削減シナリオの排出量推移")
    )
    st.altair_chart(chart, use_container_width=True)

else:
    st.info("まず排出量シナリオを計算してください。")

# --------------------------------------------------
# 脱炭素ロードマップの生成
# --------------------------------------------------
st.header("脱炭素ロードマップの生成")

# 初期化（未定義回避）
if "roadmap_md" not in st.session_state:
    st.session_state["roadmap_md"] = None

if st.button("ロードマップ生成"):

    if "scenario_df" not in st.session_state:
        st.error("先に排出量シナリオを計算してください。")
        st.stop()

    scenario_records = st.session_state["scenario_df"].to_dict(orient="records")

    payload = {
        "industry": industry,
        "employees": employees,
        "baseline_year": baseline_year,
        "target_years": years,
        "scope1_tco2": scope1,
        "scope2_tco2": scope2,
        "additional_info": add_info,
        "scenario": scenario_records,
        "emission_sources": emission_sources,
        "emission_equipments": emission_equipments,
        "saving_law": is_saving_law,
        "emission_profile": emission_profile,
    }

    user_prompt = json.dumps(payload, ensure_ascii=False)

    with st.spinner("ロードマップを生成中..."):
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": ROADMAP_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )

    st.session_state["roadmap_md"] = response.choices[0].message.content

# 生成済みなら常に表示（ここが重要）
if st.session_state["roadmap_md"]:
    st.markdown("## 生成されたロードマップ")
    st.markdown(st.session_state["roadmap_md"])

    st.download_button(
        "ロードマップをダウンロード（txt）",
        st.session_state["roadmap_md"],
        "roadmap.txt",
    )

