import os
import shutil
import subprocess
import sys
import tempfile
import time
from typing import List, Optional


VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".webm"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".gif"}
FRAME_STRIDE = 15


def which_or_exit(cmd: str) -> str:
    path = shutil.which(cmd)
    if not path:
        print(f"Error: '{cmd}' not found on PATH. Please install it and try again.")
        sys.exit(1)
    return path


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def clear_dir(path: str) -> None:
    if not os.path.isdir(path):
        return
    for entry in os.scandir(path):
        if entry.is_dir():
            shutil.rmtree(entry.path)
        else:
            os.remove(entry.path)


def list_files(folder: str, exts: set) -> List[str]:
    if not os.path.isdir(folder):
        return []
    files = [
        entry.path
        for entry in os.scandir(folder)
        if entry.is_file() and os.path.splitext(entry.name)[1].lower() in exts
    ]
    return sorted(files, key=lambda p: os.path.basename(p).lower())


def parse_fps(value: str) -> float:
    value = value.strip()
    if "/" in value:
        num, den = value.split("/", 1)
        try:
            den_val = float(den)
            return float(num) / den_val if den_val != 0 else 0.0
        except ValueError:
            return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def estimate_frames(ffprobe_path: Optional[str], video_path: str) -> int:
    if not ffprobe_path:
        return 0
    cmd = [
        ffprobe_path,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=avg_frame_rate,duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        return 0
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(lines) < 2:
        return 0
    fps = parse_fps(lines[0])
    try:
        duration = float(lines[1])
    except ValueError:
        return 0
    if fps <= 0 or duration <= 0:
        return 0
    total = int(round(fps * duration))
    if FRAME_STRIDE > 1:
        return max(1, int(round(total / FRAME_STRIDE)))
    return total


def count_frames(folder: str) -> int:
    count = 0
    try:
        with os.scandir(folder) as it:
            for entry in it:
                if entry.is_file() and entry.name.lower().startswith("frame_") and entry.name.lower().endswith(".png"):
                    count += 1
    except FileNotFoundError:
        return 0
    return count


def list_frame_files(folder: str) -> set:
    if not os.path.isdir(folder):
        return set()
    names = set()
    with os.scandir(folder) as it:
        for entry in it:
            if not entry.is_file():
                continue
            name = entry.name
            lname = name.lower()
            if lname.startswith("frame_") and lname.endswith(".png"):
                names.add(name)
    return names


def max_frame_number(folder: str) -> int:
    max_num = 0
    try:
        with os.scandir(folder) as it:
            for entry in it:
                if not entry.is_file():
                    continue
                name = entry.name.lower()
                if not (name.startswith("frame_") and name.endswith(".png")):
                    continue
                digits = name[6:12]
                if len(digits) != 6 or not digits.isdigit():
                    continue
                num = int(digits)
                if num > max_num:
                    max_num = num
    except FileNotFoundError:
        return 0
    return max_num


def count_frames_from(folder: str, start_number: int) -> int:
    count = 0
    try:
        with os.scandir(folder) as it:
            for entry in it:
                if not entry.is_file():
                    continue
                name = entry.name.lower()
                if not (name.startswith("frame_") and name.endswith(".png")):
                    continue
                digits = name[6:12]
                if len(digits) != 6 or not digits.isdigit():
                    continue
                num = int(digits)
                if num >= start_number:
                    count += 1
    except FileNotFoundError:
        return 0
    return count


def remove_frames_from(folder: str, start_number: int) -> None:
    if not os.path.isdir(folder):
        return
    with os.scandir(folder) as it:
        for entry in it:
            if not entry.is_file():
                continue
            name = entry.name.lower()
            if not (name.startswith("frame_") and name.endswith(".png")):
                continue
            digits = name[6:12]
            if len(digits) != 6 or not digits.isdigit():
                continue
            num = int(digits)
            if num >= start_number:
                os.remove(entry.path)


def remove_new_frames(folder: str, preexisting: set) -> None:
    if not os.path.isdir(folder):
        return
    with os.scandir(folder) as it:
        for entry in it:
            if not entry.is_file():
                continue
            name = entry.name
            lname = name.lower()
            if not (lname.startswith("frame_") and lname.endswith(".png")):
                continue
            if name not in preexisting:
                os.remove(entry.path)


def progress_bar(percent: int, width: int = 28) -> str:
    fill = int((percent / 100) * width)
    return "[" + "#" * fill + "-" * (width - fill) + "]"


def render_progress(activity: str, status: str, percent: Optional[int]) -> None:
    if percent is None:
        line = f"{activity}: {status} ..."
    else:
        line = f"{activity}: {status} {progress_bar(percent)} {percent:3d}%"
    sys.stdout.write("\r" + line)
    sys.stdout.flush()


def run_ffmpeg_with_progress(
    ffmpeg_path: str,
    args: List[str],
    activity: str,
    status: str,
    progress_dir: str,
    estimated_frames: int,
    start_number: int,
    use_hwaccel: bool,
) -> tuple:
    log_path = tempfile.mkstemp(prefix="ffmpeg_extract_", suffix=".log")[1]
    log_file = open(log_path, "w", encoding="utf-8", errors="ignore")
    cmd = [ffmpeg_path]
    if use_hwaccel:
        cmd += ["-hwaccel", "auto"]
    cmd += args

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=log_file)
    while proc.poll() is None:
        if estimated_frames > 0:
            current = count_frames_from(progress_dir, start_number)
            percent = min(99, int((current / estimated_frames) * 100))
        else:
            percent = None
        render_progress(activity, status, percent)
        time.sleep(0.5)

    proc.wait()
    log_file.close()
    if estimated_frames > 0:
        render_progress(activity, status, 100)
    else:
        render_progress(activity, status, None)
    sys.stdout.write("\n")
    sys.stdout.flush()
    return proc.returncode, log_path


def run_ffmpeg_simple(ffmpeg_path: str, args: List[str]) -> tuple:
    log_path = tempfile.mkstemp(prefix="ffmpeg_extract_", suffix=".log")[1]
    log_file = open(log_path, "w", encoding="utf-8", errors="ignore")
    cmd = [ffmpeg_path] + args
    code = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=log_file).returncode
    log_file.close()
    return code, log_path


def tail_log(path: str, max_lines: int = 20) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.read().splitlines()
        if not lines:
            return ""
        return "\n".join(lines[-max_lines:])
    except OSError:
        return ""


def run_ffmpeg_with_fallback(
    ffmpeg_path: str,
    args: List[str],
    activity: str,
    status: str,
    progress_dir: Optional[str],
    estimated_frames: int,
    start_number: int,
) -> int:
    last_log = None
    preexisting = list_frame_files(progress_dir) if progress_dir else set()
    if progress_dir:
        code, last_log = run_ffmpeg_with_progress(
            ffmpeg_path,
            args,
            activity,
            status,
            progress_dir,
            estimated_frames,
            start_number,
            use_hwaccel=True,
        )
    else:
        code, last_log = run_ffmpeg_simple(ffmpeg_path, ["-hwaccel", "auto"] + args)

    if code == 0:
        if last_log and os.path.exists(last_log):
            try:
                os.remove(last_log)
            except OSError:
                pass
        return 0

    print("ffmpeg hardware acceleration failed; retrying without GPU...")

    if progress_dir:
        remove_new_frames(progress_dir, preexisting)
        code, last_log = run_ffmpeg_with_progress(
            ffmpeg_path,
            args,
            activity,
            status,
            progress_dir,
            estimated_frames,
            start_number,
            use_hwaccel=False,
        )
    else:
        code, last_log = run_ffmpeg_simple(ffmpeg_path, args)

    if code != 0 and last_log:
        tail = tail_log(last_log)
        if tail:
            print("ffmpeg error output (last lines):")
            print(tail)
        if os.path.exists(last_log):
            try:
                os.remove(last_log)
            except OSError:
                pass
    elif last_log and os.path.exists(last_log):
        try:
            os.remove(last_log)
        except OSError:
            pass
    return code


def main() -> int:
    root = os.getcwd()
    videos_dir = os.path.join(root, "Videos")
    images_dir = os.path.join(root, "Images")
    output_dir = os.path.join(root, "Extracted Frames")

    ffmpeg_path = which_or_exit("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")

    # Create expected folders so a fresh checkout can run without manual setup.
    ensure_dir(videos_dir)
    ensure_dir(images_dir)
    ensure_dir(output_dir)
    skip_clear = "--no-clear" in sys.argv
    if not skip_clear:
        clear_dir(output_dir)
    else:
        print("Skipping clear of Extracted Frames (resume mode).")

    videos = list_files(videos_dir, VIDEO_EXTS)
    images = list_files(images_dir, IMAGE_EXTS)

    print(f"Found {len(videos)} video(s) and {len(images)} image(s).")

    if skip_clear:
        counter = max_frame_number(output_dir) + 1
    else:
        counter = 1

    for video in videos:
        base_name = os.path.basename(video)
        print(f"Extracting frames from: {base_name}")
        estimated = estimate_frames(ffprobe_path, video)
        output_pattern = os.path.join(output_dir, "frame_%06d.png")
        start_number = counter
        args = [
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            video,
            "-vf",
            f"select=not(mod(n\\,{FRAME_STRIDE}))",
            "-vsync",
            "vfr",
            "-start_number",
            str(start_number),
            output_pattern,
        ]
        exit_code = run_ffmpeg_with_fallback(
            ffmpeg_path,
            args,
            "Extracting frames",
            base_name,
            output_dir,
            estimated,
            start_number,
        )
        if exit_code != 0:
            print("ffmpeg failed extracting frames from:", base_name)
            return 1

        after_count = count_frames(output_dir)
        extracted = max(0, after_count - (start_number - 1))
        print(f"Extracted {extracted} frame(s) from {base_name}.")
        counter = after_count + 1

    total_images = len(images)
    for idx, image in enumerate(images, start=1):
        dest_name = f"frame_{counter:06d}.png"
        dest_path = os.path.join(output_dir, dest_name)
        print(f"Converting image: {os.path.basename(image)} -> {dest_name}")
        args = ["-hide_banner", "-loglevel", "error", "-y", "-i", image, dest_path]
        code, log_path = run_ffmpeg_simple(ffmpeg_path, args)
        if code != 0:
            print("ffmpeg failed converting image:", os.path.basename(image))
            tail = tail_log(log_path)
            if tail:
                print("ffmpeg error output (last lines):")
                print(tail)
            if os.path.exists(log_path):
                try:
                    os.remove(log_path)
                except OSError:
                    pass
            return 1
        if os.path.exists(log_path):
            try:
                os.remove(log_path)
            except OSError:
                pass
        counter += 1
        percent = int((idx / total_images) * 100) if total_images else 100
        render_progress("Converting images", os.path.basename(image), percent)
    if total_images:
        sys.stdout.write("\n")
        sys.stdout.flush()

    if not videos and not images:
        print("No videos or images found. Nothing to do.")
    else:
        print(f"Done. Total output files: {counter - 1}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
