# Spec: Side-Panel Chatbot

## Summary

Replace the unused bottom `ChatBar` component with a persistent right-side chatbot panel. The chatbot can trigger all stage-scoped actions via natural language, retrieve contextual information about slides, navigate between stages, and never blocks the rest of the UI.

---

## 1. Current State (Problems)

### 1.1 ChatBar is dead code
`ChatBar.tsx` exists but is never rendered in `App.tsx`. It was designed as a bottom bar with slash-command autocomplete but was never wired in.

### 1.2 Global loading state blocks the entire UI
A single `loading` boolean from `useSession` is shared across all components. When any LLM operation runs:
- Stage components disable all buttons (`disabled={loading}`)
- The "Next" button is hidden (`!loading && ...`)
- Navigation via `StageIndicator` calls `goToStage` which sets `loading=true`, so clicking a stage while generation is in-flight would conflict
- Opening Settings while loading works (it's a separate `showSettings` toggle), but stage navigation is effectively blocked

### 1.3 No contextual awareness
The backend `chat_service.py` routes commands to tools but doesn't pass slide content to the LLM. If a user says "make slide 2 more punchy", the LLM router picks the right tool and params but has no access to what slide 2 actually says.

---

## 2. Target UX

```
+--------+-----------------------------+------------------+
| Header | (full width)                |                  |
+--------+-----------------------------+                  |
| Stage Indicator (full width)         |                  |
+--------------------------------------+   Chat Panel    |
|                                      |   (right side)  |
|        Main Content Area             |                  |
|        (stage component)             |   - Messages    |
|                                      |   - Input box   |
|                                      |   - Suggestions |
|                                      |                  |
+--------------------------------------+------------------+
```

- The chat panel is a fixed-width right column (~380px), always visible
- A collapse/expand toggle allows hiding it to reclaim space
- Main content area shrinks horizontally when the panel is open
- The panel persists across stage changes (conversation history is kept)
- On mobile/small screens, the panel overlays as a slide-out drawer

---

## 3. Functional Requirements

### 3.1 Stage-scoped actions (existing behavior, preserved)
The chatbot can execute any action available in the current stage. The backend already enforces this via `STAGE_ALLOWED_TOOLS`. No change needed to the validation logic.

| Stage | Available actions |
|-------|------------------|
| 1 | generate slides, regenerate slide N, update slide N text, next, back |
| 2 | generate style proposals, select style N, next, back |
| 3 | generate prompts, regenerate prompt N, update prompt N, next, back |
| 4 | generate images, regenerate image N, next, back |
| 5 | apply styles, update style for slide N, export, back |

### 3.2 Context retrieval (new)
The chatbot should be able to answer questions about the current session. When the user references a slide or asks about content, the backend should inject relevant context into the LLM prompt.

**New backend tool: `get_context`**

When the LLM determines the user is asking a question (not issuing a command), the backend injects the relevant session data into the response prompt so the LLM can answer intelligently.

Context that should be available:
- **Slide text** (title + body) for any or all slides
- **Image prompts** for any or all slides
- **Current style settings** for a slide
- **Style proposal descriptions** (stage 2)
- **Session metadata** (num slides, language, current stage, draft text summary)
- **Shared style prefix** (the common image prompt prefix)

Implementation: Rather than a separate tool call, augment the `chat_routing.prompt` to include a condensed session snapshot so the LLM always has context when answering questions. For slide-specific references ("slide 2"), the LLM already parses the index — extend the prompt to include that slide's data.

### 3.3 Navigation (existing, ensure non-blocking)
- `/next`, `/back`, `/stage N` commands already work in the backend
- These should update the session state and the frontend should reflect the new stage
- Navigation must remain functional even while an LLM operation is in progress

### 3.4 Non-blocking UI (new)

**Core principle: Chat operations and stage operations are independent. Neither blocks the other.**

#### 3.4.1 Separate loading states
Replace the single global `loading` boolean with granular loading states:

```typescript
interface LoadingState {
  // Stage-level operations (generate all, etc.)
  stageAction: boolean;
  // Per-slide operations (regenerate slide N)
  slideActions: Set<number>;
  // Chat is processing a message
  chatProcessing: boolean;
}
```

- `stageAction: true` disables the "Generate" button in the current stage but does NOT disable: stage indicator clicks, settings button, new session button, chat input
- `slideActions` tracks per-slide regeneration (already partially implemented in Stage1/Stage4 with `regeneratingSlides`)
- `chatProcessing: true` shows a typing indicator in the chat panel but does NOT disable anything outside the chat

#### 3.4.2 Navigation always works
`StageIndicator` and Header should never be disabled by loading state. Stage navigation is a lightweight metadata update (no LLM call), so it should always be instant and available.

If the user navigates away mid-generation:
- The backend operation continues to completion and updates the session
- When the user navigates back, they see the completed result (or can refresh)
- The frontend does not cancel in-flight requests — it just stops showing the spinner for that stage

#### 3.4.3 Chat input always available
The chat input is never disabled. If the backend is already processing a chat message, the new message is queued (or the send button shows a small spinner but the input remains typeable). The chat panel has its own independent loading state.

#### 3.4.4 Settings always accessible
The settings modal already works independently (`showSettings` state). No change needed.

---

## 4. Technical Design

### 4.1 Frontend changes

#### 4.1.1 New component: `ChatPanel.tsx`
Replaces `ChatBar.tsx`. Key differences from the old ChatBar:

- **Layout**: Right-side panel (not bottom bar). Fixed width, full height below header.
- **Collapse toggle**: Button to collapse to a thin strip with a chat icon, or expand back.
- **Message display**: Scrollable message list with user/assistant bubbles. Kept across stage changes.
- **Slash-command autocomplete**: Preserve the existing stage-scoped autocomplete when typing `/`.
- **Quick-action chips**: Below the input, show 2-3 contextual action buttons based on the current stage (e.g., "Generate slides", "Next stage"). These are shortcuts, not a replacement for typing.
- **Typing indicator**: Shown while the backend processes the chat message.
- **Session update handling**: When a chat action modifies the session (e.g., "regenerate slide 2"), the panel receives the updated session and calls `updateSession()` — which updates the main stage view in real-time.

#### 4.1.2 Layout change in `App.tsx`
```
Current:  Header > StageIndicator > Main (full width)
Proposed: Header > StageIndicator > [Main (flex-1) | ChatPanel (w-96)]
```

The main content area becomes `flex-1` and the chat panel is a sibling with fixed width. When collapsed, the main area takes full width.

Persist the open/collapsed state in localStorage.

#### 4.1.3 Loading state refactor in `useSession.ts`
- Remove the single `loading` boolean
- Add `stageLoading: boolean` (for heavy stage operations)
- Stage components use `stageLoading` instead of `loading`
- Navigation functions (`advanceStage`, `previousStage`, `goToStage`) should NOT set any loading state — they are instant metadata updates
- Chat has its own `chatLoading` state, local to `ChatPanel`

#### 4.1.4 Delete `ChatBar.tsx`
Remove the dead code entirely. `ChatPanel.tsx` replaces it.

### 4.2 Backend changes

#### 4.2.1 Augment chat routing with session context
Modify `chat_service.py` `process_message()` to build a context snapshot and include it in the LLM routing prompt.

```python
def _build_context_snapshot(self, session: SessionState) -> str:
    """Build a condensed session snapshot for the LLM."""
    lines = [
        f"Session has {len(session.slides)} slides.",
        f"Current stage: {session.current_stage}",
        f"Language: {session.language}",
    ]
    for i, slide in enumerate(session.slides):
        lines.append(f"Slide {i+1}: title={slide.text.title!r}, body={slide.text.body[:100]!r}")
        if slide.image_prompt:
            lines.append(f"  prompt: {slide.image_prompt[:80]}")
    return "\n".join(lines)
```

Update `chat_routing.prompt` to include a `{context}` placeholder with this snapshot.

#### 4.2.2 New chat endpoint for context queries (optional)
If full context is too large for the routing prompt, add a two-step flow:
1. LLM routes to `get_context` tool with params specifying what to retrieve
2. Backend builds the context string and returns it as the assistant message

For v1, the simpler approach (always include condensed context in the routing prompt) is preferred.

#### 4.2.3 No other backend changes needed
The existing tool execution, stage validation, and slash-command parsing all remain as-is.

### 4.3 Prompt changes

#### 4.3.1 Update `chat_routing.prompt`
Add a `{context}` section so the LLM knows about the session state:

```
You are an AI assistant for Lucid, a carousel creation tool.
Your job is to interpret user commands and route them to the appropriate tool.

The user is currently in Stage {current_stage}.

Current session context:
{context}

Available tools for this stage:
{tool_descriptions}

...rest of prompt...
```

This allows the LLM to answer questions like "what does slide 3 say?" or "summarize my carousel" without needing a separate tool call.

---

## 5. Implementation Plan

### Phase 1: Non-blocking UI (do first, independent of chatbot)
1. Refactor `useSession.ts` — split `loading` into `stageLoading`
2. Update all 5 stage components to use `stageLoading` instead of `loading`
3. Ensure `StageIndicator` and `Header` never check loading state (they already don't gate on it, but confirm navigation functions don't set loading)
4. Make `advanceStage`/`previousStage`/`goToStage` not set loading state (they're instant API calls)

### Phase 2: Chat panel layout
5. Create `ChatPanel.tsx` with the right-side panel layout, collapse toggle, message display, and input form
6. Update `App.tsx` layout to a horizontal flex with `ChatPanel` on the right
7. Port message handling logic from old `ChatBar.tsx` (send message, display response, update session)
8. Delete `ChatBar.tsx`

### Phase 3: Slash commands and autocomplete
9. Port stage-scoped `STAGE_COMMANDS` autocomplete from `ChatBar.tsx` into `ChatPanel.tsx`
10. Add quick-action chips below the input based on current stage

### Phase 4: Context awareness
11. Add `_build_context_snapshot()` to `chat_service.py`
12. Update `chat_routing.prompt` to include `{context}`
13. Update `get_routing_prompt()` to accept and format the context

### Phase 5: Polish
14. Persist chat panel open/collapsed state in localStorage
15. Persist chat message history across stage changes (already in component state; just ensure the component doesn't unmount on stage change)
16. Mobile/responsive: On small screens, make the panel a slide-out drawer with an overlay
17. Add tests for the new context-aware chat routing

---

## 6. Files to modify

| File | Change |
|------|--------|
| `frontend/src/App.tsx` | New layout with ChatPanel, pass session + stage props |
| `frontend/src/components/ChatPanel.tsx` | **New file** — replaces ChatBar |
| `frontend/src/components/ChatBar.tsx` | **Delete** |
| `frontend/src/hooks/useSession.ts` | Split `loading` into `stageLoading`, remove `setLoading` from public API |
| `frontend/src/components/Stage1.tsx` | Use `stageLoading` instead of `loading` |
| `frontend/src/components/Stage2.tsx` | Use `stageLoading` instead of `loading` |
| `frontend/src/components/Stage3.tsx` | Use `stageLoading` instead of `loading` |
| `frontend/src/components/Stage4.tsx` | Use `stageLoading` instead of `loading` |
| `frontend/src/components/Stage5.tsx` | Use `stageLoading` instead of `loading` |
| `backend/app/services/chat_service.py` | Add context snapshot builder, pass context to prompt |
| `backend/prompts/chat_routing.prompt` | Add `{context}` placeholder |
| `backend/tests/test_chat.py` | Add tests for context-aware routing |

---

## 7. Out of scope (for now)

- **Streaming responses**: The chatbot waits for the full response. Streaming can be added later via SSE.
- **Multi-turn conversation memory**: The LLM routing prompt is stateless (one message at a time). Full conversation history in the LLM context can be added later.
- **Chat-initiated generation with progress**: When the chat triggers "generate images", the images generate in the background. The chat says "Generating images..." but doesn't stream per-slide progress. The main stage view shows spinners as usual.
- **Undo via chat**: No undo/revert capability.
- **Voice input**: Text-only.
