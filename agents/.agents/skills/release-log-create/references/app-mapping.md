# App Mapping

Use these default mappings when grouping `script_drop` changes into stakeholder sections.

## Section map

- `Patient App`
  - `apps/patient_app`

- `Pharmacy Admin / Pharmacy API`
  - `apps/pharmacy_admin_web`
  - `apps/pharmacy_api`
  - `apps/pharmacy_api_web`

- `Core / Internal Ops`
  - `apps/core`
  - `apps/core_web`
  - `apps/update_comms`
  - `apps/update_comms_email`
  - `apps/surveys`

- `Courier Tools`
  - `apps/courier_admin_web`
  - `apps/courier_legacy_web`

- `Program Request APIs`
  - `apps/program_request_api`
  - `apps/program_request_api_web`

- `Shared Platform / Security / Reliability`
  - `apps/event_bus`
  - `apps/d0_receiver`
  - `apps/kathy_bot`
  - `apps/prometheus_metrics`
  - `apps/telcom_parser`
  - `apps/xml`
  - cross-cutting commits that touch multiple app groups
  - security or reliability work that impacts more than one surface

## Notes

- If a commit touches one clear app section and also shared infrastructure, prefer the app section.
- If a commit spans multiple user-facing app groups, place it in `Shared Platform / Security / Reliability` unless one audience is clearly primary.
- If the user asks for a narrower audience, filter to the matching sections before drafting.
