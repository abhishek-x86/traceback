def calculate_moving_average(values: list[float], window_size: int) -> list[float]:
    if not values or window_size <= 0:
        return []

    averages = []
    # Bug: using range(len(values)) instead of valid window bounds causes IndexError
    for i in range(len(values)):
        window = values[i : i + window_size]
        if len(window) < window_size:
            raise IndexError("Unexpected slice length at array boundary")
        averages.append(sum(window) / window_size)

    return averages