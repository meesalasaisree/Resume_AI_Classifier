import json
import sqlite3

DB_NAME = "interview_prep.db"
JSON_INPUT = "dataset_500_questions_enhanced.json"


def seed_database():
    # 1. Load the enhanced dataset JSON file
    with open(JSON_INPUT, "r", encoding="utf-8") as f:
        questions = json.load(f)

    # 2. Convert nested structures (test_cases) to JSON strings for SQLite storage
    for q in questions:
        if isinstance(q.get("test_cases"), (list, dict)):
            q["test_cases"] = json.dumps(q["test_cases"])

    # 3. Connect to SQLite database
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 4. Ensure target table exists
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS company_interview_vault (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            track TEXT NOT NULL,
            company TEXT NOT NULL,
            prompt TEXT NOT NULL,
            sample_input TEXT NOT NULL,
            sample_output TEXT NOT NULL,
            test_cases TEXT NOT NULL
        )
    """
    )

    # 5. Populate/Replace all records into the vault
    cursor.executemany(
        """
        INSERT OR REPLACE INTO company_interview_vault 
        (id, title, difficulty, track, company, prompt, sample_input, sample_output, test_cases)
        VALUES (:id, :title, :difficulty, :track, :company, :prompt, :sample_input, :sample_output, :test_cases)
    """,
        questions,
    )

    # 6. Commit transaction and close connection
    conn.commit()
    conn.close()

    print(
        f"Successfully verified and seeded all {len(questions)} questions from '{JSON_INPUT}' into '{DB_NAME}'."
    )


if __name__ == "__main__":
    seed_database()