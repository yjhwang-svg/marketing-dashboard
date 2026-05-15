import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime, timedelta

st.set_page_config(page_title="마케팅 성과 대시보드", layout="wide", page_icon="📊")

import os

# Streamlit Cloud에서 __file__ 경로가 다를 수 있어 resolve()로 절대경로 사용
DATA_DIR = Path(__file__).resolve().parent
# fallback: cwd도 확인해서 data/ 있는 쪽 사용
if not (DATA_DIR / "data").exists():
    DATA_DIR = Path(os.getcwd())

CHANNEL_DIR = DATA_DIR / "data" / "channel"
AF_DIR = DATA_DIR / "data" / "appsflyer"

MEDIA_SOURCE_MAP = {
    "googleadwords_int": "구글", "Google Ads": "구글", "google": "구글",
    "Facebook Ads": "메타", "facebook": "메타", "meta": "메타", "instagram": "메타",
    "naver_search": "네이버", "naver": "네이버", "NaverSearchAd": "네이버",
}
CHANNEL_COLORS = {"구글": "#1a56db", "메타": "#f59e0b", "네이버": "#7c3aed"}
TYPE_ORDER = ["VID", "IMG", "CRS", "TXT", "기타"]


# ── 데이터 로드 ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data():
    ch_files = sorted(CHANNEL_DIR.glob("*_channel.csv"))
    af_files = sorted(AF_DIR.glob("*_appsflyer.csv"))

    def read_all(files):
        frames = []
        for f in files:
            try:
                frames.append(pd.read_csv(f, encoding="utf-8-sig"))
            except Exception:
                pass
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    ch = read_all(ch_files)
    af = read_all(af_files)

    if ch.empty:
        return pd.DataFrame()

    ch = ch.rename(columns={"일": "date"})
    ch["date"] = pd.to_datetime(ch["date"])

    if not af.empty:
        af = af.rename(columns={"일": "date", "미디어소스": "채널"})
        af["채널"] = af["채널"].map(lambda x: MEDIA_SOURCE_MAP.get(str(x).strip(), str(x).strip()))
        af["date"] = pd.to_datetime(af["date"])

        join_keys = ["date", "캠페인", "그룹", "소재"]
        ch_cols = [c for c in join_keys + ["채널", "채널분류", "캠페인목적", "노출", "비용", "클릭", "회원가입", "구매", "구매매출"] if c in ch.columns]
        af_cols = [c for c in join_keys + ["클릭", "회원가입", "구매", "구매매출"] if c in af.columns]

        df = pd.merge(ch[ch_cols], af[af_cols], on=join_keys, how="outer", suffixes=("_ch", "_af"))
    else:
        df = ch.copy()

    # 소재 타입 파싱
    if "소재" in df.columns:
        df["소재타입"] = df["소재"].apply(lambda n: str(n).split("_")[0].upper()).map(
            lambda t: t if t in ["VID", "IMG", "CRS", "TXT"] else "기타"
        )

    return df.sort_values("date").reset_index(drop=True)


# ── 지표 헬퍼 ─────────────────────────────────────────────────────────────────
def best_col(df, base, prefer="af"):
    alt = "ch" if prefer == "af" else "af"
    for c in [f"{base}_{prefer}", base, f"{base}_{alt}"]:
        if c in df.columns:
            return c
    return None

def s(df, base, prefer="af"):
    c = best_col(df, base, prefer)
    return df[c].fillna(0).sum() if c else 0

def calc_kpis(df):
    cost = s(df, "비용", "ch")
    imp  = s(df, "노출", "ch")
    clk  = s(df, "클릭", "ch")
    reg  = s(df, "회원가입", "af")
    pur  = s(df, "구매", "af")
    rev  = s(df, "구매매출", "af")
    return dict(
        비용=cost, 노출=imp, 클릭=clk, 회원가입=reg, 구매=pur, 매출=rev,
        CTR=clk/imp*100 if imp else 0,
        CPC=cost/clk if clk else 0,
        CPA=cost/pur if pur else 0,
        CAC=cost/reg if reg else 0,
        ROAS=rev/cost*100 if cost else 0,
    )

def delta(curr, prev, higher_is_better=True):
    """전일비/동요일비 delta 문자열과 방향 반환."""
    if not prev or prev == 0:
        return None, None
    pct = (curr - prev) / prev * 100
    good = (pct > 0) == higher_is_better
    return f"{'▲' if pct>0 else '▼'} {abs(pct):.1f}%", "normal" if good else "inverse"

def wk_delta_str(curr, prev, hib=True):
    if not prev or prev == 0:
        return "–"
    pct = (curr - prev) / prev * 100
    return f"{'▲' if pct>0 else '▼'}{abs(pct):.0f}% vs 지난주"


# ── 데이터 로드 & 검증 ────────────────────────────────────────────────────────
df = load_data()

if df.empty:
    st.error("데이터 없음 — CSV 파일을 찾을 수 없습니다.")
    with st.expander("🔍 경로 디버그"):
        st.code(f"DATA_DIR: {DATA_DIR}\nCHANNEL_DIR: {CHANNEL_DIR}\nAF_DIR: {AF_DIR}\n"
                f"channel files: {list(CHANNEL_DIR.glob('*_channel.csv')) if CHANNEL_DIR.exists() else 'directory not found'}\n"
                f"af files: {list(AF_DIR.glob('*_appsflyer.csv')) if AF_DIR.exists() else 'directory not found'}")
    st.stop()

# ── 사이드바 필터 ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("필터")
    dmin, dmax = df["date"].min().date(), df["date"].max().date()
    dr = st.date_input("날짜 범위", value=(dmin, dmax), min_value=dmin, max_value=dmax)

    chs = sorted(df["채널"].dropna().unique()) if "채널" in df.columns else []
    sel_ch = st.multiselect("채널", chs, default=chs)

    camps = sorted(df["캠페인"].dropna().unique()) if "캠페인" in df.columns else []
    sel_camp = st.multiselect("캠페인", camps, default=camps)

    st.caption(f"로드: {datetime.now().strftime('%H:%M:%S')}")
    if st.button("🔄 새로고침"):
        st.cache_data.clear()
        st.rerun()

# 필터 적용
fdf = df.copy()
if len(dr) == 2:
    fdf = fdf[(fdf["date"].dt.date >= dr[0]) & (fdf["date"].dt.date <= dr[1])]
if sel_ch and "채널" in fdf.columns:
    fdf = fdf[fdf["채널"].isin(sel_ch)]
if sel_camp and "캠페인" in fdf.columns:
    fdf = fdf[fdf["캠페인"].isin(sel_camp)]

# ── 날짜 기준 슬라이스 ────────────────────────────────────────────────────────
latest   = df["date"].max()
prev_d   = latest - timedelta(days=1)
dow_d    = latest - timedelta(days=7)
wk_start = latest - timedelta(days=latest.weekday())
lwk_start = wk_start - timedelta(days=7)
lwk_end  = lwk_start + timedelta(days=latest.weekday())

def slice_date(d):
    return fdf[fdf["date"] == d]

today_df    = slice_date(latest)
prev_df     = slice_date(prev_d)
dow_df      = slice_date(dow_d)
this_wk_df  = fdf[(fdf["date"] >= wk_start) & (fdf["date"] <= latest)]
last_wk_df  = fdf[(fdf["date"] >= lwk_start) & (fdf["date"] <= lwk_end)]

K = calc_kpis(today_df)
Kp = calc_kpis(prev_df)
Kd = calc_kpis(dow_df)
Kw = calc_kpis(this_wk_df)
Klw = calc_kpis(last_wk_df)


# ══════════════════════════════════════════════════════════════════════════════
st.title("📊 마케팅 성과 대시보드")
st.caption(f"최신 데이터: **{latest.strftime('%Y-%m-%d (%a)')}**  |  필터 적용 행: {len(fdf):,}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📅 오늘 요약", "📡 채널·캠페인", "🎨 소재 분석", "📈 트렌드", "🔀 AF 비교"])


# ── TAB 1: 오늘 요약 ──────────────────────────────────────────────────────────
with tab1:

    # 주간 누계 바
    wc = st.columns(4)
    wc[0].metric("주간 비용",    f"₩{Kw['비용']:,.0f}",    wk_delta_str(Kw['비용'],  Klw['비용'],  False))
    wc[1].metric("주간 구매",    f"{Kw['구매']:,.0f}건",    wk_delta_str(Kw['구매'],  Klw['구매']))
    wc[2].metric("주간 ROAS",   f"{Kw['ROAS']:.0f}%",      wk_delta_str(Kw['ROAS'],  Klw['ROAS']))
    wc[3].metric("주간 CPA",    f"₩{Kw['CPA']:,.0f}",      wk_delta_str(Kw['CPA'],   Klw['CPA'],  False))

    st.divider()
    st.subheader(f"일간 KPI — {latest.strftime('%m/%d (%a)')}")

    # KPI 카드: 전일비 메인 + 동요일비 서브
    def kpi_card(col, label, key, fmt_fn, hib=True):
        v, vp, vd = K[key], Kp[key], Kd[key]
        d_prev, _ = delta(v, vp, hib)
        d_dow,  _ = delta(v, vd, hib)
        col.metric(label, fmt_fn(v), d_prev)
        col.caption(f"동요일비 {d_dow}" if d_dow else "동요일 데이터 없음")

    c = st.columns(5)
    kpi_card(c[0], "비용",    "비용",  lambda v: f"₩{v:,.0f}",  False)
    kpi_card(c[1], "구매",    "구매",  lambda v: f"{v:,.0f}건")
    kpi_card(c[2], "ROAS",   "ROAS",  lambda v: f"{v:.0f}%")
    kpi_card(c[3], "CPA",    "CPA",   lambda v: f"₩{v:,.0f}",  False)
    kpi_card(c[4], "CTR",    "CTR",   lambda v: f"{v:.2f}%")

    st.divider()

    # 채널별 ROAS (전일 대비)
    if "채널" in today_df.columns and not today_df.empty:
        st.subheader("채널별 ROAS")
        cost_c = "비용"
        rev_c  = best_col(fdf, "구매매출", "af") or "구매매출"

        def ch_roas(d):
            if d.empty or cost_c not in d.columns or rev_c not in d.columns:
                return pd.DataFrame(columns=["채널", "ROAS"])
            g = d.groupby("채널")[[cost_c, rev_c]].sum().reset_index()
            g["ROAS"] = (g[rev_c] / g[cost_c] * 100).round(0)
            return g

        roas_today = ch_roas(today_df).set_index("채널")["ROAS"]
        roas_prev  = ch_roas(prev_df).set_index("채널")["ROAS"]

        rows = []
        for ch in sorted(roas_today.index):
            curr = roas_today.get(ch, 0)
            prev_v = roas_prev.get(ch, 0)
            d_str = f" ({'+' if curr-prev_v>=0 else ''}{(curr-prev_v)/prev_v*100:.1f}%)" if prev_v else ""
            rows.append(dict(채널=ch, ROAS=curr, label=f"{curr:.0f}%{d_str}"))

        fig = go.Figure()
        for r in rows:
            fig.add_bar(x=[r["채널"]], y=[r["ROAS"]], name=r["채널"],
                        marker_color=CHANNEL_COLORS.get(r["채널"], "#94a3b8"),
                        text=[r["label"]], textposition="outside")
        fig.update_layout(height=280, showlegend=False,
                          yaxis=dict(range=[0, max(r["ROAS"] for r in rows) * 1.35 if rows else 500]),
                          margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)


# ── TAB 2: 채널·캠페인 ────────────────────────────────────────────────────────
with tab2:
    cost_c  = "비용"
    imp_c   = "노출"
    click_c = best_col(fdf, "클릭",      "ch") or "클릭"
    pur_c   = best_col(fdf, "구매",      "af") or "구매"
    rev_c   = best_col(fdf, "구매매출",  "af") or "구매매출"
    reg_c   = best_col(fdf, "회원가입",  "af") or "회원가입"

    def make_table(group_col):
        agg = {c: "sum" for c in [cost_c, imp_c, click_c, pur_c, rev_c] if c in fdf.columns}
        g = fdf.groupby(group_col).agg(agg).reset_index()
        if cost_c in g.columns:
            if rev_c in g.columns:  g["ROAS"] = (g[rev_c] / g[cost_c] * 100).round(0)
            if pur_c in g.columns:  g["CPA"]  = (g[cost_c] / g[pur_c]).round(0)
        if click_c in g.columns and imp_c in g.columns:
            g["CTR"] = (g[click_c] / g[imp_c] * 100).round(2)
        return g.sort_values(cost_c, ascending=False) if cost_c in g.columns else g

    # 채널별
    st.subheader("채널별 성과")
    if "채널" in fdf.columns:
        ch_tbl = make_table("채널")
        show = ["채널"] + [c for c in [cost_c, imp_c, click_c, "CTR", pur_c, "ROAS", "CPA"] if c in ch_tbl.columns]
        st.dataframe(ch_tbl[show], use_container_width=True, hide_index=True)

        cc1, cc2 = st.columns(2)
        for ax, yval, title in [(cc1, "ROAS", "채널별 ROAS (%)"), (cc2, cost_c, "채널별 비용")]:
            if yval in ch_tbl.columns:
                fig = px.bar(ch_tbl, x="채널", y=yval, color="채널", text_auto=True,
                             title=title, color_discrete_map=CHANNEL_COLORS)
                fig.update_layout(height=260, showlegend=False, margin=dict(t=40, b=10))
                ax.plotly_chart(fig, use_container_width=True)

    st.divider()

    # 캠페인 목적별
    grp_col = "캠페인목적" if "캠페인목적" in fdf.columns else "캠페인"
    st.subheader(f"{grp_col}별 성과")
    if grp_col in fdf.columns:
        camp_tbl = make_table(grp_col)
        show = [grp_col] + [c for c in [cost_c, pur_c, "ROAS", "CPA", click_c, "CTR"] if c in camp_tbl.columns]
        st.dataframe(camp_tbl[show], use_container_width=True, hide_index=True)

    st.divider()

    # 그룹(타겟)별
    st.subheader("그룹(타겟)별 성과")
    if "그룹" in fdf.columns:
        grp_tbl = make_table("그룹")
        show = ["그룹"] + [c for c in [cost_c, pur_c, "ROAS", "CPA", "CTR"] if c in grp_tbl.columns]
        st.dataframe(grp_tbl[show], use_container_width=True, hide_index=True)


# ── TAB 3: 소재 분석 ──────────────────────────────────────────────────────────
with tab3:
    cost_c  = "비용"
    imp_c   = "노출"
    click_c = best_col(fdf, "클릭",     "ch") or "클릭"
    pur_c   = best_col(fdf, "구매",     "af") or "구매"
    rev_c   = best_col(fdf, "구매매출", "af") or "구매매출"

    if "소재타입" not in fdf.columns:
        st.info("소재명에서 타입(VID/IMG/CRS/TXT)을 파싱할 수 없습니다.")
    else:
        # 소재 타입별 집계
        agg_m = {c: "sum" for c in [cost_c, imp_c, click_c, pur_c, rev_c] if c in fdf.columns}
        type_grp = fdf.groupby("소재타입").agg(agg_m).reset_index()
        if cost_c in type_grp.columns:
            if rev_c in type_grp.columns: type_grp["ROAS"] = (type_grp[rev_c] / type_grp[cost_c] * 100).round(0)
            if pur_c in type_grp.columns: type_grp["CPA"]  = (type_grp[cost_c] / type_grp[pur_c]).round(0)
        if click_c in type_grp.columns and imp_c in type_grp.columns:
            type_grp["CTR"] = (type_grp[click_c] / type_grp[imp_c] * 100).round(2)

        type_grp["소재타입"] = pd.Categorical(
            type_grp["소재타입"],
            categories=[t for t in TYPE_ORDER if t in type_grp["소재타입"].values],
            ordered=True
        )
        type_grp = type_grp.sort_values("소재타입").reset_index(drop=True)

        # ── 소재 타입 카드 ──────────────────────────────────────────────────────
        st.subheader("소재 타입별 성과 카드")

        # ROAS 기준 TOP 타입 결정
        top_type = type_grp.loc[type_grp["ROAS"].idxmax(), "소재타입"] if "ROAS" in type_grp.columns else None

        TYPE_BADGE_CSS = {
            "VID": "background:#dbeafe;color:#1d4ed8",
            "IMG": "background:#fef3c7;color:#92400e",
            "CRS": "background:#ede9fe;color:#6d28d9",
            "TXT": "background:#dcfce7;color:#166534",
            "기타": "background:#f1f5f9;color:#475569",
        }

        def roas_color(roas, max_roas):
            ratio = roas / max_roas if max_roas else 0
            if ratio >= 0.85: return "#4ade80"
            if ratio >= 0.6:  return "#86efac"
            if ratio >= 0.4:  return "#fde68a"
            return "#fca5a5"

        def cpa_color(cpa, min_cpa):
            if min_cpa == 0: return "#e2e8f0"
            ratio = min_cpa / cpa if cpa else 0
            if ratio >= 0.9:  return "#4ade80"
            if ratio >= 0.75: return "#86efac"
            if ratio >= 0.55: return "#fde68a"
            return "#fca5a5"

        max_roas = type_grp["ROAS"].max() if "ROAS" in type_grp.columns else 1
        min_cpa  = type_grp["CPA"].min()  if "CPA"  in type_grp.columns else 0

        cols = st.columns(len(type_grp))
        for i, row in type_grp.iterrows():
            t = str(row["소재타입"])
            is_top = (t == top_type)
            badge_css = TYPE_BADGE_CSS.get(t, TYPE_BADGE_CSS["기타"])
            rc = roas_color(row.get("ROAS", 0), max_roas)
            cc = cpa_color(row.get("CPA", 0), min_cpa)

            with cols[i]:
                # TOP 배지
                if is_top:
                    st.markdown(
                        "<div style='text-align:center;margin-bottom:4px'>"
                        "<span style='background:#4ade80;color:#0f1117;font-size:11px;"
                        "font-weight:700;padding:2px 10px;border-radius:4px'>⭐ TOP</span></div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown("<div style='margin-bottom:22px'></div>", unsafe_allow_html=True)

                border = "2px solid #4ade80" if is_top else "1px solid #e2e8f0"
                st.markdown(
                    f"<div style='border:{border};border-radius:12px;padding:16px;text-align:center'>"
                    f"<span style='{badge_css};font-size:13px;font-weight:700;"
                    f"padding:3px 12px;border-radius:6px'>{t}</span>"
                    "</div>",
                    unsafe_allow_html=True,
                )

                # ROAS — 큰 숫자
                roas_val = row.get("ROAS", 0)
                st.markdown(
                    f"<div style='text-align:center;margin:8px 0 4px'>"
                    f"<div style='font-size:11px;color:#94a3b8'>ROAS</div>"
                    f"<div style='font-size:32px;font-weight:700;color:{rc}'>{roas_val:.0f}%</div>"
                    "</div>",
                    unsafe_allow_html=True,
                )

                # CTR / CPA / 구매 서브 지표
                ctr_val = row.get("CTR", 0)
                cpa_val = row.get("CPA", 0)
                pur_val = row.get(pur_c, 0) if pur_c in type_grp.columns else 0

                c1, c2 = st.columns(2)
                c1.metric("CTR",  f"{ctr_val:.2f}%")
                c2.metric("CPA",  f"₩{cpa_val:,.0f}")
                st.metric("구매", f"{int(pur_val):,}건")

        st.divider()

        # 소재 랭킹 테이블
        st.subheader("소재 랭킹")
        sort_opts = [m for m in ["ROAS", "CPA", "CTR", pur_c, cost_c]
                     if m in fdf.columns or m in type_grp.columns]

        # 소재 단위 집계
        cr_agg = {c: "sum" for c in [cost_c, imp_c, click_c, pur_c, rev_c] if c in fdf.columns}
        cr_tbl = fdf.groupby(["소재", "소재타입"]).agg(cr_agg).reset_index()
        if cost_c in cr_tbl.columns:
            if rev_c in cr_tbl.columns: cr_tbl["ROAS"] = (cr_tbl[rev_c] / cr_tbl[cost_c] * 100).round(0)
            if pur_c in cr_tbl.columns: cr_tbl["CPA"]  = (cr_tbl[cost_c] / cr_tbl[pur_c]).round(0)
        if click_c in cr_tbl.columns and imp_c in cr_tbl.columns:
            cr_tbl["CTR"] = (cr_tbl[click_c] / cr_tbl[imp_c] * 100).round(2)

        all_metrics = [m for m in ["ROAS", "CPA", "CTR", pur_c, cost_c] if m in cr_tbl.columns]
        rc1, rc2 = st.columns([2, 1])
        sort_by = rc1.selectbox("정렬 기준", all_metrics, key="cr_sort")
        top_n   = rc2.slider("상위 N개", 5, 30, 15)

        if sort_by in cr_tbl.columns:
            asc = sort_by == "CPA"
            cr_show = cr_tbl.nsmallest(top_n, sort_by) if asc else cr_tbl.nlargest(top_n, sort_by)
        else:
            cr_show = cr_tbl.head(top_n)

        show_cols = ["소재", "소재타입"] + [c for c in ["ROAS", "CTR", "CPA", cost_c, pur_c] if c in cr_show.columns]
        st.dataframe(cr_show[show_cols].reset_index(drop=True), use_container_width=True, hide_index=True)


# ── TAB 4: 트렌드 ─────────────────────────────────────────────────────────────
with tab4:
    cost_c  = "비용"
    rev_c   = best_col(fdf, "구매매출", "af") or "구매매출"
    pur_c   = best_col(fdf, "구매",     "af") or "구매"
    reg_c   = best_col(fdf, "회원가입", "af") or "회원가입"

    day_agg = {c: "sum" for c in [cost_c, rev_c, pur_c, reg_c] if c in fdf.columns}
    daily = fdf.groupby("date").agg(day_agg).reset_index()
    if cost_c in daily.columns and rev_c in daily.columns:
        daily["ROAS"] = (daily[rev_c] / daily[cost_c] * 100).round(0)

    t_sub1, t_sub2, t_sub3 = st.tabs(["비용 & ROAS", "전환", "채널별"])

    with t_sub1:
        fig = go.Figure()
        if cost_c in daily.columns:
            fig.add_bar(x=daily["date"], y=daily[cost_c], name="비용", marker_color="#bfdbfe")
        if "ROAS" in daily.columns:
            fig.add_scatter(x=daily["date"], y=daily["ROAS"], name="ROAS(%)",
                            mode="lines+markers", yaxis="y2",
                            line=dict(color="#1a56db", width=2.5))
        fig.update_layout(
            yaxis_title="비용 (원)", yaxis2=dict(overlaying="y", side="right", title="ROAS (%)"),
            height=360, margin=dict(t=20, b=10), legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig, use_container_width=True)

    with t_sub2:
        conv_cols = [c for c in [pur_c, reg_c] if c and c in daily.columns]
        if conv_cols:
            fig = px.line(daily, x="date", y=conv_cols, markers=True, height=360,
                          labels={"value": "건수", "variable": "지표"})
            fig.update_layout(margin=dict(t=20, b=10), legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig, use_container_width=True)

    with t_sub3:
        if "채널" in fdf.columns:
            metric_sel = st.selectbox("지표", ["ROAS", "비용", "구매"], key="trend_ch")
            ch_agg = {c: "sum" for c in [cost_c, rev_c, pur_c] if c in fdf.columns}
            ch_daily = fdf.groupby(["date", "채널"]).agg(ch_agg).reset_index()
            if cost_c in ch_daily.columns and rev_c in ch_daily.columns:
                ch_daily["ROAS"] = (ch_daily[rev_c] / ch_daily[cost_c] * 100).round(0)

            y_col = {"ROAS": "ROAS", "비용": cost_c, "구매": pur_c}[metric_sel]
            if y_col in ch_daily.columns:
                fig = px.line(ch_daily, x="date", y=y_col, color="채널", markers=True, height=360,
                              color_discrete_map=CHANNEL_COLORS,
                              labels={y_col: metric_sel})
                fig.update_layout(margin=dict(t=20, b=10), legend=dict(orientation="h", y=1.1))
                st.plotly_chart(fig, use_container_width=True)


# ── TAB 5: AF 비교 ────────────────────────────────────────────────────────────
with tab5:
    st.subheader("채널 리포트 vs AppsFlyer 비교")
    st.caption("플랫폼 집계(채널) vs 어트리뷰션(AF) — 차이가 클수록 어트리뷰션 로스 주의")

    rows = []
    for base, label in [("클릭","클릭"), ("회원가입","회원가입"), ("구매","구매"), ("구매매출","매출")]:
        c_ch, c_af = f"{base}_ch", f"{base}_af"
        if c_ch in fdf.columns and c_af in fdf.columns:
            v_ch = fdf[c_ch].fillna(0).sum()
            v_af = fdf[c_af].fillna(0).sum()
            loss = (v_ch - v_af) / v_ch * 100 if v_ch else 0
            rows.append({"지표": label,
                          "채널(플랫폼)": f"{v_ch:,.0f}",
                          "앱스플라이어":  f"{v_af:,.0f}",
                          "차이":          f"{v_ch - v_af:,.0f}",
                          "로스율":        f"{loss:.1f}%"})

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # 채널별 로스율 바차트
        st.subheader("채널별 구매 로스율")
        ch_loss = []
        for ch in (fdf["채널"].dropna().unique() if "채널" in fdf.columns else []):
            cdf = fdf[fdf["채널"] == ch]
            for base, label in [("구매", "구매"), ("구매매출", "매출")]:
                c_ch, c_af = f"{base}_ch", f"{base}_af"
                if c_ch in cdf.columns and c_af in cdf.columns:
                    v_ch = cdf[c_ch].fillna(0).sum()
                    v_af = cdf[c_af].fillna(0).sum()
                    loss = (v_ch - v_af) / v_ch * 100 if v_ch else 0
                    ch_loss.append({"채널": ch, "지표": label, "로스율(%)": round(loss, 1)})

        if ch_loss:
            fig = px.bar(pd.DataFrame(ch_loss), x="채널", y="로스율(%)", color="지표",
                         barmode="group", height=300,
                         color_discrete_sequence=["#1a56db", "#f59e0b"])
            fig.add_hline(y=0, line_color="#94a3b8", line_dash="dash")
            fig.update_layout(margin=dict(t=10, b=10), legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("_ch / _af 접미사 컬럼이 없습니다. 두 데이터셋이 모두 조인된 상태에서 사용해주세요.")

    with st.expander("원본 데이터", expanded=False):
        st.dataframe(fdf.reset_index(drop=True), use_container_width=True)
        st.caption(f"총 {len(fdf):,}행 (필터 적용 후)")
