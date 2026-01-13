====================================================================
SKILLFORGE v1 — FULL BUILD SPECIFICATION (PLAIN TEXT)
	1.	PRODUCT DEFINITION

Name: SkillForge

One-line description:
SkillForge is a local-first developer tool to create, test, and run “Skills”: deterministic, reusable procedural tasks (instructions + executable steps + checks) that can be used by AI agents or humans.

What a Skill is:
	•	A deterministic procedure represented as structured steps
	•	Parameterized with typed inputs
	•	Has explicit preconditions and verifiable postconditions (“checks”)
	•	Runnable in a sandbox against a target directory/repo
	•	Testable with fixtures and regression (“golden”) diffs
	•	Can mock external command outputs via “cassettes” for deterministic tests

What a Skill is NOT:
	•	Not a marketplace
	•	Not hosted SaaS
	•	Not a chat prompt pack
	•	Not a compliance / responsible-AI product
	•	Not a multi-user platform

Primary goals:
	•	Multiple creation pathways beyond recording (compose, spec, import, wrap)
	•	Deterministic execution and regression testing
	•	High quality developer UX as a CLI tool

Platforms:
	•	macOS + Linux
	•	Python 3.11+

	2.	HIGH-LEVEL USER FLOWS (MUST WORK)

Flow A: New skill from scratch
	•	skillforge new release_prep
	•	edit generated files (SKILL.txt + skill.yaml + checks.py)
	•	add fixtures
	•	skillforge test skills/release_prep
	•	skillforge bless skills/release_prep –fixture happy_path

Flow B: Generate from a structured spec
	•	skillforge generate –from spec.txt –out skills/release_prep
	•	skillforge test skills/release_prep

Flow C: Import existing automation (GitHub Actions)
	•	skillforge import github-action .github/workflows/release.yml –out skills/release_prep
	•	skillforge lint skills/release_prep
	•	skillforge test skills/release_prep

Flow D: Wrap an existing script into a skill
	•	skillforge wrap script scripts/bump_version.py –out skills/bump_version
	•	skillforge run skills/bump_version –target /path/to/repo

Flow E: Record then compile (Git-only MVP acceptable)
	•	skillforge record –name bump_version –workdir /path/to/repo
	•	(user runs commands manually)
	•	skillforge stop
	•	skillforge compile <recording_id> –out skills/bump_version
	•	skillforge run skills/bump_version –target /path/to/clean/repo_clone

Flow F: Deterministic testing when external commands/APIs are involved
	•	skillforge cassette record skills/release_prep –fixture happy_path
	•	skillforge cassette replay skills/release_prep –fixture happy_path
	•	skillforge test skills/release_prep

	3.	KEY PRINCIPLE: DETERMINISM

SkillForge must aim for deterministic behavior:
	•	Same inputs + same target repo state + same cassette mode => same outputs
	•	Sandbox execution by default
	•	Avoid hidden mutable global state where possible
	•	Provide “plan” output and run reports for reproducibility

	4.	PROJECT STRUCTURE

Repository layout:
	•	skillforge/ (python package)
	•	tests/
	•	pyproject.toml
	•	README.txt (plain text)
	•	LICENSE

Install and run:
	•	Python package with console entrypoint “skillforge”

	5.	GLOBAL CONFIG AND STORAGE

User config directory:
~/.skillforge/

Files:
	•	~/.skillforge/config.yaml
	•	~/.skillforge/recordings/
	•	~/.skillforge/logs/
	•	~/.skillforge/cache/ (optional)

Config keys (minimum):
	•	default_sandbox_root: path
	•	max_log_kb_per_command: integer (default 256)
	•	redact_patterns: list of regex strings
	•	ignore_paths: list of glob patterns
	•	default_shell: “bash” or “zsh” (recording uses it)

	6.	CLI COMMANDS (REQUIRED)

Use Typer.

Commands:

A) skillforge init
	•	Creates ~/.skillforge/ with default config.yaml
	•	Prints where it stored config

B) skillforge doctor
	•	Verifies environment: python version, git availability, rsync/cp availability
	•	Prints warnings if missing

C) skillforge new  [–out skills/]
	•	Creates a Skill folder scaffold (see Section 7)
	•	Generates:
	•	SKILL.txt (human procedure)
	•	skill.yaml (schema with placeholders)
	•	checks.py (stub checks)
	•	fixtures/happy_path/{input,expected}
	•	reports/ (empty)
	•	cassettes/ (empty)

D) skillforge generate –from <spec_file> –out <skill_dir>
	•	Parses a structured “spec.txt” and outputs a scaffold Skill folder + generated steps/checks
	•	No LLM required. Use deterministic templates/mappings.
	•	If mapping fails, insert TODO placeholders into SKILL.txt and skill.yaml

E) skillforge import github-action <workflow_yml> –out <skill_dir>
	•	Converts GitHub Actions job steps into Skill steps:
	•	“run:” entries -> shell steps
	•	“working-directory:” -> step cwd
	•	“env:” -> step env
	•	“uses:” entries -> either ignore with a warning or convert into a placeholder step with TODO
	•	Output: skill.yaml + SKILL.txt + checks.py stubs
	•	Also create a fixture folder from repo (optional: user can populate)

F) skillforge wrap script <script_path> –out <skill_dir>
	•	Supports basic inference of script arguments and turns it into a skill:
	•	If argparse detected: parse parser definitions by running script with “–help” and parsing output
	•	If click/typer: parse “–help” output similarly
	•	Create skill.yaml with inputs inferred and a single shell step to run script
	•	Add checks stub and a fixture scaffold

G) skillforge record –name <skill_name> –workdir  [–mode git] [–shell bash|zsh]
	•	Starts a recording session (Git-only MVP is acceptable)
	•	Implementation approach:
	•	Create a session id and store under ~/.skillforge/recordings//
	•	Save session_start event
	•	Launch a subshell in the target directory that logs each executed command and output
	•	Recording must capture:
	•	timestamp, cwd
	•	command string
	•	exit code
	•	duration
	•	stdout/stderr (truncated to configured max)
	•	git status and git diff after each command (Git-only mode)
	•	Minimal success: ability to record commands and diffs even if stdout capture is coarse

H) skillforge stop
	•	Stops the current recording session
	•	Writes session_end event
	•	Prints the recording_id

I) skillforge compile <recording_id> –out <skill_dir>
	•	Converts recording events into:
	•	skill.yaml with steps
	•	SKILL.txt procedure summary
	•	checks.py auto-generated checks
	•	Heuristics for compile are detailed in Section 10

J) skillforge run <skill_dir> –target  [–sandbox ] [–no-sandbox] [–dry-run] [–interactive] [–env KEY=VAL …]
	•	Executes the skill against a target directory
	•	Default behavior: create sandbox copy of target and run in sandbox
	•	Produces a run report JSON and logs under skill_dir/reports/
	•	Supports:
	•	–dry-run: prints resolved plan without executing
	•	–interactive: on step failure, prompt retry/skip/open shell in sandbox
	•	–no-sandbox: run directly in target (print a warning)
	•	Run must apply cassettes if cassette replay is enabled (Section 13)

K) skillforge test <skill_dir>
	•	Discovers fixtures in skill_dir/fixtures/*/
	•	For each fixture:
	•	copies fixture/input to sandbox
	•	runs skill
	•	validates checks
	•	compares resulting filesystem to fixture/expected (if present)
	•	compares to golden diff if blessed (if present)
	•	Outputs a test report summary and per-fixture run reports

L) skillforge bless <skill_dir> –fixture 
	•	Runs the skill on the fixture and stores regression artifacts:
	•	expected_changed_files.json
	•	expected_diff.patch (unified diff for text files)
	•	expected_hashes.json (file hashes)
	•	Subsequent test runs compare against these blessed artifacts

M) skillforge cassette record <skill_dir> –fixture 
	•	Runs the skill on the fixture in “record” mode and records external command outputs (see Section 13)

N) skillforge cassette replay <skill_dir> –fixture 
	•	Runs the skill using recorded cassettes so external commands are not executed

O) skillforge lint <skill_dir>
	•	Performs non-AI lint rules (see Section 14)

	7.	SKILL FOLDER STRUCTURE (REQUIRED)

Skill folder layout:
skills//
	•	SKILL.txt
	•	skill.yaml
	•	checks.py
	•	run.py (optional, can be generated empty)
	•	fixtures/
	•	happy_path/
	•	input/
	•	expected/
	•	cassettes/
	•	reports/
	•	_generated/ (optional internal artifacts)

Notes:
	•	Use SKILL.txt (plain text) not markdown.
	•	All generation should be deterministic and stable.

	8.	SKILL YAML SCHEMA (REQUIRED)

Minimum schema (YAML):

name: string
version: string (default “0.1.0”)
description: string

requirements:
commands: list of strings (optional)
python_packages: list of strings (optional)

inputs: list of input objects
input object fields:
	•	name: string
	•	type: one of: string, enum, int, float, bool, path
	•	description: string (optional)
	•	default: any (optional)
	•	enum_values: list (required if type=enum)
	•	required: bool (default true)
	•	pattern: regex string (optional)

preconditions: list of strings (optional)
(This is informational; enforcement can be via checks.)

steps: list of step objects

checks: list of check objects

metadata: free-form mapping (optional)
	9.	STEP TYPES (REQUIRED)

Each step has:
	•	id: string
	•	type: string
	•	name: string (optional)
	•	cwd: string (optional, supports placeholders like {target_dir})
	•	env: mapping (optional)
	•	timeout_sec: int (optional)
	•	allow_failure: bool (default false)

Supported step types:

A) shell
Fields:
	•	command: string
	•	expect_exit: int (default 0)
Behavior:
	•	Execute command using subprocess (shell=True is OK but prefer list form if feasible)
	•	Capture stdout/stderr to logs
	•	Apply secret redaction before storing logs

B) python
Fields:
	•	module: string OR file: string OR function: “module:function”
	•	args: list of strings (optional)
Behavior:
	•	Execute python module/file/function within the sandbox environment

C) file.replace
Fields:
	•	path: string
	•	pattern: string (regex)
	•	replace_with: string
Behavior:
	•	Load text file, apply regex substitution, write back

D) file.template
Fields:
	•	path: string
	•	template: string (inline) OR template_file: string
	•	mode: “overwrite” or “if_missing”
Behavior:
	•	Render placeholders using inputs and write file

E) json.patch
Fields:
	•	path: string
	•	operations: list of RFC6902-like ops (add/replace/remove) OR a simple mapping merge
Behavior:
	•	Load JSON, apply patch, write

F) yaml.patch
Fields:
	•	path: string
	•	operations: similar to json.patch
Behavior:
	•	Load YAML, apply patch, write

	10.	CHECK TYPES (REQUIRED)

Each check has:
	•	id: string
	•	type: string

Supported checks:

A) file_exists
	•	path: string

B) file_contains
	•	path: string
	•	contains: string OR regex: string

C) git_clean
	•	cwd: string (default {target_dir})
Behavior:
	•	git status --porcelain must be empty

D) stdout_contains
	•	step_id: string
	•	contains: string OR regex: string

E) exit_code
	•	step_id: string
	•	equals: int

	11.	PLACEHOLDER SUBSTITUTION

The system must support placeholder substitution in:
	•	cwd, paths, commands, template strings, env values

Placeholders:
	•	{target_dir}
	•	{sandbox_dir}
	•	plus any input: {input_name}

If a placeholder is missing at runtime, fail with clear error.
	12.	SANDBOXING

Default run behavior:
	•	Create a sandbox directory under:
	•	skill_dir/reports/_<run_id>/sandbox/
OR a global configured sandbox_root
	•	Copy target directory into sandbox
	•	Execute steps in sandbox

Copy approach:
	•	Prefer rsync if available, else shutil.copytree (excluding .git optionally but recommended to keep .git for git_clean checks)
	•	Support ignore patterns from:
	•	~/.skillforge/config.yaml ignore_paths
	•	target/.skillforgeignore
	•	skill_dir/.skillforgeignore (optional)

–no-sandbox:
	•	Run directly in target directory
	•	Print warning and require user confirmation unless –yes (optional)

	13.	CASSETTES (MOCK/REPLAY) SYSTEM

Purpose:
Enable deterministic tests when steps run external commands that depend on network/APIs.

Scope (MVP):
Cassette system applies to “shell” steps only.

Mechanism:
	•	In cassette record mode:
	•	For each shell step, store:
	•	step_id
	•	resolved command
	•	cwd
	•	exit code
	•	stdout (full, redacted)
	•	stderr (full, redacted)
	•	Store as JSON file per fixture run:
skill_dir/cassettes/<fixture_name>.json
	•	In cassette replay mode:
	•	Do not execute the command
	•	Instead return recorded stdout/stderr/exit code matching step_id
	•	If mismatch (step_id missing), fail with clear message

Important:
	•	Cassette matching must be stable: by step_id
	•	Store also a hash of the resolved command for diagnostics (do not require exact match for MVP, but warn)

	14.	LINTING RULES (NON-AI)

Implement skillforge lint <skill_dir> with these rules:

Errors:
	•	skill.yaml missing required fields (name, steps, inputs)
	•	duplicate step ids
	•	step references missing (check references step_id not found)
	•	invalid placeholder usage (unknown placeholder)
	•	file paths that are absolute (start with /) inside steps/checks (unless explicitly allowed)
	•	steps list empty

Warnings:
	•	steps exist but checks list empty
	•	steps without any checks referencing them (heuristic)
	•	shell commands that appear non-deterministic:
	•	contains “date”, “time”, “random”, “uuidgen” without pinning/controlled output
	•	presence of “sudo”
	•	presence of “rm -rf”
	•	missing fixtures/happy_path

Output:
	•	human-readable list
	•	exit code non-zero if any errors

	15.	SECRET REDACTION

Redaction must apply to:
	•	recorded stdout/stderr logs
	•	cassettes

Default regex patterns (configurable):
	•	AWS access keys (AKIA… style)
	•	“Bearer ”
	•	“password=…”
	•	“token=…”
	•	“apikey=…”

Implement:
	•	apply patterns to output strings before saving
	•	do not attempt perfect security; aim for “don’t accidentally store obvious secrets”

	16.	RECORDING IMPLEMENTATION DETAILS (GIT-ONLY MVP)

Goal: “good enough” for one-person demos.

Implement a recording session as:
	•	Create session folder: ~/.skillforge/recordings//
	•	Write events.jsonl
	•	Write logs/ files per command

How to intercept commands:
Option A (simpler):
	•	Provide “skillforge record” that launches a subshell and instructs user to prefix commands with a helper, e.g. “sf ”
	•	This is simplest to ship; still validates product concept
	•	The subshell prints a reminder “Use sf  to record commands”

Option B (better):
	•	Launch a shell with a hook (bash PROMPT_COMMAND, zsh preexec) to capture commands automatically
	•	Requires more engineering; optional after MVP

For MVP, do Option A.

Helper command within the recording session:
	•	“sf ” executes the command, captures exit code, stdout/stderr, duration, and git status/diff.

Git diff capture:
	•	After each command:
	•	status: git status –porcelain
	•	diff: git diff
Store status and diff as separate events and also write diff to a file for large diffs.

Also capture:
	•	session_start includes:
	•	OS, python version, git version
	•	workdir
	•	initial git status and diff

	17.	COMPILATION HEURISTICS (RECORDING -> SKILL)

Compile should produce a usable skill.yaml without needing AI.

Input: recording events.jsonl

Heuristics:
	•	Ignore commands in an ignore list:
	•	ls, pwd, clear, history, echo (unless echo writes files, ignore)
	•	Normalize “cd ”:
	•	Track cwd changes; do not emit cd as steps
	•	Convert absolute paths under the workdir to {target_dir}/relative_path
	•	Create one shell step per recorded command (that survived filtering)
	•	For each step:
	•	set cwd based on recording event
	•	expect_exit from recorded exit code if 0 else set expect_exit 0 and mark allow_failure true (OR set expect_exit to recorded and warn; choose deterministic default: keep expect_exit = recorded)

Auto-check generation:
	•	If git repo:
	•	if final state in recording had clean status: add git_clean check
	•	From diffs:
	•	Extract changed file paths from git diff --name-only (compute during compile by parsing diff or by capturing during record)
	•	Add file_exists check for each changed file (cap at N=20 for MVP; if more, add one check “changed_files_count_at_least” optional or just sample)

Generate SKILL.txt:
	•	Summary
	•	Preconditions (workdir is git repo; required commands)
	•	Steps (numbered list derived from steps)
	•	Expected outputs (changed files list)

Generate checks.py:
	•	Implement the check types here or in core library; checks.py can import from skillforge runtime.
	•	For MVP, checks.py can be a thin wrapper calling runtime checks.

	18.	SPEC GENERATION (SPEC.TXT -> SKILL)

Input format (spec.txt) is plain text with strict headers:

Example:

SKILL NAME: Release Prep
DESCRIPTION: Prepare a repo for release
INPUTS:
	•	repo_root: path (required)
	•	bump_type: enum[patch,minor,major] (default patch)
PRECONDITIONS:
	•	git status is clean
STEPS:
	•	run tests: pytest -q
	•	bump version: python scripts/bump_version.py –{bump_type}
	•	update changelog: python scripts/gen_changelog.py
CHECKS:
	•	tests passed
	•	CHANGELOG.md contains “##”
	•	git status is clean

Parsing rules:
	•	Simple line-based parsing; ignore extra whitespace
	•	Map “run tests” to shell step “pytest -q” if command present after colon
	•	For checks:
	•	“git status is clean” -> git_clean
	•	“file contains” patterns -> file_contains
	•	“tests passed” -> exit_code check referencing the test step

If ambiguous, generate TODO placeholders.
	19.	GITHUB ACTIONS IMPORT (WORKFLOW -> SKILL)

Support minimal subset:
	•	Find first workflow job (or all jobs; for MVP choose first job and warn if multiple)
	•	For each step:
	•	if “run:” exists:
	•	create shell step with that command text
	•	capture “working-directory” if present
	•	capture “env” if present
	•	if “uses:” exists:
	•	create placeholder step type shell with command “echo TODO: manual step for ” OR ignore and warn
	•	Add default inputs:
	•	target_dir path
	•	Add default check:
	•	git_clean (warning: might not apply; allow user to remove)
	•	Generate SKILL.txt describing original workflow file and job name

	20.	FIXTURE TESTS

Fixture structure:
skill_dir/fixtures/<fixture_name>/
	•	input/ (the starting state)
	•	expected/ (optional; the expected ending state)
	•	fixture.yaml (optional; can specify inputs for that fixture)

Test algorithm:
	•	Create sandbox
	•	Copy input -> sandbox/target
	•	Resolve inputs:
	•	target_dir = sandbox/target
	•	any additional inputs:
	•	from fixture.yaml if present else defaults
	•	Run the skill
	•	Run checks
	•	If expected exists:
	•	Compare resulting files to expected:
	•	For text files: exact match
	•	For binary: hash match
	•	Also ensure no unexpected extra files unless fixture.yaml allows it (optional)

Reporting:
	•	For each fixture: pass/fail, step timings, diff summary

	21.	GOLDEN DIFFS (BLESS/REGRESSION)

Bless operation:
	•	Run skill on fixture
	•	Compute:
	•	changed_files list
	•	unified diff for text files (if git exists inside fixture, use git diff; else use difflib)
	•	file hashes for changed files
	•	Store under:
skill_dir/fixtures/<fixture_name>/_golden/
	•	expected_changed_files.json
	•	expected_diff.patch
	•	expected_hashes.json

Test operation (when golden exists):
	•	Recompute changed files and diff
	•	Compare:
	•	changed_files set must match (or be subset/superset depending on strictness; for MVP strict match)
	•	diff must match (text diff)
	•	hashes must match for changed files

	22.	RUN REPORT FORMAT

For every run (run/test/bless/cassette record/replay), write:
skill_dir/reports/_<run_id>/
	•	run_report.json
	•	logs/step_.stdout
	•	logs/step_.stderr
	•	sandbox/ (unless no-sandbox)

run_report.json fields:
	•	run_id
	•	skill_name
	•	started_at
	•	finished_at
	•	mode: run/test/bless/cassette_record/cassette_replay
	•	target_original_path
	•	sandbox_path
	•	inputs_resolved (mapping)
	•	steps: list:
	•	id
	•	type
	•	command (resolved if shell)
	•	cwd (resolved)
	•	exit_code
	•	duration_ms
	•	stdout_log_path
	•	stderr_log_path
	•	status: success/failed/skipped
	•	checks: list:
	•	id
	•	type
	•	status
	•	message
	•	summary:
	•	success: bool
	•	failed_step_id (optional)
	•	changed_files (optional)

	23.	IMPLEMENTATION NOTES

Language/libraries:
	•	Python 3.11+
	•	Typer for CLI
	•	Rich for output formatting
	•	PyYAML for YAML
	•	Standard library for everything else where possible
	•	Use git via subprocess calls (avoid GitPython dependency for MVP)

Testing:
	•	Use pytest recommended
	•	Unit tests required for:
	•	placeholder substitution
	•	schema validation
	•	step execution for shell and file.replace
	•	check implementations
	•	spec parser
	•	github action importer (simple workflow fixture)
	•	bless/test comparison logic

Coding style:
	•	Clear error messages
	•	No hidden background daemons
	•	No long-running watchers in MVP
	•	Logs must be readable and stored in files

	24.	MVP DELIVERABLES CHECKLIST

Must deliver:
	•	All CLI commands listed in Section 6 (record can be helper-prefix MVP)
	•	Skill schema + step types + check types implemented
	•	Sandbox runner
	•	Fixture testing + bless/golden diffs
	•	Cassette record/replay
	•	Linting rules
	•	Doctor/init

Must demonstrate:
	•	Create a skill via “new” and run/test it
	•	Generate from spec and run/test it
	•	Import GitHub Action and run/lint it (even if placeholder steps exist)
	•	Record then compile then run the resulting skill

	25.	FINAL INSTRUCTIONS TO THE CODING AI TOOL

Implement SkillForge exactly to this specification:
	•	Keep it deterministic and local-first
	•	Avoid marketplace/community features
	•	Do not add responsible-AI, compliance, or governance functionality
	•	Prioritize clean CLI UX, good error messages, and strong tests
	•	Prefer simple stable approaches over clever but fragile ones
	•	If something is ambiguous, choose the simplest deterministic option and document it in README.txt

END OF DOCUMENT