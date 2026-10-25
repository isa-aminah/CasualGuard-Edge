"""Global styling for the CAUSALGUARD-EDGE Streamlit application."""

import streamlit as st


def apply_theme() -> None:
    """Inject the application-wide dark command-center theme."""
    st.markdown(
        """
        <style>
        :root {
            --bg: #080f1c;
            --panel: #111d2e;
            --panel-raised: #162438;
            --border: #26364b;
            --muted: #a8b6c9;
            --white: #f1f5f9;
            --emerald: #2dd4bf;
            --mint: #22d3ee;
            --blue: #38bdf8;
            --red: #fb7185;
            --amber: #fbbf24;
            --panel-shadow: 0 14px 36px rgba(0, 0, 0, .22);
        }
        html, body, [data-testid="stAppViewContainer"] {
            background-color: var(--bg);
            color: var(--white);
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        html { font-size: 16px !important; }
        body { background: var(--bg); }
        [data-testid="stAppViewContainer"] {
            background-image:
                radial-gradient(ellipse at 10% 0%, rgba(34, 211, 238, .055), transparent 36%),
                radial-gradient(ellipse at 100% 16%, rgba(45, 212, 191, .045), transparent 32%),
                linear-gradient(145deg, #080f1c 0%, #0a1321 52%, #080f1c 100%);
        }
        [data-testid="stHeader"] { background: rgba(8, 15, 28, .86); backdrop-filter: blur(16px); }
        [data-testid="stToolbar"] { right: 1rem; }
        [data-testid="stAppViewContainer"] > .main { background: transparent; }
        .block-container { padding: 1.55rem 2rem 2.75rem; max-width: 1780px; }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0b1424 0%, #0a1321 100%);
            border-right: 1px solid rgba(71, 95, 126, .34);
            box-shadow: 12px 0 32px rgba(0, 0, 0, .12);
        }
        [data-testid="stSidebar"] > div:first-child { padding-top: 1.1rem; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #d3deeb; }
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { color: #e2eaf4 !important; font-weight: 600; }
        h1, h2, h3, h4 { color: var(--white) !important; letter-spacing: -.025em; }
        h1 { font-size: clamp(1.75rem, 2.5vw, 2.25rem) !important; margin-bottom: .15rem !important; font-weight: 760 !important; }
        h2 { font-size: 1.3rem !important; }
        p, label, .stCaption { color: #d6e0ec; }
        [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: #aebdd0 !important; }
        [data-testid="stAlert"] [data-testid="stMarkdownContainer"] p { color: #e2e8f0; }
        [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label { color: #e2e8f0 !important; }
        [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
        [data-testid="stTextArea"] textarea { color: #f8fafc !important; }
        [data-baseweb="select"] *, [data-baseweb="popover"] * { color: #f1f5f9; }
        [data-testid="stMetric"] {
            position: relative;
            overflow: hidden;
            min-height: 112px;
            background:
                radial-gradient(ellipse at 100% 0%, rgba(34, 211, 238, .075), transparent 48%),
                linear-gradient(145deg, rgba(22, 36, 56, .98), rgba(15, 27, 44, .98));
            border: 1px solid rgba(93, 118, 151, .32);
            border-radius: 16px;
            padding: 1.05rem 1.15rem;
            box-shadow: var(--panel-shadow);
            transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
        }
        [data-testid="stMetric"]::before {
            content: ""; position: absolute; inset: 0 auto 0 0; width: 3px;
            background: linear-gradient(180deg, #22d3ee, #2dd4bf); opacity: .8;
        }
        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            border-color: rgba(103, 192, 210, .48);
            box-shadow: 0 16px 36px rgba(0, 0, 0, .22);
        }
        [data-testid="stMetricLabel"] { color: #b8c8dc; font-size: .9rem; font-weight: 650; letter-spacing: .01em; }
        [data-testid="stMetricValue"] { color: #f1f7fc; font-size: clamp(1.8rem, 2.5vw, 2.35rem); font-weight: 730; letter-spacing: -.035em; }
        [data-testid="stMetricDelta"] { color: var(--mint); font-weight: 650; }
        [data-testid="stVerticalBlockBorderWrapper"] > div {
            border-color: rgba(76, 98, 127, .34) !important;
            background: linear-gradient(145deg, rgba(17, 29, 46, .96), rgba(14, 25, 41, .98));
            border-radius: 16px;
            box-shadow: 0 12px 30px rgba(0, 0, 0, .13);
            transition: border-color .18s ease, box-shadow .18s ease;
        }
        [data-testid="stVerticalBlockBorderWrapper"] > div:hover {
            border-color: rgba(83, 135, 164, .55) !important;
            box-shadow: 0 15px 34px rgba(0, 0, 0, .18);
        }
        .cg-card {
            background: linear-gradient(145deg, #111d2e, #0f1b2c);
            border: 1px solid rgba(76, 98, 127, .34);
            border-radius: 15px;
            padding: 1rem 1.1rem;
            box-shadow: var(--panel-shadow);
            margin-bottom: .85rem;
        }
        .cg-title { color: var(--white); font-size: 1.08rem; font-weight: 700; margin: 0 0 .8rem; }
        .cg-subtitle { color: #cbd5e1; font-size: .9rem; margin: .1rem 0 .85rem; }
        .cg-brand { font-weight: 800; font-size: 1.08rem; letter-spacing: .02em; color: #eaf2ff; }
        .cg-brand span { color: #2dd4bf; }
        .cg-brand-sub { color: #aebdd0; font-size: .8rem; line-height: 1.5; margin-top: .4rem; }
        .cg-page-head {
            display: flex; align-items: center; justify-content: space-between; gap: 1rem;
            border: 1px solid rgba(76, 98, 127, .38); border-radius: 16px;
            background: linear-gradient(110deg, rgba(17, 29, 46, .98), rgba(15, 27, 44, .96));
            padding: 1.2rem 1.35rem; margin-bottom: 1.15rem;
            box-shadow: 0 10px 28px rgba(0, 0, 0, .12);
        }
        .cg-page-head p { margin: .28rem 0 0; color: #b8c7d9; font-size: 1rem; line-height: 1.5; }
        .cg-status { display: inline-flex; align-items: center; gap: .4rem; border-radius: 99px; padding: .28rem .65rem; font-weight: 700; font-size: .8rem; }
        .cg-status.high { color: #fca5a5; background: rgba(239, 68, 68, .14); }
        .cg-status.medium { color: #fcd34d; background: rgba(245, 158, 11, .14); }
        .cg-status.low, .cg-status.online { color: #6ee7b7; background: rgba(16, 185, 129, .14); }
        .cg-table { border-collapse: collapse; width: 100%; font-size: .9rem; color: #edf2f7; }
        .cg-table th { text-align: left; color: #e2e8f0; background: rgba(30, 51, 74, .9); font-weight: 700; }
        .cg-table th, .cg-table td { border: 1px solid rgba(100, 135, 170, .17); padding: .67rem .72rem; }
        .cg-table tr:nth-child(even) td { background: rgba(20, 38, 57, .33); }
        .cg-table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 10px; }
        .cg-callout { border: 1px solid rgba(52, 211, 153, .24); border-radius: 11px; background: rgba(16, 185, 129, .075); padding: .8rem .95rem; color: #c9f5e4; line-height: 1.55; }
        .cg-kicker { text-transform: uppercase; letter-spacing: .11em; color: var(--mint); font-size: .69rem; font-weight: 800; }
        .cg-node { border: 1px solid #2589dd; border-radius: 12px; padding: .8rem .55rem; text-align: center; color: #eaf4ff; background: rgba(24, 94, 150, .2); font-weight: 650; min-height: 56px; display: flex; align-items: center; justify-content: center; }
        .cg-node.context { border-color: #2dd4bf; background: rgba(45, 212, 191, .12); }
        .cg-node.estimated { border-color: #a855f7; background: rgba(168, 85, 247, .13); }
        .cg-node.outcome { border-color: var(--red); background: rgba(239, 68, 68, .14); }
        .cg-legend { display: flex; flex-wrap: wrap; gap: .6rem 1.2rem; color: #cbd5e1; font-size: .8rem; }
        .cg-dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: .35rem; }
        .cg-foot { color: #b9c7d8; font-size: .75rem; margin-top: .7rem; line-height: 1.5; }
        .cg-callout { color: #e2f7ef; }
        .cg-status { font-size: .8rem; }
        .cg-section-heading {
            color: #f8fafc; font-size: 1.22rem; font-weight: 820;
            margin: .8rem 0 .28rem; padding-left: .72rem;
            border-left: 3px solid #34d399; letter-spacing: -.012em;
        }
        .cg-section-copy { color: #d3dfec; font-size: .98rem; line-height: 1.6; margin: 0 0 .9rem; }
        .cg-causal-hero {
            display: flex; align-items: center; justify-content: space-between; gap: 1rem;
            padding: 1.15rem 1.35rem; margin: .15rem 0 1rem; border-radius: 16px;
            border: 1px solid rgba(52, 211, 153, .3);
            background: radial-gradient(ellipse at 5% 5%, rgba(16, 185, 129, .22), transparent 45%),
                        linear-gradient(120deg, rgba(18, 28, 43, .98), rgba(16, 24, 39, .96) 65%, rgba(25, 23, 42, .96));
            box-shadow: 0 14px 40px rgba(0, 0, 0, .22), 0 0 28px rgba(16, 185, 129, .08);
        }
        .cg-causal-hero-title { color: #fff; font-size: 1.45rem; font-weight: 850; margin-top: .2rem; }
        .cg-causal-hero-sub { color: #d1dbea; font-size: .95rem; line-height: 1.55; margin-top: .3rem; }
        .cg-causal-risk {
            min-width: 118px; text-align: center; border-radius: 13px; padding: .65rem .85rem;
            border: 1px solid rgba(251, 113, 133, .4); background: rgba(239, 68, 68, .12);
        }
        .cg-causal-risk span { display: block; color: #fecdd3; font-size: .9rem; font-weight: 750; }
        .cg-causal-risk strong { display: block; color: #fff; font-size: 1.65rem; line-height: 1.25; }
        .cg-causal-risk small { color: #d1dbea; font-size: .8rem; }
        .cg-causal-risk.medium { border-color: rgba(251, 191, 36, .45); background: rgba(245, 158, 11, .13); }
        .cg-causal-risk.medium span { color: #fde68a; }
        .cg-causal-risk.low { border-color: rgba(52, 211, 153, .42); background: rgba(16, 185, 129, .12); }
        .cg-causal-risk.low span { color: #a7f3d0; }
        .cg-causal-legend { display: flex; flex-wrap: wrap; gap: .6rem 1rem; color: #d8e2ef; font-size: .85rem; }
        .cg-causal-legend span { display: inline-flex; align-items: center; gap: .4rem; }
        .cg-causal-legend i { width: 11px; height: 11px; border-radius: 50%; display: inline-block; }
        .cg-causal-interpretation {
            color: #e8f4ff; font-size: .98rem; line-height: 1.7; padding: .9rem 1rem;
            border-left: 4px solid #34d399; border-radius: 0 10px 10px 0;
            background: rgba(16, 185, 129, .09); margin-top: .8rem;
        }
        [data-testid="stPlotlyChart"] { border-radius: 12px; }
        .cg-causal-legend { padding: .45rem .25rem .15rem; }
        .cg-alert-banner {
            border: 1px solid rgba(251, 191, 36, .38); border-radius: 15px;
            padding: 1.1rem 1.3rem; margin: .4rem 0 1rem;
            background: radial-gradient(ellipse at 8% 0%, rgba(245, 158, 11, .17), transparent 48%),
                        linear-gradient(115deg, #151c29, #101827);
            box-shadow: 0 9px 28px rgba(245, 158, 11, .08);
        }
        .cg-alert-banner.high { border-color: rgba(251, 113, 133, .55); box-shadow: 0 9px 30px rgba(239, 68, 68, .13); }
        .cg-alert-banner.medium { border-color: rgba(251, 191, 36, .5); }
        .cg-alert-banner.low { border-color: rgba(52, 211, 153, .45); }
        .cg-alert-overline { color: #fbbf24; font-size: .82rem; font-weight: 850; letter-spacing: .1em; }
        .cg-alert-banner.high .cg-alert-overline { color: #fda4af; }
        .cg-alert-banner.low .cg-alert-overline { color: #6ee7b7; }
        .cg-alert-title { color: #fff; font-size: 1.35rem; font-weight: 850; margin-top: .28rem; }
        .cg-alert-copy { color: #d8e2ef; font-size: 1rem; margin-top: .3rem; }
        .cg-alert-score { display: flex; flex-wrap: wrap; gap: .45rem; align-items: center; color: #f8fafc; font-weight: 800; margin-top: .7rem; }
        .cg-alert-score span { border-radius: 99px; padding: .25rem .55rem; font-size: .82rem; color: #e2e8f0; background: rgba(148, 163, 184, .15); }
        .cg-alert-status {
            padding: 1rem 1.2rem; margin: .55rem 0 1rem; border: 1px solid;
            border-radius: 14px; font-size: 1.35rem; font-weight: 850; letter-spacing: .015em;
        }
        .cg-alert-status.triggered { color: #ffe4e6; background: rgba(190, 24, 54, .2); border-color: rgba(251, 113, 133, .55); box-shadow: 0 8px 26px rgba(239, 68, 68, .1); }
        .cg-alert-status.safe { color: #d1fae5; background: rgba(6, 95, 70, .2); border-color: rgba(52, 211, 153, .4); }
        .cg-alert-status.required, .cg-alert-status.insufficient { color: #fef3c7; background: rgba(146, 64, 14, .2); border-color: rgba(251, 191, 36, .42); }
        [data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
        .stButton > button, .stDownloadButton > button {
            min-height: 2.65rem;
            border: 1px solid rgba(52, 211, 153, .38); border-radius: 11px;
            background: linear-gradient(100deg, #047857, #10b981); color: white;
            font-weight: 700; box-shadow: 0 6px 18px rgba(16, 185, 129, .12);
            transition: transform .18s ease, box-shadow .18s ease, filter .18s ease;
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            transform: translateY(-1px); border-color: #6ee7b7; color: white;
            box-shadow: 0 10px 24px rgba(16, 185, 129, .22); filter: brightness(1.06);
        }
        [data-baseweb="select"] > div,
        [data-baseweb="select"] div[role="combobox"],
        [data-baseweb="input"] > div {
            background: #101b2a !important;
            background-color: #101b2a !important;
            border-color: rgba(148, 163, 184, .34) !important;
            border-radius: 10px !important;
            color: #f1f5f9 !important;
        }
        [data-baseweb="select"] svg { fill: #cbd5e1 !important; }
        [data-baseweb="popover"] ul { background: #101b2a !important; }
        [data-baseweb="select"] > div:hover, [data-baseweb="input"] > div:focus-within {
            border-color: rgba(52, 211, 153, .7);
            box-shadow: 0 0 0 1px rgba(52, 211, 153, .22);
        }
        [data-testid="stFileUploaderDropzone"] {
            background: linear-gradient(120deg, rgba(16, 185, 129, .075), rgba(17, 28, 44, .94)) !important;
            border: 1px dashed rgba(52, 211, 153, .42) !important;
            border-radius: 13px !important;
        }
        [data-testid="stFileUploaderDropzone"] * { color: #e2e8f0 !important; }
        [data-testid="stFileUploaderDropzone"] button {
            background: rgba(16, 185, 129, .14) !important;
            border: 1px solid rgba(52, 211, 153, .42) !important;
            color: #ecfdf5 !important;
        }
        [data-testid="stSlider"] [role="slider"] { background: var(--mint); }
        [data-testid="stExpander"] {
            border: 1px solid var(--border); border-radius: 13px;
            background: linear-gradient(135deg, rgba(17, 28, 43, .86), rgba(12, 21, 34, .9));
        }
        [data-testid="stTabs"] [role="tab"] {
            color: #cbd5e1; font-size: .95rem; font-weight: 650;
            border-radius: 10px 10px 0 0; padding: .65rem .9rem;
        }
        [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            color: #a7f3d0; border-bottom-color: #34d399;
        }
        [data-testid="stPlotlyChart"] { border-radius: 13px; }
        [data-testid="stPlotlyChart"] .js-plotly-plot .xtick text,
        [data-testid="stPlotlyChart"] .js-plotly-plot .ytick text,
        [data-testid="stPlotlyChart"] .js-plotly-plot .legend text,
        [data-testid="stPlotlyChart"] .js-plotly-plot .gtitle,
        [data-testid="stPlotlyChart"] .js-plotly-plot .annotation-text {
            fill: #e2e8f0 !important;
        }
        [data-testid="stPlotlyChart"] .js-plotly-plot .legend text { font-size: 13px !important; }
        [data-testid="stPageLink"] a {
            border-radius: 10px; transition: background .18s ease, color .18s ease;
        }
        [data-testid="stPageLink"] a:hover { background: rgba(16, 185, 129, .13); }
        .cg-kicker { color: #67e8f9; }
        .cg-title {
            color: #f1f5f9; font-size: 1.12rem; font-weight: 720;
            letter-spacing: -.012em; margin-bottom: .8rem;
        }
        .cg-subtitle { color: #b5c4d8; font-size: .95rem; line-height: 1.5; }
        .cg-section-heading {
            border-left-color: #22d3ee;
            font-size: 1.2rem;
            margin-top: .6rem;
        }
        .cg-section-copy { color: #b7c5d8; }
        .cg-callout {
            border-color: rgba(34, 211, 238, .24);
            background: linear-gradient(110deg, rgba(34, 211, 238, .07), rgba(17, 29, 46, .6));
            color: #d9f7fb;
        }
        .cg-causal-hero {
            border-color: rgba(45, 212, 191, .28);
            background:
                radial-gradient(ellipse at 5% 5%, rgba(45, 212, 191, .12), transparent 46%),
                linear-gradient(120deg, #111d2e, #101b2d 65%, #151d30);
            box-shadow: 0 12px 32px rgba(0, 0, 0, .16);
        }
        .cg-causal-interpretation {
            border-left-color: #2dd4bf;
            background: rgba(45, 212, 191, .065);
        }
        .cg-table-wrap {
            border-color: rgba(76, 98, 127, .38);
            border-radius: 12px;
            background: rgba(12, 22, 36, .72);
            box-shadow: 0 8px 22px rgba(0, 0, 0, .1);
        }
        .cg-table {
            font-size: .92rem;
            line-height: 1.5;
        }
        .cg-table th {
            color: #eaf2fa;
            background: #17283e;
            letter-spacing: .01em;
        }
        .cg-table th, .cg-table td {
            border-color: rgba(88, 111, 139, .24);
            padding: .72rem .8rem;
        }
        .cg-table tr:nth-child(even) td { background: rgba(30, 48, 70, .3); }
        .cg-table tr:hover td { background: rgba(34, 211, 238, .055); }
        .cg-status {
            border: 1px solid transparent;
            padding: .3rem .68rem;
            font-size: .82rem;
        }
        .cg-status.high { color: #fecdd3; background: rgba(251, 113, 133, .13); border-color: rgba(251, 113, 133, .2); }
        .cg-status.medium { color: #fde68a; background: rgba(251, 191, 36, .12); border-color: rgba(251, 191, 36, .2); }
        .cg-status.low, .cg-status.online { color: #a7f3d0; background: rgba(52, 211, 153, .11); border-color: rgba(52, 211, 153, .2); }
        .cg-foot { color: #aebdd0; font-size: .82rem; line-height: 1.55; }
        .cg-legend, .cg-causal-legend { color: #c6d3e2; font-size: .88rem; }
        .cg-causal-legend { gap: .7rem 1.2rem; }
        .cg-alert-banner {
            box-shadow: 0 12px 30px rgba(0, 0, 0, .16);
            background:
                radial-gradient(ellipse at 8% 0%, rgba(251, 191, 36, .09), transparent 48%),
                linear-gradient(115deg, #111d2e, #101b2d);
        }
        .cg-alert-banner.high { box-shadow: 0 12px 30px rgba(0, 0, 0, .18); }
        .cg-alert-status { box-shadow: 0 10px 26px rgba(0, 0, 0, .14); }
        .stButton > button, .stDownloadButton > button {
            background: linear-gradient(110deg, #0f766e, #0e7490);
            border-color: rgba(45, 212, 191, .35);
            box-shadow: 0 5px 16px rgba(8, 145, 178, .12);
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            border-color: rgba(103, 232, 249, .68);
            box-shadow: 0 8px 20px rgba(8, 145, 178, .18);
        }
        .stButton > button:focus-visible, .stDownloadButton > button:focus-visible,
        [data-testid="stPageLink"] a:focus-visible {
            outline: 2px solid #67e8f9;
            outline-offset: 2px;
            box-shadow: 0 0 0 4px rgba(34, 211, 238, .14);
        }
        [data-baseweb="select"] > div,
        [data-baseweb="select"] div[role="combobox"],
        [data-baseweb="input"] > div {
            background: #101d30 !important;
            background-color: #101d30 !important;
            border-color: rgba(87, 111, 140, .45) !important;
        }
        [data-baseweb="select"] > div:hover,
        [data-baseweb="input"] > div:focus-within {
            border-color: rgba(34, 211, 238, .6) !important;
            box-shadow: 0 0 0 1px rgba(34, 211, 238, .16);
        }
        [data-baseweb="popover"] ul { background: #101d30 !important; }
        [data-testid="stFileUploaderDropzone"] {
            background: linear-gradient(120deg, rgba(34, 211, 238, .045), rgba(17, 29, 46, .94)) !important;
            border-color: rgba(87, 150, 171, .5) !important;
            border-radius: 13px !important;
        }
        [data-testid="stFileUploaderDropzone"] button {
            background: #14283a !important;
            border-color: rgba(45, 212, 191, .32) !important;
            box-shadow: none !important;
        }
        [data-testid="stExpander"] {
            border-color: rgba(76, 98, 127, .36);
            background: rgba(15, 27, 44, .72);
        }
        [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            color: #a5f3fc;
            border-bottom-color: #22d3ee;
        }
        [data-testid="stPlotlyChart"] {
            border: 1px solid rgba(76, 98, 127, .2);
            border-radius: 13px;
            background: rgba(10, 19, 32, .32);
            overflow: hidden;
        }
        [data-testid="stPlotlyChart"] .js-plotly-plot .xtick text,
        [data-testid="stPlotlyChart"] .js-plotly-plot .ytick text,
        [data-testid="stPlotlyChart"] .js-plotly-plot .legend text,
        [data-testid="stPlotlyChart"] .js-plotly-plot .gtitle,
        [data-testid="stPlotlyChart"] .js-plotly-plot .annotation-text {
            fill: #e5edf6 !important;
        }
        [data-testid="stDataFrame"] {
            border: 1px solid rgba(76, 98, 127, .38);
            border-radius: 12px;
            overflow: hidden;
        }
        video {
            border: 1px solid rgba(76, 98, 127, .35);
            border-radius: 12px;
            background: #050a12;
        }
        [data-testid="stProgress"] > div > div { background-color: #22d3ee; }
        [data-testid="stSlider"] [role="slider"] { border-color: #22d3ee; }
        hr { border-color: var(--border); }
        ::-webkit-scrollbar { width: 9px; height: 9px; }
        ::-webkit-scrollbar-track { background: #0b1422; }
        ::-webkit-scrollbar-thumb { background: #34465d; border-radius: 8px; }
        ::-webkit-scrollbar-thumb:hover { background: #4b7188; }
        @media (max-width: 900px) {
            .block-container { padding: 1rem .8rem 2rem; }
            .cg-page-head { align-items: flex-start; flex-direction: column; }
            .cg-causal-hero { align-items: flex-start; flex-direction: column; }
            [data-testid="stMetric"] { padding: .9rem; }
            .cg-page-head { padding: 1rem; }
            .cg-table th, .cg-table td { padding: .58rem .62rem; }
        }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after { scroll-behavior: auto !important; transition-duration: .01ms !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
