The bunny-hop and surf maps [game-g2gfast](https://github.com/zees-games/game-g2gfast) plays, as a repository of their own: the imported maps in `maps/`, the list of them with their authors in `maps.json`, and `tools/g2gmaps` to publish them to the content origin and to mirror them back down.

Every map here is somebody else's work, made for the genre years ago and imported so it can be played again. Each one is credited below and on screen whenever a server changes to it. If you made one of these maps and want it credited differently or taken down, open an issue and it will be done.

## Why the maps are not in the game's repository

A player joining a server downloads the map that is running, not every map there is. So each map is published as its own signed pack, `gamemann/<map id>`, and game-g2gfast fetches the one it needs when the map changes. Keeping them here means a map can be added, fixed or withdrawn without a release of the game, and 1.5 GB of maps does not ride along with every clone of the game's code.

Combat surf maps (a deathmatch to fight on, not a course to time) are not kept here: they live in `arena-surf-dm-maps`.

## Layout

```
maps/<id>/<id>.json      what the importer produced: the map's manifest,
maps/<id>/<id>.bin       its geometry,
maps/<id>/textures/      its textures, and the .import markers beside them
maps.json                every map, its author and its source page
tools/g2gmaps            the CLI
```

The game's zone data (starts, finishes, stages) stays in game-g2gfast under `maps/zones/`, because it is gameplay the game defines, not part of the map.

## Using it

```bash
# Work on the game against these maps: game-g2gfast/maps/imported becomes a link here.
tools/g2gmaps link

# Rewrite maps.json after adding or removing a map (credits come from the game's zones files).
tools/g2gmaps manifest

# Sign every map as gamemann/<id> into dist/, and upload dist/ to the content origin.
GAMES_S3_BUCKET=... GAMES_S3_REGION=... GAMES_S3_ACCESS_KEY=... GAMES_S3_ACCESS_SECRET=... \
    tools/g2gmaps publish --key path/to/content.key --upload

# Mirror every published map from the CDN into mirror/, each file checked against its hash
# (and the signature against a public key with --pub). Point a server's content_urls at the
# mirror to serve the maps from your own box.
tools/g2gmaps fetch --pub path/to/content.pub
```

`publish` runs through game-g2gfast's own `tools/publish_maps.sh`, so it needs Godot and the game checked out beside this repository with `link` done. `fetch` needs only Python 3.

## Credits

| Map | Author | Source |
| --- | --- | --- |
| `bhop_amor` | roma; licence stated on the page: Creative Commons Attribution-NonCommercial-NoDerivs 4.0; removal on request | https://gamebanana.com/mods/124424 |
| `bhop_angst` | Proxychains; licence stated on the page: Creative Commons Attribution-NonCommercial-NoDerivs 4.0; removal on request | https://gamebanana.com/mods/303411 |
| `bhop_arcane_v2` | Panzerhandschuh (Panzer); v2 edit uploaded by 'roger haha lol' | https://gamebanana.com/mods/124462 |
| `bhop_aztec` | Teho-Killeri (mapper), with Touch (design) and Veikko (textures) | https://gamebanana.com/mods/124514 |
| `bhop_badges` | badges (Badgeslol) | https://gamebanana.com/mods/124524 |
| `bhop_badges_mini` | GumPum | https://gamebanana.com/mods/124526 |
| `bhop_depot` | ballz of steel; licence stated on the page: Creative Commons Attribution-NonCommercial-NoDerivs 4.0; removal on request | https://gamebanana.com/mods/124816 |
| `bhop_eazy` | 31K4L | https://gamebanana.com/mods/124913 |
| `bhop_epiphany` | wet (the map's own text reads "By Nate"); licence stated on the page: Creative Commons Attribution-NonCommercial-NoDerivs 4.0 | https://gamebanana.com/mods/124957 |
| `bhop_evolve` | Zyper | https://gamebanana.com/mods/124971 |
| `bhop_fur` | Fur (TheFur) | https://gamebanana.com/mods/125103 |
| `bhop_fury` | Dotty; licence stated on the page: Creative Commons Attribution-NonCommercial-NoDerivs 4.0; removal on request | https://gamebanana.com/mods/125105 |
| `bhop_grove` | Tony Montana | https://gamebanana.com/mods/125167 |
| `bhop_hellish_dream_css` | Sonia_ (map and textures); skybox Mr.Who; textures komaokc, TopHATTwaffle, Wolves Hero; licence stated on the page: Creative Commons Attribution-NonCommercial-NoDerivs 4.0; removal on request | https://gamebanana.com/mods/125200 |
| `bhop_interloper` | Tony Montana | https://gamebanana.com/mods/125285 |
| `bhop_lego2` | Tony Montana (tmontana) | https://gamebanana.com/mods/125408 |
| `bhop_monster_jam` | monster jam and Aoki | https://gamebanana.com/mods/125558 |
| `bhop_pandora2_fix` | Sonia_ (map); skybox Mr.Who; textures Wolves Hero and Sonia_; original bhop_pandora video/advice tmontana | https://gamebanana.com/mods/125705 |
| `bhop_pit` | Roady | https://gamebanana.com/mods/453100 |
| `bhop_platformer_fxd` | DroN (SWM/DroN); published on GameBanana under its original title `bhop_mario_fxd`, renamed here to a neutral id | https://gamebanana.com/mods/125494 |
| `bhop_supernova` | Sonia_ (map design) and Benchmarked (gameplay); skybox Mr.Who; textures TopHATTwaffle and Sonia_; testers Juked, tricksterr, plar, samurai; Subnautica models by Unknown Worlds Entertainment | https://gamebanana.com/mods/313046 |
| `bhop_tesquo_v2` | george (GeorgeRulesLOL); 'Made a stage': Jagg | https://gamebanana.com/mods/126185 |
| `bhop_toroux` | toroux; the page says 'feel free to Port this map'; licence stated on the page: Creative Commons Attribution-NonCommercial-NoDerivs 4.0; removal on request | https://gamebanana.com/mods/126232 |
| `bhop_training_fun` | Soapy Soap; licence stated on the page: Creative Commons Attribution-NonCommercial-NoDerivs 4.0; removal on request | https://gamebanana.com/mods/126237 |
| `bhop_tranquility` | Nallieheai (Bhop World Cup 2020); textures TopHATTwaffle, silkroad, biql, Emque; models Aui__, Fibbs; licence stated on the page: Creative Commons Attribution-NonCommercial-NoDerivs 4.0; removal on request | https://gamebanana.com/mods/126240 |
| `buses_from_hell_fixed` | siXMan | https://gamebanana.com/mods/127607 |
| `surf_aquaflow` | NvC_DmN_CH | https://gamebanana.com/mods/137715 |
| `surf_arcade` | maz64 (maz) | https://gamebanana.com/mods/137716 |
| `surf_beginner2` | Kiiru | https://gamebanana.com/mods/137722 |
| `surf_ember` | Skar; licence stated on the page: Creative Commons Attribution-NonCommercial-NoDerivs 4.0; removal on request | https://gamebanana.com/mods/122002 |
| `surf_greensway` | NvC_DmN_CH | https://gamebanana.com/mods/137798 |
| `surf_hologram` | Chent (a Source 2 map, converted with ValveResourceFormat) | https://gamebanana.com/mods/525468 |
| `surf_interference` | NvC_DmN_CH | https://gamebanana.com/mods/137815 |
| `surf_intro` | Chent (a Source 2 map, converted with ValveResourceFormat; removal on request) | https://gamebanana.com/mods/524245 |
| `surf_kitsune` | Arblarg | https://gamebanana.com/mods/122382 |
| `surf_lithium2` | copy-mark (map); textures nikki, skybox karatekaefer; licence stated on the page: Creative Commons Attribution-NonCommercial-NoDerivs 4.0; removal on request | https://gamebanana.com/mods/122445 |
| `surf_mesa` | Arblarg | https://gamebanana.com/mods/122542 |
| `surf_summit` | Juxtapo and Phurix | https://gamebanana.com/mods/137705 |
| `surf_year3000` | ArchAngel | https://gamebanana.com/mods/123298 |
