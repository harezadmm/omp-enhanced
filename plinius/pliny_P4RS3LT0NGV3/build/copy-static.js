#!/usr/bin/env node
/**
 * Copy static files to dist/ directory
 * Copies css/, favicon.svg, and js/ directory structure to dist/
 * Generated files will be overwritten by build scripts
 */

const fs = require('fs');
const path = require('path');

console.log('📦 Copying static files to dist/...\n');

const projectRoot = path.join(__dirname, '..');
const distDir = path.join(projectRoot, 'dist');

// Ensure dist directory exists
if (!fs.existsSync(distDir)) {
    fs.mkdirSync(distDir, { recursive: true });
}

/**
 * Recursively copy directory
 */
function copyDirectory(src, dest) {
    if (!fs.existsSync(src)) {
        console.log(`⚠️  Warning: ${src} not found, skipping...`);
        return;
    }

    // Create destination directory
    if (!fs.existsSync(dest)) {
        fs.mkdirSync(dest, { recursive: true });
    }

    const entries = fs.readdirSync(src, { withFileTypes: true });

    for (const entry of entries) {
        const srcPath = path.join(src, entry.name);
        const destPath = path.join(dest, entry.name);

        if (entry.isDirectory()) {
            copyDirectory(srcPath, destPath);
        } else {
            fs.copyFileSync(srcPath, destPath);
        }
    }
}

/**
 * Copy a single file
 */
function copyFile(src, dest) {
    if (!fs.existsSync(src)) {
        console.log(`⚠️  Warning: ${src} not found, skipping...`);
        return;
    }

    const destDir = path.dirname(dest);
    if (!fs.existsSync(destDir)) {
        fs.mkdirSync(destDir, { recursive: true });
    }

    fs.copyFileSync(src, dest);
}

// Copy css/ directory
console.log('📁 Copying css/ directory...');
copyDirectory(
    path.join(projectRoot, 'css'),
    path.join(distDir, 'css')
);
console.log('✅ css/ copied');

// Copy favicon.svg
console.log('📄 Copying favicon.svg...');
copyFile(
    path.join(projectRoot, 'favicon.svg'),
    path.join(distDir, 'favicon.svg')
);
console.log('✅ favicon.svg copied');

// Copy js/ directory (excluding generated files that will be overwritten)
console.log('📁 Copying js/ directory...');
copyDirectory(
    path.join(projectRoot, 'js'),
    path.join(distDir, 'js')
);
console.log('✅ js/ copied (generated files will be overwritten by build scripts)');

console.log('\n✨ Static files copied to dist/');
console.log('   Note: Generated files (transforms-bundle.js, emojiData.js, index.html) will be created/overwritten by build scripts\n');

