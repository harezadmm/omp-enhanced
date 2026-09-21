# UI Component Templates

This document outlines the standard reusable UI components available in the project. Use these to maintain consistency across the application.

---

## 📦 Section Header with Description

Use when you need a section title with an icon and descriptive text.

**Responsive:** Stacks vertically on mobile (< 768px)

```html
<div class="section-header-card">
  <div class="section-header-card-title">
    <i class="fas fa-book"></i>
    <h3>Gibberish Dictionary</h3>
  </div>
  <p class="section-header-card-description">
    Translate text into random gibberish and corresponding dictionary.
  </p>
</div>
```

---

## 🎯 Simple Title with Icon

Use for inline titles with optional subtitles.

**Responsive:** Wraps naturally

```html
<div class="title-with-icon">
  <i class="fas fa-magic"></i>
  <h3>Universal Decoder</h3>
  <small>Prioritizing Base64</small>
</div>
```

---

## 💡 Info Boxes

Use for tips, warnings, success messages, or disclaimers.

**Variants:** `.info-box-warning`, `.info-box-success`, `.info-box-danger`

```html
<!-- Default (info) -->
<div class="info-box">
  <i class="fas fa-info-circle"></i>
  <span>Copy this text and share it. The transformation can be reversed.</span>
</div>

<!-- Warning -->
<div class="info-box info-box-warning">
  <i class="fas fa-triangle-exclamation"></i>
  <span>DISCLAIMER: Use for testing only. Do not deploy to production.</span>
</div>

<!-- Success -->
<div class="info-box info-box-success">
  <i class="fas fa-check-circle"></i>
  <span>Settings applied successfully!</span>
</div>

<!-- Danger -->
<div class="info-box info-box-danger">
  <i class="fas fa-radiation"></i>
  <span>Danger zone: This will freeze your browser!</span>
</div>
```

---

## 🃏 Card Container

Use for grouped content sections.

**Responsive:** Full width, proper padding adjustments

```html
<div class="card">
  <div class="card-header">
    <h4>Card Title</h4>
    <button class="btn btn-secondary">Action</button>
  </div>
  <div class="card-body">
    <p>Your main content goes here...</p>
  </div>
  <div class="card-footer">
    <small>Optional footer information</small>
  </div>
</div>
```

---

## 🎛️ Button Groups

Use for multiple action buttons that should stay together.

**Responsive:** Stacks vertically on very small screens (< 400px)

```html
<div class="button-group">
  <button class="btn btn-primary">
    <i class="fas fa-hammer"></i> Generate
  </button>
  <button class="btn">
    <i class="fas fa-copy"></i> Copy All
  </button>
  <button class="btn btn-secondary">
    <i class="fas fa-download"></i> Download
  </button>
</div>
```

---

## 🔘 Button Variants

Standard button classes:

- `.btn` - Base button (default gray)
- `.btn-primary` - Primary action (blue accent)
- `.btn-secondary` - Secondary action (transparent with border)

```html
<button class="btn">Default Button</button>
<button class="btn btn-primary">Primary Action</button>
<button class="btn btn-secondary">Cancel</button>
```

---

## 📝 Form Inputs

All standard HTML inputs are automatically styled and fully responsive. No extra classes needed!

**Features:**
- ✅ Responsive width (never overflows container)
- ✅ Consistent styling across all inputs
- ✅ Custom styled select dropdowns
- ✅ Proper focus states
- ✅ Text overflow handling (ellipsis)

```html
<label>
  Input Label
  <input type="text" placeholder="Automatically styled!">
  <small>Optional helper text</small>
</label>

<label>
  Select Dropdown (custom styled with arrow)
  <select>
    <option>Option 1</option>
    <option>Option 2 with longer text</option>
  </select>
</label>

<label>
  Text Area
  <textarea placeholder="Also styled automatically!"></textarea>
</label>

<label>
  Number Input
  <input type="number" min="0" max="100" value="50">
</label>
```

**Responsive Behavior:**
- Desktop: Standard padding (8px 10px)
- Mobile (< 400px): Reduced padding (6px 8px) and smaller font

---

## 🎨 Grid Layouts

Use `.options-grid` for form layouts:

```html
<div class="options-grid">
  <label>
    First Name
    <input type="text" placeholder="John">
  </label>
  <label>
    Last Name
    <input type="text" placeholder="Doe">
  </label>
  <label>
    Email
    <input type="email" placeholder="john@example.com">
  </label>
</div>
```

**Responsive:** Automatically switches to single column on small screens

---

## ✨ Best Practices

1. **Always use these standard components** instead of creating custom styles
2. **Only add overrides when absolutely necessary** - document why
3. **Test responsiveness** at 400px, 768px, and 900px breakpoints
4. **Use semantic HTML** - proper heading levels, labels, etc.
5. **Include icons from Font Awesome** for visual consistency
6. **Add ARIA labels** for accessibility when needed

---

## 🚫 Anti-Patterns (Don't Do This)

❌ Creating inline styles
❌ Duplicating component markup with slight variations
❌ Adding `!important` to override standard styles
❌ Using fixed widths that break responsiveness
❌ Nesting cards more than 2 levels deep
❌ Skipping semantic HTML elements

---

## 📐 Breakpoints

- **Mobile:** < 400px - Everything stacks, full width
- **Tablet:** 400px - 768px - Moderate stacking
- **Desktop:** > 768px - Full layout with sidebars

---

## 🎯 Quick Reference

| Component | Class | Responsive |
|-----------|-------|------------|
| Section Header | `.section-header-card` | Stacks < 768px |
| Title + Icon | `.title-with-icon` | Wraps |
| Info Box | `.info-box` | Full width |
| Card | `.card` | Full width |
| Button Group | `.button-group` | Stacks < 400px |
| Options Grid | `.options-grid` | Single col < 400px |

---

## 📞 Need a New Component?

If you find yourself copying the same markup pattern 3+ times:
1. Document the pattern
2. Add it to `style.css` with clear comments
3. Update this documentation
4. Refactor existing code to use it

