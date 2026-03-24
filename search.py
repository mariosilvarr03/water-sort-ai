"""Search algorithms for Water Sort.

Includes uninformed search methods used in the project:
- BFS
- DFS (depth-limited)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
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

