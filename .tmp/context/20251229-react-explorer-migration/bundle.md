# Task Context: Execute Prompt 002 - React Explorer Migration Plan

Session ID: 20251229-react-explorer-migration
Created: 2025-12-29
Status: in_progress

## Current Request
Run the prompt stored at `./prompts/002-react-explorer-migration-plan.md` as a delegated sub-task. The prompt instructs the agent to read `@MIGRATION_PLAN.md` and produce a detailed implementation plan for migrating AURA-PROTO from Streamlit to a React-based Explorer interface, saving the result to `./plans/react-explorer-migration-plan.md`.

## Requirements
- Load documentation standards to ensure the generated plan matches local docs style.
- Read and follow the XML-structured prompt in `./prompts/002-react-explorer-migration-plan.md`.
- Thoroughly analyze `MIGRATION_PLAN.md` as the primary source.
- Generate a detailed, actionable migration plan document.
- Save the output as `./plans/react-explorer-migration-plan.md` (relative to project root).
- Follow verification and success criteria defined in the prompt.

## Decisions Made
- This task will be executed by a `general` subagent in a fresh context.
- Documentation standards from the local environment must be applied.
- No code changes are to be made; output is documentation only.

## Files to Modify/Create
- Read: `./MIGRATION_PLAN.md` (migration high-level roadmap).
- Read: `./prompts/002-react-explorer-migration-plan.md` (this XML prompt).
- Create/overwrite: `./plans/react-explorer-migration-plan.md` (final detailed plan).

## Static Context Available
- `/c/Users/Peter/.config/opencode/context/core/standards/docs.md` — documentation standards (MUST be applied).
- `/c/Users/Peter/.config/opencode/context/core/workflows/delegation.md` — general delegation workflow (already applied by orchestrator).

## Embedded Context: Documentation Standards

```markdown
<!-- Context: standards/docs | Priority: critical | Version: 2.0 | Updated: 2025-01-21 -->

# Documentation Standards

## Quick Reference

**Golden Rule**: If users ask the same question twice, document it

**Document** (✅ DO):
- WHY decisions were made
- Complex algorithms/logic
- Public APIs, setup, common use cases

**Don't Document** (❌ DON'T):
- Obvious code (i++ doesn't need comment)
- What code does (should be self-explanatory)

**Principles**: Audience-focused, Show don't tell, Keep current

---

## Principles

**Audience-focused**: Write for users (what/how), developers (why/when), contributors (setup/conventions)
**Show, don't tell**: Code examples, real use cases, expected output
**Keep current**: Update with code changes, remove outdated info, mark deprecations

## README Structure

```markdown
# Project Name
Brief description (1-2 sentences)

## Features
- Key feature 1
- Key feature 2

## Installation
```bash
npm install package-name
```

## Quick Start
```javascript
const result = doSomething();
```

## Usage
[Detailed examples]

## API Reference
[If applicable]

## Contributing
[Link to CONTRIBUTING.md]

## License
[License type]
```

## Function Documentation

```javascript
/**
 * Calculate total price including tax
 * 
 * @param {number} price - Base price
 * @param {number} taxRate - Tax rate (0-1)
 * @returns {number} Total with tax
 * 
 * @example
 * calculateTotal(100, 0.1) // 110
 */
function calculateTotal(price, taxRate) {
  return price * (1 + taxRate);
}
```

## What to Document

### ✅ DO
- **WHY** decisions were made
- Complex algorithms/logic
- Non-obvious behavior
- Public APIs
- Setup/installation
- Common use cases
- Known limitations
- Workarounds (with explanation)

### ❌ DON'T
- Obvious code (i++ doesn't need comment)
- What code does (should be self-explanatory)
- Redundant information
- Outdated/incorrect info

## Comments

### Good
```javascript
// Calculate discount by tier (Bronze: 5%, Silver: 10%, Gold: 15%)
const discount = getDiscountByTier(customer.tier);

// HACK: API returns null instead of [], normalize it
const items = response.items || [];

// TODO: Use async/await when Node 18+ is minimum
```

### Bad
```javascript
// Increment i
i++;

// Get user
const user = getUser();
```

## API Documentation

```markdown
### POST /api/users
Create a new user

**Request:**
```json
{ "name": "John", "email": "john@example.com" }
```

**Response:**
```json
{ "id": "123", "name": "John", "email": "john@example.com" }
```

**Errors:**
- 400 - Invalid input
- 409 - Email exists
```

## Best Practices

✅ Explain WHY, not just WHAT
✅ Include working examples
✅ Show expected output
✅ Cover error handling
✅ Use consistent terminology
✅ Keep structure predictable
✅ Update when code changes

**Golden Rule**: If users ask the same question twice, document it.
```

## Constraints/Notes
- Do not modify code files; only create/update the plan markdown file.
- Follow the XML prompt structure in `./prompts/002-react-explorer-migration-plan.md` exactly.
- Use clear headings, numbered steps, and bullets so it can be easily turned into tickets.

## Progress
- [ ] Read docs standards
- [ ] Read MIGRATION_PLAN.md
- [ ] Read prompt 002 XML
- [ ] Draft detailed implementation plan
- [ ] Validate against requirements and success criteria
- [ ] Save to ./plans/react-explorer-migration-plan.md

---
**Instructions for Subagent:**
1. Load the documentation standards from `/c/Users/Peter/.config/opencode/context/core/standards/docs.md`.
2. Read `./MIGRATION_PLAN.md` and `./prompts/002-react-explorer-migration-plan.md` from the project root `D:\Peter\AURA Proto review 1\AURA-PROTO`.
3. Follow the `<objective>`, `<context>`, `<requirements>`, `<implementation>`, `<output>`, `<verification>`, and `<success_criteria>` sections in the prompt file.
4. Create the detailed migration plan as described and save it to `./plans/react-explorer-migration-plan.md`.
5. When finished, respond back with a concise summary (3–7 bullet points) describing the structure and main content of the generated plan.
