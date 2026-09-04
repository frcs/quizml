"""Target dependency graph and topological sorting."""

from graphlib import CycleError, TopologicalSorter

from quizml.exceptions import QuizMLConfigError


def get_required_target_names_set(name, targets):
    """Resolves the set of names for all required dependency targets."""
    if not name:
        return set()

    if isinstance(name, list):
        pending = list(name)
    else:
        pending = [name]

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


def sort_targets_topologically(targets, required_names=None):
    """Sorts target configs topologically according to their 'dep' attribute.

    Guarantees dependencies are compiled before dependents.
    """
    target_by_name = {}
    for t in targets:
        name = t.get("name")
        if name:
            if required_names is None or name in required_names:
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

    # Preserve any anonymous targets without a name
    for t in targets:
        if "name" not in t and required_names is None:
            ordered.append(t)

    return ordered
