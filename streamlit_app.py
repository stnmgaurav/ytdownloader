import streamlit as st
from yt_dlp import YoutubeDL
import os, time, tempfile
from pathlib import Path

# ======================= PAGE CONFIG ==========================
st.set_page_config(
    page_title="YouTube Downloader — Pro UI",
    page_icon="🎬",
    layout="centered",
)

# ======================= SIDEBAR UI ===========================
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/0/09/YouTube_full-color_icon_%282017%29.svg",
        width=120
    )
    st.markdown("## 🎬 YouTube Downloader — Pro")
    st.write("Fast • Clean • Modern UI")

    st.markdown("---")
    st.markdown("**Tips**")
    st.markdown("• MP3 download requires ffmpeg\n• Big videos take time\n• Don’t download copyrighted content")
    st.markdown("---")
    st.caption("Powered by Streamlit + yt-dlp")

# ======================= MAIN TITLE ===========================
st.title("🎥 YouTube Downloader — Pro UI")
st.write("Paste a link, choose quality, download instantly.")

# ======================= INPUT AREA ===========================
url = st.text_input("Enter YouTube URL", placeholder="https://youtu.be/xyz12345")

format_choice = st.selectbox("Format", ["MP4 (Video)", "M4A (Audio)", "MP3 (Audio)"])
quality = st.selectbox("Quality", ["Best", "1080p", "720p", "480p", "360p", "Audio Only"])

filename_override = st.text_input("Save file as (optional, without extension)")

progress_bar = st.progress(0)
log_box = st.empty()
status_box = st.empty()


# ======================= LOG FUNCTION ===========================
def log(msg, p=None):
    t = time.strftime("%H:%M:%S")
    log_box.text(f"[{t}] {msg}")
    if p is not None:
        progress_bar.progress(min(max(int(p), 0), 100))


# ======================= DOWNLOAD FUNCTION ===========================
def download_video(url, outdir, template, fmt, quality_pref):
    ydl_opts = {
        "outtmpl": str(Path(outdir) / template),
        "quiet": True,
        "noplaylist": True,
        "no_warnings": True,
    }

    # ------------ FORMAT ------------
    if fmt.startswith("MP4"):
        if quality_pref == "Best":
            ydl_opts["format"] = "bestvideo+bestaudio/best"
        elif quality_pref == "Audio Only":
            ydl_opts["format"] = "bestaudio/best"
        elif quality_pref.endswith("p"):
            height = quality_pref.replace("p", "")
            ydl_opts["format"] = f"bestvideo[height<={height}]+bestaudio/best"
        else:
            ydl_opts["format"] = "best"
    elif fmt.startswith("M4A"):
        ydl_opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
    elif fmt.startswith("MP3"):
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]

    # ------------ PROGRESS HOOK ------------
    def hook(d):
        if d["status"] == "downloading":
            if d.get("total_bytes"):
                pct = d["downloaded_bytes"] / d["total_bytes"] * 100
                log("Downloading...", pct)
        elif d["status"] == "finished":
            log("Download finished. Processing...", 90)

    ydl_opts["progress_hooks"] = [hook]

    # ------------ RUN DOWNLOAD ------------
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)

            if fmt.startswith("MP3"):
                base = os.path.splitext(path)[0]
                mp3_path = base + ".mp3"
                if os.path.exists(mp3_path):
                    path = mp3_path

            return path, None
    except Exception as e:
        return None, str(e)


# ======================= DOWNLOAD BUTTON ===========================
st.markdown("---")
if st.button("⬇ Download Now", use_container_width=True):
    if not url.strip():
        st.error("Please enter a YouTube URL.")
    else:
        status_box.info("Starting...")
        tmp = tempfile.mkdtemp()
        safe_name = filename_override.strip() or "%(title)s.%(ext)s"

        outpath, err = download_video(url, tmp, safe_name, format_choice, quality)

        if err:
            status_box.error("Failed: " + err)
            log("Error: " + err)
        else:
            status_box.success("Download ready!")
            progress_bar.progress(100)

            with open(outpath, "rb") as f:
                st.download_button(
                    label=f"Download File ({Path(outpath).name})",
                    data=f.read(),
                    file_name=Path(outpath).name,
                    mime="application/octet-stream",
                    use_container_width=True
                )

st.caption("© Pro UI — YouTube Downloader")
