# Keshia's Journal — site source

A personal photography portfolio: a homepage with a hero slideshow and
latest albums, an About page, and an Albums archive with flat and nested
albums (nested albums get a sidebar tree, like a trip with several
countries/cities in it).

The site is plain HTML/CSS/JS — no framework, no npm install. A small
Python script (`build.py`) reads your photo folders and writes the actual
`.html` pages. You run it from Terminal whenever you've changed something.

## Publishing it on GitHub Pages

1. Create a new GitHub repository and upload everything in this folder to it
   (drag-and-drop on github.com works, or `git init` + `git add .` + `git commit` + push).
2. In the repo, go to **Settings → Pages**.
3. Under "Build and deployment", set **Source: Deploy from a branch**, branch
   **main**, folder **/ (root)**. Save.
4. GitHub gives you a URL (something like `https://yourname.github.io/reponame/`)
   — it takes a minute or two to go live after the first push.

Everything in this folder is already a finished, ready-to-view website —
you don't need a build step on GitHub's side. Just keep committing the
regenerated HTML files (see below) whenever you update the site.

## Adding a new album

1. Make a new folder inside `photos/albums/`, named whatever you want the
   album's web address to look like (e.g. `photos/albums/iceland/`).
   Use lowercase and hyphens instead of spaces — that folder name becomes
   part of the URL.
2. Drag your photos into that folder. That's it — every image file in the
   folder becomes part of the gallery automatically, sorted by filename
   (so `01-sunrise.jpg`, `02-glacier.jpg`, ... if you want to control order).
3. Optional: add an `_album.json` file in the same folder for the title,
   date, description, colour, and manually-chosen cover/preview photos.
   Copy `photos/albums/sample-album/_album.json` as a starting point — it
   has comments explaining every field.
4. Run the build script (see below) and commit + push.

Supported photo formats: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.avif`, `.svg`.

### Nested albums (a trip with multiple countries/cities)

Instead of dropping photos straight into the album folder, make
sub-folders instead — one per chapter. A folder full of photos is a
gallery ("leaf"); a folder full of other folders is a section with its
own overview page ("branch"), and you can nest as deep as you like
(see `photos/albums/sample-nested-album/` — `chapter-two` contains
`part-a` and `part-b`, just like "Europe 2025 → Italy → Milan/Venice").

The site builds the sidebar tree automatically from your folder
structure — you never have to list the sub-albums anywhere yourself.
Each folder can have its own `_album.json` for a title and captions.

**Don't mix photos and sub-folders in the same folder** — pick one or
the other for each folder, or the loose photos will be ignored (the
build script will print a warning if this happens).

## Choosing hero photos and preview photos

These are never picked automatically — you choose them by editing a
text file:

- **Homepage hero slideshow**: edit `homepage_hero_photos` in
  `site.config.json` (repo root). Each entry points at one photo inside
  one album folder.
- **Homepage "latest albums"**: edit `homepage_albums` in
  `site.config.json` to choose which albums appear, and in what order.
- **An album's cover photo** (used on the homepage card) and **preview
  photos** (the 3 small photos on the Albums archive page): set
  `cover_photo` and `preview_photos` in that album's own `_album.json`.
  If you leave these out, the site just uses the first photo(s) it finds
  in the folder, alphabetically.
- **Captions under specific photos**: the `captions` object in an
  `_album.json`, keyed by filename.

All of these `.json` files support `//` comments on their own line, so
you can leave yourself notes.

## Running the build script

From Terminal, `cd` into this folder, then:

```
python3 build.py
```

(macOS has `python3` built in — if Terminal says it's not found, install
it from python.org or via `xcode-select --install`, then try again.)

This regenerates `index.html`, `about.html`, `albums.html`, and
everything under `album/`. It never touches your photos or your `.json`
files. Run it every time you add, remove, or rename an album or a photo,
or edit `site.config.json` / an `_album.json`. Then commit and push the
changes (including the regenerated HTML) to publish them.

To preview locally before pushing, run `python3 -m http.server` in this
folder and open `http://localhost:8000` in a browser.

## Editing text content

- **About page bio, portrait, social links**: `site.config.json` →
  `about` and `social_links`. Social links are all set to `#` for now —
  drop in the real URLs whenever you're ready.
- **Site name** (shown top-left of the nav): `site_name` in
  `site.config.json`.
- **An album's title/date/description**: that album's `_album.json`.

## Folder structure

```
index.html, about.html, albums.html   generated — don't hand-edit
album/                                 generated — don't hand-edit
assets/css/style.css                   colours, fonts, layout
assets/js/site.js                      hero slideshow + lightbox behaviour
photos/albums/                         your photos, organised into album folders
site.config.json                       site-wide settings (hero photos, about, socials)
build.py                               regenerates the HTML — run after any change
```

## What's already set up as a starting point

Two placeholder albums are included so you can see the two kinds in
action before you have real photos in place:

- `photos/albums/sample-album/` — a flat album (just photos).
- `photos/albums/sample-nested-album/` — a nested album, two levels deep
  (`chapter-two` contains `part-a` and `part-b`).

Delete these two folders (and their entries in `homepage_hero_photos` /
`homepage_albums` in `site.config.json`) once you've replaced them with
your own albums, then run `python3 build.py` again.
