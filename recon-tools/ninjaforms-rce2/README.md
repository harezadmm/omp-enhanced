# CVE-2026-0740

<p align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/9/98/WordPress_blue_logo.svg" width="120" alt="WordPress Logo">
</p>

## 🧩 Overview

**CVE-2026-0740** is an unauthenticated arbitrary file upload vulnerability affecting:

> **Ninja Forms File Uploads ≤ 3.3.26 (WordPress plugin)**

This flaw allows attackers to upload arbitrary files to the server without authentication, potentially leading to **remote code execution (RCE)**.

---

## ⚠️ Disclaimer

This project is provided for **educational and authorized security testing purposes only**.

* Do **NOT** use this against systems you do not own or have explicit permission to test.
* The author assumes **no responsibility** for misuse or damage.

---

## ✨ Features

* Unauthenticated exploitation
* Custom file upload support
* Path traversal for controlled file placement
* Proxy (SOCKS5) support
* Custom headers support
* Colored & structured logging output

---

## 📦 Requirements

* Python 3.9+

Install dependencies:

```bash
pip install httpx httpx-socks
```

---

## 🚀 Usage

```bash
python3 CVE-2026-0740.py -t http://target.com -f shell.php
```

### Options

| Argument        | Description                       |
| --------------- | --------------------------------- |
| `-t, --target`  | Target URL                        |
| `-f, --file`    | File to upload                    |
| `-d, --dest`    | Destination path (path traversal) |
| `-x, --proxy`   | SOCKS5 proxy                      |
| `-H, --headers` | Custom headers                    |
| `--timeout`     | Request timeout                   |
| `--no-color`    | Disable colored output            |
| `-q, --quiet`   | Quiet mode                        |
| `--verify-ssl`  | Enable SSL verification           |

---

## 🧪 Example

```bash
python3 CVE-2026-0740.py \
  -t https://victim.com \
  -f shell.php \
  -d ../../../../shell.php
```

---

## 🔍 How It Works

1. Requests a **nonce** via `admin-ajax.php`
2. Uses the nonce to perform a **file upload**
3. Exploits **path traversal** to control destination
4. Confirms upload and returns accessible file URL

---

## 📁 Affected Component

* Plugin: **Ninja Forms File Uploads**
* Endpoint: `/wp-admin/admin-ajax.php`
* Actions:

  * `nf_fu_get_new_nonce`
  * `nf_fu_upload`

---

## 🛡️ Mitigation

* Update plugin to the latest version
* Disable unnecessary file upload functionality
* Implement WAF rules
* Restrict executable file uploads
* Monitor `/wp-content/uploads/` directory

---

## 👨‍💻 Author

* **0xgh057r3c0n**

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](./LICENSE) file for details.

---

## ⭐ Contributing

Pull requests are welcome. For major changes, open an issue first to discuss what you would like to change.
