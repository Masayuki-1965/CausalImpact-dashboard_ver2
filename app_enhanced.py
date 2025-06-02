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

# 外部モジュールimport
from causal_impact_translator import translate_causal_impact_report
from utils_step1 import get_csv_files, load_and_clean_csv, make_period_key, aggregate_df, create_full_period_range, format_stats_with_japanese
from utils_step2 import get_period_defaults, validate_periods, calc_period_days, build_analysis_params
from utils_step3 import run_causal_impact_analysis, build_summary_dataframe, get_summary_csv_download_link, get_figure_pdf_download_link, get_detail_csv_download_link, build_enhanced_summary_table, get_metrics_explanation_table, get_analysis_summary_message
from utils_step3_single_group import (
    run_single_group_causal_impact_analysis, 
    validate_single_group_data, 
    suggest_intervention_point,
    build_single_group_summary_dataframe,
    get_single_group_interpretation
)

# リファクタリング後の外部モジュール
from config.constants import PAGE_CONFIG, CUSTOM_CSS_PATH
from config.help_texts import (
    DATA_FORMAT_GUIDE_HTML, FAQ_CAUSAL_IMPACT, FAQ_STATE_SPACE_MODEL,
    HEADER_CARD_HTML, STEP1_CARD_HTML, STEP2_CARD_HTML, STEP3_CARD_HTML,
    RESET_GUIDE_HTML, SIDEBAR_FLOW_DESCRIPTION
)
from utils_common import load_css, initialize_session_state, reset_session_state, get_step_status

# --- 初期化 ---
initialize_session_state()

# セッション状態に分析タイプを追加
if 'analysis_type' not in st.session_state:
    st.session_state.analysis_type = "標準分析（処置群 + 対照群）"

# --- 画面幅を最大化 ---
st.set_page_config(**PAGE_CONFIG)

# --- カスタムCSS読み込み ---
load_css(CUSTOM_CSS_PATH)

# --- サイドバー ---
with st.sidebar:
    st.markdown('<div class="sidebar-title">分析フロー</div>', unsafe_allow_html=True)
    st.markdown(SIDEBAR_FLOW_DESCRIPTION, unsafe_allow_html=True)
    
    # STEPのアクティブ状態を取得
    step_status = get_step_status()
    
    st.markdown(f"""
    <div style="margin-top:0.5em;">
        <div class="{'sidebar-step-active' if step_status['step1'] else 'sidebar-step-inactive'}">STEP 1：データ取り込み／可視化</div>
        <div class="{'sidebar-step-active' if step_status['step2'] else 'sidebar-step-inactive'}">STEP 2：分析期間／パラメータ設定</div>
        <div class="{'sidebar-step-active' if step_status['step3'] else 'sidebar-step-inactive'}">STEP 3：分析実行／結果確認</div>
    </div>
    <div class="separator-line"></div>
    """, unsafe_allow_html=True)
    
    # 最初からやり直す案内文
    st.markdown('<div style="margin-top:15px;margin-bottom:10px;"></div>', unsafe_allow_html=True)
    st.markdown(RESET_GUIDE_HTML, unsafe_allow_html=True)

    with st.expander("Causal Impactとは？", expanded=False):
        st.markdown(FAQ_CAUSAL_IMPACT, unsafe_allow_html=True)
    with st.expander("状態空間モデルとは？", expanded=False):
        st.markdown(FAQ_STATE_SPACE_MODEL, unsafe_allow_html=True)

# --- メインコンテンツ ---
st.markdown(HEADER_CARD_HTML, unsafe_allow_html=True)

st.markdown(STEP1_CARD_HTML, unsafe_allow_html=True)

# --- データ形式ガイド ---
with st.expander("データ形式ガイド", expanded=False):
    st.markdown(DATA_FORMAT_GUIDE_HTML, unsafe_allow_html=True)

# --- ファイル選択UIの代わりにファイルアップロード機能 ---
st.markdown('<div class="section-title">分析対象ファイルのアップロード</div>', unsafe_allow_html=True)

# 分析タイプの選択
st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">分析タイプの選択</div>', unsafe_allow_html=True)
analysis_type = st.radio(
    "分析タイプ選択",
    options=["二群比較（処置群＋対照群を使用）", "単群推定（処置群のみを使用）"],
    index=0,
    label_visibility="collapsed",
    help="二群比較は処置群と対照群の両方を比較します。単群推定は処置群のみで介入前後のトレンド変化を分析します。"
)

# 分析タイプをセッション状態に保存
st.session_state.analysis_type = analysis_type

# 分析タイプによって説明を表示
if analysis_type == "単群推定（処置群のみを使用）":
    st.info("単群推定では、介入前のデータから季節性やトレンドを学習し、介入後の予測値（反事実シナリオ）と実測値を比較して効果を測定します。")
else:
    st.info("二群比較では、介入の影響を受けた処置群と影響を受けていない対照群の関係性をもとに、介入後の予測値と実測値を比較して効果を測定します。")

# アップロード方法切り替えのラジオボタン
st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;margin-top:1em;">アップロード方法の選択</div>', unsafe_allow_html=True)
upload_method = st.radio(
    "アップロード方法選択",
    options=["ファイルアップロード（推奨）", "CSVテキスト直接入力"],
    index=0,
    label_visibility="collapsed",
    help="CSVデータを直接入力する方法と、ファイルをアップロードする方法があります。"
)

# 変数の初期化（エラー防止）
treatment_file = None
control_file = None
treatment_csv = ""
control_csv = ""
treatment_name = "処置群"
control_name = "対照群"
read_btn_upload = False
read_btn_text = False
read_btn_single_upload = False
read_btn_single_text = False

# 分析タイプに応じてUIを切り替え
if analysis_type == "二群比較（処置群＋対照群を使用）":
    # 既存の標準分析UI
    if upload_method == "ファイルアップロード（推奨）":
        # 処置群と対照群の名称入力欄（ファイルアップロード・CSVテキスト共通）
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">処置群データ</div>', unsafe_allow_html=True)
            
            treatment_file = st.file_uploader(
                "処置群のCSVファイルをアップロード", 
                type=['csv'], 
                key="treatment_upload", 
                help="処置群（効果を測定したい対象）のCSVファイルをアップロードしてください。",
                accept_multiple_files=False,
                label_visibility="collapsed"
            )
            
            if treatment_file:
                file_basename = os.path.splitext(treatment_file.name)[0]
                treatment_name = file_basename
                selected_treat = f"選択：{treatment_file.name}（処置群）"
                st.markdown(f'<div style="color:#1976d2;font-size:0.9em;">{selected_treat}</div>', unsafe_allow_html=True)
            else:
                treatment_name = "処置群"
                
            treatment_name = st.text_input("処置群の名称を入力", value=treatment_name, key="treatment_name_upload", help="処置群の名称を入力してください（例：商品A、店舗B など）")
            
        with col2:
            st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">対照群データ</div>', unsafe_allow_html=True)
            
            control_file = st.file_uploader(
                "対照群のCSVファイルをアップロード", 
                type=['csv'], 
                key="control_upload", 
                help="対照群（比較対象）のCSVファイルをアップロードしてください。",
                accept_multiple_files=False,
                label_visibility="collapsed"
            )
            
            if control_file:
                file_basename = os.path.splitext(control_file.name)[0]
                control_name = file_basename
                selected_ctrl = f"選択：{control_file.name}（対照群）"
                st.markdown(f'<div style="color:#1976d2;font-size:0.9em;">{selected_ctrl}</div>', unsafe_allow_html=True)
            else:
                control_name = "対照群"
                
            control_name = st.text_input("対照群の名称を入力", value=control_name, key="control_name_upload", help="対照群の名称を入力してください（例：商品B、店舗C など）")
        
        # データ読み込みボタン（標準分析・ファイルアップロード用）
        st.markdown('<div style="margin-top:25px;"></div>', unsafe_allow_html=True)
        read_btn_upload = st.button("データを読み込む", key="read_upload", help="アップロードしたファイルを読み込みます。", type="primary", use_container_width=True, disabled=(not treatment_file or not control_file))

    else:
        # CSVテキスト直接入力のUI（標準分析）
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">処置群データ</div>', unsafe_allow_html=True)
            treatment_name = st.text_input("処置群の名称を入力", value="処置群", key="treatment_name_text", help="処置群の名称を入力してください（例：商品A、店舗B など）")
            
            treatment_csv = st.text_area(
                "CSVデータを入力（カンマ・タブ・スペース区切り）",
                height=200,
                help="CSVデータを直接入力またはコピペしてください。最低限、ymd（日付）とqty（数量）の列が必要です。",
                placeholder="ymd,qty\n20170403,29\n20170425,24\n20170426,23\n20170523,24\n20170524,26"
            )
            st.markdown('<div style="color:#555555;font-size:0.9em;margin-top:-5px;margin-bottom:15px;padding-left:5px;">（上の入力欄にCSVデータをコピペしてください）</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">対照群データ</div>', unsafe_allow_html=True)
            control_name = st.text_input("対照群の名称を入力", value="対照群", key="control_name_text", help="対照群の名称を入力してください（例：商品B、店舗C など）")
            
            control_csv = st.text_area(
                "CSVデータを入力（カンマ・タブ・スペース区切り）",
                height=200,
                help="CSVデータを直接入力またはコピペしてください。最低限、ymd（日付）とqty（数量）の列が必要です。",
                placeholder="ymd,qty\n20170403,35\n20170425,30\n20170426,28\n20170523,29\n20170524,31"
            )
            st.markdown('<div style="color:#555555;font-size:0.9em;margin-top:-5px;margin-bottom:15px;padding-left:5px;">（上の入力欄にCSVデータをコピペしてください）</div>', unsafe_allow_html=True)
        
        # データ読み込みボタン（標準分析・CSVテキスト直接入力用）
        st.markdown('<div style="margin-top:25px;"></div>', unsafe_allow_html=True)
        read_btn_text = st.button("データを読み込む", key="read_text", help="入力したCSVデータを読み込みます。", type="primary", use_container_width=True, disabled=(not treatment_csv or not control_csv))

else:
    # 単群推定UI
    if upload_method == "ファイルアップロード（推奨）":
        st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">処置群データ</div>', unsafe_allow_html=True)
        
        treatment_file = st.file_uploader(
            "処置群のCSVファイルをアップロード", 
            type=['csv'], 
            key="treatment_single_upload", 
            help="処置群（効果を測定したい対象）のCSVファイルをアップロードしてください。",
            accept_multiple_files=False,
            label_visibility="collapsed"
        )
        
        if treatment_file:
            file_basename = os.path.splitext(treatment_file.name)[0]
            treatment_name = file_basename
            selected_treat = f"選択：{treatment_file.name}（単群推定）"
            st.markdown(f'<div style="color:#1976d2;font-size:0.9em;">{selected_treat}</div>', unsafe_allow_html=True)
        else:
            treatment_name = "処置群"
            
        treatment_name = st.text_input("処置群の名称を入力", value=treatment_name, key="treatment_name_single_upload", help="処置群の名称を入力してください（例：商品A、店舗B など）")
        
        # データ読み込みボタン（処置群のみ・ファイルアップロード用）
        st.markdown('<div style="margin-top:25px;"></div>', unsafe_allow_html=True)
        read_btn_single_upload = st.button("データを読み込む", key="read_single_upload", help="アップロードしたファイルを読み込みます。", type="primary", use_container_width=True, disabled=(not treatment_file))

    else:
        # CSVテキスト直接入力のUI（処置群のみ）
        st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">処置群データ</div>', unsafe_allow_html=True)
        treatment_name = st.text_input("処置群の名称を入力", value="処置群", key="treatment_name_single_text", help="処置群の名称を入力してください（例：商品A、店舗B など）")
        
        treatment_csv = st.text_area(
            "CSVデータを入力（カンマ・タブ・スペース区切り）",
            height=300,
            help="CSVデータを直接入力またはコピペしてください。最低限、ymd（日付）とqty（数量）の列が必要です。単群推定では最低37日間のデータが推奨されます。",
            placeholder="ymd,qty\n20170403,29\n20170425,24\n20170426,23\n20170523,24\n20170524,26\n...\n（介入前後を含む十分なデータを入力）"
        )
        st.markdown('<div style="color:#555555;font-size:0.9em;margin-top:-5px;margin-bottom:15px;padding-left:5px;">（最低37日間のデータを推奨、介入前期間は全体の60%以上が必要）</div>', unsafe_allow_html=True)
        
        # データ読み込みボタン（処置群のみ・CSVテキスト直接入力用）
        st.markdown('<div style="margin-top:25px;"></div>', unsafe_allow_html=True)
        read_btn_single_text = st.button("データを読み込む", key="read_single_text", help="入力したCSVデータを読み込みます。", type="primary", use_container_width=True, disabled=(not treatment_csv))

# --- アップロードされたファイルからデータを読み込む関数 ---
def load_and_clean_uploaded_csv(uploaded_file):
    try:
        # ファイル名をログに出力（デバッグ用）
        file_name = uploaded_file.name
        print(f"処理中のファイル: {file_name}")
        
        # バイト列を読み込み
        file_bytes = uploaded_file.getvalue()
        
        # エンコーディング検出の試行回数を増やす
        encodings = ['utf-8', 'shift-jis', 'cp932', 'euc-jp', 'iso-2022-jp', 'latin1']
        df = None
        
        # 方法1: 直接StringIOを使用
        for encoding in encodings:
            try:
                # エンコーディングを設定して読み込み試行
                content = file_bytes.decode(encoding)
                # テスト用に先頭行だけ解析
                test_df = pd.read_csv(io.StringIO(content.split('\n', 5)[0]), nrows=1)
                # 成功したらすべてを読み込む
                df = pd.read_csv(io.StringIO(content))
                print(f"正常に読み込み: エンコーディング {encoding}")
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"エラー（{encoding}）: {str(e)}")
                continue
        
        # どのエンコーディングでも読み込めなかった場合
        if df is None:
            try:
                # 方法2: BytesIOを直接使用
                df = pd.read_csv(io.BytesIO(file_bytes))
                print("BytesIOを使用して正常に読み込み")
            except Exception as e2:
                try:
                    # 方法3: tempfileを使用（ファイル名に依存しない処理）
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
                        tmp_file.write(file_bytes)
                        tmp_path = tmp_file.name
                    
                    # 一時ファイルから読み込む
                    df = pd.read_csv(tmp_path)
                    # 読み込み後に一時ファイルを削除
                    os.unlink(tmp_path)
                    print("一時ファイルを使用して正常に読み込み")
                except Exception as e3:
                    print(f"全ての読み込み方法が失敗: {str(e2)}, {str(e3)}")
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
                st.info(f"カラム名を自動設定しました: {df.columns[0]} → ymd, {df.columns[1]} → qty")
            else:
                st.error(f"必須カラム 'ymd' と 'qty' が見つかりません。")
                return None
        
        # 日付の処理
        df['ymd'] = df['ymd'].astype(str).str.zfill(8)
        try:
            # まず%Y%m%d形式で変換を試行
            df['ymd'] = pd.to_datetime(df['ymd'], format='%Y%m%d', errors='coerce')
        except:
            try:
                # 失敗した場合は自動推定で変換
                df['ymd'] = pd.to_datetime(df['ymd'], errors='coerce')
            except:
                st.error("日付列の変換に失敗しました。YYYYMMDD形式で入力してください。")
                return None
        
        # 無効な日付をチェック
        invalid_dates = df[df['ymd'].isna()]
        if not invalid_dates.empty:
            st.warning(f"{len(invalid_dates)}行の日付が無効なため除外されました。YYYYMMDD形式（例：20240101）で入力してください。")
            df = df.dropna(subset=['ymd'])
        
        # 欠損値を除外
        original_len = len(df)
        df = df.dropna(subset=['ymd'])
            
        # qty列の数値変換確認
        try:
            df['qty'] = pd.to_numeric(df['qty'], errors='coerce')
            if df['qty'].isna().any():
                st.warning(f"{df['qty'].isna().sum()}行の数量(qty)が数値に変換できないため除外されました。")
                df = df.dropna(subset=['qty'])
        except Exception as e:
            st.error(f"数量(qty)の処理中にエラーが発生しました。")
            return None
        
        if len(df) == 0:
            st.error("処理後のデータが0行になりました。データを確認してください。")
            return None
            
        return df
    except Exception as e:
        st.error(f"ファイルの処理中にエラーが発生しました: {str(e)}")
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
        try:
            # まず%Y%m%d形式で変換を試行
            df['ymd'] = pd.to_datetime(df['ymd'], format='%Y%m%d', errors='coerce')
        except:
            try:
                # 失敗した場合は自動推定で変換
                df['ymd'] = pd.to_datetime(df['ymd'], errors='coerce')
            except:
                st.error("日付列の変換に失敗しました。YYYYMMDD形式で入力してください。")
                return None
        
        # 無効な日付をチェック
        invalid_dates = df[df['ymd'].isna()]
        if not invalid_dates.empty:
            st.warning(f"{len(invalid_dates)}行の日付が無効なため除外されました。YYYYMMDD形式（例：20240101）で入力してください。")
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

# --- 処置群のみ分析用データセット作成関数 ---
def create_single_group_dataset(df_treat, treatment_name, freq_option):
    """
    処置群のみのデータからデータセットを作成する関数
    """
    try:
        # データフレームの集計
        agg_treat = aggregate_df(df_treat, freq_option)
        
        # 全期間の範囲を生成（処置群のみの場合）
        # 処置群のデータから開始日と終了日を取得
        df_dates = pd.to_datetime(df_treat['ymd'])
        start_date = df_dates.min()
        end_date = df_dates.max()
        
        if freq_option == "月次":
            # 月の初日のシーケンスを生成
            all_periods = pd.date_range(
                start=start_date.replace(day=1),
                end=end_date.replace(day=1),
                freq='MS'  # Month Start
            )
        elif freq_option == "旬次":
            # 旬区切りの日付リストを作成（utils_step1.pyと同じロジック）
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
            all_periods = pd.DatetimeIndex(periods)
        else:  # 日次
            all_periods = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # 全期間のインデックスを作成し、データをゼロ埋め
        all_periods_df = pd.DataFrame(index=all_periods)
        all_periods_df.index.name = 'period'
        
        # データフレームとマージしてゼロ埋め
        agg_treat_full = pd.merge(
            all_periods_df, 
            agg_treat.set_index('period'), 
            how='left', 
            left_index=True, 
            right_index=True
        ).fillna(0)
        
        # 最終データセット作成（処置群のみ）
        dataset = pd.DataFrame({
            'ymd': all_periods,
            f'処置群（{treatment_name}）': agg_treat_full['qty'].values
        })
        
        return dataset
        
    except Exception as e:
        st.error(f"処置群のみデータセット作成でエラーが発生しました: {str(e)}")
        return None

# --- 二群比較のファイルアップロード後のデータ読み込み ---
if analysis_type == "二群比較（処置群＋対照群を使用）":
    if upload_method == "ファイルアップロード（推奨）" and read_btn_upload and treatment_file and control_file:
        with st.spinner("データ読み込み中..."):
            try:
                # Streamlit Cloud環境かどうかを確認（環境変数などで判定可能）
                is_cloud_env = os.environ.get('STREAMLIT_SHARING_MODE') == 'streamlit_sharing'
                
                # セーフティチェック - ファイルサイズの確認
                if treatment_file.size > 5 * 1024 * 1024 or control_file.size > 5 * 1024 * 1024:
                    st.error("ファイルサイズが大きすぎます。5MB以下のファイルを使用してください。")
                    df_treat = None
                    df_ctrl = None
                else:
                    # ファイルのシーク位置をリセット（複数回読み込む可能性があるため）
                    treatment_file.seek(0)
                    
                    # 日本語ファイル名チェック
                    if any(ord(c) > 127 for c in treatment_file.name) and is_cloud_env:
                        st.error(f"Streamlit Cloud環境では日本語を含むファイル名（{treatment_file.name}）はサポートされていません。英数字のファイル名に変更してください。")
                        df_treat = None
                    else:
                        # 処置群ファイルの読み込み試行
                        df_treat = load_and_clean_uploaded_csv(treatment_file)
                    
                    # 処置群ファイルが読み込めた場合のみ対照群ファイルを読み込む
                    if df_treat is not None:
                        # ファイルのシーク位置をリセット
                        control_file.seek(0)
                        
                        # 日本語ファイル名チェック
                        if any(ord(c) > 127 for c in control_file.name) and is_cloud_env:
                            st.error(f"Streamlit Cloud環境では日本語を含むファイル名（{control_file.name}）はサポートされていません。英数字のファイル名に変更してください。")
                            df_ctrl = None
                        else:
                            # 対照群ファイルの読み込み試行
                            df_ctrl = load_and_clean_uploaded_csv(control_file)
                    else:
                        df_ctrl = None
                        st.error("処置群ファイルの読み込みに失敗したため、対照群ファイルの読み込みをスキップします。")
                
                if df_treat is not None and df_ctrl is not None and not df_treat.empty and not df_ctrl.empty:
                    # セッションに保存（ユーザーが入力した名称を使用）
                    st.session_state['df_treat'] = df_treat
                    st.session_state['df_ctrl'] = df_ctrl
                    # 名前が空でなければユーザー入力値を使用、空なら処理名をデフォルト値に
                    treatment_name = treatment_name.strip() if treatment_name and treatment_name.strip() else "処置群"
                    control_name = control_name.strip() if control_name and control_name.strip() else "対照群"
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
                    st.info("CSVテキスト直接入力をご利用ください。以下は入力例です：\n\nymd,qty\n20170403,29\n20170425,24\n...")
            except Exception as e:
                st.error(f"データ読み込み中に予期しないエラーが発生しました: {str(e)}")
                st.session_state['data_loaded'] = False
                
                # 代替入力方法の提案
                st.info("CSVテキスト直接入力をご利用ください。以下は入力例です：\n\nymd,qty\n20170403,29\n20170425,24\n...")

    # --- 二群比較のテキスト入力からのデータ読み込み ---
    elif upload_method == "CSVテキスト直接入力" and read_btn_text:
        with st.spinner("データ読み込み中..."):
            df_treat = load_and_clean_csv_text(treatment_csv, "処置群")
            df_ctrl = load_and_clean_csv_text(control_csv, "対照群")
            
            if df_treat is not None and df_ctrl is not None and not df_treat.empty and not df_ctrl.empty:
                # セッションに保存（ユーザーが入力した名称を使用）
                st.session_state['df_treat'] = df_treat
                st.session_state['df_ctrl'] = df_ctrl
                # 名前が空でなければユーザー入力値を使用、空なら処理名をデフォルト値に
                treatment_name = treatment_name.strip() if treatment_name and treatment_name.strip() else "処置群"
                control_name = control_name.strip() if control_name and control_name.strip() else "対照群"
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

# --- 単群推定のデータ読み込み ---
else:  # analysis_type == "単群推定（処置群のみを使用）"
    if upload_method == "ファイルアップロード（推奨）" and read_btn_single_upload and treatment_file:
        with st.spinner("処置群のみデータ読み込み中..."):
            try:
                # Streamlit Cloud環境かどうかを確認
                is_cloud_env = os.environ.get('STREAMLIT_SHARING_MODE') == 'streamlit_sharing'
                
                # セーフティチェック - ファイルサイズの確認
                if treatment_file.size > 5 * 1024 * 1024:
                    st.error("ファイルサイズが大きすぎます。5MB以下のファイルを使用してください。")
                    df_treat = None
                else:
                    # ファイルのシーク位置をリセット
                    treatment_file.seek(0)
                    
                    # 日本語ファイル名チェック
                    if any(ord(c) > 127 for c in treatment_file.name) and is_cloud_env:
                        st.error(f"Streamlit Cloud環境では日本語を含むファイル名（{treatment_file.name}）はサポートされていません。英数字のファイル名に変更してください。")
                        df_treat = None
                    else:
                        # 処置群ファイルの読み込み試行
                        df_treat = load_and_clean_uploaded_csv(treatment_file)
                
                if df_treat is not None and not df_treat.empty:
                    # 処置群のみ分析用データ検証
                    is_valid, error_msg = validate_single_group_data(df_treat)
                    
                    if is_valid:
                        # セッションに保存（処置群のみ）
                        st.session_state['df_treat'] = df_treat
                        st.session_state['df_ctrl'] = None  # 対照群なし
                        treatment_name = treatment_name.strip() if treatment_name and treatment_name.strip() else "処置群"
                        st.session_state['treatment_name'] = treatment_name
                        st.session_state['control_name'] = None
                        st.session_state['data_loaded'] = True
                        st.session_state['analysis_type'] = "単群推定（処置群のみを使用）"  # 分析タイプを明示的に保存
                        st.success("処置群のみデータを読み込みました。下記にプレビューと統計情報を表示します。")
                    else:
                        st.error(f"データ検証エラー: {error_msg}")
                        st.session_state['data_loaded'] = False
                else:
                    st.error("処置群ファイルの読み込みに失敗しました。CSVファイルの形式を確認してください。")
                    st.session_state['data_loaded'] = False
                
            except Exception as e:
                st.error(f"処置群のみデータ読み込み中に予期しないエラーが発生しました: {str(e)}")
                st.session_state['data_loaded'] = False

    elif upload_method == "CSVテキスト直接入力" and read_btn_single_text:
        with st.spinner("処置群のみデータ読み込み中..."):
            df_treat = load_and_clean_csv_text(treatment_csv, "処置群")
            
            if df_treat is not None and not df_treat.empty:
                # 処置群のみ分析用データ検証
                is_valid, error_msg = validate_single_group_data(df_treat)
                
                if is_valid:
                    # セッションに保存（処置群のみ）
                    st.session_state['df_treat'] = df_treat
                    st.session_state['df_ctrl'] = None  # 対照群なし
                    treatment_name = treatment_name.strip() if treatment_name and treatment_name.strip() else "処置群"
                    st.session_state['treatment_name'] = treatment_name
                    st.session_state['control_name'] = None
                    st.session_state['data_loaded'] = True
                    st.session_state['analysis_type'] = "単群推定（処置群のみを使用）"  # 分析タイプを明示的に保存
                    st.success("処置群のみデータを読み込みました。下記にプレビューと統計情報を表示します。")
                else:
                    st.error(f"データ検証エラー: {error_msg}")
                    st.session_state['data_loaded'] = False
            else:
                st.error("処置群データの読み込みに失敗しました。入力したCSVデータの形式を確認してください。")
                st.session_state['data_loaded'] = False

# --- データ読み込み済みなら表示（セッションから取得） ---
if st.session_state.get('data_loaded', False):
    df_treat = st.session_state['df_treat']
    df_ctrl = st.session_state.get('df_ctrl', None)  # 処置群のみ分析では None
    treatment_name = st.session_state['treatment_name']
    control_name = st.session_state.get('control_name', None)
    current_analysis_type = st.session_state.get('analysis_type', analysis_type)
    
    # --- データプレビュー ---
    if current_analysis_type == "二群比較（処置群＋対照群を使用）" and df_ctrl is not None:
        st.markdown('<div class="section-title">読み込みデータのプレビュー（上位10件表示）</div>', unsafe_allow_html=True)
        # 二群比較の場合（処置群 + 対照群）
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f'<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">処置群（{treatment_name}）</div>', unsafe_allow_html=True)
            preview_df_treat = df_treat[['ymd', 'qty']].head(10).copy()
            preview_df_treat['ymd'] = preview_df_treat['ymd'].dt.strftime('%Y-%m-%d')
            preview_df_treat.index = range(1, len(preview_df_treat) + 1)
            st.dataframe(preview_df_treat, use_container_width=True)
        with col2:
            st.markdown(f'<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">対照群（{control_name}）</div>', unsafe_allow_html=True)
            preview_df_ctrl = df_ctrl[['ymd', 'qty']].head(10).copy()
            preview_df_ctrl['ymd'] = preview_df_ctrl['ymd'].dt.strftime('%Y-%m-%d')
            preview_df_ctrl.index = range(1, len(preview_df_ctrl) + 1)
            st.dataframe(preview_df_ctrl, use_container_width=True)
    else:
        # 単群推定の場合
        # データプレビューと統計情報を横並びで表示
        st.markdown('<div class="section-title">読み込みデータのプレビューと統計情報</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">データプレビュー（上位10件表示）</div>', unsafe_allow_html=True)
            preview_df_treat = df_treat[['ymd', 'qty']].head(10).copy()
            preview_df_treat['ymd'] = preview_df_treat['ymd'].dt.strftime('%Y-%m-%d')
            preview_df_treat.index = range(1, len(preview_df_treat) + 1)
            st.dataframe(preview_df_treat, use_container_width=True)
        with col2:
            st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">統計情報</div>', unsafe_allow_html=True)
            if 'qty' in df_treat.columns:
                stats_treat = format_stats_with_japanese(df_treat[['qty']])
                st.dataframe(stats_treat, use_container_width=True, hide_index=True)
            else:
                st.error("データに 'qty' カラムが見つかりません")
        
        # データ量の簡潔な表示（統計情報表の下に移動）
        total_days = len(df_treat)
        if total_days >= 36:
            st.success(f"✅ データ量：{total_days}件（分析に十分なデータ量が確保されています）")
        else:
            st.warning(f"⚠️ データ量：{total_days}件（より信頼性の高い分析のため、36件以上のデータを推奨します）")

    # --- 統計情報（二群比較のみ） ---
    if current_analysis_type == "二群比較（処置群＋対照群を使用）" and df_ctrl is not None:
        st.markdown('<div class="section-title">データの統計情報</div>', unsafe_allow_html=True)
        
        # 二群比較の統計情報表示
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
        
        # データ量の簡潔な表示（統計情報表の下に移動）
        treat_days = len(df_treat)
        ctrl_days = len(df_ctrl)
        min_days = min(treat_days, ctrl_days)
        if min_days >= 24:
            st.success(f"✅ データ量：処置群{treat_days}件、対照群{ctrl_days}件（分析に十分なデータ量が確保されています）")
        else:
            st.warning(f"⚠️ データ量：処置群{treat_days}件、対照群{ctrl_days}件（より信頼性の高い分析のため、24件以上のデータを推奨します）")

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
    # データ集計方法をセッションに保存
    st.session_state['freq_option'] = freq_option
    with col2:
        if freq_option == "月次":
            st.markdown("""
<div style="font-size:0.98em;margin-top:0.1em;padding-left:0;">
<span style="font-weight:bold;">月次集計：</span>月単位で集計し、日付はその月の1日になります<br>
<span style="font-weight:normal;color:#666;">旬次集計：</span>月を上旬・中旬・下旬に3分割して集計し、日付はそれぞれ1日（上旬）、11日（中旬）、21日（下旬）になります<br>
</div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
<div style="font-size:0.98em;margin-top:0.1em;padding-left:0;">
<span style="font-weight:normal;color:#666;">月次集計：</span>月単位で集計し、日付はその月の1日になります<br>
<span style="font-weight:bold;">旬次集計：</span>月を上旬・中旬・下旬に3分割して集計し、日付はそれぞれ1日（上旬）、11日（中旬）、21日（下旬）になります<br>
</div>
            """, unsafe_allow_html=True)
    
    # 「データセットを作成する」ボタンの上に余白を追加
    st.markdown('<div style="margin-top:25px;"></div>', unsafe_allow_html=True)
    create_btn = st.button("データセットを作成する", key="create", help="Causal Impact分析用データセットを作成します。", type="primary", use_container_width=True)
    
    if create_btn or ('dataset_created' in st.session_state and st.session_state['dataset_created']):
        if create_btn:  # 新しくデータセットを作成する場合のみ実行
            if current_analysis_type == "二群比較（処置群＋対照群を使用）" and df_ctrl is not None:
                # 二群比較のデータセット作成（既存ロジック）
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
                    f'対照群（{control_name}）': agg_ctrl_full['qty'].values
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
            else:
                # 処置群のみ分析のデータセット作成
                dataset = create_single_group_dataset(df_treat, treatment_name, freq_option)
                
                if dataset is not None:
                    # データ期間情報を保存（処置群のみ）
                    treat_period = f"{df_treat['ymd'].min().strftime('%Y/%m/%d')} ～ {df_treat['ymd'].max().strftime('%Y/%m/%d')}"
                    st.session_state['period_info'] = {
                        'treat_period': treat_period,
                        'ctrl_period': None,  # 処置群のみ分析では対照群なし
                        'common_period': treat_period  # 処置群のみの期間
                    }
                else:
                    st.error("単群推定用データセットの作成に失敗しました。")
                    dataset = None
            
            if dataset is not None:
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
                
                # 単群推定の場合は推奨介入ポイントを使用
                if current_analysis_type == "単群推定（処置群のみを使用）":
                    try:
                        suggested_date, _, _ = suggest_intervention_point(df_treat)
                        # suggested_dateが日付型かどうかを確認
                        if hasattr(suggested_date, 'date'):
                            suggested_date_obj = suggested_date.date() if hasattr(suggested_date, 'date') else suggested_date
                        elif isinstance(suggested_date, str) and suggested_date != "エラー：推奨日計算失敗":
                            try:
                                suggested_date_obj = pd.to_datetime(suggested_date).date()
                            except:
                                suggested_date_obj = None
                        else:
                            suggested_date_obj = None
                        
                        if suggested_date_obj is not None:
                            # 推奨介入ポイントをセッションに保存
                            st.session_state['suggested_intervention_date'] = pd.to_datetime(suggested_date_obj)
                            
                            # データセット内で推奨日に最も近い日付を見つける
                            dataset_dates = dataset['ymd'].dt.date
                            closest_idx = (dataset_dates - suggested_date_obj).abs().idxmin()
                            suggested_dataset_date = dataset.iloc[closest_idx]['ymd'].date()
                            
                            # 推奨日を基準に期間を設定
                            if closest_idx > 0:
                                default_pre_end = dataset.iloc[closest_idx-1]['ymd'].date()
                                default_post_start = suggested_dataset_date
                    except Exception as e:
                        # エラーが発生した場合はデフォルトの中点を使用
                        pass
                
                st.session_state['period_defaults'] = {
                    'pre_start': dataset_min_date,
                    'pre_end': default_pre_end,
                    'post_start': default_post_start,
                    'post_end': dataset_max_date
                }
        else:
            # データセットが既に作成済みの場合、セッションから取得
            dataset = st.session_state['dataset']
        
        if dataset is not None:
            # データセット情報の表示（新規作成・既存問わず）
            period_info = st.session_state.get('period_info', {})
            common_period = period_info.get('common_period', f"{dataset['ymd'].min().strftime('%Y/%m/%d')} ～ {dataset['ymd'].max().strftime('%Y/%m/%d')}")
            
            st.markdown(f"""
<div style="margin-bottom:1.5em;">
<div style="display:flex;align-items:center;margin-bottom:0.5em;">
  <div style="font-weight:bold;font-size:1.05em;margin-right:0.5em;">作成期間：</div>
<div>{dataset['ymd'].min().strftime('%Y/%m/%d')} ～ {dataset['ymd'].max().strftime('%Y/%m/%d')}</div>
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
                    period_info = st.session_state['period_info']
                    if current_analysis_type == "二群比較（処置群＋対照群を使用）":
                        st.markdown(f"""
<div style="margin-top:0.5em;">
<p><b>処置群期間：</b>{period_info['treat_period']}</p>
<p><b>対照群期間：</b>{period_info['ctrl_period']}</p>
<p><b>共通期間：</b>{period_info['common_period']}</p>
<p style="margin-top:1em;font-size:0.9em;color:#666;">※処置群と対照群の共通期間に基づいてデータセットを作成しています。
<br>※共通期間は「処置群と対照群の開始日のうち遅い方」から「終了日のうち早い方」までとして計算しています。
<br>※欠損値はすべてゼロ埋めされています。</p>
</div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
<div style="margin-top:0.5em;">
<p><b>処置群期間：</b>{period_info['treat_period']}</p>
<p style="margin-top:1em;font-size:0.9em;color:#666;">※単群推定では、処置群のデータ期間全体を対象としています。<br>※欠損値はすべてゼロ埋めされています。</p>
</div>
                        """, unsafe_allow_html=True)

            # データプレビューと統計情報の表示
            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">データプレビュー（上位10件表示）</div>', unsafe_allow_html=True)
                preview_df = dataset.head(10).copy()
                preview_df['ymd'] = preview_df['ymd'].dt.strftime('%Y-%m-%d')
                preview_df.index = range(1, len(preview_df) + 1)
                st.dataframe(preview_df, use_container_width=True)
            with col2:
                st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">統計情報</div>', unsafe_allow_html=True)
                
                # 統計情報の列名を動的に取得
                numeric_columns = [col for col in dataset.columns if col != 'ymd']
                
                stats_data = []
                for col in numeric_columns:
                    stats_data.append([
                        len(dataset),
                        round(dataset[col].mean(), 2),
                        round(dataset[col].std(), 2),
                        dataset[col].min(),
                        dataset[col].quantile(0.25),
                        dataset[col].quantile(0.5),
                        dataset[col].quantile(0.75),
                        dataset[col].max()
                    ])
                
                stats_df = pd.DataFrame(stats_data).T
                stats_df.columns = numeric_columns
                stats_df.index = ['count（個数）', 'mean（平均）', 'std（標準偏差）', 'min（最小値）', '25%（第1四分位数）', '50%（中央値）', '75%（第3四分位数）', 'max（最大値）']
                stats_df.insert(0, '統計項目', stats_df.index)
                st.dataframe(stats_df, use_container_width=True, hide_index=True)

            # --- 時系列可視化セクション ---
            st.markdown('<div class="section-title">時系列プロット</div>', unsafe_allow_html=True)
            
            if current_analysis_type == "二群比較（処置群＋対照群を使用）" and len(dataset.columns) >= 3:
                st.markdown('<div style="font-weight:bold;margin-bottom:1em;font-size:1.05em;">処置群と対照群の時系列推移</div>', unsafe_allow_html=True)
                # 二群比較の時系列可視化（処置群 + 対照群）
                # 列名を動的に取得
                treatment_col = [col for col in dataset.columns if col != 'ymd' and '処置群' in col][0]
                control_col = [col for col in dataset.columns if col != 'ymd' and '対照群' in col][0]
                
                # プロットの作成
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                # 処置群のトレース追加
                fig.add_trace(
                    go.Scatter(
                        x=dataset['ymd'], 
                        y=dataset[treatment_col], 
                        name=treatment_col, 
                        line=dict(color="#1976d2", width=2), 
                        mode='lines+markers', 
                        marker=dict(size=4),
                        hovertemplate='日付: %{x|%Y-%m-%d}<br>数量: %{y}<extra></extra>'
                    ),
                    secondary_y=False
                )
                
                # 対照群のトレース追加
                fig.add_trace(
                    go.Scatter(
                        x=dataset['ymd'], 
                        y=dataset[control_col], 
                        name=control_col, 
                        line=dict(color="#ef5350", width=2), 
                        mode='lines+markers', 
                        marker=dict(size=4),
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
                
                # レイアウトの設定（凡例を中央に配置、range sliderを追加）
                fig.update_layout(
                    height=500,
                    hovermode='x unified',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="center",
                        x=0.5
                    ),
                    xaxis_rangeslider_visible=True,
                    dragmode="zoom"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
            else:
                # 単群推定の時系列可視化
                st.markdown('<div style="font-weight:bold;margin-bottom:1em;font-size:1.05em;">処置群の時系列推移</div>', unsafe_allow_html=True)
                
                # 列名を動的に取得
                treatment_col = [col for col in dataset.columns if col != 'ymd'][0]
                
                # プロットの作成
                fig = go.Figure()
                
                # 処置群のトレース追加（凡例を明示）
                fig.add_trace(
                    go.Scatter(
                        x=dataset['ymd'], 
                        y=dataset[treatment_col], 
                        name=f"処置群（{treatment_name}）", 
                        line=dict(color="#1976d2", width=2), 
                        mode='lines', 
                        hovertemplate='日付: %{x|%Y-%m-%d}<br>数量: %{y}<extra></extra>'
                    )
                )
                
                # レイアウトの設定（凡例表示、range slider追加）
                fig.update_layout(
                    showlegend=True,  # 凡例を明示的に表示
                    legend=dict(
                        orientation="h", 
                        yanchor="bottom", 
                        y=1.02, 
                        xanchor="center", 
                        x=0.5
                    ),
                    hovermode="x unified",
                    plot_bgcolor='white',
                    margin=dict(t=50, l=60, r=60, b=60),
                    height=500,
                    autosize=True,
                    xaxis_rangeslider_visible=True,
                    dragmode="zoom"
                )
                
                # X軸の設定
                fig.update_xaxes(
                    title_text="日付", 
                    type="date", 
                    tickformat="%Y-%m", 
                    showgrid=True, 
                    tickangle=-30
                )
                
                # Y軸の設定（左軸ラベルを青文字で明示）
                fig.update_yaxes(
                    title_text="処置群の数量",
                    title_font=dict(color="#1976d2"),
                    tickfont=dict(color="#1976d2"),
                    showgrid=True
                )
                
                st.plotly_chart(fig, use_container_width=True)

            # --- Plotlyインタラクティブグラフの使い方ガイド ---
            with st.expander("Plotlyインタラクティブグラフの使い方ガイド"):
                st.markdown("""
<div style="line-height:1.7;">
<ul>
<li><b>データ確認</b>：グラフ上の線やポイントにマウスを置くと、詳細値がポップアップ表示されます</li>
<li><b>拡大表示</b>：グラフ内で見たい期間をドラッグして範囲選択すると拡大表示されます</li>
<li><b>レンジ(範囲)スライダー</b>：グラフ下部のスライダーバーで表示期間を調整できます（ハンドルをドラッグして範囲を変更）</li>
<li><b>表示移動</b>：拡大後、右クリックドラッグで表示位置を調整できます</li>
<li><b>初期表示</b>：ダブルクリックすると全期間表示に戻ります</li>
<li><b>系列表示切替</b>：グラフ上部の凡例をクリックすると系列の表示/非表示を切り替えできます</li>
</ul>
</div>
                """, unsafe_allow_html=True)
            
            # --- 分析期間設定のヒント ---
            with st.expander("分析期間設定のヒント"):
                if current_analysis_type == "二群比較（処置群＋対照群を使用）":
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
  <li><b>データ量の推奨</b>：分析の信頼性向上のため、介入前後を合わせて24件以上のデータを推奨します</li>
</ul>
</div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
<div style="line-height:1.7;">
<ul>
  <li><b>介入期間</b>：処置群において、施策（介入）実施後の効果を測定したい期間を設定してください</li>
  <li><b>介入前期間</b>：施策（介入）実施前の期間として、十分な長さのデータを含めて設定してください
    <ul>
      <li><b>季節性</b>：介入前期間に季節性がある場合は、少なくとも2〜3周期分のデータを含めるのが望ましいです</li>
      <li><b>イレギュラー要因</b>：外部要因による大きな影響がある期間は、介入前期間に含めないことをおすすめします</li>
      <li><b>単群推定の特徴</b>：対照群がないため、介入前のトレンドと季節性パターンから反事実シナリオを構築します</li>
      <li><b>介入前期間の重要性</b>：単群推定では介入前期間のデータ品質が分析結果に大きく影響するため、全体の60%以上を介入前期間に設定することを推奨します</li>
    </ul>
  </li>
  <li><b>データ量の推奨</b>：単群推定では季節性学習のため、36件以上のデータを強く推奨します（月次データ：3年分、旬次データ：1年分程度）</li>
  <li><b>介入日の設定</b>：実際の施策実施日を正確に設定してください。不正確な介入日設定は分析結果の信頼性を大きく損ないます</li>
</ul>
</div>
                    """, unsafe_allow_html=True)

            # STEP 1完了メッセージと次のSTEPへのボタンを表示
            st.success("データセットの作成が完了しました。次のステップで分析期間とパラメータの設定を行います。")
            
            # 分析期間とパラメータを設定するボタンを追加
            next_step_btn = st.button("分析期間とパラメータを設定する", key="next_step", help="次のステップ（分析期間とパラメータ設定）に進みます。", type="primary", use_container_width=True)
            
            # STEP2への遷移処理
            if next_step_btn:
                st.session_state['show_step2'] = True
            
            # --- STEP 2: 分析期間／パラメータ設定 ---
            # データセット作成完了後、ボタンを押すか既にパラメータ設定画面を表示中ならSTEP 2を表示
            if st.session_state.get('show_step2', False):
                dataset = st.session_state['dataset']  # セッションから取得
                current_analysis_type = st.session_state.get('analysis_type', analysis_type)
                
                st.markdown(STEP2_CARD_HTML, unsafe_allow_html=True)
                
                # --- 分析期間設定 ---
                st.markdown('<div class="section-title">分析期間の設定</div>', unsafe_allow_html=True)
                
                if current_analysis_type == "二群比較（処置群＋対照群を使用）":
                    st.info("注意：介入期間の開始日は、介入前期間の終了日より後の日付を指定してください。")
                else:
                    # 割合ベースの説明に統一（日付は表示せず誤解を防ぐ）
                    st.info("介入前期間は、データ全体の60%以上を確保することを推奨します。介入期間の開始日は、介入前期間の終了日より後の日付を指定してください。")
                
                # デフォルト値をセッションから取得
                pre_start, pre_end, post_start, post_end = get_period_defaults(st.session_state, dataset)
                
                # 介入前期間の設定
                st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">介入前期間 (Pre-Period)</div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    pre_start_date = st.date_input(
                        "開始日",
                        value=pre_start,
                        min_value=dataset['ymd'].min().date(),
                        max_value=dataset['ymd'].max().date(),
                        key="pre_start",
                        help="介入前期間の開始日を選択してください"
                    )
                    # 個別バリデーション: 介入前期間開始日
                    if pre_start_date is not None:
                        if pre_start_date < dataset['ymd'].min().date():
                            st.error(f"⚠️ 開始日がデータセット期間外です（{dataset['ymd'].min().date()} ～ {dataset['ymd'].max().date()}）")
                        elif pre_start_date > dataset['ymd'].max().date():
                            st.error(f"⚠️ 開始日がデータセット期間外です（{dataset['ymd'].min().date()} ～ {dataset['ymd'].max().date()}）")
                    else:
                        st.info("📅 開始日を選択してください")
                with col2:
                    pre_end_date = st.date_input(
                        "終了日",
                        value=pre_end,
                        min_value=dataset['ymd'].min().date(),
                        max_value=dataset['ymd'].max().date(),
                        key="pre_end",
                        help="介入前期間の終了日を選択してください"
                    )
                    # 個別バリデーション: 介入前期間終了日
                    if pre_end_date is not None:
                        if pre_end_date < dataset['ymd'].min().date():
                            st.error(f"⚠️ 終了日がデータセット期間外です（{dataset['ymd'].min().date()} ～ {dataset['ymd'].max().date()}）")
                        elif pre_end_date > dataset['ymd'].max().date():
                            st.error(f"⚠️ 終了日がデータセット期間外です（{dataset['ymd'].min().date()} ～ {dataset['ymd'].max().date()}）")
                    else:
                        st.info("📅 終了日を選択してください")
                
                # 介入期間の設定
                st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;margin-top:1.5em;">介入期間 (Post-Period)</div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    post_start_date = st.date_input(
                        "開始日",
                        value=post_start,
                        min_value=dataset['ymd'].min().date(),
                        max_value=dataset['ymd'].max().date(),
                        key="post_start",
                        help="介入期間の開始日を選択してください"
                    )
                    # 個別バリデーション: 介入期間開始日
                    if post_start_date is not None:
                        if post_start_date < dataset['ymd'].min().date():
                            st.error(f"⚠️ 開始日がデータセット期間外です（{dataset['ymd'].min().date()} ～ {dataset['ymd'].max().date()}）")
                        elif post_start_date > dataset['ymd'].max().date():
                            st.error(f"⚠️ 開始日がデータセット期間外です（{dataset['ymd'].min().date()} ～ {dataset['ymd'].max().date()}）")
                    else:
                        st.info("📅 開始日を選択してください")
                with col2:
                    post_end_date = st.date_input(
                        "終了日",
                        value=post_end,
                        min_value=dataset['ymd'].min().date(),
                        max_value=dataset['ymd'].max().date(),
                        key="post_end",
                        help="介入期間の終了日を選択してください"
                    )
                    # 個別バリデーション: 介入期間終了日
                    if post_end_date is not None:
                        if post_end_date < dataset['ymd'].min().date():
                            st.error(f"⚠️ 終了日がデータセット期間外です（{dataset['ymd'].min().date()} ～ {dataset['ymd'].max().date()}）")
                        elif post_end_date > dataset['ymd'].max().date():
                            st.error(f"⚠️ 終了日がデータセット期間外です（{dataset['ymd'].min().date()} ～ {dataset['ymd'].max().date()}）")
                    else:
                        st.info("📅 終了日を選択してください")
                
                # 期間設定の妥当性チェック
                is_valid, error_msg = validate_periods(pre_end_date, post_start_date, dataset, pre_start_date, post_end_date)
                if not is_valid:
                    st.error(error_msg)
                
                # 実際のデータセット件数計算と表示
                try:
                    # すべての日付が設定されている場合のみ計算を実行
                    if all(date is not None for date in [pre_start_date, pre_end_date, post_start_date, post_end_date]):
                        # データセットから該当期間の件数を計算
                        dataset_dates = pd.to_datetime(dataset['ymd']).dt.date
                        
                        # 介入前期間の件数
                        pre_mask = (dataset_dates >= pre_start_date) & (dataset_dates <= pre_end_date)
                        pre_count = pre_mask.sum()
                        
                        # 介入期間の件数
                        post_mask = (dataset_dates >= post_start_date) & (dataset_dates <= post_end_date)
                        post_count = post_mask.sum()
                        
                        total_count = pre_count + post_count
                        if total_count > 0:
                            pre_ratio = pre_count / total_count * 100
                        else:
                            pre_ratio = 0
                        
                        # 単群推定の場合、介入前期間比率をチェック
                        if current_analysis_type == "単群推定（処置群のみを使用）":
                            if pre_ratio >= 60:
                                st.success(f"✅ 介入前期間比率: {pre_ratio:.1f}% （推奨: 60%以上）")
                            else:
                                st.warning(f"⚠️ 介入前期間比率: {pre_ratio:.1f}% （推奨: 60%以上）")
                            
                            st.markdown(f"""
<div style="margin-bottom:1em;">
<p>介入前期間: {pre_start_date.strftime('%Y-%m-%d')} 〜 {pre_end_date.strftime('%Y-%m-%d')} （{pre_count}件）</p>
<p>介入期間: {post_start_date.strftime('%Y-%m-%d')} 〜 {post_end_date.strftime('%Y-%m-%d')} （{post_count}件）</p>
</div>
                            """, unsafe_allow_html=True)
                        else:
                            st.success(f"期間設定が完了しました。介入前期間: {pre_count}件、介入期間: {post_count}件")
                            
                            st.markdown(f"""
<div style="margin-bottom:1em;">
<p>介入前期間: {pre_start_date.strftime('%Y-%m-%d')} 〜 {pre_end_date.strftime('%Y-%m-%d')} （{pre_count}件）</p>
<p>介入期間: {post_start_date.strftime('%Y-%m-%d')} 〜 {post_end_date.strftime('%Y-%m-%d')} （{post_count}件）</p>
</div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("日付を正しく設定してください。全ての日付が設定されると、件数が計算されます。")
                        
                except (TypeError, AttributeError, ValueError):
                    st.info("日付を正しく設定してください。全ての日付が設定されると、件数が計算されます。")
                
                # 分析期間をセッションに保存
                st.session_state['analysis_period'] = {
                    'pre_start': pre_start_date,
                    'pre_end': pre_end_date,
                    'post_start': post_start_date,
                    'post_end': post_end_date
                }
                
                # --- モデル・パラメータ設定 ---
                st.markdown('<div class="section-title">モデルの基本パラメータの設定</div>', unsafe_allow_html=True)
                
                # 信頼区間の設定
                st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">信頼区間の設定</div>', unsafe_allow_html=True)
                
                alpha_percent = st.slider(
                    "信頼区間レベル",
                    min_value=90,
                    max_value=99,
                    value=95,
                    step=1,
                    format="%d%%",
                    help="統計的有意性の判定基準。95% = 95%信頼区間（α=0.05）"
                )
                # 内部処理用にalphaを計算
                alpha = (100 - alpha_percent) / 100
                
                # 季節性の設定
                st.markdown('<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;margin-top:1.5em;">季節性の設定</div>', unsafe_allow_html=True)
                
                seasonality = st.checkbox(
                    "季節性を考慮する",
                    value=True,
                    help="データに周期的なパターンがある場合にチェック"
                )
                
                if seasonality:
                    col1, col2 = st.columns(2)
                    with col1:
                        # データ集計方法に応じてデフォルト値を最適化
                        if 'freq_option' in st.session_state:
                            freq_option = st.session_state.get('freq_option', '月次')
                        else:
                            freq_option = '月次'  # デフォルト
                        
                        # 最適なデフォルト値の設定
                        if freq_option == "月次":
                            default_index = 2  # 月次 (30日)
                            optimal_default = "月次 (30日)"
                        else:  # 旬次
                            default_index = 1  # 旬次 (10日)
                            optimal_default = "旬次 (10日)"
                        
                        seasonality_type = st.selectbox(
                            "季節性の種類",
                            options=["週次 (7日)", "旬次 (10日)", "月次 (30日)", "四半期 (90日)", "年次 (365日)", "カスタム"],
                            index=default_index,
                            help=f"データの周期性に応じて選択。{freq_option}データには{optimal_default}が推奨されます。"
                        )
                    with col2:
                        if seasonality_type == "カスタム":
                            custom_period = st.number_input(
                                "カスタム周期（日数）",
                                min_value=2,
                                max_value=365,
                                value=30,
                                help="独自の季節性周期を指定"
                            )

                # 基本パラメータの注釈（季節性の設定の直下に配置）
                with st.expander("基本パラメータの設定とデフォルト値"):
                    # データ集計方法に応じて動的にデフォルト値を表示
                    freq_option = st.session_state.get('freq_option', '月次')
                    if freq_option == "月次":
                        seasonality_default = "月次 (30日)"
                    else:
                        seasonality_default = "旬次 (10日)"
                    
                    st.markdown(f"""
<div style="margin-top:0.5em;">
<table style="width:100%;border-collapse:collapse;font-size:0.9em;">
<thead>
<tr style="background-color:#f8f9fa;">
<th style="border:1px solid #dee2e6;padding:8px;text-align:left;font-weight:bold;width:20%;">パラメータ名</th>
<th style="border:1px solid #dee2e6;padding:8px;text-align:left;font-weight:bold;width:65%;">意味</th>
<th style="border:1px solid #dee2e6;padding:8px;text-align:center;font-weight:bold;width:15%;">デフォルト値</th>
</tr>
</thead>
<tbody>
<tr>
<td style="border:1px solid #dee2e6;padding:8px;white-space:nowrap;">信頼区間レベル</td>
<td style="border:1px solid #dee2e6;padding:8px;">分析結果の不確実性を表現する範囲です。値が大きいほど信頼区間は広くなり、効果の推定に対する確度が高まりますが、区間自体は広くなります。</td>
<td style="border:1px solid #dee2e6;padding:8px;text-align:center;white-space:nowrap;">95%</td>
</tr>
<tr>
<td style="border:1px solid #dee2e6;padding:8px;white-space:nowrap;">季節性を考慮する</td>
<td style="border:1px solid #dee2e6;padding:8px;">時系列データに含まれる周期的なパターン（曜日・月・季節など）を考慮するかどうかを指定します。これらの影響が分析対象に含まれる場合はオンにします。</td>
<td style="border:1px solid #dee2e6;padding:8px;text-align:center;white-space:nowrap;">オン</td>
</tr>
<tr>
<td style="border:1px solid #dee2e6;padding:8px;white-space:nowrap;">周期タイプ</td>
<td style="border:1px solid #dee2e6;padding:8px;">季節性を考慮する場合に、データのパターンに合わせた周期を選択します。
<ul style="margin-top:0.5em;margin-bottom:0;">
<li><strong>週次 (7日)</strong>：週単位で繰り返すパターン（例：平日と週末の差）</li>
<li><strong>旬次 (10日)</strong>：上旬・中旬・下旬など、10日単位のパターン</li>
<li><strong>月次 (30日)</strong>：月単位の繰り返し（例：月初・月末の需要変動）</li>
<li><strong>四半期 (90日)</strong>：四半期ごとのパターン（例：決算期の影響）</li>
<li><strong>年次 (365日)</strong>：季節変動など年単位の周期</li>
<li><strong>カスタム</strong>：上記以外の特定の周期を対象とする場合に選択</li>
</ul></td>
<td style="border:1px solid #dee2e6;padding:8px;text-align:center;white-space:nowrap;">{seasonality_default}</td>
</tr>
</tbody>
</table>
</div>
                     """, unsafe_allow_html=True)
                 
                # 高度な設定
                with st.expander("高度なオプション設定（デフォルト設定でも十分な性能を発揮するため、変更は必須ではありません）"):
                    col1, col2 = st.columns(2)
                    with col1:
                        prior_level_sd = st.slider(
                            "レベル変動の事前分散",
                            min_value=0.001,
                            max_value=0.1,
                            value=0.01,
                            step=0.001,
                            format="%.3f",
                            help="ベイズモデルにおける事前分布のパラメータ。時系列の水準（レベル）の変動性を制御します。値が大きいほど水準変化に対して寛容になります。"
                        )
                        standardize = st.checkbox(
                            "データを標準化する",
                            value=True,
                            help="分析前にデータを標準化（推奨）"
                        )
                    with col2:
                        niter = st.number_input(
                            "MCMC反復回数",
                            min_value=500,
                            max_value=5000,
                            value=1000,
                            step=100,
                            help="ベイズ推定の精度を制御（多いほど精密だが時間がかかる）"
                        )
                        if current_analysis_type == "単群推定（処置群のみを使用）":
                            st.markdown("""
<div style="background-color:#e3f2fd;padding:10px;border-radius:5px;margin-top:10px;">
<b>単群推定の特別設定:</b><br>
• より多いMCMC反復回数を推奨<br>
• 季節性パラメータの慎重な調整が重要<br>
• データ標準化は必須
</div>
                            """, unsafe_allow_html=True)
                    
                    # 高度なパラメータの注釈（デザインを基本パラメータと統一）
                    st.markdown("---")
                    st.markdown("**高度なパラメータの設定とデフォルト値**")
                    st.markdown("""
<div style="margin-top:0.5em;">
<table style="width:100%;border-collapse:collapse;font-size:0.9em;">
<thead>
<tr style="background-color:#f8f9fa;">
<th style="border:1px solid #dee2e6;padding:8px;text-align:left;font-weight:bold;width:20%;">パラメータ名（オプション）</th>
<th style="border:1px solid #dee2e6;padding:8px;text-align:left;font-weight:bold;width:65%;">意味</th>
<th style="border:1px solid #dee2e6;padding:8px;text-align:center;font-weight:bold;width:15%;">デフォルト値</th>
</tr>
</thead>
<tbody>
<tr>
<td style="border:1px solid #dee2e6;padding:8px;white-space:nowrap;">レベル変動の事前分散</td>
<td style="border:1px solid #dee2e6;padding:8px;">ベイズモデルにおける事前分布のパラメータで、時系列の水準（レベル）の変動性をどの程度許容するかを指定します。値が大きいほど水準変化に対して寛容になります。</td>
<td style="border:1px solid #dee2e6;padding:8px;text-align:center;white-space:nowrap;">0.010</td>
</tr>
<tr>
<td style="border:1px solid #dee2e6;padding:8px;white-space:nowrap;">データを標準化する</td>
<td style="border:1px solid #dee2e6;padding:8px;">分析前にデータを平均0、標準偏差1になるように変換するかどうかを指定します。データのスケールが大きく異なる場合や、単位の影響を排除したい場合にオンにします。</td>
<td style="border:1px solid #dee2e6;padding:8px;text-align:center;white-space:nowrap;">オン</td>
</tr>
<tr>
<td style="border:1px solid #dee2e6;padding:8px;white-space:nowrap;">MCMC反復回数</td>
<td style="border:1px solid #dee2e6;padding:8px;">モンテカルロマルコフ連鎖（MCMC）シミュレーションの反復回数を指定します。値が大きいほど推定精度が向上しますが、計算時間も長くなります。</td>
<td style="border:1px solid #dee2e6;padding:8px;text-align:center;white-space:nowrap;">1000</td>
</tr>
</tbody>
</table>
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
                        seasonality_period = custom_period if 'custom_period' in locals() else 30
                
                st.session_state['analysis_params'] = build_analysis_params(
                    alpha,
                    seasonality,
                    seasonality_type if seasonality else None,
                    custom_period if seasonality and seasonality_type == "カスタム" else None,
                    prior_level_sd,
                    standardize,
                    niter
                )
                
                # --- 分析実行準備 ---
                st.markdown('<div class="section-title">分析実行</div>', unsafe_allow_html=True)
                
                # 設定確認
                if is_valid:
                    st.success("✅ 分析実行の準備が完了しました。以下のボタンをクリックして分析を開始してください。")
                    
                    # 分析実行ボタン
                    analyze_btn = st.button(
                        "Causal Impact分析を実行する",
                        key="analyze",
                        help="設定したパラメータで分析を実行します",
                        type="primary",
                        use_container_width=True
                    )
                    
                    if analyze_btn:
                        st.session_state['params_saved'] = True
                        st.session_state['show_step3'] = True
                        
                        # 分析実行処理を開始
                        with st.spinner("Causal Impact分析を実行中..."):
                            try:
                                # 分析期間の取得
                                analysis_period = st.session_state['analysis_period']
                                analysis_params = st.session_state['analysis_params']
                                dataset = st.session_state['dataset']
                                
                                # 分析期間をリスト形式に変換
                                pre_period = [analysis_period['pre_start'], analysis_period['pre_end']]
                                post_period = [analysis_period['post_start'], analysis_period['post_end']]
                                
                                # 分析タイプに応じて分析実行
                                if current_analysis_type == "単群推定（処置群のみを使用）":
                                    # 処置群のみ分析実行
                                    from utils_step3_single_group import run_single_group_causal_impact_analysis
                                    
                                    # データセットを処置群のみ分析用に準備
                                    # データセットの列名を取得（ymd以外の最初の列が処置群データ）
                                    data_columns = [col for col in dataset.columns if col != 'ymd']
                                    if len(data_columns) == 0:
                                        st.error("データセットに処置群データが見つかりません。")
                                        st.stop()
                                    
                                    # 処置群のみ分析用データフレーム作成
                                    single_group_data = dataset[['ymd', data_columns[0]]].copy()
                                    single_group_data.columns = ['date', 'y']  # CausalImpact用の標準列名
                                    
                                    # 日付をpandasのTimestamp形式に確実に変換
                                    single_group_data['date'] = pd.to_datetime(single_group_data['date'])
                                    single_group_data = single_group_data.set_index('date')
                                    
                                    # 分析期間の日付もpandasのTimestamp形式に変換
                                    pre_period_converted = [pd.to_datetime(pre_period[0]), pd.to_datetime(pre_period[1])]
                                    post_period_converted = [pd.to_datetime(post_period[0]), pd.to_datetime(post_period[1])]
                                    
                                    # 季節性パラメータの設定
                                    if analysis_params.get('seasonality', False):
                                        nseasons = analysis_params.get('seasonality_period', 7)
                                        season_duration = 1
                                    else:
                                        nseasons = 1
                                        season_duration = 1
                                    
                                    # 処置群のみ分析実行
                                    ci, summary, report, fig = run_single_group_causal_impact_analysis(
                                        single_group_data, 
                                        pre_period_converted, 
                                        post_period_converted,
                                        nseasons=nseasons,
                                        season_duration=season_duration
                                    )
                                    
                                    # 結果をセッションに保存
                                    st.session_state['causal_impact_result'] = ci
                                    st.session_state['analysis_summary'] = summary
                                    st.session_state['analysis_report'] = report
                                    st.session_state['analysis_figure'] = fig
                                    st.session_state['analysis_completed'] = True
                                    
                                else:
                                    # 二群比較分析実行（既存機能）
                                    from utils_step3 import run_causal_impact_analysis
                                    
                                    # 分析期間の日付をpandasのTimestamp形式に変換
                                    pre_period_converted = [pd.to_datetime(pre_period[0]), pd.to_datetime(pre_period[1])]
                                    post_period_converted = [pd.to_datetime(post_period[0]), pd.to_datetime(post_period[1])]
                                    
                                    # 二群比較分析用データセットを適切な形式に変換
                                    # CausalImpactは日付をインデックスとしたデータフレームを期待
                                    analysis_dataset = dataset.copy()
                                    analysis_dataset['ymd'] = pd.to_datetime(analysis_dataset['ymd'])
                                    analysis_dataset = analysis_dataset.set_index('ymd')
                                    
                                    # 既存の二群比較分析を実行（引数を3つに修正）
                                    ci, summary, report, fig = run_causal_impact_analysis(
                                        analysis_dataset, 
                                        pre_period_converted, 
                                        post_period_converted
                                    )
                                    
                                    # 結果をセッションに保存
                                    st.session_state['causal_impact_result'] = ci
                                    st.session_state['analysis_summary'] = summary
                                    st.session_state['analysis_report'] = report
                                    st.session_state['analysis_figure'] = fig
                                    st.session_state['analysis_completed'] = True
                                
                                # 分析完了メッセージ
                                st.success("✅ Causal Impact分析が完了しました！下記の結果をご確認ください。")
                                
                            except Exception as e:
                                st.error(f"❌ 分析実行中にエラーが発生しました: {str(e)}")
                                st.error("パラメータ設定を確認して再度実行してください。")
                                st.session_state['analysis_completed'] = False
                else:
                    st.error("❌ 期間設定に問題があります。上記のエラーを修正してから分析を実行してください。")

# --- STEP 3: 分析結果表示 ---
# 分析が完了している場合、結果を表示
if st.session_state.get('analysis_completed', False) and st.session_state.get('show_step3', False):
    
    st.markdown("""
<div class="step-card">
    <h2 style="font-size:1.8em;font-weight:bold;color:#1565c0;margin-bottom:0.5em;">STEP 3：分析実行／結果確認</h2>
    <div style="color:#1976d2;font-size:1.1em;line-height:1.5;">Causal Impact 分析の結果を、グラフおよび数値サマリーで視覚的に確認できます。分析条件や効果測定結果に基づいて傾向を把握し、必要に応じてグラフや表をダウンロードして活用してください。</div>
</div>
    """, unsafe_allow_html=True)
    
    # 分析結果の取得
    ci = st.session_state.get('causal_impact_result')
    summary = st.session_state.get('analysis_summary')
    report = st.session_state.get('analysis_report')
    fig = st.session_state.get('analysis_figure')
    current_analysis_type = st.session_state.get('analysis_type', analysis_type)
    
    if ci is not None:
        # --- 分析結果サマリー（改善版） ---
        st.markdown('<div class="section-title">分析結果サマリー</div>', unsafe_allow_html=True)
        
        # 分析条件の構築
        analysis_period = st.session_state.get('analysis_period', {})
        analysis_params = st.session_state.get('analysis_params', {})
        treatment_name = st.session_state.get('treatment_name', '処置群')
        control_name = st.session_state.get('control_name', '対照群')
        freq_option = st.session_state.get('freq_option', '月次')
        
        if current_analysis_type == "単群推定（処置群のみを使用）":
            analysis_target = treatment_name
            analysis_method = "単群推定（Single Group Causal Impact）"
        else:
            analysis_target = f"{treatment_name}（vs {control_name}）"
            analysis_method = "二群比較（Two-Group Causal Impact）"
        
        # 介入期間と全体期間の表示用文字列とデータポイント数の計算
        intervention_period_str = "期間情報なし"
        data_point_count = 0
        
        if analysis_period:
            try:
                # 介入期間の表示
                intervention_period_str = f"{analysis_period['post_start'].strftime('%Y-%m-%d')} ～ {analysis_period['post_end'].strftime('%Y-%m-%d')}"
                
                # データポイント数の計算
                dataset = st.session_state.get('dataset')
                if dataset is not None:
                    dataset_dates = pd.to_datetime(dataset['ymd']).dt.date
                    post_mask = (dataset_dates >= analysis_period['post_start']) & (dataset_dates <= analysis_period['post_end'])
                    data_point_count = post_mask.sum()
                    intervention_period_str += f"（{data_point_count}件）"
            except:
                intervention_period_str = "期間情報取得エラー"
        
        # 信頼水準の取得
        confidence_level = int((1 - analysis_params.get('alpha', 0.05)) * 100) if analysis_params else 95
        
        # データ粒度の表示（「集計」を追加）
        data_granularity = f"{freq_option}集計"
        
        # 分析条件を中項目として表示（一部を横並びに）
        # 分析対象（中項目） - ファイル名が長い場合は省略
        analysis_target_display = analysis_target if len(analysis_target) <= 50 else analysis_target[:47] + "..."
        st.markdown(f'<div style="margin-bottom:0.8em;"><span style="font-weight:bold;font-size:1.05em;">分析対象：</span><span style="color:#424242;">{analysis_target_display}</span></div>', unsafe_allow_html=True)
        
        # 分析期間（データ粒度を統合）
        st.markdown(f'<div style="margin-bottom:0.8em;"><span style="font-weight:bold;font-size:1.05em;">分析期間：</span><span style="color:#424242;">{intervention_period_str}（{data_granularity}）</span></div>', unsafe_allow_html=True)
        
        # 分析手法（信頼水準を統合）
        st.markdown(f'<div style="margin-bottom:1.5em;"><span style="font-weight:bold;font-size:1.05em;">分析手法：</span><span style="color:#424242;">{analysis_method}（信頼水準：{confidence_level}%）</span></div>', unsafe_allow_html=True)
        
        # 中項目「分析結果概要」を追加
        st.markdown('<div style="font-weight:bold;margin-bottom:1em;font-size:1.05em;">分析結果概要</div>', unsafe_allow_html=True)
        
        # サマリー情報の詳細表示（表形式に改善）
        relative_effect_value = None
        p_value = None
        
        if summary is not None:
            try:
                # 新しい表形式での分析結果表示
                from utils_step3 import build_enhanced_summary_table, get_metrics_explanation_table
                
                results_df = build_enhanced_summary_table(ci, confidence_level)
                
                if not results_df.empty:
                    st.dataframe(results_df, use_container_width=True, hide_index=True)
                    
                    # --- 分析レポートのまとめ（テーブル直下に配置） ---
                    try:
                        # 新しい関数を使用してサマリーメッセージを生成
                        from utils_step3 import get_analysis_summary_message
                        summary_message = get_analysis_summary_message(ci, confidence_level)
                        
                        if summary_message:
                            st.success(summary_message)
                            
                            # --- 詳細レポート（実行結果メッセージの直下に配置） ---
                            with st.expander("詳細レポート", expanded=False):
                                if report is not None:
                                    try:
                                        # レポートを日本語に翻訳
                                        st.markdown("**📋 Causal Impact分析の詳細レポート**")
                                        
                                        # 信頼水準を取得（デフォルト95%）
                                        confidence_level_alpha = confidence_level / 100 if confidence_level else 0.95
                                        
                                        # 翻訳処理を実行
                                        report_jp = translate_causal_impact_report(str(report), alpha=confidence_level_alpha)
                                        
                                        # 翻訳されたレポートを段落ごとに分割して表示
                                        report_paragraphs = report_jp.split('\n\n')
                                        
                                        for paragraph in report_paragraphs:
                                            if paragraph.strip():
                                                # 段落内の文章を適切に表示
                                                paragraph = paragraph.strip()
                                                
                                                # タイトル行の処理
                                                if '分析レポート {CausalImpact}' in paragraph:
                                                    st.markdown(f"**{paragraph}**")
                                                # 事後確率などの重要な統計値を強調表示
                                                elif '事後確率' in paragraph or 'p値' in paragraph:
                                                    st.markdown(f"**{paragraph}**")
                                                else:
                                                    st.markdown(paragraph)
                                        
                                    except Exception as e:
                                        st.error(f"レポート翻訳でエラーが発生しました: {str(e)}")
                                        # フォールバック：元の英語レポートを表示
                                        st.text(str(report))
                        else:
                            # フォールバック：従来の方法でメッセージ生成を試行
                            if hasattr(ci, 'summary') and hasattr(ci.summary, 'iloc'):
                                summary_df_temp = ci.summary
                                
                                # 相対効果と有意性の判定
                                relative_effect_temp = None
                                p_value_temp = None
                                is_significant_temp = False
                                
                                # 相対効果の取得
                                if 'RelEffect' in summary_df_temp.index:
                                    rel_effect_avg = summary_df_temp.loc['RelEffect', 'Average']
                                    if not hasattr(rel_effect_avg, '__iter__'):
                                        relative_effect_temp = rel_effect_avg * 100
                                
                                # p値の取得
                                if hasattr(ci, 'p_value'):
                                    p_value_temp = ci.p_value
                                
                                # 統計的有意性の判定（信頼区間による）
                                if 'Cumulative' in summary_df_temp.columns:
                                    cumulative_data = summary_df_temp['Cumulative']
                                    if 'AbsEffect_lower' in cumulative_data.index and 'AbsEffect_upper' in cumulative_data.index:
                                        lower_bound = cumulative_data['AbsEffect_lower']
                                        upper_bound = cumulative_data['AbsEffect_upper']
                                        if (lower_bound > 0 and upper_bound > 0) or (lower_bound < 0 and upper_bound < 0):
                                            is_significant_temp = True
                                
                                # メッセージの作成と表示
                                if relative_effect_temp is not None and p_value_temp is not None:
                                    if is_significant_temp:
                                        fallback_message = f"相対効果は {relative_effect_temp:+.1f}% で、統計的に有意です（p = {p_value_temp:.3f}）。詳しくは、この下の「詳細レポート」を参照ください。"
                                    else:
                                        fallback_message = f"相対効果は {relative_effect_temp:+.1f}% ですが、統計的には有意ではありません（p = {p_value_temp:.3f}）。詳しくは、この下の「詳細レポート」を参照ください。"
                                    
                                    st.success(fallback_message)
                                    
                                    # --- 詳細レポート（フォールバック時の直下配置） ---
                                    with st.expander("詳細レポート", expanded=False):
                                        if report is not None:
                                            try:
                                                # レポートを日本語に翻訳
                                                st.markdown("**📋 Causal Impact分析の詳細レポート**")
                                                
                                                # 信頼水準を取得（デフォルト95%）
                                                confidence_level_alpha = confidence_level / 100 if confidence_level else 0.95
                                                
                                                # 翻訳処理を実行
                                                report_jp = translate_causal_impact_report(str(report), alpha=confidence_level_alpha)
                                                
                                                # 翻訳されたレポートを段落ごとに分割して表示
                                                report_paragraphs = report_jp.split('\n\n')
                                                
                                                for paragraph in report_paragraphs:
                                                    if paragraph.strip():
                                                        # 段落内の文章を適切に表示
                                                        paragraph = paragraph.strip()
                                                        
                                                        # タイトル行の処理
                                                        if '分析レポート {CausalImpact}' in paragraph:
                                                            st.markdown(f"**{paragraph}**")
                                                        # 事後確率などの重要な統計値を強調表示
                                                        elif '事後確率' in paragraph or 'p値' in paragraph:
                                                            st.markdown(f"**{paragraph}**")
                                                        else:
                                                            st.markdown(paragraph)
                                                
                                            except Exception as e:
                                                st.error(f"レポート翻訳でエラーが発生しました: {str(e)}")
                                                # フォールバック：元の英語レポートを表示
                                                st.text(str(report))
                    except Exception as e:
                        pass  # エラーが発生した場合はメッセージ表示をスキップ
                    
                    # 指標の説明（展開可能）
                    with st.expander("指標の説明", expanded=False):
                        st.markdown(get_metrics_explanation_table(), unsafe_allow_html=True)
                else:
                    # CausalImpactの結果から主要指標を抽出して表形式で表示（フォールバック）
                    if hasattr(ci, 'summary') and hasattr(ci.summary, 'iloc'):
                        # pandas DataFrameとして処理
                        summary_df = ci.summary.copy()
                        
                        # 主要指標の抽出と表形式での表示
                        if 'Average' in summary_df.columns and 'Cumulative' in summary_df.columns:
                            # 分析結果テーブルの作成
                            results_data = []
                            
                            # 各指標の行を作成
                            if 'Actual' in summary_df.index:
                                avg_actual = summary_df.loc['Actual', 'Average']
                                cum_actual = summary_df.loc['Actual', 'Cumulative']
                                results_data.append(['実測値', f"{avg_actual:.1f}", f"{cum_actual:,.0f}"])
                            
                            if 'Predicted' in summary_df.index:
                                avg_pred = summary_df.loc['Predicted', 'Average']
                                cum_pred = summary_df.loc['Predicted', 'Cumulative']
                                # 標準偏差がある場合は括弧内に表示
                                if hasattr(summary_df.loc['Predicted', 'Average'], '__iter__'):
                                    # 複数値の場合（標準偏差含む）
                                    pred_str = str(summary_df.loc['Predicted', 'Average'])
                                    cum_pred_str = str(summary_df.loc['Predicted', 'Cumulative'])
                                else:
                                    pred_str = f"{avg_pred:.1f}"
                                    cum_pred_str = f"{cum_pred:,.0f}"
                                results_data.append(['予測値（標準偏差）', pred_str, cum_pred_str])
                            
                            if '95% CI' in summary_df.index:
                                avg_ci = str(summary_df.loc['95% CI', 'Average'])
                                cum_ci = str(summary_df.loc['95% CI', 'Cumulative'])
                                results_data.append(['予測値 95% 信頼区間', avg_ci, cum_ci])
                            
                            if 'AbsEffect' in summary_df.index:
                                avg_abs = summary_df.loc['AbsEffect', 'Average']
                                cum_abs = summary_df.loc['AbsEffect', 'Cumulative']
                                # 標準偏差がある場合は括弧内に表示
                                if hasattr(avg_abs, '__iter__'):
                                    abs_str = str(avg_abs)
                                    cum_abs_str = str(cum_abs)
                                else:
                                    abs_str = f"{avg_abs:.1f}"
                                    cum_abs_str = f"{cum_abs:,.0f}"
                                results_data.append(['絶対効果（標準偏差）', abs_str, cum_abs_str])
                            
                            if 'AbsEffect_lower' in summary_df.index and 'AbsEffect_upper' in summary_df.index:
                                avg_abs_ci = f"[{summary_df.loc['AbsEffect_lower', 'Average']:.1f}, {summary_df.loc['AbsEffect_upper', 'Average']:.1f}]"
                                cum_abs_ci = f"[{summary_df.loc['AbsEffect_lower', 'Cumulative']:,.0f}, {summary_df.loc['AbsEffect_upper', 'Cumulative']:,.0f}]"
                                results_data.append(['絶対効果 95% 信頼区間', avg_abs_ci, cum_abs_ci])
                            
                            if 'RelEffect' in summary_df.index:
                                avg_rel = summary_df.loc['RelEffect', 'Average']
                                cum_rel = summary_df.loc['RelEffect', 'Cumulative']
                                # パーセンテージ表示
                                if hasattr(avg_rel, '__iter__'):
                                    rel_str = str(avg_rel)
                                    cum_rel_str = str(cum_rel)
                                else:
                                    rel_str = f"{avg_rel*100:.1f}%"
                                    cum_rel_str = f"{cum_rel*100:.1f}%"
                                    relative_effect_value = avg_rel*100  # 後で使用するため保存
                                results_data.append(['相対効果（標準偏差）', rel_str, cum_rel_str])
                            
                            if 'RelEffect_lower' in summary_df.index and 'RelEffect_upper' in summary_df.index:
                                avg_rel_ci = f"[{summary_df.loc['RelEffect_lower', 'Average']*100:.1f}%, {summary_df.loc['RelEffect_upper', 'Average']*100:.1f}%]"
                                cum_rel_ci = f"[{summary_df.loc['RelEffect_lower', 'Cumulative']*100:.1f}%, {summary_df.loc['RelEffect_upper', 'Cumulative']*100:.1f}%]"
                                results_data.append(['相対効果 95% 信頼区間', avg_rel_ci, cum_rel_ci])
                            
                            # 事後確率の追加
                            if hasattr(ci, 'p_value'):
                                p_value = ci.p_value if ci.p_value is not None else "N/A"
                                results_data.append(['p値（事後確率）', str(p_value), "同左"])
                            
                            # 結果テーブルの表示
                            if results_data:
                                results_df = pd.DataFrame(results_data, columns=['指標', '分析期間の平均値', '分析期間の累積値'])
                                st.dataframe(results_df, use_container_width=True, hide_index=True)
                                
                                # --- 分析レポートのまとめ（フォールバック版） ---
                                try:
                                    summary_message = get_analysis_summary_message(ci, confidence_level)
                                    if summary_message:
                                        st.success(summary_message)
                                except Exception as e:
                                    pass  # エラーが発生した場合はメッセージ表示をスキップ
                                
                                # 指標の説明（展開可能）
                                with st.expander("指標の説明", expanded=False):
                                    st.markdown(get_metrics_explanation_table(), unsafe_allow_html=True)
                        
                        # 完全なサマリーテーブルをexpanderで表示
                        with st.expander("完全なサマリーテーブル", expanded=False):
                            st.dataframe(summary_df, use_container_width=True)
                    else:
                        # フォールバック：テキスト形式で表示
                        with st.expander("分析結果（テキスト形式）", expanded=False):
                            st.text(str(summary))
                            
            except Exception as e:
                st.warning("サマリー情報の詳細表示でエラーが発生しました。基本情報を表示します。")
                with st.expander("分析結果（テキスト形式）", expanded=False):
                    st.text(str(summary))
        
        # --- 分析レポートのまとめ ---
        try:
            # 統計的有意性と相対効果の判定
            if hasattr(ci, 'summary') and hasattr(ci.summary, 'iloc'):
                summary_df = ci.summary
                
                # 相対効果の取得
                if relative_effect_value is None and 'RelEffect' in summary_df.index:
                    rel_effect_avg = summary_df.loc['RelEffect', 'Average']
                    if not hasattr(rel_effect_avg, '__iter__'):
                        relative_effect_value = rel_effect_avg * 100
                
                # p値の取得
                if p_value is None and hasattr(ci, 'p_value'):
                    p_value = ci.p_value
                
                # 統計的有意性の判定（信頼区間による）
                is_significant = False
                if 'Cumulative' in summary_df.columns:
                    cumulative_data = summary_df['Cumulative']
                    if 'AbsEffect_lower' in cumulative_data.index and 'AbsEffect_upper' in cumulative_data.index:
                        lower_bound = cumulative_data['AbsEffect_lower']
                        upper_bound = cumulative_data['AbsEffect_upper']
                        if (lower_bound > 0 and upper_bound > 0) or (lower_bound < 0 and upper_bound < 0):
                            is_significant = True
                
                # メッセージの作成
                if relative_effect_value is not None and p_value is not None:
                    if is_significant:
                        summary_message = f"相対効果は {relative_effect_value:+.1f}% で、統計的に有意です（p = {p_value:.3f}）。詳細はレポートを参照ください。"
                    else:
                        summary_message = f"相対効果は {relative_effect_value:+.1f}% ですが、統計的には有意ではありません（p = {p_value:.3f}）。詳細はレポートを参照ください。"
                    
                    st.success(summary_message)
                
        except Exception as e:
            pass  # エラーが発生した場合はメッセージ表示をスキップ

        # --- 分析結果グラフ（改善版） ---
        st.markdown('<div class="section-title">分析結果グラフ</div>', unsafe_allow_html=True)
        
        if fig is not None:
            try:
                # 総タイトルと説明文を分析タイプに応じて表示
                if current_analysis_type == "単群推定（処置群のみを使用）":
                    # 総タイトル（中項目スタイル）
                    st.markdown(f'<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">{treatment_name}</div>', unsafe_allow_html=True)
                    # 説明文（中項目スタイル）
                    st.markdown('<div style="margin-bottom:1em;font-size:1.05em;"><span style="font-weight:bold;">処置群のみ分析：</span><span style="font-weight:normal;">介入前トレンドからの予測との比較</span></div>', unsafe_allow_html=True)
                else:
                    # 総タイトル（中項目スタイル）
                    st.markdown(f'<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">{treatment_name}（vs {control_name}）</div>', unsafe_allow_html=True)
                    # 説明文（中項目スタイル）
                    st.markdown('<div style="margin-bottom:1em;font-size:1.05em;"><span style="font-weight:bold;">二群比較分析：</span><span style="font-weight:normal;">対照群との関係性による予測との比較</span></div>', unsafe_allow_html=True)
                
                # matplotlibのフォント設定を確認・修正してからグラフ表示
                import matplotlib
                import matplotlib.pyplot as plt
                
                # Windows環境の日本語フォント設定
                try:
                    # Windows標準の日本語フォントを優先設定
                    matplotlib.rcParams['font.family'] = ['Yu Gothic', 'Meiryo', 'MS Gothic', 'DejaVu Sans']
                    matplotlib.rcParams['font.sans-serif'] = ['Yu Gothic', 'Meiryo', 'MS Gothic', 'DejaVu Sans']
                    # 警告を抑制
                    matplotlib.rcParams['axes.unicode_minus'] = False
                except Exception as e:
                    pass  # フォント設定に失敗してもエラーで止まらないように
                
                # グラフのタイトルを日本語で設定
                try:
                    axes = fig.get_axes()
                    if len(axes) >= 3:
                        # 各グラフのタイトルを通常文字に設定
                        axes[0].set_title('実測値 vs 予測値', fontsize=12, weight='normal')
                        axes[1].set_title('時点効果', fontsize=12, weight='normal')
                        axes[2].set_title('累積効果', fontsize=12, weight='normal')
                    
                    # 下部の注釈メッセージを削除
                    for ax in axes:
                        texts = ax.texts[:]  # リストのコピーを作成
                        for text in texts:
                            text_content = text.get_text()
                            if ("Note:" in text_content or 
                                "observations were removed" in text_content or
                                "diffuse initialization" in text_content):
                                text.remove()  # テキストを完全に削除
                    
                    # 図全体のタイトルを削除
                    fig.suptitle('')
                except Exception as e:
                    pass  # タイトル設定に失敗してもエラーで止まらないように
                
                # matplotlibの図をStreamlitに表示
                st.pyplot(fig)
                
                # グラフの見方（常時表示）
                if current_analysis_type == "単群推定（処置群のみを使用）":
                    st.markdown("""
<div style="color:#666;font-size:0.95em;margin-top:0.5em;padding:10px;background-color:#f8f9fa;border-radius:4px;">
<strong>グラフの見方：</strong>実測データ（黒線）と予測データ（青線）の比較により介入効果を評価。影部分は予測の不確実性を示す信頼区間。対照群がないため外部要因の影響に注意。
</div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
<div style="color:#666;font-size:0.95em;margin-top:0.5em;padding:10px;background-color:#f8f9fa;border-radius:4px;">
<strong>グラフの見方：</strong>実測データ（黒線）と対照群から推定した予測データ（青線）の比較により純粋な介入効果を評価。影部分は予測の不確実性を示す信頼区間。対照群により外部要因の影響を除去。
</div>
                    """, unsafe_allow_html=True)
            
            except Exception as e:
                st.error(f"グラフ表示でエラーが発生しました: {str(e)}")
                # フォールバック：元の図をそのまま表示
                try:
                    st.pyplot(fig)
                except:
                    st.error("グラフの表示に失敗しました。")
        
        # --- 詳細レポート（改善版） ---
        with st.expander("詳細レポート", expanded=False):
            if report is not None:
                try:
                    # レポートを日本語に翻訳
                    st.markdown("**📋 Causal Impact分析の詳細レポート**")
                    
                    # 信頼水準を取得（デフォルト95%）
                    confidence_level = confidence_level / 100 if confidence_level else 0.95
                    
                    # 翻訳処理を実行
                    report_jp = translate_causal_impact_report(str(report), alpha=confidence_level)
                    
                    # 翻訳されたレポートを段落ごとに分割して表示
                    report_paragraphs = report_jp.split('\n\n')
                    
                    for paragraph in report_paragraphs:
                        if paragraph.strip():
                            # 段落内の文章を適切に表示
                            paragraph = paragraph.strip()
                            
                            # タイトル行の処理
                            if '分析レポート {CausalImpact}' in paragraph:
                                st.markdown(f"**{paragraph}**")
                            # 事後確率などの重要な統計値を強調表示
                            elif '事後確率' in paragraph or 'p値' in paragraph:
                                st.markdown(f"**{paragraph}**")
                            else:
                                st.markdown(paragraph)
                    
                except Exception as e:
                    st.error(f"レポート翻訳でエラーが発生しました: {str(e)}")
                    # フォールバック：元の英語レポートを表示
                    st.text(str(report))
        
        # --- 結果の解釈ガイド（簡潔版） ---
        with st.expander("結果の解釈ガイド", expanded=False):
            if current_analysis_type == "単群推定（処置群のみを使用）":
                st.markdown("""
<div style="line-height:1.6;">
<p><strong>分析手法の特徴：</strong>介入前のトレンドと季節性から「介入がなかった場合」の予測値を推定し、実測値と比較。</p>
<p><strong>信頼性と制約：</strong>対照群がないため、外部要因の影響も効果として計測される可能性があります。結果の解釈には注意が必要。</p>
<p><strong>有意性の判断：</strong>信頼区間が0を含まない場合に統計的に有意。実用的な効果サイズも併せて判断。</p>
</div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
<div style="line-height:1.6;">
<p><strong>分析手法の特徴：</strong>対照群との関係から「介入がなかった場合」の処置群予測値を算出し、実測値と比較。</p>
<p><strong>信頼性の利点：</strong>対照群により外部要因の影響を適切に除去し、より信頼性の高い因果効果を推定。</p>
<p><strong>有意性の判断：</strong>信頼区間が0を含まない場合に統計的に有意。効果の持続性・安定性も確認。</p>
</div>
                """, unsafe_allow_html=True)

        # --- 分析品質の評価（簡潔版） ---
        with st.expander("分析品質の評価", expanded=False):
            # 分析品質のチェック項目
            quality_items = []
            
            # データ量の評価
            analysis_period = st.session_state.get('analysis_period', {})
            if analysis_period:
                try:
                    dataset = st.session_state.get('dataset')
                    if dataset is not None:
                        dataset_dates = pd.to_datetime(dataset['ymd']).dt.date
                        pre_mask = (dataset_dates >= analysis_period['pre_start']) & (dataset_dates <= analysis_period['pre_end'])
                        post_mask = (dataset_dates >= analysis_period['post_start']) & (dataset_dates <= analysis_period['post_end'])
                        pre_count = pre_mask.sum()
                        post_count = post_mask.sum()
                        total_count = pre_count + post_count
                        
                        # データ量評価
                        if current_analysis_type == "単群推定（処置群のみを使用）":
                            if total_count >= 36:
                                quality_items.append(["✅", "データ量", f"{total_count}件（推奨36件以上）"])
                            else:
                                quality_items.append(["⚠️", "データ量", f"{total_count}件（推奨36件以上に不足）"])
                        else:
                            if total_count >= 24:
                                quality_items.append(["✅", "データ量", f"{total_count}件（推奨24件以上）"])
                            else:
                                quality_items.append(["⚠️", "データ量", f"{total_count}件（推奨24件以上に不足）"])
                        
                        # 介入前期間比率の評価（単群のみ）
                        if current_analysis_type == "単群推定（処置群のみを使用）" and total_count > 0:
                            pre_ratio = pre_count / total_count * 100
                            if pre_ratio >= 60:
                                quality_items.append(["✅", "介入前期間比率", f"{pre_ratio:.1f}%（推奨60%以上）"])
                            else:
                                quality_items.append(["⚠️", "介入前期間比率", f"{pre_ratio:.1f}%（推奨60%以上）"])
                except Exception as e:
                    quality_items.append(["❌", "データ評価", "期間データの評価でエラーが発生"])
            
            # 分析タイプ別の評価
            if current_analysis_type == "単群推定（処置群のみを使用）":
                quality_items.append(["ℹ️", "分析手法", "単群推定（外部要因の影響に注意）"])
            else:
                quality_items.append(["✅", "分析手法", "二群比較（外部要因の統制可能）"])
            
            # 品質評価テーブルの表示
            if quality_items:
                quality_df = pd.DataFrame(quality_items, columns=['評価', '項目', '詳細'])
                st.dataframe(quality_df, use_container_width=True, hide_index=True)
        
        # --- ダウンロード機能（Phase 3.3で実装予定） ---
        st.markdown('<div class="section-title">結果のダウンロード</div>', unsafe_allow_html=True)
        st.info("📥 **ダウンロード機能**：CSV・PDFダウンロード機能は次回実装予定です。")
    
    else:
        st.error("分析結果が見つかりません。再度分析を実行してください。")

st.markdown("---")
st.markdown("### 🚧 開発進捗")
st.markdown("**処置群のみ分析機能**の実装進捗：")
st.markdown("""
- ✅ 処置群のみデータの取り込み機能
- ✅ 介入ポイント自動推奨機能  
- ✅ 期間設定・パラメータ設定機能
- ✅ 分析実行機能（Phase 3.1完了）
- 🔄 結果表示機能（Phase 3.2実装中）
- 🔄 ダウンロード機能（Phase 3.3実装予定）
""") 