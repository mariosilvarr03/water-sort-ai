"""Search algorithms for Water Sort.

Includes uninformed and informed search methods used in the project:
- BFS
- DFS (depth-limited)
- IDDFS
- Greedy Best-First Search
- A*
- Weighted A*
"""

from __future__ import annotations

import tracemalloc
from collections import deque
from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from time import perf_counter
from typing import Callable, Literal, TypeAlias

from project import Move, State, apply_move, is_goal, valid_moves

HeuristicFn: TypeAlias = Callable[[State, int], float]


@dataclass(slots=True)
class SearchResult:
    solved: bool
    moves: list[Move]
    expanded: int
    generated: int
    max_frontier: int
    max_visited: int
    time_sec: float
    final_state: State | None = None
    timed_out: bool = False
    peak_memory_kb: float = 0.0



def _track_memory(fn):
    """Decorator: measures peak heap memory during a search call."""
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        tracemalloc.start()
        try:
            result = fn(*args, **kwargs)
        finally:
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
        result.peak_memory_kb = peak / 1024
        return result

    return wrapper


def h_color_boundaries(state: State, capacity: int) -> int:
    """Lower bound based on color transitions inside tubes.

    Each adjacent color change inside a tube creates one boundary.
    A single move can remove at most one such boundary, so this is admissible.
    """
    del capacity  # Unused but kept for a consistent heuristic signature.

    boundaries = 0
    for tube in state:
        for idx in range(1, len(tube)):
            if tube[idx] != tube[idx - 1]:
                boundaries += 1
    return boundaries


def h_split_colors(state: State, capacity: int) -> int:
    """Lower bound based on color dispersion across tubes.

    For each color appearing in k different tubes, at least (k - 1) merges
    are needed to gather that color into one tube. Summing over colors gives
    an admissible lower bound.
    """
    del capacity  # Unused but kept for a consistent heuristic signature.

    color_to_tubes: dict[int | str, set[int]] = {}
    for tube_idx, tube in enumerate(state):
        for color in set(tube):
            color_to_tubes.setdefault(color, set()).add(tube_idx)

    return sum(len(tubes) - 1 for tubes in color_to_tubes.values())


HEURISTICS: dict[str, HeuristicFn] = {
    "h_color_boundaries": h_color_boundaries,
    "h_split_colors": h_split_colors,
}

DEFAULT_HEURISTIC = "h_split_colors"


def available_heuristics() -> tuple[str, ...]:
    """Return the list of heuristic names available to informed searches."""
    return tuple(HEURISTICS.keys())


def _time_limit_reached(start_time: float, time_limit_sec: float | None) -> bool:
    if time_limit_sec is None:
        return False
    return (perf_counter() - start_time) >= time_limit_sec


@_track_memory
def bfs(initial_state: State, capacity: int, time_limit_sec: float | None = None) -> SearchResult:
    """Run breadth-first search from an initial Water Sort state."""
    start_time = perf_counter()

    if is_goal(initial_state, capacity):
        return _solved_initial_result(start_time, initial_state)

    frontier = deque([initial_state])
    parents: dict[State, tuple[State | None, Move | None]] = {initial_state: (None, None)}

    expanded = 0
    generated = 1
    max_frontier = 1
    max_visited = 1

    while frontier:
        if _time_limit_reached(start_time, time_limit_sec):
            elapsed = perf_counter() - start_time
            return SearchResult(
                solved=False,
                moves=[],
                expanded=expanded,
                generated=generated,
                max_frontier=max_frontier,
                max_visited=max_visited,
                time_sec=elapsed,
                final_state=None,
                timed_out=True,
            )

        current = frontier.popleft()
        expanded += 1

        for move in valid_moves(current, capacity):
            nxt = apply_move(current, move, capacity)
            if nxt in parents:
                continue

            parents[nxt] = (current, move)
            generated += 1
            frontier.append(nxt)

            if is_goal(nxt, capacity):
                elapsed = perf_counter() - start_time
                return SearchResult(
                    solved=True,
                    moves=_reconstruct_path(parents, nxt),
                    expanded=expanded,
                    generated=generated,
                    max_frontier=max(max_frontier, len(frontier)),
                    max_visited=max(max_visited, len(parents)),
                    time_sec=elapsed,
                    final_state=nxt,
                )

        if len(frontier) > max_frontier:
            max_frontier = len(frontier)
        if len(parents) > max_visited:
            max_visited = len(parents)

    elapsed = perf_counter() - start_time
    return SearchResult(
        solved=False,
        moves=[],
        expanded=expanded,
        generated=generated,
        max_frontier=max_frontier,
        max_visited=max_visited,
        time_sec=elapsed,
        final_state=None,
    )


@_track_memory
def dfs(initial_state: State, capacity: int, depth_limit: int = 30, time_limit_sec: float | None = None) -> SearchResult:
    """Run depth-first search with a depth limit."""
    start_time = perf_counter()

    if is_goal(initial_state, capacity):
        return _solved_initial_result(start_time, initial_state)

    stack: list[tuple[State, int]] = [(initial_state, 0)]
    parents: dict[State, tuple[State | None, Move | None]] = {initial_state: (None, None)}
    seen_depth: dict[State, int] = {initial_state: 0}

    expanded = 0
    generated = 1
    max_frontier = 1
    max_visited = 1

    while stack:
        if _time_limit_reached(start_time, time_limit_sec):
            elapsed = perf_counter() - start_time
            return SearchResult(
                solved=False,
                moves=[],
                expanded=expanded,
                generated=generated,
                max_frontier=max_frontier,
                max_visited=max_visited,
                time_sec=elapsed,
                final_state=None,
                timed_out=True,
            )

        current, depth = stack.pop()

        if is_goal(current, capacity):
            elapsed = perf_counter() - start_time
            return SearchResult(
                solved=True,
                moves=_reconstruct_path(parents, current),
                expanded=expanded,
                generated=generated,
                max_frontier=max_frontier,
                max_visited=max_visited,
                time_sec=elapsed,
                final_state=current,
            )

        if depth >= depth_limit:
            continue

        expanded += 1
        moves = _ordered_moves_for_dfs(current, capacity)

        # Reverse to preserve natural left-to-right exploration when using stack.
        for move in reversed(moves):
            nxt = apply_move(current, move, capacity)
            next_depth = depth + 1

            best_depth = seen_depth.get(nxt)
            if best_depth is not None and best_depth <= next_depth:
                continue

            seen_depth[nxt] = next_depth
            parents[nxt] = (current, move)
            stack.append((nxt, next_depth))
            generated += 1

        if len(stack) > max_frontier:
            max_frontier = len(stack)
        if len(seen_depth) > max_visited:
            max_visited = len(seen_depth)

    elapsed = perf_counter() - start_time
    return SearchResult(
        solved=False,
        moves=[],
        expanded=expanded,
        generated=generated,
        max_frontier=max_frontier,
        max_visited=max_visited,
        time_sec=elapsed,
        final_state=None,
    )


@_track_memory
def iddfs(initial_state: State, capacity: int, max_depth: int = 30, time_limit_sec: float | None = None) -> SearchResult:
    """Run iterative deepening DFS up to max_depth."""
    start_time = perf_counter()

    if is_goal(initial_state, capacity):
        return _solved_initial_result(start_time, initial_state)

    expanded_total = 0
    generated_total = 1
    max_frontier_overall = 1
    max_visited_overall = 1

    for depth_limit in range(max_depth + 1):
        if _time_limit_reached(start_time, time_limit_sec):
            elapsed = perf_counter() - start_time
            return SearchResult(
                solved=False,
                moves=[],
                expanded=expanded_total,
                generated=generated_total,
                max_frontier=max_frontier_overall,
                max_visited=max_visited_overall,
                time_sec=elapsed,
                final_state=None,
                timed_out=True,
            )

        found, moves, final_state, expanded_i, generated_i, max_frontier_i, max_visited_i, timed_out_i = _depth_limited_search(
            initial_state,
            capacity,
            depth_limit,
            start_time,
            time_limit_sec,
        )

        expanded_total += expanded_i
        generated_total += generated_i
        max_frontier_overall = max(max_frontier_overall, max_frontier_i)
        max_visited_overall = max(max_visited_overall, max_visited_i)

        if found:
            elapsed = perf_counter() - start_time
            return SearchResult(
                solved=True,
                moves=moves,
                expanded=expanded_total,
                generated=generated_total,
                max_frontier=max_frontier_overall,
                max_visited=max_visited_overall,
                time_sec=elapsed,
                final_state=final_state,
            )

        if timed_out_i:
            elapsed = perf_counter() - start_time
            return SearchResult(
                solved=False,
                moves=[],
                expanded=expanded_total,
                generated=generated_total,
                max_frontier=max_frontier_overall,
                max_visited=max_visited_overall,
                time_sec=elapsed,
                final_state=None,
                timed_out=True,
            )

    elapsed = perf_counter() - start_time
    return SearchResult(
        solved=False,
        moves=[],
        expanded=expanded_total,
        generated=generated_total,
        max_frontier=max_frontier_overall,
        max_visited=max_visited_overall,
        time_sec=elapsed,
        final_state=None,
    )


@_track_memory
def greedy(
    initial_state: State,
    capacity: int,
    heuristic: str | HeuristicFn = DEFAULT_HEURISTIC,
    time_limit_sec: float | None = None,
) -> SearchResult:
    """Run Greedy Best-First Search using f(n) = h(n)."""
    return _best_first_search(
        initial_state=initial_state,
        capacity=capacity,
        heuristic=heuristic,
        mode="greedy",
        weight=1.0,
        time_limit_sec=time_limit_sec,
    )


@_track_memory
def astar(
    initial_state: State,
    capacity: int,
    heuristic: str | HeuristicFn = DEFAULT_HEURISTIC,
    time_limit_sec: float | None = None,
) -> SearchResult:
    """Run A* using f(n) = g(n) + h(n)."""
    return _best_first_search(
        initial_state=initial_state,
        capacity=capacity,
        heuristic=heuristic,
        mode="astar",
        weight=1.0,
        time_limit_sec=time_limit_sec,
    )


@_track_memory
def weighted_astar(
    initial_state: State,
    capacity: int,
    heuristic: str | HeuristicFn = DEFAULT_HEURISTIC,
    weight: float = 1.5,
    time_limit_sec: float | None = None,
) -> SearchResult:
    """Run Weighted A* using f(n) = g(n) + w*h(n), with w >= 1."""
    if weight < 1.0:
        raise ValueError("Weighted A* requires weight >= 1.0.")

    return _best_first_search(
        initial_state=initial_state,
        capacity=capacity,
        heuristic=heuristic,
        mode="weighted_astar",
        weight=weight,
        time_limit_sec=time_limit_sec,
    )


def _ordered_moves_for_dfs(state: State, capacity: int) -> list[Move]:
    """Return DFS moves ordered and pruned to reduce obvious useless actions."""
    raw_moves = valid_moves(state, capacity)
    if not raw_moves:
        return []

    empty_indices = [idx for idx, tube in enumerate(state) if not tube]
    canonical_empty = empty_indices[0] if empty_indices else None

    ranked: list[tuple[int, Move]] = []
    for move in raw_moves:
        if _is_useless_move_for_dfs(state, move, capacity, canonical_empty):
            continue

        src, dst = move
        src_tube = state[src]
        dst_tube = state[dst]

        rank = 0

        # Prefer merging into a non-empty tube.
        if not dst_tube:
            rank += 10

        # Prefer moving from mixed tubes before relocating pure tubes.
        if _is_uniform_tube(src_tube):
            rank += 2

        ranked.append((rank, move))

    if not ranked:
        # Fallback to keep completeness if all moves were pruned.
        return raw_moves

    ranked.sort(key=lambda item: (item[0], item[1][0], item[1][1]))
    return [move for _, move in ranked]


def _is_useless_move_for_dfs(
    state: State,
    move: Move,
    capacity: int,
    canonical_empty: int | None,
) -> bool:
    src, dst = move
    src_tube = state[src]
    dst_tube = state[dst]

    # Keep complete single-color tubes untouched.
    if len(src_tube) == capacity and _is_uniform_tube(src_tube):
        return True

    if not dst_tube:
        # Avoid symmetric copies when there are multiple empty tubes.
        if canonical_empty is not None and dst != canonical_empty:
            return True

        # Moving a fully uniform tube into an empty tube is usually a pure relocation.
        if _is_uniform_tube(src_tube):
            return True

    return False


def _is_uniform_tube(tube: tuple) -> bool:
    return bool(tube) and len(set(tube)) == 1


def _depth_limited_search(
    initial_state: State,
    capacity: int,
    depth_limit: int,
    start_time: float,
    time_limit_sec: float | None,
) -> tuple[bool, list[Move], State | None, int, int, int, int, bool]:
    """Single DLS pass used by IDDFS."""
    path_states: set[State] = {initial_state}
    path_moves: list[Move] = []
    seen_iter: set[State] = {initial_state}
    best_depth_iter: dict[State, int] = {initial_state: 0}

    expanded = 0
    generated = 0
    max_frontier = 1

    final_moves: list[Move] | None = None
    final_state: State | None = None
    timed_out = False

    def dls(state: State, depth: int) -> bool:
        nonlocal expanded, generated, max_frontier, final_moves, final_state, timed_out

        if _time_limit_reached(start_time, time_limit_sec):
            timed_out = True
            return False

        if is_goal(state, capacity):
            final_moves = list(path_moves)
            final_state = state
            return True

        if depth >= depth_limit:
            return False

        expanded += 1

        for move in _ordered_moves_for_dfs(state, capacity):
            nxt = apply_move(state, move, capacity)
            next_depth = depth + 1

            if nxt in path_states:
                continue

            best_known = best_depth_iter.get(nxt)
            if best_known is not None and best_known <= next_depth:
                continue

            best_depth_iter[nxt] = next_depth
            generated += 1
            path_states.add(nxt)
            seen_iter.add(nxt)
            path_moves.append(move)

            if len(path_states) > max_frontier:
                max_frontier = len(path_states)

            if dls(nxt, next_depth):
                return True

            path_moves.pop()
            path_states.remove(nxt)

        return False

    found = dls(initial_state, 0)
    return (
        found,
        final_moves if final_moves is not None else [],
        final_state,
        expanded,
        generated,
        max_frontier,
        len(seen_iter),
        timed_out,
    )


def _solved_initial_result(start_time: float, initial_state: State) -> SearchResult:
    elapsed = perf_counter() - start_time
    return SearchResult(
        solved=True,
        moves=[],
        expanded=0,
        generated=1,
        max_frontier=1,
        max_visited=1,
        time_sec=elapsed,
        final_state=initial_state,
    )


def _reconstruct_path(
    parents: dict[State, tuple[State | None, Move | None]],
    goal_state: State,
) -> list[Move]:
    """Rebuild the move sequence from start to goal using parent links."""
    path: list[Move] = []
    current = goal_state

    while True:
        parent, move = parents[current]
        if parent is None or move is None:
            break
        path.append(move)
        current = parent

    path.reverse()
    return path


def _resolve_heuristic(heuristic: str | HeuristicFn) -> HeuristicFn:
    if callable(heuristic):
        return heuristic

    fn = HEURISTICS.get(heuristic)
    if fn is None:
        names = ", ".join(available_heuristics())
        raise ValueError(f"Unknown heuristic '{heuristic}'. Available: {names}")
    return fn


def _priority(mode: Literal["greedy", "astar", "weighted_astar"], g: int, h: float, weight: float) -> float:
    if mode == "greedy":
        return h
    if mode == "astar":
        return g + h
    return g + weight * h


def _best_first_search(
    initial_state: State,
    capacity: int,
    heuristic: str | HeuristicFn,
    mode: Literal["greedy", "astar", "weighted_astar"],
    weight: float,
    time_limit_sec: float | None = None,
) -> SearchResult:
    """Shared engine for Greedy, A*, and Weighted A*."""
    start_time = perf_counter()
    heuristic_fn = _resolve_heuristic(heuristic)

    if is_goal(initial_state, capacity):
        return _solved_initial_result(start_time, initial_state)

    tie = count()
    frontier: list[tuple[float, int, int, State]] = []
    parents: dict[State, tuple[State | None, Move | None]] = {initial_state: (None, None)}
    best_g: dict[State, int] = {initial_state: 0}

    initial_h = heuristic_fn(initial_state, capacity)
    heappush(frontier, (_priority(mode, 0, initial_h, weight), next(tie), 0, initial_state))

    expanded = 0
    generated = 1
    max_frontier = 1
    max_visited = 1

    while frontier:
        if _time_limit_reached(start_time, time_limit_sec):
            elapsed = perf_counter() - start_time
            return SearchResult(
                solved=False,
                moves=[],
                expanded=expanded,
                generated=generated,
                max_frontier=max_frontier,
                max_visited=max_visited,
                time_sec=elapsed,
                final_state=None,
                timed_out=True,
            )

        _, _, queued_g, current = heappop(frontier)

        current_g = best_g.get(current)
        if current_g is None or queued_g != current_g:
            continue

        if is_goal(current, capacity):
            elapsed = perf_counter() - start_time
            return SearchResult(
                solved=True,
                moves=_reconstruct_path(parents, current),
                expanded=expanded,
                generated=generated,
                max_frontier=max_frontier,
                max_visited=max_visited,
                time_sec=elapsed,
                final_state=current,
            )

        expanded += 1

        for move in valid_moves(current, capacity):
            nxt = apply_move(current, move, capacity)
            new_g = current_g + 1

            if new_g >= best_g.get(nxt, 10**12):
                continue

            best_g[nxt] = new_g
            parents[nxt] = (current, move)
            h = heuristic_fn(nxt, capacity)
            f = _priority(mode, new_g, h, weight)
            heappush(frontier, (f, next(tie), new_g, nxt))
            generated += 1

        if len(frontier) > max_frontier:
            max_frontier = len(frontier)
        if len(best_g) > max_visited:
            max_visited = len(best_g)

    elapsed = perf_counter() - start_time
    return SearchResult(
        solved=False,
        moves=[],
        expanded=expanded,
        generated=generated,
        max_frontier=max_frontier,
        max_visited=max_visited,
        time_sec=elapsed,
        final_state=None,
    )


def run_benchmark(
    initial_state: "State",
    capacity: int,
    heuristic: str = DEFAULT_HEURISTIC,
    weight: float = 1.5,
    time_limit_sec: float = 60.0,
) -> None:
    """Run all algorithms on the same state and print a comparison table."""
    entries = [
        ("BFS", lambda s, c: bfs(s, c, time_limit_sec=time_limit_sec)),
        ("DFS", lambda s, c: dfs(s, c, time_limit_sec=time_limit_sec)),
        ("IDDFS", lambda s, c: iddfs(s, c, time_limit_sec=time_limit_sec)),
        (f"Greedy({heuristic})", lambda s, c: greedy(s, c, heuristic=heuristic, time_limit_sec=time_limit_sec)),
        (f"A*({heuristic})", lambda s, c: astar(s, c, heuristic=heuristic, time_limit_sec=time_limit_sec)),
        (f"W-A*(w={weight:.1f},{heuristic})", lambda s, c: weighted_astar(s, c, heuristic=heuristic, weight=weight, time_limit_sec=time_limit_sec)),
    ]
    c0,c1,c2,c3,c4,c5,c6 = 34,9,7,11,11,10,10
    hdr = (f"{'Algorithm':<{c0}} {'Solved':>{c1}} {'Moves':>{c2}}"
           f" {'Expanded':>{c3}} {'Generated':>{c4}}"
           f" {'Mem(KB)':>{c5}} {'Time(s)':>{c6}}")
    sep = '-' * len(hdr)
    print()
    print("===== BENCHMARK =====")
    print(hdr)
    print(sep)
    for name, fn in entries:
        r = fn(initial_state, capacity)
        status = "Yes" if r.solved else ("Timeout" if r.timed_out else "No")
        mv = str(len(r.moves)) if r.solved else "-"
        print(f"{name:<{c0}} {status:>{c1}} {mv:>{c2}}"
              f" {r.expanded:>{c3}} {r.generated:>{c4}}"
              f" {r.peak_memory_kb:>{c5}.1f} {r.time_sec:>{c6}.4f}")
    print(sep)
    print()
