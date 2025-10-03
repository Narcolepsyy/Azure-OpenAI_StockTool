# Q&A Sticky Headers Implementation

A complete web component implementation for Q&A pages with sticky question headers, inspired by Perplexity's thread view interface.

## 🚀 Features

- **Semantic HTML structure** with proper landmarks and accessibility
- **CSS-only sticky positioning** with enhanced visual states
- **Responsive design** that works across desktop and mobile
- **Intersection Observer** for detecting "stuck" state
- **Keyboard navigation** support (j/k keys for section navigation)
- **Dark mode** support via CSS custom properties
- **Performance optimized** for many sections

## 📁 File Structure

```
qa-sticky-headers.html    # Complete implementation
README.md                 # This documentation
```

## 🏗️ Architecture Overview

### HTML Structure
```html
<main class="qa-app">
  <header class="app-header">...</header>
  <div class="qa-scroll" role="region">    <!-- Scroll container -->
    <section class="qa">                   <!-- Q&A pair -->
      <header class="qa__head">            <!-- Sticky header -->
        <h2 class="qa__title">...</h2>
        <div class="qa__tools">...</div>
      </header>
      <div class="qa__body">...</div>      <!-- Answer content -->
    </section>
    <!-- More sections... -->
  </div>
</main>
```

### CSS Key Classes

- `.qa-scroll` - Creates the scrolling context for sticky behavior
- `.qa__head` - The sticky header with `position: sticky; top: 0`
- `.qa__head.is-stuck` - Enhanced visual state when header is pinned
- `.qa__body` - Answer content area

### JavaScript Features

- **Intersection Observer** - Detects when headers are "stuck"
- **Keyboard shortcuts** - j/k navigation between sections  
- **Clipboard API** - Copy section links
- **Native Share API** - Share functionality where supported

## 🔧 Integration Guide

### Framework Adaptation

#### React Component Example
```jsx
function QASection({ question, answer, id }) {
  const headerRef = useRef();
  
  useEffect(() => {
    const observer = new IntersectionObserver(/* ... */);
    if (headerRef.current) {
      observer.observe(headerRef.current);
    }
    return () => observer.disconnect();
  }, []);

  return (
    <section className="qa" aria-labelledby={id}>
      <header ref={headerRef} className="qa__head">
        <h2 className="qa__title" id={id}>{question}</h2>
        <QATools />
      </header>
      <div className="qa__body">
        <Answer content={answer} />
      </div>
    </section>
  );
}
```

#### Vue Component Example
```vue
<template>
  <section class="qa" :aria-labelledby="questionId">
    <header ref="header" class="qa__head">
      <h2 class="qa__title" :id="questionId">{{ question }}</h2>
      <QATools />
    </header>
    <div class="qa__body">
      <Answer :content="answer" />
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps(['question', 'answer', 'questionId'])
const header = ref()
let observer

onMounted(() => {
  observer = new IntersectionObserver(/* ... */)
  if (header.value) {
    observer.observe(header.value)
  }
})

onUnmounted(() => {
  observer?.disconnect()
})
</script>
```

### Data Integration

```javascript
// Example data structure
const qaData = [
  {
    id: 'q1',
    question: 'How do sticky headers work?',
    answer: 'Sticky positioning is a hybrid...',
    timestamp: '2024-01-15T10:30:00Z',
    tags: ['css', 'positioning']
  },
  // ... more entries
];

// Render sections dynamically
function renderQASections(data) {
  const container = document.querySelector('.qa-scroll');
  
  data.forEach(item => {
    const section = document.createElement('section');
    section.className = 'qa';
    section.setAttribute('aria-labelledby', item.id);
    
    section.innerHTML = `
      <header class="qa__head">
        <h2 class="qa__title" id="${item.id}">${item.question}</h2>
        <div class="qa__tools" aria-hidden="true">
          <button class="qa__tool-btn" type="button" title="Copy link">🔗</button>
          <button class="qa__tool-btn" type="button" title="Share">↗</button>
        </div>
      </header>
      <div class="qa__body">
        <p>${item.answer}</p>
      </div>
    `;
    
    container.appendChild(section);
  });
}
```

## ⚠️ Common Pitfalls & Solutions

### 1. Sticky Not Working

**Problem**: Sticky positioning doesn't work as expected.

**Common causes**:
- Missing offset value (`top`, `bottom`, `left`, `right`)
- Ancestor has `overflow: hidden/auto/scroll`
- Ancestor has CSS transform or filter

**Solution**:
```css
/* ✅ Correct - specify offset */
.qa__head {
  position: sticky;
  top: 0; /* Required! */
}

/* ✅ Ensure scroll container doesn't interfere */
.qa-scroll {
  overflow: auto; /* This is the scroll context */
}

/* ❌ Avoid transforms on ancestors */
.parent {
  /* transform: translateZ(0); - This breaks sticky! */
}
```

### 2. Ancestor Overflow Issues

**Problem**: Parent elements with overflow settings break sticky behavior.

**Solution**:
```css
/* Move sticky element up in the DOM hierarchy */
/* OR ensure only the designated scroll container has overflow */

.container {
  /* overflow: hidden; - Remove this */
}

.qa-scroll {
  overflow: auto; /* Only here */
}
```

### 3. Z-Index Conflicts

**Problem**: Sticky headers appear behind other content.

**Solution**:
```css
.qa__head {
  position: sticky;
  top: 0;
  z-index: 2; /* Higher than body content */
  background: var(--bg-primary); /* Solid background */
}
```

### 4. Mobile Safari Issues

**Problem**: Viewport height behavior on mobile Safari.

**Solution**:
```css
/* Use dynamic viewport units */
.qa-scroll {
  height: 100dvh; /* Dynamic viewport height */
  /* Fallback for older browsers */
  height: 100vh;
}

/* Add touch scroll behavior */
.qa-scroll {
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}
```

### 5. Performance with Many Sections

**Problem**: Lag with hundreds of Q&A sections.

**Solutions**:
```css
/* Use CSS containment */
.qa {
  contain: layout style;
}
```

```javascript
// Implement virtual scrolling
function createVirtualScroll(items, containerHeight, itemHeight) {
  // Only render visible items + buffer
  const visibleStart = Math.floor(scrollTop / itemHeight);
  const visibleEnd = Math.min(visibleStart + Math.ceil(containerHeight / itemHeight) + 1, items.length);
  
  return items.slice(visibleStart, visibleEnd);
}

// Use single Intersection Observer
const observer = new IntersectionObserver(handleIntersection, { threshold: [1] });
document.querySelectorAll('.qa__head').forEach(header => observer.observe(header));
```

## 🎨 Customization

### Theming with CSS Custom Properties

```css
:root {
  /* Colors */
  --bg-primary: #ffffff;
  --bg-secondary: #fafafa;
  --text-primary: #111827;
  --text-secondary: #6b7280;
  --border-color: #e5e7eb;
  --accent-color: #3b82f6;
  
  /* Spacing */
  --spacing-sm: 8px;
  --spacing-md: 12px;
  --spacing-lg: 16px;
  --spacing-xl: 24px;
  
  /* Shadows */
  --shadow-light: 0 1px 3px rgba(0, 0, 0, 0.1);
  --shadow-stuck: 0 2px 8px rgba(0, 0, 0, 0.08);
  
  /* Border radius */
  --border-radius: 8px;
}

/* Dark mode */
@media (prefers-color-scheme: dark) {
  :root {
    --bg-primary: #1f2937;
    --bg-secondary: #111827;
    --text-primary: #f9fafb;
    --text-secondary: #9ca3af;
    --border-color: #374151;
  }
}
```

### Custom Stuck State Animation

```css
.qa__head {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.qa__head.is-stuck {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: saturate(120%) blur(8px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  transform: translateZ(0); /* Force hardware acceleration */
}
```

## 🧪 Testing Checklist

### Browser Compatibility
- [ ] Chrome 56+ (desktop & mobile)
- [ ] Firefox 32+
- [ ] Safari 13+ (desktop & iOS)
- [ ] Edge 16+
- [ ] Samsung Internet 6.2+

### Responsive Testing
- [ ] Desktop (1024px+)
- [ ] Tablet (768px - 1023px)
- [ ] Mobile (320px - 767px)
- [ ] Landscape orientation on mobile

### Accessibility Testing
- [ ] Screen reader navigation (NVDA, JAWS, VoiceOver)
- [ ] Keyboard-only navigation
- [ ] High contrast mode
- [ ] Color contrast ratios (WCAG AA)
- [ ] Focus management

### Performance Testing
- [ ] 100+ sections scroll performance
- [ ] Memory usage with Intersection Observer
- [ ] Paint/layout thrashing detection
- [ ] Mobile performance on older devices

## 🚀 Performance Optimization

### Lazy Loading Sections
```javascript
function lazyLoadSections() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const section = entry.target;
        // Load content dynamically
        loadSectionContent(section);
        observer.unobserve(section);
      }
    });
  });
  
  document.querySelectorAll('.qa[data-lazy]').forEach(section => {
    observer.observe(section);
  });
}
```

### Content Virtualization
```javascript
class VirtualQAScroller {
  constructor(container, items, itemHeight = 200) {
    this.container = container;
    this.items = items;
    this.itemHeight = itemHeight;
    this.visible = new Map();
    this.setupScrollListener();
  }
  
  render() {
    const scrollTop = this.container.scrollTop;
    const containerHeight = this.container.clientHeight;
    
    const startIndex = Math.floor(scrollTop / this.itemHeight);
    const endIndex = Math.min(
      startIndex + Math.ceil(containerHeight / this.itemHeight) + 2,
      this.items.length
    );
    
    this.updateVisibleItems(startIndex, endIndex);
  }
}
```

## 🔗 Related Resources

- [MDN: CSS position sticky](https://developer.mozilla.org/en-US/docs/Web/CSS/position#sticky)
- [Intersection Observer API](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API)
- [WCAG Accessibility Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [CSS Containment](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Containment)

## 📄 License

This implementation is provided as-is for educational and development purposes. Feel free to adapt and modify for your projects.

## 🤝 Contributing

To improve this implementation:

1. Test across different browsers and devices
2. Submit performance optimization suggestions  
3. Report accessibility issues
4. Suggest framework-specific adaptations

---

*Built with semantic HTML, modern CSS, and progressive enhancement principles.*