#!/usr/bin/env node

const assert = require('assert');
const path = require('path');

const Ean13Utils = require(path.join(__dirname, '..', 'js', 'utils', 'ean13.js'));

assert.strictEqual(Ean13Utils.checksum('590123412345'), '7');
assert.strictEqual(Ean13Utils.checksum('400638133393'), '1');

const from12 = Ean13Utils.normalize('590123412345');
assert.strictEqual(from12.ok, true);
assert.strictEqual(from12.value, '5901234123457');

const from13 = Ean13Utils.normalize('5901234123457');
assert.strictEqual(from13.ok, true);
assert.strictEqual(from13.value, '5901234123457');

const wrongCheck = Ean13Utils.normalize('5901234123450');
assert.strictEqual(wrongCheck.ok, true);
assert.strictEqual(wrongCheck.value, '5901234123457');

const withSeparators = Ean13Utils.normalize('590-1234-12345');
assert.strictEqual(withSeparators.ok, true);
assert.strictEqual(withSeparators.value, '5901234123457');

const upcA = Ean13Utils.normalize('036000291452');
assert.strictEqual(upcA.ok, true);
assert.strictEqual(upcA.value, '0036000291452');

const tooShort = Ean13Utils.normalize('12345');
assert.strictEqual(tooShort.ok, false);

const tooLong = Ean13Utils.normalize('12345678901234');
assert.strictEqual(tooLong.ok, false);

const EAN13 = require(path.join(__dirname, '..', 'node_modules', 'jsbarcode', 'bin', 'barcodes', 'EAN_UPC', 'EAN13.js')).default;
const defaults = require(path.join(__dirname, '..', 'node_modules', 'jsbarcode', 'bin', 'options', 'defaults.js')).default;

const normalizedWrong = Ean13Utils.normalize('5901234123450');
const encoder = new EAN13(normalizedWrong.value, Object.assign({}, defaults, { displayValue: true }));
assert.strictEqual(encoder.valid(), true, 'Normalized value should pass JsBarcode validation');

console.log('EAN-13 codes tests passed');
