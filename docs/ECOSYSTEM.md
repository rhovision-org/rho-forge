# Building a recoverable reservation app

| Project | Use it for |
| --- | --- |
| [Forge](https://github.com/rhovision-org/rho-forge) | Compile resource flows into actors with separate revision scopes where the workflow permits. |
| [Weave](https://github.com/rhovision-org/rho-weave) | Extract authorized choices from a Forge lane manifest and synthesize a checked recovery controller for a stated objective. |
| [Observer](https://github.com/rhovision-org/rho-observer) | Select an explicit finalized block for a read, with freshness and evidence attached. |
| [Foundry](https://github.com/rhovision-org/rho-foundry) | Compile arithmetic rules and linear guards for contracts that need richer conditions or large counters. |

The [venue workflow](../examples/venues.json) gives four box offices independent seat inventories. A recovery controller can read one office's actor after an interrupted reservation workflow and choose its next authorized operation from the manifest-derived policy. The caller chooses the goal, the admissible operations and the observations the controller may use.

For an external read, pin the Observer anchor to the expected network and shard and use a by-hash transport whose response can be authenticated. Actor capabilities and revision checks govern mutation. Observer describes evidence from configured sources. The application owns its transport, authority distribution and external effects.
