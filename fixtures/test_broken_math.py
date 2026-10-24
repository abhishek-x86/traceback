import pytest
from fixtures.broken_math import calculate_moving_average

def test_moving_average_simple():
    data = [10.0, 20.0, 30.0, 40.0]
    expected = [15.0, 25.0, 35.0]
    assert calculate_moving_average(data, 2) == expected

def test_moving_average_empty():
    assert calculate_moving_average([], 3) == []