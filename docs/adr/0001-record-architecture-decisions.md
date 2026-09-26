# ADR-0001: Record architecture decisions

- Status: Accepted
- Date: 2026-09-26

## Context

The library will be maintained in the open, and contributors will ask why it works the way it does. Those
answers should not live only in issue threads or in one person's head.

## Decision

Record each significant decision as a short Markdown file in `docs/adr/`, numbered in order. Each record
has these sections: Status, Date, Context, Options considered, Decision, Consequences, and Related
requirements where they apply.

Status is one of Proposed, Accepted, Superseded by ADR-NNNN, or Rejected. An accepted record is not edited
except to change its status; a new record replaces it.

## Consequences

- Reviewers can check a pull request against the recorded decisions.
- Changing a decision takes a new record, which makes the change and its reasons visible.
