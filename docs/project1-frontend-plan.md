# Portfolio RAG Chatbot — Frontend Plan

## Architecture

Chatbot widget embedded in existing React portfolio. Floating button → chat panel. Connects to FastAPI backend via REST API.

```
ChatWidget (floating button + panel)
  └── ChatPanel (message list)
       ├── ChatMessage (user/bot bubbles)
       │    ├── SourceCard (expandable citations)
       │    └── EmailConfirmation (success card)
       └── TypingIndicator (loading state)
  └── ChatInput (text input + send)

useChat hook ← manages all state
chatApi service ← handles API calls

AIShowcase section ← separate portfolio section explaining the AI system
```

---

## File Structure (in your existing portfolio repo, deploys via Netlify)

```
src/
├── components/
│   ├── chatbot/
│   │   ├── ChatWidget.jsx          # Floating button + panel container
│   │   ├── ChatPanel.jsx           # Message list with auto-scroll
│   │   ├── ChatMessage.jsx         # Single message bubble
│   │   ├── ChatInput.jsx           # Input bar + send button
│   │   ├── SourceCard.jsx          # Expandable RAG citations
│   │   ├── TypingIndicator.jsx     # Three bouncing dots
│   │   └── EmailConfirmation.jsx   # "Email sent" success card
│   │
│   └── ai-showcase/
│       ├── AIShowcase.jsx          # Portfolio section explaining the AI
│       ├── ArchitectureDiagram.jsx # LangGraph visual (Mermaid or image)
│       └── TechBadge.jsx           # Tech stack pill badges
│
├── hooks/
│   └── useChat.js                  # Chat state management hook
│
├── services/
│   └── chatApi.js                  # Backend API client
│
└── ...existing portfolio files...
```

---

## File Specifications

### `services/chatApi.js`

```javascript
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export async function sendMessage(message, threadId) {
  // POST /chat
  // Body: { message, thread_id }
  // Returns: { response, thread_id, intent, sources[], email_sent }
  // Error handling: network error, 429, 500 → return friendly error messages
}

export async function sendMessageStream(message, threadId, onChunk) {
  // POST /chat/stream (SSE) — Phase 2, after basic chat works
  // Calls onChunk(text) for each token
}
```

### `hooks/useChat.js`

```javascript
/*
State:
  messages: [{ id, role: "user"|"bot", text, sources?, emailSent?, timestamp }]
  isLoading: boolean
  threadId: string (from localStorage)
  error: string | null

Functions:
  sendMessage(text) → add user msg, call API, add bot response
  clearChat() → wipe messages, new threadId

On mount:
  - Check localStorage for "chatbot_thread_id"
  - If found: reuse (conversation persists across page navs)
  - If not: crypto.randomUUID(), store it

On sendMessage:
  1. Add { role: "user", text } to messages immediately
  2. isLoading = true
  3. Call chatApi.sendMessage(text, threadId)
  4. Add { role: "bot", text: response, sources, emailSent } to messages
  5. isLoading = false
  On error: set error message, isLoading = false
*/
```

### `ChatWidget.jsx`

```
Collapsed state:
  - Floating circular button, fixed bottom-right (bottom: 24px, right: 24px)
  - Chat bubble icon
  - Subtle pulse animation on first visit
  - z-index above everything

Expanded state:
  - Chat panel slides up from button
  - ~380px wide × 520px tall (desktop)
  - On mobile (< 640px): full-screen overlay
  - Header: title + minimize button + clear chat button
  - Body: ChatPanel
  - Animations: slide up + fade in (200ms), slide down + fade out (150ms)

Layout:
┌─────────────────────────────┐
│ 💬 AI Assistant           ✕ │  ← Header
├─────────────────────────────┤
│                             │
│   [ChatPanel]               │  ← Message list
│                             │
├─────────────────────────────┤
│ [ChatInput]                 │  ← Input bar
└─────────────────────────────┘

        [💬]  ← Floating button (when collapsed)
```

### `ChatPanel.jsx`

```
- Scrollable message container
- Auto-scroll to bottom on new message (useRef + scrollIntoView, smooth)
- Renders hardcoded welcome message first (no API call):
  "Hi! I'm Shashikar's AI assistant. Ask me about his projects, 
   skills, or experience — or ask me to send him a message!"

Note: Shashikar's full name is Shashikar Anthoni Raj.
Portfolio: https://shashikaranthoniraj.netlify.app/
- Maps messages → ChatMessage components
- Shows TypingIndicator when isLoading = true
- Shows 2-3 suggestion chips after welcome:
  [What are his top skills?]  [Tell me about his projects]  [Contact Shashikar]
  Clicking sends that text as a message
```

### `ChatMessage.jsx`

```
Props: { role, text, sources, emailSent, timestamp }

User messages: aligned right, portfolio accent color bg, white text
Bot messages: aligned left, gray-100 bg, dark text
  - If sources exist → SourceCard below message
  - If emailSent → EmailConfirmation below message
  - Support basic markdown (bold, links) via react-markdown or regex

Error messages: bot bubble with ⚠️ icon, soft red accent
```

### `ChatInput.jsx`

```
- Text input + send button
- Auto-focus when chat opens
- Enter sends, Shift+Enter for newline (optional)
- Send button disabled when empty or isLoading
- Input disabled while isLoading
- Clear input after send
- Max 500 chars, show count when > 400
```

### `SourceCard.jsx`

```
Collapsed: "📎 3 sources" (clickable)
Expanded:
  ┌─────────────────────────────┐
  │ 📎 Sources                   │
  │ 📄 projects.md (92% match)  │
  │ "Shashikar built an Event..."│
  │ 📄 experience.md (87% match)│
  │ "At Ford Motor Company..."   │
  └─────────────────────────────┘

Props: sources[] from API response
Each: document name, relevance %, truncated chunk text
```

### `TypingIndicator.jsx`

```
Three dots with staggered bounce animation (0ms, 200ms, 400ms delay)
Styled as bot message (left-aligned, gray bubble)
Pure CSS animation, no library
```

### `EmailConfirmation.jsx`

```
┌─────────────────────────────┐
│ ✅ Message sent to Shashikar │
│ He'll get back to you soon!  │
└─────────────────────────────┘

Soft green background. Shows when emailSent = true.
```

### `AIShowcase.jsx`

```
Portfolio section (not inside chatbot). Goes alongside About, Projects, Skills, etc.

┌─────────────────────────────────────────────────────────────┐
│  🤖 AI-Powered Portfolio Assistant                          │
│                                                             │
│  This portfolio features an AI chatbot built with           │
│  a multi-agent RAG system. Try it out! →  [Open Chat]      │
│                                                             │
│  ┌─────────────────────────────────────────────┐           │
│  │        [LangGraph Architecture Diagram]     │           │
│  └─────────────────────────────────────────────┘           │
│                                                             │
│  How it works:                                             │
│  • Advanced RAG with query expansion & reranking           │
│  • Multi-agent orchestration via LangGraph                 │
│  • Guardrails for safe, scoped responses                   │
│  • Email agent for direct contact                          │
│                                                             │
│  [FastAPI] [LangGraph] [OpenAI] [ChromaDB] [React]        │
│                                                             │
│  [View on GitHub →]                                        │
└─────────────────────────────────────────────────────────────┘

"Open Chat" button triggers ChatWidget to open.
Architecture diagram: static image from /graph/image endpoint or Mermaid component.
TechBadge.jsx: pill badges (inline-flex px-3 py-1 rounded-full text-sm)
```

---

## Design Spec

```
Colors: Match existing portfolio theme
  Chat bubble (user): portfolio primary/accent color
  Chat bubble (bot): gray-100 / gray-200
  Chat header: darker shade of primary
  Floating button: primary color
  Source cards: light blue-gray bg
  Email confirmation: soft green bg
  Error: soft red bg

Typography: Same font as portfolio
  Message text: 14px
  Header: 16px semibold
  Timestamps: 12px text-gray-400
  Source text: 13px

Spacing: Tailwind utilities
  Message gap: space-y-3
  Bubble padding: p-3 px-4
  Panel padding: p-4

Shadows: shadow-xl on panel, shadow-lg on button
Borders: rounded-2xl panel, rounded-full button, rounded-lg cards
```

Claude Code prompt for design:
```
Use Tailwind CSS. Match the existing portfolio's color scheme: [HEX COLOR].
Keep it minimal, clean, professional. No gradients. Subtle shadows. Rounded corners.
```

---

## State Flow

```
User types → ChatInput → useChat.sendMessage()
  → adds user message to state (optimistic)
  → isLoading = true
  → chatApi.sendMessage(text, threadId)
  → POST /api/v1/chat { message, thread_id }
  → backend processes (guardrails → router → agent → response)
  → returns { response, thread_id, intent, sources, email_sent }
  → adds bot message to state (with sources/emailSent)
  → isLoading = false
  → ChatPanel re-renders, auto-scrolls
```

---

## Edge Cases to Handle

- **Welcome message**: Hardcoded, no API call, shows instantly on first open
- **Suggestion chips**: Clickable, send text as message, reduce friction
- **Error states**: Backend down, 500, offline → show as bot messages with ⚠️
- **Thread persistence**: localStorage "chatbot_thread_id" → survives page refresh/navigation
- **Mobile**: < 640px → full-screen overlay, close button visible, keyboard doesn't cover input
- **CORS**: FastAPI must allow portfolio domain in allow_origins

---

## Build Order

```
Phase 1: API Client + Hook (1-2 hours)
  □ chatApi.js
  □ useChat.js
  □ Test with console.log (mock API if backend not ready)

Phase 2: Core Chat UI (2-3 hours)
  □ ChatWidget.jsx (button + panel toggle)
  □ ChatPanel.jsx (message list + auto-scroll)
  □ ChatMessage.jsx (user + bot bubbles)
  □ ChatInput.jsx (input + send)
  □ TypingIndicator.jsx
  □ Wire useChat hook

Phase 3: Rich Features (1-2 hours)
  □ SourceCard.jsx
  □ EmailConfirmation.jsx
  □ Suggestion chips
  □ Welcome message
  □ Error handling UI

Phase 4: AI Showcase Section (1-2 hours)
  □ AIShowcase.jsx
  □ ArchitectureDiagram.jsx
  □ TechBadge.jsx
  □ "Open Chat" button wired to ChatWidget

Phase 5: Polish (1-2 hours)
  □ Mobile responsive (full-screen on small screens)
  □ Open/close animations
  □ Match portfolio colors exactly
  □ Dark mode (if portfolio has it)
  □ Cross-browser test
```
