"""Exercise independently clocked reservation lanes on an isolated Rholo node."""

import argparse
import json
from pathlib import Path

import isolated_rholo
from probe_generated import decode, multiset
from rhoforge.compiler import Actor
from rhoforge.partition import compile_partitioned


SPEC = Path(__file__).resolve().parents[1] / "examples/venues.json"


def probe(request, repeats, anchor):
    manifest, factory = compile_partitioned(json.loads(SPEC.read_text()))

    def actor(lane):
        return Actor({**manifest["lanes"][lane], "roles": manifest["roles"]})

    a, b = actor("free_a"), actor("free_b")
    expected = [
        a.call("clerk", "reserve_all_a", 0),
        b.call("clerk", "reserve_all_b", 0),
        a.call("clerk", "reserve_all_a", 0),
        b.call("clerk", "reserve_a", 1),
        a.call("manager", "issue_a", 1),
        a.call("read", "", 0),
        b.call("read", "", 0),
        actor("free_a").call("read", "", 0),
    ]
    term = f'''new result, factory, ready_a, ready_b, ready_c in {{
      {factory} |
      factory!("free_a", *ready_a) | factory!("free_b", *ready_b) |
      factory!("free_a", *ready_c) |
      for (view_a, clerk_a, manager_a <- ready_a;
           view_b, clerk_b, manager_b <- ready_b;
           view_c, clerk_c, manager_c <- ready_c) {{
        new x, y, z, cross, denied, read_a, read_b, read_c in {{
          clerk_a!("reserve_all_a", 0, *x) | clerk_a!("reserve_all_a", 0, *y) |
          clerk_b!("reserve_all_b", 0, *z) | view_c!(*read_c) |
          for (@first <- x; @second <- y; @third <- z; @fresh <- read_c) {{
            result!(first) | result!(second) | result!(third) | result!(fresh) |
            clerk_b!("reserve_a", 1, *cross) | manager_a!("issue_a", 1, *denied) |
            view_a!(*read_a) | view_b!(*read_b) |
            for (@bad <- cross; @bad_role <- denied; @state_a <- read_a; @state_b <- read_b) {{
              result!(bad) | result!(bad_role) | result!(state_a) | result!(state_b)
            }}
          }}
        }}
      }}
    }}'''
    observed = []
    for _ in range(repeats):
        reply = request("/api/explore-deploy-by-block-hash", {
            "term": term, "blockHash": anchor, "usePreStateHash": False,
        })
        if reply.get("block", {}).get("blockHash") != anchor or reply.get("replySource") != "firstPrivateName":
            raise ValueError("unexpected response anchor or result channel")
        actual = [decode(item) for item in reply["expr"]]
        if multiset(actual) != multiset(expected):
            raise AssertionError(f"partitioned actor mismatch: {actual!r} != {expected!r}")
        observed.append(actual)
    return [{"fixture": "independent_commits_same_lane_race_and_authority",
             "expected": expected, "observed": observed, "passed": True}]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = isolated_rholo.run(args.binary.resolve(), args.sha256, args.commit, args.repeats, probe)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print("PASS", result["fixture_count"], "native fixture", args.repeats, "repetitions")
