"""GPU 状态解析单元测试。"""

from nex.gpu import parse_gpu_line


def test_parse_gpu_line_normal():
    status = parse_gpu_line(
        "NVIDIA GeForce RTX 5060 Laptop GPU, 57, 96, 2597, 65.78"
    )
    assert status is not None
    assert status.name == "NVIDIA GeForce RTX 5060 Laptop GPU"
    assert status.temperature == 57
    assert status.utilization == 96
    assert status.memory_used == 2597
    assert status.power == 65.78


def test_parse_gpu_line_na_values():
    status = parse_gpu_line("GPU, [N/A], [N/A], 100, [N/A]")
    assert status is not None
    assert status.temperature is None
    assert status.utilization is None
    assert status.memory_used == 100
    assert status.power is None


def test_parse_gpu_line_invalid():
    assert parse_gpu_line("") is None
    assert parse_gpu_line("a,b") is None
