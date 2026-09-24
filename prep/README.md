# Interview prep content

Plain-text question banks that HireTrack loads into the database on startup.
Edit them in any editor and send a PR; new questions appear the next time the API starts.
Existing progress is never overwritten.

| Folder | Format |
| --- | --- |
| `dsa/problems.csv` | `title,topic,difficulty,url` |
| `python/`, `sql/`, `backend/`, `genai/`, `system-design/` | `questions.md` |

Question file format:

```markdown
## What is the GIL?
Tags: concurrency, cpython

Model answer in Markdown. Everything until the next `##` heading belongs to this question.
```

Answers are short on purpose: they are the points to hit in an interview, not a textbook.
