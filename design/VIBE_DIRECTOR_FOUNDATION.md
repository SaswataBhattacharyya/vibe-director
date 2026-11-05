# Vibe Director design foundation

This document accompanies the [interactive workspace prototype](prototypes/vibe-director-flow-proposal.html) and [interactive Clapper character sheet](prototypes/vibe-director-mascot-sheet.html). It provides general visual and interaction guidance. The prototypes are local simulations, not production implementations or evidence of user testing. Current user requests govern redesign; these examples do not freeze routes, layouts or terminology.

## Intended experience

Vibe Director should feel like a creative studio with a distinct personality while keeping the work surface calm. A creator should always know where they are, what action comes next, what a video request contains, and whether a take is merely generated or has been accepted. The emotional goals are authored energy at entry, control during editing, and confidence when recovering or reviewing work. These are design hypotheses to test, not claims of measured user sentiment.

## Visual foundation

- Dark canvas, restrained comic expression and rounded Nunito typography. Use Nunito Bold 700 for headings and controls, Regular 400 for longer copy. The font files and license are bundled beside the prototypes.
- **Concrete & ink** and **Midnight mixtape** are palette examples in the prototype. They do not require removing other production themes. Verify actual theme controls and persistence in the app before changing them.
- Concentrate character in the brand and key transitions. Use flat, readable editor surfaces, visible focus, clear selected states, and adequate control contrast. Avoid repeated cards, decorative labels, and long explanations around every action.

| Role | Concrete & ink | Midnight mixtape |
| --- | --- | --- |
| Canvas | `#090A0C` | `#110C1E` |
| Surface | `#191A1D` | `#211831` |
| Text | `#F8F2E7` | `#F8F1FF` |
| Primary action | `#F28E5D` | `#F5C65C` |
| Focus | `#F8DC91` | `#78D6FF` |
| Warning | `#F1C078` | `#FFD779` |
| Error | `#F29E99` | `#FFAAA7` |

The full role tokens are in the prototype CSS. Before production adoption, check rendered contrast in both palettes, keyboard focus, narrow layouts, zoom/reflow, long content, and reduced motion. Colour alone must not distinguish a state.

## Navigation and working surface

- The sidebar names destinations. Horizontal numbered tabs show the creative sequence. Local tabs such as Create and Current take switch panels within Video. The current location must stay selected across the relevant navigation levels, including Screenplay and Current take.
- Distinguish sidebar section headings from playable links. The sidebar remains in place while the work area scrolls. Projects appear below Resources with an Add project affordance. In the prototype, added names are browser-only previews and do not create project workspaces.
- Place the profile **icon only** beside the Vibe Director wordmark. It opens a compact popover for profile details and settings; the palette switcher lives there. Clapper has its **own space at the bottom** of the sidebar, with a drop shadow and no visible caption.
- The bottom taskbar keeps project/clip context, preview controls, and the next action available while editing. Preview controls are explicitly a simulation and should not be mistaken for production engine controls.
- Keep the primary action after its required inputs. Show a readiness blocker beside Generate. Preserve an editable draft separately from the submitted request, generated take, and accepted take. Retake returns to editing without submitting. Uncertain submission status requires recovery of the existing request before retrying.

The application shell is implemented in `frontend/src/StudioShell.tsx`, `frontend/src/App.tsx` and `frontend/src/style.css`. Adapt the actual components while preserving working backend contracts. See the [functionality audit](../audit/FUNCTIONALITY_AUDIT.md) for the source map; the prototypes provide visual examples.

## Clapper, the visual companion

Clapper is a clapperboard with small expressive eyes. It has no mouth or text caption. Its hinge, tilt, eye direction, timing, and posture carry personality. The character sheet is interactive: replay each moment to see the intended motion. The app prototype shows Clapper in the sidebar and changes its moment with the route or relevant job state.

| Moment | Emotional job | Motion cue |
| --- | --- | --- |
| Hello | Welcome without interruption | Brief playful tilt and hinge greeting; no state icon |
| Waiting | Show that work is underway | Slower lean and gaze scan; the optional hourglass turns 180° **inside** its own icon space |
| Ready | Invite the next deliberate action | Lively hinge lift and forward attention |
| Confirmed | Acknowledge a completed decision | One clear clap and settle |
| Attention | Help the creator notice a blocker | Tilt, softened eyes, and a restrained icon cue |

State icons are optional companions, not part of Clapper's body; Clapper must make sense without them. Motion should be tied to a real state transition or explicit replay, never imply false generation progress. Respect `prefers-reduced-motion`: the state, labels, and controls remain understandable without animation. The mascot must not cover inputs, pull focus from an error, or become the only source of status information.

## Language and proof

Use the creator's vocabulary: story, screenplay, video draft, prompt, take. Prefer direct actions such as “Check readiness”, “Generate video”, and “Edit request”. Status text says what happened and what the creator can do next. Creative wit belongs in the brand and optional moments; errors and recovery stay plain. Never claim a request was sent, saved, or generated without confirmation from the real app.

The HTML can be opened locally or served from the repository root. It simulates draft, readiness, request, take, and recovery states; it does not call a model, create a real project, or prove backend readiness. The character sheet is also a prototype. Production application work should verify navigation, profile popover, taskbar, real project creation, truthful status, persistence, keyboard use, responsive behavior, and a screen-reader walkthrough against the actual app before treating this foundation as implemented.
