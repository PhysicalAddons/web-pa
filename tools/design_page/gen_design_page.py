"""Build web-pa's design-documents page from the PA2 repo.

One MkDocs Material page: the rendering-pipeline architecture reference,
the five design documents (docs/design-*.md), and the credits and
references (CREDITS.md + THIRD_PARTY_LICENSES.md).

Content is kept as written; only the markdown plumbing changes: headings
are demoted one level (each document becomes an H2 section), headings
wrapped over two `##` lines are joined, two-space list nesting becomes
the four spaces Python-Markdown needs, underscores that would read as
emphasis are escaped, and every section gets a stable explicit anchor
plus a mini index of its sub-sections.
"""
import re
import sys
from pathlib import Path

# Run from anywhere:  python tools/design_page/gen_design_page.py
# The add-on repo is expected next to web-pa (Projects/PSA2/physical_atmosphere²);
# set PA2_REPO to point elsewhere.
import os

HERE = Path(__file__).resolve().parent
WEB_PA = HERE.parents[1]
REPO = Path(os.environ.get("PA2_REPO") or WEB_PA.parent / "PSA2" / "physical_atmosphere²")
SRC = REPO / "docs"
OUT = WEB_PA / "docs" / "design-documents.md"

# Newest first, like the release notes.
DOCS = [
    dict(
        file="design-auto-exposure-2026-09.md",
        slug="auto-exposure",
        label="shipped",
        css="label-fixed",
        status="Shipping · Auto modes 3.0.0-beta · Meter choice 3.0.7-beta",
        date="07.09.2026",
        summary=(
            "Auto range placement, auto exposure and auto white balance on "
            "one measurement core: a percentile-band meter over the "
            "published planes, an adaptation curve, and the physical "
            "illuminant. Amended with the Meter choice (Sky / Viewport / "
            "Incident), the offscreen viewport meter and what it took to "
            "make it read the sky, and the law that keeps the scene's own "
            "lamps neutral under the Range placement."
        ),
    ),
    dict(
        file="design-ksa-lut-atmosphere-2026-09.md",
        slug="lut-atmosphere",
        label="shipped",
        css="label-fixed",
        status="Shipping · the default sky since 3.0.0-beta",
        date="05.09.2026",
        summary=(
            "The visible sky as a lookup-table chain — transmittance, "
            "sky-view and aerial LUTs resolved by the rectangle and the "
            "lighting equirect — with the cloud pipeline ported from KSA "
            "on top. The decision, the resources, every phase with its "
            "measured gate, the review amendments and the open decisions."
        ),
    ),
    dict(
        file="design-refraction-2026-09.md",
        slug="refraction",
        label="design",
        css="label-research",
        status="Shipping · every stage landed · amended 10.09.2026",
        date="03.09.2026",
        figure="refraction_figure.html",
        summary=(
            "One ray-marched refraction law for sky, ground and celestials: "
            "bending from the air's pressure and temperature profile, the "
            "green flash, horizon shimmer and space views. Every stage has "
            "landed: bent view rays for sky, ground, clouds and celestials, "
            "dispersion, the shimmer split and Young's inversion presets. "
            "Amended with the sun's chromatic limb law, the LUT sky's "
            "horizon-band transmittance limit, and what landed after: the "
            "near shimmer on turbulence physics, heat blur, gravity-wave "
            "mirage layers, and the air masses retired in favour of them."
        ),
    ),
    dict(
        file="design-1to1-window-sky.md",
        slug="window-sky",
        label="shipped",
        css="label-fixed",
        status="Shipped · amended 10.09.2026",
        date="04.08.2026",
        summary=(
            "The sky and composed ground are marched at exact view "
            "resolution through Window-coordinate mapping, with EEVEE's own "
            "temporal AA recipe and the hybrid cut against scene geometry. "
            "Amended with what actually shipped and where it departs from "
            "the plan; one fovea variant for both engines and 1:1 clouds "
            "since."
        ),
    ),
    dict(
        file="design-cloud-temporal-upscale.md",
        slug="cloud-upscale",
        label="shipped",
        css="label-fixed",
        status="Shipped · superseded in part · interim system",
        date="05.08.2026",
        summary=(
            "The cloud march leaves the 1:1 sky pass for its own interleaved "
            "low-resolution pass with a KSA-style temporal resolve, the KSA "
            "march port and the dual-paraboloid shadow volume. Includes the "
            "fidelity audit against the KSA sources and the cost "
            "measurements. Since then the light grid and the house march "
            "are gone and the density model is the ported one; the clouds "
            "are an interim system pending the real cloud renderer."
        ),
    ),
    dict(
        file="design-north-offset.md",
        slug="north-offset",
        label="shipped",
        css="label-fixed",
        status="Implemented 04.09.2026",
        date="31.07.2026",
        summary=(
            "A single angle that rotates the modelled world against true "
            "north, so GIS-derived geometry keeps its imported orientation. "
            "Scoped and costed on 31.07.2026, implemented on 04.09.2026 as "
            "recommended: sun, stars, cloud map, wind, city lights, flight "
            "paths and the compass all turn together."
        ),
    ),
    dict(
        file="design-ground-shader-2026-07.md",
        slug="ground-shader",
        label="shipped",
        css="label-fixed",
        status="Shipped · 2.7 · BRDF superseded 08.2026",
        date="07.2026",
        summary=(
            "A dedicated GPU compose pass shades the planet surface "
            "offscreen and folds it into the scatter/transmittance pair: "
            "water reflections, cloud bounce, night lights, moonlight, the "
            "heightmap and object shadows on the ground. The Hapke-lite land "
            "BRDF it recommends was replaced by the Principled model in "
            "August 2026."
        ),
    ),
]

HEAD = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
FENCE = re.compile(r"^\s*```")
CODE_SPAN = re.compile(r"(`+[^`]*`+)")


def slugify(text, limit=48):
    text = re.sub(r"[`*_\"']", "", text)
    text = re.sub(r"[^A-Za-z0-9]+", "-", text.lower()).strip("-")
    if len(text) > limit:
        text = text[:limit].rstrip("-")
    return text


def short_title(text):
    """Index link text: the heading up to its first parenthesis."""
    cut = text.find(" (")
    if cut > 0:
        text = text[:cut]
    return text.strip()


def escape_underscores(segment):
    """Escape underscores that Python-Markdown could read as emphasis
    delimiters (outside code spans).  Intra-word underscores are left
    alone; the sources never use _italics_."""
    segment = re.sub(r"(?<![\w\\])_(?=\w)", r"\\_", segment)
    segment = re.sub(r"(?<=\w)_(?![\w])", r"\\_", segment)
    return segment


def escape_line(line):
    parts = CODE_SPAN.split(line)
    return "".join(p if p.startswith("`") else escape_underscores(p) for p in parts)


BOLD = re.compile(r"\*\*(?=\S)[^*]+?(?<=\S)\*\*")
ITALIC = re.compile(r"(?<![\w*\\])\*(?=[^\s*])[^*]*?(?<=[^\s*])\*(?![\w*])")


def escape_stars(block):
    """Escape asterisks that are multiplication signs, not emphasis.
    `block` is one paragraph (lines joined with newlines) with code spans
    already excluded; **bold** and *italic* pairs that follow the
    CommonMark left/right-flanking rule are kept, every other `*` is
    escaped."""
    keep = []

    def stash(m):
        keep.append(m.group(0))
        return f"\x00{len(keep) - 1}\x00"

    block = BOLD.sub(stash, block)
    block = ITALIC.sub(stash, block)
    block = block.replace("*", r"\*")
    return re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], block)


def escape_block(lines):
    """Apply the asterisk rule to a paragraph's worth of already
    underscore-escaped lines, leaving code spans untouched."""
    text = "\n".join(lines)
    parts = CODE_SPAN.split(text)
    text = "".join(p if p.startswith("`") else escape_stars(p) for p in parts)
    return text.split("\n")


LIST_ITEM = re.compile(r"^\s*(?:[-*]|\d+\.)\s+")  # the docs never use "+" bullets
TWO_SPACE = re.compile(r"^  \S")
GAP = re.compile(r"\S {2,}\S")


def aligned_run(lines, i):
    """Length of a column-aligned note block starting at lines[i]: three
    or more two-space-indented lines, most of them with an internal
    column gap."""
    j = i
    while j < len(lines) and TWO_SPACE.match(lines[j]):
        j += 1
    n = j - i
    if n >= 3 and sum(bool(GAP.search(x)) for x in lines[i:j]) > n // 2:
        return n
    return 0


def fix_blocks(lines):
    """Two Python-Markdown quirks the sources were not written for:
    a list cannot interrupt a paragraph (it needs a blank line first),
    and a column-aligned run of two-space-indented lines is prose to it,
    which collapses the alignment.  Insert the blank line, and turn
    aligned runs of three or more lines into fenced code."""
    out, in_fence, i = [], False, 0
    while i < len(lines):
        ln = lines[i]
        if FENCE.match(ln):
            in_fence = not in_fence
            out.append(ln)
            i += 1
            continue
        if not in_fence:
            n = aligned_run(lines, i)
            prev = out[-1] if out else ""
            if (n and prev.strip() and not prev.startswith(" ")
                    and prev.rstrip().endswith(":") and not LIST_ITEM.match(prev)):
                out += ["", "```"] + [x[2:] for x in lines[i:i + n]] + ["```", ""]
                i += n
                continue
            if (LIST_ITEM.match(ln) and out and out[-1].strip()
                    and not LIST_ITEM.match(out[-1]) and not HEAD.match(out[-1])):
                out.append("")
        out.append(ln)
        i += 1
    return out


def escape_paragraphs(lines):
    """Run escape_block over each blank-line-separated block outside
    fenced code; indented (4-space) code blocks are left alone."""
    out, block, in_fence = [], [], False

    def flush():
        if block:
            if all(ln.startswith("    ") or not ln.strip() for ln in block):
                out.extend(block)
            else:
                out.extend(escape_block(block))
            block.clear()

    for ln in lines:
        if FENCE.match(ln):
            flush()
            in_fence = not in_fence
            out.append(ln)
            continue
        if in_fence:
            out.append(ln)
            continue
        if not ln.strip():
            flush()
            out.append(ln)
            continue
        block.append(ln)
    flush()
    return out


def read_items(path):
    """Lines with headings joined: ("head", level, text) | ("line", text)."""
    lines = path.read_text(encoding="utf-8").split("\n")
    items = []
    in_fence = False
    i = 0
    while i < len(lines):
        ln = lines[i]
        if FENCE.match(ln):
            in_fence = not in_fence
            items.append(("line", ln))
            i += 1
            continue
        m = HEAD.match(ln) if not in_fence else None
        if not m:
            items.append(("line", ln))
            i += 1
            continue
        level, text = len(m.group(1)), m.group(2)
        j = i + 1
        # Join a heading wrapped onto following lines of the same level.
        while j < len(lines):
            m2 = HEAD.match(lines[j])
            if m2 and len(m2.group(1)) == level:
                text += " " + m2.group(2).strip()
                j += 1
            else:
                break
        items.append(("head", level, text))
        i = j
    return items


def convert(path, slug, title_override=None):
    """Demote a document one level under an H2 with explicit anchors.
    Returns (title, sections, body_lines)."""
    items = read_items(path)
    title = title_override or next(t for k, *rest in items if k == "head" for t in [rest[1]] if rest[0] == 1)
    # fix_blocks works on raw lines; run it on the line runs between
    # headings so heading tuples stay intact.
    fixed, run = [], []
    for it in items:
        if it[0] == "line":
            run.append(it[1])
        else:
            fixed += [("line", x) for x in fix_blocks(run)]
            run = []
            fixed.append(it)
    fixed += [("line", x) for x in fix_blocks(run)]
    items = fixed
    used = set()
    sections = []
    out = []
    in_fence = False
    for it in items:
        if it[0] == "line":
            ln = it[1]
            if FENCE.match(ln):
                in_fence = not in_fence
                out.append(ln)
                continue
            if in_fence:
                out.append(ln)
                continue
            # Two-space hanging indents / nesting -> four spaces so nested
            # bullets and continuation paragraphs stay inside their item.
            if ln.startswith("  ") and not ln.startswith("   "):
                ln = "  " + ln
            out.append(escape_line(ln))
            continue
        _, level, text = it
        if level == 1:
            continue  # the document title becomes the section header
        if level == 2:
            sid = f"{slug}-{slugify(short_title(text))}"
            base, n = sid, 2
            while sid in used:
                sid = f"{base}-{n}"
                n += 1
            used.add(sid)
            sections.append((sid, short_title(text)))
            out.append(f"{'#' * (level + 1)} {escape_line(text)} {{#{sid}}}")
        else:
            out.append(f"{'#' * (level + 1)} {escape_line(text)}")
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return title, sections, escape_paragraphs(out)


def section_header(title, slug, meta, sections, index_label="In this document"):
    head = [f"## {escape_line(title)} {{#{slug}}}", "", meta, ""]
    if sections:
        links = " · ".join(f"[{escape_line(t)}](#{sid})" for sid, t in sections)
        head += [f"**{index_label}:** {links}", ""]
    return head


def render_doc(doc):
    title, sections, body = convert(SRC / doc["file"], doc["slug"])
    meta = (
        f"`{doc['label']}:`{{: .{doc['css']} }} {doc['status']} · "
        f"{doc['date']} · `docs/{doc['file']}`"
    )
    out = section_header(title, doc["slug"], meta, sections)
    if doc.get("figure"):
        out += [(HERE / doc["figure"]).read_text(encoding="utf-8").rstrip(), ""]
    return title, out + body


def render_credits():
    title, sections, body = convert(REPO / "CREDITS.md", "credits", "Credits & references")
    meta = "`reference:`{: .label-improvements } As shipped in the add-on · `CREDITS.md` · `THIRD_PARTY_LICENSES.md`"
    _, _, lic = convert(REPO / "THIRD_PARTY_LICENSES.md", "licenses")
    lic_id = "credits-third-party-licenses"
    sections = sections + [(lic_id, "Third-party licenses")]
    out = section_header(title, "credits", meta, sections)
    out += body
    out += ["", f"### Third-party licenses {{#{lic_id}}}", ""]
    # THIRD_PARTY_LICENSES.md's own sections become H4 under this H3.
    out += [re.sub(r"^###(?= )", "####", ln) for ln in lic]
    return title, out


def main():
    pipeline = (HERE / "pipeline_section.md").read_text(encoding="utf-8").rstrip()
    page = [
        "---",
        "title: Design documents",
        "---",
        "",
        "# Design documents",
        "",
        "How _Physical Atmosphere²_ renders, and why it renders that way: "
        "the architecture reference for the rendering pipeline, the "
        "engineering design documents behind its major features, and the "
        "credits and references the work stands on. Everything is "
        "published as written. The design documents are working notes "
        "rather than user documentation: each records a direction, the "
        "physics and architecture chosen for it and the stage plan, and is "
        "amended as stages land with what actually shipped and where it "
        "departed from the plan. \"User\" in them is the add-on's author "
        "setting the direction, commit hashes and file paths refer to the "
        "add-on's source tree, and dates are when a decision was made. For "
        "what the features do, see the "
        "[documentation](/physical-atmosphere/documentation/) and the "
        "[release notes](/physical-atmosphere/release-notes/).",
        "",
        "| Section | Status | Date |",
        "| --- | --- | --- |",
        "| [Rendering pipeline](#pipeline)<br><small>The architecture "
        "reference: one atmosphere core compiled many ways, the rect and "
        "equirect renderers, the TAA round, shader assembly, every pass and "
        "LUT, and how the sky reaches EEVEE and Cycles.</small> "
        "| `reference:`{: .label-improvements } Architecture reference "
        "| 03.09.2026 |",
    ]
    rendered = [pipeline]
    for doc in DOCS:
        title, body = render_doc(doc)
        rendered.append("\n".join(body))
        page.append(
            f"| [{escape_line(title)}](#{doc['slug']})<br><small>{doc['summary']}</small> "
            f"| `{doc['label']}:`{{: .{doc['css']} }} {doc['status']} "
            f"| {doc['date']} |"
        )
    title, body = render_credits()
    rendered.append("\n".join(body))
    page.append(
        f"| [{title}](#credits)<br><small>The published work the add-on is "
        "built on: shader code used directly, techniques and ideas adapted, "
        "papers and data, and the third-party licenses.</small> "
        "| `reference:`{: .label-improvements } Credits "
        "| — |"
    )
    page.append("")
    for body in rendered:
        page += ["", body, ""]
    OUT.write_text("\n".join(page).rstrip("\n") + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(page)} top-level chunks)")


if __name__ == "__main__":
    sys.exit(main())
