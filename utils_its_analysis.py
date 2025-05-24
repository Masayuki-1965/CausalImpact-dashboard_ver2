import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.linear_model import LinearRegression
import statsmodels.api as sm
from scipy import stats
import warnings
import matplotlib
matplotlib.use('Agg')

warnings.filterwarnings('ignore')

def run_interrupted_time_series_analysis(data, intervention_date, confidence_level=0.95):
    """
    中断時系列分析（Interrupted Time Series, ITS）を実行する関数
    
    Parameters:
    -----------
    data : pandas.DataFrame
        時系列データ（日付と値の列を含む）
    intervention_date : datetime
        介入日
    confidence_level : float
        信頼水準（デフォルト：0.95）
        
    Returns:
    --------
    dict : 分析結果
        - model: 回帰モデル
        - summary: モデルサマリー
        - interpretation: 結果解釈
        - plot: 分析結果プロット
    """
    
    # データの準備
    df = data.copy()
    df.columns = ['date', 'value']
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    # 介入ポイントを特定
    intervention_idx = df[df['date'] >= intervention_date].index[0] if any(df['date'] >= intervention_date) else len(df)
    
    # 説明変数を作成
    df['time'] = range(len(df))  # 時間トレンド
    df['intervention'] = (df['date'] >= intervention_date).astype(int)  # 介入ダミー
    df['time_since_intervention'] = np.maximum(0, df['time'] - intervention_idx)  # 介入後時間
    
    # ITSモデル: y = β0 + β1*time + β2*intervention + β3*time_since_intervention + ε
    X = df[['time', 'intervention', 'time_since_intervention']]
    X = sm.add_constant(X)  # 定数項を追加
    y = df['value']
    
    # 回帰分析を実行
    model = sm.OLS(y, X).fit()
    
    # 結果の解釈
    interpretation = interpret_its_results(model, confidence_level)
    
    # プロットの作成
    fig = create_its_plot(df, model, intervention_date, intervention_idx)
    
    return {
        'model': model,
        'summary': model.summary(),
        'interpretation': interpretation,
        'plot': fig,
        'data': df
    }

def interpret_its_results(model, confidence_level=0.95):
    """
    ITS分析結果を解釈する関数
    
    Parameters:
    -----------
    model : statsmodels regression model
        回帰モデル
    confidence_level : float
        信頼水準
        
    Returns:
    --------
    str : 解釈テキスト
    """
    alpha = 1 - confidence_level
    
    # 回帰係数を取得
    const = model.params['const']
    time_coeff = model.params['time']
    intervention_coeff = model.params['intervention']
    time_since_coeff = model.params['time_since_intervention']
    
    # p値を取得
    const_p = model.pvalues['const']
    time_p = model.pvalues['time']
    intervention_p = model.pvalues['intervention']
    time_since_p = model.pvalues['time_since_intervention']
    
    # 信頼区間を取得
    conf_int = model.conf_int(alpha=alpha)
    
    interpretation = f"""
    ## 中断時系列分析（ITS）結果

    ### モデル適合度
    - R² = {model.rsquared:.4f}
    - 調整済みR² = {model.rsquared_adj:.4f}
    - F統計量 = {model.fvalue:.4f} (p = {model.f_pvalue:.4f})

    ### 分析結果

    **1. 介入前のベースライントレンド**
    - 係数: {time_coeff:.4f} (p = {time_p:.4f})
    - 解釈: {'統計的に有意な' if time_p < alpha else '統計的に有意でない'}傾向変化
    - {confidence_level*100:.0f}% 信頼区間: [{conf_int.loc['time', 0]:.4f}, {conf_int.loc['time', 1]:.4f}]

    **2. 介入による即座の効果（レベル変化）**
    - 係数: {intervention_coeff:.4f} (p = {intervention_p:.4f})
    - 解釈: 介入により{'増加' if intervention_coeff > 0 else '減少'}の{'有意な' if intervention_p < alpha else '有意でない'}即座の効果
    - {confidence_level*100:.0f}% 信頼区間: [{conf_int.loc['intervention', 0]:.4f}, {conf_int.loc['intervention', 1]:.4f}]

    **3. 介入による長期的効果（トレンド変化）**
    - 係数: {time_since_coeff:.4f} (p = {time_since_p:.4f})
    - 解釈: 介入後のトレンドが{'増加' if time_since_coeff > 0 else '減少'}方向に{'有意に' if time_since_p < alpha else '有意でなく'}変化
    - {confidence_level*100:.0f}% 信頼区間: [{conf_int.loc['time_since_intervention', 0]:.4f}, {conf_int.loc['time_since_intervention', 1]:.4f}]

    ### 統計的有意性の判定基準
    - 有意水準: α = {alpha:.3f}
    - 統計的有意: p < {alpha:.3f}

    ### 注意事項
    - この分析は自己相関や季節性を考慮していない基本的なITSモデルです
    - より高度な分析には、ARIMA成分や季節性調整が推奨されます
    - 外部要因や他の共変量の影響を考慮することも重要です
    """
    
    return interpretation

def create_its_plot(df, model, intervention_date, intervention_idx):
    """
    ITS分析結果のプロットを作成する関数
    
    Parameters:
    -----------
    df : pandas.DataFrame
        分析データ
    model : statsmodels regression model
        回帰モデル
    intervention_date : datetime
        介入日
    intervention_idx : int
        介入のインデックス位置
        
    Returns:
    --------
    matplotlib.figure.Figure : プロット
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # 予測値を計算
    X = df[['time', 'intervention', 'time_since_intervention']]
    X = sm.add_constant(X)
    predicted = model.predict(X)
    
    # 上部プロット: 実測値と予測値
    ax1.plot(df['date'], df['value'], 'o-', label='実測値', alpha=0.7, markersize=4)
    ax1.plot(df['date'], predicted, '--', label='予測値（ITSモデル）', color='red', linewidth=2)
    ax1.axvline(x=intervention_date, color='orange', linestyle=':', linewidth=2, label='介入ポイント')
    
    # 介入前後の背景色を変更
    ax1.axvspan(df['date'].min(), intervention_date, alpha=0.1, color='blue', label='介入前期間')
    ax1.axvspan(intervention_date, df['date'].max(), alpha=0.1, color='red', label='介入後期間')
    
    ax1.set_title('中断時系列分析（ITS）：実測値 vs 予測値', fontsize=14, fontweight='bold')
    ax1.set_xlabel('日付')
    ax1.set_ylabel('値')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 下部プロット: 残差分析
    residuals = df['value'] - predicted
    ax2.plot(df['date'], residuals, 'o-', color='green', alpha=0.7, markersize=4)
    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    ax2.axvline(x=intervention_date, color='orange', linestyle=':', linewidth=2)
    ax2.set_title('残差分析', fontsize=14, fontweight='bold')
    ax2.set_xlabel('日付')
    ax2.set_ylabel('残差')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

def validate_its_data(data, min_pre_period=10, min_post_period=5):
    """
    ITSデータの妥当性をチェックする関数
    
    Parameters:
    -----------
    data : pandas.DataFrame
        時系列データ
    min_pre_period : int
        最低限必要な介入前期間の観測数
    min_post_period : int
        最低限必要な介入後期間の観測数
        
    Returns:
    --------
    bool : 妥当性チェック結果
    str : エラーメッセージ（問題がある場合）
    """
    if data.empty:
        return False, "データが空です"
    
    if len(data) < min_pre_period + min_post_period:
        return False, f"データが不十分です。最低{min_pre_period + min_post_period}点のデータが必要です"
    
    # 欠損値チェック
    if data.isnull().any().any():
        return False, "データに欠損値が含まれています"
    
    return True, ""

def suggest_its_intervention_point(data, min_pre_ratio=0.5):
    """
    ITSのための最適な介入ポイントを提案する関数
    
    Parameters:
    -----------
    data : pandas.DataFrame
        時系列データ
    min_pre_ratio : float
        介入前期間の最低比率
        
    Returns:
    --------
    datetime : 推奨介入日
    """
    total_points = len(data)
    min_pre_points = int(total_points * min_pre_ratio)
    
    # 推奨介入ポイントは全体の60%地点
    suggested_index = max(min_pre_points, int(total_points * 0.6))
    suggested_date = data.iloc[suggested_index, 0]
    
    return suggested_date

def create_its_summary_dataframe(model, confidence_level=0.95):
    """
    ITS分析結果をDataFrameにまとめる関数
    
    Parameters:
    -----------
    model : statsmodels regression model
        回帰モデル
    confidence_level : float
        信頼水準
        
    Returns:
    --------
    pandas.DataFrame : サマリーDataFrame
    """
    alpha = 1 - confidence_level
    conf_int = model.conf_int(alpha=alpha)
    
    summary_data = []
    param_names = {
        'const': 'ベースライン水準',
        'time': '介入前トレンド',
        'intervention': '介入による即座の効果',
        'time_since_intervention': '介入による長期的効果'
    }
    
    for param in model.params.index:
        if param in param_names:
            summary_data.append({
                '効果': param_names[param],
                '係数': f"{model.params[param]:.4f}",
                f'{confidence_level*100:.0f}% 信頼区間': f"[{conf_int.loc[param, 0]:.4f}, {conf_int.loc[param, 1]:.4f}]",
                'p値': f"{model.pvalues[param]:.4f}",
                '統計的有意性': '有意' if model.pvalues[param] < alpha else '非有意'
            })
    
    # モデル適合度情報を追加
    summary_data.append({
        '効果': 'モデル適合度',
        '係数': f"R² = {model.rsquared:.4f}",
        f'{confidence_level*100:.0f}% 信頼区間': f"調整済みR² = {model.rsquared_adj:.4f}",
        'p値': f"{model.f_pvalue:.4f}",
        '統計的有意性': 'モデル全体の有意性'
    })
    
    return pd.DataFrame(summary_data) 