import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import io
from datetime import datetime
import base64
import tempfile
from PIL import Image
import plotly.io as pio
import plotly.figure_factory as ff
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as ReportLabImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
# 必要な外部モジュールのみimport
from causal_impact_translator import translate_causal_impact_report
from utils_step1 import get_csv_files, load_and_clean_csv, make_period_key, aggregate_df, create_full_period_range, format_stats_with_japanese
from utils_step2 import get_period_defaults, validate_periods, calc_period_days, build_analysis_params
from utils_step3 import run_causal_impact_analysis, build_summary_dataframe

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

# --- PDFレポート用に日本語フォントの登録 ---
# noto_sans_jp_path = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansJP-Regular.ttf")
# if os.path.exists(noto_sans_jp_path):
#     pdfmetrics.registerFont(TTFont('NotoSansJP', noto_sans_jp_path))
# else:
#     st.warning("日本語フォントが見つかりません。PDFレポートの日本語表示が正しく行われない可能性があります。")

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
.red-action-button {
    background: linear-gradient(135deg, #ff5252 0%, #e52d27 100%);
    color: #fff;
    font-weight: normal;
    font-size: 1.0em;
    border-radius: 8px;
    padding: 0.5em 2em;
    margin: 0.6em 0;
    box-shadow: 0 6px 15px rgba(229, 45, 39, 0.4);
    width: 100%;
    display: inline-block;
    text-align: center;
    text-decoration: none;
    border: none;
    transition: all 0.2s ease;
    cursor: pointer;
}
.red-action-button:hover {
    background: linear-gradient(135deg, #e52d27 0%, #ff5252 100%);
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
    
    # セッション状態をリセットする関数
    def reset_session_state():
        # 初期化が必要な状態変数をリセット
        st.session_state['data_loaded'] = False
        st.session_state['dataset_created'] = False
        st.session_state['params_saved'] = False
        st.session_state['analysis_completed'] = False
        # 期間のデフォルト値もリセット
        st.session_state['period_defaults'] = {
            'pre_start': None,
            'pre_end': None,
            'post_start': None,
            'post_end': None
        }
        # その他の状態変数も削除
        keys_to_remove = [
            'df_treat', 'df_ctrl', 'treatment_name', 'control_name',
            'dataset', 'analysis_period', 'analysis_params'
        ]
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]
    
    # 最初からやり直す案内文
    st.markdown('<div style="margin-top:15px;margin-bottom:10px;"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="background-color:#ffebee;border-radius:8px;padding:12px 15px;border-left:4px solid #d32f2f;margin-bottom:15px;">
        <div style="font-weight:bold;margin-bottom:8px;color:#d32f2f;font-size:1.05em;">最初からやり直す場合：</div>
        <div style="line-height:1.5;">画面左上の<b>更新ボタン（⟳）</b>をクリックするか、<b>Ctrl + R</b>を押して、STEP1「データ取込／可視化」から再実行してください。</div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("Causal Impactとは？", expanded=False):
        st.markdown("""
<div class="sidebar-faq-body">
<b>Causal Impactは、介入（施策）の効果を測定する統計手法です。</b><br><br>
施策の影響を受けた<b>“処置群”</b>と影響を受けていない<b>“対照群”</b>の関係性をもとに、<b>状態空間モデル</b>を用いて介入がなかった場合の処置群の予測値を算出し、処置群の実測値と比較します。
</div>
""", unsafe_allow_html=True)
    with st.expander("状態空間モデルとは？", expanded=False):
        st.markdown("""
<div class="sidebar-faq-body">
<b>状態空間モデル</b>は、時系列データの変化する傾向や構造を捉えるための統計モデルです。
観測データの背後にある“見えない状態”を推定しながら、将来の値を予測します。
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
""", unsafe_allow_html=True)

# --- ファイル選択UIの代わりにファイルアップロード機能 ---
st.markdown('<div class="section-title">分析対象ファイルのアップロード</div>', unsafe_allow_html=True)

# アップロード方法切り替えのラジオボタン
upload_method = st.radio(
    "アップロード方法を選択",
    options=["CSVテキスト直接入力", "ファイルアップロード（工事中）"],
    index=0,
    help="CSVデータを直接入力する方法と、ファイルをアップロードする方法があります。"
)

if upload_method == "ファイルアップロード（工事中）":
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">処置群ファイル</div>', unsafe_allow_html=True)
        # ファイルサイズ制限を明示的に設定（5MB）
        treatment_file = st.file_uploader(
            "処置群のCSVファイルをアップロード", 
            type=['csv'], 
            key="treatment_upload", 
            help="処置群（効果を測定したい対象）のCSVファイルをアップロードしてください。",
            accept_multiple_files=False
        )
        if treatment_file:
            treatment_name = os.path.splitext(treatment_file.name)[0]
            selected_treat = f"選択：{treatment_file.name}（処置群）"
            st.markdown(f'<div style="color:#1976d2;font-size:0.9em;">{selected_treat}</div>', unsafe_allow_html=True)
        else:
            treatment_name = ""
    with col2:
        st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">対照群ファイル</div>', unsafe_allow_html=True)
        # ファイルサイズ制限を明示的に設定（5MB）
        control_file = st.file_uploader(
            "対照群のCSVファイルをアップロード", 
            type=['csv'], 
            key="control_upload", 
            help="対照群（比較対象）のCSVファイルをアップロードしてください。",
            accept_multiple_files=False
        )
        if control_file:
            control_name = os.path.splitext(control_file.name)[0]
            selected_ctrl = f"選択：{control_file.name}（対照群）"
            st.markdown(f'<div style="color:#1976d2;font-size:0.9em;">{selected_ctrl}</div>', unsafe_allow_html=True)
        else:
            control_name = ""
    
    # --- データ読み込みボタン ---
    st.markdown('<div style="margin-top:25px;"></div>', unsafe_allow_html=True)
    read_btn = st.button("データを読み込む", key="read", help="アップロードしたファイルを読み込みます。", type="primary", use_container_width=True, disabled=(not treatment_file or not control_file))
else:
    # CSVテキスト直接入力のUI
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">処置群データ</div>', unsafe_allow_html=True)
        treatment_name = st.text_input("処置群の名称", value="処置群", help="処置群の名称を入力してください（例：商品A、店舗B など）")
        
        treatment_csv = st.text_area(
            "処置群のCSVデータを入力（カンマ／タブ／スペース区切り）",
            height=200,
            help="CSVデータを直接入力してください。最低限、ymd（日付）とqty（数量）の列が必要です。",
            placeholder="ymd,qty\n20170403,29\n20170425,24\n20170426,23\n20170523,24\n20170524,26"
        )
    
    with col2:
        st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">対照群データ</div>', unsafe_allow_html=True)
        control_name = st.text_input("対照群の名称", value="対照群", help="対照群の名称を入力してください（例：商品B、店舗C など）")
        
        control_csv = st.text_area(
            "対照群のCSVデータを入力（カンマ／タブ／スペース区切り）",
            height=200,
            help="CSVデータを直接入力してください。最低限、ymd（日付）とqty（数量）の列が必要です。",
            placeholder="ymd,qty\n20170403,35\n20170425,30\n20170426,28\n20170523,29\n20170524,31"
        )
    
    # --- データ読み込みボタン ---
    st.markdown('<div style="margin-top:25px;"></div>', unsafe_allow_html=True)
    read_btn = st.button("データを読み込む", key="read_text", help="入力したCSVデータを読み込みます。", type="primary", use_container_width=True, disabled=(not treatment_csv or not control_csv))

# --- アップロードされたファイルからデータを読み込む関数 ---
def load_and_clean_uploaded_csv(uploaded_file):
    try:
        # バイト列を読み込み
        file_bytes = uploaded_file.getvalue()
        
        # エンコーディング検出の試行回数を増やす
        encodings = ['utf-8', 'shift-jis', 'cp932', 'euc-jp', 'iso-2022-jp', 'latin1']
        df = None
        
        for encoding in encodings:
            try:
                # エンコーディングを設定して読み込み試行
                content = file_bytes.decode(encoding)
                # テスト用に先頭行だけ解析
                test_df = pd.read_csv(io.StringIO(content.split('\n', 5)[0]), nrows=1)
                # 成功したらすべてを読み込む
                df = pd.read_csv(io.StringIO(content))
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                continue
        
        # どのエンコーディングでも読み込めなかった場合
        if df is None:
            try:
                # 方法2: tempfileを使用
                with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
                    tmp_file.write(file_bytes)
                    tmp_path = tmp_file.name
                
                # 一時ファイルから読み込む
                df = pd.read_csv(tmp_path)
                # 読み込み後に一時ファイルを削除
                os.unlink(tmp_path)
            except Exception as e:
                # 方法3: BytesIOを直接使用
                try:
                    df = pd.read_csv(io.BytesIO(file_bytes))
                except Exception as e2:
                    st.error(f"ファイルの読み込みに失敗しました。")
                    return None
        
        # カラム名の確認とクリーニング
        df.columns = [col.strip() for col in df.columns]
        
        # 必須カラムが含まれているか確認
        required_columns = ['ymd', 'qty']
        if not all(col in df.columns for col in required_columns):
            # カスタムカラムの場合は、最初の2つのカラムがymdとqtyと仮定
            if len(df.columns) >= 2:
                rename_dict = {df.columns[0]: 'ymd', df.columns[1]: 'qty'}
                df = df.rename(columns=rename_dict)
            else:
                st.error(f"必須カラム 'ymd' と 'qty' が見つかりません。")
                return None
        
        # 日付の処理
        df['ymd'] = df['ymd'].astype(str).str.zfill(8)
        df['ymd'] = pd.to_datetime(df['ymd'], format='%Y%m%d', errors='coerce')
        
        # 無効な日付をチェック
        invalid_dates = df[df['ymd'].isna()]
        if not invalid_dates.empty:
            df = df.dropna(subset=['ymd'])
        
        # 欠損値を除外
        original_len = len(df)
        df = df.dropna(subset=['ymd'])
            
        # qty列の数値変換確認
        try:
            df['qty'] = pd.to_numeric(df['qty'], errors='coerce')
            if df['qty'].isna().any():
                df = df.dropna(subset=['qty'])
        except Exception as e:
            st.error(f"数量(qty)の処理中にエラーが発生しました。")
            return None
            
        return df
    except Exception as e:
        st.error(f"ファイルの処理中にエラーが発生しました。")
        return None

# --- テキスト入力からCSVデータを読み込む関数 ---
def load_and_clean_csv_text(csv_text, source_name):
    try:
        # 空のテキストチェック
        if not csv_text.strip():
            st.error(f"{source_name}のCSVデータが入力されていません。")
            return None
        
        # 入力テキストの前処理（改行と区切り文字の正規化）
        csv_text = csv_text.strip()
        # 最初の行を取得してヘッダー行を分析
        lines = csv_text.split('\n')
        if len(lines) == 0:
            st.error(f"{source_name}の入力データに行がありません。")
            return None
            
        # データ形式のチェック（タブ区切り、カンマ区切り、スペース区切りに対応）
        header = lines[0]
        sep = None
        
        # 区切り文字の検出（タブ、カンマ、スペースの順で試す）
        if '\t' in header:
            sep = '\t'
        elif ',' in header:
            sep = ','
        elif ' ' in header and len(header.split()) > 1:
            sep = '\\s+'  # 正規表現によるスペース区切り
        else:
            # 区切り文字が見つからない場合は、カンマ区切りと仮定
            sep = ','
        
        try:
            # 区切り文字を指定してCSVをパース
            if sep == '\\s+':
                # 正規表現のスペース区切りの場合
                df = pd.read_csv(io.StringIO(csv_text), sep=sep, engine='python')
            else:
                df = pd.read_csv(io.StringIO(csv_text), sep=sep)
        except Exception as e:
            st.error(f"{source_name}のCSVデータ形式が不正です。")
            # タブ区切りでもカンマ区切りでも失敗した場合、スペース区切りを試す
            try:
                df = pd.read_csv(io.StringIO(csv_text), delim_whitespace=True)
            except Exception as e2:
                st.error(f"{source_name}のデータ読み込みに失敗しました。")
                return None
        
        # カラム名の確認とクリーニング（空白を除去）
        df.columns = [col.strip() for col in df.columns]
        
        # 必須カラムが含まれているか確認
        required_columns = ['ymd', 'qty']
        if not all(col in df.columns for col in required_columns):
            # カスタムカラムの場合は、最初の2つのカラムがymdとqtyと仮定
            if len(df.columns) >= 2:
                rename_dict = {df.columns[0]: 'ymd', df.columns[1]: 'qty'}
                df = df.rename(columns=rename_dict)
            else:
                st.error(f"{source_name}の必須カラム 'ymd' と 'qty' が見つかりません。")
                return None
        
        # 日付の処理
        df['ymd'] = df['ymd'].astype(str).str.zfill(8)
        df['ymd'] = pd.to_datetime(df['ymd'], format='%Y%m%d', errors='coerce')
        
        # 無効な日付をチェック
        invalid_dates = df[df['ymd'].isna()]
        if not invalid_dates.empty:
            df = df.dropna(subset=['ymd'])
        
        # 欠損値を除外
        original_len = len(df)
        df = df.dropna(subset=['ymd'])
            
        # qty列の数値変換確認
        try:
            df['qty'] = pd.to_numeric(df['qty'], errors='coerce')
            if df['qty'].isna().any():
                df = df.dropna(subset=['qty'])
        except Exception as e:
            st.error(f"{source_name}の数量(qty)の処理中にエラーが発生しました。")
            return None
        
        # カラムがすべて揃っていることを確認
        if 'ymd' not in df.columns or 'qty' not in df.columns:
            st.error(f"{source_name}のデータにymdまたはqtyカラムがありません。")
            return None
        
        # データが空でないことを確認
        if df.empty:
            st.error(f"{source_name}の有効なデータがありません。")
            return None
            
        return df
    except Exception as e:
        st.error(f"{source_name}のデータ処理中にエラーが発生しました。")
        return None

# --- カスタムエラーハンドリング関数 ---
def check_date_validity(date_value, min_date, max_date, date_type):
    """
    日付の有効性をチェックし、適切なエラーメッセージを返す
    """
    # 日付が未設定の場合
    if date_value is None:
        return "日付が正しく設定されていません。"
    
    # データセットの最小日付より前の日付が選択された場合
    if min_date is not None and date_value < min_date:
        return f"⚠ 分析期間設定エラー：指定された{date_type}（{date_value}）はデータセットの対象期間（{min_date} ～ {max_date}）外です。対象期間内の日付を選択してください。"
    
    # データセットの最大日付より後の日付が選択された場合
    if max_date is not None and date_value > max_date:
        return f"⚠ 分析期間設定エラー：指定された{date_type}（{date_value}）はデータセットの対象期間（{min_date} ～ {max_date}）外です。対象期間内の日付を選択してください。"
    
    # 日付が有効な場合はNoneを返す
    return None

# --- ファイルアップロード後のデータ読み込み ---
if upload_method == "ファイルアップロード（工事中）" and read_btn and treatment_file and control_file:
    with st.spinner("データ読み込み中..."):
        try:
            # セーフティチェック - ファイルサイズの確認
            if treatment_file.size > 5 * 1024 * 1024 or control_file.size > 5 * 1024 * 1024:
                st.error("ファイルサイズが大きすぎます。5MB以下のファイルを使用してください。")
                df_treat = None
                df_ctrl = None
            else:
                # ファイルのシーク位置をリセット（複数回読み込む可能性があるため）
                treatment_file.seek(0)
                
                # 処置群ファイルの読み込み試行
                df_treat = load_and_clean_uploaded_csv(treatment_file)
                
                # 処置群ファイルが読み込めた場合のみ対照群ファイルを読み込む
                if df_treat is not None:
                    # ファイルのシーク位置をリセット
                    control_file.seek(0)
                    
                    # 対照群ファイルの読み込み試行
                    df_ctrl = load_and_clean_uploaded_csv(control_file)
                else:
                    df_ctrl = None
                    st.error("処置群ファイルの読み込みに失敗したため、対照群ファイルの読み込みをスキップします。")
            
            if df_treat is not None and df_ctrl is not None and not df_treat.empty and not df_ctrl.empty:
                # セッションに保存
                st.session_state['df_treat'] = df_treat
                st.session_state['df_ctrl'] = df_ctrl
                st.session_state['treatment_name'] = treatment_name
                st.session_state['control_name'] = control_name
                st.session_state['data_loaded'] = True
                st.success("データを読み込みました。下記にプレビューと統計情報を表示します。")
            else:
                st.error("データの読み込みに失敗しました。CSVファイルの形式を確認してください。")
                if df_treat is None:
                    st.error("処置群ファイルの読み込みに失敗しました。")
                elif df_treat.empty:
                    st.error("処置群ファイルに有効なデータがありません。")
                if df_ctrl is None:
                    st.error("対照群ファイルの読み込みに失敗しました。")
                elif df_ctrl is not None and df_ctrl.empty:
                    st.error("対照群ファイルに有効なデータがありません。")
                st.session_state['data_loaded'] = False
                
                # 代替入力方法の提案
                st.info("CSVテキスト直接入力をご利用ください。")
        except Exception as e:
            st.error(f"データ読み込み中に予期しないエラーが発生しました: {str(e)}")
            st.session_state['data_loaded'] = False
            
            # 代替入力方法の提案
            st.info("CSVテキスト直接入力をご利用ください。")

# --- テキスト入力からのデータ読み込み ---
elif upload_method == "CSVテキスト直接入力" and read_btn:
    with st.spinner("データ読み込み中..."):
        df_treat = load_and_clean_csv_text(treatment_csv, "処置群")
        df_ctrl = load_and_clean_csv_text(control_csv, "対照群")
        
        if df_treat is not None and df_ctrl is not None and not df_treat.empty and not df_ctrl.empty:
            # セッションに保存
            st.session_state['df_treat'] = df_treat
            st.session_state['df_ctrl'] = df_ctrl
            st.session_state['treatment_name'] = treatment_name
            st.session_state['control_name'] = control_name
            st.session_state['data_loaded'] = True
            st.success("データを読み込みました。下記にプレビューと統計情報を表示します。")
        else:
            st.error("データの読み込みに失敗しました。入力したCSVデータの形式を確認してください。")
            if df_treat is None:
                st.error("処置群データの読み込みに失敗しました。")
            if df_ctrl is None:
                st.error("対照群データの読み込みに失敗しました。")
            st.session_state['data_loaded'] = False

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
            pre_start, pre_end, post_start, post_end = get_period_defaults(st.session_state, dataset)
            
            # 介入前期間の設定
            st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.15em;">介入前期間 (Pre-Period)</div>', unsafe_allow_html=True)
            st.markdown('<div style="margin-bottom:1em;">モデル構築に使用する介入前の期間を指定します。</div>', unsafe_allow_html=True)
            
            # 警告メッセージを削除
            # st.info("介入前期間と介入期間の整合性に注意してください。介入前期間の終了日は介入期間の開始日より前になるようにしてください。")
            
            # データセット期間の範囲を取得
            dataset_min_date = dataset['ymd'].min().date()
            dataset_max_date = dataset['ymd'].max().date()
            
            # 介入前期間の入力フォーム
            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<div style="font-weight:bold;margin-bottom:0.3em;">開始日</div>', unsafe_allow_html=True)
                pre_start_date = st.date_input(
                    "pre_start",
                    value=pre_start,
                    # min_valueとmax_valueの制約を緩和（実質的な制約を削除）
                    # 実際の検証は後で行う
                    min_value=pd.to_datetime("1900-01-01").date(),
                    max_value=pd.to_datetime("2100-12-31").date(),
                    format="YYYY/MM/DD",
                    label_visibility="collapsed"
                )
                # 開始日の妥当性チェック
                pre_start_error = check_date_validity(pre_start_date, dataset_min_date, dataset_max_date, "介入前期間の開始日")
                if pre_start_error:
                    st.error(pre_start_error)
                
            with col2:
                st.markdown('<div style="font-weight:bold;margin-bottom:0.3em;">終了日</div>', unsafe_allow_html=True)
                pre_end_date = st.date_input(
                    "pre_end",
                    value=pre_end,
                    # min_valueに制約を設ける（論理的な整合性を保つため）が、max_valueの制約は緩和
                    min_value=pre_start_date,
                    max_value=pd.to_datetime("2100-12-31").date(),
                    format="YYYY/MM/DD",
                    label_visibility="collapsed"
                )
                # 終了日の妥当性チェック
                pre_end_error = check_date_validity(pre_end_date, dataset_min_date, dataset_max_date, "介入前期間の終了日")
                if pre_end_error:
                    st.error(pre_end_error)
            
            # 介入期間の設定
            st.markdown('<div style="font-weight:bold;margin-top:1.5em;margin-bottom:0.5em;font-size:1.15em;">介入期間 (Post-Period)</div>', unsafe_allow_html=True)
            
            # 説明文と警告メッセージを統合
            st.markdown("""
<div style="margin-bottom:1em;">効果を測定する介入後の期間を指定します。
<span style="color:red;font-weight:bold;">※介入期間の開始日は介入前期間の終了日より後の日付を指定する必要があります。</span>
<br><span style="color:#666;font-size:0.9em;">※指定された日付がデータセットに存在しない場合は、分析対象として無効となります。有効な日付を選択してください。</span>
</div>
            """, unsafe_allow_html=True)
            
            # 最小日付は翌日ではなく、データセットの最小日付を設定
            min_post_start = pre_end_date + pd.Timedelta(days=1) if pre_end_date is not None else dataset_min_date
            
            # 推奨開始日（介入前期間の終了日の翌日）を計算 - エラー対策
            try:
                if pre_end_date is not None:
                    suggested_post_start = pre_end_date + pd.Timedelta(days=1)
                else:
                    # pre_end_dateが無効な場合はデータセット最小日付を使用
                    suggested_post_start = dataset_min_date
            except (TypeError, ValueError):
                # エラーが発生した場合もデータセット最小日付を使用
                suggested_post_start = dataset_min_date
            
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
                    # min_valueはデータセットの開始日ではなく、1900年に設定し、max_valueの制約も緩和
                    min_value=pd.to_datetime("1900-01-01").date(),
                    max_value=pd.to_datetime("2100-12-31").date(),
                    format="YYYY/MM/DD",
                    label_visibility="collapsed"
                )
                # 開始日の妥当性チェック - 介入前期間終了日との関係も確認
                post_start_error = check_date_validity(post_start_date, dataset_min_date, dataset_max_date, "介入期間の開始日")
                if post_start_error:
                    st.error(post_start_error)
                elif pre_end_date is not None and post_start_date is not None and post_start_date <= pre_end_date:
                    st.error(f"⚠ 分析期間の設定エラー：介入期間の開始日（{post_start_date}）は、介入前期間の終了日（{pre_end_date}）より後の日付を指定してください。")
                
            with col2:
                st.markdown('<div style="font-weight:bold;margin-bottom:0.3em;">終了日</div>', unsafe_allow_html=True)
                # min_valueに条件付きで値を設定（post_start_dateがNoneの場合の対応）
                post_end_date = st.date_input(
                    "post_end",
                    value=post_end,
                    # min_valueとmax_valueの制約を緩和（実質的な制約を削除）
                    min_value=pd.to_datetime("1900-01-01").date(),
                    max_value=pd.to_datetime("2100-12-31").date(),
                    format="YYYY/MM/DD",
                    label_visibility="collapsed"
                )
                # 終了日の妥当性チェック - post_start_dateとの関係性もチェック
                post_end_error = check_date_validity(post_end_date, dataset_min_date, dataset_max_date, "介入期間の終了日")
                if post_end_error:
                    st.error(post_end_error)
                elif post_start_date is not None and post_end_date is not None and post_end_date < post_start_date:
                    st.error(f"⚠ 分析期間の設定エラー：介入期間の終了日（{post_end_date}）は、介入期間の開始日（{post_start_date}）以降の日付を指定してください。")
            
            # 整合性チェックは上で行うのでここでは削除
            
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
    <th style="padding:8px; text-align:left; border:1px solid #ddd; width:28%;">パラメータ名</th>
    <th style="padding:8px; text-align:left; border:1px solid #ddd; width:57%;">意味</th>
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
    <td style="padding:8px; border:1px solid #ddd;">季節性を考慮する場合に、データのパターンに合わせた周期を選択します。
<ul style="margin-top:0.5em;margin-bottom:0;">
<li><b>週次 (7日)</b>：週単位で繰り返すパターンがある場合（平日と週末の違いなど）</li>
<li><b>旬次 (10日)</b>：上旬・中旬・下旬の周期がある場合</li>
<li><b>月次 (30日)</b>：月単位で繰り返すパターンがある場合（月初・月末の変動など）</li>
<li><b>四半期 (90日)</b>：四半期単位で繰り返すパターンがある場合（決算期の影響など）</li>
<li><b>年次 (365日)</b>：年単位で繰り返すパターンがある場合（季節変動など）</li>
<li><b>カスタム</b>：上記以外の特定の周期がある場合</li>
</ul></td>
    <td style="padding:8px; border:1px solid #ddd; text-align:center;">旬次 (10日)</td>
  </tr>
  <tr style="background-color:#f9fbfd;">
    <td style="padding:8px; border:1px solid #ddd; white-space:nowrap;"><b>水準の事前分布の標準偏差</b></td>
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
<div style="margin-top:1em; font-size:0.9em; color:#555;">
<p>※パラメータはデフォルト設定でも多くの場合適切に動作しますが、データの特性や分析目的に応じて調整することで、より精度の高い分析が可能になります。</p>
</div>
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
            
            st.session_state['analysis_params'] = build_analysis_params(
                alpha,
                seasonality,
                seasonality_type if seasonality else None,
                custom_period if seasonality and seasonality_type == "カスタム" else None,
                prior_level_sd,
                standardize if 'standardize' in locals() else False,
                niter if 'niter' in locals() else 1000
            )
            # params_savedフラグをTrueに設定
            st.session_state['params_saved'] = True
            
            # --- 分析実行 ---
            st.markdown('<div class="section-title">分析実行</div>', unsafe_allow_html=True)
            
            # 分析準備完了メッセージ
            st.success("分析実行の準備が完了しました。以下のボタンをクリックして分析を開始してください。")
            
            # 分析前の日付整合性チェック
            date_error = False
            
            # 入力された日付の妥当性チェック
            invalid_dates = []
            
            # 介入前期間の開始日チェック
            if pre_start_error:
                date_error = True
                invalid_dates.append(f"介入前期間の開始日（{pre_start_date}）")
            
            # 介入前期間の終了日チェック
            if pre_end_error:
                date_error = True
                invalid_dates.append(f"介入前期間の終了日（{pre_end_date}）")
            
            # 介入期間の開始日チェック
            if post_start_error:
                date_error = True
                invalid_dates.append(f"介入期間の開始日（{post_start_date}）")
            
            # 介入期間の終了日チェック
            if post_end_error:
                date_error = True
                invalid_dates.append(f"介入期間の終了日（{post_end_date}）")
            
            # 介入前/介入期間の整合性チェック
            if pre_end_date is not None and post_start_date is not None and post_start_date <= pre_end_date:
                date_error = True
                if not invalid_dates:  # 他のエラーがなければ表示する
                    st.error(f"⚠ 分析期間の設定エラー：介入期間の開始日（{post_start_date}）は、介入前期間の終了日（{pre_end_date}）より後の日付を指定してください。")
                st.markdown('<div style="margin-bottom:1em;color:#d32f2f;font-weight:bold;">分析期間を修正してから分析を実行してください。</div>', unsafe_allow_html=True)
            
            # 日付が対象期間外かどうかを事前にチェック
            pre_start_str = str(pre_start_date) if pre_start_date else ""
            pre_end_str = str(pre_end_date) if pre_end_date else ""
            post_start_str = str(post_start_date) if post_start_date else ""
            post_end_str = str(post_end_date) if post_end_date else ""
            
            # データセットからすべての日付を取得
            all_dates = set(d.date().strftime("%Y-%m-%d") for d in dataset['ymd'])
            
            # 対象期間外または存在しない日付をチェック
            missing_dates = []
            for date_str, date_type in [
                (pre_start_str, "介入前期間の開始日"),
                (pre_end_str, "介入前期間の終了日"),
                (post_start_str, "介入期間の開始日"),
                (post_end_str, "介入期間の終了日")
            ]:
                if date_str and date_str not in all_dates:
                    date_error = True
                    missing_dates.append(f"{date_type}（{date_str}）")
            
            # 対象期間外または存在しない日付がある場合はエラーを表示
            if missing_dates:
                date_error = True
                dates_str = "、".join(missing_dates)
                st.error(f"⚠ 分析期間設定エラー：{dates_str} がデータセットに存在しません。")
                st.markdown("""
<div style="margin-bottom:1.5em;background:#ffebee;padding:1em;border-radius:8px;border-left:4px solid #d32f2f;">
<p style="font-weight:bold;margin-bottom:0.8em;">日付設定の問題：</p>
<ul style="margin-bottom:0;">
  <li>指定された日付はデータセットに存在しません。</li>
  <li>デフォルト設定では、日次データでは暦日が自動的に全て含まれますが、週次・月次などの集計データの場合は、特定の日付のみが有効です。</li>
  <li>現在のデータ集計方法に合わせて、日付を以下のパターンから選択してください：</li>
  <ul>
    <li>日次データ：全ての暦日</li>
    <li>週次データ：同一の曜日（例：毎週月曜日）</li>
    <li>旬次データ：1日、11日、21日</li>
    <li>月次データ：各月の1日</li>
    <li>四半期データ：1月1日、4月1日、7月1日、10月1日</li>
  </ul>
</ul>
</div>
                """, unsafe_allow_html=True)
            
            # min_valueがmax_valueより大きいケースの事前チェック
            # ケース①・④の対応：日付が対象期間外の場合
            if post_start_date and dataset_max_date and post_start_date > dataset_max_date:
                date_error = True
                st.error(f"⚠ 分析期間設定エラー：指定された介入期間の開始日（{post_start_date}）はデータセットの対象期間（～{dataset_max_date}）を超えています。")
                st.markdown(f"""
<div style="margin-bottom:1.5em;background:#ffebee;padding:1em;border-radius:8px;border-left:4px solid #d32f2f;">
<p style="font-weight:bold;margin-bottom:0.8em;">日付設定の問題：</p>
<ul style="margin-bottom:0;">
  <li>指定された介入期間の開始日（{post_start_date}）が対象期間の終了日（{dataset_max_date}）より後の日付になっています。</li>
  <li>対象期間内の日付を選択してください。</li>
</ul>
</div>
                """, unsafe_allow_html=True)
            
            if pre_start_date and dataset_max_date and pre_start_date > dataset_max_date:
                date_error = True
                st.error(f"⚠ 分析期間設定エラー：指定された介入前期間の開始日（{pre_start_date}）はデータセットの対象期間（～{dataset_max_date}）を超えています。")
                st.markdown(f"""
<div style="margin-bottom:1.5em;background:#ffebee;padding:1em;border-radius:8px;border-left:4px solid #d32f2f;">
<p style="font-weight:bold;margin-bottom:0.8em;">日付設定の問題：</p>
<ul style="margin-bottom:0;">
  <li>指定された介入前期間の開始日（{pre_start_date}）が対象期間の終了日（{dataset_max_date}）より後の日付になっています。</li>
  <li>対象期間内の日付を選択してください。</li>
</ul>
</div>
                """, unsafe_allow_html=True)
            
            # 介入前期間終了日と介入期間開始日の整合性チェックを再度確認（冗長だが念のため）
            if pre_end_date and post_start_date and post_start_date <= pre_end_date:
                date_error = True
                if not any([pre_start_error, pre_end_error, post_start_error, post_end_error]):  # 他のエラーがなければ表示
                    st.error(f"⚠ 分析期間の設定エラー：介入期間の開始日（{post_start_date}）は、介入前期間の終了日（{pre_end_date}）より後の日付を指定してください。")
                    st.markdown(f"""
<div style="margin-bottom:1.5em;background:#ffebee;padding:1em;border-radius:8px;border-left:4px solid #d32f2f;">
<p style="font-weight:bold;margin-bottom:0.8em;">日付整合性の問題：</p>
<ul style="margin-bottom:0;">
  <li>介入期間の開始日（{post_start_date}）は、介入前期間の終了日（{pre_end_date}）より後である必要があります。</li>
  <li>分析の前後で期間が重複しないよう、日付を調整してください。</li>
</ul>
</div>
                    """, unsafe_allow_html=True)

            # 介入期間の終了日と開始日の整合性チェック
            if post_end_date and post_start_date and post_end_date < post_start_date:
                date_error = True
                if not any([pre_start_error, pre_end_error, post_start_error, post_end_error]):  # 他のエラーがなければ表示
                    st.error(f"⚠ 分析期間の設定エラー：介入期間の終了日（{post_end_date}）は、開始日（{post_start_date}）以降の日付を指定してください。")
                    st.markdown(f"""
<div style="margin-bottom:1.5em;background:#ffebee;padding:1em;border-radius:8px;border-left:4px solid #d32f2f;">
<p style="font-weight:bold;margin-bottom:0.8em;">日付整合性の問題：</p>
<ul style="margin-bottom:0;">
  <li>介入期間の終了日（{post_end_date}）は、開始日（{post_start_date}）と同じか、それより後の日付である必要があります。</li>
  <li>正しい期間範囲を設定してください。</li>
</ul>
</div>
                    """, unsafe_allow_html=True)
            
            # 分析実行ボタン - エラーの場合は無効化
            if date_error:
                st.button("分析実行", key="analyze_disabled", help="日付設定を修正してから分析を実行してください。", type="primary", use_container_width=True, disabled=True)
                analyze_btn = False
            else:
                analyze_btn = st.button("分析実行", key="analyze", help="Causal Impact分析を実行します。", type="primary", use_container_width=True)
            
            # 分析実行時の処理
            if analyze_btn:
                st.session_state['params_saved'] = True
                with st.spinner("Causal Impact分析を実行中..."):
                    try:
                        # データセットを取得
                        dataset = st.session_state['dataset']
                        treatment_col = [col for col in dataset.columns if '処置群' in col][0]
                        control_col = [col for col in dataset.columns if '対照群' in col][0]
                        
                        # 前処理済みデータを取得
                        data = dataset.set_index('ymd')[[treatment_col, control_col]]
                        
                        # 分析期間を取得
                        period = st.session_state['analysis_period']
                        pre_period = [str(period['pre_start']), str(period['pre_end'])]
                        post_period = [str(period['post_start']), str(period['post_end'])]
                        
                        # 対象期間チェック（以下のチェックは冗長だが念のため残す）
                        all_index = set(str(d.date()) for d in data.index)
                        invalid_dates = []
                        for d in pre_period + post_period:
                            if d not in all_index:
                                invalid_dates.append(d)
                        
                        if invalid_dates:
                            # 存在しない日付がある場合はエラーを表示
                            st.error(f"⚠ 分析期間設定エラー：指定された日付 {', '.join(invalid_dates)} がデータセットに存在しません。")
                            st.markdown("""
<div style="margin-bottom:1.5em;background:#ffebee;padding:1em;border-radius:8px;border-left:4px solid #d32f2f;">
<p style="font-weight:bold;margin-bottom:0.8em;">日付設定の問題：</p>
<ul style="margin-bottom:0;">
  <li>デフォルト設定では、日次データでは暦日が自動的に全て含まれますが、週次・月次などの集計データの場合は、特定の日付のみが有効です。</li>
  <li>現在のデータ集計方法に合わせて、日付を以下のパターンから選択してください：</li>
  <ul>
    <li>日次データ：全ての暦日</li>
    <li>週次データ：同一の曜日（例：毎週月曜日）</li>
    <li>旬次データ：1日、11日、21日</li>
    <li>月次データ：各月の1日</li>
    <li>四半期データ：1月1日、4月1日、7月1日、10月1日</li>
  </ul>
</ul>
</div>
                            """, unsafe_allow_html=True)
                            st.session_state['analysis_completed'] = False
                        else:
                            try:
                                # CausalImpact分析を実行
                                ci, summary, report, fig = run_causal_impact_analysis(data, pre_period, post_period)
                                
                                # 結果の表示
                                alpha = st.session_state['analysis_params']['alpha']
                                alpha_percent = int(alpha * 100)
                                treatment_name = st.session_state['treatment_name']
                                period = st.session_state['analysis_period']
                                
                                st.markdown('<div class="section-title">分析結果サマリー</div>', unsafe_allow_html=True)
                                
                                col1, col2, col3 = st.columns([2,3,2])
                                with col1:
                                    st.markdown(f'**分析対象**：{treatment_name}')
                                with col2:
                                    st.markdown(f'**分析期間**：{period["post_start"].strftime("%Y-%m-%d")} 〜 {period["post_end"].strftime("%Y-%m-%d")}')
                                with col3:
                                    st.markdown(f'**信頼水準**：{alpha_percent}%')
                                
                                # サマリーの表示
                                df_summary = build_summary_dataframe(summary, alpha_percent)
                                
                                # 相対効果の信頼区間行が正しく「同左」になっていることを確認
                                relative_effect_ci_row = f'相対効果 {alpha_percent}% 信頼区間'
                                if relative_effect_ci_row in df_summary.index:
                                    # 確実に「同左」に設定
                                    df_summary.at[relative_effect_ci_row, '分析期間の累積値'] = '同左'
                                    print(f"相対効果の信頼区間行を修正: {relative_effect_ci_row}")
                                
                                # インデックス列に名前を追加
                                df_summary = df_summary.rename_axis('指標')
                                
                                # サマリー表示
                                st.dataframe(df_summary, use_container_width=True)
                                
                                # 指標の説明
                                with st.expander("指標の説明", expanded=False):
                                    st.markdown("""
<table style="width:100%; border-collapse: collapse; margin-top:0.5em; font-size:0.9em;">
  <tr style="background-color:#f0f5fa;">
    <th style="padding:8px; text-align:left; border:1px solid #ddd; width:28%;">指標名</th>
    <th style="padding:8px; text-align:left; border:1px solid #ddd; width:72%;">意味</th>
  </tr>
  <tr>
    <td style="padding:8px; border:1px solid #ddd; white-space:nowrap;"><b>実測値</b></td>
    <td style="padding:8px; border:1px solid #ddd;">介入期間中に実際に観測された応答変数の値です。対象となる処置群の実際の測定値を表します。</td>
  </tr>
  <tr style="background-color:#f9fbfd;">
    <td style="padding:8px; border:1px solid #ddd; white-space:nowrap;"><b>予測値 (標準偏差)</b></td>
    <td style="padding:8px; border:1px solid #ddd;">介入が行われなかった場合に予測される応答値です。括弧内の数値は予測の不確実性を示す標準偏差です。</td>
  </tr>
  <tr>
    <td style="padding:8px; border:1px solid #ddd; white-space:nowrap;"><b>予測値 XX% 信頼区間</b></td>
    <td style="padding:8px; border:1px solid #ddd;">予測値の信頼区間を示します。実際の効果がこの範囲内に収まる確率がXX%であることを意味します。区間は[下限値, 上限値]として表示されます。</td>
  </tr>
  <tr style="background-color:#f9fbfd;">
    <td style="padding:8px; border:1px solid #ddd; white-space:nowrap;"><b>絶対効果 (標準偏差)</b></td>
    <td style="padding:8px; border:1px solid #ddd;">実測値から予測値を引いた差分で、介入による効果の絶対値を示します。プラスの値は正の効果、マイナスの値は負の効果を意味します。括弧内の数値は標準偏差です。</td>
  </tr>
  <tr>
    <td style="padding:8px; border:1px solid #ddd; white-space:nowrap;"><b>絶対効果 XX% 信頼区間</b></td>
    <td style="padding:8px; border:1px solid #ddd;">絶対効果の信頼区間です。この範囲に0が含まれていない場合、効果は統計的に有意と判断できます。区間は[下限値, 上限値]として表示されます。</td>
  </tr>
  <tr style="background-color:#f9fbfd;">
    <td style="padding:8px; border:1px solid #ddd; white-space:nowrap;"><b>相対効果 (標準偏差)</b></td>
    <td style="padding:8px; border:1px solid #ddd;">絶対効果を予測値で割った比率で、効果のパーセンテージを示します。予測値に対して何%の変化があったかを表します。相対効果については、分析期間の平均値の欄に表示しています。</td>
  </tr>
  <tr>
    <td style="padding:8px; border:1px solid #ddd; white-space:nowrap;"><b>相対効果 XX% 信頼区間</b></td>
    <td style="padding:8px; border:1px solid #ddd;">相対効果の信頼区間です。この範囲に0%が含まれていない場合、相対効果は統計的に有意と判断できます。相対効果の信頼区間についても、分析期間の平均値の欄に表示しています。</td>
  </tr>
  <tr style="background-color:#f9fbfd;">
    <td style="padding:8px; border:1px solid #ddd; white-space:nowrap;"><b>p値 (事後確率)</b></td>
    <td style="padding:8px; border:1px solid #ddd;">観測された効果（または、より極端な効果）が単なる偶然で生じる確率です。一般的に0.05未満の場合、効果は統計的に有意と判断されます。数値が小さいほど、効果が偶然ではなく介入によるものである可能性が高いことを示します。p値については、分析期間の平均値の欄に表示しています。</td>
  </tr>
</table>
<div style="margin-top:1em; font-size:0.9em; color:#555;">
<p><b>分析期間の平均値</b>：介入期間中の1日あたりの平均値を示します。</p>
<p><b>分析期間の累積値</b>：介入期間全体での合計値を示します。</p>
<p>※相対効果、相対効果の信頼区間、およびp値については、分析期間の平均値の欄に集約して表示しています。</p>
</div>
                                    """, unsafe_allow_html=True)
                                
                                # グラフの表示
                                plt.tight_layout()
                                st.pyplot(fig)
                                
                                # 詳細レポート
                                with st.expander("詳細レポート"):
                                    report_jp = translate_causal_impact_report(report, alpha)
                                    st.text(report_jp)
                                
                                st.success("Causal Impact分析が完了しました。分析結果のグラフおよびサマリーをご確認のうえ、必要な情報を以下よりダウンロードしてください。")
                                
                                # 分析結果のダウンロードセクション
                                st.markdown('<div class="section-title">分析結果のダウンロード</div>', unsafe_allow_html=True)
                                
                                # utils_step3.pyのダウンロード関数を使用してリンクを生成
                                from utils_step3 import get_summary_csv_download_link, get_figure_pdf_download_link
                                
                                # ダウンロードボタンの表示
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    csv_href, csv_filename = get_summary_csv_download_link(
                                        df_summary, 
                                        treatment_name, 
                                        period["post_start"], 
                                        period["post_end"], 
                                        alpha_percent
                                    )
                                    st.markdown(
                                        f'<a href="{csv_href}" download="{csv_filename}" '
                                        f'class="red-action-button" '
                                        f'style="color:#fff;text-decoration:none;text-align:center;display:inline-block;width:100%;">'
                                        f'分析結果サマリー（CSV）</a>',
                                        unsafe_allow_html=True
                                    )
                                
                                with col2:
                                    pdf_href, pdf_filename = get_figure_pdf_download_link(
                                        fig, 
                                        treatment_name, 
                                        period["post_start"], 
                                        period["post_end"]
                                    )
                                    st.markdown(
                                        f'<a href="{pdf_href}" download="{pdf_filename}" '
                                        f'class="red-action-button" '
                                        f'style="color:#fff;text-decoration:none;text-align:center;display:inline-block;width:100%;">'
                                        f'分析結果グラフ（PDF）</a>',
                                        unsafe_allow_html=True
                                    )
                                
                                # 終了メッセージの追加
                                st.markdown('<div style="margin-top:25px;"></div>', unsafe_allow_html=True)
                                st.success("これでCausal Impactの分析は終了です。\n新たなデータで再度分析を行う場合は、サイドバーの「最初からやり直す」ボタン、または画面左上の更新（Ctrl + R）をクリックし、STEP1「データ取込／可視化」から再実行してください。")
                                
                                st.session_state['analysis_completed'] = True
                                
                            except ValueError as e:
                                # ValueErrorの場合（例：日付フォーマットエラーなど）
                                error_msg = str(e)
                                st.error(f"分析エラー：{error_msg}")
                                st.markdown("""
<div style="margin-bottom:1.5em;background:#ffebee;padding:1em;border-radius:8px;border-left:4px solid #d32f2f;">
<p style="font-weight:bold;margin-bottom:0.8em;">分析エラー：</p>
<p>分析期間の設定に問題があります。日付が正しく設定されているか確認してください。</p>
<ul>
  <li>介入前期間と介入期間の日付が正しく設定されているか確認してください。</li>
  <li>介入期間の開始日は介入前期間の終了日より後の日付である必要があります。</li>
  <li>指定された日付がデータセットに存在するか確認してください。</li>
</ul>
</div>
                                """, unsafe_allow_html=True)
                                st.session_state['analysis_completed'] = False
                                
                            except Exception as e:
                                # その他の例外
                                error_msg = str(e)
                                st.error(f"Causal Impact分析中にエラーが発生しました: {error_msg}")
                                st.session_state['analysis_completed'] = False
                    except Exception as e:
                        st.error(f"Causal Impact分析中にエラーが発生しました: {e}")
                        st.session_state['analysis_completed'] = False

else:
    st.info("処置群・対照群のCSVファイルを選択し、「データを読み込む」ボタンを押してください。") 