# Contributing to 3beditor

Thanks for helping. 3beditor is made and maintained by Duong Phu Dong ([@DongDuong2001](https://github.com/DongDuong2001)) at Three Bugs Studio.

## How to send a change

1. Fork the repo and make a branch from `main`.
2. Make your change. Keep it small and focused on one thing.
3. Run the tests. They need Python 3.10+ and FFmpeg:
   ```bash
   python -m pytest -q tests
   ```
4. Open a pull request to `main` and fill in the template.

Only [@DongDuong2001](https://github.com/DongDuong2001) reviews, approves and merges pull requests. Nobody can push to `main` directly.

## Rules for code

- Python standard library and FFmpeg only. No new dependencies without asking in an issue first.
- New logic needs a test in `tests/`.
- Skill text (`skills/`, `commands/`) is written in plain English for people who don't edit videos.
- Media you add (sounds, fonts, images) must be CC0 or your own work, with the source listed in a `CREDITS.md`.
- Never add code that downloads TikTok or YouTube audio, or gets around a site's bot checks.

## Bugs and ideas

Open an [issue](https://github.com/Three-Bugs-Studio/3beditor/issues/new/choose). For security problems, see [SECURITY.md](SECURITY.md).

By contributing, you agree your work is released under the [MIT License](LICENSE).
