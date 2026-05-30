"""
보정: 반투명 정렬 가이드를 게임 위에 올려놓고 Enter → bbox 저장.
"""
import json
import tkinter as tk
import mss
import pyautogui

from vision import capture, learn_palette, save_debug_image, ROWS, COLS

CONFIG_PATH = "config.json"


def detect_scale():
    with mss.MSS() as sct:
        mon = sct.monitors[1]
    sw, sh = pyautogui.size()
    return mon["width"] / sw, mon["height"] / sh


def show_guide():
    """
    반투명 정렬 가이드.
    - 드래그로 이동, 모서리로 크기 조정
    - 빨간 그리드 선을 게임 타일 경계에 맞추고 Enter
    """
    root = tk.Tk()
    root.title("빨간 선을 게임 타일 경계에 맞추고 Enter")
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.45)
    root.geometry("850x500+100+60")
    root.resizable(True, True)

    canvas = tk.Canvas(root, bg="black", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    def redraw(event=None):
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w < 10 or h < 10:
            return
        canvas.create_rectangle(1, 1, w - 1, h - 1, outline="#FF4444", width=3)
        for i in range(1, COLS):
            x = int(i * w / COLS)
            canvas.create_line(x, 0, x, h, fill="#FF4444", width=1)
        for i in range(1, ROWS):
            y = int(i * h / ROWS)
            canvas.create_line(0, y, w, y, fill="#FF4444", width=1)
        canvas.create_text(
            w // 2, h // 2,
            text="빨간 선을 게임 타일 경계에 맞추세요\nEnter 눌러 완료  /  드래그로 이동  /  모서리로 크기 조정",
            fill="white", font=("Arial", 13, "bold"), justify="center",
        )

    canvas.bind("<Configure>", redraw)

    # 드래그 이동
    def on_press(e):
        root._ox = e.x_root - root.winfo_x()
        root._oy = e.y_root - root.winfo_y()
    def on_drag(e):
        root.geometry(f"+{e.x_root - root._ox}+{e.y_root - root._oy}")
    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)

    result = {}

    def confirm(event=None):
        root.update_idletasks()
        x = canvas.winfo_rootx()
        y = canvas.winfo_rooty()
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        result["logical"] = {"x1": x, "y1": y, "x2": x + w, "y2": y + h}
        root.destroy()

    root.bind("<Return>", confirm)
    root.mainloop()
    return result.get("logical")


def calibrate():
    print("=== Color Tiles 보정 ===")
    print("게임을 브라우저에 열어놓고, 반투명 빨간 가이드를 게임 그리드 위에 정렬하세요.")
    print("Enter 눌러 완료.\n")

    logical = show_guide()
    if not logical:
        print("보정 취소.")
        return

    scale_x, scale_y = detect_scale()
    bbox = {
        "x1": int(logical["x1"] * scale_x),
        "y1": int(logical["y1"] * scale_y),
        "x2": int(logical["x2"] * scale_x),
        "y2": int(logical["y2"] * scale_y),
    }
    w = bbox["x2"] - bbox["x1"]
    h = bbox["y2"] - bbox["y1"]
    print(f"bbox: {bbox}  크기: {w}×{h}  비율: {w/h:.2f} (목표 {COLS/ROWS:.2f})")

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

    save_debug_image(img, config, "debug.png")
    print(f"보정 완료 → {CONFIG_PATH} / debug.png 저장됨")


if __name__ == "__main__":
    calibrate()
