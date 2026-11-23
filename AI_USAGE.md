# AI Usage Documentation

## Tools Used

| Tool | Version / Access | What I used it for |
|------|------------------|--------------------|
| Claude | Claude Opus 5.5, claude.ai | Generated the initial project scaffold: schema, Flask routes, validation, templates, CSS, Job Match algorithm, unit tests, README |
| [YOU WRITE THIS: any other tool, e.g. ChatGPT or Copilot] | | |

## Key Prompts

**"Okay walk me through it"**, followed by terminal screenshots at each step:
   - `zsh: command not found: python` / `mysql` → use `python3`; install MySQL with Homebrew
   - `ERROR 1045 (28000): Access denied for user 'root'@'localhost'` → the password had been set to the literal placeholder text
   - `ERROR: Could not open requirements file` → I was in my home folder, not the project folder
   - *Result:* the app running locally on macOS with MySQL 26.10.

## What AI Generated

| File | What Claude produced |
|------|----------------------|
| `schema.sql` | 4 tables with PKs, FKs (`ON DELETE CASCADE`), ENUMs, JSON columns, a CHECK constraint on salary range, indexes, and sample data |
| `database.py` | Connection helper reading settings from `.env`, and one function per query. All SQL uses `%s` placeholders |
| `app.py` | CRUD routes for all 4 tables, server-side validation, delete confirmation, dashboard, error pages |
| `matching.py` | Job Match algorithm (case-insensitive, alias-aware, ranked) |
| `templates/`, `static/style.css` | All pages and styling |
| `tests/test_matching.py` | Unit tests for the matching logic |

### Design decisions the AI made (and why)

- **SQL lives only in `database.py`.** Routes stay short and the queries are in one place.
- **Parameterized queries everywhere** (`cursor.execute(sql, (value,))`) to prevent SQL injection.
- **Match % is based on the job's requirements**, not the user's skills. This reproduces the spec example exactly (Data Analyst = 2/3 = 67%, missing Tableau).
- **Interview rounds are edited as normal form rows** and converted to a JSON array on save, so users never type raw JSON.
- **Deletes need a confirmation page + POST**, so a link click or browser prefetch can never delete data. The page shows how many child rows the cascade will remove.
- **Validation is server-side**, not only HTML `required`, because HTML checks can be bypassed.

### How the AI output was checked

Claude ran the app against a local MySQL-compatible server and an automated script that:
- loaded every page (and 404 for missing records)
- ran a full create / edit / delete cycle on all 4 tables
- confirmed cascade deletes removed child rows
- submitted invalid data to every form and confirmed the right error messages appeared
- confirmed Job Match output matches the spec example

## What Worked Well

- Claude produced a complete first version from the spec in one pass. It had every required page, all 4 tables, and the Job Match feature, which saved me the boilerplate.
- The README setup steps worked once my machine had the right tools. The dashboard loaded with sample data on the first run after setup.
- Pasting exact error messages and terminal screenshots got fast, specific fixes. For example, it caught that my password was literally the placeholder text, and that I was running pip from the wrong folder.
- Going one step at a time and confirming each result before moving on worked better than running every command at once.
- When I asked Claude to write my "What I Modified" and "Lessons Learned" sections for me, it refused because they would describe work I hadn't done. It walked me through doing the work instead, which is why this file reflects what actually happened.

## What I Modified

- **Setup:** MacBook Pro (Apple Silicon), macOS, Python 3.11.4, MySQL 26.10.0 installed with Homebrew
- **Issues and fixes:**
  - `python` was not found. macOS uses `python3` and `pip3`.
  - MySQL was not installed. Installed it with `brew install mysql` and started it with `brew services start mysql`.
  - Setting the root password: I copied the placeholder text from the instructions literally, twice, so the password was not what I expected and I got `ERROR 1045 Access denied`. I learned to read what a command actually does before running it.
  - Ran `pip install -r requirements.txt` from my home folder and got "No such file". Fixed by running `cd` into the project folder first.
  - Port 5000 is used by AirPlay on macOS, so I ran the app with `PORT=5001 python3 app.py`.
  - After these fixes, the dashboard loaded with all sample data.

## Lessons Learned

- AI-generated code is only as good as the environment it runs in. The code worked, but my Mac needed Python, MySQL and the right folder before anything ran. Most of my problems were setup, not code.
- Read commands before running them. I copied a placeholder password into MySQL twice and locked myself out until I worked out what had actually been saved.
- Exact error text matters. "It doesn't work" gets generic advice. Pasting `ERROR 1045 Access denied` or the full pip error got the actual fix.
- AI is fast at boilerplate (CRUD routes, templates, CSS), but I still have to understand it well enough to explain and change it. The graded parts are my modifications and what I learned, not the generated code.
- Keep secrets out of the repo. The password lives in `.env`, which `.gitignore` excludes, and I checked `git status` before committing.