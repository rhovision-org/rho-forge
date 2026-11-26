from copy import deepcopy
from itertools import product
import json
from pathlib import Path
import unittest

from rhoforge.compiler import Actor, LimitError, compile_workflow
from rhoforge.partition import compile_partitioned


def venues(seats=3):
    raw = json.loads((Path(__file__).resolve().parents[1] / "examples/venues.json").read_text())
    for place, bounds in raw["places"].items():
        bounds.update(capacity=seats, initial=seats if place.startswith("free_") else 0)
    for mission in raw["missions"]:
        goal = mission["goal"]
        goal[next(iter(goal))] = seats
    return raw


class Partitions(unittest.TestCase):
    def test_large_product_compiles_as_four_independent_actors(self):
        spec = venues()
        with self.assertRaises(LimitError):
            compile_workflow(spec)
        manifest, source = compile_partitioned(spec)
        self.assertEqual(compile_partitioned(spec), (manifest, source))
        self.assertEqual(set(manifest["lanes"]), {"free_a", "free_b", "free_c", "free_d"})
        self.assertEqual([len(m["markings"]) for m in manifest["lanes"].values()], [10] * 4)
        first, second, *_ = (Actor({**v, "roles": manifest["roles"]}) for v in manifest["lanes"].values())
        self.assertEqual(first.call("manager", "reserve_all_a", 0)[0], "DENIED")
        self.assertEqual(first.call("clerk", "reserve_all_a", 0)[0], "OK")
        self.assertEqual(first.call("clerk", "reserve_all_a", 0)[0], "STALE")
        self.assertEqual(second.call("clerk", "reserve_all_b", 0)[0], "OK")
        self.assertEqual(second.call("clerk", "reserve_a", 1)[0], "DENIED")

    def test_every_edge_matches_global_actor_after_projection(self):
        spec = venues(1)
        flat, _ = compile_workflow(spec)
        divided, _ = compile_partitioned(spec)
        lanes = list(divided["lanes"].values())
        by_marking = {
            tuple(row[p] for p in flat["places"]): i for i, row in enumerate(flat["markings"])
        }
        self.assertEqual(len(by_marking), 81)
        for local_ids in product(*(range(len(lane["markings"])) for lane in lanes)):
            marking = {}
            for lane, i in zip(lanes, local_ids):
                marking.update(lane["markings"][i])
            flat_id = by_marking[tuple(marking[p] for p in flat["places"])]
            for role in flat["roles"]:
                projected = {}
                for lane, i in zip(lanes, local_ids):
                    for action, step in lane["actions"][role][str(i)].items():
                        target = {**marking, **lane["markings"][step["target"]]}
                        projected[action] = {
                            "plan": step["plan"],
                            "target": by_marking[tuple(target[p] for p in flat["places"])],
                        }
                self.assertEqual(projected, flat["actions"][role][str(flat_id)])

    def test_cross_lane_missions_and_read_dependencies_are_joined(self):
        raw = deepcopy(venues(1))
        raw["missions"].append({
            "name": "reserve_pair", "role": "clerk", "goal": {"held_a": 1, "held_b": 1}
        })
        # held_c is read through consume/produce even though its change is zero.
        raw["transitions"][0]["consume"]["held_c"] = 1
        raw["transitions"][0]["produce"]["held_c"] = 1
        manifest, _ = compile_partitioned(raw)
        self.assertEqual(set(manifest["lanes"]), {"free_a", "free_d"})
        self.assertEqual(len(manifest["lanes"]["free_a"]["places"]), 9)
        self.assertIn("reserve_pair", manifest["lanes"]["free_a"]["mission_goals"])
