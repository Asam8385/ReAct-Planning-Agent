# Acceptance criteria

Scaffold tests verify fixture integrity only. Runtime acceptance
requires implementing and testing the following behaviors.

1. Healthy service completes after verification without recovery.
2. Stopped service recovers through an approved restart.
3. When a restart fails for a configuration fault, the agent replans
   from new evidence and proposes approved configuration restoration.
   A correct initial diagnosis may also restore configuration directly.
4. Persistent fault terminates within two recovery attempts.
5. Rejected approval causes no simulator mutation.
6. A scripted model repeatedly requesting tools cannot exceed budgets.
7. No-progress detection stops repeated ineffective actions.
8. Failed calls, retries and approval resumes preserve task limits.
9. MCP timeouts produce bounded failure or an unconfirmed mutation;
   mutation retries reconcile state instead of duplicating actions.
10. Completion requires an independent healthy result after recovery.
11. Two task IDs never share simulated state.
12. HTTP tool discovery and calls are tested over a localhost socket.
13. Cancellation stops future work and reports the last known state.
14. Direct attempts to bypass approval or use an invalid action fail
    inside the MCP server as well as inside the agent controller.
