#!/usr/bin/env python3
"""
Static site generator for Keshia's Journal.

Run this from the site folder any time you add/remove/rename albums or
photos, or edit site.config.json / an _album.json file:

    python3 build.py

It reads photos/albums/** and writes fresh index.html, about.html,
albums.html, and album/**/index.html pages. It never touches the photos
themselves or any _album.json / site.config.json file.

Uses only the Python standard library -- no installs needed.
"""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PHOTOS_DIR = ROOT / "photos" / "albums"
ALBUM_OUT_DIR = ROOT / "album"
SITE_CONFIG_PATH = ROOT / "site.config.json"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".svg"}
PALETTE = ["orange", "pink", "periwinkle", "green"]


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def strip_comments(text):
    """Allow // line comments in our .json files, which plain json.loads rejects."""
    return re.sub(r"(?m)^\s*//.*$", "", text)


def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(strip_comments(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as e:
        raise SystemExit(f"Could not parse {path.relative_to(ROOT)}: {e}")


def slug_to_title(slug):
    return slug.replace("-", " ").replace("_", " ")


def is_image(path):
    return path.is_file() and path.suffix.lower() in IMAGE_EXTS


def list_images(dir_path):
    return sorted((p.name for p in dir_path.iterdir() if is_image(p)), key=str.lower)


def list_subdirs(dir_path):
    return sorted(
        (p for p in dir_path.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))),
        key=lambda p: p.name.lower(),
    )


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ---------------------------------------------------------------------------
# reading photos/albums/** into a tree
# ---------------------------------------------------------------------------

def build_node(dir_path, path_ids, title_chain, color):
    meta = load_json(dir_path / "_album.json", {})
    subdirs = list_subdirs(dir_path)
    images = list_images(dir_path)
    title = meta.get("title") or slug_to_title(dir_path.name)
    node = {
        "id": dir_path.name,
        "path": path_ids,
        "rel_prefix": "/".join(path_ids[1:]),  # location of this node's folder, relative to the top album's root
        "title": title,
        "title_chain": title_chain + [title],
        "date": meta.get("date", ""),
        "excerpt": meta.get("excerpt", ""),
        "color": color,
        "meta": meta,
    }
    if subdirs:
        if images:
            print(f"  warning: {dir_path.relative_to(ROOT)} has both photos and sub-folders; "
                  f"the photos there will be ignored (a folder should be either a gallery or a group of folders)")
        node["children"] = [
            build_node(sd, path_ids + [sd.name], node["title_chain"], color) for sd in subdirs
        ]
        node["photos"] = []
    else:
        node["children"] = []
        node["photos"] = images
    node["is_branch"] = bool(node["children"])
    return node


def load_albums():
    if not PHOTOS_DIR.exists():
        raise SystemExit(f"Could not find {PHOTOS_DIR.relative_to(ROOT)} -- is this script in the right folder?")
    top_dirs = list_subdirs(PHOTOS_DIR)
    albums = {}
    order = []
    for i, d in enumerate(top_dirs):
        meta_peek = load_json(d / "_album.json", {})
        color = meta_peek.get("color") or PALETTE[i % len(PALETTE)]
        node = build_node(d, [d.name], [], color)
        node["nested"] = node["is_branch"]
        albums[node["id"]] = node
        order.append(node["id"])
    return albums, order


def find_node(top_node, path_ids):
    """path_ids includes the top id itself as the first element."""
    node = top_node
    for pid in path_ids[1:]:
        node = next((c for c in node["children"] if c["id"] == pid), None)
        if node is None:
            return None
    return node


def flatten_descendants(node, level=0):
    items = []
    for child in node["children"]:
        items.append((child, level))
        items.extend(flatten_descendants(child, level + 1))
    return items


def all_nodes(node):
    yield node
    for child in node["children"]:
        yield from all_nodes(child)


# ---------------------------------------------------------------------------
# picking cover / preview photos (manual first, automatic fallback)
# ---------------------------------------------------------------------------

def collect_default_photos(node, limit, prefix=""):
    results = []
    for fn in node["photos"]:
        rel = fn if not prefix else f"{prefix}/{fn}"
        results.append(rel)
        if len(results) >= limit:
            return results
    for child in node["children"]:
        if len(results) >= limit:
            break
        child_prefix = child["id"] if not prefix else f"{prefix}/{child['id']}"
        results.extend(collect_default_photos(child, limit - len(results), child_prefix))
    return results[:limit]


def node_cover_rel(node, top_dir):
    prefix = node["rel_prefix"]
    explicit = node["meta"].get("cover_photo")
    if explicit:
        candidate = explicit if not prefix else f"{prefix}/{explicit}"
        if (top_dir / candidate).exists():
            return candidate
        print(f"  warning: cover_photo '{explicit}' in {node['id']}/_album.json not found, using automatic pick instead")
    defaults = collect_default_photos(node, 1, prefix)
    return defaults[0] if defaults else None


def node_preview_rels(node, top_dir, count=3):
    result = []
    for rel in node["meta"].get("preview_photos") or []:
        if (top_dir / rel).exists():
            result.append(rel)
        else:
            print(f"  warning: preview_photos entry '{rel}' in {node['id']}/_album.json not found, skipping")
    if len(result) < count:
        for rel in collect_default_photos(node, count + len(result)):
            if rel not in result:
                result.append(rel)
            if len(result) >= count:
                break
    return result[:count]


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

def prefix_for_depth(depth):
    return "../" * depth


def photo_src(prefix, top_id, rel):
    return f"{prefix}photos/albums/{top_id}/{rel}"


def album_href(prefix, path_ids):
    return f"{prefix}album/{'/'.join(path_ids)}/index.html"


def render_nav(prefix, active, site_name):
    def link(href, label, key):
        cls = "nav-link is-active" if key == active else "nav-link"
        return f'<a class="{cls}" href="{href}">{label}</a>'

    return f"""<div class="nav">
  <div class="nav-inner">
    <a class="nav-brand" href="{prefix}index.html">{esc(site_name)}</a>
    <div class="nav-links">
      {link(prefix + "index.html", "Home", "home")}
      {link(prefix + "albums.html", "Albums", "albums")}
      {link(prefix + "about.html", "About", "about")}
    </div>
  </div>
</div>"""


def render_page(title, active, depth, body, site_name, include_lightbox=False):
    prefix = prefix_for_depth(depth)
    lightbox_html = LIGHTBOX_HTML if include_lightbox else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — {esc(site_name)}</title>
<link rel="stylesheet" href="{prefix}assets/css/style.css">
</head>
<body>
{render_nav(prefix, active, site_name)}
{body}
{lightbox_html}
<script src="{prefix}assets/js/site.js"></script>
</body>
</html>
"""


LIGHTBOX_HTML = """<div class="lightbox">
  <div class="lightbox-body">
    <div class="lightbox-photo"><img src="" alt=""></div>
    <p class="lightbox-caption"></p>
    <span class="lightbox-counter"></span>
  </div>
  <button class="lightbox-btn lightbox-close" aria-label="Close">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="4" x2="20" y2="20"></line><line x1="20" y1="4" x2="4" y2="20"></line></svg>
  </button>
  <button class="lightbox-btn lightbox-prev" aria-label="Previous photo">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 6 9 12 15 18"></polyline></svg>
  </button>
  <button class="lightbox-btn lightbox-next" aria-label="Next photo">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 6 15 12 9 18"></polyline></svg>
  </button>
</div>"""


SOCIAL_ICONS = {
    "Instagram": '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="18" height="18" rx="5"></rect><circle cx="12" cy="12" r="4.2"></circle><circle cx="17.3" cy="6.7" r="1"></circle></svg>',
    "TikTok": '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M14 4v10.5a3.5 3.5 0 1 1-3.5-3.5"></path><path d="M14 4c.4 2.2 2.1 3.8 4.3 4"></path></svg>',
    "LinkedIn": '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="18" height="18" rx="4"></rect><line x1="7.5" y1="10" x2="7.5" y2="17"></line><circle cx="7.5" cy="6.7" r="0.6" fill="currentColor"></circle><path d="M11.5 17v-4.2c0-1.5 1-2.3 2.2-2.3s2 .8 2 2.3V17"></path></svg>',
    "Goodreads": '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 6.5c-1.4-1.1-3.5-1.7-6-1.5-.5 0-.9.4-.9.9v11c0 .5.4.9.9.8 2.2-.2 4.3.3 6 1.5V6.5z"></path><path d="M12 6.5c1.4-1.1 3.5-1.7 6-1.5.5 0 .9.4.9.9v11c0 .5-.4.9-.9.8-2.2-.2-4.3.3-6 1.5V6.5z"></path></svg>',
    "Letterboxd": '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="6.5" cy="12" r="3.5"></circle><circle cx="17.5" cy="12" r="3.5"></circle></svg>',
    "Spotify": '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"></circle><path d="M7 10.3c3-1 7-.6 9.5.9M7.5 13.3c2.4-.7 5.6-.4 7.7.8M8 16.2c1.9-.5 4.3-.3 5.8.6"></path></svg>',
    "Google Scholar": '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 9.5 12 5l9 4.5-9 4.5-9-4.5z"></path><path d="M7 11.5V16c0 1.4 2.2 2.5 5 2.5s5-1.1 5-2.5v-4.5"></path></svg>',
}
GENERIC_ICON = '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"></circle></svg>'


def render_masonry(prefix, top_id, photos_rel, captions, two_col):
    cls = "masonry masonry-2col" if two_col else "masonry"
    items = []
    for rel in photos_rel:
        filename = rel.split("/")[-1]
        caption = captions.get(filename, "")
        src = photo_src(prefix, top_id, rel)
        cap_html = f'<p class="masonry-caption">{esc(caption)}</p>' if caption else ""
        items.append(f"""    <div class="masonry-item js-lightbox-item" data-caption="{esc(caption)}" data-full="{src}">
      <div class="masonry-photo"><img src="{src}" alt="{esc(caption)}" loading="lazy"></div>
      {cap_html}
    </div>""")
    return f'<div class="{cls}">\n' + "\n".join(items) + "\n  </div>"


# ---------------------------------------------------------------------------
# page builders
# ---------------------------------------------------------------------------

def build_home(config, albums, order):
    prefix = prefix_for_depth(0)

    hero_entries = config.get("homepage_hero_photos") or []
    slides = []
    for i, entry in enumerate(hero_entries):
        top_id = entry.get("album")
        rel = entry.get("photo")
        top_dir = PHOTOS_DIR / (top_id or "")
        if not top_id or not rel or not (top_dir / rel).exists():
            print(f"  warning: homepage_hero_photos entry #{i + 1} points to a missing photo, skipping")
            continue
        src = photo_src(prefix, top_id, rel)
        label = entry.get("label", "")
        label_html = f'<div class="hero-slide-label">{esc(label)}</div>' if label else ""
        active = " is-active" if not slides else ""
        slides.append(f"""    <div class="hero-slide{active}">
      <img src="{src}" alt="{esc(label)}">
      {label_html}
    </div>""")

    if slides:
        dots = "\n".join(
            f'    <button class="hero-dot{" is-active" if i == 0 else ""}" aria-label="Go to slide {i + 1}"></button>'
            for i in range(len(slides))
        )
        hero_html = f"""<div class="hero" data-hero>
{chr(10).join(slides)}
  <div class="hero-dots">
{dots}
  </div>
</div>"""
    else:
        hero_html = ('<div class="hero" style="display:flex;align-items:center;justify-content:center;'
                     'color:var(--color-muted);font-family:var(--font-body);font-size:14px">'
                     'Add photos to "homepage_hero_photos" in site.config.json</div>')

    featured_ids = config.get("homepage_albums") or order
    cards = []
    for top_id in featured_ids:
        node = albums.get(top_id)
        if not node:
            print(f"  warning: homepage_albums lists unknown album '{top_id}', skipping")
            continue
        top_dir = PHOTOS_DIR / top_id
        cover = node_cover_rel(node, top_dir)
        img_html = f'<img src="{photo_src(prefix, top_id, cover)}" alt="">' if cover else ""
        cards.append(f"""      <a class="album-card" href="{album_href(prefix, [top_id])}">
        <div class="album-card-photo">{img_html}</div>
        <div class="album-card-title-row">
          <span class="album-card-title" style="color:var(--{node['color']})">{esc(node['title'])}</span>
          <span class="album-card-date">{esc(node['date'])}</span>
        </div>
        <p class="album-card-excerpt">{esc(node['excerpt'])}</p>
      </a>""")

    body = f"""<div>
  {hero_html}
  <div class="wrap">
    <div class="section-label">latest albums</div>
    <div class="card-grid">
{chr(10).join(cards)}
    </div>
  </div>
</div>"""

    (ROOT / "index.html").write_text(
        render_page("Home", "home", 0, body, config.get("site_name", "")),
        encoding="utf-8",
    )


def build_about(config):
    prefix = prefix_for_depth(0)
    about = config.get("about", {})
    portrait = about.get("portrait_photo")
    if portrait:
        portrait_html = f'<img src="{prefix}photos/{portrait}" alt="">'
    else:
        portrait_html = '<span class="about-portrait-label">portrait photo</span>'

    icons = []
    for link in config.get("social_links", []):
        name = link.get("name", "")
        url = link.get("url", "#")
        svg = SOCIAL_ICONS.get(name, GENERIC_ICON)
        icons.append(
            f'    <a class="social-icon" href="{esc(url)}" aria-label="{esc(name)}" title="{esc(name)}">{svg}</a>'
        )

    body = f"""<div class="wrap">
  <div class="about-grid">
    <div>
      <h1 class="about-heading">{esc(about.get("heading", ""))}</h1>
      <p class="about-p1">{esc(about.get("paragraph_1", ""))}</p>
      <p class="about-p2">{esc(about.get("paragraph_2", ""))}</p>
    </div>
    <div class="about-portrait">{portrait_html}</div>
  </div>
  <div class="social-row">
{chr(10).join(icons)}
  </div>
</div>"""

    (ROOT / "about.html").write_text(
        render_page("About", "about", 0, body, config.get("site_name", "")),
        encoding="utf-8",
    )


def build_albums_archive(config, albums, order):
    prefix = prefix_for_depth(0)
    cards = []
    for top_id in order:
        node = albums[top_id]
        top_dir = PHOTOS_DIR / top_id
        previews = node_preview_rels(node, top_dir, 3)
        preview_html = "\n".join(
            f'        <div class="archive-preview-photo"><img src="{photo_src(prefix, top_id, rel)}" alt=""></div>'
            for rel in previews
        )
        cards.append(f"""    <a class="album-card archive-card" href="{album_href(prefix, [top_id])}">
      <div class="archive-preview-grid">
{preview_html}
      </div>
      <div class="album-card-title-row">
        <span class="album-card-title" style="color:var(--{node['color']})">{esc(node['title'])}</span>
        <span class="album-card-date">{esc(node['date'])}</span>
      </div>
      <p class="album-card-excerpt">{esc(node['excerpt'])}</p>
    </a>""")

    body = f"""<div class="wrap">
  <h1 class="archive-title">albums</h1>
  <div class="archive-grid">
{chr(10).join(cards)}
  </div>
</div>"""

    (ROOT / "albums.html").write_text(
        render_page("Albums", "albums", 0, body, config.get("site_name", "")),
        encoding="utf-8",
    )


def album_header_html(top_node, prefix):
    return f"""  <a class="back-link" href="{prefix}albums.html">← all albums</a>
  <div class="album-header">
    <h1 class="album-title" style="color:var(--{top_node['color']})">{esc(top_node['title'])}</h1>
    <span class="album-date-badge">{esc(top_node['date'])}</span>
  </div>
  <p class="album-excerpt">{esc(top_node['excerpt'])}</p>"""


def build_flat_album(top_node):
    depth = len(top_node["path"]) + 1  # +1 for the "album/" folder itself
    prefix = prefix_for_depth(depth)
    captions = top_node["meta"].get("captions", {})
    photos_rel = top_node["photos"]

    header = album_header_html(top_node, prefix)
    gallery = render_masonry(prefix, top_node["id"], photos_rel, captions, two_col=False)
    body = f'<div class="wrap">\n{header}\n{gallery}\n</div>'

    out_dir = ALBUM_OUT_DIR / top_node["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(
        render_page(top_node["title"], "albums", depth, body, SITE_NAME, include_lightbox=bool(photos_rel)),
        encoding="utf-8",
    )


def render_sidebar(top_node, current_path, prefix):
    items = [f'  <a class="sidebar-overview" href="{album_href(prefix, top_node["path"])}">overview</a>']
    for node, level in flatten_descendants(top_node):
        active = " is-active" if node["path"] == current_path else ""
        style = f'padding-left:{level * 16}px;border-left-color:var(--{top_node["color"]})' if active else f'padding-left:{level * 16}px'
        items.append(
            f'  <a class="sidebar-item{active}" style="{style}" href="{album_href(prefix, node["path"])}">{esc(node["title"])}</a>'
        )
    return '<div class="sidebar">\n' + "\n".join(items) + "\n</div>"


def build_nested_node_page(top_node, node):
    depth = len(node["path"]) + 1  # +1 for the "album/" folder itself
    prefix = prefix_for_depth(depth)
    top_dir = PHOTOS_DIR / top_node["id"]

    header = album_header_html(top_node, prefix)

    breadcrumb_html = ""
    if node["path"] != top_node["path"]:
        breadcrumb_html = f'<div class="breadcrumb">{esc(" / ".join(node["title_chain"]))}</div>'

    if node["is_branch"]:
        cards = []
        for child in node["children"]:
            cover = node_cover_rel(child, top_dir)
            img_html = f'<img src="{photo_src(prefix, top_node["id"], cover)}" alt="">' if cover else ""
            cards.append(f"""      <a class="overview-card" href="{album_href(prefix, child["path"])}">
        <div class="overview-card-photo">{img_html}</div>
        <div class="overview-card-title" style="color:var(--{top_node['color']})">{esc(child['title'])}</div>
      </a>""")
        content = f'    <div class="overview-grid">\n{chr(10).join(cards)}\n    </div>'
        has_photos = False
    else:
        captions = node["meta"].get("captions", {})
        photos_rel = [
            (node["rel_prefix"] + "/" + fn) if node["rel_prefix"] else fn
            for fn in node["photos"]
        ]
        content = "    " + render_masonry(prefix, top_node["id"], photos_rel, captions, two_col=True)
        has_photos = bool(photos_rel)

    body = f"""<div class="wrap">
{header}
  <div class="nested-layout">
{render_sidebar(top_node, node["path"], prefix)}
    <div>
      {breadcrumb_html}
{content}
    </div>
  </div>
</div>"""

    out_dir = ALBUM_OUT_DIR
    for pid in node["path"]:
        out_dir = out_dir / pid
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(
        render_page(node["title"], "albums", depth, body, SITE_NAME, include_lightbox=has_photos),
        encoding="utf-8",
    )


def build_nested_album(top_node):
    for node in all_nodes(top_node):
        build_nested_node_page(top_node, node)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    global SITE_NAME
    config = load_json(SITE_CONFIG_PATH, {})
    SITE_NAME = config.get("site_name", "Photography")

    print("Reading photos/albums ...")
    albums, order = load_albums()
    if not order:
        raise SystemExit(f"No album folders found in {PHOTOS_DIR.relative_to(ROOT)}. Create one and try again.")
    for top_id in order:
        node = albums[top_id]
        kind = "nested" if node["nested"] else "flat"
        print(f"  - {top_id} ({kind}, color: {node['color']})")

    if ALBUM_OUT_DIR.exists():
        shutil.rmtree(ALBUM_OUT_DIR)
    ALBUM_OUT_DIR.mkdir(parents=True)

    print("Writing pages ...")
    build_home(config, albums, order)
    build_about(config)
    build_albums_archive(config, albums, order)
    for top_id in order:
        node = albums[top_id]
        if node["nested"]:
            build_nested_album(node)
        else:
            build_flat_album(node)

    print("Done. Open index.html in a browser, or commit + push to publish via GitHub Pages.")


if __name__ == "__main__":
    main()
