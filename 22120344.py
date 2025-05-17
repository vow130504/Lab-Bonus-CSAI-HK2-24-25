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
            row = [cell.replace('_', '_') for cell in row]
            grid.append(row)
    return grid

def write_output(grid, file_path, method=None):
    """Ghi kết quả vào file output với tên file riêng cho mỗi phương pháp."""
    if method:
        file_path = file_path.replace('.txt', f'_{method}.txt')
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

def check_grid_validity(grid):
    """Kiểm tra tính hợp lệ của lưới trước khi giải."""
    rows, cols = len(grid), len(grid[0])
    for i in range(rows):
        for j in range(cols):
            if grid[i][j].isdigit():
                k = int(grid[i][j])
                neighbors = get_neighbors(i, j, rows, cols)
                trap_count = sum(1 for ni, nj in neighbors if grid[ni][nj] == 'T')
                unknown_count = sum(1 for ni, nj in neighbors if grid[ni][nj] == '_')
                if trap_count > k or (trap_count + unknown_count) < k:
                    return False
    return True

def generate_cnf(grid):
    """Tạo các ràng buộc CNF đúng cho bài toán."""
    rows, cols = len(grid), len(grid[0])
    cnf = CNF()
    var_map = {}
    var_count = 0

    # Gán biến logic cho các ô trống
    for i in range(rows):
        for j in range(cols):
            if grid[i][j] == '_':
                var_count += 1
                var_map[(i, j)] = var_count
            elif grid[i][j] in ['T', 'G']:
                var_map[(i, j)] = None

    clauses_set = set()

    # Tạo ràng buộc cho các ô có số
    for i in range(rows):
        for j in range(cols):
            if grid[i][j].isdigit():
                k = int(grid[i][j])
                neighbors = get_neighbors(i, j, rows, cols)
                trap_count = sum(1 for ni, nj in neighbors if grid[ni][nj] == 'T')
                neighbor_vars = [var_map.get((ni, nj)) for ni, nj in neighbors if var_map.get((ni, nj)) is not None]

                unknown_count = len(neighbor_vars)
                adjusted_k = k - trap_count
                if adjusted_k < 0 or adjusted_k > unknown_count:
                    print(f"Invalid grid: Cell ({i},{j}) requires {k} traps, but has {trap_count} traps and {unknown_count} unknowns.")
                    return None, None, 0

                if neighbor_vars:
                    # Ràng buộc: đúng adjusted_k bẫy
                    if adjusted_k == 0:
                        for var_id in neighbor_vars:
                            clauses_set.add((-var_id,))  # Tất cả phải là G
                    else:
                        # Ít nhất adjusted_k bẫy
                        if adjusted_k > 0:
                            for comb in itertools.combinations(neighbor_vars, len(neighbor_vars) - adjusted_k + 1):
                                clause = tuple(var_id for var_id in comb)
                                clauses_set.add(clause)
                        # Không quá adjusted_k bẫy
                        if adjusted_k < len(neighbor_vars):
                            for comb in itertools.combinations(neighbor_vars, adjusted_k + 1):
                                clause = tuple(-var_id for var_id in comb)
                                clauses_set.add(clause)

    for clause in clauses_set:
        cnf.append(list(clause))

    return cnf, var_map, var_count

def solve_with_pysat(grid, output_file):
    """Giải bài toán bằng PySAT (CNF đúng)."""
    start_time = time.perf_counter()
    if not check_grid_validity(grid):
        print("Grid is invalid.")
        write_output(grid, output_file, "pysat")
        return None, None

    cnf, var_map, _ = generate_cnf(grid)
    if cnf is None:
        write_output(grid, output_file, "pysat")
        return None, None

    solver = Glucose3()
    for clause in cnf.clauses:
        solver.add_clause(clause)

    result_grid = [row[:] for row in grid]
    if solver.solve():
        model = solver.get_model()
        for (i, j), var_id in var_map.items():
            if var_id is not None:
                result_grid[i][j] = 'T' if model[var_id - 1] > 0 else 'G'
        write_output(result_grid, output_file, "pysat")
    else:
        print("No solution found with PySAT.")
        write_output(grid, output_file, "pysat")

    end_time = time.perf_counter()
    execution_time = end_time - start_time
    return result_grid, execution_time

def is_valid_grid(grid, partial=False):
    """Kiểm tra lưới có hợp lệ không trong quá trình giải."""
    rows, cols = len(grid), len(grid[0])
    for i in range(rows):
        for j in range(cols):
            if grid[i][j].isdigit():
                k = int(grid[i][j])
                neighbors = get_neighbors(i, j, rows, cols)
                trap_count = sum(1 for ni, nj in neighbors if grid[ni][nj] == 'T')
                ground_count = sum(1 for ni, nj in neighbors if grid[ni][nj] == 'G')
                unknown_count = sum(1 for ni, nj in neighbors if grid[ni][nj] == '_')
                
                if not partial:
                    # Nếu kiểm tra giải pháp cuối cùng, số bẫy phải chính xác là k
                    if trap_count != k:
                        return False
                else:
                    # Kiểm tra giải pháp một phần
                    # Nếu số bẫy đã vượt quá k, không hợp lệ
                    if trap_count > k:
                        return False
                    # Nếu số bẫy hiện tại + số ô chưa biết < k, không thể đạt được k bẫy
                    if trap_count + unknown_count < k:
                        return False
    return True

def brute_force(grid, output_file):
    """Giải bài toán bằng Brute-force."""
    start_time = time.perf_counter()
    if not check_grid_validity(grid):
        print("Grid is invalid.")
        write_output(grid, output_file, "bruteforce")
        return None, None

    rows, cols = len(grid), len(grid[0])
    empty_cells = [(i, j) for i in range(rows) for j in range(cols) if grid[i][j] == '_']
    print(f"Number of empty cells: {len(empty_cells)}")
    
    def try_combinations(index, temp_grid):
        if index == len(empty_cells):
            if is_valid_grid(temp_grid):
                return temp_grid
            return None
        
        i, j = empty_cells[index]
        
        # Thử gán 'G' trước
        temp_grid[i][j] = 'G'
        if is_valid_grid(temp_grid, partial=True):
            result = try_combinations(index + 1, temp_grid)
            if result:
                return result
        
        # Thử gán 'T' 
        temp_grid[i][j] = 'T'
        if is_valid_grid(temp_grid, partial=True):
            result = try_combinations(index + 1, temp_grid)
            if result:
                return result
        
        # Quay lui
        temp_grid[i][j] = '_'
        return None

    result_grid = [row[:] for row in grid]
    result = try_combinations(0, result_grid)
    
    if result:
        write_output(result, output_file, "bruteforce")
    else:
        print("No solution found with Brute-force.")
        write_output(grid, output_file, "bruteforce")

    end_time = time.perf_counter()
    execution_time = end_time - start_time
    return result, execution_time

def backtracking(grid, output_file):
    """Giải bài toán bằng Backtracking với pruning."""
    start_time = time.perf_counter()
    if not check_grid_validity(grid):
        print("Grid is invalid.")
        write_output(grid, output_file, "backtracking")
        return None, None

    rows, cols = len(grid), len(grid[0])
    
    # Chọn ô để thử: ưu tiên các ô gần với ô số
    def get_priority_cells(grid):
        cells = []
        for i in range(rows):
            for j in range(cols):
                if grid[i][j] == '_':
                    priority = 0
                    neighbors = get_neighbors(i, j, rows, cols)
                    for ni, nj in neighbors:
                        if grid[ni][nj].isdigit():
                            priority += 1
                    cells.append((priority, i, j))
        # Sắp xếp theo mức độ ưu tiên giảm dần
        return [(i, j) for _, i, j in sorted(cells, reverse=True)]
    
    empty_cells = get_priority_cells(grid)
    print(f"Number of empty cells: {len(empty_cells)}")
    
    def try_backtrack(index, temp_grid):
        if index == len(empty_cells):
            if is_valid_grid(temp_grid):
                return temp_grid
            return None
        
        i, j = empty_cells[index]
        
        # Thử gán 'G' trước
        temp_grid[i][j] = 'G'
        if is_valid_grid(temp_grid, partial=True):
            result = try_backtrack(index + 1, temp_grid)
            if result:
                return result
        
        # Thử gán 'T'
        temp_grid[i][j] = 'T'
        if is_valid_grid(temp_grid, partial=True):
            result = try_backtrack(index + 1, temp_grid)
            if result:
                return result
        
        # Quay lui
        temp_grid[i][j] = '_'
        return None

    result_grid = [row[:] for row in grid]
    result = try_backtrack(0, result_grid)
    
    if result:
        write_output(result, output_file, "backtracking")
    else:
        print("No solution found with Backtracking.")
        write_output(grid, output_file, "backtracking")

    end_time = time.perf_counter()
    execution_time = end_time - start_time
    return result, execution_time

def create_test_cases():
    """Tạo 3 test case mẫu."""
    os.makedirs('testcases', exist_ok=True)
    
    # Test case 1: 5x5
    test1 = [
        ['2', 'T', 'T', '1', '_'],
        ['_', '5', '4', '2', '_'],
        ['3', '_', '_', '2', '1'],
        ['3', 'T', '6', '_', '1'],
        ['2', '_', '_', '2', '1']
    ]
    write_output(test1, 'testcases/input_1.txt')
    
    # Test case 2: 11x11
    test2 = [
        ['3', '_', '_', '_', '_', '_', '_', '_', '_', '_', '2'],
        ['_', '_', '_', '_', '_', '_', '_', '_', '_', '_', '_'],
        ['_', '_', '3', '_', '_', '_', '_', '_', '3', '_', '_'],
        ['_', '_', '_', '_', '_', '_', '_', '_', '_', '_', '_'],
        ['_', '_', '_', '_', '4', '_', '4', '_', '_', '_', '_'],
        ['_', '_', '_', '_', '_', '_', '_', '_', '_', '_', '_'],
        ['_', '_', '_', '_', '4', '_', '4', '_', '_', '_', '_'],
        ['_', '_', '_', '_', '_', '_', '_', '_', '_', '_', '_'],
        ['_', '_', '3', '_', '_', '_', '_', '_', '3', '_', '_'],
        ['_', '_', '_', '_', '_', '_', '_', '_', '_', '_', '_'],
        ['3', '_', '_', '_', '_', '_', '_', '_', '_', '_', '2']
    ]
    write_output(test2, 'testcases/input_2.txt')
    
    # Test case 3: 20x20
    test3 = []
    test3.append(['3'] + ['_']*18 + ['2'])
    for _ in range(2):
        test3.append(['_']*20)
    test3.append(['_', '_', '3'] + ['_']*14 + ['3', '_', '_'])
    for _ in range(2):
        test3.append(['_']*20)
    test3.append(['_']*4 + ['4'] + ['_']*10 + ['4'] + ['_']*4)
    for _ in range(2):
        test3.append(['_']*20)
    test3.append(['_']*6 + ['4'] + ['_']*6 + ['4'] + ['_']*6)
    for _ in range(2):
        test3.append(['_']*20)
    test3.append(['_']*8 + ['5'] + ['_']*2 + ['5'] + ['_']*8)
    for _ in range(2):
        test3.append(['_']*20)
    test3.append(['_']*8 + ['5'] + ['_']*2 + ['5'] + ['_']*8)
    for _ in range(2):
        test3.append(['_']*20)
    test3.append(['_']*6 + ['4'] + ['_']*6 + ['4'] + ['_']*6)
    for _ in range(2):
        test3.append(['_']*20)
    test3.append(['_']*4 + ['4'] + ['_']*10 + ['4'] + ['_']*4)
    for _ in range(2):
        test3.append(['_']*20)
    test3.append(['_', '_', '3'] + ['_']*14 + ['3', '_', '_'])
    for _ in range(2):
        test3.append(['_']*20)
    test3.append(['3'] + ['_']*18 + ['2'])
    write_output(test3, 'testcases/input_3.txt')

def main():
    create_test_cases()
    for i in range(1, 4):
        input_file = f'testcases/input_{i}.txt'
        output_file = f'testcases/output_{i}.txt'
        print(f"\nProcessing {input_file}")
        
        grid = read_input(input_file)
        
        print("Solving with PySAT...")
        result_pysat, time_pysat = solve_with_pysat(grid, output_file)
        if result_pysat:
            print(f"PySAT Time: {time_pysat:.4f} seconds")
        else:
            print("No solution found with PySAT")
        
        if i < 4:  # Chỉ chạy brute-force và backtracking cho các test case nhỏ hơn
            print("Solving with Brute-force...")
            result_bf, time_bf = brute_force(grid, output_file)
            if result_bf:
                print(f"Brute-force Time: {time_bf:.4f} seconds")
            else:
                print("No solution found with Brute-force")
            
            print("Solving with Backtracking...")
            result_bt, time_bt = backtracking(grid, output_file)
            if result_bt:
                print(f"Backtracking Time: {time_bt:.4f} seconds")
            else:
                print("No solution found with Backtracking")

if __name__ == "__main__":
    main()