A comment is a note in the source for humans. The compiler ignores it.

Two styles
- `//` single-line: ignore from `//` to the end of the line. Best for a short note about one line. Put it above the line if the line is long; align comments to the right only when lines are short.
- `/* ... */` multi-line (C-style): ignore everything between the markers.

Multi-line comments do not nest. The first `*/` ends the comment. A second `/*` inside is ignored as text, so leftover code after the first `*/` will try to compile.

Warning: do not put `/* */` inside another `/* */`. Wrapping `//` comments inside a multi-line comment is fine.

What / how / why
- Library, program, or function: comment **what** it does (top of file, or just before the function).
- Inside that unit: comment **how** it will do it, if the approach is not obvious.
- At the statement level: comment **why**, not what. If you need a comment to explain what a line does, rewrite the line.

Bad: `// Set sight range to 0` above `sight = 0;`
Good: `// The player drank a blindness potion`

Comment as if the reader has never seen the code. You will forget why you chose one approach over another.

Commenting out
Turning code into a comment so it is not compiled. Uses:
- New code that does not compile yet, but you still need to run the rest.
- Broken code you will fix later.
- Isolating a bug by disabling pieces.
- Keeping the old version around until the replacement works.

Prefer `//` for real comments so you can always wrap a block in `/* */` without a nesting conflict. To disable a block that already has `/* */` comments, `#if 0` (covered later) is the safer tool.

Best practice: comment liberally, in human language, for someone who does not know the code.
