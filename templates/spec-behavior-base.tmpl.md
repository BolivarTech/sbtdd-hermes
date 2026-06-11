# Spec-Behavior Base

<!-- replace: short project / feature name -->
**Feature:** `<feature-name>`

---

## Objective

<!-- replace: one or two sentences describing WHAT this feature does and WHY it is needed -->
> This feature allows `<actor>` to `<action>` so that `<business value>`.

---

## Requirements (SDD)

<!-- replace: add one bullet per functional requirement; remove example bullets -->
- The system SHALL `<requirement 1>`.
- The system SHALL `<requirement 2>`.

**Example (remove this block):**
- The system SHALL validate user credentials before granting access.
- The system SHALL return an error message when login fails.

---

## Scenarios (BDD)

<!-- replace: duplicate the scenario block below for each acceptance scenario -->

### Scenario: `<scenario title>`

**Given** `<initial context or precondition>`
**When** `<action taken by the actor>`
**Then** `<expected observable outcome>`

**Example scenario (remove this block):**

### Scenario: Successful login

**Given** a registered user with valid credentials
**When** the user submits the login form
**Then** the system grants access and redirects to the dashboard

---

## Constraints

<!-- replace: technical, regulatory, or environmental limits that MUST be respected -->
- `<constraint 1>` (e.g., response time < 200 ms)
- `<constraint 2>` (e.g., must run on Python 3.11+)

---

## Non-goals

<!-- replace: explicitly list what this feature does NOT cover to prevent scope creep -->
- `<non-goal 1>` (e.g., password reset flow is out of scope)
- `<non-goal 2>` (e.g., multi-factor authentication is not included in this iteration)
