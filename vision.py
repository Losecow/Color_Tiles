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


def auto_detect_board(rows=ROWS, cols=COLS, padding=6):
    """
    전체 화면에서 게임 보드 bbox 자동 감지.
    - 터미널 텍스트 등 작은 블롭(< 500px²) 제거 후 타일 군집화
    - cols/rows 비율(17:10=1.7)에 가장 가까운 영역을 게임판으로 선택
    반환: {"x1","y1","x2","y2"} (물리 픽셀 기준) 또는 None
    """
    target_ratio = cols / rows  # 1.7

    img, _ = full_screenshot()
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    sat_mask = (hsv[:, :, 1] > 50).astype(np.uint8)

    # 터미널 텍스트 등 소형 블롭 제거 (타일 최소 면적 500px²)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(sat_mask)
    filtered = np.zeros_like(sat_mask)
    for i in range(1, n):
        if int(stats[i, cv2.CC_STAT_AREA]) >= 500:
            filtered[labels == i] = 1

    # 인접 타일 연결
    kernel = np.ones((30, 30), np.uint8)
    dilated = cv2.dilate(filtered, kernel, iterations=2)

    n2, _, st2, _ = cv2.connectedComponentsWithStats(dilated)
    if n2 < 2:
        return None

    # 넓이 × (비율 오차 패널티) 스코어 — 게임판 비율(17:10)에 가장 가까운 최대 영역 선택
    best, best_score = None, -1
    for i in range(1, n2):
        x = int(st2[i, cv2.CC_STAT_LEFT])
        y = int(st2[i, cv2.CC_STAT_TOP])
        w = int(st2[i, cv2.CC_STAT_WIDTH])
        h = int(st2[i, cv2.CC_STAT_HEIGHT])
        area = int(st2[i, cv2.CC_STAT_AREA])
        if w < 200 or h < 100:
            continue
        ratio_err = abs(w / h - target_ratio)
        score = area / (1 + ratio_err * 10)
        if score > best_score:
            best_score = score
            best = (x, y, w, h)

    if best is None:
        return None

    x, y, w, h = best
    return {
        "x1": max(0, x - padding),
        "y1": max(0, y - padding),
        "x2": x + w + padding,
        "y2": y + h + padding,
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
