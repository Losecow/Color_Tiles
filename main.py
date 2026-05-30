"""
Color Tiles 자동 플레이 봇.

사용법:
  python main.py   # 게임이 화면에 열려 있으면 바로 실행

중단: Ctrl+C 또는 마우스를 화면 좌상단으로 이동 (pyautogui FAILSAFE).
"""
import json
import time

from vision import get_frame_and_board, print_board, auto_detect_board, capture, learn_palette, is_game_over, ROWS, COLS
from board import color_counts, is_clear, tile_count
from solver import best_click, tiles_gained
from control import click_cell

CONFIG_PATH = "config.json"
CLICK_DELAY = 0.25
START_DELAY = 3


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def fresh_config():
    """매 실행마다 bbox 재감지 + 팔레트 재학습 (보드가 매 판 새로 생성되므로)"""
    config = load_config()

    print("게임 보드 자동 감지 중...")
    detected = auto_detect_board()
    if detected is None:
        raise RuntimeError("게임 보드를 찾지 못했습니다. 게임이 화면에 표시된 상태인지 확인하세요.")
    config["bbox"] = detected
    print(f"  bbox: {detected}")

    img = capture(detected)
    config["palette"] = learn_palette(img, ROWS, COLS)
    print(f"  팔레트: {len(config['palette'])}색 학습 완료")

    save_config(config)
    return config


def run():
    config = fresh_config()
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

            if is_game_over(img):
                elapsed = time.time() - start
                print(f"\n[게임 오버] 점수: {score} | 클릭: {clicks} | 경과: {elapsed:.1f}s")
                break

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
