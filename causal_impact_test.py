import pandas as pd
from causalimpact import CausalImpact
import matplotlib.pyplot as plt

# データの読み込み
sample = pd.read_csv('data/sample-data_87(9-10).csv')

# 日付をdatetime型に変換
sample['ymd'] = pd.to_datetime(sample['ymd'])

# CausalImpact用データセット作成（indexを日付に）
data = sample.set_index('ymd')
data = data[['treatment_group', 'control_group']]

# データ内容と期間の確認
print('データ先頭:')
print(data.head())
print('データ末尾:')
print(data.tail())
print('日付範囲:', data.index.min(), '～', data.index.max())

# 介入前・介入後期間の指定
pre_period = [str(data.index.min().date()), '2020-08-01']
post_period = ['2020-09-01', '2020-10-01']
print('pre_period:', pre_period)
print('post_period:', post_period)

# 欠損値の有無確認
print('欠損値有無:', data.isnull().sum())

# CausalImpact分析
ci = CausalImpact(data, pre_period, post_period)
print(ci.summary())
print(ci.summary(output='report'))
ci.plot()
plt.show() 