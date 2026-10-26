# Translating Sonos Web

The interface is fully translatable. English is the primary language and the reference; every other language is a single JSON file.

## Add a new language

1. Copy `static/i18n/en.json` to `static/i18n/<code>.json`, using the two-letter [ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) code – e.g. `fr.json`, `es.json`, `nl.json`.
2. Set the display name in `_meta`, written in the language itself:
   ```json
   "_meta": { "name": "Français" }
   ```
3. Translate the values. **Do not change the keys.**
4. Reload the page. The new language shows up automatically under *Rooms › Language* – no code changes, no build step, no server restart.

The interface picks the browser language automatically if a matching file exists, otherwise English. The choice under *Rooms › Language* is stored per device.

## Rules

- **Placeholders** in curly braces are filled in at runtime and must stay as they are: `"Volume {name}"` → `"Volume {name}"` (you may move them within the sentence).
- **Plurals** are objects with categories from [`Intl.PluralRules`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/PluralRules) for your language (`zero`, `one`, `two`, `few`, `many`, `other`). `other` is required:
  ```json
  "tracks": { "one": "{count} track", "other": "{count} tracks" }
  ```
- **Lists** such as `days.short` must keep their length and order (Sunday first).
- A few values contain simple HTML (`<b>`, `<i>`, `<br>`, `<code>`) – keep the tags.
- Missing keys fall back to English, so a partial translation already works.

## Checking your work

Open the browser console while using the interface in your language:

- `I18N.untranslated` – keys that are still missing in your file (English was shown instead)
- `I18N.missing` – keys that exist nowhere (please report these as a bug)

Each missing key is also logged once to the console as you click through the interface.

## Notes

- Error messages from the server arrive as codes and are translated via the `err.*` keys.
- Demo mode content (room names, playlists, lyrics) is sample data and stays in English.
- Pull requests with new languages are welcome.
