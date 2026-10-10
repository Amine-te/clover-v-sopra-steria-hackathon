# 012 AgentCore deployment (optional, last)

- **Status:** Draft
- **Owner:**
- **Needs:** 009

## Summary

Hosts the Strands agent on AWS AgentCore. If permissions block it, it stays in the architecture slide as the target.

## Inputs and outputs

- In: the working agent from 009.
- Out: the agent running on AgentCore and called from the app.

## Acceptance criteria

- **F012-AC1:** Given the needed permissions, when deployed, then the app calls the hosted agent and gets the same results as locally.
- **F012-AC2:** Given no permissions, when checked, then the local agent remains the demo path.

## Open questions

- Are AgentCore permissions available (see `open-questions.md`, 5)?
