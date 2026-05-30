"""
자동 보정: 사용자 입력 없이 게임판 bbox를 화면에서 감지하고 팔레트를 학습한다.
게임이 화면에 표시된 상태에서 실행하면 됨.
"""
import json
import pyautogui

from vision import auto_detect_board, capture, learn_palette, ROWS, COLS

CONFIG_PATH = "config.json"


def detect_scale():
    with __import__("mss").MSS() as sct:
        mon = sct.monitors[1]
        cap_w, cap_h = mon["width"], mon["height"]
    screen_w, screen_h = pyautogui.size()
    return cap_w / screen_w, cap_h / screen_h


def auto_calibrate():
    print("=== 자동 보정 시작 ===")
    print("게임 보드 감지 중...")

    bbox = auto_detect_board()
    if bbox is None:
        print("게임 보드를 찾지 못했습니다. 게임이 화면에 표시된 상태인지 확인하세요.")
        return False

    print(f"  보드 감지 완료: {bbox}")

    img = capture(bbox)
    print("  팔레트 학습 중...")
    palette = learn_palette(img, ROWS, COLS)
    scale_x, scale_y = detect_scale()

    config = {
        "bbox": bbox,
        "rows": ROWS,
        "cols": COLS,
        "palette": palette,
        "bg_color": [200, 200, 200],
        "scale_x": scale_x,
        "scale_y": scale_y,
    }
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    print(f"  격자: {ROWS}x{COLS} (고정)")
    print(f"  팔레트: {len(palette)}색")
    print(f"  HiDPI: x={scale_x:.2f}, y={scale_y:.2f}")
    print(f"자동 보정 완료 → {CONFIG_PATH}")
    return True


if __name__ == "__main__":
    auto_calibrate()
