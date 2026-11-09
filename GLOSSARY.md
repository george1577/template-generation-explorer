# Template Generation

Template Generation is a design pattern for personalized customer messages: an LLM writes the
messages ahead of time as reusable templates, people review them once, and at send time the only
step is filling in blanks. This glossary covers the words used in the app and its guide.

## The pattern

**Template**:
A complete message written by an LLM ahead of time, with placeholders where the per-customer details go.
_Avoid_: Draft, form letter, prompt template

**Placeholder**:
A marked blank in a template, such as `[CUSTOMER_NAME]`, that gets replaced with a real value at send time.
_Avoid_: Variable, slot, tag, token

**Template key**:
The combination of attributes one template is written for: destination, package type and language (for example Toledo / Family / English).
_Avoid_: Template ID, combination, variant

**Template store**:
The collection of all templates, one per template key, along with each one's review status.
_Avoid_: Database, cache, library

## Review

**Review**:
A person's one-time decision on a template before it can be used. Every template has one of three statuses: pending, approved or rejected.
_Avoid_: Moderation, validation, QA

**Automatic check**:
A rule that flags a likely problem in a template (such as a missing placeholder or a mention of a price) to help the reviewer. It never approves anything on its own.
_Avoid_: Validator, guardrail, test

## Send time

**Fill**:
Replacing each placeholder in an approved template with a customer's value, using plain string replacement. No LLM runs during a fill.
_Avoid_: Render, generate, personalize

**Letter**:
The finished message a customer receives: an approved template after it has been filled.
_Avoid_: Output, response, note

**Live generation**:
The approach the pattern avoids: asking an LLM to write each customer's letter at send time, with no person reviewing it.
_Avoid_: Direct generation, zero-shot letter, on-demand generation
