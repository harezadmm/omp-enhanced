# CVE-2025-3515 - WordPress File Upload RCE

## Usage

```bash
python3 exploit.py <target>
```

## Overview

**CVE-2025-3515** is a file upload vulnerability in the "Drag and Drop Multiple File Upload for Contact Form 7" WordPress plugin that allows unauthenticated attackers to upload malicious files and achieve remote code execution.

- **Plugin**: drag-and-drop-multiple-file-upload-contact-form-7
- **Affected Versions**: ≤ 1.3.8.9
- **Discovered by**: mikemyers (Wordfence)

## Technical details

### Vulnerable component
- **File**: `/inc/dnd-upload-cf7.php`
- **Function**: `dnd_upload_cf7_upload()` (line 856)

**Missing extensions in blacklist**: `.phar`, `.php5`, `.inc`

## Patch (Version 1.3.9.0) also appears to be vulnerable

### Additional findings

#### 1. File Write Operations
```php
// Line 107-108 - Potential path traversal
if ( $handle = fopen( $htaccess_file, 'w' ) ) {
    fwrite( $handle, "Options -Indexes \n <Files *.php> \n deny from all \n </Files>" );
```

#### 2. Log File Creation
```php
// Line 523-524 - Unvalidated log writing
$file = fopen( $uploads_dir['upload_dir']."/logs.txt", "a");
fwrite( $file, "\n". ( is_array( $message ) ? print_r( $message, true ) : $message ) );
```

## Detection

### File system indicators
```bash
# Search for suspicious uploads
find /wp-content/uploads/ -name "*.phar" -o -name "*.php5" -o -name "*.inc"

# Check for web shells
grep -r "system\|exec\|shell_exec" /wp-content/uploads/
```

### Log analysis
```bash
# Apache/Nginx access logs
grep "admin-ajax.php" /var/log/apache2/access.log | grep "dnd_codedropz_upload"

# WordPress debug logs
grep "dnd_upload_cf7_upload" /wp-content/debug.log
```

## References

- [Wordfence Threat Intelligence](https://www.wordfence.com/threat-intel/vulnerabilities/id/e1298242-61d2-49c1-bae7-96b5e12bd03d)
- [WordPress Plugin Repository](https://wordpress.org/plugins/drag-and-drop-multiple-file-upload-contact-form-7/)
- [Professor6T9 PoC](https://github.com/Professor6T9/CVE-2025-3515)
