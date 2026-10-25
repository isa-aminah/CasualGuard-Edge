"""Upload, save, review, and run YOLO + ByteTrack on video clips."""

import sqlite3
from html import escape

import streamlit as st

from active_video import get_active_video, set_active_video
from app.components import event_selector, html_table, metric_table
from app.video_processing import MODEL_WEIGHTS, analyze_video
from app.video_views import render_video_pair
from navigation import page_header
from video_library import (
    MAX_VIDEO_BYTES,
    VideoLibraryError,
    analysis_is_current,
    delete_video,
    get_video,
    list_videos,
    record_analysis,
    save_video,
    source_path,
)

def render() -> None:
    page_header("Video Analysis", "Save clips for later, then detect pedestrians and track vehicles with YOLO + ByteTrack")

    with st.container(border=True):
        st.markdown("<div class='cg-title'>Video Library</div>", unsafe_allow_html=True)
        upload_col, save_col = st.columns([3, 1], vertical_alignment="bottom")
        with upload_col:
            uploaded = st.file_uploader(
                "Upload a video to the server library",
                type=["mp4", "mov", "avi", "mkv", "webm"],
                key="video_upload",
                help="Videos are saved on the application server and remain available in this library.",
            )
        with save_col:
            save_clicked = st.button(
                "Save video",
                type="primary",
                disabled=uploaded is None,
                use_container_width=True,
            )

        if save_clicked and uploaded is not None:
            if uploaded.size > MAX_VIDEO_BYTES:
                st.error("The video exceeds the 500 MB limit.")
            else:
                try:
                    video = save_video(uploaded.getvalue(), uploaded.name)
                    set_active_video(video["video_id"])
                    st.session_state["pending_shared_video_selection"] = video["video_id"]
                    st.success(f"Saved **{video['original_name']}** to the server video library.")
                    st.rerun()
                except VideoLibraryError as exc:
                    st.error(str(exc))
                except OSError as exc:
                    st.error(f"Could not save the video to server storage: {exc}")

        saved_videos = list_videos()
        st.caption(f"{len(saved_videos)} video(s) saved in the server library.")
        if saved_videos:
            active_video_id = get_active_video()
            video_ids = [video["video_id"] for video in saved_videos]
            selected_index = (
                video_ids.index(active_video_id)
                if active_video_id in video_ids
                else 0
            )
            selection_key = f"video_library_selection_{active_video_id or 'none'}"
            selected_library_id = st.selectbox(
                "Choose a saved video to use",
                options=video_ids,
                index=selected_index,
                format_func=lambda video_id: next(
                    video["original_name"]
                    for video in saved_videos
                    if video["video_id"] == video_id
                ),
                key=selection_key,
                help="Loading a saved clip makes it active across the dashboard, causal analysis, and other pages.",
            )
            if st.button(
                "Load selected video across pages",
                type="primary",
                use_container_width=True,
                key=f"load_saved_video_{active_video_id or 'none'}",
            ):
                set_active_video(selected_library_id)
                st.session_state["pending_shared_video_selection"] = selected_library_id
                st.rerun()

            with st.expander("Saved video library"):
                rows = [
                    [
                        escape(video["original_name"]),
                        escape(video["uploaded_at"][:19].replace("T", " ") + " UTC"),
                        f"{video['size_bytes'] / (1024 * 1024):.1f} MB",
                        "Analyzed" if video["processed_filename"] else "Not analyzed",
                    ]
                    for video in saved_videos
                ]
                st.markdown(
                    html_table(["Video", "Saved", "Size", "Analysis"], rows),
                    unsafe_allow_html=True,
                )

        selected_video_id = get_active_video()
        selected_video = get_video(selected_video_id) if selected_video_id else None
        if selected_video is None:
            st.info("Upload and save a clip here. Saved videos can then be selected from the shared sidebar menu.")
        else:
            st.caption(
                f"Selected: **{selected_video['original_name']}** · "
                f"saved {selected_video['uploaded_at'][:19].replace('T', ' ')} UTC"
            )
            with st.expander("Delete saved video"):
                st.warning(
                    "Deleting permanently removes this original clip, its annotated video, "
                    "and all saved analysis for this video."
                )
                confirmed = st.checkbox(
                    f"I understand this permanently deletes {selected_video['original_name']}.",
                    key=f"confirm_delete_{selected_video_id}",
                )
                delete_clicked = st.button(
                    "Delete video and analysis",
                    disabled=not confirmed,
                    key=f"delete_video_{selected_video_id}",
                    use_container_width=True,
                )
                if delete_clicked:
                    try:
                        delete_video(selected_video_id)
                        set_active_video(None)
                        st.session_state.pop("active_event_id", None)
                        st.session_state.pop("video_library_selection", None)
                        st.session_state.pop(
                            f"video_library_selection_{selected_video_id}", None
                        )
                        st.success(
                            f"Deleted **{selected_video['original_name']}** and its saved analysis."
                        )
                        st.rerun()
                    except VideoLibraryError as exc:
                        st.error(str(exc))
                    except sqlite3.Error as exc:
                        st.error(f"Could not remove the video record from the library: {exc}")
                    except OSError as exc:
                        st.error(f"Could not delete the saved video files: {exc}")

    event_id, event = event_selector()
    video_col, details_col = st.columns([2.15, .95], gap="large")
    with video_col:
        with st.container(border=True):
            if selected_video:
                has_analysis = analysis_is_current(selected_video, MODEL_WEIGHTS)
                render_video_pair(selected_video)

                if has_analysis:
                    st.success(
                        f"Tracked with **{selected_video['model_name']}** and ByteTrack · "
                        f"{selected_video['frames_processed']:,} frames"
                    )
                    count_cols = st.columns(4)
                    count_cols[0].metric("Pedestrian tracks", selected_video["pedestrian_tracks"])
                    count_cols[1].metric("Vehicle tracks", selected_video["vehicle_tracks"])
                    count_cols[2].metric("Person detections", selected_video["pedestrian_detections"])
                    count_cols[3].metric("Vehicle detections", selected_video["vehicle_detections"])
                else:
                    st.caption(
                        "Detections are filtered to people, cars, motorcycles, buses, and trucks. "
                        "Each annotated frame includes ByteTrack IDs."
                    )

                analyze_clicked = st.button(
                    "Run YOLO + ByteTrack",
                    type="primary",
                    use_container_width=True,
                    key=f"analyze_{selected_video_id}",
                )
                if analyze_clicked:
                    progress = st.progress(0, text="Preparing video analysis…")
                    try:
                        result = analyze_video(
                            source_path(selected_video),
                            selected_video_id,
                            progress_callback=lambda value, text: progress.progress(value, text=text),
                        )
                        record_analysis(selected_video_id, result)
                        st.success("Detection and tracking finished. The annotated video is saved in your library.")
                        st.rerun()
                    except (ImportError, ModuleNotFoundError) as exc:
                        st.error(
                            "YOLO video dependencies are not installed. Install the project requirements "
                            "with `python -m pip install -r requirements.txt`, then restart Streamlit."
                        )
                        st.exception(exc)
                    except Exception as exc:
                        st.error(f"Video analysis failed: {exc}")
                        st.caption("Check that the source clip is readable, the model weights are available, and the server can write to its data directory.")
            else:
                st.info("Upload and save a video to run person and vehicle detection with YOLO + ByteTrack.")

    with details_col:
        with st.container(border=True):
            st.markdown(f"<div class='cg-title'>Event Details · {event_id or '—'}</div>", unsafe_allow_html=True)
            if event:
                st.markdown(metric_table(event, include_location=True), unsafe_allow_html=True)
            elif selected_video and analysis_is_current(selected_video, MODEL_WEIGHTS):
                st.info("No pedestrian-vehicle interactions met the close-approach threshold for this video.")
            elif selected_video:
                st.info("Run YOLO + ByteTrack to calculate event metrics from the selected video.")
            else:
                st.info("Event metrics appear here after a saved video is analyzed.")
            if selected_video and selected_video["processed_at"]:
                st.caption(f"Last processed: {selected_video['processed_at'][:19].replace('T', ' ')} UTC")

if __name__ == "__main__":
    render()
