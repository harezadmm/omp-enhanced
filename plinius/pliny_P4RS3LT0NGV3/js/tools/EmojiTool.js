/**
 * Emoji Tool - Steganography/Emoji encoding tool
 */
class EmojiTool extends Tool {
    constructor() {
        super({
            id: 'steganography',
            name: 'Emoji',
            icon: 'fa-smile',
            title: 'Hide text in emojis (H)',
            order: 3
        });
    }
    
    getVueData() {
        const allEmojis = window.EmojiUtils ? window.EmojiUtils.getAllEmojis() : [];
        return {
            emojiMessage: '',
            encodedMessage: '',
            decodeInput: '',
            decodedMessage: '',
            selectedCarrier: null,
            activeSteg: null,
            carriers: window.steganography.carriers,
            filteredEmojis: [...allEmojis],
            selectedEmoji: null,
            carrierEmojiList: [...allEmojis],
            compatibleEmojis: [],
            quickCarrierEmojis: ['🐍','🐉','🐲','🔥','💥','🗿','⚓','⭐','✨','🚀','💀','🪨','🍃','🪶','🔮','🐢','🐊','🦎']
        };
    }
    
    getVueMethods() {
        const self = this;
        return {
            async initializeEmojiList() {
                if (!window.EmojiUtils) {
                    console.warn('EmojiUtils not available');
                    return;
                }
                
                this.showNotification('Checking emoji compatibility...', 'info', 'fas fa-spinner fa-spin');
                
                const progressCallback = (tested, total, compatible) => {
                    if (tested % 500 === 0 || tested === total) {
                        const percent = ((tested / total) * 100).toFixed(0);
                        console.log(`Emoji compatibility: ${percent}% (${compatible} compatible so far)`);
                    }
                };
                
                const compatible = await window.EmojiUtils.getCompatibleEmojis(progressCallback);
                this.compatibleEmojis = compatible;
                this.filteredEmojis = [...compatible];
                this.carrierEmojiList = [...compatible];
                this.emojiListInitialized = true;
                
                this.showNotification(`${compatible.length} compatible emojis loaded`, 'success', 'fas fa-check');
                
                if (this.activeTab === 'steganography') {
                    this.$nextTick(() => {
                        this.renderEmojiGrid();
                    });
                }
            },
            selectCarrier: function(carrier) {
                if (this.selectedCarrier === carrier) {
                    this.selectedCarrier = null;
                    this.encodedMessage = '';
                } else {
                    this.selectedCarrier = carrier;
                    this.activeSteg = 'emoji';
                    this.autoEncode();
                }
            },
            setStegMode: function(mode) {
                if (mode === 'invisible') {
                    this.activeSteg = mode;
                    this.selectedCarrier = null;
                    this.autoEncode();
                    
                    if (this.encodedMessage) {
                        this.$nextTick(() => {
                            this.forceCopyToClipboard(this.encodedMessage);
                            this.showNotification('Invisible text created and copied!', 'success', 'fas fa-check');
                        });
                    }
                } else {
                    if (this.activeSteg === mode) {
                        this.activeSteg = null;
                        this.encodedMessage = '';
                    } else {
                        this.activeSteg = mode;
                        this.autoEncode();
                    }
                }
            },
            autoEncode: function() {
                if (!this.emojiMessage || this.activeTab !== 'steganography') {
                    this.encodedMessage = '';
                    return;
                }
                
                if (this.activeSteg === 'invisible') {
                    this.encodedMessage = window.steganography.encodeInvisible(this.emojiMessage);
                } else if (this.selectedCarrier) {
                    this.encodedMessage = window.steganography.encodeEmoji(
                        this.selectedCarrier.emoji,
                        this.emojiMessage
                    );
                }
            },
            selectEmoji: function(emoji) {
                const emojiStr = String(emoji);
                
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(emojiStr)
                        .then(() => {
                            this.showNotification('Emoji copied!', 'success', 'fas fa-check');
                            this.addToCopyHistory('Emoji', emojiStr);
                        })
                        .catch(err => {
                            console.warn('Emoji clipboard API failed:', err);
                            this.forceCopyToClipboard(emojiStr);
                            this.showNotification('Emoji copied!', 'success', 'fas fa-check');
                        });
                } else {
                    this.forceCopyToClipboard(emojiStr);
                    this.showNotification('Emoji copied!', 'success', 'fas fa-check');
                }
                
                if (this.activeTab === 'steganography') {
                    this.selectedEmoji = emoji;
                    
                    const tempCarrier = {
                        name: `${emoji} Carrier`,
                        emoji: emoji,
                        encode: (text) => this.steganography.encode(text, emoji),
                        decode: (text) => this.steganography.decode(text),
                        preview: (text) => `${emoji}${text}${emoji}`
                    };
                    
                    this.selectedCarrier = tempCarrier;
                    this.activeSteg = 'emoji';
                    
                    if (this.emojiMessage) {
                        this.autoEncode();
                        
                        this.$nextTick(() => {
                            if (this.encodedMessage) {
                                const encodedStr = String(this.encodedMessage);
                                
                                if (navigator.clipboard && navigator.clipboard.writeText) {
                                    navigator.clipboard.writeText(encodedStr)
                                        .then(() => {
                                            this.showNotification(`Hidden message copied with ${emoji}`, 'success', 'fas fa-check');
                                            this.addToCopyHistory(`Hidden Message with ${emoji}`, encodedStr);
                                        })
                                        .catch(err => {
                                            console.warn('Encoded emoji clipboard API failed:', err);
                                            this.forceCopyToClipboard(encodedStr);
                                            this.showNotification(`Hidden message copied with ${emoji}`, 'success', 'fas fa-check');
                                        });
                                } else {
                                    this.forceCopyToClipboard(encodedStr);
                                    this.showNotification(`Hidden message copied with ${emoji}`, 'success', 'fas fa-check');
                                }
                            }
                        });
                    }
                }
            },
            renderEmojiGrid: function() {
                const container = document.getElementById('emoji-grid-container');
                if (!container) {
                    console.error('emoji-grid-container not found!');
                    return;
                }
                
                container.style.cssText = 'display: block !important; visibility: visible !important; min-height: 300px;';
                
                const emojiLibrary = document.querySelector('.emoji-library');
                if (emojiLibrary) {
                    emojiLibrary.style.cssText = 'display: block !important; visibility: visible !important;';
                }
                
                while (container.firstChild) {
                    container.removeChild(container.firstChild);
                }
                
                this._renderEmojiGridInternal('emoji-grid-container', this.selectEmoji.bind(this), this.filteredEmojis);
            },
            _renderEmojiGridInternal: function(containerId, onEmojiSelect, filteredList) {
                const container = document.getElementById(containerId);
                if (!container) {
                    console.error('Container not found:', containerId);
                    return;
                }
                
                const categories = window.emojiData && window.emojiData.categories ? window.emojiData.categories : [];
                
                const emojiHeader = document.createElement('div');
                emojiHeader.className = 'emoji-header';
                
                const headerTitle = document.createElement('h3');
                const icon = document.createElement('i');
                icon.className = 'fas fa-icons';
                headerTitle.appendChild(icon);
                headerTitle.appendChild(document.createTextNode(' Choose an Emoji'));
                
                const subtitle = document.createElement('p');
                subtitle.className = 'emoji-subtitle';
                const magicIcon = document.createElement('i');
                magicIcon.className = 'fas fa-magic';
                subtitle.appendChild(magicIcon);
                subtitle.appendChild(document.createTextNode(' Click any emoji to copy your hidden message'));
                
                emojiHeader.appendChild(headerTitle);
                emojiHeader.appendChild(subtitle);
                container.appendChild(emojiHeader);
                
                const categoryTabs = document.createElement('div');
                categoryTabs.className = 'emoji-category-tabs';
                
                categories.forEach(category => {
                    const tab = document.createElement('button');
                    tab.className = 'emoji-category-tab';
                    if (category.id === 'all') {
                        tab.classList.add('active');
                    }
                    tab.setAttribute('data-category', category.id);
                    tab.textContent = `${category.icon} ${category.name}`;
                    categoryTabs.appendChild(tab);
                });
                
                container.appendChild(categoryTabs);
                
                const gridContainer = document.createElement('div');
                gridContainer.className = 'emoji-grid';
                
                let activeCategory = 'all';
                const activeCategoryTab = container.querySelector('.emoji-category-tab.active');
                if (activeCategoryTab) {
                    activeCategory = activeCategoryTab.getAttribute('data-category');
                }
                
                let emojisToShow = [];
                if (filteredList && filteredList.length > 0) {
                    emojisToShow = filteredList;
                } else if (window.emojiData && typeof window.emojiData.getByCategory === 'function') {
                    emojisToShow = window.emojiData.getByCategory(activeCategory, false);
                }
                
                const emojisToRender = emojisToShow.filter(emoji => {
                    if (this.compatibleEmojis && this.compatibleEmojis.length > 0) {
                        return this.compatibleEmojis.includes(emoji);
                    }
                    if (window.emojiCompatibility && typeof window.emojiCompatibility.shouldShowInPicker === 'function') {
                        return window.emojiCompatibility.shouldShowInPicker(emoji);
                    }
                    return true;
                });
                
                emojisToRender.forEach(emoji => {
                    const emojiButton = document.createElement('button');
                    emojiButton.className = 'emoji-button';
                    emojiButton.textContent = emoji;
                    emojiButton.title = 'Click to encode with this emoji';
                    
                    emojiButton.addEventListener('click', () => {
                        if (typeof onEmojiSelect === 'function') {
                            onEmojiSelect(emoji);
                            emojiButton.style.backgroundColor = '#e6f7ff';
                            setTimeout(() => {
                                emojiButton.style.backgroundColor = '';
                            }, 300);
                        }
                    });
                    
                    gridContainer.appendChild(emojiButton);
                });
                
                container.appendChild(gridContainer);
                
                const categoryTabButtons = container.querySelectorAll('.emoji-category-tab');
                categoryTabButtons.forEach(tab => {
                    tab.addEventListener('click', () => {
                        categoryTabButtons.forEach(t => t.classList.remove('active'));
                        tab.classList.add('active');
                        
                        const selectedCategory = tab.getAttribute('data-category');
                        let emojisToShow = [];
                        if (window.emojiData && typeof window.emojiData.getByCategory === 'function') {
                            emojisToShow = window.emojiData.getByCategory(selectedCategory, false);
                        }
                        
                        while (gridContainer.firstChild) {
                            gridContainer.removeChild(gridContainer.firstChild);
                        }
                        
                        const emojisToRender = emojisToShow.filter(emoji => {
                            if (this.compatibleEmojis && this.compatibleEmojis.length > 0) {
                                return this.compatibleEmojis.includes(emoji);
                            }
                            if (window.emojiCompatibility && typeof window.emojiCompatibility.shouldShowInPicker === 'function') {
                                return window.emojiCompatibility.shouldShowInPicker(emoji);
                            }
                            return true;
                        });
                        
                        emojisToRender.forEach(emoji => {
                            const emojiButton = document.createElement('button');
                            emojiButton.className = 'emoji-button';
                            emojiButton.textContent = emoji;
                            emojiButton.title = 'Click to encode with this emoji';
                            
                            emojiButton.addEventListener('click', () => {
                                if (typeof onEmojiSelect === 'function') {
                                    onEmojiSelect(emoji);
                                    emojiButton.style.backgroundColor = '#e6f7ff';
                                    setTimeout(() => {
                                        emojiButton.style.backgroundColor = '';
                                    }, 300);
                                }
                            });
                            
                            gridContainer.appendChild(emojiButton);
                        });
                        
                        const countDisplay = container.querySelector('.emoji-count');
                        if (countDisplay) {
                            countDisplay.textContent = `${emojisToShow.length} emojis available`;
                        }
                    });
                });
                
                const countDisplay = document.createElement('div');
                countDisplay.className = 'emoji-count';
                countDisplay.textContent = `${emojisToShow.length} emojis available`;
                container.appendChild(countDisplay);
            },
            filterEmojis: function() {
                const allEmojis = window.EmojiUtils ? window.EmojiUtils.getAllEmojis() : [];
                this.filteredEmojis = this.compatibleEmojis.length > 0 ? [...this.compatibleEmojis] : [...allEmojis];
                this.renderEmojiGrid();
            }
        };
    }
    
    getVueLifecycle() {
        return {
            mounted() {
                this.initializeEmojiList();
                
                this.$nextTick(() => {
                    const allEmojis = window.EmojiUtils ? window.EmojiUtils.getAllEmojis() : [];
                    this.filteredEmojis = this.compatibleEmojis.length > 0 ? [...this.compatibleEmojis] : [...allEmojis];
                    
                    const initializeEmojiGrid = () => {
                        if (this.activeTab !== 'steganography') {
                            return;
                        }
                        
                        const emojiGridContainer = document.getElementById('emoji-grid-container');
                        if (emojiGridContainer) {
                            emojiGridContainer.setAttribute('style', 'display: block !important; visibility: visible !important; min-height: 300px; padding: 10px;');
                            
                            const emojiLibrary = document.querySelector('.emoji-library');
                            if (emojiLibrary) {
                                emojiLibrary.setAttribute('style', 'display: block !important; visibility: visible !important; margin-top: 20px; overflow: visible;');
                            }
                            
                            this.renderEmojiGrid();
                            clearInterval(emojiGridInitializer);
                        }
                    };
                    
                    const emojiGridInitializer = setInterval(initializeEmojiGrid, 500);
                });
            }
        };
    }
    
    onActivate(vueInstance) {
        vueInstance.$nextTick(() => {
            const emojiGridContainer = document.getElementById('emoji-grid-container');
            if (emojiGridContainer) {
                emojiGridContainer.setAttribute('style', 'display: block !important; visibility: visible !important; min-height: 300px; padding: 10px;');
                vueInstance.renderEmojiGrid();
            }
        });
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = EmojiTool;
} else {
    window.EmojiTool = EmojiTool;
}
