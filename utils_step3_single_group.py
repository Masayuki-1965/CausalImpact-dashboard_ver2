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
        
        # CausalImpactのsummary_dataから直接取得（より確実）
        if hasattr(ci, 'summary_data') and ci.summary_data is not None:
            summary_data = ci.summary_data
            results_data = []
            
            # p値の取得
            p_value = None
            if hasattr(ci, 'p_value'):
                p_value = ci.p_value
            else:
                # summary()テキストからp値を抽出
                try:
                    summary_text = str(ci.summary())
                    p_match = re.search(r'Posterior tail-area probability p:\s+([0-9.]+)', summary_text)
                    if p_match:
                        p_value = float(p_match.group(1))
                except:
                    pass
            
            # 項目を順番に処理（シンプルな構成）
            
            # 1. 実測値
            for index_name in summary_data.index:
                if 'actual' in str(index_name).lower():
                    avg_val = summary_data.loc[index_name, 'Average'] if 'Average' in summary_data.columns else summary_data.loc[index_name].iloc[0]
                    cum_val = summary_data.loc[index_name, 'Cumulative'] if 'Cumulative' in summary_data.columns else summary_data.loc[index_name].iloc[1]
                    results_data.append(['実測値', f"{avg_val:.1f}", f"{cum_val:.1f}"])
                    break
            
            # 2. 予測値
            for index_name in summary_data.index:
                if ('predicted' in str(index_name).lower() or 'prediction' in str(index_name).lower()) and 'lower' not in str(index_name).lower() and 'upper' not in str(index_name).lower():
                    avg_val = summary_data.loc[index_name, 'Average'] if 'Average' in summary_data.columns else summary_data.loc[index_name].iloc[0]
                    cum_val = summary_data.loc[index_name, 'Cumulative'] if 'Cumulative' in summary_data.columns else summary_data.loc[index_name].iloc[1]
                    results_data.append(['予測値', f"{avg_val:.1f}", f"{cum_val:.1f}"])
                    break
            
            # 3. 予測値信頼区間（予測値のすぐ下に配置）
            pred_lower = None
            pred_upper = None
            for index_name in summary_data.index:
                if 'predicted' in str(index_name).lower() and 'lower' in str(index_name).lower():
                    pred_lower = index_name
                elif 'predicted' in str(index_name).lower() and 'upper' in str(index_name).lower():
                    pred_upper = index_name
            
            if pred_lower and pred_upper:
                lower_avg = summary_data.loc[pred_lower, 'Average'] if 'Average' in summary_data.columns else summary_data.loc[pred_lower].iloc[0]
                upper_avg = summary_data.loc[pred_upper, 'Average'] if 'Average' in summary_data.columns else summary_data.loc[pred_upper].iloc[0]
                lower_cum = summary_data.loc[pred_lower, 'Cumulative'] if 'Cumulative' in summary_data.columns else summary_data.loc[pred_lower].iloc[1]
                upper_cum = summary_data.loc[pred_upper, 'Cumulative'] if 'Cumulative' in summary_data.columns else summary_data.loc[pred_upper].iloc[1]
                results_data.append([f'予測値 {confidence_level}% 信頼区間', f"[{lower_avg:.1f}, {upper_avg:.1f}]", f"[{lower_cum:.1f}, {upper_cum:.1f}]"])
            
            # 4. 絶対効果
            for index_name in summary_data.index:
                if ('abseffect' in str(index_name).lower() or 'abs_effect' in str(index_name).lower() or 'absolute' in str(index_name).lower()) and 'lower' not in str(index_name).lower() and 'upper' not in str(index_name).lower():
                    avg_val = summary_data.loc[index_name, 'Average'] if 'Average' in summary_data.columns else summary_data.loc[index_name].iloc[0]
                    cum_val = summary_data.loc[index_name, 'Cumulative'] if 'Cumulative' in summary_data.columns else summary_data.loc[index_name].iloc[1]
                    results_data.append(['絶対効果', f"{avg_val:.1f}", f"{cum_val:.1f}"])
                    break
            
            # 5. 相対効果
            for index_name in summary_data.index:
                if ('releffect' in str(index_name).lower() or 'rel_effect' in str(index_name).lower() or 'relative' in str(index_name).lower()) and 'lower' not in str(index_name).lower() and 'upper' not in str(index_name).lower():
                    avg_val = summary_data.loc[index_name, 'Average'] if 'Average' in summary_data.columns else summary_data.loc[index_name].iloc[0]
                    # %変換
                    rel_pct = avg_val * 100 if abs(avg_val) < 10 else avg_val
                    results_data.append(['相対効果', f"{rel_pct:.1f}%", f"{rel_pct:.1f}%"])
                    break
            
            # 6. p値
            if p_value is not None:
                results_data.append(['p値', f"{p_value:.4f}", f"{p_value:.4f}"])
            
            # DataFrameを作成
            df_result = pd.DataFrame(results_data, columns=['指標', '分析期間の平均値', '分析期間の累積値'])
            
            return df_result
        
        else:
            # フォールバック：テキスト解析
            return build_single_group_text_based_summary_table(ci, confidence_level)
        
    except Exception as e:
        print(f"Error in build_single_group_unified_summary_table: {e}")
        # エラーの場合は確実な日本語表記のフォールバックを使用
        return build_single_group_guaranteed_japanese_table(ci, confidence_level)

def build_single_group_text_based_summary_table(ci, confidence_level=95):
    """
    CausalImpactのテキスト出力を解析して日本語表記のテーブルを生成
    """
    try:
        import pandas as pd
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
        
        # テキスト解析で確実な日本語化
        for line in lines[1:]:  # ヘッダー行をスキップ
            if not line.strip():
                continue
                
            parts = re.split(r'\s{2,}', line.strip())
            if len(parts) >= 2:
                item_name = parts[0]
                avg_value = parts[1] if len(parts) > 1 else ""
                cum_value = parts[2] if len(parts) > 2 else avg_value
                
                # 完全な英語→日本語変換辞書
                translation_dict = {
                    'Actual': '実測値',
                    'Predicted': '予測値（標準偏差）',
                    'AbsEffect': '絶対効果（標準偏差）',
                    'RelEffect': '相対効果（標準偏差）'
                }
                
                jp_name = translation_dict.get(item_name, item_name)
                
                # CI行の判定と変換
                if '95% CI' in line or 'CI' in item_name:
                    if 'Predicted' in line or 'predicted' in item_name.lower():
                        jp_name = f'予測値 {confidence_level}% 信頼区間'
                    elif 'AbsEffect' in line or 'abs' in item_name.lower():
                        jp_name = f'絶対効果 {confidence_level}% 信頼区間'
                    elif 'RelEffect' in line or 'rel' in item_name.lower():
                        jp_name = f'相対効果 {confidence_level}% 信頼区間'
                
                # 相対効果の%変換
                if 'rel' in jp_name.lower() or '相対効果' in jp_name:
                    if '[' in avg_value and ']' in avg_value and '%' not in avg_value:
                        # 信頼区間の%変換
                        matches = re.findall(r'[-+]?[0-9]*\.?[0-9]+', avg_value)
                        if len(matches) >= 2:
                            lower = float(matches[0]) * 100
                            upper = float(matches[1]) * 100
                            avg_value = f"[{lower:.1f}%, {upper:.1f}%]"
                            cum_value = avg_value
                    elif '%' not in avg_value:
                        try:
                            rel_val = float(avg_value) * 100
                            avg_value = f"{rel_val:.1f}%"
                            cum_value = avg_value
                        except:
                            pass
                
                results_data.append([jp_name, avg_value, cum_value])
        
        # p値を追加
        if p_value is not None:
            results_data.append(['p値', f"{p_value:.4f}", f"{p_value:.4f}"])
        
        # DataFrameを作成
        df_result = pd.DataFrame(results_data, columns=['指標', '分析期間の平均値', '分析期間の累積値'])
        
        return df_result
        
    except Exception as e:
        print(f"Error in build_single_group_text_based_summary_table: {e}")
        return build_single_group_guaranteed_japanese_table(ci, confidence_level)

def build_single_group_guaranteed_japanese_table(ci, confidence_level=95):
    """
    確実に日本語表記を返すフォールバック関数
    """
    try:
        import pandas as pd
        import numpy as np
        
        # 最低限の日本語表記テーブルを構築
        results_data = [
            ['実測値', '---', '---'],
            ['予測値（標準偏差）', '---', '---'],
            [f'予測値 {confidence_level}% 信頼区間', '---', '---'],
            ['絶対効果（標準偏差）', '---', '---'],
            [f'絶対効果 {confidence_level}% 信頼区間', '---', '---'],
            ['相対効果（標準偏差）', '---', '---'],
            [f'相対効果 {confidence_level}% 信頼区間', '---', '---'],
            ['p値', '---', '---']
        ]
        
        return pd.DataFrame(results_data, columns=['指標', '分析期間の平均値', '分析期間の累積値'])
        
    except:
        # 最終フォールバック
        return pd.DataFrame(columns=['指標', '分析期間の平均値', '分析期間の累積値'])

def build_single_group_summary_dataframe(ci, alpha_percent):
    """
    単群推定の分析結果を見やすい表形式で整理する関数（日本語表記保証）
    統一関数を優先使用し、確実に日本語表記で表示
    
    Parameters:
    -----------
    ci : CausalImpact
        分析結果オブジェクト
    alpha_percent : int
        信頼水準（%）、95等を想定
        
    Returns:
    --------
    pandas.DataFrame
        整形された分析結果テーブル（日本語表記）
    """
    try:
        # 統一関数を使用（日本語表記保証）
        unified_result = build_single_group_unified_summary_table(ci, alpha_percent)
        if unified_result is not None and not unified_result.empty:
            return unified_result
    except Exception as e:
        print(f"Single group unified function error: {e}")
    
    # 統一関数が失敗した場合でも日本語表記を保証する独自実装
    try:
        import pandas as pd
        import numpy as np
        
        # CausalImpactのsummary()から数値を取得
        summary_text = str(ci.summary())
        lines = [l for l in summary_text.split('\n') if l.strip()]
        
        results_data = []
        
        # データの解析
        actual_avg = None
        pred_avg = None
        pred_sd = None
        pred_ci_lower = None
        pred_ci_upper = None
        abs_avg = None
        abs_sd = None
        abs_ci_lower = None
        abs_ci_upper = None
        rel_avg = None
        rel_sd = None
        rel_ci_lower = None
        rel_ci_upper = None
        p_value = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if 'Actual' in line:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        actual_avg = float(parts[1])
                    except:
                        pass
                        
            elif 'Predicted' in line:
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        pred_avg = float(parts[1])
                        if '(' in parts[2] and ')' in parts[3]:
                            pred_sd_str = parts[2].replace('(', '') + parts[3].replace(')', '')
                            pred_sd = float(pred_sd_str)
                    except:
                        pass
                if len(parts) >= 6:
                    try:
                        ci_str = ' '.join(parts[4:6])
                        ci_str = ci_str.replace('[', '').replace(']', '').replace(',', '')
                        ci_parts = ci_str.split()
                        if len(ci_parts) >= 2:
                            pred_ci_lower = float(ci_parts[0])
                            pred_ci_upper = float(ci_parts[1])
                    except:
                        pass
                        
            elif 'AbsEffect' in line:
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        abs_avg = float(parts[1])
                        if '(' in parts[2] and ')' in parts[3]:
                            abs_sd_str = parts[2].replace('(', '') + parts[3].replace(')', '')
                            abs_sd = float(abs_sd_str)
                    except:
                        pass
                if len(parts) >= 6:
                    try:
                        ci_str = ' '.join(parts[4:6])
                        ci_str = ci_str.replace('[', '').replace(']', '').replace(',', '')
                        ci_parts = ci_str.split()
                        if len(ci_parts) >= 2:
                            abs_ci_lower = float(ci_parts[0])
                            abs_ci_upper = float(ci_parts[1])
                    except:
                        pass
                        
            elif 'RelEffect' in line:
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        rel_str = parts[1].replace('%', '')
                        rel_avg = float(rel_str)
                        if '(' in parts[2] and ')' in parts[3]:
                            rel_sd_str = parts[2].replace('(', '').replace('%', '') + parts[3].replace(')', '').replace('%', '')
                            rel_sd = float(rel_sd_str)
                    except:
                        pass
                if len(parts) >= 6:
                    try:
                        ci_str = ' '.join(parts[4:6])
                        ci_str = ci_str.replace('[', '').replace(']', '').replace(',', '').replace('%', '')
                        ci_parts = ci_str.split()
                        if len(ci_parts) >= 2:
                            rel_ci_lower = float(ci_parts[0])
                            rel_ci_upper = float(ci_parts[1])
                    except:
                        pass
                        
            elif 'Posterior tail-area probability p:' in line:
                import re
                p_match = re.search(r'p:\s+([0-9.]+)', line)
                if p_match:
                    try:
                        p_value = float(p_match.group(1))
                    except:
                        pass
        
        # 累積値の計算（実際のデータから）
        try:
            if hasattr(ci, 'inferences') and ci.inferences is not None:
                df = ci.inferences.copy().reset_index()
                
                # 日付列を統一
                if 'index' in df.columns:
                    df = df.rename(columns={'index': 'date'})
                
                # 列名マッピング
                column_mapping = {
                    'predicted': 'preds',
                    'point_effects': 'point_effects'
                }
                
                for old_name, new_name in column_mapping.items():
                    if old_name in df.columns:
                        df = df.rename(columns={old_name: new_name})
                
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
                
                # 累積値計算
                if 'preds' in post_data.columns and 'point_effects' in post_data.columns:
                    # 実測値の累積
                    y_values = post_data['preds'] + post_data['point_effects']
                    actual_cum = y_values.sum()
                    
                    # 予測値の累積
                    pred_cum = post_data['preds'].sum()
                    
                    # 絶対効果の累積
                    abs_cum = post_data['point_effects'].sum()
                    
                    # 相対効果の累積
                    rel_cum = (abs_cum / pred_cum * 100) if pred_cum != 0 else 0
                else:
                    actual_cum = actual_avg * len(post_data) if actual_avg and len(post_data) > 0 else None
                    pred_cum = pred_avg * len(post_data) if pred_avg and len(post_data) > 0 else None
                    abs_cum = abs_avg * len(post_data) if abs_avg and len(post_data) > 0 else None
                    rel_cum = rel_avg
        except:
            # フォールバック：平均値×期間で累積値を推定
            actual_cum = actual_avg
            pred_cum = pred_avg
            abs_cum = abs_avg
            rel_cum = rel_avg
        
        # 結果データを日本語表記で構築
        if actual_avg is not None:
            if actual_cum is not None:
                results_data.append(['実測値', f"{actual_avg:.1f}", f"{actual_cum:,.1f}"])
            else:
                results_data.append(['実測値', f"{actual_avg:.1f}", f"{actual_avg:.1f}"])
        
        if pred_avg is not None:
            if pred_sd is not None:
                if pred_cum is not None:
                    results_data.append(['予測値（標準偏差）', f"{pred_avg:.1f} ({pred_sd:.1f})", f"{pred_cum:,.1f} ({pred_sd:.1f})"])
                else:
                    results_data.append(['予測値（標準偏差）', f"{pred_avg:.1f} ({pred_sd:.1f})", f"{pred_avg:.1f} ({pred_sd:.1f})"])
            else:
                if pred_cum is not None:
                    results_data.append(['予測値（標準偏差）', f"{pred_avg:.1f}", f"{pred_cum:,.1f}"])
                else:
                    results_data.append(['予測値（標準偏差）', f"{pred_avg:.1f}", f"{pred_avg:.1f}"])
        
        if pred_ci_lower is not None and pred_ci_upper is not None:
            ci_str = f"[{pred_ci_lower:.1f}, {pred_ci_upper:.1f}]"
            if pred_cum is not None:
                # 累積値の信頼区間も適切に計算（簡易的に平均値の信頼区間を使用）
                results_data.append([f'予測値 {alpha_percent}% 信頼区間', ci_str, ci_str])
            else:
                results_data.append([f'予測値 {alpha_percent}% 信頼区間', ci_str, ci_str])
        
        if abs_avg is not None:
            if abs_sd is not None:
                if abs_cum is not None:
                    results_data.append(['絶対効果（標準偏差）', f"{abs_avg:.1f} ({abs_sd:.1f})", f"{abs_cum:,.1f} ({abs_sd:.1f})"])
                else:
                    results_data.append(['絶対効果（標準偏差）', f"{abs_avg:.1f} ({abs_sd:.1f})", f"{abs_avg:.1f} ({abs_sd:.1f})"])
            else:
                if abs_cum is not None:
                    results_data.append(['絶対効果（標準偏差）', f"{abs_avg:.1f}", f"{abs_cum:,.1f}"])
                else:
                    results_data.append(['絶対効果（標準偏差）', f"{abs_avg:.1f}", f"{abs_avg:.1f}"])
        
        if abs_ci_lower is not None and abs_ci_upper is not None:
            ci_str = f"[{abs_ci_lower:.1f}, {abs_ci_upper:.1f}]"
            results_data.append([f'絶対効果 {alpha_percent}% 信頼区間', ci_str, ci_str])
        
        if rel_avg is not None:
            if rel_sd is not None:
                if rel_cum is not None:
                    results_data.append(['相対効果（標準偏差）', f"{rel_avg:.1f}% ({rel_sd:.1f}%)", f"{rel_cum:.1f}% ({rel_sd:.1f}%)"])
                else:
                    results_data.append(['相対効果（標準偏差）', f"{rel_avg:.1f}% ({rel_sd:.1f}%)", f"{rel_avg:.1f}% ({rel_sd:.1f}%)"])
            else:
                if rel_cum is not None:
                    results_data.append(['相対効果（標準偏差）', f"{rel_avg:.1f}%", f"{rel_cum:.1f}%"])
                else:
                    results_data.append(['相対効果（標準偏差）', f"{rel_avg:.1f}%", f"{rel_avg:.1f}%"])
        
        if rel_ci_lower is not None and rel_ci_upper is not None:
            ci_str = f"[{rel_ci_lower:.1f}%, {rel_ci_upper:.1f}%]"
            results_data.append([f'相対効果 {alpha_percent}% 信頼区間', ci_str, ci_str])
        
        if p_value is not None:
            results_data.append(['p値', f"{p_value:.4f}", f"{p_value:.4f}"])
        
        # DataFrameを作成（日本語表記で統一）
        df_result = pd.DataFrame(results_data, columns=['指標', '分析期間の平均値', '分析期間の累積値'])
        
        return df_result
        
    except Exception as e:
        print(f"Error in build_single_group_summary_dataframe: {e}")
        # 最終的なエラーの場合でも確実な日本語表記を返す
        return build_single_group_guaranteed_japanese_table(ci, alpha_percent)

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
        fontSize=12,  # 14→12に縮小
        alignment=1,  # 中央揃え
        spaceAfter=8   # 12→8に縮小
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=10,  # 11→10に縮小
        spaceAfter=4   # 6→4に縮小
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=8,   # 9→8に縮小
        spaceAfter=3  # 5→3に縮小
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=7,   # 8→7に縮小
        spaceAfter=2  # 3→2に縮小
    )
    
    # PDF内容を構築
    story = []
    
    # タイトル
    story.append(Paragraph('Causal Impact分析レポート（単群推定）', title_style))
    story.append(Spacer(1, 4))  # 8→4に縮小
    
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
    story.append(Spacer(1, 6))  # 8→6に縮小
    
    # 分析結果サマリー
    story.append(Paragraph('分析結果サマリー', heading_style))
    
    # 分析結果概要テーブル
    story.append(Paragraph('分析結果概要：', heading_style))
    
    # サマリーテーブルをPDF用に変換
    table_data = []
    for index, row in summary_df.iterrows():
        table_data.append([str(row[col]) for col in summary_df.columns])
    
    # ヘッダーを追加
    headers = [str(col) for col in summary_df.columns]
    table_data.insert(0, headers)
    
    # テーブル作成（よりコンパクトに）
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 7),  # 8→7に縮小
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),  # 8→4に縮小
        ('TOPPADDING', (0, 0), (-1, -1), 4),  # デフォルト→4に設定
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    story.append(Spacer(1, 6))  # 8→6に縮小
    
    # 分析レポートまとめメッセージ（単群推定用）
    summary_message = get_single_group_analysis_summary_message(ci, confidence_level)
    if summary_message:
        story.append(Paragraph(summary_message, normal_style))
    else:
        # フォールバック用メッセージ
        story.append(Paragraph("分析が完了しました。詳細はレポートを参照ください。", normal_style))
    story.append(Spacer(1, 8))  # 12→8に縮小
    
    # グラフを画像として挿入
    story.append(Paragraph('分析結果グラフ', heading_style))
    
    # グラフタイトル・サブタイトルは削除（ユーザー要求通り）
    story.append(Spacer(1, 2))  # 4→2に縮小
    
    # MatplotlibのグラフをPDFに変換
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
    img_buffer.seek(0)
    
    # 画像をPDFに挿入（さらにサイズをコンパクトに）
    img = Image(img_buffer, width=360, height=240)  # 400×260→360×240に縮小
    story.append(img)
    story.append(Spacer(1, 4))  # 8→4に縮小
    
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
    信頼区間の数値不一致を避けるため、ユーザー向けには8列のクリーンなフォーマットで提供
    
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
    
    # 8列の簡潔なフォーマット（信頼区間列を除去）
    jp_names = [
        '日付', '実測値', '予測値', '効果',
        '累積実測値', '累積予測値', '累積効果', '介入期間フラグ'
    ]
    
    en_names = [
        'date', 'y', 'preds', 'point_effects',
        'post_cum_y', 'post_cum_pred', 'post_cum_effects', 'post_period'
    ]
    
    # データフレームの列名マッピング（pycausalimpactの出力に対応）
    column_mapping = {
        'predicted': 'preds',
        'point_effects': 'point_effects'
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
    
    # 介入期間フラグを追加
    if period_start and period_end:
        post_start = pd.to_datetime(period_start)
        post_end = pd.to_datetime(period_end)
        mask_post = (pd.to_datetime(df['date']) >= post_start) & (pd.to_datetime(df['date']) <= post_end)
        df['post_period'] = mask_post.astype(int)  # 1が介入期間、0が介入前期間
        
        # 介入期間のデータのみで累積値を計算
        post_data = df[mask_post].copy()
        if len(post_data) > 0:
            # 累積値を正しく計算（各行で累積されていく）
            post_data = post_data.reset_index(drop=True)
            post_data['post_cum_y'] = post_data['y'].cumsum()
            post_data['post_cum_pred'] = post_data['preds'].cumsum() if 'preds' in post_data.columns else np.nan
            post_data['post_cum_effects'] = post_data['point_effects'].cumsum() if 'point_effects' in post_data.columns else np.nan
            
            # 元のデータフレームの該当箇所に累積値をセット
            post_indices = df[mask_post].index
            for i, idx in enumerate(post_indices):
                if i < len(post_data):
                    df.loc[idx, 'post_cum_y'] = post_data.iloc[i]['post_cum_y']
                    df.loc[idx, 'post_cum_pred'] = post_data.iloc[i]['post_cum_pred']
                    df.loc[idx, 'post_cum_effects'] = post_data.iloc[i]['post_cum_effects']
    else:
        df['post_period'] = 0
    
    # 不足している列を追加（NaNで初期化）
    for en_name in en_names:
        if en_name not in df.columns:
            df[en_name] = np.nan
    
    # 出力用データフレームを作成（8列のみ）
    output_df = df[en_names].copy()
    
    # 日付をYYYY/MM/DD形式に変換
    try:
        output_df['date'] = pd.to_datetime(output_df['date']).dt.strftime('%Y/%m/%d')
    except Exception as e:
        # 日付変換に失敗した場合は文字列として出力
        output_df['date'] = output_df['date'].astype(str)
    
    # CSVバッファを作成
    csv_buffer = io.StringIO()
    
    # 1行目：日本語項目名
    csv_buffer.write(','.join(jp_names) + '\n')
    
    # 2行目：英字変数名
    csv_buffer.write(','.join(en_names) + '\n')
    
    # 3行目以降：実データ
    output_df.to_csv(csv_buffer, index=False, header=False)
    
    # 注釈を追加（信頼区間の不一致について説明）
    csv_buffer.write('\n')
    csv_buffer.write('【CSV出力データについて】\n')
    csv_buffer.write('※ 累積値は介入期間のみ出力されます（介入前期間はゼロまたは空欄になります）。\n')
    csv_buffer.write('　 介入期間フラグ：1＝介入期間、0＝介入前期間\n')
    csv_buffer.write('※ 統計的判断に必要な信頼区間の情報は、「詳細レポート」および「サマリー表」でご確認ください。\n')
    
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
            'point_effects': 'point_effects'
        }
        
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # 実測値（y）の算出
        if 'y' not in df.columns:
            if 'preds' in df.columns and 'point_effects' in df.columns:
                df['y'] = df['preds'] + df['point_effects']
            else:
                df['y'] = np.nan
        
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
                return f"相対効果は {relative_effect:+.1f}% で、統計的に有意です（p = {p_value:.3f}）。詳しくは「詳細レポート」を参照ください。"
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