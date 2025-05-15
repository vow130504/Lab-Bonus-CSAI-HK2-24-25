import os
import time
import itertools
from pysat.solvers import Glucose3
from pysat.formula import CNF

def read_input(file_path):
    """Đọc lưới từ file input."""
    grid = []
    with open(file_path, 'r') as f:
        for line in f:
            row = line.strip().split(',')
            grid.append(row)
    return grid

def write_output(grid, file_path):
    """Ghi kết quả vào file output."""
    with open(file_path, 'w') as f:
        for row in grid:
            f.write(','.join(row) + '\n')

def get_neighbors(i, j, rows, cols):
    """Lấy các ô lân cận (8 ô xung quanh)."""
    neighbors = []
    for di in [-1, 0, 1]:
        for dj in [-1, 0, 1]:
            if di == 0 and dj == 0:
                continue
            ni, nj = i + di, j + dj
            if 0 <= ni < rows and 0 <= nj < cols:
                neighbors.append((ni, nj))
    return neighbors

def generate_cnf(grid):
    """Tạo các ràng buộc CNF."""
    rows, cols = len(grid), len(grid[0])
    cnf = CNF()
    var_map = {}  # Biến logic cho mỗi ô: (i,j) -> id
    var_count = 0

    # Gán biến logic cho các ô
    for i in range(rows):
        for j in range(cols):
            if grid[i][j] not in ['T', 'G']:
                var_count += 1
                var_map[(i, j)] = var_count
            elif grid[i][j] == 'T':
                var_map[(i, j)] = None  # Đã biết là bẫy
            elif grid[i][j] == 'G':
                var_map[(i, j)] = None  # Đã biết là ngọc

    # Tạo ràng buộc cho các ô có số
    for i in range(rows):
        for j in range(cols):
            if grid[i][j].isdigit():
                k = int(grid[i][j])
                neighbors = get_neighbors(i, j, rows, cols)
                neighbor_vars = [var_map.get((ni, nj)) for ni, nj in neighbors if var_map.get((ni, nj)) is not None]

                # Tạo tổ hợp để đảm bảo đúng k ô là bẫy
                for comb in itertools.combinations(range(len(neighbor_vars)), k + 1):
                    # Không quá k bẫy
                    clause = [-neighbor_vars[i] for i in comb]
                    cnf.append(clause)
                for comb in itertools.combinations(range(len(neighbor_vars)), len(neighbor_vars) - k + 1):
                    # Ít nhất k bẫy
                    clause = [neighbor_vars[i] for i in comb]
                    cnf.append(clause)

    return cnf, var_map, var_count

def solve_with_pysat(grid):
    """Giải bài toán bằng PySAT."""
    start_time = time.time()
    cnf, var_map, _ = generate_cnf(grid)
    solver = Glucose3()
    for clause in cnf.clauses:
        solver.add_clause(clause)

    result_grid = [row[:] for row in grid]
    if solver.solve():
        model = solver.get_model()
        for (i, j), var_id in var_map.items():
            if var_id is not None:
                result_grid[i][j] = 'T' if model[var_id - 1] > 0 else 'G'
    else:
        print("No solution found with PySAT.")
        return None, None

    end_time = time.time()
    return result_grid, end_time - start_time

def is_valid_grid(grid, partial=False):
    """Kiểm tra lưới có hợp lệ không."""
    rows, cols = len(grid), len(grid[0])
    for i in range(rows):
        for j in range(cols):
            if grid[i][j].isdigit():
                k = int(grid[i][j])
                neighbors = get_neighbors(i, j, rows, cols)
                trap_count = sum(1 for ni, nj in neighbors if grid[ni][nj] == 'T')
                if not partial and trap_count != k:
                    return False
                if partial and trap_count > k:
                    return False
    return True

def brute_force(grid):
    """Giải bài toán bằng Brute-force."""
    start_time = time.time()
    rows, cols = len(grid), len(grid[0])
    empty_cells = [(i, j) for i in range(rows) for j in range(cols) if grid[i][j] not in ['T', 'G'] and not grid[i][j].isdigit()]
    
    def try_combinations(index, temp_grid):
        if index == len(empty_cells):
            return temp_grid if is_valid_grid(temp_grid) else None
        i, j = empty_cells[index]
        # Thử T
        temp_grid[i][j] = 'T'
        if is_valid_grid(temp_grid, partial=True):
            result = try_combinations(index + 1, temp_grid)
            if result:
                return result
        # Thử G
        temp_grid[i][j] = 'G'
        if is_valid_grid(temp_grid, partial=True):
            result = try_combinations(index + 1, temp_grid)
            if result:
                return result
        temp_grid[i][j] = '-'
        return None

    result_grid = [row[:] for row in grid]
    result = try_combinations(0, result_grid)
    end_time = time.time()
    return result, end_time - start_time

def backtracking(grid):
    """Giải bài toán bằng Backtracking."""
    start_time = time.time()
    rows, cols = len(grid), len(grid[0])
    empty_cells = [(i, j) for i in range(rows) for j in range(cols) if grid[i][j] not in ['T', 'G'] and not grid[i][j].isdigit()]
    
    def solve(index, grid):
        if index == len(empty_cells):
            return grid if is_valid_grid(grid) else None
        i, j = empty_cells[index]
        # Thử T
        grid[i][j] = 'T'
        if is_valid_grid(grid, partial=True):
            result = solve(index + 1, grid)
            if result:
                return result
        # Thử G
        grid[i][j] = 'G'
        if is_valid_grid(grid, partial=True):
            result = solve(index + 1, grid)
            if result:
                return result
        grid[i][j] = '-'
        return None

    result_grid = [row[:] for row in grid]
    result = solve(0, result_grid)
    end_time = time.time()
    return result, end_time - start_time

def create_test_cases():
    """Tạo 3 test case mẫu."""
    os.makedirs('testcases', exist_ok=True)
    
    # Test case 1: 5x5
    test1 = [
        ['2', 'T', 'T', '1', 'G'],
        ['T', '5', '4', '2', 'G'],
        ['3', 'T', 'T', '2', '1'],
        ['3', 'T', '6', 'T', '1'],
        ['2', 'T', 'T', '2', '1']
    ]
    write_output(test1, 'testcases/input_1.txt')
    
    # Test case 2: 11x11 (đơn giản hóa)
    test2 = [['-' for _ in range(11)] for _ in range(11)]
    test2[0][0] = '3'; test2[0][10] = '2'; test2[5][5] = '4'; test2[10][0] = '3'; test2[10][10] = '2'
    write_output(test2, 'testcases/input_2.txt')
    
    # Test case 3: 20x20 (đơn giản hóa)
    test3 = [['-' for _ in range(20)] for _ in range(20)]
    test3[0][0] = '3'; test3[0][19] = '2'; test3[10][10] = '5'; test3[19][0] = '3'; test3[19][19] = '2'
    write_output(test3, 'testcases/input_3.txt')

def main():
    create_test_cases()
    for i in range(1, 4):
        input_file = f'testcases/input_{i}.txt'
        output_file = f'testcases/output_{i}.txt'
        print(f"\nProcessing {input_file}")
        
        grid = read_input(input_file)
        
        # PySAT
        print("Solving with PySAT...")
        result_pysat, time_pysat = solve_with_pysat(grid)
        if result_pysat:
            write_output(result_pysat, output_file)
            print(f"PySAT Time: {time_pysat:.4f} seconds")
        
        # Brute-force
        print("Solving with Brute-force...")
        result_bf, time_bf = brute_force(grid)
        if result_bf:
            print(f"Brute-force Time: {time_bf:.4f} seconds")
        
        # Backtracking
        print("Solving with Backtracking...")
        result_bt, time_bt = backtracking(grid)
        if result_bt:
            print(f"Backtracking Time: {time_bt:.4f} seconds")

if __name__ == "__main__":
    main()