/**
 * Codes Tool — generate and decode QR codes and barcodes.
 */
class CodesTool extends Tool {
    constructor() {
        super({
            id: 'codes',
            name: 'Codes',
            icon: 'fa-qrcode',
            title: 'QR codes and barcodes',
            order: 9
        });
    }

    getVueData() {
        return {
            codesMode: 'generate',
            codesFormat: 'qr',
            codesInput: '',
            codesQrSize: 256,
            codesQrMargin: 2,
            codesQrEcl: 'M',
            codesBarcodeHeight: 80,
            codesBarcodeWidth: 2,
            codesBarcodeDisplayValue: true,
            codesOutputUrl: '',
            codesOutputSvg: '',
            codesError: '',
            codesDecodeResult: '',
            codesDecodeFormat: '',
            codesDecodeError: '',
            codesDecodeLoading: false,
            codesDecodePreview: ''
        };
    }

    getVueMethods() {
        return {
            codesFormatLabel: function(format) {
                var labels = {
                    qr: 'QR Code',
                    code128: 'Code 128',
                    ean13: 'EAN-13',
                    code39: 'Code 39'
                };
                return labels[format] || format;
            },
            codesValidateGenerateInput: function() {
                var text = String(this.codesInput || '').trim();
                if (!text) {
                    return 'Enter text or data to encode.';
                }
                if (this.codesFormat === 'ean13') {
                    var digits = text.replace(/\D/g, '');
                    if (!digits.length) {
                        return 'EAN-13 requires digits only (12 or 13 digits). Letters and symbols are not valid.';
                    }
                    if (digits.length < 12 || digits.length > 13) {
                        return 'EAN-13 requires 12 or 13 digits (check digit is calculated automatically for 12).';
                    }
                }
                if (this.codesFormat === 'code39' && !/^[0-9A-Z\s\-\.\$\/\+\%]+$/.test(text.toUpperCase())) {
                    return 'Code 39 supports A–Z, 0–9, space, and - . $ / + %.';
                }
                return '';
            },
            codesClearOutput: function() {
                this.codesOutputUrl = '';
                this.codesOutputSvg = '';
            },
            codesResetGenerate: function() {
                this.codesClearOutput();
                this.codesError = '';
            },
            codesGenerate: function() {
                var validationError = this.codesValidateGenerateInput();
                if (validationError) {
                    this.codesClearOutput();
                    this.codesError = validationError;
                    return;
                }

                this.codesError = '';
                this.codesClearOutput();

                var text = String(this.codesInput || '').trim();
                if (this.codesFormat === 'ean13') {
                    if (typeof Ean13Utils === 'undefined' || typeof Ean13Utils.normalize !== 'function') {
                        this.codesError = 'EAN-13 helpers not loaded. Rebuild the app (npm run build).';
                        return;
                    }
                    var ean13 = Ean13Utils.normalize(text);
                    if (!ean13.ok) {
                        this.codesError = ean13.error;
                        return;
                    }
                    text = ean13.value;
                }
                if (this.codesFormat === 'code39') {
                    text = text.toUpperCase();
                }

                var self = this;

                if (this.codesFormat === 'qr') {
                    if (typeof window.QRCode === 'undefined' || typeof window.QRCode.toDataURL !== 'function') {
                        this.codesError = 'QR library not loaded. Rebuild the app (npm run build).';
                        return;
                    }
                    window.QRCode.toDataURL(text, {
                        width: Math.max(128, Math.min(1024, Number(this.codesQrSize) || 256)),
                        margin: Math.max(0, Math.min(20, Number(this.codesQrMargin) || 2)),
                        errorCorrectionLevel: this.codesQrEcl || 'M'
                    }).then(function(url) {
                        self.codesOutputUrl = url;
                        if (typeof self.showNotification === 'function') {
                            self.showNotification('QR code generated', 'success', 'fas fa-qrcode');
                        }
                    }).catch(function(err) {
                        self.codesError = (err && err.message) || 'Failed to generate QR code.';
                    });
                    return;
                }

                if (typeof window.JsBarcode === 'undefined') {
                    this.codesError = 'Barcode library not loaded. Rebuild the app (npm run build).';
                    return;
                }

                try {
                    var formatMap = {
                        code128: 'CODE128',
                        ean13: 'EAN13',
                        code39: 'CODE39'
                    };
                    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                    window.JsBarcode(svg, text, {
                        format: formatMap[this.codesFormat] || 'CODE128',
                        displayValue: !!this.codesBarcodeDisplayValue,
                        height: Math.max(40, Math.min(200, Number(this.codesBarcodeHeight) || 80)),
                        width: Math.max(1, Math.min(4, Number(this.codesBarcodeWidth) || 2)),
                        margin: 10
                    });
                    var svgMarkup = new XMLSerializer().serializeToString(svg);
                    this.codesOutputSvg = svgMarkup;
                    this.codesOutputUrl = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgMarkup);
                    if (typeof this.showNotification === 'function') {
                        this.showNotification(this.codesFormatLabel(this.codesFormat) + ' generated', 'success', 'fas fa-barcode');
                    }
                } catch (err) {
                    this.codesError = (err && err.message) || 'Failed to generate barcode.';
                }
            },
            codesRasterizeToPng: function(imageUrl) {
                return new Promise(function(resolve, reject) {
                    var img = new Image();
                    img.onload = function() {
                        var canvas = document.createElement('canvas');
                        canvas.width = img.naturalWidth || img.width;
                        canvas.height = img.naturalHeight || img.height;
                        var ctx = canvas.getContext('2d');
                        ctx.fillStyle = '#ffffff';
                        ctx.fillRect(0, 0, canvas.width, canvas.height);
                        ctx.drawImage(img, 0, 0);
                        resolve(canvas.toDataURL('image/png'));
                    };
                    img.onerror = function() {
                        reject(new Error('Failed to render barcode image.'));
                    };
                    img.src = imageUrl;
                });
            },
            codesCopyImage: function() {
                var self = this;
                if (!this.codesOutputUrl) {
                    return;
                }
                if (!navigator.clipboard || typeof navigator.clipboard.write !== 'function') {
                    this.codesError = 'Image copy is not supported in this browser.';
                    return;
                }

                var blobPromise;
                if (this.codesOutputUrl.indexOf('data:image/png') === 0) {
                    blobPromise = fetch(this.codesOutputUrl).then(function(response) {
                        return response.blob();
                    });
                } else {
                    blobPromise = this.codesRasterizeToPng(this.codesOutputUrl).then(function(pngUrl) {
                        return fetch(pngUrl).then(function(response) {
                            return response.blob();
                        });
                    });
                }

                blobPromise.then(function(blob) {
                    return navigator.clipboard.write([
                        new ClipboardItem({ 'image/png': blob })
                    ]);
                }).then(function() {
                    if (typeof self.showNotification === 'function') {
                        self.showNotification('Image copied to clipboard', 'success', 'fas fa-copy');
                    }
                }).catch(function(err) {
                    self.codesError = (err && err.message) || 'Failed to copy image to clipboard.';
                });
            },
            codesDownload: function() {
                if (!this.codesOutputUrl) {
                    return;
                }
                var ext = this.codesFormat === 'qr' ? 'png' : 'svg';
                var link = document.createElement('a');
                link.href = this.codesOutputUrl;
                link.download = 'code-' + this.codesFormat + '.' + ext;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                if (typeof this.showNotification === 'function') {
                    this.showNotification('Download started', 'success', 'fas fa-download');
                }
            },
            codesCopyOutput: function() {
                if (!this.codesInput.trim()) {
                    return;
                }
                if (typeof this.copyToClipboard === 'function') {
                    this.copyToClipboard(this.codesInput);
                } else if (navigator.clipboard) {
                    navigator.clipboard.writeText(this.codesInput);
                }
            },
            codesResetDecode: function() {
                this.codesDecodeResult = '';
                this.codesDecodeFormat = '';
                this.codesDecodeError = '';
                this.codesDecodePreview = '';
                this.codesDecodeLoading = false;
            },
            codesHandleFileUpload: function(event) {
                var file = event && event.target && event.target.files && event.target.files[0];
                if (!file) {
                    return;
                }
                this.codesDecodeFromFile(file);
                event.target.value = '';
            },
            codesDecodeFromFile: function(file) {
                var self = this;
                if (!file || !file.type.match(/^image\//)) {
                    this.codesDecodeError = 'Choose a PNG, JPEG, GIF, or WebP image.';
                    return;
                }
                if (typeof window.ZXing === 'undefined' || !window.ZXing.BrowserMultiFormatReader) {
                    this.codesDecodeError = 'Scanner library not loaded. Rebuild the app (npm run build).';
                    return;
                }

                this.codesDecodeLoading = true;
                this.codesDecodeError = '';
                this.codesDecodeResult = '';
                this.codesDecodeFormat = '';

                var reader = new FileReader();
                reader.onload = function(loadEvent) {
                    self.codesDecodePreview = loadEvent.target.result;
                    self.codesScanImage(loadEvent.target.result);
                };
                reader.onerror = function() {
                    self.codesDecodeLoading = false;
                    self.codesDecodeError = 'Could not read that file.';
                };
                reader.readAsDataURL(file);
            },
            codesScanImage: function(dataUrl) {
                var self = this;
                var codeReader = new window.ZXing.BrowserMultiFormatReader();

                codeReader.decodeFromImageUrl(dataUrl).then(function(result) {
                    self.codesDecodeResult = result.getText();
                    self.codesDecodeFormat = result.getBarcodeFormat
                        ? String(result.getBarcodeFormat())
                        : 'unknown';
                    self.codesDecodeError = '';
                    if (typeof self.showNotification === 'function') {
                        self.showNotification('Code decoded', 'success', 'fas fa-search');
                    }
                }).catch(function() {
                    self.codesDecodeResult = '';
                    self.codesDecodeFormat = '';
                    self.codesDecodeError = 'No QR code or barcode found in that image.';
                }).finally(function() {
                    self.codesDecodeLoading = false;
                    codeReader.reset();
                });
            },
            codesUseDecodedText: function() {
                if (!this.codesDecodeResult) {
                    return;
                }
                this.codesMode = 'generate';
                this.codesInput = this.codesDecodeResult;
                if (typeof this.showNotification === 'function') {
                    this.showNotification('Copied decoded text to Generate tab', 'success', 'fas fa-arrow-right');
                }
            }
        };
    }

    getVueWatchers() {
        return {
            codesMode: function(mode) {
                this.codesError = '';
                if (this.activeTab === 'codes' && window.TabRouting) {
                    window.TabRouting.setHash('codes', mode === 'decode' ? 'decode' : '');
                }
            },
            codesFormat: function() {
                this.codesResetGenerate();
            }
        };
    }

    onActivate(vueInstance) {
        vueInstance.codesError = '';
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = CodesTool;
} else {
    window.CodesTool = CodesTool;
}
