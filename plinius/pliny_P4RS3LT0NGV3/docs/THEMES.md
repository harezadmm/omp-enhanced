# Themes

P4RS3LT0NGV3 uses a **token-based theme system**. Most UI reads CSS custom properties (`--accent-color`, `--button-bg`, etc.) from `body.theme-*` blocks, so new themes are mostly palette + typography work—not per-component rewrites.

## Built-in themes

| ID | Name | Notes |
|----|------|--------|
| `dark` | Dark | Default; blue accent |
| `light` | Light | Light surfaces; blue accent |
| `accessible` | Accessible | WCAG 2.1 AA high-contrast; system fonts; strong focus rings |
| `bt6` | BT6 | Black + blood red + gold; mono titles |
| `pliny` | Pliny | CRT green-on-black |
| `cyberpunk` | Cyberpunk | Magenta + cyan neon |
| `wildwest` | Wild West | Cream / sage / dusty rose (light `color-scheme`) |

Users pick a theme in **Advanced Settings** (utility dock → Settings tab). Press **`D`** to cycle themes. The choice is saved in `localStorage` under the key `theme`.

## Accessible theme

The **`accessible`** theme targets **[WCAG 2.1 Level AA](https://www.w3.org/TR/WCAG21/)** for color, contrast, focus, and motion.

| Requirement | Implementation |
|-------------|------------------|
| **1.4.3 Contrast (AA)** | `#000000` / `#595959` text on `#ffffff`; `#004080` accent; category active colors darkened for white labels |
| **1.4.11 Non-text contrast** | `2px` borders at `#555555` on inputs, buttons, and cards |
| **2.4.7 Focus visible** | `3px` `#004080` outline + `2px` offset on all interactive elements |
| **1.4.12 Text spacing** | `1rem` base size, `1.5` line-height, system UI fonts |
| **1.4.1 Use of color** | Active nav/tabs use underline + weight + border, not color alone |
| **2.3.3 Animation** | Logo glitch and decorative card effects disabled |
| **Transform cards** | Text **Options** / **Favorite** buttons; fixed preview contrast and row heights |
| **Translation picker** | Text **Favorite** (and **Remove** on custom langs); star/× icons hidden |

Decorative themes (Cyberpunk, Pliny, etc.) are unchanged. For audits, test with the **Accessible** theme selected and keyboard-only navigation.

## How it works

1. **`js/utils/theme.js`** — Registry (`themes` array), `applyTheme()`, `cycleTheme()`, persistence.
2. **`css/style.css`** — One `body.theme-<id> { … }` block per theme defining design tokens.
3. **`css/themes-atmosphere.css`** — Optional “premium” overrides for custom themes (nav, transform cards, backgrounds, fonts). Imported at the top of `style.css`.
4. **`index.template.html`** — Inline bootstrap script applies the saved theme **before** Vue mounts (avoids flash of wrong theme).

When a theme is applied, the body gets:

- `theme-<id>` — primary selector (e.g. `theme-bt6`)
- `dark-theme` or `light-theme` — legacy aliases still used by a few rules

Copy an existing `body.theme-*` block as a starting point—`body.theme-dark` and `body.theme-light` are the simplest references; custom themes often follow the BT6 / Pliny pattern.

## Adding a new theme

### 1. Register in `js/utils/theme.js`

```javascript
{ id: 'mytheme', name: 'My Theme', icon: 'fa-star' }
```

- **`id`** — lowercase, no spaces; becomes `body.theme-mytheme`.
- **`name`** — label in the dropdown.
- **`icon`** — optional Font Awesome class (not shown in dropdown today, but kept for future use).

### 2. Add tokens in `css/style.css`

Add a new block (copy from `body.theme-dark` or an existing custom theme):

```css
body.theme-mytheme {
    --main-bg-color: #…;
    --secondary-bg: #…;
    --nav-bg: #…;
    --utility-tab-bg: #…;
    --text-color: #…;
    --text-muted: #…;
    --accent-color: #…;
    --accent-color-rgb: R, G, B;   /* comma-separated, no spaces */
    --accent-hover: #…;
    /* … accent-tint-*, surface-*, button-*, input-*, error-*, etc. */
    --glitch-color: #…;
    --glitch-color-rgb: R, G, B;
    --switch-border: #…;
    --switch-surface-glow: rgba(…);
    --switch-track-bg: #…;
    --switch-track-border: #…;
    --switch-track-checked-bg: #…;
    --switch-track-checked-glow: rgba(…);
    --switch-thumb-bg: #…;
    --switch-thumb-glow: rgba(…);
    --switch-thumb-checked-bg: #…;
    --switch-thumb-checked-glow: rgba(…);
    color-scheme: dark; /* or light for pale themes */
}
```

**Required tokens** — At minimum, match what `body.theme-dark` defines: surfaces, text, accent (+ `-rgb`), buttons, inputs, focus/error/success, tooltips, switch tokens, and legacy aliases (`--text-primary`, `--border-color`, etc.) at the bottom of the block.

**Light themes** — Set `color-scheme: light` and ensure `--text-on-accent` contrasts on `--accent-color`. Wild West is the reference for a light custom theme.

**Optional theme tokens** (used by atmosphere CSS):

- `--theme-display-font`, `--theme-ui-font`, `--theme-mono-font`
- `--theme-secondary`, `--theme-secondary-rgb`
- `--theme-radius` — corner radius (`0` for sharp, `2px`–`6px` for rounded)
- Wild West also uses `--theme-cream`, `--theme-charcoal`, etc.

### 3. Optional atmosphere in `css/themes-atmosphere.css`

For a distinctive look beyond color swaps, add a section:

```css
body.theme-mytheme .app-root::before { /* background texture / tint */ }
body.theme-mytheme .transform-button { /* card chrome */ }
body.theme-mytheme .app-nav .tab-buttons button.active { /* nav active state */ }
```

If you add a custom theme here, also extend the shared selectors at the top of the file (`body[class*="theme-…"]`) so shell layering (`::before` / z-index) stays consistent.

**Style guidelines** (project convention):

- Use **flat colors** only—no CSS gradients unless explicitly requested.
- Toggle switches (`.switch.neon`) pick up colors from `--switch-*` tokens automatically.
- Avoid logo `::before` / `::after` decorations.

### 4. Fonts (if needed)

Google Fonts are imported at the top of `css/style.css`. Add families there, then reference them in your `--theme-*-font` tokens.

### 5. Select carets & dropdowns

Custom themes with non-default accents often need a `select` caret override. See existing blocks:

```css
body.theme-mytheme select:not(.settings-theme-select) { background-image: url("data:…"); }
body.theme-mytheme .settings-theme-select { … }
```

Wild West required extra care so theme dropdown carets do not tile—use `background-repeat: no-repeat` and longhand `background-*` when overriding selects.

### 6. Build & test

```bash
npm run build
npm test
```

Open `dist/index.html` (or `npm start`) and check:

- [ ] Advanced Settings theme dropdown lists your theme
- [ ] **`D`** cycles through it without errors
- [ ] Nav, main content, utility dock (desktop)
- [ ] Mobile: utility panel toggle in header; no overlapping FAB
- [ ] Transform grid, toggles, inputs, notifications
- [ ] Advanced Settings / OpenRouter model dropdown (if applicable)
- [ ] Reload persists choice

No change to `index.template.html` is required unless you rename the bootstrap script flow—the dropdown is driven by `themeOptions` from Vue, which reads `ThemeUtils.getThemes()`.

## File checklist

| File | Action |
|------|--------|
| `js/utils/theme.js` | Add `{ id, name, icon }` |
| `css/style.css` | Add `body.theme-<id> { … }` token block |
| `css/themes-atmosphere.css` | Optional component/atmosphere overrides |
| `css/style.css` `@import` | Already imports `themes-atmosphere.css` — no change |
| `README.md` | Add theme to user-facing list (optional) |

## Updating an existing theme

1. Edit the `body.theme-<id>` token block in `css/style.css`.
2. Adjust matching rules in `css/themes-atmosphere.css` if the theme has premium styling.
3. Rebuild and spot-check the same checklist above.

Token changes propagate everywhere that uses `var(--…)`; you rarely need to touch individual tools or templates.

## Related docs

- **User-facing overview**: `README.md` → User Experience
- **Project layout**: `CONTRIBUTING.md` → Project Structure
- **UI patterns**: `docs/UI-COMPONENTS.md`
