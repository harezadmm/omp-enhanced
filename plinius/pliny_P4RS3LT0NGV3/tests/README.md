# Tests

## Test Suites

### `test_universal.js`
Tests universal decoder and all transformers:
- Encoding/decoding round-trips
- Universal decoder detection accuracy
- Edge cases and Unicode handling

```bash
npm run test:universal
```

### `test_steganography_options.js`
Tests steganography with all advanced option combinations:
  - Bit order (MSB/LSB)
- Variation selector mapping
  - Initial presentation options
- Zero-width character options

```bash
npm run test:steg
```

## Running Tests

```bash
npm run test:all      # Run all tests
npm test              # Universal decoder tests
npm run test:steg     # Steganography tests
```

## Test Structure

Tests use Node.js `vm` module to create sandboxed environments that mirror the browser context.

## Adding New Tests

1. Place test files in `tests/` directory
2. Use `path.resolve(__dirname, '..')` for project root
3. Add corresponding npm script in `package.json`
