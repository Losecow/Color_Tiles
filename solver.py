"""
핵심 솔버: 고립 타일 최소화 + 색별 패리티(홀짝) 추적 전략.

정렬 키 (사전식, 낮을수록 우선):
  (isolation_after, parity_risk, -gained, dist_center)
"""
from board import EMPTY, color_counts, apply_removal

DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


# ──────────────────────────────────────────────
# 기본 게임 로직
# ──────────────────────────────────────────────

def first_tile_in_dir(board, r, c, dr, dc):
    """(r,c)에서 (dr,dc) 방향으로 첫 번째 비빈칸의 (색, 좌표) 반환"""
    rows, cols = len(board), len(board[0])
    nr, nc = r + dr, c + dc
    while 0 <= nr < rows and 0 <= nc < cols:
        if board[nr][nc] != EMPTY:
            return board[nr][nc], (nr, nc)
        nr += dr
        nc += dc
    return None, None


def tiles_gained(board, r, c):
    """
    빈칸 (r,c) 클릭 시 제거되는 타일 좌표 집합 반환.
    같은 색이 2개 이상 만나면 그 색의 모든 인접 타일 제거.
    3개 이상도 전부 제거됨(홀수 제거 가능).
    """
    if board[r][c] != EMPTY:
        return set()

    color_to_positions: dict[int, list] = {}
    for dr, dc in DIRECTIONS:
        color, pos = first_tile_in_dir(board, r, c, dr, dc)
        if color is not None:
            color_to_positions.setdefault(color, []).append(pos)

    result = set()
    for color, positions in color_to_positions.items():
        if len(positions) >= 2:
            result.update(positions)
    return result


# ──────────────────────────────────────────────
# 고립도 추정 (v1)
# ──────────────────────────────────────────────

def estimate_isolation_v1(board_after):
    """
    v1: 색별 잔여 개수가 홀수면 +1 페널티.
    언젠가 1개가 고립될 가능성을 단순 추정.
    """
    counts = color_counts(board_after)
    return sum(1 for cnt in counts.values() if cnt % 2 != 0)


# ──────────────────────────────────────────────
# 패리티(홀짝) 위험 계산
# ──────────────────────────────────────────────

def _odd_match_possible(board, color):
    """
    board에서 color가 한 빈칸에 3방향 이상 모이는 경우가 있으면 True.
    홀수 잔여를 다시 홀수개 제거해 짝수(0)로 회수할 수 있는지 검사.
    """
    rows, cols = len(board), len(board[0])
    for r in range(rows):
        for c in range(cols):
            if board[r][c] != EMPTY:
                continue
            same = sum(
                1 for dr, dc in DIRECTIONS
                if first_tile_in_dir(board, r, c, dr, dc)[0] == color
            )
            if same >= 3:
                return True
    return False


def calc_parity_risk(board_after, removed_colors_k, remaining_before):
    """
    removed_colors_k: {color: 이번에 제거한 수}
    remaining_before: {color: 클릭 전 잔여 수}
    반환값: 정수 위험도 (낮을수록 좋음)
    """
    risk = 0
    for color, k in removed_colors_k.items():
        rem_after = remaining_before.get(color, 0) - k
        if rem_after <= 0:
            continue
        if rem_after % 2 == 0:
            pass  # 안전
        elif _odd_match_possible(board_after, color):
            risk += 1   # 만회 경로 있음
        else:
            risk += 10  # 고립 확정 위험
    return risk


# ──────────────────────────────────────────────
# 후보 평가 및 최적 선택
# ──────────────────────────────────────────────

def score_candidate(board, r, c, remaining):
    """
    후보 (r,c)의 정렬 키 반환. 유효하지 않으면 None.
    """
    gained_set = tiles_gained(board, r, c)
    gained = len(gained_set)
    if gained == 0:
        return None  # 오답(시간 -10초) → 제외

    board_after = apply_removal(board, gained_set)

    removed_colors_k: dict[int, int] = {}
    for pos in gained_set:
        color = board[pos[0]][pos[1]]
        removed_colors_k[color] = removed_colors_k.get(color, 0) + 1

    isolation = estimate_isolation_v1(board_after)
    par_risk = calc_parity_risk(board_after, removed_colors_k, remaining)

    rows, cols = len(board), len(board[0])
    dist_center = abs(r - rows / 2) + abs(c - cols / 2)

    return (isolation, par_risk, -gained, dist_center)


def best_click(board, remaining):
    """
    최적 클릭 좌표 (r, c) 반환. 유효 후보 없으면 None.
    remaining: {color: 잔여 수} — 매 클릭 후 갱신된 값을 전달할 것.
    """
    rows, cols = len(board), len(board[0])
    candidates = []
    for r in range(rows):
        for c in range(cols):
            if board[r][c] != EMPTY:
                continue
            key = score_candidate(board, r, c, remaining)
            if key is not None:
                candidates.append((key, r, c))

    if not candidates:
        return None
    candidates.sort()
    _, r, c = candidates[0]
    return r, c
