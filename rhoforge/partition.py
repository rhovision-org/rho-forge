"""Factor independent resource places into separate revision scopes."""

from dataclasses import replace
import hashlib
from itertools import chain

from .compiler import (
    MAX_EPOCH,
    MAX_SOURCE,
    LimitError,
    compile_markings,
    emit_instance,
    encode,
    parse_workflow,
)


def _components(workflow):
    groups = [{name} for name in workflow.names]
    transitions = {
        action: {
            name for name, take, put in zip(workflow.names, consume, produce)
            if take or put
        }
        for action, (_, consume, produce) in workflow.transitions.items()
    }
    missions = {action: set(goal) for action, (_, goal) in workflow.missions.items()}
    for footprint in chain(transitions.values(), missions.values()):
        combined = set().union(*(group for group in groups if group & footprint))
        groups = [group for group in groups if group.isdisjoint(footprint)]
        groups.append(combined)
    return sorted(sorted(group) for group in groups), transitions, missions


def _project(workflow, names, transitions, missions):
    members = set(names)
    indices = [workflow.names.index(name) for name in names]
    initial = [workflow.initial[i] for i in indices]
    weights = {
        key: {name: invariant["weights"][name] for name in names}
        for key, invariant in workflow.invariants.items()
    }
    # An invariant may mention several components. Every primitive changes
    # only one, so the contribution of each component is itself conserved.
    invariants = {
        key: {"weights": row, "value": sum(row[k] * v for k, v in zip(names, initial))}
        for key, row in weights.items() if any(row.values())
    }
    return replace(
        workflow,
        names=names,
        caps=[workflow.caps[i] for i in indices],
        initial=initial,
        transitions={
            action: (role, tuple(consume[i] for i in indices), tuple(produce[i] for i in indices))
            for action, (role, consume, produce) in workflow.transitions.items()
            if transitions[action] <= members
        },
        invariants=invariants,
        missions={
            action: definition for action, definition in workflow.missions.items()
            if missions[action] <= members
        },
    )


def compile_partitioned(raw):
    """Return a local factory and per-lane state tables with independent clocks."""
    workflow = parse_workflow(raw)
    groups, transitions, missions = _components(workflow)
    digest = hashlib.sha256(encode(raw).encode()).hexdigest()
    lanes = {}
    source = [
        "// Rho Forge partitioned factory; spec sha256 " + digest,
        "contract factory(@lane, ret) = {",
        "  match lane {",
    ]
    for names in groups:
        lane = names[0]
        try:
            table = compile_markings(_project(workflow, names, transitions, missions))
        except LimitError as error:
            raise LimitError(f"lane {lane}: {error}") from error
        lanes[lane] = table
        source.append(f"    {encode(lane)} => {{")
        source.extend("    " + line for line in emit_instance(
            workflow.roles, table["actions"], send_only=True
        ))
        source.append("    }")
    source.extend(['    _ => { ret!("UNKNOWN_LANE") }', "  }", "}"])
    code = "\n".join(source) + "\n"
    if len(code.encode()) > MAX_SOURCE:
        raise LimitError("generated source limit; no source emitted")
    return {
        "schema": "rho-forge/partitioned-v1",
        "name": workflow.title,
        "spec_sha256": digest,
        "source_sha256": hashlib.sha256(code.encode()).hexdigest(),
        "factory": "factory",
        "roles": workflow.roles,
        "max_epoch": MAX_EPOCH,
        "lanes": lanes,
    }, code
