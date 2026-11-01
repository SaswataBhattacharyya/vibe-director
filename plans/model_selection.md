# Director model selection

## Owner request — 2026-10-26

Show the LLM selector on Home, Story, ACE-Step chat and Vibe Editor. Typing `/model` in a chat opens the same list as the dropdown.

## Implemented behavior

- The page header exposes the selector throughout the app, including Home. The old entry point remains the sidebar person icon → Director settings.
- Story collaborator, ACE-Step chat and Vibe Editor each have a nearby picker. `/model` opens it, removes only the command, retains the rest of the draft and makes no chat request. Enter in the model search does not submit the enclosing chat form.
- Model selection is shared across pages and persisted on the server with revision checks. Codex reasoning depth is selectable. Saved Director lessons remain intact. This selects the reasoning LLM, not the ACE-Step music weights or a ComfyUI model.
- Codex entries come from the installed account's model cache. Ollama entries come from the configured server's installed-model list. OpenCode entries come from its configured provider catalog. An OpenCode alias to an uninstalled local model is disabled. Catalog discovery performs no inference; its cache lasts up to one minute.
- OpenCode uses its existing API credentials/configuration (`opencode auth login`). No API credentials enter browser drafts. Provider availability means the catalog was found, not that paid quota, image support or inference quality has been validated.
- Story graph, screenplay and editing requests now honor the selected provider rather than forcing Codex. ACE-Step and Vibe Editor already use the shared structured reasoning adapter. Required JSON schemas are retained. Local requests reuse the existing GPU admission guard and unload Ollama after the request. OpenCode runs without tool permissions, in an isolated temporary working directory.
- A provider explicitly pinned by an existing run retains that provider's last saved model profile. An in-flight inference keeps its original request. Changes apply to subsequent requests; this does not promise a frozen model snapshot for every future stage of a long-running job.

## Checks and owner acceptance

Focused CPU tests cover persistence, stale/invalid choices, provider routing, existing Codex image handling, OpenCode permissions/schema checks and Ollama admission/image inputs. Browser fixtures cover shared selection and `/model` in all three chats without inference. Live inspection checks only catalog rendering. No paid, local inference or GPU generation tests were run.

Owner: refresh the page, choose a model and click **Use model**, then send a small chat request when ready. New providers still require real inference acceptance; a listed model can reject unsupported image/schema inputs. Existing project-wide testing/Git restrictions remain in force. This bounded owner request supersedes the earlier deferral of non-Codex adapter work.
