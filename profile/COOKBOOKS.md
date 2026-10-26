# ZQM Labs Cookbook Catalog

> Catalog reviewed 2026-10-26. This is a navigation and assurance guide, not a release certification. Repository READMEs and workflow runs are the source of truth for current instructions and CI status.

ZQM Labs cookbooks are small, focused examples for the game client, content pipeline, testing, identity, and payments. **Implemented** means a starter example or focused test contract exists; it does not mean the entire roadmap is complete.

## Catalog

| Cookbook | Best used for | Why it is included | Implemented foundation | Automated evidence | Validation still needed |
| --- | --- | --- | --- | --- | --- |
| [Godot](https://github.com/ZQM-Labs/godot-cookbook) | Native game UI and scene patterns | Provides the native-engine counterpart to browser-first examples, so scene structure, input, UI, and accessibility contracts can be explored for packaged/native experiences rather than assuming all games run in a browser. | First-scene project and static contract tests | Static checks cover scene references and key interaction/accessibility contracts | Run the pinned Godot version in editor/headless mode and test actual viewport behavior |
| [Phaser](https://github.com/ZQM-Labs/phaser-cookbook) | Browser-game scenes and input | Covers browser-native game interaction and low-friction delivery; it complements Godot and supports rapid web demos where installation should not be a prerequisite. | First scene with keyboard/pointer interaction, status text, and load-failure handling | Node contract tests plus a mocked runtime harness | Real-browser/device smoke test with the pinned Phaser library; CDN availability is not guaranteed |
| [Tiled](https://github.com/ZQM-Labs/tiled-cookbook) | Tile-map structure and object markers | Separates map authoring from runtime code and provides a portable way to represent tile geometry and gameplay markers, reducing hand-edited map data and content/runtime drift. | Minimal map fixture with marker objects | Structural fixture tests and CI | Open/export with the target Tiled version; add tileset, collision geometry, and a playable sample |
| [LDtk](https://github.com/ZQM-Labs/ldtk-cookbook) | Level contracts and checkpoint identity | Documents structured level authoring and stable entity/checkpoint identity, which makes authored content easier to validate before it reaches a player build. | LDtk-shaped fixture and Node validator | Fixture validation and Node CI | Confirm the fixture/schema against an actual LDtk editor export |
| [Location Games](https://github.com/ZQM-Labs/location-games-cookbook) | Freshness checks for location-aware checkpoints | Addresses the distinctive risks of games played in physical places—location freshness, safety, accessibility alternatives, and the limits of GPS as evidence—rather than treating a map coordinate as secure authorization. | Timestamp evaluation wrapper with stale/invalid/future-time rejection | Deterministic unit tests | Validate integration in the consuming game; client GPS is not secure proof of physical presence |
| [Blender](https://github.com/ZQM-Labs/blender-cookbook) | Procedural 3D starter assets | Makes 3D asset generation repeatable and scriptable, helping teams produce reusable assets and verify export paths instead of relying on undocumented manual steps. | Python generator and GLB export path | Contract tests for the generator interface | Execute with the documented Blender build; inspect generated scene and open exported GLB in a real viewer |
| [Krita](https://github.com/ZQM-Labs/krita-cookbook) | 2D asset starters and palettes | Covers the 2D illustration and palette workflow needed for consistent game art, with asset contracts that help catch missing or malformed exports before integration. | Transparent SVG starter and palette data | Automated asset-contract tests | Import into Krita, check visual quality, and produce/review native layered .kra and final raster exports |
| [Audacity](https://github.com/ZQM-Labs/audacity-cookbook) | Repeatable sound-effect generation | Adds a reproducible audio workflow for sound effects and exports; deterministic file checks catch technical failures while explicitly leaving subjective listening and mix quality to human review. | Deterministic PCM WAV pulse generator | Tests for encoding, duration, non-silence, headroom, and determinism | Listen critically in Audacity and on representative speakers/headphones; numeric checks do not establish sound quality |
| [Playwright](https://github.com/ZQM-Labs/playwright-cookbook) | Browser behavior and regression tests | Provides browser regression patterns for player-critical interactions and state transitions, complementing unit tests that cannot prove the browser experience behaves correctly. | Browser-oriented example for client state and reload behavior | Automated tests include storage-failure and reload-state cases | Add/retain real browser execution for target applications; client-side state is not server-side entitlement |
| [PocketBase](https://github.com/ZQM-Labs/pocketbase-cookbook) | Authentication, ownership, and access rules | Documents backend identity and record-access boundaries so client interfaces are not mistaken for authorization; negative access cases and isolated integration tests are especially important. | Auth/profile example and fail-closed environment handling | Unit/regression coverage; live auth/access suite requires disposable synthetic accounts and a test instance | Run the opt-in integration suite against an isolated PocketBase instance; never point tests at production |
| [Stripe](https://github.com/ZQM-Labs/stripe-cookbook) | Checkout, webhooks, and durable fulfillment | Covers payment-to-fulfillment reliability, including webhook authenticity, idempotency, rollback, and failure recovery; payment success must not be conflated with durable entitlement delivery. | Failure-injection and transaction rollback patterns | Automated fault-injection tests and PostgreSQL rollback coverage | Exercise interrupted/rejected webhook recovery in a test environment; never use live payments as a test fixture |

## Assurance levels

Use these labels when reviewing or extending examples:

1. **Static contract** — files, metadata, references, or expected strings are checked. This is useful, but does not prove that the target application can open or execute the example.
2. **Unit/runtime harness** — behavior is exercised by code-level tests, possibly with mocks. This does not establish browser rendering, editor compatibility, or external-service behavior.
3. **Target-runtime smoke test** — the actual pinned engine, editor, browser, or application opens/runs the artifact.
4. **Integration test** — components are exercised together against isolated, synthetic services and data.
5. **Production readiness** — requires separate operational, security, accessibility, recovery, and release evidence; a cookbook CI pass alone is never sufficient.

Do not promote a cookbook's assurance level without recorded evidence. In particular, never treat a successful structural test as proof of secure authorization, physical location, payment entitlement, or production suitability.

## Cross-cookbook integration path

1. Build the game interaction in **Godot** or **Phaser**.
2. Use **Tiled** or **LDtk** for level structure where appropriate; validate exported content before packaging.
3. Use **Blender**, **Krita**, and **Audacity** for assets, then review the outputs in their actual target tools.
4. Use **Playwright** to exercise the player-facing critical path in a browser.
5. Use **PocketBase** for server-enforced identity and record access; test both allowed and denied requests.
6. Use **Stripe** only for payment flows that require it. Verify webhook authenticity and durable, idempotent server-side fulfillment; never unlock paid content from a client redirect alone.
7. For location-aware games, use **Location Games** freshness checks as a quality signal, not as an authorization boundary.

## Contributor checklist

For each new or upgraded pattern:

- [ ] State the target application/engine and exact tested version.
- [ ] Provide the smallest complete example and copy-pasteable test command.
- [ ] Keep tests deterministic and use synthetic data.
- [ ] Test negative paths and malformed input, not only the happy path.
- [ ] Separate static/unit evidence from target-runtime and integration evidence.
- [ ] Document prerequisites, known limitations, and what remains unverified.
- [ ] Never embed credentials, call production services by default, or delete a developer's working data.
- [ ] Update this catalog only when the underlying repository evidence changes.

## Sources

- [ZQM Labs repositories](https://github.com/orgs/ZQM-Labs/repositories)
- [Cookbook repositories](https://github.com/search?q=org%3AZQM-Labs+topic%3Acookbook&type=repositories)
