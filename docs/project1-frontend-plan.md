# Portfolio RAG Chatbot — Frontend Implementation Plan

## ⚠️ Critical: What I Found in Your Repo vs What the Plan Assumes

Your frontend plan has several mismatches with your actual portfolio. **Claude Code must use these:**

| Plan Says | Your Repo Actually Uses |
|---|---|
| `.jsx` files | **`.tsx` (TypeScript)** |
| Tailwind CSS | **CSS Modules (`.module.css`)** |
| `import.meta.env.VITE_API_URL` | **`process.env.REACT_APP_API_URL`** (CRA) |
| Generic fonts | **"Outfit" primary, "Roboto" secondary** |
| Generic colors | **See exact palette below** |

---

## Your Portfolio's Exact Design System

```css
/* From vars.css */
--color-text: #fff;
--color-primary: #576cbc;     /* Soft blue-purple — buttons, user bubbles */
--color-secondary: #19376d;   /* Deep navy — bot bubbles, panels */
--color-dark: #0b2447;        /* Darker navy — chat header */
--color-bg: #04152d;          /* Near-black navy — page background */

/* From index.css */
Accent green: #5dd6ac          /* Scrollbar, focus rings, success states */
Font: "Outfit", Arial, Helvetica, sans-serif
Focus ring: 2px solid #5dd6ac, offset 4px
Selection: rgba(93, 214, 172, 0.3)
```

## Your Portfolio's Existing Structure

```
src/
├── App.tsx                    ← Add ChatWidget import here
├── App.module.css
├── vars.css                   ← CSS variables (colors)
├── index.css                  ← Global styles
├── components/
│   ├── About/                 ← Each component = folder with .tsx + .module.css
│   │   ├── about.tsx
│   │   └── about.module.css
│   ├── Experience/
│   ├── Education/
│   ├── Skills/
│   ├── Projects/
│   ├── Contact/
│   └── Navbar/
├── data/                      ← JSON data files
└── assets/                    ← Images
```

**Pattern:** Each component lives in `ComponentName/componentName.tsx` + `componentName.module.css`

**Repo:** `ShashikarNEU/personal-portfolio` | Branch: `master` | Deployed: Netlify

**Existing deps:** React 18, TypeScript, MUI, Bootstrap, react-icons, react-router-dom, react-scroll

---

## Backend API Contract (Already Built)

```
POST /api/v1/chat
  Request:  { message: string, thread_id: string }
  Response: { response: string, thread_id: string, sources: Source[], email_sent: boolean }
  
  Source: { document: string, chunk: string, relevance_score: float }

GET /api/v1/health       → { status: "ok" }
GET /api/v1/graph/image  → PNG bytes (LangGraph architecture diagram)

Rate limit: 10/minute per IP (SlowAPI)
Daily cap: 200 requests
```

---

## New Files to Create

```
src/
├── services/
│   └── chatApi.ts                         # API client
├── hooks/
│   └── useChat.ts                         # Chat state management
├── components/
│   ├── chatbot/
│   │   ├── ChatWidget.tsx                 # Floating button + panel container
│   │   ├── ChatWidget.module.css
│   │   ├── ChatPanel.tsx                  # Message list + suggestion chips
│   │   ├── ChatPanel.module.css
│   │   ├── ChatMessage.tsx                # User/bot message bubbles
│   │   ├── ChatMessage.module.css
│   │   ├── ChatInput.tsx                  # Input bar + send button
│   │   ├── ChatInput.module.css
│   │   ├── SourceCard.tsx                 # Expandable citations
│   │   ├── SourceCard.module.css
│   │   ├── ThinkingIndicator.tsx          # ★ Multi-step RAG loading animation
│   │   ├── ThinkingIndicator.module.css
│   │   └── EmailConfirmation.tsx          # Success card
│   │   └── EmailConfirmation.module.css
│   │
│   └── AIShowcase/
│       ├── aiShowcase.tsx                 # Portfolio section
│       ├── aiShowcase.module.css
│       ├── TechBadge.tsx
│       └── TechBadge.module.css

Modified files:
├── App.tsx                                # Add <ChatWidget /> + <AIShowcase />
```

Total: **21 new files** + **1 modified file**

---

## ★ Key Improvement: Multi-Step "Thinking" Indicator

Instead of boring bouncing dots, show a **Perplexity/Claude-style multi-step progress indicator** that cycles through stages during the 6–14 second RAG processing time. This is the showpiece feature.

### Design

```
┌──────────────────────────────────┐
│  ┌─ ✦ Searching knowledge base...│  ← Step 1 (0-3s) with spinning icon
│  │                               │
│  ├─ ✦ Analyzing relevance...     │  ← Step 2 (3-6s)
│  │                               │
│  ├─ ○ Generating response...     │  ← Step 3 (6s+) with pulse animation
│  │                               │
│  └─ ○ Almost there...            │  ← Step 4 (10s+) appears only if slow
└──────────────────────────────────┘
```

### How It Works

```tsx
const THINKING_STEPS = [
  { text: "Searching knowledge base...", delay: 0 },
  { text: "Analyzing relevance...", delay: 2500 },
  { text: "Generating response...", delay: 5500 },
  { text: "Almost there...", delay: 10000 },       // only if it's really slow
];

// Component uses setInterval to reveal steps one by one
// Each step fades in with a staggered animation
// Active step has a pulsing dot/spinner
// Completed steps get a check mark ✓
// The whole thing disappears when isLoading becomes false
```

### Visual Style
- Left-aligned like a bot message
- Semi-transparent dark navy background (matches bot bubble)
- Each step line has:
  - **Active:** Pulsing green dot (#5dd6ac) + white text
  - **Completed:** Green checkmark + dimmed text
  - **Pending:** Hidden (revealed on timer)
- Subtle shimmer/glow effect on the active step
- The container has a slight glass-morphism effect (backdrop-filter: blur)

---

## Component Specifications (All Details for Claude Code)

### 1. `services/chatApi.ts`

```typescript
const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000/api/v1";

// Types
interface Source { document: string; chunk: string; relevance_score: number; }
interface ChatResponse { response: string; thread_id: string; sources: Source[]; email_sent: boolean; }

// sendMessage(message, threadId) → POST /chat
// Handle: 429 → "Too many messages, wait a moment"
//   NOTE: SlowAPI returns 429 with plain text body, NOT JSON. Catch by status code only.
// Handle: 500 → response body is {"detail": "..."}, NOT ChatResponse schema.
//   Parse the detail field for the error message.
// Handle: non-ok (other) → "Something went wrong. Please try again later."
// Handle: network error (TypeError: Failed to fetch) → "Backend may be offline"
// Use native fetch, NOT axios (no extra dependency needed)
// Add AbortController with 30s timeout to prevent hanging on slow responses
```

### 2. `hooks/useChat.ts`

```typescript
// State
messages: ChatMessageData[]      // { id, role: "user"|"bot", text, sources?, emailSent?, isError?, timestamp }
isLoading: boolean
error: string | null
threadId: string (useRef)

// Init: welcome message hardcoded (no API call)
// threadId: localStorage "chatbot_thread_id" → crypto.randomUUID() if missing

// sendMessage(text):
//   1. Add user message immediately (optimistic)
//   2. isLoading = true
//   3. await chatApi.sendMessage(text, threadId)
//   4. IMPORTANT: Always read thread_id FROM THE RESPONSE and update the ref + localStorage.
//      The server generates its own thread_id if the client's doesn't match an existing thread.
//      On first request, the server's returned thread_id is the canonical one.
//   5. Add bot response (with sources, emailSent)
//   6. isLoading = false
//   On error: add error message as bot bubble with isError=true

// clearChat(): new UUID, reset messages to [welcome], clear localStorage threadId
```

### 3. `ChatWidget.tsx` — Floating Button + Panel

```
COLLAPSED:
  - Fixed bottom-right (bottom: 24px, right: 24px)
  - 56px circular button, #576cbc gradient background
  - Chat bubble SVG icon (use inline SVG, no library)
  - Subtle pulse animation on first visit (before user has ever opened)
  - z-index: 9999

EXPANDED:
  - 380px wide × 520px tall panel
  - Slides up from button position with scale+fade animation
  - backdrop-filter: blur(12px) for glass effect
  - Border: 1px solid rgba(87, 108, 188, 0.25)
  - box-shadow: 0 8px 40px rgba(0,0,0,0.45)
  - border-radius: 16px

  Header bar:
    - "💬 AI Assistant" left
    - Clear (trash icon) + Close (X icon) buttons right
    - Background: rgba(11, 36, 71, 0.9) (#0b2447)
    
  Body: <ChatPanel />

MOBILE (< 640px):
  - Full-screen overlay (position: fixed, inset: 0)
  - No border-radius
  - Close button must be visible and reachable

KEYBOARD:
  - Escape closes panel
  - Focus trap when open (optional but nice)

ANIMATIONS:
  - Open: scale(0.92) → scale(1) + opacity 0→1, cubic-bezier(0.16, 1, 0.3, 1), 250ms
  - Close: reverse, 150ms
  - Button: scale(0.8) + opacity→0 when panel is open
```

### 4. `ChatPanel.tsx` — Message List

```
- Scrollable container (flex: 1, overflow-y: auto)
- Custom thin scrollbar matching portfolio theme
- Auto-scroll to bottom on new message (useRef + scrollIntoView smooth)

- Welcome message (first, hardcoded, no API):
  "Hi! I'm Shashikar's AI assistant. Ask me about his projects,
   skills, or experience — or ask me to send him a message!"

- Suggestion chips (shown ONLY when messages.length <= 1):
  "What are his top skills?" | "Tell me about his projects" | "Contact Shashikar"
  - Pill-shaped buttons
  - rgba(87,108,188,0.15) bg, 1px border rgba(87,108,188,0.35)
  - On click → call sendMessage with chip text
  - Disappear after first user message

- When isLoading → show <ThinkingIndicator /> at bottom

- Renders messages → <ChatMessage /> components
```

### 5. `ChatMessage.tsx` — Message Bubbles

```
USER messages:
  - Aligned right (flex-end)
  - Background: linear-gradient(135deg, #576cbc, #4a5da8)
  - White text
  - border-radius: 16px 16px 4px 16px (flat bottom-right)

BOT messages:
  - Aligned left (flex-start)
  - Background: rgba(25, 55, 109, 0.5)
  - rgba(255,255,255,0.9) text
  - border-radius: 16px 16px 16px 4px (flat bottom-left)
  - If sources[] → <SourceCard /> below bubble
  - If emailSent → <EmailConfirmation /> below bubble

ERROR messages:
  - Bot-aligned
  - Background: rgba(220, 53, 69, 0.15), border: rgba(220,53,69,0.3)
  - ⚠️ icon prefix

MARKDOWN support:
  - **bold** → <strong>
  - [text](url) → <a> link (green #5dd6ac color, opens in new tab)
  - Use regex splitting, NOT react-markdown (avoid extra dep)

ANIMATION: fade-in + translateY(6px→0) on mount, 200ms
```

### 6. `ChatInput.tsx` — Input Bar

```
- Textarea (not input) for potential multiline
- Placeholder: "Type a message..."
- Background: rgba(11, 36, 71, 0.8)
- Border: 1px solid rgba(87,108,188,0.3), focus → 0.6 opacity
- Send button: 40px square, #576cbc, send arrow SVG icon
- Enter to send, Shift+Enter for newline
- Disabled while isLoading (opacity 0.5)
- Max 500 chars, show remaining count when < 100 remaining
- Auto-focus when panel opens
```

### 7. `SourceCard.tsx` — Expandable Citations

```
COLLAPSED: "📎 3 sources" pill button (clickable)
EXPANDED (toggle):
  Each source shows:
  - 📄 document name + relevance % (green badge)
  - Truncated chunk text (150 chars max, dimmed)
  
Background: rgba(11, 36, 71, 0.6)
Border: 1px solid rgba(87,108,188,0.2)
```

### 8. `ThinkingIndicator.tsx` — ★ Multi-Step RAG Loading

```
STEPS (revealed sequentially on timers):
  Step 1 (instant):    "Searching knowledge base..."
  Step 2 (after 2.5s): "Analyzing relevance..."  
  Step 3 (after 5.5s): "Generating response..."
  Step 4 (after 10s):  "Almost there..."  ← only shows if backend is slow

EACH STEP LINE:
  - Completed: ✓ green check (#5dd6ac) + dimmed text (opacity 0.5)
  - Active: pulsing green dot (CSS @keyframes pulse) + white text + subtle glow
  - Pending: hidden

CONTAINER:
  - Bot-aligned (left side)
  - Background: rgba(25, 55, 109, 0.4) with backdrop-filter: blur(8px)
  - Border: 1px solid rgba(87,108,188,0.2)
  - border-radius: 12px
  - Padding: 12px 16px
  - Each step fades in with animation: fadeInSlide 0.3s ease

CSS ANIMATIONS:
  @keyframes pulse → scale 1→1.3→1 on the dot, 1.5s infinite
  @keyframes fadeInSlide → opacity 0→1 + translateY(4px→0)
  @keyframes shimmer → optional subtle shimmer on active step text

CLEANUP: Clear all timeouts when isLoading becomes false
```

### 9. `EmailConfirmation.tsx`

```
┌──────────────────────────────┐
│ ✅ Message sent to Shashikar │
│ He'll get back to you soon!  │
└──────────────────────────────┘

Background: rgba(93, 214, 172, 0.12)
Border: 1px solid rgba(93, 214, 172, 0.3)
Green title (#5dd6ac), dimmed subtitle
```

### 10. `AIShowcase/aiShowcase.tsx` — Portfolio Section

```
A NEW SECTION on your portfolio, inserted between Skills and Projects (or after Projects).
Follows the same section layout pattern as your other components.

LAYOUT:
┌─────────────────────────────────────────────────────────────┐
│  Section Title: "AI-Powered Portfolio" (match other section │
│  title styles from your portfolio)                          │
│                                                             │
│  Description text:                                          │
│  "This portfolio features an AI chatbot built with a        │
│   multi-agent RAG system. It can answer questions about my  │
│   projects, skills, and experience — or send me a message   │
│   directly."                                                │
│                                                             │
│  [Try the AI Assistant →] button (opens ChatWidget)         │
│                                                             │
│  ┌─────────────────────────────────────────────┐           │
│  │    Architecture diagram                      │           │
│  │    (fetch from /api/v1/graph/image           │           │
│  │     OR use a static placeholder image        │           │
│  │     OR render a Mermaid-style SVG diagram)   │           │
│  └─────────────────────────────────────────────┘           │
│                                                             │
│  "How it works" — 4 feature cards in a grid:               │
│    🔍 Advanced RAG with semantic search & reranking         │
│    🤖 Multi-agent orchestration via LangGraph               │
│    🛡️ Guardrails for safe, scoped responses                │
│    📧 Email agent for direct contact                        │
│                                                             │
│  Tech badges (pill-shaped):                                │
│  [FastAPI] [LangGraph] [OpenAI] [Pinecone] [React]        │
│  [SendGrid] [Python] [TypeScript]                          │
│                                                             │
│  [View on GitHub →] link                                    │
└─────────────────────────────────────────────────────────────┘

FEATURE CARDS:
  - 2×2 grid on desktop, single column on mobile
  - Each card: icon + title + one-line description
  - Background: rgba(25, 55, 109, 0.3)
  - Border: 1px solid rgba(87,108,188,0.2)
  - Hover: slight scale + border glow

"TRY THE AI ASSISTANT" BUTTON:
  - This needs a way to trigger ChatWidget.open() from outside
  - Solution: use a custom event (window.dispatchEvent) or
    lift isOpen state to App.tsx and pass down via props/context
  - Simplest: ChatWidget listens for a custom "open-chat" event
    AIShowcase dispatches that event on button click

GITHUB LINK: https://github.com/ShashikarNEU/portfolio-rag-chatbot
  (or whatever your backend repo is named)
```

### 11. App.tsx Modifications

```tsx
// Add imports:
import ChatWidget from './components/chatbot/ChatWidget';
import AIShowcase from './components/AIShowcase/aiShowcase';

// In the JSX, add:
<div id="ai-showcase"><AIShowcase /></div>   // between skills and projects (or after contact)
<ChatWidget />                                // at the very end, outside all sections

// Also add "AI" to Navbar links if you want
```

---

## Architecture Diagram Options (for AIShowcase)

**Option A: Static SVG/image** (simplest)
- Create a clean diagram showing: User → FastAPI → LangGraph → Tools (RAG / Email) → Response
- Store as `src/assets/architecture.png` or inline SVG

**Option B: Fetch from backend** — **NOT RECOMMENDED**
- `GET /api/v1/graph/image` tries `draw_mermaid_png()` which requires `pygraphviz` (often not installed).
- Falls back to plain text mermaid (not renderable as an image).
- Backend may not be running when portfolio is viewed.
- Do NOT rely on this endpoint for the frontend.

**Option C: CSS/HTML diagram** (most impressive)
- Build a simple flow diagram with CSS boxes + connecting lines
- Animated arrows showing data flow
- This looks the most intentional and custom

Recommend **Option A or C**. Do NOT use Option B.

---

## Edge Cases to Handle

1. **Backend offline**: Show error as bot bubble: "Can't reach the server right now. The backend may be offline."
2. **Rate limited (429)**: SlowAPI returns 429 with **plain text body** (not JSON). Catch by status code, show: "You're sending messages too fast. Please wait a moment."
3. **Daily cap hit**: Backend returns a **normal 200 response** with a friendly message ("I'm resting for today..."). The frontend cannot distinguish this from a regular reply — just display it as a normal bot message. This is intentional.
4. **Global 500 error**: The backend's catch-all handler returns `{"detail": "Something went wrong..."}` (not a ChatResponse). The frontend must handle both response shapes — check for `detail` field on 500 status.
5. **Empty message**: Send button disabled, no API call
6. **Very long response**: Bot bubble should word-wrap, not overflow
7. **Thread persistence**: localStorage survives page refresh and navigation. **Always sync thread_id from the server response**, not just the client-generated one.
8. **Mobile keyboard**: Input should remain visible when keyboard opens (fixed bottom)
9. **Multiple rapid sends**: isLoading prevents double-sends
10. **CORS**: Already configured — backend allows `http://localhost:3000` and `https://shashikaranthoniraj.netlify.app`. No backend changes needed.
11. **ThinkingIndicator cleanup**: Clear all timeouts when response arrives
12. **Fetch timeout**: Use AbortController with ~30s timeout. The `/chat` endpoint is sync (runs in FastAPI threadpool due to SqliteSaver) and typical response time is 3-15s, but can be longer under load.

---

## Environment Variables

```bash
# .env (for local development — already have backend running)
REACT_APP_API_URL=http://localhost:8000/api/v1

# Netlify environment variable (for production)
REACT_APP_API_URL=https://your-backend-domain.com/api/v1
```

---

## Build Order (2 Claude Code sessions)

```
Session 1: Complete Chatbot Widget (17 files + App.tsx wiring)
  ✦ chatApi.ts — API client with fetch, AbortController, error handling
  ✦ useChat.ts — state management, thread sync, localStorage
  ✦ ChatWidget.tsx + .module.css — floating button, panel, animations, mobile
  ✦ ChatPanel.tsx + .module.css — message list, suggestion chips, auto-scroll
  ✦ ChatMessage.tsx + .module.css — user/bot/error bubbles, markdown
  ✦ ChatInput.tsx + .module.css — textarea, send, char count
  ✦ ThinkingIndicator.tsx + .module.css — multi-step RAG loading (key feature)
  ✦ SourceCard.tsx + .module.css — expandable citations
  ✦ EmailConfirmation.tsx + .module.css — green success card
  ✦ Wire <ChatWidget /> into App.tsx
  → Test: full chatbot flow end-to-end with backend running
    - Button appears bottom-right, panel opens/closes with animation
    - Welcome message + suggestion chips on first load
    - Send message → ThinkingIndicator → bot response
    - Sources expand/collapse, email confirmation shows
    - Error states render correctly
    - Mobile full-screen overlay works

Session 2: AI Showcase Section + Polish (4 files + App.tsx update)
  ✦ AIShowcase/aiShowcase.tsx + .module.css — portfolio section
  ✦ TechBadge.tsx + .module.css — pill-shaped tech tags
  ✦ CSS/HTML architecture diagram (Option C — custom-built, no backend dependency)
  ✦ "Try the AI Assistant →" button wired to ChatWidget via custom event
  ✦ Add <AIShowcase /> to App.tsx between Skills and Projects
  ✦ Final responsive polish across both chatbot + showcase
  → Test: full portfolio with chatbot + showcase section
    - AIShowcase renders between Skills and Projects
    - "Try the AI Assistant" opens chat widget
    - Architecture diagram looks clean and intentional
    - All existing portfolio sections unaffected
```

---

# Claude Code Prompt

Copy everything below this line and paste it into Claude Code.

---

```
I'm adding a chatbot widget to my existing React portfolio.

## Context
- Repo: ShashikarNEU/personal-portfolio (branch: master, deployed on Netlify)
- Live site: https://shashikaranthoniraj.netlify.app/
- Backend API (already built): http://localhost:8000/api/v1
- The portfolio uses React 18 + TypeScript + CSS Modules + CRA (create-react-app)
- IMPORTANT: This is CRA, NOT Vite. Use process.env.REACT_APP_* for env vars, NOT import.meta.env
- IMPORTANT: Use .tsx files and .module.css files to match the existing codebase pattern
- IMPORTANT: Do NOT install Tailwind or any new CSS framework. Use CSS Modules only.
- Existing dependencies: MUI, Bootstrap, react-icons, react-scroll — you may use react-icons for icons if needed

## Portfolio Design System (from vars.css and index.css)
```css
--color-text: #fff;
--color-primary: #576cbc;      /* Blue-purple — user bubbles, buttons, accents */
--color-secondary: #19376d;    /* Deep navy — bot bubbles, panel backgrounds */
--color-dark: #0b2447;         /* Darker navy — headers */
--color-bg: #04152d;           /* Near-black navy — page background */
Accent green: #5dd6ac          /* Success states, links, active indicators */
Font: "Outfit", Arial, Helvetica, sans-serif
```
All backgrounds use rgba() with low opacity for glass/translucent effects. No solid opaque boxes.

## Backend API Contract
```
POST /api/v1/chat
  Request:  { message: string, thread_id: string }
  Response: { response: string, thread_id: string, sources: Source[], email_sent: boolean }
  Source:   { document: string, chunk: string, relevance_score: number }

GET /api/v1/health → { status: "ok" }
GET /api/v1/graph/image → PNG bytes (LangGraph architecture diagram)
```

## Existing App.tsx structure
```tsx
import React, {useState} from 'react';
import About from './components/About/about';
import Experience from './components/Experience/experience';
import Education from './components/Education/education';
import Skills from './components/Skills/skills';
import Projects from './components/Projects/projects';
import Contact from './components/Contact/contact';
import Navbar from './components/Navbar/navbar';
import styles from './App.module.css';
import ProjectDetails from './components/Projects/projectDetails';

function App() {
  const [openModal, setOpenModal] = useState({ state: false, project: null });
  return (
    <div className={styles.App}>
      <Navbar />
      <div id="about"><About /></div>
      <div id="experience"><Experience /></div>
      <div id="education"><Education /></div>
      <div id="skills"><Skills /></div>
      <div id="projects"><Projects openModal={openModal} setOpenModal={setOpenModal} /></div>
      <div id="contact"><Contact /></div>
      {openModal.state && <ProjectDetails openModal={openModal} setOpenModal={setOpenModal} />}
    </div>
  );
}
export default App;
```

## What to Build (all files)

### 1. src/services/chatApi.ts
- const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000/api/v1"
- Export types: Source, ChatResponse
- sendMessage(message: string, threadId: string): Promise<ChatResponse>
  - POST to /chat with { message, thread_id }
  - Add AbortController with 30s timeout to prevent hanging on slow responses
  - Handle 429 → throw "You're sending messages too fast. Please wait a moment."
    NOTE: SlowAPI returns 429 with plain text body, NOT JSON. Catch by status code only.
  - Handle 500 → response body is {"detail": "..."}, NOT ChatResponse schema. Show the detail message.
  - Handle other non-ok → throw "Something went wrong. Please try again later."
  - Handle TypeError (network) → throw "Can't reach the server right now. The backend may be offline."
- Use native fetch, no axios

### 2. src/hooks/useChat.ts
- Interface ChatMessageData: { id, role: "user"|"bot", text, sources?, emailSent?, isError?, timestamp }
- State: messages (array), isLoading (boolean), error (string|null)
- threadId stored in useRef, persisted to localStorage key "chatbot_thread_id"
- On init: hardcoded welcome message: "Hi! I'm Shashikar's AI assistant. Ask me about his projects, skills, or experience — or ask me to send him a message!"
- sendMessage(text): optimistic user message → API call → bot response or error message
  IMPORTANT: After each successful API response, read thread_id FROM the response and
  update the ref + localStorage. The server is the source of truth for thread_id.
- clearChat(): new UUID, reset to welcome message
- Return: { messages, isLoading, error, sendMessage, clearChat }

### 3. src/components/chatbot/ChatWidget.tsx + ChatWidget.module.css
- Floating circular button: fixed bottom-right (bottom: 24px, right: 24px), z-index 9999
- 56px round button, gradient background (135deg, #576cbc → #4a5da8), chat bubble SVG icon
- Subtle CSS pulse animation on first visit (box-shadow pulse), stops after first open
- Click toggles panel open/close
- Panel: 380px × 520px, border-radius 16px, backdrop-filter blur(12px)
- Background: rgba(4, 21, 45, 0.97), border: 1px solid rgba(87,108,188,0.25)
- Shadow: 0 8px 40px rgba(0,0,0,0.45)
- Header: "💬 AI Assistant" + clear chat (trash icon SVG) + close (X SVG) buttons
- Header bg: rgba(11, 36, 71, 0.9)
- Open animation: scale(0.92)→scale(1) + opacity 0→1, 250ms cubic-bezier(0.16,1,0.3,1)
- Close: reverse 150ms
- Escape key closes panel
- MOBILE (< 640px): full-screen overlay (fixed inset 0, no border-radius)
- Button hides (opacity 0, pointer-events none) when panel is open
- Listen for custom event "open-chatbot" to open from AIShowcase section
  ```tsx
  useEffect(() => {
    const handler = () => { setIsOpen(true); setHasBeenOpened(true); };
    window.addEventListener("open-chatbot", handler);
    return () => window.removeEventListener("open-chatbot", handler);
  }, []);
  ```

### 4. src/components/chatbot/ChatPanel.tsx + ChatPanel.module.css
- Scrollable message container (flex: 1, overflow-y: auto)
- Thin custom scrollbar (5px, rgba(87,108,188,0.3))
- Auto-scroll to bottom on new message (useRef + useEffect + scrollIntoView smooth)
- Map messages → <ChatMessage /> components
- Suggestion chips after welcome (only when messages.length <= 1):
  "What are his top skills?" | "Tell me about his projects" | "Contact Shashikar"
  - Pill-shaped: rgba(87,108,188,0.15) bg, 1px border, rounded-full, 13px font
  - On click → call onSend with chip text
- When isLoading → show <ThinkingIndicator /> at bottom
- <ChatInput /> at bottom (sticky)

### 5. src/components/chatbot/ChatMessage.tsx + ChatMessage.module.css
- User: aligned right, gradient bg (#576cbc→#4a5da8), white text, rounded with flat bottom-right
- Bot: aligned left, rgba(25,55,109,0.5) bg, near-white text, rounded with flat bottom-left
- Error: bot-aligned, rgba(220,53,69,0.15) bg with red border, ⚠️ prefix
- Basic markdown: **bold** → <strong>, [text](url) → <a> with #5dd6ac color, target _blank
  Use regex splitting, NOT react-markdown library
- If sources exist → <SourceCard sources={sources} /> below bubble
- If emailSent → <EmailConfirmation /> below bubble
- Fade-in animation on mount: opacity 0→1, translateY(6px→0), 200ms

### 6. src/components/chatbot/ChatInput.tsx + ChatInput.module.css
- Textarea (rows=1, resizable: none) + send button
- Input: rgba(11,36,71,0.8) bg, 1px border rgba(87,108,188,0.3), rounded-xl
- Focus: border opacity increases to 0.6
- Send button: 40px square, #576cbc bg, white send arrow SVG icon
- Enter sends, Shift+Enter newline
- Disabled (opacity 0.5) while isLoading
- Max 500 chars. Show remaining count when < 100 chars left
- Auto-focus when chat panel opens (pass autoFocus prop)

### 7. src/components/chatbot/SourceCard.tsx + SourceCard.module.css
- Collapsed: "📎 3 sources" pill button (clickable toggle)
- Expanded: list of sources, each showing:
  - 📄 document name (bold) + relevance % as green badge (#5dd6ac)
  - Truncated chunk text (150 chars, dimmed)
- Container: rgba(11,36,71,0.6) bg, 1px border rgba(87,108,188,0.2), rounded-lg

### 8. ★ src/components/chatbot/ThinkingIndicator.tsx + ThinkingIndicator.module.css
THIS IS THE KEY FEATURE. Build a multi-step "thinking" animation like Perplexity/Claude shows.

Steps revealed sequentially on timers:
  Step 1 (instant):    "Searching knowledge base..."
  Step 2 (after 2.5s): "Analyzing relevance..."
  Step 3 (after 5.5s): "Generating response..."
  Step 4 (after 10s):  "Almost there..."  ← only for slow responses

Each step line visual:
  - COMPLETED step: ✓ green checkmark (#5dd6ac) + text at opacity 0.5, strikethrough-like feel
  - ACTIVE step: pulsing green dot (#5dd6ac, CSS @keyframes scale 1→1.4→1, 1.5s infinite) + white text + subtle glow (text-shadow: 0 0 8px rgba(93,214,172,0.3))
  - PENDING step: hidden (not yet revealed)

Container styling:
  - Bot-aligned (left side of chat)
  - Background: rgba(25, 55, 109, 0.35) with backdrop-filter: blur(8px)
  - Border: 1px solid rgba(87,108,188,0.15)
  - border-radius: 14px
  - padding: 14px 18px
  - min-width: 220px

Each step fades in: @keyframes fadeInSlide → opacity 0→1, translateY(6px→0), 300ms ease-out
Vertical line connecting steps (2px wide, rgba(87,108,188,0.2)) on the left side

CRITICAL: Use useEffect with setTimeout for timers. Return cleanup function that clears ALL timeouts when component unmounts (when isLoading becomes false and this component is removed from DOM).

### 9. src/components/chatbot/EmailConfirmation.tsx + EmailConfirmation.module.css
- Green card: rgba(93,214,172,0.12) bg, 1px border rgba(93,214,172,0.3)
- ✅ icon + "Message sent to Shashikar" (green, bold) + "He'll get back to you soon!" (dimmed)
- Rounded, inline with message flow

### 10. src/components/AIShowcase/aiShowcase.tsx + aiShowcase.module.css + TechBadge.tsx + TechBadge.module.css

A new portfolio section. Follow the SAME section layout pattern as other sections (look at how About, Skills, Projects are structured — centered container, section title style, responsive grid).

Content:
  - Section title: "AI-Powered Portfolio" (use the same styling as other section titles in the portfolio)
  - Description paragraph about the chatbot
  - "Try the AI Assistant →" button that dispatches: window.dispatchEvent(new Event("open-chatbot"))
    Style: #576cbc bg, white text, rounded, hover glow
  - Architecture diagram: For now, create a CLEAN CSS/HTML flow diagram showing:
    User Message → FastAPI → LangGraph Agent → [Search Portfolio tool / Send Email tool] → Response
    Use CSS boxes with connecting lines/arrows, subtle animations on hover
    Match portfolio colors. This should look intentional and custom-built.
  - "How it works" — 4 feature cards in responsive 2×2 grid:
    🔍 "Semantic Search" — "Advanced RAG with query expansion & reranking"
    🤖 "Multi-Agent System" — "Intelligent orchestration via LangGraph"
    🛡️ "Smart Guardrails" — "Safe, scoped responses with prompt protection"
    📧 "Contact Agent" — "Send messages directly via email"
    Cards: rgba(25,55,109,0.3) bg, 1px border, rounded-lg, hover: slight scale + border glow
  - Tech badges (TechBadge.tsx): pill-shaped inline-flex
    [FastAPI] [LangGraph] [GPT-5 Mini] [Pinecone] [React] [SendGrid] [Python] [TypeScript]
    Style: rgba(87,108,188,0.15) bg, 1px border, rounded-full, 13px font
  - "View on GitHub →" link at bottom

### 11. Modify App.tsx
- Import ChatWidget and AIShowcase
- Add <div id="ai-showcase"><AIShowcase /></div> AFTER skills section, BEFORE projects
- Add <ChatWidget /> at the very end (after ProjectDetails modal), it's position:fixed so placement in DOM doesn't matter much

## Design Rules
- ALL new CSS must use CSS Modules (.module.css files)
- Use CSS variables from vars.css where possible: var(--color-primary), var(--color-bg), etc.
- Backgrounds: semi-transparent with rgba(), glass-morphism feel
- Borders: subtle, 1px, low-opacity rgba of primary color
- Font: inherit from body ("Outfit")
- Animations: subtle, purposeful, 200-300ms, ease or cubic-bezier
- No gradients except on user bubble and floating button (as specified)
- Icons: inline SVGs (simple ones like send arrow, trash, X, chat bubble) — do NOT add icon libraries
- Test that it doesn't break existing styles or layout

## Quality Checks
After building, verify:
1. Chat button appears on every page, bottom-right, above all content
2. Panel opens/closes with smooth animation
3. Welcome message shows immediately (no API call)
4. Suggestion chips appear and disappear after first message
5. ThinkingIndicator shows multi-step progress during loading
6. Messages render with correct alignment and colors
7. Sources expand/collapse
8. Error states display as bot bubbles with ⚠️
9. Mobile: full-screen overlay on small screens
10. AIShowcase section renders between Skills and Projects
11. "Try the AI Assistant" button opens the chat widget
12. No TypeScript errors, no console warnings
13. Existing portfolio sections are unaffected

This is SESSION 1 — build the complete chatbot widget. Start with chatApi.ts and useChat.ts,
then build all chatbot UI components (ChatWidget, ChatPanel, ChatMessage, ChatInput,
ThinkingIndicator, SourceCard, EmailConfirmation), then wire ChatWidget into App.tsx.
Do NOT build AIShowcase yet — that's Session 2.
```