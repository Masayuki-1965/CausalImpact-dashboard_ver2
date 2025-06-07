# PDF テンプレート管理モジュール
# 日本語・英語両対応のPDFレポートテンプレート

def get_pdf_content_japanese():
    """日本語版PDFコンテンツテンプレート"""
    return {
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
        'graph_explanation_two_group': 'グラフの見方：実測データ（黒線）と対照群から推定した予測データ（青線）の比較により純粋な介入効果を評価。影の部分は予測の不確実性を示す信頼区間。対照群により外部要因の影響を除去。',
        'graph_explanation_single_group': 'グラフの見方：実測データ（黒線）と予測データ（青線）の比較により介入効果を評価。影の部分は予測の不確実性を示す信頼区間。対照群がないため、外部要因の影響に注意が必要。',
        
        # テーブル項目名
        'table_indicator': '指標',
        'table_avg_analysis_period': '分析期間の平均値',
        'table_total_analysis_period': '分析期間の累積値',
        'table_actual': '実測値',
        'table_predicted': '予測値',
        'table_predicted_ci': '予測値 95% 信頼区間',
        'table_absolute_effect': '絶対効果',
        'table_relative_effect': '相対効果',
        'table_p_value': 'p値',
        
        # コメント文テンプレート
        'comment_significant': '相対効果は {effect:+.1f}% で、統計的に有意です（p = {p_value:.3f}）。詳しくは「詳細レポート」を参照ください。',
        'comment_not_significant': '相対効果は {effect:+.1f}% ですが、統計的には有意ではありません（p = {p_value:.3f}）。詳しくは「詳細レポート」を参照ください。'
    }

def get_pdf_content_english():
    """英語版PDFコンテンツテンプレート（日本語フォント利用不可時のフォールバック）"""
    return {
        'title_two_group': 'Causal Impact Analysis Report (Two-Group Comparison)',
        'title_single_group': 'Causal Impact Analysis Report (Single Group Estimation)',
        'section_analysis_info': 'Analysis Target and Conditions',
        'section_summary': 'Analysis Result Summary',
        'section_graph': 'Analysis Result Graph',
        'label_target': 'Analysis Target: ',
        'label_period': 'Analysis Period: ',
        'label_method': 'Analysis Method: ',
        'method_two_group': 'Two-Group Causal Impact',
        'method_single_group': 'Single Group Causal Impact',
        'confidence_level': 'Confidence Level: ',
        'graph_explanation_two_group': 'How to read the graph: Evaluate pure intervention effects by comparing actual data (black line) with predicted data (blue line) estimated from control group. Shaded area shows confidence interval indicating prediction uncertainty. External factors are eliminated by control group.',
        'graph_explanation_single_group': 'How to read the graph: Evaluate intervention effects by comparing actual data (black line) with predicted data (blue line). Shaded area shows confidence interval indicating prediction uncertainty. Attention needed for external factors due to absence of control group.',
        
        # テーブル項目名（英語版）
        'table_indicator': 'Indicator',
        'table_avg_analysis_period': 'Average in Analysis Period',
        'table_total_analysis_period': 'Cumulative in Analysis Period',
        'table_actual': 'Actual',
        'table_predicted': 'Predicted',
        'table_predicted_ci': 'Predicted 95% CI',
        'table_absolute_effect': 'Absolute Effect',
        'table_relative_effect': 'Relative Effect',
        'table_p_value': 'p-value',
        
        # コメント文テンプレート（英語版）
        'comment_significant': 'Relative effect is {effect:+.1f}% and statistically significant (p = {p_value:.3f}). Please refer to "Detailed Report" for more information.',
        'comment_not_significant': 'Relative effect is {effect:+.1f}% but not statistically significant (p = {p_value:.3f}). Please refer to "Detailed Report" for more information.'
    }

def get_pdf_content(use_japanese=True):
    """
    PDF作成用コンテンツを取得
    
    Parameters:
    -----------
    use_japanese : bool
        日本語フォントが利用可能な場合True、そうでなければFalse
        
    Returns:
    --------
    dict: PDFコンテンツ辞書
    """
    if use_japanese:
        return get_pdf_content_japanese()
    else:
        return get_pdf_content_english()

def format_analysis_info_section(content, analysis_info, total_data_count, confidence_level, is_single_group=False):
    """
    分析情報セクションをフォーマット
    
    Parameters:
    -----------
    content : dict
        PDFコンテンツ辞書
    analysis_info : dict
        分析情報
    total_data_count : int
        データ件数
    confidence_level : int
        信頼水準
    is_single_group : bool
        単群推定の場合True
        
    Returns:
    --------
    list: フォーマット済みテキストリスト
    """
    
    treatment_name = analysis_info.get('treatment_name', 'Analysis Target')
    control_name = analysis_info.get('control_name', 'Control Group')
    period_start = analysis_info.get('period_start')
    period_end = analysis_info.get('period_end')
    freq_option = analysis_info.get('freq_option', '')
    
    result = []
    
    # 分析対象
    if is_single_group:
        result.append(f"　{content['label_target']}　{treatment_name}")
    else:
        result.append(f"　{content['label_target']}　{treatment_name}（vs {control_name}）")
    
    # 分析期間
    if period_start and period_end:
        result.append(f"　{content['label_period']}　{period_start.strftime('%Y-%m-%d')} ～ {period_end.strftime('%Y-%m-%d')}（{total_data_count}件）（{freq_option}）")
    
    # 分析手法
    method = content['method_single_group'] if is_single_group else content['method_two_group']
    result.append(f"　{content['label_method']}　{method}（{content['confidence_level']}{confidence_level}%）")
    
    return result

def get_pdf_comment_message(relative_effect, p_value, is_significant, use_japanese=True):
    """
    PDF用コメントメッセージを生成
    
    Parameters:
    -----------
    relative_effect : float
        相対効果（%）
    p_value : float
        p値
    is_significant : bool
        統計的有意性
    use_japanese : bool
        日本語版の場合True
        
    Returns:
    --------
    str: フォーマット済みコメントメッセージ
    """
    content = get_pdf_content(use_japanese)
    
    if is_significant:
        return content['comment_significant'].format(effect=relative_effect, p_value=p_value)
    else:
        return content['comment_not_significant'].format(effect=relative_effect, p_value=p_value)