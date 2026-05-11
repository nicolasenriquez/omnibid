# Motion Standards

## Purpose

Motion should clarify state changes and hierarchy. It should not be decorative.

## Rules

- Prefer the shared motion tokens in `tokens.css`.
- Keep most transitions under 300ms.
- Use motion for:
  - hover and press feedback
  - loading and progress indication
  - reveal and containment changes
  - state confirmation
- Avoid animations that do not communicate meaning.
- Respect reduced-motion preferences.

## Recommended Defaults

- Fast interactions: 120ms
- Standard component transitions: 180ms
- Slower structural transitions: 240ms
- Use the standard easing curve unless there is a clear reason not to.

## Patterns

- Use subtle opacity and transform changes for entry and exit.
- Use progress motion for asynchronous work.
- Use animation only when it improves legibility of the workflow.
