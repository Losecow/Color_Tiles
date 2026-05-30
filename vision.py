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


def auto_detect_board(padding=6):
    """
    전체 화면에서 게임 보드 bbox 자동 감지.
    채도 높은(타일) 픽셀 밀집 영역의 최대 연결 컴포넌트를 찾는다.
    반환: {"x1","y1","x2","y2"} (물리 픽셀 기준) 또는 None
    """
    img, _ = full_screenshot()
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    sat_mask = (hsv[:, :, 1] > 50).astype(np.uint8)

    # 타일들을 이어붙여 보드 영역으로 만들기
    kernel = np.ones((25, 25), np.uint8)
    dilated = cv2.dilate(sat_mask, kernel, iterations=2)

    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(dilated)
    if num_labels < 2:
        return None

    # 배경(0) 제외하고 가장 큰 영역
    areas = stats[1:, cv2.CC_STAT_AREA]
    largest = int(np.argmax(areas)) + 1
    x = int(stats[largest, cv2.CC_STAT_LEFT])
    y = int(stats[largest, cv2.CC_STAT_TOP])
    w = int(stats[largest, cv2.CC_STAT_WIDTH])
    h = int(stats[largest, cv2.CC_STAT_HEIGHT])

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


def print_board(board):
    """콘솔 디버그 출력 (빈칸='.', 색=A-Z)"""
    symbols = ".ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    for row in board:
        print(" ".join(symbols[v] if v < len(symbols) else "?" for v in row))


def get_frame_and_board(config):
    img = capture(config["bbox"])
    board = recognize_board(img, config)
    return img, board
