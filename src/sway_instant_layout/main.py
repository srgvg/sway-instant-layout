import datetime
import i3ipc
import json
import math
import subprocess
import sys
from pathlib import Path
from . import layouts, __version__


counter_file = Path("~/.local/share/sway-instant-layout/counter.json").expanduser()
counter_file.parent.mkdir(exist_ok=True, parents=True)


def swaymsg(*args):
    """Run a swaymsg command. Each argument is passed as a separate token."""
    subprocess.check_call(["swaymsg"] + list(args), stdout=subprocess.DEVNULL)


def get_workspace_windows():
    """Return (ordered_con_ids, focused_con_id) for tiled windows in current workspace."""
    i3 = i3ipc.Connection()
    focused = i3.get_tree().find_focused()
    if focused is None:
        return [], None
    workspace = focused.workspace()
    all_leaves = workspace.leaves()
    floating_ids = {f.id for f in getattr(workspace, "floating_nodes", [])}
    tiled = [l for l in all_leaves if l.id not in floating_ids and l.type != "floating_con"]
    tiled_ids = {l.id for l in tiled}
    focused_id = focused.id if focused.id in tiled_ids else (tiled[0].id if tiled else None)
    return [l.id for l in tiled], focused_id


def focus_window(con_id):
    swaymsg(f"[con_id={con_id}]", "focus")


def normalize_tree(tree):
    """Normalize the layout JSON tree from get_json(), flattening nested lists.

    The original layout helpers (get_stack, node) sometimes produce structures like:
        {"nodes": [leaf_node, [container_dict]]}
    where a child is wrapped in a list. This function flattens those.
    """
    if tree is False or tree is None:
        return None
    if isinstance(tree, list):
        if len(tree) == 0:
            return None
        if len(tree) == 1:
            return normalize_tree(tree[0])
        # Multiple top-level elements: wrap in a splith container
        return {
            "type": "con",
            "layout": "splith",
            "nodes": [normalize_tree(x) for x in tree if x],
        }
    result = dict(tree)
    if "nodes" in result:
        new_nodes = []
        for child in result["nodes"]:
            if isinstance(child, list):
                for item in child:
                    n = normalize_tree(item)
                    if n:
                        new_nodes.append(n)
            elif child:
                new_nodes.append(normalize_tree(child))
        result["nodes"] = [n for n in new_nodes if n]
    return result


def is_leaf(node):
    """A leaf node represents a window slot (has swallows defined)."""
    return bool(node.get("swallows"))


def apply_layout(layout, dry_run=False):
    """Apply a layout to the current sway workspace using IPC commands.

    Replaces the i3 append_layout + xdotool unmap/remap + swallow approach
    with a scratchpad-based technique:
      1. Move all tiled windows to scratchpad.
      2. Place them back one by one, using split/focus parent commands to
         build the desired container tree.
    """
    windows, focused_id = get_workspace_windows()
    if not windows:
        print("No tiled windows found in current workspace.")
        return

    window_count = len(windows)

    # Put focused window first so it becomes the "main" window in the layout
    if focused_id and focused_id in windows:
        windows = [focused_id] + [w for w in windows if w != focused_id]

    t = layout.get_json(window_count)
    if isinstance(t, tuple):
        layout_dict, remap_order = t
        if set(range(window_count)) != set(remap_order):
            raise ValueError("Layout returned invalid remap order")
        windows = [windows[ii] for ii in remap_order]
    else:
        layout_dict = t

    if layout_dict is False:
        return

    tree = normalize_tree(layout_dict)
    if tree is None:
        return

    if dry_run:
        print("Layout tree (normalized):")
        print(json.dumps(tree, indent=4))
        print("\nWindows in placement order:", windows)
        return

    # Step 1: move all windows to scratchpad (they become floating)
    for win_id in windows:
        swaymsg(f"[con_id={win_id}]", "move", "container", "to", "scratchpad")

    # Step 2: place windows back according to the layout tree
    win_iter = iter(windows)

    def set_container_split(layout_type):
        if layout_type == "tabbed":
            swaymsg("layout", "tabbed")
        elif layout_type == "stacking":
            swaymsg("layout", "stacking")
        elif layout_type == "splitv":
            swaymsg("split", "v")
        else:  # splith
            swaymsg("split", "h")

    def place_window(win_id):
        """Move a window from scratchpad to workspace and make it tiled."""
        swaymsg(f"[con_id={win_id}]", "move", "container", "to", "workspace", "current")
        swaymsg(f"[con_id={win_id}]", "focus")
        swaymsg("floating", "disable")
        swaymsg(f"[con_id={win_id}]", "focus")

    def process_node(node):
        """
        Recursively traverse the layout tree, placing windows.

        Returns (first_win_id, is_container):
          - first_win_id: con_id of the first window placed in this subtree,
            used as the anchor for split setup before the next sibling.
          - is_container: True if this node had child containers (not a leaf).
            When True, the caller will issue 'focus parent' before splitting,
            so the split applies at the container level rather than window level.
        """
        if is_leaf(node):
            win = next(win_iter, None)
            if win is None:
                return None, False
            place_window(win)
            return win, False

        layout_type = node.get("layout", "splith")
        children = node.get("nodes", [])
        first_in_node = None
        prev_first = None
        prev_is_container = False

        for i, child in enumerate(children):
            if i > 0 and prev_first is not None:
                # Refocus the anchor window before setting up the split
                swaymsg(f"[con_id={prev_first}]", "focus")
                if prev_is_container:
                    # The previous sibling was a multi-window container.
                    # Move focus to the container level so split applies there,
                    # placing the next group as a sibling of the whole container.
                    swaymsg("focus", "parent")
                set_container_split(layout_type)

            child_first, child_is_container = process_node(child)

            if child_first is not None:
                if first_in_node is None:
                    first_in_node = child_first
                prev_first = child_first
                prev_is_container = child_is_container

        return first_in_node, True

    process_node(tree)

    # Restore focus to the original active window
    if focused_id:
        focus_window(focused_id)


def load_usage():
    try:
        with open(counter_file, "r") as op:
            return json.load(op)
    except (OSError, ValueError):
        return {}


def count_usage(layout_name):
    usage = load_usage()
    if layout_name not in usage:
        usage[layout_name] = (0, datetime.datetime.now().timestamp())
    usage[layout_name] = (
        usage[layout_name][0] + 1,
        datetime.datetime.now().timestamp(),
    )
    with open(counter_file, "w") as op:
        json.dump(usage, op)


def list_layouts_in_smart_order():
    """List layouts in smart order: most common on top (by log10 usage),
    within one log10 unit sorted by most-recently-used."""
    usage = load_usage()
    sort_me = []
    for layout in layouts.layouts:
        if " " in layout.name:
            raise ValueError(
                f"No spaces in layout names please. Offender: '{layout.name}'"
            )
        for alias in [layout.name] + layout.aliases:
            usage_count, last_used = usage.get(
                alias, (0, datetime.datetime.now().timestamp())
            )
            if alias == layout.name:
                desc = alias
            else:
                desc = f"{alias} ({layout.name})"
            sort_me.append(
                (-1 * math.ceil(math.log10(usage_count + 1)), -1 * last_used, desc)
            )
    sort_me.sort()
    for _, _, name in sort_me:
        print(name)


def print_help():
    print(
        """sway-instant-layout applies ready made layouts to sway workspaces,
    based on the numerical position of the windows.

    Call with '--list' to get a list of available layouts (and their aliases).

    Call with '--desc' to get detailed information about every layout available.

    Call with the name of a layout to apply it to the current workspace.

    Call with '-' to read layout name from stdin.

    Call with 'name --dry-run' to inspect the layout tree and window placement order.

    Call with '--notification' + the name of a layout to apply the layout
    and show a desktop notification with the layout name.

    To integrate into sway, add this to your sway config:
        bindsym $mod+Escape exec "sway-instant-layout --list | wofi --dmenu | sway-instant-layout -"

    """
    )
    sys.exit(0)


def print_desc():
    import textwrap

    for layout_class in layouts.layouts:
        print(f"Layout: {layout_class.name}")
        print(f"Aliases: {layout_class.aliases}")
        print(textwrap.indent(textwrap.dedent(layout_class.description), "\t"))
        print("")
        print("-" * 80)
        print("")


def main():
    showNotification = False
    if len(sys.argv) == 1 or sys.argv[1] == "--help":
        print_help()
    elif sys.argv[1] == "--desc":
        print_desc()
        sys.exit(0)
    elif sys.argv[1] == "--version":
        print(__version__)
        sys.exit(0)
    elif sys.argv[1] == "--list":
        list_layouts_in_smart_order()
        sys.exit(0)
    elif sys.argv[1] == "-":
        query = sys.stdin.readline().strip()
        print(f'query "{query}"')
        if not query.strip():  # e.g. wofi cancel
            sys.exit(0)
    else:
        if sys.argv[1] == "--notification":
            showNotification = True
            query = sys.argv[2]
        else:
            query = sys.argv[1]
    if " " in query:
        query = query[: query.find(" ")]
    for layout_class in layouts.layouts:
        if query == layout_class.name or query in layout_class.aliases:
            apply_layout(layout_class(), "--dry-run" in sys.argv)
            if showNotification:
                subprocess.check_call(
                    ["notify-send", "-t", "2000", "Applied layout", layout_class.name]
                )
            count_usage(query)
            sys.exit(0)
    else:
        print("Could not find the requested layout")
        sys.exit(1)
