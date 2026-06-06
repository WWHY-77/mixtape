# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **このリポジトリでの方針**: ユーザーは **Python をメインで学習** しています。回答・コード例・解説は原則 **日本語** で、**Python（`python/` ディレクトリ）を中心** に扱ってください。R / Stata は「他言語での対応例」として必要なときだけ参照します。

## このリポジトリの位置づけ

Scott Cunningham の教科書 *Causal Inference: The Mixtape*（因果推論の教科書）の **データ＋再現コード** リポジトリです。ソフトウェアのプロジェクトではありません。ビルドシステム・パッケージ定義ファイル・テスト・Linter はありません。教科書の各例・各図に対応する **独立した分析スクリプト** を、3言語（Python / R / Stata）で並行して提供し、それらが使う Stata データセットを同梱したものです。

学習者がスクリプトを1本ずつ実行し、因果推論の手法（OLS、IV、DID、RDD、マッチング、合成コントロールなど）を再現しながら学ぶことを想定しています。

## ディレクトリ構成

- **`python/`** — Python の再現スクリプト（**ここが学習の中心**）。
- **`R/`** — R の再現スクリプト（参考用）。
- **`Do/`** — Stata の `.do` 再現スクリプト（参考用）。
- **ルートの `*.dta`** — Stata 形式のデータセット（例: `card.dta`, `castle.dta`, `abortion.dta`, `lmb-data.dta`）。これが正本で、後述のとおり HTTP 経由でも配信されています。`abortion 2.dta` のように末尾に ` 2` が付くファイルは誤って複製されたコピーで、別データではありません。
- **`Texas/`** — 合成コントロール法の独立した例。専用の `Do/` `R/` `Data/` を持ちます。
- **`class material/`** — 講義スライド（LaTeX/Beamer、`workshop.tex`）。

スクリプトは「トピック＋バリアント」で命名され、同じ basename が3言語で対応します（例: `python/card.py`・`R/card.R`・`Do/card.do` は同じ例の再現）。Python 版を学ぶときに対応する手法を他言語で確認したい場合は、同名ファイルを見てください。

## データの読み込み方法（重要）

スクリプトはローカルの `.dta` を相対パスで読みません。**この repo の `master` ブランチの GitHub raw URL からダウンロード** します。そのため、ルートの `.dta` を編集しても、`master` に push するまでスクリプトには反映されません。

Python での定型（各スクリプト冒頭に書かれています）:

```python
import ssl
ssl._create_default_https_context = ssl._create_unverified_context  # ダウンロード時のSSL検証を無効化

def read_data(file):
    return pd.read_stata("https://github.com/scunning1975/mixtape/raw/master/" + file)
```

つまり実行には **ネットワーク接続が必須** です（データは毎回リモート取得）。

## 実行方法

各スクリプトは独立しており、スクリプト間の依存・オーケストレーションはありません。1本ずつ実行します。

```bash
python python/card.py
```

（参考: R は `Rscript R/card.R`、Stata は `do Do/card.do`）

### Python の主要ライブラリ

`numpy`, `pandas`, `statsmodels`（回帰・IV など）, `plotnine`（ggplot 風の作図）。一部スクリプトで `stargazer`・`rpy2` を使用します。実行前にこれらを `pip install` しておく必要があります。

Python スクリプトの典型的な構成: `read_data()` で `.dta` を pandas DataFrame として取得 → `statsmodels`（`smf.ols('y ~ x', data=df).fit()` など）で推定 → `plotnine` で可視化、という流れです。

## 追加・編集時の慣習

- 学習目的の編集・実験は **`python/` を中心** に行ってください。手法の確認のために R / Stata 版を参照するのは構いませんが、主たる成果物は Python です。
- 3言語の並行性を保つ必要がある変更（教科書本体への貢献など）では、`python/`・`R/`・`Do/` の3版が同じ推定結果を出すようにします。
- 新しいデータセットはルートに `.dta` として置き、リモート URL で読み込む都合上、参照前に `master` へ commit / push する必要があります。
- 本家への貢献は `scunning1975/mixtape` への fork + PR 形式です（[CONTRIBUTING.md](CONTRIBUTING.md) 参照）。Issue を解決する PR では本文に `Fixes #<番号>` を記載します。
