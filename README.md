# Resume AI Classifier

A Streamlit web application that helps with resume screening and interview preparation using AI. It includes a question dataset, coding-question ingestion scripts and an AI-based grading/evaluation feature.

## Project Structure

| File | Purpose |
|------|---------|
| `web_app.py` | Main Streamlit web application |
| `seed_500_questions.py` | Seeds the database with the question set |
| `ingest_leetcode.py` | Loads LeetCode-style coding questions |
| `ingest_all_coding.py` | Loads all coding questions |
| `dataset_500_questions_enhanced.json` | Question dataset |
| `training_data.json` | Training data for the model |
| `requirements.txt` | Python dependencies |

## Requirements

- Python 3.10 or newer
- Git (only if you want to clone; you can also download a ZIP)

## How to Run (Windows)

### 1. Get the project

**Option A: Download ZIP (easiest)**
1. On the GitHub page, click the green **Code** button, then **Download ZIP**
2. Right-click the ZIP file and choose **Extract All**

**Option B: Clone with Git**
```
git clone https://github.com/meesalasaisree/Resume_AI_Classifier.git
```

### 2. Open Command Prompt in the project folder

Open the extracted folder in File Explorer, click the address bar, type `cmd` and press Enter.

### 3. Create and activate a virtual environment

```
python -m venv venv
venv\Scripts\activate
```

### 4. Install dependencies

```
pip install -r requirements.txt
```

### 5. Prepare the data

Run these once to create the databases:

```
python seed_500_questions.py
python ingest_leetcode.py
python ingest_all_coding.py
```

### 6. Start the app

```
streamlit run web_app.py
```

The app opens automatically in your browser at `http://localhost:8501`.

## Notes

- The trained model folders (`saved_grading_model`, `fine_tuned_evaluator_checkpoint`) and private data files are not included in this repository because of their size and privacy. [Add a download link or instructions here if the app needs them.]
- If a setting or API key is required, create the file `.streamlit/secrets.toml` and add it there. [Describe which keys are needed, if any.]

## Author

Meesala Sai Sree
