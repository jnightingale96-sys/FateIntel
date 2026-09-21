"""SVG diagram of a conceptual site model and its assessment (structure only, no risk shown).

Columns: sources -> environmental media (layered by longest pathway from a source) -> receptors. A medium that
is also a protected receptor (groundwater, surface water) is drawn once, in the media column, with a receptor
outline. Edge colour: green = measured data for at least one contaminant using that pathway, amber = no measured
data for any of them, grey dashed = pathway not connected to any source and receptor. Receptors with no linkage
are dashed and labelled, never called safe.
"""

from __future__ import annotations

from typing import Any
from xml.sax.saxutils import escape

from .conceptual_site_model import MEDIA, RECEPTORS, ConceptualSiteModel, assess

NODE_W, COL_GAP, ROW_GAP, PAD_TOP, PAD_X = 210, 175, 30, 84, 36
INK, MUTED, LINE = "#143234", "#5c7370", "#9fb3b0"
GREEN, AMBER, RED, BLUE = "#2f9e6e", "#d98a2b", "#b04a4a", "#3f8fa0"

Node = tuple[str, str]  # (kind, id) where kind is source / medium / receptor


def _text(value: str) -> str:
    return escape(value.replace("_", " "))


def _layers(model: ConceptualSiteModel, media: set[str]) -> dict[str, int]:
    """Longest-path depth from any release medium; edges inside a cycle (e.g. sediment<->surface water) are ignored."""
    edges = [(l.from_node, l.to_node) for l in model.links if l.from_node in media and l.to_node in media]
    reach: dict[str, set[str]] = {m: set() for m in media}
    for a, b in edges:
        reach[a].add(b)
    for _ in media:  # transitive closure, tiny graphs
        for m in media:
            reach[m] |= {z for y in reach[m] for z in reach[y]}
    layering = [(a, b) for a, b in edges if a not in reach[b]]
    depth = {m: 0 for m in media}
    for _ in media:
        for a, b in layering:
            depth[b] = max(depth[b], depth[a] + 1)
    return depth


def render_svg(model: ConceptualSiteModel, jurisdiction: str, assessment: dict[str, Any] | None = None) -> str:
    assessment = assessment or assess(model, jurisdiction)
    edge_state: dict[tuple[str, str, str], str] = {}
    for linkage in assessment["linkages"]:
        for step in linkage["path"]:
            key = (step["pathway"], step["from"], step["to"])
            if linkage["status"] == "POTENTIAL_LINKAGE_DATA_PRESENT":
                edge_state[key] = "data"
            else:
                edge_state.setdefault(key, "missing")
    unsupported = {(u["pathway"], u["from"], u["to"]) for u in assessment["unsupported_pathway_links"]}
    unlinked = {r["receptor"] for r in assessment["receptors_without_linkage"]}
    pop_names = {f["contaminant"] for f in assessment["contaminant_pops_flags"]
                 if f["status"] == "POPS_REGULATORY_STATUS_DETECTED"}

    # ---- which nodes exist and which column each sits in -------------------------------------------
    media = {m for s in model.sources for m in s.release_media}
    for link in model.links:
        media |= {n for n in (link.from_node, link.to_node) if n in MEDIA}
    media |= {r for r in model.receptors if r in MEDIA}
    depth = _layers(model, media)
    pure_receptors = [r for r in model.receptors if r not in MEDIA]
    pure_receptors += [l.to_node for l in model.links
                       if l.to_node in RECEPTORS and l.to_node not in MEDIA and l.to_node not in pure_receptors]
    pure_receptors = list(dict.fromkeys(pure_receptors))

    columns: list[list[Node]] = [[("source", s.id) for s in model.sources]]
    columns += [[("medium", m) for m in sorted(media) if depth[m] == d] for d in range(max(depth.values(), default=0) + 1)]
    columns.append([("receptor", r) for r in pure_receptors])
    columns = [c for c in columns if c]

    def key_of(name: str) -> Node:
        return ("medium", name) if name in media else ("receptor", name)

    # ---- edges (drawn between nodes; colour by data state) -----------------------------------------------
    edges: list[dict[str, Any]] = []
    for s in model.sources:
        for m in s.release_media:
            edges.append({"a": ("source", s.id), "b": ("medium", m), "colour": LINE, "dashed": False, "label": None})
    for link in model.links:
        key = (link.pathway, link.from_node, link.to_node)
        state = edge_state.get(key)
        if key in unsupported or state is None:
            colour, dashed = LINE, True
        else:
            colour, dashed = (GREEN if state == "data" else AMBER), False
        edges.append({"a": key_of(link.from_node), "b": key_of(link.to_node), "colour": colour,
                      "dashed": dashed, "label": link.pathway})

    # order nodes within columns by the average position of their neighbours in earlier columns (fewer crossings)
    col_of = {n: ci for ci, col in enumerate(columns) for n in col}
    rank: dict[Node, float] = {n: i for i, n in enumerate(columns[0])}
    for ci in range(1, len(columns)):
        def barycentre(node: Node) -> float:
            preds = [rank[e["a"]] for e in edges if e["b"] == node and e["a"] in rank and col_of[e["a"]] < ci]
            return sum(preds) / len(preds) if preds else 1e6
        columns[ci].sort(key=lambda n: (barycentre(n), n[1]))
        for i, n in enumerate(columns[ci]):
            rank[n] = i

    # ---- geometry ----------------------------------------------------------------------------------------
    outs = {n: [e for e in edges if e["a"] == n] for n in col_of}
    ins = {n: [e for e in edges if e["b"] == n] for n in col_of}

    def node_height(node: Node) -> int:
        base = 46 + 16 * len(next(s for s in model.sources if s.id == node[1]).contaminants) if node[0] == "source" else 46
        return max(base, 16 * max(len(outs[node]), len(ins[node])) + 16)

    heights = {n: node_height(n) for n in col_of}
    col_h = [sum(heights[n] for n in col) + ROW_GAP * (len(col) - 1) for col in columns]
    tallest = max(col_h)
    pos: dict[Node, tuple[float, float]] = {}
    for ci, col in enumerate(columns):
        y = PAD_TOP + (tallest - col_h[ci]) / 2
        for n in col:
            pos[n] = (PAD_X + ci * (NODE_W + COL_GAP), y)
            y += heights[n] + ROW_GAP
    canvas_w = PAD_X * 2 + len(columns) * NODE_W + (len(columns) - 1) * COL_GAP
    canvas_h = tallest + PAD_TOP + 92

    def centre_y(n: Node) -> float:
        return pos[n][1] + heights[n] / 2

    def port_y(n: Node, edge: dict[str, Any], side: str) -> float:
        group = sorted(outs[n] if side == "out" else ins[n],
                       key=lambda e: centre_y(e["b"] if side == "out" else e["a"]))
        return pos[n][1] + heights[n] * (group.index(edge) + 1) / (len(group) + 1)

    body: list[str] = []
    labels: list[str] = []
    for edge in edges:
        a, b = edge["a"], edge["b"]
        ax, bx = pos[a][0], pos[b][0]
        y1 = port_y(a, edge, "out")
        y2 = port_y(b, edge, "in")
        x1 = ax + NODE_W
        if bx > ax:
            x2 = bx
            d = f"M{x1:.1f},{y1:.1f} C{x1 + COL_GAP / 2:.1f},{y1:.1f} {x2 - COL_GAP / 2:.1f},{y2:.1f} {x2:.1f},{y2:.1f}"
            lx, ly = x2 - COL_GAP / 2, y2 - 4
        else:  # same column or back-edge: loop out to the right of both nodes
            x2 = bx + NODE_W
            bulge = max(x1, x2) + 44
            d = f"M{x1:.1f},{y1:.1f} C{bulge:.1f},{y1:.1f} {bulge:.1f},{y2:.1f} {x2 + 4:.1f},{y2:.1f}"
            lx, ly = bulge - 6, (y1 + y2) / 2
        dash = ' stroke-dasharray="6 5"' if edge["dashed"] else ""
        body.append(f'<path d="{d}" fill="none" stroke="{edge["colour"]}" stroke-width="2"{dash} '
                    f'marker-end="url(#arrow-{edge["colour"][1:]})"/>')
        if edge["label"]:
            labels.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" font-size="9.5" fill="{MUTED}" '
                          f'stroke="#ffffff" stroke-width="3" paint-order="stroke">{_text(edge["label"])}</text>')

    for node, (x, y) in pos.items():
        kind, ident = node
        h = heights[node]
        if kind == "source":
            source = next(s for s in model.sources if s.id == ident)
            body.append(f'<rect x="{x}" y="{y}" width="{NODE_W}" height="{h}" fill="#f2f7f6" stroke="{INK}" stroke-width="1.5"/>')
            body.append(f'<text x="{x + 10}" y="{y + 18}" font-size="11" font-weight="700" fill="{INK}">{escape(source.id)} · {_text(source.kind)}</text>')
            for i, c in enumerate(source.contaminants):
                pop = " · POP" if c.name in pop_names else ""
                body.append(f'<text x="{x + 10}" y="{y + 38 + 16 * i}" font-size="10.5" fill="{INK}">{escape(c.name)} '
                            f'<tspan fill="{MUTED}">({_text(c.contaminant_group)})</tspan><tspan font-weight="700" fill="{RED}">{pop}</tspan></text>')
        else:
            is_receptor = kind == "receptor" or ident in model.receptors
            dead = ident in unlinked
            stroke = RED if dead else (BLUE if is_receptor else INK)
            dash = ' stroke-dasharray="5 4"' if dead else ""
            fill = "#ffffff" if is_receptor else "#f7faf9"
            body.append(f'<rect x="{x}" y="{y}" width="{NODE_W}" height="{h}" fill="{fill}" stroke="{stroke}" '
                        f'stroke-width="{2.2 if is_receptor else 1.4}"{dash}/>')
            body.append(f'<text x="{x + 10}" y="{y + 20}" font-size="12" font-weight="700" fill="{INK}">{_text(ident)}</text>')
            sub = ("receptor: no linkage identified" if dead else "receptor") if is_receptor else "environmental medium"
            body.append(f'<text x="{x + 10}" y="{y + 36}" font-size="10" fill="{RED if dead else MUTED}">{sub}</text>')

    ly = canvas_h - 34
    legend: list[str] = []
    lx = PAD_X
    for colour, dashed, text in ((GREEN, False, "measured data for at least one contaminant"),
                                 (AMBER, False, "no measured data"), (LINE, True, "pathway not connected")):
        dash = ' stroke-dasharray="6 5"' if dashed else ""
        legend.append(f'<line x1="{lx}" y1="{ly}" x2="{lx + 30}" y2="{ly}" stroke="{colour}" stroke-width="2"{dash}/>')
        legend.append(f'<text x="{lx + 38}" y="{ly + 4}" font-size="10.5" fill="{MUTED}">{text}</text>')
        lx += 38 + len(text) * 5.6 + 26
    legend.append(f'<rect x="{lx}" y="{ly - 7}" width="24" height="14" fill="#fff" stroke="{RED}" stroke-dasharray="4 3" stroke-width="1.6"/>')
    legend.append(f'<text x="{lx + 32}" y="{ly + 4}" font-size="10.5" fill="{MUTED}">receptor with no linkage identified (not a finding of no risk)</text>')

    markers = "".join(
        f'<marker id="arrow-{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
        f'<path d="M0,0 L10,5 L0,10 Z" fill="{c}"/></marker>' for c in (LINE, GREEN, AMBER))
    head = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {canvas_w:.0f} {canvas_h:.0f}" width="{canvas_w:.0f}" '
        f'height="{canvas_h:.0f}" font-family="Inter, Segoe UI, Arial, sans-serif" role="img" '
        f'aria-label="Conceptual site model diagram">',
        f"<defs>{markers}</defs>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{PAD_X}" y="30" font-size="15" font-weight="800" fill="{INK}">Conceptual site model · {escape(jurisdiction)}</text>',
        f'<text x="{PAD_X}" y="50" font-size="11" fill="{MUTED}">Source → medium → receptor. Potential linkages only: no exposure or risk is calculated.</text>',
    ]
    return "\n".join(head + body + labels + legend + ["</svg>"])


# Entirely fictional site, for documentation and demonstration only.
EXAMPLE_SITE_PAYLOAD: dict[str, Any] = {
    "jurisdiction": "UK",
    "sources": [
        {"id": "S1", "kind": "former_manufacturing", "release_media": ["soil"], "contaminants": [
            {"name": "lead", "contaminant_group": "metal_inorganic"},
            {"name": "PCB-153", "contaminant_group": "legacy_pop_organic", "cas_number": "1336-36-3"}]},
        {"id": "S2", "kind": "spill", "release_media": ["groundwater"], "contaminants": [
            {"name": "trichloroethylene", "contaminant_group": "hydrocarbon_solvent"}]},
    ],
    "receptors": ["residents", "workers", "groundwater", "surface_water", "aquatic_organisms", "wildlife"],
    "links": [
        {"pathway": "ingestion", "from": "soil", "to": "residents"},
        {"pathway": "dermal_contact", "from": "soil", "to": "workers"},
        {"pathway": "soil_to_groundwater", "from": "soil", "to": "groundwater"},
        {"pathway": "groundwater_to_surface_water", "from": "groundwater", "to": "surface_water"},
        {"pathway": "runoff", "from": "soil", "to": "surface_water"},
        {"pathway": "direct_contact_ecological", "from": "surface_water", "to": "aquatic_organisms"},
        {"pathway": "volatilisation", "from": "groundwater", "to": "air"},
        {"pathway": "inhalation", "from": "air", "to": "residents"},
        {"pathway": "erosion", "from": "soil", "to": "sediment"},
    ],
    # Soil has not been sampled yet in this fictional site: only the groundwater plume is measured.
    "measured": {"groundwater": ["trichloroethylene"]},
}
