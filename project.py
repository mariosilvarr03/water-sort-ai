"""Minimal Water Sort core logic for milestone 0.

This module defines the immutable game state, move generation, move
application and basic parsing/printing utilities.  It's intentionally
small so we can unit‑test the foundation before adding search.

State:
    tuple of tubes where each tube is a tuple of colors (bottom->top).
    Colors are single-character strings (e.g. 'A', 'B').  An empty tube
    is represented by an empty tuple.  Capacity is held separately.

Moves are represented as a pair (src, dst) of tube indices.  The amount
poured is determined by the rules and recomputed during application.

Example usage (run as script) will self‑test a few tiny puzzles.
"""

from __future__ import annotations

from pathlib import Path
from collections import deque
from dataclasses import dataclass
from typing import List, Tuple, Iterable, Optional
import heapq
import itertools
import time
from typing import Dict

Tube = Tuple[str, ...]          # bottom -> top
State = Tuple[Tube, ...]
Move = Tuple[int, int]          # (src_index, dst_index)


# --- Core model -----------------------------------------------------------


def is_goal(state: State, capacity: int) -> bool:
    """Goal: every tube is empty OR full and uniform."""
    for tube in state:
        if len(tube) == 0:
            continue
        if len(tube) != capacity:
            return False
        if len(set(tube)) != 1:
            return False
    return True


def _top_color(tube: Tube) -> Optional[str]:
    return tube[-1] if tube else None


def _contiguous_top_block(tube: Tube) -> int:
    """Return length of contiguous block of same-color pieces at top."""
    if not tube:
        return 0
    top = tube[-1]
    count = 0
    for c in reversed(tube):
        if c == top:
            count += 1
        else:
            break
    return count


def legal_moves(state: State, capacity: int) -> List[Move]:
    """Return all legal pours (src, dst) from given state.

    The returned moves exclude those that pour zero units or would
    leave the source unchanged.
    """
    n = len(state)
    moves: List[Move] = []
    for i in range(n):
        tube_i = state[i]
        if not tube_i:
            continue
        top_i = _top_color(tube_i)
        block_len = _contiguous_top_block(tube_i)
        for j in range(n):
            if i == j:
                continue
            tube_j = state[j]
            if len(tube_j) >= capacity:
                continue
            # can pour if dst empty or same top color
            if tube_j and _top_color(tube_j) != top_i:
                continue
            space = capacity - len(tube_j)
            amount = min(block_len, space)
            if amount > 0:
                moves.append((i, j))
    return moves


def apply_move(state: State, move: Move, capacity: int) -> State:
    """Return new state after applying the move.

    Move is (src, dst); amount to pour is computed according to rules.
    """
    src, dst = move
    tubes = list(map(list, state))  # make mutable copies

    if src == dst:
        raise ValueError("src and dst must differ")
    if not tubes[src]:
        raise ValueError("cannot pour from empty tube")
    if len(tubes[dst]) >= capacity:
        raise ValueError("cannot pour into full tube")

    top_color = tubes[src][-1]
    # count contiguous same color on top of src
    block = 0
    for c in reversed(tubes[src]):
        if c == top_color:
            block += 1
        else:
            break
    space = capacity - len(tubes[dst])
    amount = min(block, space)
    
    if amount <= 0:
        raise ValueError("move results in zero pour")
    # perform pour
    for _ in range(amount):
        tubes[dst].append(tubes[src].pop())

    # convert back to immutable
    return tuple(tuple(t) for t in tubes)


def normalize(state: State) -> State:
    """Optional canonicalization: sort empty tubes to the end.

    This is handy for hashing since empty tubes are interchangeable.
    
    empties = [tube for tube in state if len(tube) == 0]
    nonempties = [tube for tube in state if len(tube) > 0]
    return tuple(nonempties + empties)"""
    # For now, just return as-is (no normalization).
    return state


# --- Parsing / printing ---------------------------------------------------


def parse_puzzle(lines: Iterable[str]) -> Tuple[State, int]:
    """Build a state from lines of the file plus return capacity.

    Lines beginning with '#' are ignored.  Each other line corresponds to
    a tube, tokens separated by whitespace.  A dot (.) denotes an empty
    position; explicit empties may be omitted if tube shorter than
    capacity.  All tubes must have the same number of tokens or fewer.
    The declared capacity is the maximum tokens seen on any non-comment
    line.  We'll treat missing tokens as empties, which translate to
    truncation since our representation omits empties.
    """
    tubes: List[Tube] = []
    cap = 0
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        tokens = line.split()
        cap = max(cap, len(tokens))
        # remove dots
        tube = tuple(tok for tok in tokens if tok != ".")
        tubes.append(tube)
    # ensure all tubes <= cap
    for tube in tubes:
        if len(tube) > cap:
            raise ValueError("tube longer than capacity")
    return tuple(tubes), cap


def state_to_string(state: State, capacity: int) -> str:
    """Render state as multiline string (bottom->top)."""
    lines: List[str] = []
    for tube in state:
        elems = list(tube)
        # pad with dots for empty slots
        elems += ["."] * (capacity - len(elems))
        lines.append(" ".join(elems))
    return "\n".join(lines)


# --- Utility helpers -----------------------------------------------------

def state_stats(state: State, capacity: int) -> Tuple[int, int, int]:
    """Return (tubes, capacity, distinct_colors) for a given state."""
    tubes = len(state)
    colors = {c for tube in state for c in tube}
    return tubes, capacity, len(colors)


# --- Search framework ----------------------------------------------------

import time


@dataclass
class SearchResult:
    solved: bool
    moves: List[Move]
    expanded: int
    generated: int
    max_frontier: int
    max_visited: int
    time_sec: float


def bfs(initial: State, capacity: int) -> SearchResult:
    """Breadth-first search from **initial** state using global functions.

    The search records simple metrics and returns a SearchResult.  Costs are
    uniform (1 per move) so BFS also finds a shortest-move solution.
    """
    start = time.perf_counter()
    frontier = deque([normalize(initial)])
    visited = {normalize(initial)}
    parent: dict[State, Optional[State]] = {normalize(initial): None}
    action: dict[State, Move] = {}

    expanded = 0
    generated = 0
    max_frontier = 1
    max_visited = 1

    solution_state: Optional[State] = None

    while frontier:
        if len(frontier) > max_frontier:
            max_frontier = len(frontier)
        current = frontier.popleft()
        expanded += 1
        if is_goal(current, capacity):
            solution_state = current
            break
        for mv in legal_moves(current, capacity):
            child = normalize(apply_move(current, mv, capacity))
            generated += 1
            key = normalize(child)
            if key in visited:
                continue
            visited.add(key)
            parent[key] = normalize(current)
            action[key] = mv
            frontier.append(child)
        if len(visited) > max_visited:
            max_visited = len(visited)
    end = time.perf_counter()

    moves: List[Move] = []
    if solution_state is not None:
        # reconstruct from parent/action
        key = normalize(solution_state)
        while parent[key] is not None:
            moves.append(action[key])
            key = parent[key]
        moves.reverse()
    return SearchResult(
        solved=(solution_state is not None),
        moves=moves,
        expanded=expanded,
        generated=generated,
        max_frontier=max_frontier,
        max_visited=max_visited,
        time_sec=end - start,
    )

def ucs(initial: State, capacity: int) -> SearchResult:
    """Uniform Cost Search (Dijkstra) with unit move costs.

    Even though each move costs 1 (so UCS ~= BFS), we implement it properly
    because A* will reuse this structure.

    Metrics:
      - expanded: #states popped for expansion
      - generated: #children generated
      - max_frontier: peak heap size
      - max_visited: peak size of best_g (i.e., discovered states)
    """
    start = time.perf_counter()

    # Priority queue entries: (g, tie, state)
    pq: List[tuple[int, int, State]] = []
    tie = itertools.count()

    heapq.heappush(pq, (0, next(tie), initial))

    # best known cost to reach state
    best_g: Dict[State, int] = {initial: 0}

    # parent pointers for solution reconstruction
    parent: Dict[State, Optional[State]] = {initial: None}
    action: Dict[State, Move] = {}

    expanded = 0
    generated = 0
    max_frontier = 1
    max_visited = 1

    solution_state: Optional[State] = None

    while pq:
        max_frontier = max(max_frontier, len(pq))

        g, _, current = heapq.heappop(pq)

        # Skip stale heap entries (we already found a cheaper path)
        if g != best_g.get(current, float("inf")):
            continue

        expanded += 1

        if is_goal(current, capacity):
            solution_state = current
            break

        for mv in legal_moves(current, capacity):
            child = apply_move(current, mv, capacity)
            generated += 1

            new_g = g + 1  # unit cost per move
            old_g = best_g.get(child)

            if old_g is None or new_g < old_g:
                best_g[child] = new_g
                parent[child] = current
                action[child] = mv
                heapq.heappush(pq, (new_g, next(tie), child))

        max_visited = max(max_visited, len(best_g))

    end = time.perf_counter()

    # Reconstruct solution
    moves: List[Move] = []
    if solution_state is not None:
        key = solution_state
        while parent[key] is not None:
            moves.append(action[key])
            key = parent[key]
        moves.reverse()

    return SearchResult(
        solved=(solution_state is not None),
        moves=moves,
        expanded=expanded,
        generated=generated,
        max_frontier=max_frontier,
        max_visited=max_visited,
        time_sec=end - start,
    )


def dfs(initial: State, capacity: int, depth_limit: Optional[int] = None) -> SearchResult:
    """Depth-First Search (optionally depth-limited).

    Uses path-checking (avoids cycles on the current path).
    If depth_limit is None, runs unbounded DFS (can be risky on larger puzzles).

    Returns the first solution found (not guaranteed optimal).
    """
    start = time.perf_counter()

    # Stack entries: (state, depth, path_set)
    # We store path_set to avoid cycles along the current path.
    stack: List[Tuple[State, int, set[State]]] = [(initial, 0, {initial})]

    # Parent/action maps for reconstruction
    parent: Dict[State, Optional[State]] = {initial: None}
    action: Dict[State, Move] = {}

    expanded = 0
    generated = 0
    max_frontier = 1
    max_visited = 1

    solution_state: Optional[State] = None

    while stack:
        max_frontier = max(max_frontier, len(stack))

        current, depth, path_set = stack.pop()
        expanded += 1

        if is_goal(current, capacity):
            solution_state = current
            break

        if depth_limit is not None and depth >= depth_limit:
            continue

        for mv in legal_moves(current, capacity):
            child = apply_move(current, mv, capacity)
            generated += 1

            # Path-checking (prevents loops like A->B->A)
            if child in path_set:
                continue

            if child not in parent:
                parent[child] = current
                action[child] = mv
                max_visited = max(max_visited, len(parent))

            # Child gets a new path set (copy) including itself
            new_path = set(path_set)
            new_path.add(child)
            stack.append((child, depth + 1, new_path))

    end = time.perf_counter()

    moves: List[Move] = []
    if solution_state is not None:
        key = solution_state
        while parent[key] is not None:
            moves.append(action[key])
            key = parent[key]
        moves.reverse()

    return SearchResult(
        solved=(solution_state is not None),
        moves=moves,
        expanded=expanded,
        generated=generated,
        max_frontier=max_frontier,
        max_visited=max_visited,
        time_sec=end - start,
    )

def iddfs(initial: State, capacity: int, max_depth: int) -> SearchResult:
    """Iterative Deepening DFS.

    Runs depth-limited DFS with limits 0..max_depth and returns the first solution.
    Metrics are accumulated across iterations.
    """
    start = time.perf_counter()

    total_expanded = 0
    total_generated = 0
    peak_frontier = 0
    peak_visited = 0

    best_solution: Optional[SearchResult] = None

    for limit in range(max_depth + 1):
        res = dfs(initial, capacity, depth_limit=limit)

        total_expanded += res.expanded
        total_generated += res.generated
        peak_frontier = max(peak_frontier, res.max_frontier)
        peak_visited = max(peak_visited, res.max_visited)

        if res.solved:
            best_solution = res
            break

    end = time.perf_counter()

    if best_solution is None:
        return SearchResult(
            solved=False,
            moves=[],
            expanded=total_expanded,
            generated=total_generated,
            max_frontier=peak_frontier,
            max_visited=peak_visited,
            time_sec=end - start,
        )

    # Use the found moves, but override metrics with totals
    return SearchResult(
        solved=True,
        moves=best_solution.moves,
        expanded=total_expanded,
        generated=total_generated,
        max_frontier=peak_frontier,
        max_visited=peak_visited,
        time_sec=end - start,
    )


# --- Simple self‑tests ----------------------------------------------------


def _test_core():
    # ---------- capacity 2 core sanity checks ----------
    cap2 = 2

    # Goal example: every non-empty tube is FULL and uniform (or empty)
    state_goal = (("A", "A"), ("B", "B"), (), ())
    assert is_goal(state_goal, cap2)

    # Pour into empty should be legal
    assert (0, 2) in legal_moves(state_goal, cap2)

    # Applying a move should update tubes correctly
    moved = apply_move(state_goal, (0, 2), cap2)
    assert moved == ((), ("B", "B"), ("A", "A"), ())
    assert is_goal(moved, cap2)

    # Non-goal: mixed colors in a non-empty tube
    bad = (("A", "B"), (), ("A", "A"), ())
    assert not is_goal(bad, cap2)

    # Blocked move check (but other moves may still exist!)
    state_blocked = (("A", "B"), ("A",), (), ())
    moves = legal_moves(state_blocked, cap2)
    assert (0, 1) not in moves  # src top B cannot pour onto dst top A
    assert (0, 2) in moves or (0, 3) in moves  # can pour into empty

    # ---------- parsing sanity (capacity 4) ----------
    raw = [
        "# comment",
        "A A B B",
        "B B A A",
        ". . . .",
        ". . . .",
    ]
    st, cap4 = parse_puzzle(raw)
    assert cap4 == 4
    assert st[0] == ("A", "A", "B", "B")
    assert st[2] == () and st[3] == ()

    # ---------- search sanity on a tiny solvable instance (capacity 2) ----------
    tiny = (("A", "B"), ("B", "A"), (), ())
    assert not is_goal(tiny, cap2)

    res_bfs = bfs(tiny, cap2)
    assert res_bfs.solved, f"BFS failed: {res_bfs}"
    assert is_goal(apply_moves(tiny, res_bfs.moves, cap2), cap2)

    res_ucs = ucs(tiny, cap2)
    assert res_ucs.solved, f"UCS failed: {res_ucs}"
    assert is_goal(apply_moves(tiny, res_ucs.moves, cap2), cap2)

    res_dfs = dfs(tiny, cap2, depth_limit=20)
    assert res_dfs.solved, f"DFS failed: {res_dfs}"
    assert is_goal(apply_moves(tiny, res_dfs.moves, cap2), cap2)

    res_id = iddfs(tiny, cap2, max_depth=20)
    assert res_id.solved, f"IDDFS failed: {res_id}"
    assert is_goal(apply_moves(tiny, res_id.moves, cap2), cap2)

    print("core tests passed")

## --- Puzzle loading and testing utilities ----------------------------------

def load_puzzle_file(path: str | Path) -> Tuple[State, int]:
    """Load a puzzle from a text file path."""
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        return parse_puzzle(f.readlines())


def apply_moves(state: State, moves: List[Move], capacity: int) -> State:
    """Apply a sequence of moves to a state (for verification/tests)."""
    for mv in moves:
        state = apply_move(state, mv, capacity)
    return state

def test_puzzles_folder(folder: str = "puzzles") -> None:
    """Load all .txt puzzles in a folder, run BFS, and verify solutions."""
    folder_path = Path(folder)
    if not folder_path.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path.resolve()}")

    puzzle_files = sorted(folder_path.glob("*.txt"))
    if not puzzle_files:
        raise FileNotFoundError(f"No .txt puzzle files found in {folder_path.resolve()}")

    print(f"Running BFS on {len(puzzle_files)} puzzles in {folder_path}...\n")

    failures = 0
    for file in puzzle_files:
        state, cap = load_puzzle_file(file)

        # Normalize once at start (optional, keeps consistency)
        state0 = normalize(state)

        res = bfs(state0, cap)

        if not res.solved:
            failures += 1
            print(f"❌ {file.name}: NOT SOLVED | expanded={res.expanded} generated={res.generated} time={res.time_sec:.4f}s")
            continue

        final_state = apply_moves(state0, res.moves, cap)
        ok = is_goal(final_state, cap)
        
        if not ok:
            failures += 1
            print(f"❌ {file.name}: SOLVER CLAIMED SOLVED but final state is not goal!")
            print("Final state:\n", state_to_string(final_state, cap))
        else:
            print(f"✅ {file.name}: moves={len(res.moves)} expanded={res.expanded} gen={res.generated} "
                  f"maxQ={res.max_frontier} visited={res.max_visited} time={res.time_sec:.4f}s")

        res_dfs = dfs(state0, cap, depth_limit=30)


        if res_dfs.solved:
            assert is_goal(apply_moves(state0, res_dfs.moves, cap), cap)
            print(f"   DFS: moves={len(res_dfs.moves)} expanded={res_dfs.expanded} time={res_dfs.time_sec:.4f}s")
        else:
            print(f"   DFS: NOT SOLVED (limit)")

        res_id = iddfs(state0, cap, max_depth=30)

        if res_id.solved:
            print(f"   IDDFS: moves={len(res_id.moves)} expanded={res_id.expanded} time={res_id.time_sec:.4f}s")
        else:
            print("   IDDFS: NOT SOLVED (max depth)")

    print("\nDone.")
    if failures:
        raise AssertionError(f"{failures} puzzle(s) failed.")


if __name__ == "__main__":
    _test_core()
    test_puzzles_folder("puzzles")   # change folder name if yours differs
    # _demo()