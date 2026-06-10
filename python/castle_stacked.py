# Castle Doctrine データで stacked DiD の「データ構造」を体感するスクリプト
#
# 目的: staggered(処置時点がバラバラ) なパネルを、
#   (1) 素朴な TWFE で推定 → Goodman-Bacon の「悪い比較」が混ざる
#   (2) コホートごとの「サブ実験」に切り分け、クリーンな対照だけ残して "積む"
#   (3) 積んだデータで TWFE → 実験内だけのクリーンな比較になる
# の流れを、各段階のデータフレームを print しながら確認する。
#
# 注意: データは GitHub raw からダウンロードするのでネット接続が必要。

import ssl
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ssl._create_default_https_context = ssl._create_unverified_context
pd.set_option("display.width", 120)


def read_data(file):
    return pd.read_stata("https://github.com/scunning1975/mixtape/raw/master/" + file)


# ----------------------------------------------------------------------
# 0. 元データ: 50州 x 11年(2000-2010) の均衡パネル
#    sid=州ID, year=年, l_homicide=対数殺人率(結果Y),
#    effyear=法律の発効年(=処置コホート g), post=処置済みダミー
# ----------------------------------------------------------------------
castle = read_data("castle.dta")
d = castle[["sid", "year", "l_homicide", "effyear", "post"]].copy()

print("=" * 70)
print("[0] 元データ(long形式)")
print("    shape:", d.shape, " = 50州 x 11年")
print("    コホート(effyear)ごとの州数:")
print((d.groupby("effyear").size() // 11).rename("n_states").to_string())
print("    未処置(never-treated)の州数:", d[d.effyear.isna()].sid.nunique())
# 1つの州は元データでは1回ずつしか登場しない(例: sid=1 は11行)
print("    例: sid=1 の行数 =", (d.sid == 1).sum(), "(各年1行ずつ)")

# ----------------------------------------------------------------------
# 1. 素朴な staggered TWFE
#    l_homicide ~ post + 州FE + 年FE
#    → これが Goodman-Bacon 分解で「悪い2x2」を含むと示されたもの
# ----------------------------------------------------------------------
naive = smf.ols("l_homicide ~ post + C(sid) + C(year)", data=d).fit(
    cov_type="cluster", cov_kwds={"groups": d.sid}
)
print("=" * 70)
print("[1] 素朴な TWFE の処置効果(post):", round(naive.params["post"], 4),
      " (SE", round(naive.bse["post"], 4), ")")

# ----------------------------------------------------------------------
# 2. サブ実験を作って "積む"
#    各コホート g について:
#      - 処置群   : effyear == g
#      - クリーン対照: 未処置(effyear=NaN) または 窓の最後(g+POST)までに処置されない州
#                    (= すでに処置済みの州は対照に入れない ← ここが肝)
#      - イベント窓: rel = year - g が [-PRE, +POST] の範囲
#    g=2009 は +2 年(2011)がデータに無いので除外
# ----------------------------------------------------------------------
PRE, POST = 2, 2
cohorts = [2005, 2006, 2007, 2008]

frames = []
for g in cohorts:
    win = d[d.year.between(g - PRE, g + POST)].copy()
    treated = win.effyear == g
    clean_control = win.effyear.isna() | (win.effyear > g + POST)
    sub = win[treated | clean_control].copy()
    sub["stack"] = g                       # どのサブ実験か
    sub["rel"] = sub.year - g              # イベント時間(処置からの相対年)
    sub["treat"] = ((sub.effyear == g) & (sub.year >= g)).astype(int)
    sub["role"] = np.where(sub.effyear == g, "treated", "control")
    frames.append(sub)

stacked = pd.concat(frames, ignore_index=True)

print("=" * 70)
print("[2] 積んだあとの構造")
comp = (
    stacked.groupby(["stack", "role"]).sid.nunique().unstack(fill_value=0)
    .assign(rows=stacked.groupby("stack").size())
)
print(comp.to_string())
print("    積んだ後の総行数:", stacked.shape[0], " (元の窓内行数より増える=重複して登場)")

# 同じ州が複数のサブ実験に登場することを確認(stacking の本質)
nt_sid = int(d[d.effyear.isna()].sid.iloc[0])   # 実際に never-treated な州を1つ選ぶ
print("-" * 70)
print(f"    未処置の州 sid={nt_sid} は、全サブ実験で『対照』として登場する:")
print(stacked[stacked.sid == nt_sid][["sid", "year", "stack", "rel", "role", "treat"]]
      .to_string(index=False))
print(f"    → sid={nt_sid} は元データで11行だったが、4つのstackに分かれて何度も使われる")

# ----------------------------------------------------------------------
# 3. 積んだデータで TWFE(ただし固定効果を stack と交差させる)
#    州FE → (州 x stack)FE,  年FE → (年 x stack)FE
#    こうすると比較が各サブ実験の内側に閉じ、汚い比較が起きない
# ----------------------------------------------------------------------
stacked["unit_stack"] = stacked.sid.astype(str) + "_" + stacked["stack"].astype(str)
stacked["time_stack"] = stacked.year.astype(str) + "_" + stacked["stack"].astype(str)

stk = smf.ols(
    "l_homicide ~ treat + C(unit_stack) + C(time_stack)", data=stacked
).fit(cov_type="cluster", cov_kwds={"groups": stacked.sid})

print("=" * 70)
print("[3] stacked TWFE の処置効果(treat):", round(stk.params["treat"], 4),
      " (SE", round(stk.bse["treat"], 4), ")")

# ----------------------------------------------------------------------
# 4. イベントスタディ版(動的効果): rel ダミー(基準 rel=-1)を交差FEとともに
# ----------------------------------------------------------------------
es_df = stacked[stacked.role.isin(["treated", "control"])].copy()
# 処置群のみが rel に応じて効果を持つ: treat_rel = (処置群) x rel ダミー
es_df["evt"] = np.where(es_df.role == "treated", es_df.rel, -1)  # 対照は常に基準
es = smf.ols(
    "l_homicide ~ C(evt, Treatment(reference=-1)) + C(unit_stack) + C(time_stack)",
    data=es_df,
).fit(cov_type="cluster", cov_kwds={"groups": es_df.sid})

print("=" * 70)
print("[4] イベントスタディ(stacked, 基準 rel=-1)")
for k in [-2, 0, 1, 2]:
    name = f"C(evt, Treatment(reference=-1))[T.{k}]"
    if name in es.params.index:
        print(f"    rel={k:+d}: {es.params[name]:+.4f}  (SE {es.bse[name]:.4f})")
print("    rel<0 が0近傍なら pre-trend なし(平行トレンドの目視チェック)")
