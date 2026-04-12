# Water Sort AI

Water Sort game project with Human and AI modes, implemented in Python with Pygame.

![watersort_image1](images\image1_watersort.png)

![watersort_image2](images\image2_watersort.png)

## How to start the game

### 1. Requirements

- Python 3.11+ (recommended)
- Pygame

### 2. Install dependencies

In a terminal, inside the project folder:

```powershell
python -m pip install pygame
```

If you are using a virtual environment on Windows:

```powershell
.\.venv-win\Scripts\python.exe -m pip install pygame
```

### 3. Run the game

From the project root:

```powershell
python water-sort.py
```

Or, if you use the project's virtual environment:

```powershell
.\.venv-win\Scripts\python.exe water-sort.py
```

## How to play

## Objective

Sort the colors so that every non-empty tube is full and single-color.

## Move rules

You can pour from a source tube into a destination tube only when:

- the source tube is not empty
- the destination tube is not full
- the destination is empty or its top color matches the source top color

The game automatically pours the largest possible contiguous top block.

## Game modes

### Human mode

- Click Human
- Click a tube to select the source
- Click another tube to attempt the move
- Hint: suggests the next move
- Undo: reverts the last move

### AI mode

- Click AI
- Choose the algorithm in Algorithm
- For informed algorithms, choose the heuristic in Heuristic
- For W-A*, choose the weight in Weight
- Click Run AI to let the AI solve the board

Available algorithms:

- BFS
- DFS
- IDDFS
- GREEDY
- A*
- W-A*

## Difficulty

The Difficulty button cycles through:

- Level 1 (6 tubes)
- Level 2 (8 tubes)
- Level 3 (10 tubes)

## Keyboard shortcuts

- Space: reset to the initial board
- Enter: generate a new board
- B: run benchmark on the current state (output in console)

## Notes

- The current game state is shown in the Status field in the interface.
- Algorithm metrics are printed in the command line console.
