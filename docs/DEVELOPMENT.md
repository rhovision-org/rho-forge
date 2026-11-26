# Working on Forge

`rhoforge/compiler.py` validates resource flows and conservation, builds the reachable marking table, and finds shortest permitted mission paths. `rhoforge/partition.py` groups places by what each transition and mission touches. Its factory keeps a separate state and revision in every instance. `examples/escrow.json` uses the flat compiler. `examples/venues.json` covers the four-lane layout.

```mermaid
flowchart TD
    P["Resource workflow"] --> C["Validate conservation"]
    C --> B{"Factory mode"}
    B --> G["One marking table"]
    B --> L["Group dependent places"]
    L --> T["A table per lane"]
    T --> M["Find authorized mission paths"]
    G --> M
    M --> R["Rholang factory"]
    M --> J["Resource manifest"]
```

The [reference](REFERENCE.md) describes input and the flat actor interface. See the [partitioned factory](PARTITIONING.md) for role order, state scope and the native race probe. For a first end-to-end contract use the [escrow walkthrough](GUIDE.md).

```sh
python3 -m unittest discover -s tests -v
python3 -m rhoforge examples/venues.json --partition --out build-venues
```

For reviews, explain which resources an operation touches even when it leaves a resource count unchanged. Test conservation and permissions, and show cases where paired calls should commit independently or share a revision check. The probe scripts in `tools/` verify generated actors against a pinned Rholo revision. [CI workflow](../.github/workflows/ci.yml)
