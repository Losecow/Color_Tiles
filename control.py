"""
마우스 제어 및 좌표 변환.
macOS HiDPI(레티나): mss 캡처 좌표 = 물리 픽셀, pyautogui 좌표 = 논리 픽셀.
config의 scale_x/y로 변환. (캡처 bbox는 물리 픽셀 기준으로 저장됨.)
"""
import pyautogui
import time

pyautogui.FAILSAFE = True  # 마우스를 화면 좌상단으로 옮기면 즉시 중단


def cell_to_screen(bbox, rows, cols, r, c, scale_x=1.0, scale_y=1.0):
    """
    셀 (r,c) 중앙의 논리 픽셀 좌표 반환 (pyautogui용).
    bbox는 물리 픽셀 기준.
    """
    board_w = bbox["x2"] - bbox["x1"]
    board_h = bbox["y2"] - bbox["y1"]
    px = bbox["x1"] + (c + 0.5) * board_w / cols  # 물리 픽셀
    py = bbox["y1"] + (r + 0.5) * board_h / rows
    return int(px / scale_x), int(py / scale_y)   # 논리 픽셀


def click_cell(bbox, rows, cols, r, c, scale_x=1.0, scale_y=1.0):
    sx, sy = cell_to_screen(bbox, rows, cols, r, c, scale_x, scale_y)
    pyautogui.click(sx, sy)


def verify_click(bbox, rows, cols, r, c, scale_x=1.0, scale_y=1.0):
    """
    보정 검증용: 마우스를 목표 셀로 이동 (클릭 없이).
    실제 타일 위에 커서가 맞는지 눈으로 확인.
    """
    sx, sy = cell_to_screen(bbox, rows, cols, r, c, scale_x, scale_y)
    pyautogui.moveTo(sx, sy, duration=0.3)
    print(f"  셀 ({r},{c}) → 화면 ({sx},{sy})")
    time.sleep(0.5)
