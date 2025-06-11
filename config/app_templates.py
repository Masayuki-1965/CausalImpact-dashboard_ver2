# アプリ画面表示用テンプレート管理モジュール
# アプリ画面上の表示は常に日本語に固定（PDF出力とは独立）

def get_app_content():
    """
    アプリ画面表示用の日本語固定コンテンツテンプレート
    環境に関係なくアプリ画面では常に日本語表記を使用
    
    Returns:
    --------
    dict: アプリ画面用日本語コンテンツ辞書
    """
    return {
        # タイトル系
        'title_two_group': 'Causal Impact分析レポート（二群比較）',
        'title_single_group': 'Causal Impact分析レポート（単群推定）',
        'section_analysis_info': '■分析対象と条件',
        'section_summary': '■分析結果サマリー',
        'section_graph': '■分析結果グラフ',
        'label_target': '分析対象：',
        'label_period': '分析期間：',
        'label_method': '分析手法：',
        'method_two_group': '二群比較（Two-Group Causal Impact）',
        'method_single_group': '単群推定（Single Group Causal Impact）',
        'confidence_level': '信頼水準：',
        
        # アプリ画面用テーブル項目名（常に日本語）
        'table_indicator': '指標',
        'table_avg_analysis_period': '分析期間の平均値',
        'table_total_analysis_period': '分析期間の累積値',
        'table_actual': '実測値',
        'table_predicted': '予測値',
        'table_predicted_ci': '予測値 {}% 信頼区間',
        'table_absolute_effect': '絶対効果（実測値 − 予測値）',
        'table_relative_effect': '相対効果（絶対効果 ÷ 予測値）',
        'table_p_value': 'p値',
        
        # グラフ説明文
        'graph_explanation_two_group': 'グラフの見方：実測データ（黒線）と対照群から推定した予測データ（青線）の比較により純粋な介入効果を評価。影の部分は予測の不確実性を示す信頼区間。対照群により外部要因の影響を除去。',
        'graph_explanation_single_group': 'グラフの見方：実測データ（黒線）と予測データ（青線）の比較により介入効果を評価。影の部分は予測の不確実性を示す信頼区間。対照群がないため、外部要因の影響に注意が必要。',
        
        # コメント文テンプレート
        'comment_significant': '相対効果は {effect:+.1f}% で、統計的に有意です（p = {p_value:.3f}）。詳しくは「詳細レポート」を参照ください。',
        'comment_not_significant': '相対効果は {effect:+.1f}% ですが、統計的には有意ではありません（p = {p_value:.3f}）。詳しくは「詳細レポート」を参照ください。'
    }

def get_app_frequency_display_name(freq_option):
    """
    アプリ画面用データ頻度の表示名を取得（日本語固定）
    
    Parameters:
    -----------
    freq_option : str
        データ頻度オプション
        
    Returns:
    --------
    str: 日本語表示名
    """
    freq_mapping = {
        '月次': '月次',
        '旬次': '旬次',
        '週次': '週次',
        '日次': '日次',
        '時次': '時次'
    }
    
    return freq_mapping.get(freq_option, freq_option)

def get_app_comment_message(relative_effect, p_value, is_significant):
    """
    アプリ画面用コメントメッセージを生成（日本語固定）
    
    Parameters:
    -----------
    relative_effect : float
        相対効果（%）
    p_value : float
        p値
    is_significant : bool
        統計的有意性
        
    Returns:
    --------
    str: フォーマット済み日本語コメントメッセージ
    """
    content = get_app_content()
    
    if is_significant:
        return content['comment_significant'].format(effect=relative_effect, p_value=p_value)
    else:
        return content['comment_not_significant'].format(effect=relative_effect, p_value=p_value) 