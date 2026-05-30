"""
solver.tiles_gained 및 best_click 단위 테스트.
손계산 보드로 결과를 직접 대조.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from solver import tiles_gained, best_click, estimate_isolation_v1
from board import color_counts

# 색 상수
A, B, C = 1, 2, 3
E = 0  # EMPTY


# ──────────────────────────────
# tiles_gained 테스트
# ──────────────────────────────

def test_basic_pair():
    """좌우 같은 색 → 2개 제거"""
    board = [
        [A, E, A],
    ]
    result = tiles_gained(board, 0, 1)
    assert result == {(0, 0), (0, 2)}, f"expected pair removal, got {result}"


def test_four_directions():
    """상하좌우 같은 색 4개 → 전부 제거"""
    board = [
        [E, A, E],
        [A, E, A],
        [E, A, E],
    ]
    result = tiles_gained(board, 1, 1)
    assert result == {(0, 1), (2, 1), (1, 0), (1, 2)}, f"got {result}"


def test_three_same_color():
    """홀수(3개) 같은 색 → 전부 제거 (명세 §6.1 확인)"""
    board = [
        [A, E, A],
        [E, E, E],
        [E, E, A],
    ]
    # (0,1) 클릭: 좌(0,0)=A, 우(0,2)=A → 2개. 하(2,2)=A → 단독이라 무시.
    result = tiles_gained(board, 0, 1)
    assert result == {(0, 0), (0, 2)}, f"got {result}"

    # (1,2) 클릭: 상(0,2)=A, 하(2,2)=A → 2개.
    result2 = tiles_gained(board, 1, 2)
    assert result2 == {(0, 2), (2, 2)}, f"got {result2}"


def test_three_in_one_click():
    """한 빈칸에 같은 색이 3방향 → 3개 전부 제거"""
    board = [
        [E, A, E],
        [A, E, E],
        [E, A, E],
    ]
    # (1,1) 클릭: 상(0,1)=A, 좌(1,0)=A, 하(2,1)=A → 3개 모두
    result = tiles_gained(board, 1, 1)
    assert result == {(0, 1), (1, 0), (2, 1)}, f"got {result}"


def test_no_match():
    """매칭 없는 빈칸 → 빈 집합"""
    board = [
        [A, E, B],
    ]
    result = tiles_gained(board, 0, 1)
    assert result == set(), f"expected empty, got {result}"


def test_not_empty_cell():
    """타일이 있는 칸 → 빈 집합"""
    board = [[A, A, A]]
    result = tiles_gained(board, 0, 0)
    assert result == set()


def test_mixed_colors():
    """여러 색이 섞인 경우 같은 색끼리만 매칭"""
    board = [
        [A, E, B],
        [E, E, E],
        [A, E, B],
    ]
    # (0,1) 클릭: 좌A 우B → 서로 다른 색, 각 1개씩 → 매칭 없음
    assert tiles_gained(board, 0, 1) == set()

    # (1,0) 클릭: 상A, 하A → 2개 제거
    result = tiles_gained(board, 1, 0)
    assert result == {(0, 0), (2, 0)}, f"got {result}"


# ──────────────────────────────
# estimate_isolation_v1 테스트
# ──────────────────────────────

def test_isolation_v1_even():
    board = [[A, A, B, B]]
    assert estimate_isolation_v1(board) == 0


def test_isolation_v1_odd():
    board = [[A, A, A, B, B]]  # A=3(홀수)
    assert estimate_isolation_v1(board) == 1


# ──────────────────────────────
# best_click 통합 테스트
# ──────────────────────────────

def test_best_click_picks_highest_gain():
    """득점이 높은 쪽을 선택"""
    board = [
        [A, E, A, E, B],
    ]
    remaining = color_counts(board)
    click = best_click(board, remaining)
    # (0,1): A 2개 제거. (0,3): B 단독 → 매칭 없음.
    assert click == (0, 1), f"expected (0,1), got {click}"


def test_no_valid_click():
    """유효 후보 없으면 None"""
    board = [[A, E, B]]
    remaining = color_counts(board)
    assert best_click(board, remaining) is None


if __name__ == "__main__":
    tests = [
        test_basic_pair,
        test_four_directions,
        test_three_same_color,
        test_three_in_one_click,
        test_no_match,
        test_not_empty_cell,
        test_mixed_colors,
        test_isolation_v1_even,
        test_isolation_v1_odd,
        test_best_click_picks_highest_gain,
        test_no_valid_click,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {t.__name__}: {e}")
            failed += 1
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
