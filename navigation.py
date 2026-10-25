"""Custom application rail and shared page-header components."""

from __future__ import annotations

import streamlit as st

from active_video import get_active_video, initialize, set_active_video
from video_library import list_videos


def render_sidebar(pages: dict[str, st.Page]) -> None:
    """Render the brand rail and links to the registered Streamlit pages."""
    initialize()
    with st.sidebar:
        st.markdown(
            """
            <div style="padding:.35rem .4rem 1.1rem">
              <div style="display:flex;gap:.65rem;align-items:center">
                <div style="font-size:1.8rem;color:#34d399">◈</div>
                <div class="cg-brand">CAUSAL<span>GUARD-EDGE</span></div>
              </div>
              <div class="cg-brand-sub">Pedestrian - Vehicle Near-Miss Monitoring &amp; Causal Analysis</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        videos = list_videos()
        if videos:
            options = {video["video_id"]: video for video in videos}
            active_id = get_active_video()
            pending_video_id = st.session_state.pop(
                "pending_shared_video_selection", None
            )
            if pending_video_id in options:
                active_id = pending_video_id
                st.session_state["shared_video_selector"] = pending_video_id
                set_active_video(pending_video_id)
            if active_id not in options:
                active_id = videos[0]["video_id"]
                set_active_video(active_id)
            if st.session_state.get("shared_video_selector") not in options:
                st.session_state["shared_video_selector"] = active_id
            selected_id = st.selectbox(
                "Active video",
                options=list(options),
                format_func=lambda video_id: options[video_id]["original_name"],
                key="shared_video_selector",
            )
            set_active_video(selected_id)
            st.markdown("<div class='cg-foot'>The selected video is shared across analysis pages.</div>", unsafe_allow_html=True)
        st.markdown("<div class='cg-kicker' style='padding:.25rem .55rem .55rem'>Monitoring</div>", unsafe_allow_html=True)
        links = (
            ("Dashboard", ":material/home:"),
            ("Video Analysis", ":material/videocam:"),
            ("Causal Analysis", ":material/account_tree:"),
            ("Counterfactual Analysis", ":material/hub:"),
            ("Alert Status", ":material/notifications:"),
        )
        for title, icon in links:
            st.page_link(pages[title], label=title, icon=icon)
        st.markdown(
            """
            <div style="margin:1.25rem .45rem 0;color:#cbd5e1;font-size:.8rem">
              <span style="color:#10b981">●</span> System Online
              <div style="color:#73849b;font-size:.7rem;margin-top:.25rem">EDGE NODE · LOCAL MONITORING</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def page_header(title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="cg-page-head">
          <div><h1>{title}</h1><p>{description}</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
