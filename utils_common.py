# -*- coding: utf-8 -*-
"""
Causal Impact分析アプリ 共通ユーティリティ

app.py内の共通処理を外部化
"""

import os
import streamlit as st
from config.constants import (
    CUSTOM_CSS_PATH, SESSION_KEYS, PERIOD_DEFAULTS, RESET_SESSION_KEYS
)

def load_css(css_file_path):
    """
    外部CSSファイルを読み込んでStreamlitに適用する
    
    Parameters:
    -----------
    css_file_path : str
        CSSファイルのパス
    """
    try:
        with open(css_file_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
        st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"CSSファイルが見つかりません: {css_file_path}")
    except Exception as e:
        st.warning(f"CSSファイルの読み込みエラー: {e}")

def initialize_session_state():
    """
    セッション状態を初期化する
    """
    if SESSION_KEYS['INITIALIZED'] not in st.session_state:
        st.session_state[SESSION_KEYS['INITIALIZED']] = True
        st.session_state[SESSION_KEYS['DATA_LOADED']] = False
        st.session_state[SESSION_KEYS['DATASET_CREATED']] = False
        st.session_state[SESSION_KEYS['PARAMS_SAVED']] = False
        st.session_state[SESSION_KEYS['ANALYSIS_COMPLETED']] = False
        st.session_state[SESSION_KEYS['PERIOD_DEFAULTS']] = PERIOD_DEFAULTS.copy()

def reset_session_state():
    """
    セッション状態をリセットする
    """
    # 初期化が必要な状態変数をリセット
    st.session_state[SESSION_KEYS['DATA_LOADED']] = False
    st.session_state[SESSION_KEYS['DATASET_CREATED']] = False
    st.session_state[SESSION_KEYS['PARAMS_SAVED']] = False
    st.session_state[SESSION_KEYS['ANALYSIS_COMPLETED']] = False
    st.session_state[SESSION_KEYS['PERIOD_DEFAULTS']] = PERIOD_DEFAULTS.copy()
    
    # その他の状態変数も削除
    for key in RESET_SESSION_KEYS:
        if key in st.session_state:
            del st.session_state[key]

def get_step_status():
    """
    各STEPのアクティブ状態を取得する
    
    Returns:
    --------
    dict: 各STEPのアクティブ状態
    """
    step1_active = True  # STEP 1は常に表示
    step2_active = False
    step3_active = False
    
    # データ読み込み済みならSTEP 2をアクティブに
    if st.session_state.get(SESSION_KEYS['DATA_LOADED'], False):
        if st.session_state.get(SESSION_KEYS['DATASET_CREATED'], False):
            step2_active = True
    
    # STEP 3のアクティブ状態を複数の条件で判定（確実性向上）
    # 1. 分析設定が完了している場合
    if st.session_state.get(SESSION_KEYS['PARAMS_SAVED'], False):
        step3_active = True
    
    # 2. 分析実行が完了している場合
    if st.session_state.get(SESSION_KEYS['ANALYSIS_COMPLETED'], False):
        step3_active = True
    
    # 3. STEP3表示フラグが設定されている場合（分析実行ボタン押下時）
    if st.session_state.get('show_step3', False):
        step3_active = True
        
    return {
        'step1': step1_active,
        'step2': step2_active,
        'step3': step3_active
    } 