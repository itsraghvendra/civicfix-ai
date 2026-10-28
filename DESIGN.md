# CIVICFIX AI — Design System & Visual Specification (Tailwind CSS)

A premium, earthy, nature-inspired civic-tech design system built with **Tailwind CSS** for Lucknow Municipal Corporation (LMC).

---

## 1. Brand Color Palette & Tailwind Classes

| Token Name | Hex Code | Tailwind Utility | Role & Usage |
| :--- | :--- | :--- | :--- |
| **Soft White** | `#E8E9DF` | `bg-[#E8E9DF]` | Main canvas / application page background |
| **Sage Green** | `#A9B887` | `bg-[#A9B887]`, `border-[#A9B887]` | Secondary actions, selected nav states, subtle highlights |
| **Sage Light** | `#E8EDE0` | `bg-[#E8EDE0]` | Hover tint for secondary interactive elements |
| **Deep Olive** | `#2E3D28` | `bg-[#2E3D28]`, `text-[#2E3D28]` | Sidebar background, brand identity, key headings, primary buttons |
| **White** | `#FFFFFF` | `bg-white` | Cards, form surfaces, interactive containers |
| **Deep Slate** | `#1E251B` | `text-[#1E251B]` | High-contrast body text (WCAG AAA compliant) |
| **Muted Olive** | `#576352` | `text-[#576352]` | Secondary captions, helper descriptions, timestamps |
| **Border Subtle** | `#D5D7C9` | `border-[#D5D7C9]` | 1px clean container and card dividers |

---

## 2. Design Style & Philosophy

- **Corporate / Enterprise Clean**: Solid foundation of enterprise civic-tech reliability and institutional credibility.
- **Flat 2.0 Depth**: Subtle 1px borders with restrained, natural drop shadows (`border border-[#D5D7C9] shadow-sm`). No aggressive drop shadows or neon glows.
- **Bento Grid Layout**: Employed on the Municipal Officer Workspace to deliver instant, scan-friendly visual hierarchy for summary counts (`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4`).
- **Swiss Style Typography & Alignment**: Strict typographic rhythm, left-aligned headings, generous negative space, and disciplined data hierarchy.

---

## 3. Typography

- **Font Family**: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif (`font-sans`).
- **Scales & Weights**:
  - `H1` (Page Headers): `text-2xl` – `text-3xl`, Weight 700, Letter-spacing `-0.02em`, Color: `#2E3D28`.
  - `H2` (Section Titles): `text-lg` – `text-xl`, Weight 700, Letter-spacing `-0.015em`, Color: `#2E3D28`.
  - Body Text: `text-sm`, Weight 400, Line-height `1.5`, Color: `#1E251B`.
  - Microcopy / Captions: `text-xs` – `text-[11px]`, Weight 500, Color: `#576352`.

---

## 4. Buttons (Human, Grounded, Anti-AI-Gimmick)

### Prohibited Patterns
- ❌ No gradients
- ❌ No outer glows or neon lighting effects
- ❌ No AI sparkles (✨) or buzzword labels
- ❌ No oversized pill shapes

### Permitted Patterns
- **Primary Button**:
  - Class: `btn-primary` or `bg-[#2E3D28] text-white hover:bg-[#3B4D34] active:scale-[0.99] focus:outline-none focus:ring-2 focus:ring-[#2E3D28] focus:ring-offset-2 rounded-lg h-[42px] px-5 font-medium text-sm flex items-center justify-center gap-2`
  - Fill: Solid Deep Olive (`#2E3D28`)
  - Label Color: Soft White (`#FFFFFF`), medium weight (500)
  - Height: `42px`
  - Corner Radius: `8px` (`rounded-lg`)
- **Secondary Button**:
  - Class: `btn-secondary` or `border border-[#2E3D28] text-[#2E3D28] bg-white hover:bg-[#E8EDE0] active:scale-[0.99] rounded-lg h-[42px] px-5 font-medium text-sm flex items-center justify-center gap-2`
  - Fill: White with Deep Olive outline or Sage Green tint
  - Corner Radius: `8px` (`rounded-lg`)
- **Labels**:
  - Direct, human actions: *"Submit complaint"*, *"Track status"*, *"Assign officer"*, *"Save changes"*.

---

## 5. Semantic Priority Tags

Priority tags must remain strictly distinct and semantically meaningful for rapid human triage:

| Priority | Tailwind Classes | Semantic Meaning |
| :--- | :--- | :--- |
| **High** | `bg-red-50 text-red-700 border border-red-200` | Immediate danger to life, safety, or critical infrastructure |
| **Medium** | `bg-amber-50 text-amber-700 border border-amber-200` | Significant civic disruption, health, or sanitation concern |
| **Low** | `bg-gray-100 text-gray-700 border border-gray-300` | Routine municipal maintenance and cosmetic upkeep |

---

## 6. Lucknow Hero Imagery Specification

- **Subject**: Architectural heritage of Lucknow (Rumi Darwaza / Bara Imambara).
- **Overlay**: Dark Olive gradient overlay (`bg-gradient-to-r from-[#2E3D28]/95 via-[#2E3D28]/85 to-[#2E3D28]/70`) ensuring soft-white typography exceeds WCAG AAA contrast ratios.
- **Caption**: Embedded badge `"📍 Serving Lucknow • Municipal Grievance Redressal"`.
- **Corner Radius**: Consistent `rounded-lg` (`8px`) with soft shadow.
- **Accessibility**: Descriptive image alt text (`alt="Architectural view of the historic Rumi Darwaza in Lucknow, Uttar Pradesh"`).

---

## 7. Spacing & Radius Standards

- **Corner Radius**: Universal `8px` (`rounded-lg`) applied across cards, buttons, input fields, badges, and the hero image.
- **Card Padding**: `p-5` to `p-6` generous internal breathing space.
- **Grid Gaps**: `gap-4` to `gap-6` column gaps.
- **Borders**: Clean `1px` subtle lines (`border border-[#D5D7C9]`).
