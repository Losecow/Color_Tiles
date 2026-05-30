"""
vision 모듈: 화면 캡처 → 2D 보드 배열.
"""
import json
import numpy as np
import cv2
import mss

EMPTY = 0
ROWS = 15
COLS = 23
BG_SAT_THRESHOLD = 40  # HSV 채도 이하면 빈칸(체크무늬 배경)


def load_config(path="config.json"):
    with open(path) as f:
        return json.load(f)


def capture(bbox):
    """지정 영역 캡처 → BGR numpy 배열"""
    with mss.MSS() as sct:
        monitor = {
            "left": bbox["x1"], "top": bbox["y1"],
            "width": bbox["x2"] - bbox["x1"],
            "height": bbox["y2"] - bbox["y1"],
        }
        shot = sct.grab(monitor)
        img = np.array(shot)
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def cell_mean_bgr(img, r, c, rows, cols):
    """셀 중앙 5×5 패치 평균 BGR"""
    h, w = img.shape[:2]
    cy = int((r + 0.5) * h / rows)
    cx = int((c + 0.5) * w / cols)
    patch = img[max(0, cy - 2):cy + 3, max(0, cx - 2):cx + 3]
    return patch.mean(axis=(0, 1))


def nearest_color_id(bgr, palette):
    """팔레트에서 L2 최근접 색 인덱스 반환 (0-based)"""
    arr = np.array(palette, dtype=np.float32)
    dists = np.linalg.norm(arr - np.array(bgr, dtype=np.float32), axis=1)
    return int(np.argmin(dists))


def bgr_saturation(bgr):
    pixel = np.uint8([[bgr]])
    hsv = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)[0][0]
    return int(hsv[1])


def learn_palette(img, rows=ROWS, cols=COLS, n_clusters=12):
    """
    고채도 타일 셀만 샘플링해 K-Means 팔레트 생성.
    배경(빈칸) 색은 포함하지 않아 팔레트 오염 방지.
    """
    tile_samples = []
    for r in range(rows):
        for c in range(cols):
            bgr = cell_mean_bgr(img, r, c, rows, cols)
            if bgr_saturation(bgr) >= 50:
                tile_samples.append(bgr)

    if len(tile_samples) < n_clusters:
        tile_samples = [cell_mean_bgr(img, r, c, rows, cols)
                        for r in range(rows) for c in range(cols)]

    samples = np.array(tile_samples, dtype=np.float32)
    k = min(n_clusters, len(samples))
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _, _, centers = cv2.kmeans(samples, k, None, criteria, 10, cv2.KMEANS_PP_CENTERS)
    return centers.astype(int).tolist()


def recognize_board(img, config):
    """캡처 이미지 → 2D 보드 배열. EMPTY(0) 또는 색 ID(1-based)."""
    rows, cols = config["rows"], config["cols"]
    palette = config["palette"]
    board = []
    for r in range(rows):
        row = []
        for c in range(cols):
            bgr = cell_mean_bgr(img, r, c, rows, cols)
            if bgr_saturation(bgr) < BG_SAT_THRESHOLD:
                row.append(EMPTY)
            else:
                row.append(nearest_color_id(bgr, palette) + 1)
        board.append(row)
    return board


def save_debug_image(img, config, filename="debug.png"):
    """
    그리드 + 색 인식 결과 오버레이 이미지 저장.
    빈칸=회색 점, 타일=팔레트 색상 점.
    """
    debug = img.copy()
    rows = config.get("rows", ROWS)
    cols = config.get("cols", COLS)
    palette = config.get("palette", [])
    h, w = img.shape[:2]
    cell_h = h / rows
    cell_w = w / cols

    for r in range(rows + 1):
        y = int(r * cell_h)
        cv2.line(debug, (0, y), (w, y), (0, 255, 0), 1)
    for c in range(cols + 1):
        x = int(c * cell_w)
        cv2.line(debug, (x, 0), (x, h), (0, 255, 0), 1)

    for r in range(rows):
        for c in range(cols):
            cy = int((r + 0.5) * cell_h)
            cx = int((c + 0.5) * cell_w)
            bgr = cell_mean_bgr(img, r, c, rows, cols)
            if bgr_saturation(bgr) < BG_SAT_THRESHOLD:
                cv2.circle(debug, (cx, cy), 3, (160, 160, 160), -1)
            elif palette:
                pid = nearest_color_id(bgr, palette)
                dot_color = tuple(int(v) for v in palette[pid])
                cv2.circle(debug, (cx, cy), 6, dot_color, -1)
                cv2.circle(debug, (cx, cy), 6, (0, 0, 0), 1)
            else:
                cv2.circle(debug, (cx, cy), 4, (0, 0, 255), -1)

    cv2.imwrite(filename, debug)


def is_game_over(img):
    """게임 오버 오버레이(Play Again 화면) 감지."""
    h, w = img.shape[:2]
    cy1, cy2 = int(h * 0.35), int(h * 0.65)
    cx1, cx2 = int(w * 0.25), int(w * 0.75)
    center = img[cy1:cy2, cx1:cx2]
    hsv = cv2.cvtColor(center, cv2.COLOR_BGR2HSV)
    bright_low_sat = np.mean((hsv[:, :, 1] < 30) & (hsv[:, :, 2] > 180))
    return bool(bright_low_sat > 0.3)


def print_board(board):
    """콘솔 디버그 출력 (빈칸='.', 색=A-Z)"""
    symbols = ".ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    for row in board:
        print(" ".join(symbols[v] if v < len(symbols) else "?" for v in row))


def get_frame_and_board(config):
    img = capture(config["bbox"])
    board = recognize_board(img, config)
    return img, board
