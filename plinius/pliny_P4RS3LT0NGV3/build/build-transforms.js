#!/usr/bin/env node

/**
 * Build Script for Transforms
 * Dynamically discovers and bundles all transformers from the directory structure
 */

const fs = require('fs');
const path = require('path');

// First, read the BaseTransformer class
const baseTransformerPath = path.join(__dirname, '..', 'src', 'transformers', 'BaseTransformer.js');
const baseTransformerContent = fs.readFileSync(baseTransformerPath, 'utf8')
    .replace(/export\s+(default\s+)?/g, ''); // Remove export/export default statements

// Discover all transformers dynamically
const transformersDir = path.join(__dirname, '..', 'src', 'transformers');
const transforms = {};

// Files to skip
const skipFiles = ['BaseTransformer.js', 'index.js', 'loader.js', 'loader-node.js', 'README.md'];

// Get all category directories
const categoryDirs = fs.readdirSync(transformersDir, { withFileTypes: true })
    .filter(dirent => dirent.isDirectory())
    .map(dirent => dirent.name)
    .sort();

// Discover transforms from each category directory
for (const categoryDir of categoryDirs) {
    const categoryPath = path.join(transformersDir, categoryDir);
    const files = fs.readdirSync(categoryPath)
        .filter(file => file.endsWith('.js') && !skipFiles.includes(file));
    
    for (const file of files) {
        // Convert filename to transform name (kebab-case to snake_case)
        // e.g., "upside-down.js" -> "upside_down", "base64.js" -> "base64"
        const transformName = file.replace('.js', '').replace(/-/g, '_');
        const filePath = `${categoryDir}/${file}`;
        transforms[transformName] = filePath;
    }
}

// Start building the output
let output = `/**
 * P4RS3LT0NGV3 Transforms - Bundled for Browser
 * Auto-generated from modular source files
 * Build date: ${new Date().toISOString()}
 * Total transforms: ${Object.keys(transforms).length}
 */

(function() {
'use strict';

// BaseTransformer class
${baseTransformerContent}

const transforms = {};

`;

// Load and bundle each transform
for (const [name, filePath] of Object.entries(transforms)) {
    const fullPath = path.join(transformersDir, filePath);
    
    try {
        let content = fs.readFileSync(fullPath, 'utf8');
        
        // Extract category from directory path
        const categoryDir = path.dirname(filePath);
        let category = categoryDir === '.' ? 'special' : categoryDir;
        
        // Special case: randomizer.js should have category 'randomizer' for UI handling
        if (name === 'randomizer') {
            category = 'randomizer';
        }
        
        // Automatically set/update category based on directory
        // Pattern: category: '...' or category: "..."
        const categoryPattern = /category\s*:\s*['"]([^'"]+)['"]/;
        
        if (categoryPattern.test(content)) {
            // Replace existing category
            content = content.replace(categoryPattern, `category: '${category}'`);
        } else {
            // Inject category after name or priority property
            // Look for the object opening and find a good place to inject
            const injectPattern = /(name\s*:\s*['"][^'"]+['"],?\s*)/;
            if (injectPattern.test(content)) {
                content = content.replace(injectPattern, `$1    category: '${category}',\n    `);
            } else {
                // Fallback: inject after the opening brace of BaseTransformer
                content = content.replace(/(new BaseTransformer\(\{)/, `$1\n    category: '${category}',`);
            }
        }
        
        // Extract the object definition (remove comments, import, and export statements)
        let cleanContent = content
            .replace(/^\/\/.*$/gm, '') // Remove single-line comments
            .replace(/import\s+.*?from\s+['"].*?['"]\s*;?\s*/g, '') // Remove import statements
            .replace(/export default\s*/g, '') // Remove export statement
            .trim();

        if (/^(const|let|var|function)\s/m.test(cleanContent)) {
            console.error(`❌ ${name}: top-level declarations break the bundle — wrap in export default (function(){ ... return new BaseTransformer(...); })();`);
            process.exit(1);
        }

        output += `// ${name} (from ${filePath})\n`;
        if (/^\(function\s*\(\)/.test(cleanContent)) {
            output += `transforms['${name}'] = ${cleanContent}\n\n`;
        } else if (/^new BaseTransformer\s*\(/.test(cleanContent)) {
            output += `transforms['${name}'] = ${cleanContent}\n\n`;
        } else {
            output += `transforms['${name}'] = ${cleanContent}\n\n`;
        }
        
        console.log(`✅ Bundled: ${name} (category: ${category})`);
    } catch (error) {
        console.error(`❌ Error bundling ${name}:`, error.message);
    }
}

// Close the IIFE and expose to window
output += `
// Expose to window
window.transforms = transforms;
window.encoders = transforms; // Alias for compatibility

})();
`;

// Write the bundled file
const outputPath = path.join(__dirname, '..', 'dist', 'js', 'bundles', 'transforms-bundle.js');
const outputDir = path.dirname(outputPath);

// Ensure the directory exists
if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
}

fs.writeFileSync(outputPath, output, 'utf8');

console.log(`\n✨ Bundle created: ${outputPath}`);
console.log(`📦 Size: ${(output.length / 1024).toFixed(2)} KB`);
console.log(`🔢 Total transforms: ${Object.keys(transforms).length}`);
