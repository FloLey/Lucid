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
5. **Check for cancellation** between each iteration (see 3.5)

This is a standard tool-use agent pattern. The Gemini API supports function calling natively — the LLM returns structured tool calls, the backend executes them and feeds results back.

### 3.3 Visible agent steps in the chat UI (new)

The user must see the agent's reasoning process in real-time, not just the final answer.

#### 3.3.1 Streamed events

The backend streams events to the frontend via **SSE (Server-Sent Events)** as the agent loop progresses. The chat panel renders each event incrementally.

Event types:

| Event | Payload | Rendered as |
|-------|---------|-------------|
| `thinking` | `{text: "..."}` | Collapsible "Thinking..." block with italic text, dimmed |
| `tool_call` | `{name: "get_slide", args: {slide_index: 1}}` | Inline chip: "Reading slide 1..." with tool icon |
| `tool_result` | `{name: "get_slide", result: {...}}` | Collapsible detail below the chip showing returned data |
| `text` | `{text: "..."}` | Normal assistant message bubble (final response) |
| `error` | `{message: "..."}` | Red error message |
| `done` | `{session: {...}}` | Signals completion, carries the updated session state |

#### 3.3.2 Chat message rendering

A single agent turn renders as a group in the chat:

```
User: "slide 2 repeats slide 1, fix it"

  [Thinking] Comparing slide contents...          ← collapsible, dimmed
  [Tool] get_slide(1) → "Hook: 5 tips for..."     ← chip + collapsible result
  [Tool] get_slide(2) → "Here are 5 tips..."      ← chip + collapsible result
  [Tool] regenerate_slide(1, instruction="...")    ← chip, shows as "Rewriting slide 2..."
  [Tool result] ✓ Slide 2 regenerated             ← success indicator

  Assistant: "I've rewritten slide 2 to focus on..."   ← final text bubble
  [Undo button]                                         ← appears after write tools
```

- Tool call chips show a human-readable label (e.g., "Reading slide 1" not `get_slide(slide_index=0)`)
- Thinking blocks are collapsed by default, expandable on click
- Tool result details are collapsed by default, expandable on click
- Write tool chips show a spinner while executing, then a checkmark or X
- The final text message appears as a normal assistant bubble

### 3.4 Interrupt agent execution (new)

The user can stop the agent mid-loop.

#### 3.4.1 Stop button
While the agent is running, the chat input's "Send" button becomes a "Stop" button. Clicking it:
1. Frontend aborts the SSE connection (`AbortController.abort()`)
2. Frontend sends `POST /api/chat/cancel` with the session ID
3. Backend sets a cancellation flag for this session
4. Between agent loop iterations, the backend checks the flag and stops
5. Any write tools already executed are NOT rolled back (use Undo for that)
6. The chat shows the steps completed so far + a "Stopped by user" message

#### 3.4.2 Graceful stopping
The agent only stops between iterations — it never interrupts a Gemini API call or a tool execution mid-flight. This means:
- If the LLM is generating a response, we wait for it to finish, then stop before executing the tool calls
- If a tool is executing (e.g., `regenerate_slide`), we wait for it to finish, then stop before the next LLM call
- This avoids leaving the session in an inconsistent state

### 3.5 Undo agent changes (new)

After the agent executes write tools, the user can undo all changes made in that turn.

#### 3.5.1 Session snapshots
Before the agent loop begins, the backend takes a deep copy of the session state. This is the "pre-agent snapshot."

- Stored in memory on the `SessionManager` as `_snapshots: dict[str, SessionState]` (one per session)
- Only the most recent snapshot is kept (one level of undo)
- The snapshot is taken before the first write tool executes, not at the start of the loop (read-only turns don't need snapshots)

#### 3.5.2 Undo endpoint
`POST /api/chat/undo` with `{session_id}`:
- Restores the session from the snapshot
- Persists the restored state to `sessions_db.json`
- Returns the restored session
- Clears the snapshot (can't undo twice)
- Returns 404 if no snapshot exists

#### 3.5.3 Undo in the UI
- After an agent turn that executed write tools, an "Undo" button appears below the agent's message group
- Clicking it calls the undo endpoint, updates the session, and shows "Changes undone" in the chat
- The undo button disappears after clicking (or after the next agent turn, which creates a new snapshot)
- Read-only turns (questions, context lookups) don't show an undo button

### 3.6 Navigation (existing, ensure non-blocking)
- `/next`, `/back`, `/stage N` commands already work in the backend
- These should update the session state and the frontend should reflect the new stage
- Navigation must remain functional even while an LLM operation is in progress

### 3.7 Non-blocking UI (new)

**Core principle: Chat operations and stage operations are independent. Neither blocks the other.**

#### 3.7.1 Separate loading states
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

#### 3.7.2 Navigation always works
`StageIndicator` and Header should never be disabled by loading state. Stage navigation is a lightweight metadata update (no LLM call), so it should always be instant and available.

If the user navigates away mid-generation:
- The backend operation continues to completion and updates the session
- When the user navigates back, they see the completed result (or can refresh)
- The frontend does not cancel in-flight requests — it just stops showing the spinner for that stage

#### 3.7.3 Chat input always available
The chat input is never disabled. If the backend is already processing a chat message, the new message is queued (or the send button shows a small spinner but the input remains typeable). The chat panel has its own independent loading state.

#### 3.7.4 Settings always accessible
The settings modal already works independently (`showSettings` state). No change needed.

---

## 4. Technical Design

### 4.1 Frontend changes

#### 4.1.1 New component: `ChatPanel.tsx`
Replaces `ChatBar.tsx`. Key differences from the old ChatBar:

- **Layout**: Right-side panel (not bottom bar). Fixed width, full height below header.
- **Collapse toggle**: Button to collapse to a thin strip with a chat icon, or expand back.
- **Message display**: Scrollable message list with user/assistant bubbles. Kept across stage changes.
- **Streamed agent steps**: Renders `thinking`, `tool_call`, `tool_result` events inline (see 3.3.2). Uses `fetch()` with `ReadableStream` to consume SSE events from the backend.
- **Stop button**: While agent is running, the Send button becomes a Stop button that aborts the SSE connection and sends a cancel request.
- **Undo button**: After a turn with write tools, shows an Undo button below the message group. Calls `POST /api/chat/undo` and updates the session.
- **Slash-command autocomplete**: Preserve the existing stage-scoped autocomplete when typing `/`.
- **Quick-action chips**: Below the input, show 2-3 contextual action buttons based on the current stage (e.g., "Generate slides", "Next stage"). These are shortcuts, not a replacement for typing.
- **Session update handling**: When a chat action modifies the session (via `done` SSE event), the panel calls `updateSession()` — which updates the main stage view in real-time.

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

#### 4.2.1 SSE streaming endpoint

Replace the current `POST /api/chat/message` (which returns a single JSON response) with an SSE streaming endpoint.

```python
from fastapi.responses import StreamingResponse

@router.post("/message")
async def send_message(request: ChatMessageRequest):
    """Process a chat message via streaming agent loop."""
    return StreamingResponse(
        chat_service.process_message_stream(
            session_id=request.session_id,
            message=request.message,
        ),
        media_type="text/event-stream",
    )
```

Each SSE event is a JSON line:
```
data: {"event": "thinking", "text": "Let me check the slide contents..."}

data: {"event": "tool_call", "name": "get_slide", "args": {"slide_index": 0}}

data: {"event": "tool_result", "name": "get_slide", "result": {"title": "Hook", "body": "..."}}

data: {"event": "text", "text": "I've rewritten slide 2 to avoid repetition."}

data: {"event": "done", "session": {...}, "has_writes": true}
```

The `has_writes` flag on the `done` event tells the frontend whether to show the Undo button.

#### 4.2.2 Cancel endpoint

```python
# In-memory cancellation flags
_cancel_flags: dict[str, bool] = {}

@router.post("/cancel")
async def cancel_agent(request: CancelRequest):
    """Signal the agent loop to stop after the current step."""
    _cancel_flags[request.session_id] = True
    return {"status": "cancelled"}
```

The agent loop checks `_cancel_flags[session_id]` between iterations and stops gracefully.

#### 4.2.3 Undo endpoint

```python
@router.post("/undo")
async def undo_agent(request: UndoRequest):
    """Restore session to pre-agent snapshot."""
    snapshot = session_manager.get_snapshot(session_id)
    if not snapshot:
        raise HTTPException(404, "No snapshot available")
    session = session_manager.restore_snapshot(session_id)
    return {"session": session.model_dump()}
```

#### 4.2.4 Rewrite `chat_service.py` — agent loop with Gemini function calling

Replace the current single-shot routing with an agentic tool loop using Gemini's native function calling API.

**Current flow** (single-shot):
```
user message → LLM returns JSON {tool, params, response} → execute one tool → return
```

**New flow** (streaming agent loop):
```
user message → LLM returns function_call parts → execute → stream events → feed results back → repeat → stream final text → done
```

```python
from google.genai import types

async def process_message_stream(self, session_id: str, message: str):
    """Agent loop that yields SSE events."""
    session = session_manager.get_session(session_id)
    current_stage = session.current_stage
    has_writes = False
    snapshot_taken = False

    # Build tool declarations (read tools + stage-gated write tools)
    tool_declarations = self._get_tool_declarations(current_stage)
    tools = types.Tool(function_declarations=tool_declarations)
    config = types.GenerateContentConfig(
        tools=[tools],
        system_instruction=self._get_system_prompt(current_stage),
        temperature=1.0,  # Gemini 3 recommended default
    )

    # Conversation contents for multi-turn
    contents = [
        types.Content(role="user", parts=[types.Part(text=message)])
    ]

    max_iterations = 5
    for _ in range(max_iterations):
        # Check cancellation
        if _cancel_flags.get(session_id):
            _cancel_flags.pop(session_id, None)
            yield sse_event("error", {"message": "Stopped by user"})
            break

        # Call Gemini with function declarations
        response = gemini_service.generate_with_tools(contents, config)

        # Check for thinking (Gemini 3 models)
        # The SDK includes thought in response parts when available

        # Process response parts
        function_calls = []
        for part in response.candidates[0].content.parts:
            if part.thought:
                yield sse_event("thinking", {"text": part.thought})
            elif part.function_call:
                function_calls.append(part.function_call)
            elif part.text:
                yield sse_event("text", {"text": part.text})

        if not function_calls:
            # No tool calls — LLM gave final text, done
            break

        # Execute tool calls and stream results
        # Append the model's response to conversation history
        contents.append(response.candidates[0].content)

        function_response_parts = []
        for fc in function_calls:
            yield sse_event("tool_call", {"name": fc.name, "args": dict(fc.args)})

            # Snapshot before first write tool
            is_write = fc.name not in READ_TOOLS
            if is_write and not snapshot_taken:
                session_manager.take_snapshot(session_id)
                snapshot_taken = True
                has_writes = True

            # Execute the tool
            result = await self._execute_tool(session_id, fc.name, fc.args)
            yield sse_event("tool_result", {"name": fc.name, "result": result})

            # Build function response part for next Gemini call
            function_response_parts.append(
                types.Part.from_function_response(
                    name=fc.name,
                    response={"result": result},
                )
            )

        # Append tool results to conversation for next iteration
        contents.append(types.Content(role="user", parts=function_response_parts))

    # Emit done with final session state
    session = session_manager.get_session(session_id)
    yield sse_event("done", {"session": session.model_dump(), "has_writes": has_writes})
```

#### 4.2.5 Tool declarations using Gemini function calling schema

Tool declarations follow the OpenAPI-subset format required by the Gemini API:

```python
READ_TOOLS = {"get_slide", "get_all_slides", "get_draft", "get_session_info", "get_style_proposals"}

def _get_tool_declarations(self, current_stage: int) -> list[dict]:
    """Build function declarations for read + stage-gated write tools."""
    declarations = [
        # Read tools (always available)
        {
            "name": "get_slide",
            "description": "Get the full content of a specific slide (title, body, image prompt, style).",
            "parameters": {
                "type": "object",
                "properties": {
                    "slide_index": {
                        "type": "integer",
                        "description": "1-based slide number (e.g., 1 for slide 1)",
                    }
                },
                "required": ["slide_index"],
            },
        },
        {
            "name": "get_all_slides",
            "description": "Get a summary of all slides (index, title, body).",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "get_draft",
            "description": "Get the original draft text the user provided.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "get_session_info",
            "description": "Get session metadata: current stage, number of slides, language, style prefix.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "get_style_proposals",
            "description": "Get the list of style proposals and which one is selected.",
            "parameters": {"type": "object", "properties": {}},
        },
    ]

    # Add stage-gated write tools
    declarations.extend(self._get_write_tool_declarations(current_stage))
    return declarations
```

Write tool declarations follow the same format. Example for `regenerate_slide`:
```python
{
    "name": "regenerate_slide",
    "description": "Regenerate a slide's text with an instruction. The instruction should describe what to change.",
    "parameters": {
        "type": "object",
        "properties": {
            "slide_index": {
                "type": "integer",
                "description": "1-based slide number",
            },
            "instruction": {
                "type": "string",
                "description": "What to change about the slide (e.g., 'make it less formal', 'add a question')",
            },
        },
        "required": ["slide_index"],
    },
}
```

#### 4.2.6 Add `generate_with_tools()` to `gemini_service.py`

Extend the Gemini service to support function-calling mode using the `google.genai` SDK:

```python
def generate_with_tools(
    self,
    contents: list,
    config: "types.GenerateContentConfig",
) -> "types.GenerateContentResponse":
    """Call Gemini with function declarations and return the raw response.

    The caller handles extracting function_call parts, text parts, and
    thought signatures. The SDK handles thought_signature management
    automatically when contents are passed back in subsequent turns.
    """
    self._ensure_configured()
    return self._client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=config,
    )
```

This is intentionally thin — the agent loop in `chat_service.py` owns the multi-turn orchestration. The Gemini SDK automatically handles thought signatures when you pass `response.candidates[0].content` back into the contents for the next turn.

#### 4.2.7 Read tool implementations

```python
def _execute_read_tool(self, session: SessionState, tool: str, params: dict) -> dict:
    if tool == "get_slide":
        idx = params["slide_index"] - 1  # Convert 1-based to 0-based
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

#### 4.2.8 Session snapshot methods on `SessionManager`

```python
class SessionManager:
    def __init__(self):
        self._sessions: dict[str, SessionState] = {}
        self._snapshots: dict[str, SessionState] = {}  # NEW

    def take_snapshot(self, session_id: str):
        """Deep copy current session state before agent writes."""
        session = self._sessions.get(session_id)
        if session:
            self._snapshots[session_id] = session.model_copy(deep=True)

    def restore_snapshot(self, session_id: str) -> Optional[SessionState]:
        """Restore session from snapshot and persist. Returns None if no snapshot."""
        snapshot = self._snapshots.pop(session_id, None)
        if snapshot:
            self._sessions[session_id] = snapshot
            self._save()
            return snapshot
        return None

    def get_snapshot(self, session_id: str) -> Optional[SessionState]:
        return self._snapshots.get(session_id)
```

#### 4.2.9 Slash commands preserved as shortcuts

The existing regex-based slash command parsing (`/next`, `/back`, `/regen slide 2`, etc.) remains as a fast path that bypasses the LLM entirely. If the user types a slash command, execute it directly without entering the agent loop. The SSE response for slash commands is a single `done` event with no intermediate steps.

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
3. Ensure `StageIndicator` and `Header` never check loading state
4. Make `advanceStage`/`previousStage`/`goToStage` not set loading state (they're instant API calls)

### Phase 2: Backend agent loop + SSE
5. Add `generate_with_tools()` to `gemini_service.py` (Gemini function-calling support)
6. Implement read tool handlers (`get_slide`, `get_all_slides`, `get_draft`, `get_session_info`, `get_style_proposals`)
7. Build tool declaration registry (read tools always, write tools per stage)
8. Rewrite `chat_service.py` with `process_message_stream()` — streaming agent loop yielding SSE events
9. Add SSE endpoint in `chat.py` route (StreamingResponse with `text/event-stream`)
10. Add cancel endpoint + cancellation flag checking between iterations
11. Add session snapshot/restore methods to `SessionManager`
12. Add undo endpoint in `chat.py` route
13. Rewrite `chat_routing.prompt` as an agent system prompt
14. Keep slash-command fast path (`/next`, `/back`, etc.) as direct execution
15. Add tests for: agent loop, read tools, multi-step chains, cancellation, undo, SSE event format

### Phase 3: Chat panel layout + SSE consumption
16. Create `ChatPanel.tsx` with right-side panel layout, collapse toggle
17. Implement SSE consumption: `fetch()` + `ReadableStream` to parse streamed events
18. Render agent steps inline: thinking blocks (collapsible), tool call chips, tool result details (collapsible), final text bubbles
19. Update `App.tsx` layout to horizontal flex with `ChatPanel` on the right
20. Delete `ChatBar.tsx`

### Phase 4: Interrupt + Undo UI
21. Stop button: swap Send → Stop while agent is running, abort SSE + call cancel endpoint
22. Undo button: show after turns with writes, call undo endpoint, update session
23. Frontend API client: add `cancelAgent()` and `undoAgent()` to `api.ts`

### Phase 5: Slash commands and autocomplete
24. Port stage-scoped `STAGE_COMMANDS` autocomplete into `ChatPanel.tsx`
25. Add quick-action chips below input based on current stage

### Phase 6: Polish
26. Persist chat panel open/collapsed state in localStorage
27. Persist chat message history across stage changes
28. Mobile/responsive: slide-out drawer with overlay on small screens

---

## 6. Files to modify

| File | Change |
|------|--------|
| **Frontend** | |
| `frontend/src/App.tsx` | New layout with ChatPanel, pass session + stage props |
| `frontend/src/components/ChatPanel.tsx` | **New file** — right-side panel with SSE consumption, agent step rendering, stop/undo buttons |
| `frontend/src/components/ChatBar.tsx` | **Delete** |
| `frontend/src/hooks/useSession.ts` | Split `loading` into `stageLoading`, remove `setLoading` from public API |
| `frontend/src/components/Stage1.tsx` | Use `stageLoading` instead of `loading` |
| `frontend/src/components/Stage2.tsx` | Use `stageLoading` instead of `loading` |
| `frontend/src/components/Stage3.tsx` | Use `stageLoading` instead of `loading` |
| `frontend/src/components/Stage4.tsx` | Use `stageLoading` instead of `loading` |
| `frontend/src/components/Stage5.tsx` | Use `stageLoading` instead of `loading` |
| `frontend/src/services/api.ts` | Add `sendChatMessageSSE()`, `cancelAgent()`, `undoAgent()` |
| `frontend/src/types/index.ts` | Add `ChatEvent` type union for SSE events |
| **Backend** | |
| `backend/app/services/gemini_service.py` | Add `generate_with_tools()` — thin wrapper for Gemini function calling |
| `backend/app/services/chat_service.py` | Rewrite: streaming agent loop, read tool handlers, tool declarations, cancellation |
| `backend/app/services/session_manager.py` | Add `take_snapshot()`, `restore_snapshot()`, `get_snapshot()` |
| `backend/app/routes/chat.py` | SSE streaming endpoint, cancel endpoint, undo endpoint |
| `backend/prompts/chat_routing.prompt` | Rewrite as agent system prompt |
| `backend/tests/test_chat.py` | Add tests for agent loop, read tools, cancel, undo, SSE |

---

## 7. Out of scope (for now)

- **Multi-turn conversation memory**: Each user message starts a fresh agent loop. The LLM does not see previous chat messages. Full conversation history can be added later by passing prior messages to the Gemini call.
- **Chat-initiated generation with progress**: When the chat triggers "generate images", the images generate synchronously within the agent turn. Async background generation with per-slide progress can be added later.
- **Chatbot rewrites content directly**: The chatbot always delegates content changes to existing stage services (via `regenerate_slide` with an instruction). It never writes slide text itself — this ensures consistent quality via the specialized prompts.
- **Multi-level undo**: Only one level of undo (the last agent turn). A full undo stack can be added later.
- **Voice input**: Text-only.
