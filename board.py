"""
2D 보드 모델.
0 = 빈칸, 양수 = 색 ID.
"""
from copy import deepcopy

EMPTY = 0


def empty_cells(board):
    return [(r, c) for r, row in enumerate(board) for c, v in enumerate(row) if v == EMPTY]


def tile_count(board):
    return sum(1 for row in board for v in row if v != EMPTY)


def color_counts(board):
    counts = {}
    for row in board:
        for v in row:
            if v != EMPTY:
                counts[v] = counts.get(v, 0) + 1
    return counts


def apply_removal(board, positions):
    """positions: iterable of (r,c) — 해당 위치를 빈칸으로 만든 새 보드 반환"""
    b = deepcopy(board)
    for r, c in positions:
        b[r][c] = EMPTY
    return b


def is_clear(board):
    return tile_count(board) == 0
