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
        fig = ci.plot(figsize=(11, 7))
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
                    "approximate" in text_content or
                    "first" in text_content.lower() or
                    "removed due to" in text_content.lower()):
                    text.remove()  # テキストを完全に削除
        
        # フィギュアレベルでのテキスト削除も試行
        if hasattr(fig, 'texts'):
            fig_texts = fig.texts[:]  # フィギュアのテキストリストのコピーを作成
            for text in fig_texts:
                text_content = text.get_text()
                if ("Note:" in text_content or
                    "observations were removed" in text_content or
                    "diffuse initialization" in text_content or
                    "approximate" in text_content or
                    "first" in text_content.lower() or
                    "removed due to" in text_content.lower()):
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

def build_single_group_unified_summary_table(ci, confidence_level=95):
    """
    単群推定分析のCausalImpactのsummary()出力を直接使用して統一した分析結果テーブルを生成する関数
    詳細レポート、分析結果概要、CSV出力で同じ数値を使用して一貫性を保つ
    
    Parameters:
    -----------
    ci : CausalImpact
        分析結果オブジェクト
    confidence_level : int
        信頼水準（%）、デフォルト95%
        
    Returns:
    --------
    pandas.DataFrame
        整形された分析結果テーブル（詳細レポートと同じ数値）
    """
    try:
        import pandas as pd
        import numpy as np
        import re
        
        # CausalImpactのsummary()を取得
        summary_text = str(ci.summary())
        lines = [l for l in summary_text.split('\n') if l.strip()]
        
        results_data = []
        
        # p値を抽出
        p_value = None
        for line in lines:
            if 'Posterior tail-area probability p:' in line:
                p_match = re.search(r'p:\s+([0-9.]+)', line)
                if p_match:
                    p_value = float(p_match.group(1))
                    break
        
        # サマリーデータを解析（詳細レポートと同じ方法）
        for line in lines[1:]:  # ヘッダー行をスキップ
            parts = re.split(r'\s{2,}', line.strip())
            if len(parts) == 3:
                item_name = parts[0]
                avg_value = parts[1]
                cum_value = parts[2]
                
                # 項目名を日本語化
                if 'Actual' in item_name:
                    jp_name = '実測値'
                elif 'Predicted' in item_name:
                    jp_name = '予測値' if '95% CI' not in line else f'予測値 {confidence_level}% 信頼区間'
                elif 'AbsEffect' in item_name:
                    jp_name = '絶対効果' if '95% CI' not in line else f'絶対効果 {confidence_level}% 信頼区間'
                elif 'RelEffect' in item_name:
                    jp_name = '相対効果' if '95% CI' not in line else f'相対効果 {confidence_level}% 信頼区間'
                else:
                    jp_name = item_name
                
                # 相対効果の場合は%表記に変換し、平均値・累積値を同じにする
                if 'RelEffect' in item_name:
                    try:
                        # パーセンテージ変換
                        if '[' in avg_value and ']' in avg_value:
                            # 信頼区間の場合
                            avg_value = avg_value.replace('%', '')  # 既に%が含まれている場合は除去
                            if not '%' in avg_value:
                                # %が含まれていない場合は変換
                                matches = re.findall(r'[-+]?[0-9]*\.?[0-9]+', avg_value)
                                if len(matches) >= 2:
                                    lower = float(matches[0]) * 100
                                    upper = float(matches[1]) * 100
                                    avg_value = f"[{lower:.1f}%, {upper:.1f}%]"
                        else:
                            # 単一値の場合
                            try:
                                rel_val = float(avg_value) * 100
                                avg_value = f"{rel_val:.1f}%"
                            except:
                                if not '%' in avg_value:
                                    avg_value += '%'
                        
                        # 累積値は平均値と同じにする（相対効果の場合）
                        cum_value = avg_value
                    except:
                        pass
                
                results_data.append([jp_name, avg_value, cum_value])
        
        # p値を追加
        if p_value is not None:
            results_data.append(['p値（事後確率）', f"{p_value:.4f}", f"{p_value:.4f}"])
        
        # DataFrameを作成
        df_result = pd.DataFrame(results_data, columns=['指標', '分析期間の平均値', '分析期間の累積値'])
        
        return df_result
        
    except Exception as e:
        print(f"Error in build_single_group_unified_summary_table: {e}")
        # エラーの場合は元の関数にフォールバック
        return build_single_group_summary_dataframe(ci, confidence_level)

def build_single_group_summary_dataframe(ci, alpha_percent):
    """
    CausalImpactの分析結果を見やすい表形式で整理する関数（単群推定用）
    統一関数を優先使用し、エラー時のみ独自計算を実行
    
    Parameters:
    -----------
    ci : CausalImpact
        分析結果オブジェクト
    alpha_percent : int
        信頼水準（%）
        
    Returns:
    --------
    pandas.DataFrame
        整形された分析結果テーブル
    """
    try:
        # まず統一関数を試行
        return build_single_group_unified_summary_table(ci, alpha_percent)
    except:
        # 統一関数が失敗した場合のみ独自計算を実行
        pass
    
    try:
        import pandas as pd
        import numpy as np
        
        # CSVと同じデータソースを使用：ci.inferencesから直接計算
        if hasattr(ci, 'inferences') and ci.inferences is not None:
            df = ci.inferences.copy().reset_index()
        elif hasattr(ci, 'data'):
            df = ci.data.copy().reset_index()
        else:
            # フォールバック：既存の方法
            return build_single_group_summary_fallback(ci, alpha_percent)
        
        # 日付列を統一
        if 'index' in df.columns:
            df = df.rename(columns={'index': 'date'})
        elif df.index.name:
            df = df.reset_index().rename(columns={df.index.name: 'date'})
        
        # 日付列が存在しない場合の対処
        if 'date' not in df.columns:
            if len(df.columns) > 0:
                df = df.rename(columns={df.columns[0]: 'date'})
            else:
                return pd.DataFrame(columns=['指標', '分析期間の平均値', '分析期間の累積値'])
        
        # 列名マッピング（CSVと同じ）
        column_mapping = {
            'predicted': 'preds',
            'predicted_lower': 'preds_lower', 
            'predicted_upper': 'preds_upper',
            'point_effects': 'point_effects',
            'point_effects_lower': 'point_effects_lower',
            'point_effects_upper': 'point_effects_upper'
        }
        
        # 列名を統一
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # 実測値（y）の算出（予測値＋効果）
        if 'y' not in df.columns:
            if 'preds' in df.columns and 'point_effects' in df.columns:
                df['y'] = df['preds'] + df['point_effects']
            else:
                # データが不足している場合はフォールバック
                return build_single_group_summary_fallback(ci, alpha_percent)
        
        # 介入期間のデータのみを抽出（累積値用）
        # セッション状態から期間情報を取得
        analysis_period = None
        try:
            import streamlit as st
            if hasattr(st, 'session_state') and 'analysis_period' in st.session_state:
                analysis_period = st.session_state['analysis_period']
        except:
            pass
        
        if analysis_period and 'post_start' in analysis_period and 'post_end' in analysis_period:
            post_start = pd.to_datetime(analysis_period['post_start'])
            post_end = pd.to_datetime(analysis_period['post_end'])
            mask_post = (pd.to_datetime(df['date']) >= post_start) & (pd.to_datetime(df['date']) <= post_end)
            post_data = df[mask_post].copy()
        else:
            # 期間情報が取得できない場合は全データを使用
            post_data = df.copy()
        
        if len(post_data) == 0:
            return build_single_group_summary_fallback(ci, alpha_percent)
        
        # 信頼水準の計算（パーセント→少数）
        confidence_level = alpha_percent
        
        # 各指標の平均値と累積値を計算
        results_data = []
        
        # 実測値
        if 'y' in post_data.columns:
            actual_avg = post_data['y'].mean()
            actual_cum = post_data['y'].sum()  # 実測値は期間合計
            results_data.append(['実測値', f"{actual_avg:.1f}", f"{actual_cum:,.1f}"])
        
        # 予測値（標準偏差・反事実シナリオ表記を削除）
        if 'preds' in post_data.columns:
            pred_avg = post_data['preds'].mean()
            # CSVと同じ累積計算：各日の累積値の最終値
            pred_cumsum = post_data['preds'].cumsum()
            pred_cum = pred_cumsum.iloc[-1] if len(pred_cumsum) > 0 else 0
            
            results_data.append(['予測値', f"{pred_avg:.1f}", f"{pred_cum:,.1f}"])
        
        # 予測値信頼区間
        if 'preds_lower' in post_data.columns and 'preds_upper' in post_data.columns:
            pred_lower_avg = post_data['preds_lower'].mean()
            pred_upper_avg = post_data['preds_upper'].mean()
            # CSVと同じ累積計算
            pred_lower_cumsum = post_data['preds_lower'].cumsum()
            pred_upper_cumsum = post_data['preds_upper'].cumsum()
            pred_lower_cum = pred_lower_cumsum.iloc[-1] if len(pred_lower_cumsum) > 0 else 0
            pred_upper_cum = pred_upper_cumsum.iloc[-1] if len(pred_upper_cumsum) > 0 else 0
            
            avg_ci_str = f"[{pred_lower_avg:.1f}, {pred_upper_avg:.1f}]"
            cum_ci_str = f"[{pred_lower_cum:,.1f}, {pred_upper_cum:,.1f}]"
            results_data.append([f'予測値 {confidence_level}% 信頼区間', avg_ci_str, cum_ci_str])
        
        # 絶対効果（標準偏差を削除）
        if 'point_effects' in post_data.columns:
            abs_avg = post_data['point_effects'].mean()
            # CSVと同じ累積計算
            abs_cumsum = post_data['point_effects'].cumsum()
            abs_cum = abs_cumsum.iloc[-1] if len(abs_cumsum) > 0 else 0
            
            results_data.append(['絶対効果', f"{abs_avg:.1f}", f"{abs_cum:,.1f}"])
        
        # 絶対効果信頼区間
        if 'point_effects_lower' in post_data.columns and 'point_effects_upper' in post_data.columns:
            abs_lower_avg = post_data['point_effects_lower'].mean()
            abs_upper_avg = post_data['point_effects_upper'].mean()
            # CSVと同じ累積計算
            abs_lower_cumsum = post_data['point_effects_lower'].cumsum()
            abs_upper_cumsum = post_data['point_effects_upper'].cumsum()
            abs_lower_cum = abs_lower_cumsum.iloc[-1] if len(abs_lower_cumsum) > 0 else 0
            abs_upper_cum = abs_upper_cumsum.iloc[-1] if len(abs_upper_cumsum) > 0 else 0
            
            avg_ci_str = f"[{abs_lower_avg:.1f}, {abs_upper_avg:.1f}]"
            cum_ci_str = f"[{abs_lower_cum:,.1f}, {abs_upper_cum:,.1f}]"
            results_data.append([f'絶対効果 {confidence_level}% 信頼区間', avg_ci_str, cum_ci_str])
        
        # 相対効果（標準偏差を削除、明示的数値表示）
        if 'point_effects' in post_data.columns and 'preds' in post_data.columns:
            # 相対効果を統一した計算方法で算出：累積値ベース（総効果/総予測値）
            total_abs_effect = post_data['point_effects'].sum()
            total_pred = post_data['preds'].sum()
            rel_unified = (total_abs_effect / total_pred * 100) if total_pred != 0 else 0
            
            # 平均値・累積値ともに同じ値を使用
            results_data.append(['相対効果', f"{rel_unified:.1f}%", f"{rel_unified:.1f}%"])
        
        # 相対効果信頼区間（明示的数値表示）
        if ('point_effects_lower' in post_data.columns and 'point_effects_upper' in post_data.columns and 
            'preds' in post_data.columns):
            # 累積値ベースで統一した計算
            total_abs_lower = post_data['point_effects_lower'].sum()
            total_abs_upper = post_data['point_effects_upper'].sum()
            total_pred = post_data['preds'].sum()
            rel_lower_unified = (total_abs_lower / total_pred * 100) if total_pred != 0 else 0
            rel_upper_unified = (total_abs_upper / total_pred * 100) if total_pred != 0 else 0
            
            # 平均値・累積値ともに同じ値を使用
            rel_ci_unified_str = f"[{rel_lower_unified:.1f}%, {rel_upper_unified:.1f}%]"
            results_data.append([f'相対効果 {confidence_level}% 信頼区間', rel_ci_unified_str, rel_ci_unified_str])
        
        # p値（事後確率）（明示的数値表示）
        if hasattr(ci, 'p_value') and ci.p_value is not None:
            p_value = ci.p_value
            results_data.append(['p値（事後確率）', f"{p_value:.4f}", f"{p_value:.4f}"])
        else:
            # テキストサマリーからp値を抽出
            try:
                import re
                summary_text = str(ci.summary())
                p_match = re.search(r'Posterior tail-area probability p:\s+([0-9.]+)', summary_text)
                if p_match:
                    p_value = float(p_match.group(1))
                    results_data.append(['p値（事後確率）', f"{p_value:.4f}", f"{p_value:.4f}"])
            except:
                pass  # p値が取得できない場合はスキップ
        
        # DataFrameを作成
        df_result = pd.DataFrame(results_data, columns=['指標', '分析期間の平均値', '分析期間の累積値'])
        
        return df_result
        
    except Exception as e:
        print(f"Error in build_single_group_summary_dataframe: {e}")
        # エラーの場合はフォールバック
        return build_single_group_summary_fallback(ci, alpha_percent)

def build_single_group_summary_fallback(ci, alpha_percent):
    """
    フォールバックとしてテキストサマリーを解析してサマリーデータフレームを作成する関数
    
    Parameters:
    -----------
    ci : CausalImpact
        CausalImpactの分析結果サマリー
    alpha_percent : int
        信頼水準（%）
        
    Returns:
    --------
    pandas.DataFrame
        分析結果のサマリーテーブル
    """
    lines = [l for l in ci.summary().split('\n') if l.strip()]
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

def get_single_group_comprehensive_pdf_download_link(ci, analysis_info, summary_df, fig, confidence_level=95):
    """
    単群推定の分析結果の包括的PDFレポートを生成してダウンロードリンクを返す関数
    統一関数による数値でサマリーテーブルを更新し、詳細レポートとの一貫性を保つ
    
    Parameters:
    -----------
    ci : CausalImpact
        CausalImpactオブジェクト
    analysis_info : dict
        分析情報辞書
    summary_df : pandas.DataFrame
        分析結果概要テーブル
    fig : matplotlib.figure.Figure
        分析結果グラフ
    confidence_level : int
        信頼水準（95等）
        
    Returns:
    --------
    href, filename : str, str
        ダウンロードリンクのbase64データとファイル名
    """
    try:
        # 統一関数によるサマリーテーブルで更新
        try:
            unified_summary_df = build_single_group_unified_summary_table(ci, confidence_level)
            # インデックスをリセットして統一
            unified_summary_df = unified_summary_df.reset_index(drop=True)
            summary_df = unified_summary_df
        except Exception as e:
            print(f"統一サマリーテーブル生成でエラー、元のサマリーを使用: {e}")
            pass
    except:
        pass
    
    import pandas as pd
    import numpy as np
    import io
    import base64
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from datetime import datetime

    # メモリ上でPDFを作成
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
    
    # スタイル設定
    styles = getSampleStyleSheet()
    
    # フォント設定（日本語対応のためフォールバック）
    try:
        # Windowsの場合
        font_path = "C:/Windows/Fonts/NotoSansCJK-Regular.ttc"
        pdfmetrics.registerFont(TTFont('NotoSansCJK', font_path))
        font_name = 'NotoSansCJK'
    except:
        try:
            # 代替フォント
            font_path = "C:/Windows/Fonts/msgothic.ttc"
            pdfmetrics.registerFont(TTFont('MSGothic', font_path))
            font_name = 'MSGothic'
        except:
            # フォールバック：英語フォント
            font_name = 'Helvetica'
    
    # カスタムスタイル
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontName=font_name,
        fontSize=16,
        alignment=1,  # 中央揃え
        spaceAfter=20
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=12,
        spaceAfter=10
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=10,
        spaceAfter=8
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=9,
        spaceAfter=6
    )
    
    # PDF内容を構築
    story = []
    
    # タイトル
    story.append(Paragraph('Causal Impact分析レポート（単群推定）', title_style))
    story.append(Spacer(1, 12))
    
    # 分析条件
    if font_name == 'Helvetica':
        story.append(Paragraph("Analysis Conditions", subtitle_style))
    else:
        story.append(Paragraph("分析条件", subtitle_style))
    
    # analysis_info辞書から必要な情報を取得
    treatment_name = analysis_info.get('treatment_name', '分析対象')
    period_start = analysis_info.get('period_start')
    period_end = analysis_info.get('period_end')
    
    conditions_text = []
    if font_name == 'Helvetica':
        conditions_text.append(f"Analysis Target: {treatment_name}")
        conditions_text.append(f"Analysis Period: {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}")
        conditions_text.append(f"Method: Single Group Causal Impact")
        conditions_text.append(f"Confidence Level: {confidence_level}%")
    else:
        conditions_text.append(f"分析対象：{treatment_name}")
        conditions_text.append(f"分析期間：{period_start.strftime('%Y年%m月%d日')} ～ {period_end.strftime('%Y年%m月%d日')}")
        conditions_text.append(f"分析手法：単群推定Causal Impact")
        conditions_text.append(f"信頼水準：{confidence_level}%")
    
    for text in conditions_text:
        story.append(Paragraph(text, normal_style))
    story.append(Spacer(1, 12))
    
    # 分析結果サマリー
    story.append(Paragraph('分析結果サマリー', heading_style))
    
    # 分析結果概要テーブル
    story.append(Paragraph('分析結果概要', heading_style))
    
    # サマリーテーブルをPDF用に変換
    table_data = []
    for index, row in summary_df.iterrows():
        table_data.append([str(row[col]) for col in summary_df.columns])
    
    # ヘッダーを追加
    headers = [str(col) for col in summary_df.columns]
    table_data.insert(0, headers)
    
    # テーブル作成
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    story.append(Spacer(1, 12))
    
    # 分析レポートまとめメッセージ（単群推定用）
    summary_message = get_single_group_analysis_summary_message(ci, confidence_level)
    if summary_message:
        story.append(Paragraph(summary_message, normal_style))
    else:
        # フォールバック用メッセージ
        story.append(Paragraph("分析が完了しました。詳細はレポートを参照ください。", normal_style))
    story.append(Spacer(1, 20))
    
    # グラフを画像として挿入
    story.append(Paragraph('分析結果グラフ', heading_style))
    
    # グラフタイトル
    graph_title = f"{treatment_name}"
    graph_subtitle = "単群推定分析：介入前トレンドからの予測との比較"
    
    story.append(Paragraph(graph_title, normal_style))
    story.append(Paragraph(graph_subtitle, normal_style))
    story.append(Spacer(1, 6))
    
    # MatplotlibのグラフをPDFに変換
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
    img_buffer.seek(0)
    
    # 画像をPDFに挿入
    img = Image(img_buffer, width=450, height=300)  # サイズ調整
    story.append(img)
    story.append(Spacer(1, 12))
    
    # グラフの見方（単群推定用）
    graph_explanation = "実測データ（黒線）と介入前トレンドから推定した予測データ（青線）の比較により介入効果を評価。影の部分は予測の不確実性を示す信頼区間。介入前データのパターンを学習し、反事実シナリオを推定。"
    
    story.append(Paragraph(f"グラフの見方：{graph_explanation}", normal_style))
    
    # PDFを構築
    doc.build(story)
    pdf_buffer.seek(0)
    
    # Base64エンコード
    pdf_base64 = base64.b64encode(pdf_buffer.read()).decode()
    
    # ファイル名生成
    filename = f"causal_impact_report_{treatment_name}_{period_start.strftime('%Y%m%d')}_{period_end.strftime('%Y%m%d')}_SingleGroup.pdf"
    
    # ダウンロードリンク生成
    href = f'data:application/pdf;base64,{pdf_base64}'
    
    return href, filename

def get_single_group_comprehensive_csv_download_link(ci, analysis_info, confidence_level=95):
    """
    単群推定の予測値・実測値の詳細データをロングフォーマットCSVとしてダウンロードするリンクを生成する関数
    統一関数による数値でサマリー情報をコメントとして追加し、詳細レポートとの一貫性を保つ
    
    Parameters:
    -----------
    ci : CausalImpact
        CausalImpactオブジェクト
    analysis_info : dict
        分析情報（treatment_name, period_start, period_end等）
    confidence_level : int
        信頼水準（95等）
        
    Returns:
    --------
    href, filename : str, str
        ダウンロードリンクのbase64データとファイル名
    """
    import pandas as pd
    import numpy as np
    import io
    import base64
    
    # CausalImpactの結果データを取得
    if hasattr(ci, 'inferences') and ci.inferences is not None:
        df = ci.inferences.copy().reset_index()
    elif hasattr(ci, 'data'):
        # データがあるがinferencesがない場合の処理
        df = ci.data.copy().reset_index()
    else:
        raise ValueError("CausalImpactオブジェクトから分析結果を取得できません")
    
    # 日付列を統一
    if 'index' in df.columns:
        df = df.rename(columns={'index': 'date'})
    elif df.index.name:
        df = df.reset_index().rename(columns={df.index.name: 'date'})
    
    # 日付列が存在しない場合の対処
    if 'date' not in df.columns:
        # 最初の列を日付列として使用
        if len(df.columns) > 0:
            df = df.rename(columns={df.columns[0]: 'date'})
        else:
            # データフレームが空の場合は空のDataFrameを返す
            raise ValueError("データフレームに列が存在しません")
    
    # 15列の日本語名・英字名（要求仕様通り）
    jp_names = [
        '日付', '実測値', '予測値', '予測値下限', '予測値上限',
        '効果', '効果下限', '効果上限',
        '累積実測値', '累積予測値', '累積予測値下限', '累積予測値上限',
        '累積効果', '累積効果下限', '累積効果上限'
    ]
    
    en_names = [
        'date', 'y', 'preds', 'preds_lower', 'preds_upper',
        'point_effects', 'point_effects_lower', 'point_effects_upper',
        'post_cum_y', 'post_cum_pred', 'post_cum_pred_lower', 'post_cum_pred_upper',
        'post_cum_effects', 'post_cum_effects_lower', 'post_cum_effects_upper'
    ]
    
    # データフレームの列名マッピング（pycausalimpactの出力に対応）
    column_mapping = {
        'predicted': 'preds',
        'predicted_lower': 'preds_lower', 
        'predicted_upper': 'preds_upper',
        'point_effects': 'point_effects',
        'point_effects_lower': 'point_effects_lower',
        'point_effects_upper': 'point_effects_upper'
    }
    
    # 列名を統一
    for old_name, new_name in column_mapping.items():
        if old_name in df.columns:
            df = df.rename(columns={old_name: new_name})
    
    # 期間情報
    period_start = analysis_info.get('period_start')
    period_end = analysis_info.get('period_end')
    
    # 実測値（y）の算出（予測値＋効果）
    if 'y' not in df.columns:
        if 'preds' in df.columns and 'point_effects' in df.columns:
            df['y'] = df['preds'] + df['point_effects']
        else:
            df['y'] = np.nan
    
    # 累積値の計算（介入期間のみ）
    if period_start and period_end:
        post_start = pd.to_datetime(period_start)
        post_end = pd.to_datetime(period_end)
        mask_post = (pd.to_datetime(df['date']) >= post_start) & (pd.to_datetime(df['date']) <= post_end)
        
        # 介入期間のデータのみで累積値を計算
        post_data = df[mask_post].copy()
        if len(post_data) > 0:
            # 累積値を正しく計算（各行で累積されていく）
            post_data = post_data.reset_index(drop=True)
            post_data['post_cum_y'] = post_data['y'].cumsum()
            post_data['post_cum_pred'] = post_data['preds'].cumsum() if 'preds' in post_data.columns else np.nan
            post_data['post_cum_pred_lower'] = post_data['preds_lower'].cumsum() if 'preds_lower' in post_data.columns else np.nan
            post_data['post_cum_pred_upper'] = post_data['preds_upper'].cumsum() if 'preds_upper' in post_data.columns else np.nan
            post_data['post_cum_effects'] = post_data['point_effects'].cumsum() if 'point_effects' in post_data.columns else np.nan
            post_data['post_cum_effects_lower'] = post_data['point_effects_lower'].cumsum() if 'point_effects_lower' in post_data.columns else np.nan
            post_data['post_cum_effects_upper'] = post_data['point_effects_upper'].cumsum() if 'point_effects_upper' in post_data.columns else np.nan
            
            # 元のデータフレームの該当箇所に累積値をセット
            post_indices = df[mask_post].index
            for i, idx in enumerate(post_indices):
                if i < len(post_data):
                    df.loc[idx, 'post_cum_y'] = post_data.iloc[i]['post_cum_y']
                    df.loc[idx, 'post_cum_pred'] = post_data.iloc[i]['post_cum_pred']
                    df.loc[idx, 'post_cum_pred_lower'] = post_data.iloc[i]['post_cum_pred_lower']
                    df.loc[idx, 'post_cum_pred_upper'] = post_data.iloc[i]['post_cum_pred_upper']
                    df.loc[idx, 'post_cum_effects'] = post_data.iloc[i]['post_cum_effects']
                    df.loc[idx, 'post_cum_effects_lower'] = post_data.iloc[i]['post_cum_effects_lower']
                    df.loc[idx, 'post_cum_effects_upper'] = post_data.iloc[i]['post_cum_effects_upper']
    
    # 不足している列を追加（NaNで初期化）
    for en_name in en_names:
        if en_name not in df.columns:
            df[en_name] = np.nan
    
    # 出力用データフレームを作成（15列のみ）
    output_df = df[en_names].copy()
    
    # 日付をYYYY/MM/DD形式に変換
    try:
        output_df['date'] = pd.to_datetime(output_df['date']).dt.strftime('%Y/%m/%d')
    except Exception as e:
        # 日付変換に失敗した場合は文字列として出力
        output_df['date'] = output_df['date'].astype(str)
    
    # CSVバッファを作成
    csv_buffer = io.StringIO()
    
    # 統一関数によるサマリー情報をコメントとして追加
    try:
        unified_summary = build_single_group_unified_summary_table(ci, confidence_level)
        csv_buffer.write("# 分析結果サマリー（CausalImpact summary()出力ベース）\n")
        for idx, row in unified_summary.iterrows():
            csv_buffer.write(f"# {row['指標']}: 平均値={row['分析期間の平均値']}, 累積値={row['分析期間の累積値']}\n")
        csv_buffer.write("#\n")
        csv_buffer.write("# 以下は日次詳細データ（15列フォーマット）\n")
        csv_buffer.write("#\n")
    except Exception as e:
        print(f"統一サマリー追加でエラー: {e}")
        csv_buffer.write("# 分析結果詳細データ（単群推定）\n")
        csv_buffer.write("#\n")
    
    # 1行目：日本語項目名
    csv_buffer.write(','.join(jp_names) + '\n')
    
    # 2行目：英字変数名
    csv_buffer.write(','.join(en_names) + '\n')
    
    # 3行目以降：実データ
    output_df.to_csv(csv_buffer, index=False, header=False)
    
    # 注釈を追加
    csv_buffer.write('\n※I～O列の累積値は、介入期間のみ出力しています（介入期間外は空欄）。\n')
    csv_buffer.write('※分析結果サマリーの数値は、CausalImpactライブラリのsummary()出力と完全一致しています。\n')
    
    # Base64エンコード
    csv_string = csv_buffer.getvalue()
    csv_base64 = base64.b64encode(csv_string.encode('utf-8-sig')).decode()
    
    # ファイル名生成
    treatment_name = analysis_info.get('treatment_name', '分析対象')
    filename = f"causal_impact_detail_{treatment_name}_{period_start.strftime('%Y%m%d')}_{period_end.strftime('%Y%m%d')}_SingleGroup.csv"
    
    # ダウンロードリンク生成
    href = f'data:text/csv;charset=utf-8-sig;base64,{csv_base64}'
    
    return href, filename

def get_single_group_analysis_summary_message(ci, confidence_level=95):
    """
    単群推定の分析結果から相対効果と統計的有意性を判定してサマリーメッセージを生成する関数
    build_single_group_summary_dataframeと同じデータソースと計算方法を使用して一貫性を保つ
    
    Parameters:
    -----------
    ci : CausalImpact
        分析結果オブジェクト
    confidence_level : int
        信頼水準（%）、デフォルト95%
        
    Returns:
    --------
    str or None
        分析結果のサマリーメッセージ（生成できない場合はNone）
    """
    try:
        import pandas as pd
        import numpy as np
        import re
        
        # build_single_group_summary_dataframeと同じデータソースを使用
        if hasattr(ci, 'inferences') and ci.inferences is not None:
            df = ci.inferences.copy().reset_index()
        elif hasattr(ci, 'data'):
            df = ci.data.copy().reset_index()
        else:
            # フォールバック：既存の方法
            return get_single_group_analysis_summary_message_fallback(ci, confidence_level)
        
        # 日付列を統一
        if 'index' in df.columns:
            df = df.rename(columns={'index': 'date'})
        elif df.index.name:
            df = df.reset_index().rename(columns={df.index.name: 'date'})
        
        if 'date' not in df.columns:
            if len(df.columns) > 0:
                df = df.rename(columns={df.columns[0]: 'date'})
            else:
                return get_single_group_analysis_summary_message_fallback(ci, confidence_level)
        
        # 列名マッピング（build_single_group_summary_dataframeと同じ）
        column_mapping = {
            'predicted': 'preds',
            'predicted_lower': 'preds_lower', 
            'predicted_upper': 'preds_upper',
            'point_effects': 'point_effects',
            'point_effects_lower': 'point_effects_lower',
            'point_effects_upper': 'point_effects_upper'
        }
        
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # 実測値（y）の算出
        if 'y' not in df.columns:
            if 'preds' in df.columns and 'point_effects' in df.columns:
                df['y'] = df['preds'] + df['point_effects']
            else:
                return get_single_group_analysis_summary_message_fallback(ci, confidence_level)
        
        # 介入期間のデータのみを抽出
        analysis_period = None
        try:
            import streamlit as st
            if hasattr(st, 'session_state') and 'analysis_period' in st.session_state:
                analysis_period = st.session_state['analysis_period']
        except:
            pass
        
        if analysis_period and 'post_start' in analysis_period and 'post_end' in analysis_period:
            post_start = pd.to_datetime(analysis_period['post_start'])
            post_end = pd.to_datetime(analysis_period['post_end'])
            mask_post = (pd.to_datetime(df['date']) >= post_start) & (pd.to_datetime(df['date']) <= post_end)
            post_data = df[mask_post].copy()
        else:
            post_data = df.copy()
        
        if len(post_data) == 0:
            return get_single_group_analysis_summary_message_fallback(ci, confidence_level)
        
        # build_single_group_summary_dataframeと同じ方法で相対効果を計算（累積値を使用）
        relative_effect = None
        p_value = None
        
        if 'point_effects' in post_data.columns and 'preds' in post_data.columns:
            # 統一した累積値ベースの計算（アプリ表示と完全に同じ方法）
            total_abs_effect = post_data['point_effects'].sum()
            total_pred = post_data['preds'].sum()
            relative_effect = (total_abs_effect / total_pred * 100) if total_pred != 0 else 0
        
        # p値の取得
        if hasattr(ci, 'p_value') and ci.p_value is not None:
            p_value = ci.p_value
        else:
            # テキストサマリーからp値を抽出
            try:
                summary_text = str(ci.summary())
                p_match = re.search(r'Posterior tail-area probability p:\s+([0-9.]+)', summary_text)
                if p_match:
                    p_value = float(p_match.group(1))
            except:
                pass
        
        # 統計的有意性の判定（信頼区間による）
        is_significant = False
        if ('point_effects_lower' in post_data.columns and 'point_effects_upper' in post_data.columns):
            # 累積効果の信頼区間で判定
            abs_lower_cumsum = post_data['point_effects_lower'].cumsum()
            abs_upper_cumsum = post_data['point_effects_upper'].cumsum()
            lower_bound = abs_lower_cumsum.iloc[-1] if len(abs_lower_cumsum) > 0 else 0
            upper_bound = abs_upper_cumsum.iloc[-1] if len(abs_upper_cumsum) > 0 else 0
            if (lower_bound > 0 and upper_bound > 0) or (lower_bound < 0 and upper_bound < 0):
                is_significant = True
        
        # メッセージの生成
        if relative_effect is not None and p_value is not None:
            # 統計的有意性の判定（p値による）
            is_significant_by_p = p_value < 0.05
            
            # より確実な有意性判定（信頼区間とp値の両方を考慮）
            final_significance = is_significant or is_significant_by_p
            
            if final_significance:
                return f"相対効果は {relative_effect:+.1f}% で、統計的に有意です（p = {p_value:.3f}）。詳しくは、この下の「詳細レポート」を参照ください。"
            else:
                return f"相対効果は {relative_effect:+.1f}% ですが、統計的には有意ではありません（p = {p_value:.3f}）。詳しくは、この下の「詳細レポート」を参照ください。"
        
        return get_single_group_analysis_summary_message_fallback(ci, confidence_level)
        
    except Exception as e:
        print(f"Error in get_single_group_analysis_summary_message: {e}")
        return get_single_group_analysis_summary_message_fallback(ci, confidence_level)

def get_single_group_analysis_summary_message_fallback(ci, confidence_level=95):
    """
    フォールバック用の単群推定分析結果サマリーメッセージ生成関数
    """
    try:
        import re
        
        # 相対効果と有意性の取得
        relative_effect = None
        p_value = None
        is_significant = False
        
        # 1. CausalImpactのsummary_dataから取得を試行
        if hasattr(ci, 'summary_data') and ci.summary_data is not None:
            if 'rel_effect' in ci.summary_data.index:
                relative_effect = ci.summary_data.loc['rel_effect', 'average'] * 100
            
            # 統計的有意性の判定（信頼区間による）
            if ('abs_effect_lower' in ci.summary_data.index and 
                'abs_effect_upper' in ci.summary_data.index):
                lower_bound = ci.summary_data.loc['abs_effect_lower', 'cumulative']
                upper_bound = ci.summary_data.loc['abs_effect_upper', 'cumulative']
                if (lower_bound > 0 and upper_bound > 0) or (lower_bound < 0 and upper_bound < 0):
                    is_significant = True
        
        # 2. p値の取得
        if hasattr(ci, 'p_value') and ci.p_value is not None:
            p_value = ci.p_value
        else:
            # テキストサマリーからp値を抽出
            summary_text = str(ci.summary())
            p_match = re.search(r'Posterior tail-area probability p:\s+([0-9.]+)', summary_text)
            if p_match:
                p_value = float(p_match.group(1))
        
        # 3. フォールバック：テキストから相対効果も抽出
        if relative_effect is None:
            summary_text = str(ci.summary())
            # 相対効果の行を探す（パーセンテージ形式）
            for line in summary_text.split('\n'):
                if 'RelEffect' in line or '相対効果' in line:
                    # パーセンテージ値を抽出
                    percent_match = re.search(r'([-+]?\d+\.?\d*)%', line)
                    if percent_match:
                        relative_effect = float(percent_match.group(1))
                        break
        
        # さらなるフォールバック：DataFrame型のsummaryからの抽出
        if relative_effect is None and hasattr(ci, 'summary'):
            try:
                summary_df = ci.summary
                if hasattr(summary_df, 'loc') and 'RelEffect' in summary_df.index:
                    rel_effect_val = summary_df.loc['RelEffect', 'Average']
                    if not hasattr(rel_effect_val, '__iter__'):
                        relative_effect = rel_effect_val * 100
            except:
                pass
        
        # 4. メッセージの生成
        if relative_effect is not None and p_value is not None:
            # 統計的有意性の判定（p値による）
            is_significant_by_p = p_value < 0.05
            
            # より確実な有意性判定（信頼区間とp値の両方を考慮）
            final_significance = is_significant or is_significant_by_p
            
            if final_significance:
                return f"相対効果は {relative_effect:+.1f}% で、統計的に有意です（p = {p_value:.3f}）。詳しくは、この下の「詳細レポート」を参照ください。"
            else:
                return f"相対効果は {relative_effect:+.1f}% ですが、統計的には有意ではありません（p = {p_value:.3f}）。詳しくは、この下の「詳細レポート」を参照ください。"
        
        return None
        
    except Exception as e:
        print(f"Error in get_single_group_analysis_summary_message_fallback: {e}")
        return None 