#!/usr/bin/env node

/**
 * Test Suite for Steganography Options Round-Trip
 * 
 * Tests encoding and decoding with various advanced option combinations
 * to ensure they work correctly together.
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

// Get project root directory (parent of tests directory)
const projectRoot = path.resolve(__dirname, '..');

// Load steganography module
const stegCode = fs.readFileSync(path.join(projectRoot, 'js/core/steganography.js'), 'utf8');
const escapeParserCode = fs.readFileSync(path.join(projectRoot, 'js/utils/escapeParser.js'), 'utf8');

// Create sandbox
const sandbox = {
    window: {
        EscapeParser: {}
    },
    console: console,
    TextEncoder: TextEncoder,
    TextDecoder: TextDecoder
};

vm.createContext(sandbox);

// Load escape parser first
vm.runInContext(escapeParserCode, sandbox);

// Load steganography
vm.runInContext(stegCode, sandbox);

const steganography = sandbox.window.steganography;

// Test strings
const testStrings = [
    'hello',
    'hello world',
    'Hello World!',
    'Test with emoji 🐍',
    'Special chars: !@#$%^&*()',
    'Unicode: 你好 🌞',
    'Longer text: The quick brown fox jumps over the lazy dog.'
];

// Test option combinations
const testConfigs = [
    {
        name: 'Default options',
        options: {}
    },
    {
        name: 'LSB bit order',
        options: { bitOrder: 'lsb' }
    },
    {
        name: 'Swapped VS (VS15=1, VS16=0)',
        options: { bitZeroVS: '\ufe0f', bitOneVS: '\ufe0e' }
    },
    {
        name: 'No initial presentation',
        options: { initialPresentation: 'none' }
    },
    {
        name: 'Text initial presentation',
        options: { initialPresentation: 'text' }
    },
    {
        name: 'Inter-bit ZWNJ every bit',
        options: { interBitZW: '\u200C', interBitEvery: 1 }
    },
    {
        name: 'Inter-bit ZWJ every 2 bits',
        options: { interBitZW: '\u200D', interBitEvery: 2 }
    },
    {
        name: 'Inter-bit ZWSP every 4 bits',
        options: { interBitZW: '\u200B', interBitEvery: 4 }
    },
    {
        name: 'Trailing ZWNJ',
        options: { trailingZW: '\u200C' }
    },
    {
        name: 'Trailing ZWJ',
        options: { trailingZW: '\u200D' }
    },
    {
        name: 'Trailing BOM',
        options: { trailingZW: '\ufeff' }
    },
    {
        name: 'Complex: LSB + swapped VS + inter-bit',
        options: {
            bitOrder: 'lsb',
            bitZeroVS: '\ufe0f',
            bitOneVS: '\ufe0e',
            interBitZW: '\u200C',
            interBitEvery: 2
        }
    },
    {
        name: 'Complex: All options',
        options: {
            bitOrder: 'lsb',
            bitZeroVS: '\ufe0f',
            bitOneVS: '\ufe0e',
            initialPresentation: 'text',
            interBitZW: '\u200D',
            interBitEvery: 3,
            trailingZW: '\u200C'
        }
    }
];

console.log('🧪 Testing Steganography Options Round-Trip\n');
console.log('='.repeat(80));

let totalTests = 0;
let passedTests = 0;
let failedTests = 0;
const failures = [];

// Test each configuration
for (const config of testConfigs) {
    console.log(`\n📋 Testing: ${config.name}`);
    console.log('   Options:', JSON.stringify(config.options, null, 2));
    
    // Reset to defaults first, then apply test options
    // This ensures each test starts with a clean state
    steganography.setStegOptions({
        bitZeroVS: '\ufe0e',
        bitOneVS: '\ufe0f',
        initialPresentation: 'emoji',
        trailingZW: '\u200B',
        interBitZW: null,
        interBitEvery: 1,
        bitOrder: 'msb'
    });
    steganography.setStegOptions(config.options);
    
    // Test each string
    for (const testString of testStrings) {
        totalTests++;
        
        try {
            // Encode with current options
            const encoded = steganography.encodeEmoji('🐍', testString);
            
            // Decode with same options (should match)
            const decoded = steganography.decodeEmoji(encoded);
            
            // Check if decoded matches original
            if (decoded === testString) {
                passedTests++;
                process.stdout.write('  ✅');
            } else {
                failedTests++;
                process.stdout.write('  ❌');
                failures.push({
                    config: config.name,
                    options: config.options,
                    original: testString,
                    encoded: encoded,
                    decoded: decoded,
                    encodedLength: encoded.length,
                    decodedLength: decoded.length
                });
            }
        } catch (error) {
            failedTests++;
            process.stdout.write('  💥');
            failures.push({
                config: config.name,
                options: config.options,
                original: testString,
                error: error.message,
                stack: error.stack
            });
        }
    }
    
    console.log(''); // New line after each config
}

// Summary
console.log('\n' + '='.repeat(80));
console.log('\n📊 Test Summary:\n');
console.log(`Total tests: ${totalTests}`);
console.log(`✅ Passed: ${passedTests}`);
console.log(`❌ Failed: ${failedTests}`);
console.log(`Success rate: ${((passedTests / totalTests) * 100).toFixed(1)}%`);

// Show failures
if (failures.length > 0) {
    console.log('\n❌ Failed Tests:\n');
    failures.forEach((failure, index) => {
        console.log(`${index + 1}. Config: ${failure.config}`);
        console.log(`   Options: ${JSON.stringify(failure.options)}`);
        if (failure.error) {
            console.log(`   Error: ${failure.error}`);
        } else {
            console.log(`   Original: "${failure.original}"`);
            console.log(`   Encoded length: ${failure.encodedLength} chars`);
            console.log(`   Decoded: "${failure.decoded}"`);
            console.log(`   Decoded length: ${failure.decodedLength} chars`);
            console.log(`   Match: ${failure.original === failure.decoded ? 'YES' : 'NO'}`);
        }
        console.log('');
    });
}

// Exit with error code if tests failed
process.exit(failedTests > 0 ? 1 : 0);

