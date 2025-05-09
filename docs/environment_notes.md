# Python環境・ライブラリ構成に関する留意事項

## 概要
本プロジェクトでCausal Impact分析が正常に動作したPython仮想環境の構成および、環境構築・ライブラリに関する注意点をまとめます。

---

## 1. Pythonバージョン
- Python 3.13.x（仮想環境venvを利用）

## 2. 主要ライブラリ
- pycausalimpact（WillianFuks版 causalimpact, import名は `from causalimpact import CausalImpact`）
- pandas
- matplotlib
- statsmodels
- numpy
- その他 requirements.txt 参照

## 3. インストール手順のポイント
- causalimpactはWillianFuks版（pycausalimpact）を利用し、以下でインストール：
  - `pip install git+https://github.com/WillianFuks/causalimpact.git`
  - または requirements.txt の `pycausalimpact @ git+https://github.com/WillianFuks/causalimpact.git`
- 依存パッケージの競合やバージョン不整合が起きた場合は、`pip install --force-reinstall ...` で再インストール推奨。
- Streamlitや他の可視化・分析系パッケージとのバージョン競合に注意。

## 4. トラブルシューティング
- `ModuleNotFoundError: No module named 'pycausalimpact'` などimportエラー時は、`causalimpact`名でのimportも試す。
- requirements.txtで環境を再現する際は、`pip install -r requirements.txt` を推奨。
- Windows環境ではパスや依存関係の競合に注意。

## 5. その他
- サンプルデータや分析スクリプトも合わせて管理し、動作確認済みの状態でコミットすること。
- 仮想環境の利用を徹底し、グローバル環境との混在を避ける。 