from pathlib import Path
from tempfile import TemporaryDirectory

import memory


def main() -> None:
    with TemporaryDirectory() as sandbox:
        memory.MEMORY_FILE = Path(sandbox) / "memories.json"

        # File does not exist yet
        assert memory.load_memories("hassan") == []

        # Save
        saved = memory.save_memory(
            "hassan",
            "User prefers dark mode.",
        )

        assert memory.MEMORY_FILE.exists()
        assert len(memory.load_memories("hassan")) == 1

        # Duplicate
        duplicate = memory.save_memory(
            "hassan",
            "  USER PREFERS DARK MODE.  ",
        )

        assert duplicate.id == saved.id
        assert len(memory.load_memories("hassan")) == 1

        # User isolation
        memory.save_memory(
            "sanaz",
            "User prefers Persian responses.",
        )

        assert len(memory.load_memories("hassan")) == 1
        assert len(memory.load_memories("sanaz")) == 1

        # Update
        updated = memory.update_memory(
            user_id="hassan",
            memory_id=saved.id,
            new_content="User prefers light mode.",
        )

        assert updated is not None
        assert updated.id == saved.id
        assert updated.content == "User prefers light mode."
        assert len(memory.load_memories("hassan")) == 1

        # Delete
        assert memory.delete_memory("hassan", saved.id) is True
        assert memory.delete_memory("hassan", saved.id) is False
        assert memory.load_memories("hassan") == []

        # Sanaz memory must remain
        assert len(memory.load_memories("sanaz")) == 1

        print("All sandbox memory tests passed.")


if __name__ == "__main__":
    main()
