# ZQM Visual System

This document defines the first-pass visual rules for ZQM Labs and ZQM Computing. It is a working standard, not a claim that every existing repository has been migrated.

## Brand architecture

### ZQM Labs
**Role:** Community games, playful experiences, game operations, and open tools.

- Ink: `#2b2118`
- Cream: `#fff7ea`
- Quest orange: `#e07b24`
- Dark orange for text on light surfaces: `#b35c12`
- Motifs: lantern, map pin, compass, friendly character silhouettes, checkpoint constellations.
- Voice: curious, accessible, playful; avoid promising availability, language coverage, or real-world venue details that have not been verified.

### ZQM Computing
**Role:** Geospatial engineering, scientific computing, data infrastructure, and reusable engineering patterns.

- Night navy: `#081522`
- Deep blue-green: `#102b3b`
- Spatial cyan: `#56d6d0`
- Mint: `#7fe2c3`
- Light text: `#f1f7f6`
- Motifs: topographic contours, coordinate grids, hex cells, spatial layers, precise geometry.
- Voice: technical, clear, evidence-led; diagrams must represent actual system behavior, not decorative guesses.

## Shared rules

1. **Related, not identical.** Keep a shared level of craft and geometry, but make games and engineering tools distinguishable at a glance.
2. **Prefer source-owned assets.** Keep SVG and raster assets in the repository that owns their use. Avoid third-party image hosts for core branding.
3. **Use SVG for scalable vector work.** Give each SVG explicit dimensions, a `viewBox`, a descriptive `<title>`, and a `<desc>` when the artwork conveys meaningful information.
4. **Do not encode essential text only in artwork.** Repeat product names, calls to action, and important claims in accessible HTML/Markdown.
5. **Keep text readable.** Check at narrow mobile widths and in dark/light GitHub themes; do not rely on color alone to communicate status.
6. **Respect product boundaries.** Do not use playful game artwork as the default for infrastructure, security, attestation, or internal research repositories.
7. **No invented claims.** Verify language support, locations, features, production status, performance figures, and release readiness against the relevant source before placing them in graphics.
8. **No secrets or sensitive operational details.** Never place tokens, internal hostnames, personal data, private maps, or security findings in public artwork.
9. **Use reproducible assets.** Keep editable vector source in Git. For platform-specific avatars or social preview uploads, export the source to the required PNG/JPEG dimensions and review the rendered output.
10. **Avoid duplicating canonical logos.** If an asset already exists and is current, reuse it; propose replacements rather than silently replacing established art.

## Recommended sizes

| Use | Working size | Format | Notes |
|---|---:|---|---|
| GitHub profile README banner | 1200 × 320 | SVG source; export if a platform requires raster | Keep important text in the left/center safe area |
| Repository README banner | 1200 × 340 | SVG or WebP | Include project name and one concise descriptor |
| GitHub organization/avatar upload | 500 × 500 | PNG/JPG/GIF under 1 MB | Export from the canonical vector mark |
| Repository social preview | 1280 × 640 | PNG/JPG | Confirm platform support before choosing format |
| App/PWA icon | 512 × 512 source | SVG plus required raster exports | Check maskable/safe-area requirements separately |
| In-product illustration | Component-specific | WebP/PNG/SVG | Optimize file size; preserve useful alt text |

These are working design targets. Confirm current platform constraints before uploading a final avatar or social preview.

## Current starter assets

- `profile/assets/zqm-labs-banner.svg` — organization README banner.
- `profile/assets/zqm-labs-mark.svg` — vector mark source for future avatar exports.
- `profile/assets/zqm-computing-banner.svg` — engineering profile banner in the ZQM Computing repository.
- `profile/assets/zqm-computing-mark.svg` — vector mark source for future avatar exports.
- `lantern-player/assets/img/wisps-lost-lanterns-readme-banner.svg` — game-specific README banner.

The game banner is in the player repository and is proposed separately. The profile banners are also proposed in their own pull requests. Do not assume any proposed asset is deployed until its pull request is reviewed and merged.

## Review checklist for new visuals

- [ ] Correct project and brand family.
- [ ] Source file committed to the owning repository.
- [ ] Explicit dimensions and valid SVG structure (if SVG).
- [ ] Descriptive title/description and useful alt text.
- [ ] No unverified product, availability, localization, or performance claims.
- [ ] Readable at mobile width and in GitHub's rendered README.
- [ ] File paths and casing verified against repository contents.
- [ ] Raster exports optimized when required by the target platform.
- [ ] Runtime assets included in offline precache only when the app actually needs them.
