# streamlit_app.py
import streamlit as st
from yt_dlp import YoutubeDL
import tempfile, os, shutil, time
from pathlib import Path

st.set_page_config(
    page_title="YouTube Downloader — Pro",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ---------- Sidebar ----------
with st.sidebar:
    st.image("https://static.streamlit.io/examples/dice.jpg", width=200)
    st.markdown("### YouTube Downloader (Pro UI)")
    st.markdown("Convert & download videos or audio from YouTube.\n\n**Use responsibly — respect copyrights.**")
    st.markdown("---")
    st.markdown("**Tips**")
    st.markdown("- For audio, choose MP3 or M4A.\n- Larger videos take longer to process.")
    st.markdown("---")
    st.caption("Built with Streamlit & yt-dlp")

# ---------- Main UI ----------
st.title("🎬 YouTube Downloader — Pro UI")
st.write("Paste a YouTube link, choose format & quality, then click **Download**.")

col1, col2 = st.columns([3,1])
with col1:
    url = st.text_input("Enter YouTube video URL", placeholder="https://www.youtube.com/watch?v=...")
with col2:
    st.write("")  # spacing
    submit = st.button("Fetch")

st.markdown("---")
# Options
format_choice = st.selectbox("Format", ["mp4 (video)", "m4a (audio)", "mp3 (audio)"], index=0)
quality = st.selectbox("Preferred quality", ["best", "720p", "480p", "360p", "audio-only"], index=0)
filename_override = st.text_input("Optional: Save file as (without extension)", value="")

# Progress and logs
progress_bar = st.progress(0)
status = st.empty()
log_area = st.empty()

# helper to update status/log
def log(msg, progress=None):
    timestamp = time.strftime("%H:%M:%S")
    log_area.text_area("App log", value=f"[{timestamp}] {msg}\n" + (log_area._value if hasattr(log_area, "_value") else ""), height=200)
    if progress is not None:
        progress_bar.progress(min(max(int(progress), 0), 100))

# download function
def download_with_ytdlp(url, outdir, outtmpl, choice_format, quality_pref):
    # Build yt-dlp options
    ydl_opts = {
        "outtmpl": str(Path(outdir) / outtmpl),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    # Format selection
    if choice_format.startswith("mp4"):
        # video bestvideo+bestaudio or best
        if quality_pref == "best":
            ydl_opts["format"] = "bestvideo+bestaudio/best"
        elif quality_pref == "audio-only":
            ydl_opts["format"] = "bestaudio/best"
        else:
            # try to map 720p etc.
            if quality_pref.endswith("p"):
                ydl_opts["format"] = f"bestvideo[height<={quality_pref.replace('p','')}] + bestaudio/best"
            else:
                ydl_opts["format"] = "bestvideo+bestaudio/best"
    else:
        # audio formats
        if choice_format.startswith("m4a"):
            ydl_opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
        else:  # mp3 request - download audio then convert
            ydl_opts["format"] = "bestaudio/best"
            # try to convert to mp3 via postprocessor (requires ffmpeg)
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]

    # progress hook to track events
    def _hook(d):
        if d.get("status") == "downloading":
            downloaded = d.get("downloaded_bytes", 0) or 0
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            if total:
                pct = int(downloaded / total * 100)
                log(f"Downloading: {d.get('filename', '')} ({pct}%)", progress=pct)
            else:
                log(f"Downloading: {d.get('filename', '')} ...", progress=10)
        elif d.get("status") == "finished":
            log("Download finished, processing...", progress=90)

    ydl_opts["progress_hooks"] = [_hook]

    # Run download
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # determine final path
            filename = ydl.prepare_filename(info)
            # if postprocessor changed extension (mp3), adjust name
            if choice_format.startswith("mp3"):
                # check common mp3 path
                base = os.path.splitext(filename)[0]
                mp3candidate = base + ".mp3"
                if os.path.exists(mp3candidate):
                    filename = mp3candidate
            return filename, None
    except Exception as e:
        return None, str(e)

# When Fetch pressed, preview metadata
if submit and url:
    status.info("Fetching video info...")
    progress_bar.progress(5)
    try:
        # minimal info extraction
        with YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            meta = ydl.extract_info(url, download=False)
        st.markdown("### Video information")
        st.write("**Title:**", meta.get("title"))
        st.write("**Uploader:**", meta.get("uploader"))
        st.write("**Duration:**", f"{int(meta.get('duration',0)) // 60} min {int(meta.get('duration',0)) % 60} sec")
        if meta.get("view_count") is not None:
            st.write("**Views:**", f"{meta.get('view_count'):,}")
        st.markdown("---")
        # show thumbnail
        if meta.get("thumbnail"):
            st.image(meta.get("thumbnail"), width=360)
        status.success("Info loaded. Choose options and click Download below.")
    except Exception as e:
        status.error("Could not fetch info: " + str(e))
        log(f"Info fetch error: {e}", progress=0)

# Download button area
st.markdown("---")
download_col1, download_col2 = st.columns([3,1])

with download_col1:
    if st.button("Download now"):
        if not url:
            st.error("Please paste a YouTube URL first.")
        else:
            status.info("Starting download...")
            progress_bar.progress(1)
            tmpdir = tempfile.mkdtemp()
            try:
                # create safe output template
                safe_name = filename_override.strip() or "%(title)s.%(ext)s"
                # use yt-dlp to download
                outpath, err = download_with_ytdlp(url, tmpdir, safe_name, format_choice, quality)
                if err:
                    status.error("Download failed: " + err)
                    log("Error: " + err, progress=0)
                else:
                    status.success("Download & processing complete.")
                    progress_bar.progress(100)
                    # send file for download
                    if outpath and os.path.exists(outpath):
                        st.markdown("**Ready to download:**")
                        with open(outpath, "rb") as f:
                            data = f.read()
                            ext = Path(outpath).suffix.lower().lstrip(".")
                            suggested_name = Path(outpath).name
                            # streamlit download button
                            st.download_button(
                                label=f"Download file ({suggested_name})",
                                data=data,
                                file_name=suggested_name,
                                mime="application/octet-stream",
                            )
                    else:
                        status.error("File not found after processing.")
            except Exception as e:
                status.error("Unexpected error: " + str(e))
                log("Unexpected error: " + str(e), progress=0)
            finally:
                # cleanup temporary files after a short delay so user can download
                # NOTE: We will keep files for now to allow download; optionally remove after
                pass

with download_col2:
    st.write("")
    st.write("")
    st.write("")
    st.caption("Pro UI ready")

st.markdown("---")
st.caption("By using this app you agree to follow YouTube's Terms of Service.")
