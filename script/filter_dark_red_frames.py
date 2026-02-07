import os
import sys
from typing import List

try:
    import cv2
    import numpy as np
except ImportError as exc:
    print("Error: OpenCV (cv2) and numpy are required. Please install them first.")
    print("Example: pip install opencv-python numpy")
    raise SystemExit(1) from exc


INPUT_DIR = "Extracted Frames"
OUTPUT_DIR = "Post-Processed"

# Target maroon-ish colors derived from provided hex values.
# We compute HSV from the sample colors and then apply a margin.
SAMPLE_HEX = ["#7c194f", "#542843", "#85233c", "#4f0e2e"]
H_MARGIN = 4
S_MARGIN = 30
V_MARGIN = 30

def hex_to_bgr(hex_color: str) -> np.ndarray:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return np.array([[[b, g, r]]], dtype=np.uint8)

def compute_hsv_range(sample_hex: str) -> tuple:
    bgr = hex_to_bgr(sample_hex)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[0][0]
    h, s, v = int(hsv[0]), int(hsv[1]), int(hsv[2])
    h_min = max(0, h - H_MARGIN)
    h_max = min(179, h + H_MARGIN)
    s_min = max(0, s - S_MARGIN)
    s_max = min(255, s + S_MARGIN)
    v_min = max(0, v - V_MARGIN)
    v_max = min(255, v + V_MARGIN)
    return (np.array([h_min, s_min, v_min]), np.array([h_max, s_max, v_max]))

RANGES = [compute_hsv_range(hx) for hx in SAMPLE_HEX]

# Minimum number of matching pixels to keep a frame (total across all ranges)
MIN_PIXELS = 1000
# Minimum connected pixel cluster size to keep colored
MIN_CLUSTER_PIXELS = 500


def list_frames(folder: str) -> List[str]:
    if not os.path.isdir(folder):
        return []
    exts = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
    files = [
        entry.path
        for entry in os.scandir(folder)
        if entry.is_file() and os.path.splitext(entry.name)[1].lower() in exts
    ]
    return sorted(files, key=lambda p: os.path.basename(p).lower())


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def main() -> int:
    root = os.getcwd()
    input_dir = os.path.join(root, INPUT_DIR)
    output_dir = os.path.join(root, OUTPUT_DIR)

    # Always create the output folder so the workflow is consistent on a fresh checkout.
    ensure_dir(output_dir)

    if not os.path.isdir(input_dir):
        print(f"Input folder not found: {input_dir}")
        return 1

    frames = list_frames(input_dir)
    print(f"Scanning {len(frames)} frame(s) in: {input_dir}")

    kept = 0
    processed = 0

    for path in frames:
        processed += 1
        img = cv2.imread(path)
        if img is None:
            print(f"Warning: Could not read {os.path.basename(path)}")
            continue

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask = None
        for lower, upper in RANGES:
            m = cv2.inRange(hsv, lower, upper)
            mask = m if mask is None else cv2.bitwise_or(mask, m)

        total_matches = cv2.countNonZero(mask)
        if total_matches < MIN_PIXELS:
            continue

        # Keep only sufficiently large connected regions
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        filtered_mask = np.zeros_like(mask)
        for label in range(1, num_labels):
            area = stats[label, cv2.CC_STAT_AREA]
            if area >= MIN_CLUSTER_PIXELS:
                filtered_mask[labels == label] = 255

        filtered_count = cv2.countNonZero(filtered_mask)
        if filtered_count == 0:
            continue
        if filtered_count < MIN_PIXELS:
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        output = gray_bgr
        output[filtered_mask > 0] = img[filtered_mask > 0]

        out_name = os.path.basename(path)
        out_path = os.path.join(output_dir, out_name)
        cv2.imwrite(out_path, output)
        kept += 1

        if kept % 100 == 0:
            print(f"Saved {kept} matching frame(s) so far...")

    print(f"Done. Processed {processed} frame(s); saved {kept} matching frame(s) to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
