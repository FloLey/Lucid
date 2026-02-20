# Lucid — User Guide

This guide walks you through creating a complete social media carousel from a rough draft to a ready-to-export ZIP of slides.

---

## Prerequisites

- Lucid is running (see [Installation](../README.md#installation--requirements))
- You have a Google API key configured (required for AI features)
- The app is open at `http://localhost:5173`

---

## Overview

Lucid uses a 5-stage pipeline. Each stage builds on the last, and you can always step **backward** to revise without losing downstream work.

```
Stage 1: Draft → Stage 2: Style → Stage 3: Image Prompts → Stage 4: Images → Stage 5: Typography
```

---

## Stage 1: Draft

### 1. Paste your draft

Click the **Your Draft** text area and paste your raw content. It can be anything — bullet points, stream-of-consciousness notes, an existing article. Lucid will restructure it into slides.

### 2. Configure generation

| Option | Description |
| :--- | :--- |
| **Number of Slides** | Pick a fixed count (3–10) or choose **Auto** to let the AI decide. |
| **Language** | Output language for slide text (defaults to English). |
| **Include Titles** | Toggle whether each slide gets a title. |
| **Additional Instructions** | Optional free-form guidance, e.g. *"Make it conversational, target entrepreneurs"*. |

### 3. Generate slides

Click **Generate Slides**. The right panel will populate with a card per slide showing its title (if enabled) and body text.

### 4. Review and edit

Each slide card offers two actions:

- **Edit** — Opens an inline editor. Modify the title and/or body text, then click **Save** (or **Cancel** to discard).
- **Regenerate** — Expands an instruction input. Type an optional instruction (e.g. *"Make this punchier"*) and press **Enter** or click **Go** to regenerate just that slide.

When you're happy with the slide text, click **Next: Choose Style →**.

---

## Stage 2: Style Proposals

Lucid generates visual style proposals based on your slide content. All images generated later will follow the style you pick here, ensuring a coherent look across the carousel.

### 1. Configure proposals

| Option | Description |
| :--- | :--- |
| **Number of Proposals** | Choose 2, 3, or 4 style proposals to generate. |
| **Additional Instructions** | Optional style guidance, e.g. *"Warm colors, minimalist, professional photography"*. |

### 2. Generate proposals

Click **Generate Style Proposals**. Each proposal card shows a preview image and a text description of the visual style.

### 3. Select a style

Click a proposal card to select it — it will highlight with a blue border and a **Selected** badge. You must select a style before advancing.

Click **Next: Image Prompts →** (top-right of the panel) when ready, or **← Back** to revise your slides.

---

## Stage 3: Image Prompts

Instead of generating images immediately, Lucid first writes a specific, text-free image prompt for each slide. This lets you review and refine what will be generated before spending API calls on images.

### 1. Optionally add image style instructions

The **Image Style Instructions** field lets you add extra guidance on top of the chosen style (e.g. *"Always include natural light, avoid people"*).

### 2. Generate prompts

Click **Generate Image Prompts**. Each slide gets an individual prompt. A **Shared Style prefix** box (in blue) shows the common style context prepended to every prompt.

### 3. Review and edit prompts

Each prompt card offers:

- **Edit** — Opens a textarea to rewrite the prompt manually. Click **Save** when done.
- **Regenerate** — Asks the AI to rewrite just that prompt (keeps the shared style prefix).

Once you're satisfied with all prompts, click **Next: Generate Images →**, or **← Back** to revisit style proposals.

---

## Stage 4: Image Generation

Lucid sends all image prompts in parallel to Gemini and displays the results.

### 1. Generate images

Click **Generate Images**. A spinner appears over each slide thumbnail while it loads. Generation runs concurrently — all slides process at the same time.

### 2. Regenerate individual images

If a specific background doesn't look right, click **Regen** next to that slide to regenerate it alone without touching the others.

### 3. Advance

Once images look good, click **Next: Apply Typography →**, or **← Back** to edit image prompts.

---

## Stage 5: Typography & Layout

This is where your slides come together. A deterministic rendering engine lays text over the backgrounds — no AI involved, pixel-perfect every time.

### Navigating slides

Click any **thumbnail** at the bottom of the canvas to switch the active slide.

### Editing text

Click directly on the **title** or **body** text box on the canvas and type to edit. Text is saved automatically.

### Repositioning text boxes

Click and drag a text box to move it anywhere on the canvas.

### Resizing text boxes

Drag the **edges** of a text box to resize it. The font size scales automatically to fit the available space (binary search fitting — no text ever overflows).

### Styling text

Use the **Style Toolbar** above the canvas to adjust:

- Font family and weight
- Text color
- Alignment (left / center / right)
- Drop shadow and stroke properties
- Vertical position presets

Select a text box (title or body) first, then make toolbar changes — they apply to the selected box on the active slide.

### Applying a style to all slides

After styling one slide exactly how you want, click **Apply to All Slides** in the toolbar. This copies the current slide's style settings to every slide in the carousel.

### Exporting

Click **Export ZIP** (top-right) to download a ZIP archive containing:

- All final composited slides as PNG files (1080×1350 px)
- Project metadata

---

## Settings & Configuration

Click the **gear icon** in the top-right header to open the Settings modal. Changes here affect the defaults for new projects.

### Tabs

| Tab | What you can configure |
| :--- | :--- |
| **Prompts** | Edit the LLM prompt templates used at each stage. The backend validates that required `{variables}` are preserved before saving. |
| **Instructions** | Pre-seed stage-specific instructions (e.g. always use a certain tone in Stage 1). |
| **Global** | Default slide count, language, and title inclusion. |
| **Image** | Output resolution (default: 1080×1350) and the image model. |
| **Style** | Base typography defaults (font family, colors, stroke). |

Click **Save Changes** to apply. Use **Reset All to Defaults** (red button) to restore factory settings — a confirmation dialog will appear first.

---

## Tips

- **Start messy.** The Stage 1 AI is designed to handle unstructured input. Don't clean up your draft before pasting — let Lucid do the restructuring.
- **Edit prompts before generating images.** Image generation is the most expensive step. Spend time in Stage 3 to get prompts right before triggering Stage 4.
- **Use "Apply to All Slides" early.** Style one slide to your liking in Stage 5, then apply to all before fine-tuning individual slides.
- **No API key?** The app still works — images will be gradient placeholders, and you can test the typography/layout stage with your own content.
