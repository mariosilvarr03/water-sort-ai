"""Core Water Sort logic, independent from any UI framework.

State representation:
- A state is a tuple of tubes.
- Each tube is a tuple ordered from bottom to top.
- Example: ((0, 1, 1), (2,), (), ())
"""

from __future__ import annotations

from typing import Iterable, Sequence, TypeAlias

Color: TypeAlias = int | str
Tube: TypeAlias = tuple[Color, ...]
State: TypeAlias = tuple[Tube, ...]
Move: TypeAlias = tuple[int, int]


def to_state(raw_state: Iterable[Iterable[Color]]) -> State:
    """Convert nested iterables to the immutable State format."""
    return tuple(tuple(tube) for tube in raw_state)


def is_goal(state: State, capacity: int) -> bool:
    """Return True when every non-empty tube is full and monochromatic."""
    _validate_capacity(capacity)
    _validate_state(state, capacity)

    for tube in state:
        if not tube:
            continue
        if len(tube) != capacity:
            return False
        if len(set(tube)) != 1:
            return False
    return True


def valid_moves(state: State, capacity: int) -> list[Move]:
    """Return all legal moves as (source_index, destination_index)."""
    _validate_capacity(capacity)
    _validate_state(state, capacity)

    moves: list[Move] = []
    for src in range(len(state)):
        for dst in range(len(state)):
            if src == dst:
                continue
            if _can_pour(state[src], state[dst], capacity):
                moves.append((src, dst))
    return moves


def apply_move(state: State, move: Move, capacity: int) -> State:
    """Apply one legal move and return a new state.

    The pour follows Water Sort behavior:
    - You can only pour from non-empty source to non-full destination.
    - Destination must be empty or have the same top color.
    - Pour as many top blocks of the same color as possible until destination is full.
    """
    _validate_capacity(capacity)
    _validate_state(state, capacity)

    src_idx, dst_idx = move
    if src_idx == dst_idx:
        raise ValueError("Source and destination must be different tubes.")
    if not (0 <= src_idx < len(state)) or not (0 <= dst_idx < len(state)):
        raise IndexError("Tube index out of range.")

    src_tube = state[src_idx]
    dst_tube = state[dst_idx]
    if not _can_pour(src_tube, dst_tube, capacity):
        raise ValueError(f"Illegal move: {move}")

    color = src_tube[-1]
    run_length = _top_run_length(src_tube)
    free_slots = capacity - len(dst_tube)
    amount = min(run_length, free_slots)

    moved = (color,) * amount
    new_src = src_tube[:-amount]
    new_dst = dst_tube + moved

    new_state = list(state)
    new_state[src_idx] = new_src
    new_state[dst_idx] = new_dst
    return tuple(new_state)


def _can_pour(src_tube: Tube, dst_tube: Tube, capacity: int) -> bool:
    if not src_tube:
        return False
    if len(dst_tube) >= capacity:
        return False
    return not dst_tube or dst_tube[-1] == src_tube[-1]


def _top_run_length(tube: Sequence[Color]) -> int:
    """Count consecutive equal colors from the top of a tube."""
    if not tube:
        return 0
    top = tube[-1]
    n = 1
    for idx in range(len(tube) - 2, -1, -1):
        if tube[idx] != top:
            break
        n += 1
    return n


def _validate_capacity(capacity: int) -> None:
    if capacity <= 0:
        raise ValueError("Tube capacity must be greater than zero.")


def _validate_state(state: State, capacity: int) -> None:
    for i, tube in enumerate(state):
        if len(tube) > capacity:
            raise ValueError(f"Tube {i} exceeds capacity {capacity}.")
