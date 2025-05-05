# Python環境・ライブラリ構成に関する留意事項

## 概要
本プロジェクトでCausal Impact分析が正常に動作したPython仮想環境の構成および、環境構築・ライブラリに関する注意点をまとめます。

---

## 1. Pythonバージョン
- Python 3.13.x（仮想環境venvを利用）

## 2. 主要ライブラリ
- causalimpact（import名は `from causalimpact import CausalImpact`）
- pandas
- matplotlib
- statsmodels
- numpy
- その他 requirements.txt 参照

## 3. インストール手順のポイント
- 公式PyPI版やGitHub版の `causalimpact`/`pycausalimpact` は環境によってimport名や挙動が異なるため注意。
- 本環境では `pip install pycausalimpact` または `pip install git+https://github.com/WillianFuks/causalimpact.git` でインストールし、`from causalimpact import CausalImpact` で利用。
- 依存パッケージの競合やバージョン不整合が起きた場合は、`pip install --force-reinstall ...` で再インストール推奨。
- Streamlitや他の可視化・分析系パッケージとのバージョン競合に注意。

## 4. トラブルシューティング
- `ModuleNotFoundError: No module named 'pycausalimpact'` などimportエラー時は、`causalimpact`名でのimportも試す。
- requirements.txtで環境を再現する際は、`pip install -r requirements.txt` を推奨。
- Windows環境ではパスや依存関係の競合に注意。

## 5. その他
- サンプルデータや分析スクリプトも合わせて管理し、動作確認済みの状態でコミットすること。
- 仮想環境の利用を徹底し、グローバル環境との混在を避ける。 