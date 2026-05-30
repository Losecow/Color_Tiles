"""
Color Tiles 자동 플레이 봇.

사용법:
  1. python calibrate.py   # 최초 1회 보정
  2. python main.py        # 자동 플레이 시작

중단: Ctrl+C 또는 마우스를 화면 좌상단으로 이동 (pyautogui FAILSAFE).
"""
import json
import time
import sys

from vision import get_frame_and_board, print_board
from board import color_counts, apply_removal, is_clear, tile_count
from solver import best_click, tiles_gained
from control import click_cell

CONFIG_PATH = "config.json"
CLICK_DELAY = 0.25   # 클릭 간 딜레이 (게임 애니메이션 대기, 초)
START_DELAY = 3      # 봇 시작 전 게임 창으로 이동할 시간


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def run():
    config = load_config()
    bbox = config["bbox"]
    rows, cols = config["rows"], config["cols"]
    scale_x = config.get("scale_x", 1.0)
    scale_y = config.get("scale_y", 1.0)

    print("=== Color Tiles 봇 시작 ===")
    print(f"설정: {rows}x{cols} 격자 | HiDPI x={scale_x:.2f} y={scale_y:.2f}")
    print(f"{START_DELAY}초 후 자동 클릭 시작. 중단: Ctrl+C 또는 마우스를 좌상단으로.")
    time.sleep(START_DELAY)

    # 초기 보드 인식
    img, board = get_frame_and_board(config)
    remaining = color_counts(board)
    print("\n초기 보드:")
    print_board(board)
    print(f"타일 총 수: {tile_count(board)} | 색 종류: {len(remaining)}")
    print(f"색별 잔여: {remaining}\n")

    clicks = 0
    score = 0
    start = time.time()

    try:
        while True:
            img, board = get_frame_and_board(config)

            if is_clear(board):
                elapsed = time.time() - start
                print(f"\n[클리어!] 점수: {score} | 클릭: {clicks} | 경과: {elapsed:.1f}s")
                break

            remaining = color_counts(board)
            click = best_click(board, remaining)

            if click is None:
                print("  유효 후보 없음 — 0.5s 대기 후 재인식")
                time.sleep(0.5)
                continue

            r, c = click
            gained_set = tiles_gained(board, r, c)
            gained = len(gained_set)
            score += gained

            elapsed = time.time() - start
            print(f"  [{elapsed:5.1f}s] 클릭 ({r:2d},{c:2d}) +{gained:2d}점 → 누적 {score:3d}점"
                  f" | 잔여 {tile_count(board) - gained}개")

            click_cell(bbox, rows, cols, r, c, scale_x, scale_y)
            clicks += 1
            time.sleep(CLICK_DELAY)

    except KeyboardInterrupt:
        elapsed = time.time() - start
        print(f"\n[중단] 점수: {score} | 클릭: {clicks} | 경과: {elapsed:.1f}s")


if __name__ == "__main__":
    run()
