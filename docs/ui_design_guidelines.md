# UI/UXデザイン統一ガイドライン

## 概要

このドキュメントは、Causal Impact分析アプリケーションのUI/UXデザイン統一方針を定めたものです。
一貫性のあるユーザーエクスペリエンスを提供するため、すべての開発者・デザイナーが遵守すべき基準を明記しています。

## デザイン原則

### 1. 階層構造の明確化
- **大項目（セクションタイトル）**: 左側に青線があるタイトル
- **中項目**: 黒字、太字、適度な余白
- **説明文**: 通常の文字サイズ、適切な行間
- **注釈文**: 小さめの文字、グレー系の色

### 2. カラーパレット
- **プライマリカラー**: #1976d2（青）
- **セカンダリカラー**: #ef5350（赤）
- **テキストカラー**: #333333（濃いグレー）
- **注釈テキスト**: #666666（中程度のグレー）
- **背景色**: #ffffff（白）

### 3. タイポグラフィ

#### 大項目（セクションタイトル）
```html
<div class="section-title">タイトル</div>
```

#### 中項目
```html
<div style="font-weight:bold;margin-bottom:1em;font-size:1.05em;">中項目タイトル</div>
```

#### 分析条件表示スタイル（中項目の統一ルール）
分析条件や統計情報を表示する際の統一スタイル：

**横並び形式（推奨）:**
```html
<div style="margin-bottom:0.8em;">
<span style="font-weight:bold;font-size:1.05em;">項目名：</span>
<span style="color:#424242;">項目の値</span>
</div>
```

**縦並び形式（必要な場合のみ）:**
```html
<div style="font-weight:bold;margin-bottom:0.5em;font-size:1.05em;">項目名</div>
<div style="margin-bottom:1em;color:#424242;">項目の値</div>
```

**適用例:**
- 分析対象：雨戸_台風の影響あり（vs 一般サッシ）
- 分析期間：2017-04-01 ～ 2020-10-01
- 分析手法：二群比較（Two-Group Causal Impact）
- データ粒度：月次
- 信頼水準：95%

**特徴:**
- 通常は横並び形式を使用（コンパクトで視認性が高い）
- ラベル部分は太字（font-weight:bold）、フォントサイズ1.05em
- 値部分は通常の文字色で若干薄めのグレー（#424242）
- 各項目間に適度な余白（margin-bottom:0.8em）を確保
- コロン（：）の右側に半角スペースを入れてから値を配置

#### 説明文
- 通常のStreamlitマークダウン
- 行間: 1.6-1.7

#### 注釈文
```html
<span style="color:#666;font-size:0.95em;">注釈テキスト</span>
```

### 4. レイアウト原則

#### 余白・間隔
- セクション間: 適度な余白を確保
- 要素間: 一貫した間隔を維持
- 左右の余白: コンテナ幅に応じて調整

#### グリッドシステム
- Streamlitの`st.columns()`を活用
- 2カラム、3カラム、4カラムレイアウトを適切に使い分け

### 5. インタラクティブ要素

#### ボタン
- プライマリボタン: `type="primary"`
- セカンダリボタン: デフォルトスタイル
- 幅: `use_container_width=True`で統一

#### 入力フィールド
- ラベルは明確で簡潔に
- ヘルプテキストを適切に配置
- バリデーションメッセージは一貫したスタイル

### 6. メッセージ表示の統一ルール

#### 手順・注意喚起系（青系）
- **使用場面**: 操作手順の説明、推奨事項の案内、システムからの情報提供
- **スタイル**: `st.info()` または背景薄青＋濃青文字
- **例**:
  - 「単群推定では、介入前のデータから季節性やトレンドを学習し...」
  - 「推奨介入ポイント: 2022-10-24 （データ全体の60%地点）」
  - 分析タイプの説明文

#### 実行・処理結果系（緑系）
- **使用場面**: 処理完了の通知、成功メッセージ、設定完了の確認
- **スタイル**: `st.success()` または背景薄緑＋濃緑文字
- **例**:
  - 「データを読み込みました。下記にプレビューと統計情報を表示します。」
  - 「✅ データ量：653ポイント（分析に十分なデータ量が確保されています）」
  - 「✅ 介入前期間比率: 69.5% （推奨: 60%以上）」
  - 「データセットの作成が完了しました。次のステップで...」

#### 警告・注意系（オレンジ系）
- **使用場面**: 推奨値未満の警告、設定上の注意点
- **スタイル**: `st.warning()` または背景薄オレンジ＋濃オレンジ文字
- **例**:
  - 「⚠️ 介入前期間比率: 45.0% （推奨: 60%以上）」
  - データ量不足の警告

#### エラー系（赤系）
- **使用場面**: エラー発生、必須項目未入力、設定値の問題
- **スタイル**: `st.error()` または背景薄赤＋濃赤文字
- **例**:
  - データ読み込み失敗
  - 期間設定の妥当性エラー

### 7. データ表示

#### テーブル
- ヘッダーは太字
- 行間は適度に確保
- 数値は右寄せ、テキストは左寄せ

#### グラフ・チャート
- カラーパレットを統一
- 凡例は上部中央に配置
- レンジスライダーを標準装備

## 禁止事項

### 1. アイコンの使用
- 絵文字やアイコンの使用は極力控える
- 必要な場合は事前に承認を得る

### 2. 色の無秩序な使用
- 定義されたカラーパレット以外の色は使用しない
- 装飾目的での色の多用は避ける

### 3. フォントサイズの不統一
- 階層に応じたフォントサイズを遵守
- 任意のサイズ指定は避ける

## チェックリスト

新機能開発・既存機能修正時は以下を確認：

- [ ] セクションタイトルは適切なスタイルか
- [ ] 中項目のフォントサイズ・色は統一されているか
- [ ] 分析条件表示は統一ガイドライン（コロン形式）に準拠しているか
- [ ] 分析条件は横並び形式で表示されているか（推奨）
- [ ] カラーパレットに準拠しているか
- [ ] 余白・間隔は一貫しているか
- [ ] アイコンを不必要に使用していないか
- [ ] ボタンスタイルは統一されているか
- [ ] テーブル・グラフのスタイルは一貫しているか
- [ ] メッセージ表示の色使いルールに準拠しているか
  - [ ] 手順・注意喚起系は青系（st.info）
  - [ ] 実行・処理結果系は緑系（st.success）
  - [ ] 警告・注意系はオレンジ系（st.warning）
  - [ ] エラー系は赤系（st.error）
- [ ] 分析結果表示は表形式で見やすく整理されているか
- [ ] 指標説明は展開可能な形式で提供されているか
- [ ] 指標説明の信頼区間は「XX%」形式で汎用性を確保しているか
- [ ] 高度なパラメータの見出しは重複していないか
- [ ] パラメータ表のヘッダーは「高度なパラメータ名」になっているか
- [ ] STEP 3の補足説明文は適切な内容になっているか
- [ ] 分析結果サマリーの構成（分析条件→分析結果概要）は適切か
- [ ] 分析期間は介入期間を表示し、データポイント数を併記しているか
- [ ] 信頼区間の表示は設定値に応じて動的に変更されているか

## 分析結果サマリーの表示ルール

### 構成要素
分析結果サマリーは以下の構成で表示する：

1. **大項目「分析結果サマリー」**
2. **各項目を中項目として表示（一部横並び）：**
   - 分析対象（単独行）
   - 分析期間とデータ粒度（横並び、2:1の比率）
   - 分析手法と信頼水準（横並び、2:1の比率）
3. **中項目「分析結果概要」**
4. **サマリー表（分析結果の数値出力）**
5. **分析レポートのまとめ（テーブル直下に配置）**

### 表示仕様
- **分析期間**: 介入期間のみを表示し、データポイント数をカッコ書きで併記
- **データ粒度**: 「月次集計」「旬次集計」の形式で「集計」を付加
- **信頼区間**: 設定された信頼水準に応じて動的に表示（例：「予測値 90% 信頼区間」）
- **データ粒度・信頼水準**: 中央寄り配置（text-align:center; padding-left:1em;）
- **分析対象**: 50文字を超える場合は47文字で切り詰めて「...」を付加

### 分析レポートのまとめ表示
- **配置**: 分析結果概要テーブルの直下に必ず配置
- **スタイル**: `st.success()`を使用した緑色のメッセージ
- **内容**: 相対効果（%）と統計的有意性を1行で表示
- **例**: 「相対効果は +15.2% で、統計的に有意です（p = 0.001）。詳細はレポートを参照ください。」
- **実装**: `get_analysis_summary_message()`関数を使用して自動生成

## 分析結果グラフの表示ルール

### グラフタイトルの表示
- **処置群名**: 太字で表示
- **分析手法説明**: 「：」より右側は通常フォント（font-weight:normal）
- **例**: 
  - `<span style="font-weight:bold;">二群比較分析：</span><span style="font-weight:normal;">対照群との関係性による予測との比較</span>`
  - `<span style="font-weight:bold;">処置群のみ分析：</span><span style="font-weight:normal;">介入前トレンドからの予測との比較</span>`

### グラフの見方
- グラフ下部に常時表示（展開不要）
- 背景色: #f8f9fa、角丸: 4px
- 分析タイプに応じて内容を動的に変更

## 注釈の簡素化ルール

### 統合方針
- 「結果の解釈ガイド」は「指標の説明」に統合
- 注釈数を最小限に抑制してUIをシンプル化
- 重複する内容は削除し、必要な情報のみ残す

### 指標の説明の拡張
- 従来の指標説明に加えて「結果の解釈ガイド」セクションを追加
- 分析手法の特徴、有意性の判断、注意事項を含める
- 分析タイプ（二群比較・単群推定）に関わらず汎用的な内容で統一

### 削除対象
- 独立した「結果の解釈ガイド」の展開可能セクション
- 内容が重複する注釈や説明文
- 過度に詳細な説明（簡潔性を重視）

## 更新履歴

- 2024-12-XX: 初版作成
- 2024-12-XX: アイコン使用禁止、フォント統一方針を追加
- 2024-12-XX: メッセージ表示の統一ルール（色使い分け）を追加
- 2024-12-XX: 分析条件表示スタイル（コロン形式）を追加、分析結果の表形式表示・指標説明の展開機能を追加
- 2024-12-XX: 分析条件の横並び表示を推奨に変更、指標説明の汎用性向上（「XX%」表記）、高度なパラメータ表の見出し改善
- 2024-12-XX: STEP 3補足説明文の統一、分析結果サマリーの構成改善（分析条件→分析結果概要）、信頼区間の動的表示対応
- 2024-12-XX: 分析結果表示のUI/UX改善 - 項目値の通常フォント化、レイアウト調整、分析レポートまとめ追加、注釈の簡素化、グラフの見方常時表示化

## 分析結果表示の改善ルール（2024-12-XX追加）

### 分析結果サマリー表示ルール
- **項目名**：太字（`font-weight:bold`）で表示
- **項目値**：通常フォント（`color:#424242`）で表示  
- **ファイル名省略**：50文字を超える場合は47文字で切り捨て「...」を付加
- **レイアウト調整**：データ粒度・信頼水準は中央寄り（`text-align:center`）で配置
- **カラム比率**：分析期間とデータ粒度、分析手法と信頼水準は2:1の比率

### 分析レポートまとめ表示ルール
- **配置**：分析結果概要テーブルの直下に配置
- **スタイル**：`st.success()`を使用（実行・処理結果系の緑系メッセージ）
- **内容**：相対効果（％）とp値による統計的有意性を1行で要約
- **文例**：
  - 有意な場合：「相対効果は +XX% で、統計的に有意です（p = 0.000）。詳細はレポートを参照ください。」
  - 非有意の場合：「相対効果は +XX% ですが、統計的には有意ではありません（p = 0.456）。詳細はレポートを参照ください。」

### グラフ表示改善ルール
- **グラフの見方**：エキスパンダー形式から常時表示に変更
- **スタイル**：薄いグレー背景（`#f8f9fa`）、小さめ文字（`0.95em`）、適度なパディング
- **内容**：必要最小限の情報に絞り、分析タイプ別に適切な説明を提供

### 注釈・補足情報の簡素化ルール
- **結果の解釈ガイド**：詳細なリストから簡潔な3ポイントに削減
- **分析品質の評価**：冗長な評価項目を削除、必要最小限の品質チェックに絞る
- **情報の階層化**：重要度に応じて情報を整理し、視認性を向上

### 表記・スタイル統一
- **コロン形式**：項目名の後は必ず「：」（全角コロン）を使用
- **余白調整**：`margin-bottom:0.8em`で統一的な間隔を確保
- **色使い統一**：項目値は`#424242`、注釈は`#666`で統一

## サイドバーアクティブ表示の統一ルール（2024-12-XX追加）

### 基本仕様
- **目的**: ユーザーが分析フェーズの遷移を直感的に把握できるよう、各STEPの進行状況を視覚的に表示
- **実装場所**: サイドバー（`app_enhanced.py`および`app.py`の左サイドバー領域）

### アクティブ状態の判定基準
**STEP 1（データ取り込み／可視化）**:
- 常時アクティブ状態で表示

**STEP 2（分析期間／パラメータ設定）**:
- データ読み込み完了（`SESSION_KEYS['DATA_LOADED'] = True`）
- かつ、データセット作成完了（`SESSION_KEYS['DATASET_CREATED'] = True`）

**STEP 3（分析実行／結果確認）**:
- 分析設定完了（`SESSION_KEYS['PARAMS_SAVED'] = True`）
- または、分析実行完了（`SESSION_KEYS['ANALYSIS_COMPLETED'] = True`）

### スタイル仕様
**アクティブ状態（`.sidebar-step-active`）**:
- 背景：青色グラデーション（`#2196f3` → `#1565c0`）
- 文字色：白色（`white`）
- フォント：太字（`font-weight: 600`）
- ボックスシャドウ：`0 3px 10px rgba(33, 150, 243, 0.25)`

**非アクティブ状態（`.sidebar-step-inactive`）**:
- 背景：薄青色（`#e8f4fd`）
- 文字色：青色（`#1976d2`）
- フォント：中太字（`font-weight: 500`）
- ボックスシャドウ：`0 1px 4px rgba(33, 150, 243, 0.1)`

### 状態遷移の実装要件
**即座反映の保証**:
- 分析実行ボタン押下時：`show_step3 = True`の設定（app_enhanced.py:1666）
- 分析完了時：`ANALYSIS_COMPLETED = True`の設定（app_enhanced.py:1726, 1754）
- サイドバー表示時：`get_step_status()`関数による最新状態の取得（utils_common.py:58-86）

**セッション状態の確実性**:
- 状態変更は必ずセッション変数に永続化
- ページ再読み込み時も状態を正しく復元
- 分析完了メッセージ表示と同時にSTEP3をアクティブ化

### トラブルシューティング
**問題**: 分析完了後もSTEP3がアクティブ状態にならない
**解決策**:
1. セッション状態の設定タイミングを確認
2. `get_step_status()`関数の判定ロジックを検証
3. Streamlitの再描画タイミングを考慮した実装

**実装時の注意点**:
- 分析実行ボタン押下と分析完了は別々の処理として管理
- どちらかの状態でもSTEP3をアクティブ化
- エラー発生時は適切に状態をリセット

### 検証チェックリスト
- [ ] 分析実行ボタン押下時にSTEP3がアクティブ化される
- [ ] 分析完了メッセージ表示時にSTEP3がアクティブ状態を維持
- [ ] ページ再読み込み後も状態が正しく復元される
- [ ] エラー発生時に適切な状態管理が行われる
- [ ] 二群比較・単群推定の両分析タイプで正常動作する

## 関連ファイル

- `config/help_texts.py`: ヘルプテキスト定数
- `styles/`: CSSスタイルファイル
- `app_enhanced.py`: メインアプリケーション

---

**注意**: このガイドラインは継続的に更新されます。新しい要件や改善点があれば、チーム内で議論の上、このドキュメントを更新してください。 

### 5. 分析結果表示の改善規則

#### 5.1 分析条件の表示スタイル
- **ラベル**: 太字 (`font-weight:bold`)、項目値: 通常フォント (`color:#424242`)
- **項目構成（統合版）**:
  - 分析対象: `{処置群名}（vs {対照群名}）` または `{処置群名}`（単群推定の場合）
  - 分析期間: `{期間}（{データ粒度}）` - データ粒度（月次集計・旬次集計）を統合表示
  - 分析手法: `{手法名}（信頼水準：{%}%）` - 信頼水準を統合表示

#### 5.2 レイアウト仕様
- **縦並び配置**: 統一感とコンパクトさを重視し、横並びを避けて縦方向に整列
- **ファイル名処理**: 50文字を超える場合は47文字で切り捨てて「...」を追加
- **余白**: 各項目間は `margin-bottom:0.8em`（最終項目は `1.5em`） 

## サマリーテーブルのフォーマット仕様

### 数値表示の精度
- **分析期間の平均値**: 小数点第1位まで表示
- **分析期間の累積値**: 小数点第1位まで表示（桁区切りカンマ付き）
- **相対効果（%）**: 小数点第1位まで表示
- **p値**: 小数点第4位まで表示
- **信頼区間**: 小数点第1位まで表示（[下限, 上限]形式）

### 累積値欄の表記方式
- **基本方針**: 視認性重視のため、両欄に同じ値を表示
- **適用対象**: 相対効果（標準偏差）、相対効果信頼区間、p値（事後確率）
- **旧方式**: 「同左」表記で省略表示
- **新方式**: 平均値と累積値の両欄に同一数値を明示表示
- **利点**: データの見落としを防ぎ、直感的な理解を促進 