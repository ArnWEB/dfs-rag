# EXIM RAG Ingest Manager - Style Guide

## Brand Identity

- **Application Name**: EXIM RAG Ingest Manager
- **Short Name**: EXIM RAG

## Color Palette

### Primary Colors

| Color Name | Hex Code | Usage |
|------------|----------|-------|
| bank-blue | `#0A3D91` | Primary brand color, buttons, active states |
| bank-blue-dark | `#072C6A` | Hover states, emphasis |
| bank-blue-light | `#E8F0FF` | Highlights, backgrounds |

### Accent Colors

| Color Name | Hex Code | Usage |
|------------|----------|-------|
| bank-yellow | `#FFC400` | Warnings, highlights |
| bank-red | `#D62828` | Errors, destructive actions |

### Neutral Colors

| Color Name | Hex Code | Usage |
|------------|----------|-------|
| bank-gray-light | `#F5F7FA` | Page backgrounds |
| bank-gray-border | `#E0E5EC` | Borders, dividers |
| bank-gray-text | `#5F6B7A` | Body text, secondary text |

### Semantic Colors

| Purpose | Color Variable | Hex |
|---------|---------------|-----|
| Success | green-500 | `#22c55e` |
| Warning | bank-yellow | `#FFC400` |
| Error/Destructive | bank-red | `#D62828` |
| Info | bank-blue | `#0A3D91` |

## Typography

### Font Family

```css
font-family: "Inter", "Roboto", sans-serif;
```

### Font Sizes

| Element | Size | Weight |
|---------|------|--------|
| Page Title | 3xl (30px) | Bold (700) |
| Section Title | 2xl (24px) | Semibold (600) |
| Card Title | lg (18px) | Semibold (600) |
| Body | sm (14px) | Regular (400) |
| Small/Caption | xs (12px) | Regular (400) |

## Spacing System

### Base Unit
- Base spacing: 4px
- Common spacing: 4, 8, 12, 16, 24, 32, 48, 80px

### Container
- Max width: 1200px
- Centered with padding: 24px

## Component Styles

### Buttons

**Primary Button**
```jsx
className="bg-bank-blue hover:bg-bank-blue-dark text-white font-medium rounded-bank"
```

**Secondary/Outline**
```jsx
className="border border-bank-gray-border bg-white hover:bg-bank-gray-light text-bank-blue"
```

**Destructive**
```jsx
className="bg-bank-red hover:bg-bank-red/90 text-white"
```

### Cards

```jsx
className="rounded-lg border border-bank-gray-border bg-white shadow-card"
```

### Inputs

```jsx
className="border border-bank-gray-border rounded-md px-3 py-2 focus:ring-2 focus:ring-bank-blue"
```

## Layout Structure

### Sidebar
- Width: 256px (w-64)
- Background: bank-blue (#0A3D91)
- Text: white
- Active item: bg-white/20

### Header
- Height: 56px (h-14)
- Background: white
- Shadow: shadow-nav (0px 2px 8px rgba(0,0,0,0.05))

### Main Content
- Background: bank-gray-light (#F5F7FA)
- Padding: 24px

### Border Radius
- Default: 6px (rounded-bank)
- Small: 4px
- Large: 8px
- Full: 9999px (for pills/avatars)

## Shadows

```css
shadow-card: 0px 4px 12px rgba(0,0,0,0.06)
shadow-nav: 0px 2px 8px rgba(0,0,0,0.05)
```

## Icons

Using Lucide React icons. Common sizes:
- Small: h-3 w-3 (12px)
- Default: h-4 w-4 (16px)
- Large: h-5 w-5 (20px)
- XLarge: h-8 w-8 (32px)

## Best Practices

### Do's
1. Use bank-blue for primary actions
2. Use white backgrounds for cards
3. Use bank-gray-light for page backgrounds
4. Use shadows on cards and elevated elements
5. Keep consistent 6px border radius
6. Use semibold for headings

### Don'ts
1. Don't mix color schemes
2. Don't use hardcoded hex colors (use CSS variables)
3. Don't skip focus states on interactive elements
4. Don't use inconsistent spacing

## Tailwind CSS Usage

### Custom Colors Available
```css
bg-bank-blue        /* #0A3D91 */
bg-bank-blue-dark   /* #072C6A */
bg-bank-blue-light  /* #E8F0FF */
bg-bank-yellow      /* #FFC400 */
bg-bank-red         /* #D62828 */
bg-bank-gray-light  /* #F5F7FA */
text-bank-blue-dark /* #072C6A */
text-bank-gray-text /* #5F6B7A */
border-bank-gray-border /* #E0E5EC */
rounded-bank        /* 6px */
shadow-card         /* 0px 4px 12px rgba(0,0,0,0.06) */
shadow-nav          /* 0px 2px 8px rgba(0,0,0,0.05) */
```

## Responsive Breakpoints

| Breakpoint | Width | Target |
|------------|-------|--------|
| sm | 640px | Mobile landscape |
| md | 768px | Tablet |
| lg | 1024px | Small desktop |
| xl | 1200px | Desktop |

## Status Indicators

| Status | Badge Style |
|--------|-------------|
| Connected | Badge with green-500 bg |
| Disconnected | Badge with red bg |
| Running | Badge with yellow bg + spin icon |
| Success | Green check icon |
| Error | Red X icon |
| Warning | Yellow alert icon |

## File Organization

```
src/
├── components/
│   ├── ui/           # Reusable UI components
│   └── layout/        # Layout components (Sidebar, Header)
├── pages/             # Page components
├── lib/              # Utilities (api, auth, keycloak)
├── stores/           # State management
└── index.css         # Global styles & theme
```

## Example: Creating a New Card

```tsx
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"

function ExampleCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Card Title</CardTitle>
      </CardHeader>
      <CardContent>
        Content goes here
      </CardContent>
    </Card>
  )
}
```
