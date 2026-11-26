"""Compare the complete product table with the generated lane tables."""

import argparse
from copy import deepcopy
import json
from pathlib import Path
from statistics import median
from time import perf_counter_ns

from rhoforge.compiler import LimitError, compile_workflow
from rhoforge.partition import compile_partitioned

ROOT = Path(__file__).resolve().parents[1]


def measure(compiler, spec, partitioned):
    manifest, source = compiler(spec)
    samples = []
    for _ in range(25):
        start = perf_counter_ns()
        compiler(spec)
        samples.append(perf_counter_ns() - start)
    tables = list(manifest["lanes"].values()) if partitioned else [manifest]
    return {
        "markings": sum(len(t["markings"]) for t in tables),
        "edges": sum(t["primitive_edges"] for t in tables),
        "source_bytes": len(source.encode()),
        "median_compile_ms": round(median(samples) / 1_000_000, 3),
    }


def benchmark():
    large = json.loads((ROOT / "examples/venues.json").read_text())
    small = deepcopy(large)
    for place in small["places"].values():
        place["capacity"], place["initial"] = 1, int(place["initial"] > 0)
    for mission in small["missions"]:
        mission["goal"] = dict.fromkeys(mission["goal"], 1)
    result = {
        "one_seat_per_lane": {
            "single_cell": measure(compile_workflow, small, False),
            "independent_lanes": measure(compile_partitioned, small, True),
        },
        "three_seats_per_lane": {
            "independent_lanes": measure(compile_partitioned, large, True),
        },
    }
    try:
        compile_workflow(large)
    except LimitError as error:
        result["three_seats_per_lane"]["single_cell"] = {"compiler_limit": str(error)}
    else:
        raise AssertionError("expected the flat product to exceed the state budget")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    report = json.dumps(benchmark(), indent=2) + "\n"
    args.out.write_text(report)
    print(report, end="")
