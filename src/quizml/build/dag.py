"""Target dependency graph (DAG), alias expansion, and topological sorting."""

from graphlib import CycleError, TopologicalSorter

from quizml.exceptions import QuizMLConfigError


def get_required_target_names_set(name, targets):
    """Resolves the set of the names of the required targets including dependencies."""
    if not name:
        return set()

    pending = list(name) if isinstance(name, list) else [name]

    dep_map = {}
    for target in targets:
        t_name = target.get("name", "")
        if t_name and "dep" in target:
            deps = target["dep"]
            dep_map[t_name] = deps if isinstance(deps, list) else [deps]

    required_set = set(pending)
    visited = set()

    while pending:
        curr = pending.pop()
        if curr in visited:
            continue
        visited.add(curr)
        for dep in dep_map.get(curr, []):
            required_set.add(dep)
            pending.append(dep)

    return required_set


def expand_target_aliases(names, targets, aliases):
    """Expand selected aliases to configured target names."""
    if not names:
        return names
    if not isinstance(aliases, dict):
        raise QuizMLConfigError("The 'aliases' config setting must be a mapping.")

    target_names = {target.get("name") for target in targets if target.get("name")}
    collisions = target_names.intersection(aliases)
    if collisions:
        names_str = ", ".join(sorted(collisions))
        raise QuizMLConfigError(
            f"Target aliases conflict with target names: {names_str}."
        )
    expanded = []
    active = []

    def expand(name):
        if name in aliases:
            if name in active:
                cycle = " -> ".join([*active, name])
                raise QuizMLConfigError(f"Circular target alias detected: {cycle}")
            value = aliases[name]
            if isinstance(value, str):
                members = [value]
            elif isinstance(value, list) and all(
                isinstance(item, str) for item in value
            ):
                members = value
            else:
                raise QuizMLConfigError(
                    f"Target alias '{name}' must be a target name or a list of target names."
                )
            active.append(name)
            for member in members:
                expand(member)
            active.pop()
        elif name in target_names:
            expanded.append(name)
        else:
            raise QuizMLConfigError(f"Unknown target or target alias '{name}'.")

    for name in names if isinstance(names, list) else [names]:
        expand(name)
    return list(dict.fromkeys(expanded))


def sort_targets_topologically(targets, required_names=None):
    """Sorts target configs topologically according to their 'dep' attribute."""
    all_target_names = {t.get("name") for t in targets if t.get("name")}
    for target in targets:
        name = target.get("name", "<unnamed>")
        dep = target.get("dep")
        if not dep:
            continue
        dependencies = dep if isinstance(dep, list) else [dep]
        for dependency in dependencies:
            if dependency not in all_target_names:
                raise QuizMLConfigError(
                    f"Target '{name}' depends on unknown target '{dependency}'."
                )

    target_by_name = {}
    for t in targets:
        name = t.get("name")
        if name and (required_names is None or name in required_names):
            target_by_name[name] = t

    graph = {}
    for name, t in target_by_name.items():
        dep = t.get("dep")
        if not dep:
            graph[name] = set()
        elif isinstance(dep, list):
            graph[name] = {d for d in dep if d in target_by_name}
        else:
            graph[name] = {dep} if dep in target_by_name else set()

    try:
        ts = TopologicalSorter(graph)
        sorted_names = list(ts.static_order())
    except CycleError as err:
        raise QuizMLConfigError(
            f"Circular dependency detected among targets: {err}"
        ) from err

    ordered = [target_by_name[n] for n in sorted_names if n in target_by_name]

    for t in targets:
        if "name" not in t and required_names is None:
            ordered.append(t)

    return ordered
