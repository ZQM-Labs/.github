# ZQM Labs Cookbook Catalog

This catalog explains why each cookbook topic belongs in the ZQM Labs portfolio. Inclusion rationale is not a claim that every example is complete, validated against every target application, or production-ready. Consult each repository's README, license, dependencies, current CI, and target-runtime evidence before relying on it.

## Game engines and level design

### [godot-cookbook](https://github.com/ZQM-Labs/godot-cookbook)
**Purpose:** Godot scene structure, UI, input, and reusable game interactions.  
**Why included:** Covers native-game patterns for projects that need a packaged client or structured scene system. Verify examples in the target Godot version.

### [phaser-cookbook](https://github.com/ZQM-Labs/phaser-cookbook)
**Purpose:** Browser-first game scenes and interactions.  
**Why included:** Supports low-friction web delivery and JavaScript/TypeScript game experiences. Browser behavior still requires runtime testing.

### [tiled-cookbook](https://github.com/ZQM-Labs/tiled-cookbook)
**Purpose:** Tile-map authoring and map metadata.  
**Why included:** Helps separate level geometry from gameplay logic and standardize checkpoint or object markers. Validate exported maps against the consuming runtime.

### [ldtk-cookbook](https://github.com/ZQM-Labs/ldtk-cookbook)
**Purpose:** Structured level data and entity metadata.  
**Why included:** Supports stable object identity and validation of authored level content before it reaches a player.

### [location-games-cookbook](https://github.com/ZQM-Labs/location-games-cookbook)
**Purpose:** Location-aware game design and field operations.  
**Why included:** Location games require explicit treatment of physical safety, stale or inaccurate GPS, privacy, accessibility alternatives, and checkpoint verification limits.

## Art, assets, and audio

### [blender-cookbook](https://github.com/ZQM-Labs/blender-cookbook)
**Purpose:** Repeatable 3D asset creation and export.  
**Why included:** Establishes reusable asset-production patterns and reduces avoidable differences between source files and game-ready exports.

### [krita-cookbook](https://github.com/ZQM-Labs/krita-cookbook)
**Purpose:** 2D illustration, palette, and export workflows.  
**Why included:** Supports consistent visual assets and repeatable export settings across game content.

### [audacity-cookbook](https://github.com/ZQM-Labs/audacity-cookbook)
**Purpose:** Sound-effect editing and audio export.  
**Why included:** Documents repeatable audio editing so effects can be regenerated and delivered with consistent formats and levels.

## Testing, backend, and payments

### [playwright-cookbook](https://github.com/ZQM-Labs/playwright-cookbook)
**Purpose:** Browser automation and end-to-end regression checks.  
**Why included:** Helps validate navigation, client state, and important player flows. Passing browser tests does not guarantee coverage of every device or browser.

### [pocketbase-cookbook](https://github.com/ZQM-Labs/pocketbase-cookbook)
**Purpose:** Backend schema, authentication, record ownership, and authorization.  
**Why included:** Persistent game and organizer data needs explicit access boundaries and tests for unauthorized reads and writes.

### [stripe-cookbook](https://github.com/ZQM-Labs/stripe-cookbook)
**Purpose:** Checkout, webhook processing, and fulfillment workflows.  
**Why included:** Payment processing must handle retries, duplicate events, failures, and reconciliation. A successful checkout page alone is not proof that fulfillment completed.

## Cross-cutting validation checklist

For every cookbook, record the current state of:

- [ ] Clear scope and intended audience.
- [ ] Supported tool/runtime versions and prerequisites.
- [ ] Reproducible quick start with expected output.
- [ ] Tests and exact commands to run them.
- [ ] Current CI status, linked to the relevant commit.
- [ ] Target-application validation where applicable.
- [ ] Security, privacy, accessibility, and safety limits.
- [ ] License and attribution requirements.
- [ ] Known gaps and last-reviewed date.

Use explicit evidence labels: **documented**, **unit-tested**, **integration-tested**, **validated in target runtime**, and **production-observed**. Do not promote one assurance level based on evidence from a weaker level.

## Related projects

- [ZQM Labs profile](https://github.com/ZQM-Labs/.github/blob/main/profile/README.md)
- [All ZQM Labs repositories](https://github.com/orgs/ZQM-Labs/repositories)
- [ZQM Labs contribution guidelines](https://github.com/ZQM-Labs/.github/blob/main/CONTRIBUTING.md)
- [ZQM Labs security policy](https://github.com/ZQM-Labs/.github/blob/main/SECURITY.md)
