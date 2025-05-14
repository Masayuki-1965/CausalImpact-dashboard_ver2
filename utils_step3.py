import matplotlib.pyplot as plt
import pandas as pd
import re
from causalimpact import CausalImpact

def run_causal_impact_analysis(data, pre_period, post_period):
    ci = CausalImpact(data, pre_period, post_period)
    summary = ci.summary()
    report = ci.summary(output='report')
    fig = ci.plot(figsize=(10, 6))
    if fig is None:
        fig = plt.gcf()
    return ci, summary, report, fig

def build_summary_dataframe(summary, alpha_percent):
    lines = [l for l in summary.split('\n') if l.strip()]
    data_lines = []
    for line in lines[1:]:
        parts = re.split(r'\s{2,}', line.strip())
        if len(parts) == 3:
            data_lines.append([parts[1], parts[2]])
    df_summary = pd.DataFrame(data_lines, columns=['分析期間の平均値','分析期間の累積値'])
    japanese_index = [
        '実測値',
        '予測値 (標準偏差)',
        f'予測値 {alpha_percent}% 信頼区間',
        '絶対効果 (標準偏差)',
        f'絶対効果 {alpha_percent}% 信頼区間',
        '相対効果 (標準偏差)',
        f'相対効果 {alpha_percent}% 信頼区間'
    ]
    df_summary.index = japanese_index[:len(df_summary)]
    return df_summary 