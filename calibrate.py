"""
보정 모드: 게임판 bbox·격자·색 팔레트를 학습하여 config.json 저장.
macOS 화면 기록/손쉬운 사용 권한 허용 필요.
"""
import json
import time
import numpy as np
import cv2
import mss
import pyautogui

CONFIG_PATH = "config.json"
BG_SAT_THRESHOLD = 40  # 채도 이하면 배경(빈칸)으로 판정


def capture_region(bbox):
    with mss.mss() as sct:
        monitor = {
            "left": bbox["x1"], "top": bbox["y1"],
            "width": bbox["x2"] - bbox["x1"],
            "height": bbox["y2"] - bbox["y1"],
        }
        shot = sct.grab(monitor)
        img = np.array(shot)
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def cell_mean_bgr(img, r, c, rows, cols):
    h, w = img.shape[:2]
    cy = int((r + 0.5) * h / rows)
    cx = int((c + 0.5) * w / cols)
    patch = img[max(0, cy - 2):cy + 3, max(0, cx - 2):cx + 3]
    return patch.mean(axis=(0, 1))


def learn_palette(img, rows, cols, n_clusters=14):
    """셀 중앙 패치 평균색 → K-Means 군집화로 색 팔레트 생성"""
    samples = []
    for r in range(rows):
        for c in range(cols):
            bgr = cell_mean_bgr(img, r, c, rows, cols)
            samples.append(bgr)

    samples = np.array(samples, dtype=np.float32)
    k = min(n_clusters, len(samples))
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _, _, centers = cv2.kmeans(samples, k, None, criteria, 10, cv2.KMEANS_PP_CENTERS)
    return centers.astype(int).tolist()


def detect_bg_color(img, rows, cols):
    """채도가 낮은 셀들의 평균으로 배경색 추정"""
    low_sat = []
    for r in range(rows):
        for c in range(cols):
            bgr = cell_mean_bgr(img, r, c, rows, cols)
            pixel = np.uint8([[bgr]])
            hsv = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)[0][0]
            if hsv[1] < BG_SAT_THRESHOLD:
                low_sat.append(bgr)
    if low_sat:
        return np.mean(low_sat, axis=0).astype(int).tolist()
    return [200, 200, 200]


def detect_scale():
    """HiDPI 배율 추정: mss 캡처 해상도 vs pyautogui 화면 크기 비교"""
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        cap_w, cap_h = monitor["width"], monitor["height"]
    screen_w, screen_h = pyautogui.size()
    return cap_w / screen_w, cap_h / screen_h


def get_bbox_from_clicks(delay=3):
    print(f"게임판 좌상단에 마우스를 놓으세요 ({delay}초 후 기록)...")
    time.sleep(delay)
    x1, y1 = pyautogui.position()
    print(f"  좌상단: ({x1}, {y1})")
    print(f"게임판 우하단에 마우스를 놓으세요 ({delay}초 후 기록)...")
    time.sleep(delay)
    x2, y2 = pyautogui.position()
    print(f"  우하단: ({x2}, {y2})")
    scale_x, scale_y = detect_scale()
    return {
        "x1": int(x1 * scale_x), "y1": int(y1 * scale_y),
        "x2": int(x2 * scale_x), "y2": int(y2 * scale_y),
    }


def get_bbox_from_input():
    scale_x, scale_y = detect_scale()
    print(f"HiDPI 배율: x={scale_x:.2f}, y={scale_y:.2f}")
    x1 = int(float(input("x1 (좌상단 화면 X): ")) * scale_x)
    y1 = int(float(input("y1 (좌상단 화면 Y): ")) * scale_y)
    x2 = int(float(input("x2 (우하단 화면 X): ")) * scale_x)
    y2 = int(float(input("y2 (우하단 화면 Y): ")) * scale_y)
    return {"x1": x1, "y1": y1, "x2": x2, "y2": y2}


def calibrate():
    print("=== Color Tiles 보정 모드 ===")
    mode = input("좌표 입력: [1] 마우스 위치  [2] 직접 입력 → ").strip()
    if mode == "1":
        bbox = get_bbox_from_clicks()
    else:
        bbox = get_bbox_from_input()

    rows = int(input("격자 행 수 (rows): "))
    cols = int(input("격자 열 수 (cols): "))

    print("현재 보드 캡처 중...")
    img = capture_region(bbox)

    print("색 팔레트 학습 중...")
    palette = learn_palette(img, rows, cols)
    bg_color = detect_bg_color(img, rows, cols)
    scale_x, scale_y = detect_scale()

    config = {
        "bbox": bbox,
        "rows": rows,
        "cols": cols,
        "palette": palette,
        "bg_color": bg_color,
        "scale_x": scale_x,
        "scale_y": scale_y,
    }
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n보정 완료 → {CONFIG_PATH}")
    print(f"  bbox   : {bbox}")
    print(f"  격자   : {rows}x{cols}")
    print(f"  팔레트 : {len(palette)}색")
    print(f"  배경색 : {bg_color}")
    print(f"  HiDPI  : x={scale_x:.2f}, y={scale_y:.2f}")


if __name__ == "__main__":
    calibrate()
