# ZQM Labs — Z’s Quests & Mischief

**Community-centered games built for curiosity, exploration, and a little mischief.**

[Visit zqmlabs.com](https://zqmlabs.com) · [Browse repositories](https://github.com/orgs/ZQM-Labs/repositories)

ZQM Labs builds self-guided quest games and the tools that help communities turn places, stories, and shared challenges into playable experiences. The goal is global and community-centered: local neighborhoods and events are examples of where people can play, not the limit of the studio’s audience.

## Start here

- **[Play the Wisp’s Lost Lanterns demo](https://zqmlabs.com/games/hunt-for-wisps/play/?demo=1)** — try the browser-based scavenger-hunt experience.
- **[Explore Wisp’s Lost Lanterns](https://zqmlabs.com/games/hunt-for-wisps/)** — read about the game and its checkpoint experience.
- **[Explore the game-development repositories](https://github.com/orgs/ZQM-Labs/repositories)** — find player, content, authoring, organizer, testing, and website projects.

The Wisp’s Lost Lanterns demo is an exploratory experience. A demo link does not itself confirm event dates, local availability, paid booking, or production readiness.

## How the projects fit together

| Stage | Repository | Role |
| --- | --- | --- |
| Player experience | [quest-player](https://github.com/ZQM-Labs/quest-player) | Browser-based quest-player experience and client behavior |
| Quest content | [quest-packs](https://github.com/ZQM-Labs/quest-packs) | Structured quest-pack content and examples |
| Authoring and validation | [quest-authoring](https://github.com/ZQM-Labs/quest-authoring) | Content format, authoring guidance, and validation |
| Organizer operations | [organizer-toolkit](https://github.com/ZQM-Labs/organizer-toolkit) | Setup, print, event-day, and troubleshooting workflows |
| Playtesting | [playtests](https://github.com/ZQM-Labs/playtests) | Playtest protocols, findings, and evidence |
| Public website | [zqmlabs-site](https://github.com/ZQM-Labs/zqmlabs-site) | Source for the public studio website |

Conceptual flow: **author content → validate packs → deliver the player experience → operate the event → playtest and improve**. This is a workflow map, not a claim that every step is currently automated or integrated end to end.

## Cookbooks and practical examples

The cookbooks document focused patterns for game engines, level design, assets, audio, browser testing, backend services, payments, and location-based play. Each has an individual rationale below. The rationale explains why the topic belongs in the collection; it is not evidence that every recipe is complete, tested against every target application, or production-ready.

See the [ZQM Labs Cookbook Catalog](COOKBOOKS.md) for the inventory, scope, evidence expectations, and known validation gaps.

### Game engines and level design

- [Godot Cookbook](https://github.com/ZQM-Labs/godot-cookbook) — scene organization, UI, input, and reusable native-game interaction patterns.
- [Phaser Cookbook](https://github.com/ZQM-Labs/phaser-cookbook) — browser-first scenes and interactions suited to low-friction web delivery.
- [Tiled Cookbook](https://github.com/ZQM-Labs/tiled-cookbook) — portable tile-map authoring and map metadata conventions that help keep geometry and gameplay coordinated.
- [LDtk Cookbook](https://github.com/ZQM-Labs/ldtk-cookbook) — structured level data, stable entity/checkpoint identity, and validation of authored content.
- [Location Games Cookbook](https://github.com/ZQM-Labs/location-games-cookbook) — location-aware game design, real-world safety, stale-location handling, accessibility alternatives, and checkpoint verification limits.

### Art, assets, and audio

- [Blender Cookbook](https://github.com/ZQM-Labs/blender-cookbook) — repeatable 3D asset creation and export practices for reusable game assets.
- [Krita Cookbook](https://github.com/ZQM-Labs/krita-cookbook) — 2D illustration, palette discipline, and export workflows for consistent visual assets.
- [Audacity Cookbook](https://github.com/ZQM-Labs/audacity-cookbook) — reproducible sound-effect editing and export workflows.

### Testing, backend, and payments

- [Playwright Cookbook](https://github.com/ZQM-Labs/playwright-cookbook) — browser-level regression checks for navigation, client state, and key player flows.
- [PocketBase Cookbook](https://github.com/ZQM-Labs/pocketbase-cookbook) — backend schema, authentication, record ownership, and authorization boundaries for remotely stored game or organizer data.
- [Stripe Cookbook](https://github.com/ZQM-Labs/stripe-cookbook) — checkout integration, webhook idempotency, failure handling, and reconciliation between payment and fulfillment.

### Validation principles

- A passing unit or structural test is not proof of target-editor compatibility or production readiness.
- Offline behavior requires tests for installation, reload, update, and recovery—not just a service-worker file.
- Accessibility and physical checkpoint safety require their own review and field evidence.
- Payment completion must be distinguished from successful, idempotent fulfillment.
- GPS and QR checkpoints are game mechanics, not proof of identity or secure authorization.

## Two complementary organizations

| Organization | Focus |
| --- | --- |
| [ZQM Labs](https://github.com/ZQM-Labs) | Games, quest experiences, content, and community play |
| [ZQM Computing](https://github.com/ZQM-Computing) | Geospatial engineering, open-source spatial patterns, data infrastructure, and supporting technology |

The organizations are related but distinct. ZQM Computing contributes geospatial methods where they support games; ZQM Labs remains focused on the game experiences and the people who play them.

## Contribute

- Read the [contribution guidelines](https://github.com/ZQM-Labs/.github/blob/main/CONTRIBUTING.md).
- Review the [security policy](https://github.com/ZQM-Labs/.github/blob/main/SECURITY.md) before reporting vulnerabilities.
- Follow the [Code of Conduct](https://github.com/ZQM-Labs/.github/blob/main/CODE_OF_CONDUCT.md).
- When reporting defects, include reproduction steps, environment details, expected behavior, and observed behavior. Label assumptions separately from verified findings.

Check each repository’s README, license, and current CI before relying on its instructions or claims.

---

*Games, gear & a little mischief. Play more. Plan less.*
