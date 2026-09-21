#!/usr/bin/env node

/**
 * Build Emoji Data from Official Unicode Source
 * Fetches emoji-test.txt from Unicode.org and generates emojiData.js
 */

const https = require('https');
const fs = require('fs');
const path = require('path');

// Unicode emoji test file (always uses latest version - compatibility testing handles older devices)
// URL automatically redirects to newest Unicode emoji release
const EMOJI_DATA_URL = 'https://www.unicode.org/Public/emoji/latest/emoji-test.txt';
const CACHE_DIR = path.join(__dirname, '..', '.cache');
const CACHE_FILE = path.join(CACHE_DIR, 'emoji-test.txt');
const CACHE_MAX_AGE = 7 * 24 * 60 * 60 * 1000; // 7 days in milliseconds

// Check for --force flag to bypass cache
const FORCE_DOWNLOAD = process.argv.includes('--force') || process.argv.includes('-f');

const startTime = Date.now();

/**
 * Check if cached file exists and is recent enough
 */
function shouldUseCache() {
    if (FORCE_DOWNLOAD) {
        console.log('🔄 Force download requested, bypassing cache...');
        return false;
    }
    
    if (!fs.existsSync(CACHE_FILE)) {
        return false;
    }
    
    const stats = fs.statSync(CACHE_FILE);
    const age = Date.now() - stats.mtimeMs;
    
    if (age > CACHE_MAX_AGE) {
        console.log(`⏰ Cache is ${Math.floor(age / (24 * 60 * 60 * 1000))} days old, will refresh...`);
        return false;
    }
    
    return true;
}

/**
 * Download emoji data from Unicode.org
 */
function downloadEmojiData(callback) {
    console.log('📥 Downloading emoji data from Unicode.org...');
    console.log(`   Source: ${EMOJI_DATA_URL}`);
    
    https.get(EMOJI_DATA_URL, (response) => {
        let data = '';
        let downloadedBytes = 0;
        const totalBytes = parseInt(response.headers['content-length'] || '0', 10);
        
        response.on('data', (chunk) => {
            data += chunk;
            downloadedBytes += chunk.length;
            
            // Show progress if we know the total size
            if (totalBytes > 0) {
                const percent = ((downloadedBytes / totalBytes) * 100).toFixed(1);
                process.stdout.write(`\r   Progress: ${percent}% (${(downloadedBytes / 1024).toFixed(0)} KB)`);
            }
        });
        
        response.on('end', () => {
            const downloadTime = ((Date.now() - startTime) / 1000).toFixed(2);
            console.log(`\n✅ Downloaded ${(data.length / 1024).toFixed(2)} KB in ${downloadTime}s`);
            
            // Save to cache
            if (!fs.existsSync(CACHE_DIR)) {
                fs.mkdirSync(CACHE_DIR, { recursive: true });
            }
            fs.writeFileSync(CACHE_FILE, data, 'utf8');
            console.log(`💾 Cached to ${CACHE_FILE}`);
            
            callback(data, downloadTime);
        });
    }).on('error', (err) => {
        console.error('❌ Error fetching emoji data:', err.message);
        process.exit(1);
    });
}

/**
 * Load emoji data from cache or download if needed
 */
function loadEmojiData() {
    if (shouldUseCache()) {
        console.log('📂 Using cached emoji data...');
        const stats = fs.statSync(CACHE_FILE);
        const age = Math.floor((Date.now() - stats.mtimeMs) / (60 * 60 * 1000));
        console.log(`   Cache age: ${age} hours`);
        
        const data = fs.readFileSync(CACHE_FILE, 'utf8');
        const loadTime = ((Date.now() - startTime) / 1000).toFixed(2);
        console.log(`✅ Loaded ${(data.length / 1024).toFixed(2)} KB from cache in ${loadTime}s`);
        
        processEmojiData(data, '0.00');
    } else {
        downloadEmojiData((data, downloadTime) => {
            processEmojiData(data, downloadTime);
        });
    }
}

/**
 * Process emoji data (parse and generate)
 */
function processEmojiData(data, downloadTime) {
    // Parse the emoji data
    console.log('🔨 Parsing emoji data...');
    const parseStart = Date.now();
    const emojiData = parseEmojiTestFile(data);
    const parseTime = ((Date.now() - parseStart) / 1000).toFixed(2);
    console.log(`✅ Parsed ${Object.keys(emojiData).length} emojis in ${parseTime}s`);
    
    // Generate JavaScript file
    console.log('📝 Generating emojiData.js...');
    const genStart = Date.now();
    generateEmojiDataFile(emojiData);
    const genTime = ((Date.now() - genStart) / 1000).toFixed(2);
    
    const totalTime = ((Date.now() - startTime) / 1000).toFixed(2);
    console.log(`\n⏱️  Total time: ${totalTime}s (download: ${downloadTime}s, parse: ${parseTime}s, generate: ${genTime}s)`);
}

// Start loading emoji data
loadEmojiData();

/**
 * Check if an emoji has complex modifiers (skin tones, ZWJ sequences, etc.)
 * Currently disabled - we want to use the full Unicode 15.1 set
 */
function hasComplexModifiers(emoji, name) {
    // Mark all emojis as simple (no filtering)
    return false;
}

/**
 * Parse the emoji-test.txt file format
 * Format: <codepoints> ; <status> # <emoji> <version> <name>
 */
function parseEmojiTestFile(content) {
    const lines = content.split('\n');
    const emojis = {};
    let currentGroup = '';
    let currentSubgroup = '';
    
    for (const line of lines) {
        // Parse group headers
        if (line.startsWith('# group:')) {
            currentGroup = line.replace('# group:', '').trim();
            continue;
        }
        
        // Parse subgroup headers
        if (line.startsWith('# subgroup:')) {
            currentSubgroup = line.replace('# subgroup:', '').trim();
            continue;
        }
        
        // Skip comments and empty lines
        if (line.startsWith('#') || !line.trim() || !line.includes(';')) {
            continue;
        }
        
        // Parse emoji line
        // Format: 1F600 ; fully-qualified # 😀 E1.0 grinning face
        // Or: 1F64D 1F3FD 200D 2642 FE0F ; fully-qualified # 🙍🏽‍♂️ E2.0 man frowning: medium skin tone
        
        // Extract codepoints from the left side (more reliable than character representation)
        const codepointMatch = line.match(/^([0-9A-Fa-f\s]+)\s*;\s*(fully-qualified|minimally-qualified|unqualified)/);
        let emoji = null;
        
        if (codepointMatch) {
            // Reconstruct emoji from codepoints to avoid corruption issues
            const codepoints = codepointMatch[1].trim().split(/\s+/)
                .map(cp => parseInt(cp, 16))
                .filter(cp => !isNaN(cp));
            
            if (codepoints.length > 0) {
                // Convert codepoints to emoji string
                emoji = String.fromCodePoint(...codepoints);
            }
        }
        
        // Fallback: extract from character representation if codepoint parsing fails
        if (!emoji) {
            const parts = line.split('#');
            if (parts.length < 2) continue;
            
            const emojiPart = parts[1].trim();
            const match = emojiPart.match(/^(.+?)\s+E\d+\.\d+\s+(.+)$/);
            
            if (match) {
                emoji = match[1].trim();
            } else {
                continue;
            }
        }
        
        // Extract name from the line
        const nameMatch = line.match(/#\s+.+?\s+E\d+\.\d+\s+(.+)$/);
        const name = nameMatch ? nameMatch[1].trim() : '';
        
        if (emoji && name) {
            
            // Only include fully-qualified emojis
            if (line.includes('fully-qualified')) {
                // Filter out overly complex sequences for better UX
                const isSimple = !hasComplexModifiers(emoji, name);
                
                emojis[emoji] = {
                    official: name,
                    group: currentGroup,
                    subgroup: currentSubgroup,
                    keywords: generateKeywords(name, currentGroup, currentSubgroup),
                    isSimple: isSimple
                };
            }
        }
    }
    
    return emojis;
}

/**
 * Generate keywords from the official emoji name
 */
function generateKeywords(name, group, subgroup) {
    const keywords = new Set();
    
    // Add words from the official name
    const nameWords = name.toLowerCase()
        .replace(/[()]/g, '')
        .split(/[\s-]+/)
        .filter(word => word.length > 2 && !['with', 'and', 'the'].includes(word));
    
    nameWords.forEach(word => keywords.add(word));
    
    // Add group/subgroup as keywords
    if (group) {
        const groupWords = group.toLowerCase().split(/[\s&-]+/);
        groupWords.forEach(word => {
            if (word.length > 3) keywords.add(word);
        });
    }
    
    // Special keyword mappings for common words
    const keywordMap = {
        'grinning': ['smile', 'happy', 'grin'],
        'tears of joy': ['laugh', 'lol', 'funny'],
        'heart': ['love', 'like'],
        'thumbs up': ['good', 'yes', 'approve', 'like'],
        'thumbs down': ['bad', 'no', 'disapprove'],
        'waving': ['hello', 'hi', 'bye', 'wave'],
        'clapping': ['applause', 'clap', 'praise'],
        'folded': ['pray', 'thanks', 'please'],
        'fire': ['hot', 'lit', 'flame'],
        'crying': ['sad', 'tear', 'cry'],
        'skull': ['dead', 'death'],
        'poop': ['shit', 'crap', 'poo'],
        'hundred': ['100', 'perfect'],
        'collision': ['boom', 'bang', 'explosion'],
        'dog': ['puppy', 'pet'],
        'cat': ['kitty', 'pet'],
        'sun': ['sunny', 'day'],
        'moon': ['night'],
        'star': ['favorite'],
        'rainbow': ['pride', 'colorful']
    };
    
    // Add mapped keywords
    for (const [trigger, extras] of Object.entries(keywordMap)) {
        if (name.toLowerCase().includes(trigger)) {
            extras.forEach(k => keywords.add(k));
        }
    }
    
    return Array.from(keywords);
}

/**
 * Map Unicode groups to category IDs (using official Unicode categories)
 * Split "People & Body" into subcategories for better organization
 */
function mapGroupToCategory(group, subgroup) {
    const groupMap = {
        'Smileys & Emotion': 'smileys_emotion',
        'Animals & Nature': 'animals_nature',
        'Food & Drink': 'food_drink',
        'Travel & Places': 'travel_places',
        'Activities': 'activities',
        'Objects': 'objects',
        'Symbols': 'symbols',
        'Flags': 'flags'
    };
    
    // Special handling for People & Body - split into subcategories
    if (group === 'People & Body') {
        // Hands and gestures
        if (subgroup.startsWith('hand-') || subgroup === 'hands' || subgroup === 'hand-prop') {
            return 'people_hands';
        }
        // Body parts
        if (subgroup === 'body-parts') {
            return 'people_body_parts';
        }
        // People (person-*, person, family)
        if (subgroup.startsWith('person-') || subgroup === 'person' || subgroup === 'family' || subgroup === 'person-symbol') {
            return 'people_persons';
        }
        // Default to people_body if subgroup doesn't match
        return 'people_body';
    }
    
    return groupMap[group] || 'symbols';
}

/**
 * Load keyword mappings from emojiWordMap.js
 */
function loadEmojiWordMap() {
    const wordMapPath = path.join(__dirname, '..', 'src', 'emojiWordMap.js');
    
    if (!fs.existsSync(wordMapPath)) {
        console.log('⚠️  emojiWordMap.js not found, skipping keyword merge');
        return {};
    }
    
    try {
        const code = fs.readFileSync(wordMapPath, 'utf8');
        
        // Use vm to safely execute the file and extract emojiKeywords
        const vm = require('vm');
        const sandbox = { 
            window: {},
            console: console // Allow console in case the file uses it
        };
        vm.createContext(sandbox);
        
        // Execute the entire file in the sandbox
        vm.runInContext(code, sandbox);
        
        const keywordMap = sandbox.window.emojiKeywords || {};
        console.log(`📚 Loaded ${Object.keys(keywordMap).length} keyword mappings from emojiWordMap.js`);
        
        return keywordMap;
    } catch (error) {
        console.log(`⚠️  Error loading emojiWordMap.js: ${error.message}, skipping keyword merge`);
        return {};
    }
}

/**
 * Merge keywords from wordMap into emojiData keywords
 */
function mergeKeywords(baseKeywords, wordMapKeywords) {
    const merged = new Set(baseKeywords);
    
    // Add all keywords from wordMap
    if (Array.isArray(wordMapKeywords)) {
        wordMapKeywords.forEach(kw => merged.add(kw.toLowerCase()));
    }
    
    return Array.from(merged).sort();
}

/**
 * Generate the emojiData.js file
 */
function generateEmojiDataFile(emojiData) {
    const outputPath = path.join(__dirname, '..', 'dist', 'js', 'data', 'emojiData.js');
    
    // Ensure data directory exists
    const dataDir = path.dirname(outputPath);
    if (!fs.existsSync(dataDir)) {
        fs.mkdirSync(dataDir, { recursive: true });
    }
    
    // Load keyword mappings from emojiWordMap.js
    console.log('📚 Loading keyword mappings from emojiWordMap.js...');
    const wordMap = loadEmojiWordMap();
    
    let output = `// Unified Emoji Data for P4RS3LT0NGV3
// Generated from Unicode Official Emoji Data (latest version with compatibility testing)
// Keywords merged from emojiWordMap.js for enhanced searchability
// Source: ${EMOJI_DATA_URL}
// Generated: ${new Date().toISOString()}

window.emojiData = {
`;
    
    let mergedCount = 0;
    
    // Add each emoji
    for (const [emoji, data] of Object.entries(emojiData)) {
        const category = mapGroupToCategory(data.group, data.subgroup);
        
        // Merge keywords from wordMap if available
        let finalKeywords = data.keywords;
        if (wordMap[emoji]) {
            finalKeywords = mergeKeywords(data.keywords, wordMap[emoji]);
            mergedCount++;
        }
        
        const keywordsStr = JSON.stringify(finalKeywords);
        const isSimple = data.isSimple ? 'true' : 'false';
        
        output += `    '${emoji}': { official: '${data.official.replace(/'/g, "\\'")}', keywords: ${keywordsStr}, category: '${category}', isSimple: ${isSimple} },\n`;
    }
    
    if (mergedCount > 0) {
        console.log(`✅ Merged keywords for ${mergedCount} emojis from emojiWordMap.js`);
    }
    
    output += `};

// Helper to get all emojis by category (optionally filter to simple emojis only)
window.emojiData.getByCategory = function(categoryId, simpleOnly = false) {
    let emojis = categoryId === 'all' 
        ? Object.keys(window.emojiData).filter(key => typeof window.emojiData[key] === 'object')
        : Object.entries(window.emojiData)
            .filter(([emoji, data]) => typeof data === 'object' && data.category === categoryId)
            .map(([emoji]) => emoji);
    
    // Filter to simple emojis if requested (better for UI display)
    if (simpleOnly) {
        emojis = emojis.filter(emoji => window.emojiData[emoji]?.isSimple);
    }
    
    return emojis;
};

// Helper to search emojis by keyword
window.emojiData.searchByKeyword = function(keyword) {
    const lowerKeyword = keyword.toLowerCase();
    return Object.entries(window.emojiData)
        .filter(([emoji, data]) => 
            typeof data === 'object' && (
                data.official.toLowerCase().includes(lowerKeyword) ||
                data.keywords.some(kw => kw.toLowerCase().includes(lowerKeyword))
            )
        )
        .map(([emoji]) => emoji);
};

// Helper to get emoji by keyword (for encoding)
window.emojiData.getEmojiForWord = function(word) {
    const lowerWord = word.toLowerCase();
    const matches = Object.entries(window.emojiData)
        .filter(([emoji, data]) => 
            typeof data === 'object' && data.keywords.includes(lowerWord)
        )
        .map(([emoji]) => emoji);
    
    // Return random match if multiple found
    return matches.length > 0 ? matches[Math.floor(Math.random() * matches.length)] : null;
};

// Categories for UI (official Unicode 15.1 categories, with People & Body split)
window.emojiData.categories = [
    { id: 'all', name: 'All Emojis', icon: '🔍' },
    { id: 'smileys_emotion', name: 'Smileys & Emotion', icon: '😀' },
    { id: 'people_hands', name: 'Hands & Gestures', icon: '👋' },
    { id: 'people_persons', name: 'People', icon: '👤' },
    { id: 'people_body_parts', name: 'Body Parts', icon: '🦵' },
    { id: 'animals_nature', name: 'Animals & Nature', icon: '🐶' },
    { id: 'food_drink', name: 'Food & Drink', icon: '🍕' },
    { id: 'travel_places', name: 'Travel & Places', icon: '✈️' },
    { id: 'activities', name: 'Activities', icon: '⚽' },
    { id: 'objects', name: 'Objects', icon: '💡' },
    { id: 'symbols', name: 'Symbols', icon: '❤️' },
    { id: 'flags', name: 'Flags', icon: '🏁' }
];
`;
    
    // Write the file
    fs.writeFileSync(outputPath, output, 'utf8');
    
    const emojiCount = Object.keys(emojiData).length;
    const fileSize = (output.length / 1024).toFixed(2);
    
    console.log(`✅ Generated ${emojiCount} emojis → ${fileSize} KB`);
}
