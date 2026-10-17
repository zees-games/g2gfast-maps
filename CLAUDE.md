# g2gfast-maps

The imported maps game-g2gfast plays, as their own repository. Read `../../CLAUDE.md` and `../game-g2gfast/CLAUDE.md` first.

**Each map is its own signed pack, `gamemann/<map id>`, never one pack for all of them.** A player joining a server downloads the map that is running; the game fetches the rest one at a time on a map change (`G2GConfig.map_content_owner`, `sv_map_content_owner` in the game's own `game.yml`). One pack for 1.5 GB of maps would put every map on every join.

**`maps/` is where the game loads them from.** `tools/g2gmaps link` makes `game-g2gfast/maps/imported` a relative link here, which is the path the `.import` markers were written against, so the game imports, tests and publishes these files without a copy. `link` refuses to replace a real directory that differs from `maps/`, because that directory would be the only copy of the difference.

**Releasing is a tag (since 2026-10-05): `git tag v1.x.y && git push --tags`.** `.github/workflows/release.yml` calls dot-ci's `release-maps.yml`, which checks game-g2gfast out beside this repository, links `maps/` in at its `maps/imported`, imports, and attaches one `<map>-<version>-pack.zip` per map (`scripts/package-subpacks.sh`); website-city's release sync publishes each as `gamemann/<map>@<version>` and signs it, once this repository is an asset with a release sync on the site and the site runs the multi-pack publisher (website-city 6b12dae2f). Every map in a release gets the release's version; the content-addressed store means an unchanged file is never re-downloaded, only its manifest is new. The CI runner has no `/extra`, so the private-reference check below does not run there; it stays the job of a local publish. game-g2gfast's `game.yml` lists the courses as `maps:` and the server's installer pins each to the newest version on the origin.

**The local path is still there** for a one-off: **Publishing goes through the game's `tools/publish_maps.sh`**, not a second publisher: the pack has to carry `.godot/imported/` and the rewritten markers, and only a Godot project that has imported the maps can produce those. **A pack's version is its files' hash** (`0.0.0-<12 hex>`, `G2GMapCatalogue.pack_version`, since 2026-10-04): a republish of changed files is a new `id@version` a client that holds the old one will fetch, and a republish of unchanged files is the same version. Everything before that was `@0.0.0`. `dist/` is the signed output (866 MB of packs, the textures imported beside the maps, the difference being the imported textures) and is gitignored.

**`fetch` mirrors packs verbatim; it does not rebuild `maps/`.** A published pack's markers point at its mount prefix, not at `res://maps/imported/`, so unpacking one into `maps/` would break the game's import. A mirror is a content origin (`<out>/gamemann/<id>/manifest.json` + `objects/`) a server can list in `content_urls`. Every object is hash-checked; `--pub` checks the manifest's signature over the DECODED payload bytes, which is what dot-cloud signs.

**Combat surf maps are not here.** Maps whose zones file says `"kind": "arena"` live in `../arena-surf-dm-maps`, and `tools/g2gmaps manifest` refuses to run while one is in `maps/`.

**Credits are mandatory.** `manifest` copies each map's author and source page from the game's `maps/zones/<id>.json` and refuses to finish if any map has none. The game shows the author on screen at a map change (`[credit-1]`).

Plain git, no LFS: the largest file is 66 MB (`surf_summit.bin`), under GitHub's 100 MB limit, and LFS bandwidth quotas would make every clone of a public repository a bill.
