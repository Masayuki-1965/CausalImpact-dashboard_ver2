import streamlit as st
import pandas as pd
import os
import glob
import plotly.express as px

# --- 画面幅を最大化 ---
st.set_page_config(layout="wide")

# --- カスタムCSS（全体の余白・フォント・配色・テイスト調整） ---
st.markdown("""
<style>
body, .main, .block-container {
    background-color: #f7fafd !important;
    font-family: 'Noto Sans JP', 'Meiryo', sans-serif;
}
.big-title {
    font-size:3.2em;
    font-weight:900;
    color:#1565c0;
    margin-bottom:0.1em;
    letter-spacing: 0.04em;
    text-shadow: 0 2px 8px #e3e8ee33;
    line-height:1.1;
}
.sub-title {
    font-size:1.15em;
    color:#1976d2;
    margin-bottom:1.2em;
    font-weight:500;
}
.card {
    background: #fff;
    border-radius: 12px;
    padding: 1.1em 1.5em;
    margin-bottom: 1.1em;
    border: 1.5px solid #e3e8ee;
    box-shadow: 0 2px 12px #e3e8ee55;
}
.section-title {
    font-size: 1.18em;
    font-weight: bold;
    color: #1976d2;
    margin-bottom: 0.5em;
    margin-top: 0.5em;
}
.stButton>button {
    background: #1976d2;
    color: #fff;
    font-weight: bold;
    font-size: 1.1em;
    border-radius: 8px;
    padding: 0.5em 2em;
    margin: 0.5em 0;
    box-shadow: 0 2px 8px #e3e8ee33;
}
.stButton>button:hover {
    background: #1565c0;
}
.stDataFrame, .stTable {
    font-size: 1.05em;
}
hr {
    border: none;
    border-top: 2px solid #e3e8ee;
    margin: 1.2em 0;
}
.sidebar-card {
    background: #fff;
    border-radius: 12px;
    padding: 1.1em 1.1em 1.1em 1.1em;
    margin-bottom: 1.1em;
    border: 1.5px solid #e3e8ee;
    box-shadow: 0 2px 8px #e3e8ee33;
}
.sidebar-step {
    font-size:1.1em;
    font-weight:bold;
    display:block;
    margin-bottom:0.7em;
}
.sidebar-step-active {
    background:#e3f2fd;
    color:#1976d2;
    border-radius:8px;
    padding:0.3em 1.2em;
    margin-bottom:0.5em;
    display:inline-block;
}
.sidebar-step-inactive {
    background:#f5f5f5;
    color:#90a4ae;
    border-radius:8px;
    padding:0.3em 1.2em;
    margin-bottom:0.5em;
    display:inline-block;
}
.sidebar-faq-title {
    font-size:1.05em;
    font-weight:bold;
    color:#1976d2;
    margin-bottom:0.3em;
}
.sidebar-faq-body {
    background:#f4f8fd;
    border-radius:8px;
    padding:1em 1.2em;
    color:#333;
    font-size:0.98em;
}
</style>
""", unsafe_allow_html=True)

# --- サイドバー ---
with st.sidebar:
    st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
    st.markdown('<span style="font-size:1.25em;font-weight:bold;color:#1976d2;">分析フロー</span>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.98em;color:#333;margin-bottom:0.7em;">Causal Impact分析は以下の<b>3つのステップ</b>で行います。各ステップのコンテンツはメイン画面に表示されます。</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="margin-top:0.2em;">
        <span class="sidebar-step sidebar-step-active">STEP 1：データ取り込み／可視化</span><br>
        <span class="sidebar-step sidebar-step-inactive">STEP 2：分析期間／モデル設定</span><br>
        <span class="sidebar-step sidebar-step-inactive">STEP 3：分析実行／結果確認</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
    with st.expander("Causal Impactとは？", expanded=False):
        st.markdown("""
<div class="sidebar-faq-title">Causal Impactとは？</div>
<div class="sidebar-faq-body">
<b>Causal Impactは、介入（施策）の効果を測定するための統計手法です。</b><br><br>
介入前のデータから予測モデルを構築し、介入がなかった場合の予測値と実際の値を比較することで、介入の効果を推定します。
</div>
""", unsafe_allow_html=True)
    with st.expander("処置群と対照群について", expanded=False):
        st.markdown("""
<div class="sidebar-faq-title">処置群と対照群について</div>
<div class="sidebar-faq-body">
<b>処置群</b>は、施策（介入）の影響を受けたグループです。<br>
<b>対照群</b>は、施策の影響を受けていないグループであり、比較対象となります。
</div>
""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- メインコンテンツ ---
st.markdown("""
<div class="big-title">Causal Impact 分析</div>
<div class="sub-title">施策効果を測定し、可視化するシンプルな分析ツール</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="card" style="background:#e3f2fd;">
    <span style="font-size:1.18em;font-weight:bold;color:#1976d2;">STEP 1：データ取り込み／可視化</span><br>
    <span style="color:#1976d2;">このステップでは、分析に必要な時系列データを読み込み、可視化します。処置群（効果を測定したい対象）と対照群（比較対象）のデータをCSVファイルから取り込み、分析用データセットを作成します。</span>
</div>
""", unsafe_allow_html=True)

# --- データ形式ガイド ---
with st.expander("データ形式ガイド", expanded=True):
    st.markdown("""
<span style="font-size:1.1em;font-weight:bold;color:#1976d2;">CSVファイルの要件</span><br>
CSVファイルには、<b>ymd（日付）</b> と <b>qty（数量）</b> の2つのカラムが必須です。

<div style="display:flex;gap:2em;">
<div>
<b>基本レイアウト</b>
<table style="border-collapse:collapse;">
<tr><th style="border:1px solid #e3e8ee;padding:4px 12px;">ymd</th><th style="border:1px solid #e3e8ee;padding:4px 12px;">qty</th></tr>
<tr><td style="border:1px solid #e3e8ee;padding:4px 12px;">20170403</td><td style="border:1px solid #e3e8ee;padding:4px 12px;">29</td></tr>
<tr><td style="border:1px solid #e3e8ee;padding:4px 12px;">20170425</td><td style="border:1px solid #e3e8ee;padding:4px 12px;">24</td></tr>
<tr><td style="border:1px solid #e3e8ee;padding:4px 12px;">20170426</td><td style="border:1px solid #e3e8ee;padding:4px 12px;">23</td></tr>
</table>
</div>
<div>
<b>追加カラムがある場合の例</b>
<table style="border-collapse:collapse;">
<tr><th style="border:1px solid #e3e8ee;padding:4px 12px;">product_category</th><th style="border:1px solid #e3e8ee;padding:4px 12px;">ymd</th><th style="border:1px solid #e3e8ee;padding:4px 12px;">qty</th></tr>
<tr><td style="border:1px solid #e3e8ee;padding:4px 12px;">サンジョ3</td><td style="border:1px solid #e3e8ee;padding:4px 12px;">20170403</td><td style="border:1px solid #e3e8ee;padding:4px 12px;">29</td></tr>
<tr><td style="border:1px solid #e3e8ee;padding:4px 12px;">サンジョ3</td><td style="border:1px solid #e3e8ee;padding:4px 12px;">20170425</td><td style="border:1px solid #e3e8ee;padding:4px 12px;">24</td></tr>
</table>
</div>
</div>

<ul style="margin-top:1em;">
<li><b>ymd：</b>日付（YYYYMMDD形式の整数や文字列）</li>
<li><b>qty：</b>数量（整数または小数）</li>
</ul>
上記以外のカラムは自由に追加できます。なくても問題ありません。
""", unsafe_allow_html=True)

# --- データ取り込みガイド ---
st.markdown('<div class="section-title">データ取り込み</div>', unsafe_allow_html=True)
st.markdown("""
<div class="card" style="background:#f4f8fd;">
<b>データファイルの保管場所</b><br>
<ul>
<li>処置群データ：<span style="background:#e3f2fd;padding:2px 8px;border-radius:6px;">data/treatment_data/</span> フォルダ</li>
<li>対照群データ：<span style="background:#e3f2fd;padding:2px 8px;border-radius:6px;">data/control_data/</span> フォルダ</li>
</ul>
処置群と対照群それぞれのCSVデータファイルを、上記の専用フォルダに保存してください（複数ファイル保存可）<br>
CSVファイルの名称を製品名・品種名などに設定すると、処置群・対照群の名称として表示されます（日本語表記も可）<br>
フォルダ内に複数のCSVファイルを保存しておくと、「データ選択」メニューから対象ファイルを選択できます。
</div>
""", unsafe_allow_html=True)

# --- ファイル選択UI ---
treatment_dir = "data/treatment_data"
control_dir = "data/control_data"

def get_csv_files(directory):
    files = glob.glob(os.path.join(directory, "*.csv"))
    return [os.path.basename(f) for f in files]

treatment_files = get_csv_files(treatment_dir)
control_files = get_csv_files(control_dir)

col1, col2 = st.columns(2)
with col1:
    treatment_file = st.selectbox("処置群ファイル", treatment_files, key="treat")
with col2:
    control_file = st.selectbox("対照群ファイル", control_files, key="ctrl")

# --- データ読み込みボタン ---
read_btn = st.button("データを読み込む", key="read", help="選択したファイルを読み込みます。", type="primary")

if read_btn:
    treatment_path = os.path.join(treatment_dir, treatment_file)
    control_path = os.path.join(control_dir, control_file)
    df_treat = pd.read_csv(treatment_path)
    df_ctrl = pd.read_csv(control_path)

    st.success("データを読み込みました。下記にプレビューと統計情報を表示します。")

    # --- データプレビュー ---
    st.markdown('<div class="section-title">読み込みデータのプレビュー（上位10件）</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**処置群（{treatment_file}）**")
        st.dataframe(df_treat.head(10), use_container_width=True)
    with col2:
        st.markdown(f"**対照群（{control_file}）**")
        st.dataframe(df_ctrl.head(10), use_container_width=True)

    # --- 統計情報 ---
    st.markdown('<div class="section-title">データの統計情報</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**処置群（{treatment_file}）**")
        st.dataframe(df_treat.describe(), use_container_width=True)
    with col2:
        st.markdown(f"**対照群（{control_file}）**")
        st.dataframe(df_ctrl.describe(), use_container_width=True)

    # --- 日付をdatetime型に変換 ---
    df_treat['ymd'] = pd.to_datetime(df_treat['ymd'])
    df_ctrl['ymd'] = pd.to_datetime(df_ctrl['ymd'])

    # --- 時系列プロット ---
    st.markdown('<div class="section-title">時系列プロット</div>', unsafe_allow_html=True)
    fig = px.line()
    fig.add_scatter(x=df_treat['ymd'], y=df_treat['qty'], name=f"処置群（{treatment_file}）", line=dict(color="#1976d2"))
    fig.add_scatter(x=df_ctrl['ymd'], y=df_ctrl['qty'], name=f"対照群（{control_file}）", line=dict(color="#ef5350"))
    fig.update_layout(xaxis_title="日付", yaxis_title="数量", legend_title_text="グループ")
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Plotlyインタラクティブグラフの使い方ガイド"):
        st.markdown("""
- **データ確認**：グラフ上の線やポイントにマウスを置くと、詳細値がポップアップ表示されます
- **拡大表示**：見たい期間をドラッグして範囲選択すると拡大表示されます
- **表示移動**：拡大後、右クリックドラッグで表示位置を調整できます
- **初期表示**：ダブルクリックすると全期間表示に戻ります
        """)

    # --- データセット作成ボタン ---
    create_btn = st.button("データセット作成", key="create", help="Causal Impact分析用データセットを作成します。", type="primary")
    if create_btn:
        st.success("データセットの作成が完了しました。分析設定に進みましょう。")
        st.markdown('<span style="color:#388e3c;font-weight:bold;">STEP1完了</span>', unsafe_allow_html=True)
else:
    st.info("処置群・対照群のCSVファイルを選択し、「データを読み込む」ボタンを押してください。") 