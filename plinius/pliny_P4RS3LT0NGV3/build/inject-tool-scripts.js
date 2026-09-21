#!/usr/bin/env node
/**
 * Auto-discover and inject tool script tags into index.template.html
 * Also generates auto-registration code for toolRegistry.js
 */

const fs = require('fs');
const path = require('path');

console.log('🔧 Auto-discovering tools and generating script tags...\n');

const toolsDir = path.join(__dirname, '../js/tools');
const templatePath = path.join(__dirname, '../index.template.html');
const registryPath = path.join(__dirname, '../js/core/toolRegistry.js');

// Discover all tool files (excluding Tool.js base class)
const toolFiles = fs.readdirSync(toolsDir)
    .filter(file => file.endsWith('Tool.js') && file !== 'Tool.js')
    .sort(); // Sort for consistent ordering

console.log(`📦 Found ${toolFiles.length} tools:`);
toolFiles.forEach(file => console.log(`   - ${file}`));

// Generate script tags
const scriptTags = toolFiles.map(file => 
    `    <script src="js/tools/${file}"></script>`
).join('\n');

// Read index.template.html
let templateContent = fs.readFileSync(templatePath, 'utf8');

// Find the tool scripts section (between Tool.js and toolRegistry.js)
const toolJsMarker = '<script src="js/tools/Tool.js"></script>';
const registryMarker = '<script src="js/core/toolRegistry.js"></script>';

const toolJsIndex = templateContent.indexOf(toolJsMarker);
const registryIndex = templateContent.indexOf(registryMarker);

if (toolJsIndex === -1 || registryIndex === -1) {
    console.error('\n❌ Could not find tool script markers in index.template.html');
    process.exit(1);
}

// Extract the section between Tool.js and toolRegistry.js
const before = templateContent.substring(0, toolJsIndex + toolJsMarker.length);
const after = templateContent.substring(registryIndex);

// Replace with dynamic script tags
const newTemplateContent = before + '\n' + scriptTags + '\n' + after;

// Write updated template
fs.writeFileSync(templatePath, newTemplateContent, 'utf8');
console.log('\n✅ Updated index.template.html with dynamic tool script tags');

// Generate auto-registration code
const registrationCode = toolFiles.map(file => {
    // Extract class name from filename (e.g., "TransformTool.js" -> "TransformTool")
    const className = file.replace('.js', '');
    return `if (typeof ${className} !== 'undefined') {
    window.toolRegistry.register(new ${className}());
}`;
}).join('\n');

// Read toolRegistry.js
let registryContent = fs.readFileSync(registryPath, 'utf8');

// Find and replace the manual registration section
const autoRegisterStart = '// Auto-register tools if they\'re available';
const autoRegisterEnd = '// Export for module systems';

const startIndex = registryContent.indexOf(autoRegisterStart);
const endIndex = registryContent.indexOf(autoRegisterEnd);

if (startIndex === -1 || endIndex === -1) {
    console.error('\n❌ Could not find auto-registration section in toolRegistry.js');
    process.exit(1);
}

// Replace with dynamic registration
const beforeRegistry = registryContent.substring(0, startIndex);
const afterRegistry = registryContent.substring(endIndex);

const newRegistryContent = beforeRegistry + 
    autoRegisterStart + '\n' + 
    registrationCode + '\n\n' + 
    afterRegistry;

// Write updated registry
fs.writeFileSync(registryPath, newRegistryContent, 'utf8');
console.log('✅ Updated toolRegistry.js with dynamic tool registration');
console.log(`\n✨ ${toolFiles.length} tools auto-discovered and registered!\n`);

