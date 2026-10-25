# ZQM-Labs/.github

<!-- ZQM-START -->
<!-- markdownlint-disable MD033 -->
<p align="center">
  <strong>ZQM Labs — Z's Quests & Mischief</strong><br>
  <a href="https://zqmlabs.com">zqmlabs.com</a> •
  <a href="https://github.com/ZQM-Labs">GitHub</a>
</p>
<!-- markdownlint-enable MD033 -->
<!-- ZQM-END -->

The **ZQM Labs GitHub organization profile and community-health repository**. It supplies the public organization profile and reusable contribution, conduct, issue, and pull-request guidance for repositories that do not define their own. Product code and game content live in the individual project repositories; this repo is the organization-level front door.

- `profile/README.md` — the public org profile shown on the ZQM-Labs page (ZQM Labs — Z's Quests & Mischief).
- Community health files here (contributing guidelines, code of conduct, issue and PR templates) apply as org-wide defaults to repositories that don't carry their own.

Brand and project work live in the org's repositories; this repo is the front door.

## Repository role and status

**Status:** Active, public. Documented verdict (2026-10-19 estate audit): **KEEP**.

**What this repository is:** The org-level presence repository for ZQM-Labs. Its `profile/README.md` is what GitHub renders on the organization's public profile page — the front door for the game lab — and the community-health files here apply as org-wide defaults.

**What it contributes:**

- The ZQM-Labs org profile page itself: who the lab is, the Dr. Z / Wisp story, the live Halloween pilot, and the map of the games repositories (player, quest packs, authoring, organizer toolkit, playtests, quest-analytics, site).
- The public statement of the two-account boundary: ZQM-Labs is the game lab; ZQM-Computing is geospatial engineering and infrastructure.
- Org-wide community defaults for every ZQM-Labs repository that does not supply its own.

**Why it is not a deletion candidate:** Deleting it removes the org's public profile page and its community-health defaults. It is a brand surface, not scaffolding.

**Placement:** ZQM-Labs (org profile).

<!-- ZQM-FOOTER-START -->
<!-- markdownlint-disable MD033 -->
---

<p align="center">
  <em>Play more. Plan less.</em><br>
  <a href="https://zqmlabs.com">zqmlabs.com</a> •
  <a href="https://github.com/ZQM-Labs">ZQM Labs</a> •
  <a href="https://github.com/ZQM-Computing">ZQM Computing</a>
</p>
<!-- markdownlint-enable MD033 -->
<!-- ZQM-FOOTER-END -->

Organization defaults — no installation.

## Usage

The community-health files in this repository act as organization-wide
defaults: repositories in the ZQM-Labs org that don't carry their own
contributing guide, code of conduct, or issue/PR templates inherit these.
The org profile itself lives in `profile/README.md`.

## License

MIT — see [LICENSE](LICENSE).

## Validation

This repository uses GitHub Actions for continuous integration. See the [Actions tab](https://github.com/ZQM-Labs/.github/actions) for workflow runs.

To validate locally:

```bash
# Run documentation checks
python scripts/check_docs.py
```
