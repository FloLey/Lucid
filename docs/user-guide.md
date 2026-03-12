# Lucid — User Guide

Lucid has two independent creation modes: a **6-stage Slide Generation pipeline** that converts rough drafts into polished social media carousels, and a **Matrix Generation** tool that maps any theme or cross-axis relationship into a live-streaming n×n visual grid. Choose your mode on the home screen.

---

## Prerequisites

- Lucid is running (see [Installation](../README.md#installation--requirements))
- You have a Google API key configured (required for AI features)
- The app is open at `http://localhost:5173`

---

## Slide Generation

### Projects

Everything in Lucid's slide pipeline lives inside a **project**. The Slide Generation home screen lists all your projects as thumbnail cards showing the project name, mode, slide count, and how far through the pipeline it has reached.

#### Creating a project

Click **New Project**. A modal asks for three things:

| Option | Description |
| :--- | :--- |
| **Mode** | **Carousel** — multiple slides exported as a set (the default). **Single Image** — one slide only. |
| **Slide count** | Choose 3, 5, 7, or 10 slides (ignored for Single Image mode). |
| **Template** | Optional. Pick a saved template to pre-load its configuration. Defaults to *Carousel Default* or *Single Image Default* if none is chosen. |

Click **Create** to open the project at Stage 1 (Research).

#### Renaming a project

Projects are auto-named (*Untitled • YYYY-MM-DD • …*) when created. Click the project name at the top of the editor to rename it inline.

#### Reopening a project

Click any project card on the home screen to reopen it exactly where you left off — the pipeline remembers your current stage and all generated content.

#### Deleting a project

Hover over a project card and click the **trash icon** to delete it. This also removes all associated generated images.

---

### Templates

A **template** is a reusable configuration blueprint. It stores defaults for mode, slide count, LLM prompts, typography style, and stage instructions — so you can start a new project with a consistent setup without reconfiguring from scratch.

#### Built-in templates

Lucid ships with two default templates seeded on first run:

| Template | Mode | Default slides |
| :--- | :--- | :--- |
| **Carousel Default** | Carousel | 5 |
| **Single Image Default** | Single Image | 1 |

#### Viewing and managing templates

Click **Templates** on the home screen to open the Templates panel. Each card shows the template name, mode, and default slide count. From here you can:

- **Create** a new template by typing a name and clicking **Create**.
- **Delete** a template using the trash icon on its card.

> **Note:** Deleting a template does not affect projects already created from it — each project stores a private copy of its configuration.

#### Using a template

When creating a new project, select a template from the **Template** dropdown in the New Project modal. The project will inherit that template's prompt configuration, typography defaults, and stage instructions. Once created, the project's config is independent — changes to the template do not retroactively affect existing projects.

#### Customising a template's configuration

Template configuration (prompts, style defaults, image settings) is edited through the **Settings** modal inside a project. Recommended workflow:

1. Create a project from an existing template.
2. Open **Settings** (gear icon) and adjust Prompts, Style, Image, and Instructions tabs.
3. Future projects can be created from templates that reflect your refined defaults.

---

### The Pipeline

Lucid uses a strict, bi-directional 6-stage pipeline. Each stage builds on the last, and you can always step **backward** to revise without losing downstream work.

```
Stage 1: Research → Stage 2: Draft → Stage 3: Style → Stage 4: Image Prompts → Stage 5: Images → Stage 6: Typography
```

---

### Stage 1: Research

The Research stage lets you brainstorm and gather information through a chat interface before writing your draft. The AI assistant is grounded in real-time Google Search.

#### 1. Ask questions

Type your message and press **Enter** (or click **Send**). Continue the conversation to explore angles, gather statistics, or refine ideas. The full conversation is saved as part of your project.

#### 2. Add research instructions (optional)

In the right panel, enter guidance for how the conversation should be synthesised into a draft — for example, *"Focus on three key arguments"* or *"Keep it beginner-friendly"*.

#### 3. Create your draft

When satisfied with the research, click **Create Draft & Proceed →**. Lucid synthesises the entire conversation into a structured draft and advances you to Stage 2.

#### 4. Skip research

If you already have content, click **Skip Research** to go straight to Stage 2 with an empty draft.

---

### Stage 2: Draft

#### 1. Paste your draft

Click the **Your Draft** text area and paste your raw content — bullet points, notes, an existing article. Lucid will restructure it. If you came from Stage 1, the draft has been pre-populated from the research conversation.

#### 2. Configure generation

| Option | Description |
| :--- | :--- |
| **Number of Slides** | Pick a fixed count (3–10) or choose **Auto** to let the AI decide. |
| **Language** | Output language for slide text (defaults to English). |
| **Include Titles** | Toggle whether each slide gets a title. |
| **Additional Instructions** | Optional guidance, e.g. *"Make it conversational, target entrepreneurs"*. |

#### 3. Generate slides

Click **Generate Slides**. The right panel populates with a card per slide showing its title (if enabled) and body text.

#### 4. Review and edit

Each slide card offers two actions:

- **Edit** — Opens an inline editor. Modify the title and/or body text, then click **Save** (or **Cancel** to discard).
- **Regenerate** — Expands an instruction input. Type an optional instruction (e.g. *"Make this punchier"*) and press **Enter** or click **Go** to regenerate just that slide via SSE streaming.

When happy with the slide text, click **Next: Choose Style →**.

---

### Stage 3: Style Proposals

Lucid generates visual style proposals based on your slide content. All images generated later follow the style you pick here.

#### 1. Configure proposals

| Option | Description |
| :--- | :--- |
| **Number of Proposals** | Choose 2, 3, or 4 style proposals to generate. |
| **Additional Instructions** | Optional style guidance, e.g. *"Warm colors, minimalist, professional photography"*. |

#### 2. Generate proposals

Click **Generate Style Proposals**. Each proposal card shows a preview image and a text description of the visual style.

#### 3. Select a style

Click a proposal card to select it — it highlights with a blue border and a **Selected** badge. You must select a style before advancing.

Click **Next: Image Prompts →** when ready, or **← Back** to revise your draft.

---

### Stage 4: Image Prompts

Instead of generating images immediately, Lucid first writes a specific, text-free image prompt for each slide. This lets you review and refine before spending API calls.

#### 1. Optionally add image style instructions

The **Image Style Instructions** field adds extra guidance on top of the chosen style (e.g. *"Always include natural light, avoid people"*).

#### 2. Generate prompts

Click **Generate Image Prompts**. Each slide gets an individual prompt. A **Shared Style prefix** box shows the common style context prepended to every prompt.

#### 3. Review and edit prompts

Each prompt card offers:

- **Edit** — Opens a textarea to rewrite the prompt manually. Click **Save** when done.
- **Regenerate** — Asks the AI to rewrite just that prompt (keeps the shared style prefix).

Once satisfied with all prompts, click **Next: Generate Images →**, or **← Back** to revisit style proposals.

---

### Stage 5: Image Generation

Lucid sends all image prompts in parallel to Gemini and displays the results.

#### 1. Generate images

Click **Generate Images**. A spinner appears over each slide thumbnail while it loads. Generation runs concurrently — all slides process at the same time.

#### 2. Regenerate individual images

If a specific background doesn't look right, click **Regen** next to that slide to regenerate it alone without touching the others.

#### 3. Advance

Once images look good, click **Next: Apply Typography →**, or **← Back** to edit image prompts.

---

### Stage 6: Typography & Layout

A deterministic rendering engine lays text over the backgrounds — no AI, pixel-perfect every time.

#### Navigating slides

Click any **thumbnail** at the bottom of the canvas to switch the active slide.

#### Editing text

Click directly on the **title** or **body** text box on the canvas and type to edit. Text is saved automatically.

#### Repositioning text boxes

Click and drag a text box to move it anywhere on the canvas.

#### Resizing text boxes

Drag the **edges** of a text box to resize it. The font size scales automatically to fit (binary search fitting — no text ever overflows).

#### Styling text

Use the **Style Toolbar** above the canvas to adjust font family, weight, text colour, alignment, drop shadow, and stroke properties. Select a text box first, then make toolbar changes.

#### Applying a style to all slides

After styling one slide, click **Apply to All Slides** in the toolbar to copy that style to every slide in the carousel.

#### Exporting

Click **Export ZIP** (top-right) to download a ZIP archive containing:

- All final composited slides as PNG files (1080×1350 px)
- Project metadata

---

### Settings & Configuration

Click the **gear icon** in the top-right header to open the Settings modal.

| Tab | What you can configure |
| :--- | :--- |
| **Prompts** | Edit LLM prompt templates. The backend validates required `{variables}` are preserved before saving. |
| **Instructions** | Pre-seed stage-specific instructions (e.g. always use a certain tone in Stage 2). |
| **Global** | Default slide count, language, and title inclusion. |
| **Image** | Output resolution (default: 1080×1350) and the image model. |
| **Style** | Base typography defaults (font family, colours, stroke). |

Click **Save Changes** to apply. **Reset All to Defaults** (red button) restores factory settings.

---

## Matrix Generation

The Concept Matrix Generator is a fully independent mode — it has its own home screen, project list, settings, and views, all separate from the carousel pipeline.

### Accessing Matrix Generation

On the Lucid home screen, click **Matrix Generation**. You'll see the Matrix workspace with a list of all your past matrices.

### Creating a Matrix

Click **New Matrix**. Choose a generation mode, configure grid size and style, then click **Generate Matrix**.

#### Mode: Theme

Enter a theme string (e.g. *"The philosophy of time and consciousness"*). The AI picks n distinct diagonal concepts from the theme and invents a unique pair of descriptive axes for each concept. It then populates every cell at the intersection of those axes.

- Grid is square: n×n
- Size picker: n ∈ {2, 3, 4, 5, 6}

#### Mode: Description

Describe a cross-axis relationship (e.g. *"feels like a certain generation but is actually from a different one"*). A single LLM call derives both axis labels and n shared labels, producing a rectangular grid.

- Grid is rectangular: rows × columns
- Rows and columns are picked independently from {2, 3, 4, 5, 6}

#### Style Mode

Controls the tone of every cell's content:

| Style | Character |
| :--- | :--- |
| **Neutral** | Balanced, informative |
| **Fun** | Playful, informal |
| **Absurd** | Unexpected, surreal juxtapositions |
| **Academic** | Analytical, precise |

#### Other Options

| Option | Description |
| :--- | :--- |
| **Language** | Output language for cell text |
| **Name** | Optional display name (auto-generated if left blank) |
| **Generate images** | Check to generate a background image for each cell immediately (slower; can be triggered later) |

---

### The Matrix Grid — Cells, Axes, and Streaming

Once generation starts, cells appear in the grid as they complete — you don't wait for the full matrix before reviewing results. The status badge on each matrix card tracks progress: **Pending → Generating → Done / Failed**.

Each cell contains:
- A **title** summarising the intersection
- A **body** with a short explanation or example
- An optional **background image** generated from the cell's content

Axis labels appear along the top row and left column of the grid.

---

### Views

Three views are available from inside any completed matrix:

#### Grid View (default)

Interactive n×n grid with axis labels. Click any cell to expand it and read its full content.

#### Poster View

Full-page visual layout designed for screenshots or sharing. Renders the entire matrix in a clean grid with large axis headers — ideal for exporting as a single image.

#### Reveal View

Presentation mode: cycles through cells one at a time. Use this for storytelling or to walk an audience through the matrix cell by cell.

---

### Adding Images

Images can be added at any point:

- **At creation:** check **Generate images for each cell** in the New Matrix modal.
- **After generation:** click **Generate Images** in the matrix toolbar to bulk-generate images for all cells in parallel.
- **Per cell:** click **Regen** on an individual cell to regenerate only that cell's image.

Image prompts are AI-written from each cell's content, styled to match the matrix's global style mode.

---

### Revalidating a Matrix

If some cells fail (or produce low-quality content), click **Revalidate**. This runs a validation pass that checks every cell, identifies failures or weak outputs, and regenerates only those.

You can supply a **user comment** in the revalidation dialog (e.g. *"cells should be more specific and concrete"*). This text is injected into the validator prompt and used as extra instructions when regenerating failed cells.

Progress streams via SSE, the same way as initial generation.

---

### Matrix Settings

Click **Settings** in the Matrix workspace to configure generation parameters. Changes are persisted in `matrix_settings.json`.

#### Models

| Setting | Description |
| :--- | :--- |
| **Text Model** | Gemini model ID for cell text generation |
| **Image Model** | Gemini model ID for cell image generation |

#### Temperatures

Higher temperature = more creative/unexpected output, lower = more consistent/predictable.

| Setting | Controls |
| :--- | :--- |
| **Diagonal (seed concepts)** | Creativity when picking the n diagonal concepts (theme mode) |
| **Axes (descriptors)** | Creativity when inventing axis labels |
| **Cell (off-diagonal)** | Creativity for the majority of cell content |
| **Validation** | Creativity during the revalidation/regeneration pass |

#### Performance

| Setting | Description |
| :--- | :--- |
| **Max Concurrency** | Number of parallel LLM calls during generation (1–20) |
| **Max Retries** | Automatic retry attempts for failed cells before marking them failed (0–5) |

Click **Save settings** to apply, or **Reset to defaults** to restore factory values.

---

## Tips

- **Use Research for unfamiliar topics.** Stage 1 is powered by Google Search — valuable when you need current statistics, recent news, or want to explore an unfamiliar topic.
- **Start messy in Stage 2.** The Draft AI handles unstructured input well. Don't clean up your draft before pasting.
- **Edit image prompts before generating.** Image generation is the most expensive step. Spend time in Stage 4 to get prompts right before triggering Stage 5.
- **Use "Apply to All Slides" early.** Style one slide to your liking in Stage 6, then apply to all before fine-tuning individual slides.
- **Try different Matrix style modes.** *Absurd* produces the most surprising and memorable grids; *Neutral* gives the most consistent educational output.
- **Use Matrix revalidation iteratively.** After a first revalidate pass, review the grid and run another pass with a more specific user comment if cells are still weak.
- **No API key?** The app still works — images will be gradient placeholders, and you can test the typography/layout stage and matrix grid structure with your own content.
