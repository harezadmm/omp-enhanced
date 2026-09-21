# Tool HTML Templates

Templates are injected at build time into `index.html` via `npm run build:templates`.

## Workflow

1. Edit `.html` files in `templates/`
2. Run `npm run build:templates`
3. Refresh browser

## Template Files

- `decoder.html` - Universal Decoder
- `steganography.html` - Emoji Steganography
- `transforms.html` - Text Transformations
- `tokenade.html` - Tokenade Generator
- `fuzzer.html` - Mutation Lab
- `tokenizer.html` - Tokenizer Visualization
- `splitter.html` - Message Splitter
- `gibberish.html` - Gibberish Generator

## Adding a New Tool Template

1. Create `templates/yourtool.html`
2. Start with: `<div v-if="activeTab === 'yourtool'" class="tab-content">`
3. Use Vue directives (`v-model`, `@click`, etc.)
4. Reference data/methods from your tool's `getVueData()` and `getVueMethods()`
5. Run `npm run build:templates`

## Important

- **Never edit `index.html` directly** - it's generated
- **Always rebuild after template changes** - `npm run build:templates`
- Templates are injected at the `#tool-content-container` marker
