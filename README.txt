SKILLFORGE
==========

A local-first developer tool to create, test, and run deterministic Skills.

WHAT IS A SKILL?
----------------
A Skill is:
- A deterministic procedure represented as structured steps
- Parameterized with typed inputs
- Has explicit preconditions and verifiable postconditions (checks)
- Runnable in a sandbox against a target directory/repo
- Testable with fixtures and regression (golden) diffs

INSTALLATION
------------
    pip install -e .

For development:
    pip install -e ".[dev]"

QUICK START
-----------
1. Initialize SkillForge:
    skillforge init

2. Check your environment:
    skillforge doctor

3. Create a new skill:
    skillforge new my_skill

4. Test a skill:
    skillforge test skills/my_skill

5. Run a skill:
    skillforge run skills/my_skill --target /path/to/repo

COMMANDS
--------
- init              Create ~/.skillforge/ with default config
- doctor            Verify environment (python, git, rsync)
- new               Create a new skill scaffold
- generate          Generate skill from a spec file
- import            Import from GitHub Actions workflow
- wrap              Wrap an existing script as a skill
- record            Start recording a session
- stop              Stop recording session
- compile           Compile recording into a skill
- run               Execute a skill
- test              Run fixture tests
- bless             Store golden regression artifacts
- cassette          Record/replay external command outputs
- lint              Validate skill structure

SKILL FOLDER STRUCTURE
----------------------
skills/<skill_name>/
    SKILL.txt           Human-readable procedure
    skill.yaml          Skill schema and configuration
    checks.py           Check implementations
    fixtures/           Test fixtures
        happy_path/
            input/
            expected/
    cassettes/          Recorded command outputs
    reports/            Run reports

CONFIGURATION
-------------
User config is stored at ~/.skillforge/config.yaml

Config options:
- default_sandbox_root: path for sandbox directories
- max_log_kb_per_command: max log size (default 256)
- redact_patterns: regex patterns for secret redaction
- ignore_paths: glob patterns to ignore during copy
- default_shell: bash or zsh

PLATFORMS
---------
- macOS
- Linux
- Python 3.11+

LICENSE
-------
MIT License
