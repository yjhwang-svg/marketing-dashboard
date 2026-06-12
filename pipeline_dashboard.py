# -*- coding: utf-8 -*-
"""
토스 일주일방문미션 세팅 솔루션 — 행 범위 입력 → 1)이미지 2)에어브릿지 3)엑셀 선택 실행.
실행: streamlit run pipeline_dashboard.py
"""
import streamlit as st
import pandas as pd
import pipeline_core as pc

LOGO = "https://yt3.googleusercontent.com/7Dc7Kb5eH2SMw2S4fomJXoB4MXeBVkuK51K6gHG-j49gqmsOAWlOiEkt3ULpeSauoOAVk99xUA=s900-c-k-c0x00ffffff-no-rj"
BLUE = "#3182F6"
SHEET_URL = "https://docs.google.com/spreadsheets/d/11GuRNtcK2dqc82SlP9DD4BXKnU1z6ad6_62EWLJxWKc/edit?gid=1445054260#gid=1445054260"

st.set_page_config(page_title="토스 일주일방문미션 세팅 솔루션", layout="centered", page_icon=LOGO)

# ── 스타일 ────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
@import url('https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.34.1/dist/tabler-icons.min.css');
html, body, [class*="css"], .stMarkdown, input, button, label, p, span, div, h1, h2, h3, .stDataFrame {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
section[data-testid="stSidebar"], [data-testid="collapsedControl"] { display:none !important; }
header[data-testid="stHeader"] { background:transparent; }
.block-container { max-width:720px; padding-top:2.4rem; padding-bottom:4rem; }
.stApp { background:#F2F4F6; }
h1,h2,h3 { letter-spacing:-0.02em; color:#191F28 !important; }

/* 카드 */
[data-testid="stVerticalBlockBorderWrapper"] {
    background:#fff; border:1px solid #ECEFF3 !important; border-radius:18px !important;
    padding:4px 22px 18px !important; margin-bottom:13px;
}

/* 섹션 헤더 + 아이콘 칩 */
.shead { display:flex; align-items:center; gap:9px; margin:12px 0 12px; }
.chip { width:30px; height:30px; border-radius:9px; background:#E8F3FF; color:%s;
        display:flex; align-items:center; justify-content:center; font-size:17px; flex-shrink:0; }
.shead .t { font-size:14.5px; font-weight:700; color:#191F28; }
.shead .s { font-size:12px; font-weight:500; color:#8B95A1; margin-left:2px; }

/* 작업 토글 미니카드 (컬럼 안 bordered container) */
.stepcard { text-align:center; }
.stepcard .ico { width:46px; height:46px; margin:4px auto 8px; border-radius:14px;
    background:#F2F7FF; color:%s; display:flex; align-items:center; justify-content:center; font-size:24px; }
.stepcard .num { font-size:11px; font-weight:700; color:#B0B8C1; letter-spacing:0.04em; }
.stepcard .nm  { font-size:14px; font-weight:700; color:#191F28; margin-top:1px; }
.stepcard .de  { font-size:11px; color:#8B95A1; margin-top:3px; line-height:1.5; min-height:34px; }
.stepcard .de a { color:%s; text-decoration:underline; }
.desc-line { font-size:12.5px; color:#8B95A1; margin:-2px 0 12px; line-height:1.5; }
.desc-line a { color:%s; text-decoration:underline; font-weight:500; }

/* 입력 */
input[type="number"], input[type="text"] { border-radius:10px !important; font-size:14px !important; }
.stNumberInput label, .stTextInput label { font-size:12.5px !important; color:#8B95A1 !important; }

/* 토스 블루 버튼 */
div.stButton > button {
    background:%s; color:#fff; border:none; border-radius:14px; height:54px;
    font-size:15.5px; font-weight:700; width:100%%; transition:filter .15s;
}
div.stButton > button:hover { filter:brightness(0.93); color:#fff; border:none; }
div.stButton > button:active { transform:scale(0.99); }
div.stButton > button p { color:#fff !important; font-weight:700 !important; }

.stProgress > div > div > div > div { background:%s !important; }

/* 폰트 override로 깨진 Streamlit 기본(Material) 아이콘 숨김 — expander 펼침 화살표 등 */
[data-testid="stExpanderToggleIcon"],
details summary [data-testid="stIconMaterial"],
.streamlit-expanderHeader svg { display:none !important; }
[data-testid="stExpander"] summary { padding-left:14px !important; }
</style>
""" % (BLUE, BLUE, BLUE, BLUE, BLUE, BLUE), unsafe_allow_html=True)

STEP_LABELS = {1: "이미지 링크", 2: "에어브릿지 링크", 3: "엑셀 파일"}
STEPS_META = {
    1: ("ti-photo", "이미지 링크", "랜딩 내 상품 썸네일로<br>이미지를 생성해요"),
    2: ("ti-link", "에어브릿지 링크", ""),
    3: ("ti-file-spreadsheet", "엑셀 파일",
        "<a href='{}' target='_blank'>시트</a> 내 S열~AB열까지<br>모두 기재되었는지 확인해주세요".format(SHEET_URL)),
}


def pad(row, n=29):
    row = list(row)
    return row + [''] * (n - len(row)) if len(row) < n else row


@st.cache_resource(show_spinner=False, ttl=1800)
def boot_tabs():
    """탭 이름만 캐시 (변하지 않음). 토큰은 만료되므로 캐시하지 않는다."""
    token = pc.get_token()
    return pc.get_tab(token, pc.TARGET_ID, pc.TARGET_GID), pc.get_tab(token, pc.SOURCE_ID, pc.SOURCE_GID)


def shead(icon, title, sub=""):
    st.markdown(
        "<div class='shead'><div class='chip'><i class='ti {}'></i></div>"
        "<span class='t'>{}</span><span class='s'>{}</span></div>".format(icon, title, sub),
        unsafe_allow_html=True)


# ── 헤더 ──────────────────────────────────────────────────────────
st.markdown(
    "<div style='display:flex;align-items:center;gap:14px;margin-bottom:18px;'>"
    "<img src='%s' style='width:50px;height:50px;border-radius:14px;'/>"
    "<div style='font-size:23px;font-weight:700;color:#191F28;letter-spacing:-0.03em;'>토스 일주일방문미션 세팅 솔루션</div></div>"
    % LOGO, unsafe_allow_html=True)


# ── 비밀번호 게이트 (app_password 설정 시에만 활성) ────────────────
def gate():
    pw = pc.get_config().get('password')
    if not pw:
        return True
    if st.session_state.get('authed'):
        return True
    with st.container(border=True):
        shead("ti-lock", "비밀번호를 입력해주세요")
        v = st.text_input("비밀번호", type="password", label_visibility="collapsed")
        if st.button("입장하기"):
            if v == pw:
                st.session_state['authed'] = True
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
    return False


if not gate():
    st.stop()

# ── ① 세팅 범위 선택 ──────────────────────────────────────────────
with st.container(border=True):
    shead("ti-list-numbers", "세팅 범위 선택")
    st.markdown(
        "<div class='desc-line'><a href='{}' target='_blank'>시트</a> 내 처리할 행 범위를 지정해주세요</div>".format(SHEET_URL),
        unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    start_row = c1.number_input("시작 행", min_value=4, max_value=400, value=47, step=1)
    end_row = c2.number_input("끝 행", min_value=4, max_value=400, value=47, step=1)

# ── ② 작업 선택 (아이콘 토글 카드) ────────────────────────────────
shead("ti-checklist", "실행 작업", "체크한 작업을 순서대로 실행합니다")
cols = st.columns(3)
toggles = {}
for i, key in enumerate([1, 2, 3]):
    icon, nm, de = STEPS_META[key]
    with cols[i]:
        with st.container(border=True):
            st.markdown(
                "<div class='stepcard'><div class='ico'><i class='ti {}'></i></div>"
                "<div class='num'>STEP {}</div><div class='nm'>{}</div><div class='de'>{}</div></div>".format(
                    icon, key, nm, de),
                unsafe_allow_html=True)
            toggles[key] = st.toggle("사용", value=True, key="step{}".format(key), label_visibility="collapsed")
st.markdown(
    "<div style='font-size:12px;color:#8B95A1;margin:2px 0 14px;line-height:1.5;'>"
    "<i class='ti ti-info-circle' style='color:#B0B8C1;'></i> "
    "엑셀은 해당 행의 S~AB가 모두 채워져야 실행되며, 완료 시 <b>공유 드라이브</b>에 저장됩니다. 이미지·에어브릿지 결과가 없으면 오류가 표시됩니다.</div>",
    unsafe_allow_html=True)

# ── ③ 저장 폴더 (공유 드라이브 내) ────────────────────────────────
with st.container(border=True):
    shead("ti-folder", "엑셀 저장 폴더", "공유 드라이브 내")
    st.markdown(
        "<div class='desc-line'>비워두면 공유 드라이브 최상위에 저장됩니다. "
        "폴더 링크/ID를 붙여넣거나, 폴더명(예: <b>2026-06/토스</b>)을 입력하면 해당 폴더에 저장돼요 (없으면 자동 생성).</div>",
        unsafe_allow_html=True)
    folder_spec = st.text_input("저장 폴더", value="", placeholder="예: 2026-06/토스  또는  폴더 링크",
                                label_visibility="collapsed")

run = st.button("실행하기")
steps = [s for s in [1, 2, 3] if toggles[s]]

# ── 실행 ──────────────────────────────────────────────────────────
if run:
    if start_row > end_row:
        st.error("시작 행이 끝 행보다 큽니다."); st.stop()
    if not steps:
        st.warning("실행할 작업을 1개 이상 선택하세요."); st.stop()
    try:
        token = pc.get_token()          # 매 실행마다 새 토큰 (1시간 만료 방지)
        ttab, stab = boot_tabs()
    except Exception as e:
        st.error("초기화(인증/시트) 실패: {}".format(e)); st.stop()

    with st.spinner("시트 로딩 중..."):
        tgt = pc.load_target(token, ttab)
        src = pc.load_source(token, stab) if 2 in steps else []

    # 저장 폴더 해석 (3번 실행 시)
    dest_folder_id = None
    if 3 in steps:
        fr = pc.resolve_drive_folder(token, pc.get_config()['drive'], folder_spec)
        if not fr['ok']:
            st.error("저장 폴더 오류 · {}".format(fr['msg'])); st.stop()
        dest_folder_id = fr['id']
        st.markdown(
            "<div style='font-size:12.5px;color:#8B95A1;margin:2px 0;'>"
            "<i class='ti ti-folder'></i> 저장 위치: <b>{}</b></div>".format(fr['name']),
            unsafe_allow_html=True)

    rows = list(range(int(start_row), int(end_row) + 1))
    st.markdown(
        "<div style='background:#E8F3FF;border-radius:12px;padding:12px 16px;font-size:13px;color:#1B64DA;font-weight:600;margin:10px 0 4px;'>"
        "<i class='ti ti-player-play'></i>  대상 {}개 행 ({}~{}) · {}</div>".format(
            len(rows), start_row, end_row, "  →  ".join(STEP_LABELS[s] for s in steps)),
        unsafe_allow_html=True)

    results, files, blocked = [], [], []
    progress = st.progress(0.0)
    log = st.container()

    for idx, rn in enumerate(rows):
        row = pad(tgt[rn - 1]) if rn - 1 < len(tgt) else pad([])
        name = pc.cell(row, 'M_name') or pc.cell(row, 'Y_name') or '(이름없음)'
        rec = {"행": rn, "상품명": name, "이미지": "—", "에어브릿지": "—", "엑셀": "—"}

        with log.expander("{}행 · {}".format(rn, name), expanded=False):
          try:
            if 1 in steps:
                r = pc.process_image(token, ttab, rn, row)
                if r['ok']:
                    row[pc.COL['AB_img']] = r['url']; rec["이미지"] = "✅"
                    st.success("이미지 · {}".format(r['msg'])); st.write(r['url'])
                else:
                    rec["이미지"] = "❌"; st.error("이미지 · {}".format(r['msg']))

            if 2 in steps:
                r = pc.process_airbridge(token, ttab, rn, row, src)
                if r['ok']:
                    row[pc.COL['T_link']] = r['link']; rec["에어브릿지"] = "✅"
                    st.success("에어브릿지 · {}".format(r['msg'])); st.write(r['link'])
                else:
                    rec["에어브릿지"] = "❌"; st.error("에어브릿지 · {}".format(r['msg']))

            if 3 in steps:
                r = pc.process_excel(token, ttab, rn, row, dest_folder_id=dest_folder_id)
                if r['ok']:
                    rec["엑셀"] = "✅"; files.append((r['campaign'], r.get('link', ''), r.get('data')))
                    if r.get('link'):
                        st.success("엑셀 · {}".format(r['msg'])); st.markdown("[드라이브에서 열기]({})".format(r['link']))
                    else:
                        st.success("엑셀 · {}".format(r['msg']))
                elif r.get('blocked'):
                    rec["엑셀"] = "⛔"; st.error("엑셀 · {}".format(r['msg']))
                    blocked.append({'row': rn, 'reason': r.get('reason'),
                                    'missing': r.get('missing', []), 'need': r.get('need', [])})
                else:
                    rec["엑셀"] = "❌"; st.error("엑셀 · {}".format(r['msg']))
          except Exception as e:
            st.error("행 처리 중 오류: {}".format(str(e)[:160]))

        results.append(rec)
        progress.progress((idx + 1) / len(rows))

    st.markdown("<div style='font-size:15px;font-weight:700;color:#191F28;margin:18px 0 8px;'>실행 결과</div>", unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

    # 3번이 막힌 경우 → 상황별 안내 문구 (variation)
    if blocked:
        def fmt_rows(rs):
            rs = sorted(set(rs))
            return ', '.join(str(r) for r in rs) + '행'
        # (1) S~AB 빈 셀 때문에 막힌 경우: 컬럼별로 묶기
        by_col = {}
        for b in blocked:
            if b['reason'] == 'cells':
                for lab in b['missing']:
                    by_col.setdefault(lab, []).append(b['row'])
        # (2) 1·2번 미실행으로 막힌 경우
        prereq_rows = [b['row'] for b in blocked if b['reason'] == 'prereq']

        tips = []
        for lab, rs in by_col.items():
            tips.append("{}의 <b>{}</b> 열을 채운 뒤 STEP 3를 다시 실행해주세요".format(fmt_rows(rs), lab))
        if prereq_rows:
            tips.append("{}은 <b>STEP 1·2(이미지·에어브릿지)</b>를 먼저 실행한 뒤 STEP 3를 다시 실행해주세요".format(fmt_rows(prereq_rows)))

        body = "<br>".join("· " + t for t in tips)
        st.markdown(
            "<div style='background:#FFF4E5;border:1px solid #FFE0B2;border-radius:12px;"
            "padding:14px 16px;margin-top:10px;font-size:13.5px;color:#8A5300;line-height:1.7;'>"
            "<b><i class='ti ti-alert-triangle'></i> 엑셀 파일이 생성되지 않은 행이 있어요</b><br>{}</div>".format(body),
            unsafe_allow_html=True)

    if files:
        st.markdown("<div style='font-size:15px;font-weight:700;color:#191F28;margin:18px 0 8px;'>생성된 엑셀 파일 (공유 드라이브 저장 완료)</div>", unsafe_allow_html=True)
        XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if len(files) == 1:
            camp, link, data = files[0]
            cda, cdb = st.columns(2)
            if data:
                cda.download_button("⬇  {}.xlsx 내려받기".format(camp), data, file_name="{}.xlsx".format(camp), mime=XLSX, use_container_width=True)
            if link:
                cdb.link_button("드라이브에서 열기", link, use_container_width=True)
        else:
            import io, zipfile
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for camp, link, data in files:
                    if data:
                        zf.writestr("{}.xlsx".format(camp), data)
            st.download_button("⬇  전체 {}건 ZIP 내려받기".format(len(files)), buf.getvalue(),
                file_name="toss_files.zip", mime="application/zip")
            for camp, link, _ in files:
                if link:
                    st.markdown("<span style='font-size:13px;color:#4E5968;'>• <a href='{}' target='_blank'>{}.xlsx</a></span>".format(link, camp), unsafe_allow_html=True)
                else:
                    st.markdown("<span style='font-size:13px;color:#4E5968;'>• {}.xlsx</span>".format(camp), unsafe_allow_html=True)
