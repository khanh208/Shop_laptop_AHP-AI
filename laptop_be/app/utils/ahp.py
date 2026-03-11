import math

RI_TABLE = {
    1: 0.0,
    2: 0.0,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
}

def saaty_from_diff(diff: float) -> int:
    if diff < 0.25:
        return 1
    if diff < 0.50:
        return 2
    if diff < 1.00:
        return 3
    if diff < 1.50:
        return 4
    if diff < 2.00:
        return 5
    if diff < 2.50:
        return 6
    if diff < 3.00:
        return 7
    if diff < 3.50:
        return 8
    return 9

def build_ahp(criteria_scores: list[dict]) -> dict:
    """
    criteria_scores = [
      {"criterion_id": 1, "code": "cpu", "name": "CPU", "score": 4.5},
      ...
    ]
    """
    n = len(criteria_scores)
    matrix = [[1.0 for _ in range(n)] for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i == j:
                matrix[i][j] = 1.0
                continue

            si = criteria_scores[i]["score"]
            sj = criteria_scores[j]["score"]

            if si == sj:
                matrix[i][j] = 1.0
            elif si > sj:
                matrix[i][j] = float(saaty_from_diff(si - sj))
            else:
                matrix[i][j] = 1.0 / float(saaty_from_diff(sj - si))

    col_sums = [sum(matrix[i][j] for i in range(n)) for j in range(n)]
    normalized = [
        [matrix[i][j] / col_sums[j] for j in range(n)]
        for i in range(n)
    ]
    weights = [sum(row) / n for row in normalized]

    weighted_sum = [
        sum(matrix[i][j] * weights[j] for j in range(n))
        for i in range(n)
    ]
    lambda_values = [weighted_sum[i] / weights[i] for i in range(n)]
    lambda_max = sum(lambda_values) / n

    ci = (lambda_max - n) / (n - 1) if n > 1 else 0.0
    ri = RI_TABLE.get(n, 1.49)
    cr = (ci / ri) if ri != 0 else 0.0

    return {
        "pairwise_matrix": matrix,
        "normalized_matrix": normalized,
        "weights": weights,
        "summary": {
            "criteria_count": n,
            "lambda_max": lambda_max,
            "ci": ci,
            "ri": ri,
            "cr": cr,
            "is_consistent": cr < 0.1,
        }
    }