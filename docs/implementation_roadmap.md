# 処置群のみ分析機能　技術仕様・設計ドキュメント

## 概要

このドキュメントは、既存のCausal Impactアプリケーションに「処置群のみ分析」機能を追加するための技術仕様・設計方針・アーキテクチャを定義します。

---

## 🎯 設計方針・アーキテクチャ

### 基本設計原則

#### 1. 既存機能との完全互換性
- 標準分析（処置群+対照群）の既存機能は一切変更しない
- セッション状態の後方互換性を完全維持
- デフォルト動作は標準分析のまま

#### 2. 3ステップ構成の完全維持
- STEP1: データ取り込み／可視化
- STEP2: 分析期間／パラメータ設定  
- STEP3: 分析実行／結果確認
- 各ステップ内での分析タイプ別分岐実装

#### 3. モジュラー設計
- 分析タイプ別の処理を独立したモジュールに分離
- 共通処理の再利用性を最大化
- 将来的な分析手法追加への拡張性確保

### アーキテクチャ概要

```
app_enhanced.py (メインアプリケーション)
├── STEP1: データ取り込み／可視化
│   ├── 分析タイプ選択 (二群比較 / 単群推定)
│   ├── データアップロード (ファイル / テキスト入力)
│   ├── データ処理・検証 (共通 + 分析タイプ別)
│   └── 可視化 (共通 + 分析タイプ別)
├── STEP2: 期間設定／パラメータ設定
│   ├── 期間設定UI (分析タイプ別分岐)
│   ├── パラメータ設定 (分析タイプ別)
│   └── 設定値検証 (分析タイプ別)
└── STEP3: 分析実行／結果確認
    ├── 分析実行 (分析タイプ別分岐)
    ├── 結果表示 (共通フォーマット)
    └── ダウンロード (共通機能)
```

---

## 🔧 技術仕様

### 分析手法の選定

#### メイン手法: Causal Impact拡張
**選定理由:**
- 既存システムとの親和性が最高
- ベイズ構造時系列モデルによる堅牢な分析
- 季節性・トレンドパターンを適切に考慮
- ユーザーが慣れ親しんだ分析結果形式を維持

**技術的特徴:**
- 状態空間モデルによる時系列分解
- ベイズ推定による不確実性の適切な表現
- 介入前期間のパターン学習による反事実シナリオ構築

#### オプション手法: ITS分析（将来実装）
**選定理由:**
- より統計学的に解釈しやすい結果
- 効果の詳細な分解（即座の効果 vs 長期的効果）
- 学術・実務での標準的手法

### 必要な依存関係

```python
# requirements.txtに追加済み
causalimpact>=1.2.0
pandas>=1.5.0
numpy>=1.21.0
plotly>=5.0.0
streamlit>=1.28.0

# 将来のITS分析用（オプション）
statsmodels>=0.14.0
scikit-learn>=1.3.0
```

### ファイル構成・モジュール設計

```
project_root/
├── app_enhanced.py                    # メインアプリケーション
├── utils_step1.py                     # STEP1共通処理
├── utils_step2.py                     # STEP2共通処理  
├── utils_step3.py                     # STEP3標準分析処理
├── utils_step3_single_group.py        # STEP3単群推定処理
├── utils_its_analysis.py              # ITS分析（将来実装）
├── utils_common.py                    # 全体共通処理
├── causal_impact_translator.py        # 結果翻訳
├── config/
│   ├── constants.py                   # 定数定義
│   └── help_texts.py                  # UI文言
├── styles/
│   └── custom.css                     # スタイル定義
└── docs/
    ├── priority_development_checklist.md  # 進捗管理
    ├── implementation_roadmap.md           # 技術仕様（このファイル）
    └── ui_design_guidelines.md             # デザインガイド
```

### セッション状態設計

```python
# 既存セッション状態（維持）
st.session_state.data_loaded = False
st.session_state.df_treat = None
st.session_state.df_ctrl = None
st.session_state.dataset = None
st.session_state.dataset_created = False

# 追加セッション状態
st.session_state.analysis_type = "二群比較（処置群＋対照群を使用）"
st.session_state.treatment_name = "処置群"
st.session_state.control_name = "対照群"
st.session_state.suggested_intervention_date = None
st.session_state.period_defaults = {}
st.session_state.period_info = {}

# STEP2用追加状態（実装予定）
st.session_state.period_settings = {}
st.session_state.analysis_params = {}
st.session_state.step2_completed = False

# STEP3用追加状態（実装予定）
st.session_state.analysis_results = None
st.session_state.analysis_completed = False
```

---

## 📊 データ処理仕様

### データ検証ルール

#### 共通検証
- 必須カラム: `ymd`（日付）、`qty`（数量）
- 日付形式: YYYYMMDD（8桁数字）
- 数量: 数値型（整数・小数対応）
- 欠損値: 自動的に0で補完

#### 単群推定特有の検証
- **最低データ量**: 36ポイント以上
- **介入前期間比率**: 全体の60%以上を推奨
- **季節性学習**: 月次データなら3年分、旬次データなら1年分を推奨

### データ集計仕様

#### 集計方法
- **月次集計**: 月の1日に集約
- **旬次集計**: 1日（上旬）、11日（中旬）、21日（下旬）に集約
- **欠損期間**: 0で自動補完

#### 期間調整
- **二群比較**: 処置群・対照群の共通期間を自動算出
- **単群推定**: 処置群の全期間を対象

---

## 🎨 UI/UX設計仕様

### 分析タイプ選択UI

```python
analysis_type = st.radio(
    "分析タイプ選択",
    options=["二群比較（処置群＋対照群を使用）", "単群推定（処置群のみを使用）"],
    index=0,  # デフォルトは二群比較
    help="分析手法の説明..."
)
```

### 動的UI分岐設計

```python
# 分析タイプに応じたUI分岐
if analysis_type == "二群比較（処置群＋対照群を使用）":
    # 既存の標準分析UI
    display_standard_analysis_ui()
else:
    # 単群推定用UI
    display_single_group_analysis_ui()
```

### デザイン統一方針

詳細は `docs/ui_design_guidelines.md` を参照

- **階層構造**: 大項目（青線）→ 中項目（黒字太字）→ 説明文 → 注釈文
- **カラーパレット**: プライマリ#1976d2、セカンダリ#ef5350
- **フォントサイズ**: 階層に応じた統一サイズ
- **アイコン使用**: 極力控える

---

## 🔍 分析処理仕様

### Causal Impact拡張処理

#### 単群推定用パラメータ
```python
# 基本パラメータ
causal_impact_params = {
    'niter': 1000,           # MCMC反復回数
    'standardize_data': True, # データ標準化
    'prior_level_sd': 0.01,  # レベル変動の事前分散
    'nseasons': 12,          # 季節性周期（月次の場合）
}

# 単群推定特有の調整
single_group_adjustments = {
    'alpha': 0.05,           # 信頼区間レベル
    'model_args': {
        'niter': 1500,       # より多い反復回数
        'standardize_data': True,
    }
}
```

#### 介入ポイント推奨アルゴリズム
```python
def suggest_intervention_point(data):
    """
    データの中点を基準に、以下を考慮して推奨ポイントを算出:
    1. 全体の60%を介入前期間として確保
    2. 季節性パターンの学習に十分な期間
    3. 統計的検出力の最大化
    """
    total_points = len(data)
    suggested_idx = int(total_points * 0.6)
    return data.iloc[suggested_idx]['ymd']
```

### 結果フォーマット統一

#### サマリー情報
- 効果値（絶対値・相対値）
- 信頼区間（95%）
- 統計的有意性（p値）
- 累積効果

#### 可視化要素
- 実測値 vs 予測値
- 信頼区間の表示
- 介入ポイントの明示
- 効果期間のハイライト

---

## 🧪 テスト戦略

### 単体テスト対象

#### データ処理関数
- `validate_single_group_data()`
- `suggest_intervention_point()`
- `create_single_group_dataset()`

#### 分析関数
- `run_single_group_causal_impact_analysis()`
- `build_single_group_summary_dataframe()`
- `get_single_group_interpretation()`

### 統合テスト対象

#### UI統合テスト
- 分析タイプ切り替え
- セッション状態管理
- STEP1→STEP2→STEP3の遷移

#### 分析統合テスト
- データ読み込み→分析実行→結果表示
- エラーハンドリング
- パフォーマンス測定

### テストデータ

#### 標準テストケース
- 月次データ（36ポイント、3年分）
- 旬次データ（36ポイント、1年分）
- 季節性あり/なしパターン

#### エッジケース
- 最低限データ量（36ポイント）
- 大量データ（1000ポイント以上）
- 異常値・欠損値を含むデータ

---

## 🚀 パフォーマンス仕様

### 処理時間目標

| データ量 | 目標処理時間 | 備考 |
|---------|-------------|------|
| 36ポイント | < 10秒 | 最低限データ |
| 100ポイント | < 30秒 | 標準的データ |
| 500ポイント | < 2分 | 大量データ |

### メモリ使用量

- 基本処理: < 100MB
- 大量データ処理: < 500MB
- メモリリーク防止策の実装

### 最適化方針

- 不要な中間データの削除
- 効率的なデータ構造の使用
- 処理進捗の可視化

---

## 🔒 セキュリティ・品質保証

### データセキュリティ
- アップロードファイルのサイズ制限（5MB）
- 悪意のあるファイル形式の検証
- セッション状態の適切な管理

### エラーハンドリング
- 分析タイプ別のエラー分岐
- ユーザーフレンドリーなエラーメッセージ
- ログ出力による問題追跡

### 品質保証
- コードレビューによる品質確保
- 自動テストによる回帰防止
- ユーザビリティテストによるUX検証

---

**最終更新**: 2024年12月  
**ドキュメント種別**: 技術仕様・設計方針  
**関連ドキュメント**: priority_development_checklist.md（進捗管理）、ui_design_guidelines.md（デザイン） 