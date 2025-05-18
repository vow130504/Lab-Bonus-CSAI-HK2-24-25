import os
import time
import itertools
from pysat.solvers import Glucose3
from pysat.formula import CNF
from collections import defaultdict
from itertools import product

def read_input(file_path):
    """Đọc grid từ file input."""
    grid = []
    with open(file_path, 'r') as f:
        for line in f:
            row = [cell.strip() for cell in line.strip().split(',')]
            grid.append(row)
    return grid

def write_output(grid, file_path):
    """Ghi kết quả ra file output."""
    with open(file_path, 'w') as f:
        for row in grid:
            f.write(','.join(row) + '\n')

def get_neighbors(i, j, rows, cols):
    """Lấy các ô lân cận (8 hướng)."""
    return [(i+di, j+dj) for di in [-1, 0, 1] for dj in [-1, 0, 1] 
            if (di != 0 or dj != 0) and 0 <= i+di < rows and 0 <= j+dj < cols]

def preprocess_grid(grid):
    """Tiền xử lý grid để xác định các ô bắt buộc."""
    rows, cols = len(grid), len(grid[0])
    changed = True
    
    while changed:
        changed = False
        for i in range(rows):
            for j in range(cols):
                if grid[i][j].isdigit():
                    k = int(grid[i][j])
                    neighbors = get_neighbors(i, j, rows, cols)
                    traps = sum(1 for ni, nj in neighbors if grid[ni][nj] == 'T')
                    unknowns = [(ni, nj) for ni, nj in neighbors if grid[ni][nj] == '_']
                    
                    if k - traps == len(unknowns):
                        for ni, nj in unknowns:
                            grid[ni][nj] = 'T'
                            changed = True
                    elif traps == k and unknowns:
                        for ni, nj in unknowns:
                            grid[ni][nj] = 'G'
                            changed = True
    return grid

def is_grid_valid(grid):
    """Kiểm tra tính hợp lệ của grid."""
    rows, cols = len(grid), len(grid[0])
    for i in range(rows):
        for j in range(cols):
            if grid[i][j].isdigit():
                k = int(grid[i][j])
                neighbors = get_neighbors(i, j, rows, cols)
                if k > len(neighbors):
                    print(f"Lỗi ở ô ({i},{j}): Số trap {k} > số ô lân cận {len(neighbors)}")
                    return False
                traps = sum(1 for ni, nj in neighbors if grid[ni][nj] == 'T')
                if traps > k:
                    print(f"Lỗi ở ô ({i},{j}): Đã có {traps} trap nhưng yêu cầu chỉ {k}")
                    return False
    return True

def generate_cnf(grid):
    """Tạo CNF constraints chính xác."""
    rows, cols = len(grid), len(grid[0])
    cnf = CNF()
    var_map = {}
    var_count = 0

    # Gán biến cho các ô chưa xác định
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
                neighbor_vars = [var_map[(ni, nj)] for ni, nj in neighbors 
                               if var_map.get((ni, nj)) is not None]

                remaining = k - trap_count
                unknown_count = len(neighbor_vars)
                
                if remaining < 0 or remaining > unknown_count:
                    print(f"Không thể thỏa mãn ô ({i},{j}): cần {remaining} trap trong {unknown_count} ô")
                    return None, None, 0

                if neighbor_vars:
                    # Exactly-K constraint
                    if remaining == 0:
                        for var_id in neighbor_vars:
                            clauses_set.add(frozenset([-var_id]))  # Tất cả phải là G
                    elif remaining == unknown_count:
                        for var_id in neighbor_vars:
                            clauses_set.add(frozenset([var_id]))    # Tất cả phải là T
                    else:
                        # At least K
                        for comb in itertools.combinations(neighbor_vars, unknown_count - remaining + 1):
                            clauses_set.add(frozenset(comb))
                        # At most K
                        for comb in itertools.combinations(neighbor_vars, remaining + 1):
                            clauses_set.add(frozenset(-var_id for var_id in comb))

    # Thêm clauses vào CNF
    for clause in clauses_set:
        cnf.append(list(clause))
    
    return cnf, var_map, var_count

def solve_with_pysat(grid, output_file):
    """Giải bằng PySAT với các tối ưu."""
    start_time = time.perf_counter()
    
    grid = preprocess_grid([row[:] for row in grid])
    if not is_grid_valid(grid):
        return None, None
    
    cnf, var_map, _ = generate_cnf(grid)
    if cnf is None:
        return None, None

    solver = Glucose3(bootstrap_with=cnf.clauses)
    result_grid = [row[:] for row in grid]
    
    if solver.solve():
        model = solver.get_model()
        for (i, j), var_id in var_map.items():
            if var_id is not None:
                result_grid[i][j] = 'T' if model[var_id - 1] > 0 else 'G'
        write_output(result_grid, output_file)
    else:
        print("Không tìm thấy lời giải với PySAT.")
    
    end_time = time.perf_counter()
    return result_grid, end_time - start_time

def optimized_brute_force(grid):
    """Brute-force được tối ưu với heuristic."""
    start_time = time.perf_counter()
    grid = preprocess_grid([row[:] for row in grid])
    if not is_grid_valid(grid):
        return None, None
    
    cnf, var_map, _ = generate_cnf(grid)
    if cnf is None:
        return None, None
    
    variables = [var_id for var_id in var_map.values() if var_id is not None]
    var_positions = {v: k for k, v in var_map.items() if v is not None}
    
    # Giới hạn kích thước để đảm bảo hiệu suất
    if len(variables) > 40:
        print("Brute-force không khả thi với số lượng biến lớn.")
        return None, None
    
    # Sắp xếp biến theo độ phức tạp (xuất hiện nhiều trong clauses)
    var_complexity = {var: 0 for var in variables}
    for clause in cnf.clauses:
        for lit in clause:
            var_complexity[abs(lit)] += 1
    variables.sort(key=lambda x: -var_complexity[x])
    
    result_grid = [row[:] for row in grid]
    
    # Hàm kiểm tra tính hợp lệ tối ưu
    def is_valid(assignment):
        for clause in cnf.clauses:
            satisfied = False
            for lit in clause:
                var = abs(lit)
                if var in assignment:
                    if (lit > 0 and assignment[var]) or (lit < 0 and not assignment[var]):
                        satisfied = True
                        break
            if not satisfied:
                return False
        return True
    
    # Duyệt có thứ tự
    for bits in product([False, True], repeat=len(variables)):
        assignment = dict(zip(variables, bits))
        if is_valid(assignment):
            for var_id, pos in var_positions.items():
                i, j = pos
                result_grid[i][j] = 'T' if assignment[var_id] else 'G'
            end_time = time.perf_counter()
            return result_grid, end_time - start_time
    
    print("Không tìm thấy lời giải với Brute-force.")
    end_time = time.perf_counter()
    return None, end_time - start_time

def optimized_backtracking(grid):
    """Backtracking với MRV, LCV và forward checking."""
    start_time = time.perf_counter()
    grid = preprocess_grid([row[:] for row in grid])
    if not is_grid_valid(grid):
        return None, None
    
    cnf, var_map, var_count = generate_cnf(grid)
    if cnf is None:
        return None, None
    
    variables = [var_id for var_id in var_map.values() if var_id is not None]
    var_positions = {v: k for k, v in var_map.items() if v is not None}
    
    # Xây dựng watch list và clause database
    watch_list = defaultdict(list)
    clause_db = []
    for clause_idx, clause in enumerate(cnf.clauses):
        clause_db.append(clause)
        for lit in clause[:2]:
            watch_list[abs(lit)].append(clause_idx)
    
    result_grid = [row[:] for row in grid]
    assignments = {}  # {var_id: True/False}
    learned_clauses = []
    
    def is_consistent(var, value):
        """Kiểm tra tính nhất quán khi gán var=value"""
        temp_assign = assignments.copy()
        temp_assign[var] = value
        
        # Chỉ kiểm tra các clause liên quan
        for clause_idx in watch_list.get(var, []):
            clause = clause_db[clause_idx]
            satisfied = False
            unassigned_lits = []
            for lit in clause:
                var_id = abs(lit)
                if var_id in temp_assign:
                    if (lit > 0 and temp_assign[var_id]) or (lit < 0 and not temp_assign[var_id]):
                        satisfied = True
                        break
                else:
                    unassigned_lits.append(lit)
            
            if not satisfied:
                if len(unassigned_lits) == 0:
                    return False
                if len(unassigned_lits) == 1:
                    # Unit propagation
                    lit = unassigned_lits[0]
                    var_id = abs(lit)
                    val = lit > 0
                    if var_id in temp_assign and temp_assign[var_id] != val:
                        return False
        return True
    
    def select_unassigned_variable():
        """Chọn biến theo VSIDS heuristic (ưu tiên biến xuất hiện nhiều trong các clause gần đây)"""
        unassigned = [var for var in variables if var not in assignments]
        if not unassigned:
            return None
        
        # Tính điểm VSIDS
        vsids_scores = defaultdict(int)
        for clause in clause_db + learned_clauses:
            for lit in clause:
                var = abs(lit)
                if var in unassigned:
                    vsids_scores[var] += 1
        
        # Chọn biến có điểm cao nhất
        return max(unassigned, key=lambda x: vsids_scores[x]) if vsids_scores else unassigned[0]
    
    def analyze_conflict():
        """Phân tích mâu thuẫn để học clause mới (simplified)"""
        # Trong implementation đơn giản này, chúng ta chỉ trả về một clause ngẫu nhiên
        # Trong thực tế cần implement conflict analysis phức tạp hơn
        return clause_db[0] if clause_db else []
    
    def backtrack():
        nonlocal learned_clauses
        if len(assignments) == len(variables):
            return True
        
        var = select_unassigned_variable()
        for value in [True, False]:  # Thử True trước (T), sau đó False (G)
            if is_consistent(var, value):
                assignments[var] = value
                if backtrack():
                    return True
                del assignments[var]
            else:
                # Học clause mới từ mâu thuẫn
                new_clause = analyze_conflict()
                if new_clause:
                    learned_clauses.append(new_clause)
        return False
    
    if backtrack():
        for var_id, pos in var_positions.items():
            i, j = pos
            result_grid[i][j] = 'T' if assignments.get(var_id, False) else 'G'
    else:
        print("Không tìm thấy lời giải với Backtracking.")
        return None, time.perf_counter() - start_time
    
    return result_grid, time.perf_counter() - start_time

def main():
    if not os.path.exists('testcases'):
        os.makedirs('testcases')
    
    for i in range(1, 5):
        input_file = f'testcases/input_{i}.txt'
        output_file = f'testcases/output_{i}.txt'
        
        if not os.path.exists(input_file):
            print(f"File {input_file} không tồn tại")
            continue
        
        print(f"\nĐang xử lý {input_file}")
        grid = read_input(input_file)
        
        if not is_grid_valid(grid):
            print("Grid không hợp lệ!")
            continue
        
        print("Giải bằng PySAT...")
        result_pysat, time_pysat = solve_with_pysat(grid, output_file)
        print(f"Thời gian: {time_pysat:.6f}s")
        
        if len(grid) <= 6:
            print("Giải bằng Brute-force...")
            result_bf, time_bf = optimized_brute_force(grid)
            print(f"Thời gian: {time_bf:.6f}s")
        else:
            print("Bỏ qua Brute-force do kích thước lớn")
        
        print("Giải bằng Backtracking...")
        result_bt, time_bt = optimized_backtracking(grid)
        print(f"Thời gian: {time_bt:.6f}s")

if __name__ == "__main__":
    main()