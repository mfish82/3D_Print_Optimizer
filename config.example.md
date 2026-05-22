# Bambu Optimizer — User Config
# Copy this file to config.md and fill in your values.
# config.md is gitignored and never uploaded to GitHub.

## Printer
printer: P2S
# Your Bambu printer model — e.g. P2S, X1C, A1, A1Mini, H2D, or any other Bambu model.
# Claude uses this for context. Any Bambu model works; the feedback loop learns your specific printer over time.

## Paths
skill_dir: C:\Users\YOUR_USERNAME\.claude\skills\bambu-optimizer
# The directory where this skill lives (contains SKILL.md)

profile_base: C:\Users\YOUR_USERNAME\AppData\Roaming\BambuStudio\user\YOUR_USER_ID
# BambuStudio user profile directory — contains process\ and filament\ subdirectories
# Find YOUR_USER_ID: browse to AppData\Roaming\BambuStudio\user\ — it's the numeric folder

print_log: C:\PATH\TO\YOUR\print-log.md
# Markdown file where print history is tracked
# Can live anywhere — Obsidian vault, Dropbox, local folder, etc.
# Claude will create it if it doesn't exist yet
