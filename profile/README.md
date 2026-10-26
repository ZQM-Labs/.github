# ZQM Labs — Z’s Quests & Mischief

**Community-centered games built for curiosity, exploration, and a little mischief.**

[Visit zqmlabs.com](https://zqmlabs.com)

ZQM Labs creates self-guided quest games and the tools that help communities turn places, stories, and shared challenges into playable experiences. Our games are designed for people to play together—in local neighborhoods, at community events, and wherever a quest can bring people together.

## Start here

- **[Play the Wisp’s Lost Lanterns demo](https://zqmlabs.com/games/hunt-for-wisps/play/?demo=1)** — try the browser-based scavenger-hunt experience.
- **[Explore Wisp’s Lost Lanterns](https://zqmlabs.com/games/hunt-for-wisps/)** — learn about the game, its checkpoints, and its play experience.
- **[Visit ZQM Labs](https://zqmlabs.com)** — see the broader studio and its projects.

Wisp’s Lost Lanterns is our Halloween quest: players follow clues and discover six lantern checkpoints. The demo is available to explore; event dates, availability, and location-specific arrangements are published separately from the demo.

## What we build

| Area | Project | Purpose |
| --- | --- | --- |
| Player experience | [quest-player](https://github.com/ZQM-Labs/quest-player) | Browser-based, offline-conscious quest-player experience |
| Quest content | [quest-packs](https://github.com/ZQM-Labs/quest-packs) | Structured quest-pack content and sample material |
| Authoring | [quest-authoring](https://github.com/ZQM-Labs/quest-authoring) | Quest-pack format, authoring guidance, and validation |
| Organizer operations | [organizer-toolkit](https://github.com/ZQM-Labs/organizer-toolkit) | Setup, print, event-day, and troubleshooting guidance |
| Playtesting | [playtests](https://github.com/ZQM-Labs/playtests) | Playtest protocols and recorded findings |
| Website | [zqmlabs-site](https://github.com/ZQM-Labs/zqmlabs-site) | Source for the public website |

Our approach favors approachable play, clear instructions, accessible alternatives where practical, and honest documentation of what has—and has not—been tested. GPS and QR checkpoints are game mechanics, not proof of identity or secure authorization.

## Cookbooks and practical examples

The ZQM Labs cookbooks collect focused, reproducible patterns for building, testing, authoring, and operating game experiences. They are practical starting points—not a claim that every example has been validated in every target application or production environment. See the [Cookbook Catalog](COOKBOOKS.md) for the implemented foundations, automated evidence, assurance levels, and outstanding target-runtime validation for each cookbook.

### Game engines and level design

- [Godot Cookbook](https://github.com/ZQM-Labs/godot-cookbook) — responsive game UI, input, and scene patterns.
- [Phaser Cookbook](https://github.com/ZQM-Labs/phaser-cookbook) — browser-game scenes, interaction, and accessibility-oriented patterns.
- [Tiled Cookbook](https://github.com/ZQM-Labs/tiled-cookbook) — tile-map structure and checkpoint markers.
- [LDtk Cookbook](https://github.com/ZQM-Labs/ldtk-cookbook) — level contracts, checkpoint identity, and structural validation.
- [Location Games Cookbook](https://github.com/ZQM-Labs/location-games-cookbook) — location-aware quest mechanics and checkpoint freshness.

### Art, assets, and audio

- [Blender Cookbook](https://github.com/ZQM-Labs/blender-cookbook) — procedural 3D assets and export workflows.
- [Krita Cookbook](https://github.com/ZQM-Labs/krita-cookbook) — 2D art assets, palettes, and export-ready starters.
- [Audacity Cookbook](https://github.com/ZQM-Labs/audacity-cookbook) — deterministic sound-effect generation and audio workflow examples.

### Testing, backend, and payments

- [Playwright Cookbook](https://github.com/ZQM-Labs/playwright-cookbook) — browser-level tests for player experiences and client-side state.
- [PocketBase Cookbook](https://github.com/ZQM-Labs/pocketbase-cookbook) — authentication, record ownership, and backend authorization examples.
- [Stripe Cookbook](https://github.com/ZQM-Labs/stripe-cookbook) — checkout, webhook reliability, and purchase-fulfillment testing patterns.

Examples and automated checks have different levels of assurance: a passing structural or unit test does not by itself prove real-editor compatibility, browser compatibility, perceptual quality, secure physical presence, or production readiness. Consult each cookbook's README for its current scope, prerequisites, and validation status.

## Two complementary efforts

| Organization | Focus |
| --- | --- |
| [ZQM Labs](https://github.com/ZQM-Labs) | Games, quest experiences, content, and community play |
| [ZQM Computing](https://github.com/ZQM-Computing) | Geospatial engineering, open-source spatial patterns, data infrastructure, and supporting technology |

The organizations are related, but have distinct purposes. ZQM Computing contributes geospatial engineering where it supports game experiences; ZQM Labs remains focused on the games and the people who play them.

## Get involved

- Browse the [ZQM Labs repositories](https://github.com/orgs/ZQM-Labs/repositories).
- Read the [contribution guidelines](https://github.com/ZQM-Labs/.github/blob/main/CONTRIBUTING.md) before opening a pull request.
- Review the [security policy](https://github.com/ZQM-Labs/.github/blob/main/SECURITY.md) to report vulnerabilities responsibly.
- Follow the [Code of Conduct](https://github.com/ZQM-Labs/.github/blob/main/CODE_OF_CONDUCT.md) when participating.

We welcome useful bug reports, reproducible examples, documentation improvements, accessibility feedback, and thoughtful contributions. Please distinguish verified behavior from assumptions, and include reproduction steps when reporting a defect.

---

*Games, gear & a little mischief. Play more. Plan less.*
