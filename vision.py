"""
vision 모듈: 화면 캡처 → 2D 보드 배열.
"""
import json
import numpy as np
import cv2
import mss

EMPTY = 0
BG_SAT_THRESHOLD = 40  # HSV 채도 이하면 빈칸(체크무늬 배경)


def load_config(path="config.json"):
    with open(path) as f:
        return json.load(f)


def capture(bbox):
    """지정 영역 캡처 → BGR numpy 배열"""
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
