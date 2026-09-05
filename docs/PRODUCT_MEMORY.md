# PhoneCodex Product Memory

This file stores the product direction so future coding stays connected to the bigger idea.

## Core Vision

PhoneCodex is not just an app blocker. It is an AI-managed phone environment where the user describes an intention, and the phone reshapes itself into a safer, more focused world.

The long-term idea has two connected products:

1. **AI Phone Assistant**
   - User talks or types a task.
   - AI helps operate or configure the phone with permission.
   - This is later and needs careful control surfaces such as intents, deterministic accessibility, ADB/Shizuku, Device Owner, or future OS-level APIs.

2. **Parallel Focus Worlds**
   - User enters a constrained phone world.
   - Distractions are removed or delayed.
   - Useful tools remain available.
   - Exit can be intentionally difficult, but never unsafe.

## World Types

### Normal World

AI acts like a soft helper and coach.

- Warn gently.
- Suggest better action.
- Organize tasks.
- Reduce distractions softly.
- No hard blocking by default.

### Study World

AI checks whether phone activity matches the study goal.

Example: user says, “I need to study DSA for 2 hours. Allow YouTube lectures, browser search, and family calls.”

Expected behavior:

- YouTube lecture: allow.
- YouTube Shorts: warn.
- Repeated Shorts: block.
- Chrome docs/search: allow.
- Chrome porn/random entertainment: block.
- Instagram notification: hide or delay.
- Important call/message: allow.
- Random chat: delay or ask.

### Deep Work World

Stronger than Study World.

- Only pre-approved apps/tools.
- Less asking.
- More blocking.
- Designed for serious building, coding, writing, or exams.

### Strict Lock World

AI becomes guard.

- Escape is hard until timer ends.
- Emergency exit must always exist.
- Break flow requires friction: wait, reason, accountability, or pre-consented penalty.
- Never block emergency calls or critical safety paths.

### Recovery World

After failure, AI helps restart instead of shaming the user.

- Explain what happened.
- Reduce guilt.
- Restart with a smaller focus session.
- Learn temptation patterns.

## Product Rule

PhoneCodex should use commitment mechanisms, not traps.

Good:

- User pre-consents before entering strict mode.
- Emergency exit is always available.
- Normal exit waits until timer or requires friction.
- AI explains decisions.

Bad:

- No exit at all.
- Blocking emergency use.
- Forcing payment without safety path.
- Letting AI directly do dangerous actions.

## Architecture Principle

```text
classifier suggests -> PolicyEngine decides -> overlay executes -> log records
```

AI is advisor.
PolicyEngine is law.
Overlay is hand.
Log is witness.

## Current Build Meaning

The current Android app is only the foundation.

- Session = which world is active.
- Policy = rules of that world.
- UI = visible control panel.
- Accessibility later = detects current app/screen.
- Overlay later = enforces decisions.
- AI later = understands messy context like YouTube lecture vs Shorts.

## Build Order

1. Start/stop Study World.
2. Test PolicyEngine manually from UI.
3. Add real package detection with AccessibilityService.
4. Feed detected package into PolicyEngine.
5. Show overlay when decision is BLOCK/LOCK.
6. Add attempt counting and event log.
7. Add notification handling.
8. Add AI classifier for conditional content.
9. Add stricter exit mechanisms.
10. Explore PhoneCodex operator layer separately.

## Important Future Ideas

- Adaptive strike system.
- Accountability friend.
- Paid escape or donation penalty, only with pre-consent.
- AI daily debrief.
- Allowed-path suggestions.
- Focus pet/companion.
- Personal temptation profile.
- App install gate later.
- Phone operator layer later.
- Soft parallel world first, hard OS/profile world later.

## MVP Truth

The first real demo is:

```text
Start Study World -> open Instagram -> detect package -> PolicyEngine says BLOCK -> overlay appears -> attempt is logged
```

Until this works on the real phone, do not overbuild AI, cloud, payments, mascot, or OS-level dreams.

## Important Reminder: Inside-App Control

PhoneCodex should not only block entire apps. Many users still need parts of distracting apps.

Example:

- Instagram posts/messages may be allowed.
- Instagram Reels should be blocked during a chosen world.
- YouTube lectures may be allowed.
- YouTube Shorts should be blocked.
- Chrome documentation/search may be allowed.
- Chrome adult/random entertainment should be blocked.

This makes PhoneCodex useful beyond students. It can help anyone reshape app behavior around their intention instead of deleting the whole app.

## AI Promise Memory

The AI should remember the user's pre-commitment for the active world.

Example:

User says: "For the next 8 hours, do not allow Reels. I can use Instagram only for messages and normal posts."

During the world:

- If user opens messages/posts: allow.
- If user opens Reels: warn/block.
- If user asks AI to allow Reels during strict mode: AI should remind them of the promise instead of obeying immediately.
- In normal mode, AI can be softer and allow changes more easily.
- In strict mode, changing rules requires friction or waiting until the world ends.

This is the difference between a dumb blocker and an AI-managed parallel phone world.

## Product Principle

Do not think only in app names. Think in behavior and intent inside apps.

```text
same app + useful intent = allow
same app + distraction intent = warn/block
same app + strict promise broken = lock/friction
```

## Future Idea: Visual Context Understanding

Current PhoneCodex mostly understands the screen through Accessibility text:

- app package name
- visible text
- button labels
- content descriptions
- occasional titles or metadata

This is weak for video-heavy content. A user may open a movie, reel, or distracting video where the visible text still looks study-related, or where no meaningful text is exposed at all.

Future direction:

- Add optional visual understanding for video/content screens.
- Capture a privacy-safe screenshot or frame only after user pre-consent.
- Send the image to a vision model or on-device classifier.
- Decide whether the visual content matches the active world goal.
- Combine signals instead of trusting only one source.

Mental model:

```text
package name = where are we?
accessibility text = what does the UI say?
visual frame = what is actually being watched?
audio/transcript later = what is being said?
policy = final decision
```

This could become a major differentiator because most blockers only know app names, and even smarter blockers often rely on text or URLs. PhoneCodex should eventually understand the actual activity happening inside the app.

Safety rule:

- Visual capture must be opt-in.
- Do not collect sensitive screens by default.
- Never capture banking, OTP, password, private messages, or emergency screens.
- Prefer on-device filtering before any cloud call.

## Future Idea: Permanent Guardrails

PhoneCodex should support two different kinds of control:

1. **Session Worlds**
   - Temporary modes like Study World, Deep Work World, Monk Mode, Sleep World.
   - User enters for minutes/hours/days.
   - Rules depend on current goal.
   - Example: during Study World, YouTube lecture is allowed but Shorts is blocked.

2. **Permanent Guardrails**
   - Long-term bans independent of focus sessions.
   - Always active, even in Normal World.
   - Designed for things the user wants removed from life for a long period.
   - Example: block porn for 1 year while the rest of the phone stays normal.

This is important because not every restriction is about studying. Some restrictions are identity-level commitments.

Example:

```text
Permanent layer: porn blocked for 1 year
Normal World: everything else normal
Study World: extra study-specific rules
Deep Work World: stricter work-only rules
```

Decision order should eventually become:

```text
Emergency/safety allow
-> Permanent Guardrails
-> Active World rules
-> App/content signals
-> Feedback memory
-> AI
-> Policy final decision
```

Product insight:

- Focus Worlds are for temporary intention.
- Permanent Guardrails are for long-term self-protection.
- Both can coexist.
- This can make PhoneCodex useful not only for productivity, but for serious habit change.

## Long-Term Life Rules

PhoneCodex should support rules that are independent of a short focus session.

Current Study World is temporary:

```text
for 2 hours -> block shorts -> then session ends
```

But some rules are identity-level commitments:

```text
for 1 year -> do not allow porn-related content anywhere
```

This should become a separate layer called Life Rules or Core Promises.

Difference:

- Focus Session: temporary, goal-based, adjustable before/during the session depending on strictness.
- Life Rule: long-term, always active, harder to bypass, not tied to Study World.

Example:

User says: "For the next 1 year, I do not want porn on my phone at any cost."

PhoneCodex converts that into:

- duration: 1 year
- category: adult / porn
- scope: all modes, including normal mode
- enforcement: block or lock, not just warn
- change rule: cannot be removed instantly; requires waiting period, accountability, or recovery flow

This creates a layered policy system:

```text
Emergency allowlist
    > Life Rules / Core Promises
        > Current Focus World rules
            > AI suggestions
                > Overlay action
```

Meaning: AI can suggest, but it cannot override a long-term promise casually.

Why this matters:

Many blockers only work during focus time. PhoneCodex should also protect the user from behaviors they have already decided are not part of their life. This is not only productivity; it is self-governance.

Important product warning:

Long-term rules must still avoid trapping the user dangerously. Always allow emergency, phone, essential settings/recovery, and safe account recovery. Strong does not mean unsafe.

## Strict Zone Recovery

Locked and strict Study World sessions need a humane recovery path, not a no-exit trap.

Principles:

- No no-exit traps. Emergency and safety paths stay available.
- The user chooses any break fee before entering the commitment, not as a surprise mid-lock.
- Emergency override stays free. Never charge for safety.
- Real payment or donation flows come later. v0 only models the policy; it does not charge money.

Default recovery policy (v0 model):

- Mistake window: 10 minutes to undo an accidental lock or strict entry.
- Cooldown: 24 hours before another early exit is allowed.
- Trusted admin: optional later; off by default in v0.
- Break fee: optional later; disabled in v0 until user pre-consents before commitment.
- Emergency override: always allowed.

This layer defines how locked sessions are recovered later without weakening active blocking during the session.
