import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import re
import io
import base64
from causalimpact import CausalImpact
import matplotlib
matplotlib.use('Agg')  # バックエンドを明示的に指定（サーバー環境対応）

def run_single_group_causal_impact_analysis(data, pre_period, post_period, nseasons=7, season_duration=1):
    """
    処置群のみのデータでCausal Impact分析を実行する関数
    
    Parameters:
    -----------
    data : pandas.DataFrame
        時系列データ（日付と処置群の値のみ）
    pre_period : list
        介入前期間 [start_date, end_date]
    post_period : list  
        介入後期間 [start_date, end_date]
    nseasons : int
        季節性の周期数（デフォルト：7日間の週次周期）
    season_duration : int
        各季節の長さ（デフォルト：1日）
        
    Returns:
    --------
    ci : CausalImpact
        分析結果オブジェクト
    summary : str
        分析結果サマリー
    report : str
        分析レポート
    fig : matplotlib.figure.Figure
        分析結果グラフ
    """
    try:
        # データの準備（処置群のみの場合）
        # CausalImpactは対照群なしでも動作するが、データ形式を調整
        if len(data.columns) == 2:  # 日付と処置群の値のみの場合
            # データフレームをCausalImpact用に調整
            analysis_data = data.copy()
            analysis_data.columns = ['date', 'y']  # 標準的な列名に変更
            analysis_data = analysis_data.set_index('date')
        else:
            analysis_data = data
        
        # 季節性パラメータを設定
        model_args = {
            'nseasons': nseasons,
            'season.duration': season_duration,
            'dynamic.regression': True
        }
        
        # Causal Impact分析を実行
        ci = CausalImpact(analysis_data, pre_period, post_period, model_args=model_args)
        
        # サマリーとレポートを取得
        summary = ci.summary()
        report = ci.summary(output='report')
        
        # グラフを作成
        fig = ci.plot(figsize=(12, 8))
        if fig is None:
            fig = plt.gcf()
        
        # グラフのタイトルを日本語に変更
        axes = fig.get_axes()
        if len(axes) >= 3:
            axes[0].set_title('実測値 vs 予測値', fontsize=12, weight='normal')
            axes[1].set_title('時点効果', fontsize=12, weight='normal')
            axes[2].set_title('累積効果', fontsize=12, weight='normal')
        
        # 下部の注釈メッセージを非表示にする
        for ax in axes:
            texts = ax.texts[:]  # テキストリストのコピーを作成
            for text in texts:
                text_content = text.get_text()
                if ("Note:" in text_content or 
                    "observations were removed" in text_content or
                    "diffuse initialization" in text_content or
                    "approximate" in text_content):
                    text.remove()  # テキストを完全に削除
        
        # 図全体のタイトルを削除
        fig.suptitle('')
        
        plt.tight_layout()
        
        return ci, summary, report, fig
        
    except Exception as e:
        raise Exception(f"処置群のみCausal Impact分析でエラーが発生しました: {str(e)}")

def validate_single_group_data(data, min_pre_period_days=30):
    """
    処置群のみのデータの妥当性をチェックする関数
    
    Parameters:
    -----------
    data : pandas.DataFrame
        時系列データ
    min_pre_period_days : int
        最低限必要な介入前期間の日数
        
    Returns:
    --------
    bool : 妥当性チェック結果
    str : エラーメッセージ（問題がある場合）
    """
    try:
        # データの基本チェック
        if data.empty:
            return False, "データが空です"
        
        total_days = len(data)
        min_total_days = min_pre_period_days + 7  # 介入前期間 + 最低限の介入後期間
        
        if total_days < min_total_days:
            return False, f"データが不十分です。現在{total_days}日間ですが、単群推定では最低{min_total_days}日間のデータが必要です。より信頼性の高い分析のため、37日以上のデータを推奨します。"
        
        # 欠損値チェック
        if data.isnull().any().any():
            return False, "データに欠損値が含まれています"
        
        # 日付の連続性チェック
        if len(data.columns) >= 2:
            if 'ymd' in data.columns:
                date_col = data['ymd']
            else:
                date_col = data.iloc[:, 0]
            
            # 日付型かどうかを確認
            if not pd.api.types.is_datetime64_any_dtype(date_col):
                # 日付型でない場合は変換を試行
                try:
                    # 文字列から日付への変換を試行
                    test_dates = pd.to_datetime(date_col.astype(str), format='%Y%m%d', errors='coerce')
                    if test_dates.isna().any():
                        # %Y%m%d形式で変換できない場合は他の形式も試行
                        test_dates = pd.to_datetime(date_col.astype(str), errors='coerce')
                        if test_dates.isna().any():
                            return False, "日付列の形式が正しくありません。YYYYMMDD形式または標準的な日付形式で入力してください。"
                except Exception as e:
                    return False, f"日付列の形式が正しくありません: {str(e)}"
        
        return True, ""
        
    except Exception as e:
        return False, f"データ検証中にエラーが発生しました: {str(e)}"

def suggest_intervention_point(data, min_pre_period_ratio=0.6):
    """
    データから最適な介入ポイントを提案する関数
    
    Parameters:
    -----------
    data : pandas.DataFrame
        時系列データ
    min_pre_period_ratio : float
        介入前期間の最低比率（デフォルト：全体の60%）
        
    Returns:
    --------
    suggested_date : datetime
        推奨介入日
    pre_period_days : int
        介入前期間の日数
    post_period_days : int
        介入後期間の日数
    """
    try:
        total_days = len(data)
        min_pre_days = int(total_days * min_pre_period_ratio)
        
        # 推奨介入ポイントは全体の70%地点
        suggested_index = int(total_days * 0.7)
        
        # データの第1列（日付列）を取得
        if 'ymd' in data.columns:
            suggested_date = data.iloc[suggested_index]['ymd']
        else:
            suggested_date = data.iloc[suggested_index, 0]
        
        # 日付型への変換を確実に行う
        if isinstance(suggested_date, str):
            # 文字列の場合はpandasで日付に変換
            try:
                suggested_date = pd.to_datetime(suggested_date)
            except:
                # 変換できない場合は文字列のまま返す
                pass
        elif not pd.api.types.is_datetime64_any_dtype(type(suggested_date)):
            # 日付型でない場合は文字列に変換
            suggested_date = str(suggested_date)
        
        pre_period_days = suggested_index
        post_period_days = total_days - suggested_index - 1
        
        return suggested_date, pre_period_days, post_period_days
        
    except Exception as e:
        # エラーが発生した場合はデフォルト値を返す
        total_days = len(data) if data is not None and not data.empty else 30
        suggested_index = int(total_days * 0.7)
        return "エラー：推奨日計算失敗", suggested_index, total_days - suggested_index - 1

def build_single_group_summary_dataframe(summary, alpha_percent):
    """
    処置群のみ分析の結果サマリーをデータフレームにまとめる関数
    
    Parameters:
    -----------
    summary : str
        CausalImpactの分析結果サマリー
    alpha_percent : int
        信頼水準（%）
        
    Returns:
    --------
    pandas.DataFrame
        整形されたサマリーデータフレーム
    """
    lines = [l for l in summary.split('\n') if l.strip()]
    data_lines = []
    
    # p値を抽出
    p_value = None
    for line in lines:
        if 'Posterior tail-area probability p:' in line:
            p_match = re.search(r'p:\s+([0-9.]+)', line)
            if p_match:
                p_value = float(p_match.group(1))
                break
    
    # サマリーデータを抽出・整形
    for line in lines[1:]:
        parts = re.split(r'\s{2,}', line.strip())
        if len(parts) == 3:
            item_name = parts[0]
            avg_value = parts[1]
            cum_value = parts[2]
            
            # 相対効果に関連する行を識別
            is_relative_effect = (
                '相対効果' in item_name or 
                'relative effect' in item_name.lower() or
                'relative' in item_name.lower() and 'effect' in item_name.lower() or
                '%' in avg_value and '%' in cum_value
            )
            
            if is_relative_effect:
                data_lines.append([avg_value, '同左'])
            else:
                data_lines.append([avg_value, cum_value])
    
    df_summary = pd.DataFrame(data_lines, columns=['分析期間の平均値','分析期間の累積値'])
    
    # インデックス名の設定
    japanese_index = [
        '実測値',
        '予測値（反事実シナリオ）',
        f'予測値 {alpha_percent}% 信頼区間',
        '絶対効果 (標準偏差)',
        f'絶対効果 {alpha_percent}% 信頼区間',
        '相対効果 (標準偏差)',
        f'相対効果 {alpha_percent}% 信頼区間'
    ]
    
    if len(df_summary) <= len(japanese_index):
        df_summary.index = japanese_index[:len(df_summary)]
    else:
        df_summary.index = japanese_index + [f"行{i+1}" for i in range(len(japanese_index), len(df_summary))]
    
    # 相対効果行を「同左」に設定
    for idx in df_summary.index:
        if '相対効果' in idx:
            df_summary.at[idx, '分析期間の累積値'] = '同左'
    
    # p値を追加
    if p_value is not None:
        p_value_str = f"{p_value:.4f}"
        df_summary.loc['p値 (事後確率)'] = [p_value_str, '同左']
    
    return df_summary

def get_single_group_interpretation(ci, alpha_level=0.05):
    """
    処置群のみ分析の結果解釈を生成する関数
    
    Parameters:
    -----------
    ci : CausalImpact
        分析結果オブジェクト
    alpha_level : float
        有意水準（デフォルト：0.05）
        
    Returns:
    --------
    str : 結果解釈テキスト
    """
    summary_data = ci.summary_data
    p_value = summary_data.loc['Posterior tail-area probability p:']['Posterior tail-area probability p:']
    
    # 効果の方向性を判定
    avg_effect = summary_data.loc['Actual']['Average']
    predicted_avg = summary_data.loc['Predicted']['Average'] 
    
    effect_direction = "正の効果" if avg_effect > predicted_avg else "負の効果"
    is_significant = p_value < alpha_level
    
    interpretation = f"""
    ## 分析結果の解釈（処置群のみ分析）
    
    **効果の有意性**: {'統計的に有意' if is_significant else '統計的に有意でない'} (p = {p_value:.4f})
    
    **効果の方向性**: {effect_direction}
    
    **注意事項**: 
    - この分析は処置群のみのデータに基づいています
    - 対照群がないため、外部要因の影響を完全に排除できない可能性があります
    - 介入前のトレンドと季節性パターンから反事実シナリオを構築しています
    - 結果の解釈には他の情報源との照合が推奨されます
    """
    
    return interpretation 