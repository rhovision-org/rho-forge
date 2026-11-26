# Independent resource lanes

```sh
python3 -m rhoforge examples/venues.json --partition --out build-venues
```

The input uses the regular Forge workflow schema. The compiler joins all the places used by each transition, including places that the transition reads by consuming and reproducing the same quantity. It also joins every place named in one mission. The connected components form lanes. The lane ID is its first place name in lexical order.

Each primitive modifies one lane, so every declared conservation equality projects onto independent per-lane equalities. Each projected equality starts at its own initial total. The reachable global markings are the product of the lane markings, and the compiler constructs only the individual lane tables. Role-authorized mission paths are synthesized within a lane.

## Calling the generated factory

Include `factory.rho` within `new factory in { ... }` and invoke `factory!("free_a", *ready)`. It creates one fresh instance of that lane. The reply carries the send-only view capability followed by the send-only operation capabilities in manifest role order. Unknown lane IDs return the string `"UNKNOWN_LANE"`.

The operation and view argument shapes match the [original actor API](REFERENCE.md). A state ID and revision are scoped to one instance of one lane. Give capabilities to their intended holders. Keep the initializer private when applications require a particular instance.

Use `manifest.json` with schema `rho-forge/partitioned-v1` to recover the per-lane states, actions, plans and invariants. Its source digest binds the manifest to the expected factory bytes when those bytes are checked independently. It does not authenticate the publisher.

## Evidence and bounds

```sh
PYTHONPATH=. python3 tools/benchmark_partition.py --out /tmp/forge-partition.json
PYTHONPATH=. python3 tools/probe_partition.py --binary /path/to/rnode \
  --sha256 232d12bd5d3fadc8371c26ec6a888ea48a4062b1187bb63c35b9d19423f28ead \
  --commit e63b7e5a8ccfcc25ff64860ac989d95a748eaaca --out /tmp/forge-native.json
```

The benchmark compiles four one-seat lanes both ways, then compiles four three-seat lanes with the partitioned backend. The native probe exercises simultaneous commits across lanes, a same-revision race, role and lane denial, and isolation between two instances created for the same lane. The original escrow evidence describes the historical compiler at [2598608](https://github.com/rhovision-org/rho-forge/tree/2598608908992df91c2d0bdb0063d6d8030d4639). CI generates and checks fresh evidence for each revision.

The partitioned compiler retains the per-lane bounds of 128 markings and 4,096 primitive edges, and a total generated source limit of 512 KB. A cross-lane transaction or snapshot would require an additional coordination protocol. Declare every resource a mission must read or update to keep that mission atomic.
