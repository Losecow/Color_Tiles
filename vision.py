"""
vision 모듈: 화면 캡처 → 2D 보드 배열.
"""
import json
import numpy as np
import cv2
import mss

EMPTY = 0
ROWS = 10
COLS = 17
BG_SAT_THRESHOLD = 40  # HSV 채도 이하면 빈칸(체크무늬 배경)


def load_config(path="config.json"):
    with open(path) as f:
        return json.load(f)


def full_screenshot():
    """전체 화면 캡처 → BGR numpy 배열 + mss monitor 정보"""
    with mss.MSS() as sct:
        mon = sct.monitors[1]
        shot = sct.grab(mon)
        img = np.array(shot)
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR), mon


def auto_detect_board(rows=ROWS, cols=COLS, padding=4):
    """
    전체 화면에서 게임 보드 bbox 자동 감지.
    1) 타일 크기(≥1500px²) 이상 블롭만 유지 → 터미널 텍스트 제거
    2) 행/열 밀도 투영 → 가장 밀집된 연속 구간을 게임판 경계로 선택
    """
    img, _ = full_screenshot()
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    sat_mask = (hsv[:, :, 1] > 50).astype(np.uint8)

    # 터미널 텍스트·소아이콘 제거 (타일 최소 ~32×32px = 1000px²)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(sat_mask)
    tile_mask = np.zeros_like(sat_mask)
    for i in range(1, n):
        if int(stats[i, cv2.CC_STAT_AREA]) >= 1000:
            tile_mask[labels == i] = 1

    if tile_mask.sum() == 0:
        return None

    # 행/열 밀도
    row_dens = tile_mask.mean(axis=1)
    col_dens = tile_mask.mean(axis=0)
    thr = max(row_dens.max(), col_dens.max()) * 0.2

    def largest_run(dens, threshold):
        """밀도가 threshold 이상인 가장 긴 연속 구간의 (start, end) 반환"""
        active = np.where(dens > threshold)[0]
        if len(active) == 0:
            return 0, 0
        runs, start, prev = [], active[0], active[0]
        for idx in active[1:]:
            if idx - prev > 8:
                runs.append((start, prev))
                start = idx
            prev = idx
        runs.append((start, prev))
        return max(runs, key=lambda r: r[1] - r[0])

    y1, y2 = largest_run(row_dens, thr)
    x1, x2 = largest_run(col_dens, thr)

    return {
        "x1": max(0, int(x1) - padding),
        "y1": max(0, int(y1) - padding),
        "x2": int(x2) + padding,
        "y2": int(y2) + padding,
    }


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


def learn_palette(img, rows=ROWS, cols=COLS, n_clusters=14):
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


def recognize_board(img, config):
    """
    캡처 이미지 → 2D 보드 배열.
    EMPTY(0) 또는 색 ID(1-based).
    """
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
                row.append(nearest_color_id(bgr, palette) + 1)  # 1-based
        board.append(row)
    return board


def save_debug_image(img, rows, cols, filename="debug.png"):
    """감지된 그리드를 오버레이한 디버그 이미지 저장"""
    debug = img.copy()
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
            cv2.circle(debug, (cx, cy), 4, (0, 0, 255), -1)

    cv2.imwrite(filename, debug)


def is_game_over(img):
    """
    게임 오버 오버레이(Play Again 화면) 감지.
    중앙 영역에 밝고 채도 낮은 픽셀이 30% 이상이면 오버레이로 판단.
    """
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
