# Project 5 - context window management
#
# All of these run in ONE session. Do not reset history between turns.
# Set your limit low (for example 8 messages) so trimming actually happens.

# TEST_CASES = [
#     # POINT: normal turn, history is still small, no trim yet
#     # EXPECT: 5.0 and no trim message printed
#     "Divide 10 by 2.",

#     # POINT: grow the history with another tool call
#     # EXPECT: HELLO AGENTIC WORLD
#     'Convert "hello agentic world" to uppercase.',

#     # POINT: pronoun reference, proves memory still works before trimming
#     # EXPECT: 3 words
#     "How many words was that?",

#     # POINT: this turn should push history over the limit and trigger the trim
#     # EXPECT: 8.0 plus a printed line showing how many messages were dropped
#     "Divide 40 by 5.",

#     # POINT: the cut must not split a function_call from its output
#     # EXPECT: no API error - this is the test that catches an unsafe cut point
#     "Divide 100 by 4.",

#     # POINT: forgetting works as designed
#     # EXPECT: the agent cannot recall it, and says so - this is CORRECT
#     "What was my very first question?",

#     # POINT: recent memory must still work after trimming
#     # EXPECT: 25.0 referenced from the previous turn
#     "What was the last result?",

#     # POINT: keep pushing so the trim runs several times, not just once
#     # EXPECT: 12.5, history stays at or under the limit
#     "Divide that by 2.",

#     # POINT: error path still works while trimming is active
#     # EXPECT: division by zero error handled, still no crash
#     "Divide 7 by 0.",

#     # POINT: recovery still works with a trimmed history
#     # EXPECT: 3.5
#     "Use 2 instead.",
# ]

TEST_CASES = [
    # 1. This will be pushed out of the window later.
    #    EXPECT: HELLO AGENTIC WORLD
    'Convert "hello agentic world" to uppercase.',
    # 2-4. Filler to force trimming.
    "Count the words in: one two three four five.",
    "Convert this to uppercase: filler text.",
    "Count the words in: alpha beta gamma.",
    # 5. CONTROL - the answer is still inside the window.
    #    EXPECT: it answers correctly. Proves rule 8 didn't make it over-cautious.
    "What did I just ask before this?",
    # 6. THE TEST - the answer was trimmed away.
    #    EXPECT (new): "I don't know / that part was removed"
    #    BEFORE:       a confident wrong answer
    "What was my very first question?",
]
