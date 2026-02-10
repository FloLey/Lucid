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

### 3.2 Agentic tool loop (new — core change)

The chatbot is an **agent**, not a single-shot router. It has a tool loop: the LLM can call read tools to gather context, reason about what it learned, then call write tools to take action. Multiple tool calls per turn are supported.

**Example: "slide 2 repeats what slide 1 says, fix it"**
1. LLM calls `get_slide(1)` → returns slide 1 title + body
2. LLM calls `get_slide(2)` → returns slide 2 title + body
3. LLM now understands the overlap and calls `regenerate_slide(slide_index=1, instruction="This slide repeats slide 1 which says '...'. Rewrite to cover a distinct angle while keeping the core message.")`
4. The existing `stage1_service.regenerate_slide_text` handles the actual rewriting — it already injects the draft, surrounding slides, and language context into its own prompt

**Key principle: the chatbot LLM never rewrites content itself.** It gathers context via read tools, formulates a precise instruction, and delegates the actual content work to the existing stage services (which have specialized prompts and proper context handling).

#### 3.2.1 Read tools (new)

These tools return data to the LLM so it can make informed decisions. They do NOT modify session state.

| Tool | Params | Returns |
|------|--------|---------|
| `get_slide` | `slide_index` | Slide title, body, image prompt, style summary |
| `get_all_slides` | (none) | Summary of all slides (index, title, body snippet) |
| `get_draft` | (none) | The original draft text |
| `get_session_info` | (none) | Current stage, num slides, language, shared style prefix |
| `get_style_proposals` | (none) | List of style proposals with descriptions (stage 2) |

#### 3.2.2 Write tools (existing — no changes)

The existing action tools (`regenerate_slide`, `update_slide`, `generate_slides`, `regenerate_prompt`, etc.) remain unchanged. The chatbot calls them the same way the old single-shot router did — the only difference is that the LLM can now gather context first to formulate better `instruction` params.

#### 3.2.3 Agent loop implementation

The backend runs a loop:
1. Send user message + tool definitions to LLM
2. If LLM responds with tool calls → execute them, append results, go to step 1
3. If LLM responds with a text message (no tool calls) → return to user
4. Cap at a maximum number of iterations (e.g., 5) to prevent runaway loops

This is a standard tool-use agent pattern. The Gemini API supports function calling natively — the LLM returns structured tool calls, the backend executes them and feeds results back.

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

#### 4.2.1 Rewrite `chat_service.py` — agent loop with function calling

Replace the current single-shot routing with an agentic tool loop using Gemini's native function calling.

**Current flow** (single-shot):
```
user message → LLM returns JSON {tool, params, response} → execute tool → return
```

**New flow** (agent loop):
```
user message → LLM returns tool_calls[] → execute tools → feed results back → LLM returns more tool_calls[] or final text → return
```

```python
async def process_message(self, session_id: str, message: str) -> Dict[str, Any]:
    session = session_manager.get_session(session_id)
    current_stage = session.current_stage

    # Build tool definitions (read + write tools for current stage)
    tools = self._get_tool_definitions(current_stage)

    # Agent loop
    messages = [{"role": "user", "content": message}]
    max_iterations = 5
    last_session = session

    for _ in range(max_iterations):
        response = await gemini_service.generate_with_tools(
            system_prompt=self._get_system_prompt(current_stage),
            messages=messages,
            tools=tools,
        )

        if not response.tool_calls:
            # LLM gave a final text response — done
            return {
                "success": True,
                "response": response.text,
                "session": last_session.model_dump(),
            }

        # Execute each tool call
        tool_results = []
        for tool_call in response.tool_calls:
            result = await self._execute_tool(session_id, tool_call.name, tool_call.params)
            if result.get("session"):
                last_session = result["session"]
            tool_results.append({"tool": tool_call.name, "result": result})

        # Append assistant tool calls + results to messages for next iteration
        messages.append({"role": "assistant", "tool_calls": response.tool_calls})
        messages.append({"role": "tool", "results": tool_results})

    # Max iterations reached
    return {"success": True, "response": "Done.", "session": last_session.model_dump()}
```

#### 4.2.2 Add read tool implementations

New methods in `chat_service.py` that return data without modifying state:

```python
def _execute_read_tool(self, session: SessionState, tool: str, params: dict) -> dict:
    if tool == "get_slide":
        idx = params["slide_index"]
        slide = session.slides[idx]
        return {
            "index": idx + 1,
            "title": slide.text.title,
            "body": slide.text.body,
            "image_prompt": slide.image_prompt,
            "has_image": slide.image_data is not None,
        }
    elif tool == "get_all_slides":
        return {
            "slides": [
                {"index": i + 1, "title": s.text.title, "body": s.text.body}
                for i, s in enumerate(session.slides)
            ]
        }
    elif tool == "get_draft":
        return {"draft_text": session.draft_text}
    elif tool == "get_session_info":
        return {
            "current_stage": session.current_stage,
            "num_slides": len(session.slides),
            "language": session.language,
            "shared_prompt_prefix": session.shared_prompt_prefix,
        }
    elif tool == "get_style_proposals":
        return {
            "proposals": [
                {"index": p.index, "description": p.description}
                for p in session.style_proposals
            ],
            "selected_index": session.selected_style_proposal_index,
        }
```

Read tools are NOT stage-gated — the LLM can read any slide data regardless of the current stage.

#### 4.2.3 Add `generate_with_tools()` to `gemini_service.py`

Extend the Gemini service to support function-calling mode. This wraps the Gemini API's native tool use:
- Accepts a system prompt, message history, and tool definitions
- Returns either a text response or a list of tool calls
- Tool definitions follow the Gemini function declaration schema

#### 4.2.4 Slash commands preserved as shortcuts

The existing regex-based slash command parsing (`/next`, `/back`, `/regen slide 2`, etc.) remains as a fast path that bypasses the LLM entirely. If the user types a slash command, execute it directly without entering the agent loop.

### 4.3 Prompt changes

#### 4.3.1 Rewrite `chat_routing.prompt` as agent system prompt

The prompt shifts from "parse this message into a JSON tool call" to "you are an agent with tools — use them to help the user."

```
You are an AI assistant for Lucid, a carousel creation tool.
You help users create and refine social media carousel slides.

The user is currently in Stage {current_stage}.

You have access to tools. Use READ tools to gather context before taking action.
Use WRITE tools to make changes. You can call multiple tools in sequence.

IMPORTANT:
- Always read the relevant slide content before modifying it
- When rewriting slides, use regenerate_slide with a clear instruction — do NOT rewrite content yourself
- Only use write tools that are available in the current stage
- Read tools are always available regardless of stage

If the user asks a question (not requesting an action), use read tools to get the information and answer directly.
```

Tool definitions are passed as structured function declarations to the Gemini API (not as text in the prompt). The system prompt only provides behavioral guidance.

---

## 5. Implementation Plan

### Phase 1: Non-blocking UI (do first, independent of chatbot)
1. Refactor `useSession.ts` — split `loading` into `stageLoading`
2. Update all 5 stage components to use `stageLoading` instead of `loading`
3. Ensure `StageIndicator` and `Header` never check loading state (they already don't gate on it, but confirm navigation functions don't set loading)
4. Make `advanceStage`/`previousStage`/`goToStage` not set loading state (they're instant API calls)

### Phase 2: Backend agent loop
5. Add `generate_with_tools()` to `gemini_service.py` (Gemini function-calling support)
6. Implement read tool handlers in `chat_service.py` (`get_slide`, `get_all_slides`, `get_draft`, `get_session_info`, `get_style_proposals`)
7. Rewrite `chat_service.py` `process_message()` with the agent loop (tool calls → execute → feed back → repeat)
8. Rewrite `chat_routing.prompt` as an agent system prompt
9. Keep slash-command fast path (`/next`, `/back`, etc.) as direct execution bypassing the LLM
10. Add tests for the agent loop (read tools, multi-step tool chains, max iteration cap)

### Phase 3: Chat panel layout
11. Create `ChatPanel.tsx` with the right-side panel layout, collapse toggle, message display, and input form
12. Update `App.tsx` layout to a horizontal flex with `ChatPanel` on the right
13. Port message handling logic from old `ChatBar.tsx` (send message, display response, update session)
14. Delete `ChatBar.tsx`

### Phase 4: Slash commands and autocomplete
15. Port stage-scoped `STAGE_COMMANDS` autocomplete from `ChatBar.tsx` into `ChatPanel.tsx`
16. Add quick-action chips below the input based on current stage

### Phase 5: Polish
17. Persist chat panel open/collapsed state in localStorage
18. Persist chat message history across stage changes (already in component state; just ensure the component doesn't unmount on stage change)
19. Mobile/responsive: On small screens, make the panel a slide-out drawer with an overlay

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
| `backend/app/services/gemini_service.py` | Add `generate_with_tools()` for function-calling support |
| `backend/app/services/chat_service.py` | Rewrite: agent loop, read tool handlers, tool definitions |
| `backend/prompts/chat_routing.prompt` | Rewrite as agent system prompt |
| `backend/tests/test_chat.py` | Add tests for agent loop, read tools, multi-step chains |

---

## 7. Out of scope (for now)

- **Streaming responses**: The chatbot waits for the full agent loop to complete. Streaming intermediate steps (e.g., "Reading slide 2...") can be added later via SSE.
- **Multi-turn conversation memory**: Each user message starts a fresh agent loop. The LLM does not see previous chat messages. Full conversation history can be added later by passing prior messages to the Gemini call.
- **Chat-initiated generation with progress**: When the chat triggers "generate images", the images generate synchronously. The chat blocks until done. Async background generation with progress can be added later.
- **Chatbot rewrites content directly**: The chatbot always delegates content changes to existing stage services (via `regenerate_slide` with an instruction). It never writes slide text itself — this ensures consistent quality via the specialized prompts.
- **Undo via chat**: No undo/revert capability.
- **Voice input**: Text-only.
