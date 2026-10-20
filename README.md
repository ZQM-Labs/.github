# ZQM-Labs/.github

<!-- ZQM-START -->
<p align="center">
  <strong>ZQM Labs — Z's Quests & Mischief</strong><br>
  <a href="https://zqmlabs.com">zqmlabs.com</a> •
  <a href="https://github.com/ZQM-Labs">GitHub</a>
</p>
<!-- ZQM-END -->



Organization profile and community health files for the ZQM-Labs org.

- `profile/README.md` — the public org profile shown on the ZQM-Labs page (ZQM Labs — Z's Quests & Mischief).
- Community health files here (contributing guidelines, code of conduct, issue and PR templates) apply as org-wide defaults to repositories that don't carry their own.

Brand and project work live in the org's repositories; this repo is the front door.


<!-- ZQM-FOOTER-START -->
---

<p align="center">
  <em>Play more. Plan less.</em><br>
  <a href="https://zqmlabs.com">zqmlabs.com</a> •
  <a href="https://github.com/ZQM-Labs">ZQM Labs</a> •
  <a href="https://github.com/ZQM-Computing">ZQM Computing</a>
</p>
<!-- ZQM-FOOTER-END -->

## Installation

```bash
pip install -e .
```

Requires Python 3.11+.

## License

MIT — see [LICENSE](LICENSE).

## Validation

This repository uses GitHub Actions for continuous integration. See [CI workflow](.github/workflows/ci.yml) for details.

To validate locally:

```bash
# Run documentation checks
python scripts/check_docs.py
```
