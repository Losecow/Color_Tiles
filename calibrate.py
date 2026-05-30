"""
보정: 마우스를 두 모서리에 가져다 놓는 방식으로 게임판 bbox를 지정.
한 번 실행 후 config.json에 저장 → main.py는 이를 재사용.
"""
import json
import time
import pyautogui
import mss

from vision import capture, learn_palette, ROWS, COLS

CONFIG_PATH = "config.json"


def detect_scale():
    with mss.MSS() as sct:
        mon = sct.monitors[1]
        cap_w, cap_h = mon["width"], mon["height"]
    screen_w, screen_h = pyautogui.size()
    return cap_w / screen_w, cap_h / screen_h


def hover_point(label, seconds=4):
    """countdown 후 현재 마우스 위치를 (논리 픽셀로) 반환"""
    print(f"{label} 위에 마우스를 올려놓으세요... ({seconds}초 후 기록)")
    for i in range(seconds, 0, -1):
        print(f"  {i}...", end="\r", flush=True)
        time.sleep(1)
    x, y = pyautogui.position()
    print(f"  기록됨: ({x}, {y})          ")
    return x, y


def calibrate():
    print("=== Color Tiles 보정 ===")
    print("게임 보드가 보이는 상태에서 실행하세요.\n")

    lx, ly = hover_point("게임판 좌상단 타일 중앙")
    rx, ry = hover_point("게임판 우하단 타일 중앙")

    scale_x, scale_y = detect_scale()

    # 타일 중앙 → 타일 간격 계산 → 보드 전체 bbox
    cell_w = (rx - lx) / (COLS - 1)
    cell_h = (ry - ly) / (ROWS - 1)

    # 논리 픽셀 bbox (pyautogui 좌표계)
    bx1 = int(lx - cell_w * 0.5)
    by1 = int(ly - cell_h * 0.5)
    bx2 = int(rx + cell_w * 0.5)
    by2 = int(ry + cell_h * 0.5)

    # mss 캡처는 물리 픽셀 기준이므로 변환
    bbox = {
        "x1": int(bx1 * scale_x),
        "y1": int(by1 * scale_y),
        "x2": int(bx2 * scale_x),
        "y2": int(by2 * scale_y),
    }

    w = bbox["x2"] - bbox["x1"]
    h = bbox["y2"] - bbox["y1"]
    print(f"\nbbox: {bbox}")
    print(f"크기: {w}x{h}  비율: {w/h:.2f} (목표 {COLS/ROWS:.2f})")

    print("팔레트 학습 중...")
    img = capture(bbox)
    palette = learn_palette(img, ROWS, COLS)

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

    print(f"보정 완료 → {CONFIG_PATH} 저장됨")


if __name__ == "__main__":
    calibrate()
