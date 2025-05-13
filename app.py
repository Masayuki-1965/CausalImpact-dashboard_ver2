import streamlit as st
import pandas as pd
import os
import glob
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import numpy as np
import matplotlib.pyplot as plt
from causalimpact import CausalImpact

# --- 初期化コード（最初に実行）---
if 'session_initialized' not in st.session_state:
    st.session_state['session_initialized'] = True
    st.session_state['data_loaded'] = False
    st.session_state['dataset_created'] = False
    st.session_state['params_saved'] = False
    st.session_state['analysis_completed'] = False
    # 分析期間のデフォルト値を格納する辞書を初期化
    st.session_state['period_defaults'] = {
        'pre_start': None,
        'pre_end': None,
        'post_start': None,
        'post_end': None
    }

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
    font-size: 3.5em;
    font-weight: 900;
    color: white;
    margin-bottom: 0.1em;
    letter-spacing: 0.04em;
    text-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    line-height: 1.1;
    text-align: center;
}
.sub-title {
    font-size: 1.25em;
    color: white;
    margin-bottom: 1em;
    font-weight: 500;
    text-align: center;
}
.card {
    background: #fff;
    border-radius: 12px;
    padding: 1.3em 1.8em;
    margin-bottom: 1.4em;
    border: 1.5px solid #e3e8ee;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
}
.blue-header-card {
    background: linear-gradient(135deg, #1976d2 0%, #0d47a1 100%);
    border-radius: 12px;
    padding: 1.7em 2em;
    margin-bottom: 2em;
    border: none;
    box-shadow: 0 4px 20px rgba(25, 118, 210, 0.15);
    color: white;
    height: 170px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.step-card {
    background: #e3f2fd;
    border-radius: 12px;
    padding: 1.2em 1.5em;
    margin-bottom: 1.5em;
    border: 1px solid rgba(25, 118, 210, 0.2);
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.03);
}
.section-title {
    font-size: 1.3em;
    font-weight: bold;
    color: #1976d2;
    margin-bottom: 0.8em;
    margin-top: 1em;
    border-left: 5px solid #1976d2;
    padding-left: 12px;
}
.stButton>button {
    background: linear-gradient(135deg, #1976d2 0%, #0d47a1 100%);
    color: #fff;
    font-weight: bold;
    font-size: 1.2em;
    border-radius: 8px;
    padding: 0.6em 2em;
    margin: 0.8em 0;
    box-shadow: 0 6px 15px rgba(25, 118, 210, 0.4);
    width: 100%;
    transition: all 0.2s ease;
}
.stButton>button:hover {
    background: linear-gradient(135deg, #1565c0 0%, #0d47a1 100%);
    box-shadow: 0 8px 20px rgba(25, 118, 210, 0.5);
    transform: translateY(-3px);
}
.stDataFrame, .stTable {
    font-size: 1.05em;
}
hr {
    border: none;
    border-top: 2px solid #e3e8ee;
    margin: 1.5em 0;
}
.sidebar-card {
    background: #fff;
    border-radius: 12px;
    padding: 1.3em 1.5em;
    margin-bottom: 1.4em;
    border: 1.5px solid #e3e8ee;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
}
.sidebar-title {
    font-size: 1.3em;
    font-weight: 600;
    color: #1976d2;
    margin-bottom: 0.7em;
    letter-spacing: 0.02em;
}
.sidebar-step {
    font-size: 1.1em;
    font-weight: bold;
    display: block;
    margin-bottom: 0.7em;
}
.sidebar-step-active {
    background: linear-gradient(135deg, #2196f3 0%, #1565c0 100%);
    color: white;
    border-radius: 8px;
    padding: 0.6em 1.2em;
    margin-bottom: 0.8em;
    display: inline-block;
    box-shadow: 0 3px 10px rgba(33, 150, 243, 0.25);
    width: 100%;
    font-size: 1.15em;
    font-weight: 600;
    letter-spacing: 0.015em;
    transition: all 0.2s ease;
}
.sidebar-step-inactive {
    background: #e8f4fd;
    color: #1976d2;
    border-radius: 8px;
    padding: 0.6em 1.2em;
    margin-bottom: 0.8em;
    display: inline-block;
    box-shadow: 0 1px 4px rgba(33, 150, 243, 0.1);
    width: 100%;
    font-size: 1.15em;
    font-weight: 500;
    letter-spacing: 0.01em;
    transition: all 0.2s ease;
}
.sidebar-step-inactive:hover {
    background: #e1f0fd;
    box-shadow: 0 2px 6px rgba(33, 150, 243, 0.15);
}
.sidebar-faq-title {
    font-size: 1.15em;
    font-weight: bold;
    color: #1976d2;
    margin-bottom: 0.5em;
}
.sidebar-faq-body {
    background: #f4f8fd;
    border-radius: 8px;
    padding: 1.2em 1.3em;
    color: #333;
    font-size: 0.98em;
    line-height: 1.6;
}
.data-format-table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
}
.data-format-table th, .data-format-table td {
    border: 1px solid #e0e0e0;
    padding: 8px 12px;
    text-align: left;
}
.data-format-table th {
    background-color: #f5f5f5;
    font-weight: bold;
}
.file-location {
    background: #e3f2fd;
    padding: 4px 10px;
    border-radius: 6px;
    color: #1565c0;
    font-weight: 500;
}
.expander-header {
    font-size: 1.15em;
    font-weight: bold;
    color: #1976d2;
}
div[data-testid="stExpander"] div[role="button"] p {
    font-size: 1.15em !important;
    font-weight: bold !important;
    color: #1976d2 !important;
}
.separator-line {
    border-top: 1px solid #e0e0e0;
    margin: 1.5em 0;
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

# --- サイドバー ---
with st.sidebar:
    st.markdown('<div class="sidebar-title">分析フロー</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:1em;color:#333;margin-bottom:1em;line-height:1.5;">Causal Impact分析は以下の<b>3つのステップ</b>で行います。各ステップのコンテンツはメイン画面に表示されます。</div>', unsafe_allow_html=True)
    
    # STEPのアクティブ状態を決定
    step1_active = True  # STEP 1は常に表示
    step2_active = False
    step3_active = False
    
    # データ読み込み済みならSTEP 2をアクティブに
    if st.session_state.get('data_loaded', False):
        if 'dataset_created' in st.session_state and st.session_state['dataset_created']:
            step2_active = True
    
    # 分析設定済みならSTEP 3をアクティブに
    if 'params_saved' in st.session_state and st.session_state['params_saved']:
        step3_active = True
    
    # 分析実行済みならSTEP 3をアクティブに
    if 'analysis_completed' in st.session_state and st.session_state['analysis_completed']:
        step3_active = True
        
    st.markdown(f"""
    <div style="margin-top:0.5em;">
        <div class="{'sidebar-step-active' if step1_active else 'sidebar-step-inactive'}">STEP 1：データ取り込み／可視化</div>
        <div class="{'sidebar-step-active' if step2_active else 'sidebar-step-inactive'}">STEP 2：分析期間／パラメータ設定</div>
        <div class="{'sidebar-step-active' if step3_active else 'sidebar-step-inactive'}">STEP 3：分析実行／結果確認</div>
    </div>
    <div class="separator-line"></div>
    """, unsafe_allow_html=True)

    with st.expander("Causal Impactとは？", expanded=False):
        st.markdown("""
<div class="sidebar-faq-body">
<b>Causal Impactは、介入（施策）の効果を測定するための統計手法です。</b><br><br>
介入前のデータから予測モデルを構築し、介入がなかった場合の予測値と実際の値を比較することで、介入の効果を推定します。
</div>
""", unsafe_allow_html=True)
    with st.expander("処置群と対照群について", expanded=False):
        st.markdown("""
<div class="sidebar-faq-body">
<b>処置群</b>は、施策（介入）の影響を受けたグループです。<br><br>
<b>対照群</b>は、施策の影響を受けていないグループであり、比較対象となります。
</div>
""", unsafe_allow_html=True)

# --- メインコンテンツ ---
st.markdown("""
<div class="blue-header-card">
    <div class="big-title">Causal Impact 分析</div>
    <div class="sub-title">施策効果を測定し、可視化するシンプルな分析ツール</div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="step-card">
    <h2 style="font-size:1.8em;font-weight:bold;color:#1565c0;margin-bottom:0.5em;">STEP 1：データ取り込み／可視化</h2>
    <div style="color:#1976d2;font-size:1.1em;line-height:1.5;">このステップでは、分析に必要な時系列データを読み込み、可視化します。処置群（効果を測定したい対象）と対照群（比較対象）のデータをCSVファイルから取り込み、分析用データセットを作成します。</div>
</div>
""", unsafe_allow_html=True)

# --- データ形式ガイド ---
with st.expander("データ形式ガイド", expanded=False):
    st.markdown("""
<div class="section-title" style="margin-top:0;">CSVファイルの要件</div>
<div style="font-size:1.05em;line-height:1.6;margin-bottom:1.2em;">
CSVファイルには、<b>ymd（日付）</b> と <b>qty（数量）</b> の2つのカラムが必須です。
</div>

<div style="display:flex;gap:2.5em;margin-bottom:1.5em;">
<div style="flex:1;">
<div style="font-weight:bold;font-size:1.1em;margin-bottom:0.5em;color:#1976d2;">基本レイアウト</div>
<table class="data-format-table">
<tr><th>ymd</th><th>qty</th></tr>
<tr><td>20170403</td><td>29</td></tr>
<tr><td>20170425</td><td>24</td></tr>
<tr><td>20170426</td><td>23</td></tr>
<tr><td>20170523</td><td>24</td></tr>
<tr><td>20170524</td><td>26</td></tr>
<tr><td>20170529</td><td>21</td></tr>
<tr><td>...</td><td>...</td></tr>
</table>
</div>
<div style="flex:1;">
<div style="font-weight:bold;font-size:1.1em;margin-bottom:0.5em;color:#1976d2;">追加カラムがある場合の例</div>
<table class="data-format-table">
<tr><th>product_category</th><th>ymd</th><th>qty</th></tr>
<tr><td>ﾒｳ3</td><td>20170403</td><td>29</td></tr>
<tr><td>ﾒｳ3</td><td>20170425</td><td>24</td></tr>
<tr><td>ﾒｳ3</td><td>20170426</td><td>23</td></tr>
<tr><td>ﾒｳ3</td><td>20170523</td><td>24</td></tr>
<tr><td>ﾒｳ3</td><td>20170524</td><td>26</td></tr>
<tr><td>ﾒｳ3</td><td>20170529</td><td>21</td></tr>
<tr><td>...</td><td>...</td><td>...</td></tr>
</table>
</div>
</div>

<ul style="margin-top:1em;font-size:1.05em;line-height:1.6;">
<li><b>ymd：</b>日付（YYYYMMDD形式の8桁数字）</li>
<li><b>qty：</b>数量（整数または小数）</li>
</ul>
<p style="margin-top:0.5em;color:#555;">※ 上記以外のカラムは自由に追加できます。なくても問題ありません</p>

<div class="section-title">データファイルの保存場所</div>
<p style="margin-bottom:1em;font-size:1.05em;line-height:1.6;">処置群と対照群それぞれのCSVデータファイルを、以下の専用フォルダに保存してください。</p>

<div style="background:#f5f5f5;border-radius:10px;padding:1.2em;margin-bottom:1.5em;">
<div style="display:flex;margin-bottom:1em;">
<div style="width:180px;font-weight:bold;">処置群データ：</div>
<div class="file-location">data/treatment_data/</div>
</div>
<div style="display:flex;">
<div style="width:180px;font-weight:bold;">対照群データ：</div>
<div class="file-location">data/control_data/</div>
</div>
</div>

<ul style="font-size:1.05em;line-height:1.6;">
<li>CSVファイルの名称を製品名・品種名などに設定すると、処置群・対照群の名称として表示されます（日本語表記も可）</li>
<li>フォルダ内に複数のCSVファイルを保存しておくと、「データ選択」メニューから対象ファイルを選択できます</li>
</ul>
""", unsafe_allow_html=True)

# --- ファイル選択UI ---
st.markdown('<div class="section-title">分析対象ファイルの選択</div>', unsafe_allow_html=True)

treatment_dir = "data/treatment_data"
control_dir = "data/control_data"

def get_csv_files(directory):
    files = glob.glob(os.path.join(directory, "*.csv"))
    return [os.path.basename(f) for f in files]

treatment_files = get_csv_files(treatment_dir)
control_files = get_csv_files(control_dir)

col1, col2 = st.columns(2)
with col1:
    st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">処置群ファイル</div>', unsafe_allow_html=True)
    treatment_file = st.selectbox("", treatment_files, key="treat", label_visibility="collapsed")
    selected_treat = f"選択：{treatment_file}（処置群）" if treatment_files else "処置群ファイルが見つかりません"
    st.markdown(f'<div style="color:#1976d2;font-size:0.9em;">{selected_treat}</div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">対照群ファイル</div>', unsafe_allow_html=True)
    control_file = st.selectbox("", control_files, key="ctrl", label_visibility="collapsed")
    selected_ctrl = f"選択：{control_file}（対照群）" if control_files else "対照群ファイルが見つかりません"
    st.markdown(f'<div style="color:#1976d2;font-size:0.9em;">{selected_ctrl}</div>', unsafe_allow_html=True)

# --- データ読み込みボタン ---
st.markdown('<div style="margin-top:25px;"></div>', unsafe_allow_html=True)
read_btn = st.button("データを読み込む", key="read", help="選択したファイルを読み込みます。", type="primary", use_container_width=True)

# --- データ読み込み・クリーニング関数 ---
def load_and_clean_csv(path):
    # ymd, qtyだけ抽出（他カラムは無視）
    df = pd.read_csv(path, usecols=lambda c: c.strip() in ['ymd', 'qty'])
    df['ymd'] = df['ymd'].astype(str).str.zfill(8)
    df['ymd'] = pd.to_datetime(df['ymd'], format='%Y%m%d', errors='coerce')
    df = df.dropna(subset=['ymd'])
    return df

# --- ファイル選択後のデータ読み込み ---
if read_btn:
    treatment_path = os.path.join(treatment_dir, treatment_file)
    control_path = os.path.join(control_dir, control_file)
    df_treat = load_and_clean_csv(treatment_path)
    df_ctrl = load_and_clean_csv(control_path)
    treatment_name = os.path.splitext(treatment_file)[0]
    control_name = os.path.splitext(control_file)[0]
    # セッションに保存
    st.session_state['df_treat'] = df_treat
    st.session_state['df_ctrl'] = df_ctrl
    st.session_state['treatment_name'] = treatment_name
    st.session_state['control_name'] = control_name
    st.session_state['data_loaded'] = True
    st.success("データを読み込みました。下記にプレビューと統計情報を表示します。")

# --- データ読み込み済みなら表示（セッションから取得） ---
if st.session_state.get('data_loaded', False):
    df_treat = st.session_state['df_treat']
    df_ctrl = st.session_state['df_ctrl']
    treatment_name = st.session_state['treatment_name']
    control_name = st.session_state['control_name']
    # --- データプレビュー ---
    st.markdown('<div class="section-title">読み込みデータのプレビュー（上位10件表示）</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">処置群（{treatment_name}）</div>', unsafe_allow_html=True)
        preview_df_treat = df_treat.head(10).copy()
        preview_df_treat.index = range(1, len(preview_df_treat) + 1)
        st.dataframe(preview_df_treat, use_container_width=True)
    with col2:
        st.markdown(f'<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">対照群（{control_name}）</div>', unsafe_allow_html=True)
        preview_df_ctrl = df_ctrl.head(10).copy()
        preview_df_ctrl.index = range(1, len(preview_df_ctrl) + 1)
        st.dataframe(preview_df_ctrl, use_container_width=True)
    # --- 統計情報 ---
    st.markdown('<div class="section-title">データの統計情報</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    def format_stats_with_japanese(df):
        stats = df.describe().reset_index()
        stats.columns = ['統計項目', '数値']
        stats['統計項目'] = stats['統計項目'].replace({
            'count': 'count（個数）',
            'mean': 'mean（平均）',
            'std': 'std（標準偏差）',
            'min': 'min（最小値）',
            '25%': '25%（第1四分位数）',
            '50%': '50%（中央値）',
            '75%': '75%（第3四分位数）',
            'max': 'max（最大値）'
        })
        for i, row in stats.iterrows():
            if row['統計項目'] != 'count（個数）':
                stats.at[i, '数値'] = round(row['数値'], 2)
        return stats
    with col1:
        st.markdown(f'<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">処置群（{treatment_name}）</div>', unsafe_allow_html=True)
        if 'qty' in df_treat.columns:
            stats_treat = format_stats_with_japanese(df_treat[['qty']])
            st.dataframe(stats_treat, use_container_width=True, hide_index=True)
        else:
            st.error("データに 'qty' カラムが見つかりません")
    with col2:
        st.markdown(f'<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">対照群（{control_name}）</div>', unsafe_allow_html=True)
        if 'qty' in df_ctrl.columns:
            stats_ctrl = format_stats_with_japanese(df_ctrl[['qty']])
            st.dataframe(stats_ctrl, use_container_width=True, hide_index=True)
        else:
            st.error("データに 'qty' カラムが見つかりません")
    # --- 分析用データセット作成セクション ---
    st.markdown('<div class="section-title">分析用データセットの作成</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">分析データ集計方法の選択</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 3])
    with col1:
        freq_option = st.radio(
            "データ集計方法",
            options=["月次", "旬次"],
            label_visibility="collapsed"
        )
    with col2:
        if freq_option == "月次":
            st.markdown("""
<div style="font-size:0.98em;margin-top:0.1em;padding-left:0;">
<span style="font-weight:bold;">月次集計：</span>月単位で集計し、日付はその月の1日になります<br>
<span style="font-weight:normal;color:#666;">旬次集計：</span>月を上旬・中旬・下旬に3分割して集計し、日付はそれぞれ1日（上旬）、11日（中旬）、21日（下旬）になります<br>
<div style="color:#1976d2;font-size:0.9em;margin-top:0.3em;padding-left:0;">※欠損値は自動的に0で埋められます。</div>
</div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
<div style="font-size:0.98em;margin-top:0.1em;padding-left:0;">
<span style="font-weight:normal;color:#666;">月次集計：</span>月単位で集計し、日付はその月の1日になります<br>
<span style="font-weight:bold;">旬次集計：</span>月を上旬・中旬・下旬に3分割して集計し、日付はそれぞれ1日（上旬）、11日（中旬）、21日（下旬）になります<br>
<div style="color:#1976d2;font-size:0.9em;margin-top:0.3em;padding-left:0;">※欠損値は自動的に0で埋められます。</div>
</div>
            """, unsafe_allow_html=True)
    
    # 「データセットを作成する」ボタンの上に余白を追加
    st.markdown('<div style="margin-top:25px;"></div>', unsafe_allow_html=True)
    create_btn = st.button("データセットを作成する", key="create", help="Causal Impact分析用データセットを作成します。", type="primary", use_container_width=True)
    
    if create_btn or ('dataset_created' in st.session_state and st.session_state['dataset_created']):
        if create_btn:  # 新しくデータセットを作成する場合のみ実行
            def make_period_key(dt, freq):
                if freq == "月次":
                    return dt.strftime('%Y-%m-01')
                elif freq == "旬次":
                    day = dt.day
                    if day <= 10:
                        return dt.strftime('%Y-%m-01')
                    elif day <= 20:
                        return dt.strftime('%Y-%m-11')
                    else:
                        return dt.strftime('%Y-%m-21')
                else:
                    return dt.strftime('%Y-%m-%d')
                    
            def aggregate_df(df, freq):
                df = df.copy()
                df['period'] = df['ymd'].apply(lambda x: make_period_key(x, freq))
                agg = df.groupby('period', as_index=False)['qty'].sum()
                agg['period'] = pd.to_datetime(agg['period'])
                return agg
                
            def create_full_period_range(df1, df2, freq):
                # 両方のデータフレームから最初と最後の日付を取得
                df1_dates = pd.to_datetime(df1['ymd'])
                df2_dates = pd.to_datetime(df2['ymd'])
                
                # 「処置群と対照群の開始日のうち遅い方」から「終了日のうち早い方」までを共通期間とする
                start_date = max(df1_dates.min(), df2_dates.min())
                end_date = min(df1_dates.max(), df2_dates.max())
                
                # 共通期間の範囲を生成（周期に合わせて）
                if freq == "月次":
                    # 月の初日のシーケンスを生成
                    periods = pd.date_range(
                        start=start_date.replace(day=1),
                        end=end_date.replace(day=1),
                        freq='MS'  # Month Start
                    )
                elif freq == "旬次":
                    # 旬区切りの日付リストを作成
                    first_month = start_date.replace(day=1)
                    last_month = end_date.replace(day=1)
                    months = pd.date_range(start=first_month, end=last_month, freq='MS')
                    
                    periods = []
                    for month in months:
                        # 各月の1日、11日、21日を追加（範囲内の場合のみ）
                        for day in [1, 11, 21]:
                            date = month.replace(day=day)
                            if start_date <= date <= end_date:
                                periods.append(date)
                    periods = pd.DatetimeIndex(periods)
                else:  # 日次
                    periods = pd.date_range(start=start_date, end=end_date, freq='D')
                
                return periods
                    
            # データフレームの集計
            agg_treat = aggregate_df(df_treat, freq_option)
            agg_ctrl = aggregate_df(df_ctrl, freq_option)
            
            # 共通期間の全日付範囲を生成（両群の開始日の遅い方から終了日の早い方まで）
            all_periods = create_full_period_range(df_treat, df_ctrl, freq_option)
            
            # 全期間のインデックスを作成し、データをゼロ埋め
            all_periods_df = pd.DataFrame(index=all_periods)
            all_periods_df.index.name = 'period'
            
            # 各データフレームとマージしてゼロ埋め
            agg_treat_full = pd.merge(
                all_periods_df, 
                agg_treat.set_index('period'), 
                how='left', 
                left_index=True, 
                right_index=True
            ).fillna(0)
            
            agg_ctrl_full = pd.merge(
                all_periods_df, 
                agg_ctrl.set_index('period'), 
                how='left', 
                left_index=True, 
                right_index=True
            ).fillna(0)
            
            # 最終データセット作成
            dataset = pd.DataFrame({
                'ymd': all_periods,
                f'処置群（{treatment_name}）': agg_treat_full['qty'].values,
                f'対照群（{control_name}）': agg_ctrl['qty'].values if len(agg_ctrl_full) == 0 else agg_ctrl_full['qty'].values
            })
            
            # データ期間情報を保存（表示用）
            treat_period = f"{df_treat['ymd'].min().strftime('%Y/%m/%d')} ～ {df_treat['ymd'].max().strftime('%Y/%m/%d')}"
            ctrl_period = f"{df_ctrl['ymd'].min().strftime('%Y/%m/%d')} ～ {df_ctrl['ymd'].max().strftime('%Y/%m/%d')}"
            common_period = f"{all_periods.min().strftime('%Y/%m/%d')} ～ {all_periods.max().strftime('%Y/%m/%d')}"
            st.session_state['period_info'] = {
                'treat_period': treat_period,
                'ctrl_period': ctrl_period,
                'common_period': common_period
            }
            
            # セッションに保存
            st.session_state['dataset'] = dataset
            st.session_state['dataset_created'] = True
            
            # 分析期間のデフォルト値を設定
            dataset_min_date = dataset['ymd'].min().date()
            dataset_max_date = dataset['ymd'].max().date()
            
            # データセットの前半部分を介入前期間、後半部分を介入期間としてデフォルト設定
            mid_point_idx = len(dataset) // 2
            default_pre_end = dataset.iloc[mid_point_idx-1]['ymd'].date()
            default_post_start = dataset.iloc[mid_point_idx]['ymd'].date()
            
            st.session_state['period_defaults'] = {
                'pre_start': dataset_min_date,
                'pre_end': default_pre_end,
                'post_start': default_post_start,
                'post_end': dataset_max_date
            }
        else:
            # データセットが既に作成済みの場合、セッションから取得
            dataset = st.session_state['dataset']
        
        # データセット情報の表示（新規作成・既存問わず）
        period_info = st.session_state.get('period_info', {})
        common_period = period_info.get('common_period', f"{dataset['ymd'].min().strftime('%Y/%m/%d')} ～ {dataset['ymd'].max().strftime('%Y/%m/%d')}")
        
        st.markdown(f"""
<div style="margin-bottom:1.5em;">
<div style="display:flex;align-items:center;margin-bottom:0.5em;">
  <div style="font-weight:bold;font-size:1.05em;margin-right:0.5em;">対象期間：</div>
<div>{dataset['ymd'].min().strftime('%Y/%m/%d')} ～ {dataset['ymd'].max().strftime('%Y/%m/%d')}</div>
  <div style="color:#1976d2;font-size:0.9em;margin-left:2em;">　※処置群と対照群の共通期間に基づいてデータセットを作成しています。</div>
</div>
<div style="display:flex;align-items:center;margin-bottom:0.5em;">
  <div style="font-weight:bold;font-size:1.05em;margin-right:0.5em;">データ数：</div>
<div>{len(dataset)} 件</div>
</div>
</div>
        """, unsafe_allow_html=True)
        
        # 元データの期間情報がある場合は詳細を表示
        if 'period_info' in st.session_state:
            with st.expander("元データの期間情報", expanded=False):
                st.markdown(f"""
<div style="margin-top:0.5em;">
<p><b>処置群期間：</b>{st.session_state['period_info']['treat_period']}</p>
<p><b>対照群期間：</b>{st.session_state['period_info']['ctrl_period']}</p>
<p><b>共通期間：</b>{st.session_state['period_info']['common_period']}</p>
<p style="margin-top:1em;font-size:0.9em;color:#666;">※共通期間は「処置群と対照群の開始日のうち遅い方」から「終了日のうち早い方」までとして計算しています。<br>※欠損値はすべてゼロ埋めされています。</p>
</div>
                """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">データプレビュー（上位10件表示）</div>', unsafe_allow_html=True)
            preview_df = dataset.head(10).copy()
            preview_df['ymd'] = preview_df['ymd'].dt.strftime('%Y-%m-%d')
            preview_df.index = range(1, len(preview_df) + 1)
            st.dataframe(preview_df, use_container_width=True)
        with col2:
            st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">統計情報</div>', unsafe_allow_html=True)
            treatment_col = f'処置群（{treatment_name}）'
            control_col = f'対照群（{control_name}）'
            stats_df = pd.DataFrame({
                '統計項目': ['count（個数）', 'mean（平均）', 'std（標準偏差）', 'min（最小値）', '25%（第1四分位数）', '50%（中央値）', '75%（第3四分位数）', 'max（最大値）'],
                treatment_col: [len(dataset), round(dataset[treatment_col].mean(),2), round(dataset[treatment_col].std(),2), dataset[treatment_col].min(), dataset[treatment_col].quantile(0.25), dataset[treatment_col].quantile(0.5), dataset[treatment_col].quantile(0.75), dataset[treatment_col].max()],
                control_col: [len(dataset), round(dataset[control_col].mean(),2), round(dataset[control_col].std(),2), dataset[control_col].min(), dataset[control_col].quantile(0.25), dataset[control_col].quantile(0.5), dataset[control_col].quantile(0.75), dataset[control_col].max()]
            })
            st.dataframe(stats_df, use_container_width=True, hide_index=True)
        st.markdown('<div class="section-title">時系列プロット</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">処置群と対照群の時系列推移</div>', unsafe_allow_html=True)
        
        # プロットの作成を明示的に行う
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # 処置群のトレース追加
        fig.add_trace(
            go.Scatter(
                x=dataset['ymd'], 
                y=dataset[treatment_col], 
                name=f"処置群（{treatment_name}）", 
                line=dict(color="#1976d2", width=2), 
                mode='lines', 
                hovertemplate='日付: %{x|%Y-%m-%d}<br>数量: %{y}<extra></extra>'
            ),
            secondary_y=False
        )
        
        # 対照群のトレース追加
        fig.add_trace(
            go.Scatter(
                x=dataset['ymd'], 
                y=dataset[control_col], 
                name=f"対照群（{control_name}）", 
                line=dict(color="#ef5350", width=2), 
                mode='lines', 
                hovertemplate='日付: %{x|%Y-%m-%d}<br>数量: %{y}<extra></extra>'
            ),
            secondary_y=True
        )
        
        # X軸の設定
        fig.update_xaxes(
            title_text="日付", 
            type="date", 
            tickformat="%Y-%m", 
            showgrid=True, 
            tickangle=-30
        )
        
        # 左Y軸の設定（処置群）
        fig.update_yaxes(
            title_text="処置群の数量", 
            secondary_y=False, 
            title_font=dict(color="#1976d2"), 
            tickfont=dict(color="#1976d2")
        )
        
        # 右Y軸の設定（対照群）
        fig.update_yaxes(
            title_text="対照群の数量", 
            secondary_y=True, 
            title_font=dict(color="#ef5350"), 
            tickfont=dict(color="#ef5350")
        )
        
        # レイアウト設定
        fig.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            hovermode="x unified",
            plot_bgcolor='white',
            margin=dict(t=50, l=60, r=60, b=60),
            height=500,
            autosize=True,
            xaxis_rangeslider_visible=True,
            dragmode="zoom"
        )
        
        # プロット表示
        st.plotly_chart(fig, use_container_width=True)
        with st.expander("Plotlyインタラクティブグラフの使い方ガイド"):
            st.markdown("""
<div style="line-height:1.7;">
<ul>
<li><b>データ確認</b>：グラフ上の線やポイントにマウスを置くと、詳細値がポップアップ表示されます</li>
<li><b>拡大表示</b>：見たい期間をドラッグして範囲選択すると拡大表示されます</li>
<li><b>表示移動</b>：拡大後、右クリックドラッグで表示位置を調整できます</li>
<li><b>初期表示</b>：ダブルクリックすると全期間表示に戻ります</li>
<li><b>系列表示切替</b>：凡例をクリックすると系列の表示/非表示を切り替えできます</li>
</ul>
</div>
            """, unsafe_allow_html=True)
        with st.expander("分析期間設定のヒント"):
            st.markdown("""
<div style="line-height:1.7;">
<ul>
  <li><b>介入期間</b>：処置群（青線）において、施策（介入）実施後の効果を測定したい期間を設定してください</li>
  <li><b>介入前期間</b>：施策（介入）実施前の期間として、十分な長さのデータを含めて設定してください
    <ul>
      <li><b>季節性</b>：介入前期間に季節性がある場合は、少なくとも2〜3周期分のデータを含めるのが望ましいです</li>
      <li><b>イレギュラー要因</b>：外部要因による大きな影響がある期間は、介入前期間に含めないことをおすすめします</li>
    </ul>
  </li>
</ul>
</div>
        """, unsafe_allow_html=True)

        # STEP 1完了メッセージと次のSTEPへのボタンを表示
        st.success("データセットの作成が完了しました。次のステップで分析期間とパラメータの設定を行います。")
        
        # 分析期間とパラメータを設定するボタンを追加
        next_step_btn = st.button("分析期間とパラメータを設定する", key="next_step", help="次のステップ（分析期間とパラメータ設定）に進みます。", type="primary", use_container_width=True)
        
        # --- STEP 2: 分析期間／パラメータ設定 ---
        # データセット作成完了後、ボタンを押すか既にパラメータ設定画面を表示中ならSTEP 2を表示
        if next_step_btn or ('show_step2' in st.session_state and st.session_state['show_step2']):
            # ボタンを押した場合はセッション状態を更新
            if next_step_btn:
                st.session_state['show_step2'] = True
            
            dataset = st.session_state['dataset']  # セッションから取得
            
            st.markdown("""
<div class="step-card">
    <h2 style="font-size:1.8em;font-weight:bold;color:#1565c0;margin-bottom:0.5em;">STEP 2：分析期間／パラメータ設定</h2>
    <div style="color:#1976d2;font-size:1.1em;line-height:1.5;">このステップでは、Causal Impact分析に必要な期間とモデルパラメータを設定します。介入前期間（モデル構築用）と介入期間（効果測定期間）を指定し、必要に応じてモデルの詳細設定を行います。</div>
</div>
            """, unsafe_allow_html=True)
            
            # --- 分析期間設定 ---
            st.markdown('<div class="section-title">分析期間の設定</div>', unsafe_allow_html=True)
            
            st.markdown("""
<div style="margin-bottom:1.5em;line-height:1.6;">
介入前期間のデータをもとに予測モデルを構築し、介入期間の効果を測定します。
</div>
            """, unsafe_allow_html=True)
            
            # デフォルト値をセッションから取得
            period_defaults = st.session_state.get('period_defaults', {})
            
            # デフォルト値を設定
            pre_start = period_defaults.get('pre_start', dataset['ymd'].min().date())
            pre_end = period_defaults.get('pre_end', dataset['ymd'].max().date())
            post_start = period_defaults.get('post_start', dataset['ymd'].min().date())
            post_end = period_defaults.get('post_end', dataset['ymd'].max().date())
            
            # 介入前期間の設定
            st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.15em;">介入前期間 (Pre-Period)</div>', unsafe_allow_html=True)
            st.markdown('<div style="margin-bottom:1em;">モデル構築に使用する介入前の期間を指定します。</div>', unsafe_allow_html=True)
            
            # 警告メッセージを削除
            # st.info("介入前期間と介入期間の整合性に注意してください。介入前期間の終了日は介入期間の開始日より前になるようにしてください。")
            
            # 介入前期間の入力フォーム
            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<div style="font-weight:bold;margin-bottom:0.3em;">開始日</div>', unsafe_allow_html=True)
                pre_start_date = st.date_input(
                    "pre_start",
                    value=pre_start,
                    min_value=dataset['ymd'].min().date(),
                    max_value=dataset['ymd'].max().date() - pd.Timedelta(days=1),
                    format="YYYY/MM/DD",
                    label_visibility="collapsed"
                )
            with col2:
                st.markdown('<div style="font-weight:bold;margin-bottom:0.3em;">終了日</div>', unsafe_allow_html=True)
                pre_end_date = st.date_input(
                    "pre_end",
                    value=pre_end,
                    min_value=pre_start_date,
                    max_value=dataset['ymd'].max().date() - pd.Timedelta(days=1),
                    format="YYYY/MM/DD",
                    label_visibility="collapsed"
                )
            
            # 介入期間の設定
            st.markdown('<div style="font-weight:bold;margin-top:1.5em;margin-bottom:0.5em;font-size:1.15em;">介入期間 (Post-Period)</div>', unsafe_allow_html=True)
            
            # 説明文と警告メッセージを統合
            st.markdown('<div style="margin-bottom:1em;">効果を測定する介入後の期間を指定します。（※介入期間の開始日は介入前期間の終了日より後の日付を指定してください。）</div>', unsafe_allow_html=True)
            
            # 単独の警告メッセージを削除
            # st.info("介入期間の開始日は介入前期間の終了日より後の日付を選択してください。")
            
            # 最小日付は翌日ではなく、データセットの最小日付を設定
            min_post_start = dataset['ymd'].min().date()
            
            # 推奨開始日（介入前期間の終了日の翌日）を計算 - エラー対策
            try:
                if pre_end_date is not None:
                    suggested_post_start = pre_end_date + pd.Timedelta(days=1)
                else:
                    # pre_end_dateが無効な場合はデータセット最小日付を使用
                    suggested_post_start = dataset['ymd'].min().date()
            except (TypeError, ValueError):
                # エラーが発生した場合もデータセット最小日付を使用
                suggested_post_start = dataset['ymd'].min().date()
            
            # 介入前期間の終了日よりも後の日付をデフォルト値として設定
            # post_startがNoneでなく、日付の場合のみ比較を実行
            try:
                if post_start is None or pre_end_date is None:
                    post_start = suggested_post_start
                elif isinstance(post_start, type(pre_end_date)) and post_start <= pre_end_date:
                    post_start = suggested_post_start
            except (TypeError, ValueError):
                post_start = suggested_post_start
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<div style="font-weight:bold;margin-bottom:0.3em;">開始日</div>', unsafe_allow_html=True)
                post_start_date = st.date_input(
                    "post_start",
                    value=post_start,
                    min_value=min_post_start,
                    max_value=dataset['ymd'].max().date(),
                    format="YYYY/MM/DD",
                    label_visibility="collapsed"
                )
            with col2:
                st.markdown('<div style="font-weight:bold;margin-bottom:0.3em;">終了日</div>', unsafe_allow_html=True)
                # min_valueに条件付きで値を設定（post_start_dateがNoneの場合の対応）
                min_val = post_start_date if post_start_date is not None else min_post_start
                post_end_date = st.date_input(
                    "post_end",
                    value=post_end,
                    min_value=min_val,
                    max_value=dataset['ymd'].max().date(),
                    format="YYYY/MM/DD",
                    label_visibility="collapsed"
                )
            
            # 整合性チェック - 日付が有効な場合のみ比較
            try:
                if pre_end_date is not None and post_start_date is not None and post_start_date <= pre_end_date:
                    st.warning(f"介入期間の開始日（{post_start_date}）が介入前期間の終了日（{pre_end_date}）以前に設定されています。正確な分析のためには、介入期間の開始日は介入前期間の終了日よりも後に設定することをおすすめします。")
            except (TypeError, ValueError):
                pass
            
            # 選択された分析期間の表示
            st.markdown('<div style="font-weight:bold;margin-top:1.5em;margin-bottom:0.5em;font-size:1.15em;">選択された分析期間</div>', unsafe_allow_html=True)
            
            # 日数計算 - エラーハンドリングを追加
            try:
                pre_days = (pre_end_date - pre_start_date).days + 1
                post_days = (post_end_date - post_start_date).days + 1
                
                # 日付が正しく設定されている場合のみ表示
                st.markdown(f"""
<div style="margin-bottom:1em;">
<p>介入前期間: {pre_start_date.strftime('%Y-%m-%d')} 〜 {pre_end_date.strftime('%Y-%m-%d')} （{pre_days}日間）</p>
<p>介入期間: {post_start_date.strftime('%Y-%m-%d')} 〜 {post_end_date.strftime('%Y-%m-%d')} （{post_days}日間）</p>
</div>
                """, unsafe_allow_html=True)
            except (TypeError, AttributeError) as e:
                # 日付計算でエラーが発生した場合は、日付のみ表示
                st.markdown(f"""
<div style="margin-bottom:1em;">
<p>介入前期間: {pre_start_date} 〜 {pre_end_date}</p>
<p>介入期間: {post_start_date} 〜 {post_end_date}</p>
</div>
                """, unsafe_allow_html=True)
                st.info("日付を正しく設定してください。全ての日付が設定されると、日数が計算されます。")

            # 分析期間をセッションに保存
            st.session_state['analysis_period'] = {
                'pre_start': pre_start_date,
                'pre_end': pre_end_date,
                'post_start': post_start_date,
                'post_end': post_end_date
            }
            
            # --- モデル・パラメータ設定 ---
            st.markdown('<div class="section-title">モデル・パラメータの設定</div>', unsafe_allow_html=True)
            
            # 基本パラメータと詳細設定の分離
            with st.expander("詳細設定　（※デフォルト値での分析で十分な場合は設定不要です）", expanded=False):
                # 信頼区間の設定
                st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;">信頼区間</div>', unsafe_allow_html=True)
                alpha = st.slider(
                    "",
                    min_value=0.80,
                    max_value=0.99,
                    value=0.95,
                    step=0.01,
                    format="%.2f",
                    label_visibility="collapsed"
                )
                
                # 季節性の設定
                st.markdown('<div style="font-weight:bold;margin-top:1em;margin-bottom:0.5em;">季節性を考慮する</div>', unsafe_allow_html=True)
                seasonality = st.checkbox("", value=False, label_visibility="collapsed")
                
                # 季節性がオンの場合、周期タイプを選択
                if seasonality:
                    st.markdown('<div style="font-weight:bold;margin-top:0.5em;margin-bottom:0.5em;">周期タイプ</div>', unsafe_allow_html=True)
                    seasonality_type = st.radio(
                        "",
                        options=["週次 (7日)", "旬次 (10日)", "月次 (30日)", "四半期 (90日)", "年次 (365日)", "カスタム"],
                        index=1,  # デフォルト値を「旬次 (10日)」に設定
                        label_visibility="collapsed"
                    )
                    
                    # カスタム選択時のみ日数指定フィールドを表示
                    if seasonality_type == "カスタム":
                        custom_period = st.number_input(
                            "カスタム周期（日数）",
                            min_value=2,
                            max_value=365,
                            value=7,
                            step=1,
                            help="季節性の周期を日数で指定します"
                        )
                
                # 事前分布のハイパーパラメータ設定
                st.markdown('<div style="font-weight:bold;margin-top:1em;margin-bottom:0.5em;">水準の事前分布の標準偏差</div>', unsafe_allow_html=True)
                prior_level_sd = st.slider(
                    "",
                    min_value=0.001,
                    max_value=0.100,
                    value=0.010,
                    step=0.001,
                    format="%.3f",
                    label_visibility="collapsed"
                )
                
                # 追加パラメータ（必要に応じて追加）
                st.markdown('<div style="font-weight:bold;margin-top:1em;margin-bottom:0.5em;">その他の設定</div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    standardize = st.checkbox("データを標準化する", value=False, help="入力データを標準化してから分析します")
                with col2:
                    niter = st.number_input("MCMC反復回数", min_value=100, max_value=10000, value=1000, step=100, help="モンテカルロシミュレーションの反復回数")
            
            # パラメータの説明を別セクションとして表形式で追加（デフォルトで折りたたみ）
            with st.expander("パラメータの説明", expanded=False):
                st.markdown("""
<table style="width:100%; border-collapse: collapse; margin-top:0.5em; font-size:0.9em;">
  <tr style="background-color:#f0f5fa;">
    <th style="padding:8px; text-align:left; border:1px solid #ddd; width:20%;">パラメータ名</th>
    <th style="padding:8px; text-align:left; border:1px solid #ddd; width:65%;">意味</th>
    <th style="padding:8px; text-align:left; border:1px solid #ddd; width:15%;">デフォルト値</th>
  </tr>
  <tr>
    <td style="padding:8px; border:1px solid #ddd; white-space:nowrap;"><b>信頼区間</b></td>
    <td style="padding:8px; border:1px solid #ddd;">分析結果の不確実性を表現する範囲です。値が大きいほど信頼区間は広くなり、効果の推定に対する確信度が高まりますが、区間自体は広くなります。</td>
    <td style="padding:8px; border:1px solid #ddd; text-align:center;">0.95</td>
  </tr>
  <tr style="background-color:#f9fbfd;">
    <td style="padding:8px; border:1px solid #ddd; white-space:nowrap;"><b>季節性を考慮する</b></td>
    <td style="padding:8px; border:1px solid #ddd;">時系列データに含まれる周期的なパターンを考慮するかどうかを指定します。曜日・月・季節などの影響がある場合はオンにします。</td>
    <td style="padding:8px; border:1px solid #ddd; text-align:center;">オフ</td>
  </tr>
  <tr>
    <td style="padding:8px; border:1px solid #ddd; white-space:nowrap;"><b>周期タイプ</b></td>
    <td style="padding:8px; border:1px solid #ddd;">
      ・<b>週次 (7日)</b>: 週単位で繰り返すパターンがある場合（平日と週末の違いなど）<br>
      ・<b>旬次 (10日)</b>: 上旬・中旬・下旬の周期がある場合<br>
      ・<b>月次 (30日)</b>: 月単位で繰り返すパターンがある場合（月初・月末の変動など）<br>
      ・<b>四半期 (90日)</b>: 四半期単位で繰り返すパターンがある場合（決算期の影響など）<br>
      ・<b>年次 (365日)</b>: 年単位で繰り返すパターンがある場合（季節変動など）<br>
      ・<b>カスタム</b>: 上記以外の特定の周期がある場合
    </td>
    <td style="padding:8px; border:1px solid #ddd; text-align:center;">旬次 (10日)</td>
  </tr>
  <tr style="background-color:#f9fbfd;">
    <td style="padding:8px; border:1px solid #ddd; white-space:nowrap;"><b>水準の事前分布の<br>標準偏差</b></td>
    <td style="padding:8px; border:1px solid #ddd;">ベイズモデルにおける事前分布のパラメータで、時系列の水準（レベル）の変動性をどの程度許容するかを指定します。値が大きいほど水準の変化に対して寛容になります。</td>
    <td style="padding:8px; border:1px solid #ddd; text-align:center;">0.010</td>
  </tr>
  <tr>
    <td style="padding:8px; border:1px solid #ddd; white-space:nowrap;"><b>データを標準化する</b></td>
    <td style="padding:8px; border:1px solid #ddd;">分析前にデータを平均0、標準偏差1になるように変換するかどうかを指定します。データのスケールが大きく異なる場合や、単位の影響を排除したい場合にオンにします。</td>
    <td style="padding:8px; border:1px solid #ddd; text-align:center;">オフ</td>
  </tr>
  <tr style="background-color:#f9fbfd;">
    <td style="padding:8px; border:1px solid #ddd; white-space:nowrap;"><b>MCMC反復回数</b></td>
    <td style="padding:8px; border:1px solid #ddd;">モンテカルロマルコフ連鎖（MCMC）シミュレーションの反復回数を指定します。値が大きいほど推定精度が向上しますが、計算時間も長くなります。</td>
    <td style="padding:8px; border:1px solid #ddd; text-align:center;">1000</td>
  </tr>
</table>
                """, unsafe_allow_html=True)
            
            # パラメータをセッションに保存
            seasonality_period = None
            if seasonality:
                if seasonality_type == "週次 (7日)":
                    seasonality_period = 7
                elif seasonality_type == "旬次 (10日)":
                    seasonality_period = 10
                elif seasonality_type == "月次 (30日)":
                    seasonality_period = 30
                elif seasonality_type == "四半期 (90日)":
                    seasonality_period = 90
                elif seasonality_type == "年次 (365日)":
                    seasonality_period = 365
                else:  # カスタム
                    seasonality_period = custom_period if 'custom_period' in locals() else 7
            
            st.session_state['analysis_params'] = {
                'alpha': alpha,
                'seasonality': seasonality,
                'seasonality_period': seasonality_period,
                'prior_level_sd': prior_level_sd,
                'standardize': standardize if 'standardize' in locals() else False,
                'niter': niter if 'niter' in locals() else 1000
            }
            # params_savedフラグをTrueに設定
            st.session_state['params_saved'] = True
            
            # --- 分析実行 ---
            st.markdown('<div class="section-title">分析実行</div>', unsafe_allow_html=True)
            
            # 分析準備完了メッセージ
            st.success("分析実行の準備が完了しました。以下のボタンをクリックして分析を開始してください。")
            
            # 分析実行ボタン
            analyze_btn = st.button("分析実行", key="analyze", help="Causal Impact分析を実行します。", type="primary", use_container_width=True)
            
            # 分析実行時の処理
            if analyze_btn:
                # 分析パラメータが保存されたことを明示的に記録
                st.session_state['params_saved'] = True
                
                # 分析中メッセージ
                with st.spinner("Causal Impact分析を実行中..."):
                    try:
                        # STEP 3の見出しと説明を追加
                        st.markdown("""
<div class="step-card">
    <h2 style="font-size:1.8em;font-weight:bold;color:#1565c0;margin-bottom:0.5em;">STEP 3：分析実行／結果確認</h2>
    <div style="color:#1976d2;font-size:1.1em;line-height:1.5;">このステップでは、設定した期間とパラメータに基づいてCausal Impact分析を実行し、結果を確認します。分析結果のグラフとサマリーから、処置群への介入効果を評価できます。</div>
</div>
                        """, unsafe_allow_html=True)
                        
                        # データセット取得
                        dataset = st.session_state['dataset']
                        treatment_col = [col for col in dataset.columns if '処置群' in col][0]
                        control_col = [col for col in dataset.columns if '対照群' in col][0]
                        data = dataset.set_index('ymd')[[treatment_col, control_col]]
                        # 期間取得
                        period = st.session_state['analysis_period']
                        pre_period = [str(period['pre_start']), str(period['pre_end'])]
                        post_period = [str(period['post_start']), str(period['post_end'])]
                        # --- 日付バリデーション ---
                        all_index = set(str(d.date()) for d in data.index)
                        invalid_dates = []
                        for d in pre_period + post_period:
                            if d not in all_index:
                                invalid_dates.append(d)
                        if invalid_dates:
                            st.error("分析期間には、存在する日付を設定してください（例：月次データの場合は1日、旬次データの場合は1日・11日・21日）")
                            st.session_state['analysis_completed'] = False
                        else:
                            # CausalImpact分析
                            ci = CausalImpact(data, pre_period, post_period)
                            # 分析実行結果表示
                            alpha = st.session_state['analysis_params']['alpha']
                            # 信頼区間をパーセント表示に変換（例：0.95 → 95%）
                            alpha_percent = int(alpha * 100)
                            treatment_name = st.session_state['treatment_name']
                            period = st.session_state['analysis_period']
                            st.markdown('<div class="section-title">分析結果グラフ</div>', unsafe_allow_html=True)
                            col1, col2, col3 = st.columns([2,3,2])
                            with col1:
                                st.markdown(f'**分析対象**：{treatment_name}')
                            with col2:
                                st.markdown(f'**分析期間**：{period["post_start"].strftime("%Y-%m-%d")} 〜 {period["post_end"].strftime("%Y-%m-%d")}')
                            with col3:
                                st.markdown(f'**信頼水準**：{alpha_percent}%')
                            # サマリーとレポート取得
                            summary = ci.summary()
                            report = ci.summary(output='report')
                            # グラフ描画
                            fig = ci.plot(figsize=(10, 6))
                            # figがNoneの場合は現在のFigureを利用
                            if fig is None:
                                fig = plt.gcf()
                            # タイトル追加
                            axes = fig.axes
                            if len(axes) >= 3:
                                # 英語のタイトルを設定（文字化け対策）
                                axes[0].set_title("Graph 1: Predicted vs Actual", fontsize=12)
                                axes[1].set_title("Graph 2: Point Effects", fontsize=12)
                                axes[2].set_title("Graph 3: Cumulative Effect", fontsize=12)
                                
                                # 下部の"Note: The first 1 observations..."メッセージを削除
                                # 各サブプロットの下部テキストを確認して削除
                                for ax in axes:
                                    # テキストオブジェクトを検索
                                    for text in ax.texts:
                                        # "Note:"で始まるテキストを削除
                                        if "Note:" in text.get_text():
                                            text.set_visible(False)
                                    
                                    # フットノートとして表示されている場合は別の方法で削除
                                    # _remove_annotationメソッドがあれば使用
                                    if hasattr(ax, '_remove_annotation'):
                                        ax._remove_annotation('Note')
                                    
                                    # 下部に余白がないように調整（メッセージが表示される領域を除外）
                                    ax.set_xlabel('')
                                    
                                # 図全体のレイアウトを調整して下部のメッセージ領域を除外
                                plt.subplots_adjust(bottom=0.1, hspace=0.3)
                                
                                # 図の下部に表示されるテキストを全て削除する別の方法
                                fig.texts = []
                            
                            plt.tight_layout()
                            st.pyplot(fig)
                            
                            # グラフに関する注釈を追加
                            st.markdown("""
<div style="margin-top:0.5em;margin-bottom:1.5em;background:#f5f8fd;padding:1em;border-radius:8px;">
<p style="font-size:0.9em;color:#444;margin-bottom:0.8em;"><b>グラフの見方：</b></p>
<p style="font-size:0.9em;color:#444;margin-bottom:0.8em;"><b>Graph 1（予測値 vs 実測値の比較）</b>：介入がなかった場合の予測値（青の破線）と実測値（黒の実線）を比較したグラフです。介入の影響を視覚的に確認できます。</p>
<p style="font-size:0.9em;color:#444;margin-bottom:0.8em;"><b>Graph 2（時点効果）</b>：各時点における介入の影響（効果）を示したグラフです。プラス・マイナスの変化から、影響の方向と大きさを把握できます。</p>
<p style="font-size:0.9em;color:#444;"><b>Graph 3（累積効果）</b>：分析期間を通じて蓄積された効果の合計を示しています。右肩上がりであれば、介入が継続的に効果を発揮していると判断できます。</p>
</div>
                            """, unsafe_allow_html=True)
                            
                            # 分析結果サマリーのセクションタイトルを追加
                            st.markdown('<div class="section-title">分析結果サマリー</div>', unsafe_allow_html=True)
                            
                            # 分析結果サマリー 表形式で表示
                            import re
                            # 数値部分のみ抽出してDataFrame化
                            lines = [l for l in summary.split('\n') if l.strip()]
                            data_lines = []
                            for line in lines[1:]:
                                parts = re.split(r'\s{2,}', line.strip())
                                if len(parts) == 3:
                                    # 平均と累積値を抽出
                                    data_lines.append([parts[1], parts[2]])
                            import pandas as pd
                            df_summary = pd.DataFrame(data_lines, columns=['分析期間の平均値','分析期間の累積値'])
                            # 日本語インデックス設定 - 信頼区間の値を動的に反映
                            japanese_index = [
                                '実測値',
                                '予測値 (標準偏差)',
                                f'予測値 {alpha_percent}% 信頼区間',
                                '絶対効果 (標準偏差)',
                                f'絶対効果 {alpha_percent}% 信頼区間',
                                '相対効果 (標準偏差)',
                                f'相対効果 {alpha_percent}% 信頼区間'
                            ]
                            df_summary.index = japanese_index[:len(df_summary)]
                            st.dataframe(df_summary, use_container_width=True)
                            # 詳細レポート（日本語訳）
                            with st.expander("詳細レポート"):
                                # 詳細レポートの初期化 - エラー修正
                                report_jp = report
                                
                                # 詳細レポートの構造的な日本語化（段落ごとに処理）
                                # 先頭の「Analysis report {CausalImpact}」を置換
                                report_jp = report_jp.replace("Analysis report {CausalImpact}", "分析レポート {CausalImpact}")
                                
                                # 最初の段落（介入期間と予測値の比較）
                                first_para_en = """During the post-intervention period, the response variable had
an average value of approx. [0-9.]+. In the absence of an
intervention, we would have expected an average response of [0-9.]+.
The 95% interval of this counterfactual prediction is \[[0-9., -]+\].
Subtracting this prediction from the observed response yields
an estimate of the causal effect the intervention had on the
response variable. This effect is [0-9.+]+ with a 95% interval of
\[[0-9., -]+\]. For a discussion of the significance of this effect,
see below."""
                                
                                import re
                                # 数値部分を正規表現でキャプチャしながら置換
                                # 1. 最初の"During the post-intervention period..."段落
                                first_para_match = re.search(r"During the post-intervention period.*?see below\.", report_jp, re.DOTALL)
                                if first_para_match:
                                    # 数値をキャプチャ
                                    avg_value = re.search(r"average value of approx. ([0-9.]+)", first_para_match.group(0))
                                    exp_response = re.search(r"expected an average response of ([0-9.]+)", first_para_match.group(0))
                                    interval_pred = re.search(r"prediction is \[([0-9., -]+)\]", first_para_match.group(0))
                                    effect = re.search(r"This effect is ([0-9.+\-]+) with", first_para_match.group(0))
                                    effect_interval = re.search(r"95% interval of\s+\[([0-9., -]+)\]", first_para_match.group(0))
                                    
                                    if avg_value and exp_response and interval_pred and effect and effect_interval:
                                        # 数値を保持して日本語化 - 信頼区間を動的に反映
                                        first_para_jp = f"""介入期間中、応答変数は平均値が約{avg_value.group(1)}でした。もし介入がなかった場合、予測される平均応答値は{exp_response.group(1)}でした。この反事実予測の{alpha_percent}%信頼区間は[{interval_pred.group(1)}]です。この予測値を観測値から引くことで、介入が応答変数に与えた因果効果の推定値が得られます。この効果は{effect.group(1)}であり、{alpha_percent}%信頼区間は[{effect_interval.group(1)}]です。この効果の有意性については以下を参照してください。"""
                                        
                                        # 元のテキストを置換
                                        report_jp = report_jp.replace(first_para_match.group(0), first_para_jp)
                                
                                # 1b. 最初の段落の別パターン（"By contrast"を含む負の効果の場合）
                                alt_first_para_match = re.search(r"During the post-intervention period.*?By contrast.*?see below\.", report_jp, re.DOTALL)
                                if alt_first_para_match:
                                    # 数値をキャプチャ
                                    avg_value = re.search(r"average value of approx. ([0-9.]+)", alt_first_para_match.group(0))
                                    exp_response = re.search(r"expected an average response of ([0-9.]+)", alt_first_para_match.group(0))
                                    interval_pred = re.search(r"prediction is \[([0-9., -]+)\]", alt_first_para_match.group(0))
                                    effect = re.search(r"This effect is (-[0-9.]+) with", alt_first_para_match.group(0))
                                    effect_interval = re.search(r"95% interval of\s+\[([0-9., -]+)\]", alt_first_para_match.group(0))
                                    
                                    if avg_value and exp_response and interval_pred and effect and effect_interval:
                                        # 数値を保持して日本語化 - 信頼区間を動的に反映
                                        alt_first_para_jp = f"""介入期間中、応答変数は平均値が約{avg_value.group(1)}でした。対照的に、介入がなかった場合には、予測される平均応答値は{exp_response.group(1)}でした。この反事実予測の{alpha_percent}%信頼区間は[{interval_pred.group(1)}]です。この予測値を観測値から引くことで、介入が応答変数に与えた因果効果の推定値が得られます。この効果は{effect.group(1)}であり、{alpha_percent}%信頼区間は[{effect_interval.group(1)}]です。この効果の有意性については以下を参照してください。"""
                                        
                                        # 元のテキストを置換
                                        report_jp = report_jp.replace(alt_first_para_match.group(0), alt_first_para_jp)
                                
                                # 2. 二番目の"Summing up the individual data points..."段落
                                second_para_match = re.search(r"Summing up the individual data points.*?this prediction is \[[0-9., -]+\].", report_jp, re.DOTALL)
                                if second_para_match:
                                    # 数値をキャプチャ
                                    overall_value = re.search(r"overall value of ([0-9.]+)", second_para_match.group(0))
                                    sum_expected = re.search(r"expected\s+a sum of ([0-9.]+)", second_para_match.group(0))
                                    sum_interval = re.search(r"prediction is \[([0-9., -]+)\]", second_para_match.group(0))
                                    
                                    if overall_value and sum_expected and sum_interval:
                                        # 数値を保持して日本語化 - 信頼区間を動的に反映
                                        second_para_jp = f"""介入期間中の個々のデータポイントを合計すると（これが意味を持つ場合のみ）、応答変数の全体値は{overall_value.group(1)}でした。介入がなかった場合、予測される合計値は{sum_expected.group(1)}でした。この予測の{alpha_percent}%信頼区間は[{sum_interval.group(1)}]です。"""
                                        
                                        # 元のテキストを置換
                                        report_jp = report_jp.replace(second_para_match.group(0), second_para_jp)
                                
                                # 3. 三番目の"The above results are given in terms of absolute numbers..."段落
                                third_para_match = re.search(r"The above results are given in terms of absolute numbers.*?this percentage is \[[0-9.%, -]+\].", report_jp, re.DOTALL)
                                if third_para_match:
                                    # 数値をキャプチャ
                                    increase = re.search(r"increase of \+?([0-9.%]+)", third_para_match.group(0))
                                    percentage_interval = re.search(r"percentage is \[([0-9.%, -]+)\]", third_para_match.group(0))
                                    
                                    if increase and percentage_interval:
                                        # 数値を保持して日本語化 - 信頼区間を動的に反映
                                        third_para_jp = f"""上記の結果は絶対値で示されています。相対的には、応答変数は{increase.group(1)}の増加を示しました。この割合の{alpha_percent}%信頼区間は[{percentage_interval.group(1)}]です。"""
                                        
                                        # 元のテキストを置換
                                        report_jp = report_jp.replace(third_para_match.group(0), third_para_jp)
                                
                                # 3b. 三番目の段落の別パターン（"decrease"を含む場合 - 負の効果）
                                alt_third_para_match = re.search(r"The above results are given in terms of absolute numbers.*?decrease of -[0-9.]+%.*?this percentage is \[[0-9.%, -]+\].", report_jp, re.DOTALL)
                                if alt_third_para_match:
                                    # 数値をキャプチャ
                                    decrease = re.search(r"decrease of (-[0-9.]+%)", alt_third_para_match.group(0))
                                    percentage_interval = re.search(r"percentage is \[([0-9.%, -]+)\]", alt_third_para_match.group(0))
                                    
                                    if decrease and percentage_interval:
                                        # 数値を保持して日本語化 - 信頼区間を動的に反映
                                        alt_third_para_jp = f"""上記の結果は絶対値で示されています。相対的には、応答変数は{decrease.group(1)}の減少を示しました。この割合の{alpha_percent}%信頼区間は[{percentage_interval.group(1)}]です。"""
                                        
                                        # 元のテキストを置換
                                        report_jp = report_jp.replace(alt_third_para_match.group(0), alt_third_para_jp)
                                
                                # 4. 四番目の"This means that, although the intervention appears..."段落
                                fourth_para_match = re.search(r"This means that, although the intervention appears.*?was above zero.", report_jp, re.DOTALL)
                                if fourth_para_match:
                                    fourth_para_jp = """これは、介入が正の効果をもたらしたように見えるものの、介入期間全体を考慮するとこの効果は統計的に有意ではないことを意味します。介入期間内の個々の日や短い期間については（効果の時系列グラフの下限が0より上にある場合に示されるように）依然として有意な効果があった可能性があります。"""
                                    report_jp = report_jp.replace(fourth_para_match.group(0), fourth_para_jp)
                                
                                # 統計的に有意な場合の代替パターン（正の効果があり、統計的に有意である場合）
                                alt_fourth_para_match = re.search(r"This means that the positive effect observed during the intervention.*?of the underlying intervention\.", report_jp, re.DOTALL)
                                if alt_fourth_para_match:
                                    # 効果値を抽出
                                    effect_value = re.search(r"absolute effect \(([0-9.]+)\)", alt_fourth_para_match.group(0))
                                    effect_str = effect_value.group(1) if effect_value else "X"
                                    alt_fourth_para_jp = f"""これは、介入期間中に観察された正の効果が統計的に有意であり、ランダムな変動に起因する可能性が低いことを意味します。ただし、この増加が実質的な意味を持つかどうかという問題は、絶対効果（{effect_str}）を介入の本来の目標と比較することによってのみ答えることができることに注意すべきです。"""
                                    report_jp = report_jp.replace(alt_fourth_para_match.group(0), alt_fourth_para_jp)
                                
                                # 統計的に有意な負の効果を持つ場合のパターン
                                negative_fourth_para_match = re.search(r"This means that the negative effect observed during the intervention.*?in the absence of the intervention\.", report_jp, re.DOTALL)
                                if negative_fourth_para_match:
                                    negative_fourth_para_jp = """これは、介入期間中に観察された負の効果が統計的に有意であることを意味します。実験者が正の効果を期待していた場合は、制御変数の異常が、介入がない場合に応答変数で起こるはずだったことについて過度に楽観的な期待を引き起こした可能性があるかどうかを再確認することをお勧めします。"""
                                    report_jp = report_jp.replace(negative_fourth_para_match.group(0), negative_fourth_para_jp)
                                
                                # 5. 五番目の"The apparent effect could be the result of random fluctuations..."段落
                                fifth_para_match = re.search(r"The apparent effect could be the result of random fluctuations.*?during the learning period.", report_jp, re.DOTALL)
                                if fifth_para_match:
                                    fifth_para_jp = """見かけ上の効果は、介入と無関係なランダムな変動の結果である可能性があります。これは、介入期間が非常に長く、効果が既に消失した時間の多くを含む場合によく起こります。また、介入期間が短すぎてシグナルとノイズを区別できない場合にも起こり得ます。最後に、有意な効果が見つからないのは、制御変数が十分でない場合や、これらの変数が学習期間中に応答変数とうまく相関していない場合にも起こることがあります。"""
                                    report_jp = report_jp.replace(fifth_para_match.group(0), fifth_para_jp)
                                
                                # 6. 最後の"The probability of obtaining this effect by chance..."段落（有意でない場合）
                                sixth_para_match = re.search(r"The probability of obtaining this effect by chance is p = [0-9]+%.*?considered statistically significant.", report_jp, re.DOTALL)
                                if sixth_para_match:
                                    p_value = re.search(r"p = ([0-9]+%)", sixth_para_match.group(0))
                                    if p_value:
                                        sixth_para_jp = f"""この効果が偶然によって得られる確率はp = {p_value.group(1)}です。これは、この効果が見せかけのものである可能性があり、一般的には統計的に有意とはみなされないことを意味します。"""
                                        report_jp = report_jp.replace(sixth_para_match.group(0), sixth_para_jp)
                                
                                # 6b. 最後の段落の別パターン（効果が統計的に有意な場合）
                                alt_sixth_para_match = re.search(r"The probability of obtaining this effect by chance is very small.*?considered statistically\s+significant\.", report_jp, re.DOTALL)
                                if alt_sixth_para_match:
                                    # p値を抽出
                                    p_value = re.search(r"probability p = ([0-9.]+)", alt_sixth_para_match.group(0))
                                    p_str = p_value.group(1) if p_value else "X"
                                    alt_sixth_para_jp = f"""この効果が偶然によって得られる確率は非常に小さいです（ベイズ単側尾部確率 p = {p_str}）。これは、因果効果が統計的に有意であると考えられることを意味します。"""
                                    report_jp = report_jp.replace(alt_sixth_para_match.group(0), alt_sixth_para_jp)
                                
                                # p値の行を日本語に置換
                                p_line_match = re.search(r"Posterior tail-area probability p: [0-9.]+", report_jp)
                                if p_line_match:
                                    p_value = re.search(r"p: ([0-9.]+)", p_line_match.group(0))
                                    if p_value:
                                        p_line_jp = f"事後確率 p値: {p_value.group(1)}"
                                        report_jp = report_jp.replace(p_line_match.group(0), p_line_jp)
                                
                                # 因果効果の確率の行を日本語に置換
                                prob_line_match = re.search(r"Posterior probability of a causal effect: [0-9.]+%", report_jp)
                                if prob_line_match:
                                    prob_value = re.search(r": ([0-9.]+%)", prob_line_match.group(0))
                                    if prob_value:
                                        prob_line_jp = f"因果効果の事後確率: {prob_value.group(1)}"
                                        report_jp = report_jp.replace(prob_line_match.group(0), prob_line_jp)
                                
                                # 改行の調整：連続する改行を1つに統一して段落間の余白を調整
                                report_jp = re.sub(r'\n\s*\n\s*\n+', '\n\n', report_jp)
                                
                                # レポート表示
                                st.text(report_jp)
                            st.success("Causal Impact分析が完了しました。分析結果のグラフとサマリーを確認してください。")
                            st.session_state['analysis_completed'] = True
                    except Exception as e:
                        st.error(f"Causal Impact分析中にエラーが発生しました: {e}")
                        st.session_state['analysis_completed'] = False

else:
    st.info("処置群・対照群のCSVファイルを選択し、「データを読み込む」ボタンを押してください。") 