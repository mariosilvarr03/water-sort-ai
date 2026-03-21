"""Search algorithms for Water Sort.

Includes uninformed search methods used in the project:
- BFS
- DFS (depth-limited)
- IDDFS
- Uniform Cost Search (UCS)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from time import perf_counter

from project import Move, State, apply_move, is_goal, valid_moves


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


def bfs(initial_state: State, capacity: int) -> SearchResult:
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


def dfs(initial_state: State, capacity: int, depth_limit: int = 30) -> SearchResult:
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


def iddfs(initial_state: State, capacity: int, max_depth: int = 30) -> SearchResult:
    """Run iterative deepening DFS up to max_depth."""
    start_time = perf_counter()

    if is_goal(initial_state, capacity):
        return _solved_initial_result(start_time, initial_state)

    expanded_total = 0
    generated_total = 1
    max_frontier_overall = 1
    max_visited_overall = 1

    for depth_limit in range(max_depth + 1):
        found, moves, final_state, expanded_i, generated_i, max_frontier_i, max_visited_i = _depth_limited_search(
            initial_state,
            capacity,
            depth_limit,
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


def ucs(initial_state: State, capacity: int) -> SearchResult:
    """Run Uniform Cost Search (unit-cost moves in Water Sort)."""
    start_time = perf_counter()

    if is_goal(initial_state, capacity):
        return _solved_initial_result(start_time, initial_state)

    tie = count()
    frontier: list[tuple[int, int, State]] = []
    heappush(frontier, (0, next(tie), initial_state))

    best_cost: dict[State, int] = {initial_state: 0}
    parents: dict[State, tuple[State | None, Move | None]] = {initial_state: (None, None)}

    expanded = 0
    generated = 1
    max_frontier = 1
    max_visited = 1

    while frontier:
        cost, _, current = heappop(frontier)

        if cost != best_cost.get(current):
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
            new_cost = cost + 1

            if new_cost < best_cost.get(nxt, 10**12):
                best_cost[nxt] = new_cost
                parents[nxt] = (current, move)
                heappush(frontier, (new_cost, next(tie), nxt))
                generated += 1

        if len(frontier) > max_frontier:
            max_frontier = len(frontier)
        if len(best_cost) > max_visited:
            max_visited = len(best_cost)

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
) -> tuple[bool, list[Move], State | None, int, int, int, int]:
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

    def dls(state: State, depth: int) -> bool:
        nonlocal expanded, generated, max_frontier, final_moves, final_state

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

