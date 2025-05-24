# -*- coding: utf-8 -*-
"""
Causal Impact分析アプリ 定数・設定値

アプリケーション全体で使用する定数を一元管理
"""

import os

# === ファイルパス設定 ===
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
STYLES_DIR = os.path.join(PROJECT_ROOT, 'styles')
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'config')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
DOCS_DIR = os.path.join(PROJECT_ROOT, 'docs')
FONTS_DIR = os.path.join(PROJECT_ROOT, 'fonts')

CUSTOM_CSS_PATH = os.path.join(STYLES_DIR, 'custom.css')

# === データ要件 ===
REQUIRED_COLUMNS = ['ymd', 'qty']
DATE_FORMAT = 'YYYYMMDD'
DATE_COLUMN = 'ymd'
QUANTITY_COLUMN = 'qty'

# === セッション状態のキー ===
SESSION_KEYS = {
    'INITIALIZED': 'session_initialized',
    'DATA_LOADED': 'data_loaded',
    'DATASET_CREATED': 'dataset_created',
    'PARAMS_SAVED': 'params_saved',
    'ANALYSIS_COMPLETED': 'analysis_completed',
    'PERIOD_DEFAULTS': 'period_defaults',
}

# === 期間設定のデフォルト値 ===
PERIOD_DEFAULTS = {
    'pre_start': None,
    'pre_end': None,
    'post_start': None,
    'post_end': None
}

# === 削除対象のセッションキー ===
RESET_SESSION_KEYS = [
    'df_treat', 'df_ctrl', 'treatment_name', 'control_name',
    'dataset', 'analysis_period', 'analysis_params'
]

# === UI設定 ===
PAGE_CONFIG = {
    'layout': 'wide',
    'page_title': 'Causal Impact 分析',
    'page_icon': '📊'
}

# === 分析パラメータのデフォルト値 ===
DEFAULT_ANALYSIS_PARAMS = {
    'alpha': 0.05,  # 信頼区間（5%=95%信頼区間）
    'standardize_data': True,
    'prior_level_sd': 0.01,
    'nseasons': 7,
    'season_duration': 1
}

# === ファイル名テンプレート ===
FILENAME_TEMPLATES = {
    'summary_csv': 'causal_impact_summary_{treatment}_{start}_{end}.csv',
    'graph_pdf': 'causal_impact_graph_{treatment}_{start}_{end}.pdf',
    'detail_csv': 'causal_impact_detail_{treatment}_{start}_{end}.csv'
}

# === エラーメッセージ ===
ERROR_MESSAGES = {
    'FILE_NOT_FOUND': 'ファイルが見つかりません',
    'INVALID_CSV_FORMAT': 'CSVファイルの形式が正しくありません',
    'MISSING_REQUIRED_COLUMNS': f'必須カラム（{", ".join(REQUIRED_COLUMNS)}）が見つかりません',
    'INVALID_DATE_FORMAT': f'日付形式が正しくありません（{DATE_FORMAT}形式で入力してください）',
    'ANALYSIS_ERROR': 'Causal Impact分析中にエラーが発生しました',
    'PERIOD_SETTING_ERROR': '期間設定にエラーがあります',
}

# === 成功メッセージ ===
SUCCESS_MESSAGES = {
    'DATA_LOADED': 'データの読み込みが完了しました',
    'DATASET_CREATED': 'データセットの作成が完了しました',
    'PARAMS_SAVED': '分析設定の保存が完了しました',
    'ANALYSIS_COMPLETED': '分析が正常に完了しました',
} 