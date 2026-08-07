TEST_CASES = [
    # Setup
    "Create notes.txt with the content: hello agentic world",
    # Normal case, structured result
    "What files exist, and how big are they?",
    # Validation failure - empty path
    "Read the file with an empty name",
    # Error code - file does not exist
    "Read missing.txt",
    # Sandbox - now a code, not a crash
    "Read the file ../.env",
    # Truncation - create a big file by hand in workspace/ first
    "Read big.txt and tell me if you got all of it",
    # Structured list output
    "Search all files for the word hello",
]
