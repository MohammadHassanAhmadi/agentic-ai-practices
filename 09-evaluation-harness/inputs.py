# =============================================================
# GROUP A - run these as they are. No code changes.
# Run in order. Test 0 creates the file the others need.
# =============================================================

NOTES_CONTENT = """Our team spent Q1 on the payment service migration. We moved 40 percent
of traffic to the new gateway and cut average latency from 800ms to 310ms.
Two incidents happened during the rollout, both caused by missing retry
logic on timeout.

For Q2 the budget is tight. We have approval for two contractors, not the
four we asked for. The plan is to finish the migration first, then start
the reporting rewrite in Q3.

The main risk is the legacy database. Nobody on the current team wrote it,
and the documentation is three years out of date."""

TESTS_A = [
    # 0. Setup. Orchestrator must write this itself.
    #    Watch: no [reader] line appears.
    f"Write a file called notes.txt with this content:\n\n{NOTES_CONTENT}",
    # 1. Happy path. THE MAIN TEST.
    #    Watch: orchestrator history holds ONE tool result, not the file content.
    "Read notes.txt and write a 3-bullet summary of it into summary.txt",
    # 2. Search through the worker.
    #    Watch: real matches, because notes.txt contains "budget".
    "Search all files for the word 'budget' and summarise what you find",
    # 3. Unknown agent name.
    #    Watch: INVALID_ARGUMENTS envelope, no crash, no retry loop.
    "Delegate this task to an agent called 'writer': create a poem file",
    # 4. Worker cannot write.
    #    Watch: worker refuses; orchestrator writes it itself or explains.
    "Ask the reader agent to write hello.txt",
    # 5. Missing file. COMPLETED, not FAILED.
    #    Watch: orchestrator reports it and does not retry.
    "Read missing.txt and tell me what is inside",
    # 6. Approval gate. Answer "no".
    #    Watch: orchestrator stops, does not work around it.
    "Delete summary.txt",
    # 7. Approval gate. Answer "yes". RUN LAST - deletes notes.txt.
    "Delete notes.txt",
]


# =============================================================
# GROUP B - each needs ONE temporary change. Undo it after.
# Run each on its own.
# =============================================================

TESTS_B = [
    # 8. Child hits its iteration cap.
    #
    #    CHANGE:  in call_sub_agent, set  max_iterations=1
    #    UNDO:    set it back to MAX_TRY_ATTEMPT
    #
    #    Watch: worker STOPPED -> {"ok": false} -> orchestrator explains.
    #           No crash. It retries at most once with a different task.
    "Search all files for 'budget' and tell me which file each match is in",
    # 9. Depth cap blocks nested delegation.
    #
    #    CHANGE:  add CALL_SUB_AGENT_SCHEMA to READER_TOOL_SCHEMAS
    #    UNDO:    remove it again
    #
    #    Watch: DELEGATION_NOT_ALLOWED comes from your depth check,
    #           not from the model choosing not to try.
    "Ask the reader agent to delegate reading notes.txt to another reader agent",
    # 10. A crashing agent returns FAILED, not an exception.
    #
    #     CHANGE:  in run_agent, right after the client.responses.create call,
    #              add:  raise RuntimeError("boom")  when depth == 1
    #     UNDO:    remove that line
    #
    #     Watch: worker -> FAILED -> AGENT_ERROR envelope.
    #            The orchestrator keeps running. The app does not crash.
    "Read notes.txt and tell me what it says",
]
