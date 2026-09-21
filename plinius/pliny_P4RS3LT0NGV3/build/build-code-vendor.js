#!/usr/bin/env node
/**
 * Bundle QR/barcode vendor libraries for the Codes tool (local copies, no CDN).
 */

const fs = require('fs');
const path = require('path');
const esbuild = require('esbuild');

const projectRoot = path.join(__dirname, '..');
const vendorDir = path.join(projectRoot, 'js/vendor');

if (!fs.existsSync(vendorDir)) {
    fs.mkdirSync(vendorDir, { recursive: true });
}

const bundles = [
    {
        entry: path.join(projectRoot, 'node_modules/qrcode/lib/browser.js'),
        outfile: path.join(vendorDir, 'qrcode.min.js'),
        globalName: 'QRCode'
    },
    {
        entry: path.join(projectRoot, 'node_modules/jsbarcode/bin/JsBarcode.js'),
        outfile: path.join(vendorDir, 'JsBarcode.min.js'),
        globalName: 'JsBarcode'
    }
];

console.log('📦 Building Codes tool vendor bundles...\n');

bundles.forEach(function(spec) {
    esbuild.buildSync({
        entryPoints: [spec.entry],
        bundle: true,
        format: 'iife',
        globalName: spec.globalName,
        outfile: spec.outfile,
        minify: true,
        platform: 'browser'
    });
    const sizeKb = (fs.statSync(spec.outfile).size / 1024).toFixed(1);
    console.log('✅ ' + path.basename(spec.outfile) + ' (' + sizeKb + 'KB)');
});

const zxingSrc = path.join(projectRoot, 'node_modules/@zxing/library/umd/index.min.js');
const zxingDest = path.join(vendorDir, 'zxing.min.js');
fs.copyFileSync(zxingSrc, zxingDest);
console.log('✅ zxing.min.js (' + (fs.statSync(zxingDest).size / 1024).toFixed(1) + 'KB)');
console.log('\n✨ Codes vendor bundles ready\n');
